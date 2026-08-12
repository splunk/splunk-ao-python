"""
app_manual_lab0.py — Manual instrumentation via SplunkAOLogger → Splunk AO lab0.

  SplunkAOLogger is used directly in the turn handler to build the trace hierarchy:
    trace        → invoke_agent M365 Splunk AO Demo Agent
      agent_span → Agent workflow
        agent_span → invoke_agent QAAgent
          agent_span → turn
            llm_span → chat gpt-4o-mini

  Session is created once per conversation (conv_id as external_id) so multi-turn
  messages in the same Teams conversation are grouped under one session.

  Prerequisites:
    Copy .env.example to .env and fill in:
      SPLUNK_AO_REALM, SPLUNK_AO_O11Y_TOKEN, SPLUNK_AO_PROJECT, SPLUNK_AO_AGENT_STREAM
      AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY

  Run:    APP_MODE=manual_lab0 uv run python start_server.py
  Test:   npx @microsoft/m365agentsplayground  (or send a POST to /api/messages)
  Find:   Splunk AO → Agent Stream: microsoft-365-agents-sdk → service: m365-manual-lab0
"""

import os
import time

from dotenv import load_dotenv

load_dotenv(override=False)

os.environ.setdefault("OTEL_SERVICE_NAME", "m365-manual-lab0")

# --- Splunk AO Logger --------------------------------------------------------
from splunk_ao import SplunkAOLogger

_logger = SplunkAOLogger(
    project=os.environ.get("SPLUNK_AO_PROJECT"),
    agent_stream=os.environ.get("SPLUNK_AO_AGENT_STREAM"),
)

# conv_id → session_id; avoids a network round-trip on every turn
_session_cache: dict[str, str] = {}

# --- Direct Azure OpenAI client ----------------------------------------------
from openai import AzureOpenAI

_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
_azure_client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
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
    await context.send_activity("Hello! MS 365 manual-instrumentation (lab0) demo. Ask me anything.")


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, state: TurnState) -> None:
    user_text = context.activity.text or ""
    if not user_text.strip():
        await context.send_activity("Please send a message.")
        return

    conv_id = context.activity.conversation.id if context.activity.conversation else "unknown"
    channel_id = context.activity.channel_id or "unknown"

    # --- Session: one per conversation, server-side deduped by conv_id -------
    if conv_id not in _session_cache:
        session_id = _logger.start_session(
            external_id=conv_id,
            metadata={"channel": channel_id},
        )
        _session_cache[conv_id] = session_id
    _logger.set_session(_session_cache[conv_id])

    # -------------------------------------------------------------------------
    # Trace hierarchy (mirrors auto-instrumented span tree):
    #
    #   start_trace      "invoke_agent M365 Splunk AO Demo Agent"
    #     add_agent_span   "Agent workflow"
    #       add_agent_span   "invoke_agent QAAgent"
    #         add_agent_span   "turn"
    #           add_llm_span     gpt-4o-mini
    #         conclude  ← turn
    #       conclude    ← invoke_agent QAAgent
    #     conclude      ← Agent workflow
    #   conclude        ← trace
    # -------------------------------------------------------------------------
    t0 = time.monotonic_ns()

    _logger.start_trace(input=user_text, name="invoke_agent M365 Splunk AO Demo Agent")
    _logger.add_agent_span(input=user_text, name="Agent workflow")
    _logger.add_agent_span(input=user_text, name="invoke_agent QAAgent")
    _logger.add_agent_span(input=user_text, name="turn")

    t_llm = time.monotonic_ns()
    response = _azure_client.chat.completions.create(
        model=_deployment,
        messages=[
            {"role": "system", "content": "You are a concise, helpful assistant."},
            {"role": "user", "content": user_text},
        ],
    )
    llm_elapsed_ns = time.monotonic_ns() - t_llm

    reply = response.choices[0].message.content or ""
    usage = response.usage

    _logger.add_llm_span(
        input=user_text,
        output=reply,
        model=_deployment,
        num_input_tokens=usage.prompt_tokens if usage else None,
        num_output_tokens=usage.completion_tokens if usage else None,
        total_tokens=usage.total_tokens if usage else None,
        duration_ns=llm_elapsed_ns,
    )

    total_elapsed_ns = time.monotonic_ns() - t0
    _logger.conclude(output=reply, duration_ns=total_elapsed_ns)  # turn
    _logger.conclude(output=reply, duration_ns=total_elapsed_ns)  # invoke_agent QAAgent
    _logger.conclude(output=reply, duration_ns=total_elapsed_ns)  # Agent workflow
    _logger.conclude(output=reply, duration_ns=total_elapsed_ns)  # trace
    _logger.flush()

    await context.send_activity(reply)
