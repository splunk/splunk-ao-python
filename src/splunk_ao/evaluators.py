"""
Evaluators service layer — the renamed successor to Metrics (HYBIM-730).

Provides ``Evaluators`` (service class) and the module-level convenience
functions ``create_custom_llm_evaluator``, ``get_evaluators``, and
``delete_evaluator``.

The old ``metrics`` module and its symbols remain available but are deprecated.
"""
from __future__ import annotations

import datetime
import warnings

from splunk_ao.metrics import Metrics, create_custom_llm_metric, delete_metric, get_metrics
from splunk_ao.resources.models.base_scorer_version_response import BaseScorerVersionResponse
from splunk_ao.resources.models.output_type_enum import OutputTypeEnum
from splunk_ao.resources.models.log_records_metrics_response import LogRecordsMetricsResponse
from galileo_core.schemas.logging.step import StepType
from splunk_ao.search import FilterType

__all__ = [
    "Evaluators",
    "create_custom_llm_evaluator",
    "delete_evaluator",
    "get_evaluators",
]


class Evaluators(Metrics):
    """
    Low-level service class for managing evaluators.

    ``Evaluators`` is the new name for the ``Metrics`` service class.
    Inherits all methods from ``Metrics`` unchanged.

    Examples
    --------
        from splunk_ao.evaluators import Evaluators

        svc = Evaluators()
        svc.delete_metric(name="old-evaluator")
    """


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def create_custom_llm_evaluator(
    name: str,
    user_prompt: str,
    node_level: StepType = StepType.llm,
    cot_enabled: bool = True,
    model_name: str = "gpt-4.1-mini",
    num_judges: int = 3,
    description: str = "",
    tags: list[str] | None = None,
    output_type: OutputTypeEnum = OutputTypeEnum.BOOLEAN,
    ground_truth: bool = False,
) -> BaseScorerVersionResponse:
    """
    Create a custom LLM evaluator.

    This is the renamed equivalent of ``create_custom_llm_metric`` from
    ``splunk_ao.metrics``.

    Parameters
    ----------
    name:
        Name of the evaluator.
    user_prompt:
        Prompt template for the evaluator.
    node_level:
        Node level. Defaults to ``StepType.llm``.
    cot_enabled:
        Whether chain-of-thought reasoning is enabled.
    model_name:
        Model alias to use for judging.
    num_judges:
        Number of judge LLMs to use.
    description:
        Human-readable description.
    tags:
        Tags to associate with the evaluator.
    output_type:
        Output type (boolean, percentage, etc.).
    ground_truth:
        Whether the evaluator requires a ground-truth reference value.

    Returns
    -------
    BaseScorerVersionResponse
        The created evaluator version details.
    """
    return create_custom_llm_metric(
        name=name,
        user_prompt=user_prompt,
        node_level=node_level,
        cot_enabled=cot_enabled,
        model_name=model_name,
        num_judges=num_judges,
        description=description,
        tags=tags,
        output_type=output_type,
        ground_truth=ground_truth,
    )


def get_evaluators(
    project_id: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    experiment_id: str | None = None,
    agent_stream_id: str | None = None,
    filters: list[FilterType] | None = None,
    group_by: str | None = None,
    interval: int = 5,
) -> LogRecordsMetricsResponse:
    """
    Query evaluator results for a project.

    This is the renamed equivalent of ``get_metrics`` from ``splunk_ao.metrics``.

    Parameters
    ----------
    project_id:
        Project UUID.
    start_time:
        Start of the query window.
    end_time:
        End of the query window.
    experiment_id:
        Filter by experiment ID (optional).
    agent_stream_id:
        Filter by agent stream ID (optional).
    filters:
        Additional query filters.
    group_by:
        Field to group results by.
    interval:
        Time interval in seconds.

    Returns
    -------
    LogRecordsMetricsResponse
        Evaluator query results.
    """
    return get_metrics(
        project_id=project_id,
        start_time=start_time,
        end_time=end_time,
        experiment_id=experiment_id,
        log_stream_id=agent_stream_id,
        filters=filters,
        group_by=group_by,
        interval=interval,
    )


def delete_evaluator(name: str) -> None:
    """
    Delete an evaluator by name.

    This is the renamed equivalent of ``delete_metric`` from ``splunk_ao.metrics``.

    Parameters
    ----------
    name:
        The evaluator name to delete.
    """
    return delete_metric(name=name)


# ---------------------------------------------------------------------------
# Deprecated aliases for old ``metrics`` module function names
# ---------------------------------------------------------------------------

def __getattr__(name: str):
    _deprecated = {
        "create_custom_llm_metric": ("create_custom_llm_evaluator", create_custom_llm_evaluator),
        "get_metrics": ("get_evaluators", get_evaluators),
        "delete_metric": ("delete_evaluator", delete_evaluator),
    }
    if name in _deprecated:
        new_name, obj = _deprecated[name]
        warnings.warn(
            f"splunk_ao.evaluators.{name} is deprecated; use {new_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return obj
    raise AttributeError(f"module 'splunk_ao.evaluators' has no attribute {name!r}")
