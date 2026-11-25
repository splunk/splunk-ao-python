from typing import Literal

DEFAULT_PROJECT_NAME = "default"
DEFAULT_AGENT_STREAM_NAME = "default"
DEFAULT_MODE = "batch"

DEFAULT_API_URL = "https://api.galileo.ai/"
DEFAULT_CONSOLE_URL = "https://app.galileo.ai/"

# Type definitions
LoggerModeType = Literal["batch", "distributed"]

__all__ = (
    "DEFAULT_AGENT_STREAM_NAME",
    "DEFAULT_API_URL",
    "DEFAULT_CONSOLE_URL",
    "DEFAULT_MODE",
    "DEFAULT_PROJECT_NAME",
    "LoggerModeType",
)
