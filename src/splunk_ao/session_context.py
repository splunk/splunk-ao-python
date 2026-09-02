"""Execution-context-local session selection and W3C baggage propagation."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from opentelemetry import baggage, propagate
from opentelemetry import context as otel_context
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context
from opentelemetry.propagators import textmap

GEN_AI_CONVERSATION_ID = "gen_ai.conversation.id"


class _SessionSelection:
    """Marker type for execution-local session selection state."""


_SESSION_UNSET = _SessionSelection()
_SESSION_CLEARED = _SessionSelection()
SessionSelection = str | _SessionSelection | None

_session_id_context: ContextVar[SessionSelection] = ContextVar("session_id_context", default=_SESSION_UNSET)


def set_session_context(session_id: str | None) -> None:
    """Set or reset the explicit session selection for this execution context.

    Passing ``None`` retains the historical reset behavior: inbound baggage and
    the logger compatibility field may be consulted again. Use
    :func:`clear_session_context` when an explicit clear must mask inbound
    baggage for the remainder of the execution context.
    """
    _session_id_context.set(_SESSION_UNSET if session_id is None else session_id)


def clear_session_context() -> None:
    """Explicitly suppress local, inbound, and compatibility session selection."""
    _session_id_context.set(_SESSION_CLEARED)


def get_session_selection() -> SessionSelection:
    """Return the raw execution-local selection for nested-context restoration."""
    return _session_id_context.get()


def restore_session_selection(selection: SessionSelection) -> None:
    """Restore a previously captured execution-local selection."""
    _session_id_context.set(selection)


def explicit_session_id(selection: SessionSelection) -> tuple[bool, str | None]:
    """Return whether a saved selection is explicit and its session value."""
    if selection is _SESSION_CLEARED:
        return True, None
    if isinstance(selection, str) and selection:
        return True, selection
    return False, None


def _baggage_session_id(context: Context | None = None) -> str | None:
    """Resolve an opaque conversation ID from baggage."""
    value = baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=context)
    return value.strip() if isinstance(value, str) and value.strip() else None


def get_effective_session_id(logger_session_id: str | None = None, context: Context | None = None) -> str | None:
    """Resolve the execution-local, inbound, or compatibility session ID."""
    local_selection = _session_id_context.get()
    if local_selection is _SESSION_CLEARED:
        return None
    if isinstance(local_selection, str) and local_selection:
        return local_selection
    baggage_session_id = _baggage_session_id(context)
    if baggage_session_id:
        return baggage_session_id
    return logger_session_id


def _context_with_conversation_id(context: Context, session_id: str | None) -> Context:
    """Return a context with the conversation baggage normalized or removed."""
    normalized = baggage.remove_baggage(GEN_AI_CONVERSATION_ID, context=context)
    if session_id:
        normalized = baggage.set_baggage(GEN_AI_CONVERSATION_ID, session_id, context=normalized)
    return normalized


class SplunkAOSessionPropagator(textmap.TextMapPropagator):
    """Preserve the configured propagator while normalizing session baggage."""

    def __init__(self, delegate: textmap.TextMapPropagator) -> None:
        self._delegate = delegate
        self._baggage = W3CBaggagePropagator()

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        getter: textmap.Getter[textmap.CarrierT] = textmap.default_getter,
    ) -> Context:
        extracted = self._delegate.extract(carrier, context=context, getter=getter)
        extracted = self._baggage.extract(carrier, context=extracted, getter=getter)
        return _context_with_conversation_id(extracted, _baggage_session_id(extracted))

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        setter: textmap.Setter[textmap.CarrierT] = textmap.default_setter,
    ) -> None:
        active = context if context is not None else otel_context.get_current()
        normalized = _context_with_conversation_id(active, get_effective_session_id(context=active))
        self._delegate.inject(carrier, context=normalized, setter=setter)
        self._baggage.inject(carrier, context=normalized, setter=setter)

    @property
    def fields(self) -> set[str]:
        return set(self._delegate.fields) | set(self._baggage.fields)


def _session_propagator() -> SplunkAOSessionPropagator:
    current = propagate.get_global_textmap()
    if isinstance(current, SplunkAOSessionPropagator):
        return current
    return SplunkAOSessionPropagator(current)


def install_session_propagator() -> None:
    """Wrap the process-global propagator with the session-aware adapter.

    The current propagator remains the delegate. Replacing the global
    propagator later also removes this adapter until this function is called
    again.
    """
    current = propagate.get_global_textmap()
    if not isinstance(current, SplunkAOSessionPropagator):
        propagate.set_global_textmap(SplunkAOSessionPropagator(current))


def inject_session_context(
    carrier: Any, context: Context | None = None, setter: textmap.Setter[Any] = textmap.default_setter
) -> None:
    """Inject configured trace context and normalized session baggage."""
    _session_propagator().inject(carrier, context=context, setter=setter)


def extract_session_context(
    carrier: Any, context: Context | None = None, getter: textmap.Getter[Any] = textmap.default_getter
) -> Context:
    """Extract configured trace context and normalize session baggage."""
    return _session_propagator().extract(carrier, context=context, getter=getter)
