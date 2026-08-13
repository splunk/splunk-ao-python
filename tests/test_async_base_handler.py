import asyncio
import uuid
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan

from splunk_ao import get_tracing_headers
from splunk_ao.handlers.base_async_handler import SplunkAOAsyncBaseHandler
from splunk_ao.logger.logger import SplunkAOLogger
from splunk_ao.session_context import set_session_context
from tests.testutils.setup import setup_mock_logstreams_client, setup_mock_projects_client, setup_mock_traces_client


class RecordingSink:
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []
        self.force_flush_calls = 0

    def emit(self, span: ReadableSpan) -> None:
        self.spans.append(span)

    def force_flush(self) -> bool:
        self.force_flush_calls += 1
        return True

    def shutdown(self) -> None:
        return None


@pytest.mark.asyncio
async def test_async_child_enqueues_when_its_callback_ends() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOAsyncBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    try:
        await handler.async_start_node(
            node_type="chain", parent_run_id=None, run_id=root_id, name="root", input="request"
        )
        await handler.async_start_node(
            node_type="llm", parent_run_id=root_id, run_id=child_id, name="child", input="prompt", model="model"
        )

        await handler.async_end_node(child_id, output="answer", model="model")

        assert [(span.attributes or {}).get("gen_ai.operation.name") for span in sink.spans] == ["chat"]
        assert str(root_id) in handler._active_steps
        assert sink.force_flush_calls == 0

        await handler.async_end_node(root_id, output="done")

        assert [(span.attributes or {}).get("gen_ai.operation.name") for span in sink.spans] == [
            "chat",
            "invoke_workflow",
        ]
        assert sink.spans[0].parent == sink.spans[1].context
        assert sink.force_flush_calls == 0
    finally:
        logger.terminate()


@pytest.mark.asyncio
async def test_concurrent_async_handlers_keep_parent_and_session_context_isolated() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    first_started = asyncio.Event()
    second_started = asyncio.Event()

    async def run_handler(label: str, own_started: asyncio.Event, other_started: asyncio.Event) -> None:
        set_session_context(label)
        handler = SplunkAOAsyncBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
        root_id = uuid.uuid4()
        child_id = uuid.uuid4()
        try:
            await handler.async_start_node(
                node_type="chain", parent_run_id=None, run_id=root_id, name=f"{label}-root", input="request"
            )
            own_started.set()
            await other_started.wait()
            await handler.async_start_node(
                node_type="llm",
                parent_run_id=root_id,
                run_id=child_id,
                name=f"{label}-child",
                input="prompt",
                model="model",
            )
            await asyncio.sleep(0)
            await handler.async_end_node(child_id, output="answer", model="model")
            await handler.async_end_node(root_id, output="done")
        finally:
            set_session_context(None)

    try:
        await asyncio.gather(
            run_handler("conversation-a", first_started, second_started),
            run_handler("conversation-b", second_started, first_started),
        )

        assert len(sink.spans) == 4
        for label in ("conversation-a", "conversation-b"):
            request_spans = [
                span for span in sink.spans if (span.attributes or {}).get("gen_ai.conversation.id") == label
            ]
            root = next(
                span
                for span in request_spans
                if (span.attributes or {}).get("gen_ai.operation.name") == "invoke_workflow"
            )
            child = next(
                span for span in request_spans if (span.attributes or {}).get("gen_ai.operation.name") == "chat"
            )
            assert child.parent == root.context
            assert child.context.trace_id == root.context.trace_id
            assert (child.attributes or {}).get("gen_ai.conversation.id") == label
            assert (root.attributes or {}).get("gen_ai.conversation.id") == label
        root_trace_ids = {
            span.context.trace_id
            for span in sink.spans
            if (span.attributes or {}).get("gen_ai.operation.name") == "invoke_workflow"
        }
        assert len(root_trace_ids) == 2
        assert sink.force_flush_calls == 0
    finally:
        logger.terminate()


class TestSplunkAOAsyncBaseHandlerCallback:
    @pytest.fixture
    @patch("splunk_ao.logger.logger.AgentStreams")
    @patch("splunk_ao.logger.logger.Projects")
    @patch("splunk_ao.logger.logger.Traces")
    def splunk_ao_logger(self, mock_traces_client: Mock, mock_projects_client: Mock, mock_logstreams_client: Mock):
        """Creates a mock Galileo logger for testing"""
        setup_mock_traces_client(mock_traces_client)
        setup_mock_projects_client(mock_projects_client)
        setup_mock_logstreams_client(mock_logstreams_client)
        return SplunkAOLogger(project="my_project", agent_stream="my_log_stream", ingestion_hook=lambda _: None)

    @pytest.fixture
    def handler(self, splunk_ao_logger: SplunkAOLogger) -> Generator[SplunkAOAsyncBaseHandler, None, None]:
        """Creates a SplunkAOCallback with a mock logger"""
        handler = SplunkAOAsyncBaseHandler(splunk_ao_logger=splunk_ao_logger, flush_on_chain_end=False)
        # Reset the root node before each test
        handler._root_node = None
        yield handler
        # Clean up after each test
        handler._root_node = None
        splunk_ao_logger.terminate()

    @pytest.mark.asyncio
    async def test_initialization(self, splunk_ao_logger: SplunkAOLogger) -> None:
        """Test callback initialization with various parameters"""
        # Default initialization
        callback = SplunkAOAsyncBaseHandler(splunk_ao_logger=splunk_ao_logger)
        assert callback._splunk_ao_logger == splunk_ao_logger
        assert callback._start_new_trace is True
        assert callback._flush_on_chain_end is False
        assert callback._nodes == {}

        # Custom initialization
        callback = SplunkAOAsyncBaseHandler(
            splunk_ao_logger=splunk_ao_logger, start_new_trace=False, flush_on_chain_end=False
        )
        assert callback._start_new_trace is False
        assert callback._flush_on_chain_end is False

    @pytest.mark.asyncio
    async def test_start_node(self, handler: SplunkAOAsyncBaseHandler) -> None:
        """Test creating a node and establishing parent-child relationships"""
        # Create a parent node
        parent_id = uuid.uuid4()
        node = await handler.async_start_node(
            node_type="chain", parent_run_id=None, run_id=parent_id, name="Parent Chain", input={"query": "test"}
        )

        assert node.node_type == "chain"
        assert node.run_id == parent_id
        assert node.parent_run_id is None
        assert "name" in node.span_params
        assert node.span_params["name"] == "Parent Chain"
        assert node.span_params["start_time"] > 0
        assert str(parent_id) in handler._nodes

        # Create a child node
        child_id = uuid.uuid4()
        child_node = await handler.async_start_node(
            node_type="llm", parent_run_id=parent_id, run_id=child_id, name="Child LLM", input="test prompt"
        )

        assert child_node.node_type == "llm"
        assert child_node.parent_run_id == parent_id
        assert str(child_id) in handler._nodes

        # Verify parent-child relationship was established
        assert str(child_id) in handler._nodes[str(parent_id)].children

        # Verify root node was set properly
        assert handler._root_node
        assert handler._root_node.run_id == parent_id

    @pytest.mark.asyncio
    async def test_live_root_is_reused_by_async_commit(
        self, handler: SplunkAOAsyncBaseHandler, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        run_id = uuid.uuid4()
        await handler.async_start_node(
            node_type="chain", parent_run_id=None, run_id=run_id, name="Root", input="request"
        )
        live_root = handler._owned_root
        live_context = splunk_ao_logger._otel_ids[live_root.id].span_context

        headers = get_tracing_headers()
        await handler.async_end_node(run_id, output="done")

        assert headers["traceparent"].split("-")[2] == format(live_context.span_id, "016x")
        assert splunk_ao_logger.traces[0].spans[0] is live_root
        assert splunk_ao_logger.current_parent() is None

    @pytest.mark.asyncio
    async def test_end_node(self, handler: SplunkAOAsyncBaseHandler, splunk_ao_logger: SplunkAOLogger) -> None:
        """Test ending a node and updating its parameters"""
        # Create a node
        run_id = uuid.uuid4()
        await handler.async_start_node(
            node_type="chain", parent_run_id=None, run_id=run_id, name="Test Chain", input='{"query": "test"}'
        )

        # End the node and commit the trace
        await handler.async_end_node(run_id, output='{"result": "test result"}')

        traces = splunk_ao_logger.traces
        assert len(traces) == 1
        assert len(traces[0].spans) == 1
        assert traces[0].spans[0].name == "Test Chain"
        assert traces[0].spans[0].type == "workflow"
        assert traces[0].spans[0].input == '{"query": "test"}'
        assert traces[0].spans[0].output == '{"result": "test result"}'

    @pytest.mark.asyncio
    async def test_commit_failure_concludes_handler_owned_trace(
        self, handler: SplunkAOAsyncBaseHandler, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        run_id = uuid.uuid4()
        await handler.async_start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

        with patch.object(handler, "_log_node_children", side_effect=RuntimeError("conversion failed")):
            await handler.async_end_node(run_id, output="result")

        assert splunk_ao_logger.current_parent() is None
        assert handler._nodes == {}
        assert handler._root_node is None

    @pytest.mark.asyncio
    async def test_start_new_trace_false_preserves_handler_root_and_caller(
        self, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        splunk_ao_logger.start_trace(input="request", name="caller")
        caller_operation = splunk_ao_logger.add_workflow_span(input="outer", name="outer")
        handler = SplunkAOAsyncBaseHandler(
            splunk_ao_logger=splunk_ao_logger, start_new_trace=False, flush_on_chain_end=False
        )
        root_id = uuid.uuid4()
        child_id = uuid.uuid4()
        await handler.async_start_node(
            node_type="chain", parent_run_id=None, run_id=root_id, name="handler-root", input="work"
        )
        await handler.async_start_node(
            node_type="llm",
            parent_run_id=root_id,
            run_id=child_id,
            name="handler-child",
            input="prompt",
            output="answer",
            model="model",
        )

        await handler.async_end_node(root_id, output="done")

        assert splunk_ao_logger.current_parent() is caller_operation
        [handler_root] = caller_operation.spans
        assert handler_root.name == "handler-root"
        assert [child.name for child in handler_root.spans] == ["handler-child"]
        splunk_ao_logger.conclude(output="outer done")
        splunk_ao_logger.conclude(output="done")
