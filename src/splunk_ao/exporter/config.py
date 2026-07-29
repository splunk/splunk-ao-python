"""Shared OTLP exporter configuration and routing."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SpanExporter

from splunk_ao.constants import DEFAULT_LOG_STREAM_NAME, DEFAULT_PROJECT_NAME
from splunk_ao.deployment import DeploymentMode
from splunk_ao.exporter.span_transform import NormalizingSpanExporter
from splunk_ao.utils.env_helpers import (
    _get_log_stream_from_env,
    _get_log_stream_id_from_env,
    _get_project_from_env,
    _get_project_id_from_env,
)


@dataclass
class ExporterConfig:
    """Resolved public configuration for an OTLP HTTP exporter."""

    endpoint: str
    headers: dict[str, str]


@dataclass
class RoutingAttrs:
    """Optional project, agent-stream, and experiment routing values."""

    project_name: str | None = None
    project_id: str | None = None
    agent_stream_name: str | None = None
    agent_stream_id: str | None = None
    experiment_id: str | None = None


ExporterFactory = Callable[..., SpanExporter]


def _resolve_name_or_id(
    label: str,
    explicit_name: str | None,
    explicit_id: str | None,
    context_name: str | None,
    context_id: str | None,
    environment_name: str | None,
    environment_id: str | None,
    default_name: str | None,
) -> tuple[str | None, str | None]:
    """Resolve one routing identity while preserving the selected form."""
    for source, name, id_ in (
        ("arguments", explicit_name, explicit_id),
        ("context", context_name, context_id),
        ("environment", environment_name, environment_id),
    ):
        if name and id_:
            raise ValueError(f"Cannot configure both {label} name and ID from {source}.")
        if name:
            return name, None
        if id_:
            return None, id_
    return default_name, None


def resolve_routing(
    deployment: DeploymentMode,
    *,
    project: str | None = None,
    project_id: str | None = None,
    agent_stream: str | None = None,
    agent_stream_id: str | None = None,
    experiment_id: str | None = None,
    context_project: str | None = None,
    context_project_id: str | None = None,
    context_agent_stream: str | None = None,
    context_agent_stream_id: str | None = None,
    context_experiment_id: str | None = None,
) -> RoutingAttrs:
    """Capture routing once using explicit, context, environment, then default precedence."""
    standalone = deployment == DeploymentMode.STANDALONE
    project_name, resolved_project_id = _resolve_name_or_id(
        "project",
        project,
        project_id,
        context_project,
        context_project_id,
        _get_project_from_env(),
        _get_project_id_from_env(),
        DEFAULT_PROJECT_NAME if standalone else None,
    )
    agent_stream_name, resolved_agent_stream_id = _resolve_name_or_id(
        "agent stream",
        agent_stream,
        agent_stream_id,
        context_agent_stream,
        context_agent_stream_id,
        _get_log_stream_from_env(),
        _get_log_stream_id_from_env(),
        DEFAULT_LOG_STREAM_NAME if standalone else None,
    )
    return RoutingAttrs(
        project_name=project_name,
        project_id=resolved_project_id,
        agent_stream_name=agent_stream_name,
        agent_stream_id=resolved_agent_stream_id,
        experiment_id=experiment_id or context_experiment_id,
    )


def resolve_exporter_config(endpoint: str, auth_header: tuple[str, str], routing: RoutingAttrs) -> ExporterConfig:
    """Resolve endpoint, authentication, and routing request headers."""
    headers = {auth_header[0]: auth_header[1]}
    if routing.project_name:
        headers["project"] = routing.project_name
    elif routing.project_id:
        headers["projectid"] = routing.project_id

    if routing.experiment_id:
        headers["experimentid"] = routing.experiment_id
    elif routing.agent_stream_name:
        headers["agentstream"] = routing.agent_stream_name
    elif routing.agent_stream_id:
        headers["agentstreamid"] = routing.agent_stream_id

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
    elif routing.agent_stream_name:
        attributes["splunk_ao.agentstream.name"] = routing.agent_stream_name
    elif routing.agent_stream_id:
        attributes["splunk_ao.agentstream.id"] = routing.agent_stream_id

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
