# mypy: disable-error-code=syntax
# We need to ignore syntax errors until https://github.com/python/mypy/issues/17535 is resolved.
import os
from collections.abc import Iterator
from typing import Any, ClassVar, Optional

from httpx import Response
from pydantic import SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_core import Url

from galileo_core.constants.request_method import RequestMethod
from galileo_core.helpers.api_client import ApiClient
from galileo_core.schemas.base_config import GalileoConfig
from splunk_ao.constants import DEFAULT_CONSOLE_URL
from splunk_ao.deployment import DeploymentMode, O11yConfig
from splunk_ao.deployment import resolve_deployment as _resolve_deployment
from splunk_ao.shared.exceptions import ConfigurationError, MissingConfigurationError


class O11yApiClient(ApiClient):
    """API client for Splunk Observability Cloud AO endpoints."""

    sf_token: SecretStr
    path_prefix: str = "/ao/api"

    @property
    def auth_header(self) -> dict[str, str]:
        return {"X-SF-Token": self.sf_token.get_secret_value()}

    def _prefixed(self, path: str) -> str:
        normalized_path = f"/{path.lstrip('/')}"
        prefix = self.path_prefix.strip("/")
        if not prefix:
            return normalized_path

        normalized_prefix = f"/{prefix}"
        if normalized_path == normalized_prefix or normalized_path.startswith(f"{normalized_prefix}/"):
            return normalized_path
        return f"{normalized_prefix}{normalized_path}"

    async def arequest(self, method: RequestMethod, path: str, *args: Any, **kwargs: Any) -> Any:
        return await super().arequest(method, self._prefixed(path), *args, **kwargs)

    def stream_request(self, method: RequestMethod, path: str, *args: Any, **kwargs: Any) -> Iterator[Response]:
        return super().stream_request(method, self._prefixed(path), *args, **kwargs)


# Mapping of SPLUNK_AO_* → GALILEO_* env var pairs used by the bridge.
# Defined at module level so both _bridge_env_vars() and reset() can reference
# the same authoritative list without duplication.
_BRIDGE: list[tuple[str, str]] = [
    ("SPLUNK_AO_API_KEY", "GALILEO_API_KEY"),
    ("SPLUNK_AO_API_URL", "GALILEO_API_URL"),
    ("SPLUNK_AO_CONSOLE_URL", "GALILEO_CONSOLE_URL"),
    ("SPLUNK_AO_PROJECT", "GALILEO_PROJECT"),
    ("SPLUNK_AO_PROJECT_ID", "GALILEO_PROJECT_ID"),
    ("SPLUNK_AO_AGENT_STREAM", "GALILEO_LOG_STREAM"),
    ("SPLUNK_AO_LOG_STREAM", "GALILEO_LOG_STREAM"),  # deprecated alias
    ("SPLUNK_AO_AGENT_STREAM_ID", "GALILEO_LOG_STREAM_ID"),
    ("SPLUNK_AO_LOG_STREAM_ID", "GALILEO_LOG_STREAM_ID"),  # deprecated alias
    ("SPLUNK_AO_JWT_TOKEN", "GALILEO_JWT_TOKEN"),
    ("SPLUNK_AO_SSO_ID_TOKEN", "GALILEO_SSO_ID_TOKEN"),
    ("SPLUNK_AO_SSO_PROVIDER", "GALILEO_SSO_PROVIDER"),
    ("SPLUNK_AO_USERNAME", "GALILEO_USERNAME"),
    ("SPLUNK_AO_PASSWORD", "GALILEO_PASSWORD"),
    ("SPLUNK_AO_MODE", "GALILEO_MODE"),
]


class SplunkAOConfig(GalileoConfig):
    """Configure authentication and endpoints for standalone and O11y deployments."""

    # Config file for this project.
    config_filename: str = "galileo-python-config.json"
    console_url: Url = DEFAULT_CONSOLE_URL

    _instance: ClassVar[Optional["SplunkAOConfig"]] = None

    def reset(self) -> None:
        # Remove any GALILEO_* keys the bridge injected into os.environ so that
        # the next get() call re-bridges from scratch with whatever SPLUNK_AO_*
        # values are current.  Without this, galileo-core would re-read the
        # stale bridged value after a credential rotation because _bridge_env_vars
        # guards against overwriting an already-present GALILEO_* key.
        for _splunk_key, galileo_key in _BRIDGE:
            os.environ.pop(galileo_key, None)
        SplunkAOConfig._instance = None
        super().reset()

    @classmethod
    def resolve_deployment(cls) -> DeploymentMode:
        """Infer the deployment mode from configured environment variables."""
        return _resolve_deployment()

    @classmethod
    def _is_o11y_env(cls) -> bool:
        try:
            return cls.resolve_deployment() == DeploymentMode.O11Y
        except MissingConfigurationError:
            return False

    @field_validator("api_url", mode="before")
    @classmethod
    def set_api_url(cls, api_url: str | Url | None, info: ValidationInfo) -> Url:
        """Derive the O11y API URL from its realm and preserve standalone validation."""
        if cls._is_o11y_env():
            return Url(O11yConfig.from_env().require_api_url())
        return super().set_api_url(api_url, info)

    @model_validator(mode="after")
    def set_jwt_token(self) -> "SplunkAOConfig":
        """Skip standalone JWT exchange when O11y uses direct SF-token authentication."""
        if self._is_o11y_env():
            self.jwt_token = None
            self.refresh_token = None
            return self
        super().set_jwt_token()
        return self

    @model_validator(mode="after")
    def set_validated_api_client(self) -> "SplunkAOConfig":
        """Use the SF-token aware API client for O11y deployments."""
        if self._is_o11y_env():
            o11y = O11yConfig.from_env()
            self.validated_api_client = O11yApiClient(
                host=o11y.api_root, sf_token=o11y.crud_token, jwt_token=SecretStr(""), ssl_context=self.ssl_context
            )
            return self
        super().set_validated_api_client()
        return self

    def _uses_o11y_api_client(self) -> bool:
        return isinstance(self.validated_api_client, O11yApiClient)

    def refresh_jwt_token(self) -> None:
        """Skip JWT refresh when authenticating directly with an O11y SF token."""
        if self._uses_o11y_api_client():
            return
        super().refresh_jwt_token()

    @classmethod
    def get(cls, **kwargs: Any) -> "SplunkAOConfig":
        """Initialize the shared config with deployment-aware auth validation."""
        if cls._instance is None:
            cls._bridge_env_vars()
            error_message = cls._check_auth_config(kwargs)
            if error_message is not None:
                raise ConfigurationError(error_message)
        cls._instance = cls._get(cls._instance, **kwargs)
        assert cls._instance is not None, "Failed to initialize SplunkAOConfig"
        return cls._instance

    @classmethod
    def _bridge_env_vars(cls) -> None:
        """Bridge SPLUNK_AO_* env vars into GALILEO_* for galileo-core compatibility.

        galileo-core still reads GALILEO_* env vars. Until galileo-core is updated,
        this method propagates any SPLUNK_AO_* values to their GALILEO_* equivalents
        so that galileo-core can authenticate successfully.

        Only bridges values that are not already set — explicit GALILEO_* overrides win.
        reset() clears any previously-bridged GALILEO_* keys so that this guard
        cannot return a stale value after a credential rotation.
        """
        if cls._is_o11y_env() and "GALILEO_CONSOLE_URL" not in os.environ:
            os.environ["GALILEO_CONSOLE_URL"] = O11yConfig.from_env().require_console_url()

        for new_key, old_key in _BRIDGE:
            if new_key in os.environ and old_key not in os.environ:
                os.environ[old_key] = os.environ[new_key]

    @staticmethod
    def _check_auth_config(kwargs: dict) -> str | None:
        """Validate that a complete auth method is configured.

        Returns None if at least one complete auth method is detectable from
        either kwargs or the environment. Otherwise returns a specific error
        message identifying what's missing.

        Auth methods supported by the underlying config model:
          - SF tokens (o11y): SPLUNK_AO_REALM and at least one of
            SPLUNK_AO_SF_TOKEN or SPLUNK_AO_SF_API_TOKEN env vars
          - API key (standalone): api_key kwarg or SPLUNK_AO_API_KEY env
          - Pre-exchanged JWT (standalone): jwt_token or SPLUNK_AO_JWT_TOKEN
          - SSO (paired): sso_id_token + sso_provider, both kwargs and env vars
          - Username/password (paired): username + password, both kwargs and env vars

        For standalone auth, kwargs and env vars are interchangeable — e.g.
        sso_id_token can come from a kwarg while sso_provider comes from the
        environment. O11y tokens are environment-only.
        """

        def _val(kwarg_name: str, env_name: str) -> str | None:
            value = kwargs.get(kwarg_name)
            if value:
                return str(value)
            return os.environ.get(env_name)

        realm = os.environ.get("SPLUNK_AO_REALM")
        sf_token = os.environ.get("SPLUNK_AO_SF_TOKEN")
        sf_api_token = os.environ.get("SPLUNK_AO_SF_API_TOKEN")
        if realm or sf_token or sf_api_token:
            if not realm:
                return "O11y authentication requires SPLUNK_AO_REALM to be set."
            if not sf_token and not sf_api_token:
                return "O11y authentication requires SPLUNK_AO_SF_TOKEN or SPLUNK_AO_SF_API_TOKEN to be set."
            return None

        # Standalone methods — either alone is sufficient.
        if _val("api_key", "SPLUNK_AO_API_KEY"):
            return None
        if _val("jwt_token", "SPLUNK_AO_JWT_TOKEN"):
            return None

        # SSO requires BOTH id_token and provider.
        sso_id_token = _val("sso_id_token", "SPLUNK_AO_SSO_ID_TOKEN")
        sso_provider = _val("sso_provider", "SPLUNK_AO_SSO_PROVIDER")
        if sso_id_token and sso_provider:
            return None
        if sso_id_token and not sso_provider:
            return (
                "SPLUNK_AO_SSO_ID_TOKEN is set but SPLUNK_AO_SSO_PROVIDER is missing. "
                "SSO authentication requires both. Set SPLUNK_AO_SSO_PROVIDER to your "
                "IdP identifier (e.g. 'okta', 'custom') or pass sso_provider=... "
                "as a keyword argument."
            )
        if sso_provider and not sso_id_token:
            return (
                "SPLUNK_AO_SSO_PROVIDER is set but SPLUNK_AO_SSO_ID_TOKEN is missing. "
                "SSO authentication requires both. Set SPLUNK_AO_SSO_ID_TOKEN to your "
                "IdP-issued ID token or pass sso_id_token=... as a keyword argument."
            )

        # Username/password requires BOTH.
        username = _val("username", "SPLUNK_AO_USERNAME")
        password = _val("password", "SPLUNK_AO_PASSWORD")
        if username and password:
            return None
        if username and not password:
            return (
                "SPLUNK_AO_USERNAME is set but SPLUNK_AO_PASSWORD is missing. "
                "Username/password authentication requires both."
            )
        if password and not username:
            return (
                "SPLUNK_AO_PASSWORD is set but SPLUNK_AO_USERNAME is missing. "
                "Username/password authentication requires both."
            )

        # Nothing configured anywhere.
        return (
            "No Splunk AO authentication detected. Set one of: SPLUNK_AO_REALM with "
            "SPLUNK_AO_SF_TOKEN or SPLUNK_AO_SF_API_TOKEN; SPLUNK_AO_API_KEY; "
            "SPLUNK_AO_SSO_ID_TOKEN with SPLUNK_AO_SSO_PROVIDER; "
            "or SPLUNK_AO_USERNAME with SPLUNK_AO_PASSWORD. "
            "Alternatively, pass the equivalent kwargs to SplunkAOConfig.get(). "
            "See https://docs.splunk.com for setup instructions."
        )
