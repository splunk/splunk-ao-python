import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from splunk_ao import splunk_ao_context
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.schema.handlers import INTEGRATION, NODE_TYPE, Node
from splunk_ao.schema.logged import LoggedAgentSpan, LoggedWorkflowSpan
from splunk_ao.schema.trace import TracesIngestRequest
from splunk_ao.utils.serialization import convert_to_string_dict, serialize_to_str

_logger = logging.getLogger(__name__)


class SplunkAOBaseHandler:
    """
    Callback handler for logging traces to the Splunk AO platform.

    Attributes
    ----------
    _splunk_ao_logger : SplunkAOLogger
        The Splunk AO logger instance.
    _nodes : dict[UUID, Node]
        A dictionary of nodes, where the key is the run_id and the value is the node.
    _start_new_trace : bool
        Whether the handler owns and concludes a local trace lifecycle. An
        active W3C parent is still inherited when this is ``True``. Set it to
        ``False`` only when attaching to caller-owned active logger state.
    _flush_on_chain_end : bool
        Whether to flush the trace when a chain ends.
    _root_node : Optional[Node]
        The root node of the trace, if any.
    _nodes : dict[str, Node]
        A dictionary of nodes, where the key is the run_id as a string and the value is the Node object.
    _integration : INTEGRATION
        The integration type, e.g., "langchain". This is used to identify the source of the trace.
    """

    def __init__(
        self,
        integration: INTEGRATION = "langchain",
        splunk_ao_logger: SplunkAOLogger | None = None,
        start_new_trace: bool = True,
        flush_on_chain_end: bool | None = None,
        ingestion_hook: Callable[[TracesIngestRequest], None] | None = None,
    ):
        self._splunk_ao_logger: SplunkAOLogger = splunk_ao_logger or splunk_ao_context.get_logger_instance(
            ingestion_hook=ingestion_hook
        )
        if splunk_ao_logger and ingestion_hook:
            if self._splunk_ao_logger.mode == "distributed":
                raise ValueError("ingestion_hook can only be used in batch mode")
            self._splunk_ao_logger._ingestion_hook = ingestion_hook
        self._start_new_trace: bool = start_new_trace
        self._flush_on_chain_end = ingestion_hook is not None if flush_on_chain_end is None else flush_on_chain_end
        self._nodes: dict[str, Node] = {}
        self._root_node: Node | None = None
        self._integration: INTEGRATION = integration
        self._owned_trace: Any = None
        self._owned_root: Any = None
        self._owned_parent: Any = None

    def commit(self) -> None:
        """Commit the nodes to the trace using the Splunk AO Logger. Optionally flush the trace."""
        if not self._nodes:
            _logger.warning("No nodes to commit")
            return

        root = self._root_node
        if root is None:
            _logger.warning("Unable to add nodes to trace: Root node not set")
            return

        root_node = self._nodes.get(str(root.run_id))
        if root_node is None:
            _logger.warning("Unable to add nodes to trace: Root node does not exist")
            return

        try:
            if self._owned_root is not None:
                self._update_owned_root(root_node)
                self._log_node_children(root_node)
                root_output = self._root_output(root_node)
                self._splunk_ao_logger.conclude(
                    output=serialize_to_str(root_output),
                    duration_ns=root_node.span_params.get("duration_ns"),
                    status_code=root_node.span_params.get("status_code"),
                )
                if self._owned_trace is not None:
                    self._conclude_owned_trace(
                        self._owned_trace,
                        output=SplunkAOLogger._coerce_output(root_output),
                        status_code=root_node.span_params.get("status_code"),
                    )
            elif self._start_new_trace:
                if self._owned_trace is None:
                    self._start_owned_root(root_node)
                if self._owned_trace is None:
                    return

                # Leaf-only roots cannot remain active in the Path 1 logger:
                # leaf creation is an immediate completion operation. Preserve
                # the pre-DTA direct leaf topology at commit while the owned
                # envelope retains the incoming context.
                self.log_node_tree(root_node)
                root_output = self._root_output(root_node)
                self._conclude_owned_trace(
                    self._owned_trace,
                    output=SplunkAOLogger._coerce_output(root_output),
                    status_code=root_node.span_params.get("status_code"),
                )
            elif self._has_reusable_caller_root():
                # Preserve the pre-DTA visible tree: the buffered handler root
                # remains a child of the caller-owned live operation. The
                # handler concludes only that buffered subtree and returns to
                # the same caller operation.
                self.log_node_tree(root_node)
            else:
                _logger.warning("Unable to commit handler telemetry: no caller-owned active operation")

            if self._flush_on_chain_end:
                self._splunk_ao_logger.flush()
        except Exception:
            self._conclude_owned_state_on_failure()
            _logger.warning("Failed to commit handler telemetry", exc_info=True)
        finally:
            self._nodes.clear()
            self._root_node = None
            self._owned_trace = None
            self._owned_root = None
            self._owned_parent = None

    def _start_owned_root(self, root_node: Node) -> None:
        """Open the handler-owned envelope and real root at callback start."""
        if self._owned_root is not None:
            return

        if not self._start_new_trace:
            # Caller-owned mode deliberately leaves the caller's real
            # operation current for outbound W3C propagation. The buffered
            # handler root is reconstructed beneath it at commit.
            self._owned_parent = self._splunk_ao_logger.current_parent()
            return

        if self._owned_trace is None:
            self._owned_trace = self._splunk_ao_logger.start_trace(
                input=SplunkAOLogger._coerce_output(root_node.span_params.get("input", "")),
                name=root_node.span_params.get("name"),
                metadata=root_node.span_params.get("metadata"),
            )
        parent = self._owned_trace

        if parent is None:
            return
        self._owned_parent = parent

        # A leaf root is still logged at commit. There is no open Path 1 leaf
        # identity to keep active without changing its completion semantics.
        if root_node.node_type not in ("agent", "chain", "workflow"):
            return

        metadata = root_node.span_params.get("metadata")
        if metadata is not None:
            metadata = convert_to_string_dict(metadata)
        step_number = self._step_number(metadata)
        root_kwargs = {
            "input": serialize_to_str(root_node.span_params.get("input", "")),
            "name": root_node.span_params.get("name"),
            "metadata": metadata,
            "tags": root_node.span_params.get("tags"),
            "created_at": root_node.span_params.get("created_at"),
            "status_code": root_node.span_params.get("status_code"),
            "step_number": step_number,
        }
        if root_node.node_type == "agent":
            self._owned_root = self._splunk_ao_logger.add_agent_span(**root_kwargs)
        else:
            self._owned_root = self._splunk_ao_logger.add_workflow_span(**root_kwargs)

        if self._owned_root is None:
            self._conclude_owned_state_on_failure()
            self._owned_trace = None
            self._owned_parent = None

    def _update_owned_root(self, root_node: Node) -> None:
        """Apply final callback data to the live root before it is completed."""
        if self._owned_root is None:
            return
        self._sync_owned_root_kind(root_node)
        self._owned_root.input = serialize_to_str(root_node.span_params.get("input", ""))
        if root_node.span_params.get("name") is not None:
            self._owned_root.name = root_node.span_params["name"]
        if root_node.span_params.get("tags") is not None:
            self._owned_root.tags = root_node.span_params["tags"]
        metadata = root_node.span_params.get("metadata")
        if metadata is not None:
            converted_metadata = convert_to_string_dict(metadata)
            self._owned_root.user_metadata = converted_metadata
            self._owned_root.step_number = self._step_number(converted_metadata)

    @staticmethod
    def _step_number(metadata: dict[str, str] | None) -> int | None:
        """Read the LangGraph step number using the pre-DTA conversion rule."""
        if not metadata or not (value := metadata.get("langgraph_step")):
            return None
        try:
            return int(value)
        except Exception as exc:
            _logger.warning(f"Invalid step number: {value}, exception raised {exc}")
            return None

    def _sync_owned_root_kind(self, root_node: Node) -> None:
        """Preserve a late LangGraph chain-to-agent classification.

        LangGraph identifies some roots from child metadata after the root
        callback has started. Replace only the proprietary model object while
        retaining its UUID and preassigned OTel identity, so outbound W3C
        context and the eventually exported agent span remain identical.
        """
        if root_node.node_type != "agent" or not isinstance(self._owned_root, LoggedWorkflowSpan):
            return
        if self._splunk_ao_logger.current_parent() is not self._owned_root:
            return

        previous = self._owned_root
        parent = previous._parent
        if parent is None:
            return
        replacement = LoggedAgentSpan.model_validate(previous.model_dump(exclude={"type"}))
        replacement._parent = parent
        replacement.spans = previous.spans
        parent.spans = [replacement if child is previous else child for child in parent.spans]
        self._owned_root = replacement
        self._splunk_ao_logger._set_current_parent(replacement)

    def _log_node_children(self, root_node: Node) -> None:
        """Log buffered descendants beneath the already-active real root."""
        for child_id in root_node.children:
            child_node = self._nodes.get(child_id)
            if child_node is not None:
                self.log_node_tree(child_node)
            else:
                _logger.warning(f"Child node {child_id} not found")

    def _root_output(self, root_node: Node) -> Any:
        output = root_node.span_params.get("output", "")
        if output or not root_node.children:
            return output
        last_child = self._nodes.get(root_node.children[-1])
        return last_child.span_params.get("output", "") if last_child is not None else ""

    def _has_reusable_caller_root(self) -> bool:
        """Return whether start_new_trace=False has caller-owned active state."""
        return self._splunk_ao_logger.current_parent() is not None

    def _conclude_owned_state_on_failure(self) -> None:
        """Close only the handler root/envelope and return to caller state."""
        while (
            self._owned_parent is not None
            and self._splunk_ao_logger.current_parent() is not None
            and self._splunk_ao_logger.current_parent() is not self._owned_parent
        ):
            self._splunk_ao_logger.conclude(output="", status_code=500)
        if self._owned_trace is not None:
            self._conclude_owned_trace(self._owned_trace, output="", status_code=500)

    def _conclude_owned_trace(self, trace: Any, output: Any, status_code: int | None) -> None:
        current_parent = self._splunk_ao_logger.current_parent()
        root = current_parent
        while root is not None and root._parent is not None:
            root = root._parent

        if root is trace:
            self._splunk_ao_logger.conclude(output=output, status_code=status_code, conclude_all=True)

    def log_node_tree(self, node: Node) -> None:
        """
        Log a node and its children recursively.

        Parameters
        ----------
        node : Node
            The node to log.
        """
        is_span_with_children = False
        input_ = node.span_params.get("input", "")
        output = node.span_params.get("output", "")
        name = node.span_params.get("name")
        metadata = node.span_params.get("metadata", {})
        tags = node.span_params.get("tags")
        created_at = node.span_params.get("created_at")

        # Convert metadata to a dict[str, str]
        if metadata is not None:
            metadata = convert_to_string_dict(metadata)

        step_number = None
        if metadata and (metadata_step_number := metadata.get("langgraph_step")):
            try:
                step_number = int(metadata_step_number)
            except Exception as e:
                _logger.warning(f"Invalid step number: {metadata_step_number}, exception raised {e}")

        # Log the current node based on its type
        if node.node_type in ("chain", "workflow"):
            self._splunk_ao_logger.add_workflow_span(
                input=input_,
                output=output,
                name=name,
                duration_ns=node.span_params.get("duration_ns"),
                metadata=metadata,
                tags=tags,
                created_at=created_at,
                step_number=step_number,
                status_code=node.span_params.get("status_code"),
            )
            is_span_with_children = True
        elif node.node_type == "agent":
            self._splunk_ao_logger.add_agent_span(
                input=input_,
                output=output,
                name=name,
                duration_ns=node.span_params.get("duration_ns"),
                metadata=metadata,
                tags=tags,
                created_at=created_at,
                step_number=step_number,
                status_code=node.span_params.get("status_code"),
            )
            is_span_with_children = True
        elif node.node_type in ("llm", "chat"):
            self._splunk_ao_logger.add_llm_span(
                input=input_,
                output=output,
                model=node.span_params.get("model"),
                temperature=node.span_params.get("temperature"),
                tools=node.span_params.get("tools"),
                name=name,
                duration_ns=node.span_params.get("duration_ns"),
                metadata=metadata,
                tags=tags,
                num_input_tokens=node.span_params.get("num_input_tokens"),
                num_output_tokens=node.span_params.get("num_output_tokens"),
                total_tokens=node.span_params.get("total_tokens"),
                time_to_first_token_ns=node.span_params.get("time_to_first_token_ns"),
                created_at=created_at,
                step_number=step_number,
                status_code=node.span_params.get("status_code"),
            )
        elif node.node_type == "retriever":
            self._splunk_ao_logger.add_retriever_span(
                input=input_,
                output=output,
                name=name,
                duration_ns=node.span_params.get("duration_ns"),
                metadata=metadata,
                tags=tags,
                created_at=created_at,
                step_number=step_number,
            )
        elif node.node_type == "tool":
            tool_span = self._splunk_ao_logger.add_tool_span(
                input=input_,
                output=output,
                name=name,
                duration_ns=node.span_params.get("duration_ns"),
                metadata=metadata,
                tags=tags,
                created_at=created_at,
                step_number=step_number,
                tool_call_id=node.span_params.get("tool_call_id"),
                status_code=node.span_params.get("status_code"),
            )
            # If tool has children (e.g., agent-as-tool invocations), push it to parent stack
            if node.children and tool_span is not None:
                parent_before_tool = self._splunk_ao_logger.current_parent()
                tool_span._parent = parent_before_tool
                self._splunk_ao_logger._set_current_parent(tool_span)
                is_span_with_children = True
        else:
            _logger.warning(f"Unknown node type: {node.node_type}")

        # Process all child nodes
        last_child = None
        for child_id in node.children:
            child_node = self._nodes.get(child_id)
            if child_node:
                self.log_node_tree(child_node)
                last_child = child_node
            else:
                _logger.warning(f"Child node {child_id} not found")

        # Conclude parent span. Use the last child's output if necessary
        if is_span_with_children:
            output = output or (last_child.span_params.get("output", "") if last_child else "")
            self._splunk_ao_logger.conclude(
                output=serialize_to_str(output), status_code=node.span_params.get("status_code")
            )

    def start_node(self, node_type: NODE_TYPE, parent_run_id: UUID | None, run_id: UUID, **kwargs: Any) -> Node:
        """
        Start a new node in the chain.

        Parameters
        ----------
        node_type : NODE_TYPE
            The type of node.
        parent_run_id : Optional[UUID]
            The parent run ID.
        run_id : UUID
            The run ID.
        **kwargs : Any
            Additional parameters for the span.

        Returns
        -------
        Node
            The created node.
        """
        node_id = str(run_id)
        parent_node_id = str(parent_run_id) if parent_run_id else None

        if node_id in self._nodes:
            _logger.debug(f"Node already exists for run_id {run_id}, overwriting...")

        # Create new node
        node = Node(node_type=node_type, span_params=kwargs, run_id=run_id, parent_run_id=parent_run_id)

        # start_time is used to calculate duration_ns
        if "start_time" not in node.span_params:
            node.span_params["start_time"] = time.perf_counter_ns()

        if "created_at" not in node.span_params:
            node.span_params["created_at"] = datetime.now(tz=UTC)

        found_node = self._nodes.get(node_id)
        if found_node:
            _logger.debug(f"Node already exists for run_id {run_id}, overwriting...")
            self._nodes[node_id].span_params.update(**kwargs)
            self._nodes[node_id].children.extend(node.children)
            return found_node

        self._nodes[node_id] = node

        # Set as root node if needed
        if not self._root_node:
            _logger.debug(f"Setting root node to {node_id}")
            self._root_node = node
            try:
                self._start_owned_root(node)
            except Exception:
                self._conclude_owned_state_on_failure()
                self._owned_trace = None
                self._owned_root = None
                self._owned_parent = None
                _logger.warning("Failed to start handler root telemetry", exc_info=True)

        # A LangGraph child may have reclassified the existing root from a
        # chain to an agent immediately before this callback reached us.
        if self._root_node is not None:
            self._sync_owned_root_kind(self._root_node)

        # Add to parent's children if parent exists
        if parent_run_id:
            parent = self._nodes.get(str(parent_run_id))
            if parent:
                parent.children.append(node_id)
            else:
                _logger.debug(f"Parent node {parent_node_id} not found for {node_id}")

        return node

    def end_node(self, run_id: UUID, **kwargs: Any) -> None:
        """
        End a node in the chain. Commit the nodes to a trace if the run_id matches the root node.

        Parameters
        ----------
        run_id : UUID
            The run ID.
        **kwargs : Any
            Additional parameters to update the span with.
        """
        node_id = str(run_id)
        node = self._nodes.get(node_id)

        if not node:
            _logger.debug(f"No node exists for run_id {node_id}")
            return

        node.span_params["duration_ns"] = time.perf_counter_ns() - node.span_params["start_time"]

        # Update node parameters
        node.span_params.update(**kwargs)

        # Check if this is the root node and commit if so
        root = self._root_node
        if root and node.run_id == root.run_id:
            self.commit()

    def get_node(self, run_id: UUID) -> Node | None:
        """
        Get a node by its run ID.

        Parameters
        ----------
        run_id : UUID
            The run ID of the node to retrieve.

        Returns
        -------
        Optional[Node]
            The node if found, otherwise None.
        """
        return self._nodes.get(str(run_id))

    def get_nodes(self) -> dict[str, Node]:
        """
        Get all nodes.

        Returns
        -------
        dict[str, Node]
            A dictionary of all nodes.
        """
        return self._nodes
