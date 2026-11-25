"""Immutable OTLP span preparation before serialization."""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from splunk_ao.exporter.diagnostics import ExportHealth, get_export_health

ROUTING_ATTRIBUTE_KEYS = frozenset(
    {
        "splunk_ao.project.name",
        "splunk_ao.project.id",
        "splunk_ao.logstream.name",
        "splunk_ao.logstream.id",
        "splunk_ao.experiment.id",
    }
)


def copy_span_for_export(span: ReadableSpan, routing_resource: Resource | None = None) -> ReadableSpan:
    """Return an immutable span copy with final attributes and routing."""
    attributes = {key: value for key, value in (span.attributes or {}).items() if key not in ROUTING_ATTRIBUTE_KEYS}

    source_resource = span.resource or Resource({})
    base_resource = Resource(
        {key: value for key, value in source_resource.attributes.items() if key not in ROUTING_ATTRIBUTE_KEYS},
        schema_url=source_resource.schema_url,
    )
    resource = routing_resource.merge(base_resource) if routing_resource is not None else base_resource

    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=resource,
        attributes=attributes,
        events=span.events,
        links=span.links,
        kind=span.kind,
        status=span.status,
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class NormalizingSpanExporter(SpanExporter):
    """Apply SDK routing once before delegating export."""

    def __init__(self, delegate: SpanExporter, routing_resource: Resource | None = None) -> None:
        self._delegate = delegate
        self._routing_resource = routing_resource

    @property
    def delegate(self) -> SpanExporter:
        """Return the wrapped exporter for SDK composition and diagnostics."""
        return self._delegate

    @property
    def export_health(self) -> ExportHealth:
        """Return the delegate's receiver-acknowledgement health snapshot."""
        return get_export_health(self._delegate)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export immutable copies of the supplied spans."""
        return self._delegate.export(tuple(copy_span_for_export(span, self._routing_resource) for span in spans))

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Delegate flushing exactly once."""
        return self._delegate.force_flush(timeout_millis)

    def shutdown(self) -> None:
        """Delegate shutdown exactly once."""
        self._delegate.shutdown()
