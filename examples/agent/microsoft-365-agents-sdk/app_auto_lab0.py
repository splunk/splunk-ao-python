"""
app_auto_lab0.py — Auto-instrumentation via SplunkAOSpanProcessor → Splunk AO lab0.

  OpenAIAgentsTraceInstrumentor hooks into the OpenAI Agents SDK and emits spans
  automatically. SplunkAOSpanProcessor exports them to Splunk AO — no local collector
  or OTEL_EXPORTER_OTLP_ENDPOINT needed.

  Prerequisites:
    Copy .env.example to .env and fill in:
      SPLUNK_AO_REALM, SPLUNK_AO_O11Y_TOKEN, SPLUNK_AO_PROJECT, SPLUNK_AO_AGENT_STREAM
      AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY

  Run:    APP_MODE=auto_lab0 uv run python start_server.py
  Test:   npx @microsoft/m365agentsplayground  (or send a POST to /api/messages)
  Find:   Splunk AO → Agent Stream: microsoft-365-agents-sdk → service: m365-auto-lab0
"""

import os

from dotenv import load_dotenv
from opentelemetry import context as otel_context

load_dotenv(override=False)

# --- MS A365 Observability SDK: configure TracerProvider first ---------------
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

a365_configure(
    service_name=os.environ.get("OTEL_SERVICE_NAME", "m365-auto-lab0"),
    service_namespace="splunk.ao.demo",
)

# --- Attach SplunkAOSpanProcessor to the MS A365 TracerProvider --------------
from splunk_ao.otel import SplunkAOSpanProcessor, add_splunk_ao_span_processor

add_splunk_ao_span_processor(
    a365_get_tracer_provider(),
    SplunkAOSpanProcessor(
        project=os.environ.get("SPLUNK_AO_PROJECT"),
        agentstream=os.environ.get("SPLUNK_AO_AGENT_STREAM"),
    ),
)

# --- Auto-instrumentation: hooks into OpenAI Agents SDK tracing --------------
from microsoft_agents_a365.observability.extensions.openai import OpenAIAgentsTraceInstrumentor

OpenAIAgentsTraceInstrumentor().instrument()

# --- OpenAI Agents SDK (wraps Azure OpenAI) ----------------------------------
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

# --- Microsoft 365 Agents SDK ------------------------------------------------
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
    await context.send_activity("Hello! MS A365 auto-instrumentation (lab0) demo. Ask me anything.")


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

    with InvokeAgentScope.start(
        request, InvokeAgentScopeDetails(), agent_details,
        span_details=SpanDetails(parent_context=otel_context.get_current()),
    ):
        result = await Runner.run(_agent, input=user_text)
        reply = result.final_output

    await context.send_activity(reply)
