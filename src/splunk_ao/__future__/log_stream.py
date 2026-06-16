"""Deprecated: use splunk_ao.log_stream instead of splunk_ao.__future__.log_stream."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.log_stream is deprecated. Use splunk_ao.log_stream instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.log_stream import LogStream  # noqa: E402

__all__ = ["LogStream"]
