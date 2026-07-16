"""Splunk Observability Cloud OTLP exporter construction."""

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from splunk_ao.deployment import O11yConfig
from splunk_ao.exporter.config import (
    ExporterConfig,
    ExporterFactory,
    RoutingAttrs,
    build_exporter,
    resolve_exporter_config,
)


def _o11y_auth_header(config: O11yConfig) -> tuple[str, str]:
    return "X-SF-Token", config.require_ingest_token().get_secret_value()


def resolve_o11y_exporter_config(config: O11yConfig, routing: RoutingAttrs) -> ExporterConfig:
    """Resolve o11y endpoint, authentication, and routing headers."""
    return resolve_exporter_config(config.otlp_endpoint, _o11y_auth_header(config), routing)


def build_o11y_exporter(
    config: O11yConfig, routing: RoutingAttrs, _exporter_factory: ExporterFactory = OTLPSpanExporter
) -> OTLPSpanExporter:
    """Build an OTLP exporter authenticated for Splunk Observability Cloud."""
    return build_exporter(config.otlp_endpoint, _o11y_auth_header(config), routing, _exporter_factory)
