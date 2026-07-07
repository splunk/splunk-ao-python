from abc import ABC, abstractmethod
from typing import Any, ClassVar

from ..models import ToolMetadata


class BaseTool(ABC):
    """Base class for all tools"""

    # Tool metadata as class variables
    metadata: ClassVar[type[ToolMetadata]]

    def __init__(self):
        """Initialize the base tool"""

    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        """Get tool metadata for planning"""
        # Create an instance of the metadata class
        return cls.metadata()  # This will use the default values defined in the metadata class

    @abstractmethod
    async def execute(self, **inputs: Any) -> dict[str, Any]:
        """Execute the tool with given inputs"""
        raise NotImplementedError("Tool must implement execute method")
