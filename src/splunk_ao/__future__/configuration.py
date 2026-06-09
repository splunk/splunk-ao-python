"""Deprecated: use splunk_ao.configuration instead of splunk_ao.__future__.configuration."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.configuration is deprecated. Use splunk_ao.configuration instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.configuration import (  # noqa: E402
    _CONFIGURATION_KEYS,
    _KEYS_BY_NAME,
    VALID_LOG_LEVELS,
    ConfigKey,
    Configuration,
    ConfigurationMeta,
    parse_log_level,
)

__all__ = [
    "VALID_LOG_LEVELS",
    "_CONFIGURATION_KEYS",
    "_KEYS_BY_NAME",
    "ConfigKey",
    "Configuration",
    "ConfigurationMeta",
    "parse_log_level",
]
