import os
from unittest.mock import MagicMock, patch

import pytest

from splunk_ao.config import _BRIDGE, SplunkAOConfig
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
    ("SPLUNK_AO_AGENT_STREAM", "GALILEO_LOG_STREAM"),
    ("SPLUNK_AO_AGENT_STREAM_ID", "GALILEO_LOG_STREAM_ID"),
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
        assert os.environ.get(galileo_key) == value, (
            f"Expected {galileo_key}={value!r} after bridging {splunk_key}"
        )


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
            assert galileo_key not in os.environ, (
                f"{galileo_key} must not be set when its SPLUNK_AO_* source is absent"
            )


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


# ---------------------------------------------------------------------------
# Regression tests: stale bridge after reset() + credential change (HYBIM-787)
# ---------------------------------------------------------------------------


def test_reset_clears_bridged_galileo_env_vars() -> None:
    """reset() must remove every GALILEO_* key the bridge may have written.

    Before the fix, galileo-core env vars persisted across reset() calls, so
    the _bridge_env_vars guard ("skip if GALILEO_* already set") would silently
    reuse the stale value on the next get().

    We patch GalileoConfig.reset to a no-op so the test only exercises the
    env-var cleanup logic we added, without needing a fully-initialised Pydantic
    model instance.
    """
    galileo_keys = [galileo_key for _splunk_key, galileo_key in _BRIDGE]

    # Seed all GALILEO_* keys to simulate a prior bridge run, and suppress the
    # parent reset() so we can isolate the env-var cleanup we added.
    with (
        patch.dict(os.environ, {k: "stale-value" for k in galileo_keys}, clear=False),
        patch("galileo_core.schemas.base_config.GalileoConfig.reset"),
    ):
        mock_instance = MagicMock(spec=SplunkAOConfig)
        SplunkAOConfig.reset(mock_instance)

        for galileo_key in galileo_keys:
            assert galileo_key not in os.environ, (
                f"reset() must remove {galileo_key} from os.environ; "
                f"found stale value '{os.environ.get(galileo_key)}'"
            )


def test_bridge_picks_up_new_credential_after_reset(monkeypatch) -> None:
    """After reset(), _bridge_env_vars must copy the *new* SPLUNK_AO_* value.

    Regression test for HYBIM-787: get() → reset() → rotate credential → get()
    must result in the updated GALILEO_* value, not the original stale one.

    We patch GalileoConfig.reset to a no-op so the test only exercises the
    env-var cleanup + re-bridge behaviour without needing a fully-initialised
    Pydantic model instance.
    """
    monkeypatch.setenv("SPLUNK_AO_API_KEY", "key-first")
    monkeypatch.delenv("GALILEO_API_KEY", raising=False)

    # First bridge — mirrors key-first into GALILEO_API_KEY.
    SplunkAOConfig._bridge_env_vars()
    assert os.environ.get("GALILEO_API_KEY") == "key-first", "Bridge must copy key-first on first call"

    # reset() — this is the core of the fix under test.
    with patch("galileo_core.schemas.base_config.GalileoConfig.reset"):
        mock_instance = MagicMock(spec=SplunkAOConfig)
        SplunkAOConfig.reset(mock_instance)

    assert "GALILEO_API_KEY" not in os.environ, "reset() must remove stale GALILEO_API_KEY"

    # Rotate the credential.
    monkeypatch.setenv("SPLUNK_AO_API_KEY", "key-rotated")

    # Second bridge — must pick up the new key now that reset() cleared the old one.
    SplunkAOConfig._bridge_env_vars()
    assert os.environ.get("GALILEO_API_KEY") == "key-rotated", (
        "After reset() + credential rotation, bridge must copy the new key; "
        "got stale value instead"
    )
    # Cleanup: monkeypatch will restore SPLUNK_AO_API_KEY, but the bridge wrote
    # GALILEO_API_KEY directly to os.environ — remove it so it doesn't leak.
    os.environ.pop("GALILEO_API_KEY", None)


def test_reset_removes_all_bridgeable_galileo_vars() -> None:
    """reset() removes all GALILEO_* keys the bridge *could* have written.

    This is acceptable because no consumer of this SDK sets GALILEO_* directly
    (the bridge owns those keys).  This test documents the known behaviour so
    that any future change to this contract is deliberate and reviewed.
    """
    galileo_keys = [galileo_key for _splunk_key, galileo_key in _BRIDGE]

    with (
        patch.dict(os.environ, {k: "user-set" for k in galileo_keys}, clear=False),
        patch("galileo_core.schemas.base_config.GalileoConfig.reset"),
    ):
        mock_instance = MagicMock(spec=SplunkAOConfig)
        SplunkAOConfig.reset(mock_instance)

        # All GALILEO_* keys are removed — this is the documented trade-off of Option 2.
        for galileo_key in galileo_keys:
            assert galileo_key not in os.environ, (
                f"reset() is expected to remove {galileo_key} "
                f"(bridge owns all GALILEO_* keys; no SDK consumer sets them directly)"
            )
