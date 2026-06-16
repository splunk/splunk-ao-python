"""Deprecated: use splunk_ao.shared.experiment_result instead of splunk_ao.__future__.shared.experiment_result."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.experiment_result is deprecated. "
    "Use splunk_ao.shared.experiment_result instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.experiment_result import (  # noqa: E402
    ExperimentPhaseInfo,
    ExperimentRunResult,
    ExperimentStatusInfo,
)

__all__ = ["ExperimentPhaseInfo", "ExperimentRunResult", "ExperimentStatusInfo"]
