import logging
from collections.abc import Sequence
from typing import Any, Literal

from agents import (
    AgentSpanData,
    CustomSpanData,
    FunctionSpanData,
    GenerationSpanData,
    GuardrailSpanData,
    HandoffSpanData,
    Span,
    SpanData,
)
from agents.tracing import ResponseSpanData

from galileo_core.schemas.logging.span import Span as SplunkAOSpan
from splunk_ao.schema.handlers import SPAN_TYPE
from splunk_ao.utils.serialization import _convert_langchain_content_block, serialize_to_str

_logger = logging.getLogger(__name__)

_TEXT_PART_TYPES = ("text", "input_text", "output_text")
# Responses API tool-call items, by the field holding the call's arguments.
_TOOL_CALL_ITEM_FIELDS = {"function_call": "arguments", "custom_tool_call": "input"}
_TOOL_OUTPUT_ITEM_TYPES = ("function_call_output", "custom_tool_call_output")
# Message roles have no "developer" in the OTel GenAI schema or in LoggedMessage.
_ROLE_MAP = {"developer": "system"}


def _content_block(part: Any) -> dict[str, Any] | None:
    """Convert one Chat Completions or Responses content part into an ingest content block."""
    if isinstance(part, str):
        return {"type": "text", "text": part}
    if not isinstance(part, dict):
        return None
    kind = part.get("type")
    if kind in _TEXT_PART_TYPES or (kind is None and isinstance(part.get("text"), str)):
        return {"type": "text", "text": part.get("text") or ""}
    if kind == "refusal":
        return {"type": "text", "text": part.get("refusal") or ""}
    if kind == "input_image":
        if not isinstance(part.get("image_url"), str):
            # Only a provider file_id: there is no data or URL to attach.
            return {"type": "text", "text": serialize_to_str(part)}
        # Responses API carries image_url as a plain string, not {"url": ...}.
        part = {"type": "image_url", "image_url": {"url": part["image_url"]}}
    elif kind == "input_file":
        # Responses API carries the file fields on the part itself, not under "file".
        part = {"type": "file", "file": part}
    return _convert_langchain_content_block(part)


def _message_content(content: Any) -> Any:
    """Keep string content; convert a list of parts into ingest content blocks."""
    if not isinstance(content, list):
        return content
    return [block for block in (_content_block(part) for part in content) if block is not None]


def _normalize_chat_messages(messages: Any) -> Any:
    """Convert multi-part content in Chat Completions messages into ingest content blocks."""
    if not isinstance(messages, list | tuple):
        return messages
    return [
        {**message, "content": _message_content(message["content"])}
        if isinstance(message, dict) and isinstance(message.get("content"), list)
        else message
        for message in messages
    ]


def _as_dict(item: Any) -> Any:
    return item.model_dump(exclude_none=True) if hasattr(item, "model_dump") else item


def _tool_call(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("call_id"),
        "type": "function",
        "function": {"name": item.get("name"), "arguments": item.get(_TOOL_CALL_ITEM_FIELDS[item["type"]])},
    }


def _normalize_responses_input(items: Any) -> list[dict[str, Any]]:
    """Convert Responses API input (a string or item list) into chat messages, in the order sent."""
    if isinstance(items, str):
        return [{"role": "user", "content": items}]
    messages: list[dict[str, Any]] = []
    for item in map(_as_dict, items or []):
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind in _TOOL_CALL_ITEM_FIELDS:
            previous = messages[-1] if messages else None
            # Parallel tool calls are one assistant turn that the item list splits up.
            if previous and previous["role"] == "assistant" and previous.get("tool_calls") and not previous["content"]:
                previous["tool_calls"].append(_tool_call(item))
            else:
                messages.append({"role": "assistant", "content": "", "tool_calls": [_tool_call(item)]})
        elif kind in _TOOL_OUTPUT_ITEM_TYPES:
            output = item.get("output")
            if isinstance(output, str):
                content = output
            elif isinstance(output, list):
                # A tool result can carry multimodal parts (e.g. text + an image); convert them into
                # content blocks instead of dumping the whole list, including any base64 payload, as JSON.
                content = _message_content(output)
            else:
                content = serialize_to_str(output)
            messages.append({"role": "tool", "tool_call_id": item.get("call_id"), "content": content})
        elif "role" in item:
            role = _ROLE_MAP.get(item["role"], item["role"])
            messages.append({"role": role, "content": _message_content(item.get("content") or "")})
        # Items without a role (reasoning, hosted tool calls) are skipped, as in the OTel OpenAI instrumentation.
    return messages


def _normalize_responses_output(items: Any) -> dict[str, Any] | None:
    """Combine Responses API output items into the single assistant message an LLM span records."""
    texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for item in map(_as_dict, items or []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            content = _message_content(item.get("content") or [])
            if isinstance(content, str):
                texts.append(content)
                continue
            texts.extend(block["text"] for block in content if block.get("type") == "text" and block.get("text"))
        elif item.get("type") in _TOOL_CALL_ITEM_FIELDS:
            tool_calls.append(_tool_call(item))
    if not texts and not tool_calls:
        return None
    message: dict[str, Any] = {"role": "assistant", "content": "\n".join(texts)}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _extract_user_input(llm_input: Any) -> str | None:
    """Return the text of the latest user message that has any, from an LLM span's message list."""
    if not isinstance(llm_input, list):
        return None
    for message in reversed(llm_input):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content:
            return content
        if isinstance(content, list):
            texts = [b["text"] for b in content if isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"]]
            if texts:
                return " ".join(texts)
    return None


class SplunkAOCustomSpan(CustomSpanData):
    def __init__(self, span: SplunkAOSpan, data: dict[str, Any]):
        self.span = span
        super().__init__(span.name, data)

    @property
    def type(self) -> Literal["splunk_ao_custom"]:
        return "splunk_ao_custom"


def _map_span_type(span_data: SpanData, span: Span[Any] | None = None) -> SPAN_TYPE | Literal["splunk_ao_custom"]:
    """Determine the Splunk AO span type based on the OpenAI Agent span data."""
    if isinstance(span_data, GenerationSpanData | ResponseSpanData):
        return "llm"
    if isinstance(span_data, FunctionSpanData | GuardrailSpanData):
        return "tool"
    if isinstance(span_data, SplunkAOCustomSpan):
        return span_data.type
    if isinstance(span_data, AgentSpanData | HandoffSpanData | CustomSpanData):
        return "workflow"

    if hasattr(span_data, "type") and span_data.type:
        span_type = span_data.type
        if span_type in ["function", "guardrail", "tool"]:
            return "tool"
        if span_type in ["generation", "response"]:
            return "llm"
        if span_type in ["agent", "handoff", "custom"]:
            return "workflow"

    _logger.debug(f"Unknown span data type {type(span_data)}, defaulting to workflow.")
    return "workflow"


def _map_span_name(span: Span[Any]) -> str:
    """Determine the name for a given OpenAI Agent span."""
    if hasattr(span.span_data, "name") and span.span_data.name:
        return span.span_data.name

    if isinstance(span.span_data, GenerationSpanData):
        return "Generation"

    if isinstance(span.span_data, ResponseSpanData):
        return "Response"

    if isinstance(span.span_data, HandoffSpanData):
        return f"Handoff: {span.span_data.from_agent} -> {span.span_data.to_agent}"

    if hasattr(span.span_data, "type") and span.span_data.type:
        return span.span_data.type.capitalize()

    return "Unknown Span"


def _parse_usage(usage_data: dict | Any | None) -> dict[str, Any]:
    """
    Safely parse usage data into a standardized dictionary with detailed token breakdowns.

    Extracts standard token counts plus detailed breakdowns like reasoning tokens,
    cached tokens, audio tokens, etc.
    """
    parsed: dict[str, Any] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "input_tokens_details": None,
        "output_tokens_details": None,
    }
    if usage_data is None:
        return parsed

    usage_dict = {}
    if hasattr(usage_data, "model_dump"):
        try:
            usage_dict = usage_data.model_dump()
        except Exception:
            _logger.debug("Failed to model_dump usage data.", exc_info=True)
            if isinstance(usage_data, dict):
                usage_dict = usage_data
            else:
                return parsed
    elif isinstance(usage_data, dict):
        usage_dict = usage_data
    else:
        return parsed

    input_tokens = usage_dict.get("input_tokens", usage_dict.get("prompt_tokens", None))
    output_tokens = usage_dict.get("output_tokens", usage_dict.get("completion_tokens", None))
    parsed["input_tokens"] = input_tokens if isinstance(input_tokens, int) else None
    parsed["output_tokens"] = output_tokens if isinstance(output_tokens, int) else None
    parsed["total_tokens"] = usage_dict.get("total_tokens")

    if parsed["total_tokens"] is None:
        if isinstance(parsed["input_tokens"], int) and isinstance(parsed["output_tokens"], int):
            parsed["total_tokens"] = parsed["input_tokens"] + parsed["output_tokens"]

    # Extract detailed token breakdowns
    for tokens_details_key in ["input_tokens_details", "output_tokens_details"]:
        if tokens_details_key in usage_dict and usage_dict[tokens_details_key] is not None:
            tokens_details = usage_dict[tokens_details_key]
            # Convert to dict if it's an object
            if hasattr(tokens_details, "model_dump"):
                try:
                    tokens_details = tokens_details.model_dump()
                except Exception:
                    _logger.debug(f"Failed to model_dump {tokens_details_key}.", exc_info=True)
                    if hasattr(tokens_details, "__dict__"):
                        tokens_details = tokens_details.__dict__
                    elif isinstance(tokens_details, dict):
                        pass
                    else:
                        continue
            elif hasattr(tokens_details, "__dict__"):
                tokens_details = tokens_details.__dict__
            elif not isinstance(tokens_details, dict):
                continue

            # Filter out None values and store
            filtered_details = {k: v for k, v in tokens_details.items() if v is not None}
            if filtered_details:
                parsed[tokens_details_key] = filtered_details

    # Ensure standard token values are integers if not None
    for key in ["input_tokens", "output_tokens", "total_tokens"]:
        if parsed[key] is not None:
            try:
                parsed[key] = int(parsed[key])
            except (ValueError, TypeError):
                _logger.warning(f"Could not convert usage value '{parsed[key]}' for key '{key}' to int.")
                parsed[key] = None

    return parsed


def _extract_llm_data(span_data: GenerationSpanData | ResponseSpanData) -> dict[str, Any]:
    """Extract data specific to LLM spans (Generation, Response)."""
    data: dict[str, Any] = {
        "input": None,
        "output": None,
        "model": None,
        "temperature": None,
        "num_input_tokens": None,
        "num_output_tokens": None,
        "total_tokens": None,
        "metadata": {"gen_ai_system": "openai"},  # Default assumption
        "model_parameters": {},
        "tools": None,
        "status_code": 200,  # Assume success unless error is set later
    }

    if isinstance(span_data, GenerationSpanData):
        data["input"] = span_data.input
        data["output"] = span_data.output
        data["model"] = span_data.model
        usage = _parse_usage(span_data.usage)
        # Extract standard token counts
        for key in ["input_tokens", "output_tokens", "total_tokens"]:
            if usage.get(key) is not None:
                data[f"num_{key}"] = usage[key]

        # Add detailed token breakdowns to metadata
        if usage.get("input_tokens_details"):
            data["metadata"]["input_tokens_details"] = usage["input_tokens_details"]
            # Extract specific cached tokens metric
            if "cached_tokens" in usage["input_tokens_details"]:
                data["metadata"]["num_cached_input_tokens"] = usage["input_tokens_details"]["cached_tokens"]

        if usage.get("output_tokens_details"):
            data["metadata"]["output_tokens_details"] = usage["output_tokens_details"]
            # Extract specific reasoning tokens metric
            if "reasoning_tokens" in usage["output_tokens_details"]:
                data["metadata"]["num_reasoning_tokens"] = usage["output_tokens_details"]["reasoning_tokens"]

        if span_data.model_config:
            # Ensure model_config is a dict
            model_config = span_data.model_config if isinstance(span_data.model_config, dict) else {}
            data["model_parameters"].update(model_config)
            data["temperature"] = model_config.get("temperature")
            data["metadata"]["model_config"] = model_config

    elif isinstance(span_data, ResponseSpanData):
        data["input"] = span_data.input
        if response := span_data.response:
            data["output"] = response.output
            data["model"] = response.model
            usage = _parse_usage(response.usage)
            # Extract standard token counts
            for key in ["input_tokens", "output_tokens", "total_tokens"]:
                if usage.get(key) is not None:
                    data[f"num_{key}"] = usage[key]

            # Add detailed token breakdowns to metadata
            if usage.get("input_tokens_details"):
                # Extract specific cached tokens metric
                if "cached_tokens" in usage["input_tokens_details"]:
                    data["num_cached_input_tokens"] = usage["input_tokens_details"]["cached_tokens"]

            if usage.get("output_tokens_details"):
                # Extract specific reasoning tokens metric
                if "reasoning_tokens" in usage["output_tokens_details"]:
                    data["num_reasoning_tokens"] = usage["output_tokens_details"]["reasoning_tokens"]

            data["temperature"] = response.temperature

            tools_raw = getattr(response, "tools", None)
            if tools_raw:
                try:
                    data["tools"] = [t.model_dump() for t in tools_raw if hasattr(t, "model_dump")]
                except Exception:
                    _logger.debug("Failed to serialize tools.", exc_info=True)
                    data["tools"] = serialize_to_str(tools_raw)

            # Extract metadata and model parameters
            try:
                response_meta = response.model_dump(
                    exclude={"input", "output", "usage", "tools", "error", "status"}, exclude_none=True
                )
                data["metadata"]["response_metadata"] = response_meta
            except Exception:
                _logger.debug("Failed to model_dump response metadata.", exc_info=True)
                response_meta = {}  # Fallback

            data["model_parameters"] = {
                k: v
                for k, v in response_meta.items()
                if k
                in (
                    "temperature",
                    "max_output_tokens",
                    "top_p",
                    "tool_choice",
                    "parallel_tool_calls",
                    "truncation",
                    "seed",
                    "frequency_penalty",
                    "presence_penalty",
                )
            }
            # Add serialized tools to model parameters for context
            if data["tools"]:
                data["model_parameters"]["tools"] = data["tools"]

            # Handle potential error in response object
            if hasattr(response, "error") and response.error:
                data["metadata"]["error_details"] = response.error
                # Use 500 as default if status_code is not present on error
                data["status_code"] = getattr(response.error, "status_code", 500)

            # Include instructions in metadata if available
            if hasattr(response, "instructions") and response.instructions:
                data["metadata"]["instructions"] = response.instructions

    if isinstance(span_data, GenerationSpanData):
        # GenerationSpanData: input/output are list[dict] — LoggedLlmSpan validators handle conversion.
        # output is Sequence[Mapping] (a list from the SDK's models, possibly a tuple from a custom model),
        # but LlmSpanAllowedOutputType only accepts a single dict; take the first choice.
        data["input"] = _normalize_chat_messages(data["input"])
        if isinstance(data["output"], Sequence) and not isinstance(data["output"], str):
            choices = list(data["output"])
            if len(choices) > 1:
                _logger.debug("GenerationSpanData.output has %d choices; only the first is recorded", len(choices))
            first = choices[0] if choices else None
            if isinstance(first, dict) and first.get("object") == "response":
                # Streamed Chat Completions record the adapter's Responses-shaped response, not the message.
                data["output"] = _normalize_responses_output(first.get("output")) or serialize_to_str(None)
            else:
                data["output"] = _normalize_chat_messages([first])[0] if first is not None else None
    else:
        # ResponseSpanData: input is a string or item list, output a list of ResponseOutputItem objects.
        # Both are only set once the model call returns, so they are None when the span starts.
        if data["input"] is None:
            data["input"] = serialize_to_str(None)
        else:
            data["input"] = _normalize_responses_input(data["input"])
        data["output"] = _normalize_responses_output(data["output"]) or serialize_to_str(None)

    if data["temperature"] is not None:
        try:
            data["temperature"] = float(data["temperature"])
        except (ValueError, TypeError):
            data["temperature"] = None

    # Clean up None values that add_llm_span doesn't expect, but keep necessary keys
    return {k: v for k, v in data.items() if v is not None or k in ["input", "output", "metadata", "model_parameters"]}


def _extract_tool_data(span_data: FunctionSpanData | GuardrailSpanData) -> dict[str, Any]:
    """Extract data specific to Tool spans (Function, Guardrail)."""
    data: dict[str, Any] = {
        "input": None,
        "output": None,
        "metadata": {},
        "status_code": 200,  # Assume success
    }
    if isinstance(span_data, FunctionSpanData):
        data["input"] = serialize_to_str(span_data.input)
        data["output"] = serialize_to_str(span_data.output)
    elif isinstance(span_data, GuardrailSpanData):
        data["input"] = None  # Guardrails might not map directly
        data["output"] = serialize_to_str({"triggered": span_data.triggered})
        data["metadata"]["triggered"] = span_data.triggered
        if span_data.triggered:
            # Indicate potential issue if guardrail triggered
            # Note: Splunk AO doesn't have a specific warning status, use metadata
            data["metadata"]["status"] = "warning"

    # Clean up None values, keeping essential keys
    return {k: v for k, v in data.items() if v is not None or k in ["input", "output", "metadata"]}


def _extract_workflow_data(span_data: AgentSpanData | HandoffSpanData | CustomSpanData) -> dict[str, Any]:
    """Extract data specific to Workflow spans (Agent, Handoff, Custom)."""
    data: dict[str, Any] = {
        "input": None,
        "output": None,
        "metadata": {},
        "status_code": 200,  # Assume success
    }
    if isinstance(span_data, AgentSpanData):
        # Agent input/output is often implicit; capture config in metadata
        data["metadata"]["tools"] = getattr(span_data, "tools", None)
        data["metadata"]["handoffs"] = getattr(span_data, "handoffs", None)
        data["metadata"]["output_type"] = getattr(span_data, "output_type", None)
    elif isinstance(span_data, HandoffSpanData):
        data["input"] = serialize_to_str({"from_agent": span_data.from_agent})
        data["output"] = serialize_to_str({"to_agent": span_data.to_agent})
        data["metadata"]["from_agent"] = span_data.from_agent
        data["metadata"]["to_agent"] = span_data.to_agent
    elif isinstance(span_data, CustomSpanData):
        custom_data_dict = span_data.data or {}
        data["input"] = serialize_to_str(custom_data_dict.get("input"))
        data["output"] = serialize_to_str(custom_data_dict.get("output"))
        # Filter out None values from metadata more carefully
        data["metadata"] = {k: v for k, v in custom_data_dict.items() if k not in ["input", "output"] and v is not None}

    # Clean up None values, keeping essential keys and non-empty metadata
    data = {k: v for k, v in data.items() if (v is not None and v != {}) or k in ["input", "output"]}
    # Ensure metadata is always a dict, even if empty after filtering
    if "metadata" not in data:
        data["metadata"] = {}

    return data
