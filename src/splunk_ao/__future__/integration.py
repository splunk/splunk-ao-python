"""Deprecated: use splunk_ao.integration instead of splunk_ao.__future__.integration."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.integration is deprecated. Use splunk_ao.integration instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.integration import Integration  # noqa: E402

__all__ = ["Integration"]
