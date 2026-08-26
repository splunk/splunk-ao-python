"""Shared callback-to-span construction for incremental handler telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from galileo_core.schemas.logging.agent import AgentType
from galileo_core.schemas.logging.span import LlmMetrics, RetrieverSpan, StepWithChildSpans, ToolSpan
from galileo_core.schemas.logging.step import BaseStep, Metrics
from splunk_ao.logger.logger import HandlerStepContext
from splunk_ao.schema.handlers import Node
from splunk_ao.schema.logged import LoggedAgentSpan, LoggedLlmSpan, LoggedWorkflowSpan
from splunk_ao.utils.retrievers import convert_to_documents
from splunk_ao.utils.serialization import convert_to_string_dict, serialize_to_str


@dataclass
class HandlerSpanState:
    """Mutable ownership state for one in-flight framework callback."""

    step: BaseStep
    activation: HandlerStepContext | None


def _created_at(node: Node) -> datetime:
    created_at = node.span_params.get("created_at")
    if isinstance(created_at, datetime):
        return created_at
    start_time_iso = node.span_params.get("start_time_iso")
    if isinstance(start_time_iso, str) and start_time_iso:
        return datetime.fromisoformat(start_time_iso)
    return datetime.now(tz=UTC)


def _metadata(node: Node) -> dict[str, str] | None:
    metadata = node.span_params.get("metadata")
    return convert_to_string_dict(metadata) if metadata is not None else None


def _step_number(metadata: dict[str, str] | None) -> int | None:
    if not metadata or not (value := metadata.get("langgraph_step")):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_handler_step(
    node: Node, *, step_id: UUID | None = None, children: list[BaseStep] | None = None, openai_agents: bool = False
) -> BaseStep:
    """Build a schema-validated provisional or final span from a callback node."""
    params = node.span_params
    metadata = _metadata(node)
    step_number = _step_number(metadata)
    input_value = params.get("input", "")
    output = params.get("output", "")
    status_code = params.get("status_code")
    if params.get("error"):
        output = params["error"]
        status_code = 500
    if openai_agents and node.node_type in ("agent", "chain", "workflow", "tool"):
        input_value = input_value or node.node_type.capitalize() + " Step"

    name = params.get("name")
    if openai_agents and node.node_type in ("llm", "chat"):
        name = name or "LLM Span"
    common = {
        "name": name,
        "created_at": _created_at(node),
        "user_metadata": metadata,
        "tags": params.get("tags"),
        "status_code": status_code,
        "id": step_id or uuid4(),
        "step_number": step_number,
    }
    duration_ns = params.get("duration_ns")

    if node.node_type in ("chain", "workflow") or (openai_agents and node.node_type == "agent"):
        return LoggedWorkflowSpan(
            **common,
            input=input_value,
            output=serialize_to_str(output),
            metrics=Metrics(duration_ns=duration_ns),
            spans=children or [],
        )
    if node.node_type == "agent":
        return LoggedAgentSpan(
            **common,
            input=input_value,
            output=serialize_to_str(output),
            metrics=Metrics(duration_ns=duration_ns),
            spans=children or [],
            agent_type=params.get("agent_type", AgentType.default),
        )
    if node.node_type in ("llm", "chat"):
        return LoggedLlmSpan(
            **common,
            input=input_value,
            output=output if output is not None else "",
            metrics=LlmMetrics.model_validate(
                {
                    "duration_ns": duration_ns,
                    "num_input_tokens": params.get("num_input_tokens"),
                    "num_output_tokens": params.get("num_output_tokens"),
                    "num_total_tokens": params.get("num_total_tokens", params.get("total_tokens")),
                    "time_to_first_token_ns": params.get("time_to_first_token_ns"),
                    "num_reasoning_tokens": params.get("num_reasoning_tokens"),
                    "num_cached_input_tokens": params.get("num_cached_input_tokens"),
                }
            ),
            tools=params.get("tools"),
            events=params.get("events"),
            model=params.get("model"),
            temperature=params.get("temperature"),
        )
    if node.node_type == "retriever":
        retriever_common = {**common, "status_code": None}
        return RetrieverSpan(
            **retriever_common,
            input=serialize_to_str(input_value),
            output=convert_to_documents(output, "output"),
            metrics=Metrics(duration_ns=duration_ns),
            spans=children or [],
        )
    if node.node_type == "tool":
        return ToolSpan(
            **common,
            input=serialize_to_str(input_value),
            output=serialize_to_str(output) if output is not None else None,
            metrics=Metrics(duration_ns=duration_ns),
            spans=children or [],
            tool_call_id=params.get("tool_call_id"),
        )
    raise ValueError(f"Unsupported handler node type: {node.node_type}")


def finalize_handler_step(node: Node, state: HandlerSpanState, *, openai_agents: bool = False) -> BaseStep:
    """Build the final validated form while retaining the provisional UUID and children."""
    children = list(state.step.spans) if isinstance(state.step, StepWithChildSpans) else None
    return build_handler_step(node, step_id=state.step.id, children=children, openai_agents=openai_agents)
