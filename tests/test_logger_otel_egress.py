import asyncio
import json
from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from opentelemetry import context, propagate, trace
from opentelemetry.sdk.trace import ReadableSpan

from splunk_ao import log, splunk_ao_context
from splunk_ao.deployment import DeploymentMode
from splunk_ao.exceptions import SplunkAOLoggerException
from splunk_ao.exporter.span_transform import copy_span_for_export
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.openai import _wrap
from splunk_ao.openai.models import OpenAiModuleDefinition
from splunk_ao.shared.exceptions import MissingConfigurationError
from splunk_ao.utils.singleton import SplunkAOLoggerSingleton


class RecordingSink:
    def __init__(self, *, force_flush_result: bool = True, force_flush_error: Exception | None = None) -> None:
        self.spans: list[ReadableSpan] = []
        self.force_flush_result = force_flush_result
        self.force_flush_error = force_flush_error
        self.force_flush_calls = 0
        self.shutdown_calls = 0

    def emit(self, span: ReadableSpan) -> None:
        self.spans.append(span)

    def force_flush(self) -> bool:
        self.force_flush_calls += 1
        if self.force_flush_error is not None:
            raise self.force_flush_error
        return self.force_flush_result

    def shutdown(self) -> None:
        self.shutdown_calls += 1


@pytest.fixture
def recording_sink() -> RecordingSink:
    return RecordingSink()


@pytest.fixture
def otlp_logger(recording_sink: RecordingSink) -> Generator[SplunkAOLogger, None, None]:
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", _sink=recording_sink)
    yield logger
    logger.terminate()


def operation_names(spans: list[ReadableSpan]) -> list[str | None]:
    return [(span.attributes or {}).get("gen_ai.operation.name") for span in spans]


def configure_o11y(monkeypatch: pytest.MonkeyPatch, *, ingest_token: bool = True) -> None:
    for name in ("SPLUNK_AO_API_KEY", "SPLUNK_AO_CONSOLE_URL", "SPLUNK_AO_API_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SPLUNK_AO_REALM", "us1")
    monkeypatch.setenv("SPLUNK_AO_O11Y_API_TOKEN", "api-token")
    if ingest_token:
        monkeypatch.setenv("SPLUNK_AO_O11Y_TOKEN", "ingest-token")
    else:
        monkeypatch.delenv("SPLUNK_AO_O11Y_TOKEN", raising=False)


def test_complete_leaf_is_enqueued_before_flush(otlp_logger: SplunkAOLogger, recording_sink: RecordingSink) -> None:
    root = otlp_logger.start_trace(input="question")
    envelope_context = otlp_logger._otel_ids[root.id].span_context
    leaf = otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5")

    assert operation_names(recording_sink.spans) == ["chat"]
    assert recording_sink.spans[0].parent is None
    assert recording_sink.spans[0].context != envelope_context
    assert leaf.id not in otlp_logger._otel_ids
    assert root.id in otlp_logger._otel_ids
    assert recording_sink.force_flush_calls == 0


def test_path1_session_is_captured_when_stable_span_identity_is_assigned(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink
) -> None:
    otlp_logger.set_session("conversation-at-start")
    otlp_logger.start_trace(input="question")
    otlp_logger.add_workflow_span(input="work", name="workflow")

    otlp_logger.set_session("conversation-changed-later")
    otlp_logger.conclude(output="done")
    otlp_logger.conclude(output="trace done")

    [workflow_span] = recording_sink.spans
    assert workflow_span.attributes["gen_ai.conversation.id"] == "conversation-at-start"
    assert "splunk_ao.session.id" not in workflow_span.attributes
    otlp_logger.clear_session()


def test_single_llm_trace_emits_only_real_child(otlp_logger: SplunkAOLogger, recording_sink: RecordingSink) -> None:
    otlp_logger.add_single_llm_span_trace(input="question", output="answer", model="gpt-5")

    [llm_span] = recording_sink.spans
    assert operation_names(recording_sink.spans) == ["chat"]
    assert llm_span.context is not None
    assert llm_span.parent is None
    assert otlp_logger._otel_ids == {}
    assert otlp_logger.traces == []


@pytest.mark.parametrize("nested", [False, True])
def test_agent_inherits_last_llm_output_and_finish_reason(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink, nested: bool
) -> None:
    # Given: a manual agent with a completed LLM child
    otlp_logger.start_trace(input="question")
    otlp_logger.add_agent_span(input="question", name="agent")
    if nested:
        otlp_logger.add_workflow_span(input="question", name="nested")
    otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5", finish_reason="stop")

    # When: parents conclude without explicit outputs
    otlp_logger.conclude(conclude_all=True)

    # Then: both the LLM and enclosing operations preserve the answer and its reason
    for span in recording_sink.spans:
        output = json.loads(span.attributes["gen_ai.output.messages"])
        assert output[0]["parts"] == [{"type": "text", "content": "answer"}]
        assert output[0]["finish_reason"] == "stop"
    assert recording_sink.spans[0].attributes["gen_ai.response.finish_reasons"] == ("stop",)


@pytest.mark.parametrize("output", ["", "Different answer"])
def test_agent_explicit_output_does_not_inherit_child_finish_reason(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink, output: str
) -> None:
    # Given: an LLM answer with a known finish reason
    otlp_logger.start_trace(input="question")
    otlp_logger.add_agent_span(input="question", name="agent")
    otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5", finish_reason="stop")

    # When: the agent concludes with a different explicit output
    otlp_logger.conclude(output=output)
    otlp_logger.conclude()

    # Then: the output is preserved and the child's reason is not assigned to it
    agent_output = json.loads(recording_sink.spans[-1].attributes["gen_ai.output.messages"])
    assert agent_output[0]["parts"] == [{"type": "text", "content": output}]
    assert agent_output[0]["finish_reason"] == "unknown"


def test_single_llm_trace_preserves_finish_reason(otlp_logger: SplunkAOLogger, recording_sink: RecordingSink) -> None:
    # Given/When: a single completed LLM trace with a provider finish reason
    otlp_logger.add_single_llm_span_trace(input="question", output="answer", model="gpt-5", finish_reason="length")

    # Then: the provider's reason is present in the exported message and attribute
    [span] = recording_sink.spans
    assert span.attributes["gen_ai.response.finish_reasons"] == ("length",)
    assert json.loads(span.attributes["gen_ai.output.messages"])[0]["finish_reason"] == "length"


@pytest.mark.parametrize("return_answer", [False, True])
def test_openai_answer_and_finish_reason_reach_decorated_agent(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink, create_chat_completion, return_answer: bool
) -> None:
    # Given: an instrumented OpenAI completion with a provider finish reason
    definition = OpenAiModuleDefinition(
        module="openai.resources.chat.completions", object="Completions", method="create", type="chat", sync=True
    )
    wrapped = _wrap(definition, lambda: otlp_logger)

    @log(span_type="agent")
    def agent() -> str | None:
        response = wrapped(
            Mock(return_value=create_chat_completion),
            None,
            (),
            {"messages": [{"role": "user", "content": "question"}], "model": "gpt-5"},
        )
        answer = response.choices[0].message.content
        print(answer)
        return answer if return_answer else None

    # When: the agent prints the answer, optionally returning it as well
    with patch.object(splunk_ao_context, "get_logger_instance", return_value=otlp_logger):
        assert agent() == (create_chat_completion.choices[0].message.content if return_answer else None)

    # Then: the parent and child have identical output and the provider's finish reason
    llm, parent = recording_sink.spans
    assert parent.attributes["gen_ai.output.messages"] == llm.attributes["gen_ai.output.messages"]
    assert json.loads(parent.attributes["gen_ai.output.messages"])[0]["finish_reason"] == "stop"


def test_llm_span_per_modality_tokens_reach_exported_attributes(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink
) -> None:
    # Given: an LLM span logged with an image/audio breakdown of its token counts
    otlp_logger.start_trace(input="question")
    otlp_logger.add_llm_span(
        input="prompt",
        output="answer",
        model="gemini-2.5-flash",
        num_input_tokens=120,
        num_output_tokens=40,
        image_input_tokens=5,
        audio_input_tokens=100,
        audio_output_tokens=20,
        image_output_tokens=0,
    )

    # When: the completed span is copied for export
    exported = copy_span_for_export(recording_sink.spans[0], normalize_attributes=True)

    # Then: every modality count is on the wire under its token-details attribute
    attributes = exported.attributes or {}
    assert attributes["gen_ai.usage.image.input_tokens"] == 5
    assert attributes["gen_ai.usage.audio.input_tokens"] == 100
    assert attributes["gen_ai.usage.audio.output_tokens"] == 20
    assert attributes["gen_ai.usage.image.output_tokens"] == 0


@pytest.mark.parametrize(("leaf_kind", "leaf_operation"), [("tool", "execute_tool"), ("retriever", "retrieval")])
def test_pending_leaf_emits_when_trace_envelope_is_released(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink, leaf_kind: str, leaf_operation: str
) -> None:
    otlp_logger.start_trace(input="question")
    if leaf_kind == "tool":
        leaf = otlp_logger.add_tool_span(input="args", output="result", name="search")
    else:
        leaf = otlp_logger.add_retriever_span(input="query", output=["document"], name="search")
    otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5")

    assert operation_names(recording_sink.spans) == ["chat"]
    assert leaf.id in otlp_logger._pending_otel_steps

    otlp_logger.conclude(output="answer")

    assert operation_names(recording_sink.spans) == ["chat", leaf_operation]
    assert all(span.parent is None for span in recording_sink.spans)
    assert otlp_logger._otel_ids == {}


def test_promoted_tool_emits_after_child_and_before_root(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink
) -> None:
    root = otlp_logger.start_trace(input="question")
    tool = otlp_logger.add_tool_span(input="args", output="result", name="search")
    tool._parent = root
    otlp_logger._set_current_parent(tool)
    otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5")

    otlp_logger.conclude(output="result")
    otlp_logger.conclude(output="answer")

    llm_span, tool_span = recording_sink.spans
    assert operation_names(recording_sink.spans) == ["chat", "execute_tool"]
    assert llm_span.parent == tool_span.context
    assert tool_span.parent is None


def test_conclude_all_emits_each_open_parent_once(otlp_logger: SplunkAOLogger, recording_sink: RecordingSink) -> None:
    root = otlp_logger.start_trace(input="question")
    envelope_context = otlp_logger._otel_ids[root.id].span_context
    otlp_logger.add_workflow_span(input="workflow")
    otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5")

    otlp_logger.conclude(output="done", conclude_all=True)

    llm_span, workflow_span = recording_sink.spans
    assert operation_names(recording_sink.spans) == ["chat", "invoke_workflow"]
    assert llm_span.parent == workflow_span.context
    assert workflow_span.parent is None
    assert all(span.context != envelope_context and span.parent != envelope_context for span in recording_sink.spans)
    assert otlp_logger._otel_ids == {}


def test_top_level_span_inherits_external_upstream_parent(recording_sink: RecordingSink) -> None:
    remote_context = propagate.extract({"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"})
    upstream_context = trace.get_current_span(remote_context).get_span_context()
    token = context.attach(remote_context)
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", _sink=recording_sink)
    try:
        root = logger.start_trace(input="question")
        envelope_context = logger._otel_ids[root.id].span_context
        logger.add_llm_span(input="prompt", output="answer", model="gpt-5")
        logger.conclude(output="answer")

        [llm_span] = recording_sink.spans
        assert llm_span.context is not None
        assert llm_span.context.trace_id == upstream_context.trace_id
        assert llm_span.parent == upstream_context
        assert llm_span.parent != envelope_context
    finally:
        logger.terminate()
        context.detach(token)


def test_final_normalization_preserves_non_empty_schema_valid_content(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink
) -> None:
    otlp_logger.start_trace(input="question")
    otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5")

    source_attributes = recording_sink.spans[0].attributes or {}
    source_output_messages = json.loads(source_attributes["gen_ai.output.messages"])
    expected_output_messages = [
        {"finish_reason": "unknown", "parts": [{"content": "answer", "type": "text"}], "role": "assistant"}
    ]
    assert source_output_messages == expected_output_messages

    passthrough = copy_span_for_export(recording_sink.spans[0], normalize_attributes=False)
    passthrough_attributes = passthrough.attributes or {}
    assert json.loads(passthrough_attributes["gen_ai.output.messages"]) == expected_output_messages
    assert "splunk_ao.output.messages" not in passthrough_attributes

    exported = copy_span_for_export(recording_sink.spans[0], normalize_attributes=True)
    attributes = exported.attributes or {}
    output_messages = json.loads(attributes["splunk_ao.output.messages"])

    assert "gen_ai.output.messages" not in attributes
    assert output_messages == expected_output_messages


def test_conversion_failure_releases_leaf_and_restores_parent(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink
) -> None:
    root = otlp_logger.start_trace(input="question")
    root_ids = otlp_logger._otel_ids[root.id]

    with patch.object(otlp_logger._converter, "convert_span", side_effect=RuntimeError("boom")):
        leaf = otlp_logger.add_llm_span(input="prompt", output="answer", model="gpt-5")

    assert leaf is not None
    assert leaf.id not in otlp_logger._otel_ids
    assert root.id in otlp_logger._otel_ids
    assert trace.get_current_span().get_span_context() == root_ids.span_context
    assert recording_sink.spans == []


def test_flush_only_drains_and_does_not_complete_open_trace(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink
) -> None:
    root = otlp_logger.start_trace(input="unfinished")

    assert otlp_logger.flush() is None

    assert recording_sink.force_flush_calls == 1
    assert recording_sink.spans == []
    assert root.id in otlp_logger._otel_ids
    assert otlp_logger.current_parent() is root


@pytest.mark.asyncio
async def test_async_flush_offloads_force_flush(
    otlp_logger: SplunkAOLogger, recording_sink: RecordingSink, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []

    async def tracking_to_thread(func):
        calls.append(func)
        return func()

    monkeypatch.setattr(asyncio, "to_thread", tracking_to_thread)

    assert await otlp_logger.async_flush() is None
    assert calls == [recording_sink.force_flush]


def test_flush_does_not_use_session_crud_client(otlp_logger: SplunkAOLogger, recording_sink: RecordingSink) -> None:
    crud_client = otlp_logger._traces_client
    assert crud_client is not None
    crud_client.ingest_traces = Mock()
    crud_client.ingest_spans = Mock()
    crud_client.update_trace = Mock()
    crud_client.update_span = Mock()

    otlp_logger.start_trace(input="question")
    otlp_logger.conclude(output="answer")
    otlp_logger.flush()

    crud_client.ingest_traces.assert_not_called()
    crud_client.ingest_spans.assert_not_called()
    crud_client.update_trace.assert_not_called()
    crud_client.update_span.assert_not_called()
    assert recording_sink.force_flush_calls == 1


def test_terminate_drains_shuts_down_once_and_discards_unfinished_context() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", _sink=sink)
    logger.start_trace(input="unfinished")

    logger.terminate()
    logger.terminate()

    assert sink.spans == []
    assert sink.force_flush_calls == 1
    assert sink.shutdown_calls == 1
    assert logger._otel_ids == {}
    assert logger.current_parent() is None
    assert not trace.get_current_span().get_span_context().is_valid


def test_terminate_still_shuts_down_when_drain_raises() -> None:
    sink = RecordingSink(force_flush_error=RuntimeError("drain failed"))
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", _sink=sink)

    logger.terminate()

    assert sink.force_flush_calls == 1
    assert sink.shutdown_calls == 1


def test_logger_does_not_replace_global_tracer_provider(recording_sink: RecordingSink) -> None:
    provider = trace.get_tracer_provider()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="log-stream-id", _sink=recording_sink)

    assert trace.get_tracer_provider() is provider
    logger.terminate()


def test_o11y_names_build_routing_without_eager_lookup(
    monkeypatch: pytest.MonkeyPatch, recording_sink: RecordingSink
) -> None:
    configure_o11y(monkeypatch)
    monkeypatch.setenv("OTEL_SERVICE_NAME", "travel-planner")

    with (
        patch.object(SplunkAOLogger, "_init_project") as init_project,
        patch.object(SplunkAOLogger, "_init_agent_stream") as init_log_stream,
    ):
        logger = SplunkAOLogger(project="project", agent_stream="stream", _sink=recording_sink)

    assert logger._deployment == DeploymentMode.O11Y
    assert logger._traces_client is None
    assert logger._resource.attributes["service.name"] == "travel-planner"
    assert logger._resource.attributes["splunk_ao.project.name"] == "project"
    assert logger._resource.attributes["splunk_ao.logstream.name"] == "stream"
    init_project.assert_not_called()
    init_log_stream.assert_not_called()
    logger.terminate()


def test_o11y_ids_construct_session_client_without_lookup(
    monkeypatch: pytest.MonkeyPatch, recording_sink: RecordingSink
) -> None:
    configure_o11y(monkeypatch)

    with (
        patch.object(SplunkAOLogger, "_init_project") as init_project,
        patch.object(SplunkAOLogger, "_init_agent_stream") as init_log_stream,
    ):
        logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=recording_sink)

    assert logger._traces_client is not None
    init_project.assert_not_called()
    init_log_stream.assert_not_called()
    logger.terminate()


def test_o11y_name_session_client_is_resolved_lazily(
    monkeypatch: pytest.MonkeyPatch, recording_sink: RecordingSink
) -> None:
    configure_o11y(monkeypatch)
    logger = SplunkAOLogger(project="project", agent_stream="stream", _sink=recording_sink)
    session_client = MagicMock()

    def resolve_project() -> None:
        logger.project_id = "project-id"

    def resolve_log_stream() -> None:
        logger.agent_stream_id = "stream-id"

    with (
        patch.object(logger, "_init_project", side_effect=resolve_project) as init_project,
        patch.object(logger, "_init_agent_stream", side_effect=resolve_log_stream) as init_log_stream,
        patch.object(logger, "_create_traces_client", return_value=session_client),
    ):
        assert logger._ensure_session_crud_client() is session_client
        assert logger._ensure_session_crud_client() is session_client

    init_project.assert_called_once()
    init_log_stream.assert_called_once()
    logger.terminate()


def test_o11y_no_routing_exports_but_explicit_session_fails(
    monkeypatch: pytest.MonkeyPatch, recording_sink: RecordingSink
) -> None:
    configure_o11y(monkeypatch)
    for name in ("SPLUNK_AO_PROJECT", "SPLUNK_AO_PROJECT_ID", "SPLUNK_AO_LOG_STREAM", "SPLUNK_AO_LOG_STREAM_ID"):
        monkeypatch.delenv(name, raising=False)
    logger = SplunkAOLogger(_sink=recording_sink)

    logger.start_trace(input="question")
    logger.add_llm_span(input="prompt", output="answer", model="gpt-5")
    logger.conclude(output="answer")

    assert len(recording_sink.spans) == 1
    assert recording_sink.spans[0].parent is None
    assert logger._resource.attributes.get("splunk_ao.project.name") is None
    with pytest.raises(SplunkAOLoggerException, match=r"project.*agent stream or experiment"):
        logger.start_session(name="session")
    assert logger._traces_client is None
    logger.terminate()


def test_o11y_crud_only_token_cannot_construct_telemetry_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_o11y(monkeypatch, ingest_token=False)

    with pytest.raises(MissingConfigurationError, match="SPLUNK_AO_O11Y_TOKEN"):
        SplunkAOLogger(project="project", agent_stream="stream")


def test_singleton_keeps_id_routes_distinct_and_resets_one(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_o11y(monkeypatch)
    singleton = SplunkAOLoggerSingleton()
    first = singleton.get(project_id="project-1", agent_stream_id="stream")
    second = singleton.get(project_id="project-2", agent_stream_id="stream")

    assert first is singleton.get(project_id="project-1", agent_stream_id="stream")
    assert first is not second

    singleton.reset(project_id="project-1", agent_stream_id="stream")

    assert first._terminated
    assert not second._terminated
    assert list(singleton.get_all_loggers().values()) == [second]


def test_singleton_reset_matches_ingestion_hook_logger() -> None:
    singleton = SplunkAOLoggerSingleton()
    logger = singleton.get(project="project", agent_stream="stream", ingestion_hook=lambda _: None)

    singleton.reset(project="project", agent_stream="stream")

    assert logger._terminated
    assert singleton.get_all_loggers() == {}
