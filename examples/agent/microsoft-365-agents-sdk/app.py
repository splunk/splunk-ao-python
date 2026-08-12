"""
Microsoft 365 Agents SDK demo — MS A365 auto-instrumentation via OpenAIAgentsTraceInstrumentor.

Instrumentation:
  - OpenAIAgentsTraceInstrumentor hooks into OpenAI Agents SDK tracing → emits gen_ai.* spans.
  - InvokeAgentScope wraps each turn manually (no auto-instrumentor for M365 turn layer yet).
  - All spans → OTLP → local collector.

Run:    uv run python start_server.py
Test:   npx @microsoft/m365agentsplayground
"""

import os

from dotenv import load_dotenv
from opentelemetry import context as otel_context

load_dotenv(override=False)

# --- MS A365 Observability SDK: configure first, then attach OTLP exporter ---
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from microsoft_agents_a365.observability.core import (
    AgentDetails,
    Channel,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    Request,
    SpanDetails,
    configure as a365_configure,
    get_tracer_provider as a365_get_tracer_provider,
)

a365_configure(service_name="m365-splunk-ao-demo", service_namespace="splunk.ao.demo")

_otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
a365_get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{_otlp_endpoint}/v1/traces"))
)

# --- Auto-instrumentation: hooks into OpenAI Agents SDK tracing ---
from microsoft_agents_a365.observability.extensions.openai import OpenAIAgentsTraceInstrumentor

OpenAIAgentsTraceInstrumentor().instrument()

# --- OpenAI Agents SDK (wraps Azure OpenAI) ---
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncAzureOpenAI

_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
_azure_client = AsyncAzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)
_agent = Agent(
    name="QAAgent",
    instructions="You are a concise, helpful assistant.",
    model=OpenAIChatCompletionsModel(model=_deployment, openai_client=_azure_client),
)

# --- Splunk AO Logger (optional — skipped without creds) ---
from splunk_ao import SplunkAOLogger

_ao_logger: SplunkAOLogger | None = None
if os.environ.get("SPLUNK_AO_API_KEY") or os.environ.get("SPLUNK_AO_REALM"):
    _ao_logger = SplunkAOLogger()
else:
    print("[splunk-ao] No credentials — otel-tui-only mode.")

# --- Microsoft 365 Agents SDK ---
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import AgentApplication, MemoryStorage, TurnContext, TurnState
from microsoft_agents.hosting.core.authorization import (
    AgentAuthConfiguration,
    AnonymousTokenProvider,
    ConnectionManager,
)

_app_id = os.environ.get("MicrosoftAppId", "")
_app_password = os.environ.get("MicrosoftAppPassword", "")
_tenant_id = os.environ.get("MicrosoftAppTenantId", "")

if _app_id and _app_password:
    from microsoft_agents.authentication.msal import MsalConnectionManager
    _connection_manager = MsalConnectionManager(
        connections_configurations={
            "SERVICE_CONNECTION": AgentAuthConfiguration(
                client_id=_app_id,
                client_secret=_app_password,
                tenant_id=_tenant_id or "common",
            )
        }
    )
else:
    _connection_manager = ConnectionManager(
        provider_factory=lambda config: AnonymousTokenProvider(),
        connections_configurations={"SERVICE_CONNECTION": AgentAuthConfiguration(anonymous_allowed=True)},
    )

STORAGE = MemoryStorage()
ADAPTER = CloudAdapter(connection_manager=_connection_manager)
AGENT_APP = AgentApplication[TurnState](storage=STORAGE, adapter=ADAPTER, connection_manager=_connection_manager)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState) -> None:
    await context.send_activity("Hello! MS A365 auto-instrumentation demo. Ask me anything.")


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, state: TurnState) -> None:
    user_text = context.activity.text or ""
    if not user_text.strip():
        await context.send_activity("Please send a message.")
        return

    conv_id = context.activity.conversation.id if context.activity.conversation else "unknown"
    channel_id = context.activity.channel_id or "unknown"

    request = Request(
        content=user_text,
        session_id=conv_id,
        conversation_id=conv_id,
        channel=Channel(name=channel_id),
    )
    agent_details = AgentDetails(agent_id="m365-splunk-ao-demo", agent_name="M365 Splunk AO Demo Agent")

    # InvokeAgentScope: manual turn-level span (no auto-instrumentor for M365 turn layer)
    with InvokeAgentScope.start(
        request, InvokeAgentScopeDetails(), agent_details,
        span_details=SpanDetails(parent_context=otel_context.get_current()),
    ):
        # OpenAI Agents SDK run — auto-instrumented by OpenAIAgentsTraceInstrumentor
        result = await Runner.run(_agent, input=user_text)
        reply = result.final_output

        # Splunk AO Logger (optional)
        if _ao_logger:
            _ao_logger.start_session(name=conv_id, metadata={"channel": channel_id})
            _ao_logger.start_trace(input=user_text, metadata={"conversation_id": conv_id})
            _ao_logger.conclude(output=reply)
            _ao_logger.flush()

    await context.send_activity(reply)
