"""Tests for shared and standalone OTLP exporter configuration."""

from typing import Any
from unittest.mock import patch

from splunk_ao.deployment import DeploymentMode, StandaloneConfig
from splunk_ao.exporter.config import RoutingAttrs, create_otel_resource, routing_resource_attributes
from splunk_ao.exporter.span_transform import NormalizingSpanExporter
from splunk_ao.exporter.standalone import build_standalone_exporter, resolve_standalone_exporter_config
from splunk_ao.logger import logger as logger_module
from splunk_ao.logger.logger import SplunkAOLogger


def make_routing(**kwargs: str) -> RoutingAttrs:
    return RoutingAttrs(**kwargs)


def make_standalone_cfg() -> StandaloneConfig:
    return StandaloneConfig(api_key="key", console_url="https://console.demo.galileocloud.io")


def test_standalone_exporter_endpoint() -> None:
    cfg = StandaloneConfig(api_key="key", console_url="https://ao.example.com")
    result = resolve_standalone_exporter_config(cfg, routing=make_routing(project_name="proj1"))

    assert result.endpoint == cfg.otlp_endpoint == "https://api.ao.example.com/otel/v1/traces"


def test_standalone_exporter_endpoint_uses_explicit_api_url() -> None:
    cfg = StandaloneConfig(
        api_key="key", console_url="https://console.demo.galileocloud.io", api_url="https://custom-api.example.com"
    )
    result = resolve_standalone_exporter_config(cfg, routing=make_routing(project_name="proj1"))

    assert result.endpoint == "https://custom-api.example.com/otel/v1/traces"


def test_standalone_exporter_auth_header_uses_unmasked_secret() -> None:
    cfg = StandaloneConfig(api_key="my-key", console_url="https://ao.example.com")
    result = resolve_standalone_exporter_config(cfg, routing=make_routing(project_name="proj1"))

    assert result.headers["Splunk-AO-API-Key"] == "my-key"


def test_standalone_exporter_project_header() -> None:
    result = resolve_standalone_exporter_config(make_standalone_cfg(), routing=make_routing(project_name="proj1"))

    assert result.headers["project"] == "proj1"


def test_standalone_exporter_project_name_precedes_populated_id() -> None:
    result = resolve_standalone_exporter_config(
        make_standalone_cfg(), routing=make_routing(project_name="proj1", project_id="pid1")
    )

    assert result.headers["project"] == "proj1"
    assert "projectid" not in result.headers


def test_standalone_exporter_project_id_header() -> None:
    result = resolve_standalone_exporter_config(make_standalone_cfg(), routing=make_routing(project_id="pid1"))

    assert "project" not in result.headers
    assert result.headers["projectid"] == "pid1"


def test_standalone_exporter_logstream_header_absent_when_experiment() -> None:
    result = resolve_standalone_exporter_config(
        make_standalone_cfg(), routing=make_routing(project_name="p", agent_stream_name="ls", experiment_id="exp1")
    )

    assert "logstream" not in result.headers
    assert result.headers["experimentid"] == "exp1"


def test_standalone_exporter_logstream_id_header() -> None:
    result = resolve_standalone_exporter_config(
        make_standalone_cfg(), routing=make_routing(project_id="pid", agent_stream_id="lsid")
    )

    assert "logstream" not in result.headers
    assert result.headers["logstreamid"] == "lsid"


def test_standalone_exporter_no_routing_headers_when_routing_absent() -> None:
    result = resolve_standalone_exporter_config(make_standalone_cfg(), routing=make_routing())

    for header in ("project", "projectid", "logstream", "logstreamid", "experimentid"):
        assert header not in result.headers


def test_routing_resource_attributes_match_name_headers() -> None:
    routing = make_routing(project_name="p", agent_stream_name="ls")
    cfg = resolve_standalone_exporter_config(make_standalone_cfg(), routing)
    attrs = routing_resource_attributes(routing)

    assert cfg.headers["project"] == attrs["splunk_ao.project.name"] == "p"
    assert cfg.headers["logstream"] == attrs["splunk_ao.logstream.name"] == "ls"


def test_routing_resource_attributes_match_id_headers() -> None:
    routing = make_routing(project_id="pid", agent_stream_id="lsid")
    cfg = resolve_standalone_exporter_config(make_standalone_cfg(), routing)
    attrs = routing_resource_attributes(routing)

    assert cfg.headers["projectid"] == attrs["splunk_ao.project.id"] == "pid"
    assert cfg.headers["logstreamid"] == attrs["splunk_ao.logstream.id"] == "lsid"


def test_routing_resource_attributes_prioritize_experiment() -> None:
    attrs = routing_resource_attributes(
        make_routing(project_name="p", agent_stream_name="ls", agent_stream_id="lsid", experiment_id="exp")
    )

    assert attrs["splunk_ao.experiment.id"] == "exp"
    assert "splunk_ao.logstream.name" not in attrs
    assert "splunk_ao.logstream.id" not in attrs


def test_routing_resource_attributes_empty_when_routing_absent() -> None:
    assert routing_resource_attributes(RoutingAttrs()) == {}


def test_otel_resource_honors_service_name_and_preserves_routing(monkeypatch: Any) -> None:
    monkeypatch.setenv("OTEL_SERVICE_NAME", "travel-planner")

    resource = create_otel_resource(make_routing(project_name="project", agent_stream_name="stream"))

    assert resource.attributes["service.name"] == "travel-planner"
    assert resource.attributes["splunk_ao.project.name"] == "project"
    assert resource.attributes["splunk_ao.logstream.name"] == "stream"


def test_otel_resource_supplies_default_service_name(monkeypatch: Any) -> None:
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("OTEL_RESOURCE_ATTRIBUTES", raising=False)

    resource = create_otel_resource(make_routing())

    assert str(resource.attributes["service.name"]).startswith("unknown_service")


def test_explicit_routing_overrides_environment_resource_routing(monkeypatch: Any) -> None:
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES", "splunk_ao.project.name=environment-project,deployment.environment.name=test"
    )

    resource = create_otel_resource(make_routing(project_name="explicit-project"))

    assert resource.attributes["splunk_ao.project.name"] == "explicit-project"
    assert resource.attributes["deployment.environment.name"] == "test"


def test_resource_drops_reserved_environment_routing_when_sdk_routing_absent(monkeypatch: Any) -> None:
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        (
            "splunk_ao.project.name=environment-project,"
            "splunk_ao.logstream.id=environment-stream,"
            "splunk_ao.experiment.id=environment-experiment,"
            "deployment.environment.name=test"
        ),
    )

    resource = create_otel_resource(make_routing())

    for key in ("splunk_ao.project.name", "splunk_ao.logstream.id", "splunk_ao.experiment.id"):
        assert key not in resource.attributes
    assert resource.attributes["deployment.environment.name"] == "test"


def test_resource_removes_conflicting_routing_forms(monkeypatch: Any) -> None:
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES", "splunk_ao.project.name=stale-project,splunk_ao.logstream.name=stale-stream"
    )

    resource = create_otel_resource(make_routing(project_id="project-id", agent_stream_id="stream-id"))

    assert "splunk_ao.project.name" not in resource.attributes
    assert "splunk_ao.logstream.name" not in resource.attributes
    assert resource.attributes["splunk_ao.project.id"] == "project-id"
    assert resource.attributes["splunk_ao.logstream.id"] == "stream-id"


def test_build_standalone_exporter_passes_resolved_public_config_to_factory() -> None:
    captured: dict[str, Any] = {}
    expected_exporter = object()

    def exporter_factory(**kwargs: Any) -> object:
        captured.update(kwargs)
        return expected_exporter

    exporter = build_standalone_exporter(
        make_standalone_cfg(), make_routing(project_name="p"), _exporter_factory=exporter_factory
    )

    assert isinstance(exporter, NormalizingSpanExporter)
    assert exporter.delegate is expected_exporter
    assert captured == {
        "endpoint": "https://api.demo.galileocloud.io/otel/v1/traces",
        "headers": {"Splunk-AO-API-Key": "key", "project": "p"},
    }


def test_standalone_exporter_passes_deployment_explicitly_to_diagnostics() -> None:
    with patch("splunk_ao.exporter.config.DiagnosticOTLPSpanExporter") as diagnostic_exporter:
        exporter = build_standalone_exporter(make_standalone_cfg(), make_routing())

    assert exporter.delegate is diagnostic_exporter.return_value
    assert diagnostic_exporter.call_args.kwargs["deployment"] == DeploymentMode.STANDALONE


def test_healthz_probe_no_longer_called_on_exporter_construction() -> None:
    with patch("httpx.get") as httpx_get:
        build_standalone_exporter(
            make_standalone_cfg(), make_routing(project_name="p"), _exporter_factory=lambda **_: object()
        )

    httpx_get.assert_not_called()


def test_healthz_probe_and_cache_are_removed_from_logger() -> None:
    assert not hasattr(logger_module, "_ingest_service_cache")
    assert not hasattr(SplunkAOLogger, "_is_ingest_service_available")
