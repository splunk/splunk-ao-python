import json
import logging
from collections.abc import Callable
from contextvars import Context, copy_context
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any
from uuid import UUID

from packaging.version import Version

from splunk_ao.handlers.base_handler import SplunkAOBaseHandler
from splunk_ao.logger import SplunkAOLogger
from splunk_ao.schema.handlers import NodeType
from splunk_ao.utils.serialization import convert_time_delta_to_ns, serialize_to_str
from splunk_ao.utils.uuid_utils import deterministic_uuid4

_logger = logging.getLogger(__name__)

# Lazy import state — crewai wraps sys.stdout/sys.stderr at import time, which
# causes pytest-xdist worker hangs.  All crewai/litellm imports are deferred to
# _resolve_crewai_imports(), called once from CrewAIEventListener.__init__.
CREWAI_AVAILABLE = False
CREWAI_EVENTS_MODULE_AVAILABLE = False
LITE_LLM_AVAILABLE = False
litellm = None
_crewai_imports_resolved = False


def _resolve_crewai_imports() -> None:
    """Import crewai and litellm on first use, populating module-level globals."""
    global CREWAI_AVAILABLE, CREWAI_EVENTS_MODULE_AVAILABLE
    global LITE_LLM_AVAILABLE, litellm, _crewai_imports_resolved

    if _crewai_imports_resolved:
        return
    _crewai_imports_resolved = True

    try:
        from crewai import __version__ as _crewai_version_str

        crewai_version = Version(_crewai_version_str)
        CREWAI_EVENTS_MODULE_AVAILABLE = Version("0.177.0") <= crewai_version

        CREWAI_AVAILABLE = True
    except ImportError:
        _logger.warning("CrewAI not available, using stubs")

    try:
        import litellm as _litellm

        litellm = _litellm
        LITE_LLM_AVAILABLE = True
    except ImportError:
        _logger.warning("LiteLLM not available, using stubs")
        litellm = None


@dataclass
class _CrewRun:
    """Callback state retained until one crew or standalone operation ends."""

    handler: SplunkAOBaseHandler
    context: Context
    tasks: set[str] = field(default_factory=set)
    agent_run_ids: dict[tuple[str, str], UUID] = field(default_factory=dict)
    active_tool_run_id: UUID | None = None
    warned: bool = False
    source: Any = None


class CrewAIEventListener:
    """
    CrewAI event listener for logging traces to the Splunk AO platform.

    Attributes
    ----------
    _handler : SplunkAOBaseHandler
        The handler for managing the trace.
    """

    def __init__(
        self,
        splunk_ao_logger: SplunkAOLogger | None = None,
        start_new_trace: bool = True,
        flush_on_crew_completed: bool = False,
    ):
        _resolve_crewai_imports()

        self._handler = SplunkAOBaseHandler(
            flush_on_chain_end=flush_on_crew_completed,
            start_new_trace=start_new_trace,
            splunk_ao_logger=splunk_ao_logger,
            integration="crewai",
        )
        self._active_tool_run_id: UUID | None = None
        self._agent_run_ids: dict[tuple[str, str], UUID] = {}
        self._crew_runs: dict[UUID, _CrewRun] = {}
        self._standalone_runs: dict[UUID, _CrewRun] = {}

        if CREWAI_AVAILABLE:
            # Register with the event bus directly instead of inheriting from
            # BaseEventListener — dynamic __bases__ assignment is rejected by
            # CPython when the deallocator differs from object's.
            try:
                if CREWAI_EVENTS_MODULE_AVAILABLE:
                    from crewai.events import crewai_event_bus  # pyright: ignore[reportMissingImports]
                else:
                    from crewai.utilities.events import crewai_event_bus  # pyright: ignore[reportMissingImports]
                self.setup_listeners(crewai_event_bus)
            except ImportError:
                _logger.warning("Could not import crewai event bus, skipping listener setup")

        if LITE_LLM_AVAILABLE and litellm is not None:
            if not litellm.success_callback:
                litellm.success_callback = []
            litellm.success_callback.append(self.lite_llm_usage_callback)

    def _on(self, event_bus: Any, event_type: type) -> Callable:
        """Use CrewAI's event loop instead of its unordered synchronous worker pool."""
        # Preserve registration for older event buses without an async event API.
        if not callable(getattr(event_bus, "aemit", None)):
            return event_bus.on(event_type)

        def register(callback: Callable[[Any, Any], None]) -> Callable:
            @wraps(callback)
            async def receive(source: Any, event: Any) -> None:
                # Lifecycle mutations cannot yield; export waiting happens afterward.
                flush_logger = self._dispatch_event(callback, source, event)
                if flush_logger is not None:
                    if flush_logger._ingestion_hook:
                        # Legacy hooks flush the whole mutable trace list. Wait for
                        # active runs and do not yield while that list is flushed.
                        if not self._crew_runs and not self._standalone_runs:
                            flush_logger.flush()
                    else:
                        await flush_logger.async_flush()

            return event_bus.on(event_type)(receive)

        return register

    def _dispatch_event(self, callback: Callable[[Any, Any], None], source: Any, event: Any) -> SplunkAOLogger | None:
        """Keep each crew's callbacks in one context, independent of delivery tasks."""
        name = callback.__name__
        run_id = self._generate_run_id(source, event)
        runs = self._crew_runs
        standalone_failure = False
        crew_id: UUID | None
        if name.startswith("on_crew_kickoff_"):
            crew_id = self._to_uuid(run_id)
        else:
            task = getattr(event, "task", None)
            agent = getattr(event, "agent", None) or getattr(task, "agent", None)
            crew = getattr(agent, "crew", None)
            crew_id = self._to_uuid(getattr(crew, "id", None))
            if crew_id is None:
                task_id = str(getattr(event, "task_id", None) or getattr(task, "id", ""))
                agent_id = str(getattr(event, "agent_id", None) or getattr(agent, "id", ""))
                matches = [
                    (registry, owner)
                    for registry in (self._crew_runs, self._standalone_runs)
                    for owner, run in registry.items()
                    if (task_id and task_id in run.tasks)
                    or (agent_id and any(key[0] == agent_id for key in run.agent_run_ids))
                ]
                if len(matches) == 1:
                    runs, crew_id = matches[0]
                elif not matches:
                    # An unlinked call is independent, even while a crew is active.
                    runs, crew_id = self._standalone_runs, self._to_uuid(run_id)
                    if crew_id not in runs and name == "on_llm_call_failed":
                        # Older failures have no call ID or messages; use only an unambiguous source.
                        owners = [
                            owner
                            for owner, run in runs.items()
                            if run.source is source
                            and run.handler._root_node is not None
                            and run.handler._root_node.node_type == NodeType.LLM.value
                        ]
                        if len(owners) == 1:
                            crew_id, standalone_failure = owners[0], True

        if crew_id is None:
            _logger.debug("Ignoring CrewAI callback without an identifiable crew: %s", name)
            return None

        is_root = (
            standalone_failure
            or name.startswith("on_crew_kickoff_")
            or (runs is self._standalone_runs and crew_id == self._to_uuid(run_id))
        )
        terminal = is_root and not name.endswith("_started")
        if is_root and name.endswith("_started") and crew_id not in runs:
            handler = self._handler
            if self._crew_runs or self._standalone_runs:
                handler = SplunkAOBaseHandler(
                    splunk_ao_logger=handler._splunk_ao_logger,
                    start_new_trace=handler._start_new_trace,
                    flush_on_chain_end=handler._flush_on_chain_end,
                    integration="crewai",
                )
            runs[crew_id] = _CrewRun(handler, copy_context(), source=source)

        run = runs.get(crew_id)
        if run is None:
            _logger.debug("Ignoring CrewAI callback without an active crew: %s", name)
            return None

        previous_handler, previous_tool, previous_agents = self._handler, self._active_tool_run_id, self._agent_run_ids
        self._handler, self._active_tool_run_id, self._agent_run_ids = (
            run.handler,
            run.active_tool_run_id,
            run.agent_run_ids,
        )
        if name == "on_task_started":
            run.tasks.add(str(getattr(getattr(event, "task", source), "id", "")))
        flush = run.handler._flush_on_chain_end
        run.handler._flush_on_chain_end = False
        try:
            run.context.run(callback, source, event)
        except Exception as exc:
            if is_root:
                # A root callback failure must not retain an unfinished invocation.
                try:
                    run.context.run(run.handler._conclude_owned_state_on_failure)
                finally:
                    run.context.run(run.handler._reset_handler_state)
                    runs.pop(crew_id, None)
                raise
            if not run.warned:
                _logger.warning(
                    "CrewAI telemetry callback %s failed (%s); continuing the crew", name, type(exc).__name__
                )
                run.warned = True
        finally:
            run.handler._flush_on_chain_end = flush
            run.active_tool_run_id = self._active_tool_run_id
            self._handler, self._active_tool_run_id, self._agent_run_ids = (
                previous_handler,
                previous_tool,
                previous_agents,
            )
            if terminal:
                runs.pop(crew_id, None)
        return run.handler._splunk_ao_logger if terminal and flush else None

    def setup_listeners(self, crewai_event_bus: Any) -> None:
        """Setup event listeners for CrewAI events."""
        if not CREWAI_AVAILABLE:
            _logger.warning("CrewAI not available, skipping event listener setup")
            return

        # Lazy-import event types — crewai is guaranteed to be in sys.modules at
        # this point because _resolve_crewai_imports() ran in __init__.
        if CREWAI_EVENTS_MODULE_AVAILABLE:
            from crewai.events.types.agent_events import (  # pyright: ignore[reportMissingImports]
                AgentExecutionCompletedEvent,
                AgentExecutionErrorEvent,
                AgentExecutionStartedEvent,
            )
            from crewai.events.types.crew_events import (  # pyright: ignore[reportMissingImports]
                CrewKickoffCompletedEvent,
                CrewKickoffFailedEvent,
                CrewKickoffStartedEvent,
            )
            from crewai.events.types.llm_events import (  # pyright: ignore[reportMissingImports]
                LLMCallCompletedEvent,
                LLMCallFailedEvent,
                LLMCallStartedEvent,
            )
            from crewai.events.types.memory_events import (  # pyright: ignore[reportMissingImports]
                MemoryQueryCompletedEvent,
                MemoryQueryFailedEvent,
                MemoryQueryStartedEvent,
                MemoryRetrievalCompletedEvent,
                MemoryRetrievalStartedEvent,
                MemorySaveCompletedEvent,
                MemorySaveFailedEvent,
                MemorySaveStartedEvent,
            )

            try:
                from crewai.events.types.memory_events import (  # pyright: ignore[reportMissingImports]
                    MemoryRetrievalFailedEvent,
                )
            except ImportError:
                MemoryRetrievalFailedEvent = None

            from crewai.events.types.task_events import (  # pyright: ignore[reportMissingImports]
                TaskCompletedEvent,
                TaskFailedEvent,
                TaskStartedEvent,
            )
            from crewai.events.types.tool_usage_events import (  # pyright: ignore[reportMissingImports]
                ToolUsageErrorEvent,
                ToolUsageFinishedEvent,
                ToolUsageStartedEvent,
            )
        else:
            from crewai.utilities.events.agent_events import (  # pyright: ignore[reportMissingImports]
                AgentExecutionCompletedEvent,
                AgentExecutionErrorEvent,
                AgentExecutionStartedEvent,
            )
            from crewai.utilities.events.crew_events import (  # pyright: ignore[reportMissingImports]
                CrewKickoffCompletedEvent,
                CrewKickoffFailedEvent,
                CrewKickoffStartedEvent,
            )
            from crewai.utilities.events.llm_events import (  # pyright: ignore[reportMissingImports]
                LLMCallCompletedEvent,
                LLMCallFailedEvent,
                LLMCallStartedEvent,
            )
            from crewai.utilities.events.task_events import (  # pyright: ignore[reportMissingImports]
                TaskCompletedEvent,
                TaskFailedEvent,
                TaskStartedEvent,
            )
            from crewai.utilities.events.tool_usage_events import (  # pyright: ignore[reportMissingImports]
                ToolUsageErrorEvent,
                ToolUsageFinishedEvent,
                ToolUsageStartedEvent,
            )

            MemoryRetrievalFailedEvent = None

        # Crew event handlers
        @self._on(crewai_event_bus, CrewKickoffStartedEvent)
        def on_crew_kickoff_started(source: Any, event: CrewKickoffStartedEvent) -> None:
            self._handle_crew_kickoff_started(source, event)

        @self._on(crewai_event_bus, CrewKickoffCompletedEvent)
        def on_crew_kickoff_completed(source: Any, event: CrewKickoffCompletedEvent) -> None:
            self._handle_crew_kickoff_completed(source, event)

        @self._on(crewai_event_bus, CrewKickoffFailedEvent)
        def on_crew_kickoff_failed(source: Any, event: CrewKickoffFailedEvent) -> None:
            self._handle_crew_kickoff_failed(source, event)

        # Agent event handlers
        @self._on(crewai_event_bus, AgentExecutionStartedEvent)
        def on_agent_execution_started(source: Any, event: AgentExecutionStartedEvent) -> None:
            self._handle_agent_execution_started(source, event)

        @self._on(crewai_event_bus, AgentExecutionCompletedEvent)
        def on_agent_execution_completed(source: Any, event: AgentExecutionCompletedEvent) -> None:
            self._handle_agent_execution_completed(source, event)

        @self._on(crewai_event_bus, AgentExecutionErrorEvent)
        def on_agent_execution_error(source: Any, event: AgentExecutionErrorEvent) -> None:
            self._handle_agent_execution_error(source, event)

        # Task event handlers
        @self._on(crewai_event_bus, TaskStartedEvent)
        def on_task_started(source: Any, event: TaskStartedEvent) -> None:
            self._handle_task_started(source, event)

        @self._on(crewai_event_bus, TaskCompletedEvent)
        def on_task_completed(source: Any, event: TaskCompletedEvent) -> None:
            self._handle_task_completed(source, event)

        @self._on(crewai_event_bus, TaskFailedEvent)
        def on_task_failed(source: Any, event: TaskFailedEvent) -> None:
            self._handle_task_failed(source, event)

        # Tool event handlers
        @self._on(crewai_event_bus, ToolUsageStartedEvent)
        def on_tool_usage_started(source: Any, event: ToolUsageStartedEvent) -> None:
            self._handle_tool_usage_started(source, event)

        @self._on(crewai_event_bus, ToolUsageFinishedEvent)
        def on_tool_usage_finished(source: Any, event: ToolUsageFinishedEvent) -> None:
            self._handle_tool_usage_finished(source, event)

        @self._on(crewai_event_bus, ToolUsageErrorEvent)
        def on_tool_usage_error(source: Any, event: ToolUsageErrorEvent) -> None:
            self._handle_tool_usage_error(source, event)

        # LLM event handlers
        @self._on(crewai_event_bus, LLMCallStartedEvent)
        def on_llm_call_started(source: Any, event: LLMCallStartedEvent) -> None:
            self._handle_llm_call_started(source, event)

        @self._on(crewai_event_bus, LLMCallCompletedEvent)
        def on_llm_call_completed(source: Any, event: LLMCallCompletedEvent) -> None:
            self._handle_llm_call_completed(source, event)

        @self._on(crewai_event_bus, LLMCallFailedEvent)
        def on_llm_call_failed(source: Any, event: LLMCallFailedEvent) -> None:
            self._handle_llm_call_failed(source, event)

        # Memory event handlers (only available in CrewAI >= 0.177.0)
        if CREWAI_EVENTS_MODULE_AVAILABLE:

            @self._on(crewai_event_bus, MemoryQueryStartedEvent)
            def on_memory_query_started(source: Any, event: MemoryQueryStartedEvent) -> None:
                self._handle_memory_query_started(source, event)

            @self._on(crewai_event_bus, MemoryQueryCompletedEvent)
            def on_memory_query_completed(source: Any, event: MemoryQueryCompletedEvent) -> None:
                self._handle_memory_query_completed(source, event)

            @self._on(crewai_event_bus, MemoryQueryFailedEvent)
            def on_memory_query_failed(source: Any, event: MemoryQueryFailedEvent) -> None:
                self._handle_memory_query_failed(source, event)

            @self._on(crewai_event_bus, MemorySaveStartedEvent)
            def on_memory_save_started(source: Any, event: MemorySaveStartedEvent) -> None:
                self._handle_memory_save_started(source, event)

            @self._on(crewai_event_bus, MemorySaveCompletedEvent)
            def on_memory_save_completed(source: Any, event: MemorySaveCompletedEvent) -> None:
                self._handle_memory_save_completed(source, event)

            @self._on(crewai_event_bus, MemorySaveFailedEvent)
            def on_memory_save_failed(source: Any, event: MemorySaveFailedEvent) -> None:
                self._handle_memory_save_failed(source, event)

            @self._on(crewai_event_bus, MemoryRetrievalStartedEvent)
            def on_memory_retrieval_started(source: Any, event: MemoryRetrievalStartedEvent) -> None:
                self._handle_memory_retrieval_started(source, event)

            @self._on(crewai_event_bus, MemoryRetrievalCompletedEvent)
            def on_memory_retrieval_completed(source: Any, event: MemoryRetrievalCompletedEvent) -> None:
                self._handle_memory_retrieval_completed(source, event)

            if MemoryRetrievalFailedEvent is not None:

                @self._on(crewai_event_bus, MemoryRetrievalFailedEvent)
                def on_memory_retrieval_failed(source: Any, event: MemoryRetrievalFailedEvent) -> None:
                    self._handle_memory_retrieval_failed(source, event)

    @staticmethod
    def _hash_to_uuid(value: str) -> UUID:
        """Hash a string to a deterministic UUID."""
        return deterministic_uuid4(value)

    def _generate_run_id(self, source: Any, event: Any) -> UUID:
        """Generate a consistent UUID for event tracing."""
        # 1. Memory event specific ID generation
        if hasattr(event, "query") and getattr(event, "type", "").startswith("memory_query"):  # Memory query events
            source_type = event.source_type if hasattr(event, "source_type") else ""
            return self._hash_to_uuid(
                f"memory_query_{event.query}_{source_type}_{getattr(event, 'agent_id', '')}_{getattr(event, 'limit', '')}_{getattr(event, 'score_threshold', '')}"
            )

        if hasattr(event, "value") and getattr(event, "type", "").startswith("memory_save"):  # Memory save events
            return self._hash_to_uuid(
                f"memory_save_{getattr(event, 'agent_id', '')}_{getattr(event, 'task_id', '')}_{getattr(event, 'agent_role', '')}"
            )

        if hasattr(event, "memory_content") or getattr(event, "type", "").startswith(
            "memory_retrieval"
        ):  # Memory retrieval events
            # Use consistent fields for all retrieval events (started/completed/failed) - exclude memory_content to ensure same ID
            return self._hash_to_uuid(
                f"memory_retrieval_{getattr(event, 'task_id', '')}_{getattr(event, 'agent_id', '')}"
            )

        # 2. event.call_id — LLM events in crewAI >= 1.0
        call_id = getattr(event, "call_id", None)
        if call_id:
            return self._hash_to_uuid(f"call_{call_id}")

        # 3. source.id — still works for Crew/Task sources
        if hasattr(source, "id") and source.id:
            return source.id

        # 4. event.messages hash — LLM fallback for crewAI < 1.0
        if hasattr(event, "messages") and event.messages is not None:
            messages = json.dumps(event.to_json().get("messages", []))
            return self._hash_to_uuid(messages)

        # 5. Tool events — use crewAI's event scope tracking for correlation (crewAI >= 1.0)
        if hasattr(event, "tool_args"):
            # crewAI < 1.0: source is a Tool instance with .id, already handled by step 3.
            # Fallback to tool_args hash for other cases.
            tool_name = getattr(event, "tool_name", "")
            if isinstance(event.tool_args, str):
                tool_args = event.tool_args
            else:
                tool_args = json.dumps(event.tool_args) if isinstance(event.tool_args, dict) else str(event.tool_args)
            agent_id = getattr(event, "agent_id", "") or ""
            return self._hash_to_uuid(f"{tool_name}_{tool_args}_{agent_id}")

        # 6. event.agent.id — Agent events in crewAI >= 1.0 (source no longer has .id)
        # Include task ID to generate unique run IDs when the same agent handles
        # multiple tasks (e.g. manager agent in hierarchical crews).
        event_agent = getattr(event, "agent", None)
        if event_agent is not None and getattr(event_agent, "id", None):
            task_id = getattr(getattr(event, "task", None), "id", "")
            return self._hash_to_uuid(f"{event_agent.id}_{task_id}")

        # 7. dict messages — lite_llm callback
        if isinstance(event, dict) and "messages" in event:
            messages = json.dumps(event["messages"])
            return self._hash_to_uuid(messages)

        # 8. Generic fallback
        return self._hash_to_uuid(
            f"{getattr(event, 'crew_name', '')}_{getattr(event, 'agent', '')}_{getattr(event, 'task', '')}"
        )

    @staticmethod
    def _event_timestamp(event: Any) -> datetime | None:
        timestamp = getattr(event, "timestamp", None)
        if not isinstance(timestamp, datetime):
            return None
        return timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)

    def _start_node(self, event: Any, **kwargs: Any) -> None:
        timestamp = self._event_timestamp(event)
        if timestamp is not None:
            existing = self._handler.get_node(kwargs["run_id"])
            kwargs["created_at"] = existing.span_params.get("created_at", timestamp) if existing else timestamp
        self._handler.start_node(**kwargs)

    def _end_node(self, event: Any, *, run_id: UUID, **kwargs: Any) -> None:
        timestamp = self._event_timestamp(event)
        node = self._handler.get_node(run_id)
        created_at = node.span_params.get("created_at") if node else None
        if timestamp is not None and isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            kwargs["duration_ns"] = max(0, convert_time_delta_to_ns(timestamp - created_at))
        self._handler.end_node(run_id=run_id, **kwargs)

    def _extract_metadata(self, event: Any) -> dict:
        """Extract metadata from event for span attributes."""
        metadata = {}
        metadata["timestamp"] = event.timestamp.isoformat()

        # Add source information
        if hasattr(event, "source_type") and event.source_type:
            metadata["source_type"] = event.source_type

        if hasattr(event, "fingerprint_metadata") and event.fingerprint_metadata:
            metadata.update(event.fingerprint_metadata)

        return metadata

    # Crew event handlers
    def _handle_crew_kickoff_started(self, source: Any, event: Any) -> None:
        """Handle crew execution start."""
        run_id = self._generate_run_id(source, event)
        crew_name = event.crew_name if hasattr(event, "crew_name") else "Crew"

        metadata = self._extract_metadata(event)
        metadata["crew_name"] = crew_name

        input = getattr(event, "inputs", {})

        self._start_node(
            event,
            node_type=NodeType.CHAIN.value,
            parent_run_id=None,  # Root node
            run_id=run_id,
            name=crew_name,
            input=serialize_to_str(input) if input else "-",
            metadata=metadata,
        )

    def _update_crew_input(self, run_id: str) -> None:
        """Update crew input with task descriptions. if input is not set."""
        nodes = self._handler.get_nodes()
        root_node = nodes.get(str(run_id))
        if not root_node:
            return

        input = root_node.span_params.get("input", "-")
        tasks = ""

        if not input or input == "-":
            tasks = "\n".join(
                [
                    str(node.span_params.get("metadata", {}).get("task_description"))
                    for node in nodes.values()
                    if node.span_params.get("metadata", {}).get("task_description")
                ]
            )
            input = f"Tasks: {tasks}" if tasks else "-"
            root_node.span_params["input"] = input

    def _handle_crew_kickoff_completed(self, source: Any, event: Any) -> None:
        """Handle crew execution completion."""
        run_id = self._generate_run_id(source, event)
        output = getattr(event, "output", {})
        self._update_crew_input(str(run_id))
        self._end_node(event, run_id=run_id, output=serialize_to_str(getattr(output, "raw", output)))
        self._agent_run_ids.clear()

    def _handle_crew_kickoff_failed(self, source: Any, event: Any) -> None:
        """Handle crew execution failure."""
        run_id = self._generate_run_id(source, event)
        metadata = self._extract_metadata(event)
        metadata["error"] = event.error

        self._end_node(event, run_id=run_id, output=f"Error: {event.error}", metadata=metadata)
        self._agent_run_ids.clear()

    # Agent event handlers
    def _handle_agent_execution_started(self, source: Any, event: Any) -> None:
        """Handle agent execution start."""
        run_id = self._generate_run_id(source, event)
        event_task = getattr(event, "task", None)
        agent_id = str(getattr(getattr(event, "agent", None), "id", ""))
        task_id = str(getattr(event_task, "id", ""))
        self._agent_run_ids[agent_id, task_id] = run_id
        parent_run_id = self._to_uuid(getattr(event_task, "id", None)) if event_task else None

        # When a delegation tool creates a temporary task, that task has no node.
        # Fall back to the active tool node so the worker agent is linked correctly.
        if parent_run_id and str(parent_run_id) not in self._handler.get_nodes() and self._active_tool_run_id:
            parent_run_id = self._active_tool_run_id
        role = "Unknown Agent"
        metadata = self._extract_metadata(event)

        if hasattr(event, "agent") and event.agent:
            if hasattr(event.agent, "role"):
                role = event.agent.role
                metadata["agent_role"] = role
            if hasattr(event.agent, "id"):
                metadata["agent_id"] = str(event.agent.id)

        if hasattr(event, "tools") and event.tools:
            metadata["available_tools"] = [str(getattr(tool, "name", tool)) for tool in event.tools]

        self._start_node(
            event,
            node_type=NodeType.AGENT.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name=role,
            input=serialize_to_str(getattr(event, "task_prompt", "-")),
            metadata=metadata,
        )

    def _handle_agent_execution_completed(self, source: Any, event: Any) -> None:
        """Handle agent execution completion."""
        run_id = self._generate_run_id(source, event)
        self._end_node(event, run_id=run_id, output=serialize_to_str(getattr(event, "output", "")))

    def _handle_agent_execution_error(self, source: Any, event: Any) -> None:
        """Handle agent execution error."""
        run_id = self._generate_run_id(source, event)
        metadata = self._extract_metadata(event)
        metadata["error"] = getattr(event, "error", "Unknown error")

        self._end_node(
            event, run_id=run_id, output=f"Error: {getattr(event, 'error', 'Unknown error')}", metadata=metadata
        )

    # Task event handlers
    def _handle_task_started(self, source: Any, event: Any) -> None:
        """Handle task start."""
        run_id = self._generate_run_id(source, event)
        task = event.task if hasattr(event, "task") else None
        task_agent = getattr(task, "agent", None) if task else None
        task_crew = getattr(task_agent, "crew", None) if task_agent else None
        parent_run_id = self._to_uuid(getattr(task_crew, "id", None)) if task_crew else None

        metadata = self._extract_metadata(event)
        if task:
            if hasattr(task, "description"):
                metadata["task_description"] = task.description
            if hasattr(task, "id"):
                metadata["task_id"] = str(task.id)

        task_name = "Unknown Task"
        if task and hasattr(task, "description"):
            # Use first 50 chars of description as name
            task_name = task.description[:50] + "..." if len(task.description) > 50 else task.description

        input = getattr(event, "context", "")
        if not input:
            input = task.description if task and hasattr(task, "description") else ""

        self._start_node(
            event,
            node_type=NodeType.CHAIN.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name=task_name,
            input=serialize_to_str(input) if input else "-",
            metadata=metadata,
        )

    def _handle_task_completed(self, source: Any, event: Any) -> None:
        """Handle task completion."""
        run_id = self._generate_run_id(source, event)
        output = ""
        if hasattr(event, "output") and event.output:
            output = event.output.raw if hasattr(event.output, "raw") else str(event.output)

        self._end_node(event, run_id=run_id, output=serialize_to_str(output))

    def _handle_task_failed(self, source: Any, event: Any) -> None:
        """Handle task failure."""
        run_id = self._generate_run_id(source, event)
        metadata = self._extract_metadata(event)
        metadata["error"] = event.error

        self._end_node(event, run_id=run_id, output=f"Error: {event.error}", metadata=metadata)

    # Tool event handlers
    def _handle_tool_usage_started(self, source: Any, event: Any) -> None:
        """Handle tool usage start."""
        run_id = self._generate_run_id(source, event)
        # Compute parent using the same hash as _generate_run_id step 6
        # so the tool links to the correct agent node.
        agent_id = getattr(event, "agent_id", None) or str(getattr(getattr(event, "agent", None), "id", ""))
        task_id = getattr(event, "task_id", "")
        if agent_id and task_id:
            parent_run_id: UUID | None = self._hash_to_uuid(f"{agent_id}_{task_id}")
        else:
            event_agent = getattr(event, "agent", None)
            parent_run_id = self._to_uuid(getattr(event_agent, "id", None)) if event_agent else None
            if not parent_run_id:
                parent_run_id = self._to_uuid(getattr(event, "agent_id", None))
        input = getattr(event, "tool_args", {})
        tool_name = getattr(event, "tool_name", "Unknown Tool")

        metadata = self._extract_metadata(event)
        metadata["tool_name"] = tool_name
        if input:
            metadata["tool_args"] = str(input)

        self._start_node(
            event,
            node_type=NodeType.TOOL.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name=tool_name,
            input=serialize_to_str(input) if input else "-",
            metadata=metadata,
        )
        self._active_tool_run_id = run_id

    def _handle_tool_usage_finished(self, source: Any, event: Any) -> None:
        """Handle tool usage completion."""
        run_id = self._generate_run_id(source, event)
        self._end_node(event, run_id=run_id, output=serialize_to_str(getattr(event, "output", "")))
        self._active_tool_run_id = None

    def _handle_tool_usage_error(self, source: Any, event: Any) -> None:
        """Handle tool usage error."""
        run_id = self._generate_run_id(source, event)
        metadata = self._extract_metadata(event)
        metadata["error"] = getattr(event, "error", "Unknown error")

        self._end_node(
            event, run_id=run_id, output=f"Error: {getattr(event, 'error', 'Unknown error')}", metadata=metadata
        )
        self._active_tool_run_id = None

    def _to_uuid(self, id: str | None | UUID) -> UUID | None:
        if isinstance(id, UUID):
            return id
        if isinstance(id, str):
            try:
                return UUID(id)
            except ValueError:
                return None
        return None

    # LLM event handlers
    def _handle_llm_call_started(self, source: Any, event: Any) -> None:
        """Handle LLM call start."""
        run_id = self._generate_run_id(source, event)
        parent_run_id = self._agent_run_ids.get(
            (str(getattr(event, "agent_id", "")), str(getattr(event, "task_id", "")))
        ) or self._to_uuid(getattr(event, "agent_id", None))
        llm_name = getattr(event, "model", None) or getattr(source, "model", "Unknown Model")

        metadata = self._extract_metadata(event)
        metadata["model"] = llm_name
        if hasattr(source, "temperature"):
            metadata["temperature"] = str(source.temperature)

        self._start_node(
            event,
            node_type=NodeType.LLM.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name=llm_name,
            input=serialize_to_str(getattr(event, "messages", [])),
            model=llm_name,
            temperature=getattr(source, "temperature", None),
            metadata=metadata,
        )

    def _handle_llm_call_completed(self, source: Any, event: Any) -> None:
        """Handle LLM call completion."""
        run_id = self._generate_run_id(source, event)

        token_kwargs: dict[str, Any] = {}
        response = getattr(event, "response", None)
        if response is not None:
            usage = getattr(response, "usage", None) or (getattr(response, "model_extra", None) or {}).get("usage")
            if usage is None:
                # Fallback: some crewai/litellm versions expose usage on the source object
                usage = getattr(source, "_token_usage", None)
            if usage is not None:
                _get = usage.get if isinstance(usage, dict) else lambda k, d=0: getattr(usage, k, d)
                token_kwargs["num_input_tokens"] = _get("prompt_tokens", 0)
                token_kwargs["num_output_tokens"] = _get("completion_tokens", 0)
                token_kwargs["total_tokens"] = _get("total_tokens", 0)

        self._end_node(event, run_id=run_id, output=serialize_to_str(response or ""), **token_kwargs)

    def _handle_llm_call_failed(self, source: Any, event: Any) -> None:
        """Handle LLM call failure."""
        run_id = self._generate_run_id(source, event)
        root = self._handler._root_node
        if self._handler.get_node(run_id) is None and root is not None and root.node_type == NodeType.LLM.value:
            run_id = root.run_id
        metadata = self._extract_metadata(event)
        metadata["error"] = getattr(event, "error", "Unknown error")

        self._end_node(
            event, run_id=run_id, output=f"Error: {getattr(event, 'error', 'Unknown error')}", metadata=metadata
        )

    # Memory event handlers
    def _handle_memory_query_started(self, source: Any, event: Any) -> None:
        """Handle memory query start."""
        run_id = self._generate_run_id(source, event)
        parent_run_id = self._to_uuid(getattr(event, "agent_id", None))
        parent_node = self._handler.get_node(parent_run_id) if parent_run_id else None

        if not parent_node and parent_run_id:
            task_id = getattr(event, "task_id", None)
            if task_id:
                task_run_id = self._to_uuid(task_id)
                parent_node = self._handler.get_node(task_run_id) if task_run_id else None
                if parent_node:
                    self._start_node(
                        event,
                        node_type=NodeType.AGENT.value,
                        parent_run_id=task_run_id,
                        run_id=parent_run_id,
                        name=getattr(event, "agent_role", "Unknown Agent"),
                        input=serialize_to_str(event.query),
                    )

        metadata = self._extract_metadata(event)
        metadata["query"] = event.query
        metadata["limit"] = event.limit
        if event.score_threshold is not None:
            metadata["score_threshold"] = event.score_threshold
        if hasattr(event, "agent_role") and event.agent_role:
            metadata["agent_role"] = event.agent_role

        self._start_node(
            event,
            node_type=NodeType.RETRIEVER.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name="Memory Query",
            input=serialize_to_str(event.query),
            metadata=metadata,
        )

    def _handle_memory_query_completed(self, source: Any, event: Any) -> None:
        """Handle memory query completion."""
        run_id = self._generate_run_id(source, event)

        metadata = self._extract_metadata(event)
        metadata["query_time_ms"] = event.query_time_ms
        metadata["results_count"] = len(event.results) if hasattr(event.results, "__len__") else 0

        output = serialize_to_str(event.results) if event.results else "No results found"
        self._end_node(event, run_id=run_id, output=output, metadata=metadata)

    def _handle_memory_query_failed(self, source: Any, event: Any) -> None:
        """Handle memory query failure."""
        run_id = self._generate_run_id(source, event)

        metadata = self._extract_metadata(event)
        metadata["error"] = event.error

        self._end_node(event, run_id=run_id, output=f"Memory query failed: {event.error}", metadata=metadata)

    def _handle_memory_save_started(self, source: Any, event: Any) -> None:
        """Handle memory save start."""
        run_id = self._generate_run_id(source, event)
        parent_run_id = self._to_uuid(getattr(event, "agent_id", None))

        metadata = self._extract_metadata(event)
        if hasattr(event, "metadata") and event.metadata:
            metadata.update(event.metadata)
        if hasattr(event, "agent_role") and event.agent_role:
            metadata["agent_role"] = event.agent_role

        input_value = event.value if event.value else "Memory content"

        self._start_node(
            event,
            node_type=NodeType.CHAIN.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name="Memory Save",
            input=serialize_to_str(input_value),
            metadata=metadata,
        )

    def _handle_memory_save_completed(self, source: Any, event: Any) -> None:
        """Handle memory save completion."""
        run_id = self._generate_run_id(source, event)

        metadata = self._extract_metadata(event)
        metadata["save_time_ms"] = event.save_time_ms

        self._end_node(event, run_id=run_id, output=f"Memory saved successfully: {event.value}", metadata=metadata)

    def _handle_memory_save_failed(self, source: Any, event: Any) -> None:
        """Handle memory save failure."""
        run_id = self._generate_run_id(source, event)

        metadata = self._extract_metadata(event)
        metadata["error"] = event.error

        self._end_node(event, run_id=run_id, output=f"Memory save failed: {event.error}", metadata=metadata)

    def _handle_memory_retrieval_started(self, source: Any, event: Any) -> None:
        """Handle memory retrieval start."""
        run_id = self._generate_run_id(source, event)
        parent_run_id = self._to_uuid(getattr(event, "task_id", None))

        metadata = self._extract_metadata(event)
        if hasattr(event, "task_id") and event.task_id:
            metadata["task_id"] = event.task_id

        self._start_node(
            event,
            node_type=NodeType.CHAIN.value,
            parent_run_id=parent_run_id,
            run_id=run_id,
            name="Memory Retrieval",
            input="Retrieving relevant memories for task",
            metadata=metadata,
        )

    def _handle_memory_retrieval_completed(self, source: Any, event: Any) -> None:
        """Handle memory retrieval completion."""
        run_id = self._generate_run_id(source, event)

        metadata = self._extract_metadata(event)
        metadata["retrieval_time_ms"] = event.retrieval_time_ms

        self._end_node(event, run_id=run_id, output=serialize_to_str(event.memory_content), metadata=metadata)

    def _handle_memory_retrieval_failed(self, source: Any, event: Any) -> None:
        """Handle memory retrieval failure."""
        run_id = self._generate_run_id(source, event)

        metadata = self._extract_metadata(event)
        metadata["error"] = getattr(event, "error", "Unknown error")

        self._end_node(event, run_id=run_id, output=f"Memory retrieval failed: {metadata['error']}", metadata=metadata)

    def lite_llm_usage_callback(
        self,
        kwargs: dict,  # kwargs to completion
        completion_response: Any,  # response from completion
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        node_id = self._generate_run_id(kwargs, kwargs)

        node = self._handler.get_node(node_id)
        if node is None:
            for run in (*tuple(self._crew_runs.values()), *tuple(self._standalone_runs.values())):
                node = run.handler.get_node(node_id)
                if node is not None:
                    break
        if not node:
            _logger.debug(f"No node exists for run_id {node_id}")
            return
        usage = completion_response.model_extra["usage"]
        node.span_params["usage"] = usage.model_dump() if hasattr(usage, "model_dump") else usage
        get_usage = usage.get if isinstance(usage, dict) else lambda key, default=0: getattr(usage, key, default)
        node.span_params["num_input_tokens"] = get_usage("prompt_tokens", 0)
        node.span_params["num_output_tokens"] = get_usage("completion_tokens", 0)
        node.span_params["total_tokens"] = get_usage("total_tokens", 0)
