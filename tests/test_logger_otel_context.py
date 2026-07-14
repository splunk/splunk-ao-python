import asyncio
import atexit
from collections.abc import Callable, Generator

import pytest
from opentelemetry import context, propagate, trace
from opentelemetry.trace import SpanContext, TraceFlags

from splunk_ao.logger import SplunkAOLogger
from splunk_ao.logger.logger import _otel_context_state


@pytest.fixture(autouse=True)
def isolated_otel_context() -> Generator[None, None, None]:
    state_token = _otel_context_state.set(None)
    token = context.attach(context.Context())
    try:
        yield
    finally:
        context.detach(token)
        _otel_context_state.reset(state_token)


@pytest.fixture
def make_logger() -> Generator[Callable[[], SplunkAOLogger], None, None]:
    loggers: list[SplunkAOLogger] = []

    def factory() -> SplunkAOLogger:
        logger = SplunkAOLogger(ingestion_hook=lambda _: None)
        loggers.append(logger)
        return logger

    yield factory

    for logger in loggers:
        atexit.unregister(logger.terminate)
        if logger.current_parent() is not None:
            logger.conclude(output="cleanup", conclude_all=True)


def test_start_trace_assigns_and_activates_fresh_context(make_logger: Callable[[], SplunkAOLogger]) -> None:
    logger = make_logger()
    root = logger.start_trace(input="q")

    root_ids = logger._otel_ids[root.id]
    active = trace.get_current_span().get_span_context()

    assert root_ids.span_context.is_valid
    assert root_ids.parent_span_context is None
    assert active == root_ids.span_context
    assert not hasattr(logger, "_otel_trace_id")

    logger.conclude(output="a")
    assert not trace.get_current_span().get_span_context().is_valid
    assert logger._otel_ids == {}


def test_every_path1_step_gets_stable_ids_and_actual_parent(make_logger: Callable[[], SplunkAOLogger]) -> None:
    logger = make_logger()
    root = logger.start_trace(input="q")
    workflow = logger.add_workflow_span(input="workflow")
    agent = logger.add_agent_span(input="agent")
    agent_context = logger._otel_ids[agent.id].span_context

    llm = logger.add_llm_span(input="prompt", output="answer", model="model")
    retriever = logger.add_retriever_span(input="query", output=["document"])
    tool = logger.add_tool_span(input="arguments", output="result", name="tool")
    control = logger.add_control_span(input="control")

    steps = [root, workflow, agent, llm, retriever, tool, control]
    assert all(step.id in logger._otel_ids for step in steps)
    assert logger._otel_ids[workflow.id].parent_span_context == logger._otel_ids[root.id].span_context
    assert logger._otel_ids[agent.id].parent_span_context == logger._otel_ids[workflow.id].span_context

    for leaf in (llm, retriever, tool, control):
        assert leaf is not None
        leaf_ids = logger._otel_ids[leaf.id]
        assert leaf_ids.parent_span_context == agent_context
        assert leaf_ids.span_context.trace_id == agent_context.trace_id

    assert trace.get_current_span().get_span_context() == agent_context

    logger.conclude(output="agent-output")
    assert trace.get_current_span().get_span_context() == logger._otel_ids[workflow.id].span_context
    assert all(step.id not in logger._otel_ids for step in (agent, llm, retriever, tool, control))
    logger.conclude(output="workflow-output")
    logger.conclude(output="trace-output")
    assert logger._otel_ids == {}


def test_completed_leaf_siblings_share_parent_and_do_not_become_active(
    make_logger: Callable[[], SplunkAOLogger],
) -> None:
    logger = make_logger()
    root = logger.start_trace(input="q")
    root_context = logger._otel_ids[root.id].span_context

    first = logger.add_llm_span(input="first", output="one", model="model")
    second = logger.add_tool_span(input="second", output="two", name="tool")

    assert logger._otel_ids[first.id].parent_span_context == root_context
    assert logger._otel_ids[second.id].parent_span_context == root_context
    assert trace.get_current_span().get_span_context() == root_context

    logger.conclude(output="done")


@pytest.mark.parametrize("parent_kind", ["tool", "retriever"])
def test_promoted_parent_becomes_active_and_parents_children(
    make_logger: Callable[[], SplunkAOLogger], parent_kind: str
) -> None:
    logger = make_logger()
    root = logger.start_trace(input="q")

    if parent_kind == "tool":
        parent = logger.add_tool_span(input="arguments", output="result", name="tool")
    else:
        parent = logger.add_retriever_span(input="query", output=["document"])

    parent._parent = root
    logger._set_current_parent(parent)
    assert trace.get_current_span().get_span_context() == logger._otel_ids[parent.id].span_context

    child = logger.add_llm_span(input="prompt", output="answer", model="model")
    assert logger._otel_ids[child.id].parent_span_context == logger._otel_ids[parent.id].span_context

    logger.conclude(output=parent.output)
    assert trace.get_current_span().get_span_context() == logger._otel_ids[root.id].span_context
    logger.conclude(output="trace-output")


def test_deep_parent_chain_restores_each_open_context(make_logger: Callable[[], SplunkAOLogger]) -> None:
    logger = make_logger()
    root = logger.start_trace(input="q")
    workflow = logger.add_workflow_span(input="workflow")
    agent = logger.add_agent_span(input="agent")
    llm = logger.add_llm_span(input="prompt", output="answer", model="model")

    assert logger._otel_ids[workflow.id].parent_span_context == logger._otel_ids[root.id].span_context
    assert logger._otel_ids[agent.id].parent_span_context == logger._otel_ids[workflow.id].span_context
    assert logger._otel_ids[llm.id].parent_span_context == logger._otel_ids[agent.id].span_context
    assert logger._current_otel_span_id() == logger._otel_ids[agent.id].span_context.span_id

    logger.conclude(output="agent-output")
    assert logger._current_otel_span_id() == logger._otel_ids[workflow.id].span_context.span_id
    logger.conclude(output="workflow-output")
    assert logger._current_otel_span_id() == logger._otel_ids[root.id].span_context.span_id
    logger.conclude(output="trace-output")
    assert not trace.get_current_span().get_span_context().is_valid


def test_single_llm_trace_assigns_both_contexts_and_cleans_up(
    make_logger: Callable[[], SplunkAOLogger], monkeypatch: pytest.MonkeyPatch
) -> None:
    logger = make_logger()
    assigned: list[tuple[SpanContext | None, SpanContext]] = []
    original = SplunkAOLogger._assign_otel_context

    def recording_assign(
        self: SplunkAOLogger, otel_trace_id: int, parent_span_context: SpanContext | None, trace_state
    ) -> SpanContext:
        span_context = original(self, otel_trace_id, parent_span_context, trace_state)
        assigned.append((parent_span_context, span_context))
        return span_context

    monkeypatch.setattr(SplunkAOLogger, "_assign_otel_context", recording_assign)
    logger.add_single_llm_span_trace(input="q", output="a", model="model")

    assert len(assigned) == 2
    assert assigned[0][0] is None
    assert assigned[1][0] == assigned[0][1]
    assert assigned[1][1].trace_id == assigned[0][1].trace_id
    assert logger._otel_ids == {}
    assert not trace.get_current_span().get_span_context().is_valid


def test_start_trace_inherits_remote_parent_and_preserves_tracestate(make_logger: Callable[[], SplunkAOLogger]) -> None:
    carrier = {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", "tracestate": "vendor=value"}
    remote_context = propagate.extract(carrier)
    remote_span_context = trace.get_current_span(remote_context).get_span_context()
    token = context.attach(remote_context)
    try:
        logger = make_logger()
        root = logger.start_trace(input="q")
        root_ids = logger._otel_ids[root.id]

        assert root_ids.span_context.trace_id == remote_span_context.trace_id
        assert root_ids.parent_span_context == remote_span_context
        assert root_ids.parent_span_context.is_remote
        assert root_ids.span_context.trace_state == remote_span_context.trace_state

        logger.add_llm_span(input="prompt", output="answer", model="model")
        carrier_out: dict[str, str] = {}
        propagate.inject(carrier_out)
        assert carrier_out["tracestate"] == "vendor=value"

        logger.conclude(output="a")
        assert trace.get_current_span().get_span_context() == remote_span_context
    finally:
        context.detach(token)


def test_trace_flags_are_always_sampled_with_unsampled_remote_parent(make_logger: Callable[[], SplunkAOLogger]) -> None:
    remote_context = propagate.extract({"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"})
    token = context.attach(remote_context)
    try:
        logger = make_logger()
        root = logger.start_trace(input="q")
        child = logger.add_llm_span(input="prompt", output="answer", model="model")

        assert logger._otel_ids[root.id].span_context.trace_flags == TraceFlags(TraceFlags.SAMPLED)
        assert logger._otel_ids[child.id].span_context.trace_flags == TraceFlags(TraceFlags.SAMPLED)
        logger.conclude(output="a")
    finally:
        context.detach(token)


@pytest.mark.asyncio
async def test_concurrent_traces_on_same_logger_are_isolated(make_logger: Callable[[], SplunkAOLogger]) -> None:
    logger = make_logger()
    results: dict[str, dict[str, int]] = {}

    async def run_trace(label: str) -> None:
        root = logger.start_trace(input=label)
        root_context = logger._otel_ids[root.id].span_context
        await asyncio.sleep(0)
        workflow = logger.add_workflow_span(input=f"{label}-workflow")
        await asyncio.sleep(0)
        child = logger.add_llm_span(input=label, output="done", model="model")
        results[label] = {
            "trace_id": root_context.trace_id,
            "root_span_id": root_context.span_id,
            "workflow_span_id": logger._otel_ids[workflow.id].span_context.span_id,
            "child_parent_id": logger._otel_ids[child.id].parent_span_context.span_id,
        }
        logger.conclude(output="workflow-done")
        assert logger._current_otel_span_id() == root_context.span_id
        await asyncio.sleep(0)
        logger.conclude(output="trace-done")

    await asyncio.gather(run_trace("request-a"), run_trace("request-b"))

    assert results["request-a"]["trace_id"] != results["request-b"]["trace_id"]
    assert results["request-a"]["child_parent_id"] == results["request-a"]["workflow_span_id"]
    assert results["request-b"]["child_parent_id"] == results["request-b"]["workflow_span_id"]
    assert not trace.get_current_span().get_span_context().is_valid
    assert logger._otel_ids == {}


@pytest.mark.asyncio
async def test_copied_async_context_can_add_and_conclude_child(make_logger: Callable[[], SplunkAOLogger]) -> None:
    logger = make_logger()
    root = logger.start_trace(input="q")
    root_context = logger._otel_ids[root.id].span_context

    async def run_child() -> None:
        workflow = logger.add_workflow_span(input="workflow")
        assert trace.get_current_span().get_span_context() == logger._otel_ids[workflow.id].span_context
        logger.conclude(output="workflow-output")
        assert trace.get_current_span().get_span_context() == root_context

    await asyncio.create_task(run_child())

    assert trace.get_current_span().get_span_context() == root_context
    logger.conclude(output="trace-output")
    assert not trace.get_current_span().get_span_context().is_valid


def test_interleaved_logger_reset_preserves_current_logger(make_logger: Callable[[], SplunkAOLogger]) -> None:
    logger_a = make_logger()
    logger_b = make_logger()
    logger_a.start_trace(input="a")
    root_b = logger_b.start_trace(input="b")
    workflow_b = logger_b.add_workflow_span(input="workflow-b")
    workflow_b_context = logger_b._otel_ids[workflow_b.id].span_context

    logger_a.reset_parent_tracking()

    assert trace.get_current_span().get_span_context() == workflow_b_context
    assert logger_a._otel_ids == {}
    logger_b.conclude(output="workflow-output")
    assert trace.get_current_span().get_span_context() == logger_b._otel_ids[root_b.id].span_context
    logger_b.conclude(output="trace-output")
    assert not trace.get_current_span().get_span_context().is_valid


def test_logger_does_not_replace_global_tracer_provider(make_logger: Callable[[], SplunkAOLogger]) -> None:
    provider_before = trace.get_tracer_provider()
    logger = make_logger()
    logger.start_trace(input="q")
    logger.conclude(output="a")
    assert trace.get_tracer_provider() is provider_before
