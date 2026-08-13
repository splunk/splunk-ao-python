from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import FastAPI
from opentelemetry import baggage, context, propagate, trace
from opentelemetry.context import Context
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagators import textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
from starlette.applications import Starlette
from starlette.testclient import TestClient

from splunk_ao import instrument_distributed_tracing
from splunk_ao.http_instrumentation import _client_provider_ids, _instrumented_apps, _load_instrumentors
from splunk_ao.session_context import GEN_AI_CONVERSATION_ID, SplunkAOSessionPropagator, _session_id_context


class FakeTracerProvider:
    def add_span_processor(self, span_processor: Any) -> None:
        return None

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: Any | None = None,
    ) -> MagicMock:
        return MagicMock()


class CustomPropagator(textmap.TextMapPropagator):
    def extract(
        self,
        carrier: textmap.CarrierT,
        context: context.Context | None = None,
        getter: textmap.Getter[textmap.CarrierT] = textmap.default_getter,
    ) -> context.Context:
        return context if context is not None else Context()

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: context.Context | None = None,
        setter: textmap.Setter[textmap.CarrierT] = textmap.default_setter,
    ) -> None:
        setter.set(carrier, "x-custom-context", "preserved")

    @property
    def fields(self) -> set[str]:
        return {"x-custom-context"}


@dataclass
class RecordingInstrumentor:
    instrument_calls: list[dict[str, Any]]
    app_calls: list[tuple[Any, dict[str, Any]]]

    def instrument(self, **kwargs: Any) -> None:
        self.instrument_calls.append(kwargs)

    def instrument_app(self, app: Any, **kwargs: Any) -> None:
        self.app_calls.append((app, kwargs))


def instrumentor_type(recorder: RecordingInstrumentor) -> type:
    class Instrumentor:
        def __new__(cls) -> RecordingInstrumentor:
            return recorder

        @classmethod
        def instrument_app(cls, app: Any, **kwargs: Any) -> None:
            recorder.instrument_app(app, **kwargs)

    return Instrumentor


@pytest.fixture(autouse=True)
def reset_instrumentation_state() -> Generator[None, None, None]:
    previous_propagator = propagate.get_global_textmap()
    session_token = _session_id_context.set(None)
    _client_provider_ids.clear()
    _instrumented_apps.clear()
    try:
        yield
    finally:
        _client_provider_ids.clear()
        _instrumented_apps.clear()
        propagate.set_global_textmap(previous_propagator)
        _session_id_context.reset(session_token)


@pytest.fixture
def instrumentors() -> tuple[dict[str, type], dict[str, RecordingInstrumentor]]:
    recorders = {
        name: RecordingInstrumentor(instrument_calls=[], app_calls=[])
        for name in ("fastapi", "starlette", "requests", "httpx", "aiohttp_client")
    }
    types = {
        "fastapi": instrumentor_type(recorders["fastapi"]),
        "starlette": instrumentor_type(recorders["starlette"]),
        "requests": instrumentor_type(recorders["requests"]),
        "httpx": instrumentor_type(recorders["httpx"]),
        "aiohttp-client": instrumentor_type(recorders["aiohttp_client"]),
    }
    return types, recorders


def test_missing_extra_fails_before_instrumentation_or_propagator_change() -> None:
    previous_propagator = propagate.get_global_textmap()

    with (
        patch("splunk_ao.http_instrumentation._load_instrumentors", side_effect=ImportError("install the extra")),
        pytest.raises(ImportError, match="install the extra"),
    ):
        instrument_distributed_tracing(tracer_provider=FakeTracerProvider())

    assert _client_provider_ids == {}
    assert _instrumented_apps == set()
    assert propagate.get_global_textmap() is previous_propagator


def test_distributed_tracing_extra_loads_every_supported_upstream_instrumentor() -> None:
    assert set(_load_instrumentors()) == {"fastapi", "starlette", "requests", "httpx", "aiohttp-client"}


@pytest.mark.parametrize(("app", "expected"), [(FastAPI(), "fastapi"), (Starlette(), "starlette")])
def test_instruments_matching_app_and_every_enabled_client_once(
    app: Any, expected: str, instrumentors: tuple[dict[str, type], dict[str, RecordingInstrumentor]]
) -> None:
    types, recorders = instrumentors
    provider = FakeTracerProvider()

    with patch("splunk_ao.http_instrumentation._load_instrumentors", return_value=types):
        instrument_distributed_tracing(tracer_provider=provider, app=app)
        instrument_distributed_tracing(tracer_provider=provider, app=app)

    assert recorders[expected].app_calls == [(app, {"tracer_provider": provider})]
    other_framework = "starlette" if expected == "fastapi" else "fastapi"
    assert recorders[other_framework].app_calls == []
    assert recorders["requests"].instrument_calls == [{"tracer_provider": provider}]
    assert recorders["httpx"].instrument_calls == [{"tracer_provider": provider}]
    assert recorders["aiohttp_client"].instrument_calls == [{"tracer_provider": provider}]
    assert isinstance(propagate.get_global_textmap(), SplunkAOSessionPropagator)


def test_disabled_clients_are_not_instrumented(
    instrumentors: tuple[dict[str, type], dict[str, RecordingInstrumentor]],
) -> None:
    types, recorders = instrumentors

    with patch("splunk_ao.http_instrumentation._load_instrumentors", return_value=types):
        instrument_distributed_tracing(
            tracer_provider=FakeTracerProvider(),
            instrument_requests=False,
            instrument_httpx=False,
            instrument_aiohttp_client=False,
        )

    assert all(not recorder.instrument_calls for recorder in recorders.values())


def test_provider_conflict_fails_before_partial_instrumentation(
    instrumentors: tuple[dict[str, type], dict[str, RecordingInstrumentor]],
) -> None:
    types, recorders = instrumentors
    first_provider = FakeTracerProvider()
    second_provider = FakeTracerProvider()

    with patch("splunk_ao.http_instrumentation._load_instrumentors", return_value=types):
        instrument_distributed_tracing(tracer_provider=first_provider)
        with pytest.raises(RuntimeError, match="another tracer provider"):
            instrument_distributed_tracing(tracer_provider=second_provider, app=FastAPI())

    assert recorders["fastapi"].app_calls == []
    assert all(len(recorders[name].instrument_calls) == 1 for name in ("requests", "httpx", "aiohttp_client"))


def test_uses_current_provider_without_replacing_it(
    instrumentors: tuple[dict[str, type], dict[str, RecordingInstrumentor]],
) -> None:
    types, recorders = instrumentors
    provider = FakeTracerProvider()

    with (
        patch("splunk_ao.http_instrumentation._load_instrumentors", return_value=types),
        patch("splunk_ao.http_instrumentation.trace.get_tracer_provider", return_value=provider),
        patch.object(trace, "set_tracer_provider") as set_provider,
    ):
        instrument_distributed_tracing()

    set_provider.assert_not_called()
    assert recorders["requests"].instrument_calls == [{"tracer_provider": provider}]


def test_installed_global_propagator_injects_only_conversation_session(
    instrumentors: tuple[dict[str, type], dict[str, RecordingInstrumentor]],
) -> None:
    types, _ = instrumentors
    span_context = SpanContext(
        trace_id=0x4BF92F3577B34DA6A3CE929D0E0E4736,
        span_id=0x00F067AA0BA902B7,
        is_remote=False,
        trace_flags=TraceFlags.SAMPLED,
    )
    token = context.attach(trace.set_span_in_context(NonRecordingSpan(span_context)))
    _session_id_context.set("conversation-123")
    try:
        with patch("splunk_ao.http_instrumentation._load_instrumentors", return_value=types):
            instrument_distributed_tracing(
                tracer_provider=FakeTracerProvider(),
                instrument_requests=False,
                instrument_httpx=False,
                instrument_aiohttp_client=False,
            )
        carrier: dict[str, str] = {}
        propagate.inject(carrier)
    finally:
        context.detach(token)

    extracted = propagate.extract(carrier)
    assert baggage.get_baggage(GEN_AI_CONVERSATION_ID, context=extracted) == "conversation-123"
    assert "splunk_ao.session.id" not in carrier.get("baggage", "")


def test_session_adapter_preserves_application_configured_propagator(
    instrumentors: tuple[dict[str, type], dict[str, RecordingInstrumentor]],
) -> None:
    types, _ = instrumentors
    custom = CustomPropagator()
    propagate.set_global_textmap(custom)

    with patch("splunk_ao.http_instrumentation._load_instrumentors", return_value=types):
        instrument_distributed_tracing(
            tracer_provider=FakeTracerProvider(),
            instrument_requests=False,
            instrument_httpx=False,
            instrument_aiohttp_client=False,
        )

    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    installed = propagate.get_global_textmap()
    assert carrier["x-custom-context"] == "preserved"
    assert isinstance(installed, SplunkAOSessionPropagator)
    assert installed._delegate is custom


def test_real_requests_instrumentor_injects_trace_and_conversation_without_manual_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: dict[str, str] = {}

    def capture_send(session: requests.Session, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        del session, kwargs
        captured_headers.update(request.headers)
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response.url = request.url
        return response

    monkeypatch.setattr(requests.Session, "send", capture_send)
    provider = TracerProvider()
    requests_instrumentor = RequestsInstrumentor()
    try:
        instrument_distributed_tracing(
            tracer_provider=provider, instrument_httpx=False, instrument_aiohttp_client=False
        )
        _session_id_context.set("conversation-outbound")
        with provider.get_tracer(__name__).start_as_current_span("caller") as caller:
            response = requests.get("https://example.test/automatic-context", timeout=1)
            expected_trace_id = f"{caller.get_span_context().trace_id:032x}"

        assert response.status_code == 200
        assert captured_headers["traceparent"].split("-")[1] == expected_trace_id
        assert captured_headers["baggage"] == "gen_ai.conversation.id=conversation-outbound"
        assert "splunk_ao.session.id" not in captured_headers["baggage"]
    finally:
        requests_instrumentor.uninstrument()
        provider.shutdown()


def test_real_fastapi_instrumentor_extracts_trace_and_conversation_without_sdk_middleware() -> None:
    expected_trace_id = 0x4BF92F3577B34DA6A3CE929D0E0E4736
    observed: dict[str, Any] = {}
    provider = TracerProvider()
    app = FastAPI()

    @app.get("/automatic-context")
    def automatic_context() -> dict[str, bool]:
        observed["trace_id"] = trace.get_current_span().get_span_context().trace_id
        observed["conversation_id"] = baggage.get_baggage(GEN_AI_CONVERSATION_ID)
        return {"ok": True}

    try:
        instrument_distributed_tracing(
            tracer_provider=provider,
            app=app,
            instrument_requests=False,
            instrument_httpx=False,
            instrument_aiohttp_client=False,
        )
        with TestClient(app) as client:
            response = client.get(
                "/automatic-context",
                headers={
                    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                    "baggage": "gen_ai.conversation.id=conversation-inbound",
                },
            )

        assert response.json() == {"ok": True}
        assert observed == {"trace_id": expected_trace_id, "conversation_id": "conversation-inbound"}
    finally:
        FastAPIInstrumentor.uninstrument_app(app)
        provider.shutdown()
