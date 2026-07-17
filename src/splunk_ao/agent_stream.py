"""
Agent Streams — the renamed successor to Log Streams (HYBIM-730).

``AgentStream`` is the canonical name going forward.  ``LogStream`` is kept
as a deprecated alias in ``splunk_ao.__init__`` and will be removed in a
future major release.

The underlying implementation is shared with ``splunk_ao.log_stream``; the
API endpoints still use the ``/log_streams`` path (server-side rename is
tracked separately).
"""
from __future__ import annotations

import warnings

from splunk_ao.log_stream import LogStream

__all__ = ["AgentStream"]


class AgentStream(LogStream):
    """
    Object-centric interface for Splunk AO agent streams.

    ``AgentStream`` is the new name for what was previously called a
    *Log Stream*.  All functionality is identical; only the name has
    changed.  Use ``AgentStream`` for all new code.

    See ``splunk_ao.log_stream.LogStream`` for the full API reference —
    every method, property, and class-method is inherited unchanged.

    Examples
    --------
        from splunk_ao import AgentStream

        # Create and persist a new agent stream
        stream = AgentStream(name="prod-traces", project_name="my-project").create()

        # Retrieve an existing stream
        stream = AgentStream.get(name="prod-traces", project_name="my-project")

        # List streams for a project
        streams = AgentStream.list(project_name="my-project")

        # Enable evaluators on the stream
        from splunk_ao import SplunkAOMetrics
        stream.set_metrics([SplunkAOMetrics.correctness, SplunkAOMetrics.completeness])
    """


# Convenience: expose the deprecated ``LogStream`` name with a warning
def __getattr__(name: str):
    if name == "LogStream":
        warnings.warn(
            "splunk_ao.agent_stream.LogStream is deprecated; "
            "import AgentStream from splunk_ao.agent_stream instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return LogStream
    raise AttributeError(f"module 'splunk_ao.agent_stream' has no attribute {name!r}")
