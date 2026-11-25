"""Utilities for reading environment variables with defaults."""

from os import getenv

from splunk_ao.constants import DEFAULT_AGENT_STREAM_NAME, DEFAULT_MODE, DEFAULT_PROJECT_NAME, LoggerModeType
from splunk_ao.exceptions import SplunkAOLoggerException


def _get_mode_or_default(mode: str | None) -> LoggerModeType:
    """
    Validates the mode value. If the environment variable contains
    an invalid value, falls back to default.

    Parameters
    ----------
    mode : Optional[str]
        The mode value, or None to check environment variable.

    Returns
    -------
    LoggerModeType
        The mode value to use:
        Both "batch" and the temporarily retained "distributed" value use
        scheduled OTLP batch export. The distinction remains only for the
        deprecated ingestion-hook compatibility guard.
    """
    if mode is None:
        mode = getenv("SPLUNK_AO_MODE", DEFAULT_MODE)

    if not isinstance(mode, str):
        raise SplunkAOLoggerException(f"Invalid mode: {mode}. Mode must be 'batch' or 'distributed'.")

    mode = mode.lower()
    if mode not in ("batch", "distributed"):
        raise SplunkAOLoggerException(f"Invalid mode: '{mode}'. Mode must be 'batch' or 'distributed'.")

    return mode  # type: ignore[return-value]


def _get_project_or_default(project: str | None) -> str:
    """
    Get the project name, falling back to SPLUNK_AO_PROJECT env var or default.

    Parameters
    ----------
    project : Optional[str]
        The project name, or None to check environment variable.

    Returns
    -------
    str
        The project name to use.
    """
    if project is None:
        return getenv("SPLUNK_AO_PROJECT", DEFAULT_PROJECT_NAME)
    return project


def _get_agent_stream_or_default(agent_stream: str | None) -> str:
    """
    Get the log stream name, falling back to SPLUNK_AO_AGENT_STREAM env var or default.

    Parameters
    ----------
    agent_stream : Optional[str]
        The log stream name, or None to check environment variable.

    Returns
    -------
    str
        The log stream name to use.
    """
    if agent_stream is None:
        # SPLUNK_AO_LOG_STREAM is a deprecated alias; SPLUNK_AO_AGENT_STREAM takes precedence.
        return getenv("SPLUNK_AO_AGENT_STREAM") or getenv("SPLUNK_AO_LOG_STREAM") or DEFAULT_AGENT_STREAM_NAME
    return agent_stream


def _get_project_from_env() -> str | None:
    """
    Get the project name from SPLUNK_AO_PROJECT environment variable.

    Returns
    -------
    Optional[str]
        The project name from environment variable, or None if not set.
    """
    return getenv("SPLUNK_AO_PROJECT")


def _get_project_id_from_env() -> str | None:
    """
    Get the project ID from SPLUNK_AO_PROJECT_ID environment variable.

    Returns
    -------
    Optional[str]
        The project ID from environment variable, or None if not set.
    """
    return getenv("SPLUNK_AO_PROJECT_ID")


def _get_agent_stream_from_env() -> str | None:
    """
    Get the log stream name from SPLUNK_AO_AGENT_STREAM environment variable.

    Returns
    -------
    Optional[str]
        The log stream name from environment variable, or None if not set.
    """
    # SPLUNK_AO_LOG_STREAM is a deprecated alias; SPLUNK_AO_AGENT_STREAM takes precedence.
    return getenv("SPLUNK_AO_AGENT_STREAM") or getenv("SPLUNK_AO_LOG_STREAM") or None


def _get_agent_stream_id_from_env() -> str | None:
    """
    Get the log stream ID from SPLUNK_AO_AGENT_STREAM_ID environment variable.

    Returns
    -------
    Optional[str]
        The log stream ID from environment variable, or None if not set.
    """
    # SPLUNK_AO_LOG_STREAM_ID is a deprecated alias; SPLUNK_AO_AGENT_STREAM_ID takes precedence.
    return getenv("SPLUNK_AO_AGENT_STREAM_ID") or getenv("SPLUNK_AO_LOG_STREAM_ID") or None
