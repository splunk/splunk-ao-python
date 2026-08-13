"""Tests for W3C tracing middleware."""

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan

from splunk_ao import get_tracing_headers
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.middleware import TracingMiddleware, get_request_logger


class RecordingSink:
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def emit(self, span: ReadableSpan) -> None:
        self.spans.append(span)

    def force_flush(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None


@pytest.fixture
def app_factory(monkeypatch: pytest.MonkeyPatch):
    loggers: list[SplunkAOLogger] = []
    sinks: list[RecordingSink] = []

    def logger_factory() -> SplunkAOLogger:
        sink = RecordingSink()
        logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
        loggers.append(logger)
        sinks.append(sink)
        return logger

    monkeypatch.setattr("splunk_ao.middleware.tracing.SplunkAOLogger", logger_factory)

    def make_app(*, fail: bool = False) -> FastAPI:
        app = FastAPI()
        app.add_middleware(TracingMiddleware)

        @app.get("/test")
        async def endpoint() -> dict[str, Any]:
            logger = get_request_logger()
            try:
                logger.start_trace(input="request", name="request")
                operation = logger.add_workflow_span(input="work", name="operation")
                ids = logger._otel_ids[operation.id]
                outbound = get_tracing_headers()
                if fail:
                    raise RuntimeError("request failed")
                logger.conclude(output="done")
                logger.conclude(output="complete")
                return {
                    "trace_id": format(ids.span_context.trace_id, "032x"),
                    "span_id": format(ids.span_context.span_id, "016x"),
                    "parent_span_id": (
                        format(ids.parent_span_context.span_id, "016x") if ids.parent_span_context is not None else None
                    ),
                    "outbound": outbound,
                }
            finally:
                logger.terminate()

        return app

    return make_app, loggers, sinks


def test_middleware_and_request_logger_continue_w3c_parent(app_factory) -> None:
    make_app, _, sinks = app_factory
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    parent_id = "00f067aa0ba902b7"
    response = TestClient(make_app()).get(
        "/test", headers={"traceparent": f"00-{trace_id}-{parent_id}-01", "tracestate": "vendor=value"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == trace_id
    assert data["outbound"]["tracestate"] == "vendor=value"
    [exported] = sinks[0].spans
    assert exported.context.trace_id == int(trace_id, 16)
    assert exported.parent.span_id == int(parent_id, 16)


def test_middleware_without_header_starts_new_trace_and_does_not_leak(app_factory) -> None:
    make_app, _, sinks = app_factory
    client = TestClient(make_app())
    first = client.get(
        "/test", headers={"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
    ).json()
    second = client.get("/test").json()

    assert first["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert second["trace_id"] != first["trace_id"]
    [first_exported] = sinks[0].spans
    [second_exported] = sinks[1].spans
    assert first_exported.parent.span_id == int("00f067aa0ba902b7", 16)
    assert second_exported.parent is None


def test_middleware_ignores_proprietary_headers(app_factory) -> None:
    make_app, _, sinks = app_factory
    response = TestClient(make_app()).get(
        "/test",
        headers={
            "Splunk-AO-Trace-ID": "4bf92f35-77b3-4da6-a3ce-929d0e0e4736",
            "Splunk-AO-Parent-ID": "00f067aa-0ba9-42b7-8000-000000000000",
        },
    )

    assert response.status_code == 200
    assert response.json()["trace_id"] != "4bf92f3577b34da6a3ce929d0e0e4736"
    [exported] = sinks[0].spans
    assert exported.parent is None


def test_middleware_detaches_context_on_exception(app_factory) -> None:
    make_app, _, _ = app_factory
    with pytest.raises(RuntimeError, match="request failed"):
        TestClient(make_app(fail=True)).get(
            "/test", headers={"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
        )

    assert not trace.get_current_span().get_span_context().is_valid


def test_get_request_logger_constructs_plain_request_scoped_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    constructor = Mock(return_value=Mock(spec=SplunkAOLogger))
    monkeypatch.setattr("splunk_ao.middleware.tracing.SplunkAOLogger", constructor)

    assert get_request_logger() is constructor.return_value
    constructor.assert_called_once_with()
