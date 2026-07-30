"""Deployment-aware OTLP export and batching primitives."""

from splunk_ao.exporter.config import (
    ExporterConfig,
    RoutingAttrs,
    build_exporter,
    create_otel_resource,
    resolve_exporter_config,
    resolve_routing,
    routing_resource_attributes,
)
from splunk_ao.exporter.o11y import build_o11y_exporter, resolve_o11y_exporter_config
from splunk_ao.exporter.sink import BatchConfig, SpanSink, build_batch_processor, build_span_sink
from splunk_ao.exporter.standalone import build_standalone_exporter, resolve_standalone_exporter_config

__all__ = [
    "BatchConfig",
    "ExporterConfig",
    "RoutingAttrs",
    "SpanSink",
    "build_batch_processor",
    "build_exporter",
    "build_o11y_exporter",
    "build_span_sink",
    "build_standalone_exporter",
    "create_otel_resource",
    "resolve_exporter_config",
    "resolve_o11y_exporter_config",
    "resolve_routing",
    "resolve_standalone_exporter_config",
    "routing_resource_attributes",
]
