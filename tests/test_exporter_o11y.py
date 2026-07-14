"""Tests for Splunk Observability Cloud OTLP exporter configuration."""

from typing import Any

from splunk_ao.deployment import O11yConfig
from splunk_ao.exporter.config import RoutingAttrs
from splunk_ao.exporter.o11y import build_o11y_exporter, resolve_o11y_exporter_config


def make_routing(**kwargs: str) -> RoutingAttrs:
    return RoutingAttrs(**kwargs)


def test_o11y_exporter_endpoint_derived_from_realm() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    result = resolve_o11y_exporter_config(cfg, routing=make_routing(project_name="proj1"))

    assert result.endpoint == "https://ingest.us1.observability.splunkcloud.com/v2/trace/otlp"


def test_o11y_exporter_uses_unmasked_sf_ingest_token_header() -> None:
    cfg = O11yConfig(realm="eu0", sf_token="my-sf-token", sf_api_token="crud-only-token")
    result = resolve_o11y_exporter_config(cfg, routing=make_routing(project_name="proj1"))

    assert result.headers["X-SF-Token"] == "my-sf-token"


def test_o11y_exporter_project_header_present() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    result = resolve_o11y_exporter_config(cfg, routing=make_routing(project_name="proj1"))

    assert result.headers["project"] == "proj1"


def test_o11y_exporter_project_id_header_present() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    result = resolve_o11y_exporter_config(cfg, routing=make_routing(project_id="pid1"))

    assert "project" not in result.headers
    assert result.headers["projectid"] == "pid1"


def test_o11y_exporter_logstream_header_absent_when_experiment() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    result = resolve_o11y_exporter_config(
        cfg, routing=make_routing(project_name="p", log_stream_name="ls", experiment_id="exp1")
    )

    assert "logstream" not in result.headers
    assert result.headers["experimentid"] == "exp1"


def test_o11y_exporter_no_routing_headers_when_routing_absent() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    result = resolve_o11y_exporter_config(cfg, routing=make_routing())

    for header in ("project", "projectid", "logstream", "logstreamid", "experimentid"):
        assert header not in result.headers


def test_build_o11y_exporter_passes_resolved_public_config_to_factory() -> None:
    captured: dict[str, Any] = {}
    expected_exporter = object()

    def exporter_factory(**kwargs: Any) -> object:
        captured.update(kwargs)
        return expected_exporter

    exporter = build_o11y_exporter(
        O11yConfig(realm="us1", sf_token="tok"),
        make_routing(project_id="pid", log_stream_id="lsid"),
        _exporter_factory=exporter_factory,
    )

    assert exporter is expected_exporter
    assert captured == {
        "endpoint": "https://ingest.us1.observability.splunkcloud.com/v2/trace/otlp",
        "headers": {"X-SF-Token": "tok", "projectid": "pid", "logstreamid": "lsid"},
    }
