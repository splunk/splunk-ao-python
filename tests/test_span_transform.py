from collections.abc import Sequence

import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import SpanContext, SpanKind, TraceFlags
from opentelemetry.trace.status import Status, StatusCode

from splunk_ao.exporter.span_transform import NormalizingSpanExporter, copy_span_for_export


class RecordingExporter(SpanExporter):
    def __init__(self) -> None:
        self.batches: list[Sequence[ReadableSpan]] = []
        self.flushes: list[int] = []
        self.shutdowns = 0

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.batches.append(spans)
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        self.flushes.append(timeout_millis)
        return True

    def shutdown(self) -> None:
        self.shutdowns += 1


def make_span(attributes: dict[str, object] | None = None) -> ReadableSpan:
    return ReadableSpan(
        name="span",
        context=SpanContext(
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            span_id=0x1234567890ABCDEF,
            is_remote=False,
            trace_flags=TraceFlags.SAMPLED,
        ),
        resource=Resource(
            {"service.name": "checkout", "splunk_ao.project.name": "stale"},
            schema_url="https://opentelemetry.io/schemas/1.38.0",
        ),
        attributes=attributes or {"gen_ai.request.model": "gpt-4o"},
        kind=SpanKind.CLIENT,
        status=Status(StatusCode.OK),
        start_time=1,
        end_time=2,
        instrumentation_scope=InstrumentationScope("instrumentation", "1.0"),
    )


def test_copy_span_for_export_is_immutable_and_applies_routing() -> None:
    source = make_span(
        {
            "gen_ai.request.model": "gpt-4o",
            "gen_ai.input.messages": "input-json",
            "splunk_ao.project.name": "stale-span-routing",
        }
    )
    source_attributes = dict(source.attributes or {})
    source_resource = source.resource

    exported = copy_span_for_export(
        source, Resource({"splunk_ao.project.id": "project-id", "splunk_ao.logstream.id": "log-stream-id"})
    )

    assert exported is not source
    assert dict(source.attributes or {}) == source_attributes
    assert source.resource is source_resource
    assert exported.attributes["gen_ai.request.model"] == "gpt-4o"
    assert exported.attributes["gen_ai.input.messages"] == "input-json"
    assert "splunk_ao.project.name" not in exported.attributes
    assert exported.resource.attributes["splunk_ao.project.id"] == "project-id"
    assert exported.resource.attributes["splunk_ao.logstream.id"] == "log-stream-id"
    assert "splunk_ao.project.name" not in exported.resource.attributes
    assert exported.resource.attributes["service.name"] == "checkout"


def test_source_service_name_precedes_exporter_resource_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SERVICE_NAME", "exporter-default")
    source = make_span()

    exported = copy_span_for_export(source, Resource.create({"splunk_ao.project.name": "project"}))

    assert exported.resource.attributes["service.name"] == "checkout"
    assert exported.resource.attributes["splunk_ao.project.name"] == "project"


def test_copy_span_preserves_unaffected_readable_span_fields() -> None:
    source = make_span()
    exported = copy_span_for_export(source)

    for field in (
        "name",
        "context",
        "parent",
        "events",
        "links",
        "kind",
        "status",
        "start_time",
        "end_time",
        "instrumentation_info",
        "instrumentation_scope",
    ):
        assert getattr(exported, field) == getattr(source, field)
    assert exported.resource.schema_url == source.resource.schema_url


def test_exporter_applies_routing_and_delegates_lifecycle_once() -> None:
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(delegate, Resource({"splunk_ao.project.name": "project"}))

    assert exporter.export((make_span(),)) == SpanExportResult.SUCCESS
    assert exporter.force_flush(1234) is True
    exporter.shutdown()

    assert len(delegate.batches) == 1
    assert delegate.batches[0][0].attributes["gen_ai.request.model"] == "gpt-4o"
    assert delegate.batches[0][0].resource.attributes["splunk_ao.project.name"] == "project"
    assert delegate.flushes == [1234]
    assert delegate.shutdowns == 1


def test_retired_normalization_switch_keeps_genai_and_sdk_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION", "true")
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(delegate)
    attributes = {
        "gen_ai.request.model": "gpt-4o",
        "gen_ai.request.top_p": 0.75,
        "gen_ai.input.messages": "input-json",
        "gen_ai.tool.definitions": "tools-json",
        "splunk_ao.metadata": '{"team":"support"}',
        "splunk_ao.redacted_input": "safe",
        "splunk_ao.llm.usage.total_tokens": 42,
        "splunk_ao.span.name": "Checkout",
    }

    assert exporter.export((make_span(attributes),)) == SpanExportResult.SUCCESS
    assert delegate.batches[0][0].attributes == attributes
