"""Context helpers for grouping spans by a simulation run."""

from contextvars import ContextVar

from opentelemetry import baggage
from opentelemetry.context import Context

from splunk_ao.converter.attribute_mapping import SPLUNK_AO_SIMULATION_RUN_ID

_simulation_run_id_context: ContextVar[str | None] = ContextVar("simulation_run_id_context", default=None)


def validate_simulation_run_id(simulation_run_id: object) -> str:
    """Validate a public simulation run ID and return it unchanged."""
    if not isinstance(simulation_run_id, str) or not simulation_run_id.strip():
        raise ValueError("simulation_run_id must be a non-empty string")
    return simulation_run_id


def get_baggage_simulation_run_id(context: Context | None = None) -> str | None:
    """Return a non-empty simulation run ID from W3C baggage."""
    value = baggage.get_baggage(SPLUNK_AO_SIMULATION_RUN_ID, context=context)
    return value.strip() if isinstance(value, str) and value.strip() else None


def get_simulation_run_id(context: Context | None = None) -> str | None:
    """Resolve the local simulation run ID, then the inbound baggage value."""
    local_value = _simulation_run_id_context.get()
    return local_value if local_value is not None else get_baggage_simulation_run_id(context)
