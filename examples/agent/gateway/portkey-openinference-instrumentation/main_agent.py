"""
Multi-span travel agent through Portkey AI Gateway.
Instrumentation: openinference-instrumentation-langchain + openinference-instrumentation-portkey

Both instrumentors active simultaneously:
  - openinference LangchainInstrumentor → LangGraph chain/step/tool spans [openinference semconv]
  - openinference PortkeyInstrumentor   → Completions spans [llm.*, full input/output JSON]

The Completions spans become children of the LangGraph step spans automatically via OTel context
propagation — LangGraph span is active when portkey_ai.Portkey.chat.completions.create() fires.

Span tree (fully auto-instrumented):
  LangGraph (chain)              [openinference.instrumentation.langchain]
    retrieval (chain)            [openinference.instrumentation.langchain]
    specialist (chain)           [openinference.instrumentation.langchain]
      Completions ×2             [openinference.instrumentation.portkey]
      mock_search_flights (tool) [openinference.instrumentation.langchain]
      mock_search_activities (tool) [openinference.instrumentation.langchain]
    synthesizer (chain)          [openinference.instrumentation.langchain]
      Completions                [openinference.instrumentation.portkey]
"""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timedelta
from typing import Annotated, Any, List, Optional, TypedDict
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.portkey import PortkeyInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from portkey_ai import Portkey

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# --- OTel setup: both instrumentors active ---
_provider = trace_sdk.TracerProvider(
    resource=Resource.create({"service.name": os.environ["OTEL_SERVICE_NAME"]})
)
_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] + "/v1/traces")
    )
)
trace_api.set_tracer_provider(_provider)
LangChainInstrumentor().instrument()  # framework spans: LangGraph chain, tool
PortkeyInstrumentor().instrument()    # LLM spans: Completions (via portkey_ai.Portkey)

# ---------------------------------------------------------------------------
# Mock data + tools
# ---------------------------------------------------------------------------

DESTINATIONS = {
    "paris": ["Eiffel Tower at sunset", "Seine dinner cruise", "Day trip to Versailles"],
    "tokyo": ["Tsukiji market food tour", "Ghibli Museum visit", "Day trip to Hakone"],
    "rome": ["Colosseum underground tour", "Private pasta masterclass", "Trastevere walk"],
    "sydney": ["Harbour Bridge climb", "Bondi to Coogee coastal walk", "Opera House tour"],
}

TRAVEL_KB: dict[str, list[str]] = {
    "rome": [
        "Book Colosseum skip-the-line tickets at least 2 weeks ahead in summer.",
        "Vatican Museums are closed on Sundays except the last Sunday of the month (free).",
        "Trastevere is the best neighbourhood for authentic Roman dining.",
        "Trenitalia connects Rome Termini to Naples in 70 min by high-speed rail.",
    ],
    "paris": [
        "Best time to visit Paris is April–June or September–October.",
        "A Navigo Week Pass covers all metro/bus zones for €30.",
        "Louvre is closed on Tuesdays; book timed-entry tickets in advance.",
    ],
    "sydney": [
        "BridgeClimb bookings must be made at least 24 hours in advance.",
        "Opal card is required for public transport; available at airport stores.",
    ],
    "tokyo": [
        "Cherry blossom season runs late March to mid April.",
        "IC cards (Suica/Pasmo) work on all trains and convenience stores.",
    ],
}

SCENARIOS = [
    ("Seattle", "Paris"),
    ("New York", "Tokyo"),
    ("San Francisco", "Rome"),
    ("Chicago", "Sydney"),
]


@tool
def mock_search_flights(origin: str, destination: str, departure: str) -> str:
    """Return mock flight options for a given route and date."""
    random.seed(hash((origin, destination, departure)) % (2**32))
    airline = random.choice(["SkyLine", "AeroJet", "CloudNine", "PacificAir"])
    fare = random.randint(650, 1400)
    return (
        f"{airline} non-stop {origin}→{destination}, depart {departure} 08:45, "
        f"arrive same day 18:30. Return premium economy ${fare}."
    )


@tool
def mock_search_activities(destination: str) -> str:
    """Return signature activities for the destination."""
    highlights = DESTINATIONS.get(destination.lower(), DESTINATIONS["paris"])
    return "Highlights:\n" + "\n".join(f"- {h}" for h in highlights)


# ---------------------------------------------------------------------------
# LangGraph state + nodes
# Each node calls portkey_ai.Portkey directly so PortkeyInstrumentor fires.
# LangGraph's active span is the OTel parent when Portkey calls are made.
# ---------------------------------------------------------------------------

class TripState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    session_id: str
    origin: str
    destination: str
    departure: str
    return_date: str
    retrieved_context: Optional[str]
    flight_summary: Optional[str]
    activities_summary: Optional[str]
    final_plan: Optional[str]


def _portkey_client(session_id: str) -> Portkey:
    return Portkey(
        api_key=os.environ["PORTKEY_API_KEY"],
        virtual_key=os.environ["PORTKEY_VIRTUAL_KEY"],
        trace_id=session_id,
        metadata={"_user": "erden"},
    )


def retrieval_node(state: TripState) -> TripState:
    docs = TRAVEL_KB.get(state["destination"].lower(), TRAVEL_KB["paris"])
    state["retrieved_context"] = "\n".join(f"- {d}" for d in docs)
    return state


def specialist_node(state: TripState) -> TripState:
    sid = state["session_id"]
    client = _portkey_client(sid)
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    context = state.get("retrieved_context") or ""
    origin, destination, departure = state["origin"], state["destination"], state["departure"]

    # LLM call 1 — PortkeyInstrumentor auto-creates Completions span as child of LangGraph step
    r1 = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": (
                "You are a travel specialist. Use tools to gather data, then summarise.\n\n"
                f"Destination knowledge base:\n{context}"
            )},
            {"role": "user", "content": (
                f"Plan a 7-day trip from {origin} to {destination} departing {departure}. "
                "Use the available tools to find a flight and activities, then summarise briefly."
            )},
        ],
    )
    step1 = r1.choices[0].message.content or ""

    flight_result = mock_search_flights.invoke({
        "origin": origin, "destination": destination, "departure": departure
    })
    activities_result = mock_search_activities.invoke({"destination": destination})

    # LLM call 2 — synthesis from tool results
    r2 = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": (
                "You are a travel specialist. Summarise the trip plan briefly.\n\n"
                f"Destination knowledge base:\n{context}"
            )},
            {"role": "user", "content": (
                f"Flight: {flight_result}\n\nActivities: {activities_result}\n\nSummarise."
            )},
        ],
    )
    summary = r2.choices[0].message.content or ""

    state["flight_summary"] = summary
    state["activities_summary"] = summary
    state["messages"].extend([HumanMessage(content=summary)])
    return state


def synthesizer_node(state: TripState) -> TripState:
    sid = state["session_id"]
    client = _portkey_client(sid)
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

    r = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": "You are a travel planner. Produce a concise 3-day itinerary."},
            {"role": "user", "content": (
                f"Trip: {state['origin']} → {state['destination']}, "
                f"{state['departure']} to {state['return_date']}.\n\n"
                f"Specialist notes:\n{state.get('flight_summary', '')}"
            )},
        ],
    )
    state["final_plan"] = r.choices[0].message.content or ""
    state["messages"].append(HumanMessage(content=state["final_plan"]))
    return state


def build_graph() -> Any:
    g = StateGraph(TripState)
    g.add_node("retrieval", retrieval_node)
    g.add_node("specialist", specialist_node)
    g.add_node("synthesizer", synthesizer_node)
    g.add_edge(START, "retrieval")
    g.add_edge("retrieval", "specialist")
    g.add_edge("specialist", "synthesizer")
    g.add_edge("synthesizer", END)
    return g.compile()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run() -> None:
    session_id = str(uuid4())
    origin, destination = random.choice(SCENARIOS)
    departure = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return_date = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")

    log.info("run started session=%s route=%s->%s", session_id, origin, destination)

    app = build_graph()
    initial: TripState = {
        "messages": [HumanMessage(content=f"Plan a trip from {origin} to {destination}.")],
        "session_id": session_id,
        "origin": origin,
        "destination": destination,
        "departure": departure,
        "return_date": return_date,
        "retrieved_context": None,
        "flight_summary": None,
        "activities_summary": None,
        "final_plan": None,
    }

    final = app.invoke(initial, config={"configurable": {"thread_id": session_id}})
    plan = final.get("final_plan", "")
    log.info("run completed session=%s plan_chars=%d", session_id, len(plan))
    if plan:
        log.info("plan=%s", plan[:300])

    _provider.force_flush()


if __name__ == "__main__":
    run()
