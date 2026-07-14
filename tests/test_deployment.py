"""Tests for deployment-mode detection and per-mode config validation."""

import contextlib
import os
from collections.abc import Iterator

import pytest

from splunk_ao.config import SplunkAOConfig
from splunk_ao.deployment import DeploymentMode, O11yConfig, StandaloneConfig
from splunk_ao.shared.exceptions import AmbiguousConfigurationError, MissingConfigurationError

_DETECTION_ENV_VARS = (
    "SPLUNK_AO_REALM",
    "SPLUNK_AO_SF_TOKEN",
    "SPLUNK_AO_SF_API_TOKEN",
    "SPLUNK_AO_API_KEY",
    "SPLUNK_AO_CONSOLE_URL",
    "SPLUNK_AO_API_URL",
)
_DEPLOYMENT_ENV_VARS = _DETECTION_ENV_VARS


@contextlib.contextmanager
def env(**overrides: str) -> Iterator[None]:
    """Temporarily replace deployment-related environment variables."""
    saved = {name: os.environ.pop(name, None) for name in _DEPLOYMENT_ENV_VARS}
    try:
        os.environ.update(overrides)
        yield
    finally:
        for name in _DEPLOYMENT_ENV_VARS:
            os.environ.pop(name, None)
        for name, value in saved.items():
            if value is not None:
                os.environ[name] = value


def test_autodetect_o11y_from_realm_and_sf_token() -> None:
    with env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok"):
        assert SplunkAOConfig.resolve_deployment() == DeploymentMode.O11Y


def test_autodetect_o11y_from_sf_api_token_only() -> None:
    with env(SPLUNK_AO_SF_API_TOKEN="tok"):
        assert SplunkAOConfig.resolve_deployment() == DeploymentMode.O11Y


def test_autodetect_standalone_from_api_key() -> None:
    with env(SPLUNK_AO_API_KEY="key", SPLUNK_AO_CONSOLE_URL="https://ao.example.com"):
        assert SplunkAOConfig.resolve_deployment() == DeploymentMode.STANDALONE


def test_autodetect_standalone_from_console_url_only() -> None:
    with env(SPLUNK_AO_CONSOLE_URL="https://ao.example.com"):
        assert SplunkAOConfig.resolve_deployment() == DeploymentMode.STANDALONE


def test_autodetect_standalone_from_api_url_only() -> None:
    with env(SPLUNK_AO_API_URL="https://api.example.com"):
        assert SplunkAOConfig.resolve_deployment() == DeploymentMode.STANDALONE


def test_o11y_and_standalone_api_url_are_ambiguous() -> None:
    with env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok", SPLUNK_AO_API_URL="https://stale-standalone.example.com"):
        with pytest.raises(AmbiguousConfigurationError) as exc_info:
            SplunkAOConfig.resolve_deployment()
    assert "SPLUNK_AO_API_URL" in str(exc_info.value)


def test_ambiguous_raises_when_both_sets_present() -> None:
    with env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok", SPLUNK_AO_API_KEY="key"):
        with pytest.raises(AmbiguousConfigurationError) as exc_info:
            SplunkAOConfig.resolve_deployment()
    assert "SPLUNK_AO_REALM" in str(exc_info.value)
    assert "SPLUNK_AO_SF_TOKEN" in str(exc_info.value)
    assert "SPLUNK_AO_API_KEY" in str(exc_info.value)


def test_missing_raises_when_neither_set() -> None:
    with env():
        with pytest.raises(MissingConfigurationError) as exc_info:
            SplunkAOConfig.resolve_deployment()
    for name in _DETECTION_ENV_VARS:
        assert name in str(exc_info.value)


def test_empty_values_do_not_select_a_deployment() -> None:
    with env(SPLUNK_AO_REALM="", SPLUNK_AO_API_KEY=""):
        with pytest.raises(MissingConfigurationError):
            SplunkAOConfig.resolve_deployment()


def test_o11y_config_from_env() -> None:
    with env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="ingest-tok", SPLUNK_AO_SF_API_TOKEN="api-tok"):
        cfg = O11yConfig.from_env()

    assert cfg.realm == "us1"
    assert cfg.sf_token.get_secret_value() == "ingest-tok"
    assert cfg.sf_api_token is not None
    assert cfg.sf_api_token.get_secret_value() == "api-tok"


def test_otlp_endpoint_derived_from_realm() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    assert cfg.otlp_endpoint == "https://ingest.us1.observability.splunkcloud.com/v2/trace/otlp"


def test_crud_token_prefers_api_token() -> None:
    cfg = O11yConfig(realm="us1", sf_token="ingest-tok", sf_api_token="api-tok")
    assert cfg.crud_token.get_secret_value() == "api-tok"


def test_crud_token_falls_back_to_sf_token() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok", sf_api_token=None)
    assert cfg.crud_token.get_secret_value() == "tok"


def test_missing_realm_raises() -> None:
    with env(SPLUNK_AO_SF_TOKEN="tok"):
        with pytest.raises(MissingConfigurationError, match="SPLUNK_AO_REALM"):
            O11yConfig.from_env()


def test_missing_sf_token_raises() -> None:
    with env(SPLUNK_AO_REALM="us1"):
        with pytest.raises(MissingConfigurationError, match="SPLUNK_AO_SF_TOKEN"):
            O11yConfig.from_env()


def test_missing_o11y_config_names_both_required_variables() -> None:
    with env():
        with pytest.raises(MissingConfigurationError) as exc_info:
            O11yConfig.from_env()
    assert "SPLUNK_AO_REALM" in str(exc_info.value)
    assert "SPLUNK_AO_SF_TOKEN" in str(exc_info.value)


def test_api_root_derives_from_realm() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    assert cfg.api_root == "https://api.us1.observability.splunkcloud.com"


def test_require_api_url_derives_from_realm() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    assert cfg.require_api_url() == "https://api.us1.observability.splunkcloud.com/v2/ao"
    assert cfg.require_api_url() == f"{cfg.api_root}/v2/ao"


def test_require_console_url_derives_from_realm() -> None:
    cfg = O11yConfig(realm="us1", sf_token="tok")
    assert cfg.require_console_url() == "https://app.us1.observability.splunkcloud.com/#/ao"


def test_standalone_config_happy_path() -> None:
    with env(SPLUNK_AO_API_KEY="key", SPLUNK_AO_CONSOLE_URL="https://ao.example.com"):
        cfg = StandaloneConfig.from_env()
        assert cfg.console_url == "https://ao.example.com"
        assert cfg.api_key.get_secret_value() == "key"


def test_missing_api_key_raises() -> None:
    with env(SPLUNK_AO_CONSOLE_URL="https://ao.example.com"):
        with pytest.raises(MissingConfigurationError, match="SPLUNK_AO_API_KEY"):
            StandaloneConfig.from_env()


def test_missing_console_url_raises() -> None:
    with env(SPLUNK_AO_API_KEY="key"):
        with pytest.raises(MissingConfigurationError, match="SPLUNK_AO_CONSOLE_URL"):
            StandaloneConfig.from_env()


def test_missing_standalone_config_names_both_required_variables() -> None:
    with env():
        with pytest.raises(MissingConfigurationError) as exc_info:
            StandaloneConfig.from_env()
    assert "SPLUNK_AO_API_KEY" in str(exc_info.value)
    assert "SPLUNK_AO_CONSOLE_URL" in str(exc_info.value)


def test_otlp_endpoint_derived_from_console_url_when_api_url_unset() -> None:
    cfg = StandaloneConfig(api_key="key", console_url="https://console.demo.galileocloud.io")
    assert cfg.otlp_endpoint == "https://api.demo.galileocloud.io/otel/traces"


def test_otlp_endpoint_derived_from_app_url() -> None:
    cfg = StandaloneConfig(api_key="key", console_url="https://app.galileo.ai/")
    assert cfg.otlp_endpoint == "https://api.galileo.ai/otel/traces"


def test_otlp_endpoint_uses_explicit_api_url_when_set() -> None:
    cfg = StandaloneConfig(
        api_key="key", console_url="https://console.demo.galileocloud.io", api_url="https://custom-api.example.com/"
    )
    assert cfg.otlp_endpoint == "https://custom-api.example.com/otel/traces"
