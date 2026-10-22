"""Regressions for callback completion in a copied async execution context."""

import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from langchain_core.callbacks.manager import AsyncCallbackManager
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from splunk_ao import get_tracing_headers
from splunk_ao.handlers.base_handler import SplunkAOBaseHandler
from splunk_ao.handlers.langchain import SplunkAOAsyncCallback, SplunkAOCallback
from splunk_ao.handlers.langchain.utils import normalize_langgraph_output
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.schema.handlers import Node


class RecordingSink:
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def emit(self, span: ReadableSpan) -> None:
        self.spans.append(span)

    def force_flush(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("callback_type", [SplunkAOCallback, SplunkAOAsyncCallback])
@pytest.mark.parametrize("flush", [False, True])
@pytest.mark.parametrize("ownership", ["independent", "external", "attached"])
async def test_real_async_dispatch_restores_caller_and_allows_callback_reuse(
    callback_type: Any, flush: bool, ownership: str
) -> None:
    # Given: real LangChain dispatch, including shielded end callbacks in copied contexts.
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    caller_context = SpanContext(1234, 5678, is_remote=True, trace_flags=TraceFlags(TraceFlags.SAMPLED))
    initial = baggage.set_baggage("test-key", "retained", context.Context())
    if ownership == "external":
        initial = trace.set_span_in_context(NonRecordingSpan(caller_context), initial)
    token = context.attach(initial)
    try:
        if ownership == "attached":
            logger.start_trace(input="caller")
            logger.add_workflow_span(input="caller", name="caller")
        caller = logger.current_parent()
        baseline = trace.get_current_span().get_span_context()
        callback = callback_type(
            splunk_ao_logger=logger, start_new_trace=ownership != "attached", flush_on_chain_end=flush
        )
        manager = AsyncCallbackManager(handlers=[callback], inheritable_handlers=[callback])
        roots = []
        for turn in range(3):
            run = await manager.on_chain_start({"name": "LangGraph"}, {"question": str(turn)})
            root_context = trace.get_current_span().get_span_context()
            child = await run.get_child().on_chain_start({"name": "child"}, {"question": str(turn)})

            # When: each end is dispatched by LangChain's real shielded task.
            await child.on_chain_end({"answer": str(turn)})
            assert trace.get_current_span().get_span_context() == root_context
            assert get_tracing_headers()["traceparent"].split("-")[2] == f"{root_context.span_id:016x}"
            await run.on_chain_end({"answer": str(turn)})

            # Then: the original task has its caller context, and exactly two spans completed.
            assert trace.get_current_span().get_span_context() == baseline
            assert logger.current_parent() is caller
            assert baggage.get_baggage("test-key") == "retained"
            assert not callback._handler._nodes
            assert not callback._handler._active_steps
            child_span, root_span = sink.spans[-2:]
            assert child_span.parent == root_span.context
            roots.append(root_span)
        assert len(sink.spans) == 6
        assert len({span.context.span_id for span in sink.spans}) == 6
        if ownership == "independent":
            assert len({span.context.trace_id for span in roots}) == 3
            assert all(span.parent is None for span in roots)
        else:
            assert all(span.parent == baseline for span in roots)
    finally:
        logger.terminate()
        context.detach(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
async def test_manual_completion_in_another_task_restores_context(failed: bool) -> None:
    # Given: a manual operation whose conclusion may execute in a copied task.
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=RecordingSink())
    baseline = trace.get_current_span().get_span_context()
    try:
        logger.start_trace(input="request")
        logger.add_agent_span(input="request", name="agent")

        # When: completion occurs in a child task, as framework callbacks may do.
        async def finish() -> None:
            logger.conclude(
                output="failure" if failed else "done", status_code=500 if failed else 200, conclude_all=True
            )

        await asyncio.create_task(finish())

        # Then: completed operations cannot stay current or parent the next request.
        assert trace.get_current_span().get_span_context() == baseline
        assert logger.current_parent() is None
        logger.start_trace(input="next request")
        assert logger.current_parent() is not None
    finally:
        logger.terminate()


@pytest.mark.asyncio
async def test_reconciling_completed_parent_preserves_new_caller_span() -> None:
    # Given: an SDK operation completed in another task before the application starts new work.
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=RecordingSink())
    logger.start_trace(input="request")
    logger.add_agent_span(input="request")

    async def finish() -> None:
        logger.conclude(output="done", conclude_all=True)

    await asyncio.create_task(finish())
    caller = SpanContext(4321, 8765, is_remote=False, trace_flags=TraceFlags(TraceFlags.SAMPLED))
    token = context.attach(trace.set_span_in_context(NonRecordingSpan(caller)))
    try:
        # When: a logger read reconciles an obsolete parent beneath a new external span.
        assert logger.current_parent() is None

        # Then: it leaves that application-owned span active and inherits it on the next invocation.
        assert trace.get_current_span().get_span_context() == caller
        operation = logger.start_trace(input="next")
        assert logger._otel_ids[operation.id].parent_span_context == caller
    finally:
        logger.terminate()
        context.detach(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("callback_type", [SplunkAOCallback, SplunkAOAsyncCallback])
@pytest.mark.parametrize("attached", [False, True])
async def test_checkpointed_root_exports_current_reply_without_changing_history(
    callback_type: Any, attached: bool
) -> None:
    # Given: a new turn's input differs from the beginning of checkpointed output history.
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    callback = callback_type(splunk_ao_logger=logger, start_new_trace=not attached, flush_on_chain_end=False)
    manager = AsyncCallbackManager(handlers=[callback], metadata={"ls_integration": "langgraph"})
    reply = AIMessage(content=[{"type": "text", "text": "current reply"}])
    history = [
        HumanMessage(content="old question"),
        AIMessage(content="old reply"),
        HumanMessage(content="new question"),
        reply,
    ]
    output = {"messages": history, "other_state": "preserved"}
    try:
        if attached:
            logger.start_trace(input="caller")
            logger.add_workflow_span(input="caller")
        caller = logger.current_parent()
        run = await manager.on_chain_start({"name": "LangGraph"}, {"messages": [history[-2]]})

        # When: a graph root completes with the full persisted state.
        await run.on_chain_end(output)

        # Then: its exported output is the current response, without changing graph memory.
        root = sink.spans[-1]
        messages = json.loads(root.attributes["gen_ai.output.messages"])
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["parts"] == [{"type": "text", "content": "current reply"}]
        assert output["messages"] is history
        assert len(history) == 4
        assert output["other_state"] == "preserved"
        assert logger.current_parent() is caller
    finally:
        logger.terminate()


@pytest.mark.parametrize("graph", [False, True])
def test_non_root_tool_messages_are_not_reduced(graph: bool) -> None:
    # Given: a tool node can return several results, even inside LangGraph.
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    callback = SplunkAOCallback(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id, node_id = uuid4(), uuid4()
    results = [ToolMessage(content="one", tool_call_id="1"), ToolMessage(content="two", tool_call_id="2")]
    try:
        callback.on_chain_start({"name": "LangGraph" if graph else "plain chain"}, {}, run_id=root_id)
        callback.on_chain_start({"name": "tools"}, {}, run_id=node_id, parent_run_id=root_id)

        # When: a nested node returns multiple tool responses.
        callback.on_chain_end({"messages": results}, run_id=node_id, parent_run_id=root_id)

        # Then: both tool responses remain in its telemetry output.
        messages = json.loads(sink.spans[0].attributes["gen_ai.output.messages"])
        assert len(messages) == 2
        assert [message["role"] for message in messages] == ["tool", "tool"]
        callback.on_chain_end({"answer": "done"}, run_id=root_id)
    finally:
        logger.terminate()


@pytest.mark.asyncio
@pytest.mark.parametrize("termination", ["error", "cancellation", "unfinished_child"])
async def test_shielded_failure_restores_context_and_discards_unfinished_children(termination: str) -> None:
    # Given: a root operation with an unfinished child in the originating task.
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    callback = SplunkAOAsyncCallback(splunk_ao_logger=logger, flush_on_chain_end=False)
    manager = AsyncCallbackManager(handlers=[callback], inheritable_handlers=[callback])
    baseline = trace.get_current_span().get_span_context()
    try:
        run = await manager.on_chain_start({"name": "LangGraph"}, {"question": "request"})
        await run.get_child().on_chain_start({"name": "unfinished child"}, {})

        # When: the framework finishes or reports failure from its shielded task.
        if termination == "unfinished_child":
            await run.on_chain_end({"answer": "done"})
        else:
            error = asyncio.CancelledError() if termination == "cancellation" else ValueError("failure")
            await run.on_chain_error(error)

        # Then: the uncompleted child is discarded, and the root emits exactly once.
        assert trace.get_current_span().get_span_context() == baseline
        assert logger.current_parent() is None
        assert len(sink.spans) == 1
        assert not logger._otel_ids
        assert not callback._handler._active_steps
        next_run = await manager.on_chain_start({"name": "LangGraph"}, {})
        await next_run.on_chain_end({"answer": "next"})
        assert len(sink.spans) == 2
        assert sink.spans[0].context.trace_id != sink.spans[1].context.trace_id
    finally:
        logger.terminate()


@pytest.mark.asyncio
@pytest.mark.parametrize("sampled", [False, True])
async def test_shared_base_handler_completion_preserves_external_parent_and_sampling(sampled: bool) -> None:
    # Given: a non-LangChain adapter using the shared base handler under a remote parent.
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    caller = SpanContext(1234, 5678, is_remote=True, trace_flags=TraceFlags(1 if sampled else 0))
    token = context.attach(trace.set_span_in_context(NonRecordingSpan(caller)))
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    try:
        for _ in range(2):
            root_id, child_id = uuid4(), uuid4()
            handler.start_node("agent", None, root_id, input="request", name="agent")
            handler.start_node("tool", root_id, child_id, input="arguments", name="tool")

            async def finish(child: UUID = child_id, root: UUID = root_id) -> None:
                handler.end_node(child, output="tool result")
                handler.end_node(root, output="answer")

            # When: a framework ends its callbacks in another task.
            await asyncio.create_task(finish())

            # Then: caller ownership and remote sampling decisions are preserved.
            assert trace.get_current_span().get_span_context() == caller
            assert logger.current_parent() is None
        assert len(sink.spans) == (4 if sampled else 0)
        if sampled:
            assert all(span.context.trace_id == caller.trace_id for span in sink.spans)
            assert all(span.parent == caller for span in sink.spans if span.name == "invoke_agent agent")
    finally:
        logger.terminate()
        context.detach(token)


@pytest.mark.parametrize(
    "terminal",
    [
        AIMessage(content=""),
        AIMessage(content="", tool_calls=[{"name": "search", "args": {}, "id": "call"}]),
        ToolMessage(content="direct result", tool_call_id="call"),
    ],
)
def test_graph_root_normalization_preserves_terminal_message_content(terminal: Any) -> None:
    node = Node(node_type="agent", run_id=uuid4(), span_params={"_langgraph_root": True})
    outputs = {"messages": [HumanMessage(content="old"), AIMessage(content="old reply"), terminal]}

    normalized = normalize_langgraph_output(outputs, node)

    assert normalized["messages"] == [terminal]
    assert normalized["messages"][0] is terminal
    assert len(outputs["messages"]) == 3


@pytest.mark.parametrize("outputs", [{"messages": []}, {"result": "arbitrary state"}, "", None])
def test_graph_root_normalization_preserves_empty_and_generic_outputs(outputs: Any) -> None:
    node = Node(node_type="agent", run_id=uuid4(), span_params={"_langgraph_root": True})
    assert normalize_langgraph_output(outputs, node) is outputs


@pytest.mark.asyncio
@pytest.mark.parametrize("callback_type", [SplunkAOCallback, SplunkAOAsyncCallback])
@pytest.mark.parametrize("checkpointed", [False, True])
@pytest.mark.parametrize("flush", [False, True])
async def test_real_graph_repeated_turns_preserve_memory_and_emit_each_reply(
    callback_type: Any, checkpointed: bool, flush: bool
) -> None:
    # Given: the same real graph can run with or without persisted conversation history.
    graph_module = pytest.importorskip("langgraph.graph")
    memory_module = pytest.importorskip("langgraph.checkpoint.memory")
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    callback = callback_type(splunk_ao_logger=logger, start_new_trace=True, flush_on_chain_end=flush)
    baseline = trace.get_current_span().get_span_context()

    async def assistant(state: dict) -> dict:
        count = sum(isinstance(message, HumanMessage) for message in state["messages"])
        return {"messages": [AIMessage(content=f"reply {count}")]}

    builder = graph_module.StateGraph(graph_module.MessagesState)
    builder.add_node("assistant", assistant)
    builder.add_edge(graph_module.START, "assistant")
    builder.add_edge("assistant", graph_module.END)
    graph = builder.compile(checkpointer=memory_module.InMemorySaver() if checkpointed else None)
    config = {"configurable": {"thread_id": "conversation"}, "callbacks": [callback]}
    try:
        for turn in range(1, 6):
            before = len(sink.spans)

            # When: one callback processes five independently invoked turns in the same thread.
            result = await graph.ainvoke({"messages": [HumanMessage(content=f"question {turn}")]}, config=config)

            # Then: state persists only with checkpoints, but every invocation gets its own trace.
            count = turn if checkpointed else 1
            assert len(result["messages"]) == count * 2
            assert result["messages"][-1].content == f"reply {count}"
            roots = [span for span in sink.spans[before:] if span.parent is None]
            assert len(roots) == 1
            output = json.loads(roots[0].attributes["gen_ai.output.messages"])
            assert len(output) == 1
            assert output[0]["parts"] == [{"type": "text", "content": f"reply {count}"}]
            assert trace.get_current_span().get_span_context() == baseline
            assert logger.current_parent() is None
        roots = [span for span in sink.spans if span.parent is None]
        assert len({root.context.trace_id for root in roots}) == 5
    finally:
        logger.terminate()
