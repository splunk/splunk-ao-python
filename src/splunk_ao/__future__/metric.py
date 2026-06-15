"""Deprecated: use splunk_ao.metric instead of splunk_ao.__future__.metric."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.metric is deprecated. Use splunk_ao.metric instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.metric import BuiltInMetrics, CodeMetric, LlmMetric, LocalMetric, Metric, SplunkAOMetric  # noqa: E402

__all__ = ["BuiltInMetrics", "CodeMetric", "LlmMetric", "LocalMetric", "Metric", "SplunkAOMetric"]
