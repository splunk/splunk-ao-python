from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from splunk_ao.schema.handlers import Node
from splunk_ao.utils.serialization import EventSerializer
from splunk_ao.utils.uuid_utils import convert_uuid_if_uuid7

_logger = logging.getLogger(__name__)


def get_agent_name(parent_run_id: UUID | None, node_name: str, nodes: dict[str, Node]) -> str:
    if parent_run_id is not None:
        # Convert UUID7 to UUID4 if needed
        parent_run_id = convert_uuid_if_uuid7(parent_run_id) or parent_run_id
        parent = nodes.get(str(parent_run_id))
        if parent:
            return parent.span_params["name"] + ":" + node_name
    return node_name


def is_agent_node(node_name: str) -> bool:
    return node_name.lower() in ["langgraph", "agent"]


def update_root_to_agent(parent_run_id: UUID | None, metadata: dict[str, Any], parent_node: Node | None) -> None:
    """Update the parent node to be an agent if it is a root-level chain and has LangGraph metadata in the children.

    Parameters
    ----------
    parent_run_id : Optional[UUID]
    metadata : dict[str, Any]
    parent_node : Optional[Node]
    """
    # Check if this node has LangGraph metadata - if so, its parent might be an agent
    # Only mark as agent if parent is a root-level chain (no grandparent)
    if parent_run_id and metadata and any(key.startswith("langgraph_") for key in metadata):
        # Only convert to agent if parent is a root-level chain (no parent of its own)
        if parent_node and parent_node.node_type == "chain" and parent_node.parent_run_id is None:
            parent_node.node_type = "agent"


@dataclass
class LLMEndResult:
    output: Any
    num_input_tokens: int | None
    num_output_tokens: int | None
    total_tokens: int | None
    image_input_tokens: int | None = None
    audio_input_tokens: int | None = None
    audio_output_tokens: int | None = None
    image_output_tokens: int | None = None


_MODALITIES = ("image", "audio")


def _modality_counts_from_details(details: Any) -> dict[str, int]:
    """Read image/audio counts from a LangChain ``input_token_details`` / ``output_token_details`` dict.

    Other keys such as ``cache_read`` or ``reasoning`` are not a modality breakdown and are ignored.
    """
    if not isinstance(details, dict):
        return {}
    return {modality: details[modality] for modality in _MODALITIES if isinstance(details.get(modality), int)}


def _modality_counts_from_entries(entries: Any) -> dict[str, int]:
    """Read image/audio counts from a Gemini ``[{"modality": "AUDIO", "token_count": N}, ...]`` list.

    A non-empty list is a breakdown even when it holds only text, so absent modalities count as 0.
    """
    if not isinstance(entries, list) or not entries:
        return {}
    counts = dict.fromkeys(_MODALITIES, 0)
    for entry in entries:
        if isinstance(entry, dict):
            modality = str(entry.get("modality", "")).lower()
            if modality in counts:
                counts[modality] += entry.get("token_count") or 0
    return counts


def _first_per_modality(*sources: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for source in sources:
        for modality, count in source.items():
            merged.setdefault(modality, count)
    return merged


def _extract_modality_breakdown(generation: Any) -> tuple[dict[str, int], dict[str, int]] | None:
    """Extract per-modality (input, output) token counts from a LangChain generation or message.

    Surfaces are checked in priority order, first value wins per modality:

    1. ``message.usage_metadata`` ``input_token_details`` / ``output_token_details``.
    2. ``message.response_metadata`` ``prompt_tokens_details`` / ``candidates_tokens_details`` (raw Gemini lists).
    3. ``message.response_metadata["usage_metadata"]``, for providers that nest usage there.

    Returns ``None`` when no surface carries a breakdown, so callers can tell "unknown" from "zero".
    """
    message = getattr(generation, "message", None) or generation
    usage = getattr(message, "usage_metadata", None)
    usage = usage if isinstance(usage, dict) else {}
    response_metadata = getattr(message, "response_metadata", None)
    response_metadata = response_metadata if isinstance(response_metadata, dict) else {}
    nested_usage = response_metadata.get("usage_metadata")
    nested_usage = nested_usage if isinstance(nested_usage, dict) else {}

    input_counts = _first_per_modality(
        _modality_counts_from_details(usage.get("input_token_details")),
        _modality_counts_from_entries(response_metadata.get("prompt_tokens_details")),
        _modality_counts_from_details(nested_usage.get("input_token_details")),
    )
    output_counts = _first_per_modality(
        _modality_counts_from_details(usage.get("output_token_details")),
        _modality_counts_from_entries(response_metadata.get("candidates_tokens_details")),
        _modality_counts_from_details(nested_usage.get("output_token_details")),
    )
    if not input_counts and not output_counts:
        return None
    return input_counts, output_counts


def parse_llm_result(response: Any) -> LLMEndResult:
    """Extract serialized output and token metrics from a LangChain LLMResult.

    Handles three token-usage sources (checked in order):
    1. ``response.llm_output["token_usage"]`` with OpenAI keys (``prompt_tokens`` / ``completion_tokens``).
    2. Same dict with GCP Vertex AI keys (``input_tokens`` / ``output_tokens``).
    3. ``ChatGeneration.message.usage_metadata`` when ``llm_output`` carries no usage.

    Also extracts the per-modality (image/audio) breakdown that Gemini reports; see
    ``_extract_modality_breakdown``.

    Parameters
    ----------
    response
        A ``langchain_core.outputs.LLMResult`` (typed as ``Any`` to avoid import).
    """
    token_usage: dict[str, Any] = response.llm_output.get("token_usage", {}) if response.llm_output else {}

    first_message = None
    try:
        flattened_messages = [message for batch in response.generations for message in batch]
        first_message = flattened_messages[0] if flattened_messages else None
        if first_message is None:
            # Empty generations - fall back to stringified representation
            output = str(response.generations)
        else:
            output = json.loads(json.dumps(first_message, cls=EventSerializer))
            if not token_usage and hasattr(first_message, "message"):
                message_token_usage = getattr(getattr(first_message, "message", {}), "usage_metadata", None)
                if message_token_usage:
                    token_usage = {**token_usage, **message_token_usage}
    except Exception as e:
        _logger.warning(f"Failed to serialize LLM output: {e}")
        output = str(response.generations)

    breakdown = None
    if first_message is not None:
        try:
            breakdown = _extract_modality_breakdown(first_message)
        except Exception as e:
            _logger.debug(f"Failed to extract per-modality token counts: {e}")
    # With a breakdown, a modality it does not mention is 0; without one, all four stay unknown.
    input_counts, output_counts = breakdown if breakdown is not None else ({}, {})
    default = 0 if breakdown is not None else None

    return LLMEndResult(
        output=output,
        num_input_tokens=token_usage.get("prompt_tokens") or token_usage.get("input_tokens"),
        num_output_tokens=token_usage.get("completion_tokens") or token_usage.get("output_tokens"),
        total_tokens=token_usage.get("total_tokens"),
        image_input_tokens=input_counts.get("image", default),
        audio_input_tokens=input_counts.get("audio", default),
        audio_output_tokens=output_counts.get("audio", default),
        image_output_tokens=output_counts.get("image", default),
    )
