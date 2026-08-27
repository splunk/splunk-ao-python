import asyncio
from collections.abc import Generator
from unittest.mock import patch

import pytest

from splunk_ao import log, splunk_ao_context
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


def test_user_exception_is_preserved_and_owned_trace_is_concluded(initialized_context: None) -> None:
    @log(span_type="workflow")
    def failing_operation() -> None:
        raise RuntimeError("application failure")

    with pytest.raises(RuntimeError, match="application failure"):
        failing_operation()

    logger = splunk_ao_context.get_logger_instance()
    assert logger.current_parent() is None
    assert splunk_ao_context.get_current_trace() is None
    assert (logger._sink.spans[-1].attributes or {})["splunk_ao.status_code"] == 500


@pytest.mark.asyncio
async def test_async_coroutine_exception_is_preserved_and_owned_trace_is_concluded(initialized_context: None) -> None:
    # Given: a decorated async operation that raises an application exception
    @log(span_type="workflow")
    async def failing_operation() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("async application failure")

    # When: the operation is awaited
    with pytest.raises(RuntimeError, match="async application failure"):
        await failing_operation()

    # Then: the original exception is re-raised and both telemetry contexts are released
    logger = splunk_ao_context.get_logger_instance()
    assert logger.current_parent() is None
    assert splunk_ao_context.get_current_trace() is None
    assert (logger._sink.spans[-1].attributes or {})["splunk_ao.status_code"] == 500


def test_sync_generator_concludes_on_close_and_preserves_errors(initialized_context: None) -> None:
    @log(span_type="workflow")
    def stream(fail: bool = False):
        yield "first"
        if fail:
            raise ValueError("stream failure")
        yield "second"

    closed_stream = stream()
    assert splunk_ao_context.get_current_trace() is None
    assert next(closed_stream) == "first"
    assert splunk_ao_context.get_current_trace() is not None
    closed_stream.close()
    assert splunk_ao_context.get_current_trace() is None

    failing_stream = stream(fail=True)
    assert next(failing_stream) == "first"
    with pytest.raises(ValueError, match="stream failure"):
        next(failing_stream)
    assert splunk_ao_context.get_current_trace() is None


@pytest.mark.asyncio
async def test_async_operations_have_invocation_local_ownership(initialized_context: None) -> None:
    entered = 0
    both_entered = asyncio.Event()

    @log(span_type="workflow")
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
async def test_async_generator_concludes_on_close(initialized_context: None) -> None:
    @log(span_type="workflow")
    async def stream():
        yield "first"
        yield "second"

    result = stream()
    assert await anext(result) == "first"
    assert splunk_ao_context.get_current_trace() is not None
    await result.aclose()

    logger = splunk_ao_context.get_logger_instance()
    assert logger.current_parent() is None
    assert splunk_ao_context.get_current_trace() is None


def test_flush_and_flush_all_do_not_conclude_active_trace(initialized_context: None) -> None:
    logger = splunk_ao_context.get_logger_instance()
    caller_trace = logger.start_trace(input="request", name="caller")

    splunk_ao_context.flush()
    assert logger.current_parent() is caller_trace

    splunk_ao_context.flush_all()
    assert logger.current_parent() is caller_trace

    logger.conclude(output="done")
