"""Request-local session context and W3C baggage propagation."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from opentelemetry import baggage, propagate
from opentelemetry import context as otel_context
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context
from opentelemetry.propagators import textmap

GEN_AI_CONVERSATION_ID = "gen_ai.conversation.id"

_session_id_context: ContextVar[str | None] = ContextVar("session_id_context", default=None)


def set_session_context(session_id: str | None) -> None:
    """Set the request-local explicit session selection."""
    _session_id_context.set(session_id)


def _baggage_session_id(context: Context | None = None) -> str | None:
    """Resolve an opaque conversation ID from baggage."""
    value = baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=context)
    return value.strip() if isinstance(value, str) and value.strip() else None


def get_effective_session_id(logger_session_id: str | None = None, context: Context | None = None) -> str | None:
    """Resolve the request-local, inbound, or compatibility session ID."""
    local_session_id = _session_id_context.get(None)
    if local_session_id:
        return local_session_id
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
    """Install the session-aware adapter without replacing its delegate."""
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
