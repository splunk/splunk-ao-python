"""Immutable OTLP span normalization before serialization."""

from __future__ import annotations

import os
from collections.abc import Sequence

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from splunk_ao.converter.attribute_mapping import normalize_attributes_for_export

ROUTING_ATTRIBUTE_KEYS = frozenset(
    {
        "splunk_ao.project.name",
        "splunk_ao.project.id",
        "splunk_ao.agentstream.name",
        "splunk_ao.agentstream.id",
        "splunk_ao.experiment.id",
    }
)

_NORMALIZATION_ENV = "SPLUNK_AO_DEV_ENABLE_ATTRIBUTE_NORMALIZATION"
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _normalization_enabled() -> bool:
    value = os.environ.get(_NORMALIZATION_ENV)
    return value is None or value.strip().lower() not in _FALSE_VALUES


def copy_span_for_export(
    span: ReadableSpan, routing_resource: Resource | None = None, *, normalize_attributes: bool = True
) -> ReadableSpan:
    """Return an immutable span copy with final attributes and routing."""
    source_attributes = {
        key: value for key, value in (span.attributes or {}).items() if key not in ROUTING_ATTRIBUTE_KEYS
    }
    attributes = normalize_attributes_for_export(source_attributes, enabled=normalize_attributes)

    source_resource = span.resource or Resource({})
    base_resource = Resource(
        {key: value for key, value in source_resource.attributes.items() if key not in ROUTING_ATTRIBUTE_KEYS},
        schema_url=source_resource.schema_url,
    )
    resource = base_resource.merge(routing_resource) if routing_resource is not None else base_resource

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
    """Apply canonical attributes and routing once before delegating export."""

    def __init__(
        self,
        delegate: SpanExporter,
        routing_resource: Resource | None = None,
        *,
        normalize_attributes: bool | None = None,
    ) -> None:
        self._delegate = delegate
        self._routing_resource = routing_resource
        self._normalize_attributes = _normalization_enabled() if normalize_attributes is None else normalize_attributes

    @property
    def delegate(self) -> SpanExporter:
        """Return the wrapped exporter for SDK composition and diagnostics."""
        return self._delegate

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export normalized immutable copies of the supplied spans."""
        return self._delegate.export(
            tuple(
                copy_span_for_export(span, self._routing_resource, normalize_attributes=self._normalize_attributes)
                for span in spans
            )
        )

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Delegate flushing exactly once."""
        return self._delegate.force_flush(timeout_millis)

    def shutdown(self) -> None:
        """Delegate shutdown exactly once."""
        self._delegate.shutdown()
