from collections.abc import Sequence
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from splunk_ao.deployment import DeploymentMode, StandaloneConfig
from splunk_ao.otel import SplunkAOOTLPExporter, SplunkAOSpanProcessor, add_splunk_ao_span_processor
from splunk_ao_a2a import _spans
from splunk_ao_a2a._constants import INSTRUMENTOR_NAME, INSTRUMENTOR_VERSION


class RecordingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


def test_a2a_native_span_uses_user_wired_deployment_aware_processor() -> None:
    delegate = RecordingExporter()
    captured_config: dict[str, object] = {}

    def exporter_factory(**kwargs: object) -> RecordingExporter:
        captured_config.update(kwargs)
        return delegate

    config = MagicMock()
    config.resolve_deployment.return_value = DeploymentMode.STANDALONE
    standalone = StandaloneConfig(
        api_key="standalone-key",
        console_url="https://console.example.com",
        api_url="https://api.example.com",
    )

    with (
        patch("splunk_ao.otel.SplunkAOConfig.get", return_value=config),
        patch("splunk_ao.otel.StandaloneConfig.from_env", return_value=standalone),
    ):
        exporter = SplunkAOOTLPExporter(
            project="a2a-project",
            agentstream="a2a-agent-stream",
            _exporter_factory=exporter_factory,
        )
        processor = SplunkAOSpanProcessor(SpanProcessor=SimpleSpanProcessor, _exporter=exporter)
        provider = TracerProvider()
        assert add_splunk_ao_span_processor(provider, processor) is processor
        tracer = provider.get_tracer(INSTRUMENTOR_NAME, INSTRUMENTOR_VERSION)
        try:
            with tracer.start_as_current_span("a2a.client.send_message") as span:
                _spans.set_client_attributes(
                    span,
                    SimpleNamespace(context_id="context-id", task_id="task-id"),
                    "SendMessage",
                    "orchestrator",
                )
        finally:
            provider.shutdown()

    assert captured_config == {
        "endpoint": "https://api.example.com/otel/v1/traces",
        "headers": {
            "Splunk-AO-API-Key": "standalone-key",
            "project": "a2a-project",
            "logstream": "a2a-agent-stream",
        },
    }
    exported = delegate.spans[0]
    assert exported.instrumentation_scope.name == INSTRUMENTOR_NAME
    assert "gen_ai.system" not in exported.attributes
    assert exported.attributes["splunk_ao.system"] == "splunk_ao_python"
    assert exported.attributes["a2a.rpc.method"] == "SendMessage"
    assert "splunk_ao.a2a.rpc.method" not in exported.attributes
    assert exported.attributes["gen_ai.conversation.id"] == "context-id"
    assert exported.attributes["splunk_ao.session.id"] == "context-id"
    assert exported.attributes["gen_ai.operation.name"] == "invoke_agent"
    assert exported.attributes["splunk_ao.operation.name"] == "invoke_agent"
    assert exported.resource.attributes["splunk_ao.project.name"] == "a2a-project"
    assert exported.resource.attributes["splunk_ao.logstream.name"] == "a2a-agent-stream"
    assert "splunk_ao.project.name" not in exported.attributes
