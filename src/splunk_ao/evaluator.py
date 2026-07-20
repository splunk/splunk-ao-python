"""
Evaluators — the renamed successor to Metrics (HYBIM-730).

``Evaluator`` and its concrete subclasses (``LlmEvaluator``, ``CodeEvaluator``,
``LocalEvaluator``, ``SplunkAOEvaluator``) are the canonical names going
forward.  The old ``Metric``-prefixed names are kept as deprecated aliases in
``splunk_ao.__init__`` and will be removed in a future major release.

The underlying implementation lives in ``splunk_ao.metric``; the API endpoints
still use the ``/scorers`` path (server-side rename is tracked separately).
"""
from __future__ import annotations

import warnings

from splunk_ao.metric import (
    BuiltInMetrics,
    CodeMetric,
    LlmMetric,
    LocalMetric,
    Metric,
    SplunkAOMetric,
)

__all__ = [
    "BuiltInEvaluators",
    "CodeEvaluator",
    "Evaluator",
    "LlmEvaluator",
    "LocalEvaluator",
    "SplunkAOEvaluator",
]


class BuiltInEvaluators(BuiltInMetrics):
    """
    Provides attribute-style access to built-in Splunk AO evaluators.

    This is the renamed successor to ``BuiltInMetrics``.  Access built-in
    evaluators via ``Evaluator.evaluators``.

    Examples
    --------
        from splunk_ao import Evaluator
        Evaluator.evaluators.correctness
        Evaluator.evaluators.completeness
    """


class Evaluator(Metric):
    """
    Base class for all Splunk AO evaluators.

    ``Evaluator`` is the new name for what was previously called a *Metric*.
    All functionality is inherited from ``splunk_ao.metric.Metric`` unchanged.

    Use one of the concrete subclasses for new code:

    - ``SplunkAOEvaluator`` — built-in Splunk AO scorers (``Evaluator.evaluators.*``)
    - ``LlmEvaluator`` — custom LLM-judge evaluators
    - ``LocalEvaluator`` — local function-based evaluators
    - ``CodeEvaluator`` — code-based evaluators

    Class Attributes
    ----------------
    evaluators : BuiltInEvaluators
        Access built-in Splunk AO evaluators.

    Examples
    --------
        from splunk_ao import Evaluator, AgentStream, SplunkAOMetrics

        stream = AgentStream.get(name="prod-traces", project_name="my-project")
        stream.set_metrics([
            Evaluator.evaluators.correctness,
            Evaluator.evaluators.completeness,
        ])

        # Get an existing evaluator by name
        ev = Evaluator.get(name="factuality-checker")

        # List all evaluators
        evaluators = Evaluator.list()
    """

    evaluators = BuiltInEvaluators()

    # ``metrics`` class attribute is inherited from Metric and intentionally
    # left as-is.  The new canonical accessor is ``Evaluator.evaluators``.


class LlmEvaluator(LlmMetric):
    """
    LLM-based evaluator — the renamed successor to ``LlmMetric``.

    See ``splunk_ao.metric.LlmMetric`` for the full API reference.

    Examples
    --------
        from splunk_ao import LlmEvaluator

        ev = LlmEvaluator(
            name="response_quality",
            prompt="Rate the quality 1-10: {input} -> {output}",
            model="gpt-4o-mini",
            judges=3,
        ).create()
    """


class CodeEvaluator(CodeMetric):
    """
    Code-based evaluator — the renamed successor to ``CodeMetric``.

    See ``splunk_ao.metric.CodeMetric`` for the full API reference.

    Examples
    --------
        from splunk_ao import CodeEvaluator

        ev = CodeEvaluator(
            name="custom_scorer",
            code="def scorer_fn(step): return 1.0",
        ).create()
    """


class LocalEvaluator(LocalMetric):
    """
    Local function-based evaluator — the renamed successor to ``LocalMetric``.

    See ``splunk_ao.metric.LocalMetric`` for the full API reference.

    Examples
    --------
        from splunk_ao import LocalEvaluator

        def my_fn(trace):
            return 0.5

        ev = LocalEvaluator(name="my_scorer", scorer_fn=my_fn)
    """


class SplunkAOEvaluator(SplunkAOMetric):
    """
    Built-in Splunk AO scorer evaluator — the renamed successor to ``SplunkAOMetric``.

    Access built-in evaluators via ``Evaluator.evaluators.*``.

    Examples
    --------
        from splunk_ao import Evaluator

        ev = Evaluator.get(name="correctness")
        assert isinstance(ev, SplunkAOEvaluator)
    """


# ---------------------------------------------------------------------------
# Deprecated aliases for the old Metric-prefixed names
# ---------------------------------------------------------------------------

def __getattr__(name: str) -> object:
    _deprecated = {
        "Metric": ("Evaluator", Evaluator),
        "LlmMetric": ("LlmEvaluator", LlmEvaluator),
        "CodeMetric": ("CodeEvaluator", CodeEvaluator),
        "LocalMetric": ("LocalEvaluator", LocalEvaluator),
        "SplunkAOMetric": ("SplunkAOEvaluator", SplunkAOEvaluator),
        "BuiltInMetrics": ("BuiltInEvaluators", BuiltInEvaluators),
    }
    if name in _deprecated:
        new_name, obj = _deprecated[name]
        warnings.warn(
            f"splunk_ao.evaluator.{name} is deprecated; use {new_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return obj
    raise AttributeError(f"module 'splunk_ao.evaluator' has no attribute {name!r}")
