import os
from unittest.mock import MagicMock, patch

import pytest

from splunk_ao.config import SplunkAOConfig
from splunk_ao.shared.exceptions import ConfigurationError

# Auth env vars cleared in tests that exercise the missing-auth guard.
_AUTH_ENV_VARS = (
    "SPLUNK_AO_API_KEY",
    "SPLUNK_AO_SSO_ID_TOKEN",
    "SPLUNK_AO_SSO_PROVIDER",
    "SPLUNK_AO_USERNAME",
    "SPLUNK_AO_PASSWORD",
    "SPLUNK_AO_JWT_TOKEN",
)


def _clear_auth_env(monkeypatch) -> None:
    """Clear every auth-related env var so the guard sees a clean slate."""
    for var in _AUTH_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# _bridge_env_vars tests
# ---------------------------------------------------------------------------

# Every (SPLUNK_AO_*, GALILEO_*) pair defined in _bridge_env_vars.
_ALL_BRIDGE_PAIRS = [
    ("SPLUNK_AO_API_KEY", "GALILEO_API_KEY"),
    ("SPLUNK_AO_API_URL", "GALILEO_API_URL"),
    ("SPLUNK_AO_CONSOLE_URL", "GALILEO_CONSOLE_URL"),
    ("SPLUNK_AO_PROJECT", "GALILEO_PROJECT"),
    ("SPLUNK_AO_PROJECT_ID", "GALILEO_PROJECT_ID"),
    ("SPLUNK_AO_LOG_STREAM", "GALILEO_LOG_STREAM"),
    ("SPLUNK_AO_LOG_STREAM_ID", "GALILEO_LOG_STREAM_ID"),
    ("SPLUNK_AO_JWT_TOKEN", "GALILEO_JWT_TOKEN"),
    ("SPLUNK_AO_SSO_ID_TOKEN", "GALILEO_SSO_ID_TOKEN"),
    ("SPLUNK_AO_SSO_PROVIDER", "GALILEO_SSO_PROVIDER"),
    ("SPLUNK_AO_USERNAME", "GALILEO_USERNAME"),
    ("SPLUNK_AO_PASSWORD", "GALILEO_PASSWORD"),
    ("SPLUNK_AO_MODE", "GALILEO_MODE"),
]

# Safe test values per key — URL keys must be valid URLs to avoid leaking
# an invalid GALILEO_* URL into the shared os.environ and breaking other tests.
_TEST_VALUE: dict[str, str] = {
    "SPLUNK_AO_API_URL": "https://splunk-ao-api-test.example.com",
    "GALILEO_API_URL": "https://galileo-api-test.example.com",
    "SPLUNK_AO_CONSOLE_URL": "https://splunk-ao-test.example.com",
    "GALILEO_CONSOLE_URL": "https://galileo-test.example.com",
}


def _val(key: str) -> str:
    return _TEST_VALUE.get(key, f"test-{key.lower().replace('_', '-')}")


@pytest.mark.parametrize("splunk_key,galileo_key", _ALL_BRIDGE_PAIRS)
def test_bridge_env_vars_propagates_splunk_ao_to_galileo(splunk_key, galileo_key) -> None:
    """Each SPLUNK_AO_* value is copied to its GALILEO_* counterpart when the
    GALILEO_* key is absent from the environment.

    Uses patch.dict so that any GALILEO_* key written directly to os.environ by
    _bridge_env_vars() (which bypasses monkeypatch tracking) is automatically
    cleaned up on block exit, preventing leakage into subsequent tests.
    """
    value = _val(splunk_key)
    with patch.dict(os.environ, {splunk_key: value}, clear=False):
        os.environ.pop(galileo_key, None)
        SplunkAOConfig._bridge_env_vars()
        assert os.environ.get(galileo_key) == value, f"Expected {galileo_key}={value!r} after bridging {splunk_key}"


@pytest.mark.parametrize("splunk_key,galileo_key", _ALL_BRIDGE_PAIRS)
def test_bridge_env_vars_does_not_overwrite_existing_galileo_value(splunk_key, galileo_key) -> None:
    """An explicit GALILEO_* value already in the environment must win over any
    SPLUNK_AO_* value — the bridge must not overwrite it."""
    existing = _val(galileo_key)
    with patch.dict(os.environ, {galileo_key: existing, splunk_key: "should-not-overwrite"}, clear=False):
        SplunkAOConfig._bridge_env_vars()
        assert os.environ.get(galileo_key) == existing, (
            f"Expected {galileo_key} to retain its original value; bridge must not overwrite it"
        )


def test_bridge_env_vars_skips_absent_splunk_ao_keys() -> None:
    """When a SPLUNK_AO_* key is absent, the corresponding GALILEO_* key must
    not be set (no spurious entries introduced by the bridge)."""
    all_bridge_keys = {k for pair in _ALL_BRIDGE_PAIRS for k in pair}
    # Build an env that has no bridge-related keys at all.
    clean_env = {k: v for k, v in os.environ.items() if k not in all_bridge_keys}
    with patch.dict(os.environ, clean_env, clear=True):
        SplunkAOConfig._bridge_env_vars()
        for _, galileo_key in _ALL_BRIDGE_PAIRS:
            assert galileo_key not in os.environ, f"{galileo_key} must not be set when its SPLUNK_AO_* source is absent"


# ---------------------------------------------------------------------------


@patch("galileo_core.schemas.base_config.GalileoConfig.set_validated_api_client", new=lambda x: x)
@patch("galileo_core.schemas.base_config.GalileoConfig.get_jwt_token")
def test_default_console_url(mock_get_jwt_token) -> None:
    """
    Test that the default console_url is used when SPLUNK_AO_CONSOLE_URL is not set.
    """
    mock_get_jwt_token.return_value = ("mock_jwt_token", "mock_refresh_token")

    # Unset the environment variable to ensure we test the default
    with patch.dict("os.environ", {}, clear=True):
        # Reset the global config object to force re-initialization
        SplunkAOConfig.get().reset()
        config = SplunkAOConfig.get(api_key="mock_api_key")

        assert str(config.console_url) == "https://app.galileo.ai/"
        assert str(config.api_url) == "https://api.galileo.ai/"


def test_no_auth_configured_raises_with_full_options_listed(monkeypatch) -> None:
    """When no auth is configured anywhere, the error lists every supported method."""
    # Given: no auth env vars and no cached instance
    _clear_auth_env(monkeypatch)
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)

    # When/Then: calling get() without credentials raises ConfigurationError
    # listing every supported standalone or paired auth method
    with pytest.raises(ConfigurationError) as exc_info:
        SplunkAOConfig.get()
    message = str(exc_info.value)
    assert "No Splunk AO authentication detected" in message
    assert "SPLUNK_AO_API_KEY" in message
    assert "SPLUNK_AO_SSO_ID_TOKEN" in message
    assert "SPLUNK_AO_SSO_PROVIDER" in message
    assert "SPLUNK_AO_USERNAME" in message
    assert "SPLUNK_AO_PASSWORD" in message


@pytest.mark.parametrize(
    "env_setup",
    [
        # Standalone methods.
        {"SPLUNK_AO_API_KEY": "test-api-key"},
        {"SPLUNK_AO_JWT_TOKEN": "test-jwt"},
        # Paired methods — both halves required.
        {"SPLUNK_AO_SSO_ID_TOKEN": "test-sso-token", "SPLUNK_AO_SSO_PROVIDER": "okta"},
        {"SPLUNK_AO_USERNAME": "test-user", "SPLUNK_AO_PASSWORD": "test-pass"},
    ],
    ids=["api_key", "jwt_token", "sso_id_token_and_provider", "username_and_password"],
)
def test_complete_auth_config_via_env_passes_guard(monkeypatch, env_setup) -> None:
    """A complete auth configuration in environment variables bypasses the guard."""
    # Given: a complete env-var auth configuration, no cached instance, and _get
    # stubbed out so downstream network calls never happen
    _clear_auth_env(monkeypatch)
    for env_var, value in env_setup.items():
        monkeypatch.setenv(env_var, value)
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    monkeypatch.setattr(SplunkAOConfig, "_get", lambda *a, **kw: MagicMock(spec=SplunkAOConfig))

    # When/Then: the guard passes and _get is reached without raising
    SplunkAOConfig.get()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"api_key": "test-api-key"},
        {"jwt_token": "test-jwt"},
        {"sso_id_token": "test-sso-token", "sso_provider": "okta"},
        {"username": "test-user", "password": "test-pass"},
    ],
    ids=["api_key", "jwt_token", "sso_id_token_and_provider", "username_and_password"],
)
def test_complete_auth_config_via_kwargs_passes_guard(monkeypatch, kwargs) -> None:
    """A complete auth configuration passed as kwargs bypasses the guard."""
    # Given: no auth env vars (kwargs are the only auth source), no cached instance,
    # and _get stubbed out so downstream network calls never happen
    _clear_auth_env(monkeypatch)
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    monkeypatch.setattr(SplunkAOConfig, "_get", lambda *a, **kw: MagicMock(spec=SplunkAOConfig))

    # When/Then: the guard passes and _get is reached without raising
    SplunkAOConfig.get(**kwargs)


def test_kwargs_and_env_can_be_mixed(monkeypatch) -> None:
    """One half of a paired auth method can come from kwargs, the other from env."""
    # Given: sso_id_token in env, sso_provider in kwargs, no cached instance,
    # and _get stubbed out so downstream network calls never happen
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("SPLUNK_AO_SSO_ID_TOKEN", "test-sso-token")
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)
    monkeypatch.setattr(SplunkAOConfig, "_get", lambda *a, **kw: MagicMock(spec=SplunkAOConfig))

    # When/Then: the guard accepts the mixed configuration and _get is reached without raising
    SplunkAOConfig.get(sso_provider="okta")


@pytest.mark.parametrize(
    "env_setup,expected_missing,expected_present",
    [
        ({"SPLUNK_AO_SSO_ID_TOKEN": "test-token"}, "SPLUNK_AO_SSO_PROVIDER", "SPLUNK_AO_SSO_ID_TOKEN"),
        ({"SPLUNK_AO_SSO_PROVIDER": "okta"}, "SPLUNK_AO_SSO_ID_TOKEN", "SPLUNK_AO_SSO_PROVIDER"),
        ({"SPLUNK_AO_USERNAME": "test-user"}, "SPLUNK_AO_PASSWORD", "SPLUNK_AO_USERNAME"),
        ({"SPLUNK_AO_PASSWORD": "test-pass"}, "SPLUNK_AO_USERNAME", "SPLUNK_AO_PASSWORD"),
    ],
    ids=[
        "sso_id_token_without_provider",
        "sso_provider_without_id_token",
        "username_without_password",
        "password_without_username",
    ],
)
def test_incomplete_auth_config_rejected_with_specific_guidance(
    monkeypatch, env_setup, expected_missing, expected_present
) -> None:
    """Setting only one half of a paired auth method gives a targeted error."""
    # Given: an incomplete paired auth configuration and no cached instance
    _clear_auth_env(monkeypatch)
    for env_var, value in env_setup.items():
        monkeypatch.setenv(env_var, value)
    monkeypatch.setattr(SplunkAOConfig, "_instance", None)

    # When/Then: the guard rejects with a message identifying both the
    # variable that's set and the one that's missing
    with pytest.raises(ConfigurationError) as exc_info:
        SplunkAOConfig.get()
    message = str(exc_info.value)
    assert expected_present in message, f"Expected error to reference {expected_present}: {message}"
    assert expected_missing in message, f"Expected error to reference {expected_missing}: {message}"
    assert "is set but" in message, f"Expected targeted incomplete-config phrasing: {message}"
