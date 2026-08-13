from collections.abc import Generator

import pytest
from opentelemetry import baggage, context, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, TraceState

from splunk_ao import extract_tracing_context, get_tracing_headers
from splunk_ao.exceptions import SplunkAOLoggerException
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.logger.logger import _otel_context_state
from splunk_ao.session_context import GEN_AI_CONVERSATION_ID, _session_id_context


class RecordingSink:
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def emit(self, span: ReadableSpan) -> None:
        self.spans.append(span)

    def force_flush(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None


@pytest.fixture(autouse=True)
def isolated_context() -> Generator[None, None, None]:
    state_token = _otel_context_state.set(None)
    session_token = _session_id_context.set(None)
    token = context.attach(context.Context())
    try:
        yield
    finally:
        context.detach(token)
        _session_id_context.reset(session_token)
        _otel_context_state.reset(state_token)


def make_logger() -> tuple[SplunkAOLogger, RecordingSink]:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    return logger, sink


def attach_span_context(span_context: SpanContext):
    return context.attach(trace.set_span_in_context(NonRecordingSpan(span_context)))


def test_get_tracing_headers_injects_native_otel_context_into_same_carrier() -> None:
    span_context = SpanContext(
        trace_id=0x4BF92F3577B34DA6A3CE929D0E0E4736,
        span_id=0x00F067AA0BA902B7,
        is_remote=False,
        trace_flags=TraceFlags.SAMPLED,
        trace_state=TraceState([("vendor", "value")]),
    )
    token = attach_span_context(span_context)
    try:
        carrier = {"existing": "header"}
        result = get_tracing_headers(carrier)
    finally:
        context.detach(token)

    assert result is carrier
    assert carrier["existing"] == "header"
    assert carrier["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert carrier["tracestate"] == "vendor=value"


def test_get_tracing_headers_rejects_no_active_operation() -> None:
    with pytest.raises(SplunkAOLoggerException, match="active exportable operation"):
        get_tracing_headers()


def test_get_tracing_headers_rejects_internal_trace_envelope() -> None:
    logger, _ = make_logger()
    try:
        logger.start_trace(input="request")
        with pytest.raises(SplunkAOLoggerException, match="active exportable operation"):
            get_tracing_headers()
        logger.conclude(output="done")
    finally:
        logger.terminate()


def test_get_tracing_headers_uses_real_path1_operation_and_no_routing_headers() -> None:
    logger, _ = make_logger()
    try:
        logger.start_trace(input="request")
        operation = logger.add_workflow_span(input="work", name="operation")
        operation_context = logger._otel_ids[operation.id].span_context

        headers = get_tracing_headers()

        assert headers["traceparent"].split("-")[2] == format(operation_context.span_id, "016x")
        assert set(headers).isdisjoint(
            {"project", "projectid", "logstream", "logstreamid", "experimentid", "X-SF-Token", "Splunk-AO-API-Key"}
        )
        logger.conclude(output="work")
        logger.conclude(output="done")
    finally:
        logger.terminate()


def test_get_tracing_headers_injects_only_standard_conversation_baggage() -> None:
    logger, _ = make_logger()
    try:
        logger.set_session("conversation-123")
        logger.start_trace(input="request")
        logger.add_workflow_span(input="work", name="operation")

        headers = get_tracing_headers()

        extracted = extract_tracing_context(headers)
        assert baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=extracted) == "conversation-123"
        assert "splunk_ao.session.id" not in headers.get("baggage", "")
        assert all(
            private_name not in headers.get("baggage", "")
            for private_name in (
                "project",
                "agent_stream",
                "logstream",
                "experiment",
                "agent_name",
                "workflow_name",
                "model_name",
                "token",
            )
        )
        logger.conclude(output="work")
        logger.conclude(output="done")
    finally:
        logger.terminate()


def test_extract_tracing_context_restores_conversation_baggage() -> None:
    extracted = extract_tracing_context(
        {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "baggage": "gen_ai.conversation.id=conversation-456,unrelated=value",
        }
    )

    assert baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=extracted) == "conversation-456"
    assert baggage.get_baggage("unrelated", context=extracted) == "value"


@pytest.mark.parametrize("header", ["gen_ai.conversation.id=", "gen_ai.conversation.id"])
def test_extract_tracing_context_ignores_malformed_or_empty_conversation_baggage(header: str) -> None:
    extracted = extract_tracing_context(
        {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", "baggage": header}
    )

    assert baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=extracted) is None


def test_local_session_overrides_inbound_conversation_when_injecting() -> None:
    inbound = extract_tracing_context(
        {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "baggage": "gen_ai.conversation.id=inbound-session,unrelated=value",
        }
    )
    token = context.attach(inbound)
    _session_id_context.set("local-session")
    try:
        headers = get_tracing_headers()
    finally:
        context.detach(token)

    extracted = extract_tracing_context(headers)
    assert baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=extracted) == "local-session"
    assert baggage.get_baggage("unrelated", context=extracted) == "value"


def test_inbound_conversation_overrides_compatibility_logger_field_for_path1() -> None:
    remote = extract_tracing_context(
        {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "baggage": "gen_ai.conversation.id=inbound-session",
        }
    )
    token = context.attach(remote)
    logger, sink = make_logger()
    logger.session_id = "stale-logger-session"
    try:
        logger.start_trace(input="request")
        logger.add_workflow_span(input="work", name="operation")
        logger.conclude(output="work")
        logger.conclude(output="done")

        [operation] = sink.spans
        assert operation.attributes[GEN_AI_CONVERSATION_ID] == "inbound-session"
    finally:
        logger.terminate()
        context.detach(token)


def test_extract_tracing_context_is_case_insensitive_and_preserves_tracestate() -> None:
    extracted = extract_tracing_context(
        {"TRACEPARENT": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", "TRACESTATE": "vendor=value"}
    )
    span_context = trace.get_current_span(extracted).get_span_context()

    assert span_context.is_valid
    assert span_context.trace_id == 0x4BF92F3577B34DA6A3CE929D0E0E4736
    assert span_context.span_id == 0x00F067AA0BA902B7
    assert span_context.is_remote
    assert span_context.trace_state.get("vendor") == "value"


@pytest.mark.parametrize("carrier", [{}, {"traceparent": "not-valid"}])
def test_extract_tracing_context_rejects_missing_or_malformed_parent(carrier: dict[str, str]) -> None:
    extracted = extract_tracing_context(carrier)
    assert not trace.get_current_span(extracted).get_span_context().is_valid
