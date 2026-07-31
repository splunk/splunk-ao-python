import json
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest

from galileo_core.schemas.shared.document import Document
from galileo_core.schemas.shared.multimodal import ContentModality
from splunk_ao import Message, MessageRole, log, splunk_ao_context
from splunk_ao.constants.tracing import PARENT_ID_HEADER, TRACE_ID_HEADER
from splunk_ao.decorator import _parent_id_context, _trace_id_context
from splunk_ao.schema.content_blocks import DataContentBlock, TextContentBlock
from splunk_ao.tracing import get_tracing_headers
from tests.testutils.setup import setup_mock_logstreams_client, setup_mock_projects_client, setup_mock_traces_client


@pytest.fixture
def reset_context() -> Generator[None, None, None]:
    splunk_ao_context.reset()
    yield
    splunk_ao_context.reset()


@pytest.fixture
def set_distributed_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPLUNK_AO_MODE", "distributed")


@pytest.fixture
def distributed_clients(set_distributed_mode: None) -> Generator[Mock, None, None]:
    with (
        patch("splunk_ao.logger.logger.Traces") as traces_client,
        patch("splunk_ao.logger.logger.Projects") as projects_client,
        patch("splunk_ao.logger.logger.AgentStreams") as logstreams_client,
    ):
        client = setup_mock_traces_client(traces_client)
        setup_mock_projects_client(projects_client)
        setup_mock_logstreams_client(logstreams_client)
        yield client


def init_logger():
    splunk_ao_context.init(project="test-project", agent_stream="test-stream")
    return splunk_ao_context.get_logger_instance()


def test_decorator_get_tracing_headers(reset_context: None, distributed_clients: Mock) -> None:
    logger = init_logger()

    @log(span_type="workflow")
    def orchestrator(query: str) -> dict:
        trace = splunk_ao_context.get_current_trace()
        return {"result": query, "headers": get_tracing_headers(), "trace_id": str(trace.id)}

    result = orchestrator("test input")

    headers = result["headers"]
    assert headers[TRACE_ID_HEADER] == result["trace_id"]
    assert PARENT_ID_HEADER in headers
    assert logger.current_parent() is None


def test_decorator_respects_incoming_distributed_context(reset_context: None, distributed_clients: Mock) -> None:
    trace_id = "12345678-1234-4678-9abc-123456789abc"
    parent_id = "87654321-4321-4876-9cba-987654321cba"
    _trace_id_context.set(trace_id)
    _parent_id_context.set(parent_id)
    logger = init_logger()

    @log(span_type="workflow")
    def downstream_service(query: str) -> str:
        return f"processed: {query}"

    assert downstream_service("test input") == "processed: test input"
    assert logger.mode == "distributed"
    assert str(logger.traces[0].id) == trace_id
    assert logger.traces[0].name == "stub_trace"
    assert (logger._sink.spans[-1].attributes or {})["gen_ai.operation.name"] == "invoke_workflow"


def test_completed_workflow_is_enqueued_and_flush_does_not_change_ownership(
    reset_context: None, distributed_clients: Mock
) -> None:
    logger = init_logger()

    @log(span_type="workflow")
    def workflow(input_value: str) -> str:
        return f"output: {input_value}"

    assert workflow("test input") == "output: test input"

    emitted = logger._sink.spans
    assert len(emitted) == 1
    attrs = emitted[0].attributes or {}
    assert attrs["gen_ai.operation.name"] == "invoke_workflow"
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        {"finish_reason": "unknown", "parts": [{"content": "output: test input", "type": "text"}], "role": "assistant"}
    ]
    assert emitted[0].end_time >= emitted[0].start_time
    assert logger.current_parent() is None

    logger.flush()

    assert logger._sink.spans == emitted
    assert logger.current_parent() is None
    distributed_clients.ingest_traces.assert_not_called()
    distributed_clients.ingest_spans.assert_not_called()
    distributed_clients.update_trace.assert_not_called()
    distributed_clients.update_span.assert_not_called()


def test_decorator_workflow_arguments_and_result_reach_otel_span(
    reset_context: None, distributed_clients: Mock
) -> None:
    logger = init_logger()

    @log(span_type="workflow")
    def add(arg1: int, arg2: int) -> dict[str, int]:
        return {"sum": arg1 + arg2}

    assert add(1, 2) == {"sum": 3}

    [span] = logger._sink.spans
    attrs = span.attributes or {}
    assert json.loads(attrs["gen_ai.input.messages"]) == [
        {"role": "user", "parts": [{"type": "text", "content": '{"arg1":1,"arg2":2}'}]}
    ]
    assert json.loads(attrs["gen_ai.output.messages"]) == [
        {"role": "assistant", "parts": [{"type": "text", "content": '{"sum":3}'}], "finish_reason": "unknown"}
    ]


def test_workflow_empty_output_is_preserved(reset_context: None, distributed_clients: Mock) -> None:
    logger = init_logger()

    @log(span_type="workflow")
    def workflow() -> str:
        return ""

    assert workflow() == ""
    assert json.loads((logger._sink.spans[-1].attributes or {})["gen_ai.output.messages"]) == [
        {"finish_reason": "unknown", "parts": [{"content": "", "type": "text"}], "role": "assistant"}
    ]
    assert logger.current_parent() is None


def test_top_level_workflows_have_independent_durations_and_traces(
    reset_context: None, distributed_clients: Mock
) -> None:
    logger = init_logger()

    @log(span_type="workflow")
    def first() -> str:
        return "first"

    @log(span_type="workflow")
    def second() -> str:
        return "second"

    first()
    second()
    first_span, second_span = logger._sink.spans

    assert first_span.end_time >= first_span.start_time
    assert second_span.end_time >= second_span.start_time
    assert first_span.context.trace_id != second_span.context.trace_id
    assert logger.current_parent() is None
    distributed_clients.update_trace.assert_not_called()


def test_content_blocks_are_preserved_on_completed_operation(reset_context: None, distributed_clients: Mock) -> None:
    logger = init_logger()
    blocks = [
        TextContentBlock(text="Here is the result"),
        DataContentBlock(modality=ContentModality.image, url="https://example.com/img.png"),
    ]

    @log(span_type="workflow")
    def workflow() -> list:
        return blocks

    workflow()

    output_messages = (logger._sink.spans[-1].attributes or {})["gen_ai.output.messages"]
    assert "Here is the result" in output_messages
    assert "https://example.com/img.png" in output_messages
    assert logger.current_parent() is None


@pytest.mark.parametrize(
    ("output", "expected_values", "expect_messages"),
    [
        (
            [Message(content="Hello", role=MessageRole.user), Message(content="Hi!", role=MessageRole.assistant)],
            ("Hello", "Hi!"),
            True,
        ),
        (
            [Document(content="Tokyo is the capital of Japan."), Document(content="Mount Fuji is 3776m tall.")],
            ("Tokyo", "Mount Fuji"),
            False,
        ),
    ],
)
def test_only_message_outputs_use_otel_message_schema(
    reset_context: None,
    distributed_clients: Mock,
    output: list,
    expected_values: tuple[str, str],
    expect_messages: bool,
) -> None:
    logger = init_logger()

    @log(span_type="workflow")
    def workflow() -> list:
        return output

    workflow()
    trace_output = (logger._sink.spans[-1].attributes or {}).get("gen_ai.output.messages")

    if expect_messages:
        assert isinstance(trace_output, str)
        assert all(value in trace_output for value in expected_values)
    else:
        assert trace_output is None
    assert logger.current_parent() is None
