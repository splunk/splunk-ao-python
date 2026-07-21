from collections.abc import Sequence
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link, SpanContext, SpanKind, TraceFlags
from opentelemetry.trace.status import Status, StatusCode

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
from splunk_ao.otel import (
    _TRACE_PROVIDER_CONTEXT_VAR,
    SplunkAOOTLPExporter,
    SplunkAOSpanProcessor,
    add_splunk_ao_span_processor,
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
        _log_stream_context,
        _experiment_id_context,
        _session_id_context,
        _dataset_input_context,
        _dataset_output_context,
        _dataset_metadata_context,
    )
    for context_var in contexts:
        context_var.set(None)
    _TRACE_PROVIDER_CONTEXT_VAR.set(None)
    for name in ("SPLUNK_AO_PROJECT", "SPLUNK_AO_PROJECT_ID", "SPLUNK_AO_LOG_STREAM", "SPLUNK_AO_LOG_STREAM_ID"):
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
    o11y = O11yConfig(realm="us1", sf_token="o11y-token")
    with (
        patch("splunk_ao.otel.SplunkAOConfig.get", return_value=config),
        patch("splunk_ao.otel.StandaloneConfig.from_env", return_value=standalone),
        patch("splunk_ao.otel.O11yConfig.from_env", return_value=o11y),
    ):
        return SplunkAOOTLPExporter(_exporter_factory=factory, **routing)


def test_standalone_exporter_uses_shared_config_and_name_routing() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.STANDALONE, factory, project="payments", logstream="production")

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
        log_stream_id="ignored-log-stream-id",
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
    crud_only = O11yConfig(realm="us1", sf_api_token="api-token")

    with (
        patch("splunk_ao.otel.SplunkAOConfig.get", return_value=config),
        patch("splunk_ao.otel.O11yConfig.from_env", return_value=crud_only),
        pytest.raises(MissingConfigurationError, match="SPLUNK_AO_SF_TOKEN"),
    ):
        SplunkAOOTLPExporter(_exporter_factory=factory)

    assert factory.calls == []


def test_explicit_id_routing_precedes_context_and_environment_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPLUNK_AO_PROJECT", "environment-project")
    monkeypatch.setenv("SPLUNK_AO_LOG_STREAM", "environment-log-stream")
    _project_context.set("context-project")
    _log_stream_context.set("context-log-stream")
    factory = RecordingExporterFactory()

    exporter = build_exporter(
        DeploymentMode.O11Y, factory, project_id="explicit-project-id", log_stream_id="explicit-log-stream-id"
    )

    assert factory.calls[0]["headers"] == {
        "X-SF-Token": "o11y-token",
        "projectid": "explicit-project-id",
        "logstreamid": "explicit-log-stream-id",
    }
    exporter.shutdown()


def test_exporter_copies_span_without_mutating_source() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(
        DeploymentMode.O11Y, factory, project="authoritative-project", logstream="authoritative-log-stream"
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
    assert exported.resource.attributes["splunk_ao.logstream.name"] == "authoritative-log-stream"
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
        "instrumentation_info",
        "status",
        "start_time",
        "end_time",
        "instrumentation_scope",
    ):
        assert getattr(exported, field) == getattr(source, field)
    assert exported.resource.schema_url == source.resource.schema_url
    assert exported.attributes["gen_ai.request.model"] == "gpt-4o"
    assert exported.attributes["gen_ai.provider.name"] == "openai"
    assert exported.attributes["gen_ai.system"] == "legacy-upstream-provider"
    assert exported.attributes["custom.attribute"] == "preserved"
    exporter.shutdown()


def test_exporter_delegates_force_flush_and_shutdown() -> None:
    factory = RecordingExporterFactory()
    exporter = build_exporter(DeploymentMode.O11Y, factory)

    assert exporter.force_flush(1234) is True
    exporter.shutdown()

    assert factory.exporter.force_flush_timeouts == [1234]
    assert factory.exporter.shutdown_calls == 1


def test_processor_does_not_put_routing_on_span_attributes() -> None:
    exporter = RecordingExporter()
    processor = SplunkAOSpanProcessor(
        project="project", logstream="log-stream", SpanProcessor=RecordingSpanProcessor, _exporter=exporter
    )
    _project_context.set("later-project")
    _log_stream_context.set("later-log-stream")
    _experiment_id_context.set("later-experiment")
    _session_id_context.set("session-id")
    _dataset_input_context.set("question")
    span = MagicMock()

    processor.on_start(span)

    calls = {args[0]: args[1] for args, _ in span.set_attribute.call_args_list}
    assert not ROUTING_KEYS.intersection(calls)
    assert calls["splunk_ao.session.id"] == "session-id"
    assert calls["splunk_ao.dataset.input"] == "question"
    processor.shutdown()


def test_processor_forwards_complete_routing_to_immutable_exporter() -> None:
    exporter = RecordingExporter()
    exporter_factory = MagicMock()
    with patch("splunk_ao.otel.SplunkAOOTLPExporter", return_value=exporter) as exporter_class:
        processor = SplunkAOSpanProcessor(
            project_id="project-id",
            log_stream_id="log-stream-id",
            experiment_id="experiment-id",
            SpanProcessor=RecordingSpanProcessor,
            _exporter_factory=exporter_factory,
        )

    exporter_class.assert_called_once_with(
        project=None,
        project_id="project-id",
        logstream=None,
        log_stream_id="log-stream-id",
        experiment_id="experiment-id",
        _exporter_factory=exporter_factory,
    )
    processor.shutdown()


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
