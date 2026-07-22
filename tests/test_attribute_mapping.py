import json
from uuid import uuid4

import pytest

from galileo_core.schemas.logging.span import (
    AgentSpan,
    AgentType,
    LlmMetrics,
    LlmSpan,
    RetrieverSpan,
    ToolSpan,
    WorkflowSpan,
)
from galileo_core.schemas.shared.document import Document
from splunk_ao.converter.attribute_mapping import (
    CONTENT_ALIAS_BY_GEN_AI,
    SPLUNK_ALIAS_BY_GEN_AI,
    build_span_attributes,
    normalize_attributes_for_export,
)
from splunk_ao.logger.control import ControlResult, ControlSpan


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
    assert json.loads(attrs["gen_ai.input.messages"])[0]["content"] == "prompt"
    assert json.loads(attrs["gen_ai.output.messages"])["content"] == "answer"
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
    assert attrs["gen_ai.tool.call.arguments"] == '{"q":"x"}'
    assert attrs["gen_ai.tool.call.result"] == "result"
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
    assert json.loads(attrs["gen_ai.retrieval.documents"])[0]["content"] == "doc"
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
    assert attrs["gen_ai.input.messages"] == "question"
    assert attrs["gen_ai.output.messages"] == "answer"


def test_control_mapping_preserves_structured_content() -> None:
    span = ControlSpan(
        name="guardrail",
        input={"text": "question"},
        output=ControlResult(action="observe", matched=True, confidence=0.9),
    )

    attrs = build_span_attributes(span)

    assert attrs["splunk_ao.operation.name"] == "control"
    assert json.loads(attrs["gen_ai.input.messages"]) == {"text": "question"}
    assert json.loads(attrs["gen_ai.output.messages"])["matched"] is True


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


def test_normalizer_converts_first_chunk_seconds_to_splunk_nanoseconds() -> None:
    result = normalize_attributes_for_export({"gen_ai.response.time_to_first_chunk": 0.125})

    assert result["gen_ai.response.time_to_first_chunk"] == 0.125
    assert result["splunk_ao.llm.time_to_first_token_ns"] == 125_000_000


def test_normalizer_is_idempotent() -> None:
    source = {"gen_ai.operation.name": "chat", "gen_ai.input.messages": "input-json", "custom.attribute": "unchanged"}

    once = normalize_attributes_for_export(source)

    assert normalize_attributes_for_export(once) == once


def test_normalizer_can_be_disabled_for_developer_comparison() -> None:
    source = {
        "gen_ai.request.model": "gpt-4o",
        "gen_ai.input.messages": "input-json",
        "splunk_ao.system": "source-value",
    }

    assert normalize_attributes_for_export(source, enabled=False) == source


def test_every_alias_uses_an_explicit_destination_namespace() -> None:
    assert SPLUNK_ALIAS_BY_GEN_AI
    assert all(source.startswith("gen_ai.") for source in SPLUNK_ALIAS_BY_GEN_AI)
    assert all(destination.startswith("splunk_ao.") for destination in SPLUNK_ALIAS_BY_GEN_AI.values())
