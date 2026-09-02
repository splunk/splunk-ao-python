"""W3C distributed-tracing utilities for Splunk AO."""

from collections.abc import Mapping, MutableMapping
from typing import Any

from opentelemetry.context import Context
from opentelemetry.propagators import textmap

from splunk_ao.exceptions import SplunkAOLoggerException
from splunk_ao.logger.logger import _has_active_exportable_span_context
from splunk_ao.session_context import extract_session_context, inject_session_context


class _CaseInsensitiveGetter(textmap.Getter[Mapping[str, str]]):
    """Read all case-insensitive carrier values without collapsing duplicates."""

    def get(self, carrier: Mapping[str, str], key: str) -> list[str] | None:
        getlist = getattr(carrier, "getlist", None)
        if callable(getlist):
            values = getlist(key)
            normalized = [str(value) for value in values]
            if key.lower() == "baggage" and len(normalized) > 1:
                return [",".join(normalized)]
            return normalized or None
        values = [str(value) for candidate, value in carrier.items() if str(candidate).lower() == key.lower()]
        if key.lower() == "baggage" and len(values) > 1:
            return [",".join(values)]
        return values or None

    def keys(self, carrier: Mapping[str, str]) -> list[str]:
        return [str(key) for key in carrier]


_case_insensitive_getter: textmap.Getter[Any] = _CaseInsensitiveGetter()


def get_tracing_headers(carrier: MutableMapping[str, str] | None = None) -> MutableMapping[str, str]:
    """Inject the active operation's W3C trace context into a carrier.

    Parameters
    ----------
    carrier : MutableMapping[str, str] | None
        Existing carrier to populate. A new dictionary is created when omitted.

    Returns
    -------
    MutableMapping[str, str]
        The supplied carrier, or a new dictionary, containing ``traceparent``
        and any other fields owned by the configured OTel propagator.

    Raises
    ------
    SplunkAOLoggerException
        If there is no active exportable operation span. The internal Splunk AO
        trace envelope is not exportable and cannot be used as a wire parent.
    """
    if not _has_active_exportable_span_context():
        raise SplunkAOLoggerException("Distributed tracing requires an active exportable operation span")

    if carrier is None:
        carrier = {}
    inject_session_context(carrier)
    return carrier


def extract_tracing_context(carrier: Mapping[str, str]) -> Context:
    """Extract W3C trace context from an incoming text-map carrier."""
    return extract_session_context(carrier, getter=_case_insensitive_getter)
