"""Tests for the SDK-owned DTB batch span sink."""

from collections.abc import Generator, Sequence
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import SpanContext, TraceFlags, TraceState

from splunk_ao.exporter.sink import BatchConfig, SpanSink, build_batch_processor, build_span_sink


class RecordingExporter(SpanExporter):
    def __init__(self) -> None:
        self.exported: list[ReadableSpan] = []
        self.shutdown_calls = 0

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.exported.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.shutdown_calls += 1


def make_readable_span(index: int = 1) -> ReadableSpan:
    context = SpanContext(
        trace_id=index,
        span_id=index,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        trace_state=TraceState(),
    )
    return ReadableSpan(name=f"span-{index}", context=context, resource=Resource({}), start_time=1, end_time=2)


@pytest.fixture
def shutdown_workers() -> Generator[list[Any], None, None]:
    workers: list[Any] = []
    yield workers
    for worker in reversed(workers):
        worker.shutdown()


def test_batch_processor_wraps_exporter(shutdown_workers: list[Any]) -> None:
    processor = build_batch_processor(RecordingExporter())
    shutdown_workers.append(processor)

    assert isinstance(processor, BatchSpanProcessor)


def test_batch_processor_accepts_custom_config(shutdown_workers: list[Any]) -> None:
    exporter = RecordingExporter()
    processor = build_batch_processor(exporter, BatchConfig(max_export_batch_size=1))
    shutdown_workers.append(processor)

    processor.on_end(make_readable_span())
    processor.force_flush()

    assert len(exporter.exported) == 1


def test_span_sink_does_not_replace_global(shutdown_workers: list[Any]) -> None:
    original_global = trace.get_tracer_provider()
    sink = build_span_sink(RecordingExporter(), Resource({}))
    shutdown_workers.append(sink)

    assert trace.get_tracer_provider() is original_global


def test_span_sink_exports_spans_on_force_flush(shutdown_workers: list[Any]) -> None:
    exporter = RecordingExporter()
    sink = build_span_sink(exporter, Resource({}))
    shutdown_workers.append(sink)

    sink.emit(make_readable_span())
    assert sink.force_flush()

    assert len(exporter.exported) == 1


def test_spans_not_exported_before_force_flush(shutdown_workers: list[Any]) -> None:
    exporter = RecordingExporter()
    sink = build_span_sink(exporter, Resource({}), BatchConfig(schedule_delay_millis=60_000))
    shutdown_workers.append(sink)

    for index in range(1, 6):
        sink.emit(make_readable_span(index))

    assert exporter.exported == []
    assert sink.force_flush()
    assert len(exporter.exported) == 5


def test_exporter_retry_is_not_added_by_batch_processor(shutdown_workers: list[Any]) -> None:
    export_attempts: list[int] = []

    class FailThenSucceedExporter(SpanExporter):
        def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
            export_attempts.append(len(spans))
            if len(export_attempts) < 3:
                return SpanExportResult.FAILURE
            return SpanExportResult.SUCCESS

        def shutdown(self) -> None:
            pass

    processor = build_batch_processor(FailThenSucceedExporter())
    shutdown_workers.append(processor)
    processor.on_end(make_readable_span())
    processor.force_flush()

    assert export_attempts == [1]


def test_span_sink_shutdown_is_idempotent() -> None:
    class TrackingProvider:
        def __init__(self) -> None:
            self.shutdown_calls = 0

        def force_flush(self, timeout_millis: int = 30_000) -> bool:
            return True

        def shutdown(self) -> None:
            self.shutdown_calls += 1

    provider = TrackingProvider()
    sink = SpanSink(processor=AnyProcessor(), provider=provider)

    sink.shutdown()
    sink.shutdown()

    assert provider.shutdown_calls == 1


def test_span_sink_rejects_emit_after_shutdown() -> None:
    sink = build_span_sink(RecordingExporter(), Resource({}))
    sink.shutdown()

    with pytest.raises(RuntimeError, match="shut down"):
        sink.emit(make_readable_span())


class AnyProcessor:
    def on_end(self, span: ReadableSpan) -> None:
        pass
