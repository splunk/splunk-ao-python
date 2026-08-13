import logging
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from agents import Span, Trace, TracingProcessor
from agents.tracing import ResponseSpanData, get_current_span, get_trace_provider

from galileo_core.schemas.logging.span import LlmMetrics, LlmSpan
from galileo_core.schemas.logging.span import Span as SplunkAOSpan
from splunk_ao import SplunkAOLogger, splunk_ao_context
from splunk_ao.handlers.span_lifecycle import HandlerSpanState, build_handler_step, finalize_handler_step
from splunk_ao.schema.handlers import Node
from splunk_ao.utils import _get_timestamp
from splunk_ao.utils.openai_agents import (
    SplunkAOCustomSpan,
    _extract_llm_data,
    _extract_tool_data,
    _extract_workflow_data,
    _map_span_name,
    _map_span_type,
)
from splunk_ao.utils.serialization import convert_time_delta_to_ns, convert_to_string_dict, serialize_to_str

_logger = logging.getLogger(__name__)


class SplunkAOTracingProcessor(TracingProcessor):
    """
    OpenAI Agents TracingProcessor for logging traces to Splunk AO.

    Builds a tree of spans during agent execution and logs them hierarchically
    to Splunk AO upon trace completion.

    Attributes
    ----------
    _splunk_ao_logger : SplunkAOLogger
        The Splunk AO logger instance.
    _flush_on_trace_end : bool
        Whether to automatically flush the log batch to Splunk AO when a trace ends.
    _nodes : dict[str, Node]
        Stores Node objects keyed by their OpenAI span_id or trace_id (for root).
    """

    def __init__(self, splunk_ao_logger: SplunkAOLogger | None = None, flush_on_trace_end: bool = False):
        """
        OpenAI Agents TracingProcessor for logging traces to Splunk AO.

        Parameters
        ----------
        splunk_ao_logger : Optional[SplunkAOLogger]
            The Splunk AO logger instance. If None, a default instance is created.
        flush_on_trace_end : bool
            Whether to automatically flush the log batch to Splunk AO when a trace ends.
        """
        self._splunk_ao_logger: SplunkAOLogger = splunk_ao_logger or splunk_ao_context.get_logger_instance()
        self._flush_on_trace_end: bool = flush_on_trace_end
        self._nodes: dict[str, Node] = {}
        self._last_output: Any = None
        self._last_status_code: int | None = None
        self._first_input: Any = None
        self._owned_trace: Any = None
        self._owned_root: Any = None
        self._owned_root_node_id: str | None = None
        self._caller_parent: Any = None
        self._active_steps: dict[str, HandlerSpanState] = {}

    def on_trace_start(self, trace: Trace) -> None:
        """Called when an OpenAI Agent trace starts."""
        node = Node(
            node_type="agent",
            run_id=trace.trace_id,
            span_params={
                "start_time": _get_timestamp(),
                "start_time_iso": datetime.now(UTC).isoformat(),
                "name": trace.name,
                "metadata": convert_to_string_dict(trace.metadata),
            },
        )
        self._nodes[trace.trace_id] = node
        self._caller_parent = self._splunk_ao_logger.current_parent()
        if self._caller_parent is None:
            try:
                self._owned_trace = self._splunk_ao_logger.start_trace(
                    input="Agent Workflow",
                    name="Trace",
                    created_at=datetime.fromisoformat(node.span_params["start_time_iso"]),
                )
            except Exception:
                self._owned_trace = None
                _logger.warning("Failed to start OpenAI Agents trace telemetry", exc_info=True)

    def on_trace_end(self, trace: Trace) -> None:
        """Called when an OpenAI Agent trace ends."""
        node = self._nodes.get(trace.trace_id)
        if not node:
            _logger.warning(f"End called for unknown trace_id {trace.trace_id}")
            return

        node.span_params["duration_ns"] = convert_time_delta_to_ns(_get_timestamp() - node.span_params["start_time"])

        try:
            self._commit_trace(trace)
            if self._flush_on_trace_end:
                self._splunk_ao_logger.flush()
        except Exception:
            self._conclude_current_trace_on_failure()
            _logger.warning("Failed to commit OpenAI Agents telemetry", exc_info=True)
        finally:
            for state in self._active_steps.values():
                self._splunk_ao_logger._restore_handler_step_context(state.activation)
                self._splunk_ao_logger._release_otel_context(state.step)
            self._nodes = {}
            self._last_output = None
            self._last_status_code = None
            self._first_input = None
            self._owned_trace = None
            self._owned_root = None
            self._owned_root_node_id = None
            self._caller_parent = None
            self._active_steps = {}

    def _commit_trace(self, trace: Trace) -> None:
        if not self._nodes:
            _logger.warning("No nodes to commit")
            return

        root_node = self._nodes.get(trace.trace_id)
        if root_node is None:
            _logger.warning(f"Root node {trace.trace_id} not found")
            return

        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            if self._active_steps:
                _logger.warning(
                    "OpenAI Agents trace %s ended with %d unfinished callback spans",
                    trace.trace_id,
                    len(self._active_steps),
                )
            if self._owned_trace is not None:
                self._owned_trace.input = self._first_input or "Agent Workflow"
                self._owned_trace.metrics.duration_ns = root_node.span_params.get("duration_ns")
                if self._splunk_ao_logger.current_parent() is self._owned_trace:
                    self._splunk_ao_logger.conclude(output=self._last_output, status_code=self._last_status_code)
            return

        live_root_node = self._nodes.get(self._owned_root_node_id) if self._owned_root_node_id else None
        if self._owned_trace is not None and self._owned_root is not None and live_root_node is not None:
            self._owned_trace.input = self._first_input or "Agent Workflow"
            self._owned_trace.metrics.duration_ns = root_node.span_params.get("duration_ns")
            self._update_owned_root(live_root_node)
            self._log_node_tree(live_root_node, reuse_current=True)
            for child_id in root_node.children:
                if child_id == self._owned_root_node_id:
                    continue
                child = self._nodes.get(child_id)
                if child is not None:
                    self._log_node_tree(child)
            self._splunk_ao_logger.conclude(output=self._last_output, status_code=self._last_status_code)
            return

        # A caller-owned operation remains current; log framework operations
        # beneath it without ever concluding the caller's parent.
        for child_id in root_node.children:
            child = self._nodes.get(child_id)
            if child is not None:
                self._log_node_tree(child)

        if self._owned_trace is not None:
            self._splunk_ao_logger.conclude(output=self._last_output, status_code=self._last_status_code)

    def _conclude_current_trace_on_failure(self) -> None:
        if self._owned_trace is None:
            return

        current_parent = self._splunk_ao_logger.current_parent()
        if current_parent is None:
            return

        root = current_parent
        while root._parent is not None:
            root = root._parent
        if root is self._owned_trace:
            self._splunk_ao_logger.conclude(output="", status_code=500, conclude_all=True)

    def _log_node_tree(self, node: Node, reuse_current: bool = False) -> None:
        """
        Log a node and its children recursively.

        Parameters
        ----------
        node : Node
            The node to log.
        reuse_current : bool
            Whether this node is the live root already created at span start.
        """
        is_workflow_span = False
        input = node.span_params.get("input", "")
        output = node.span_params.get("output", "")
        name = node.span_params.get("name")
        metadata = node.span_params.get("metadata")
        tags = node.span_params.get("tags")
        start_time_iso = datetime.fromisoformat(node.span_params.get("start_time_iso", ""))

        # Convert metadata to a dict[str, str]
        if metadata is not None:
            metadata = convert_to_string_dict(metadata)
        # Log the current node based on its type
        if node.node_type in ("agent", "chain", "workflow"):
            if not reuse_current:
                self._splunk_ao_logger.add_workflow_span(
                    input=input or node.node_type.capitalize() + " Step",
                    output=output,
                    name=name,
                    metadata=metadata,
                    tags=tags,
                    created_at=start_time_iso,
                    duration_ns=node.span_params.get("duration_ns"),
                )
            is_workflow_span = True
        elif node.node_type in ("llm", "chat"):
            tools = node.span_params.get("tools")

            span = LlmSpan(
                input=input,
                output=output,
                name=name or "LLM Span",
                created_at=start_time_iso,
                user_metadata=metadata or {},
                tags=tags or [],
                metrics=LlmMetrics.model_validate(
                    {
                        "duration_ns": node.span_params.get("duration_ns"),
                        "num_input_tokens": node.span_params.get("num_input_tokens"),
                        "num_output_tokens": node.span_params.get("num_output_tokens"),
                        "num_total_tokens": node.span_params.get("num_total_tokens"),
                        "time_to_first_token_ns": node.span_params.get("time_to_first_token_ns"),
                        "num_reasoning_tokens": node.span_params.get("num_reasoning_tokens"),
                        "num_cached_input_tokens": node.span_params.get("num_cached_input_tokens"),
                    }
                ),
                tools=tools,
                model=node.span_params.get(
                    "model", node.span_params.get("metadata", {}).get("response_metadata", {}).get("model")
                ),
                temperature=node.span_params.get(
                    "temperature", node.span_params.get("metadata", {}).get("response_metadata", {}).get("temperature")
                ),
                status_code=node.span_params.get("status_code", 200),
                id=uuid.uuid4(),
            )
            self._splunk_ao_logger._add_completed_leaf(span)
        elif node.node_type == "retriever":
            self._splunk_ao_logger.add_retriever_span(
                input=input,
                output=output,
                name=name,
                metadata=metadata,
                tags=tags,
                created_at=start_time_iso,
                duration_ns=node.span_params.get("duration_ns"),
            )
        elif node.node_type == "tool":
            self._splunk_ao_logger.add_tool_span(
                input=input or node.node_type,
                output=output,
                name=name,
                metadata=metadata,
                tags=tags,
                created_at=start_time_iso,
                duration_ns=node.span_params.get("duration_ns"),
            )
        else:
            _logger.warning(f"Unknown node type: {node.node_type}")

        # Process all child nodes
        last_child = None
        for child_id in node.children:
            child_node = self._nodes.get(child_id)
            if child_node:
                self._log_node_tree(child_node)
                last_child = child_node
            else:
                _logger.warning(f"Child node {child_id} not found")

        # Conclude workflow span. Use the last child's output if necessary
        if is_workflow_span:
            output = output or (last_child.span_params.get("output", "") if last_child else "")
            error = node.span_params.get("error")
            status_code = node.span_params.get("status_code", 200)
            if error:
                output = error
                status_code = 500
            self._splunk_ao_logger.conclude(
                output=serialize_to_str(output),
                duration_ns=node.span_params.get("duration_ns"),
                status_code=status_code,
            )
            self._last_status_code = status_code
            self._last_output = output

    def _start_owned_root(self, node: Node) -> None:
        """Create the first top-level real operation while framework work is active."""
        if self._owned_trace is None or self._owned_root is not None:
            return
        if node.node_type not in ("agent", "chain", "workflow"):
            return

        metadata = node.span_params.get("metadata")
        if metadata is not None:
            metadata = convert_to_string_dict(metadata)
        self._owned_root = self._splunk_ao_logger.add_workflow_span(
            input=node.span_params.get("input") or node.node_type.capitalize() + " Step",
            name=node.span_params.get("name"),
            metadata=metadata,
            tags=node.span_params.get("tags"),
            created_at=datetime.fromisoformat(node.span_params["start_time_iso"]),
        )
        if self._owned_root is not None:
            self._owned_root_node_id = str(node.run_id)

    def _update_owned_root(self, node: Node) -> None:
        """Apply final OpenAI callback data to the already-live root."""
        if self._owned_root is None:
            return
        self._owned_root.input = node.span_params.get("input") or node.node_type.capitalize() + " Step"
        if node.span_params.get("name") is not None:
            self._owned_root.name = node.span_params["name"]
        if node.span_params.get("tags") is not None:
            self._owned_root.tags = node.span_params["tags"]
        metadata = node.span_params.get("metadata")
        if metadata is not None:
            self._owned_root.user_metadata = convert_to_string_dict(metadata)

    def _start_incremental_span(self, node: Node) -> None:
        """Create and activate one real OpenAI Agents callback span."""
        node_id = str(node.run_id)
        if node_id == self._owned_root_node_id and self._owned_root is not None:
            self._active_steps[node_id] = HandlerSpanState(step=self._owned_root, activation=None)
            return

        if str(node.parent_run_id) in self._active_steps:
            parent = self._active_steps[str(node.parent_run_id)].step
        else:
            parent = self._owned_trace or self._caller_parent
        if parent is None:
            raise RuntimeError(f"No active parent is available for OpenAI Agents span {node_id}")

        step = build_handler_step(node, openai_agents=True)
        self._splunk_ao_logger._register_handler_step(step, parent)
        activation = self._splunk_ao_logger._activate_handler_step(step)
        self._active_steps[node_id] = HandlerSpanState(step=step, activation=activation)

    def _finish_incremental_span(self, node: Node) -> None:
        """Finalize and enqueue an OpenAI Agents span at callback completion."""
        node_id = str(node.run_id)
        state = self._active_steps.get(node_id)
        if state is None:
            _logger.warning("Unable to complete OpenAI Agents span %s: no active state", node_id)
            return
        try:
            if node.node_type in ("agent", "chain", "workflow") and not node.span_params.get("output"):
                last_child = self._nodes.get(node.children[-1]) if node.children else None
                if last_child is not None:
                    node.span_params["output"] = last_child.span_params.get("output", "")
            final = finalize_handler_step(node, state, openai_agents=True)
            final = self._splunk_ao_logger._replace_handler_step(state.step, final)
            state.step = final
            if node_id == self._owned_root_node_id:
                self._owned_root = final

            self._splunk_ao_logger._restore_handler_step_context(state.activation)
            state.activation = None
            if self._splunk_ao_logger.current_parent() is final:
                self._splunk_ao_logger._set_current_parent(final._parent)
            self._splunk_ao_logger._complete_handler_step(final)
            self._active_steps.pop(node_id, None)
            self._last_output = node.span_params.get("output")
            self._last_status_code = node.span_params.get("status_code", 200)
        except Exception:
            self._splunk_ao_logger._restore_handler_step_context(state.activation)
            state.activation = None
            _logger.warning("Failed to complete OpenAI Agents span %s", node_id, exc_info=True)

    def on_span_start(self, span: Span[Any]) -> None:
        """Called when an OpenAI Agent span starts."""
        span_id = span.span_id
        trace_id = span.trace_id
        parent_id = span.parent_id or span.trace_id  # Parent is previous span or root trace

        if span_id in self._nodes:
            _logger.warning(f"Span node already exists for span_id {span_id}, overwriting...")

        # Determine span type and name
        splunk_ao_type = _map_span_type(span.span_data)
        span_name = _map_span_name(span)

        # Extract initial data based on type
        initial_params: dict[str, Any] = {
            "name": span_name,
            "start_time_iso": span.started_at or datetime.now(UTC).isoformat(),
        }
        if splunk_ao_type in ["llm", "chat"]:
            llm_data = _extract_llm_data(span.span_data)
            initial_params.update(
                {
                    "input": llm_data.get("input"),
                    "model": llm_data.get("model"),
                    "temperature": llm_data.get("temperature"),
                    "tools": llm_data.get("tools"),
                    "model_parameters": llm_data.get("model_parameters"),
                    "metadata": llm_data.get("metadata", {}),
                    "status_code": llm_data.get("status_code", 200),
                }
            )
            if not self._first_input and initial_params.get("input") != serialize_to_str(None):
                self._first_input = initial_params.get("input")
        elif splunk_ao_type == "tool":
            tool_data = _extract_tool_data(span.span_data)
            initial_params.update(
                {
                    "input": tool_data.get("input"),
                    "metadata": tool_data.get("metadata", {}),
                    "status_code": tool_data.get("status_code", 200),
                }
            )
        elif splunk_ao_type == "workflow":
            wf_data = _extract_workflow_data(span.span_data)
            initial_params.update(
                {
                    "input": wf_data.get("input"),
                    "metadata": wf_data.get("metadata", {}),
                    "status_code": wf_data.get("status_code", 200),
                }
            )
        elif splunk_ao_type == "splunk_ao_custom":
            custom_span = cast(SplunkAOCustomSpan, span.span_data)
            initial_params.update(
                {
                    "input": custom_span.span.input,
                    "output": custom_span.span.output,
                    "metadata": custom_span.span.user_metadata or {},
                    "tags": custom_span.span.tags,
                    "status_code": custom_span.span.status_code,
                }
            )
            splunk_ao_type = custom_span.span.type.value

        if splunk_ao_type == "splunk_ao_custom":
            splunk_ao_type = "workflow"

        # Create the node
        node = Node(node_type=splunk_ao_type, span_params=initial_params, run_id=span_id, parent_run_id=parent_id)
        self._nodes[span_id] = node

        # Add to parent's children list
        parent_node = self._nodes.get(parent_id)
        if not parent_node:
            _logger.warning(f"Parent node {parent_id} not found for span {span_id} in trace {trace_id}")
            return
        parent_node.children.append(span_id)
        if parent_id == trace_id:
            try:
                self._start_owned_root(node)
            except Exception:
                self._conclude_current_trace_on_failure()
                self._owned_trace = None
                self._owned_root = None
                self._owned_root_node_id = None
                _logger.warning("Failed to start OpenAI Agents root telemetry", exc_info=True)
        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            try:
                self._start_incremental_span(node)
            except Exception:
                self._conclude_current_trace_on_failure()
                _logger.warning("Failed to start OpenAI Agents span telemetry for %s", span_id, exc_info=True)

    def on_span_end(self, span: Span[Any]) -> None:
        """Called when an OpenAI Agent span ends."""
        span_id = span.span_id
        node = self._nodes.get(span_id)
        if not node:
            _logger.warning(f"End called for unknown span_id {span_id}")
            return

        node.span_params["name"] = _map_span_name(span)

        # Update node with final data
        splunk_ao_type = node.node_type
        end_params: dict[str, Any] = {"end_time_iso": span.ended_at or datetime.now(UTC).isoformat()}
        end_params["duration_ns"] = convert_time_delta_to_ns(
            datetime.fromisoformat(span.ended_at) - datetime.fromisoformat(node.span_params["start_time_iso"])
        )

        if splunk_ao_type == "llm":
            llm_data = _extract_llm_data(span.span_data)
            end_params.update(
                {
                    **llm_data,
                    "metadata": {**node.span_params.get("metadata", {}), **llm_data.get("metadata", {})},
                    "status_code": llm_data.get("status_code", node.span_params.get("status_code", 200)),
                }
            )
            # Ensure input is preserved if it wasn't available at start
            if node.span_params.get("input") is None:
                node.span_params["input"] = llm_data.get("input")
                if (
                    not self._first_input
                    and node.span_params["input"]
                    and node.span_params["input"] != serialize_to_str(None)
                ):
                    self._first_input = node.span_params["input"]

            # Extract embedded tool calls and merge with existing tool definitions
            if isinstance(span.span_data, ResponseSpanData) and span.span_data.response:
                embedded_tool_calls = self._extract_embedded_tool_calls(span.span_data.response)
                if embedded_tool_calls:
                    existing_tools = llm_data.get("tools") or []
                    if not isinstance(existing_tools, list):
                        existing_tools = []
                    end_params["tools"] = existing_tools + embedded_tool_calls

        elif splunk_ao_type == "tool":
            tool_data = _extract_tool_data(span.span_data)
            end_params.update(
                {
                    **tool_data,
                    "metadata": {**node.span_params.get("metadata", {}), **tool_data.get("metadata", {})},
                    "status_code": tool_data.get("status_code", node.span_params.get("status_code", 200)),
                }
            )
            if node.span_params.get("input") is None:
                node.span_params["input"] = tool_data.get("input")

        elif splunk_ao_type == "workflow":
            wf_data = _extract_workflow_data(span.span_data)
            end_params.update(
                {
                    **wf_data,
                    "metadata": {**node.span_params.get("metadata", {}), **wf_data.get("metadata", {})},
                    "status_code": wf_data.get("status_code", node.span_params.get("status_code", 200)),
                }
            )
            # Workflow output might only be known at the end
            if node.span_params.get("output") is None:
                node.span_params["output"] = wf_data.get("output")

        # Handle errors
        if error := span.error:
            end_params["error"] = error  # Store raw error
            end_params["status_code"] = 500  # Indicate error status
            end_params["metadata"] = {
                **end_params.get("metadata", {}),
                "error_message": error.get("message", str(error)),
                "error_type": error.get("type", type(error).__name__),
                "error_details": serialize_to_str(error.get("data")),
            }

        # Update the node's parameters
        node.span_params.update(end_params)
        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            self._finish_incremental_span(node)

    def shutdown(self) -> None:
        """Called when the application stops. Flushes any remaining logs."""
        self._splunk_ao_logger.flush()

    def force_flush(self) -> None:
        """Forces an immediate flush of all queued traces/spans."""
        self._splunk_ao_logger.flush()

    def _extract_embedded_tool_calls(self, response: Any) -> list[dict[str, Any]]:
        """Extract embedded tool calls from response.output."""
        if not response or not hasattr(response, "output"):
            return []

        output = response.output
        if not isinstance(output, list):
            return []

        tool_calls = []
        for item in output:
            if hasattr(item, "model_dump"):
                try:
                    item_dict = item.model_dump()
                except Exception:  # noqa: S112
                    continue
            elif isinstance(item, dict):
                item_dict = item
            else:
                continue

            item_type = item_dict.get("type", "")
            if item_type not in (
                "code_interpreter_call",
                "file_search_call",
                "web_search_call",
                "computer_call",
                "custom_tool_call",
            ):
                continue

            tool_call = {
                "type": "function",
                "function": {"name": self._get_tool_name_from_type(item_type)},
                "tool_call_id": item_dict.get("id") or item_dict.get("call_id"),
                "tool_call_type": item_type,
                "tool_call_input": self._extract_tool_input(item_dict, item_type),
                "tool_call_output": self._extract_tool_output(item_dict, item_type),
                "tool_call_status": item_dict.get("status", "completed"),
            }
            tool_calls.append(tool_call)

        return tool_calls

    def _get_tool_name_from_type(self, item_type: str) -> str:
        """Map OpenAI tool call type to tool name."""
        type_to_name = {
            "code_interpreter_call": "code_interpreter",
            "file_search_call": "file_search",
            "web_search_call": "web_search",
            "computer_call": "computer",
            "custom_tool_call": "custom_tool",
        }
        return type_to_name.get(item_type, item_type)

    def _extract_tool_input(self, item_dict: dict[str, Any], item_type: str) -> str:
        """Extract input from tool call item per OpenAI schema."""
        if item_type == "code_interpreter_call":
            return serialize_to_str(item_dict.get("code"))
        if item_type == "file_search_call":
            queries = item_dict.get("queries")
            return serialize_to_str(queries)
        if item_type == "web_search_call":
            action = item_dict.get("action", {})
            if isinstance(action, dict) and action.get("type") == "search":
                return serialize_to_str(action.get("query"))
            return serialize_to_str(action)
        if item_type == "custom_tool_call":
            return serialize_to_str(item_dict.get("input"))
        return serialize_to_str(item_dict.get("input") or item_dict.get("action"))

    def _extract_tool_output(self, item_dict: dict[str, Any], item_type: str) -> str:
        """Extract output from tool call item per OpenAI schema."""
        if item_type == "code_interpreter_call":
            outputs = item_dict.get("outputs")
            if outputs and isinstance(outputs, list):
                output_parts = []
                for output_item in outputs:
                    if isinstance(output_item, dict):
                        if output_item.get("type") == "logs":
                            output_parts.append(output_item.get("logs", ""))
                        elif output_item.get("type") == "image":
                            output_parts.append(output_item.get("url", ""))
                    else:
                        output_parts.append(str(output_item))
                return serialize_to_str("\n".join(output_parts) if output_parts else None)
            return serialize_to_str(None)
        if item_type == "file_search_call":
            return serialize_to_str(item_dict.get("results"))
        if item_type == "web_search_call":
            return serialize_to_str(item_dict.get("action"))
        if item_type == "custom_tool_call":
            return serialize_to_str(None)
        return serialize_to_str(item_dict.get("output") or item_dict.get("results"))

    @staticmethod
    def add_splunk_ao_custom_span(span: SplunkAOSpan) -> Span[SplunkAOCustomSpan]:
        """Add a Splunk AO custom span to the trace."""
        trace_provider = get_trace_provider()
        current_span = get_current_span()
        custom_span = SplunkAOCustomSpan(span, span.user_metadata)
        return trace_provider.create_span(custom_span, parent=current_span)
