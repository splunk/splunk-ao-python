"""Canonical Splunk AO field and OTLP wire-attribute mapping."""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping, Sequence
from enum import Enum
from typing import Any, cast

from opentelemetry.util.types import AttributeValue
from pydantic import BaseModel

from galileo_core.schemas.logging.span import AgentSpan, LlmSpan, RetrieverSpan, ToolSpan, WorkflowSpan
from galileo_core.schemas.logging.step import BaseStep, StepType
from splunk_ao.logger.control import ControlSpan

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
    StepType.control: "control",
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


def _mapping_value(value: Any) -> dict[str, Any] | None:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    return None


def _mapping_view(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    return value if isinstance(value, Mapping) else None


def _parse_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _parse_json_value(value: Any) -> Any:
    parsed = _parse_json_string(value)
    return parsed if isinstance(value, str) else _json_compatible(parsed)


def _text_part(value: Any) -> dict[str, Any]:
    content = value if isinstance(value, str) else _json_string(value)
    return {"type": "text", "content": content}


def _is_content_part(value: Any) -> bool:
    part = _mapping_view(value)
    if part is None:
        return False
    part_type = part.get("type")
    return isinstance(part_type, str) and bool(part_type.strip())


def _content_part(value: Any) -> dict[str, Any] | None:
    part = _mapping_value(value)
    if part is None:
        return None

    part_type = part.get("type")
    if not isinstance(part_type, str) or not part_type.strip():
        return None
    if part_type == "text" and "content" not in part and "text" in part:
        part["content"] = part.pop("text")
    elif part_type == "data":
        has_url = "url" in part
        has_base64 = "base64" in part
        if has_url == has_base64:
            return None
        if has_url:
            if "uri" in part:
                return None
            part["type"] = "uri"
            part["uri"] = part.pop("url")
        else:
            if "content" in part:
                return None
            part["type"] = "blob"
            part["content"] = part.pop("base64")
    return part


def _content_parts(value: Any) -> list[dict[str, Any]]:
    part = _content_part(value)
    if part is not None:
        return [part]

    if value and isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        parts = [_content_part(item) for item in value]
        if all(item is not None for item in parts):
            return [item for item in parts if item is not None]

    return [_text_part(value)]


def _tool_call_part(value: Any) -> dict[str, Any]:
    call = _mapping_value(value) or {}
    function = _mapping_value(call.pop("function", None)) or {}
    result = {**call, "type": "tool_call"}
    if "name" in function:
        result["name"] = function.pop("name")
    if "arguments" in function:
        result["arguments"] = _parse_json_value(function.pop("arguments"))
    result.update(function)
    return result


def _mapped_message(source: dict[str, Any], default_role: str) -> dict[str, Any]:
    role = _json_compatible(source.pop("role"))
    content = source.pop("content", None)
    source_parts = source.pop("parts", None)
    tool_call_id = source.pop("tool_call_id", None)
    tool_calls = source.pop("tool_calls", None)

    if source_parts is not None:
        parts = _content_parts(source_parts)
    elif role == "tool":
        response = {"type": "tool_call_response", "response": _parse_json_value(content)}
        if tool_call_id is not None:
            response["id"] = str(tool_call_id)
        parts = [response]
    else:
        parts = [] if content in (None, "") and tool_calls else _content_parts("" if content is None else content)

    if tool_calls:
        parts.extend(_tool_call_part(tool_call) for tool_call in tool_calls)

    return {**source, "role": str(role), "parts": parts}


def _message(value: Any, default_role: str) -> dict[str, Any]:
    source = _mapping_value(value)
    if source is None or "role" not in source:
        return {"role": default_role, "parts": _content_parts(value)}
    return _mapped_message(source, default_role)


def _message_sequence(value: Any, default_role: str) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return [_message(value, default_role)]
    if not value:
        return []

    messages = [_mapping_value(item) for item in value]
    if all(message is not None and "role" in message for message in messages):
        return [_mapped_message(message, default_role) for message in messages if message is not None]
    return [_message(value, default_role)]


def _message_container(value: Any) -> tuple[Any | None, bool, bool]:
    parsed = _parse_json_string(value)

    source = _mapping_view(parsed)
    if source is not None:
        update = _mapping_view(_parse_json_string(source.get("update")))
        for container in (update, source):
            if container is None or "messages" not in container:
                continue
            messages = _parse_json_string(container["messages"])
            if _is_message_sequence(messages, allow_empty=True):
                return messages, container is source, True

        if "role" in source or "type" in source:
            return parsed, False, True
        return parsed, False, False

    if isinstance(parsed, Sequence) and not isinstance(parsed, str | bytes | bytearray):
        if _is_message_sequence(parsed) or _is_content_part_sequence(parsed):
            return parsed, False, True
        return parsed, False, False

    return parsed, False, False


def _is_message_sequence(value: Any, *, allow_empty: bool = False) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        message = _mapping_view(value)
        return message is not None and "role" in message
    return (allow_empty and not value) or (
        bool(value) and all((message := _mapping_view(item)) is not None and "role" in message for item in value)
    )


def _is_content_part_sequence(value: Any) -> bool:
    return bool(value) and all(_is_content_part(item) for item in value)


def _orchestration_messages(value: Any, default_role: str) -> tuple[list[dict[str, Any]] | None, bool]:
    container, full_history, recognized_messages = _message_container(value)
    if container is None:
        messages = None
    elif recognized_messages and isinstance(container, Sequence) and not container:
        messages = []
    elif isinstance(container, Sequence) and not isinstance(container, str | bytes | bytearray) and not container:
        messages = [_message(container, default_role)]
    else:
        messages = _message_sequence(container, default_role)
    return messages, full_history


def _with_finish_reasons(messages: list[dict[str, Any]], finish_reason: str | None = None) -> list[dict[str, Any]]:
    for message in messages:
        source_finish_reason = message.get("finish_reason")
        message["finish_reason"] = finish_reason or source_finish_reason or "unknown"
    return messages


def _input_messages(value: Any) -> str:
    return _json_string(_message_sequence(value, "user"))


def _output_messages(value: Any, finish_reason: str | None = None) -> str:
    return _json_string(_with_finish_reasons(_message_sequence(value, "assistant"), finish_reason))


def _tool_definitions(value: Sequence[Any]) -> str:
    definitions: list[Any] = []
    for tool in value:
        definition = _mapping_value(tool)
        if definition is None:
            definitions.append(_json_compatible(tool))
            continue

        function = _mapping_value(definition.pop("function", None))
        if function is not None:
            definition = {**function, **definition}
            definition.setdefault("type", "function")
        definitions.append(definition)
    return _json_string(definitions)


def _object_content(value: Any) -> str:
    parsed = _parse_json_value(value)
    content = parsed if isinstance(parsed, Mapping) else {"value": parsed}
    return _json_string(content)


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
    attrs["gen_ai.input.messages"] = _input_messages(span.input)
    attrs["gen_ai.output.messages"] = _output_messages(span.output, span.finish_reason)
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
        attrs["gen_ai.tool.definitions"] = _tool_definitions(span.tools)
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
    attrs["gen_ai.tool.call.arguments"] = _object_content(span.input)
    if span.output is not None:
        attrs["gen_ai.tool.call.result"] = _object_content(span.output)
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
    input_messages, _ = _orchestration_messages(span.input, "user")
    if input_messages is not None:
        attrs["gen_ai.input.messages"] = _json_string(input_messages)

    if span.output is None:
        return

    output_messages, full_history = _orchestration_messages(span.output, "assistant")
    if output_messages is None:
        return
    if full_history and input_messages is not None and output_messages[: len(input_messages)] == input_messages:
        output_messages = output_messages[len(input_messages) :]
    attrs["gen_ai.output.messages"] = _json_string(_with_finish_reasons(output_messages))


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
        attrs["gen_ai.input.messages"] = _input_messages(span.input)
    if span.output is not None:
        attrs["gen_ai.output.messages"] = _output_messages(span.output)


def set_control_attributes(attrs: MutableMapping[str, AttributeValue], span: ControlSpan) -> None:
    """Map control identity, context, result, and content fields."""
    attrs["galileo.span.kind"] = "control"
    _set_operation(attrs, StepType.control)
    _set_if_present(attrs, "agent_control.control_id", _field(span, "control_id"))
    control_name = _field(span, "name")
    if control_name:
        attrs["agent_control.control_name"] = control_name

    for field_name in ("agent_name", "check_stage", "applies_to", "evaluator_name", "selector_path"):
        value = _field(span, field_name)
        if isinstance(value, Enum):
            value = value.value
        _set_if_present(attrs, f"agent_control.{field_name}", value)

    if span.output is not None:
        for field_name in ("action", "matched", "confidence", "error_message"):
            value = _field(span.output, field_name)
            if isinstance(value, Enum):
                value = value.value
            _set_if_present(attrs, f"agent_control.{field_name}", value)

    _set_generic_content(attrs, span)


def build_span_attributes(span: BaseStep, session_id: str | None = None) -> dict[str, AttributeValue]:
    """Build preliminary attributes for one proprietary Splunk AO span."""
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
    elif isinstance(span, ControlSpan) or getattr(span.type, "value", span.type) == "control":
        set_control_attributes(attrs, cast(ControlSpan, span))
    elif span.type == StepType.trace:
        _set_generic_content(attrs, span)
    else:
        raise TypeError(f"Unsupported span type: {type(span).__name__}")

    return attrs


def _alias_value(source_key: str, value: AttributeValue) -> AttributeValue:
    if source_key == "gen_ai.response.time_to_first_chunk":
        try:
            return int(float(value) * 1_000_000_000)
        except (TypeError, ValueError):
            return value
    return value


def normalize_attributes_for_export(
    attrs: Mapping[str, AttributeValue], *, enabled: bool = True
) -> dict[str, AttributeValue]:
    """Return final wire attributes without mutating the source mapping."""
    result = dict(attrs)
    result[SPLUNK_AO_SYSTEM] = SPLUNK_AO_SYSTEM_VALUE
    if not enabled:
        return result

    for source_key, destination_key in SPLUNK_ALIAS_BY_GEN_AI.items():
        if source_key in attrs:
            if destination_key == "splunk_ao.llm.time_to_first_token_ns" and destination_key in attrs:
                continue
            result[destination_key] = _alias_value(source_key, attrs[source_key])

    for source_key in CONTENT_ALIAS_BY_GEN_AI:
        result.pop(source_key, None)

    return result
