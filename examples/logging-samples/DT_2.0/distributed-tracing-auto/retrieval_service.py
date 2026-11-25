"""FastAPI service using automatic W3C server instrumentation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from splunk_ao import configure_distributed_tracing, log

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    provider.shutdown()


app = FastAPI(title="Retrieval Service", lifespan=lifespan)
provider = configure_distributed_tracing(app=app)


class RetrievalRequest(BaseModel):
    query: str


class RetrievalResponse(BaseModel):
    results: list[str]


@log(span_type="retriever")
def retrieval_service(query: str) -> list[str]:
    knowledge_base = {
        "birthplace": ["Galileo Galilei was born in Pisa, Italy in 1564."],
        "profession": ["Galileo taught geometry, mechanics, and astronomy at the University of Padua."],
        "research": ["Galileo's telescopic observations transformed our understanding of the universe."],
    }
    query_lower = query.lower()
    results: list[str] = []
    for category, facts in knowledge_base.items():
        if category in query_lower or any(word in query_lower for word in ("work", "location", "education")):
            results.extend(facts)
    return results[:3]


@app.post("/retrieve", response_model=RetrievalResponse)
@log
async def retrieve_endpoint(request: RetrievalRequest) -> RetrievalResponse:
    return RetrievalResponse(results=retrieval_service(request.query))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
