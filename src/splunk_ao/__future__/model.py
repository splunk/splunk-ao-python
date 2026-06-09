"""Deprecated: use splunk_ao.model instead of splunk_ao.__future__.model."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.model is deprecated. Use splunk_ao.model instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.model import Model  # noqa: E402

__all__ = ["Model"]
