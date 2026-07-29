from collections.abc import Generator
from unittest.mock import Mock
from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import ReadableSpan

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


def test_distributed_continuation_keeps_stub_parent_local() -> None:
    sink = RecordingSink()
    trace_id = str(uuid4())
    parent_id = str(uuid4())
    logger = SplunkAOLogger(
        project_id="project-id",
        log_stream_id="log-stream-id",
        mode="distributed",
        trace_id=trace_id,
        span_id=parent_id,
        _sink=sink,
    )
    try:
        assert str(logger.traces[0].id) == trace_id
        assert str(logger.current_parent().id) == parent_id

        logger.add_llm_span(input="prompt", output="answer", model="model")

        assert operation_names(sink.spans) == ["chat"]
        assert sink.spans[0].parent == logger._otel_ids[logger.current_parent().id].span_context
    finally:
        logger.terminate()


def test_distributed_terminate_discards_unfinished_stubs() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(
        project_id="project-id",
        log_stream_id="log-stream-id",
        mode="distributed",
        trace_id=str(uuid4()),
        span_id=str(uuid4()),
        _sink=sink,
    )

    logger.terminate()
    logger.terminate()

    assert sink.spans == []
    assert sink.force_flush_calls == 1
    assert sink.shutdown_calls == 1
    assert logger.current_parent() is None
    assert logger._otel_ids == {}
