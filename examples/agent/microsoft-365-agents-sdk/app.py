"""
Microsoft 365 Agents SDK Q&A agent with Splunk AO OTel instrumentation.

Instrumentation:
  - SplunkAOSpanProcessor() exports spans to Splunk AO via OTLP.
  - opentelemetry-instrumentation-openai-v2 auto-instruments the Azure OpenAI call,
    emitting gen_ai.* spans with input/output content.

Auth:
  - MicrosoftAppId/Password empty → AnonymousTokenProvider (local playground only).
  - MicrosoftAppId/Password set → MsalConnectionManager (Teams / Copilot / production).

Run:
  python start_server.py
Test locally:
  npx @microsoft/m365agentsplayground
"""

import os

from dotenv import load_dotenv

load_dotenv(override=True)

# --- OTel setup (must happen before any instrumented client is created) ---
from openai import AzureOpenAI
from opentelemetry import trace
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from splunk_ao.otel import SplunkAOSpanProcessor

resource = Resource.create({"service.name": "microsoft-365-agents-sdk-example"})
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(SplunkAOSpanProcessor())

trace.set_tracer_provider(tracer_provider)

OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# --- Azure OpenAI client ---
_openai_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)
_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

# --- Microsoft 365 Agents SDK ---
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import AgentApplication, MemoryStorage, TurnContext, TurnState
from microsoft_agents.hosting.core.authorization import AgentAuthConfiguration, AnonymousTokenProvider, ConnectionManager

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

AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE, adapter=ADAPTER, connection_manager=_connection_manager
)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):
    await context.send_activity("Hello! Ask me anything and I'll answer using Azure OpenAI.")


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, state: TurnState):
    user_text = context.activity.text or ""
    if not user_text.strip():
        await context.send_activity("Please send a message.")
        return

    response = _openai_client.chat.completions.create(
        model=_deployment,
        messages=[
            {"role": "system", "content": "You are a concise, helpful assistant."},
            {"role": "user", "content": user_text},
        ],
        max_tokens=512,
    )
    reply = response.choices[0].message.content or ""
    await context.send_activity(reply)
