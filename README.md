# Splunk Agent Observability Python SDK

<div align="center">

<strong>The Python client library for the Splunk Agent Observability product.</strong>

[![PyPI][pypi-badge]][pypi-url]
[![Python Version][python-badge]][python-url]
[![License][license-badge]][license-url]

</div>

[pypi-badge]: https://img.shields.io/pypi/v/splunk-ao.svg?style=for-the-badge
[pypi-url]: https://pypi.org/project/splunk-ao/
[python-badge]: https://img.shields.io/pypi/pyversions/splunk-ao.svg?style=for-the-badge
[python-url]: https://www.python.org/downloads/
[license-badge]: https://img.shields.io/pypi/l/splunk-ao.svg?style=for-the-badge
[license-url]: https://github.com/splunk/splunk-ao-python/blob/main/LICENSE

## Getting Started

### Installation

Install the SDK:

```shell
pip install splunk-ao
```

Install the optional integration dependencies used by your application:

```shell
pip install "splunk-ao[openai]"
pip install "splunk-ao[langchain]" langchain-openai
pip install "splunk-ao[distributed-tracing]"
```

Other available extras include `crewai`, `middleware`, and `all`.

### Setup

Environment variables differ based on your Agent Observability deployment:
1. On-premises, standalone, and custom deployments
2. Splunk Observability (O11y) Cloud deployments

> [!CAUTION]
> Do not mix 1) on-premises and 2) o11y Cloud environment variables. The SDK detects the deployment from the environment variables that are present and rejects ambiguous configurations.

#### On-Premises Agent Observability

| Environment variable | Description |
| --- | --- |
| `SPLUNK_AO_API_KEY` | Agent Observability API key (Required) |
| `SPLUNK_AO_CONSOLE_URL` | Agent Observability Console URL (Required) |
| `SPLUNK_AO_API_URL` | Custom API URL (Optional) |

Set your Agent Observability API key and Console URL:

```shell
export SPLUNK_AO_API_KEY="your-agent-observability-api-key"
export SPLUNK_AO_CONSOLE_URL="https://console.subdomain.yourcompany.com"
```

> [!TIP]
> Logging your first trace to on-premises Agent Observability? [Visit this guide](https://agent-observability-docs.splunk.com/sdk-redirect/on-prem-first-trace).
>
> Learn how to find each environment variable in [this guide](https://agent-observability-docs.splunk.com/sdk-redirect/on-prem-keys).

#### Splunk Observability (O11y) Cloud

> [!NOTE]
> As of August 2026, Agent Observability on Splunk Observability Cloud is not yet generally available.

| Environment variable | Description |
| --- | --- |
| `SPLUNK_AO_REALM` | Splunk Observability Cloud realm (Required) |
| `SPLUNK_AO_O11Y_TOKEN` | O11y ingest token used for OTLP export (Required for telemetry) |
| `SPLUNK_AO_O11Y_API_TOKEN` | Dedicated O11y API token used for CRUD operations (Optional) |

For telemetry export, set your realm and O11y ingest token:

```shell
export SPLUNK_AO_REALM="us1"
export SPLUNK_AO_O11Y_TOKEN="your-o11y-ingest-token"
```

`SPLUNK_AO_O11Y_TOKEN` is required to export telemetry. It is also used for CRUD
operations when it contains the necessary API permissions and no dedicated API
token is configured.

You may configure a separate token for CRUD operations:

```shell
export SPLUNK_AO_O11Y_API_TOKEN="your-o11y-api-token"
```

When both tokens are set, `SPLUNK_AO_O11Y_API_TOKEN` is preferred for CRUD and
`SPLUNK_AO_O11Y_TOKEN` is used for telemetry ingestion. For CRUD-only use, set
`SPLUNK_AO_REALM` and `SPLUNK_AO_O11Y_API_TOKEN`; an ingest token is not
required until the application exports telemetry. Attempting to construct an
OTLP exporter without `SPLUNK_AO_O11Y_TOKEN` raises a configuration error.

The SDK derives the console, API and OTLP ingest endpoints from the
realm. Do not set `SPLUNK_AO_CONSOLE_URL` or `SPLUNK_AO_API_URL` for O11y
Cloud.

#### Routing

Routing configuration is shared by both deployments:

| Environment variable | Description |
| --- | --- |
| `SPLUNK_AO_PROJECT` | Project name |
| `SPLUNK_AO_AGENT_STREAM` | Agent Stream name |

Configure Project and Agent Stream routing by name:

```shell
export SPLUNK_AO_PROJECT="your-project-name"
export SPLUNK_AO_AGENT_STREAM="your-agent-stream-name"
```

Explicit SDK arguments take precedence over the active `splunk_ao_context`,
which takes precedence over environment variables. The deprecated
`SPLUNK_AO_LOG_STREAM` variable remains a compatibility alias; use
`SPLUNK_AO_AGENT_STREAM` in new applications.

Routing is captured when an OTLP exporter is constructed and remains fixed for
that exporter's lifetime. Use a separate processor and exporter for each
additional destination.

Routing is SDK configuration, not a general OpenTelemetry Resource setting. Do
not set Agent Observability routing in `OTEL_RESOURCE_ATTRIBUTES`. Use the
supported SDK arguments, context, or `SPLUNK_AO_*` environment variables.

Set a meaningful OpenTelemetry service name when you want traces to appear
under a recognizable service in APM:

```shell
export OTEL_SERVICE_NAME="checkout-agent"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment.name=production,service.version=1.2.0"
```

`OTEL_SERVICE_NAME` is optional. If it is absent, the standard OpenTelemetry
unknown-service fallback is used. Other non-routing
`OTEL_RESOURCE_ATTRIBUTES` are preserved.

Set `SPLUNK_AO_LOGGING_DISABLED=true` to disable telemetry collection and
export.

### Usage

#### Logging traces

```python
import os

from splunk_ao import splunk_ao_context
from splunk_ao.openai import openai

# Skip this when SPLUNK_AO_PROJECT and SPLUNK_AO_AGENT_STREAM are set.
splunk_ao_context.init(project="your-project-name", agent_stream="your-agent-stream-name")

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def call_openai() -> str | None:
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "Say this is a test"}], model="gpt-5.6-terra"
    )
    return chat_completion.choices[0].message.content

print(call_openai())

# This finite example waits for its completed span to be delivered.
splunk_ao_context.flush()
```

Completed spans enter the SDK's OpenTelemetry batch processor immediately and
are exported on its schedule. Long-running applications do not need to flush
after each operation. The explicit flush above is only to make the finite
example wait for delivery before it exits.

Use the `@log` decorator to capture application operations. Every independent
top-level decorated call owns and concludes its trace. Nested decorated calls
become children of the outer operation. Captured function arguments and return
values are preserved as the operation input and output, including supported
structured and multimodal content:

```python
from splunk_ao import log, splunk_ao_context

@log
def make_nested_call() -> None:
    call_openai()
    call_openai()

splunk_ao_context.init(
    project="your-project-name",
    agent_stream="your-agent-stream-name",
)

make_nested_call()
```

If a decorated function, synchronous generator, or asynchronous generator
raises, the SDK finalizes its telemetry and re-raises the original exception.

Create a retriever span:

```python
from splunk_ao import log

@log(span_type="retriever")
def retrieve_documents(query: str) -> list[str]:
    return ["doc1", "doc2"]

retrieve_documents(query="history")
```

Create a tool span:

```python
from splunk_ao import log

@log(span_type="tool")
def lookup_weather(city: str) -> str:
    return f"The weather in {city} is sunny."

lookup_weather("Seattle")
```

Use `splunk_ao_context` to scope routing or session state for a block. It does
not create an extra operation around the block:

```python
from splunk_ao import splunk_ao_context

with splunk_ao_context(project="gen-ai-project", agent_stream="production"):
    make_nested_call()
```

For manual logging, conclude every trace or span that you start. In finite
scripts and jobs, call `terminate()` during teardown so the final queued batch
is delivered:

```python
from splunk_ao.logger import SplunkAOLogger

logger = SplunkAOLogger(project="gen-ai-project", agent_stream="production")
try:
    logger.start_trace("Say this is a test")
    logger.add_llm_span(
        input="Say this is a test",
        output="Hello, this is a test",
        model="gpt-5.6-terra",
        num_input_tokens=10,
        num_output_tokens=3,
        total_tokens=13,
        duration_ns=1000,
    )
    logger.conclude(output="Hello, this is a test", duration_ns=1000)
finally:
    logger.terminate()
```

`flush()` and `async_flush()` only drain completed spans already waiting in the
batch processor. They do not conclude an active operation and are not required
for normal scheduled export. `terminate()` drains completed spans and shuts
down resources owned by `SplunkAOLogger`; it does not turn unfinished manual
spans into completed spans.

#### Using Agent Observability context with Agent Control

If you use Agent Control hosted by Splunk, initialize Agent Control with the
current Agent Observability Agent Stream as the runtime target:

```python
import agent_control

from splunk_ao import splunk_ao_context, get_agent_control_target

# Configure SPLUNK_AO_PROJECT and SPLUNK_AO_AGENT_STREAM_ID before startup.
splunk_ao_context.init()

target = get_agent_control_target()

agent_control.init(
    agent_name="my-agent",
    target_type=target.target_type,
    target_id=target.target_id,
    # server_url, api_key, and api_key_header can be passed here or configured
    # through the Agent Control SDK environment variables.
)
```

Agent Control requires the Agent Stream target ID; the project can still be
configured by name with `SPLUNK_AO_PROJECT`. The helper resolves an explicit
Agent Stream ID, `SPLUNK_AO_AGENT_STREAM_ID` (or the deprecated
`SPLUNK_AO_LOG_STREAM_ID` alias), or an already-initialized
`splunk_ao_context` logger with resolved IDs. It does not import the Agent
Control SDK or resolve Agent Stream names over the network. If you use a direct
Agent Control client instead of `agent_control.init(...)`, pass
`target.target_type` and `target.target_id` on each evaluation call.

`splunk_ao.agent_control` resolves targets for Agent Control calls.
`splunk_ao.handlers.agent_control` bridges Agent Control telemetry into Agent
Observability logging.

OpenAI streaming example:

```python
import os

from splunk_ao.openai import openai

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

stream = client.chat.completions.create(
    messages=[{"role": "user", "content": "Say this is a test"}], model="gpt-5.6-terra", stream=True,
)

# This will create a single span trace with the OpenAI call
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

#### Using OpenTelemetry instrumentations

You can connect standard OpenTelemetry or OpenInference instrumentations to
Agent Observability without constructing an exporter yourself:

```python
from opentelemetry import trace
from opentelemetry.sdk import trace as trace_sdk
from splunk_ao import otel

tracer_provider = trace_sdk.TracerProvider()
processor = otel.add_splunk_ao_span_processor(tracer_provider)
trace.set_tracer_provider(tracer_provider)

# Configure each instrumentation library with this provider, or let it use the
# global provider set above.

# At application shutdown:
tracer_provider.shutdown()
```

`add_splunk_ao_span_processor()` reads the same deployment and routing
configuration described in [Setup](#setup). It registers a
`SplunkAOSpanProcessor`, which uses a standard OpenTelemetry
`BatchSpanProcessor`. Default logger-owned and caller-owned processors honor
the standard `OTEL_BSP_*` batch processor environment variables.

If your application needs another processor or exporter, register it through
the standard OpenTelemetry extension points. For example, to send the same
spans to an additional custom exporter:

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# custom_exporter is your SpanExporter implementation.
tracer_provider.add_span_processor(BatchSpanProcessor(custom_exporter))
```

The application owns a `TracerProvider` that it constructs, so it must call
`tracer_provider.shutdown()` during teardown. A `SplunkAOLogger` created
elsewhere owns a separate provider and should be terminated separately.

##### Automatic HTTP distributed tracing

The `distributed-tracing` extra provides a supported one-time setup for
upstream OpenTelemetry FastAPI/Starlette, Requests, HTTPX sync/async, and
aiohttp-client instrumentation. The high-level helper creates an application-owned
provider, registers Splunk AO export, and configures those transports together:

```python
from fastapi import FastAPI
from splunk_ao import configure_distributed_tracing

app = FastAPI()
provider = configure_distributed_tracing(app=app)
```

The application owns the returned `provider` and calls `provider.shutdown()`
during process teardown. The helper never replaces the process-global provider.
Pass an existing OpenTelemetry SDK `TracerProvider` through the
`tracer_provider` argument when other OpenTelemetry/OpenInference agent or model
instrumentations should use that same provider and join the trace.

For advanced composition, `add_splunk_ao_span_processor()` remains the
export-only API and `instrument_distributed_tracing()` remains the supported
transport-only API. Do not also directly instrument a client or application
component that is owned by the high-level helper; each component should have one
instrumentation owner.

After this startup call, supported inbound requests extract W3C context and
supported outbound clients inject it automatically. Application code does not
call `get_tracing_headers()` for each request and does not install
`TracingMiddleware`. Those APIs remain supported for transports and frameworks
outside the automatic support matrix.

SDK-owned authentication, health-check, Project, Agent Stream, and other
control-plane HTTP requests are scoped out of automatic client instrumentation.
They therefore do not appear as application traces, while HTTP requests made by
the application remain instrumented normally.

An explicit SDK session propagates as the standard
`gen_ai.conversation.id` W3C baggage member. Project, Agent Stream,
experiment, deployment, authentication, model, workflow, and agent identity
remain local and are never added to baggage by the SDK.

Explicit session selection is ambient within the current thread or async
execution context. Setting a session through any logger in that context selects
the conversation for subsequently started telemetry and outbound propagation
from that context. Use separate execution contexts for independent sessions.

#### Export diagnostics

The SDK does not change your application's global logging configuration.
Configure Python logging to surface standard OpenTelemetry transport,
authentication, retry, and HTTP errors, as well as Agent Observability
successful-response rejection diagnostics:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("opentelemetry.exporter.otlp.proto.http.trace_exporter").setLevel(logging.WARNING)
logging.getLogger("splunk_ao.exporter").setLevel(logging.INFO)
```

A successful HTTP response can still acknowledge that some or all spans were
rejected. The SDK emits a sanitized, rate-limited error for those
acknowledgements and one informational message after recovery. Export failures
never fail the instrumented application or business request.

The processor returned by `add_splunk_ao_span_processor()` exposes the latest
receiver acknowledgement as `processor.export_health`. Its `healthy` value is:

- `None` before an acknowledgement, or after a transport or non-2xx failure.
- `True` after an accepted 2xx response.
- `False` after a 2xx response that rejects telemetry.

This is advisory diagnostic state, not a delivery guarantee.

#### Framework handlers

Using the LangChain callback handler:

```python
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from splunk_ao.handlers.langchain import SplunkAOCallback

callback = SplunkAOCallback()
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, callbacks=[callback])

messages = [HumanMessage(content="What is LangChain and how is it used with OpenAI?")]
response = llm.invoke(messages)

print(response.content)
```

Handlers conclude traces that they own when their framework run ends. They do
not close a trace that was started by the caller. In short-lived jobs, ensure
the owning logger or provider is terminated or shut down after framework work
finishes.

For normal OTLP export, LangChain, CrewAI, Google ADK, and OpenAI Agents
handlers enqueue each operation into the existing `BatchSpanProcessor` when
that operation's end callback runs. A child can therefore enter a scheduled
or size-based export batch while its parent remains active. This is immediate
enqueue, not one network request per span, and no per-trace `flush()` is
required. The deprecated `ingestion_hook` compatibility path still constructs
one mutable whole-tree payload at trace completion.

`start_new_trace` controls ownership, not whether distributed tracing works.
Keep its default `True` for a standalone handler. Set it to `False` only when
the handler is intentionally placed beneath caller-owned active logger state;
the handler emits its own subtree and does not conclude the caller.

#### Datasets

Create a dataset:

```python
from splunk_ao.datasets import create_dataset

create_dataset(
    name="names",
    content=[
        {"name": "Lola"},
        {"name": "Jo"},
    ]
)
```

Get a dataset:

```python
from splunk_ao.datasets import get_dataset

dataset = get_dataset(name="names")
```

List all datasets:

```python
from splunk_ao.datasets import list_datasets

datasets = list_datasets()
```

> **Dataset Record Fields:**
>
> - **`generated_output`**: New field for storing model-generated outputs separately from ground truth. This allows you to track both the expected output (ground truth) and the actual model output in the same dataset record. In the UI, this field is displayed as "Generated Output".
>
>   Example:
>   ```python
>   from splunk_ao.schema.datasets import DatasetRecord
>
>   record = DatasetRecord(
>       input="What is 2+2?",
>       output="4",  # Ground truth
>       generated_output="The answer is 4"  # Model-generated output
>   )
>   ```
>
> - **`output` / `ground_truth`**: The existing `output` field is displayed as "Ground Truth" in the Agent Observability UI. The SDK accepts both `output` and `ground_truth` when creating records. Both are stored as `output` internally, and the value is also accessible through the `ground_truth` property.
>
>   Example:
>   ```python
>   from splunk_ao.schema.datasets import DatasetRecord
>
>   # Using 'output' (backward compatible)
>   record1 = DatasetRecord(input="What is 2+2?", output="4")
>   assert record1.ground_truth == "4"  # Property accessor
>
>   # Using the equivalent 'ground_truth' input name
>   record2 = DatasetRecord(input="What is 2+2?", ground_truth="4")
>   assert record2.output == "4"  # Normalized internally
>   assert record2.ground_truth == "4"  # Property accessor
>   ```

#### Experiments

Run an experiment with a prompt template:

```python
from splunk_ao import Message, MessageRole
from splunk_ao.datasets import get_dataset
from splunk_ao.experiments import run_experiment
from splunk_ao.prompts import create_prompt

prompt = create_prompt(
    name="my-prompt",
    project_name="new-project",
    template=[
        Message(role=MessageRole.system, content="you are a helpful assistant"),
        Message(role=MessageRole.user, content="why is sky blue?")
    ]
)

results = run_experiment(
    "my-experiment",
    dataset=get_dataset(name="storyteller-dataset", project_name="new-project"),
    prompt_template=prompt,
    metrics=["correctness"],
    project="new-project",
)
```

Run an experiment with a runner function with local dataset:

```python
import openai
from splunk_ao.experiments import run_experiment


dataset = [
    {"name": "Lola"},
    {"name": "Jo"},
]

def runner(input):
    return openai.chat.completions.create(
        model="gpt-5.6-terra",
        messages=[
            {"role": "user", "content": f"Say hello: {input['name']}"}
        ],
    ).choices[0].message.content

run_experiment(
    "test experiment runner",
    project="awesome-new-project",
    dataset=dataset,
    function=runner,
    metrics=['output_tone'],
)
```

### Sessions

Sessions group related traces under the same conversation. To explicitly create
a named session:

```python
from splunk_ao import SplunkAOLogger

logger = SplunkAOLogger(project="gen-ai-project", agent_stream="my-agent-stream")
try:
    session_id = logger.start_session(name="my-session-name")
    # Log and conclude operations here.
finally:
    logger.terminate()
```

`start_session()` uses session CRUD in both deployment modes and requires
complete Project plus Agent Stream or experiment routing. The O11y Cloud
telemetry logger requires `SPLUNK_AO_O11Y_TOKEN`; session CRUD uses
`SPLUNK_AO_O11Y_API_TOKEN` when configured, otherwise the ingest token must
also include API permissions. Standalone uses its configured API credentials.

You can continue a previous session by using the same session ID that was
previously generated:

```python
from splunk_ao import SplunkAOLogger

logger = SplunkAOLogger(project="gen-ai-project", agent_stream="my-agent-stream")
try:
    logger.set_session(session_id="123e4567-e89b-12d3-a456-426614174000")
    # Log and conclude operations here.
finally:
    logger.terminate()
```

`set_session()` selects an existing session ID locally; it does not create or
validate a backend session.

You can create a session through the shared `splunk_ao_context` helper, which
uses the active context or environment routing:

```python
from splunk_ao import splunk_ao_context

session_id = splunk_ao_context.start_session(name="my-session-name")
```

To scope SDK logging and caller-wired OpenTelemetry spans to an existing
session, provide the session ID on the context:

```python
from splunk_ao import splunk_ao_context

with splunk_ao_context(
    project="gen-ai-project",
    agent_stream="my-agent-stream",
    session_id="123e4567-e89b-12d3-a456-426614174000",
):
    # Run related operations here.
    ...
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines and
[ARCHITECTURE.md](ARCHITECTURE.md) for repository structure, telemetry paths, and component ownership.
