import logging
import time
from typing import Any
from uuid import UUID

from splunk_ao.handlers.base_handler import SplunkAOBaseHandler
from splunk_ao.schema.handlers import NODE_TYPE, Node
from splunk_ao.utils.serialization import serialize_to_str

_logger = logging.getLogger(__name__)


class SplunkAOAsyncBaseHandler(SplunkAOBaseHandler):
    """
    Async Callback handler for logging traces to the Splunk AO platform.

    Attributes
    ----------
    _splunk_ao_logger : SplunkAOLogger
        The Splunk AO logger instance.
    _nodes : dict[UUID, Node]
        A dictionary of nodes, where the key is the run_id and the value is the node.
    _start_new_trace : bool
        Whether to start a new trace when a chain starts. Set this to `False` to continue using the current trace.
    _flush_on_chain_end : bool
        Whether to flush the trace when a chain ends.
    """

    async def async_commit(self) -> None:
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

        owned_trace = None
        try:
            if self._start_new_trace:
                owned_trace = self._splunk_ao_logger.start_trace(
                    input=serialize_to_str(root_node.span_params.get("input", "")),
                    name=root_node.span_params.get("name"),
                    metadata=root_node.span_params.get("metadata"),
                )

            self.log_node_tree(root_node)
            root_output = root_node.span_params.get("output", "")

            if self._start_new_trace:
                self._conclude_owned_trace(
                    owned_trace,
                    output=serialize_to_str(root_output),
                    status_code=root_node.span_params.get("status_code"),
                )

            if self._flush_on_chain_end:
                await self._splunk_ao_logger.async_flush()
        except Exception:
            if owned_trace is not None:
                self._conclude_owned_trace(owned_trace, output="", status_code=500)
            _logger.warning("Failed to commit async handler telemetry", exc_info=True)
        finally:
            self._nodes.clear()
            self._root_node = None

    async def async_end_node(self, run_id: UUID, **kwargs: Any) -> None:
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
            await self.async_commit()

    async def async_start_node(
        self, node_type: NODE_TYPE, parent_run_id: UUID | None, run_id: UUID, **kwargs: Any
    ) -> Node:
        return super().start_node(node_type=node_type, parent_run_id=parent_run_id, run_id=run_id, **kwargs)
