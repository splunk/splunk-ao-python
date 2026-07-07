from abc import ABC, abstractmethod

from .models import LLMConfig, LLMMessage, LLMResponse


class LLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def generate(self, messages: list[LLMMessage], config: LLMConfig | None = None) -> LLMResponse:
        """Generate a response from the LLM"""

    @abstractmethod
    async def generate_stream(self, messages: list[LLMMessage], config: LLMConfig | None = None):
        """Generate a streaming response from the LLM"""
