"""Tests for OpenAI Agents utility functions."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from agents import (
    AgentSpanData,
    CustomSpanData,
    FunctionSpanData,
    GenerationSpanData,
    GuardrailSpanData,
    HandoffSpanData,
    Span,
)
from agents.tracing import ResponseSpanData

from galileo_core.schemas.logging.span import ToolSpan, WorkflowSpan
from splunk_ao.utils.openai_agents import (
    SplunkAOCustomSpan,
    _extract_llm_data,
    _extract_tool_data,
    _extract_user_input,
    _extract_workflow_data,
    _map_span_name,
    _map_span_type,
    _normalize_responses_input,
    _normalize_responses_output,
    _parse_usage,
)


class TestParseUsage:
    """Test _parse_usage function."""

    @pytest.mark.parametrize(
        "usage_data,expected",
        [
            (
                {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                {
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                    "input_tokens_details": None,
                    "output_tokens_details": None,
                },
            ),
            (
                {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
                {
                    "input_tokens": 15,
                    "output_tokens": 25,
                    "total_tokens": 40,
                    "input_tokens_details": None,
                    "output_tokens_details": None,
                },
            ),
            (
                {
                    "input_tokens": 10,
                    "prompt_tokens": 999,
                    "output_tokens": 20,
                    "completion_tokens": 888,
                    "total_tokens": 30,
                },
                {
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                    "input_tokens_details": None,
                    "output_tokens_details": None,
                },
            ),
            (
                {"input_tokens": 10, "output_tokens": 20},
                {
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                    "input_tokens_details": None,
                    "output_tokens_details": None,
                },
            ),
            (
                None,
                {
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "input_tokens_details": None,
                    "output_tokens_details": None,
                },
            ),
            (
                {"input_tokens": 10},
                {
                    "input_tokens": 10,
                    "output_tokens": None,
                    "total_tokens": None,
                    "input_tokens_details": None,
                    "output_tokens_details": None,
                },
            ),
        ],
    )
    def test_parse_usage_variations(self, usage_data: dict[str, Any] | None, expected: dict[str, int | None]) -> None:
        """Test various usage data formats."""
        result = _parse_usage(usage_data)
        assert result == expected

    def test_parse_usage_with_model_dump(self) -> None:
        """Test parsing from object with model_dump."""
        mock_usage = Mock()
        mock_usage.model_dump.return_value = {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15}
        result = _parse_usage(mock_usage)
        assert result == {
            "input_tokens": 5,
            "output_tokens": 10,
            "total_tokens": 15,
            "input_tokens_details": None,
            "output_tokens_details": None,
        }

    def test_parse_usage_with_invalid_values(self) -> None:
        """Test parsing with invalid token values."""
        result = _parse_usage({"input_tokens": "invalid", "output_tokens": 20})
        assert result["output_tokens"] == 20
        assert result["input_tokens"] is None


class TestExtractLlmData:
    """Test _extract_llm_data function."""

    def test_generation_span(self) -> None:
        """Test extracting from GenerationSpanData."""
        span_data = Mock(spec=GenerationSpanData)
        span_data.input = "What is AI?"
        span_data.output = "Artificial Intelligence"
        span_data.model = "gpt-4"
        span_data.usage = {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15}
        span_data.model_config = {"temperature": 0.7}

        result = _extract_llm_data(span_data)

        assert result["model"] == "gpt-4"
        assert result["temperature"] == 0.7
        assert result["num_input_tokens"] == 5
        assert result["num_output_tokens"] == 10
        assert result["status_code"] == 200

    def test_response_span_with_tools(self) -> None:
        """Test extracting from ResponseSpanData with tools."""
        mock_response = Mock()
        mock_response.output = "Response"
        mock_response.model = "gpt-4"
        mock_response.temperature = 0.7
        mock_response.usage = None
        mock_response.tools = [
            Mock(model_dump=Mock(return_value={"name": "search"})),
            Mock(model_dump=Mock(return_value={"name": "calc"})),
        ]
        mock_response.error = None
        mock_response.model_dump.return_value = {"model": "gpt-4", "temperature": 0.7}

        result = _extract_llm_data(ResponseSpanData(input="Query", response=mock_response))

        assert len(result["tools"]) == 2

    def test_response_span_with_error(self) -> None:
        """Test extracting from ResponseSpanData with error."""
        mock_response = Mock()
        mock_response.output = None
        mock_response.model = "gpt-4"
        mock_response.temperature = None
        mock_response.usage = None
        mock_response.tools = None
        mock_response.error = Mock(status_code=503)
        mock_response.model_dump.return_value = {"model": "gpt-4"}

        result = _extract_llm_data(ResponseSpanData(input="Query", response=mock_response))

        assert result["status_code"] == 503
        assert "error_details" in result["metadata"]

    def test_input_preserved_as_list(self) -> None:
        # Given: GenerationSpanData with a list input
        # When: LLM data is extracted
        # Then: input is a list (not serialized) so LoggedLlmSpan validators can convert it
        span_data = GenerationSpanData(
            input=[{"role": "system", "content": "You are helpful."}, {"role": "user", "content": "Hello"}],
            output=[{"role": "assistant", "content": "Hi"}],
            model="gpt-4",
        )
        result = _extract_llm_data(span_data)
        assert isinstance(result["input"], list)

    def test_output_unwrapped_from_list(self) -> None:
        # Given: GenerationSpanData with a single-element output list
        # When: LLM data is extracted
        # Then: output is the first element (dict), not the list
        span_data = GenerationSpanData(
            input=[{"role": "user", "content": "Hi"}], output=[{"role": "assistant", "content": "Hello"}], model="gpt-4"
        )
        result = _extract_llm_data(span_data)
        assert isinstance(result["output"], dict)
        assert result["output"]["role"] == "assistant"

    def test_empty_output_list_gives_none(self) -> None:
        # Given: GenerationSpanData with empty output list
        # When: LLM data is extracted
        # Then: output is None
        span_data = GenerationSpanData(input=[{"role": "user", "content": "Hi"}], output=[], model="gpt-4")
        result = _extract_llm_data(span_data)
        assert result["output"] is None


class TestExtractToolData:
    """Test _extract_tool_data function."""

    def test_function_span(self) -> None:
        """Test extracting from FunctionSpanData."""
        result = _extract_tool_data(FunctionSpanData(name="search", input="input data", output=[{"result": "output"}]))
        assert "input" in result and "output" in result
        assert result["status_code"] == 200

    @pytest.mark.parametrize("triggered,has_warning", [(True, True), (False, False)])
    def test_guardrail_span(self, triggered: bool, has_warning: bool) -> None:
        """Test extracting from GuardrailSpanData."""
        result = _extract_tool_data(GuardrailSpanData(name="guardrail", triggered=triggered))
        assert result["metadata"]["triggered"] is triggered
        assert ("status" in result["metadata"]) == has_warning


class TestExtractWorkflowData:
    """Test _extract_workflow_data function."""

    def test_agent_span(self) -> None:
        """Test extracting from AgentSpanData."""
        result = _extract_workflow_data(
            AgentSpanData(name="Agent", tools=["tool1"], handoffs=["agent1"], output_type="text")
        )
        assert result["metadata"]["tools"] == ["tool1"]
        assert result["metadata"]["handoffs"] == ["agent1"]

    def test_handoff_span(self) -> None:
        """Test extracting from HandoffSpanData."""
        result = _extract_workflow_data(HandoffSpanData(from_agent="agent1", to_agent="agent2"))
        assert result["metadata"]["from_agent"] == "agent1"
        assert result["metadata"]["to_agent"] == "agent2"

    def test_custom_span_filters_none(self) -> None:
        """Test CustomSpanData filters None values from metadata."""
        result = _extract_workflow_data(
            CustomSpanData(name="Test", data={"input": "in", "output": "out", "field1": "val", "field2": None})
        )
        assert "field1" in result["metadata"]
        assert "field2" not in result["metadata"]


class TestMapSpanName:
    """Test _map_span_name function."""

    def test_uses_name_attribute(self) -> None:
        """Test mapping span name from name attribute."""
        mock_span = Mock(spec=Span)
        mock_span_data = Mock()
        mock_span_data.name = "Custom Name"
        mock_span.span_data = mock_span_data
        assert _map_span_name(mock_span) == "Custom Name"

    @pytest.mark.parametrize(
        "span_data,expected_name",
        [
            (GenerationSpanData(input=[{"text": "test"}], output=[{"text": "response"}], model="gpt-4"), "Generation"),
            (ResponseSpanData(input="test", response=Mock(output="response")), "Response"),
            (HandoffSpanData(from_agent="Agent1", to_agent="Agent2"), "Handoff: Agent1 -> Agent2"),
        ],
    )
    def test_span_type_names(self, span_data: Any, expected_name: str) -> None:
        """Test mapping names for different span types."""
        mock_span = Mock(spec=Span)
        mock_span.span_data = span_data
        assert _map_span_name(mock_span) == expected_name

    def test_falls_back_to_type(self) -> None:
        """Test fallback to type attribute."""
        mock_span = Mock(spec=Span)
        mock_span_data = Mock()
        mock_span_data.name = None
        mock_span_data.type = "custom_type"
        mock_span.span_data = mock_span_data
        assert _map_span_name(mock_span) == "Custom_type"

    def test_unknown_span(self) -> None:
        """Test handling of unknown span types."""
        mock_span = Mock(spec=Span)
        mock_span.span_data = Mock(spec=[])
        assert _map_span_name(mock_span) == "Unknown Span"


class TestMapSpanType:
    """Test _map_span_type function."""

    @pytest.mark.parametrize(
        "span_data,expected_type",
        [
            # LLM spans
            (GenerationSpanData(input=[{"text": "test"}], output=[{"text": "response"}], model="gpt-4"), "llm"),
            (ResponseSpanData(input="test", response=Mock()), "llm"),
            # Tool spans
            (FunctionSpanData(name="function", input="input", output=[{"result": "output"}]), "tool"),
            (GuardrailSpanData(name="guardrail", triggered=False), "tool"),
            # Workflow spans
            (AgentSpanData(name="Agent", tools=[], handoffs=[]), "workflow"),
            (HandoffSpanData(from_agent="A", to_agent="B"), "workflow"),
            (CustomSpanData(name="Custom", data={}), "workflow"),
        ],
    )
    def test_span_data_types(self, span_data: Any, expected_type: str) -> None:
        """Test mapping various span data types."""
        assert _map_span_type(span_data) == expected_type

    def test_splunk_ao_custom_span(self) -> None:
        """Test mapping SplunkAOCustomSpan."""
        splunk_ao_span = WorkflowSpan(name="Test", input="input", output="output", status_code=200)
        assert _map_span_type(SplunkAOCustomSpan(splunk_ao_span, {})) == "splunk_ao_custom"

    @pytest.mark.parametrize(
        "type_attr,expected_type", [("function", "tool"), ("generation", "llm"), ("agent", "workflow")]
    )
    def test_type_attribute_mapping(self, type_attr: str, expected_type: str) -> None:
        """Test mapping based on type attribute."""
        assert _map_span_type(Mock(type=type_attr)) == expected_type

    def test_unknown_defaults_to_workflow(self) -> None:
        """Test unknown span types default to workflow."""
        assert _map_span_type(Mock(spec=[])) == "workflow"


class TestSplunkAOCustomSpan:
    """Test SplunkAOCustomSpan utility."""

    @pytest.mark.parametrize(
        "span",
        [
            ToolSpan(name="Tool", input="i", output="o", status_code=200),
            WorkflowSpan(name="Workflow", input="start", output="end", status_code=200),
        ],
    )
    def test_wraps_span_types(self, span: Any) -> None:
        """Test that SplunkAOCustomSpan wraps different span types."""
        assert SplunkAOCustomSpan(span, {}).type == "splunk_ao_custom"

    def test_preserves_underlying_properties(self) -> None:
        """Test accessing underlying span properties."""
        workflow_span = WorkflowSpan(
            name="Test", input="Q", output="A", user_metadata={"v": "1.0"}, tags=["test"], status_code=200
        )
        custom_span = SplunkAOCustomSpan(workflow_span, workflow_span.user_metadata or {})

        assert custom_span.span.name == "Test"
        assert custom_span.span.input == "Q"
        assert custom_span.span.output == "A"
        assert custom_span.span.tags == ["test"]
        assert custom_span.data == {"v": "1.0"}

    def test_handles_none_user_metadata(self) -> None:
        """Test that None user_metadata is handled correctly."""
        workflow_span = WorkflowSpan(
            name="Test",
            input="Q",
            output="A",
            user_metadata=None,  # pyright: ignore[reportArgumentType]
            tags=["test"],
            status_code=200,
        )
        # WorkflowSpan converts None to {} automatically, but we test the 'or {}' pattern
        custom_span = SplunkAOCustomSpan(workflow_span, workflow_span.user_metadata or {})

        assert custom_span.span.name == "Test"
        # WorkflowSpan normalizes None to {} internally
        assert custom_span.span.user_metadata == {}
        assert custom_span.data == {}

        # Verify that unpacking with 'or {}' pattern works (which is what our fix uses)
        metadata = custom_span.span.user_metadata or {}
        result = {**metadata, "status_code": custom_span.span.status_code}
        assert result == {"status_code": 200}


class TestExtractUserInput:
    """Test _extract_user_input function."""

    def test_returns_last_user_message(self) -> None:
        # Given: multi-turn input with system and user messages
        # When: user input is extracted
        # Then: the last user message content is returned
        llm_input = [{"role": "system", "content": "You are helpful."}, {"role": "user", "content": "What is AI?"}]
        assert _extract_user_input(llm_input) == "What is AI?"

    def test_returns_last_user_message_in_multi_turn(self) -> None:
        # Given: multi-turn conversation with multiple user messages
        # When: user input is extracted
        # Then: the last user message is returned, not the first
        llm_input = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow-up question"},
        ]
        assert _extract_user_input(llm_input) == "Follow-up question"

    def test_returns_none_for_non_list(self) -> None:
        # Given: non-list input
        # When: user input is extracted
        # Then: None is returned
        assert _extract_user_input("plain string") is None
        assert _extract_user_input(None) is None

    def test_returns_none_when_no_user_message(self) -> None:
        # Given: input with no user role messages
        # When: user input is extracted
        # Then: None is returned
        assert _extract_user_input([{"role": "system", "content": "System only"}]) is None

    def test_joins_text_blocks_and_skips_image_only_message(self) -> None:
        # Given: a user message with text and image blocks, followed by an image-only user message
        # When: user input is extracted
        # Then: the latest user message with text is used, and only its text is returned
        llm_input = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Describe"}, {"type": "data", "modality": "image", "url": "u"}],
            },
            {"role": "user", "content": [{"type": "data", "modality": "image", "url": "u2"}]},
        ]
        assert _extract_user_input(llm_input) == "Describe"


class TestNormalizeResponsesInput:
    """Test _normalize_responses_input function."""

    def test_string_input_is_one_user_message(self) -> None:
        # Given: a plain string Responses input
        # When: it is normalized
        # Then: it becomes one user message
        assert _normalize_responses_input("Hi") == [{"role": "user", "content": "Hi"}]

    def test_tool_turn_items_keep_roles_and_order(self) -> None:
        # Given: a second-turn Responses input with developer, reasoning, parallel calls, results and replies
        # When: it is normalized
        # Then: items map to system/user/assistant/tool messages in order, and reasoning is skipped
        items = [
            {"role": "developer", "content": "Be brief."},
            {"role": "user", "content": "Look up CUST-1"},
            {"type": "reasoning", "id": "rs_1", "summary": []},
            {"type": "function_call", "call_id": "c1", "name": "get_customer", "arguments": "{}"},
            {"type": "function_call", "call_id": "c2", "name": "get_tickets", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "c1", "output": '{"name": "Acme"}'},
            {"type": "function_call_output", "call_id": "c2", "output": "[]"},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Acme."}]},
        ]
        result = _normalize_responses_input(items)
        assert [m["role"] for m in result] == ["system", "user", "assistant", "tool", "tool", "assistant"]
        assert [c["id"] for c in result[2]["tool_calls"]] == ["c1", "c2"]
        assert result[3] == {"role": "tool", "tool_call_id": "c1", "content": '{"name": "Acme"}'}
        assert result[5]["content"] == [{"type": "text", "text": "Acme."}]

    def test_multimodal_parts_become_content_blocks(self) -> None:
        # Given: a Responses user message with text, a base64 image, and an image known only by file_id
        # When: it is normalized
        # Then: text stays text, the base64 image becomes a data block, and the file_id stays text without payload
        items = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "What is this?"},
                    {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
                    {"type": "input_image", "file_id": "file-123"},
                ],
            }
        ]
        blocks = _normalize_responses_input(items)[0]["content"]
        assert blocks[0] == {"type": "text", "text": "What is this?"}
        assert blocks[1] == {"type": "data", "modality": "image", "base64": "AAAA", "mime_type": "image/png"}
        assert blocks[2]["type"] == "text" and "file-123" in blocks[2]["text"]


class TestNormalizeResponsesOutput:
    """Test _normalize_responses_output function."""

    def test_message_and_tool_call_combine_into_one_assistant_message(self) -> None:
        # Given: Responses output with reasoning, a text message, and a function call
        # When: it is normalized
        # Then: one assistant message holds the text and the tool call
        items = [
            {"type": "reasoning", "id": "rs_1", "summary": []},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Checking."}]},
            {"type": "function_call", "call_id": "c1", "name": "lookup", "arguments": '{"id": 1}'},
        ]
        assert _normalize_responses_output(items) == {
            "role": "assistant",
            "content": "Checking.",
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": '{"id": 1}'}}],
        }

    def test_reasoning_only_output_gives_none(self) -> None:
        # Given: Responses output with only a reasoning item
        # When: it is normalized
        # Then: there is no message to record
        assert _normalize_responses_output([{"type": "reasoning", "id": "rs_1", "summary": []}]) is None


class TestGenerationMultimodalInput:
    """Test multi-part Chat Completions content in _extract_llm_data."""

    def test_image_part_becomes_content_block(self) -> None:
        # Given: GenerationSpanData whose user message has text and an image_url part
        # When: LLM data is extracted
        # Then: the content is converted to text and data blocks instead of being kept as raw parts
        span_data = GenerationSpanData(
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this?"},
                        {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                    ],
                }
            ],
            output=[{"role": "assistant", "content": "A cat."}],
            model="gpt-4",
        )
        content = _extract_llm_data(span_data)["input"][0]["content"]
        assert content == [
            {"type": "text", "text": "What is this?"},
            {"type": "data", "modality": "image", "url": "https://example.com/a.png"},
        ]

    def test_tuple_input_parts_become_content_blocks(self) -> None:
        # Given: GenerationSpanData input as a tuple, which its Sequence type allows a custom model to pass
        # When: LLM data is extracted
        # Then: the multi-part content is still converted to content blocks
        span_data = GenerationSpanData(
            input=(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this?"},
                        {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                    ],
                },
            ),
            output=[{"role": "assistant", "content": "A cat."}],
            model="gpt-4",
        )
        assert _extract_llm_data(span_data)["input"][0]["content"] == [
            {"type": "text", "text": "What is this?"},
            {"type": "data", "modality": "image", "url": "https://example.com/a.png"},
        ]


class TestGenerationStreamedOutput:
    """Test GenerationSpanData output from a streamed Chat Completions run."""

    # Streamed runs record [Response.model_dump()] instead of [ChatCompletionMessage.model_dump()].
    @staticmethod
    def _streamed_output(*items: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"id": "__fake_id__", "object": "response", "model": "gpt-4", "output": list(items), "usage": None}]

    def test_streamed_tool_call_response_becomes_assistant_tool_calls(self) -> None:
        # Given: streamed GenerationSpanData whose output is a response object holding two function calls
        # When: LLM data is extracted
        # Then: output is one assistant message with both tool calls, not a JSON dump of the response
        span_data = GenerationSpanData(
            input=[{"role": "user", "content": "Look up CUST-1"}],
            output=self._streamed_output(
                {"type": "function_call", "call_id": "c1", "name": "get_customer", "arguments": '{"id": "CUST-1"}'},
                {"type": "function_call", "call_id": "c2", "name": "get_tickets", "arguments": '{"id": "CUST-1"}'},
            ),
            model="gpt-4",
        )
        assert _extract_llm_data(span_data)["output"] == {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "get_customer", "arguments": '{"id": "CUST-1"}'}},
                {"id": "c2", "type": "function", "function": {"name": "get_tickets", "arguments": '{"id": "CUST-1"}'}},
            ],
        }

    def test_streamed_text_response_becomes_assistant_text(self) -> None:
        # Given: streamed GenerationSpanData whose output is a response object holding one output_text message
        # When: LLM data is extracted
        # Then: output is an assistant message with the answer text
        span_data = GenerationSpanData(
            input=[{"role": "user", "content": "Hi"}],
            output=self._streamed_output(
                {
                    "type": "message",
                    "id": "__fake_id__",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "Hello!", "annotations": []}],
                }
            ),
            model="gpt-4",
        )
        assert _extract_llm_data(span_data)["output"] == {"role": "assistant", "content": "Hello!"}
