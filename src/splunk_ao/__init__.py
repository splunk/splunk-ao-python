"""Splunk AO."""

# ruff: noqa: E402

import sys

vars(sys)["_splunk_ao_suppress_galileo_deprecation_warning"] = True

from galileo.resources.models.document import Document
from galileo_core.helpers.api_key import create_api_key, delete_api_key, list_api_keys
from galileo_core.helpers.dependencies import is_dependency_available
from galileo_core.schemas.logging.llm import MessageRole, ToolCall, ToolCallFunction
from galileo_core.schemas.logging.session import Session
from galileo_core.schemas.logging.span import (
    AgentSpan,
    LlmSpan,
    RetrieverSpan,
    Span,
    StepWithChildSpans,
    ToolSpan,
    WorkflowSpan,
)
from galileo_core.schemas.logging.step import StepType
from galileo_core.schemas.logging.trace import Trace
from galileo_core.schemas.protect.execution_status import ExecutionStatus
from galileo_core.schemas.protect.payload import Payload
from galileo_core.schemas.protect.request import Request
from galileo_core.schemas.protect.response import Response
from galileo_core.schemas.protect.ruleset import Ruleset
from galileo_core.schemas.protect.stage import StageType
from splunk_ao.agent_control import AgentControlTarget, AgentControlTargetUnresolvedError, get_agent_control_target
from splunk_ao.collaborator import Collaborator, CollaboratorRole
from splunk_ao.configuration import Configuration
from splunk_ao.dataset import Dataset
from splunk_ao.decorator import SplunkAODecorator, splunk_ao_context, log, start_session
from splunk_ao.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SplunkAOAPIError,
    SplunkAOLoggerException,
)
from splunk_ao.experiment import Experiment
from splunk_ao.handlers.agent_control import SplunkAOAgentControlBridge, setup_agent_control_bridge
from splunk_ao.integration import Integration
from splunk_ao.log_stream import LogStream
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.logger.control import ControlAppliesTo, ControlCheckStage, ControlResult, ControlSpan
from splunk_ao.metric import CodeMetric, LlmMetric, LocalMetric, Metric, SplunkAOMetric
from splunk_ao.model import Model
from splunk_ao.project import Project
from splunk_ao.prompt import Prompt
from splunk_ao.protect import ainvoke_protect, invoke_protect
from splunk_ao.provider import AnthropicProvider, AzureProvider, BedrockProvider, OpenAIProvider, Provider
from splunk_ao.schema.message import Message
from splunk_ao.schema.metrics import SplunkAOMetrics
from splunk_ao.shared.base import SyncState
from splunk_ao.shared.exceptions import (
    APIError,
    ConfigurationError,
    ResourceConflictError,
    ResourceNotFoundError,
    SplunkAOFutureError,
    ValidationError,
)
from splunk_ao.stages import (
    create_protect_stage,
    get_protect_stage,
    pause_protect_stage,
    resume_protect_stage,
    update_protect_stage,
)
from splunk_ao.tracing import get_tracing_headers
from splunk_ao.types import MetricSpec
from splunk_ao.utils.log_config import enable_console_logging

vars(sys)["_splunk_ao_suppress_galileo_deprecation_warning"] = False

__version__ = "0.1.0"

__all__ = [
    "APIError",
    "AgentControlTarget",
    "AgentControlTargetUnresolvedError",
    "AgentSpan",
    "AnthropicProvider",
    "AuthenticationError",
    "AzureProvider",
    "BadRequestError",
    "BedrockProvider",
    "CodeMetric",
    "Collaborator",
    "CollaboratorRole",
    "Configuration",
    "ConfigurationError",
    "ConflictError",
    "ControlAppliesTo",
    "ControlCheckStage",
    "ControlResult",
    "ControlSpan",
    "Dataset",
    "Document",
    "ExecutionStatus",
    "Experiment",
    "ForbiddenError",
    "Integration",
    "LlmMetric",
    "LlmSpan",
    "LocalMetric",
    "LogStream",
    "Message",
    "MessageRole",
    "Metric",
    "MetricSpec",
    "Model",
    "NotFoundError",
    "OpenAIProvider",
    "Payload",
    "Project",
    "Prompt",
    "Provider",
    "RateLimitError",
    "Request",
    "ResourceConflictError",
    "ResourceNotFoundError",
    "Response",
    "RetrieverSpan",
    "Ruleset",
    "ServerError",
    "Session",
    "Span",
    "SplunkAOAPIError",
    "SplunkAOAgentControlBridge",
    "SplunkAODecorator",
    "SplunkAOFutureError",
    "SplunkAOLogger",
    "SplunkAOLoggerException",
    "SplunkAOMetric",
    "SplunkAOMetrics",
    "StageType",
    "StepType",
    "StepWithChildSpans",
    "SyncState",
    "ToolCall",
    "ToolCallFunction",
    "ToolSpan",
    "Trace",
    "ValidationError",
    "WorkflowSpan",
    "ainvoke_protect",
    "create_api_key",
    "create_protect_stage",
    "delete_api_key",
    "enable_console_logging",
    "splunk_ao_context",
    "get_agent_control_target",
    "get_protect_stage",
    "get_tracing_headers",
    "invoke_protect",
    "is_dependency_available",
    "list_api_keys",
    "log",
    "pause_protect_stage",
    "resume_protect_stage",
    "setup_agent_control_bridge",
    "start_session",
    "update_protect_stage",
]
