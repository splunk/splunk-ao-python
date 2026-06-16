"""Deprecated: use splunk_ao.types instead of splunk_ao.__future__.types."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.types is deprecated. Use splunk_ao.types instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.types import MetricSpec  # noqa: E402

__all__ = ["MetricSpec"]
