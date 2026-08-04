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


def test_copy_span_for_export_is_immutable_and_combines_normalization_with_routing() -> None:
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
        source,
        Resource({"splunk_ao.project.id": "project-id", "splunk_ao.logstream.id": "log-stream-id"}),
        normalize_attributes=True,
    )

    assert exported is not source
    assert dict(source.attributes or {}) == source_attributes
    assert source.resource is source_resource
    assert exported.attributes["splunk_ao.request.model"] == "gpt-4o"
    assert exported.attributes["splunk_ao.input.messages"] == "input-json"
    assert "gen_ai.input.messages" not in exported.attributes
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


def test_exporter_normalizes_once_and_delegates_lifecycle_once() -> None:
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(
        delegate, Resource({"splunk_ao.project.name": "project"}), normalize_attributes=True
    )

    assert exporter.export((make_span(),)) == SpanExportResult.SUCCESS
    assert exporter.force_flush(1234) is True
    exporter.shutdown()

    assert len(delegate.batches) == 1
    assert delegate.batches[0][0].attributes["splunk_ao.request.model"] == "gpt-4o"
    assert delegate.batches[0][0].resource.attributes["splunk_ao.project.name"] == "project"
    assert delegate.flushes == [1234]
    assert delegate.shutdowns == 1


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
def test_private_environment_switch_disables_only_attribute_normalization(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION", value)
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(delegate, Resource({"splunk_ao.project.name": "project"}))
    source = make_span({"gen_ai.input.messages": "input-json"})

    exporter.export((source,))
    exported = delegate.batches[0][0]

    assert exported.attributes == {**source.attributes, "splunk_ao.system": "splunk_ao_python"}
    assert exported.resource.attributes["splunk_ao.project.name"] == "project"


def test_private_environment_switch_is_read_at_exporter_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION", "false")
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(delegate)
    monkeypatch.setenv("SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION", "true")

    exporter.export((make_span(),))

    assert "splunk_ao.request.model" not in delegate.batches[0][0].attributes


def test_default_normalization_is_disabled_but_sdk_marker_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION", raising=False)
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(delegate)

    exporter.export((make_span(),))

    attributes = delegate.batches[0][0].attributes
    assert attributes["gen_ai.request.model"] == "gpt-4o"
    assert "splunk_ao.request.model" not in attributes
    assert attributes["splunk_ao.system"] == "splunk_ao_python"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_private_environment_switch_explicitly_enables_normalization(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION", value)
    delegate = RecordingExporter()
    exporter = NormalizingSpanExporter(delegate)

    exporter.export((make_span({"gen_ai.input.messages": "input-json"}),))

    attributes = delegate.batches[0][0].attributes
    assert "gen_ai.input.messages" not in attributes
    assert attributes["splunk_ao.input.messages"] == "input-json"
    assert attributes["splunk_ao.system"] == "splunk_ao_python"
