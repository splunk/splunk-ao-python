from __future__ import annotations

import json
import logging
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Protocol, cast

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Tracer

from galileo_core.schemas.logging.span import AgentSpan, RetrieverSpan, ToolSpan, WorkflowSpan
from galileo_core.schemas.logging.span import Span as GalileoSpan
from splunk_ao.config import SplunkAOConfig
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
from splunk_ao.exporter import (
    RoutingAttrs,
    resolve_o11y_exporter_config,
    resolve_standalone_exporter_config,
    routing_resource_attributes,
)
from splunk_ao.utils.env_helpers import (
    _get_log_stream_from_env,
    _get_log_stream_id_from_env,
    _get_log_stream_or_default,
    _get_project_from_env,
    _get_project_id_from_env,
    _get_project_or_default,
)
from splunk_ao.utils.retrievers import document_adapter

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


_TRACE_PROVIDER_CONTEXT_VAR: ContextVar[TracerProvider | None] = ContextVar("galileo_trace_provider", default=None)


ROUTING_ATTRIBUTE_KEYS = frozenset(
    {
        "splunk_ao.project.name",
        "splunk_ao.project.id",
        "splunk_ao.logstream.name",
        "splunk_ao.logstream.id",
        "splunk_ao.experiment.id",
    }
)


def _resolve_name_or_id(
    explicit_name: str | None,
    explicit_id: str | None,
    context_name: str | None,
    environment_name: str | None,
    environment_id: str | None,
    default_name: str | None,
) -> tuple[str | None, str | None]:
    """Resolve one immutable routing identity while preserving its supplied form."""
    if explicit_name:
        return explicit_name, None
    if explicit_id:
        return None, explicit_id
    if context_name:
        return context_name, None
    if environment_name:
        return environment_name, None
    if environment_id:
        return None, environment_id
    return default_name, None


def _resolve_routing(
    deployment: DeploymentMode,
    project: str | None,
    project_id: str | None,
    logstream: str | None,
    log_stream_id: str | None,
    experiment_id: str | None,
) -> RoutingAttrs:
    """Capture routing once for one exporter without resolving names to IDs."""
    standalone = deployment == DeploymentMode.STANDALONE
    project_name, resolved_project_id = _resolve_name_or_id(
        project,
        project_id,
        _project_context.get(None),
        _get_project_from_env(),
        _get_project_id_from_env(),
        _get_project_or_default(None) if standalone else None,
    )
    log_stream_name, resolved_log_stream_id = _resolve_name_or_id(
        logstream,
        log_stream_id,
        _log_stream_context.get(None),
        _get_log_stream_from_env(),
        _get_log_stream_id_from_env(),
        _get_log_stream_or_default(None) if standalone else None,
    )
    return RoutingAttrs(
        project_name=project_name,
        project_id=resolved_project_id,
        log_stream_name=log_stream_name,
        log_stream_id=resolved_log_stream_id,
        experiment_id=experiment_id or _experiment_id_context.get(None),
    )


def _with_routing_resource(span: ReadableSpan, routing_resource: Resource) -> ReadableSpan:
    """Return an immutable copy with authoritative routing in its Resource."""
    attributes = {key: value for key, value in (span.attributes or {}).items() if key not in ROUTING_ATTRIBUTE_KEYS}
    source_resource = span.resource or Resource({})
    base_resource = Resource(
        {key: value for key, value in source_resource.attributes.items() if key not in ROUTING_ATTRIBUTE_KEYS},
        schema_url=source_resource.schema_url,
    )
    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=base_resource.merge(routing_resource),
        attributes=attributes,
        events=span.events,
        links=span.links,
        kind=span.kind,
        instrumentation_info=span.instrumentation_info,
        status=span.status,
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class SplunkAOOTLPExporter(SpanExporter):
    """
    OpenTelemetry OTLP span exporter preconfigured for Splunk AO.

    This exporter wraps the standard OTLPSpanExporter with deployment-aware
    configuration, authentication, and immutable routing. For most applications, use
    SplunkAOSpanProcessor instead, which provides a complete tracing solution.
    """

    def __init__(
        self,
        project: str | None = None,
        project_id: str | None = None,
        logstream: str | None = None,
        log_stream_id: str | None = None,
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
        logstream, log_stream_id : str, optional
            Target log-stream name or ID.
        experiment_id : str, optional
            Target experiment ID. Takes precedence over log-stream routing.
        **kwargs
            Additional configuration options passed to the underlying OTLPSpanExporter.

        Raises
        ------
        ValueError
            When configuration is not properly initialized with required credentials.
        """
        config = SplunkAOConfig.get()
        deployment = config.resolve_deployment()
        self._routing = _resolve_routing(deployment, project, project_id, logstream, log_stream_id, experiment_id)
        if deployment == DeploymentMode.O11Y:
            exporter_config = resolve_o11y_exporter_config(O11yConfig.from_env(), self._routing)
        else:
            exporter_config = resolve_standalone_exporter_config(StandaloneConfig.from_env(), self._routing)

        self.project = self._routing.project_name
        self.project_id = self._routing.project_id
        self.logstream = self._routing.log_stream_name
        self.log_stream_id = self._routing.log_stream_id
        self.experiment_id = self._routing.experiment_id
        self._routing_resource = Resource(routing_resource_attributes(self._routing))
        self._delegate = _exporter_factory(endpoint=exporter_config.endpoint, headers=exporter_config.headers, **kwargs)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export immutable copies with authoritative routing Resources."""
        return self._delegate.export(tuple(_with_routing_resource(span, self._routing_resource) for span in spans))

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Flush the delegate exporter."""
        return self._delegate.force_flush(timeout_millis)

    def shutdown(self) -> None:
        """Shut down the delegate exporter."""
        self._delegate.shutdown()


class SplunkAOSpanProcessor(SpanProcessor):
    """
    Complete OpenTelemetry span processor with integrated Galileo export functionality.

    This processor combines span processing and export capabilities into a single
    component that can be directly attached to any OpenTelemetry TracerProvider.
    It handles the complete lifecycle of spans from creation to export to Galileo.

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
        logstream: str | None = None,
        log_stream_id: str | None = None,
        experiment_id: str | None = None,
        SpanProcessor: type | None = None,
        *,
        _exporter: SpanExporter | None = None,
        _exporter_factory: Callable[..., SpanExporter] = OTLPSpanExporter,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Galileo span processor with export configuration.

        Parameters
        ----------
        project, project_id : str, optional
            Target project name or ID.
        logstream, log_stream_id : str, optional
            Target log-stream name or ID.
        experiment_id : str, optional
            Target experiment ID. Takes precedence over log-stream routing.
        SpanProcessor : type, optional
            Custom span processor class. Defaults to BatchSpanProcessor for optimal performance.

        """
        self._exporter = (
            _exporter
            if _exporter is not None
            else SplunkAOOTLPExporter(
                project=project,
                project_id=project_id,
                logstream=logstream,
                log_stream_id=log_stream_id,
                experiment_id=experiment_id,
                _exporter_factory=_exporter_factory,
                **kwargs,
            )
        )
        self._project = getattr(self._exporter, "project", project)
        self._logstream = getattr(self._exporter, "logstream", logstream)

        if SpanProcessor is None:
            SpanProcessor = BatchSpanProcessor

        self._processor = SpanProcessor(self._exporter)

    def on_start(self, span: Span, parent_context: context.Context | None = None) -> None:
        """Handle span start events by delegating to the underlying processor."""
        session_id = _session_id_context.get(None)

        if session_id:
            span.set_attribute("splunk_ao.session.id", session_id)

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
        logger.info("Splunk AO span processor shutdown for project %s and logstream %s", self._project, self._logstream)

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


def _set_retriever_span_attributes(span: trace.Span, galileo_span: RetrieverSpan) -> None:
    span.set_attribute("db.operation", "search")
    span.set_attribute("gen_ai.input.messages", json.dumps([{"role": "user", "content": galileo_span.input}]))
    span.set_attribute(
        "gen_ai.output.messages",
        json.dumps(
            [
                {
                    "role": "assistant",
                    "content": {"documents": document_adapter.dump_python(galileo_span.output, mode="json")},
                }
            ]
        ),
    )


def _set_tool_span_attributes(span: trace.Span, galileo_span: ToolSpan) -> None:
    span.set_attribute("gen_ai.operation.name", "execute_tool")
    span.set_attribute("gen_ai.tool.name", galileo_span.name)
    span.set_attribute("gen_ai.tool.call.arguments", galileo_span.input)
    span.set_attribute("gen_ai.input.messages", json.dumps([{"role": "tool", "content": galileo_span.input}]))
    if galileo_span.output is not None:
        span.set_attribute("gen_ai.tool.call.result", galileo_span.output)
        span.set_attribute("gen_ai.output.messages", json.dumps([{"role": "tool", "content": galileo_span.output}]))
    if galileo_span.tool_call_id is not None:
        span.set_attribute("gen_ai.tool.call.id", galileo_span.tool_call_id)


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


def _set_workflow_span_attributes(span: trace.Span, galileo_span: WorkflowSpan) -> None:
    """Set OpenTelemetry attributes for WorkflowSpan."""
    # Handle input - Union[str, Sequence[Message]]
    if isinstance(galileo_span.input, str):
        input_messages = [{"role": "user", "content": galileo_span.input}]
    else:
        # Sequence[Message] - serialize each message
        input_messages = []
        for msg in list(galileo_span.input):
            if hasattr(msg, "model_dump"):
                input_messages.append(msg.model_dump(exclude_none=True))
            else:
                input_messages.append(msg)
    span.set_attribute("gen_ai.input.messages", json.dumps(input_messages))

    # Handle output - Union[str, Message, Sequence[Document], None]
    if galileo_span.output is None:
        return

    output_value = galileo_span.output
    # Type annotation to handle flexible content types (string or dict)
    # Content can be: str (simple output), dict (documents), or dict (Message model_dump)
    output_messages: list[dict[str, Any]] = []

    if isinstance(output_value, str):
        output_messages = [{"role": "assistant", "content": output_value}]
    elif hasattr(output_value, "model_dump"):
        # Single Message
        output_messages = [output_value.model_dump(exclude_none=True)]
    else:
        # Sequence[Document] - wrap in assistant message
        # Use document_adapter for consistency with _set_retriever_span_attributes
        output_messages = [
            {
                "role": "assistant",
                "content": {"documents": document_adapter.dump_python(list(output_value), mode="json")},
            }
        ]

    span.set_attribute("gen_ai.output.messages", json.dumps(output_messages))


@contextmanager
def start_splunk_ao_span(galileo_span: GalileoSpan) -> Generator[trace.Span, Any, None]:
    tracer_provider = _TRACE_PROVIDER_CONTEXT_VAR.get()
    if tracer_provider is None:
        tracer_provider = trace.get_tracer_provider()
        _TRACE_PROVIDER_CONTEXT_VAR.set(cast(TracerProvider, tracer_provider))
    tracer = tracer_provider.get_tracer("galileo-tracer")
    is_conversation_root = not trace.get_current_span().get_span_context().is_valid and isinstance(
        galileo_span, WorkflowSpan | AgentSpan
    )
    with tracer.start_as_current_span(galileo_span.name) as span:
        yield span
        if is_conversation_root:
            # OTel semantic-convention attributes are boolean; the native route's
            # string-valued user_metadata bridge is an interim compatibility path.
            span.set_attribute(GEN_AI_CONVERSATION_ROOT, value=True)
        # Set dataset attributes for ground truth/reference output support
        _apply_dataset_attributes(
            span, galileo_span.dataset_input, galileo_span.dataset_output, galileo_span.dataset_metadata
        )
        if isinstance(galileo_span, RetrieverSpan):
            _set_retriever_span_attributes(span, galileo_span)
        elif isinstance(galileo_span, ToolSpan):
            _set_tool_span_attributes(span, galileo_span)
        elif isinstance(galileo_span, WorkflowSpan):
            _set_workflow_span_attributes(span, galileo_span)
