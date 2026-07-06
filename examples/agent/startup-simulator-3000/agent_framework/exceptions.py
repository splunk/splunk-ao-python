class AgentError(Exception):
    """Base class for agent framework exceptions"""


class ToolError(AgentError):
    """Base class for tool-related errors"""


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found"""


class ToolExecutionError(ToolError):
    """Raised when a tool execution fails"""

    def __init__(self, tool_name: str, original_error: Exception):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool {tool_name} execution failed: {original_error!s}")


class ConfigurationError(AgentError):
    """Raised when there's a configuration problem"""


class PlanningError(AgentError):
    """Raised when task planning fails"""


class StateError(AgentError):
    """Raised when there's a state-related error"""
