import asyncio
import inspect
import sys
import threading
import uuid
from contextvars import copy_context
from datetime import UTC, datetime, timedelta
from types import ModuleType
from typing import Any
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan

# Skip all tests in this module on Python 3.14+ (crewai doesn't support it yet)
pytestmark = pytest.mark.skipif(sys.version_info >= (3, 14), reason="crewai does not support Python 3.14+")

from splunk_ao.handlers.crewai.handler import CrewAIEventListener  # noqa: E402
from splunk_ao.logger.logger import SplunkAOLogger  # noqa: E402
from splunk_ao.schema.handlers import NodeType  # noqa: E402
from tests.testutils.setup import (  # noqa: E402
    setup_mock_logstreams_client,
    setup_mock_projects_client,
    setup_mock_traces_client,
)


class MockEvent:
    """Mock CrewAI event for testing."""

    def __init__(self, **kwargs):
        self.timestamp = datetime.now()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_json(self) -> dict[str, Any]:
        """Convert event to JSON format."""
        result = {}
        for key, value in self.__dict__.items():
            if key != "timestamp":
                result[key] = value
        return result


class MockSource:
    """Mock source object for CrewAI events."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockTask:
    """Mock CrewAI task."""

    def __init__(self, task_id=None, description="Test task", agent=None):
        self.id = task_id or uuid.uuid4()
        self.description = description
        self.agent = agent


class MockAgent:
    """Mock CrewAI agent."""

    def __init__(self, agent_id=None, role="Test Agent", crew=None):
        self.id = agent_id or uuid.uuid4()
        self.role = role
        self.crew = crew


class MockCrew:
    """Mock CrewAI crew."""

    def __init__(self, crew_id=None, name="Test Crew"):
        self.id = crew_id or uuid.uuid4()
        self.name = name


class MockOutput:
    """Mock CrewAI output."""

    def __init__(self, raw="Test output"):
        self.raw = raw


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


@pytest.fixture
def crewai_bus():
    # Given: synchronous registrations are reversed so reverting async registration fails the regression.
    # Async listeners run without yielding, as in CrewAI's dedicated event loop.
    modules = {}
    events = {}
    for group, names in {
        "crew_events": ["CrewKickoffStartedEvent", "CrewKickoffCompletedEvent", "CrewKickoffFailedEvent"],
        "task_events": ["TaskStartedEvent", "TaskCompletedEvent", "TaskFailedEvent"],
        "agent_events": ["AgentExecutionStartedEvent", "AgentExecutionCompletedEvent", "AgentExecutionErrorEvent"],
        "llm_events": ["LLMCallStartedEvent", "LLMCallCompletedEvent", "LLMCallFailedEvent"],
        "tool_usage_events": ["ToolUsageStartedEvent", "ToolUsageFinishedEvent", "ToolUsageErrorEvent"],
    }.items():
        module = ModuleType(f"crewai.utilities.events.{group}")
        for name in names:
            events[name] = type(name, (MockEvent,), {})
            setattr(module, name, events[name])
        modules[module.__name__] = module

    callbacks = {}
    bus = Mock(spec=["on", "aemit"])

    def on(event_type):
        def register(callback):
            callbacks[event_type] = callback
            return callback

        return register

    bus.on.side_effect = on
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    with (
        patch("splunk_ao.handlers.crewai.handler._crewai_imports_resolved", True),
        patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", False),
        patch("splunk_ao.handlers.crewai.handler.LITE_LLM_AVAILABLE", False),
    ):
        listener = CrewAIEventListener(splunk_ao_logger=logger)
    with (
        patch.dict(sys.modules, modules),
        patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", True),
        patch("splunk_ao.handlers.crewai.handler.CREWAI_EVENTS_MODULE_AVAILABLE", False),
    ):
        listener.setup_listeners(bus)

    async def deliver(batch):
        pending = []
        for source, event in batch:
            callback = callbacks[type(event)]
            if inspect.iscoroutinefunction(callback):
                # Each event is delivered in a distinct task/copied context.
                pending.append(asyncio.create_task(callback(source, event)))
            else:
                pending.append((callback, source, event))
        if pending and isinstance(pending[0], tuple):
            for callback, source, event in reversed(pending):
                copy_context().run(callback, source, event)
        else:
            await asyncio.gather(*pending)

    try:
        yield listener, logger, sink, events, deliver
    finally:
        logger.terminate()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("legacy_agent_source", [False, True])
def test_crewai_event_bus_preserves_callback_order_and_context(crewai_bus, asynchronous, legacy_agent_source) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    agent = MockAgent(crew=crew)
    task = MockTask(agent=agent)
    agent_source = MockSource() if legacy_agent_source else agent

    async def run(turns):
        for turn in turns:
            call_id = f"call-{turn}"
            await deliver(
                [
                    (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={"turn": turn})),
                    (task, events["TaskStartedEvent"](task=task)),
                    (
                        agent_source,
                        events["AgentExecutionStartedEvent"](agent=agent, task=task, task_prompt="Question"),
                    ),
                    (
                        MockSource(),
                        events["LLMCallStartedEvent"](
                            call_id=call_id,
                            model="local-model",
                            agent_id=str(agent.id),
                            task_id=str(task.id),
                            messages=[],
                        ),
                    ),
                    (
                        MockSource(),
                        events["LLMCallCompletedEvent"](
                            call_id=call_id, agent_id=str(agent.id), task_id=str(task.id), response=f"Reply {turn}"
                        ),
                    ),
                    (
                        agent_source,
                        events["AgentExecutionCompletedEvent"](agent=agent, task=task, output=f"Reply {turn}"),
                    ),
                    (task, events["TaskCompletedEvent"](task=task, output=MockOutput(f"Reply {turn}"))),
                    (crew, events["CrewKickoffCompletedEvent"](output=MockOutput(f"Reply {turn}"))),
                ]
            )
            # Then: one complete tree, clean state, and no context leaked into the caller.
            spans = sink.spans[turn * 4 :]
            assert len(spans) == 4
            by_operation = {span.attributes["gen_ai.operation.name"]: span for span in spans}
            llm = by_operation["chat"]
            agent_span = by_operation["invoke_agent"]
            task_span, root = [span for span in spans if span.attributes["gen_ai.operation.name"] == "invoke_workflow"]
            assert llm.parent == agent_span.context
            assert agent_span.parent == task_span.context
            assert task_span.parent == root.context
            assert logger.current_parent() is None
            assert not trace.get_current_span().get_span_context().is_valid
            assert not listener._handler.get_nodes()
            assert not listener._handler._active_steps
            assert not listener._crew_runs

    try:
        # When: the same listener/crew is reused from sync or async application code.
        if asynchronous:
            asyncio.run(run(range(3)))
        else:
            for turn in range(3):
                asyncio.run(run([turn]))
        assert len({span.context.trace_id for span in sink.spans}) == 3
    finally:
        logger.terminate()


def test_crewai_event_bus_isolates_overlapping_crews(crewai_bus) -> None:
    # Given: two crews sharing one listener and logger, with interleaved callbacks.
    listener, logger, sink, events, deliver = crewai_bus
    crews = [MockCrew(), MockCrew()]
    agents = [MockAgent(crew=crew) for crew in crews]
    tasks = [MockTask(agent=agent) for agent in agents]
    starts, ends = [], []
    for index, (crew, agent, task) in enumerate(zip(crews, agents, tasks, strict=True)):
        starts.extend(
            [
                (crew, events["CrewKickoffStartedEvent"](crew_name=f"Crew {index}", inputs={})),
                (task, events["TaskStartedEvent"](task=task)),
                (agent, events["AgentExecutionStartedEvent"](agent=agent, task=task, task_prompt="Question")),
                (
                    MockSource(),
                    events["LLMCallStartedEvent"](
                        call_id=str(index),
                        agent_id=str(agent.id),
                        task_id=str(task.id),
                        model="local-model",
                        messages=[],
                    ),
                ),
            ]
        )
        ends.extend(
            [
                (
                    MockSource(),
                    events["LLMCallCompletedEvent"](
                        call_id=str(index), agent_id=str(agent.id), task_id=str(task.id), response="Reply"
                    ),
                ),
                (agent, events["AgentExecutionCompletedEvent"](agent=agent, task=task, output="Reply")),
                (task, events["TaskCompletedEvent"](task=task, output=MockOutput("Reply"))),
                (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
            ]
        )

    # When: both trees open before either completes.
    asyncio.run(deliver(starts + ends))

    # Then: each tree has its own trace and complete, consistent hierarchy.
    assert len(sink.spans) == 8
    roots = [span for span in sink.spans if span.parent is None]
    assert len(roots) == 2
    for root in roots:
        tree = [span for span in sink.spans if span.context.trace_id == root.context.trace_id]
        assert len(tree) == 4
        assert all(span.parent in [other.context for other in tree] for span in tree if span is not root)
    assert not listener._crew_runs
    assert not listener._handler._active_steps
    assert logger.current_parent() is None
    assert not trace.get_current_span().get_span_context().is_valid


def test_crewai_event_bus_failure_releases_unfinished_children(crewai_bus) -> None:
    # Given: a crew fails while a child is unfinished.
    listener, logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    task = MockTask(agent=MockAgent(crew=crew))
    asyncio.run(
        deliver(
            [
                (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={})),
                (task, events["TaskStartedEvent"](task=task)),
                (crew, events["CrewKickoffFailedEvent"](error="synthetic failure")),
            ]
        )
    )

    # Then: only the failed root is exported and no invocation/context remains.
    assert len(sink.spans) == 1
    assert not listener._crew_runs
    assert not listener._handler.get_nodes()
    assert not listener._handler._active_steps
    assert logger.current_parent() is None
    assert not trace.get_current_span().get_span_context().is_valid


def test_crewai_event_bus_preserves_caller_owned_context(crewai_bus) -> None:
    # Given: the application has an active operation when CrewAI emits its events.
    listener, logger, sink, events, deliver = crewai_bus
    listener._handler._start_new_trace = False
    logger.start_trace(input="Request")
    caller = logger.add_workflow_span(input="Request", name="Caller")
    caller_context = trace.get_current_span().get_span_context()
    crew = MockCrew()
    task = MockTask(agent=MockAgent(crew=crew))
    try:
        # When: callbacks finish in independent delivery tasks.
        asyncio.run(
            deliver(
                [
                    (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={})),
                    (task, events["TaskStartedEvent"](task=task)),
                    (task, events["TaskCompletedEvent"](task=task, output=MockOutput("Reply"))),
                    (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
                ]
            )
        )

        # Then: the subtree inherits the caller, and callback cleanup leaves it open.
        assert len(sink.spans) == 2
        assert sink.spans[-1].parent == caller_context
        assert logger.current_parent() is caller
        assert trace.get_current_span().get_span_context() == caller_context
        assert not listener._crew_runs
    finally:
        logger.conclude(output="Reply")
        logger.conclude(output="Reply")


def test_crewai_event_bus_inherits_native_otel_parent(crewai_bus) -> None:
    # Given: standalone handler ownership beneath a caller-owned native OTel span.
    listener, logger, sink, events, deliver = crewai_bus
    caller_context = trace.SpanContext(trace_id=123, span_id=456, is_remote=True, trace_flags=trace.TraceFlags(1))
    crew = MockCrew()
    with trace.use_span(trace.NonRecordingSpan(caller_context)):
        # When: the handler opens and concludes its own SDK trace.
        asyncio.run(
            deliver(
                [
                    (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={})),
                    (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
                ]
            )
        )

        # Then: it inherits W3C parentage and leaves the caller context active.
        assert len(sink.spans) == 1
        assert sink.spans[0].parent == caller_context
        assert trace.get_current_span().get_span_context() == caller_context
        assert logger.current_parent() is None
        assert not listener._crew_runs


def test_crewai_event_bus_callback_exception_releases_invocation(crewai_bus) -> None:
    # Given: a malformed callback fails after the crew root was activated.
    listener, logger, _sink, events, deliver = crewai_bus
    crew = MockCrew()
    asyncio.run(deliver([(crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={}))]))

    # When: processing the completion fails before it can conclude the root.
    with patch.object(listener, "_handle_crew_kickoff_completed", side_effect=ValueError("synthetic event failure")):
        with pytest.raises(ValueError, match="synthetic event failure"):
            asyncio.run(deliver([(crew, events["CrewKickoffCompletedEvent"](output=MockOutput()))]))

    # Then: no pending callback state or caller context remains.
    assert not listener._crew_runs
    assert not listener._handler.get_nodes()
    assert not listener._handler._active_steps
    assert logger.current_parent() is None
    assert not trace.get_current_span().get_span_context().is_valid


def test_crewai_event_bus_without_async_api_retains_registration(crewai_callback) -> None:
    bus = Mock(spec=["on"])
    callback = Mock()

    crewai_callback._on(bus, MockEvent)(callback)

    bus.on.assert_called_once_with(MockEvent)
    bus.on.return_value.assert_called_once_with(callback)


@pytest.mark.parametrize("phase", ["start", "end"])
def test_crewai_review_child_callback_failure_keeps_crew(crewai_bus, caplog, enable_galileo_logging, phase) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    agent = MockAgent(crew=crew)
    task = MockTask(agent=agent)
    source = MockSource()

    def llm_event(kind, call_id):
        return events[kind](
            call_id=call_id,
            task_id=str(task.id),
            agent_id=str(agent.id),
            model="local-model",
            messages=[],
            response="Reply",
        )

    async def run():
        await deliver(
            [
                (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={})),
                (task, events["TaskStartedEvent"](task=task)),
                (agent, events["AgentExecutionStartedEvent"](agent=agent, task=task)),
            ]
        )
        if phase == "end":
            await deliver([(source, llm_event("LLMCallStartedEvent", "bad"))])
        method = "_handle_llm_call_started" if phase == "start" else "_handle_llm_call_completed"
        kind = "LLMCallStartedEvent" if phase == "start" else "LLMCallCompletedEvent"
        with patch.object(listener, method, side_effect=ValueError("private event payload")):
            await deliver([(source, llm_event(kind, "bad")), (source, llm_event(kind, "bad"))])
        assert crew.id in listener._crew_runs
        await deliver(
            [
                (source, llm_event("LLMCallStartedEvent", "good")),
                (source, llm_event("LLMCallCompletedEvent", "good")),
                (agent, events["AgentExecutionCompletedEvent"](agent=agent, task=task, output="Reply")),
                (task, events["TaskCompletedEvent"](task=task, output=MockOutput("Reply"))),
                (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
            ]
        )

    asyncio.run(run())
    assert len(sink.spans) == 4
    assert len({span.context.trace_id for span in sink.spans}) == 1
    assert sink.spans[-1].status.status_code != trace.StatusCode.ERROR
    warnings = [record for record in caplog.records if record.name == "splunk_ao.handlers.crewai.handler"]
    assert len(warnings) == 1
    assert "private event payload" not in caplog.text
    assert not listener._crew_runs
    assert not listener._handler._active_steps
    assert not logger._otel_ids


@pytest.mark.parametrize("crew_active", [False, True])
def test_crewai_review_standalone_llms_keep_separate_traces(crewai_bus, crew_active) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    source = MockSource()

    async def run():
        if crew_active:
            await deliver([(crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={}))])
        for index in range(2):
            await deliver(
                [
                    (
                        source,
                        events["LLMCallStartedEvent"](call_id=f"standalone-{index}", model="local-model", messages=[]),
                    )
                ]
            )
            assert logger.current_parent() is None
            assert not trace.get_current_span().get_span_context().is_valid
        for index in range(2):
            await deliver(
                [(source, events["LLMCallCompletedEvent"](call_id=f"standalone-{index}", response=f"Reply {index}"))]
            )
        if crew_active:
            await deliver([(crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Crew reply")))])

    asyncio.run(run())
    assert len(sink.spans) == 2 + int(crew_active)
    assert all(span.parent is None for span in sink.spans)
    assert len({span.context.trace_id for span in sink.spans}) == len(sink.spans)
    assert sum(span.attributes["gen_ai.operation.name"] == "chat" for span in sink.spans) == 2
    assert not listener._crew_runs
    assert not listener._standalone_runs
    assert not logger._otel_ids


@pytest.mark.parametrize("string_id", [False, True])
def test_crewai_review_standalone_task_ids_can_be_reused(crewai_bus, string_id) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    task_id = uuid.uuid4()
    task = MockTask(task_id=str(task_id) if string_id else task_id)

    async def run():
        for _ in range(2):
            await deliver(
                [
                    (task, events["TaskStartedEvent"](task=task)),
                    (task, events["TaskCompletedEvent"](task=task, output=MockOutput("Reply"))),
                ]
            )
            assert not listener._standalone_runs
            assert logger.current_parent() is None

    asyncio.run(run())
    assert len(sink.spans) == 2
    assert all(span.parent is None for span in sink.spans)
    assert len({span.context.trace_id for span in sink.spans}) == 2
    assert not logger._otel_ids


@pytest.mark.parametrize("call_id", [None, "standalone-failure"])
def test_crewai_review_failed_standalone_llm_releases_state(crewai_bus, call_id) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    source = MockSource(model="local-model")
    correlation = {"call_id": call_id} if call_id else {}
    # CrewAI 1.6 failure events omit messages and have no call_id.
    asyncio.run(
        deliver(
            [
                (
                    source,
                    events["LLMCallStartedEvent"](
                        messages=[{"role": "user", "content": "Question"}], model="local-model", **correlation
                    ),
                ),
                (source, events["LLMCallFailedEvent"](error="synthetic failure", **correlation)),
            ]
        )
    )
    assert len(sink.spans) == 1
    assert sink.spans[0].attributes["gen_ai.operation.name"] == "chat"
    assert "synthetic failure" in sink.spans[0].attributes["gen_ai.output.messages"]
    assert not listener._standalone_runs
    assert not logger._otel_ids
    assert logger.current_parent() is None


def test_crewai_review_usage_reaches_overlapping_crews(crewai_bus) -> None:
    listener, _logger, sink, events, deliver = crewai_bus
    calls = []
    starts, ends = [], []
    for index in range(2):
        crew = MockCrew()
        agent = MockAgent(crew=crew)
        task = MockTask(agent=agent)
        source = MockSource()
        messages = [{"role": "user", "content": f"Question {index}"}]
        calls.append({"messages": messages})
        starts.extend(
            [
                (crew, events["CrewKickoffStartedEvent"](crew_name=f"Crew {index}", inputs={})),
                (task, events["TaskStartedEvent"](task=task)),
                (agent, events["AgentExecutionStartedEvent"](agent=agent, task=task)),
                (
                    source,
                    events["LLMCallStartedEvent"](
                        messages=messages, agent_id=str(agent.id), task_id=str(task.id), model="local-model"
                    ),
                ),
            ]
        )
        ends.extend(
            [
                (
                    source,
                    events["LLMCallCompletedEvent"](
                        messages=messages, agent_id=str(agent.id), task_id=str(task.id), response="Reply"
                    ),
                ),
                (agent, events["AgentExecutionCompletedEvent"](agent=agent, task=task, output="Reply")),
                (task, events["TaskCompletedEvent"](task=task, output=MockOutput("Reply"))),
                (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
            ]
        )

    async def run():
        await deliver(starts)
        for index, kwargs in enumerate(calls):
            usage = Mock(prompt_tokens=10 + index, completion_tokens=5, total_tokens=15 + index)
            usage.model_dump.return_value = {
                "prompt_tokens": 10 + index,
                "completion_tokens": 5,
                "total_tokens": 15 + index,
            }
            listener.lite_llm_usage_callback(
                kwargs, Mock(model_extra={"usage": usage}), datetime.now(UTC), datetime.now(UTC)
            )
        await deliver(ends)

    asyncio.run(run())
    chats = [span for span in sink.spans if span.attributes["gen_ai.operation.name"] == "chat"]
    assert len(sink.spans) == 8
    assert len(chats) == 2
    assert [span.attributes.get("gen_ai.usage.input_tokens") for span in chats] == [10, 11]
    assert [span.attributes.get("gen_ai.usage.output_tokens") for span in chats] == [5, 5]
    assert not listener._crew_runs


def test_crewai_review_flush_runs_off_event_loop(crewai_bus, monkeypatch) -> None:
    listener, _logger, sink, events, deliver = crewai_bus
    listener._handler._flush_on_chain_end = True
    crew = MockCrew()
    flush_threads = []
    loop_thread = threading.get_ident()

    def flush():
        flush_threads.append(threading.get_ident())
        return True

    monkeypatch.setattr(sink, "force_flush", flush)
    asyncio.run(
        deliver(
            [
                (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={})),
                (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
            ]
        )
    )
    assert len(sink.spans) == 1
    assert len(flush_threads) == 1
    assert flush_threads[0] != loop_thread
    assert listener._handler._flush_on_chain_end is True


@pytest.mark.parametrize("naive", [False, True])
def test_crewai_review_uses_original_event_times(crewai_bus, naive) -> None:
    listener, _logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    agent = MockAgent(crew=crew)
    agent_source = MockSource()
    task = MockTask(agent=agent)
    base = datetime(2020, 1, 2, tzinfo=UTC)
    event_base = base.replace(tzinfo=None) if naive else base

    def event(kind, seconds, **kwargs):
        return events[kind](timestamp=event_base + timedelta(seconds=seconds), **kwargs)

    asyncio.run(
        deliver(
            [
                (crew, event("CrewKickoffStartedEvent", 0, crew_name="Crew", inputs={})),
                (task, event("TaskStartedEvent", 1, task=task)),
                (agent_source, event("AgentExecutionStartedEvent", 2, agent=agent, task=task)),
                (
                    MockSource(),
                    event(
                        "ToolUsageStartedEvent",
                        3,
                        tool_name="lookup",
                        tool_args={},
                        agent_id=str(agent.id),
                        task_id=str(task.id),
                    ),
                ),
                (
                    MockSource(),
                    event(
                        "ToolUsageFinishedEvent",
                        3.5,
                        tool_name="lookup",
                        tool_args={},
                        agent_id=str(agent.id),
                        task_id=str(task.id),
                        output="result",
                    ),
                ),
                (
                    MockSource(),
                    event(
                        "LLMCallStartedEvent",
                        4,
                        call_id="timed",
                        model="local-model",
                        agent_id=str(agent.id),
                        task_id=str(task.id),
                        messages=[],
                    ),
                ),
                (
                    MockSource(),
                    event(
                        "LLMCallCompletedEvent",
                        5,
                        call_id="timed",
                        agent_id=str(agent.id),
                        task_id=str(task.id),
                        response="Reply",
                    ),
                ),
                (agent_source, event("AgentExecutionCompletedEvent", 6, agent=agent, task=task, output="Reply")),
                (task, event("TaskCompletedEvent", 7, task=task, output=MockOutput("Reply"))),
                (crew, event("CrewKickoffCompletedEvent", 8, output=MockOutput("Reply"))),
            ]
        )
    )
    expected = {
        "invoke_workflow Crew": (0, 8),
        "invoke_workflow Test task": (1, 7),
        "invoke_agent Test Agent": (2, 6),
        "execute_tool lookup": (3, 3.5),
        "chat local-model": (4, 5),
    }
    assert len(sink.spans) == len(expected)
    for span in sink.spans:
        start, end = expected[span.name]
        assert span.start_time == int((base + timedelta(seconds=start)).timestamp() * 1e9)
        assert span.end_time - span.start_time == int((end - start) * 1e9)
    assert not listener._crew_runs


def test_crewai_review_duplicate_events_emit_once(crewai_bus) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    task = MockTask(agent=MockAgent(crew=crew))
    crew_start = (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={}))
    start = (task, events["TaskStartedEvent"](task=task))
    end = (task, events["TaskCompletedEvent"](task=task, output=MockOutput("Reply")))
    crew_end = (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply")))
    asyncio.run(deliver([crew_start, crew_start, start, start, end, end, crew_end, crew_end]))
    assert len(sink.spans) == 2
    assert sink.spans[0].parent == sink.spans[1].context
    assert not listener._crew_runs
    assert not logger._otel_ids


@pytest.mark.parametrize("caller_owned", [False, True])
def test_crewai_review_inherits_context_across_loop_thread(crewai_bus, caller_owned) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    loop = asyncio.new_event_loop()
    ready = threading.Event()

    def serve():
        asyncio.set_event_loop(loop)
        loop.call_soon(ready.set)
        loop.run_forever()

    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    crew = MockCrew()
    remote = trace.SpanContext(123, 456, is_remote=True, trace_flags=trace.TraceFlags(1))
    try:
        assert ready.wait(timeout=5)
        with trace.use_span(trace.NonRecordingSpan(remote)):
            if caller_owned:
                listener._handler._start_new_trace = False
                logger.start_trace(input="caller")
                logger.add_workflow_span(input="caller", name="caller")
            caller = logger.current_parent()
            expected = trace.get_current_span().get_span_context()
            for _ in range(2):
                future = asyncio.run_coroutine_threadsafe(
                    deliver(
                        [
                            (crew, events["CrewKickoffStartedEvent"](crew_name="Crew", inputs={})),
                            (crew, events["CrewKickoffCompletedEvent"](output=MockOutput("Reply"))),
                        ]
                    ),
                    loop,
                )
                future.result(timeout=5)
                assert logger.current_parent() is caller
                assert trace.get_current_span().get_span_context() == expected
            assert len(sink.spans) == 2
            assert all(span.parent == expected for span in sink.spans)
            assert not listener._crew_runs
            if caller_owned:
                logger.conclude(output="Reply", conclude_all=True)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        worker.join(timeout=5)
        assert not worker.is_alive()
        loop.close()


def test_crewai_review_two_agent_turns_keep_all_twenty_one_spans(crewai_bus) -> None:
    listener, logger, sink, events, deliver = crewai_bus
    crew = MockCrew()
    agents = [MockAgent(crew=crew, role=role) for role in ("Researcher", "Reviewer")]
    tasks = [MockTask(agent=agent) for agent in agents]

    async def run():
        for turn in range(3):
            batch = [(crew, events["CrewKickoffStartedEvent"](crew_name="LocalCrew", inputs={"turn": turn}))]
            for index, (agent, task) in enumerate(zip(agents, tasks, strict=True)):
                source = MockSource()
                call = {"call_id": f"{turn}-{index}", "agent_id": str(agent.id), "task_id": str(task.id)}
                batch.extend(
                    [
                        (task, events["TaskStartedEvent"](task=task)),
                        (source, events["AgentExecutionStartedEvent"](agent=agent, task=task)),
                        (source, events["LLMCallStartedEvent"](**call, model="local-model", messages=[])),
                        (source, events["LLMCallCompletedEvent"](**call, response=f"Reply {turn}")),
                        (
                            source,
                            events["AgentExecutionCompletedEvent"](agent=agent, task=task, output=f"Reply {turn}"),
                        ),
                        (task, events["TaskCompletedEvent"](task=task, output=MockOutput(f"Reply {turn}"))),
                    ]
                )
            batch.append((crew, events["CrewKickoffCompletedEvent"](output=MockOutput(f"Reply {turn}"))))
            before = len(sink.spans)
            await deliver(batch)
            spans = sink.spans[before:]
            assert len(spans) == 7
            roots = [span for span in spans if span.parent is None]
            assert len(roots) == 1
            by_id = {span.context.span_id: span for span in spans}
            for span in spans:
                operation = span.attributes["gen_ai.operation.name"]
                if span is roots[0]:
                    assert operation == "invoke_workflow"
                elif operation == "chat":
                    assert by_id[span.parent.span_id].attributes["gen_ai.operation.name"] == "invoke_agent"
                elif operation == "invoke_agent":
                    assert by_id[span.parent.span_id].attributes["gen_ai.operation.name"] == "invoke_workflow"
                else:
                    assert span.parent == roots[0].context
            assert not listener._crew_runs
            assert not listener._standalone_runs
            assert not logger._otel_ids
            assert logger.current_parent() is None
            assert not trace.get_current_span().get_span_context().is_valid

    asyncio.run(run())
    assert len(sink.spans) == 21
    assert len({span.context.trace_id for span in sink.spans}) == 3


def test_crewai_adapter_enqueues_task_at_callback_end_without_flush() -> None:
    sink = RecordingSink()
    logger = SplunkAOLogger(project_id="project-id", agent_stream_id="stream-id", _sink=sink)
    crew_id = uuid.uuid4()
    task_id = uuid.uuid4()
    crew = MockCrew(crew_id=crew_id)
    agent = MockAgent(crew=crew)
    task = MockTask(task_id=task_id, description="Research market trends", agent=agent)
    try:
        with (
            patch("splunk_ao.handlers.crewai.handler._crewai_imports_resolved", True),
            patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", False),
            patch("splunk_ao.handlers.crewai.handler.LITE_LLM_AVAILABLE", False),
        ):
            callback = CrewAIEventListener(splunk_ao_logger=logger, start_new_trace=True, flush_on_crew_completed=False)

        callback._handle_crew_kickoff_started(
            MockSource(id=crew_id), MockEvent(crew_name="Test Crew", inputs={"question": "market trends"})
        )
        callback._handle_task_started(MockSource(id=task_id), MockEvent(task=task))

        callback._handle_task_completed(MockSource(id=task_id), MockEvent(output=MockOutput("Done")))

        assert len(sink.spans) == 1
        assert sink.spans[0].name == "invoke_workflow Research market trends"
        assert str(crew_id) in callback._handler._active_steps
        assert sink.force_flush_calls == 0

        callback._handle_crew_kickoff_completed(
            MockSource(id=crew_id), MockEvent(output=MockOutput("Crew completed successfully"))
        )

        child, root = sink.spans
        assert child.parent == root.context
        assert [span.name for span in sink.spans] == [
            "invoke_workflow Research market trends",
            "invoke_workflow Test Crew",
        ]
        assert sink.force_flush_calls == 0
    finally:
        logger.terminate()


@pytest.fixture
def mock_splunk_ao_logger():
    """Creates a mock Galileo logger for testing."""
    with (
        patch("splunk_ao.logger.logger.AgentStreams") as mock_logstreams,
        patch("splunk_ao.logger.logger.Projects") as mock_projects,
        patch("splunk_ao.logger.logger.Traces") as mock_traces_client,
    ):
        setup_mock_traces_client(mock_traces_client)
        setup_mock_projects_client(mock_projects)
        setup_mock_logstreams_client(mock_logstreams)

        from splunk_ao.logger.logger import SplunkAOLogger

        return SplunkAOLogger(project="test_project", agent_stream="test_log_stream", ingestion_hook=lambda _: None)


@pytest.fixture
def crewai_callback(mock_splunk_ao_logger):
    """Creates a CrewAIEventListener instance for testing."""
    with (
        patch("splunk_ao.handlers.crewai.handler._crewai_imports_resolved", True),
        patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", False),
        patch("splunk_ao.handlers.crewai.handler.LITE_LLM_AVAILABLE", False),
    ):
        from splunk_ao.handlers.crewai.handler import CrewAIEventListener

        return CrewAIEventListener(
            splunk_ao_logger=mock_splunk_ao_logger, start_new_trace=True, flush_on_crew_completed=False
        )


def test_initialization_with_crewai_available(mock_splunk_ao_logger) -> None:
    """Test CrewAIEventListener initialization when CrewAI is available."""
    with (
        patch("splunk_ao.handlers.crewai.handler._crewai_imports_resolved", True),
        patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", True),
        patch("splunk_ao.handlers.crewai.handler.LITE_LLM_AVAILABLE", True),
    ):
        from splunk_ao.handlers.crewai.handler import CrewAIEventListener

        callback = CrewAIEventListener(
            splunk_ao_logger=mock_splunk_ao_logger, start_new_trace=False, flush_on_crew_completed=True
        )

        assert callback._handler._splunk_ao_logger == mock_splunk_ao_logger
        assert callback._handler._start_new_trace is False
        assert callback._handler._flush_on_chain_end is True


def test_initialization_with_crewai_unavailable(mock_splunk_ao_logger) -> None:
    """Test CrewAIEventListener initialization when CrewAI is unavailable."""
    with (
        patch("splunk_ao.handlers.crewai.handler._crewai_imports_resolved", True),
        patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", False),
        patch("splunk_ao.handlers.crewai.handler.LITE_LLM_AVAILABLE", False),
    ):
        from splunk_ao.handlers.crewai.handler import CrewAIEventListener

        callback = CrewAIEventListener(splunk_ao_logger=mock_splunk_ao_logger)

        assert callback._handler._splunk_ao_logger == mock_splunk_ao_logger


def test_generate_run_id_with_source_id(crewai_callback) -> None:
    """Test UUID generation when source has an ID."""
    source_id = uuid.uuid4()
    source = MockSource(id=source_id)
    event = MockEvent()

    result = crewai_callback._generate_run_id(source, event)
    assert result == source_id


def test_generate_run_id_with_messages(crewai_callback) -> None:
    """Test UUID generation from event messages."""
    messages = [{"role": "user", "content": "test"}]
    event = MockEvent(messages=messages)
    source = MockSource()

    result = crewai_callback._generate_run_id(source, event)

    # Verify it's a valid UUID
    assert isinstance(result, uuid.UUID)

    # Verify consistency - same input should produce same UUID
    result2 = crewai_callback._generate_run_id(source, event)
    assert result == result2


def test_generate_run_id_with_tool_args_dict(crewai_callback) -> None:
    """Test UUID generation from tool args as dict."""
    tool_args = {"arg1": "value1", "arg2": "value2"}
    event = MockEvent(tool_args=tool_args)
    source = MockSource()

    result = crewai_callback._generate_run_id(source, event)
    assert isinstance(result, uuid.UUID)


def test_generate_run_id_with_tool_args_string(crewai_callback) -> None:
    """Test UUID generation from tool args as string."""
    tool_args = '{"arg1": "value1"}'
    event = MockEvent(tool_args=tool_args)
    source = MockSource()

    result = crewai_callback._generate_run_id(source, event)
    assert isinstance(result, uuid.UUID)


def test_generate_run_id_fallback(crewai_callback) -> None:
    """Test UUID generation fallback method."""
    event = MockEvent(crew_name="test_crew", agent="test_agent", task="test_task")
    source = MockSource()

    result = crewai_callback._generate_run_id(source, event)
    assert isinstance(result, uuid.UUID)


def test_extract_metadata(crewai_callback) -> None:
    """Test metadata extraction from event."""
    timestamp = datetime.now()
    event = MockEvent(
        timestamp=timestamp, source_type="test_source", fingerprint_metadata={"key1": "value1", "key2": "value2"}
    )

    metadata = crewai_callback._extract_metadata(event)

    assert metadata["timestamp"] == timestamp.isoformat()
    assert metadata["source_type"] == "test_source"
    assert metadata["key1"] == "value1"
    assert metadata["key2"] == "value2"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_crew_kickoff_started(crewai_callback, generated_id) -> None:
    """Test crew kickoff started event handling."""
    crew_id = generated_id()
    source = MockSource(id=crew_id)
    event = MockEvent(crew_name="Test Crew", inputs={"input1": "value1"})

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_crew_kickoff_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert call_args[1]["parent_run_id"] is None
        assert call_args[1]["run_id"] == crew_id
        assert call_args[1]["name"] == "Test Crew"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_crew_kickoff_started_empty_inputs(crewai_callback, generated_id) -> None:
    """Test crew kickoff started event handling."""
    crew_id = generated_id()
    source = MockSource(id=crew_id)
    event = MockEvent(crew_name="Test Crew")

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_crew_kickoff_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert call_args[1]["parent_run_id"] is None
        assert call_args[1]["run_id"] == crew_id
        assert call_args[1]["name"] == "Test Crew"
        assert call_args[1]["input"] == "-"


def test_crew_events_inherit_conversation_root_marking(crewai_callback, mock_splunk_ao_logger) -> None:
    """A root crew workflow is marked while its nested task workflow is not."""
    crew_id = uuid.uuid4()
    task_id = uuid.uuid4()
    crew = MockCrew(crew_id=crew_id)
    agent = MockAgent(crew=crew)
    task = MockTask(task_id=task_id, description="Research market trends", agent=agent)

    crewai_callback._handle_crew_kickoff_started(MockSource(id=crew_id), MockEvent(crew_name="Test Crew"))
    crewai_callback._handle_task_started(MockSource(id=task_id), MockEvent(task=task))
    crewai_callback._handle_task_completed(MockSource(id=task_id), MockEvent(output=MockOutput("Done")))
    crewai_callback._handle_crew_kickoff_completed(
        MockSource(id=crew_id), MockEvent(output=MockOutput("Crew completed successfully"))
    )

    traces = mock_splunk_ao_logger.traces
    assert len(traces) == 1
    root_span = traces[0].spans[0]
    assert root_span.conversation_root is True
    assert root_span.spans[0].conversation_root is None


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_crew_kickoff_completed(crewai_callback, generated_id) -> None:
    """Test crew kickoff completed event handling."""
    crew_id = generated_id()
    source = MockSource(id=crew_id)
    output = MockOutput(raw="Crew completed successfully")
    event = MockEvent(output=output)

    with (
        patch.object(crewai_callback._handler, "end_node") as mock_end_node,
        patch.object(crewai_callback, "_update_crew_input") as mock_update_input,
    ):
        crewai_callback._handle_crew_kickoff_completed(source, event)

        mock_update_input.assert_called_once_with(str(crew_id))
        mock_end_node.assert_called_once_with(run_id=crew_id, output="Crew completed successfully")


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_crew_kickoff_failed(crewai_callback, generated_id) -> None:
    """Test crew kickoff failed event handling."""
    crew_id = generated_id()
    source = MockSource(id=crew_id)
    event = MockEvent(error="Something went wrong")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_crew_kickoff_failed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == crew_id
        assert call_args[1]["output"] == "Error: Something went wrong"
        assert call_args[1]["metadata"]["error"] == "Something went wrong"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_agent_execution_started(crewai_callback, generated_id) -> None:
    """Test agent execution started event handling."""
    agent_id = generated_id()
    task_id = generated_id()
    crew = MockCrew()
    agent = MockAgent(agent_id=agent_id, role="Research Agent", crew=crew)
    task = MockTask(task_id=task_id, agent=agent)
    source = MockSource(id=agent_id)
    event = MockEvent(agent=agent, task=task, task_prompt="Research the topic", tools=["search_tool", "analysis_tool"])

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_agent_execution_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.AGENT.value
        assert str(call_args[1]["parent_run_id"]) == str(task_id)
        assert call_args[1]["run_id"] == agent_id
        assert call_args[1]["name"] == "Research Agent"
        assert call_args[1]["input"] == "Research the topic"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_agent_execution_started_no_input(crewai_callback, generated_id) -> None:
    """Test agent execution started event handling."""
    agent_id = generated_id()
    task_id = generated_id()
    crew = MockCrew()
    agent = MockAgent(agent_id=agent_id, role="Research Agent", crew=crew)
    task = MockTask(task_id=task_id, agent=agent)
    source = MockSource(id=agent_id)
    event = MockEvent(agent=agent, task=task, tools=["search_tool", "analysis_tool"])

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_agent_execution_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.AGENT.value
        assert str(call_args[1]["parent_run_id"]) == str(task_id)
        assert call_args[1]["run_id"] == agent_id
        assert call_args[1]["name"] == "Research Agent"
        assert call_args[1]["input"] == "-"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_agent_execution_completed(crewai_callback, generated_id) -> None:
    """Test agent execution completed event handling."""
    agent_id = generated_id()
    source = MockSource(id=agent_id)
    event = MockEvent(output="Agent task completed")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_agent_execution_completed(source, event)

        mock_end_node.assert_called_once_with(run_id=agent_id, output="Agent task completed")


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_agent_execution_error(crewai_callback, generated_id) -> None:
    """Test agent execution error event handling."""
    agent_id = generated_id()
    source = MockSource(id=agent_id)
    event = MockEvent(error="Agent failed")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_agent_execution_error(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == agent_id
        assert call_args[1]["output"] == "Error: Agent failed"
        assert call_args[1]["metadata"]["error"] == "Agent failed"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_task_started(crewai_callback, generated_id) -> None:
    """Test task started event handling."""
    task_id = generated_id()
    crew_id = generated_id()
    crew = MockCrew(crew_id=crew_id)
    agent = MockAgent(crew=crew)
    task = MockTask(task_id=task_id, description="Research market trends", agent=agent)
    source = MockSource(id=task_id)
    event = MockEvent(task=task, context="Previous research context")

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_task_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert str(call_args[1]["parent_run_id"]) == str(crew_id)
        assert call_args[1]["run_id"] == task_id
        assert call_args[1]["name"] == "Research market trends"
        assert call_args[1]["input"] == "Previous research context"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_task_started_no_context(crewai_callback, generated_id) -> None:
    """Test task started event handling."""
    task_id = generated_id()
    crew_id = generated_id()
    crew = MockCrew(crew_id=crew_id)
    agent = MockAgent(crew=crew)
    task = MockTask(task_id=task_id, description="Research market trends", agent=agent)
    source = MockSource(id=task_id)
    event = MockEvent(task=task)

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_task_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert str(call_args[1]["parent_run_id"]) == str(crew_id)
        assert call_args[1]["run_id"] == task_id
        assert call_args[1]["name"] == "Research market trends"
        assert call_args[1]["input"] == task.description


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_task_started_no_description(crewai_callback, generated_id) -> None:
    """Test task started event handling."""
    task_id = generated_id()
    crew_id = generated_id()
    crew = MockCrew(crew_id=crew_id)
    agent = MockAgent(crew=crew)
    task = MockTask(task_id=task_id, description="", agent=agent)
    source = MockSource(id=task_id)
    event = MockEvent(task=task)

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_task_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert str(call_args[1]["parent_run_id"]) == str(crew_id)
        assert call_args[1]["run_id"] == task_id
        assert call_args[1]["name"] == ""
        assert call_args[1]["input"] == "-"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_task_completed(crewai_callback, generated_id) -> None:
    """Test task completed event handling."""
    task_id = generated_id()
    source = MockSource(id=task_id)
    output = MockOutput(raw="Task completed successfully")
    event = MockEvent(output=output)

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_task_completed(source, event)

        mock_end_node.assert_called_once_with(run_id=task_id, output="Task completed successfully")


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_task_failed(crewai_callback, generated_id) -> None:
    """Test task failed event handling."""
    task_id = generated_id()
    source = MockSource(id=task_id)
    event = MockEvent(error="Task execution failed")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_task_failed(source, event)
        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == task_id
        assert call_args[1]["output"] == "Error: Task execution failed"
        assert call_args[1]["metadata"]["error"] == "Task execution failed"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_tool_usage_started(crewai_callback, generated_id) -> None:
    """Test tool usage started event handling."""
    tool_id = generated_id()
    agent_id = generated_id()
    agent = MockAgent(agent_id=agent_id)
    source = MockSource(id=tool_id)
    event = MockEvent(agent=agent, tool_name="search_tool", tool_args={"query": "market research"})

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_tool_usage_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.TOOL.value
        assert str(call_args[1]["parent_run_id"]) == str(agent_id)
        assert call_args[1]["run_id"] == tool_id
        assert call_args[1]["name"] == "search_tool"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_tool_usage_started_no_input(crewai_callback, generated_id) -> None:
    """Test tool usage started event handling."""
    tool_id = generated_id()
    agent_id = generated_id()
    agent = MockAgent(agent_id=agent_id)

    source = MockSource(id=tool_id)
    event = MockEvent(agent=agent, tool_name="search_tool")

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_tool_usage_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.TOOL.value
        assert str(call_args[1]["parent_run_id"]) == str(agent_id)
        assert call_args[1]["run_id"] == tool_id
        assert call_args[1]["name"] == "search_tool"
        assert call_args[1]["input"] == "-"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_tool_usage_finished(crewai_callback, generated_id) -> None:
    """Test tool usage finished event handling."""
    tool_id = generated_id()
    source = MockSource(id=tool_id)
    event = MockEvent(output="Tool execution completed")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_tool_usage_finished(source, event)

        mock_end_node.assert_called_once_with(run_id=tool_id, output="Tool execution completed")


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_tool_usage_error(crewai_callback, generated_id) -> None:
    """Test tool usage error event handling."""
    tool_id = generated_id()
    source = MockSource(id=tool_id)
    event = MockEvent(error="Tool execution failed")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_tool_usage_error(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == tool_id
        assert call_args[1]["output"] == "Error: Tool execution failed"
        assert call_args[1]["metadata"]["error"] == "Tool execution failed"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_llm_call_started(crewai_callback, generated_id) -> None:
    """Test LLM call started event handling."""
    llm_id = generated_id()
    source = MockSource(id=llm_id, model="gpt-4", temperature=0.7)
    event = MockEvent(agent_id=generated_id(), messages=[{"role": "user", "content": "Hello"}])

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_llm_call_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.LLM.value
        assert call_args[1]["run_id"] == llm_id
        assert call_args[1]["name"] == "gpt-4"
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.7


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_llm_call_completed(crewai_callback, generated_id) -> None:
    """Test LLM call completed event handling."""
    llm_id = generated_id()
    source = MockSource(id=llm_id)
    event = MockEvent(response="Hello! How can I help you?")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_llm_call_completed(source, event)

        mock_end_node.assert_called_once_with(run_id=llm_id, output="Hello! How can I help you?")


def test_llm_call_completed_extracts_token_usage(crewai_callback) -> None:
    """Test that LLM call completed extracts token usage from response."""
    # Given: an LLM completed event whose response carries usage data
    llm_id = uuid.uuid4()
    source = MockSource(id=llm_id)
    mock_usage = Mock(prompt_tokens=150, completion_tokens=50, total_tokens=200)
    mock_response = Mock(usage=mock_usage)
    mock_response.model_extra = {}
    event = MockEvent(response=mock_response)

    # When: the completed handler processes the event
    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_llm_call_completed(source, event)

        # Then: token usage is passed to end_node
        call_args = mock_end_node.call_args[1]
        assert call_args["num_input_tokens"] == 150
        assert call_args["num_output_tokens"] == 50
        assert call_args["total_tokens"] == 200


def test_llm_call_completed_extracts_token_usage_from_model_extra(crewai_callback) -> None:
    """Test that LLM call completed extracts token usage from model_extra when usage attr is missing."""
    # Given: a response where usage is in model_extra (litellm ModelResponse pattern)
    llm_id = uuid.uuid4()
    source = MockSource(id=llm_id)
    mock_usage = Mock(prompt_tokens=100, completion_tokens=25, total_tokens=125)
    mock_response = Mock(spec=[])  # no attributes at all
    mock_response.model_extra = {"usage": mock_usage}
    event = MockEvent(response=mock_response)

    # When: the completed handler processes the event
    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_llm_call_completed(source, event)

        # Then: token usage is extracted from model_extra
        call_args = mock_end_node.call_args[1]
        assert call_args["num_input_tokens"] == 100
        assert call_args["num_output_tokens"] == 25
        assert call_args["total_tokens"] == 125


def test_llm_call_completed_extracts_token_usage_from_source(crewai_callback) -> None:
    """Test that LLM call completed falls back to source._token_usage dict."""
    # Given: a response with no usage, but source carries _token_usage as a dict
    llm_id = uuid.uuid4()
    source = MockSource(id=llm_id, _token_usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100})
    mock_response = Mock(spec=[], usage=None)
    mock_response.model_extra = {}
    event = MockEvent(response=mock_response)

    # When: the completed handler processes the event
    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_llm_call_completed(source, event)

        # Then: token usage is extracted from source._token_usage
        call_args = mock_end_node.call_args[1]
        assert call_args["num_input_tokens"] == 80
        assert call_args["num_output_tokens"] == 20
        assert call_args["total_tokens"] == 100


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_llm_call_failed(crewai_callback, generated_id) -> None:
    """Test LLM call failed event handling."""
    llm_id = generated_id()
    source = MockSource(id=llm_id)
    event = MockEvent(error="Rate limit exceeded")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_llm_call_failed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == llm_id
        assert call_args[1]["output"] == "Error: Rate limit exceeded"
        assert call_args[1]["metadata"]["error"] == "Rate limit exceeded"


def test_setup_listeners_crewai_unavailable(crewai_callback: CrewAIEventListener) -> None:
    """Test setup_listeners when CrewAI is unavailable."""
    mock_event_bus = Mock()

    with patch("splunk_ao.handlers.crewai.handler.CREWAI_AVAILABLE", False):
        crewai_callback.setup_listeners(mock_event_bus)

        # Verify that no event listeners were registered
        mock_event_bus.on.assert_not_called()


def test_update_crew_input(crewai_callback: CrewAIEventListener) -> None:
    """Test crew input update functionality."""
    crew_id = uuid.uuid4()

    # Mock nodes with task descriptions
    mock_root_node = Mock()
    mock_root_node.span_params = {"input": "-"}

    mock_task_node = Mock()
    mock_task_node.span_params = {"metadata": {"task_description": "Research market trends"}}

    mock_nodes = {str(crew_id): mock_root_node, "task1": mock_task_node}

    with patch.object(crewai_callback._handler, "get_nodes", return_value=mock_nodes):
        crewai_callback._update_crew_input(str(crew_id))

        # Verify input was updated with task descriptions
        assert "Research market trends" in mock_root_node.span_params["input"]


def test_lite_llm_usage_callback(crewai_callback: CrewAIEventListener) -> None:
    """Test LiteLLM usage callback."""
    node_id = uuid.uuid4()

    # Mock node
    mock_node = Mock()
    mock_node.span_params = {}

    # Mock completion response with usage
    mock_usage = Mock()
    mock_usage.model_dump.return_value = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150

    mock_response = Mock()
    mock_response.model_extra = {"usage": mock_usage}

    kwargs = {"messages": [{"role": "user", "content": "test"}]}

    with (
        patch.object(crewai_callback._handler, "get_node", return_value=mock_node),
        patch.object(crewai_callback, "_generate_run_id", return_value=node_id),
    ):
        crewai_callback.lite_llm_usage_callback(
            kwargs=kwargs, completion_response=mock_response, start_time=datetime.now(), end_time=datetime.now()
        )

        # Verify usage was recorded
        assert mock_node.span_params["num_input_tokens"] == 100
        assert mock_node.span_params["num_output_tokens"] == 50
        assert mock_node.span_params["total_tokens"] == 150


def test_lite_llm_usage_callback_no_node(crewai_callback) -> None:
    """Test LiteLLM usage callback when node doesn't exist."""
    kwargs = {"messages": [{"role": "user", "content": "test"}]}
    mock_response = Mock()

    with (
        patch.object(crewai_callback._handler, "get_node", return_value=None),
        patch.object(crewai_callback, "_generate_run_id", return_value=uuid.uuid4()),
    ):
        # Should not raise an exception
        crewai_callback.lite_llm_usage_callback(
            kwargs=kwargs, completion_response=mock_response, start_time=datetime.now(), end_time=datetime.now()
        )


# Memory event tests (for CrewAI >= 0.177.0)


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_query_started(crewai_callback, generated_id) -> None:
    """Test memory query started event handling."""
    query_id = generated_id()
    agent_id = generated_id()
    source = MockSource(id=query_id)
    event = MockEvent(
        query="What are the market trends?",
        limit=10,
        score_threshold=0.8,
        agent_id=agent_id,
        agent_role="Research Agent",
    )

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_memory_query_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.RETRIEVER.value
        assert str(call_args[1]["parent_run_id"]) == str(agent_id)
        expected_run_id = crewai_callback._generate_run_id(source, event)
        assert call_args[1]["run_id"] == expected_run_id

        assert call_args[1]["name"] == "Memory Query"
        assert call_args[1]["input"] == "What are the market trends?"
        assert call_args[1]["metadata"]["query"] == "What are the market trends?"
        assert call_args[1]["metadata"]["limit"] == 10
        assert call_args[1]["metadata"]["score_threshold"] == 0.8
        assert call_args[1]["metadata"]["agent_role"] == "Research Agent"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_query_completed(crewai_callback, generated_id) -> None:
    """Test memory query completed event handling."""
    query_id = generated_id()
    source = MockSource(id=query_id)
    results = [{"content": "Market trend 1"}, {"content": "Market trend 2"}]
    event = MockEvent(query="What are the market trends?", results=results, limit=10, query_time_ms=150.5)

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_memory_query_completed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        expected_run_id = crewai_callback._generate_run_id(source, event)
        assert call_args[1]["run_id"] == expected_run_id
        assert call_args[1]["metadata"]["query_time_ms"] == 150.5
        assert call_args[1]["metadata"]["results_count"] == 2


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_query_failed(crewai_callback, generated_id) -> None:
    """Test memory query failed event handling."""
    query_id = generated_id()
    source = MockSource(id=query_id)
    event = MockEvent(query="What are the market trends?", limit=10, error="Connection timeout")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_memory_query_failed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        expected_run_id = crewai_callback._generate_run_id(source, event)
        assert call_args[1]["run_id"] == expected_run_id
        assert call_args[1]["output"] == "Memory query failed: Connection timeout"
        assert call_args[1]["metadata"]["error"] == "Connection timeout"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_save_started(crewai_callback, generated_id) -> None:
    """Test memory save started event handling."""
    save_id = generated_id()
    agent_id = generated_id()
    source = MockSource(id=save_id)
    event = MockEvent(
        value="Important market insight",
        metadata={"source": "research", "confidence": 0.9},
        agent_id=agent_id,
        agent_role="Research Agent",
    )

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_memory_save_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert str(call_args[1]["parent_run_id"]) == str(agent_id)
        assert call_args[1]["run_id"] == save_id
        assert call_args[1]["name"] == "Memory Save"
        assert call_args[1]["input"] == "Important market insight"
        assert call_args[1]["metadata"]["source"] == "research"
        assert call_args[1]["metadata"]["confidence"] == 0.9
        assert call_args[1]["metadata"]["agent_role"] == "Research Agent"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_save_started_no_value(crewai_callback, generated_id) -> None:
    """Test memory save started event handling with no value."""
    save_id = generated_id()
    source = MockSource(id=save_id)
    event = MockEvent(value=None, metadata=None)

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_memory_save_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args
        assert call_args[1]["input"] == "Memory content"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_save_completed(crewai_callback, generated_id) -> None:
    """Test memory save completed event handling."""
    save_id = generated_id()
    source = MockSource(id=save_id)
    event = MockEvent(value="Important market insight", save_time_ms=75.2)

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_memory_save_completed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == save_id
        assert call_args[1]["output"] == "Memory saved successfully: Important market insight"
        assert call_args[1]["metadata"]["save_time_ms"] == 75.2


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_save_failed(crewai_callback, generated_id) -> None:
    """Test memory save failed event handling."""
    save_id = generated_id()
    source = MockSource(id=save_id)
    event = MockEvent(value="Important market insight", error="Storage full")

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_memory_save_failed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        assert call_args[1]["run_id"] == save_id
        assert call_args[1]["output"] == "Memory save failed: Storage full"
        assert call_args[1]["metadata"]["error"] == "Storage full"


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_retrieval_started(crewai_callback, generated_id) -> None:
    """Test memory retrieval started event handling."""
    retrieval_id = generated_id()
    task_id = generated_id()
    source = MockSource(id=retrieval_id)
    event = MockEvent(task_id=task_id)

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        crewai_callback._handle_memory_retrieval_started(source, event)

        mock_start_node.assert_called_once()
        call_args = mock_start_node.call_args

        assert call_args[1]["node_type"] == NodeType.CHAIN.value
        assert str(call_args[1]["parent_run_id"]) == str(task_id)
        expected_run_id = crewai_callback._generate_run_id(source, event)
        assert call_args[1]["run_id"] == expected_run_id
        assert call_args[1]["name"] == "Memory Retrieval"
        assert call_args[1]["input"] == "Retrieving relevant memories for task"
        assert call_args[1]["metadata"]["task_id"] == task_id


@pytest.mark.parametrize("generated_id", [uuid.uuid4, lambda: str(uuid.uuid4())])
def test_memory_retrieval_completed(crewai_callback, generated_id) -> None:
    """Test memory retrieval completed event handling."""
    retrieval_id = generated_id()
    source = MockSource(id=retrieval_id)
    event = MockEvent(
        task_id=generated_id(), memory_content="Retrieved relevant market insights and trends", retrieval_time_ms=120.8
    )

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        crewai_callback._handle_memory_retrieval_completed(source, event)

        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args
        expected_run_id = crewai_callback._generate_run_id(source, event)
        assert call_args[1]["run_id"] == expected_run_id
        assert call_args[1]["output"] == "Retrieved relevant market insights and trends"
        assert call_args[1]["metadata"]["retrieval_time_ms"] == 120.8


# crewAI >= 1.0 compatibility tests


def test_generate_run_id_with_call_id(crewai_callback) -> None:
    """Test that call_id correlates start and end events for LLM calls in crewAI >= 1.0."""
    # Given: start and end events with the same call_id but no source.id
    source_start = MockSource()  # No .id — crewAI 1.x BaseLLM source
    source_end = MockSource()
    call_id = "abc-123"
    start_event = MockEvent(call_id=call_id, messages=[{"role": "user", "content": "hi"}])
    end_event = MockEvent(call_id=call_id, response="hello")

    # When: generating run_ids for both events
    run_id_start = crewai_callback._generate_run_id(source_start, start_event)
    run_id_end = crewai_callback._generate_run_id(source_end, end_event)

    # Then: both produce the same UUID
    assert run_id_start == run_id_end
    assert isinstance(run_id_start, uuid.UUID)


def test_generate_run_id_agent_event_no_source_id(crewai_callback) -> None:
    """Test agent events use event.agent.id + task.id when source has no .id (crewAI >= 1.0)."""
    # Given: an event with agent.id but source without .id
    agent_id = uuid.uuid4()
    agent = MockAgent(agent_id=agent_id)
    source = MockSource()  # No .id — crewAI 1.x Adapter source
    event = MockEvent(agent=agent)

    # When: generating run_id
    result = crewai_callback._generate_run_id(source, event)

    # Then: it hashes agent.id with task context (empty when no task)
    expected = crewai_callback._hash_to_uuid(f"{agent_id}_")
    assert result == expected


def test_llm_call_lifecycle_crewai_v1(crewai_callback) -> None:
    """Test full LLM start/complete lifecycle with call_id (crewAI >= 1.0)."""
    # Given: a source without .id and events with call_id
    source = MockSource()  # No .id — crewAI 1.x BaseLLM
    call_id = "llm-call-456"
    start_event = MockEvent(
        call_id=call_id, model="gpt-4o", agent_id=str(uuid.uuid4()), messages=[{"role": "user", "content": "test"}]
    )
    end_event = MockEvent(call_id=call_id, response="LLM response")

    with (
        patch.object(crewai_callback._handler, "start_node") as mock_start,
        patch.object(crewai_callback._handler, "end_node") as mock_end,
    ):
        # When: handling start and complete
        crewai_callback._handle_llm_call_started(source, start_event)
        crewai_callback._handle_llm_call_completed(source, end_event)

        # Then: both use the same run_id
        start_run_id = mock_start.call_args[1]["run_id"]
        end_run_id = mock_end.call_args[1]["run_id"]
        assert start_run_id == end_run_id


def test_llm_call_started_prefers_event_model(crewai_callback) -> None:
    """Test that event.model is preferred over source.model for LLM name."""
    # Given: source with one model and event with a different model
    source = MockSource(id=uuid.uuid4(), model="old-model", temperature=0.5)
    event = MockEvent(model="gpt-4o", agent_id=str(uuid.uuid4()), messages=[{"role": "user", "content": "hi"}])

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        # When: handling the event
        crewai_callback._handle_llm_call_started(source, event)

        # Then: event.model wins
        call_args = mock_start_node.call_args[1]
        assert call_args["name"] == "gpt-4o"
        assert call_args["model"] == "gpt-4o"
        assert call_args["metadata"]["model"] == "gpt-4o"


def test_memory_retrieval_failed(crewai_callback) -> None:
    """Test memory retrieval failed event handling."""
    # Given: a memory retrieval failed event
    source = MockSource()
    event = MockEvent(
        type="memory_retrieval_failed",
        task_id=str(uuid.uuid4()),
        agent_id=str(uuid.uuid4()),
        error="Memory store unavailable",
    )

    with patch.object(crewai_callback._handler, "end_node") as mock_end_node:
        # When: handling the failure
        crewai_callback._handle_memory_retrieval_failed(source, event)

        # Then: error is recorded properly
        mock_end_node.assert_called_once()
        call_args = mock_end_node.call_args[1]
        assert call_args["output"] == "Memory retrieval failed: Memory store unavailable"
        assert call_args["metadata"]["error"] == "Memory store unavailable"


def test_agent_execution_started_no_task_id(crewai_callback) -> None:
    """Test agent execution started when event.task has no .id (crewAI >= 1.0)."""
    # Given: an event where task object lacks .id
    agent_id = uuid.uuid4()
    agent = MockAgent(agent_id=agent_id, role="Analyst")
    task = MockSource(description="Analyze data")  # No .id attribute
    source = MockSource(id=agent_id)
    event = MockEvent(agent=agent, task=task, task_prompt="Analyze the data")

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        # When: handling the event
        crewai_callback._handle_agent_execution_started(source, event)

        # Then: parent_run_id is None (graceful degradation)
        call_args = mock_start_node.call_args[1]
        assert call_args["parent_run_id"] is None
        assert call_args["name"] == "Analyst"


def test_task_started_no_agent_on_task(crewai_callback) -> None:
    """Test task started when task has no agent attribute (crewAI >= 1.0)."""
    # Given: a task without .agent
    task_id = uuid.uuid4()
    task = MockSource(id=task_id, description="Research market trends")
    source = MockSource(id=task_id)
    event = MockEvent(task=task)

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        # When: handling the event
        crewai_callback._handle_task_started(source, event)

        # Then: parent_run_id is None, rest works fine
        call_args = mock_start_node.call_args[1]
        assert call_args["parent_run_id"] is None
        assert call_args["name"] == "Research market trends"


def test_tool_usage_started_no_agent_id(crewai_callback) -> None:
    """Test tool usage started when event.agent has no .id (crewAI >= 1.0)."""
    # Given: an event where agent lacks .id
    agent = MockSource(role="Researcher")  # No .id
    source = MockSource()
    event = MockEvent(agent=agent, tool_name="web_search", tool_args={"query": "test"})

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        # When: handling the event
        crewai_callback._handle_tool_usage_started(source, event)

        # Then: parent_run_id is None, tool node still created
        call_args = mock_start_node.call_args[1]
        assert call_args["parent_run_id"] is None
        assert call_args["name"] == "web_search"


def test_tool_lifecycle_crewai_v1(crewai_callback) -> None:
    """Test tool start/end correlation via tool_name + tool_args hash (crewAI >= 1.0).

    In crewAI 1.x, start and finish events carry the same tool_name and tool_args,
    producing a deterministic run_id that correlates them.
    """
    # Given: a ToolUsage-like source (no .id) with matching tool_name/tool_args
    source = MockSource()

    start_event = MockEvent(tool_name="search_tool", tool_args={"query": "market research"}, agent_key="agent_1")
    end_event = MockEvent(
        tool_name="search_tool", tool_args={"query": "market research"}, output="search results", agent_key="agent_1"
    )

    # When: generating run_ids for both events
    run_id_start = crewai_callback._generate_run_id(source, start_event)
    run_id_end = crewai_callback._generate_run_id(source, end_event)

    # Then: both produce the same UUID from tool_name + tool_args
    assert run_id_start == run_id_end
    assert isinstance(run_id_start, uuid.UUID)


def test_tool_lifecycle_crewai_v1_different_sources(crewai_callback) -> None:
    """Test tool correlation works even with different source instances (thread pool race).

    The event bus may deliver start/end handlers to different thread pool workers.
    Deterministic hashing from tool_name + tool_args ensures correlation is independent
    of source identity.
    """
    # Given: different source instances (simulating thread pool race or GC reuse)
    source_start = MockSource()
    source_end = MockSource()  # Different instance!

    start_event = MockEvent(tool_name="search_tool", tool_args={"query": "test"})
    end_event = MockEvent(tool_name="search_tool", tool_args={"query": "test"}, output="results")

    # When: generating run_ids with different sources
    run_id_start = crewai_callback._generate_run_id(source_start, start_event)
    run_id_end = crewai_callback._generate_run_id(source_end, end_event)

    # Then: still produces the same UUID
    assert run_id_start == run_id_end


def test_tool_lifecycle_crewai_v1_full(crewai_callback) -> None:
    """Test full tool start/finish lifecycle with crewAI 1.x deterministic hashing."""
    # Given: source without .id, events with matching tool_name/tool_args
    source = MockSource()
    agent_id = uuid.uuid4()
    agent = MockAgent(agent_id=agent_id)

    start_event = MockEvent(agent=agent, tool_name="web_search", tool_args={"query": "test"})
    end_event = MockEvent(tool_name="web_search", tool_args={"query": "test"}, output="Results found")

    with (
        patch.object(crewai_callback._handler, "start_node") as mock_start,
        patch.object(crewai_callback._handler, "end_node") as mock_end,
    ):
        # When: handling start and finish
        crewai_callback._handle_tool_usage_started(source, start_event)
        crewai_callback._handle_tool_usage_finished(source, end_event)

        # Then: both use the same run_id
        start_run_id = mock_start.call_args[1]["run_id"]
        end_run_id = mock_end.call_args[1]["run_id"]
        assert start_run_id == end_run_id


def test_tool_lifecycle_crewai_v1_with_error(crewai_callback) -> None:
    """Test tool start/error correlation via deterministic hashing (crewAI >= 1.0)."""
    # Given: a tool that fails — error event carries the same tool_name/tool_args
    source = MockSource()
    agent_id = uuid.uuid4()
    agent = MockAgent(agent_id=agent_id)

    start_event = MockEvent(agent=agent, tool_name="web_search", tool_args={"query": "test"})
    error_event = MockEvent(tool_name="web_search", tool_args={"query": "test"}, error="Connection timeout")

    with (
        patch.object(crewai_callback._handler, "start_node") as mock_start,
        patch.object(crewai_callback._handler, "end_node") as mock_end,
    ):
        # When: handling start and error
        crewai_callback._handle_tool_usage_started(source, start_event)
        crewai_callback._handle_tool_usage_error(source, error_event)

        # Then: both use the same run_id
        start_run_id = mock_start.call_args[1]["run_id"]
        end_run_id = mock_end.call_args[1]["run_id"]
        assert start_run_id == end_run_id


def test_tool_lifecycle_crewai_v1_retry_gets_unique_ids(crewai_callback) -> None:
    """Test that retried tool calls with different args get unique run_ids (crewAI >= 1.0)."""
    # Given: two attempts with different tool_args
    source = MockSource()

    first_start = MockEvent(tool_name="search_tool", tool_args={"query": "first attempt"})
    first_error = MockEvent(tool_name="search_tool", tool_args={"query": "first attempt"}, error="fail")
    second_start = MockEvent(tool_name="search_tool", tool_args={"query": "second attempt"})
    second_finish = MockEvent(tool_name="search_tool", tool_args={"query": "second attempt"}, output="ok")

    # When: generating run_ids for both attempts
    rid_1_start = crewai_callback._generate_run_id(source, first_start)
    rid_1_error = crewai_callback._generate_run_id(source, first_error)
    rid_2_start = crewai_callback._generate_run_id(source, second_start)
    rid_2_finish = crewai_callback._generate_run_id(source, second_finish)

    # Then: each attempt correlates correctly and is distinct from the other
    assert rid_1_start == rid_1_error
    assert rid_2_start == rid_2_finish
    assert rid_1_start != rid_2_start


def test_tool_lifecycle_previous_event_id(crewai_callback) -> None:
    """Test tool start/end correlation via tool_name + tool_args with same fields."""
    # Given: a source without .id and events with matching tool_name/tool_args
    source = MockSource()

    start_event = MockEvent(tool_name="duck_duck_go_search", tool_args={"query": "latest advancements in AI"})
    end_event = MockEvent(
        tool_name="duck_duck_go_search",
        tool_args={"query": "latest advancements in AI"},
        output="No good DuckDuckGo Search Result was found",
    )

    # When: generating run_ids for both events
    run_id_start = crewai_callback._generate_run_id(source, start_event)
    run_id_end = crewai_callback._generate_run_id(source, end_event)

    # Then: both produce the same UUID
    assert run_id_start == run_id_end
    assert isinstance(run_id_start, uuid.UUID)


def test_tool_lifecycle_previous_event_id_full(crewai_callback) -> None:
    """Test full tool start/finish lifecycle with agent_id fallback for parent."""
    # Given: events matching real crewAI output (agent as null, agent_id as string)
    source = MockSource()
    agent_id = str(uuid.uuid4())

    start_event = MockEvent(agent=None, agent_id=agent_id, tool_name="duck_duck_go_search", tool_args={"query": "test"})
    end_event = MockEvent(
        agent=None,
        agent_id=agent_id,
        tool_name="duck_duck_go_search",
        tool_args={"query": "test"},
        output="search results",
    )

    with (
        patch.object(crewai_callback._handler, "start_node") as mock_start,
        patch.object(crewai_callback._handler, "end_node") as mock_end,
    ):
        # When: handling start and finish
        crewai_callback._handle_tool_usage_started(source, start_event)
        crewai_callback._handle_tool_usage_finished(source, end_event)

        # Then: both use the same run_id and parent is resolved from agent_id
        start_run_id = mock_start.call_args[1]["run_id"]
        end_run_id = mock_end.call_args[1]["run_id"]
        assert start_run_id == end_run_id
        assert str(mock_start.call_args[1]["parent_run_id"]) == agent_id


def test_tool_usage_started_agent_id_fallback(crewai_callback) -> None:
    """Test tool usage started resolves parent from event.agent_id when event.agent is None."""
    # Given: an event with agent=None but agent_id as a top-level string (crewAI >= 1.0)
    source = MockSource()
    agent_id = str(uuid.uuid4())
    event = MockEvent(
        agent=None, agent_id=agent_id, tool_name="web_search", tool_args={"query": "test"}, event_id=str(uuid.uuid4())
    )

    with patch.object(crewai_callback._handler, "start_node") as mock_start_node:
        # When: handling the event
        crewai_callback._handle_tool_usage_started(source, event)

        # Then: parent_run_id is resolved from the top-level agent_id
        call_args = mock_start_node.call_args[1]
        assert str(call_args["parent_run_id"]) == agent_id
        assert call_args["name"] == "web_search"


def test_tool_lifecycle_previous_event_id_with_error(crewai_callback) -> None:
    """Test tool start/error correlation with matching tool_name/tool_args."""
    # Given: a tool that fails — error event carries the same tool_name/tool_args
    source = MockSource()
    agent_id = str(uuid.uuid4())

    start_event = MockEvent(agent=None, agent_id=agent_id, tool_name="web_search", tool_args={"query": "test"})
    error_event = MockEvent(
        agent_id=agent_id, tool_name="web_search", tool_args={"query": "test"}, error="Connection timeout"
    )

    with (
        patch.object(crewai_callback._handler, "start_node") as mock_start,
        patch.object(crewai_callback._handler, "end_node") as mock_end,
    ):
        # When: handling start and error
        crewai_callback._handle_tool_usage_started(source, start_event)
        crewai_callback._handle_tool_usage_error(source, error_event)

        # Then: both use the same run_id
        start_run_id = mock_start.call_args[1]["run_id"]
        end_run_id = mock_end.call_args[1]["run_id"]
        assert start_run_id == end_run_id
