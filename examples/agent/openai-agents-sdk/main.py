"""
Travel agent demo using the OpenAI Agents SDK with Splunk AO instrumentation.

Two instrumentation modes, selected with the INSTRUMENTATION environment variable:

  sdk  (default)  SplunkAOTracingProcessor, registered through the Agents SDK's
                  set_trace_processors() hook.
  otel            The community OpenTelemetry instrumentation for the Agents SDK,
                  with Splunk AO attached to a tracer provider through
                  add_splunk_ao_span_processor(). Needs the extra package listed
                  in requirements.txt.

The agent is a single TravelAgent with two mock tools (flight search and activity
search), so every run makes at least one tool-calling turn followed by a final answer.

Run:
  INSTRUMENTATION=sdk  python main.py
  INSTRUMENTATION=otel python main.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("openai-agents-demo")

# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

from agents import Agent, Runner, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

# The client reads OPENAI_API_KEY and, if set, OPENAI_BASE_URL from the environment, so it works with
# OpenAI or with any OpenAI-compatible endpoint (for example a LiteLLM proxy).
_client = AsyncOpenAI()
_model = OpenAIChatCompletionsModel(
    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    openai_client=_client,
)

# ---------------------------------------------------------------------------
# Mock tools (deterministic data, no external services)
# ---------------------------------------------------------------------------

DESTINATIONS = {
    "paris": ["Eiffel Tower at sunset", "Seine dinner cruise", "Day trip to Versailles"],
    "tokyo": ["Tsukiji market food tour", "Ghibli Museum visit", "Day trip to Hakone"],
    "rome": ["Colosseum underground tour", "Private pasta masterclass", "Trastevere walk"],
    "sydney": ["Harbour Bridge climb", "Bondi to Coogee coastal walk", "Opera House tour"],
}

SCENARIOS = [
    ("Seattle", "Paris"),
    ("New York", "Tokyo"),
    ("San Francisco", "Rome"),
    ("Chicago", "Sydney"),
]


@function_tool
def mock_search_flights(origin: str, destination: str, departure: str) -> str:
    """Return mock flight options for a given route and date."""
    random.seed(hash((origin, destination, departure)) % (2**32))
    airline = random.choice(["SkyLine", "AeroJet", "CloudNine", "PacificAir"])
    fare = random.randint(650, 1400)
    return (
        f"{airline} non-stop {origin}→{destination}, depart {departure} 08:45, "
        f"arrive same day 18:30. Return premium economy ${fare}."
    )


@function_tool
def mock_search_activities(destination: str) -> str:
    """Return signature activities for the destination."""
    highlights = DESTINATIONS.get(destination.lower(), DESTINATIONS["paris"])
    return "Highlights:\n" + "\n".join(f"- {h}" for h in highlights)


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

_agent = Agent(
    name="TravelAgent",
    instructions=(
        "You are a travel specialist. Use mock_search_flights and mock_search_activities "
        "to gather data, then summarise the trip plan briefly."
    ),
    model=_model,
    tools=[mock_search_flights, mock_search_activities],
)

# ---------------------------------------------------------------------------
# Instrumentation setup
# ---------------------------------------------------------------------------

INSTRUMENTATION = os.environ.get("INSTRUMENTATION", "sdk").lower()

if INSTRUMENTATION == "otel":
    # OpenTelemetry path: community Agents SDK instrumentation + a Splunk AO span processor
    from opentelemetry import trace as trace_api
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry.sdk.resources import Resource
    from splunk_ao.otel import SplunkAOSpanProcessor, add_splunk_ao_span_processor

    _resource = Resource.create({"service.name": "openai-agents-demo"})
    _provider = trace_sdk.TracerProvider(resource=_resource)
    add_splunk_ao_span_processor(
        _provider,
        SplunkAOSpanProcessor(
            project=os.environ.get("SPLUNK_AO_PROJECT"),
            agentstream=os.environ.get("SPLUNK_AO_AGENT_STREAM"),
        ),
    )
    trace_api.set_tracer_provider(_provider)

    try:
        from opentelemetry.instrumentation.genai.openai_agents import OpenAIAgentsInstrumentor
        # Keep the Agents SDK's default exporter from also sending traces to OpenAI's tracing backend.
        OpenAIAgentsInstrumentor().instrument(disable_openai_trace_export=True)
        log.info("OpenAIAgentsInstrumentor active")
    except ImportError:
        log.warning(
            "opentelemetry-instrumentation-genai-openai-agents is not installed. "
            "Run: pip install opentelemetry-instrumentation-genai-openai-agents"
        )

else:
    # SDK path: SplunkAOTracingProcessor registered through the Agents SDK's trace-processor hook
    from agents import set_trace_processors
    from splunk_ao.handlers.openai_agents import SplunkAOTracingProcessor

    set_trace_processors([SplunkAOTracingProcessor(flush_on_trace_end=True)])
    log.info("SplunkAOTracingProcessor active")

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


async def run_once() -> None:
    session_id = str(uuid4())
    origin, destination = random.choice(SCENARIOS)
    departure = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    prompt = (
        f"Plan a 7-day trip from {origin} to {destination} departing {departure}. "
        f"Use the available tools to find a flight and activities, then summarise briefly."
    )

    log.info(
        "run started session=%s route=%s->%s instrumentation=%s",
        session_id, origin, destination, INSTRUMENTATION,
    )

    if INSTRUMENTATION == "sdk":
        from splunk_ao import splunk_ao_context
        with splunk_ao_context(
            project=os.environ.get("SPLUNK_AO_PROJECT"),
            agent_stream=os.environ.get("SPLUNK_AO_AGENT_STREAM"),
            session_id=session_id,
        ):
            result = await Runner.run(_agent, input=prompt)
    else:
        result = await Runner.run(_agent, input=prompt)

    log.info("run completed session=%s answer_chars=%d", session_id, len(result.final_output or ""))
    log.info("answer=%s", (result.final_output or "")[:300])

    if INSTRUMENTATION == "otel":
        _provider.force_flush()


if __name__ == "__main__":
    asyncio.run(run_once())
