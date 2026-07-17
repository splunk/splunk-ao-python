"""Deprecated: use splunk_ao.evaluator instead of splunk_ao.__future__.evaluator."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.evaluator is deprecated. "
    "Use splunk_ao.evaluator instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.evaluator import (  # noqa: E402
    CodeEvaluator,
    Evaluator,
    LlmEvaluator,
    LocalEvaluator,
    SplunkAOEvaluator,
)

__all__ = ["CodeEvaluator", "Evaluator", "LlmEvaluator", "LocalEvaluator", "SplunkAOEvaluator"]
