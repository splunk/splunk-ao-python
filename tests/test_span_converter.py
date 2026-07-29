from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, SpanKind, StatusCode, TraceFlags, TraceState

from galileo_core.schemas.logging.span import AgentSpan, LlmSpan, RetrieverSpan, ToolSpan, WorkflowSpan
from galileo_core.schemas.logging.step import BaseStep, Metrics, StepType
from galileo_core.schemas.logging.trace import Trace
from galileo_core.schemas.shared.document import Document
from splunk_ao.converter import SpanConverter, span_converter
from splunk_ao.converter.attribute_mapping import build_span_attributes
from splunk_ao.logger.control import ControlResult, ControlSpan
from splunk_ao.utils.headers_data import get_package_version

TRACE_ID = 0x1234567890ABCDEF1234567890ABCDEF
SPAN_ID = 0x1234567890ABCDEF
PARENT_SPAN_ID = 0xFEDCBA0987654321
CREATED_AT = datetime(2025, 1, 1, tzinfo=UTC)


def make_context(
    *,
    trace_id: int = TRACE_ID,
    span_id: int = SPAN_ID,
    is_remote: bool = False,
    trace_flags: TraceFlags = TraceFlags(TraceFlags.SAMPLED),
    trace_state: TraceState | None = None,
) -> SpanContext:
    return SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=is_remote,
        trace_flags=trace_flags,
        trace_state=trace_state or TraceState(),
    )


def convert(
    span: BaseStep,
    *,
    span_context: SpanContext | None = None,
    parent_span_context: SpanContext | None = None,
    resource: Resource | None = None,
    session_id: str | None = "session-1",
    end_time_ns: int | None = None,
) -> ReadableSpan:
    return SpanConverter().convert_span(
        span,
        span_context=span_context or make_context(),
        parent_span_context=parent_span_context,
        session_id=session_id,
        resource=resource or Resource.create({}),
        end_time_ns=end_time_ns,
    )


def supported_spans() -> list[tuple[BaseStep, str, SpanKind]]:
    return [
        (LlmSpan(input="prompt", output="answer", model="gpt-5", created_at=CREATED_AT), "chat gpt-5", SpanKind.CLIENT),
        (
            ToolSpan(name="search", input='{"q":"otel"}', output="result", created_at=CREATED_AT),
            "execute_tool search",
            SpanKind.INTERNAL,
        ),
        (
            RetrieverSpan(
                name="knowledge-base", input="query", output=[Document(content="result")], created_at=CREATED_AT
            ),
            "retrieval knowledge-base",
            SpanKind.INTERNAL,
        ),
        (
            WorkflowSpan(name="research", input="question", output="answer", created_at=CREATED_AT),
            "invoke_workflow research",
            SpanKind.INTERNAL,
        ),
        (
            AgentSpan(name="planner", input="request", output="plan", created_at=CREATED_AT),
            "invoke_agent planner",
            SpanKind.INTERNAL,
        ),
        (
            ControlSpan(
                name="guardrail",
                input='{"text":"request"}',
                output=ControlResult(action="observe", matched=True),
                created_at=CREATED_AT,
            ),
            "guardrail",
            SpanKind.INTERNAL,
        ),
    ]


@pytest.mark.parametrize(("span", "expected_name", "expected_kind"), supported_spans())
def test_supported_span_types_use_canonical_names_and_kinds(
    span: BaseStep, expected_name: str, expected_kind: SpanKind
) -> None:
    result = convert(span)

    assert isinstance(result, ReadableSpan)
    assert result.name == expected_name
    assert result.kind is expected_kind
    assert dict(result.attributes or {}) == build_span_attributes(span, "session-1")


@pytest.mark.parametrize(
    ("span", "expected_name"),
    [
        (LlmSpan(input="prompt", output="answer", model=None), "chat"),
        (ToolSpan(name="", input="input"), "execute_tool"),
        (RetrieverSpan(name="", input="query", output=[]), "retrieval"),
        (WorkflowSpan(name="", input="input"), "invoke_workflow"),
        (AgentSpan(name="", input="input"), "invoke_agent"),
    ],
)
def test_missing_optional_name_parts_do_not_leave_whitespace(span: BaseStep, expected_name: str) -> None:
    assert convert(span).name == expected_name


@pytest.mark.parametrize(
    "span", [BaseStep(type=StepType.session), ToolSpan(name="tool").model_copy(update={"type": "unknown"})]
)
def test_unsupported_step_types_fail_clearly(span: BaseStep) -> None:
    with pytest.raises(TypeError, match="Unsupported step type"):
        convert(span)


def test_trace_envelope_is_not_convertible() -> None:
    with pytest.raises(TypeError, match="LoggedTrace is a trace envelope"):
        convert(Trace(name="root", input="question"))


def test_converter_calls_shared_attribute_builder_once(monkeypatch: pytest.MonkeyPatch) -> None:
    source = ToolSpan(name="search", input="query")
    expected = {"gen_ai.operation.name": "execute_tool", "custom": "value"}
    calls: list[tuple[BaseStep, str | None]] = []

    def build(source_span: BaseStep, session_id: str | None = None) -> dict[str, Any]:
        calls.append((source_span, session_id))
        return expected

    monkeypatch.setattr(span_converter, "build_span_attributes", build)

    result = convert(source, session_id="conversation-1")

    assert calls == [(source, "conversation-1")]
    assert result.attributes == expected


def test_converter_leaves_final_export_normalization_to_the_sink() -> None:
    result = convert(LlmSpan(input="prompt", output="answer", model="gpt-5"))
    attributes = result.attributes or {}

    assert "gen_ai.input.messages" in attributes
    assert "gen_ai.output.messages" in attributes
    assert "splunk_ao.input.messages" not in attributes
    assert "splunk_ao.output.messages" not in attributes
    assert "splunk_ao.system" not in attributes


def test_resource_routing_is_preserved_without_becoming_a_span_attribute() -> None:
    resource = Resource.create(
        {"service.name": "travel-agent", "splunk_ao.project.name": "project", "splunk_ao.agentstream.name": "log-stream"}
    )

    result = convert(ToolSpan(name="search"), resource=resource)

    assert result.resource is resource
    assert result.resource.attributes["splunk_ao.project.name"] == "project"
    assert "splunk_ao.project.name" not in (result.attributes or {})
    assert "splunk_ao.agentstream.name" not in (result.attributes or {})


def test_context_parent_flags_and_trace_state_are_preserved() -> None:
    trace_state = TraceState([("vendor", "state")])
    span_context = make_context(trace_flags=TraceFlags(0), trace_state=trace_state)
    parent_context = make_context(span_id=PARENT_SPAN_ID, is_remote=True, trace_state=trace_state)

    result = convert(
        LlmSpan(input="prompt", output="answer"), span_context=span_context, parent_span_context=parent_context
    )

    assert result.context is span_context
    assert result.parent is parent_context
    assert result.context.trace_id == parent_context.trace_id == TRACE_ID
    assert result.context.span_id == SPAN_ID
    assert result.parent.span_id == PARENT_SPAN_ID
    assert result.context.trace_flags == TraceFlags(0)
    assert result.context.trace_state is trace_state
    assert result.parent.is_remote is True


def test_root_span_has_no_parent() -> None:
    assert convert(LlmSpan(input="question")).parent is None


def test_deep_parent_chain_uses_only_preassigned_contexts() -> None:
    workflow_context = make_context(span_id=0x1111111111111111)
    agent_context = make_context(span_id=0x2222222222222222)
    llm_context = make_context(span_id=0x3333333333333333)

    workflow = convert(WorkflowSpan(name="workflow"), span_context=workflow_context)
    agent = convert(AgentSpan(name="agent"), span_context=agent_context, parent_span_context=workflow_context)
    llm = convert(LlmSpan(model="model"), span_context=llm_context, parent_span_context=agent_context)

    assert workflow.context is workflow_context
    assert workflow.parent is None
    assert agent.parent is workflow_context
    assert llm.parent is agent_context
    assert workflow.context.trace_id == agent.context.trace_id == llm.context.trace_id == TRACE_ID


@pytest.mark.parametrize(
    ("created_at", "expected_start_ns"),
    [
        (datetime(2025, 1, 1, 0, 0, 0, 123456, tzinfo=UTC), 1_735_689_600_123_456_000),
        (datetime(2025, 1, 1, 0, 0, 0, 123456), 1_735_689_600_123_456_000),
    ],
)
def test_created_at_converts_to_exact_unix_nanoseconds(created_at: datetime, expected_start_ns: int) -> None:
    result = convert(ToolSpan(name="tool", created_at=created_at), end_time_ns=expected_start_ns + 1)

    assert result.start_time == expected_start_ns


def test_duration_takes_precedence_over_explicit_end_time_including_zero() -> None:
    start_ns = 1_735_689_600_000_000_000
    with_duration = ToolSpan(name="tool", created_at=CREATED_AT, metrics=Metrics(duration_ns=25))
    with_zero_duration = ToolSpan(name="tool", created_at=CREATED_AT, metrics=Metrics(duration_ns=0))

    assert convert(with_duration, end_time_ns=start_ns + 100).end_time == start_ns + 25
    assert convert(with_zero_duration, end_time_ns=start_ns + 100).end_time == start_ns


def test_explicit_end_time_precedes_wall_clock() -> None:
    assert convert(ToolSpan(name="tool", created_at=CREATED_AT), end_time_ns=1234).end_time == 1234


def test_end_time_falls_back_to_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(span_converter.time, "time_ns", lambda: 9876)

    assert convert(ToolSpan(name="tool", created_at=CREATED_AT)).end_time == 9876


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (None, StatusCode.UNSET),
        (200, StatusCode.UNSET),
        (399, StatusCode.UNSET),
        (400, StatusCode.ERROR),
        (500, StatusCode.ERROR),
    ],
)
def test_status_code_maps_to_otel_status(status_code: int | None, expected: StatusCode) -> None:
    result = convert(ToolSpan(name="tool", status_code=status_code))

    assert result.status.status_code is expected
    assert result.status.description is None


def test_error_output_is_not_inferred_as_status_description() -> None:
    result = convert(ToolSpan(name="tool", output="Error: tool failed", status_code=500))

    assert result.status.status_code is StatusCode.ERROR
    assert result.status.description is None


def test_readable_span_has_empty_events_links_and_versioned_scope() -> None:
    result = convert(LlmSpan(input="prompt", output="answer", events=[{"type": "reasoning"}]))

    assert result.events == ()
    assert result.links == ()
    assert result.instrumentation_scope.name == "splunk_ao"
    assert result.instrumentation_scope.version == get_package_version()


def test_dynamic_scorer_results_are_not_emitted() -> None:
    source = LlmSpan(input="prompt", output="answer")
    source.metrics.__dict__.update({"factuality": 0.9, "factuality_status": "passed"})

    attributes = convert(source).attributes or {}

    assert "factuality" not in attributes
    assert "factuality_status" not in attributes
