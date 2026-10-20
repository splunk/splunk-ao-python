# OpenAI Agents SDK travel agent

A small travel agent built with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) and
instrumented with Splunk AO. The agent has two mock tools (flight search and activity search), so each run
produces a tool-calling turn followed by a final answer.

The example shows two ways to send the same agent's telemetry to Splunk AO:

| `INSTRUMENTATION` | How it works |
|---|---|
| `sdk` (default) | `SplunkAOTracingProcessor`, registered with the Agents SDK's `set_trace_processors()` hook. |
| `otel` | The community OpenTelemetry instrumentation for the Agents SDK, with Splunk AO attached to a tracer provider through `add_splunk_ao_span_processor()`. |

## Prerequisites

- Python 3.11 or later
- A Splunk AO project and agent stream, plus a token that can send telemetry
- An Azure OpenAI chat deployment (the script uses `AsyncAzureOpenAI`)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in your own values; .env is git-ignored
```

For `INSTRUMENTATION=otel`, also install the extra package listed at the bottom of `requirements.txt`:

```bash
pip install opentelemetry-instrumentation-genai-openai-agents
```

Configure Splunk AO with **either** the Splunk Observability Cloud variables (`SPLUNK_AO_REALM` and
`SPLUNK_AO_O11Y_TOKEN`) **or** the standalone variables (`SPLUNK_AO_API_KEY` and `SPLUNK_AO_CONSOLE_URL`), not both.

## Run

```bash
INSTRUMENTATION=sdk  python main.py
INSTRUMENTATION=otel python main.py
```

Each run picks a random route, asks the agent to plan a trip, and logs the final answer. Open the
agent stream you configured in Splunk AO to inspect the session: the agent, its turns, the LLM calls, and
the two tool calls.

## Notes

- The tools return deterministic mock data and call no external services.
- Environment variables you export in your shell take precedence over values in `.env`.
