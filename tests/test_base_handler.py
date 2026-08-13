import uuid
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan

from splunk_ao import get_tracing_headers
from splunk_ao.handlers.base_handler import SplunkAOBaseHandler
from splunk_ao.logger.logger import SplunkAOLogger
from splunk_ao.schema.logged import LoggedAgentSpan
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


def operation_names(spans: list[ReadableSpan]) -> list[str | None]:
    return [(span.attributes or {}).get("gen_ai.operation.name") for span in spans]


def test_normal_otel_child_enqueues_at_callback_end_without_flush() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="root", input="request")
        root_step = handler._active_steps[str(root_id)].step
        handler.start_node(
            node_type="llm", parent_run_id=root_id, run_id=child_id, name="child", input="prompt", model="model"
        )

        handler.end_node(child_id, output="answer", model="model")

        assert operation_names(sink.spans) == ["chat"]
        assert str(root_id) in handler._active_steps
        assert logger.current_parent() is root_step
        assert sink.force_flush_calls == 0

        handler.end_node(root_id, output="done")

        assert operation_names(sink.spans) == ["chat", "invoke_workflow"]
        child_span, root_span = sink.spans
        assert child_span.parent == root_span.context
        assert root_span.parent is None
        assert [child.name for child in root_step.spans] == ["child"]
        assert sink.force_flush_calls == 0
    finally:
        logger.terminate()


def test_incremental_handler_root_is_active_beneath_caller_owned_operation() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    logger.start_trace(input="caller trace")
    caller = logger.add_workflow_span(input="caller operation", name="caller")
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, start_new_trace=False, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="handler", input="request")
        handler_root = handler._active_steps[str(root_id)].step
        handler_context = logger._otel_ids[handler_root.id].span_context
        headers = get_tracing_headers()
        handler.start_node(
            node_type="llm", parent_run_id=root_id, run_id=child_id, name="child", input="prompt", model="model"
        )
        handler.end_node(child_id, output="answer", model="model")
        handler.end_node(root_id, output="done")

        assert headers["traceparent"].split("-")[2] == format(handler_context.span_id, "016x")
        assert logger.current_parent() is caller
        child_span, handler_span = sink.spans
        assert child_span.parent == handler_span.context
        assert handler_span.parent == logger._otel_ids[caller.id].span_context
        assert [step.name for step in caller.spans] == ["handler"]
    finally:
        logger.conclude(output="caller done")
        logger.conclude(output="trace done")
        logger.terminate()


class TestSplunkAOBaseHandler:
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
    def handler(self, splunk_ao_logger: SplunkAOLogger) -> Generator[SplunkAOBaseHandler, None, None]:
        """Creates a SplunkAOBaseHandler with a mock logger"""
        handler = SplunkAOBaseHandler(splunk_ao_logger=splunk_ao_logger, flush_on_chain_end=False)
        yield handler
        splunk_ao_logger.terminate()

    def test_initialization(self, splunk_ao_logger: SplunkAOLogger) -> None:
        """Test callback initialization with various parameters"""
        # Default initialization
        handler = SplunkAOBaseHandler(splunk_ao_logger=splunk_ao_logger)
        assert handler._splunk_ao_logger == splunk_ao_logger
        assert handler._start_new_trace is True
        assert handler._flush_on_chain_end is False
        assert handler._nodes == {}

        # Custom initialization
        handler = SplunkAOBaseHandler(
            splunk_ao_logger=splunk_ao_logger, start_new_trace=False, flush_on_chain_end=False
        )
        assert handler._start_new_trace is False
        assert handler._flush_on_chain_end is False

    def test_start_node(self, handler: SplunkAOBaseHandler) -> None:
        """Test creating a node and establishing parent-child relationships"""
        # Create a parent node
        parent_id = uuid.uuid4()
        node = handler.start_node(
            node_type="chain", parent_run_id=None, run_id=parent_id, name="Parent Chain", input={"query": "test"}
        )

        assert node.node_type == "chain"
        assert node.run_id == parent_id
        assert node.parent_run_id is None
        assert "name" in node.span_params
        assert node.span_params["name"] == "Parent Chain"
        assert str(parent_id) in handler._nodes
        assert "start_time" in node.span_params

        # Create a child node
        child_id = uuid.uuid4()
        child_node = handler.start_node(
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

    def test_root_is_live_for_w3c_injection_and_reused_at_commit(
        self, handler: SplunkAOBaseHandler, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        run_id = uuid.uuid4()
        handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Root", input="request")
        live_root = handler._owned_root
        live_context = splunk_ao_logger._otel_ids[live_root.id].span_context

        headers = get_tracing_headers()
        handler.end_node(run_id, output="done")

        assert headers["traceparent"].split("-")[2] == format(live_context.span_id, "016x")
        assert len(splunk_ao_logger.traces[0].spans) == 1
        assert splunk_ao_logger.traces[0].spans[0] is live_root
        assert splunk_ao_logger.current_parent() is None

    def test_late_langgraph_agent_classification_preserves_live_otel_identity(
        self, handler: SplunkAOBaseHandler, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        root_id = uuid.uuid4()
        child_id = uuid.uuid4()
        root_node = handler.start_node(
            node_type="chain", parent_run_id=None, run_id=root_id, name="Root", input="request"
        )
        original_root = handler._owned_root
        original_ids = splunk_ao_logger._otel_ids[original_root.id]

        root_node.node_type = "agent"
        handler.start_node(node_type="llm", parent_run_id=root_id, run_id=child_id, name="Child", input="prompt")

        assert isinstance(handler._owned_root, LoggedAgentSpan)
        assert handler._owned_root.id == original_root.id
        assert splunk_ao_logger._otel_ids[handler._owned_root.id] is original_ids
        assert splunk_ao_logger.current_parent() is handler._owned_root

        handler.end_node(child_id, output="answer", model="model")
        handler.end_node(root_id, output="done")
        assert isinstance(splunk_ao_logger.traces[0].spans[0], LoggedAgentSpan)

    def test_end_node(self, handler: SplunkAOBaseHandler, splunk_ao_logger: SplunkAOLogger) -> None:
        """Test ending a node and updating its parameters"""
        # Create a node
        run_id = uuid.uuid4()
        handler.start_node(
            node_type="chain", parent_run_id=None, run_id=run_id, name="Test Chain", input='{"query": "test"}'
        )

        # End the node and commit the trace
        handler.end_node(run_id, output='{"result": "test result"}')

        traces = splunk_ao_logger.traces
        assert len(traces) == 1
        assert len(traces[0].spans) == 1
        assert traces[0].spans[0].name == "Test Chain"
        assert traces[0].spans[0].type == "workflow"
        assert traces[0].spans[0].input == '{"query": "test"}'
        assert traces[0].spans[0].output == '{"result": "test result"}'

    def test_commit_calls_flush(self) -> None:
        """Test that commit() calls flush() when flush_on_chain_end=True."""
        # Given: a mock logger
        mock_logger = Mock(spec=SplunkAOLogger)
        mock_logger.start_trace = Mock()
        mock_logger.conclude = Mock()
        mock_logger.current_parent = Mock(return_value=None)
        mock_logger.add_workflow_span = Mock()
        mock_logger._set_current_parent = Mock()
        handler = SplunkAOBaseHandler(splunk_ao_logger=mock_logger, flush_on_chain_end=True)

        # Setup a simple trace to commit
        run_id = uuid.uuid4()
        handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

        # When: ending the node (which triggers commit)
        handler.end_node(run_id, output="result")

        # Then: flush is called
        mock_logger.flush.assert_called_once()

    def test_commit_no_flush_when_disabled(self) -> None:
        """Test that commit() doesn't call flush or terminate when flush_on_chain_end=False."""
        # Given: a mock logger with flush disabled
        mock_logger = Mock(spec=SplunkAOLogger)
        mock_logger.mode = "batch"
        mock_logger.start_trace = Mock()
        mock_logger.conclude = Mock()
        mock_logger.current_parent = Mock(return_value=None)
        mock_logger.add_workflow_span = Mock()
        mock_logger._set_current_parent = Mock()
        handler = SplunkAOBaseHandler(splunk_ao_logger=mock_logger, flush_on_chain_end=False)

        # Setup a simple trace to commit
        run_id = uuid.uuid4()
        handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

        # When: ending the node (which triggers commit)
        handler.end_node(run_id, output="result")

        # Then: neither flush nor terminate is called
        mock_logger.flush.assert_not_called()
        mock_logger.terminate.assert_not_called()

    def test_commit_failure_concludes_only_handler_owned_trace(
        self, handler: SplunkAOBaseHandler, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        run_id = uuid.uuid4()
        handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

        with patch.object(handler, "_log_node_children", side_effect=RuntimeError("conversion failed")):
            handler.end_node(run_id, output="result")

        assert splunk_ao_logger.current_parent() is None
        assert handler._nodes == {}
        assert handler._root_node is None

    def test_commit_failure_preserves_caller_owned_trace(self, splunk_ao_logger: SplunkAOLogger) -> None:
        splunk_ao_logger.start_trace(input="request", name="caller")
        caller_operation = splunk_ao_logger.add_workflow_span(input="outer", name="outer")
        handler = SplunkAOBaseHandler(
            splunk_ao_logger=splunk_ao_logger, start_new_trace=False, flush_on_chain_end=False
        )
        run_id = uuid.uuid4()
        handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

        with patch.object(handler, "log_node_tree", side_effect=RuntimeError("conversion failed")):
            handler.end_node(run_id, output="result")

        assert splunk_ao_logger.current_parent() is caller_operation
        splunk_ao_logger.conclude(output="outer done")
        splunk_ao_logger.conclude(output="done")

    def test_start_new_trace_false_preserves_handler_root_beneath_caller(
        self, splunk_ao_logger: SplunkAOLogger
    ) -> None:
        splunk_ao_logger.start_trace(input="request", name="caller")
        caller_operation = splunk_ao_logger.add_workflow_span(input="outer", name="outer")
        handler = SplunkAOBaseHandler(
            splunk_ao_logger=splunk_ao_logger, start_new_trace=False, flush_on_chain_end=False
        )
        caller_context = splunk_ao_logger._otel_ids[caller_operation.id].span_context
        root_id = uuid.uuid4()
        child_id = uuid.uuid4()
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="handler-root", input="work")
        headers = get_tracing_headers()
        handler.start_node(
            node_type="llm",
            parent_run_id=root_id,
            run_id=child_id,
            name="handler-child",
            input="prompt",
            output="answer",
            model="model",
        )

        handler.end_node(root_id, output="done")

        assert splunk_ao_logger.current_parent() is caller_operation
        assert headers["traceparent"].split("-")[2] == format(caller_context.span_id, "016x")
        [handler_root] = caller_operation.spans
        assert handler_root.name == "handler-root"
        assert [child.name for child in handler_root.spans] == ["handler-child"]
        splunk_ao_logger.conclude(output="outer done")
        splunk_ao_logger.conclude(output="done")
