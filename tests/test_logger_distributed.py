from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from opentelemetry import context
from opentelemetry.sdk.trace import ReadableSpan

from splunk_ao import extract_tracing_context
from splunk_ao.logger import SplunkAOLogger


class RecordingSink:
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []
        self.force_flush_calls = 0
        self.shutdown_calls = 0

    def emit(self, span: ReadableSpan) -> None:
        self.spans.append(span)

    def force_flush(self) -> bool:
        self.force_flush_calls += 1
        return True

    def shutdown(self) -> None:
        self.shutdown_calls += 1


@pytest.fixture
def distributed_logger() -> Generator[tuple[SplunkAOLogger, RecordingSink], None, None]:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", mode="distributed", _sink=sink)
    yield logger, sink
    logger.terminate()


def operation_names(spans: list[ReadableSpan]) -> list[str | None]:
    return [(span.attributes or {}).get("gen_ai.operation.name") for span in spans]


@pytest.mark.parametrize("mode", ["batch", "distributed"])
def test_both_mode_values_construct_the_shared_batch_span_sink(mode: str) -> None:
    sink = RecordingSink()
    exporter = Mock()
    with (
        patch("splunk_ao.logger.logger.build_standalone_exporter", return_value=exporter),
        patch("splunk_ao.logger.logger.build_span_sink", return_value=sink) as build_sink,
    ):
        logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", mode=mode)

    try:
        build_sink.assert_called_once_with(exporter)
        assert not hasattr(logger, "_task_handler")
    finally:
        logger.terminate()


def test_distributed_mode_uses_otlp_completion_queue(distributed_logger: tuple[SplunkAOLogger, RecordingSink]) -> None:
    logger, sink = distributed_logger
    root = logger.start_trace(input="question")
    workflow = logger.add_workflow_span(input="workflow")
    logger.add_llm_span(input="prompt", output="answer", model="model")

    assert operation_names(sink.spans) == ["chat"]

    logger.conclude(output="workflow answer")
    logger.conclude(output="answer")

    llm_span, workflow_span = sink.spans
    assert operation_names(sink.spans) == ["chat", "invoke_workflow"]
    assert llm_span.parent == workflow_span.context
    assert workflow_span.parent is None
    assert workflow.id not in logger._otel_ids
    assert root.id not in logger._otel_ids
    assert logger.traces == []


def test_distributed_mode_does_not_call_proprietary_telemetry_client(
    distributed_logger: tuple[SplunkAOLogger, RecordingSink],
) -> None:
    logger, _ = distributed_logger
    client = logger._traces_client
    assert client is not None
    client.ingest_traces = Mock()
    client.ingest_spans = Mock()
    client.update_trace = Mock()
    client.update_span = Mock()

    logger.start_trace(input="question")
    logger.add_llm_span(input="prompt", output="answer", model="model")
    logger.conclude(output="answer")
    logger.flush()

    client.ingest_traces.assert_not_called()
    client.ingest_spans.assert_not_called()
    client.update_trace.assert_not_called()
    client.update_span.assert_not_called()
    assert not hasattr(logger, "_task_handler")


def test_distributed_flush_only_drains_completed_spans(
    distributed_logger: tuple[SplunkAOLogger, RecordingSink],
) -> None:
    logger, sink = distributed_logger
    root = logger.start_trace(input="unfinished")

    assert logger.flush() is None

    assert sink.force_flush_calls == 1
    assert sink.spans == []
    assert logger.current_parent() is root
    assert root.id in logger._otel_ids


def test_distributed_flush_does_not_duplicate_completed_spans(
    distributed_logger: tuple[SplunkAOLogger, RecordingSink],
) -> None:
    logger, sink = distributed_logger
    logger.start_trace(input="question")
    logger.add_llm_span(input="prompt", output="answer", model="model")
    logger.conclude(output="answer")
    emitted = list(sink.spans)

    logger.flush()
    logger.flush()

    assert sink.spans == emitted
    assert sink.force_flush_calls == 2


def test_distributed_conclude_all_emits_inner_to_outer(
    distributed_logger: tuple[SplunkAOLogger, RecordingSink],
) -> None:
    logger, sink = distributed_logger
    logger.start_trace(input="question")
    logger.add_workflow_span(input="workflow")
    logger.add_agent_span(input="agent")
    logger.add_llm_span(input="prompt", output="answer", model="model")

    logger.conclude(output="answer", conclude_all=True)

    assert operation_names(sink.spans) == ["chat", "invoke_agent", "invoke_workflow"]
    assert len({span.context.trace_id for span in sink.spans if span.context is not None}) == 1


@pytest.mark.parametrize("mode", ["batch", "distributed"])
def test_retained_mode_values_use_identical_w3c_otlp_behavior(mode: str) -> None:
    sink = RecordingSink()
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    parent_id = "00f067aa0ba902b7"
    token = context.attach(extract_tracing_context({"traceparent": f"00-{trace_id}-{parent_id}-01"}))
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", mode=mode, _sink=sink)
    try:
        logger.start_trace(input="request")
        operation = logger.add_workflow_span(input="work", name="operation")
        operation_context = logger._otel_ids[operation.id]
        logger.conclude(output="done")
        logger.conclude(output="complete")

        assert operation_context.span_context.trace_id == int(trace_id, 16)
        assert operation_context.parent_span_context is not None
        assert operation_names(sink.spans) == ["invoke_workflow"]
        assert sink.spans[0].parent is not None
        assert sink.spans[0].parent.span_id == int(parent_id, 16)
        assert sink.force_flush_calls == 0
        assert logger.current_parent() is None
    finally:
        logger.terminate()
        context.detach(token)


@pytest.mark.parametrize("mode", ["batch", "distributed"])
def test_mode_does_not_change_parent_child_topology_or_require_flush(mode: str) -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", mode=mode, _sink=sink)
    try:
        logger.start_trace(input="request")
        logger.add_workflow_span(input="workflow")
        logger.add_agent_span(input="agent")
        logger.add_llm_span(input="prompt", output="answer", model="model")
        logger.conclude(output="complete", conclude_all=True)

        llm, agent, workflow = sink.spans
        assert operation_names(sink.spans) == ["chat", "invoke_agent", "invoke_workflow"]
        assert llm.parent == agent.context
        assert agent.parent == workflow.context
        assert workflow.parent is None
        assert sink.force_flush_calls == 0
        assert logger.current_parent() is None
    finally:
        logger.terminate()


def test_unsampled_remote_parent_is_preserved_and_not_exported() -> None:
    sink = RecordingSink()
    token = context.attach(
        extract_tracing_context({"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"})
    )
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", _sink=sink)
    try:
        logger.start_trace(input="request")
        operation = logger.add_workflow_span(input="work")
        operation_context = logger._otel_ids[operation.id].span_context
        logger.add_llm_span(input="prompt", output="answer", model="model")
        logger.conclude(output="done")
        logger.conclude(output="complete")

        assert operation_context.is_valid
        assert not bool(operation_context.trace_flags)
        assert sink.spans == []
    finally:
        logger.terminate()
        context.detach(token)


def test_custom_trace_and_span_id_constructor_arguments_are_removed() -> None:
    with pytest.raises(TypeError, match="trace_id"):
        SplunkAOLogger(trace_id="4bf92f35-77b3-4da6-a3ce-929d0e0e4736")
    with pytest.raises(TypeError, match="span_id"):
        SplunkAOLogger(span_id="00f067aa-0ba9-42b7-8000-000000000000")


def test_old_logger_header_method_is_removed() -> None:
    assert not hasattr(SplunkAOLogger, "get_tracing_headers")
