import warnings
from collections.abc import Sequence
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link, SpanContext, SpanKind, TraceFlags
from opentelemetry.trace.status import Status, StatusCode

from galileo_core.schemas.logging.span import WorkflowSpan
from splunk_ao import get_tracing_headers
from splunk_ao.decorator import (
    _agent_stream_context,
    _dataset_input_context,
    _dataset_metadata_context,
    _dataset_output_context,
    _experiment_id_context,
    _project_context,
    _session_id_context,
)
from splunk_ao.deployment import DeploymentMode, O11yConfig, StandaloneConfig
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.otel import (
    _TRACE_PROVIDER_CONTEXT_VAR,
    SplunkAOOTLPExporter,
    SplunkAOSpanProcessor,
    add_splunk_ao_span_processor,
    start_splunk_ao_span,
)
from splunk_ao.shared.exceptions import MissingConfigurationError

ROUTING_KEYS = {
    "splunk_ao.project.name",
    "splunk_ao.project.id",
    "splunk_ao.logstream.name",
    "splunk_ao.logstream.id",
    "splunk_ao.experiment.id",
}


class RecordingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []
        self.force_flush_timeouts: list[int] = []
        self.shutdown_calls = 0

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        self.force_flush_timeouts.append(timeout_millis)
        return True

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class RecordingExporterFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.exporter = RecordingExporter()

    def __call__(self, **kwargs: object) -> RecordingExporter:
        self.calls.append(kwargs)
        return self.exporter


class RecordingSpanProcessor:
    def __init__(self, exporter: SpanExporter) -> None:
        self.exporter = exporter
        self.started: list[object] = []
        self.ended: list[object] = []
        self.shutdown_calls = 0

    def on_start(self, span: object, parent_context: object | None = None) -> None:
        self.started.append((span, parent_context))

    def on_end(self, span: object) -> None:
        self.ended.append(span)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def shutdown(self) -> None:
        self.shutdown_calls += 1


@pytest.fixture(autouse=True)
def reset_otel_context(monkeypatch: pytest.MonkeyPatch):
    contexts = (
        _project_context,
        _agent_stream_context,
        _experiment_id_context,
        _session_id_context,
        _dataset_input_context,
        _dataset_output_context,
        _dataset_metadata_context,
    )
    for context_var in contexts:
        context_var.set(None)
    _TRACE_PROVIDER_CONTEXT_VAR.set(None)
    for name in (
        "SPLUNK_AO_PROJECT",
        "SPLUNK_AO_PROJECT_ID",
        "SPLUNK_AO_AGENT_STREAM",
        "SPLUNK_AO_AGENT_STREAM_ID",
        "SPLUNK_AO_LOG_STREAM",
        "SPLUNK_AO_LOG_STREAM_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    yield
    for context_var in contexts:
        context_var.set(None)
    _TRACE_PROVIDER_CONTEXT_VAR.set(None)


def make_span() -> ReadableSpan:
    context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=False,
        trace_flags=TraceFlags.SAMPLED,
    )
    parent = SpanContext(
        trace_id=context.trace_id, span_id=0xFEDCBA0987654321, is_remote=True, trace_flags=TraceFlags.SAMPLED
    )
    linked_context = SpanContext(
        trace_id=0xABCDEF1234567890ABCDEF1234567890,
        span_id=0xABCDEF1234567890,
        is_remote=False,
        trace_flags=TraceFlags.SAMPLED,
    )
    return ReadableSpan(
        name="upstream-span",
        context=context,
        parent=parent,
        resource=Resource(
            {"service.name": "checkout", "splunk_ao.project.name": "stale-resource-project"},
            schema_url="https://opentelemetry.io/schemas/1.38.0",
        ),
        attributes={
            "gen_ai.request.model": "gpt-4o",
            "gen_ai.provider.name": "openai",
            "gen_ai.system": "legacy-upstream-provider",
            "custom.attribute": "preserved",
            "splunk_ao.project.name": "stale-span-project",
        },
        events=(Event("event", {"event.attribute": "value"}, timestamp=3),),
        links=(Link(linked_context, {"link.attribute": "value"}),),
        kind=SpanKind.CLIENT,
        status=Status(StatusCode.OK),
        start_time=1,
        end_time=2,
        instrumentation_scope=InstrumentationScope("upstream.instrumentor", "1.0.0"),
    )


def build_exporter(mode: DeploymentMode, factory: RecordingExporterFactory, **routing: str) -> SplunkAOOTLPExporter:
    config = MagicMock()
    config.resolve_deployment.return_value = mode
    standalone = StandaloneConfig(
        api_key="standalone-key", console_url="https://console.example.com", api_url="https://api.example.com"
    )
    o11y = O11yConfig(realm="us1", o11y_token="o11y-token")
    with (
        patch("splunk_ao.otel.SplunkAOConfig.get", return_value=config),
        patch("splunk_ao.otel.StandaloneConfig.from_env", return_value=standalone),
        patch("splunk_ao.otel.O11yConfig.from_env", return_value=o11y),
    ):
        return SplunkAOOTLPExporter(_exporter_factory=factory, **routing)


def test_standalone_exporter_uses_shared_config_and_name_routing() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.STANDALONE, factory, project="payments", agentstream="production")

    assert factory.calls == [
        {
            "endpoint": "https://api.example.com/otel/v1/traces",
            "headers": {"Splunk-AO-API-Key": "standalone-key", "project": "payments", "logstream": "production"},
        }
    ]
    exporter.shutdown()


def test_o11y_exporter_supports_id_and_experiment_routing() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(
        DeploymentMode.O11Y,
        factory,
        project_id="project-id",
        agent_stream_id="ignored-agent-stream-id",
        experiment_id="experiment-id",
    )

    assert factory.calls[0] == {
        "endpoint": "https://ingest.us1.observability.splunkcloud.com/v2/trace/otlp",
        "headers": {"X-SF-Token": "o11y-token", "projectid": "project-id", "experimentid": "experiment-id"},
    }
    exporter.shutdown()


def test_o11y_exporter_allows_auth_only_routing() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.O11Y, factory)

    assert factory.calls[0]["headers"] == {"X-SF-Token": "o11y-token"}
    exporter.export((make_span(),))
    exported = factory.exporter.spans[0]
    assert not ROUTING_KEYS.intersection(exported.resource.attributes)
    assert not ROUTING_KEYS.intersection(exported.attributes or {})
    exporter.shutdown()


def test_o11y_exporter_rejects_crud_only_config_before_delegate_construction() -> None:
    factory = RecordingExporterFactory()
    config = MagicMock()
    config.resolve_deployment.return_value = DeploymentMode.O11Y
    crud_only = O11yConfig(realm="us1", o11y_api_token="api-token")

    with (
        patch("splunk_ao.otel.SplunkAOConfig.get", return_value=config),
        patch("splunk_ao.otel.O11yConfig.from_env", return_value=crud_only),
        pytest.raises(MissingConfigurationError, match="SPLUNK_AO_O11Y_TOKEN"),
    ):
        SplunkAOOTLPExporter(_exporter_factory=factory)

    assert factory.calls == []


def test_explicit_id_routing_precedes_context_and_environment_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPLUNK_AO_PROJECT", "environment-project")
    monkeypatch.setenv("SPLUNK_AO_LOG_STREAM", "environment-log-stream")
    _project_context.set("context-project")
    _agent_stream_context.set("context-log-stream")
    factory = RecordingExporterFactory()

    exporter = build_exporter(
        DeploymentMode.O11Y, factory, project_id="explicit-project-id", agent_stream_id="explicit-agent-stream-id"
    )

    assert factory.calls[0]["headers"] == {
        "X-SF-Token": "o11y-token",
        "projectid": "explicit-project-id",
        "logstreamid": "explicit-agent-stream-id",
    }
    exporter.shutdown()


def test_exporter_copies_span_without_mutating_source() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(
        DeploymentMode.O11Y, factory, project="authoritative-project", agentstream="authoritative-agent-stream"
    )
    source = make_span()
    source_resource = source.resource
    source_attributes = dict(source.attributes or {})

    assert exporter.export((source,)) == SpanExportResult.SUCCESS

    exported = factory.exporter.spans[0]
    assert exported is not source
    assert source.resource is source_resource
    assert dict(source.attributes or {}) == source_attributes
    assert source.resource.attributes["splunk_ao.project.name"] == "stale-resource-project"
    assert source.attributes["splunk_ao.project.name"] == "stale-span-project"
    assert exported.resource.attributes["splunk_ao.project.name"] == "authoritative-project"
    assert exported.resource.attributes["splunk_ao.logstream.name"] == "authoritative-agent-stream"
    assert "splunk_ao.project.name" not in (exported.attributes or {})
    assert exported.resource.attributes["service.name"] == "checkout"
    exporter.shutdown()


def test_exporter_preserves_every_unaffected_span_field() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.O11Y, factory, project="project")
    source = make_span()

    exporter.export((source,))
    exported = factory.exporter.spans[0]

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
        "instrumentation_scope",
    ):
        assert getattr(exported, field) == getattr(source, field)
    assert exported.resource.schema_url == source.resource.schema_url
    assert exported.attributes["gen_ai.request.model"] == "gpt-4o"
    assert "splunk_ao.request.model" not in exported.attributes
    assert exported.attributes["gen_ai.provider.name"] == "openai"
    assert "splunk_ao.provider.name" not in exported.attributes
    assert exported.attributes["gen_ai.system"] == "legacy-upstream-provider"
    assert exported.attributes["splunk_ao.system"] == "splunk_ao_python"
    assert exported.attributes["custom.attribute"] == "preserved"
    exporter.shutdown()


def test_exporter_does_not_read_deprecated_instrumentation_info() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.O11Y, factory, project="project")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", DeprecationWarning)
        exporter.export((make_span(),))

    assert not any("instrumentation_scope" in str(warning.message) for warning in captured)
    exporter.shutdown()


def test_exporter_delegates_force_flush_and_shutdown() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.O11Y, factory)

    assert exporter.export_health.healthy is None
    assert exporter.export((make_span(),)) == SpanExportResult.SUCCESS
    assert exporter.export_health.healthy is None
    assert exporter.force_flush(1234) is True
    exporter.shutdown()

    assert factory.exporter.force_flush_timeouts == [1234]
    assert factory.exporter.shutdown_calls == 1


def test_processor_forwards_export_health() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.O11Y, factory)
    processor = SplunkAOSpanProcessor(SpanProcessor=RecordingSpanProcessor, _exporter=exporter)

    assert processor.export_health.healthy is None
    exporter.export((make_span(),))
    assert processor.export_health.healthy is None
    processor.shutdown()


def test_processor_does_not_put_routing_on_span_attributes() -> None:
    exporter = RecordingExporter()
    processor = SplunkAOSpanProcessor(SpanProcessor=RecordingSpanProcessor, _exporter=exporter)
    _project_context.set("later-project")
    _agent_stream_context.set("later-log-stream")
    _experiment_id_context.set("later-experiment")
    _session_id_context.set("session-id")
    _dataset_input_context.set("question")
    span = MagicMock()

    processor.on_start(span)

    calls = {args[0]: args[1] for args, _ in span.set_attribute.call_args_list}
    assert not ROUTING_KEYS.intersection(calls)
    assert calls["gen_ai.conversation.id"] == "session-id"
    assert calls["splunk_ao.dataset.input"] == "question"
    processor.shutdown()


def test_processor_reads_inbound_standard_conversation_baggage() -> None:
    exporter = RecordingExporter()
    processor = SplunkAOSpanProcessor(SpanProcessor=RecordingSpanProcessor, _exporter=exporter)
    parent_context = baggage.set_baggage("gen_ai.conversation.id", "inbound-conversation", context.Context())
    span = MagicMock()

    processor.on_start(span, parent_context=parent_context)

    calls = {args[0]: args[1] for args, _ in span.set_attribute.call_args_list}
    assert calls["gen_ai.conversation.id"] == "inbound-conversation"
    assert "splunk_ao.session.id" not in calls
    processor.shutdown()


def test_processor_forwards_complete_routing_to_immutable_exporter() -> None:
    exporter = RecordingExporter()
    exporter_factory = MagicMock()
    with patch("splunk_ao.otel.SplunkAOOTLPExporter", return_value=exporter) as exporter_class:
        processor = SplunkAOSpanProcessor(
            project_id="project-id",
            agent_stream_id="agent-stream-id",
            experiment_id="experiment-id",
            SpanProcessor=RecordingSpanProcessor,
            _exporter_factory=exporter_factory,
        )

    exporter_class.assert_called_once_with(
        project=None,
        project_id="project-id",
        agentstream=None,
        agent_stream_id="agent-stream-id",
        experiment_id="experiment-id",
        _exporter_factory=exporter_factory,
    )
    processor.shutdown()


def test_processor_rejects_prebuilt_exporter_with_otlp_options() -> None:
    with pytest.raises(ValueError, match="Routing and OTLP exporter options cannot be used with _exporter"):
        SplunkAOSpanProcessor(_exporter=RecordingExporter(), timeout=10)


@pytest.mark.parametrize(
    "routing",
    [
        {"project": "project"},
        {"project_id": "project-id"},
        {"agentstream": "agent-stream"},
        {"agent_stream_id": "agent-stream-id"},
        {"experiment_id": "experiment-id"},
    ],
)
def test_processor_rejects_prebuilt_exporter_with_routing(routing: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="Routing and OTLP exporter options cannot be used with _exporter"):
        SplunkAOSpanProcessor(_exporter=RecordingExporter(), **routing)


@pytest.mark.parametrize(
    ("legacy_name", "replacement"), [("logstream", "agentstream"), ("log_stream_id", "agent_stream_id")]
)
def test_exporter_rejects_legacy_routing_options(legacy_name: str, replacement: str) -> None:
    factory = RecordingExporterFactory()

    with pytest.raises(TypeError, match=rf"{legacy_name} is not supported; use {replacement}"):
        build_exporter(DeploymentMode.O11Y, factory, **{legacy_name: "legacy-value"})

    assert factory.calls == []


def test_helper_constructs_registers_and_returns_processor() -> None:
    provider = MagicMock()
    resolved_processor = MagicMock(spec=SplunkAOSpanProcessor)

    with patch("splunk_ao.otel.SplunkAOSpanProcessor", return_value=resolved_processor) as processor_class:
        result = add_splunk_ao_span_processor(provider, project="project")

    processor_class.assert_called_once_with(project="project")
    provider.add_span_processor.assert_called_once_with(resolved_processor)
    assert _TRACE_PROVIDER_CONTEXT_VAR.get() is provider
    assert result is resolved_processor


def test_helper_accepts_prebuilt_processor() -> None:
    provider = MagicMock()
    processor = MagicMock(spec=SplunkAOSpanProcessor)

    assert add_splunk_ao_span_processor(provider, processor) is processor
    provider.add_span_processor.assert_called_once_with(processor)


def test_helper_rejects_prebuilt_processor_and_constructor_kwargs() -> None:
    provider = MagicMock()
    processor = MagicMock(spec=SplunkAOSpanProcessor)

    with pytest.raises(ValueError, match="processor_kwargs"):
        add_splunk_ao_span_processor(provider, processor, project="other")
    provider.add_span_processor.assert_not_called()


def test_processor_construction_does_not_replace_global_provider() -> None:
    global_before = trace.get_tracer_provider()
    processor = SplunkAOSpanProcessor(SpanProcessor=RecordingSpanProcessor, _exporter=RecordingExporter())

    assert trace.get_tracer_provider() is global_before
    processor.shutdown()


def test_sdk_native_otel_span_injects_w3c_context() -> None:
    provider = SDKTracerProvider()
    _TRACE_PROVIDER_CONTEXT_VAR.set(provider)
    try:
        with start_splunk_ao_span(WorkflowSpan(input="request", name="operation")) as span:
            headers = get_tracing_headers()

        parts = headers["traceparent"].split("-")
        assert int(parts[1], 16) == span.get_span_context().trace_id
        assert int(parts[2], 16) == span.get_span_context().span_id
    finally:
        provider.shutdown()


def test_caller_owned_otel_span_injects_w3c_context() -> None:
    provider = SDKTracerProvider()
    tracer = provider.get_tracer("caller-owned")
    try:
        with tracer.start_as_current_span("operation") as span:
            headers = get_tracing_headers()

        parts = headers["traceparent"].split("-")
        assert int(parts[1], 16) == span.get_span_context().trace_id
        assert int(parts[2], 16) == span.get_span_context().span_id
    finally:
        provider.shutdown()


def test_caller_owned_otel_and_path1_logger_interoperate_bidirectionally() -> None:
    exporter = RecordingExporter()
    processor = SplunkAOSpanProcessor(_exporter=exporter)
    provider = SDKTracerProvider()
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("caller-owned")
    sink = MagicMock()
    sink.force_flush.return_value = True
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    try:
        with tracer.start_as_current_span("otel-upstream") as upstream:
            logger.start_trace(input="request")
            operation = logger.add_workflow_span(input="agent work", name="path1-operation")
            operation_context = logger._otel_ids[operation.id].span_context

            with tracer.start_as_current_span("otel-downstream") as downstream:
                headers = get_tracing_headers()

            logger.conclude(output="done")
            logger.conclude(output="complete")

        [path1_span] = [call.args[0] for call in sink.emit.call_args_list]
        assert path1_span.parent == upstream.get_span_context()
        assert path1_span.context == operation_context
        assert downstream.parent == operation_context
        assert headers["traceparent"].split("-")[2] == format(downstream.get_span_context().span_id, "016x")
    finally:
        logger.terminate()
        provider.shutdown()

    by_name = {span.name: span for span in exporter.spans}
    assert by_name["otel-downstream"].parent == operation_context


def test_explicit_conversation_session_is_applied_across_paths_1_2_and_3() -> None:
    exporter = RecordingExporter()
    processor = SplunkAOSpanProcessor(SpanProcessor=RecordingSpanProcessor, _exporter=exporter)
    provider = SDKTracerProvider()
    provider.add_span_processor(processor)
    provider_token = _TRACE_PROVIDER_CONTEXT_VAR.set(provider)
    tracer = provider.get_tracer("caller-owned")
    sink = MagicMock()
    sink.force_flush.return_value = True
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    try:
        logger.set_session("conversation-all-paths")
        logger.start_trace(input="request")
        path1_operation = logger.add_workflow_span(input="path 1", name="path-1")

        with start_splunk_ao_span(WorkflowSpan(input="path 2", name="path-2")):
            pass
        with tracer.start_as_current_span("path-3"):
            pass

        logger.conclude(output="done")
        logger.conclude(output="complete")

        [path1_span] = [call.args[0] for call in sink.emit.call_args_list]
        assert path1_span.name == "invoke_workflow path-1"
        assert path1_span.attributes["gen_ai.conversation.id"] == "conversation-all-paths"
        assert "splunk_ao.session.id" not in path1_span.attributes

        recording_processor = processor.processor
        assert isinstance(recording_processor, RecordingSpanProcessor)
        started = {span.name: span for span, _ in recording_processor.started}
        assert started["path-2"].attributes["gen_ai.conversation.id"] == "conversation-all-paths"
        assert started["path-3"].attributes["gen_ai.conversation.id"] == "conversation-all-paths"
        assert "splunk_ao.session.id" not in started["path-2"].attributes
        assert "splunk_ao.session.id" not in started["path-3"].attributes
        assert path1_operation.id not in logger._otel_ids
    finally:
        logger.clear_session()
        logger.terminate()
        _TRACE_PROVIDER_CONTEXT_VAR.reset(provider_token)
        provider.shutdown()


def test_sdk_native_and_caller_owned_spans_keep_topology_and_queue_without_flush() -> None:
    exporter = RecordingExporter()
    processor = SplunkAOSpanProcessor(_exporter=exporter)
    provider = SDKTracerProvider()
    provider.add_span_processor(processor)
    provider_token = _TRACE_PROVIDER_CONTEXT_VAR.set(provider)
    tracer = provider.get_tracer("caller-owned")
    try:
        assert isinstance(processor.processor, BatchSpanProcessor)
        with (
            patch.object(processor, "on_end", wraps=processor.on_end) as on_end,
            patch.object(processor.processor, "force_flush", wraps=processor.processor.force_flush) as force_flush,
        ):
            operation = WorkflowSpan(input="request", name="sdk-operation")
            with start_splunk_ao_span(operation) as sdk_span:
                with tracer.start_as_current_span("caller-child") as caller_span:
                    pass

            assert on_end.call_count == 2
            force_flush.assert_not_called()
            assert caller_span.parent is not None
            assert caller_span.parent.span_id == sdk_span.get_span_context().span_id
            assert caller_span.get_span_context().trace_id == sdk_span.get_span_context().trace_id
    finally:
        _TRACE_PROVIDER_CONTEXT_VAR.reset(provider_token)
        provider.shutdown()

    by_name = {span.name: span for span in exporter.spans}
    assert set(by_name) == {"sdk-operation", "caller-child"}
    assert by_name["caller-child"].parent == by_name["sdk-operation"].context
