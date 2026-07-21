"""FastAPI HTTP wrapper around the langchain-agent example.

Exposes POST /invoke and POST /invoke/nested endpoints that accept a JSON body
with a `prompt` field, pass it to a LangGraph ReAct agent, and return the response.

This mirrors the "Scenarios" test layout from splunk-otel-python-contrib PR #236:
  • HTTP span (FastAPI request) → GenAI Workflow span (LangChain/LangGraph agent)
  • The Workflow span has no GenAI parent, so `gen_ai.conversation_root` is set
    to True via the auto-detection logic in SplunkAOLogger.add_workflow_span()
    (native path) and start_splunk_ao_span() (OTel path).

Verification:
  1. Start the server:
       uvicorn app:app --reload --port 8080
  2. Send a request:
       curl -X POST http://localhost:8080/invoke \\
            -H "Content-Type: application/json" \\
            -d '{"prompt": "Say hello to Erin"}'
  3. Observe the trace in the Splunk AO console at SPLUNK_AO_CONSOLE_URL and
     confirm the root WorkflowSpan carries gen_ai.conversation_root=true in its
     user_metadata (and on the LoggedWorkflowSpan.conversation_root field).

Environment variables (see .env.example):
  SPLUNK_AO_API_KEY, SPLUNK_AO_API_URL, SPLUNK_AO_PROJECT, SPLUNK_AO_LOG_STREAM,
  OPENAI_API_KEY (or OPENAI_BASE_URL + AZURE_OPENAI_* for Azure).
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from splunk_ao import splunk_ao_context
from splunk_ao.handlers.langchain import SplunkAOCallback

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LangChain Agent HTTP — gen_ai.conversation_root demo",
    description="Wraps a LangGraph ReAct agent in FastAPI for e2e conversation-root tracing verification.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Agent setup — built once at startup, reused across requests.
# ---------------------------------------------------------------------------

_PROJECT = os.getenv("SPLUNK_AO_PROJECT", "langchain-http-demo")
_LOG_STREAM = os.getenv("SPLUNK_AO_LOG_STREAM", "langchain-http")


@tool
def greet(name: str) -> str:
    """Say hello to someone by name."""
    return f"Hello, {name}! 👋"


@tool
def get_weather(city: str) -> str:
    """Return a made-up weather report for a city (demo tool)."""
    return f"It's sunny and 22 °C in {city} right now."


_llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.7,
)

_agent = create_react_agent(
    model=_llm,
    tools=[greet, get_weather],
)


def _invoke_with_tracing(prompt: str) -> str:
    """Run the agent under a splunk_ao_context so each invocation is traced."""
    callback = SplunkAOCallback()
    with splunk_ao_context(project=_PROJECT, log_stream=_LOG_STREAM):
        result = _agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"callbacks": [callback]},
        )
    # Last message in the graph output is the final AI response.
    messages = result.get("messages", [])
    return messages[-1].content if messages else str(result)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class InvokeRequest(BaseModel):
    """Payload accepted by POST /invoke."""

    prompt: str
    """The user prompt to send to the agent (e.g. 'Say hello to Erin')."""


class InvokeResponse(BaseModel):
    """Response returned by POST /invoke."""

    response: str
    """The agent's final text output."""
    note: str = (
        "The root WorkflowSpan for this request should carry "
        "gen_ai.conversation_root=true (user_metadata) and "
        "LoggedWorkflowSpan.conversation_root=True."
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke_agent(body: InvokeRequest) -> InvokeResponse:
    """Invoke the LangGraph ReAct agent with a user prompt.

    The HTTP span (this FastAPI handler) is *not* a GenAI span, so the first
    GenAI WorkflowSpan created by the SplunkAOCallback will be detected as the
    conversation root (gen_ai.conversation_root = True).

    Scenario mirrors PR #236 test cases:
      - single_agent_under_http: HTTP request → WorkflowSpan (root = True)
    """
    logger.info("Received prompt: %s", body.prompt)
    try:
        output = _invoke_with_tracing(body.prompt)
    except Exception as exc:
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Agent response: %s", output)
    return InvokeResponse(response=output)


@app.post("/invoke/nested", response_model=InvokeResponse)
def invoke_nested(body: InvokeRequest) -> InvokeResponse:
    """Invoke two sequential agent calls in one HTTP request.

    Mirrors the 'two_sequential_agents' scenario from PR #236:
    each _invoke_with_tracing() call produces a separate trace, and each
    trace's root WorkflowSpan gets conversation_root=True independently.
    """
    logger.info("Received nested prompt: %s", body.prompt)
    try:
        out1 = _invoke_with_tracing(body.prompt)
        out2 = _invoke_with_tracing(f"Summarise in one sentence: {out1}")
    except Exception as exc:
        logger.exception("Nested agent invocation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    output = f"[Pass 1] {out1} | [Pass 2] {out2}"
    return InvokeResponse(response=output)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
