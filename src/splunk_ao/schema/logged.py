"""SDK-local ingestion models that widen input/output for multimodal content.

These models subclass the core Trace/Span types and override only the fields
that differ for ingestion (input, output, redacted_input, redacted_output).
Read-side code continues to use the core types directly.
"""

from collections.abc import Sequence
from json import dumps
from typing import Annotated, Any

from opentelemetry.trace import SpanKind
from pydantic import ConfigDict, Field, field_validator

from galileo_core.schemas.logging.llm import Message, MessageRole
from galileo_core.schemas.logging.span import (
    AgentSpan,
    LlmSpan,
    LlmSpanAllowedInputType,
    LlmSpanAllowedOutputType,
    RetrieverSpan,
    Span,  # noqa: F401  # needed for Pydantic model_rebuild to resolve forward refs
    ToolSpan,
    WorkflowSpan,
)
from galileo_core.schemas.logging.step import BaseStep
from galileo_core.schemas.logging.trace import Trace
from galileo_core.schemas.shared.document import Document
from splunk_ao.logger.control import ControlSpan
from splunk_ao.schema.content_blocks import IngestContentBlock, IngestMessageContent
from splunk_ao.schema.message import LoggedMessage

TextOrContentBlocks = IngestMessageContent
IngestInputType = str | Sequence[LoggedMessage] | list[IngestContentBlock]
IngestOutputType = str | LoggedMessage | Sequence[Document] | list[IngestContentBlock]

_INPUT_FIELD = Field(default="", description=BaseStep.model_fields["input"].description, union_mode="left_to_right")
_REDACTED_INPUT_FIELD = Field(
    default=None, description=BaseStep.model_fields["redacted_input"].description, union_mode="left_to_right"
)
_OUTPUT_FIELD = Field(default=None, description=BaseStep.model_fields["output"].description, union_mode="left_to_right")
_REDACTED_OUTPUT_FIELD = Field(
    default=None, description=BaseStep.model_fields["redacted_output"].description, union_mode="left_to_right"
)


class LoggedTrace(Trace):
    """Trace with widened input/output for multimodal ingestion."""

    input: TextOrContentBlocks = _INPUT_FIELD
    redacted_input: TextOrContentBlocks | None = _REDACTED_INPUT_FIELD
    output: TextOrContentBlocks | None = _OUTPUT_FIELD
    redacted_output: TextOrContentBlocks | None = _REDACTED_OUTPUT_FIELD
    spans: list["LoggedSpan"] = Field(default_factory=list)


class LoggedWorkflowSpan(WorkflowSpan):
    """WorkflowSpan with widened input/output for multimodal ingestion."""

    input: IngestInputType = _INPUT_FIELD
    redacted_input: IngestInputType | None = _REDACTED_INPUT_FIELD
    output: IngestOutputType | None = _OUTPUT_FIELD
    redacted_output: IngestOutputType | None = _REDACTED_OUTPUT_FIELD
    spans: list["LoggedSpan"] = Field(default_factory=list)
    conversation_root: bool | None = Field(default=None)


class LoggedAgentSpan(AgentSpan):
    """AgentSpan with widened input/output for multimodal ingestion."""

    input: IngestInputType = _INPUT_FIELD
    redacted_input: IngestInputType | None = _REDACTED_INPUT_FIELD
    output: IngestOutputType | None = _OUTPUT_FIELD
    redacted_output: IngestOutputType | None = _REDACTED_OUTPUT_FIELD
    spans: list["LoggedSpan"] = Field(default_factory=list)
    conversation_root: bool | None = Field(default=None)
    span_kind: SpanKind = Field(default=SpanKind.INTERNAL, exclude=True)

    @field_validator("span_kind", mode="before")
    @classmethod
    def normalize_span_kind(cls, value: object) -> SpanKind:
        """Allow only the explicit remote-agent client classification."""
        return SpanKind.CLIENT if value is SpanKind.CLIENT else SpanKind.INTERNAL


class LoggedRetrieverSpan(RetrieverSpan):
    """RetrieverSpan with SDK-local OTel data-source identity."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    data_source_id: str | None = Field(default=None, exclude=True)


class LoggedLlmSpan(LlmSpan):
    """LlmSpan for ingestion using LoggedMessage (supports IngestContentBlocks, not ContentParts)."""

    input: Sequence[LoggedMessage] = Field(
        default_factory=list, validate_default=True, description=BaseStep.model_fields["input"].description
    )
    redacted_input: Sequence[LoggedMessage] | None = Field(
        default=None, description=BaseStep.model_fields["redacted_input"].description
    )
    output: LoggedMessage = Field(
        default_factory=lambda: LoggedMessage(content="", role=MessageRole.assistant),
        validate_default=True,
        description=BaseStep.model_fields["output"].description,
    )
    redacted_output: LoggedMessage | None = Field(
        default=None, description=BaseStep.model_fields["redacted_output"].description
    )

    @classmethod
    def _to_logged_message(cls, msg: Message) -> LoggedMessage:
        if isinstance(msg, LoggedMessage):
            return msg
        return LoggedMessage(
            content=msg.content, role=msg.role, tool_call_id=msg.tool_call_id, tool_calls=msg.tool_calls
        )

    @classmethod
    def _convert_dict_to_message(
        cls, value: dict[str, Any], default_role: MessageRole = MessageRole.user
    ) -> LoggedMessage:
        try:
            return LoggedMessage.model_validate(value)
        except Exception:
            return LoggedMessage(content=dumps(value), role=default_role)

    @classmethod
    def _convert_input_to_messages(cls, value: LlmSpanAllowedInputType) -> Sequence[LoggedMessage]:
        messages = super()._convert_input_to_messages(value)
        return [cls._to_logged_message(m) for m in messages]

    @classmethod
    def _convert_output_to_message(cls, value: LlmSpanAllowedOutputType) -> LoggedMessage:
        message = super()._convert_output_to_message(value)
        return cls._to_logged_message(message)


class LoggedControlSpan(ControlSpan):
    """ControlSpan for ingestion using plain string input."""

    input: str = Field(default="", description=BaseStep.model_fields["input"].description)
    redacted_input: str | None = Field(default=None, description=BaseStep.model_fields["redacted_input"].description)


# ToolSpan uses plain string I/O and doesn't need multimodal widening.
# LoggedControlSpan narrows ControlSpan's Any input to str for the same reason.
LoggedSpan = Annotated[
    LoggedAgentSpan | LoggedWorkflowSpan | LoggedLlmSpan | LoggedRetrieverSpan | ToolSpan | LoggedControlSpan,
    Field(discriminator="type"),
]

LoggedTrace.model_rebuild()
LoggedWorkflowSpan.model_rebuild()
LoggedAgentSpan.model_rebuild()
LoggedRetrieverSpan.model_rebuild()
LoggedLlmSpan.model_rebuild()
LoggedControlSpan.model_rebuild()
