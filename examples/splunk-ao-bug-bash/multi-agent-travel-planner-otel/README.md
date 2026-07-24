# Multi-Agent Travel Planner with OpenTelemetry

This example adapts the Splunk OpenTelemetry Python contrib
[multi-agent travel planner](https://github.com/signalfx/splunk-otel-python-contrib/blob/main/instrumentation-genai/opentelemetry-instrumentation-langchain/examples/multi_agent_travel_planner/main.py).
It coordinates five LangChain agents through LangGraph:

1. A coordinator interprets the request.
2. Flight, hotel, and activity specialists call mock tools.
3. A plan synthesizer produces the final itinerary.

The application uses the official OpenTelemetry GenAI instrumentation for
LangChain and the Splunk Agent Observability span processor. It does not use
the Splunk distribution of OpenTelemetry instrumentations, configure a raw
OTLP exporter, or use the reference application's OAuth token manager.

The application does not need separate OpenAI instrumentation. `ChatOpenAI`
is invoked through LangChain, so the LangChain callback instrumentation emits
the model spans.

## Setup

From this directory:

```shell
cp .env.example .env
pyenv local 3.13
uv sync
```

## Telemetry configuration

The example registers one official LangChain instrumentor:

```python
tracer_provider = trace_sdk.TracerProvider(resource=resource)
otel.add_splunk_ao_span_processor(tracer_provider)
trace_api.set_tracer_provider(tracer_provider=tracer_provider)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
```

The SDK derives the endpoint, authentication, and routing from the environment.
OpenTelemetry's `BatchSpanProcessor` owns batching; the example adds no custom
batching logic.

To capture prompts, responses, and tool arguments on spans, keep these values:

```dotenv
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_only
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
```

Captured content can contain sensitive information.

### O11y Cloud

```dotenv
SPLUNK_AO_REALM=us1
SPLUNK_AO_SF_TOKEN=your-splunk-ingest-token
SPLUNK_AO_SF_API_TOKEN=your-splunk-ingest-token
SPLUNK_AO_PROJECT=your-project-name
SPLUNK_AO_LOG_STREAM=your-logstream-name
```

`SPLUNK_AO_SF_TOKEN` must have ingest permission. Routing may use project and
log-stream IDs instead of names; names and IDs should not be mixed for the same
resource.

### Standalone Agent Observability

```dotenv
SPLUNK_AO_API_KEY=your-agent-observability-api-key
SPLUNK_AO_CONSOLE_URL=https://app.galileo.ai
SPLUNK_AO_PROJECT=your-project-name
SPLUNK_AO_LOG_STREAM=your-logstream-name
```

## Run

```shell
uv run python main.py
```
