"""
Single LLM call through Portkey AI Gateway.
Instrumentation: splunk-ao[langchain] — SplunkAOAsyncCallback (logger path)

Spans emitted (via Splunk AO logger):
  LLM span → logged to Splunk AO project via SplunkAOAsyncCallback
  → routes to Splunk AO project
"""

import asyncio
import logging
import os
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders
from splunk_ao import splunk_ao_context
from splunk_ao.handlers.langchain import SplunkAOAsyncCallback

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def run() -> None:
    session_id = str(uuid4())
    log.info("run started session=%s", session_id)

    portkey_headers = createHeaders(api_key=os.environ["PORTKEY_API_KEY"], trace_id=session_id)
    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "@<your-virtual-key-slug>/gpt-4.1-mini"),
        temperature=0.4,
        base_url=PORTKEY_GATEWAY_URL,
        api_key=os.environ["PORTKEY_API_KEY"],
        default_headers=portkey_headers,
    )
    callback = SplunkAOAsyncCallback(flush_on_chain_end=True)

    with splunk_ao_context(
        project=os.environ.get("SPLUNK_AO_PROJECT"),
        agent_stream=os.environ.get("SPLUNK_AO_AGENT_STREAM"),
        session_id=session_id,
    ):
        response = await llm.ainvoke(
            [
                SystemMessage(content="You are a travel specialist. Be concise."),
                HumanMessage(content=(
                    "Plan a 7-day trip from San Francisco to Rome departing 2026-11-01. "
                    "Give me a flight option and 3 must-do activities. Be brief."
                )),
            ],
            config={"callbacks": [callback]},
        )

    answer = response.content if isinstance(response.content, str) else str(response.content)
    log.info("run completed session=%s answer_chars=%d", session_id, len(answer))
    log.info("answer=%s", answer[:300])


if __name__ == "__main__":
    asyncio.run(run())
