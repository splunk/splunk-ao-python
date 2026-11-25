"""Orchestrator process for the W3C distributed-tracing example."""

import asyncio
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from splunk_ao import get_tracing_headers, log, openai, splunk_ao_context

load_dotenv()

openai_client = openai.OpenAI()
RETRIEVAL_SERVICE_URL = "http://localhost:8000"


@log
async def orchestrator_agent(question: str) -> str:
    """Run one independently traced RAG request."""
    analysis = analyze_question(question)

    # The active @log workflow is a real exportable operation. The returned
    # carrier contains W3C traceparent and optional tracestate fields.
    headers = get_tracing_headers()
    async with httpx.AsyncClient(base_url=RETRIEVAL_SERVICE_URL, timeout=100.0) as client:
        try:
            response = await client.post("/retrieve", json={"query": question}, headers=headers)
            response.raise_for_status()
            retrieved_docs = response.json()["results"]
        except httpx.HTTPError:
            retrieved_docs = []

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
        model="gpt-5-mini",
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
    asyncio.run(main())
