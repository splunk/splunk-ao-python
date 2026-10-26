import asyncio
import json
from collections.abc import Generator
from unittest.mock import patch

import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider

from splunk_ao import get_tracing_headers, log, splunk_ao_context
from splunk_ao.schema.trace import SPAN_TYPE
from tests.testutils.setup import setup_mock_logstreams_client, setup_mock_projects_client, setup_mock_traces_client


@pytest.fixture
def initialized_context() -> Generator[None, None, None]:
    with (
        patch("splunk_ao.logger.logger.Traces") as traces,
        patch("splunk_ao.logger.logger.Projects") as projects,
        patch("splunk_ao.logger.logger.AgentStreams") as agent_streams,
    ):
        setup_mock_traces_client(traces)
        setup_mock_projects_client(projects)
        setup_mock_logstreams_client(agent_streams)
        splunk_ao_context.init(project="project", agent_stream="stream")
        yield
        splunk_ao_context.reset()


def test_top_level_calls_create_independent_otel_traces(initialized_context: None) -> None:
    @log(span_type="workflow")
    def operation(value: str) -> str:
        return value

    assert operation("first") == "first"
    assert operation("second") == "second"

    logger = splunk_ao_context.get_logger_instance()
    spans = logger._sink.spans

    assert logger.current_parent() is None
    assert splunk_ao_context.get_current_trace() is None
    assert len(spans) == 2
    assert spans[0].context.trace_id != spans[1].context.trace_id


def test_nested_decorators_share_trace_and_preserve_parenting(initialized_context: None) -> None:
    @log(span_type="llm")
    def model_call(value: str) -> str:
        return value.upper()

    @log(span_type="workflow")
    def operation(value: str) -> str:
        return model_call(value)

    assert operation("hello") == "HELLO"

    logger = splunk_ao_context.get_logger_instance()
    workflow = next(span for span in logger._sink.spans if span.name.endswith("operation"))
    llm = next(span for span in logger._sink.spans if span.name == "chat")

    assert workflow.context.trace_id == llm.context.trace_id
    assert llm.parent.span_id == workflow.context.span_id
    assert logger.current_parent() is None


def test_nested_tools_activate_their_own_context_and_preserve_parenting(initialized_context: None) -> None:
    # Given: two decorated tools nested beneath an agent, with no framework callbacks.
    headers = {}

    @log(span_type="tool", name="inner")
    def inner() -> str:
        headers["inner"] = get_tracing_headers()["traceparent"]
        return "done"

    @log(span_type="tool", name="outer")
    def outer() -> str:
        headers["outer"] = get_tracing_headers()["traceparent"]
        return inner()

    @log(span_type="agent", name="agent")
    def agent() -> str:
        return outer()

    # When: the nested calls finish normally.
    assert agent() == "done"

    # Then: every tool is active during execution and keeps the actual calling tool as parent.
    logger = splunk_ao_context.get_logger_instance()
    spans = {span.name: span for span in logger._sink.spans}
    assert len(spans) == 3
    agent_span = spans["invoke_agent agent"]
    outer_span = spans["execute_tool outer"]
    inner_span = spans["execute_tool inner"]
    assert outer_span.parent == agent_span.context
    assert inner_span.parent == outer_span.context
    assert agent_span.context.trace_id == outer_span.context.trace_id == inner_span.context.trace_id
    for name, span in (("inner", inner_span), ("outer", outer_span)):
        assert int(headers[name].split("-")[2], 16) == span.context.span_id
        assert span.attributes["gen_ai.operation.name"] == "execute_tool"
    assert logger.current_parent() is None
    assert not otel_trace.get_current_span().get_span_context().is_valid


@pytest.mark.asyncio
async def test_async_nested_tools_preserve_parenting_and_caller_context(initialized_context: None) -> None:
    # Given: nested async tools within a caller-owned agent operation.
    logger = splunk_ao_context.get_logger_instance()
    logger.start_trace(input="request")
    caller = logger.add_agent_span(input="request", name="caller")
    caller_context = otel_trace.get_current_span().get_span_context()
    contexts = {}

    @log(span_type="tool", name="inner")
    async def inner() -> str:
        contexts["inner"] = otel_trace.get_current_span().get_span_context()
        await asyncio.sleep(0)
        return "done"

    @log(span_type="tool", name="outer")
    async def outer() -> str:
        contexts["outer"] = otel_trace.get_current_span().get_span_context()
        return await inner()

    # When: async decorated work completes beneath that caller.
    assert await outer() == "done"

    # Then: only decorator-owned operations complete, with their original active identities.
    assert logger.current_parent() is caller
    assert otel_trace.get_current_span().get_span_context() == caller_context
    logger.conclude(output="done", conclude_all=True)
    spans = {span.name: span for span in logger._sink.spans}
    assert len(spans) == 3
    assert spans["execute_tool outer"].parent == spans["invoke_agent caller"].context
    assert spans["execute_tool inner"].parent == spans["execute_tool outer"].context
    assert contexts["outer"] == spans["execute_tool outer"].context
    assert contexts["inner"] == spans["execute_tool inner"].context


@pytest.mark.parametrize("sibling_type", ["tool", "llm", "retriever", "workflow", "agent"])
def test_calls_after_nested_tool_remain_siblings(initialized_context: None, sibling_type: SPAN_TYPE) -> None:
    @log(span_type="tool", name="inner")
    def inner() -> str:
        return "inner result"

    @log(span_type="tool", name="outer")
    def outer() -> str:
        return inner()

    @log(span_type=sibling_type, name="sibling")
    def sibling() -> str:
        return "sibling result"

    @log(span_type="agent", name="caller")
    def caller() -> str:
        outer()
        return sibling()

    assert caller() == "sibling result"
    logger = splunk_ao_context.get_logger_instance()
    spans = logger._sink.spans
    assert len(spans) == 4
    agent = next(span for span in spans if span.name == "invoke_agent caller")
    outer_span = next(span for span in spans if span.name == "execute_tool outer")
    inner_span = next(span for span in spans if span.name == "execute_tool inner")
    sibling_span = next(span for span in spans if span not in (agent, outer_span, inner_span))
    assert inner_span.parent == outer_span.context
    assert outer_span.parent == sibling_span.parent == agent.context
    assert logger.current_parent() is None


@pytest.mark.parametrize("span_type", ["agent", "workflow"])
def test_operation_without_return_inherits_last_child_output(initialized_context: None, span_type: SPAN_TYPE) -> None:
    # Given: an operation that prints its child's answer without returning it
    @log(span_type="llm")
    def model_call() -> str:
        return "Insufficient balance for loan"

    @log(span_type=span_type)
    def operation() -> None:
        print(model_call())

    # When: the decorated operation completes
    assert operation() is None

    # Then: the operation's output contains the child's answer
    logger = splunk_ao_context.get_logger_instance()
    parent = next(span for span in logger._sink.spans if span.name.endswith("operation"))
    output = json.loads(parent.attributes["gen_ai.output.messages"])
    assert output[0]["parts"] == [{"type": "text", "content": "Insufficient balance for loan"}]
    assert logger.current_parent() is None


@pytest.mark.parametrize("result", ["", "A different answer"])
def test_explicit_operation_output_is_not_replaced_by_child(initialized_context: None, result: str) -> None:
    # Given: an operation with a child answer and an explicit return value
    @log(span_type="llm")
    def model_call() -> str:
        return "Child answer"

    @log(span_type="agent")
    def operation() -> str:
        model_call()
        return result

    # When: the operation completes
    assert operation() == result

    # Then: even an explicitly empty answer is preserved
    logger = splunk_ao_context.get_logger_instance()
    parent = next(span for span in logger._sink.spans if span.name.endswith("operation"))
    output = json.loads(parent.attributes["gen_ai.output.messages"])
    assert output[0]["parts"] == [{"type": "text", "content": result}]


@pytest.mark.asyncio
async def test_async_operation_without_return_inherits_last_child_output(initialized_context: None) -> None:
    # Given: an async operation that does not return its child's answer
    @log(span_type="llm")
    async def model_call() -> str:
        return "Async answer"

    @log(span_type="agent")
    async def operation() -> None:
        await model_call()

    # When: the operation completes
    assert await operation() is None

    # Then: the parent captures its child's output without changing the return value
    logger = splunk_ao_context.get_logger_instance()
    parent = next(span for span in logger._sink.spans if span.name.endswith("operation"))
    output = json.loads(parent.attributes["gen_ai.output.messages"])
    assert output[0]["parts"] == [{"type": "text", "content": "Async answer"}]


def test_failed_operation_does_not_inherit_successful_child_output(initialized_context: None) -> None:
    # Given: an operation that fails after a successful child
    @log(span_type="llm")
    def model_call() -> str:
        return "Child answer"

    @log(span_type="agent")
    def operation() -> None:
        model_call()
        raise RuntimeError("application failure")

    # When: the operation raises
    with pytest.raises(RuntimeError, match="application failure"):
        operation()

    # Then: a successful answer is not substituted for the failed operation's output
    logger = splunk_ao_context.get_logger_instance()
    parent = next(span for span in logger._sink.spans if span.name.endswith("operation"))
    output = json.loads(parent.attributes["gen_ai.output.messages"])
    assert output[0]["parts"] == [{"type": "text", "content": ""}]


def test_decorator_does_not_conclude_caller_owned_trace(initialized_context: None) -> None:
    logger = splunk_ao_context.get_logger_instance()
    caller_trace = logger.start_trace(input="request", name="caller")

    @log(span_type="workflow")
    def nested_operation() -> str:
        return "done"

    assert nested_operation() == "done"
    assert logger.current_parent() is caller_trace

    logger.conclude(output="done")
    assert logger.current_parent() is None


@pytest.mark.parametrize("span_type", ["workflow", "tool"])
def test_user_exception_is_preserved_and_owned_trace_is_concluded(
    initialized_context: None, span_type: SPAN_TYPE
) -> None:
    @log(span_type=span_type)
    def failing_operation() -> None:
        raise RuntimeError("application failure")

    with pytest.raises(RuntimeError, match="application failure"):
        failing_operation()

    logger = splunk_ao_context.get_logger_instance()
    assert logger.current_parent() is None
    assert splunk_ao_context.get_current_trace() is None


@pytest.mark.parametrize("span_type", ["workflow", "agent", "tool", None])
def test_sync_generator_concludes_on_close_and_preserves_errors(
    initialized_context: None, span_type: SPAN_TYPE | None
) -> None:
    @log(span_type="tool", name="child")
    def child() -> str:
        return "first"

    @log(span_type=span_type, name="stream")
    def stream(fail: bool = False):
        yield child()
        if fail:
            raise ValueError("stream failure")
        yield "second"

    closed_stream = stream()
    assert splunk_ao_context.get_current_trace() is None
    assert next(closed_stream) == "first"
    assert splunk_ao_context.get_current_trace() is None
    closed_stream.close()
    assert splunk_ao_context.get_current_trace() is None

    failing_stream = stream(fail=True)
    assert next(failing_stream) == "first"
    with pytest.raises(ValueError, match="stream failure"):
        next(failing_stream)
    assert splunk_ao_context.get_current_trace() is None
    spans = splunk_ao_context.get_logger_instance()._sink.spans
    parents = [span.context for span in spans if span.name.endswith(" stream")]
    children = [span for span in spans if span.name == "execute_tool child"]
    assert len(spans) == 4
    assert len(children) == 2
    assert all(child.parent in parents for child in children)


@pytest.mark.asyncio
@pytest.mark.parametrize("span_type", ["workflow", "agent", "tool", None])
async def test_async_operations_have_invocation_local_ownership(
    initialized_context: None, span_type: SPAN_TYPE | None
) -> None:
    entered = 0
    both_entered = asyncio.Event()

    @log(span_type=span_type)
    async def operation(value: str) -> str:
        nonlocal entered
        entered += 1
        if entered == 2:
            both_entered.set()
        await both_entered.wait()
        return value

    assert await asyncio.gather(operation("first"), operation("second")) == ["first", "second"]

    logger = splunk_ao_context.get_logger_instance()
    spans = logger._sink.spans
    assert len(spans) == 2
    assert spans[0].context.trace_id != spans[1].context.trace_id
    assert logger.current_parent() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("span_type", ["workflow", "agent", "tool", None])
async def test_async_generator_concludes_on_close(initialized_context: None, span_type: SPAN_TYPE | None) -> None:
    @log(span_type="tool", name="child")
    async def child() -> str:
        return "first"

    @log(span_type=span_type, name="stream")
    async def stream():
        yield await child()
        yield "second"

    result = stream()
    assert await anext(result) == "first"
    assert splunk_ao_context.get_current_trace() is None
    await result.aclose()

    logger = splunk_ao_context.get_logger_instance()
    assert logger.current_parent() is None
    assert splunk_ao_context.get_current_trace() is None
    spans = logger._sink.spans
    assert len(spans) == 2
    parent = next(span for span in spans if span.name.endswith(" stream"))
    child_span = next(span for span in spans if span.name == "execute_tool child")
    assert child_span.parent == parent.context


@pytest.mark.asyncio
async def test_cancelled_tool_restores_caller_context(initialized_context: None) -> None:
    logger = splunk_ao_context.get_logger_instance()
    caller = logger.start_trace(input="request")
    caller_context = otel_trace.get_current_span().get_span_context()

    @log(span_type="tool")
    async def cancelled() -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await cancelled()

    assert logger.current_parent() is caller
    assert otel_trace.get_current_span().get_span_context() == caller_context
    assert len(logger._sink.spans) == 1
    assert logger._sink.spans[0].status.status_code == otel_trace.StatusCode.ERROR
    logger.conclude(output="done")


def test_manual_tool_keeps_caller_active(initialized_context: None) -> None:
    # Decorating tools must not change the leaf semantics of the public logger method.
    logger = splunk_ao_context.get_logger_instance()
    logger.start_trace(input="request")
    caller = logger.add_agent_span(input="request", name="caller")
    caller_context = otel_trace.get_current_span().get_span_context()
    logger.add_tool_span(input="input", output="output", name="manual")

    assert logger.current_parent() is caller
    assert otel_trace.get_current_span().get_span_context() == caller_context
    logger.conclude(output="done", conclude_all=True)


@pytest.mark.parametrize("factory", [False, True])
@pytest.mark.parametrize(
    "span_type, operation",
    [("tool", "execute_tool"), ("workflow", "invoke_workflow"), ("agent", "invoke_agent"), (None, "invoke_workflow")],
)
def test_generator_restores_consumer_between_yields(
    initialized_context: None, factory: bool, span_type: SPAN_TYPE | None, operation: str
) -> None:
    # Given: an operation yields nested work, then its consumer makes a sibling call.
    logger = splunk_ao_context.get_logger_instance()
    contexts = []

    @log(span_type="tool", name="nested")
    def nested() -> str:
        return "chunk"

    def generate():
        contexts.append(otel_trace.get_current_span().get_span_context())
        yield nested()
        contexts.append(otel_trace.get_current_span().get_span_context())
        yield nested()

    def create_stream():
        return generate()

    stream = log(span_type=span_type, name="stream")(create_stream if factory else generate)

    @log(span_type="tool", name="sibling")
    def sibling() -> str:
        return "sibling"

    @log(span_type="agent", name="caller")
    def caller() -> str:
        parent = logger.current_parent()
        caller_context = otel_trace.get_current_span().get_span_context()
        iterator = stream()
        assert logger.current_parent() is parent
        for chunk in iterator:
            assert chunk == "chunk"
            assert logger.current_parent() is parent
            assert otel_trace.get_current_span().get_span_context() == caller_context
            sibling()
        return "done"

    assert caller() == "done"
    spans = logger._sink.spans
    agent = next(span for span in spans if span.name == "invoke_agent caller")
    tool = next(span for span in spans if span.name == f"{operation} stream")
    assert len(spans) == 6
    assert tool.parent == agent.context
    assert contexts == [tool.context, tool.context]
    assert all(span.parent == tool.context for span in spans if span.name == "execute_tool nested")
    assert all(span.parent == agent.context for span in spans if span.name == "execute_tool sibling")
    assert logger.current_parent() is None
    assert not otel_trace.get_current_span().get_span_context().is_valid


@pytest.mark.parametrize("factory", [False, True])
@pytest.mark.parametrize(
    "span_type, operation",
    [("tool", "execute_tool"), ("workflow", "invoke_workflow"), ("agent", "invoke_agent"), (None, "invoke_workflow")],
)
def test_interleaved_generators_keep_their_own_output(
    initialized_context: None, factory: bool, span_type: SPAN_TYPE | None, operation: str
) -> None:
    # Given: two generators that finish in a different order from their last activation.
    def generate(prefix):
        yield prefix + "1"
        yield prefix + "2"

    if factory:
        first = log(span_type=span_type, name="first")(lambda: generate("A"))
        second = log(span_type=span_type, name="second")(lambda: generate("B"))
    else:

        @log(span_type=span_type, name="first")
        def first():
            yield from generate("A")

        @log(span_type=span_type, name="second")
        def second():
            yield from generate("B")

    @log(span_type="agent", name="caller")
    def caller() -> None:
        a, b = first(), second()
        try:
            assert list(zip(a, b, strict=False)) == [("A1", "B1"), ("A2", "B2")]
        finally:
            a.close()
            b.close()

    assert caller() is None
    spans = {span.name: span for span in splunk_ao_context.get_logger_instance()._sink.spans}
    assert len(spans) == 3
    agent = spans["invoke_agent caller"]
    assert json.loads(agent.attributes["gen_ai.output.messages"])[0]["parts"] == [{"type": "text", "content": "B1B2"}]
    for name, output in (("first", "A1A2"), ("second", "B1B2")):
        span = spans[f"{operation} {name}"]
        assert span.parent == agent.context
        if span_type == "tool":
            assert json.loads(span.attributes["gen_ai.tool.call.result"]) == {"value": output}
        else:
            assert json.loads(span.attributes["gen_ai.output.messages"])[0]["parts"] == [
                {"type": "text", "content": output}
            ]


@pytest.mark.asyncio
@pytest.mark.parametrize("factory", ["generator", "sync", "async"])
@pytest.mark.parametrize(
    "span_type, operation",
    [("tool", "execute_tool"), ("workflow", "invoke_workflow"), ("agent", "invoke_agent"), (None, "invoke_workflow")],
)
async def test_async_generator_restores_consumer_between_yields(
    initialized_context: None, factory: str, span_type: SPAN_TYPE | None, operation: str
) -> None:
    logger = splunk_ao_context.get_logger_instance()
    contexts = []

    @log(span_type="tool", name="nested")
    async def nested() -> str:
        await asyncio.sleep(0)
        return "chunk"

    async def generate():
        contexts.append(otel_trace.get_current_span().get_span_context())
        yield await nested()
        contexts.append(otel_trace.get_current_span().get_span_context())
        yield await nested()

    if factory == "sync":

        @log(span_type=span_type, name="stream")
        def stream():
            return generate()
    elif factory == "async":

        @log(span_type=span_type, name="stream")
        async def stream():
            return generate()
    else:
        stream = log(span_type=span_type, name="stream")(generate)

    @log(span_type="tool", name="sibling")
    async def sibling() -> str:
        return "sibling"

    @log(span_type="agent", name="caller")
    async def caller() -> str:
        parent = logger.current_parent()
        caller_context = otel_trace.get_current_span().get_span_context()
        iterator = await stream() if factory == "async" else stream()
        assert logger.current_parent() is parent
        async for chunk in iterator:
            assert chunk == "chunk"
            assert logger.current_parent() is parent
            assert otel_trace.get_current_span().get_span_context() == caller_context
            await sibling()
        return "done"

    assert await caller() == "done"
    spans = logger._sink.spans
    agent = next(span for span in spans if span.name == "invoke_agent caller")
    tool = next(span for span in spans if span.name == f"{operation} stream")
    assert len(spans) == 6
    assert tool.parent == agent.context
    assert contexts == [tool.context, tool.context]
    assert all(span.parent == tool.context for span in spans if span.name == "execute_tool nested")
    assert all(span.parent == agent.context for span in spans if span.name == "execute_tool sibling")
    assert logger.current_parent() is None
    assert not otel_trace.get_current_span().get_span_context().is_valid


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "span_type, operation",
    [("tool", "execute_tool"), ("workflow", "invoke_workflow"), ("agent", "invoke_agent"), (None, "invoke_workflow")],
)
async def test_interleaved_async_generators_keep_their_own_output(
    initialized_context: None, span_type: SPAN_TYPE | None, operation: str
) -> None:
    @log(span_type=span_type, name="stream")
    async def stream(prefix):
        yield prefix + "1"
        await asyncio.sleep(0)
        yield prefix + "2"

    @log(span_type="agent", name="caller")
    async def caller() -> None:
        first, second = stream("A"), stream("B")
        try:
            assert await anext(first) == "A1"
            assert await anext(second) == "B1"
            assert await anext(first) == "A2"
            assert await anext(second) == "B2"
            with pytest.raises(StopAsyncIteration):
                await anext(first)
            with pytest.raises(StopAsyncIteration):
                await anext(second)
        finally:
            await first.aclose()
            await second.aclose()

    assert await caller() is None
    spans = splunk_ao_context.get_logger_instance()._sink.spans
    agent = next(span for span in spans if span.name == "invoke_agent caller")
    assert json.loads(agent.attributes["gen_ai.output.messages"])[0]["parts"] == [{"type": "text", "content": "B1B2"}]
    tools = [span for span in spans if span.name == f"{operation} stream"]
    assert len(spans) == 3
    assert all(span.parent == agent.context for span in tools)
    for span, output in zip(tools, ["A1A2", "B1B2"], strict=True):
        if span_type == "tool":
            assert json.loads(span.attributes["gen_ai.tool.call.result"]) == {"value": output}
        else:
            assert json.loads(span.attributes["gen_ai.output.messages"])[0]["parts"] == [
                {"type": "text", "content": output}
            ]


@pytest.mark.parametrize(
    "span_type, operation",
    [("tool", "execute_tool"), ("workflow", "invoke_workflow"), ("agent", "invoke_agent"), (None, "invoke_workflow")],
)
def test_partially_consumed_generator_restores_native_caller(
    initialized_context: None, span_type: SPAN_TYPE | None, operation: str
) -> None:
    # Given: the consumer retains a real native recording span while a tool is suspended.
    logger = splunk_ao_context.get_logger_instance()
    provider = TracerProvider()
    observed = []

    @log(span_type="tool", name="cleanup")
    def cleanup() -> str:
        return "closed"

    @log(span_type=span_type, name="stream")
    def stream():
        try:
            with provider.get_tracer(__name__).start_as_current_span("generator native span") as inner:
                yield "first"
                observed.append(otel_trace.get_current_span() is inner)
                yield "second"
                yield "third"
        finally:
            cleanup()

    try:
        with provider.get_tracer(__name__).start_as_current_span("native caller") as native:
            iterator = stream()
            assert next(iterator) == "first"
            assert logger.current_parent() is None
            assert splunk_ao_context.get_current_trace() is None
            assert otel_trace.get_current_span() is native
            otel_trace.get_current_span().set_attribute("after_yield", True)
            assert next(iterator) == "second"
            assert observed == [True]
            assert otel_trace.get_current_span() is native
            iterator.close()
            assert otel_trace.get_current_span() is native
            assert native.attributes["after_yield"] is True
        spans = {span.name: span for span in logger._sink.spans}
        assert len(spans) == 2
        assert spans["execute_tool cleanup"].parent == spans[f"{operation} stream"].context
        assert spans[f"{operation} stream"].parent == native.get_span_context()
        assert logger.current_parent() is None
        assert not logger._otel_ids
        assert not logger._pending_otel_steps
    finally:
        provider.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", ["close", "error", "cancel"])
@pytest.mark.parametrize(
    "span_type, operation",
    [("tool", "execute_tool"), ("workflow", "invoke_workflow"), ("agent", "invoke_agent"), (None, "invoke_workflow")],
)
async def test_suspended_async_generator_cleanup_restores_caller(
    initialized_context: None, finish: str, span_type: SPAN_TYPE | None, operation: str
) -> None:
    logger = splunk_ao_context.get_logger_instance()
    entered = asyncio.Event()

    @log(span_type="tool", name="cleanup")
    async def cleanup() -> str:
        return "closed"

    @log(span_type=span_type, name="stream")
    async def stream():
        try:
            yield "first"
            if finish == "error":
                raise ValueError("stream failure")
            entered.set()
            await asyncio.Event().wait()
        finally:
            await cleanup()

    @log(span_type="agent", name="caller")
    async def caller() -> str:
        parent = logger.current_parent()
        caller_context = otel_trace.get_current_span().get_span_context()
        iterator = stream()
        assert await anext(iterator) == "first"
        assert logger.current_parent() is parent
        assert otel_trace.get_current_span().get_span_context() == caller_context
        if finish == "close":
            await iterator.aclose()
        elif finish == "error":
            with pytest.raises(ValueError, match="stream failure"):
                await anext(iterator)
        else:
            task = asyncio.create_task(anext(iterator))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert logger.current_parent() is parent
        assert otel_trace.get_current_span().get_span_context() == caller_context
        return "done"

    assert await caller() == "done"
    spans = {span.name: span for span in logger._sink.spans}
    assert len(spans) == 3
    tool = spans[f"{operation} stream"]
    assert tool.parent == spans["invoke_agent caller"].context
    assert spans["execute_tool cleanup"].parent == tool.context
    assert (tool.status.status_code == otel_trace.StatusCode.ERROR) == (finish != "close")
    assert logger.current_parent() is None
    assert not logger._otel_ids
    assert not logger._pending_otel_steps


@pytest.mark.asyncio
@pytest.mark.parametrize("span_type", ["tool", "workflow", "agent", None])
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_interleaved_top_level_generators_own_separate_traces(
    initialized_context: None, span_type: SPAN_TYPE | None, asynchronous: bool
) -> None:
    logger = splunk_ao_context.get_logger_instance()
    if asynchronous:

        @log(span_type=span_type, name="stream")
        async def stream(prefix):
            yield prefix + "1"
            await asyncio.sleep(0)
            yield prefix + "2"
    else:

        @log(span_type=span_type, name="stream")
        def stream(prefix):
            yield prefix + "1"
            yield prefix + "2"

    first, second = stream("A"), stream("B")
    for expected, iterator in [("A1", first), ("B1", second), ("A2", first), ("B2", second)]:
        assert (await anext(iterator) if asynchronous else next(iterator)) == expected
        assert logger.current_parent() is None
        assert splunk_ao_context.get_current_trace() is None
        assert not otel_trace.get_current_span().get_span_context().is_valid
    for iterator in (first, second):
        if asynchronous:
            with pytest.raises(StopAsyncIteration):
                await anext(iterator)
        else:
            with pytest.raises(StopIteration):
                next(iterator)
    spans = logger._sink.spans
    assert len(spans) == 2
    assert all(span.parent is None for span in spans)
    assert len({span.context.trace_id for span in spans}) == 2
    for span, output in zip(spans, ["A1A2", "B1B2"], strict=True):
        if span_type == "tool":
            assert json.loads(span.attributes["gen_ai.tool.call.result"]) == {"value": output}
        else:
            assert json.loads(span.attributes["gen_ai.output.messages"])[0]["parts"] == [
                {"type": "text", "content": output}
            ]
    assert not logger._otel_ids
    assert not logger._pending_otel_steps


def test_flush_and_flush_all_do_not_conclude_active_trace(initialized_context: None) -> None:
    logger = splunk_ao_context.get_logger_instance()
    caller_trace = logger.start_trace(input="request", name="caller")

    splunk_ao_context.flush()
    assert logger.current_parent() is caller_trace

    splunk_ao_context.flush_all()
    assert logger.current_parent() is caller_trace

    logger.conclude(output="done")
