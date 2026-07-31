# splunk-ao-adk

[![PyPI version](https://img.shields.io/pypi/v/splunk-ao-adk.svg)](https://pypi.org/project/splunk-ao-adk/)
[![Python versions](https://img.shields.io/pypi/pyversions/splunk-ao-adk.svg)](https://pypi.org/project/splunk-ao-adk/)
[![License](https://img.shields.io/pypi/l/splunk-ao-adk.svg)](https://github.com/splunk/splunk-ao-python/blob/main/LICENSE)

Splunk AO observability for [Google ADK](https://github.com/google/adk-python) agents. Automatic tracing of agent runs, LLM calls, and tool executions.

## Installation

```bash
pip install splunk-ao-adk
```

**Requirements:** Python 3.11+, Splunk AO standalone or Splunk Observability
Cloud credentials, and a [Google AI API key](https://aistudio.google.com/apikey).

## Quick Start

```python
import asyncio
from splunk_ao_adk import SplunkAOADKPlugin
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.genai import types

async def main():
    plugin = SplunkAOADKPlugin(project="my-project", agent_stream="production")
    agent = LlmAgent(name="assistant", model="gemini-2.0-flash", instruction="You are helpful.")
    runner = Runner(agent=agent, plugins=[plugin])

    message = types.Content(parts=[types.Part(text="Hello! What can you help me with?")])
    async for event in runner.run_async(user_id="user-123", session_id="session-456", new_message=message):
        if event.is_final_response():
            print(event.content.parts[0].text)

if __name__ == "__main__":
    # Configure one Splunk AO deployment below, plus GOOGLE_API_KEY.
    asyncio.run(main())
```

## Configuration

| Parameter | Description |
|-----------|-------------|
| `project` | Project name. Explicit arguments override environment routing. |
| `agent_stream` | Agent Stream name. Explicit arguments override environment routing. |
| `ingestion_hook` | Deprecated compatibility callback that receives proprietary trace requests and bypasses normal OTLP export. |

For standalone Splunk AO:

| Environment Variable | Description |
|---------------------|-------------|
| `SPLUNK_AO_API_KEY` | Splunk AO API key (required) |
| `SPLUNK_AO_CONSOLE_URL` | Splunk AO console URL (required for self-hosted deployments) |
| `SPLUNK_AO_API_URL` | Explicit API URL (optional; otherwise derived from the console URL) |
| `SPLUNK_AO_PROJECT` | Project name |
| `SPLUNK_AO_AGENT_STREAM` | Agent Stream name |

For Splunk Observability Cloud:

| Environment Variable | Description |
|---------------------|-------------|
| `SPLUNK_AO_REALM` | Observability Cloud realm (required) |
| `SPLUNK_AO_O11Y_TOKEN` | O11y ingest token used for OTLP export (required) |
| `SPLUNK_AO_O11Y_API_TOKEN` | Dedicated O11y API token used for session and other CRUD operations (optional) |
| `SPLUNK_AO_PROJECT` | Project name |
| `SPLUNK_AO_AGENT_STREAM` | Agent Stream name |

When both O11y tokens are configured, the API token is preferred for CRUD and
the ingest token is used for telemetry. A combined token can perform both when
it includes both permissions.

## Features

### Session Tracking

All traces with the same `session_id` are automatically grouped into a Splunk AO session, enabling conversation-level tracking:

```python
import asyncio
from splunk_ao_adk import SplunkAOADKPlugin
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.genai import types

async def main():
    plugin = SplunkAOADKPlugin(project="my-project", agent_stream="production")
    agent = LlmAgent(name="assistant", model="gemini-2.0-flash", instruction="You are helpful.")
    runner = Runner(agent=agent, plugins=[plugin])

    # All traces in this conversation are grouped together
    session_id = "conversation-abc"

    # First message
    message1 = types.Content(parts=[types.Part(text="Hello! What's the capital of France?")])
    async for event in runner.run_async(user_id="user-123", session_id=session_id, new_message=message1):
        if event.is_final_response():
            print(f"Response 1: {event.content.parts[0].text}")

    # Follow-up in same session
    message2 = types.Content(parts=[types.Part(text="What about Germany?")])
    async for event in runner.run_async(user_id="user-123", session_id=session_id, new_message=message2):
        if event.is_final_response():
            print(f"Response 2: {event.content.parts[0].text}")

if __name__ == "__main__":
    # Configure one Splunk AO deployment above, plus GOOGLE_API_KEY.
    asyncio.run(main())
```

### Custom Metadata

Attach custom metadata to traces using ADK's `RunConfig`. Metadata is propagated to all spans (agent, LLM, tool) within the invocation:

```python
import asyncio
from splunk_ao_adk import SplunkAOADKPlugin
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.genai import types

async def main():
    plugin = SplunkAOADKPlugin(project="my-project", agent_stream="production")
    agent = LlmAgent(name="assistant", model="gemini-2.0-flash", instruction="You are helpful.")
    runner = Runner(agent=agent, plugins=[plugin])

    run_config = RunConfig(
        custom_metadata={
            "user_tier": "premium",
            "conversation_id": "conv-abc",
            "turn": 1,
            "experiment_group": "A",
        }
    )

    message = types.Content(parts=[types.Part(text="Hello! Tell me a fun fact.")])
    async for event in runner.run_async(
        user_id="user-123",
        session_id="session-456",
        new_message=message,
        run_config=run_config,
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)

if __name__ == "__main__":
    # Configure one Splunk AO deployment above, plus GOOGLE_API_KEY.
    asyncio.run(main())
```

### Callback Mode

For granular control over which callbacks to use, attach them directly to your agent instead of using the plugin:

```python
import asyncio
from splunk_ao_adk import SplunkAOADKCallback
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.genai import types

async def main():
    callback = SplunkAOADKCallback(project="my-project", agent_stream="production")

    agent = LlmAgent(
        name="assistant",
        model="gemini-2.0-flash",
        instruction="You are helpful.",
        before_agent_callback=callback.before_agent_callback,
        after_agent_callback=callback.after_agent_callback,
        before_model_callback=callback.before_model_callback,
        after_model_callback=callback.after_model_callback,
        before_tool_callback=callback.before_tool_callback,
        after_tool_callback=callback.after_tool_callback,
    )
    runner = Runner(agent=agent)

    message = types.Content(parts=[types.Part(text="Hello! How are you?")])
    async for event in runner.run_async(user_id="user-123", session_id="session-456", new_message=message):
        if event.is_final_response():
            print(event.content.parts[0].text)

if __name__ == "__main__":
    # Configure one Splunk AO deployment above, plus GOOGLE_API_KEY.
    asyncio.run(main())
```

### Retriever Spans

By default, all `FunctionTool` calls are logged as tool spans. To log a retriever function as a **retriever span** (enabling RAG quality metrics in Splunk AO), decorate it with `@splunk_ao_retriever`:

```python
from splunk_ao_adk import splunk_ao_retriever
from google.adk.tools import FunctionTool

@splunk_ao_retriever
def search_docs(query: str) -> str:
    """Search the knowledge base."""
    results = my_vector_db.search(query)
    return "\n".join(r["content"] for r in results)

tool = FunctionTool(search_docs)
```

### Ingestion Hook

The proprietary ingestion hook remains available as deprecated migration
compatibility. It bypasses the normal OTLP export path. New custom telemetry
pipelines should use OpenTelemetry `SpanProcessor` and `SpanExporter`
extension points instead.

```python
import asyncio
import os
from splunk_ao import SplunkAOLogger
from splunk_ao_adk import SplunkAOADKPlugin
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.genai import types

logger = SplunkAOLogger(
    project=os.getenv("SPLUNK_AO_PROJECT", "my-project"),
    agent_stream=os.getenv("SPLUNK_AO_AGENT_STREAM", "dev"),
)

def my_ingestion_hook(request):
    """Capture traces locally and forward them with session management."""
    if hasattr(request, "traces") and request.traces:
        print(f"\n[Ingestion Hook] Intercepted {len(request.traces)} trace(s)")
        for trace in request.traces:
            spans = getattr(trace, "spans", []) or []
            span_types = [getattr(s, "type", "unknown") for s in spans]
            print(f"  - Trace with {len(spans)} span(s): {span_types}")

    # The same external ID returns the same Agent Observability session.
    session_id = logger.start_session(external_id=request.session_external_id)
    request.session_id = session_id

    # Forward traces through the legacy proprietary endpoint.
    logger.ingest_traces(request)

async def main():
    plugin = SplunkAOADKPlugin(ingestion_hook=my_ingestion_hook)
    agent = LlmAgent(name="assistant", model="gemini-2.0-flash", instruction="You are helpful.")
    runner = Runner(agent=agent, plugins=[plugin])

    message = types.Content(parts=[types.Part(text="Hello!")])
    async for event in runner.run_async(user_id="user-123", session_id="session-456", new_message=message):
        if event.is_final_response():
            print(event.content.parts[0].text)

if __name__ == "__main__":
    # Configure one Splunk AO deployment above, plus GOOGLE_API_KEY.
    asyncio.run(main())
```

## Resources

- [Splunk AO Documentation](https://agent-observability-docs.splunk.com)
- [Google ADK Documentation](https://google.github.io/adk-docs/)

## License

Apache-2.0
