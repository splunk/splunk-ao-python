"""Deployment detection and mode-specific configuration."""

import os
from dataclasses import dataclass
from enum import StrEnum

from pydantic import SecretStr

from splunk_ao.shared.exceptions import AmbiguousConfigurationError, MissingConfigurationError

_O11Y_ENV_VARS = ("SPLUNK_AO_REALM", "SPLUNK_AO_SF_TOKEN", "SPLUNK_AO_SF_API_TOKEN")
_STANDALONE_ENV_VARS = ("SPLUNK_AO_API_KEY", "SPLUNK_AO_CONSOLE_URL", "SPLUNK_AO_API_URL")


class DeploymentMode(StrEnum):
    """Supported Splunk AO deployment modes."""

    O11Y = "o11y"
    STANDALONE = "standalone"


def _env(name: str) -> str | None:
    return os.environ.get(name) or None


def resolve_deployment() -> DeploymentMode:
    """Infer the deployment mode from the configured environment variables."""
    present_o11y = [name for name in _O11Y_ENV_VARS if _env(name)]
    present_standalone = [name for name in _STANDALONE_ENV_VARS if _env(name)]

    if present_o11y and present_standalone:
        raise AmbiguousConfigurationError(
            "Both o11y and standalone configuration detected. "
            f"O11y variables set: {', '.join(present_o11y)}. "
            f"Standalone variables set: {', '.join(present_standalone)}."
        )
    if present_o11y:
        return DeploymentMode.O11Y
    if present_standalone:
        return DeploymentMode.STANDALONE

    raise MissingConfigurationError(
        "No Splunk AO deployment configuration detected. Set an o11y variable "
        f"({', '.join(_O11Y_ENV_VARS)}) or a standalone variable "
        f"({', '.join(_STANDALONE_ENV_VARS)})."
    )


@dataclass
class O11yConfig:
    """Configuration for a Splunk Observability Cloud deployment."""

    realm: str
    sf_token: SecretStr | None = None
    sf_api_token: SecretStr | None = None

    def __post_init__(self) -> None:
        missing = []
        if not self.realm:
            missing.append("SPLUNK_AO_REALM")
        if self.sf_token is None and self.sf_api_token is None:
            missing.append("one of SPLUNK_AO_SF_TOKEN or SPLUNK_AO_SF_API_TOKEN")
        if missing:
            raise MissingConfigurationError(f"O11y deployment requires {' and '.join(missing)} to be set.")

        if self.sf_token is not None and not isinstance(self.sf_token, SecretStr):
            self.sf_token = SecretStr(self.sf_token)
        if self.sf_api_token is not None and not isinstance(self.sf_api_token, SecretStr):
            self.sf_api_token = SecretStr(self.sf_api_token)

    @classmethod
    def from_env(cls) -> "O11yConfig":
        """Load and validate o11y configuration from the environment."""
        realm = _env("SPLUNK_AO_REALM")
        sf_token = _env("SPLUNK_AO_SF_TOKEN")
        sf_api_token = _env("SPLUNK_AO_SF_API_TOKEN")
        return cls(
            realm=realm or "",
            sf_token=SecretStr(sf_token) if sf_token else None,
            sf_api_token=SecretStr(sf_api_token) if sf_api_token else None,
        )

    @property
    def otlp_endpoint(self) -> str:
        """Return the realm-derived OTLP trace ingest endpoint."""
        return f"https://ingest.{self.realm}.observability.splunkcloud.com/v2/trace/otlp"

    @property
    def crud_token(self) -> SecretStr:
        """Return the API token when set, otherwise the ingest token."""
        if self.sf_api_token is not None:
            return self.sf_api_token
        if self.sf_token is not None:
            return self.sf_token
        raise MissingConfigurationError("O11y CRUD requires SPLUNK_AO_SF_API_TOKEN or SPLUNK_AO_SF_TOKEN to be set.")

    def require_ingest_token(self) -> SecretStr:
        """Return the token required for OTLP trace export."""
        if self.sf_token is None:
            raise MissingConfigurationError(
                "O11y OTLP trace export requires SPLUNK_AO_SF_TOKEN. "
                "SPLUNK_AO_SF_API_TOKEN supports CRUD operations only."
            )
        return self.sf_token

    @property
    def api_root(self) -> str:
        """Return the realm-derived application origin used by the AO API."""
        return f"https://app.{self.realm}.observability.splunkcloud.com"

    def require_api_url(self) -> str:
        """Return the realm-derived AO CRUD API URL."""
        return f"{self.api_root}/ao/api/"

    def require_console_url(self) -> str:
        """Return the realm-derived AO console URL."""
        return f"https://app.{self.realm}.observability.splunkcloud.com/"


@dataclass
class StandaloneConfig:
    """Configuration for a standalone Splunk AO deployment."""

    api_key: SecretStr
    console_url: str
    api_url: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, SecretStr):
            self.api_key = SecretStr(self.api_key)

    @classmethod
    def from_env(cls) -> "StandaloneConfig":
        """Load and validate standalone configuration from the environment."""
        api_key = _env("SPLUNK_AO_API_KEY")
        console_url = _env("SPLUNK_AO_CONSOLE_URL")

        if api_key is None or console_url is None:
            missing = [
                name
                for name, value in (("SPLUNK_AO_API_KEY", api_key), ("SPLUNK_AO_CONSOLE_URL", console_url))
                if value is None
            ]
            raise MissingConfigurationError(f"Standalone deployment requires {' and '.join(missing)} to be set.")

        return cls(api_key=SecretStr(api_key), console_url=console_url, api_url=_env("SPLUNK_AO_API_URL"))

    @property
    def otlp_endpoint(self) -> str:
        """Return the explicit or console-derived OTLP trace endpoint."""
        base = self.api_url or self.console_url.replace("://console.", "://api.", 1).replace("://app.", "://api.", 1)
        return f"{base.rstrip('/')}/otel/v1/traces"
