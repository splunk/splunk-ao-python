"""
Agent Streams service layer — the renamed successor to Log Streams (HYBIM-730).

Provides ``AgentStreams`` (service class) and the module-level convenience
functions ``get_agent_stream``, ``list_agent_streams``, ``create_agent_stream``,
and ``enable_evaluators``.

The old ``log_streams`` module and its symbols remain available but are
deprecated.
"""
from __future__ import annotations

import builtins
import warnings

from splunk_ao.agent_stream import AgentStream
from splunk_ao.log_streams import LogStreams, create_log_stream, get_log_stream, list_log_streams
from splunk_ao.resources.types import Unset
from splunk_ao.schema.metrics import LocalMetricConfig, Metric, SplunkAOMetrics

__all__ = [
    "AgentStreams",
    "create_agent_stream",
    "enable_evaluators",
    "get_agent_stream",
    "list_agent_streams",
]


class AgentStreams(LogStreams):
    """
    Low-level service class for managing agent streams.

    ``AgentStreams`` is the new name for the ``LogStreams`` service class.
    Inherits all methods from ``LogStreams`` and returns ``AgentStream``
    instances from listing/retrieval methods.

    Examples
    --------
        from splunk_ao.agent_streams import AgentStreams

        svc = AgentStreams()
        stream = svc.get(name="prod-traces", project_name="my-project")
        streams = svc.list(project_name="my-project")
    """


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def get_agent_stream(
    *,
    name: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> AgentStream | None:
    """
    Retrieve an agent stream by name.

    Parameters
    ----------
    name:
        The agent stream name.
    project_id:
        The project ID (mutually exclusive with *project_name*).
    project_name:
        The project name (mutually exclusive with *project_id*).

    Returns
    -------
    AgentStream | None
        The agent stream if found, ``None`` otherwise.
    """
    result = get_log_stream(name=name, project_id=project_id, project_name=project_name)
    if result is None:
        return None
    stream = AgentStream.__new__(AgentStream)
    stream.__dict__.update(result.__dict__)
    return stream


def list_agent_streams(
    *,
    project_id: str | None = None,
    project_name: str | None = None,
    limit: Unset | int = 100,
    starting_token: Unset | int = 0,
) -> builtins.list[AgentStream]:
    """
    List agent streams for a project.

    Parameters
    ----------
    project_id:
        The project ID (mutually exclusive with *project_name*).
    project_name:
        The project name (mutually exclusive with *project_id*).
    limit:
        Maximum number of results per page. Defaults to 100.
    starting_token:
        Pagination token. Defaults to 0.

    Returns
    -------
    list[AgentStream]
        A page of agent streams.
    """
    log_streams = list_log_streams(
        project_id=project_id,
        project_name=project_name,
        limit=limit,
        starting_token=starting_token,
    )
    result: builtins.list[AgentStream] = []
    for ls in log_streams:
        s = AgentStream.__new__(AgentStream)
        s.__dict__.update(ls.__dict__)
        result.append(s)
    return result


def create_agent_stream(
    name: str,
    project_id: str | None = None,
    project_name: str | None = None,
) -> AgentStream:
    """
    Create a new agent stream.

    Parameters
    ----------
    name:
        The agent stream name.
    project_id:
        The project ID (mutually exclusive with *project_name*).
    project_name:
        The project name (mutually exclusive with *project_id*).

    Returns
    -------
    AgentStream
        The created agent stream.
    """
    ls = create_log_stream(name=name, project_id=project_id, project_name=project_name)
    stream = AgentStream.__new__(AgentStream)
    stream.__dict__.update(ls.__dict__)
    return stream


def enable_evaluators(
    *,
    agent_stream_name: str | None = None,
    project_name: str | None = None,
    metrics: builtins.list[SplunkAOMetrics | Metric | LocalMetricConfig | str],
) -> builtins.list[LocalMetricConfig]:
    """
    Enable evaluators (formerly *metrics*) on an agent stream.

    Falls back to the ``SPLUNK_AO_LOG_STREAM`` and ``SPLUNK_AO_PROJECT``
    environment variables when *agent_stream_name* / *project_name* are
    not provided explicitly.

    Parameters
    ----------
    agent_stream_name:
        The agent stream name.  Falls back to ``SPLUNK_AO_LOG_STREAM`` env var.
    project_name:
        The project name.  Falls back to ``SPLUNK_AO_PROJECT`` env var.
    metrics:
        Evaluators to enable.  Accepts ``SplunkAOMetrics`` enum values,
        ``Metric`` objects, ``LocalMetricConfig`` objects, or string names.

    Returns
    -------
    list[LocalMetricConfig]
        Local evaluator configurations that must be computed client-side.
    """
    from splunk_ao.log_streams import LogStreams

    return LogStreams().enable_metrics(
        log_stream_name=agent_stream_name,
        project_name=project_name,
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Deprecated aliases for the old ``log_streams`` convenience functions
# ---------------------------------------------------------------------------

def __getattr__(name: str) -> object:
    _deprecated = {
        "get_log_stream": ("get_agent_stream", get_agent_stream),
        "list_log_streams": ("list_agent_streams", list_agent_streams),
        "create_log_stream": ("create_agent_stream", create_agent_stream),
        "enable_metrics": ("enable_evaluators", enable_evaluators),
    }
    if name in _deprecated:
        new_name, obj = _deprecated[name]
        warnings.warn(
            f"splunk_ao.agent_streams.{name} is deprecated; use {new_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return obj
    raise AttributeError(f"module 'splunk_ao.agent_streams' has no attribute {name!r}")
