"""Deprecated: use splunk_ao.shared.exceptions instead of splunk_ao.__future__.shared.exceptions."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.exceptions is deprecated. Use splunk_ao.shared.exceptions instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.exceptions import (  # noqa: E402
    APIError,
    ConfigurationError,
    GalileoFutureError,
    IntegrationNotConfiguredError,
    ResourceConflictError,
    ResourceNotFoundError,
    SyncError,
    ValidationError,
)

__all__ = [
    "APIError",
    "ConfigurationError",
    "GalileoFutureError",
    "IntegrationNotConfiguredError",
    "ResourceConflictError",
    "ResourceNotFoundError",
    "SyncError",
    "ValidationError",
]
