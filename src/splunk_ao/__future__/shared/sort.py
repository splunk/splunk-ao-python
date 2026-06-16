"""Deprecated: use splunk_ao.shared.sort instead of splunk_ao.__future__.shared.sort."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.sort is deprecated. Use splunk_ao.shared.sort instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.sort import Sort, sort  # noqa: E402

__all__ = ["Sort", "sort"]
