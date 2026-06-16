"""Deprecated: use splunk_ao.project instead of splunk_ao.__future__.project."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.project is deprecated. Use splunk_ao.project instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.project import Project  # noqa: E402

__all__ = ["Project"]
