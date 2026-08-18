import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from galileo_core.schemas.logging.llm import Message, MessageRole, ToolCall, ToolCallFunction
from galileo_core.schemas.logging.span import (
    AgentSpan,
    AgentType,
    LlmMetrics,
    LlmSpan,
    RetrieverSpan,
    ToolSpan,
    WorkflowSpan,
)
from galileo_core.schemas.logging.step import BaseStep
from galileo_core.schemas.shared.content_parts import FileContentPart, TextContentPart
from galileo_core.schemas.shared.document import Document
from splunk_ao.converter.attribute_mapping import (
    CONTENT_ALIAS_BY_GEN_AI,
    SPLUNK_ALIAS_BY_GEN_AI,
    build_span_attributes,
    normalize_attributes_for_export,
)
from splunk_ao.logger.control import ControlAppliesTo, ControlCheckStage, ControlResult, ControlSpan
from splunk_ao.schema import DataContentBlock, LoggedControlSpan, LoggedLlmSpan, LoggedMessage, TextContentBlock


def _text_message(role: str, content: str, *, finish_reason: str | None = None) -> dict:
    message = {"role": role, "parts": [{"type": "text", "content": content}]}
    if finish_reason is not None:
        message["finish_reason"] = finish_reason
    return message


def test_llm_mapping_covers_content_request_response_usage_and_units() -> None:
    span = LlmSpan(
        input="prompt",
        output="answer",
        model="gpt-5-nano",
        temperature=0.0,
        finish_reason="stop",
        tools=[{"type": "function", "name": "search"}],
        metrics=LlmMetrics(
            num_input_tokens=12,
            num_output_tokens=8,
            num_total_tokens=20,
            time_to_first_token_ns=250_000_000,
            input_cost=0.01,
            output_cost=0.02,
            total_cost=0.03,
            cache_read_input_tokens=4,
        ),
    )

    attrs = build_span_attributes(span)

    assert attrs["gen_ai.operation.name"] == "chat"
    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", "prompt")]
    assert json.loads(attrs["gen_ai.output.messages"]) == [_text_message("assistant", "answer", finish_reason="stop")]
    assert attrs["gen_ai.request.model"] == "gpt-5-nano"
    assert attrs["gen_ai.request.temperature"] == 0.0
    assert attrs["gen_ai.response.finish_reasons"] == ("stop",)
    assert attrs["gen_ai.usage.input_tokens"] == 12
    assert attrs["gen_ai.usage.output_tokens"] == 8
    assert attrs["splunk_ao.llm.usage.total_tokens"] == 20
    assert attrs["gen_ai.response.time_to_first_chunk"] == 0.25
    assert attrs["splunk_ao.llm.time_to_first_token_ns"] == 250_000_000
    assert attrs["splunk_ao.llm.cost.total_usd"] == 0.03
    assert attrs["gen_ai.usage.cache_read.input_tokens"] == 4
    assert json.loads(attrs["gen_ai.tool.definitions"])[0]["name"] == "search"


def test_llm_output_uses_unknown_when_finish_reason_is_absent() -> None:
    attrs = build_span_attributes(LlmSpan(input="prompt", output="answer"))

    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", "answer", finish_reason="unknown")
    ]


def test_llm_messages_preserve_tool_calls_and_tool_responses() -> None:
    span = LlmSpan(
        input=[
            Message(
                role=MessageRole.assistant,
                content="",
                tool_calls=[
                    ToolCall(id="call-1", function=ToolCallFunction(name="weather", arguments='{"city":"Paris"}'))
                ],
            ),
            Message(role=MessageRole.tool, content='{"temperature":21}', tool_call_id="call-1"),
        ],
        output="It is 21 degrees.",
        finish_reason="stop",
    )

    messages = json.loads(build_span_attributes(span)["gen_ai.input.messages"])

    assert messages == [
        {
            "role": "assistant",
            "parts": [{"type": "tool_call", "id": "call-1", "name": "weather", "arguments": {"city": "Paris"}}],
        },
        {"role": "tool", "parts": [{"type": "tool_call_response", "id": "call-1", "response": {"temperature": 21}}]},
    ]


def test_llm_content_parts_follow_otel_multimodal_schema_and_preserve_extensions() -> None:
    # Given: stored file content and ingest-side blob/URI content with optional extension fields.
    file_id = uuid4()
    stored_file_span = LlmSpan(
        input=[Message(role=MessageRole.user, content=[FileContentPart(file_id=file_id)])], output="answer"
    )
    ingest_span = LoggedLlmSpan(
        input=[
            LoggedMessage(
                role=MessageRole.user,
                content=[
                    TextContentBlock(text="inspect this", index=2, metadata={"language": "en"}),
                    DataContentBlock(
                        modality="document",
                        mime_type="application/pdf",
                        base64="ZG9jdW1lbnQ=",
                        index=3,
                        metadata={"source": "upload"},
                    ),
                ],
            )
        ],
        output=LoggedMessage(
            role=MessageRole.assistant,
            content=[
                DataContentBlock(
                    modality="image",
                    mime_type="image/png",
                    url="https://example.com/photo.png",
                    index=4,
                    metadata={"source": "external"},
                )
            ],
        ),
    )

    # When: the proprietary content is converted to OTel GenAI message attributes.
    stored_parts = json.loads(build_span_attributes(stored_file_span)["gen_ai.input.messages"])[0]["parts"]
    ingest_attrs = build_span_attributes(ingest_span)
    ingest_parts = json.loads(ingest_attrs["gen_ai.input.messages"])[0]["parts"]
    output_parts = json.loads(ingest_attrs["gen_ai.output.messages"])[0]["parts"]

    # Then: file parts remain files, while Galileo data parts use the OTel blob/URI schemas.
    assert stored_parts == [{"type": "file", "file_id": str(file_id)}]
    assert ingest_parts == [
        {"type": "text", "content": "inspect this", "index": 2, "metadata": {"language": "en"}},
        {
            "type": "blob",
            "modality": "document",
            "mime_type": "application/pdf",
            "content": "ZG9jdW1lbnQ=",
            "index": 3,
            "metadata": {"source": "upload"},
        },
    ]
    assert output_parts == [
        {
            "type": "uri",
            "modality": "image",
            "mime_type": "image/png",
            "uri": "https://example.com/photo.png",
            "index": 4,
            "metadata": {"source": "external"},
        }
    ]
    assert "modality" not in stored_parts[0]
    assert "content" not in stored_parts[0]


def test_native_otel_content_parts_pass_through_unchanged() -> None:
    # Given: serialized messages that already use the OTel text, URI, blob, and file part schemas.
    native_parts = [
        {"type": "text", "content": "Inspect these attachments"},
        {"type": "uri", "modality": "image", "uri": "https://example.com/photo.png", "mime_type": "image/png"},
        {"type": "blob", "modality": "audio", "content": "YXVkaW8=", "mime_type": "audio/wav"},
        {"type": "file", "modality": "document", "file_id": "file-1", "mime_type": "application/pdf"},
    ]
    span = WorkflowSpan(
        name="multimodal-workflow",
        input=json.dumps({"messages": [{"role": "user", "content": native_parts}]}),
        output=json.dumps({"messages": [{"role": "assistant", "content": native_parts}]}),
    )

    # When: the messages pass through the shared proprietary-to-OTel conversion boundary.
    attrs = build_span_attributes(span)

    # Then: regular text and every already-valid OTel multimodal part remain unchanged.
    assert json.loads(attrs["gen_ai.input.messages"])[0]["parts"] == native_parts
    assert json.loads(attrs["gen_ai.output.messages"])[0]["parts"] == native_parts


def test_llm_tool_definitions_flatten_openai_functions_and_preserve_flat_definitions() -> None:
    span = LlmSpan(
        input="prompt",
        output="answer",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "weather",
                    "description": "Get the weather",
                    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                },
            },
            {"type": "function", "name": "search", "custom": "preserved"},
        ],
    )

    definitions = json.loads(build_span_attributes(span)["gen_ai.tool.definitions"])

    assert definitions == [
        {
            "type": "function",
            "name": "weather",
            "description": "Get the weather",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
        },
        {"type": "function", "name": "search", "custom": "preserved"},
    ]


def test_common_mapping_uses_canonical_keys_and_omits_external_id() -> None:
    session_id = uuid4()
    span = ToolSpan(
        name="search",
        input='{"q":"x"}',
        output="result",
        status_code=500,
        user_metadata={"team": "checkout"},
        tags=["production"],
        external_id="not-an-otel-attribute",
        dataset_input="question",
        dataset_output="expected",
        dataset_metadata={"split": "test"},
        session_id=session_id,
        step_number=0,
    )

    attrs = build_span_attributes(span)

    assert attrs["gen_ai.operation.name"] == "execute_tool"
    assert attrs["gen_ai.tool.name"] == "search"
    assert json.loads(attrs["gen_ai.tool.call.arguments"]) == {"q": "x"}
    assert json.loads(attrs["gen_ai.tool.call.result"]) == {"value": "result"}
    assert attrs["gen_ai.conversation.id"] == str(session_id)
    assert json.loads(attrs["splunk_ao.metadata"]) == {"team": "checkout"}
    assert attrs["splunk_ao.tags"] == ("production",)
    assert attrs["splunk_ao.status_code"] == 500
    assert attrs["error.type"] == "500"
    assert attrs["splunk_ao.step_number"] == 0
    assert attrs["splunk_ao.dataset.input"] == "question"
    assert attrs["splunk_ao.dataset.output"] == "expected"
    assert json.loads(attrs["splunk_ao.dataset.metadata"]) == {"split": "test"}
    assert not any("external_id" in key for key in attrs)


def test_explicit_session_context_precedes_span_session() -> None:
    span = ToolSpan(name="search", session_id=uuid4())

    assert build_span_attributes(span, session_id="context-session")["gen_ai.conversation.id"] == "context-session"


def test_retriever_mapping_uses_query_and_documents() -> None:
    span = RetrieverSpan(
        name="vector-search", input="what is RAG?", output=[Document(content="doc", metadata={"source": "kb"})]
    )

    attrs = build_span_attributes(span)

    assert attrs["gen_ai.operation.name"] == "retrieval"
    assert attrs["gen_ai.retrieval.query.text"] == "what is RAG?"
    assert json.loads(attrs["gen_ai.retrieval.documents"]) == [{"content": "doc", "metadata": {"source": "kb"}}]
    assert attrs["splunk_ao.retrieval.documents.count"] == 1
    assert attrs["db.operation"] == "search"
    assert "gen_ai.output.messages" not in attrs


@pytest.mark.parametrize(
    ("span", "operation_key", "operation", "name_key", "name"),
    [
        (
            WorkflowSpan(name="workflow", input="question", output="answer"),
            "gen_ai.operation.name",
            "invoke_workflow",
            "gen_ai.workflow.name",
            "workflow",
        ),
        (
            AgentSpan(name="planner", input="question", output="answer", agent_type=AgentType.planner),
            "gen_ai.operation.name",
            "invoke_agent",
            "gen_ai.agent.name",
            "planner",
        ),
    ],
)
def test_orchestration_mapping(span, operation_key: str, operation: str, name_key: str, name: str) -> None:
    attrs = build_span_attributes(span)

    assert attrs[operation_key] == operation
    assert attrs[name_key] == name
    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", "question")]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", "answer", finish_reason="unknown")
    ]


def test_orchestration_extracts_serialized_langgraph_messages_with_multimodal_parts() -> None:
    # Given: serialized framework messages containing standard, extension, file, and Galileo data parts.
    file_id = uuid4()
    span = WorkflowSpan(
        name="travel-planner",
        input=json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Plan this trip"},
                            {"type": "image", "url": "https://example.com/map.png"},
                            {"type": "file", "file_id": str(file_id)},
                        ],
                    }
                ],
                "destination": "Paris",
            }
        ),
        output=json.dumps(
            {
                "update": {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": "Here is the plan"},
                                {"type": "data", "modality": "audio", "base64": "YXVkaW8="},
                            ],
                        }
                    ]
                }
            }
        ),
    )

    # When: handler state is converted at the shared attribute boundary.
    attrs = build_span_attributes(span)

    # Then: recognized message containers and every available multimodal field are preserved.
    assert json.loads(attrs["gen_ai.input.messages"]) == [
        {
            "role": "user",
            "parts": [
                {"type": "text", "content": "Plan this trip"},
                {"type": "image", "url": "https://example.com/map.png"},
                {"type": "file", "file_id": str(file_id)},
            ],
        }
    ]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        {
            "role": "assistant",
            "parts": [
                {"type": "text", "content": "Here is the plan"},
                {"type": "blob", "modality": "audio", "content": "YXVkaW8="},
            ],
            "finish_reason": "unknown",
        }
    ]


def test_orchestration_accepts_native_content_part_sequences() -> None:
    file_id = uuid4()
    span = AgentSpan(
        name="multimodal-agent",
        agent_type=AgentType.planner,
        input=[TextContentPart(text="Inspect this"), FileContentPart(file_id=file_id)],
        output=[FileContentPart(file_id=file_id)],
    )

    attrs = build_span_attributes(span)

    assert json.loads(attrs["gen_ai.input.messages"]) == [
        {
            "role": "user",
            "parts": [{"type": "text", "content": "Inspect this"}, {"type": "file", "file_id": str(file_id)}],
        }
    ]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        {"role": "assistant", "parts": [{"type": "file", "file_id": str(file_id)}], "finish_reason": "unknown"}
    ]


def test_orchestration_output_omits_repeated_input_history() -> None:
    user_message = {"role": "user", "content": "Plan a trip"}
    assistant_message = {"role": "assistant", "content": "Where would you like to go?"}
    span = AgentSpan(
        name="planner",
        agent_type=AgentType.planner,
        input=json.dumps({"messages": [user_message]}),
        output=json.dumps({"messages": [user_message, assistant_message]}),
    )

    attrs = build_span_attributes(span)

    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", "Plan a trip")]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", "Where would you like to go?", finish_reason="unknown")
    ]


@pytest.mark.parametrize("span_type", [WorkflowSpan, AgentSpan])
def test_orchestration_full_history_preserves_all_terminal_assistant_messages(
    span_type: type[WorkflowSpan] | type[AgentSpan],
) -> None:
    # Given: a full-history result with two terminal assistant outputs after the exact input history.
    user = {"role": "user", "content": "Give me two alternatives"}
    first = {"role": "assistant", "content": "First alternative"}
    second = {"role": "assistant", "content": "Second alternative"}
    span_kwargs: dict[str, Any] = {
        "name": "planner",
        "input": json.dumps({"messages": [user]}),
        "output": json.dumps({"messages": [user, first, second]}),
    }
    if span_type is AgentSpan:
        span_kwargs["agent_type"] = AgentType.planner

    # When: the orchestration content is converted.
    attrs = build_span_attributes(span_type(**span_kwargs))

    # Then: the repeated input prefix is removed without reducing the terminal outputs to one message.
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", "First alternative", finish_reason="unknown"),
        _text_message("assistant", "Second alternative", finish_reason="unknown"),
    ]


@pytest.mark.parametrize("span_type", [WorkflowSpan, AgentSpan])
def test_orchestration_full_history_removes_confirmed_input_prefix(
    span_type: type[WorkflowSpan] | type[AgentSpan],
) -> None:
    # Given: the input is the complete history immediately before the final assistant response.
    user = {"role": "user", "content": "What is the dosage?"}
    tool_call = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "call-1", "function": {"name": "search", "arguments": '{"query":"dosage"}'}}],
    }
    tool_response = {"role": "tool", "content": "10 mg daily", "tool_call_id": "call-1"}
    final = {"role": "assistant", "content": "The common dosage is 10 mg daily."}
    input_history = [user, tool_call, tool_response]
    span_kwargs: dict[str, Any] = {
        "name": "healthcare",
        "input": json.dumps({"messages": input_history}),
        "output": json.dumps({"messages": [*input_history, final]}),
    }
    if span_type is AgentSpan:
        span_kwargs["agent_type"] = AgentType.default

    # When: the orchestration content is converted.
    attrs = build_span_attributes(span_type(**span_kwargs))

    # Then: only the newly produced terminal response is exported as output.
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", "The common dosage is 10 mg daily.", finish_reason="unknown")
    ]


def test_orchestration_infers_tool_call_finish_reason_when_absent() -> None:
    # Given: a workflow emits an assistant tool call without a source finish reason.
    output = {
        "update": {
            "messages": [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": "call-1", "function": {"name": "search", "arguments": '{"query":"dosage"}'}}],
                }
            ]
        }
    }

    # When: the workflow output is converted.
    attrs = build_span_attributes(WorkflowSpan(name="tools", output=json.dumps(output)))

    # Then: the standard tool-call finish reason is inferred from the output part.
    output_message = json.loads(attrs["gen_ai.output.messages"])[0]
    assert output_message["finish_reason"] == "tool_call"
    assert output_message["parts"][0]["type"] == "tool_call"


def test_orchestration_tool_response_uses_unknown_finish_reason() -> None:
    # Given: a workflow emits a tool response, which has no model-generation finish reason.
    output = {
        "update": {"messages": [{"role": "tool", "content": {"dosage": "10 mg daily"}, "tool_call_id": "call-1"}]}
    }

    # When: the workflow output is converted.
    attrs = build_span_attributes(WorkflowSpan(name="tools", output=json.dumps(output)))

    # Then: its valid tool response structure is preserved without inventing a model finish reason.
    output_message = json.loads(attrs["gen_ai.output.messages"])[0]
    assert output_message["finish_reason"] == "unknown"
    assert output_message["parts"] == [
        {"type": "tool_call_response", "id": "call-1", "response": {"dosage": "10 mg daily"}}
    ]


def test_orchestration_preserves_explicit_finish_reason_for_tool_call() -> None:
    # Given: the source supplies its own finish reason for a message containing a tool call.
    output = {
        "update": {
            "messages": [
                {
                    "role": "assistant",
                    "content": "",
                    "finish_reason": "provider_tool_calls",
                    "tool_calls": [{"id": "call-1", "function": {"name": "search", "arguments": '{"query":"dosage"}'}}],
                }
            ]
        }
    }

    # When: the workflow output is converted.
    attrs = build_span_attributes(WorkflowSpan(name="tools", output=json.dumps(output)))

    # Then: inference does not overwrite source telemetry.
    assert json.loads(attrs["gen_ai.output.messages"])[0]["finish_reason"] == "provider_tool_calls"


def test_orchestration_full_history_with_tool_call_keeps_last_message() -> None:
    # LangGraph accumulated state: user → tool-call AI (empty content) → tool response → final AI
    # The first post-dedup message has empty content; the UI would show "—" without the fix.
    user = {"role": "user", "content": "What is the dosage of Lisinopril?"}
    ai_toolcall = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "tc1", "function": {"name": "rag_search", "arguments": '{"query":"Lisinopril dosage"}'}}],
    }
    tool_resp = {"role": "tool", "content": "Lisinopril: 10mg daily", "tool_call_id": "tc1"}
    ai_final = {"role": "assistant", "content": "Common dosage is 10mg once daily."}

    span = AgentSpan(
        name="Agent",
        agent_type=AgentType.default,
        input=json.dumps({"messages": [user]}),
        output=json.dumps({"messages": [user, ai_toolcall, tool_resp, ai_final]}),
    )

    attrs = build_span_attributes(span)

    output_messages = json.loads(attrs["gen_ai.output.messages"])
    assert len(output_messages) == 1
    assert output_messages[0]["role"] == "assistant"
    assert output_messages[0]["parts"][0]["content"] == "Common dosage is 10mg once daily."


def test_orchestration_full_history_multi_turn_keeps_last_message() -> None:
    # Multi-turn: output contains the full conversation history after multiple exchanges.
    # Only the last message should be kept regardless of role.
    user1 = {"role": "user", "content": "Hello"}
    ai1 = {"role": "assistant", "content": "Hi, how can I help?"}
    user2 = {"role": "user", "content": "What is Lisinopril?"}
    ai2 = {"role": "assistant", "content": "Lisinopril is a blood pressure medication."}

    span = AgentSpan(
        name="Agent",
        agent_type=AgentType.default,
        input=json.dumps({"messages": [user1]}),
        output=json.dumps({"messages": [user1, ai1, user2, ai2]}),
    )

    attrs = build_span_attributes(span)

    output_messages = json.loads(attrs["gen_ai.output.messages"])
    assert len(output_messages) == 1
    assert output_messages[0]["parts"][0]["content"] == "Lisinopril is a blood pressure medication."


def test_orchestration_full_history_multiple_tool_rounds_keeps_last_message() -> None:
    # Two tool call rounds before the final answer — last message is still the only output.
    user = {"role": "user", "content": "Compare Lisinopril and Amlodipine"}
    tc1_ai = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "tc1", "function": {"name": "search", "arguments": '{"query":"Lisinopril"}'}}],
    }
    tc1_resp = {"role": "tool", "content": "Lisinopril: ACE inhibitor", "tool_call_id": "tc1"}
    tc2_ai = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "tc2", "function": {"name": "search", "arguments": '{"query":"Amlodipine"}'}}],
    }
    tc2_resp = {"role": "tool", "content": "Amlodipine: calcium channel blocker", "tool_call_id": "tc2"}
    ai_final = {
        "role": "assistant",
        "content": "Lisinopril is an ACE inhibitor; Amlodipine is a calcium channel blocker.",
    }

    span = AgentSpan(
        name="Agent",
        agent_type=AgentType.default,
        input=json.dumps({"messages": [user]}),
        output=json.dumps({"messages": [user, tc1_ai, tc1_resp, tc2_ai, tc2_resp, ai_final]}),
    )

    attrs = build_span_attributes(span)

    output_messages = json.loads(attrs["gen_ai.output.messages"])
    assert len(output_messages) == 1
    assert "Amlodipine" in output_messages[0]["parts"][0]["content"]


def test_orchestration_non_full_history_output_not_reduced() -> None:
    # Plain string output (full_history=False) — the last-message reduction must NOT fire.
    span = AgentSpan(
        name="Agent",
        agent_type=AgentType.default,
        input="What is Lisinopril?",
        output="Lisinopril is a blood pressure medication.",
    )

    attrs = build_span_attributes(span)

    output_messages = json.loads(attrs["gen_ai.output.messages"])
    assert len(output_messages) == 1
    assert output_messages[0]["parts"][0]["content"] == "Lisinopril is a blood pressure medication."


def test_orchestration_preserves_schema_valid_parts_and_tool_calls() -> None:
    span = WorkflowSpan(
        name="tool-workflow",
        input=json.dumps(
            {
                "messages": [
                    {
                        "role": "assistant",
                        "parts": [{"type": "text", "content": "Checking weather"}],
                        "tool_calls": [
                            {"id": "call-1", "function": {"name": "weather", "arguments": '{"city":"Paris"}'}}
                        ],
                    },
                    {"role": "tool", "content": '{"temperature":21}', "tool_call_id": "call-1"},
                ]
            }
        ),
    )

    messages = json.loads(build_span_attributes(span)["gen_ai.input.messages"])

    assert messages == [
        {
            "role": "assistant",
            "parts": [
                {"type": "text", "content": "Checking weather"},
                {"type": "tool_call", "id": "call-1", "name": "weather", "arguments": {"city": "Paris"}},
            ],
        },
        {"role": "tool", "parts": [{"type": "tool_call_response", "id": "call-1", "response": {"temperature": 21}}]},
    ]


@pytest.mark.parametrize(
    "span",
    [
        WorkflowSpan(
            name="state-machine",
            input=json.dumps({"current_agent": "coordinator", "travellers": 2}),
            output=json.dumps({"next_agent": "flight_specialist"}),
        ),
        AgentSpan(
            name="state-agent",
            agent_type=AgentType.planner,
            input=json.dumps({"current_agent": "coordinator", "travellers": 2}),
            output=json.dumps({"next_agent": "flight_specialist"}),
        ),
    ],
)
def test_orchestration_preserves_arbitrary_state_as_messages(span: WorkflowSpan | AgentSpan) -> None:
    attrs = build_span_attributes(span)

    assert json.loads(attrs["gen_ai.input.messages"]) == [
        _text_message("user", '{"current_agent":"coordinator","travellers":2}')
    ]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", '{"next_agent":"flight_specialist"}', finish_reason="unknown")
    ]


@pytest.mark.parametrize(
    ("serialized", "expected_content"), [("false", "false"), ("0", "0"), ("{}", "{}"), ("[]", "[]")]
)
def test_orchestration_preserves_false_zero_and_empty_values(serialized: str, expected_content: str) -> None:
    attrs = build_span_attributes(WorkflowSpan(name="workflow", input=serialized, output=serialized))

    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", expected_content)]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", expected_content, finish_reason="unknown")
    ]


def test_orchestration_preserves_explicit_empty_message_history() -> None:
    attrs = build_span_attributes(WorkflowSpan(name="workflow", input='{"messages":[]}', output='{"messages":[]}'))

    assert json.loads(attrs["gen_ai.input.messages"]) == []
    assert json.loads(attrs["gen_ai.output.messages"]) == []


def test_orchestration_preserves_empty_full_history_suffix() -> None:
    history = '{"messages":[{"role":"user","content":"question"}]}'
    attrs = build_span_attributes(AgentSpan(name="agent", input=history, output=history))

    assert json.loads(attrs["gen_ai.output.messages"]) == []


def test_orchestration_falls_back_for_malformed_message_container() -> None:
    value = '{"messages":[{"content":"missing role"}],"state":"kept"}'
    attrs = build_span_attributes(WorkflowSpan(name="workflow", input=value, output=value))

    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", value)]
    assert json.loads(attrs["gen_ai.output.messages"]) == [_text_message("assistant", value, finish_reason="unknown")]


def test_orchestration_preserves_typed_extension_part_without_inventing_fields() -> None:
    parts = [
        {"type": "audio", "url": "https://example.com/answer.wav", "format": "wav"},
        {"type": "file", "file_id": "file-1"},
    ]
    serialized_parts = json.dumps(parts)
    attrs = build_span_attributes(AgentSpan(name="agent", input=serialized_parts, output=serialized_parts))

    assert json.loads(attrs["gen_ai.input.messages"]) == [{"role": "user", "parts": parts}]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        {"role": "assistant", "parts": parts, "finish_reason": "unknown"}
    ]


def test_orchestration_falls_back_when_part_type_is_empty() -> None:
    value = [{"type": "", "content": "not a valid typed part"}]
    attrs = build_span_attributes(WorkflowSpan(name="workflow", input=json.dumps(value)))

    assert json.loads(attrs["gen_ai.input.messages"]) == [
        _text_message("user", json.dumps(value, separators=(",", ":"), sort_keys=True))
    ]


def test_orchestration_keeps_non_json_strings_as_text_messages() -> None:
    span = WorkflowSpan(name="workflow", input="{not-json", output="plain response")

    attrs = build_span_attributes(span)

    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", "{not-json")]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        _text_message("assistant", "plain response", finish_reason="unknown")
    ]


def test_control_mapping_exports_fully_populated_backend_contract() -> None:
    span = LoggedControlSpan(
        name="PII Guard",
        input="question",
        output=ControlResult(action="deny", matched=True, confidence=0.97),
        control_id=42,
        agent_name="planner",
        check_stage=ControlCheckStage.pre,
        applies_to=ControlAppliesTo.llm_call,
        evaluator_name="pii-check",
        selector_path="$.input",
        tags=["agent_control", "control"],
        user_metadata={"source": "agent-control-sdk"},
    )

    attrs = build_span_attributes(span)
    output = json.loads(attrs["gen_ai.output.messages"])

    control_attrs = {key: value for key, value in attrs.items() if key.startswith(("agent_control.", "galileo."))}
    assert control_attrs == {
        "galileo.span.kind": "control",
        "agent_control.control_id": 42,
        "agent_control.control_name": "PII Guard",
        "agent_control.agent_name": "planner",
        "agent_control.check_stage": "pre",
        "agent_control.applies_to": "llm_call",
        "agent_control.evaluator_name": "pii-check",
        "agent_control.selector_path": "$.input",
        "agent_control.action": "deny",
        "agent_control.matched": True,
        "agent_control.confidence": 0.97,
    }
    assert attrs["gen_ai.operation.name"] == "control"
    assert "splunk_ao.operation.name" not in attrs
    assert attrs["splunk_ao.tags"] == ("agent_control", "control")
    assert json.loads(attrs["splunk_ao.metadata"]) == {"source": "agent-control-sdk"}
    assert json.loads(attrs["gen_ai.input.messages"]) == [_text_message("user", "question")]
    assert output[0]["role"] == "assistant"
    assert output[0]["finish_reason"] == "unknown"
    assert json.loads(output[0]["parts"][0]["content"])["matched"] is True


def test_control_mapping_omits_unpopulated_optional_fields() -> None:
    attrs = build_span_attributes(ControlSpan(input="question"))

    assert attrs["galileo.span.kind"] == "control"
    for key in (
        "agent_control.control_id",
        "agent_control.control_name",
        "agent_control.agent_name",
        "agent_control.check_stage",
        "agent_control.applies_to",
        "agent_control.evaluator_name",
        "agent_control.selector_path",
        "agent_control.action",
        "agent_control.matched",
        "agent_control.confidence",
        "agent_control.error_message",
    ):
        assert key not in attrs


def test_control_mapping_accepts_schema_compatible_control_span() -> None:
    source = ControlSpan(name="guardrail", output=ControlResult(action="observe", matched=True), control_id=42)
    alternate = SimpleNamespace(
        **{field_name: getattr(source, field_name) for field_name in type(source).model_fields}, model_extra={}
    )

    attrs = build_span_attributes(cast(BaseStep, alternate))

    assert not isinstance(alternate, ControlSpan)
    assert attrs["galileo.span.kind"] == "control"
    assert attrs["agent_control.control_id"] == 42
    assert attrs["agent_control.action"] == "observe"


def test_control_mapping_tolerates_span_without_control_fields() -> None:
    minimal = SimpleNamespace(
        type="control",
        name="guardrail",
        input="question",
        output=None,
        redacted_input=None,
        redacted_output=None,
        user_metadata={},
        tags=[],
        status_code=None,
        dataset_input=None,
        dataset_output=None,
        dataset_metadata={},
        model_extra={},
    )

    attrs = build_span_attributes(cast(BaseStep, minimal))

    assert attrs["galileo.span.kind"] == "control"
    assert attrs["agent_control.control_name"] == "guardrail"
    assert "agent_control.control_id" not in attrs


def test_control_mapping_exports_error_result_without_dropping_false() -> None:
    span = ControlSpan(
        name="guardrail", output=ControlResult(action="observe", matched=False, error_message="evaluator unavailable")
    )

    attrs = build_span_attributes(span)

    assert attrs["agent_control.action"] == "observe"
    assert attrs["agent_control.matched"] is False
    assert attrs["agent_control.error_message"] == "evaluator unavailable"
    assert "agent_control.confidence" not in attrs


def test_control_operation_name_uses_standard_export_normalization() -> None:
    attrs = build_span_attributes(ControlSpan())

    assert attrs["gen_ai.operation.name"] == "control"
    assert "splunk_ao.operation.name" not in attrs

    normalized = normalize_attributes_for_export(attrs)

    assert normalized["gen_ai.operation.name"] == "control"
    assert normalized["splunk_ao.operation.name"] == "control"


def test_normalizer_duplicates_ordinary_attributes_and_relocates_all_content() -> None:
    source = {
        "gen_ai.request.model": "gpt-4o",
        "gen_ai.usage.input_tokens": 42,
        **{key: f"value-{index}" for index, key in enumerate(CONTENT_ALIAS_BY_GEN_AI)},
    }

    result = normalize_attributes_for_export(source)

    assert result["gen_ai.request.model"] == result["splunk_ao.request.model"] == "gpt-4o"
    assert result["gen_ai.usage.input_tokens"] == result["splunk_ao.llm.usage.input_tokens"] == 42
    for source_key, destination_key in CONTENT_ALIAS_BY_GEN_AI.items():
        assert source_key not in result
        assert result[destination_key] == source[source_key]


def test_normalizer_gen_ai_wins_collisions_and_sdk_marker_is_authoritative() -> None:
    result = normalize_attributes_for_export(
        {
            "gen_ai.request.model": "canonical",
            "splunk_ao.request.model": "stale",
            "gen_ai.system": "legacy-provider",
            "gen_ai.provider.name": "current-provider",
            "splunk_ao.provider.name": "stale-provider",
            "splunk_ao.system": "other-sdk",
        }
    )

    assert result["splunk_ao.request.model"] == "canonical"
    assert result["splunk_ao.provider.name"] == "current-provider"
    assert result["splunk_ao.system"] == "splunk_ao_python"


def test_normalizer_does_not_use_deprecated_gen_ai_system_as_provider() -> None:
    result = normalize_attributes_for_export({"gen_ai.system": "legacy-provider"})

    assert result["gen_ai.system"] == "legacy-provider"
    assert "splunk_ao.provider.name" not in result


def test_normalizer_converts_first_chunk_seconds_to_splunk_nanoseconds() -> None:
    result = normalize_attributes_for_export({"gen_ai.response.time_to_first_chunk": 0.125})

    assert result["gen_ai.response.time_to_first_chunk"] == 0.125
    assert result["splunk_ao.llm.time_to_first_token_ns"] == 125_000_000


def test_normalizer_preserves_exact_source_nanoseconds() -> None:
    result = normalize_attributes_for_export(
        {"gen_ai.response.time_to_first_chunk": 0.123456789, "splunk_ao.llm.time_to_first_token_ns": 123_456_789}
    )

    assert result["splunk_ao.llm.time_to_first_token_ns"] == 123_456_789


def test_normalizer_is_idempotent() -> None:
    source = {
        "gen_ai.operation.name": "chat",
        "gen_ai.input.messages": json.dumps([_text_message("user", "question")]),
        "custom.attribute": "unchanged",
    }

    once = normalize_attributes_for_export(source)

    assert normalize_attributes_for_export(once) == once


def test_normalizer_can_be_disabled_for_developer_comparison() -> None:
    source = {
        "gen_ai.request.model": "gpt-4o",
        "gen_ai.input.messages": json.dumps([_text_message("user", "question")]),
        "splunk_ao.system": "source-value",
    }

    assert normalize_attributes_for_export(source, enabled=False) == {**source, "splunk_ao.system": "splunk_ao_python"}


def test_every_alias_uses_an_explicit_destination_namespace() -> None:
    assert SPLUNK_ALIAS_BY_GEN_AI
    assert all(source.startswith("gen_ai.") for source in SPLUNK_ALIAS_BY_GEN_AI)
    assert all(destination.startswith("splunk_ao.") for destination in SPLUNK_ALIAS_BY_GEN_AI.values())
