from .agent import Agent
from .config import AgentConfiguration
from .llm.base import LLMProvider
from .llm.openai_provider import OpenAIProvider
from .utils.logging import ConsoleAgentLogger


class AgentFactory:
    """Factory for creating agents with proper dependency injection"""

    def __init__(self, config: AgentConfiguration):
        self.config = config
        self._llm_provider: LLMProvider | None = None
        self._logger: ConsoleAgentLogger | None = None

    def get_llm_provider(self) -> LLMProvider:
        """Get or create LLM provider"""
        if not self._llm_provider:
            if "openai" in self.config.api_keys:
                self._llm_provider = OpenAIProvider(config=self.config.llm_config)
            else:
                raise ValueError("No LLM provider configured")
        return self._llm_provider

    def get_logger(self, agent_id: str) -> ConsoleAgentLogger | None:
        """Get logger if enabled"""
        if self.config.enable_logging:
            return ConsoleAgentLogger(agent_id)
        return None

    def create_agent(self, agent_class: type[Agent], agent_id: str | None = None, **kwargs) -> Agent:
        """Create an agent instance with proper dependencies"""
        # Create core dependencies
        llm_provider = self.get_llm_provider()
        logger = self.get_logger(agent_id) if agent_id else None

        # Create agent with injected dependencies
        return agent_class(
            agent_id=agent_id,
            llm_provider=llm_provider,
            logger=logger,
            verbosity=self.config.verbosity,
            metadata=self.config.metadata,
            **kwargs,
        )
