# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import json
import os
import random
from datetime import datetime, timedelta
from typing import Annotated, TypedDict
from uuid import uuid4

import dotenv
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from opentelemetry import trace as trace_api
from opentelemetry.instrumentation.genai.langchain import LangChainInstrumentor
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource

from splunk_ao import otel, splunk_ao_context

# logging.basicConfig(
#   level=logging.INFO,
#   format="%(levelname)s:%(name)s:%(message)s",
# )

# final_span_logger = logging.getLogger("splunk_ao.exporter.span_transform")
# final_span_logger.setLevel(logging.DEBUG)
# final_span_logger.propagate = False
#
# final_span_handler = logging.StreamHandler()
# final_span_handler.setLevel(logging.DEBUG)
# final_span_handler.setFormatter(
#   logging.Formatter("%(levelname)s:%(name)s:%(message)s")
# )
# final_span_logger.addHandler(final_span_handler)

dotenv.load_dotenv()


DESTINATIONS = {
    "paris": {
        "airport": "CDG",
        "highlights": ["Eiffel Tower at sunset", "Seine dinner cruise", "Day trip to Versailles"],
    },
    "tokyo": {
        "airport": "HND",
        "highlights": ["Tsukiji market food tour", "Ghibli Museum visit", "Day trip to Hakone hot springs"],
    },
    "rome": {
        "airport": "FCO",
        "highlights": ["Colosseum underground tour", "Private pasta masterclass", "Sunset walk through Trastevere"],
    },
}

USER_REQUESTS = (
    (
        "We're planning a romantic week-long trip to Paris from Seattle next month. "
        "We'd love a boutique hotel, business-class flights, and unique experiences."
    ),
    (
        "We're organizing a week-long food and culture trip to Tokyo from New York next month. "
        "We'd like a modern hotel, business-class flights, and memorable local experiences."
    ),
    (
        "We're planning a relaxed week-long getaway to Rome from San Francisco next month. "
        "We'd love a historic boutique hotel, business-class flights, and hands-on culinary experiences."
    ),
    (
        "We're arranging a romantic week-long escape to Paris from London next month. "
        "We'd like an intimate hotel, first-class flights, and distinctive art and dining experiences."
    ),
    (
        "We're planning an adventurous week-long holiday to Tokyo from Seattle next month. "
        "We'd love a design-focused hotel, premium flights, and a mix of food, nature, and cultural experiences."
    ),
)


class PlannerState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_request: str
    session_id: str
    origin: str
    destination: str
    departure: str
    return_date: str
    travellers: int
    flight_summary: str | None
    hotel_summary: str | None
    activities_summary: str | None
    final_itinerary: str | None
    current_agent: str


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-nano")


def _create_llm(agent_name: str, session_id: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=_model_name(),
        tags=[f"agent:{agent_name}", "travel-planner"],
        metadata={
            "agent_name": agent_name,
            "agent_type": agent_name,
            "session_id": session_id,
            "thread_id": session_id,
            "ls_model_name": _model_name(),
        },
    )


def _pick_destination(user_request: str) -> str:
    lowered = user_request.lower()
    for name in DESTINATIONS:
        if name in lowered:
            return name.title()
    return "Paris"


def _pick_origin(user_request: str) -> str:
    lowered = user_request.lower()
    for city in ("seattle", "new york", "san francisco", "london"):
        if city in lowered:
            return city.title()
    return "Seattle"


def _pick_user_request() -> str:
    return random.choice(USER_REQUESTS)


def _compute_dates() -> tuple[str, str]:
    start = datetime.now() + timedelta(days=30)
    end = start + timedelta(days=7)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _message_text(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    return json.dumps(message.content)


@tool
def mock_search_flights(origin: str, destination: str, departure: str) -> str:
    """Return mock flight options for an origin and destination."""
    random.seed(hash((origin, destination, departure)) % (2**32))
    airline = random.choice(["SkyLine", "AeroJet", "CloudNine"])
    fare = random.randint(700, 1250)
    return (
        f"Top choice: {airline} non-stop service {origin}->{destination}, "
        f"depart {departure} 09:15, arrive {departure} 17:05. "
        f"Premium economy fare ${fare} return."
    )


@tool
def mock_search_hotels(destination: str, check_in: str, check_out: str) -> str:
    """Return a mock hotel recommendation for a stay."""
    random.seed(hash((destination, check_in, check_out)) % (2**32))
    name = random.choice(["Grand Meridian", "Hotel Lumière", "The Atlas"])
    rate = random.randint(240, 410)
    return (
        f"{name} near the historic centre. Boutique suites, rooftop bar, "
        f"average nightly rate ${rate} including breakfast."
    )


@tool
def mock_search_activities(destination: str) -> str:
    """Return signature activities for a destination."""
    data = DESTINATIONS.get(destination.lower(), DESTINATIONS["paris"])
    highlights = data["highlights"]
    assert isinstance(highlights, list)
    bullets = "\n".join(f"- {item}" for item in highlights)
    return f"Signature experiences in {destination.title()}:\n{bullets}"


def _configured_agent(agent_name: str, state: PlannerState, tools: list[BaseTool]) -> Runnable:
    return create_agent(_create_llm(agent_name, state["session_id"]), tools=tools).with_config(
        {
            "run_name": agent_name,
            "tags": ["agent", f"agent:{agent_name}"],
            "metadata": {
                "agent_name": agent_name,
                "session_id": state["session_id"],
                "conversation_id": state["session_id"],
            },
        }
    )


def coordinator_node(state: PlannerState) -> PlannerState:
    agent = _configured_agent("coordinator", state, tools=[])
    prompt = (
        "You are the lead travel coordinator. Extract the key details from the "
        "traveller's request and describe the plan for the specialist agents."
    )
    result = agent.invoke({"messages": [SystemMessage(content=prompt), *state["messages"]]})
    state["messages"].append(result["messages"][-1])
    state["current_agent"] = "flight_specialist"
    return state


def flight_specialist_node(state: PlannerState) -> PlannerState:
    agent = _configured_agent("flight_specialist", state, tools=[mock_search_flights])
    prompt = (
        f"Find an appealing flight from {state['origin']} to "
        f"{state['destination']} departing {state['departure']} for "
        f"{state['travellers']} travellers."
    )
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    message = result["messages"][-1]
    state["flight_summary"] = _message_text(message)
    state["messages"].append(message)
    state["current_agent"] = "hotel_specialist"
    return state


def hotel_specialist_node(state: PlannerState) -> PlannerState:
    agent = _configured_agent("hotel_specialist", state, tools=[mock_search_hotels])
    prompt = (
        f"Recommend a boutique hotel in {state['destination']} between "
        f"{state['departure']} and {state['return_date']} for "
        f"{state['travellers']} travellers."
    )
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    message = result["messages"][-1]
    state["hotel_summary"] = _message_text(message)
    state["messages"].append(message)
    state["current_agent"] = "activity_specialist"
    return state


def activity_specialist_node(state: PlannerState) -> PlannerState:
    agent = _configured_agent("activity_specialist", state, tools=[mock_search_activities])
    prompt = f"Curate signature activities for a week in {state['destination']}."
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    message = result["messages"][-1]
    state["activities_summary"] = _message_text(message)
    state["messages"].append(message)
    state["current_agent"] = "plan_synthesizer"
    return state


def plan_synthesizer_node(state: PlannerState) -> PlannerState:
    llm = _create_llm("plan_synthesizer", state["session_id"])
    system_prompt = (
        "You are the travel plan synthesizer. Combine the specialist insights into "
        "a concise itinerary covering flights, accommodation, and activities."
    )
    summaries = json.dumps(
        {"flight": state["flight_summary"], "hotel": state["hotel_summary"], "activities": state["activities_summary"]},
        indent=2,
    )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Traveller request: {state['user_request']}\n\n"
                    f"Origin: {state['origin']} | Destination: "
                    f"{state['destination']}\n"
                    f"Dates: {state['departure']} to {state['return_date']}\n\n"
                    f"Specialist summaries:\n{summaries}"
                )
            ),
        ]
    )
    state["final_itinerary"] = _message_text(response)
    state["messages"].append(response)
    state["current_agent"] = "completed"
    return state


def should_continue(state: PlannerState) -> str:
    return {
        "start": "coordinator",
        "flight_specialist": "flight_specialist",
        "hotel_specialist": "hotel_specialist",
        "activity_specialist": "activity_specialist",
        "plan_synthesizer": "plan_synthesizer",
    }.get(state["current_agent"], END)


def build_workflow() -> StateGraph:
    graph = StateGraph(PlannerState)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("flight_specialist", flight_specialist_node)
    graph.add_node("hotel_specialist", hotel_specialist_node)
    graph.add_node("activity_specialist", activity_specialist_node)
    graph.add_node("plan_synthesizer", plan_synthesizer_node)
    graph.add_conditional_edges(START, should_continue)
    graph.add_conditional_edges("coordinator", should_continue)
    graph.add_conditional_edges("flight_specialist", should_continue)
    graph.add_conditional_edges("hotel_specialist", should_continue)
    graph.add_conditional_edges("activity_specialist", should_continue)
    graph.add_conditional_edges("plan_synthesizer", should_continue)
    return graph


def configure_telemetry() -> trace_sdk.TracerProvider:
    resource = Resource.create(
        {
            "service.name": "multi-agent-travel-planner",
            "service.version": "1.0.0",
            "deployment.environment": "development",
        }
    )
    tracer_provider = trace_sdk.TracerProvider(resource=resource)
    otel.add_splunk_ao_span_processor(tracer_provider)
    trace_api.set_tracer_provider(tracer_provider=tracer_provider)
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    return tracer_provider


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")

    tracer_provider = configure_telemetry()
    # random session id generated for every run, change this to a static id if you need one session for all runs.
    session_id = str(uuid4())
    user_request = _pick_user_request()
    departure, return_date = _compute_dates()
    initial_state: PlannerState = {
        "messages": [HumanMessage(content=user_request)],
        "user_request": user_request,
        "session_id": session_id,
        "origin": _pick_origin(user_request),
        "destination": _pick_destination(user_request),
        "departure": departure,
        "return_date": return_date,
        "travellers": 2,
        "flight_summary": None,
        "hotel_summary": None,
        "activities_summary": None,
        "final_itinerary": None,
        "current_agent": "start",
    }
    config = {
        "configurable": {"thread_id": session_id},
        "metadata": {"session_id": session_id, "conversation_id": session_id},
        "recursion_limit": 10,
    }

    print("🌍 Multi-Agent Travel Planner")
    print("=" * 60)

    final_state: PlannerState | None = None
    try:
        with splunk_ao_context(session_id=session_id):
            for step in build_workflow().compile().stream(initial_state, config):
                node_name, node_state = next(iter(step.items()))
                final_state = node_state
                print(f"\n🤖 {node_name.replace('_', ' ').title()} Agent")
                if node_state.get("messages"):
                    preview = _message_text(node_state["messages"][-1])
                    if len(preview) > 400:
                        preview = f"{preview[:400]}... [truncated]"
                    print(preview)

        final_plan = final_state.get("final_itinerary") if final_state else None
        if final_plan:
            print(f"\n🎉 Final itinerary\n{'-' * 40}\n{final_plan}")
        else:
            print("❌ No itinerary was generated.")
    finally:
        tracer_provider.shutdown()


if __name__ == "__main__":
    main()
