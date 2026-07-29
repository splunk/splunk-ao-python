from __future__ import annotations

import json
import logging
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Protocol, cast

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Tracer

from galileo_core.schemas.logging.span import AgentSpan, WorkflowSpan
from galileo_core.schemas.logging.span import Span as GalileoSpan
from splunk_ao.config import SplunkAOConfig
from splunk_ao.converter import build_span_attributes
from splunk_ao.decorator import (
    _dataset_input_context,
    _dataset_metadata_context,
    _dataset_output_context,
    _experiment_id_context,
    _log_stream_context,
    _project_context,
    _session_id_context,
)
from splunk_ao.deployment import DeploymentMode, O11yConfig, StandaloneConfig
from splunk_ao.exporter import RoutingAttrs, build_o11y_exporter, build_standalone_exporter, resolve_routing

logger = logging.getLogger(__name__)

GEN_AI_CONVERSATION_ROOT = "gen_ai.conversation_root"


class TracerProvider(Protocol):
    def add_span_processor(self, span_processor: Any) -> None: ...

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: Any | None = None,
    ) -> Tracer: ...


_TRACE_PROVIDER_CONTEXT_VAR: ContextVar[TracerProvider | None] = ContextVar("splunk_ao_trace_provider", default=None)

_LEGACY_ROUTING_OPTIONS = {"logstream": "agentstream", "log_stream_id": "agent_stream_id"}


def _reject_legacy_routing_options(options: dict[str, Any]) -> None:
    for legacy_name, replacement in _LEGACY_ROUTING_OPTIONS.items():
        if legacy_name in options:
            raise TypeError(f"{legacy_name} is not supported; use {replacement}")


def _resolve_routing(
    deployment: DeploymentMode,
    project: str | None,
    project_id: str | None,
    agentstream: str | None,
    agent_stream_id: str | None,
    experiment_id: str | None,
) -> RoutingAttrs:
    """Capture routing once for one exporter without resolving names to IDs."""
    return resolve_routing(
        deployment,
        project=project,
        project_id=project_id,
        log_stream=agentstream,
        log_stream_id=agent_stream_id,
        experiment_id=experiment_id,
        context_project=_project_context.get(None),
        context_log_stream=_log_stream_context.get(None),
        context_experiment_id=_experiment_id_context.get(None),
    )


class SplunkAOOTLPExporter(SpanExporter):
    """
    OpenTelemetry OTLP span exporter preconfigured for Splunk AO.

    This exporter wraps the standard OTLPSpanExporter with deployment-aware
    configuration, authentication, and immutable routing. For most applications, use
    SplunkAOSpanProcessor instead, which provides a complete tracing solution.

    Routing is captured when the exporter is constructed and remains fixed for its
    lifetime. Applications that export to multiple destinations must use a separate
    exporter and span processor for each destination.
    """

    def __init__(
        self,
        project: str | None = None,
        project_id: str | None = None,
        agentstream: str | None = None,
        agent_stream_id: str | None = None,
        experiment_id: str | None = None,
        *,
        _exporter_factory: Callable[..., SpanExporter] = OTLPSpanExporter,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Splunk AO OTLP exporter with deployment-aware configuration.

        Parameters
        ----------
        project, project_id : str, optional
            Target project name or ID.
        agentstream, agent_stream_id : str, optional
            Target agent-stream name or ID.
        experiment_id : str, optional
            Target experiment ID. Takes precedence over agent-stream routing.
        **kwargs
            Additional configuration options passed to the underlying OTLPSpanExporter.

        Raises
        ------
        ValueError
            When configuration is not properly initialized with required credentials.
        """
        _reject_legacy_routing_options(kwargs)
        config = SplunkAOConfig.get()
        deployment = config.resolve_deployment()
        self._routing = _resolve_routing(deployment, project, project_id, agentstream, agent_stream_id, experiment_id)
        if deployment == DeploymentMode.O11Y:
            self._delegate = build_o11y_exporter(O11yConfig.from_env(), self._routing, _exporter_factory, **kwargs)
        else:
            self._delegate = build_standalone_exporter(
                StandaloneConfig.from_env(), self._routing, _exporter_factory, **kwargs
            )

        self.project = self._routing.project_name
        self.project_id = self._routing.project_id
        self.agentstream = self._routing.log_stream_name
        self.agent_stream_id = self._routing.log_stream_id
        self.experiment_id = self._routing.experiment_id

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export through the shared immutable normalization pipeline."""
        return self._delegate.export(spans)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Flush the delegate exporter."""
        return self._delegate.force_flush(timeout_millis)

    def shutdown(self) -> None:
        """Shut down the delegate exporter."""
        self._delegate.shutdown()


class SplunkAOSpanProcessor(SpanProcessor):
    """
    Complete OpenTelemetry span processor with integrated Splunk AO export functionality.

    This processor combines span processing and export capabilities into a single
    component that can be directly attached to any OpenTelemetry TracerProvider.
    It handles the complete lifecycle of spans from creation to export to Splunk AO.
    Project, agent-stream, and experiment routing is fixed when the processor's exporter
    is constructed. Use separate processors and exporters for separate destinations.

    Examples
    --------
    >>> from opentelemetry.sdk.trace import TracerProvider
    >>> tracer_provider = TracerProvider()
    >>> processor = add_splunk_ao_span_processor(tracer_provider, project="my-project")
    """

    def __init__(
        self,
        project: str | None = None,
        project_id: str | None = None,
        agentstream: str | None = None,
        agent_stream_id: str | None = None,
        experiment_id: str | None = None,
        SpanProcessor: type | None = None,
        *,
        _exporter: SpanExporter | None = None,
        _exporter_factory: Callable[..., SpanExporter] = OTLPSpanExporter,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Splunk AO span processor with export configuration.

        Parameters
        ----------
        project, project_id : str, optional
            Target project name or ID.
        agentstream, agent_stream_id : str, optional
            Target agent-stream name or ID.
        experiment_id : str, optional
            Target experiment ID. Takes precedence over agent-stream routing.
        SpanProcessor : type, optional
            Custom span processor class. Defaults to BatchSpanProcessor for optimal performance.

        Raises
        ------
        ValueError
            When a prebuilt exporter is combined with exporter configuration options.
        """
        _reject_legacy_routing_options(kwargs)
        routing_provided = any(
            value is not None for value in (project, project_id, agentstream, agent_stream_id, experiment_id)
        )
        if _exporter is not None and (routing_provided or kwargs):
            raise ValueError("Routing and OTLP exporter options cannot be used with _exporter")

        self._exporter = (
            _exporter
            if _exporter is not None
            else SplunkAOOTLPExporter(
                project=project,
                project_id=project_id,
                agentstream=agentstream,
                agent_stream_id=agent_stream_id,
                experiment_id=experiment_id,
                _exporter_factory=_exporter_factory,
                **kwargs,
            )
        )
        self._project = getattr(self._exporter, "project", project)
        self._agentstream = getattr(self._exporter, "agentstream", agentstream)

        if SpanProcessor is None:
            SpanProcessor = BatchSpanProcessor

        self._processor = SpanProcessor(self._exporter)

    def on_start(self, span: Span, parent_context: context.Context | None = None) -> None:
        """Handle span start events by delegating to the underlying processor."""
        session_id = _session_id_context.get(None)

        if session_id:
            span.set_attribute("gen_ai.conversation.id", session_id)

        # Set dataset attributes for ground truth/reference output support
        _apply_dataset_attributes(
            span,
            _dataset_input_context.get(None),
            _dataset_output_context.get(None),
            _dataset_metadata_context.get(None),
        )

        self._processor.on_start(span, parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        """Handle span completion events by delegating to the underlying processor."""
        self._processor.on_end(span)

    def shutdown(self) -> None:
        """Gracefully shutdown the processor and flush any remaining spans."""
        self._processor.shutdown()
        logger.info(
            "Splunk AO span processor shutdown for project %s and agentstream %s", self._project, self._agentstream
        )

    def force_flush(self, timeout_millis: int = 40000) -> bool:
        """Force immediate export of all pending spans with specified timeout."""
        return self._processor.force_flush(timeout_millis)

    @property
    def exporter(self) -> SpanExporter:
        """Access to the underlying Splunk AO OTLP exporter instance."""
        return self._exporter

    @property
    def processor(self) -> SpanProcessor:
        """Access to the underlying OpenTelemetry span processor instance."""
        return self._processor


def add_splunk_ao_span_processor(
    tracer_provider: TracerProvider, processor: SplunkAOSpanProcessor | None = None, **processor_kwargs: Any
) -> SplunkAOSpanProcessor:
    """Construct or accept, register, and return a Splunk AO span processor."""
    if processor is not None and processor_kwargs:
        raise ValueError("processor_kwargs cannot be used with an existing processor")

    resolved_processor = processor if processor is not None else SplunkAOSpanProcessor(**processor_kwargs)
    tracer_provider.add_span_processor(resolved_processor)
    _TRACE_PROVIDER_CONTEXT_VAR.set(tracer_provider)
    return resolved_processor


def _apply_dataset_attributes(
    span: trace.Span, dataset_input: str | None, dataset_output: str | None, dataset_metadata: dict[str, Any] | None
) -> None:
    """Write dataset context attributes onto a span."""
    if dataset_input is not None:
        span.set_attribute("splunk_ao.dataset.input", dataset_input)
    if dataset_output is not None:
        span.set_attribute("splunk_ao.dataset.output", dataset_output)
    if dataset_metadata is not None:
        span.set_attribute("splunk_ao.dataset.metadata", json.dumps(dataset_metadata))


@contextmanager
def start_splunk_ao_span(ao_span: GalileoSpan) -> Generator[trace.Span, Any, None]:
    tracer_provider = _TRACE_PROVIDER_CONTEXT_VAR.get()
    if tracer_provider is None:
        tracer_provider = trace.get_tracer_provider()
        _TRACE_PROVIDER_CONTEXT_VAR.set(cast(TracerProvider, tracer_provider))
    tracer = tracer_provider.get_tracer("splunk-ao-tracer")
    is_conversation_root = not trace.get_current_span().get_span_context().is_valid and isinstance(
        ao_span, WorkflowSpan | AgentSpan
    )
    with tracer.start_as_current_span(ao_span.name) as span:
        try:
            yield span
        finally:
            try:
                attributes = build_span_attributes(ao_span, _session_id_context.get(None))
                if is_conversation_root:
                    attributes[GEN_AI_CONVERSATION_ROOT] = True
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            except Exception:
                logger.warning("Failed to finalize Splunk AO span attributes", exc_info=True)
