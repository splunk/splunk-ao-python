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
        Whether the handler owns and concludes a local trace lifecycle. An
        active W3C parent is still inherited when this is ``True``. Set it to
        ``False`` only when attaching to caller-owned active logger state.
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

        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            self._finish_incremental_node(root_node)
            if self._flush_on_chain_end:
                await self._splunk_ao_logger.async_flush()
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
                        output=serialize_to_str(root_output),
                        status_code=root_node.span_params.get("status_code"),
                    )
            elif self._start_new_trace:
                if self._owned_trace is None:
                    self._start_owned_root(root_node)
                if self._owned_trace is None:
                    return

                self.log_node_tree(root_node)
                root_output = self._root_output(root_node)
                self._conclude_owned_trace(
                    self._owned_trace,
                    output=serialize_to_str(root_output),
                    status_code=root_node.span_params.get("status_code"),
                )
            elif self._has_reusable_caller_root():
                # Preserve the pre-DTA visible tree while leaving the live
                # caller operation current and caller-owned.
                self.log_node_tree(root_node)
            else:
                _logger.warning("Unable to commit async handler telemetry: no caller-owned active operation")

            if self._flush_on_chain_end:
                await self._splunk_ao_logger.async_flush()
        except Exception:
            self._conclude_owned_state_on_failure()
            _logger.warning("Failed to commit async handler telemetry", exc_info=True)
        finally:
            self._reset_handler_state()

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

        if not getattr(self._splunk_ao_logger, "_ingestion_hook", None):
            is_root = self._root_node is node
            self._finish_incremental_node(node)
            if is_root and self._flush_on_chain_end:
                await self._splunk_ao_logger.async_flush()
            return

        # Check if this is the root node and commit if so
        root = self._root_node
        if root and node.run_id == root.run_id:
            await self.async_commit()

    async def async_start_node(
        self, node_type: NODE_TYPE, parent_run_id: UUID | None, run_id: UUID, **kwargs: Any
    ) -> Node:
        return super().start_node(node_type=node_type, parent_run_id=parent_run_id, run_id=run_id, **kwargs)
