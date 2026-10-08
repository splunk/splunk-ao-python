"""Context helpers for grouping spans by a simulation run."""

from contextvars import ContextVar

_simulation_run_id_context: ContextVar[str | None] = ContextVar("simulation_run_id_context", default=None)


def get_simulation_run_id() -> str | None:
    """Return the simulation run ID active in the current execution context."""
    return _simulation_run_id_context.get()
