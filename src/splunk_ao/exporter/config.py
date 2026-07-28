"""Shared OTLP exporter configuration and routing."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SpanExporter

from splunk_ao.exporter.span_transform import NormalizingSpanExporter


@dataclass
class ExporterConfig:
    """Resolved public configuration for an OTLP HTTP exporter."""

    endpoint: str
    headers: dict[str, str]


@dataclass
class RoutingAttrs:
    """Optional project, log-stream, and experiment routing values."""

    project_name: str | None = None
    project_id: str | None = None
    log_stream_name: str | None = None
    log_stream_id: str | None = None
    experiment_id: str | None = None


ExporterFactory = Callable[..., SpanExporter]


def resolve_exporter_config(endpoint: str, auth_header: tuple[str, str], routing: RoutingAttrs) -> ExporterConfig:
    """Resolve endpoint, authentication, and routing request headers."""
    headers = {auth_header[0]: auth_header[1]}
    if routing.project_name:
        headers["project"] = routing.project_name
    elif routing.project_id:
        headers["projectid"] = routing.project_id

    if routing.experiment_id:
        headers["experimentid"] = routing.experiment_id
    elif routing.log_stream_name:
        headers["logstream"] = routing.log_stream_name
    elif routing.log_stream_id:
        headers["logstreamid"] = routing.log_stream_id

    return ExporterConfig(endpoint=endpoint, headers=headers)


def routing_resource_attributes(routing: RoutingAttrs) -> dict[str, str]:
    """Build Resource attributes matching the routing request headers."""
    attributes: dict[str, str] = {}
    if routing.project_name:
        attributes["splunk_ao.project.name"] = routing.project_name
    elif routing.project_id:
        attributes["splunk_ao.project.id"] = routing.project_id

    if routing.experiment_id:
        attributes["splunk_ao.experiment.id"] = routing.experiment_id
    elif routing.log_stream_name:
        attributes["splunk_ao.logstream.name"] = routing.log_stream_name
    elif routing.log_stream_id:
        attributes["splunk_ao.logstream.id"] = routing.log_stream_id

    return attributes


def build_exporter(
    endpoint: str,
    auth_header: tuple[str, str],
    routing: RoutingAttrs,
    _exporter_factory: ExporterFactory = OTLPSpanExporter,
    **exporter_kwargs: Any,
) -> SpanExporter:
    """Build an OTLP HTTP exporter from shared resolved configuration."""
    config = resolve_exporter_config(endpoint, auth_header, routing)
    delegate = _exporter_factory(endpoint=config.endpoint, headers=config.headers, **exporter_kwargs)
    return NormalizingSpanExporter(delegate, Resource(routing_resource_attributes(routing)))
