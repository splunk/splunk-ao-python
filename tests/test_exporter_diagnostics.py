"""Tests for successful-response OTLP rejection diagnostics."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import MagicMock

import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from requests import Response
from requests.exceptions import Timeout

from splunk_ao.deployment import DeploymentMode
from splunk_ao.exporter.diagnostics import (
    DiagnosticOTLPSpanExporter,
    ExportHealth,
    _ExportHealthTracker,
    _RejectionDetail,
)
from splunk_ao.exporter.sink import BatchConfig, build_span_sink
from splunk_ao.exporter.span_transform import NormalizingSpanExporter
from splunk_ao.logger.logger import SplunkAOLogger
from splunk_ao.otel import SplunkAOSpanProcessor


class FakeSession:
    def __init__(self, *responses: Response | Exception) -> None:
        self.headers: dict[str, str] = {}
        self.responses = list(responses)
        self.post_calls = 0

    def post(self, **_: Any) -> Response:
        outcome = self.responses[min(self.post_calls, len(self.responses) - 1)]
        self.post_calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        pass


def response(status_code: int = 200, body: bytes = b"", content_type: str = "application/json") -> Response:
    result = Response()
    result.status_code = status_code
    result._content = body
    result.headers["Content-Type"] = content_type
    result.reason = "test response"
    return result


def diagnostic_exporter(session: FakeSession) -> DiagnosticOTLPSpanExporter:
    return DiagnosticOTLPSpanExporter(
        endpoint="https://ingest.example.test/v2/trace/otlp",
        headers={"X-SF-Token": "placeholder-secret"},
        session=session,
        deployment=DeploymentMode.O11Y,
        timeout=0.01,
    )


def test_splunk_json_rejection_returns_failure_without_retry_or_sensitive_logging() -> None:
    session = FakeSession(
        response(
            body=(
                b'{"valid":0,"invalid":{"nilServiceName":["private payload"],"bad.attribute":{"nested":"not logged"}}}'
            )
        )
    )
    exporter = diagnostic_exporter(session)
    logger = MagicMock()
    exporter._health_tracker._logger = logger

    result = exporter.export(())

    assert result == SpanExportResult.FAILURE
    assert session.post_calls == 1
    assert exporter.export_health.last_failure is not None
    assert exporter.export_health.last_failure.category == "rejected"
    log_message = logger.error.call_args.args[1]
    assert "nilServiceName=1" in log_message
    assert "bad.attribute=1" in log_message
    assert "private payload" not in log_message
    assert "not logged" not in log_message
    assert exporter._attempt_local.response is None


def test_positive_otlp_partial_success_returns_failure_without_retry() -> None:
    acknowledgement = ExportTraceServiceResponse()
    acknowledgement.partial_success.rejected_spans = 3
    acknowledgement.partial_success.error_message = "do not retain this backend detail"
    session = FakeSession(response(body=acknowledgement.SerializeToString(), content_type="application/x-protobuf"))
    exporter = diagnostic_exporter(session)

    result = exporter.export(())

    assert result == SpanExportResult.FAILURE
    assert session.post_calls == 1
    assert exporter.export_health.last_failure is not None
    assert "Rejected spans: 3" in exporter.export_health.last_failure.message
    assert "backend detail" not in exporter.export_health.last_failure.message
    assert exporter._attempt_local.response is None


@pytest.mark.parametrize("rejected_spans", [3, "3"])
def test_positive_json_otlp_partial_success_returns_failure_without_backend_detail(rejected_spans: int | str) -> None:
    body = json.dumps(
        {"partialSuccess": {"rejectedSpans": rejected_spans, "errorMessage": "do not retain this backend detail"}}
    ).encode()
    exporter = diagnostic_exporter(FakeSession(response(body=body)))

    assert exporter.export(()) == SpanExportResult.FAILURE
    assert exporter.export_health.last_failure is not None
    assert "Rejected spans: 3" in exporter.export_health.last_failure.message
    assert "backend detail" not in exporter.export_health.last_failure.message


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (b"", "application/x-protobuf"),
        (b'{"valid":1}', "application/json"),
        (b'{"other":"value"}', "application/json"),
        (b'{"partialSuccess":{"rejectedSpans":"0","errorMessage":"advisory"}}', "application/json"),
        (b'{"partialSuccess":{"rejectedSpans":"invalid"}}', "application/json"),
        (b"not-json", "application/json"),
        (b"\x80", "application/x-protobuf"),
    ],
)
def test_successful_or_unrecognized_acknowledgements_remain_successful(body: bytes, content_type: str) -> None:
    exporter = diagnostic_exporter(FakeSession(response(body=body, content_type=content_type)))

    assert exporter.export(()) == SpanExportResult.SUCCESS
    assert exporter.export_health == ExportHealth(healthy=True, consecutive_failures=0, last_failure=None)
    assert exporter._attempt_local.response is None


def test_zero_rejected_spans_with_advisory_message_is_successful() -> None:
    acknowledgement = ExportTraceServiceResponse()
    acknowledgement.partial_success.error_message = "advisory only"
    exporter = diagnostic_exporter(
        FakeSession(response(body=acknowledgement.SerializeToString(), content_type="application/protobuf"))
    )

    assert exporter.export(()) == SpanExportResult.SUCCESS
    assert exporter.export_health.healthy is True


def test_ordinary_http_failure_is_left_to_the_standard_exporter() -> None:
    exporter = diagnostic_exporter(FakeSession(response(body=b'{"valid":1}'), response(401)))
    logger = MagicMock()
    exporter._health_tracker._logger = logger

    assert exporter.export(()) == SpanExportResult.SUCCESS
    assert exporter.export_health.healthy is True
    assert exporter.export(()) == SpanExportResult.FAILURE
    assert exporter.export_health.healthy is None
    logger.error.assert_not_called()
    assert exporter._attempt_local.response is None


def test_transport_exception_is_unchanged_and_clears_response_snapshot() -> None:
    exporter = diagnostic_exporter(FakeSession(Timeout("standard exporter failure")))
    exporter._attempt_local.response = object()

    with pytest.raises(Timeout, match="standard exporter failure"):
        exporter.export(())

    assert exporter.export_health.healthy is None
    assert exporter._attempt_local.response is None


def test_repeated_rejections_are_rate_limited_and_recovery_logs_once() -> None:
    clock = MagicMock(return_value=10.0)
    logger = MagicMock()
    tracker = _ExportHealthTracker(
        DeploymentMode.O11Y, "https://ingest.example.test/v2/trace/otlp", clock=clock, logger=logger
    )

    rejection = _RejectionDetail(200, "Rejection categories: nilServiceName=1.")
    tracker.record_rejection(rejection)
    tracker.record_rejection(rejection)
    assert logger.error.call_count == 1

    clock.return_value = 71.0
    tracker.record_rejection(rejection)
    assert logger.error.call_count == 2
    assert "1 repeated rejections suppressed" in logger.error.call_args.args[1]

    tracker.record_success()
    tracker.record_success()
    assert logger.info.call_count == 1
    assert tracker.health == ExportHealth(healthy=True, consecutive_failures=0, last_failure=None)


def test_export_health_snapshots_are_immutable_and_thread_safe() -> None:
    tracker = _ExportHealthTracker(DeploymentMode.O11Y, "https://ingest.example.test/v2/trace/otlp", logger=MagicMock())
    rejection = _RejectionDetail(200)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: tracker.record_rejection(rejection), range(100)))

    health = tracker.health
    assert health.consecutive_failures == 100
    assert health.last_failure is not None
    assert health.last_failure.consecutive_failures == 100
    with pytest.raises(FrozenInstanceError):
        health.consecutive_failures = 0


def test_logger_path_reports_rejection_without_failing_the_logged_operation() -> None:
    exporter = diagnostic_exporter(FakeSession(response(body=b'{"valid":0}')))
    sink = build_span_sink(exporter, BatchConfig(schedule_delay_millis=60_000))
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    try:
        logger.add_single_llm_span_trace(input="question", output="answer", model="test-model")

        assert logger.flush() is None
        assert sink.export_health.healthy is False
        assert logger.export_health == sink.export_health
    finally:
        sink.shutdown()


def test_user_wired_processor_reports_rejection_without_failing_span_completion() -> None:
    exporter = diagnostic_exporter(FakeSession(response(body=b'{"valid":0}')))
    normalizing_exporter = NormalizingSpanExporter(exporter, Resource.create())
    processor = SplunkAOSpanProcessor(SpanProcessor=SimpleSpanProcessor, _exporter=normalizing_exporter)
    provider = TracerProvider()
    provider.add_span_processor(processor)

    with provider.get_tracer("test").start_as_current_span("operation"):
        pass

    assert processor.export_health.healthy is False
    provider.shutdown()
