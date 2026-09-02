import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from agents import Span, Trace, TracingProcessor
from agents.tracing import ResponseSpanData, get_current_span, get_trace_provider

from galileo_core.schemas.logging.span import LlmMetrics, LlmSpan
from galileo_core.schemas.logging.span import Span as SplunkAOSpan
from splunk_ao import SplunkAOLogger, splunk_ao_context
from splunk_ao.handlers.span_lifecycle import (
    HandlerSpanState,
    build_handler_step,
    discard_handler_step,
    finalize_handler_step,
    release_handler_steps,
)
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


@dataclass
class _OpenAITraceState:
    """Mutable lifecycle state owned by one OpenAI Agents trace."""

    nodes: dict[str, Node] = field(default_factory=dict)
    last_output: Any = None
    last_status_code: int | None = None
    first_input: Any = None
    owned_trace: Any = None
    owned_root: Any = None
    owned_root_node_id: str | None = None
    caller_parent: Any = None
    active_steps: dict[str, HandlerSpanState] = field(default_factory=dict)


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
    _trace_states : dict[str, _OpenAITraceState]
        Stores independent lifecycle state keyed by OpenAI trace ID.
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
        self._trace_states: dict[str, _OpenAITraceState] = {}
        self._state_lock = threading.RLock()

    def on_trace_start(self, trace: Trace) -> None:
        """Called when an OpenAI Agent trace starts."""
        trace_id = str(trace.trace_id)
        with self._state_lock:
            previous = self._trace_states.pop(trace_id, None)
            if previous is not None:
                release_handler_steps(self._splunk_ao_logger, previous.active_steps)
                self._conclude_current_trace_on_failure(previous)
                _logger.warning("Replacing unfinished OpenAI Agents trace state for %s", trace_id)

            node = Node(
                node_type="agent",
                run_id=cast(uuid.UUID, trace_id),
                span_params={
                    "start_time": _get_timestamp(),
                    "start_time_iso": datetime.now(UTC).isoformat(),
                    "name": trace.name,
                    "metadata": convert_to_string_dict(trace.metadata),
                },
            )
            state = _OpenAITraceState(nodes={trace_id: node})
            state.caller_parent = self._splunk_ao_logger.current_parent()
            self._trace_states[trace_id] = state
            if state.caller_parent is None:
                try:
                    state.owned_trace = self._splunk_ao_logger.start_trace(
                        input="Agent Workflow",
                        name="Trace",
                        created_at=datetime.fromisoformat(node.span_params["start_time_iso"]),
                    )
                except Exception:
                    state.owned_trace = None
                    _logger.warning("Failed to start OpenAI Agents trace telemetry", exc_info=True)

    def on_trace_end(self, trace: Trace) -> None:
        """Called when an OpenAI Agent trace ends."""
        trace_id = str(trace.trace_id)
        with self._state_lock:
            state = self._trace_states.get(trace_id)
            if state is None:
                _logger.warning("End called for unknown trace_id %s", trace_id)
                return
            node = state.nodes.get(trace_id)
            if node is None:
                _logger.warning("Root node %s is missing at trace end", trace_id)
                release_handler_steps(self._splunk_ao_logger, state.active_steps)
                self._trace_states.pop(trace_id, None)
                return

            node.span_params["duration_ns"] = convert_time_delta_to_ns(
                _get_timestamp() - node.span_params["start_time"]
            )

            try:
                if state.active_steps:
                    _logger.warning(
                        "OpenAI Agents trace %s ended with %d unfinished callback spans",
                        trace_id,
                        len(state.active_steps),
                    )
                    root_was_unfinished = state.owned_root_node_id in state.active_steps
                    release_handler_steps(self._splunk_ao_logger, state.active_steps)
                    if root_was_unfinished:
                        state.owned_root = None
                        state.owned_root_node_id = None
                self._commit_trace(trace, state)
                if self._flush_on_trace_end:
                    self._splunk_ao_logger.flush()
            except Exception:
                self._conclude_current_trace_on_failure(state)
                _logger.warning("Failed to commit OpenAI Agents telemetry", exc_info=True)
            finally:
                release_handler_steps(self._splunk_ao_logger, state.active_steps)
                self._trace_states.pop(trace_id, None)

    def _commit_trace(self, trace: Trace, state: _OpenAITraceState) -> None:
        if not state.nodes:
            _logger.warning("No nodes to commit")
            return

        trace_id = str(trace.trace_id)
        root_node = state.nodes.get(trace_id)
        if root_node is None:
            _logger.warning("Root node %s not found", trace_id)
            return

        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            if state.owned_trace is not None:
                state.owned_trace.input = state.first_input or "Agent Workflow"
                state.owned_trace.metrics.duration_ns = root_node.span_params.get("duration_ns")
                if self._splunk_ao_logger.current_parent() is state.owned_trace:
                    self._splunk_ao_logger.conclude(output=state.last_output, status_code=state.last_status_code)
            return

        live_root_node = state.nodes.get(state.owned_root_node_id) if state.owned_root_node_id else None
        if state.owned_trace is not None and state.owned_root is not None and live_root_node is not None:
            state.owned_trace.input = state.first_input or "Agent Workflow"
            state.owned_trace.metrics.duration_ns = root_node.span_params.get("duration_ns")
            self._update_owned_root(live_root_node, state)
            self._log_node_tree(live_root_node, state, reuse_current=True)
            for child_id in root_node.children:
                if child_id == state.owned_root_node_id:
                    continue
                child = state.nodes.get(child_id)
                if child is not None:
                    self._log_node_tree(child, state)
            self._splunk_ao_logger.conclude(output=state.last_output, status_code=state.last_status_code)
            return

        # A caller-owned operation remains current; log framework operations
        # beneath it without ever concluding the caller's parent.
        for child_id in root_node.children:
            child = state.nodes.get(child_id)
            if child is not None:
                self._log_node_tree(child, state)

        if state.owned_trace is not None:
            self._splunk_ao_logger.conclude(output=state.last_output, status_code=state.last_status_code)

    def _conclude_current_trace_on_failure(self, state: _OpenAITraceState) -> None:
        if state.owned_trace is None:
            return

        current_parent = self._splunk_ao_logger.current_parent()
        if current_parent is None:
            return

        root = current_parent
        while root._parent is not None:
            root = root._parent
        if root is state.owned_trace:
            self._splunk_ao_logger.conclude(output="", status_code=500, conclude_all=True)

    def _log_node_tree(self, node: Node, state: _OpenAITraceState, reuse_current: bool = False) -> None:
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
            child_node = state.nodes.get(child_id)
            if child_node:
                self._log_node_tree(child_node, state)
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
            state.last_status_code = status_code
            state.last_output = output

    def _start_owned_root(self, node: Node, state: _OpenAITraceState) -> None:
        """Create the first top-level real operation while framework work is active."""
        if state.owned_trace is None or state.owned_root is not None:
            return
        if node.node_type not in ("agent", "chain", "workflow"):
            return

        metadata = node.span_params.get("metadata")
        if metadata is not None:
            metadata = convert_to_string_dict(metadata)
        state.owned_root = self._splunk_ao_logger.add_workflow_span(
            input=node.span_params.get("input") or node.node_type.capitalize() + " Step",
            name=node.span_params.get("name"),
            metadata=metadata,
            tags=node.span_params.get("tags"),
            created_at=datetime.fromisoformat(node.span_params["start_time_iso"]),
        )
        if state.owned_root is not None:
            state.owned_root_node_id = str(node.run_id)

    def _update_owned_root(self, node: Node, state: _OpenAITraceState) -> None:
        """Apply final OpenAI callback data to the already-live root."""
        if state.owned_root is None:
            return
        state.owned_root.input = node.span_params.get("input") or node.node_type.capitalize() + " Step"
        if node.span_params.get("name") is not None:
            state.owned_root.name = node.span_params["name"]
        if node.span_params.get("tags") is not None:
            state.owned_root.tags = node.span_params["tags"]
        metadata = node.span_params.get("metadata")
        if metadata is not None:
            state.owned_root.user_metadata = convert_to_string_dict(metadata)

    def _start_incremental_span(self, node: Node, state: _OpenAITraceState) -> None:
        """Create and activate one real OpenAI Agents callback span."""
        node_id = str(node.run_id)
        if node_id == state.owned_root_node_id and state.owned_root is not None:
            state.active_steps[node_id] = HandlerSpanState(step=state.owned_root, activation=None)
            return

        if str(node.parent_run_id) in state.active_steps:
            parent = state.active_steps[str(node.parent_run_id)].step
        else:
            parent = state.owned_trace or state.caller_parent
        if parent is None:
            raise RuntimeError(f"No active parent is available for OpenAI Agents span {node_id}")

        step = build_handler_step(node, openai_agents=True)
        span_state = HandlerSpanState(step=step, activation=None)
        state.active_steps[node_id] = span_state
        try:
            self._splunk_ao_logger._register_handler_step(step, parent)
            span_state.activation = self._splunk_ao_logger._activate_handler_step(step)
        except Exception:
            discard_handler_step(self._splunk_ao_logger, state.active_steps, node_id)
            raise

    def _finish_incremental_span(self, node: Node, state: _OpenAITraceState) -> None:
        """Finalize and enqueue an OpenAI Agents span at callback completion."""
        node_id = str(node.run_id)
        span_state = state.active_steps.get(node_id)
        if span_state is None:
            _logger.warning("Unable to complete OpenAI Agents span %s: no active state", node_id)
            return
        try:
            if node.node_type in ("agent", "chain", "workflow") and not node.span_params.get("output"):
                last_child = state.nodes.get(node.children[-1]) if node.children else None
                if last_child is not None:
                    node.span_params["output"] = last_child.span_params.get("output", "")
            final = finalize_handler_step(node, span_state, openai_agents=True)
            final = self._splunk_ao_logger._replace_handler_step(span_state.step, final)
            span_state.step = final
            if node_id == state.owned_root_node_id:
                state.owned_root = final

            self._splunk_ao_logger._restore_handler_step_context(span_state.activation)
            span_state.activation = None
            if self._splunk_ao_logger.current_parent() is final:
                self._splunk_ao_logger._set_current_parent(final._parent)
            self._splunk_ao_logger._complete_handler_step(final)
            state.active_steps.pop(node_id, None)
            state.last_output = node.span_params.get("output")
            state.last_status_code = node.span_params.get("status_code", 200)
        except Exception:
            discard_handler_step(self._splunk_ao_logger, state.active_steps, node_id)
            if node_id == state.owned_root_node_id:
                self._conclude_current_trace_on_failure(state)
                state.owned_trace = None
                state.owned_root = None
                state.owned_root_node_id = None
            _logger.warning("Failed to complete OpenAI Agents span %s", node_id, exc_info=True)

    def on_span_start(self, span: Span[Any]) -> None:
        """Called when an OpenAI Agent span starts."""
        with self._state_lock:
            self._on_span_start(span)

    def _on_span_start(self, span: Span[Any]) -> None:
        """Start a span while the processor state lock is held."""
        span_id = str(span.span_id)
        trace_id = str(span.trace_id)
        parent_id = str(span.parent_id or span.trace_id)  # Parent is previous span or root trace
        state = self._trace_states.get(trace_id)
        if state is None:
            _logger.warning("Start called for span %s with unknown trace_id %s", span_id, trace_id)
            return

        if span_id in state.nodes:
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
            if not state.first_input and initial_params.get("input") != serialize_to_str(None):
                state.first_input = initial_params.get("input")
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
        node = Node(
            node_type=splunk_ao_type,
            span_params=initial_params,
            run_id=cast(uuid.UUID, span_id),
            parent_run_id=cast(uuid.UUID, parent_id),
        )
        state.nodes[span_id] = node

        # Add to parent's children list
        parent_node = state.nodes.get(parent_id)
        if not parent_node:
            _logger.warning(f"Parent node {parent_id} not found for span {span_id} in trace {trace_id}")
            return
        parent_node.children.append(span_id)
        if parent_id == trace_id:
            try:
                self._start_owned_root(node, state)
            except Exception:
                self._conclude_current_trace_on_failure(state)
                release_handler_steps(self._splunk_ao_logger, state.active_steps)
                state.owned_trace = None
                state.owned_root = None
                state.owned_root_node_id = None
                _logger.warning("Failed to start OpenAI Agents root telemetry", exc_info=True)
                return
        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            try:
                self._start_incremental_span(node, state)
            except Exception:
                discard_handler_step(self._splunk_ao_logger, state.active_steps, span_id)
                if parent_id == trace_id:
                    self._conclude_current_trace_on_failure(state)
                    release_handler_steps(self._splunk_ao_logger, state.active_steps)
                    state.owned_trace = None
                    state.owned_root = None
                    state.owned_root_node_id = None
                _logger.warning("Failed to start OpenAI Agents span telemetry for %s", span_id, exc_info=True)

    def on_span_end(self, span: Span[Any]) -> None:
        """Called when an OpenAI Agent span ends."""
        with self._state_lock:
            self._on_span_end(span)

    def _on_span_end(self, span: Span[Any]) -> None:
        """End a span while the processor state lock is held."""
        span_id = str(span.span_id)
        trace_id = str(span.trace_id)
        state = self._trace_states.get(trace_id)
        if state is None:
            _logger.warning("End called for span %s with unknown trace_id %s", span_id, trace_id)
            return
        node = state.nodes.get(span_id)
        if not node:
            _logger.warning(f"End called for unknown span_id {span_id}")
            return

        node.span_params["name"] = _map_span_name(span)

        # Update node with final data
        splunk_ao_type = node.node_type
        end_time_iso = span.ended_at or datetime.now(UTC).isoformat()
        end_params: dict[str, Any] = {"end_time_iso": end_time_iso}
        try:
            end_params["duration_ns"] = convert_time_delta_to_ns(
                datetime.fromisoformat(end_time_iso) - datetime.fromisoformat(node.span_params["start_time_iso"])
            )
        except (TypeError, ValueError):
            _logger.debug("OpenAI Agents span %s supplied an invalid timestamp", span_id)

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
                    not state.first_input
                    and node.span_params["input"]
                    and node.span_params["input"] != serialize_to_str(None)
                ):
                    state.first_input = node.span_params["input"]

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
            self._finish_incremental_span(node, state)

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
