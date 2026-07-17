import contextlib
import os
from collections.abc import Iterator
from contextlib import nullcontext
from unittest.mock import MagicMock, patch
from urllib.parse import urljoin
from uuid import uuid4

import pytest
from pydantic import SecretStr

from galileo_core.constants.request_method import RequestMethod
from galileo_core.constants.routes import Routes
from galileo_core.helpers.api_client import ApiClient
from galileo_core.schemas.base_config import GalileoConfig
from splunk_ao.config import O11yApiClient, SplunkAOConfig
from splunk_ao.shared.exceptions import AmbiguousConfigurationError, MissingConfigurationError

_CONFIG_ENV_VARS = (
    "SPLUNK_AO_REALM",
    "SPLUNK_AO_SF_TOKEN",
    "SPLUNK_AO_SF_API_TOKEN",
    "SPLUNK_AO_API_KEY",
    "SPLUNK_AO_API_URL",
    "SPLUNK_AO_CONSOLE_URL",
    "SPLUNK_AO_JWT_TOKEN",
    "SPLUNK_AO_SSO_ID_TOKEN",
    "SPLUNK_AO_SSO_PROVIDER",
    "SPLUNK_AO_USERNAME",
    "SPLUNK_AO_PASSWORD",
    "GALILEO_API_KEY",
    "GALILEO_API_URL",
    "GALILEO_CONSOLE_URL",
    "GALILEO_JWT_TOKEN",
    "GALILEO_REFRESH_TOKEN",
    "GALILEO_SSO_ID_TOKEN",
    "GALILEO_SSO_PROVIDER",
    "GALILEO_USERNAME",
    "GALILEO_PASSWORD",
)


@contextlib.contextmanager
def config_env(**overrides: str) -> Iterator[None]:
    saved = {name: os.environ.pop(name, None) for name in _CONFIG_ENV_VARS}
    try:
        os.environ.update(overrides)
        yield
    finally:
        for name in _CONFIG_ENV_VARS:
            os.environ.pop(name, None)
        for name, value in saved.items():
            if value is not None:
                os.environ[name] = value


def _o11y_client(token: str = "tok") -> O11yApiClient:
    client = O11yApiClient(
        host="https://api.us1.observability.splunkcloud.com", sf_token=SecretStr(token), jwt_token=SecretStr("")
    )
    client.thread_local.client = None
    return client


def test_o11y_api_client_uses_sf_token_header() -> None:
    assert _o11y_client("my-token").auth_header == {"X-SF-Token": "my-token"}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/projects", "/v2/ao/projects"),
        ("projects", "/v2/ao/projects"),
        ("/v2/ao/projects", "/v2/ao/projects"),
        ("/v2/ao", "/v2/ao"),
    ],
)
def test_o11y_api_client_prefixes_paths_once(path: str, expected: str) -> None:
    assert _o11y_client()._prefixed(path) == expected


def test_o11y_api_client_sync_request_preserves_prefix_and_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_make_request(
        request_method: RequestMethod, base_url: str, endpoint: str, headers: dict[str, str], **kwargs: object
    ) -> dict:
        captured.update(method=request_method, url=urljoin(base_url, endpoint), headers=headers)
        return {}

    monkeypatch.setattr(ApiClient, "make_request", staticmethod(fake_make_request))
    _o11y_client().request(RequestMethod.GET, path="/projects")

    assert captured == {
        "method": RequestMethod.GET,
        "url": "https://api.us1.observability.splunkcloud.com/v2/ao/projects",
        "headers": {"accept": "application/json", "Content-Type": "application/json", "X-SF-Token": "tok"},
    }


@pytest.mark.asyncio
async def test_o11y_api_client_async_request_preserves_existing_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_make_request(
        request_method: RequestMethod, base_url: str, endpoint: str, headers: dict[str, str], **kwargs: object
    ) -> dict:
        captured.update(url=urljoin(base_url, endpoint), headers=headers)
        return {}

    monkeypatch.setattr(ApiClient, "make_request", staticmethod(fake_make_request))
    await _o11y_client().arequest(RequestMethod.GET, "/v2/ao/projects", {"X-Custom": "value"})

    assert captured["url"] == "https://api.us1.observability.splunkcloud.com/v2/ao/projects"
    assert captured["headers"] == {"X-Custom": "value", "X-SF-Token": "tok"}


def test_o11y_api_client_prefixes_streaming_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_stream_request(
        self: ApiClient, method: RequestMethod, path: str, *args: object, **kwargs: object
    ) -> contextlib.AbstractContextManager[str]:
        captured["path"] = path
        return nullcontext(path)

    monkeypatch.setattr(ApiClient, "stream_request", fake_stream_request)
    with _o11y_client().stream_request(RequestMethod.GET, "/projects"):
        pass

    assert captured["path"] == "/v2/ao/projects"


@pytest.mark.parametrize("token_var", ["SPLUNK_AO_SF_TOKEN", "SPLUNK_AO_SF_API_TOKEN"])
def test_o11y_auth_guard_accepts_environment_tokens(token_var: str) -> None:
    with config_env(SPLUNK_AO_REALM="us1", **{token_var: "tok"}):
        assert SplunkAOConfig._check_auth_config({}) is None


def test_o11y_auth_guard_requires_realm() -> None:
    with config_env(SPLUNK_AO_SF_API_TOKEN="tok"):
        assert "SPLUNK_AO_REALM" in (SplunkAOConfig._check_auth_config({}) or "")


def test_o11y_get_with_api_token_but_no_realm_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    with config_env(SPLUNK_AO_SF_API_TOKEN="tok"):
        with pytest.raises(MissingConfigurationError, match="SPLUNK_AO_REALM"):
            SplunkAOConfig.get()


def test_o11y_auth_guard_requires_at_least_one_token() -> None:
    with config_env(SPLUNK_AO_REALM="us1"):
        error = SplunkAOConfig._check_auth_config({}) or ""
    assert "SPLUNK_AO_SF_TOKEN" in error
    assert "SPLUNK_AO_SF_API_TOKEN" in error


def test_o11y_auth_guard_does_not_accept_token_kwargs() -> None:
    with config_env():
        assert SplunkAOConfig._check_auth_config({"sf_token": "tok"}) is not None


def test_o11y_console_bridge_uses_realm_and_preserves_explicit_legacy_value() -> None:
    with config_env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok"):
        SplunkAOConfig._bridge_env_vars()
        assert os.environ["GALILEO_CONSOLE_URL"] == "https://app.us1.observability.splunkcloud.com/#/ao"

    with config_env(
        SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok", GALILEO_CONSOLE_URL="https://explicit.example.com"
    ):
        SplunkAOConfig._bridge_env_vars()
        assert os.environ["GALILEO_CONSOLE_URL"] == "https://explicit.example.com"


def test_o11y_console_bridge_rederives_after_reset() -> None:
    with config_env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok"):
        SplunkAOConfig._bridge_env_vars()
        assert os.environ["GALILEO_CONSOLE_URL"] == "https://app.us1.observability.splunkcloud.com/#/ao"

        with patch("galileo_core.schemas.base_config.GalileoConfig.reset"):
            SplunkAOConfig.reset(MagicMock(spec=SplunkAOConfig))

        assert "GALILEO_CONSOLE_URL" not in os.environ
        os.environ["SPLUNK_AO_REALM"] = "eu0"
        SplunkAOConfig._bridge_env_vars()
        assert os.environ["GALILEO_CONSOLE_URL"] == "https://app.eu0.observability.splunkcloud.com/#/ao"


@pytest.mark.parametrize(("api_token", "expected_token"), [(None, "ingest-token"), ("api-token", "api-token")])
def test_o11y_get_builds_realm_config_without_jwt_calls(
    monkeypatch: pytest.MonkeyPatch, api_token: str | None, expected_token: str
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("o11y configuration must not use standalone validation")

    async def async_fail(*args: object, **kwargs: object) -> None:
        fail()

    values = {"SPLUNK_AO_REALM": "us1", "SPLUNK_AO_SF_TOKEN": "ingest-token"}
    if api_token is not None:
        values["SPLUNK_AO_SF_API_TOKEN"] = api_token
    values["GALILEO_API_KEY"] = "stale-standalone-key"
    values["GALILEO_API_URL"] = "https://stale-api.example.com"
    values["GALILEO_JWT_TOKEN"] = "stale-jwt"

    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    monkeypatch.setattr(GalileoConfig, "get_jwt_token", staticmethod(fail))
    monkeypatch.setattr(ApiClient, "make_request", staticmethod(async_fail))
    monkeypatch.setattr(ApiClient, "request", fail)

    with config_env(**values):
        cfg = SplunkAOConfig.get(ssl_context=False)
        client = cfg.api_client
        assert cfg.api_client is client

        assert cfg.jwt_token is None
        assert str(cfg.console_url).rstrip("/") == "https://app.us1.observability.splunkcloud.com/#/ao"
        assert str(cfg.api_url).rstrip("/") == "https://api.us1.observability.splunkcloud.com/v2/ao"
        assert isinstance(client, O11yApiClient)
        assert str(client.host).rstrip("/") == "https://api.us1.observability.splunkcloud.com"
        assert client.auth_header == {"X-SF-Token": expected_token}
        assert client.ssl_context is False


def test_o11y_get_supports_crud_only_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("o11y configuration must not use standalone validation")

    async def async_fail(*args: object, **kwargs: object) -> None:
        fail()

    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    monkeypatch.setattr(GalileoConfig, "get_jwt_token", staticmethod(fail))
    monkeypatch.setattr(ApiClient, "make_request", staticmethod(async_fail))
    monkeypatch.setattr(ApiClient, "request", fail)

    with config_env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_API_TOKEN="api-token"):
        cfg = SplunkAOConfig.get(ssl_context=False)
        client = cfg.api_client

    assert cfg.jwt_token is None
    assert isinstance(client, O11yApiClient)
    assert client.auth_header == {"X-SF-Token": "api-token"}


def test_ambiguous_environment_fails_before_config_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    with config_env(SPLUNK_AO_REALM="us1", SPLUNK_AO_SF_TOKEN="tok", SPLUNK_AO_API_KEY="key"):
        with pytest.raises(AmbiguousConfigurationError):
            SplunkAOConfig.get()


def test_standalone_constructor_flow_still_uses_parent_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    async def fake_make_request(request_method: RequestMethod, base_url: str, endpoint: str, **kwargs: object) -> dict:
        calls.append(endpoint)
        return {"status": "ok"}

    def fake_get_jwt_token(*args: object, **kwargs: object) -> tuple[SecretStr, None]:
        calls.append("jwt")
        return SecretStr("jwt-token"), None

    def fake_request(self: ApiClient, method: RequestMethod, path: str, **kwargs: object) -> dict[str, str]:
        calls.append(path)
        return {"id": str(uuid4()), "email": "user@example.com", "role": "user"}

    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    monkeypatch.setattr(ApiClient, "make_request", staticmethod(fake_make_request))
    monkeypatch.setattr(GalileoConfig, "get_jwt_token", staticmethod(fake_get_jwt_token))
    monkeypatch.setattr(ApiClient, "request", fake_request)

    with config_env():
        cfg = SplunkAOConfig.get(console_url="https://app.galileo.ai", api_key="key")

    assert not isinstance(cfg.validated_api_client, O11yApiClient)
    assert Routes.healthcheck in calls
    assert "jwt" in calls
    assert Routes.current_user in calls
