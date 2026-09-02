import json
import uuid
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from opentelemetry import context as otel_context
from opentelemetry import propagate
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace.status import StatusCode

from splunk_ao import get_tracing_headers
from splunk_ao.exceptions import SplunkAOLoggerException
from splunk_ao.handlers.base_handler import SplunkAOBaseHandler
from splunk_ao.handlers.span_lifecycle import build_handler_step
from splunk_ao.logger.logger import SplunkAOLogger
from splunk_ao.schema.handlers import Node
from splunk_ao.schema.logged import LoggedAgentSpan, LoggedLlmSpan
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


def test_handler_step_uses_current_time_for_malformed_framework_timestamp() -> None:
    node = Node(
        node_type="tool",
        run_id=uuid.uuid4(),
        span_params={"input": "arguments", "name": "tool", "start_time_iso": "not-an-iso-timestamp"},
    )

    step = build_handler_step(node)

    assert step.created_at.tzinfo is not None


def test_handler_step_normalizes_missing_llm_output() -> None:
    node = Node(
        node_type="llm",
        run_id=uuid.uuid4(),
        span_params={"input": "prompt", "output": None, "name": "model", "model": "test-model"},
    )

    step = build_handler_step(node)

    assert isinstance(step, LoggedLlmSpan)
    assert step.output.content == ""


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


BASELINE_HANDLER_TOPOLOGY = {
    "invoke_workflow handler-root": ("invoke_workflow", None),
    "execute_tool search": ("execute_tool", "invoke_workflow handler-root"),
    "chat model": ("chat", "execute_tool search"),
}


def _handler_topology(carrier: dict[str, str] | None = None) -> dict[str, tuple[str | None, str | None]]:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    llm_id = uuid.uuid4()
    token = otel_context.attach(propagate.extract(carrier) if carrier is not None else Context())
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="handler-root", input="request")
        handler.start_node(node_type="tool", parent_run_id=root_id, run_id=tool_id, name="search", input="query")
        handler.start_node(
            node_type="llm", parent_run_id=tool_id, run_id=llm_id, name="model-call", input="prompt", model="model"
        )
        handler.end_node(llm_id, output="answer", model="model")
        handler.end_node(tool_id, output="result")
        handler.end_node(root_id, output="done")

        names_by_context = {(span.context.trace_id, span.context.span_id): span.name for span in sink.spans}
        return {
            span.name: (
                (span.attributes or {}).get("gen_ai.operation.name"),
                names_by_context.get((span.parent.trace_id, span.parent.span_id)) if span.parent is not None else None,
            )
            for span in sink.spans
        }
    finally:
        logger.terminate()
        otel_context.detach(token)


def test_distributed_and_non_distributed_handlers_preserve_baseline_local_topology() -> None:
    remote_carrier = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "vendor=value",
    }

    assert _handler_topology() == BASELINE_HANDLER_TOPOLOGY
    assert _handler_topology(remote_carrier) == BASELINE_HANDLER_TOPOLOGY


def test_leaf_only_handler_root_is_active_exportable_and_enqueued_without_flush() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    try:
        handler.start_node(
            node_type="llm", parent_run_id=None, run_id=root_id, name="leaf-root", input="prompt", model="model"
        )
        active_span_id = get_tracing_headers()["traceparent"].split("-")[2]

        handler.end_node(root_id, output="answer", model="model")

        [span] = sink.spans
        assert span.name == "chat model"
        assert (span.attributes or {}).get("gen_ai.operation.name") == "chat"
        assert format(span.context.span_id, "016x") == active_span_id
        assert span.parent is None
        assert sink.force_flush_calls == 0
    finally:
        logger.terminate()


def test_unsampled_remote_parent_suppresses_incremental_handler_export() -> None:
    remote_context = propagate.extract({"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"})
    token = otel_context.attach(remote_context)
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="root", input="request")
        handler.start_node(
            node_type="llm", parent_run_id=root_id, run_id=child_id, name="child", input="prompt", model="model"
        )
        handler.end_node(child_id, output="answer", model="model")
        handler.end_node(root_id, output="done")

        assert sink.spans == []
        assert sink.force_flush_calls == 0
    finally:
        logger.terminate()
        otel_context.detach(token)


def test_handler_error_span_enqueues_with_error_status_before_root_end() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="root", input="request")
        handler.start_node(
            node_type="tool", parent_run_id=root_id, run_id=child_id, name="failing-tool", input="arguments"
        )

        handler.end_node(child_id, error="tool failed")

        [span] = sink.spans
        assert span.name == "execute_tool failing-tool"
        assert span.status.status_code is StatusCode.ERROR
        assert json.loads(str((span.attributes or {}).get("gen_ai.tool.call.result"))) == {"value": "tool failed"}
        assert str(root_id) in handler._active_steps
        assert sink.force_flush_calls == 0

        handler.end_node(root_id, output="failed", status_code=500)
    finally:
        logger.terminate()


def test_failed_child_conversion_does_not_abort_remaining_handler_trace() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    failed_child_id = uuid.uuid4()
    good_child_id = uuid.uuid4()
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="root", input="request")
        root_step = handler._active_steps[str(root_id)].step
        root_span_id = logger._otel_ids[root_step.id].span_context.span_id
        handler.start_node(
            node_type="llm",
            parent_run_id=root_id,
            run_id=failed_child_id,
            name="bad child",
            input="prompt",
            model="model",
        )

        with patch("splunk_ao.handlers.base_handler.finalize_handler_step", side_effect=ValueError("bad child")):
            handler.end_node(failed_child_id, output="invalid")

        assert str(failed_child_id) not in handler._active_steps
        assert str(root_id) in handler._active_steps
        assert get_tracing_headers()["traceparent"].split("-")[2] == format(root_span_id, "016x")

        handler.start_node(
            node_type="llm",
            parent_run_id=root_id,
            run_id=good_child_id,
            name="good child",
            input="prompt",
            model="model",
        )
        handler.end_node(good_child_id, output="answer")
        handler.end_node(root_id, output="done")

        assert operation_names(sink.spans) == ["chat", "invoke_workflow"]
        assert all(span.status.status_code is not StatusCode.ERROR for span in sink.spans)
    finally:
        logger.terminate()


def test_root_completion_releases_unfinished_child_activation_and_identity() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    try:
        handler.start_node(node_type="chain", parent_run_id=None, run_id=root_id, name="root", input="request")
        handler.start_node(
            node_type="llm", parent_run_id=root_id, run_id=child_id, name="unfinished", input="prompt", model="model"
        )
        unfinished = handler._active_steps[str(child_id)].step

        handler.end_node(root_id, output="done")

        assert handler._active_steps == {}
        assert unfinished.id not in logger._otel_ids
        assert operation_names(sink.spans) == ["invoke_workflow"]
        with pytest.raises(SplunkAOLoggerException, match="active exportable operation"):
            get_tracing_headers()
    finally:
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
        sink = RecordingSink()
        logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
        handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=True)
        run_id = uuid.uuid4()
        try:
            handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

            handler.end_node(run_id, output="result")

            assert operation_names(sink.spans) == ["invoke_workflow"]
            assert sink.force_flush_calls == 1
        finally:
            logger.terminate()

    def test_commit_no_flush_when_disabled(self) -> None:
        """Test that commit() doesn't call flush or terminate when flush_on_chain_end=False."""
        sink = RecordingSink()
        logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
        handler = SplunkAOBaseHandler(splunk_ao_logger=logger, flush_on_chain_end=False)
        run_id = uuid.uuid4()
        try:
            handler.start_node(node_type="chain", parent_run_id=None, run_id=run_id, name="Test", input="test")

            handler.end_node(run_id, output="result")

            assert operation_names(sink.spans) == ["invoke_workflow"]
            assert sink.force_flush_calls == 0
        finally:
            logger.terminate()

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
