"""Canonical Galileo-field and OTLP wire-attribute mapping."""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping, Sequence
from enum import Enum
from typing import Any

from opentelemetry.util.types import AttributeValue
from pydantic import BaseModel

from galileo_core.schemas.logging.span import AgentSpan, LlmSpan, RetrieverSpan, ToolSpan, WorkflowSpan
from galileo_core.schemas.logging.step import BaseStep, StepType

SPLUNK_AO_SYSTEM = "splunk_ao.system"
SPLUNK_AO_SYSTEM_VALUE = "splunk_ao_python"

CONTENT_ALIAS_BY_GEN_AI: Mapping[str, str] = {
    "gen_ai.input.messages": "splunk_ao.input.messages",
    "gen_ai.system_instructions": "splunk_ao.system_instructions",
    "gen_ai.output.messages": "splunk_ao.output.messages",
    "gen_ai.tool.call.arguments": "splunk_ao.tool.call.arguments",
    "gen_ai.tool.call.result": "splunk_ao.tool.call.result",
    "gen_ai.retrieval.documents": "splunk_ao.retrieval.documents",
    "gen_ai.tool.definitions": "splunk_ao.tool.definitions",
}

SPLUNK_ALIAS_BY_GEN_AI: Mapping[str, str] = {
    "gen_ai.system": "splunk_ao.provider.name",
    "gen_ai.operation.name": "splunk_ao.operation.name",
    "gen_ai.conversation.id": "splunk_ao.session.id",
    "gen_ai.workflow.name": "splunk_ao.workflow.name",
    "gen_ai.agent.name": "splunk_ao.agent.name",
    "gen_ai.agent.id": "splunk_ao.agent.id",
    "gen_ai.agent.description": "splunk_ao.agent.description",
    "gen_ai.agent.version": "splunk_ao.agent.version",
    "gen_ai.provider.name": "splunk_ao.provider.name",
    "gen_ai.request.model": "splunk_ao.request.model",
    "gen_ai.request.temperature": "splunk_ao.request.temperature",
    "gen_ai.request.top_p": "splunk_ao.request.top_p",
    "gen_ai.request.top_k": "splunk_ao.request.top_k",
    "gen_ai.request.max_tokens": "splunk_ao.request.max_tokens",
    "gen_ai.request.stop_sequences": "splunk_ao.request.stop_sequences",
    "gen_ai.request.frequency_penalty": "splunk_ao.request.frequency_penalty",
    "gen_ai.request.presence_penalty": "splunk_ao.request.presence_penalty",
    "gen_ai.request.seed": "splunk_ao.request.seed",
    "gen_ai.response.finish_reasons": "splunk_ao.response.finish_reasons",
    "gen_ai.response.model": "splunk_ao.response.model",
    "gen_ai.response.id": "splunk_ao.response.id",
    "gen_ai.output.type": "splunk_ao.output.type",
    "gen_ai.tool.call.id": "splunk_ao.tool.call.id",
    "gen_ai.tool.name": "splunk_ao.tool.name",
    "gen_ai.tool.description": "splunk_ao.tool.description",
    "gen_ai.tool.type": "splunk_ao.tool.type",
    "gen_ai.retrieval.top_k": "splunk_ao.retrieval.top_k",
    "gen_ai.retrieval.query.text": "splunk_ao.retrieval.query.text",
    "gen_ai.usage.input_tokens": "splunk_ao.llm.usage.input_tokens",
    "gen_ai.usage.output_tokens": "splunk_ao.llm.usage.output_tokens",
    "gen_ai.usage.cache_creation.input_tokens": "splunk_ao.llm.usage.cache_creation.input_tokens",
    "gen_ai.usage.cache_read.input_tokens": "splunk_ao.llm.usage.cache_read.input_tokens",
    "gen_ai.usage.reasoning.output_tokens": "splunk_ao.llm.usage.reasoning.output_tokens",
    "gen_ai.response.time_to_first_chunk": "splunk_ao.llm.time_to_first_token_ns",
    **CONTENT_ALIAS_BY_GEN_AI,
}

_OPERATION_BY_STEP_TYPE = {
    StepType.llm: "chat",
    StepType.retriever: "retrieval",
    StepType.tool: "execute_tool",
    StepType.workflow: "invoke_workflow",
    StepType.agent: "invoke_agent",
}


def _json_compatible(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_compatible(item) for item in value]
    return value


def _json_string(value: Any) -> str:
    return json.dumps(_json_compatible(value), separators=(",", ":"), sort_keys=True, default=str)


def _content_value(value: Any) -> str:
    return value if isinstance(value, str) else _json_string(value)


def _set_if_present(attrs: MutableMapping[str, AttributeValue], key: str, value: AttributeValue | None) -> None:
    if value is not None:
        attrs[key] = value


def _field(source: Any, name: str) -> Any:
    value = getattr(source, name, None)
    if value is not None:
        return value
    extra = getattr(source, "model_extra", None)
    return extra.get(name) if extra else None


def set_common_attributes(
    attrs: MutableMapping[str, AttributeValue], span: BaseStep, session_id: str | None = None
) -> None:
    """Map fields shared by every proprietary span type."""
    if span.redacted_input is not None:
        attrs["splunk_ao.redacted_input"] = _content_value(span.redacted_input)
    if span.redacted_output is not None:
        attrs["splunk_ao.redacted_output"] = _content_value(span.redacted_output)
    if span.user_metadata:
        attrs["splunk_ao.metadata"] = _json_string(span.user_metadata)
    if span.tags:
        attrs["splunk_ao.tags"] = tuple(span.tags)
    if span.status_code is not None:
        attrs["splunk_ao.status_code"] = span.status_code
        if span.status_code >= 400:
            attrs["error.type"] = str(span.status_code)

    step_number = getattr(span, "step_number", None)
    if step_number is not None:
        attrs["splunk_ao.step_number"] = step_number

    resolved_session_id = session_id or getattr(span, "session_id", None)
    if resolved_session_id is not None:
        attrs["gen_ai.conversation.id"] = str(resolved_session_id)


def set_dataset_attributes(attrs: MutableMapping[str, AttributeValue], span: BaseStep) -> None:
    """Map optional dataset context fields."""
    _set_if_present(attrs, "splunk_ao.dataset.input", span.dataset_input)
    _set_if_present(attrs, "splunk_ao.dataset.output", span.dataset_output)
    if span.dataset_metadata:
        attrs["splunk_ao.dataset.metadata"] = _json_string(span.dataset_metadata)


def _set_operation(attrs: MutableMapping[str, AttributeValue], span_type: StepType) -> None:
    operation = _OPERATION_BY_STEP_TYPE.get(span_type)
    if operation is not None:
        attrs["gen_ai.operation.name"] = operation


def set_llm_attributes(attrs: MutableMapping[str, AttributeValue], span: LlmSpan) -> None:
    """Map LLM request, response, content, and metric fields."""
    _set_operation(attrs, StepType.llm)
    attrs["gen_ai.input.messages"] = _content_value(span.input)
    attrs["gen_ai.output.messages"] = _content_value(span.output)
    _set_if_present(attrs, "gen_ai.request.model", span.model)
    _set_if_present(attrs, "gen_ai.request.temperature", span.temperature)

    for field_name, attribute_name in (
        ("provider", "gen_ai.provider.name"),
        ("top_p", "gen_ai.request.top_p"),
        ("top_k", "gen_ai.request.top_k"),
        ("max_tokens", "gen_ai.request.max_tokens"),
        ("stop_sequences", "gen_ai.request.stop_sequences"),
        ("frequency_penalty", "gen_ai.request.frequency_penalty"),
        ("presence_penalty", "gen_ai.request.presence_penalty"),
        ("seed", "gen_ai.request.seed"),
        ("response_model", "gen_ai.response.model"),
        ("response_id", "gen_ai.response.id"),
    ):
        _set_if_present(attrs, attribute_name, _field(span, field_name))

    if span.finish_reason is not None:
        attrs["gen_ai.response.finish_reasons"] = (span.finish_reason,)
    if span.tools is not None:
        attrs["gen_ai.tool.definitions"] = _json_string(span.tools)
    if span.events is not None:
        attrs["splunk_ao.llm.events"] = _json_string(span.events)

    metrics = span.metrics
    _set_if_present(attrs, "gen_ai.usage.input_tokens", metrics.num_input_tokens)
    _set_if_present(attrs, "gen_ai.usage.output_tokens", metrics.num_output_tokens)
    _set_if_present(attrs, "splunk_ao.llm.usage.total_tokens", metrics.num_total_tokens)
    if metrics.time_to_first_token_ns is not None:
        attrs["gen_ai.response.time_to_first_chunk"] = metrics.time_to_first_token_ns / 1_000_000_000
        attrs["splunk_ao.llm.time_to_first_token_ns"] = metrics.time_to_first_token_ns

    for field_name, attribute_name in (
        ("input_cost", "splunk_ao.llm.cost.input_usd"),
        ("output_cost", "splunk_ao.llm.cost.output_usd"),
        ("total_cost", "splunk_ao.llm.cost.total_usd"),
        ("cache_creation_input_tokens", "gen_ai.usage.cache_creation.input_tokens"),
        ("cache_read_input_tokens", "gen_ai.usage.cache_read.input_tokens"),
        ("reasoning_output_tokens", "gen_ai.usage.reasoning.output_tokens"),
    ):
        _set_if_present(attrs, attribute_name, _field(metrics, field_name))

    for field_name, attribute_name in (
        ("log_probs", "splunk_ao.llm.log_probs"),
        ("top_logprobs", "splunk_ao.llm.top_logprobs"),
        ("response_format", "splunk_ao.llm.response_format"),
        ("tool_use_allowed", "splunk_ao.llm.tool_use_allowed"),
        ("structured_output_name", "splunk_ao.llm.structured_output.name"),
        ("structured_output_input", "splunk_ao.llm.structured_output.input"),
    ):
        _set_if_present(attrs, attribute_name, _field(span, field_name))


def set_tool_attributes(attrs: MutableMapping[str, AttributeValue], span: ToolSpan) -> None:
    """Map tool execution fields."""
    _set_operation(attrs, StepType.tool)
    attrs["gen_ai.tool.name"] = span.name
    attrs["gen_ai.tool.call.arguments"] = _content_value(span.input)
    if span.output is not None:
        attrs["gen_ai.tool.call.result"] = _content_value(span.output)
    _set_if_present(attrs, "gen_ai.tool.call.id", span.tool_call_id)


def set_retriever_attributes(attrs: MutableMapping[str, AttributeValue], span: RetrieverSpan) -> None:
    """Map retrieval query and document fields."""
    _set_operation(attrs, StepType.retriever)
    attrs["gen_ai.retrieval.query.text"] = span.input
    attrs["gen_ai.retrieval.documents"] = _content_value(span.output)
    attrs["splunk_ao.retrieval.documents.count"] = len(span.output)
    attrs["db.operation"] = "search"
    requested_top_k = _field(span, "num_documents")
    _set_if_present(attrs, "gen_ai.retrieval.top_k", requested_top_k)


def _set_orchestration_content(attrs: MutableMapping[str, AttributeValue], span: WorkflowSpan | AgentSpan) -> None:
    attrs["gen_ai.input.messages"] = _content_value(span.input)
    if span.output is not None:
        attrs["gen_ai.output.messages"] = _content_value(span.output)


def set_workflow_attributes(attrs: MutableMapping[str, AttributeValue], span: WorkflowSpan) -> None:
    """Map workflow fields."""
    _set_operation(attrs, StepType.workflow)
    attrs["gen_ai.workflow.name"] = span.name
    _set_orchestration_content(attrs, span)


def set_agent_attributes(attrs: MutableMapping[str, AttributeValue], span: AgentSpan) -> None:
    """Map agent fields."""
    _set_operation(attrs, StepType.agent)
    attrs["gen_ai.agent.name"] = span.name
    attrs["splunk_ao.agent.type"] = span.agent_type.value
    _set_orchestration_content(attrs, span)


def _set_generic_content(attrs: MutableMapping[str, AttributeValue], span: BaseStep) -> None:
    if span.input is not None:
        attrs["gen_ai.input.messages"] = _content_value(span.input)
    if span.output is not None:
        attrs["gen_ai.output.messages"] = _content_value(span.output)


def build_span_attributes(span: BaseStep, session_id: str | None = None) -> dict[str, AttributeValue]:
    """Build preliminary attributes for one proprietary Galileo span."""
    attrs: dict[str, AttributeValue] = {}
    set_common_attributes(attrs, span, session_id)
    set_dataset_attributes(attrs, span)

    if isinstance(span, LlmSpan):
        set_llm_attributes(attrs, span)
    elif isinstance(span, ToolSpan):
        set_tool_attributes(attrs, span)
    elif isinstance(span, RetrieverSpan):
        set_retriever_attributes(attrs, span)
    elif isinstance(span, AgentSpan):
        set_agent_attributes(attrs, span)
    elif isinstance(span, WorkflowSpan):
        set_workflow_attributes(attrs, span)
    elif getattr(span.type, "value", span.type) == "control":
        attrs["splunk_ao.operation.name"] = "control"
        _set_generic_content(attrs, span)
    elif span.type == StepType.trace:
        _set_generic_content(attrs, span)
    else:
        raise TypeError(f"Unsupported span type: {type(span).__name__}")

    return attrs


def _alias_value(source_key: str, value: AttributeValue) -> AttributeValue:
    if source_key == "gen_ai.response.time_to_first_chunk":
        return int(float(value) * 1_000_000_000)
    return value


def normalize_attributes_for_export(
    attrs: Mapping[str, AttributeValue], *, enabled: bool = True
) -> dict[str, AttributeValue]:
    """Return final wire attributes without mutating the source mapping."""
    result = dict(attrs)
    if not enabled:
        return result

    for source_key, destination_key in SPLUNK_ALIAS_BY_GEN_AI.items():
        if source_key in attrs:
            result[destination_key] = _alias_value(source_key, attrs[source_key])

    for source_key in CONTENT_ALIAS_BY_GEN_AI:
        result.pop(source_key, None)

    result[SPLUNK_AO_SYSTEM] = SPLUNK_AO_SYSTEM_VALUE
    return result
