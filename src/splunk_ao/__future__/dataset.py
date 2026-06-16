"""Deprecated: use splunk_ao.dataset instead of splunk_ao.__future__.dataset."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.dataset is deprecated. Use splunk_ao.dataset instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.dataset import Dataset  # noqa: E402

__all__ = ["Dataset"]
