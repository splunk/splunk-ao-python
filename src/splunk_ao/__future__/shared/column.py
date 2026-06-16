"""Deprecated: use splunk_ao.shared.column instead of splunk_ao.__future__.shared.column."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.column is deprecated. Use splunk_ao.shared.column instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.column import Column, ColumnCollection, _unwrap_unset  # noqa: E402

__all__ = ["Column", "ColumnCollection", "_unwrap_unset"]
