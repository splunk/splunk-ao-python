"""Orchestrator using automatic W3C HTTP client instrumentation."""

import asyncio
import os
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from splunk_ao import configure_distributed_tracing, log, openai, splunk_ao_context

load_dotenv()

provider = configure_distributed_tracing()

openai_client = openai.OpenAI()
OPENAI_MODEL = os.environ["OPENAI_MODEL"]
RETRIEVAL_SERVICE_URL = "http://localhost:8000"
BATCH_DEMO_SLEEP_SECONDS = float(os.getenv("BATCH_DEMO_SLEEP_SECONDS", "0"))


@log
async def orchestrator_agent(question: str) -> str:
    """Run one independently traced RAG request."""
    analysis = analyze_question(question)

    # HTTPX creates the client span and injects the active W3C context.
    async with httpx.AsyncClient(base_url=RETRIEVAL_SERVICE_URL, timeout=100.0) as client:
        try:
            response = await client.post("/retrieve", json={"query": question})
            response.raise_for_status()
            retrieved_docs = response.json()["results"]
        except httpx.HTTPError:
            retrieved_docs = []

    if BATCH_DEMO_SLEEP_SECONDS > 0:
        print(
            "Batching demo: analysis and distributed retrieval spans have ended; "
            f"the orchestrator root remains active for {BATCH_DEMO_SLEEP_SECONDS:g} seconds."
        )
        await asyncio.sleep(BATCH_DEMO_SLEEP_SECONDS)

    context = format_context(analysis, retrieved_docs)
    response = openai_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the user's question using only the provided context. "
                    f"If the context is insufficient, say so.\n\nContext:\n{context}"
                ),
            },
            {"role": "user", "content": question},
        ],
        model=OPENAI_MODEL,
    )
    return response.choices[0].message.content or ""


@log
def analyze_question(question: str) -> dict[str, object]:
    question_lower = question.lower()
    return {
        "needs_company_info": any(word in question_lower for word in ("company", "work", "employer")),
        "needs_location_info": any(word in question_lower for word in ("location", "where", "city", "live")),
        "question_type": "factual",
    }


@log
def format_context(analysis: dict[str, object], documents: list[str]) -> str:
    rendered = [f"Analysis: {analysis}", "", "Retrieved Documents:"]
    rendered.extend(f"{index}. {document}" for index, document in enumerate(documents, 1))
    return "\n".join(rendered)


async def main() -> None:
    # One app-owned session is propagated as gen_ai.conversation.id baggage.
    # set_session() is local-only; unlike start_session(), it performs no CRUD request.
    splunk_ao_context.set_session(str(uuid4()))
    for question in ("What did Galileo Galilei research?", "Where did Galileo Galilei work?"):
        answer = await orchestrator_agent(question)
        print(f"Question: {question}\nAnswer: {answer}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        provider.shutdown()
