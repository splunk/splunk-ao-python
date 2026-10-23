"""Private immutable trace declarations; never propagated as OTel context content."""

import json
from contextvars import ContextVar
from typing import Any

from opentelemetry import trace

TraceAttributes = tuple[tuple[str, str | int | tuple[str, ...]], ...]

# One content-free claim per execution context, not a process-wide trace registry.
_declared_trace_id: ContextVar[int | None] = ContextVar("splunk_ao_declared_trace_id", default=None)


def has_trace_declaration() -> bool:
    """Whether the active OTel trace was declared in this execution context."""
    current = trace.get_current_span().get_span_context()
    return current.is_valid and current.trace_id == _declared_trace_id.get()


def claim_trace(trace_id: int) -> None:
    """Remember only the current local declaration's identity."""
    _declared_trace_id.set(trace_id)


def capture_trace_attributes(**values: Any) -> TraceAttributes:
    """Freeze supplied normalized values without leaking mutable model references."""
    attributes: list[tuple[str, str | int | tuple[str, ...]]] = [("splunk_ao.trace.schema_version", 1)]
    for field, value in values.items():
        if value is None:
            continue
        if field in ("input", "redacted_input", "metadata", "dataset.metadata"):
            if isinstance(value, list):
                value = [block.model_dump(mode="json", exclude_none=True) for block in value]
            value = json.dumps(value)
        elif field == "tags":
            value = tuple(value)
        attributes.append((f"splunk_ao.trace.{field}", value))
    return tuple(attributes)
