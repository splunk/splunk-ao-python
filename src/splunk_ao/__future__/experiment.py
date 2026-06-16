"""Deprecated: use splunk_ao.experiment instead of splunk_ao.__future__.experiment."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.experiment is deprecated. Use splunk_ao.experiment instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.experiment import Experiment  # noqa: E402

__all__ = ["Experiment"]
