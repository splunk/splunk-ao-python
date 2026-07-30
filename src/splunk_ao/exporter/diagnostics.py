"""Diagnostics for successful OTLP responses that reject spans."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

from google.protobuf.message import DecodeError
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from requests import Response

from splunk_ao.deployment import DeploymentMode

_logger = logging.getLogger("splunk_ao.exporter")

ExportFailureCategory = Literal["rejected"]

_MAX_RESPONSE_BYTES = 64 * 1024
_MAX_MESSAGE_LENGTH = 512
_MAX_REJECTION_KEYS = 8
_DEFAULT_LOG_INTERVAL_SECONDS = 60.0
_SAFE_KEY = re.compile(r"[^a-zA-Z0-9_.-]+")
_PROTOBUF_CONTENT_TYPES = frozenset(
    {"application/protobuf", "application/vnd.google.protobuf", "application/x-protobuf"}
)


@dataclass(frozen=True)
class ExportFailure:
    """Sanitized details for the most recent acknowledged rejection."""

    category: ExportFailureCategory
    message: str
    status_code: int
    consecutive_failures: int


@dataclass(frozen=True)
class ExportHealth:
    """Immutable acknowledgement health.

    ``healthy`` is ``None`` before export and after ordinary transport or
    non-2xx failures, ``True`` after an accepted 2xx response, and ``False``
    after a 2xx response that rejects telemetry.
    """

    healthy: bool | None
    consecutive_failures: int
    last_failure: ExportFailure | None


UNKNOWN_EXPORT_HEALTH = ExportHealth(healthy=None, consecutive_failures=0, last_failure=None)


@dataclass(frozen=True)
class _RejectionDetail:
    status_code: int
    detail: str | None = None


@dataclass(frozen=True)
class _ResponseSnapshot:
    status_code: int
    content_type: str
    body: bytes


class _ExportHealthTracker:
    def __init__(
        self,
        deployment: DeploymentMode,
        endpoint: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        log_interval_seconds: float = _DEFAULT_LOG_INTERVAL_SECONDS,
        logger: logging.Logger = _logger,
    ) -> None:
        self._deployment = deployment
        self._endpoint_host = urlsplit(endpoint).hostname or "configured endpoint"
        self._clock = clock
        self._log_interval_seconds = log_interval_seconds
        self._logger = logger
        self._lock = threading.Lock()
        self._health = UNKNOWN_EXPORT_HEALTH
        self._last_logged_rejection: tuple[int, str | None] | None = None
        self._last_logged_at = 0.0
        self._suppressed_rejections = 0

    @property
    def health(self) -> ExportHealth:
        with self._lock:
            return self._health

    def record_rejection(self, detail: _RejectionDetail) -> None:
        message = self._rejection_message(detail)
        now = self._clock()
        log_message: str | None = None
        with self._lock:
            consecutive_failures = self._health.consecutive_failures + 1
            failure = ExportFailure(
                category="rejected",
                message=message,
                status_code=detail.status_code,
                consecutive_failures=consecutive_failures,
            )
            fingerprint = (detail.status_code, detail.detail)
            interval_elapsed = now - self._last_logged_at >= self._log_interval_seconds
            if self._health.healthy is not False or fingerprint != self._last_logged_rejection or interval_elapsed:
                log_message = message
                if self._suppressed_rejections:
                    log_message += f" ({self._suppressed_rejections} repeated rejections suppressed)"
                self._last_logged_rejection = fingerprint
                self._last_logged_at = now
                self._suppressed_rejections = 0
            else:
                self._suppressed_rejections += 1
            self._health = ExportHealth(healthy=False, consecutive_failures=consecutive_failures, last_failure=failure)
        if log_message is not None:
            self._logger.error("%s", log_message)

    def record_success(self) -> None:
        with self._lock:
            should_log_recovery = self._health.healthy is False
            self._health = ExportHealth(healthy=True, consecutive_failures=0, last_failure=None)
            self._last_logged_rejection = None
            self._last_logged_at = 0.0
            self._suppressed_rejections = 0
        if should_log_recovery:
            self._logger.info(
                "Splunk AO OTLP export recovered for %s endpoint %s.", self._deployment.value, self._endpoint_host
            )

    def record_unknown(self) -> None:
        """Clear acknowledgement health when the standard exporter reports another failure."""
        with self._lock:
            self._health = UNKNOWN_EXPORT_HEALTH
            self._last_logged_rejection = None
            self._last_logged_at = 0.0
            self._suppressed_rejections = 0

    def _rejection_message(self, rejection: _RejectionDetail) -> str:
        detail = f" {rejection.detail}" if rejection.detail else ""
        return (
            f"Splunk AO OTLP ingest at {self._deployment.value} endpoint "
            f"{self._endpoint_host} returned HTTP {rejection.status_code} but rejected some or all spans."
            f"{detail}"
        )[:_MAX_MESSAGE_LENGTH]


class DiagnosticOTLPSpanExporter(OTLPSpanExporter):
    """OTLP HTTP exporter that detects rejection acknowledgements returned with HTTP 2xx."""

    def __init__(self, *args: Any, deployment: DeploymentMode, **kwargs: Any) -> None:
        configured_endpoint = str(kwargs.get("endpoint", ""))
        super().__init__(*args, **kwargs)
        self._attempt_local = threading.local()
        self._health_tracker = _ExportHealthTracker(deployment, getattr(self, "_endpoint", configured_endpoint))

    @property
    def export_health(self) -> ExportHealth:
        return self._health_tracker.health

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self._attempt_local.response = None
        try:
            try:
                result = super().export(spans)
            except Exception:
                self._health_tracker.record_unknown()
                raise
            if result != SpanExportResult.SUCCESS:
                self._health_tracker.record_unknown()
                return result

            response = getattr(self._attempt_local, "response", None)
            rejection = _classify_successful_response(response) if response is not None else None
            if rejection is not None:
                self._health_tracker.record_rejection(rejection)
                return SpanExportResult.FAILURE

            self._health_tracker.record_success()
            return SpanExportResult.SUCCESS
        finally:
            self._attempt_local.response = None

    def _export(self, serialized_data: bytes, timeout_sec: float | None = None) -> Response:
        response = super()._export(serialized_data, timeout_sec)
        self._attempt_local.response = _snapshot_response(response) if 200 <= response.status_code < 300 else None
        return response


def get_export_health(owner: object) -> ExportHealth:
    """Read acknowledgement health from an SDK exporter ownership surface."""
    health = getattr(owner, "export_health", UNKNOWN_EXPORT_HEALTH)
    return health if isinstance(health, ExportHealth) else UNKNOWN_EXPORT_HEALTH


def _snapshot_response(response: Response) -> _ResponseSnapshot:
    content_type = response.headers.get("Content-Type", "").partition(";")[0].strip().lower()
    return _ResponseSnapshot(
        status_code=response.status_code, content_type=content_type, body=bytes(response.content[:_MAX_RESPONSE_BYTES])
    )


def _classify_successful_response(response: _ResponseSnapshot) -> _RejectionDetail | None:
    if not response.body:
        return None
    if response.content_type == "application/json" or response.content_type.endswith("+json"):
        return _classify_json_acknowledgement(response.body, response.status_code)
    if response.content_type in _PROTOBUF_CONTENT_TYPES:
        return _classify_protobuf_acknowledgement(response.body, response.status_code)
    return None


def _classify_json_acknowledgement(body: bytes, status_code: int) -> _RejectionDetail | None:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    partial_success = payload.get("partialSuccess")
    if isinstance(partial_success, dict):
        rejected_spans = _positive_json_integer(partial_success.get("rejectedSpans"))
        if rejected_spans is not None:
            return _RejectionDetail(status_code, f"Rejected spans: {rejected_spans}.")

    invalid = payload.get("invalid")
    if payload.get("valid") != 0 and not invalid:
        return None
    return _RejectionDetail(status_code, _summarize_rejections(invalid))


def _positive_json_integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdecimal():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _classify_protobuf_acknowledgement(body: bytes, status_code: int) -> _RejectionDetail | None:
    response = ExportTraceServiceResponse()
    try:
        response.ParseFromString(body)
    except DecodeError:
        return None
    rejected_spans = response.partial_success.rejected_spans
    if rejected_spans <= 0:
        return None
    return _RejectionDetail(status_code, f"Rejected spans: {rejected_spans}.")


def _summarize_rejections(invalid: object) -> str | None:
    if not invalid:
        return None
    if not isinstance(invalid, dict):
        return "The response contained an explicit rejection."

    summaries: list[str] = []
    for key, value in sorted(invalid.items(), key=lambda item: str(item[0]))[:_MAX_REJECTION_KEYS]:
        safe_key = _SAFE_KEY.sub("_", str(key))[:48] or "unknown"
        if isinstance(value, (list, tuple, dict, set)):
            count = len(value)
        elif isinstance(value, int) and not isinstance(value, bool):
            count = max(0, value)
        else:
            count = 1
        summaries.append(f"{safe_key}={count}")
    return f"Rejection categories: {', '.join(summaries)}." if summaries else None
