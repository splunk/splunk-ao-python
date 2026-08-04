"""Standalone Splunk AO OTLP exporter construction."""

from typing import Any

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SpanExporter

from splunk_ao.deployment import DeploymentMode, StandaloneConfig
from splunk_ao.exporter.config import (
    ExporterConfig,
    ExporterFactory,
    RoutingAttrs,
    build_exporter,
    resolve_exporter_config,
)


def _standalone_auth_header(config: StandaloneConfig) -> tuple[str, str]:
    return "Splunk-AO-API-Key", config.api_key.get_secret_value()


def resolve_standalone_exporter_config(config: StandaloneConfig, routing: RoutingAttrs) -> ExporterConfig:
    """Resolve standalone endpoint, authentication, and routing headers."""
    return resolve_exporter_config(config.otlp_endpoint, _standalone_auth_header(config), routing)


def build_standalone_exporter(
    config: StandaloneConfig,
    routing: RoutingAttrs,
    _exporter_factory: ExporterFactory = OTLPSpanExporter,
    **exporter_kwargs: Any,
) -> SpanExporter:
    """Build an OTLP exporter authenticated for standalone Splunk AO."""
    return build_exporter(
        config.otlp_endpoint,
        _standalone_auth_header(config),
        routing,
        deployment=DeploymentMode.STANDALONE,
        _exporter_factory=_exporter_factory,
        **exporter_kwargs,
    )
