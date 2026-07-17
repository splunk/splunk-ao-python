"""Deprecated: use splunk_ao.agent_stream instead of splunk_ao.__future__.agent_stream."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.agent_stream is deprecated. "
    "Use splunk_ao.agent_stream instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.agent_stream import AgentStream  # noqa: E402

__all__ = ["AgentStream"]
