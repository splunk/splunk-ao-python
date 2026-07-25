# Multi-Agent Travel Planner with the Splunk AO LangChain Handler

This is the handler-based counterpart to
[`../multi-agent-travel-planner-otel`](../multi-agent-travel-planner-otel).
It runs the same five-agent LangGraph application:

1. A coordinator interprets the request.
2. Flight, hotel, and activity specialists call mock tools.
3. A plan synthesizer produces the final itinerary.

Instead of upstream OpenTelemetry instrumentation, the application creates a
`SplunkAOLogger`, injects it into `SplunkAOCallback`, and passes that callback
to the LangGraph run:

```python
galileo_logger = SplunkAOLogger()
galileo_logger.set_session(session_id)
galileo_handler = SplunkAOCallback(splunk_ao_logger=galileo_logger)

config = {
    "callbacks": [galileo_handler],
    "configurable": {"thread_id": session_id},
    "metadata": {"session_id": session_id, "conversation_id": session_id},
}
build_workflow().compile().stream(initial_state, config)
```

`SplunkAOLogger` is the current name of the SDK class formerly called
`GalileoLogger`.

The example does not import OpenTelemetry, register a `TracerProvider`, add a
span processor, or install a LangChain OpenTelemetry instrumentor. The Splunk
AO callback translates LangChain and LangGraph callback events into the SDK's
logger model, and the logger owns export and shutdown.

## Setup

From this directory:

```shell
cp .env.example .env
pyenv local 3.13
uv sync
```

The local project installs the current repository checkout as an editable
dependency, so it exercises the handler and logger implementation on the
current branch.

You may copy the private AI and deployment credentials from the OTel version,
but keep this example's handler-specific log-stream value:

```shell
cp ../multi-agent-travel-planner-otel/.env .env
```

Then remove the two `OTEL_*` variables if present and set:

```dotenv
SPLUNK_AO_LOG_STREAM=multi-agent-travel-planner-handler
```

`ChatOpenAI` reads `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` from
the environment. The Azure-compatible base URL should include `/openai/v1`.

## Telemetry configuration

No OpenTelemetry instrumentation environment variables are required. The
handler captures the LangChain inputs, outputs, model calls, agents, and tools
through callback events.

### O11y Cloud

```dotenv
SPLUNK_AO_REALM=us1
SPLUNK_AO_SF_TOKEN=your-splunk-ingest-token
SPLUNK_AO_PROJECT=your-project-name
SPLUNK_AO_LOG_STREAM=multi-agent-travel-planner-handler
```

`SPLUNK_AO_SF_TOKEN` must have ingest permission. Routing may use project and
log-stream IDs instead of names; do not mix a name and ID for the same
resource.

### Standalone Agent Observability

```dotenv
SPLUNK_AO_API_KEY=your-agent-observability-api-key
SPLUNK_AO_CONSOLE_URL=https://app.galileo.ai
SPLUNK_AO_PROJECT=your-project-name
SPLUNK_AO_LOG_STREAM=multi-agent-travel-planner-handler
```

Set `SPLUNK_AO_API_URL` only when it cannot be derived from the console URL.

## Session and agent metadata

The example generates one conversation ID per itinerary and assigns it to the
logger with `set_session()`. The same value is used as the LangGraph
`thread_id` and supplied as `session_id` and `conversation_id` metadata. Each
specialist also supplies `agent_name` metadata and tags.

`set_session()` associates telemetry with the conversation ID without creating
a session through REST CRUD. If an application needs explicit session CRUD,
it can call `start_session()` separately.

## Optional quality noise

The application can inject mild prompt noise for evaluation testing. It is
disabled by default. Set `TRAVEL_POISON_PROB` to a value between `0` and `1` to
enable it; the other `TRAVEL_POISON_*` variables select the categories,
maximum snippets, and seed.

## Run

```shell
uv run python main.py
```

The finite example calls `galileo_logger.terminate()` in `finally`, ensuring
pending telemetry is drained and logger-owned resources are shut down even if
the workflow raises.
