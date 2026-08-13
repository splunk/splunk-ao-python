"""W3C distributed-tracing utilities for Splunk AO."""

from collections.abc import Mapping, MutableMapping

from opentelemetry import propagate
from opentelemetry.context import Context

from splunk_ao.exceptions import SplunkAOLoggerException
from splunk_ao.logger.logger import _has_active_exportable_span_context


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
    propagate.inject(carrier)
    return carrier


def extract_tracing_context(carrier: Mapping[str, str]) -> Context:
    """Extract W3C trace context from an incoming text-map carrier."""
    normalized = {str(key).lower(): value for key, value in carrier.items()}
    return propagate.extract(normalized)
