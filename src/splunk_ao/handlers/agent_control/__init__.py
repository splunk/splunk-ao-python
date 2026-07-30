"""Agent Control bridge for Splunk AO logger-backed control span ingestion.

For Agent Control target resolution, use ``splunk_ao.agent_control``.
"""

from splunk_ao.handlers.agent_control.bridge import SplunkAOAgentControlBridge, setup_agent_control_bridge

__all__ = ["SplunkAOAgentControlBridge", "setup_agent_control_bridge"]
