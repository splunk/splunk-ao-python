"""Convert completed Galileo spans to OpenTelemetry spans."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import SpanContext, SpanKind, Status, StatusCode

from galileo_core.schemas.logging.step import BaseStep, StepType
from splunk_ao.converter.attribute_mapping import build_span_attributes
from splunk_ao.utils.headers_data import get_package_version

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_INSTRUMENTATION_SCOPE = InstrumentationScope(name="splunk_ao", version=get_package_version())

_NAME_PARTS: dict[StepType, tuple[str, str]] = {
    StepType.llm: ("chat", "model"),
    StepType.tool: ("execute_tool", "name"),
    StepType.retriever: ("retrieval", "name"),
    StepType.workflow: ("invoke_workflow", "name"),
    StepType.agent: ("invoke_agent", "name"),
    StepType.control: ("", "name"),
}

_KIND_BY_STEP_TYPE = {
    step_type: SpanKind.CLIENT if step_type is StepType.llm else SpanKind.INTERNAL for step_type in _NAME_PARTS
}


def _step_type(span: BaseStep) -> StepType:
    raw_type = getattr(span, "type", None)
    try:
        step_type = StepType(raw_type)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"Unsupported step type: {raw_type}") from exc

    if step_type is StepType.trace:
        raise TypeError("LoggedTrace is a trace envelope and cannot be converted")
    if step_type not in _NAME_PARTS:
        raise TypeError(f"Unsupported step type: {step_type.value}")
    return step_type


def _span_name(span: BaseStep, step_type: StepType) -> str:
    prefix, field_name = _NAME_PARTS[step_type]
    detail = getattr(span, field_name, None)
    return " ".join(part for part in (prefix, str(detail).strip() if detail is not None else "") if part)


def _to_unix_ns(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    delta = value.astimezone(UTC) - _EPOCH
    return ((delta.days * 86_400 + delta.seconds) * 1_000_000_000) + delta.microseconds * 1_000


def _span_status(span: BaseStep) -> Status:
    status_code = span.status_code
    if status_code is None or status_code < 400:
        return Status(StatusCode.UNSET)
    return Status(StatusCode.ERROR)


def _end_time_ns(span: BaseStep, start_time_ns: int, end_time_ns: int | None) -> int:
    duration_ns = span.metrics.duration_ns
    if duration_ns is not None:
        return start_time_ns + duration_ns
    if end_time_ns is not None:
        return end_time_ns
    return time.time_ns()


class SpanConverter:
    """Convert one completed Galileo span into an OTel readable span."""

    def convert_span(
        self,
        span: BaseStep,
        span_context: SpanContext,
        parent_span_context: SpanContext | None,
        session_id: str | None,
        resource: Resource,
        end_time_ns: int | None = None,
    ) -> ReadableSpan:
        """Build a readable span using the supplied identity and resource."""
        step_type = _step_type(span)
        start_time_ns = _to_unix_ns(span.created_at)

        return ReadableSpan(
            name=_span_name(span, step_type),
            context=span_context,
            parent=parent_span_context,
            resource=resource,
            attributes=build_span_attributes(span, session_id),
            events=(),
            links=(),
            kind=_KIND_BY_STEP_TYPE[step_type],
            instrumentation_scope=_INSTRUMENTATION_SCOPE,
            status=_span_status(span),
            start_time=start_time_ns,
            end_time=_end_time_ns(span, start_time_ns, end_time_ns),
        )
