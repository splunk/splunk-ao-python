from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .utils.hooks import ToolHooks, ToolSelectionHooks


class ToolMetadata(BaseModel):
    """Base schema for tool metadata"""

    name: str = Field(description="Unique identifier for the tool")
    description: str = Field(description="Human-readable description of what the tool does")
    tags: list[str] = Field(description="Categories/capabilities of the tool")
    input_schema: dict[str, Any] = Field(description="JSON schema for tool inputs")
    output_schema: dict[str, Any] = Field(description="JSON schema for tool outputs")
    examples: list[dict[str, Any]] | None = Field(default=None, description="Example uses of the tool")


class ToolError(BaseModel):
    """Schema for tool errors"""

    error: str = Field(description="Error message from the tool")


class AgentMetadata(BaseModel):
    """Base schema for agent metadata"""

    name: str = Field(description="Name of the agent")
    description: str = Field(description="What the agent does")
    capabilities: list[str] = Field(description="High-level capabilities")
    tools: list[ToolMetadata] = Field(description="Tools available to this agent")
    version: str = Field(default="1.0.0", description="Version of the agent")
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict, description="Additional custom metadata for the agent"
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)


class VerbosityLevel(StrEnum):
    """Controls how much information is displayed to the user"""

    NONE = "none"  # Only show final results
    LOW = "low"  # Show major steps and results
    HIGH = "high"  # Show detailed execution steps, tool selection, and reasoning


class TaskAnalysis(BaseModel):
    """Analysis of a task using chain of thought reasoning"""

    input_analysis: str = Field(description="Analysis of the input, identifying key requirements and constraints")
    available_tools: list[str] = Field(description="List of tools available for the task")
    tool_capabilities: dict[str, list[str]] = Field(description="Mapping of tools to their key capabilities")
    execution_plan: list[dict[str, Any]] = Field(
        description="Ordered list of steps to execute, each with tool and reasoning"
    )
    requirements_coverage: dict[str, list[str]] = Field(
        description="How the identified requirements are covered by the planned steps"
    )
    chain_of_thought: list[str] = Field(description="Chain of thought reasoning that led to this plan")


@dataclass
class ToolContext:
    """Context object passed to tool hooks"""

    def __init__(
        self,
        task: str,
        tool_name: str,
        inputs: dict[str, Any],
        available_tools: list[dict[str, Any]],
        previous_tools: list[str],
        previous_results: list[Any],
        previous_errors: list[Any],
        message_history: list[dict[str, Any]],
        agent_id: str,
        task_id: str,
        start_time: datetime,
        metadata: dict[str, Any],
        plan: TaskAnalysis | None = None,
    ):
        self.task = task
        self.tool_name = tool_name
        self.inputs = inputs
        self.available_tools = available_tools
        self.previous_tools = previous_tools
        self.previous_results = previous_results
        self.previous_errors = previous_errors
        self.message_history = message_history
        self.agent_id = agent_id
        self.task_id = task_id
        self.start_time = start_time
        self.metadata = metadata
        self.plan = plan  # The agent's planning analysis


@dataclass
class Tool:
    """Model representing a tool that can be used by an agent"""

    name: str = field(metadata={"description": "Unique identifier for the tool"})
    description: str = field(metadata={"description": "Human-readable description of what the tool does"})
    tags: list[str] = field(metadata={"description": "Categories or labels for the tool's capabilities"})
    input_schema: dict[str, Any] = field(metadata={"description": "JSON Schema defining expected input parameters"})
    output_schema: dict[str, Any] = field(metadata={"description": "JSON Schema defining the tool's output structure"})
    hooks: ToolHooks | None = field(
        default=None, metadata={"description": "Optional hooks for tool execution lifecycle"}
    )


class ToolSelectionCriteria(BaseModel):
    """Criteria used for selecting a tool"""

    required_tags: list[str] = Field(default_factory=list, description="Tags that a tool must have to be considered")
    preferred_tags: list[str] = Field(
        default_factory=list, description="Tags that are desired but not required in a tool"
    )
    context_requirements: dict[str, Any] = Field(
        default_factory=dict, description="Specific contextual requirements that influence tool selection"
    )
    custom_rules: dict[str, Any] = Field(
        default_factory=dict, description="Additional rules or criteria for tool selection"
    )


class ToolSelectionReasoning(BaseModel):
    """Record of the reasoning process for tool selection"""

    context: dict[str, Any] = Field(description="Current context and state when the tool selection was made")
    considered_tools: list[str] = Field(description="Names of all tools that were evaluated for selection")
    selection_criteria: ToolSelectionCriteria = Field(description="Criteria used to evaluate and select the tool")
    reasoning_steps: list[str] = Field(description="Detailed steps of the decision-making process")
    selected_tool: str = Field(description="Name of the tool that was ultimately chosen")
    confidence_score: float = Field(description="Confidence level in the tool selection (0.0 to 1.0)", ge=0.0, le=1.0)


class ToolCall(BaseModel):
    """Record of a tool invocation"""

    tool_name: str = Field(description="Name of the tool that was called")
    inputs: dict[str, Any] = Field(description="Parameters passed to the tool during execution")
    outputs: dict[str, Any] | None = Field(default=None, description="Results returned by the tool execution")
    selection_reasoning: ToolSelectionReasoning | None = Field(
        default=None, description="Reasoning process that led to selecting this tool"
    )
    execution_reasoning: str = Field(description="Explanation of why this tool was executed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp when the tool was called")
    success: bool = Field(default=True, description="Whether the tool execution completed successfully")
    error: str | None = Field(default=None, description="Error message if the tool execution failed")


class ExecutionStep(BaseModel):
    """Record of a single step in the agent's execution"""

    step_type: str = Field(
        description="Category or type of execution step (e.g., 'task_received', 'processing', 'completion')"
    )
    description: str = Field(description="Human-readable description of what happened in this step")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp when the step occurred")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tools that were called during this step")
    intermediate_state: dict[str, Any] | None = Field(
        default=None, description="State or context information captured during this step"
    )


class TaskExecution(BaseModel):
    """Complete record of a task execution"""

    task_id: str = Field(description="Unique identifier for this task execution")
    agent_id: str = Field(description="Identifier of the agent executing the task")
    input: str = Field(description="Original input or request given to the agent")
    steps: list[ExecutionStep] = Field(
        default_factory=list, description="Sequence of steps taken during task execution"
    )
    output: str | None = Field(default=None, description="Final result or response from the task execution")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp when task execution began")
    end_time: datetime | None = Field(default=None, description="UTC timestamp when task execution completed")
    status: str = Field(
        default="in_progress", description="Current status of the task (e.g., 'in_progress', 'completed', 'failed')"
    )
    error: str | None = Field(default=None, description="Error message if the task execution failed")


@dataclass
class AgentConfig:
    """Configuration for an agent"""

    verbosity: VerbosityLevel = field(
        default=VerbosityLevel.LOW, metadata={"description": "Level of detail to display to the user"}
    )
    # logger: Optional[AgentLogger] = field(
    #     default=None,
    #     metadata={"description": "Optional logger for recording agent activity"}
    # )
    tool_selection_hooks: ToolSelectionHooks | None = field(
        default=None, metadata={"description": "Hooks for tool selection lifecycle"}
    )
    metadata: dict[str, Any] = field(
        default_factory=dict, metadata={"description": "Additional configuration metadata"}
    )
