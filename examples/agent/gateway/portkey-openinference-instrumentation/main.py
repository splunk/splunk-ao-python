"""
Single LLM call through Portkey AI Gateway.
Instrumentation: openinference-instrumentation-portkey

Spans emitted:
  Completions  (INTERNAL) — llm.* / openinference semconv, full input/output JSON
"""

import logging
import os
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(override=True)

from openinference.instrumentation.portkey import PortkeyInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from portkey_ai import Portkey

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_provider = trace_sdk.TracerProvider(
    resource=Resource.create({"service.name": os.environ["OTEL_SERVICE_NAME"]})
)
_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] + "/v1/traces")
    )
)
trace_api.set_tracer_provider(_provider)
PortkeyInstrumentor().instrument()

session_id = str(uuid4())
log.info("run started session=%s", session_id)

client = Portkey(
    api_key=os.environ["PORTKEY_API_KEY"],
    virtual_key=os.environ["PORTKEY_VIRTUAL_KEY"],
    trace_id=session_id,
    metadata={"_user": "erden"},
)
response = client.chat.completions.create(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    messages=[
        {"role": "system", "content": "You are a travel specialist. Be concise."},
        {"role": "user", "content": (
            "Plan a 7-day trip from San Francisco to Rome departing 2026-11-01. "
            "Give me a flight option and 3 must-do activities. Be brief."
        )},
    ],
    temperature=0.4,
)
answer = response.choices[0].message.content or ""
log.info("run completed session=%s answer_chars=%d", session_id, len(answer))
log.info("answer=%s", answer[:300])

_provider.force_flush()
