"""Deprecated: use splunk_ao.shared.base instead of splunk_ao.__future__.shared.base."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.base is deprecated. Use splunk_ao.shared.base instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.base import StateManagementMixin, SyncState  # noqa: E402

__all__ = ["StateManagementMixin", "SyncState"]
