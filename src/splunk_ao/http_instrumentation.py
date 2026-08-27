"""Supported automatic OpenTelemetry export and HTTP instrumentation setup."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, cast
from weakref import WeakKeyDictionary, WeakSet

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from splunk_ao.otel import TracerProvider, add_splunk_ao_span_processor
from splunk_ao.session_context import install_session_propagator

_logger = logging.getLogger(__name__)

_INSTALL_MESSAGE = (
    "Automatic distributed tracing requires optional dependencies. "
    "Install them with: pip install 'splunk-ao[distributed-tracing]'"
)


# Supported client instrumentors are process-wide. Retain their bounded owner
# objects so garbage collection cannot silently transfer installed wrappers.
_client_providers: dict[str, TracerProvider] = {}
_instrumented_apps: WeakKeyDictionary[Any, tuple[TracerProvider, str]] = WeakKeyDictionary()
_configured_providers: WeakSet[SDKTracerProvider] = WeakSet()

_INSTRUMENTOR_IMPORTS: dict[str, tuple[str, str]] = {
    "fastapi": ("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor"),
    "starlette": ("opentelemetry.instrumentation.starlette", "StarletteInstrumentor"),
    "requests": ("opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
    "httpx": ("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
    "aiohttp-client": ("opentelemetry.instrumentation.aiohttp_client", "AioHttpClientInstrumentor"),
}


def _load_instrumentors(names: tuple[str, ...] | None = None) -> dict[str, type[Any]]:
    """Import only the instrumentors needed for the requested components."""
    requested = tuple(_INSTRUMENTOR_IMPORTS) if names is None else names
    resolved: dict[str, type[Any]] = {}
    for name in requested:
        module_name, attribute = _INSTRUMENTOR_IMPORTS[name]
        try:
            resolved[name] = getattr(import_module(module_name), attribute)
        except (AttributeError, ImportError) as exc:
            raise ImportError(f"{_INSTALL_MESSAGE} (missing support for {name})") from exc
    return resolved


def _validate_client_ownership(names: tuple[str, ...], tracer_provider: TracerProvider) -> None:
    """Reject provider conflicts before any instrumentation is changed."""
    for name in names:
        configured_provider = _client_providers.get(name)
        if configured_provider is not None and configured_provider is not tracer_provider:
            raise RuntimeError(
                f"{name} is already instrumented through Splunk AO with another tracer provider; "
                "configure each process-wide client instrumentor through one owner"
            )


def _resolve_app_framework(app: Any) -> str:
    try:
        from starlette.applications import Starlette  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(_INSTALL_MESSAGE) from exc

    fastapi_type: type[Any] | None
    try:
        from fastapi import FastAPI  # noqa: PLC0415

        fastapi_type = FastAPI
    except ImportError:
        fastapi_type = None

    if fastapi_type is not None and isinstance(app, fastapi_type):
        framework = "fastapi"
    elif isinstance(app, Starlette):
        framework = "starlette"
    else:
        raise TypeError("app must be a FastAPI or Starlette application")
    return framework


def _validate_app_ownership(app: Any, tracer_provider: TracerProvider) -> str:
    """Resolve the framework and reject ownership conflicts without mutation."""
    framework = _resolve_app_framework(app)
    configured_owner = _instrumented_apps.get(app)
    if configured_owner is not None:
        configured_provider, configured_framework = configured_owner
        if configured_provider is not tracer_provider or configured_framework != framework:
            raise RuntimeError(
                f"{framework} app is already instrumented through Splunk AO with another tracer provider"
            )
    return framework


def _instrument_app(app: Any, framework: str, instrumentors: dict[str, Any], tracer_provider: TracerProvider) -> bool:
    if app in _instrumented_apps:
        return False
    instrumentors[framework].instrument_app(app, tracer_provider=tracer_provider)
    _instrumented_apps[app] = (tracer_provider, framework)
    return True


@dataclass
class _InstrumentationChanges:
    """Components installed by one facade invocation and safe to roll back."""

    tracer_provider: TracerProvider
    clients: list[tuple[str, Any]] = field(default_factory=list)
    app: Any | None = None
    app_framework: str | None = None
    app_instrumentor: Any | None = None

    def rollback(self) -> None:
        """Undo only components installed by this invocation."""
        for name, instrumentor in reversed(self.clients):
            try:
                instrumentor.uninstrument()
            except Exception:
                _logger.warning("Failed to roll back %s instrumentation", name, exc_info=True)
            finally:
                if _client_providers.get(name) is self.tracer_provider:
                    _client_providers.pop(name, None)

        if self.app is not None and self.app_framework is not None and self.app_instrumentor is not None:
            try:
                self.app_instrumentor.uninstrument_app(self.app)
            except Exception:
                _logger.warning("Failed to roll back %s application instrumentation", self.app_framework, exc_info=True)
            finally:
                configured_owner = _instrumented_apps.get(self.app)
                if configured_owner is not None and configured_owner[0] is self.tracer_provider:
                    _instrumented_apps.pop(self.app, None)


def _instrument_supported_transports(
    *,
    instrumentors: dict[str, type],
    tracer_provider: TracerProvider,
    app: Any | None,
    app_framework: str | None,
    instrument_requests: bool,
    instrument_httpx: bool,
    instrument_aiohttp_client: bool,
) -> _InstrumentationChanges:
    clients = {"requests": instrument_requests, "httpx": instrument_httpx, "aiohttp-client": instrument_aiohttp_client}
    enabled_clients = tuple(name for name, enabled in clients.items() if enabled)
    _validate_client_ownership(enabled_clients, tracer_provider)
    changes = _InstrumentationChanges(tracer_provider=tracer_provider)
    try:
        if app is not None and app_framework is not None:
            if _instrument_app(app, app_framework, instrumentors, tracer_provider):
                changes.app = app
                changes.app_framework = app_framework
                changes.app_instrumentor = instrumentors[app_framework]

        for name in enabled_clients:
            if _client_providers.get(name) is tracer_provider:
                continue
            instrumentor = instrumentors[name]()
            instrumentor.instrument(tracer_provider=tracer_provider)
            _client_providers[name] = tracer_provider
            changes.clients.append((name, instrumentor))
    except Exception:
        changes.rollback()
        raise
    return changes


def _requested_instrumentors(
    *, app_framework: str | None, instrument_requests: bool, instrument_httpx: bool, instrument_aiohttp_client: bool
) -> tuple[str, ...]:
    requested: list[str] = []
    if app_framework is not None:
        requested.append(app_framework)
    if instrument_requests:
        requested.append("requests")
    if instrument_httpx:
        requested.append("httpx")
    if instrument_aiohttp_client:
        requested.append("aiohttp-client")
    return tuple(requested)


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
    through one owner. The caller also owns provider shutdown. This function
    wraps the current process-global text-map propagator so explicit Splunk AO
    sessions can use W3C baggage. Install any custom global propagator before
    calling this function; replacing it afterward removes the session adapter.
    """
    resolved_provider = tracer_provider or cast(TracerProvider, trace.get_tracer_provider())
    app_framework = _validate_app_ownership(app, resolved_provider) if app is not None else None
    requested = _requested_instrumentors(
        app_framework=app_framework,
        instrument_requests=instrument_requests,
        instrument_httpx=instrument_httpx,
        instrument_aiohttp_client=instrument_aiohttp_client,
    )
    instrumentors = _load_instrumentors(requested)
    changes = _instrument_supported_transports(
        instrumentors=instrumentors,
        tracer_provider=resolved_provider,
        app=app,
        app_framework=app_framework,
        instrument_requests=instrument_requests,
        instrument_httpx=instrument_httpx,
        instrument_aiohttp_client=instrument_aiohttp_client,
    )
    try:
        install_session_propagator()
    except Exception:
        changes.rollback()
        raise


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
    has already been configured separately on the provider. This function also
    wraps the current process-global text-map propagator for session baggage.
    Install a custom global propagator first; replacing it afterward removes
    the session adapter.
    """
    resolved_provider = tracer_provider or SDKTracerProvider()
    app_framework = _validate_app_ownership(app, resolved_provider) if app is not None else None
    requested = _requested_instrumentors(
        app_framework=app_framework,
        instrument_requests=instrument_requests,
        instrument_httpx=instrument_httpx,
        instrument_aiohttp_client=instrument_aiohttp_client,
    )
    instrumentors = _load_instrumentors(requested)
    changes = _instrument_supported_transports(
        instrumentors=instrumentors,
        tracer_provider=resolved_provider,
        app=app,
        app_framework=app_framework,
        instrument_requests=instrument_requests,
        instrument_httpx=instrument_httpx,
        instrument_aiohttp_client=instrument_aiohttp_client,
    )
    try:
        if resolved_provider not in _configured_providers:
            add_splunk_ao_span_processor(resolved_provider)
            _configured_providers.add(resolved_provider)
        install_session_propagator()
    except Exception:
        changes.rollback()
        raise
    return resolved_provider
