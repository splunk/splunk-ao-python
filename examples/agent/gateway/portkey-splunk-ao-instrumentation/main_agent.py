"""
Multi-span travel agent through Portkey AI Gateway.
Instrumentation: splunk-ao[langchain] — SplunkAOAsyncCallback + LangGraph

Span tree (via Splunk AO logger path, same as healthcare-assistant):
  session
    invoke_agent LangGraph
      step retrieval
        retrieval
      step specialist
        chat @<your-virtual-key-slug>/gpt-4.1-mini ×2
        execute_tool ×2
      step synthesizer
        chat @<your-virtual-key-slug>/gpt-4.1-mini
  → routes to Splunk AO project
"""

from __future__ import annotations

import asyncio
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
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders
from splunk_ao import splunk_ao_context
from splunk_ao.handlers.langchain import SplunkAOAsyncCallback

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

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


def retrieve_destination_context(destination: str, query: str) -> list[str]:
    return TRAVEL_KB.get(destination.lower(), TRAVEL_KB["paris"])


# ---------------------------------------------------------------------------
# LangGraph state + nodes
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


def _create_llm(session_id: str, temperature: float = 0.3) -> ChatOpenAI:
    portkey_headers = createHeaders(
        api_key=os.environ["PORTKEY_API_KEY"],
        trace_id=session_id,
    )
    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "@<your-virtual-key-slug>/gpt-4.1-mini"),
        temperature=temperature,
        base_url=PORTKEY_GATEWAY_URL,
        api_key=os.environ["PORTKEY_API_KEY"],
        default_headers=portkey_headers,
        metadata={"session_id": session_id},
    )


def retrieval_node(state: TripState) -> TripState:
    query = f"travel tips for {state['destination']}"
    docs = retrieve_destination_context(state["destination"], query)
    state["retrieved_context"] = "\n".join(f"- {d}" for d in docs)
    return state


def specialist_node(state: TripState) -> TripState:
    sid = state["session_id"]
    llm = _create_llm(sid, temperature=0.4)
    llm_with_tools = llm.bind_tools([mock_search_flights, mock_search_activities])

    context = state.get("retrieved_context") or ""
    prompt = (
        f"Plan a 7-day trip from {state['origin']} to {state['destination']} "
        f"departing {state['departure']}. Use the available tools to find a flight "
        f"and activities, then summarise your findings briefly."
    )
    messages = [
        SystemMessage(content=(
            "You are a travel specialist. Use tools to gather data, then summarise.\n\n"
            f"Destination knowledge base:\n{context}"
        )),
        HumanMessage(content=prompt),
    ]

    response = llm_with_tools.invoke(messages)
    messages.append(response)

    for tc in getattr(response, "tool_calls", []):
        selected = {
            "mock_search_flights": mock_search_flights,
            "mock_search_activities": mock_search_activities,
        }.get(tc["name"])
        if selected:
            tool_result = selected.invoke(tc)
            messages.append(tool_result)

    if getattr(response, "tool_calls", []):
        final = llm_with_tools.invoke(messages)
        messages.append(final)
        summary = final.content if isinstance(final.content, str) else str(final.content)
    else:
        summary = response.content if isinstance(response.content, str) else str(response.content)

    state["flight_summary"] = summary
    state["activities_summary"] = summary
    state["messages"].extend([m for m in messages if isinstance(m, BaseMessage)])
    return state


def synthesizer_node(state: TripState) -> TripState:
    sid = state["session_id"]
    llm = _create_llm(sid, temperature=0.3)

    response = llm.invoke([
        SystemMessage(content="You are a travel planner. Produce a concise 3-day itinerary."),
        HumanMessage(content=(
            f"Trip: {state['origin']} → {state['destination']}, "
            f"{state['departure']} to {state['return_date']}.\n\n"
            f"Specialist notes:\n{state.get('flight_summary', '')}"
        )),
    ])
    state["final_plan"] = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    state["messages"].append(response)
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

async def run_once() -> None:
    session_id = str(uuid4())
    origin, destination = random.choice(SCENARIOS)
    departure = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return_date = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")

    log.info("run started session=%s route=%s->%s departure=%s", session_id, origin, destination, departure)

    callback = SplunkAOAsyncCallback(flush_on_chain_end=True)
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

    with splunk_ao_context(
        project=os.environ.get("SPLUNK_AO_PROJECT"),
        agent_stream=os.environ.get("SPLUNK_AO_AGENT_STREAM"),
        session_id=session_id,
    ):
        final = await app.ainvoke(
            initial,
            config={
                "configurable": {"thread_id": session_id},
                "callbacks": [callback],
            },
        )

    plan = final.get("final_plan", "")
    log.info("run completed session=%s plan_chars=%d", session_id, len(plan))
    if plan:
        log.info("plan_preview=%s", plan[:300] + ("..." if len(plan) > 300 else ""))


if __name__ == "__main__":
    asyncio.run(run_once())
