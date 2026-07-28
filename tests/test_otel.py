import json
from unittest.mock import Mock, patch

import pytest

from galileo_core.schemas.logging.llm import Message, MessageRole
from galileo_core.schemas.logging.span import AgentSpan, LlmSpan, RetrieverSpan, ToolSpan, WorkflowSpan
from galileo_core.schemas.shared.document import Document
from splunk_ao.decorator import (
    _dataset_input_context,
    _dataset_metadata_context,
    _dataset_output_context,
    _experiment_id_context,
    _log_stream_context,
    _project_context,
    _session_id_context,
    splunk_ao_dataset_context,
)
from splunk_ao.deployment import DeploymentMode, StandaloneConfig
from splunk_ao.otel import (
    _TRACE_PROVIDER_CONTEXT_VAR,
    SplunkAOOTLPExporter,
    SplunkAOSpanProcessor,
    _set_tool_span_attributes,
    _set_workflow_span_attributes,
    start_splunk_ao_span,
)


class TestSplunkAOSpanProcessor:
    """Test suite for SplunkAOSpanProcessor class."""

    @pytest.fixture
    def mock_processor_setup(self):
        """Set up common mocks for span processor tests."""
        with (
            patch("splunk_ao.otel.BatchSpanProcessor") as mock_batch_processor,
            patch("splunk_ao.otel.SplunkAOOTLPExporter") as mock_exporter_class,
        ):
            mock_exporter_instance = Mock()
            mock_processor_instance = Mock()
            mock_exporter_class.return_value = mock_exporter_instance
            mock_batch_processor.return_value = mock_processor_instance

            yield {
                "mock_exporter_class": mock_exporter_class,
                "mock_processor_class": mock_batch_processor,
                "mock_exporter_instance": mock_exporter_instance,
                "mock_processor_instance": mock_processor_instance,
            }

    def test_init_with_default_processor(self, mock_processor_setup):
        """Test initialization with default BatchSpanProcessor."""
        mocks = mock_processor_setup

        processor = SplunkAOSpanProcessor(project="test-project", agentstream="test-agentstream")

        # Verify exporter was created with correct parameters
        # Note: exporter is now created without explicit project/agentstream params (reads from context)
        mocks["mock_exporter_class"].assert_called_once()

        # Verify BatchSpanProcessor was created with the exporter
        mocks["mock_processor_class"].assert_called_once_with(mocks["mock_exporter_instance"])

        # Verify properties
        assert processor.exporter == mocks["mock_exporter_instance"]
        assert processor.processor == mocks["mock_processor_instance"]

    @patch("splunk_ao.otel.SplunkAOOTLPExporter")
    def test_init_with_custom_processor(self, mock_exporter_class):
        """Test initialization with custom span processor class."""
        mock_exporter_instance = Mock()
        mock_exporter_class.return_value = mock_exporter_instance

        # Create a mock custom processor class
        mock_custom_processor_class = Mock()
        mock_custom_processor_instance = Mock()
        mock_custom_processor_class.return_value = mock_custom_processor_instance

        processor = SplunkAOSpanProcessor(project="test-project", SpanProcessor=mock_custom_processor_class)

        # Verify custom processor was used
        mock_custom_processor_class.assert_called_once_with(mock_exporter_instance)
        assert processor.processor == mock_custom_processor_instance

    def test_on_start_delegates_to_processor(self, mock_processor_setup):
        """Test that on_start delegates to the underlying processor."""
        mocks = mock_processor_setup
        processor = SplunkAOSpanProcessor(project="test")

        mock_span = Mock()
        mock_context = Mock()
        processor.on_start(mock_span, mock_context)

        mocks["mock_processor_instance"].on_start.assert_called_once_with(mock_span, mock_context)

    def test_on_end_delegates_to_processor(self, mock_processor_setup):
        """Test that on_end delegates to the underlying processor."""
        mocks = mock_processor_setup
        processor = SplunkAOSpanProcessor(project="test")

        mock_span = Mock()
        mock_span.attributes = {"gen_ai.conversation_root": True}
        processor.on_end(mock_span)

        mocks["mock_processor_instance"].on_end.assert_called_once_with(mock_span)
        assert mocks["mock_processor_instance"].on_end.call_args.args[0].attributes == {
            "gen_ai.conversation_root": True
        }

    def test_shutdown_delegates_to_processor(self, mock_processor_setup):
        """Test that shutdown delegates to the underlying processor."""
        mocks = mock_processor_setup
        processor = SplunkAOSpanProcessor(project="test")

        processor.shutdown()

        mocks["mock_processor_instance"].shutdown.assert_called_once()

    def test_force_flush_delegates_to_processor(self, mock_processor_setup):
        """Test that force_flush delegates to the underlying processor."""
        mocks = mock_processor_setup
        mocks["mock_processor_instance"].force_flush.return_value = True
        processor = SplunkAOSpanProcessor(project="test")

        result = processor.force_flush(30000)

        mocks["mock_processor_instance"].force_flush.assert_called_once_with(30000)
        assert result is True

    def test_force_flush_default_timeout(self, mock_processor_setup):
        """Test that force_flush uses default timeout when not specified."""
        mocks = mock_processor_setup
        processor = SplunkAOSpanProcessor(project="test")

        processor.force_flush()

        mocks["mock_processor_instance"].force_flush.assert_called_once_with(40000)

    def test_init_passes_all_parameters_to_exporter(self, mock_processor_setup):
        """Test that all initialization parameters are passed to the exporter."""
        mocks = mock_processor_setup

        SplunkAOSpanProcessor(project="test-project", agentstream="test-agentstream")

        # Note: exporter is now created without explicit project/agentstream params (reads from context)
        mocks["mock_exporter_class"].assert_called_once()


class TestOTelIntegration:
    """Integration tests for OpenTelemetry functionality."""

    def test_exporter_and_processor_integration(self):
        """Test that SplunkAOSpanProcessor correctly integrates with SplunkAOOTLPExporter."""
        mock_batch_instance = Mock()
        mock_config = Mock()
        mock_config.resolve_deployment.return_value = DeploymentMode.STANDALONE
        standalone = StandaloneConfig(
            api_key="test-key", console_url="https://console.example.com", api_url="https://api.example.com"
        )
        experiment_token = _experiment_id_context.set(None)
        try:
            with (
                patch("splunk_ao.otel.BatchSpanProcessor", return_value=mock_batch_instance) as mock_batch_processor,
                patch("splunk_ao.otel.OTLPSpanExporter.__init__", return_value=None) as mock_otlp_init,
                patch("splunk_ao.otel.SplunkAOConfig.get", return_value=mock_config),
                patch("splunk_ao.otel.StandaloneConfig.from_env", return_value=standalone),
            ):
                processor = SplunkAOSpanProcessor(project="integration-test", agentstream="integration-agentstream")
        finally:
            _experiment_id_context.reset(experiment_token)

        # Verify the exporter was created and passed to the processor
        mock_otlp_init.assert_called_once_with(
            endpoint="https://api.example.com/otel/v1/traces",
            headers={
                "Splunk-AO-API-Key": "test-key",
                "project": "integration-test",
                "logstream": "integration-agentstream",
            },
        )
        mock_batch_processor.assert_called_once()

        # Verify the processor has access to both components
        assert hasattr(processor, "exporter")
        assert hasattr(processor, "processor")
        assert processor.processor == mock_batch_instance


class TestOTelContextIntegration:
    """Tests for OpenTelemetry context variable integration."""

    @pytest.fixture
    def reset_decorator_context(self):
        """Reset decorator context before each test."""
        for ctx in [_project_context, _log_stream_context, _experiment_id_context, _session_id_context]:
            ctx.set(None)
        yield
        for ctx in [_project_context, _log_stream_context, _experiment_id_context, _session_id_context]:
            ctx.set(None)

    @pytest.fixture
    def mock_processor_deps(self):
        """Mock dependencies for processor tests."""
        with (
            patch("splunk_ao.otel.BatchSpanProcessor") as mock_batch,
            patch("splunk_ao.otel.SplunkAOOTLPExporter") as mock_exp,
        ):
            mock_exp.return_value = Mock()
            mock_batch.return_value = Mock()
            yield {"exporter": mock_exp, "batch": mock_batch}

    def test_exporter_context_vars_and_override(self, reset_decorator_context):
        """Test exporter reads from context vars and params override them."""
        mock_config = Mock()
        mock_config.resolve_deployment.return_value = DeploymentMode.STANDALONE
        standalone = StandaloneConfig(
            api_key="test-key", console_url="https://console.example.com", api_url="https://api.example.com"
        )

        # Set context variables
        _project_context.set("context-project")
        _log_stream_context.set("context-logstream")

        with (
            patch("splunk_ao.otel.OTLPSpanExporter.__init__", return_value=None),
            patch("splunk_ao.otel.SplunkAOConfig.get", return_value=mock_config),
            patch("splunk_ao.otel.StandaloneConfig.from_env", return_value=standalone),
        ):
            # Exporter uses context values
            exporter = SplunkAOOTLPExporter()
            assert exporter.project == "context-project"
            assert exporter.agentstream == "context-logstream"

            # Explicit params override context
            exporter2 = SplunkAOOTLPExporter(project="param-project", agentstream="param-agentstream")
            assert exporter2.project == "param-project"
            assert exporter2.agentstream == "param-agentstream"

    def test_processor_captures_context_at_exporter_construction(self, mock_processor_deps, reset_decorator_context):
        """Test processor passes routing inputs to its immutable exporter."""
        _project_context.set("context-project")
        _log_stream_context.set("context-logstream")

        SplunkAOSpanProcessor()
        mock_processor_deps["exporter"].assert_called_once()

    def test_processor_on_start_sets_content_not_routing_attributes(self, mock_processor_deps, reset_decorator_context):
        """Test on_start keeps session content and omits request routing."""
        _project_context.set("test-project")
        _log_stream_context.set("test-logstream")
        _experiment_id_context.set("test-experiment")
        _session_id_context.set("test-session")

        processor = SplunkAOSpanProcessor()
        mock_span = Mock()

        # When: the processor starts a span
        processor.on_start(mock_span, None)

        assert mock_span.set_attribute.call_count == 1
        actual_calls = {(args[0], args[1]) for args, _ in mock_span.set_attribute.call_args_list}
        assert ("splunk_ao.session.id", "test-session") in actual_calls
        routing_keys = {"splunk_ao.project.name", "splunk_ao.logstream.name", "splunk_ao.experiment.id"}
        assert not routing_keys.intersection(key for key, _ in actual_calls)


class TestSetToolSpanAttributes:
    """Test suite for _set_tool_span_attributes function."""

    def test_tool_span_with_all_fields(self):
        """Test setting attributes when all ToolSpan fields are populated."""
        # Given: a ToolSpan with input, output, and tool_call_id
        tool_span = ToolSpan(
            name="test-tool",
            input="tool input data",
            output="tool output result",
            tool_call_id="call-123",
            status_code=200,
        )
        mock_otel_span = Mock()

        # When: setting tool span attributes
        _set_tool_span_attributes(mock_otel_span, tool_span)

        # Then: all attributes are set correctly
        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert calls["gen_ai.operation.name"] == "execute_tool"
        assert calls["gen_ai.tool.name"] == "test-tool"
        assert calls["gen_ai.tool.call.arguments"] == "tool input data"
        assert calls["gen_ai.tool.call.result"] == "tool output result"
        assert calls["gen_ai.input.messages"] == json.dumps([{"role": "tool", "content": "tool input data"}])
        assert calls["gen_ai.output.messages"] == json.dumps([{"role": "tool", "content": "tool output result"}])
        assert calls["gen_ai.tool.call.id"] == "call-123"
        assert mock_otel_span.set_attribute.call_count == 7

    def test_tool_span_with_only_input(self):
        """Test setting attributes when only input is provided."""
        # Given: a ToolSpan with only input (output and tool_call_id are None)
        tool_span = ToolSpan(name="test-tool", input="tool input only", output=None, tool_call_id=None, status_code=200)
        mock_otel_span = Mock()

        # When: setting tool span attributes
        _set_tool_span_attributes(mock_otel_span, tool_span)

        # Then: operation name, tool name, and input attributes are set, but not output or tool_call_id
        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert calls["gen_ai.operation.name"] == "execute_tool"
        assert calls["gen_ai.tool.name"] == "test-tool"
        assert calls["gen_ai.tool.call.arguments"] == "tool input only"
        assert calls["gen_ai.input.messages"] == json.dumps([{"role": "tool", "content": "tool input only"}])
        assert "gen_ai.tool.call.result" not in calls
        assert "gen_ai.output.messages" not in calls
        assert "gen_ai.tool.call.id" not in calls
        assert mock_otel_span.set_attribute.call_count == 4

    def test_tool_span_with_output_no_tool_call_id(self):
        """Test setting attributes when output is provided but tool_call_id is None."""
        # Given: a ToolSpan with input and output, but no tool_call_id
        tool_span = ToolSpan(
            name="test-tool", input="tool input", output="tool output", tool_call_id=None, status_code=200
        )
        mock_otel_span = Mock()

        # When: setting tool span attributes
        _set_tool_span_attributes(mock_otel_span, tool_span)

        # Then: operation name, tool name, input, and output attributes are set, but not tool_call_id
        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert calls["gen_ai.operation.name"] == "execute_tool"
        assert calls["gen_ai.tool.name"] == "test-tool"
        assert calls["gen_ai.tool.call.arguments"] == "tool input"
        assert calls["gen_ai.tool.call.result"] == "tool output"
        assert calls["gen_ai.input.messages"] == json.dumps([{"role": "tool", "content": "tool input"}])
        assert calls["gen_ai.output.messages"] == json.dumps([{"role": "tool", "content": "tool output"}])
        assert "gen_ai.tool.call.id" not in calls
        assert mock_otel_span.set_attribute.call_count == 6


class TestStartGalileoSpan:
    """Test suite for start_splunk_ao_span context manager."""

    @pytest.fixture(autouse=True)
    def reset_trace_provider(self):
        """Reset the trace provider context var before and after each test."""
        _TRACE_PROVIDER_CONTEXT_VAR.set(None)
        yield
        _TRACE_PROVIDER_CONTEXT_VAR.set(None)

    def test_start_splunk_ao_span_dispatches_tool_span(self):
        """Test that start_splunk_ao_span routes a ToolSpan to _set_tool_span_attributes."""
        # Given: a ToolSpan with all fields populated and a mock tracer provider
        tool_span = ToolSpan(
            name="my-tool",
            input="tool input data",
            output="tool output result",
            tool_call_id="call-789",
            status_code=200,
        )
        mock_otel_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_provider = Mock()
        mock_provider.get_tracer.return_value = mock_tracer
        _TRACE_PROVIDER_CONTEXT_VAR.set(mock_provider)

        # When: using start_splunk_ao_span with the ToolSpan
        with start_splunk_ao_span(tool_span) as span:
            assert span is mock_otel_span

        # Then: tool-specific attributes are retained without an SDK provider injection
        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert "gen_ai.system" not in calls
        assert calls["gen_ai.operation.name"] == "execute_tool"
        assert calls["gen_ai.tool.name"] == "my-tool"
        assert calls["gen_ai.tool.call.arguments"] == "tool input data"
        assert calls["gen_ai.tool.call.result"] == "tool output result"
        assert calls["gen_ai.input.messages"] == json.dumps([{"role": "tool", "content": "tool input data"}])
        assert calls["gen_ai.output.messages"] == json.dumps([{"role": "tool", "content": "tool output result"}])
        assert calls["gen_ai.tool.call.id"] == "call-789"

    def test_start_splunk_ao_span_tool_span_with_none_output(self):
        """Test that start_splunk_ao_span handles a ToolSpan with None output and tool_call_id."""
        # Given: a ToolSpan with only input populated
        tool_span = ToolSpan(name="minimal-tool", input="just input", output=None, tool_call_id=None, status_code=200)
        mock_otel_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_provider = Mock()
        mock_provider.get_tracer.return_value = mock_tracer
        _TRACE_PROVIDER_CONTEXT_VAR.set(mock_provider)

        # When: using start_splunk_ao_span with the minimal ToolSpan
        with start_splunk_ao_span(tool_span) as span:
            assert span is mock_otel_span

        # Then: tool attributes are set without output, call ID, or an SDK provider injection
        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert "gen_ai.system" not in calls
        assert calls["gen_ai.operation.name"] == "execute_tool"
        assert calls["gen_ai.tool.name"] == "minimal-tool"
        assert calls["gen_ai.tool.call.arguments"] == "just input"
        assert calls["gen_ai.input.messages"] == json.dumps([{"role": "tool", "content": "just input"}])
        assert "gen_ai.tool.call.result" not in calls
        assert "gen_ai.output.messages" not in calls
        assert "gen_ai.tool.call.id" not in calls

    @pytest.mark.parametrize(
        "galileo_span",
        [
            WorkflowSpan(name="workflow", input="input", output="output"),
            AgentSpan(name="agent", input="input", output="output"),
        ],
    )
    def test_start_splunk_ao_span_marks_eligible_root_without_parent(self, galileo_span):
        """Eligible spans with no caller parent receive the standard root marker."""
        mock_otel_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_provider = Mock()
        mock_provider.get_tracer.return_value = mock_tracer
        _TRACE_PROVIDER_CONTEXT_VAR.set(mock_provider)

        with patch("splunk_ao.otel.trace") as mock_trace:
            mock_trace.get_current_span.return_value.get_span_context.return_value.is_valid = False
            with start_splunk_ao_span(galileo_span):
                pass

        calls = {
            args[0]: args[1] if len(args) > 1 else kwargs["value"]
            for args, kwargs in mock_otel_span.set_attribute.call_args_list
        }
        assert calls["gen_ai.conversation_root"] is True

    def test_start_splunk_ao_span_does_not_mark_span_with_parent(self):
        """A valid caller parent prevents a new conversation root marker."""
        workflow_span = WorkflowSpan(name="workflow", input="input", output="output")
        mock_otel_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_provider = Mock()
        mock_provider.get_tracer.return_value = mock_tracer
        _TRACE_PROVIDER_CONTEXT_VAR.set(mock_provider)

        with patch("splunk_ao.otel.trace") as mock_trace:
            mock_trace.get_current_span.return_value.get_span_context.return_value.is_valid = True
            with start_splunk_ao_span(workflow_span):
                pass

        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert "gen_ai.conversation_root" not in calls

    @pytest.mark.parametrize(
        "galileo_span",
        [
            ToolSpan(name="tool", input="input", output="output"),
            LlmSpan(
                name="llm",
                input=[Message(role=MessageRole.user, content="input")],
                output=Message(role=MessageRole.assistant, content="output"),
                model="model",
            ),
            RetrieverSpan(name="retriever", input="input", output=[]),
        ],
    )
    def test_start_splunk_ao_span_does_not_mark_ineligible_root(self, galileo_span):
        """LLM, tool, and retriever spans are never conversation roots."""
        mock_otel_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_otel_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_provider = Mock()
        mock_provider.get_tracer.return_value = mock_tracer
        _TRACE_PROVIDER_CONTEXT_VAR.set(mock_provider)

        with patch("splunk_ao.otel.trace") as mock_trace:
            mock_trace.get_current_span.return_value.get_span_context.return_value.is_valid = False
            with start_splunk_ao_span(galileo_span):
                pass

        calls = {args[0]: args[1] for args, _ in mock_otel_span.set_attribute.call_args_list}
        assert "gen_ai.conversation_root" not in calls


class TestWorkflowSpanAttributes:
    """Test suite for WorkflowSpan OpenTelemetry attribute mapping."""

    @pytest.fixture
    def mock_dependencies(self):
        """Set up mocks for testing workflow span attributes."""
        with patch("splunk_ao.otel.trace") as mock_trace_module, patch("splunk_ao.otel.json") as mock_json_module:
            mock_span = Mock()
            mock_json_module.dumps.return_value = '"test"'
            yield {"span": mock_span, "trace": mock_trace_module, "json": mock_json_module}

    def test_workflow_span_with_string_input_output(self, mock_dependencies):
        """Test WorkflowSpan with string input and output."""
        # Given: a WorkflowSpan with string input and output
        workflow_span = WorkflowSpan(name="test-workflow", input="input text", output="output text", status_code=200)
        mock_span = mock_dependencies["span"]
        mock_json = mock_dependencies["json"]

        # When: setting workflow span attributes
        _set_workflow_span_attributes(mock_span, workflow_span)

        # Then: input and output should be wrapped in message format
        assert mock_span.set_attribute.call_count == 2

        # Check first call (input)
        input_call = mock_span.set_attribute.call_args_list[0]
        assert input_call[0][0] == "gen_ai.input.messages"
        mock_json.dumps.assert_any_call([{"role": "user", "content": "input text"}])

        # Check second call (output)
        output_call = mock_span.set_attribute.call_args_list[1]
        assert output_call[0][0] == "gen_ai.output.messages"
        mock_json.dumps.assert_any_call([{"role": "assistant", "content": "output text"}])

    def test_workflow_span_with_message_input_output(self, mock_dependencies):
        """Test WorkflowSpan with Message input and output."""
        # Given: a WorkflowSpan with Message input and output
        input_msg = Message(role=MessageRole.user, content="user question")
        workflow_span = WorkflowSpan(name="test-workflow", input=[input_msg], output=input_msg, status_code=200)
        mock_span = mock_dependencies["span"]
        mock_dependencies["json"]

        # When: setting workflow span attributes
        _set_workflow_span_attributes(mock_span, workflow_span)

        # Then: input and output should serialize Message objects
        assert mock_span.set_attribute.call_count == 2
        input_call = mock_span.set_attribute.call_args_list[0]
        assert input_call[0][0] == "gen_ai.input.messages"
        output_call = mock_span.set_attribute.call_args_list[1]
        assert output_call[0][0] == "gen_ai.output.messages"

    def test_workflow_span_with_document_sequence_output(self, mock_dependencies):
        """Test WorkflowSpan with Document sequence output."""
        # Given: a WorkflowSpan with string input and Document sequence output
        documents = [
            Document(content="doc1 content", metadata={"source": "db"}),
            Document(content="doc2 content", metadata={"source": "api"}),
        ]
        # Note: Using model_construct to bypass a galileo_core validator bug where
        # Message._allow_null_content_with_tool_calling assumes dict input during
        # Union type validation, but receives a list when validating Sequence[Document]
        workflow_span = WorkflowSpan.model_construct(
            name="test-workflow", input="query", output=documents, status_code=200
        )
        mock_span = mock_dependencies["span"]
        mock_dependencies["json"]

        # When: setting workflow span attributes
        _set_workflow_span_attributes(mock_span, workflow_span)

        # Then: output should be wrapped in assistant message with documents
        assert mock_span.set_attribute.call_count == 2
        output_call = mock_span.set_attribute.call_args_list[1]
        assert output_call[0][0] == "gen_ai.output.messages"

    def test_workflow_span_with_none_output(self, mock_dependencies):
        """Test WorkflowSpan with None output (should not set output attribute)."""
        # Given: a WorkflowSpan with None output
        workflow_span = WorkflowSpan(name="test-workflow", input="input text", output=None, status_code=200)
        mock_span = mock_dependencies["span"]

        # When: setting workflow span attributes
        _set_workflow_span_attributes(mock_span, workflow_span)

        # Then: only input attribute should be set, not output
        assert mock_span.set_attribute.call_count == 1
        input_call = mock_span.set_attribute.call_args_list[0]
        assert input_call[0][0] == "gen_ai.input.messages"

    def test_workflow_span_in_start_splunk_ao_span(self, mock_dependencies):
        """Test that WorkflowSpan is handled in start_splunk_ao_span context manager."""
        # Given: a WorkflowSpan
        workflow_span = WorkflowSpan(name="test-workflow", input="input", output="output", status_code=200)
        mock_span = mock_dependencies["span"]
        mock_dependencies["json"]

        # Setup the mock tracer
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)

        mock_trace_provider = Mock()
        mock_trace_provider.get_tracer.return_value = mock_tracer

        # Patch get_tracer_provider to return our mock
        with patch("splunk_ao.otel.trace.get_tracer_provider", return_value=mock_trace_provider):
            # When: using start_splunk_ao_span with WorkflowSpan
            with start_splunk_ao_span(workflow_span):
                pass

        # Then: WorkflowSpan attributes should be set without an SDK provider injection
        assert mock_span.set_attribute.call_count >= 2
        system_call = [call for call in mock_span.set_attribute.call_args_list if call[0][0] == "gen_ai.system"]
        assert system_call == []


class TestDatasetContext:
    """Tests for dataset context variables and splunk_ao_dataset_context manager."""

    @pytest.fixture
    def reset_dataset_context(self):
        """Reset dataset context variables before and after each test."""
        _dataset_input_context.set(None)
        _dataset_output_context.set(None)
        _dataset_metadata_context.set(None)
        yield
        _dataset_input_context.set(None)
        _dataset_output_context.set(None)
        _dataset_metadata_context.set(None)

    @pytest.fixture
    def mock_processor_deps(self):
        """Mock dependencies for processor tests."""
        with (
            patch("splunk_ao.otel.BatchSpanProcessor") as mock_batch,
            patch("splunk_ao.otel.SplunkAOOTLPExporter") as mock_exp,
        ):
            mock_exp.return_value = Mock()
            mock_batch.return_value = Mock()
            yield {"exporter": mock_exp, "batch": mock_batch}

    def test_splunk_ao_dataset_context_sets_values(self, reset_dataset_context):
        """Test that splunk_ao_dataset_context sets context variables correctly."""
        # Given: dataset context is initially empty
        assert _dataset_input_context.get(None) is None
        assert _dataset_output_context.get(None) is None
        assert _dataset_metadata_context.get(None) is None

        # When: entering the context manager with values
        with splunk_ao_dataset_context(
            dataset_input="test input", dataset_output="expected output", dataset_metadata={"key": "value"}
        ):
            # Then: context variables are set inside the context
            assert _dataset_input_context.get() == "test input"
            assert _dataset_output_context.get() == "expected output"
            assert _dataset_metadata_context.get() == {"key": "value"}

        # Then: context variables are reset after exiting
        assert _dataset_input_context.get(None) is None
        assert _dataset_output_context.get(None) is None
        assert _dataset_metadata_context.get(None) is None

    def test_splunk_ao_dataset_context_nested_contexts(self, reset_dataset_context):
        """Test that nested splunk_ao_dataset_context managers work correctly."""
        # Given: outer context with initial values
        with splunk_ao_dataset_context(dataset_input="outer input", dataset_output="outer output"):
            assert _dataset_input_context.get() == "outer input"
            assert _dataset_output_context.get() == "outer output"

            # When: entering inner context with different values
            with splunk_ao_dataset_context(dataset_input="inner input", dataset_output="inner output"):
                # Then: inner context values are active
                assert _dataset_input_context.get() == "inner input"
                assert _dataset_output_context.get() == "inner output"

            # Then: outer context values are restored
            assert _dataset_input_context.get() == "outer input"
            assert _dataset_output_context.get() == "outer output"

        # Then: context is empty after exiting all contexts
        assert _dataset_input_context.get(None) is None
        assert _dataset_output_context.get(None) is None

    def test_splunk_ao_dataset_context_exception_handling(self, reset_dataset_context):
        """Test that context variables are reset even when exception occurs."""
        # Given/When: an exception is raised inside the context
        with pytest.raises(ValueError, match="test error"):
            with splunk_ao_dataset_context(dataset_input="test", dataset_output="expected"):
                assert _dataset_input_context.get() == "test"
                raise ValueError("test error")

        # Then: context variables are still reset
        assert _dataset_input_context.get(None) is None
        assert _dataset_output_context.get(None) is None

    def test_processor_on_start_sets_dataset_attributes(self, mock_processor_deps, reset_dataset_context):
        """Test that on_start sets dataset attributes on spans from context."""
        # Given: dataset context variables are set
        _dataset_input_context.set("input question")
        _dataset_output_context.set("expected answer")
        _dataset_metadata_context.set({"source": "test_dataset"})

        processor = SplunkAOSpanProcessor()
        mock_span = Mock()

        # When: on_start is called
        processor.on_start(mock_span, None)

        # Then: dataset attributes are set on the span
        actual_calls = {(args[0], args[1]) for args, _ in mock_span.set_attribute.call_args_list}
        assert ("splunk_ao.dataset.input", "input question") in actual_calls
        assert ("splunk_ao.dataset.output", "expected answer") in actual_calls
        assert ("splunk_ao.dataset.metadata", json.dumps({"source": "test_dataset"})) in actual_calls

    def test_splunk_ao_dataset_context_partial_values(self, reset_dataset_context):
        """Test that splunk_ao_dataset_context works with partial values."""
        # When: only some values are provided
        with splunk_ao_dataset_context(dataset_output="expected only"):
            # Then: only provided values are set
            assert _dataset_input_context.get(None) is None
            assert _dataset_output_context.get() == "expected only"
            assert _dataset_metadata_context.get(None) is None

        # Then: values are reset after exit
        assert _dataset_output_context.get(None) is None
