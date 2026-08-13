"""Supported automatic OpenTelemetry export and HTTP instrumentation setup."""

from __future__ import annotations

from typing import Any, cast
from weakref import WeakSet

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from splunk_ao.otel import TracerProvider, add_splunk_ao_span_processor
from splunk_ao.session_context import install_session_propagator

_INSTALL_MESSAGE = (
    "Automatic distributed tracing requires optional dependencies. "
    "Install them with: pip install 'splunk-ao[distributed-tracing]'"
)


_client_provider_ids: dict[str, int] = {}
_instrumented_apps: set[tuple[int, int, str]] = set()
_configured_providers: WeakSet[SDKTracerProvider] = WeakSet()


def _load_instrumentors() -> dict[str, type]:
    try:
        from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor  # noqa: PLC0415
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: PLC0415
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor  # noqa: PLC0415
        from opentelemetry.instrumentation.requests import RequestsInstrumentor  # noqa: PLC0415
        from opentelemetry.instrumentation.starlette import StarletteInstrumentor  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(_INSTALL_MESSAGE) from exc

    return {
        "fastapi": FastAPIInstrumentor,
        "starlette": StarletteInstrumentor,
        "requests": RequestsInstrumentor,
        "httpx": HTTPXClientInstrumentor,
        "aiohttp-client": AioHttpClientInstrumentor,
    }


def _validate_client_ownership(names: tuple[str, ...], provider_id: int) -> None:
    """Reject provider conflicts before any instrumentation is changed."""
    for name in names:
        configured_provider_id = _client_provider_ids.get(name)
        if configured_provider_id is not None and configured_provider_id != provider_id:
            raise RuntimeError(
                f"{name} is already instrumented through Splunk AO with another tracer provider; "
                "configure each process-wide client instrumentor through one owner"
            )


def _resolve_app_framework(app: Any) -> str:
    try:
        from fastapi import FastAPI  # noqa: PLC0415
        from starlette.applications import Starlette  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(_INSTALL_MESSAGE) from exc

    if isinstance(app, FastAPI):
        framework = "fastapi"
    elif isinstance(app, Starlette):
        framework = "starlette"
    else:
        raise TypeError("app must be a FastAPI or Starlette application")
    return framework


def _instrument_app(app: Any, instrumentors: dict[str, Any], tracer_provider: TracerProvider) -> None:
    framework = _resolve_app_framework(app)

    key = (id(app), id(tracer_provider), framework)
    if key in _instrumented_apps:
        return
    instrumentors[framework].instrument_app(app, tracer_provider=tracer_provider)
    _instrumented_apps.add(key)


def _instrument_supported_transports(
    *,
    instrumentors: dict[str, type],
    tracer_provider: TracerProvider,
    app: Any | None,
    instrument_requests: bool,
    instrument_httpx: bool,
    instrument_aiohttp_client: bool,
) -> None:
    clients = {"requests": instrument_requests, "httpx": instrument_httpx, "aiohttp-client": instrument_aiohttp_client}
    enabled_clients = tuple(name for name, enabled in clients.items() if enabled)
    provider_id = id(tracer_provider)
    _validate_client_ownership(enabled_clients, provider_id)

    if app is not None:
        _instrument_app(app, instrumentors, tracer_provider)

    for name in enabled_clients:
        if _client_provider_ids.get(name) == provider_id:
            continue
        instrumentors[name]().instrument(tracer_provider=tracer_provider)
        _client_provider_ids[name] = provider_id

    install_session_propagator()


def instrument_distributed_tracing(
    *,
    tracer_provider: TracerProvider | None = None,
    app: Any | None = None,
    instrument_requests: bool = True,
    instrument_httpx: bool = True,
    instrument_aiohttp_client: bool = True,
) -> None:
    """Enable supported upstream OTel server and client instrumentation.

    Parameters
    ----------
    tracer_provider : TracerProvider | None
        Caller-owned provider used by the upstream instrumentors. The current
        global provider is used when omitted; this function never replaces it.
    app : Any | None
        Optional FastAPI or Starlette application to instrument.
    instrument_requests : bool
        Whether to instrument process-wide Requests clients.
    instrument_httpx : bool
        Whether to instrument process-wide HTTPX sync and async clients.
    instrument_aiohttp_client : bool
        Whether to instrument process-wide aiohttp clients.

    Notes
    -----
    Client instrumentation is process-wide. Configure each supported client
    through one owner. The caller also owns provider shutdown.
    """
    instrumentors = _load_instrumentors()
    resolved_provider = tracer_provider or cast(TracerProvider, trace.get_tracer_provider())
    _instrument_supported_transports(
        instrumentors=instrumentors,
        tracer_provider=resolved_provider,
        app=app,
        instrument_requests=instrument_requests,
        instrument_httpx=instrument_httpx,
        instrument_aiohttp_client=instrument_aiohttp_client,
    )


def configure_distributed_tracing(
    *,
    tracer_provider: SDKTracerProvider | None = None,
    app: Any | None = None,
    instrument_requests: bool = True,
    instrument_httpx: bool = True,
    instrument_aiohttp_client: bool = True,
) -> SDKTracerProvider:
    """Configure Splunk AO export and supported automatic HTTP propagation.

    Parameters
    ----------
    tracer_provider : SDKTracerProvider | None
        Optional application-owned OpenTelemetry SDK provider. A new provider
        is created when omitted. This function never replaces the process-global
        provider.
    app : Any | None
        Optional FastAPI or Starlette application to instrument.
    instrument_requests : bool
        Whether to instrument process-wide Requests clients.
    instrument_httpx : bool
        Whether to instrument process-wide HTTPX sync and async clients.
    instrument_aiohttp_client : bool
        Whether to instrument process-wide aiohttp clients.

    Returns
    -------
    SDKTracerProvider
        The configured provider. The caller owns it and must call ``shutdown()``
        during process teardown.

    Notes
    -----
    Repeated calls with the same provider do not attach another Splunk AO span
    processor. Use :func:`instrument_distributed_tracing` instead when export
    has already been configured separately on the provider.
    """
    # Resolve optional imports before constructing a processor and its worker so
    # a missing extra cannot leave partially configured background resources.
    instrumentors = _load_instrumentors()
    resolved_provider = tracer_provider or SDKTracerProvider()
    clients = {"requests": instrument_requests, "httpx": instrument_httpx, "aiohttp-client": instrument_aiohttp_client}
    enabled_clients = tuple(name for name, enabled in clients.items() if enabled)
    _validate_client_ownership(enabled_clients, id(resolved_provider))
    if app is not None:
        _resolve_app_framework(app)

    if resolved_provider not in _configured_providers:
        add_splunk_ao_span_processor(resolved_provider)
        _configured_providers.add(resolved_provider)

    _instrument_supported_transports(
        instrumentors=instrumentors,
        tracer_provider=resolved_provider,
        app=app,
        instrument_requests=instrument_requests,
        instrument_httpx=instrument_httpx,
        instrument_aiohttp_client=instrument_aiohttp_client,
    )
    return resolved_provider
