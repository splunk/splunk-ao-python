"""Resolve Galileo context for Agent Control calls.

This module produces generic Agent Control targets from Galileo state. It does
not import the Agent Control SDK; callers wire the two SDKs together explicitly.

For Agent Control telemetry ingestion, use ``splunk_ao.handlers.agent_control``.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from uuid import UUID

from splunk_ao.decorator import splunk_ao_context
from splunk_ao.utils.env_helpers import _get_agent_stream_or_default, _get_project_or_default
from splunk_ao.utils.singleton import SplunkAOLoggerSingleton

LOG_STREAM_TARGET_TYPE = "log_stream"


class AgentControlTargetUnresolvedError(ValueError):
    """Raised when no Agent Control target can be resolved from available inputs."""


@dataclass(frozen=True)
class AgentControlTarget:
    """A target identifier that can be passed to Agent Control.

    Parameters
    ----------
    target_type
        Opaque Agent Control target type. Agent Control treats this value as
        deployer-defined; Galileo currently auto-resolves only ``log_stream``
        targets.
    target_id
        Opaque Agent Control target ID.
    project_id
        Galileo project ID for logs, debugging, and audit context only. Agent
        Control resolves project ownership from ``target_type`` and
        ``target_id``.
    """

    target_type: str
    target_id: str
    project_id: str | None = None


def get_agent_control_target(
    *,
    target_type: str = LOG_STREAM_TARGET_TYPE,
    target_id: str | None = None,
    agent_stream_id: str | None = None,
    project_id: str | None = None,
) -> AgentControlTarget:
    """Resolve an Agent Control target from explicit inputs or Galileo context.

    Resolution order:

    1. Explicit ``target_id``.
    2. Explicit ``agent_stream_id`` for ``log_stream`` targets.
    3. ``SPLUNK_AO_AGENT_STREAM_ID`` for ``log_stream`` targets.
    4. An already-initialized ``splunk_ao_context`` logger.

    This helper does not resolve agent stream names over the network. If only an
    agent stream name is available, resolve it with the Galileo SDK first and pass
    the resulting ID explicitly.
    """
    explicit_project_id = _strip_optional_string(project_id)
    env_project_id = _strip_optional_string(os.getenv("SPLUNK_AO_PROJECT_ID"))
    resolved_project_id = explicit_project_id or env_project_id

    if target_type == LOG_STREAM_TARGET_TYPE:
        target_id = _strip_optional_string(target_id)
    agent_stream_id = _strip_optional_string(agent_stream_id)

    if target_type != LOG_STREAM_TARGET_TYPE and agent_stream_id is not None:
        raise AgentControlTargetUnresolvedError("agent_stream_id can only be used with target_type='log_stream'.")

    if target_id is not None and agent_stream_id is not None and target_id != agent_stream_id:
        raise AgentControlTargetUnresolvedError("target_id and agent_stream_id must match when both are provided.")

    resolved_target_id = target_id if target_id is not None else agent_stream_id
    if resolved_target_id is not None:
        if target_type == LOG_STREAM_TARGET_TYPE:
            source_label = "target_id" if target_id is not None else "agent_stream_id"
            _validate_uuid(resolved_target_id, source_label)
        return AgentControlTarget(target_type=target_type, target_id=resolved_target_id, project_id=resolved_project_id)

    if target_type != LOG_STREAM_TARGET_TYPE:
        raise AgentControlTargetUnresolvedError(
            f"Could not resolve Agent Control target for target_type={target_type!r}. "
            "Provide target_id=<id> explicitly."
        )

    # SPLUNK_AO_LOG_STREAM_ID is a deprecated alias; SPLUNK_AO_AGENT_STREAM_ID takes precedence.
    env_log_stream_id = _strip_optional_string(
        os.getenv("SPLUNK_AO_AGENT_STREAM_ID") or os.getenv("SPLUNK_AO_LOG_STREAM_ID")
    )
    if env_log_stream_id:
        _validate_uuid(env_log_stream_id, "SPLUNK_AO_AGENT_STREAM_ID")
        return AgentControlTarget(
            target_type=LOG_STREAM_TARGET_TYPE, target_id=env_log_stream_id, project_id=resolved_project_id
        )

    context_target = _resolve_agent_stream_from_cached_context()
    if context_target is not None:
        return AgentControlTarget(
            target_type=context_target.target_type,
            target_id=context_target.target_id,
            project_id=explicit_project_id or context_target.project_id or env_project_id,
        )

    raise AgentControlTargetUnresolvedError(
        "Could not resolve Galileo agent stream ID for Agent Control. Provide one of:\n"
        "  1. target_id=<uuid> or agent_stream_id=<uuid> argument\n"
        "  2. SPLUNK_AO_AGENT_STREAM_ID environment variable\n"
        "  3. An initialized splunk_ao_context with a resolved agent stream ID"
    )


def _validate_uuid(value: str, source: str) -> None:
    try:
        UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise AgentControlTargetUnresolvedError(f"{source}={value!r} is not a valid UUID.") from exc


def _strip_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def _resolve_agent_stream_from_cached_context() -> AgentControlTarget | None:
    current_project = _get_project_or_default(splunk_ao_context.get_current_project())
    current_log_stream = _get_agent_stream_or_default(splunk_ao_context.get_current_agent_stream())
    current_thread_name = threading.current_thread().name

    # Read cached logger state directly so this helper never creates or resolves
    # projects/agent streams as a side effect of building an Agent Control target.
    # Use the same default/env fallback as SplunkAOLogger so callers that rely on
    # default project/agent-stream creation can still reuse the resolved IDs.
    for key, logger in SplunkAOLoggerSingleton().get_all_loggers().items():
        if not key or key[0] != current_thread_name:
            continue
        if logger.project_name != current_project or logger.agent_stream_name != current_log_stream:
            continue
        if logger.agent_stream_id is None:
            continue
        return AgentControlTarget(
            target_type=LOG_STREAM_TARGET_TYPE, target_id=logger.agent_stream_id, project_id=logger.project_id
        )

    return None


__all__ = ["AgentControlTarget", "AgentControlTargetUnresolvedError", "get_agent_control_target"]
