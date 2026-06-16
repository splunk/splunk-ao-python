"""Deprecated: use splunk_ao.shared.query_result instead of splunk_ao.__future__.shared.query_result."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.query_result is deprecated. Use splunk_ao.shared.query_result instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.query_result import QueryResult, _flatten_dict  # noqa: E402

__all__ = ["QueryResult", "_flatten_dict"]
