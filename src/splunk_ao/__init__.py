"""Splunk AO."""

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
from splunk_ao.agent_control import AgentControlTarget, AgentControlTargetUnresolvedError, get_agent_control_target
from splunk_ao.annotation_queues import (
    AnnotationField,
    AnnotationQueue,
    AnnotationQueueRecordSelector,
    AnnotationQueues,
    AnnotationQueueUser,
    add_records_to_annotation_queue,
    create_annotation_queue,
    create_annotation_queue_field,
    delete_annotation_queue,
    delete_annotation_queue_field,
    get_annotation_queue,
    get_annotation_queue_records,
    list_annotation_queue_fields,
    list_annotation_queue_users,
    list_annotation_queues,
    remove_annotation_queue_user,
    remove_records_from_annotation_queue,
    share_annotation_queue,
    update_annotation_queue,
    update_annotation_queue_field,
    update_annotation_queue_user,
)
from splunk_ao.collaborator import Collaborator, CollaboratorRole
from splunk_ao.configuration import Configuration
from splunk_ao.dataset import Dataset
from splunk_ao.decorator import SplunkAODecorator, log, splunk_ao_context, start_session
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
from splunk_ao.provider import AnthropicProvider, AzureProvider, BedrockProvider, OpenAIProvider, Provider
from splunk_ao.resources.models.document import Document
from splunk_ao.schema.message import Message
from splunk_ao.schema.metrics import SplunkAOMetrics
from splunk_ao.shared.base import SyncState
from splunk_ao.shared.exceptions import (
    AmbiguousConfigurationError,
    APIError,
    ConfigurationError,
    MissingConfigurationError,
    ResourceConflictError,
    ResourceNotFoundError,
    SplunkAOConfigError,
    SplunkAOFutureError,
    ValidationError,
)
from splunk_ao.tracing import get_tracing_headers
from splunk_ao.types import MetricSpec
from splunk_ao.utils.log_config import enable_console_logging

__version__ = "0.1.0"

__all__ = [
    "APIError",
    "AgentControlTarget",
    "AgentControlTargetUnresolvedError",
    "AgentSpan",
    "AmbiguousConfigurationError",
    "AnnotationField",
    "AnnotationQueue",
    "AnnotationQueueRecordSelector",
    "AnnotationQueueUser",
    "AnnotationQueues",
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
    "MissingConfigurationError",
    "Model",
    "NotFoundError",
    "OpenAIProvider",
    "Project",
    "Prompt",
    "Provider",
    "RateLimitError",
    "ResourceConflictError",
    "ResourceNotFoundError",
    "RetrieverSpan",
    "ServerError",
    "Session",
    "Span",
    "SplunkAOAPIError",
    "SplunkAOAgentControlBridge",
    "SplunkAOConfigError",
    "SplunkAODecorator",
    "SplunkAOFutureError",
    "SplunkAOLogger",
    "SplunkAOLoggerException",
    "SplunkAOMetric",
    "SplunkAOMetrics",
    "StepType",
    "StepWithChildSpans",
    "SyncState",
    "ToolCall",
    "ToolCallFunction",
    "ToolSpan",
    "Trace",
    "ValidationError",
    "WorkflowSpan",
    "add_records_to_annotation_queue",
    "create_annotation_queue",
    "create_annotation_queue_field",
    "create_api_key",
    "delete_annotation_queue",
    "delete_annotation_queue_field",
    "delete_api_key",
    "enable_console_logging",
    "get_agent_control_target",
    "get_annotation_queue",
    "get_annotation_queue_records",
    "get_tracing_headers",
    "is_dependency_available",
    "list_annotation_queue_fields",
    "list_annotation_queue_users",
    "list_annotation_queues",
    "list_api_keys",
    "log",
    "remove_annotation_queue_user",
    "remove_records_from_annotation_queue",
    "setup_agent_control_bridge",
    "share_annotation_queue",
    "splunk_ao_context",
    "start_session",
    "update_annotation_queue",
    "update_annotation_queue_field",
    "update_annotation_queue_user",
]
