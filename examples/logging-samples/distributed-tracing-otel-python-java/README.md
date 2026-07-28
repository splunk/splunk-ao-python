# Distributed Tracing: Java + Python with Splunk AO via OTEL

A runnable example showing how to trace a request across a **Java Spring Boot gateway** and a **Python FastAPI + LangGraph RAG service** — with a single trace ID stitched together end-to-end in [Splunk AO](https://galileo.ai).

```
User ──POST /ask──▶ Java Gateway ──POST /process──▶ Python RAG Service
                      │ Spring AI (classify)           │ LangGraph (route → retrieve → generate)
                      │ OTel Java Agent                │ LangChainInstrumentor + RetrieverSpan
                      └──────────────────┬─────────────┘
                                         │ OTLP HTTP
                                         ▼
                                 OpenTelemetry Collector
                                         │ OTLP HTTP (with Splunk AO auth)
                                         ▼
                                      Splunk AO
```

## What this demonstrates

- **Cross-language trace propagation** — the OTel Java agent injects a W3C `traceparent` header on every outbound HTTP call; the Python service continues the same trace automatically
- **Auto-instrumentation + targeted manual spans** — `LangChainInstrumentor` handles LangGraph nodes automatically; a Splunk AO `RetrieverSpan` surfaces retrieved source documents in the trace UI; the Java service adds `gen_ai.*` attributes for proper agent hierarchy rendering
- **Collector-agnostic** — both services export plain OTLP/HTTP to `OTEL_EXPORTER_OTLP_ENDPOINT`. Point them at the bundled demo collector, or at whatever OTel Collector you already run.
- **Financial services domain** — ChromaDB is pre-seeded with realistic financial policy documents (wire transfers, KYC/AML, mortgage guidelines, etc.)

## Expected trace in Splunk AO

```
invoke_agent financial-assistant          ← Java: outer agent span (manual)
  chat classify_question                  ← Java: LLM classification (manual span)
  POST /process                           ← Java agent: auto-instrumented HTTP call
    rag_pipeline                          ← Python: WorkflowSpan (Splunk AO)
      LangGraph.invoke                    ← Python: auto-instrumented by LangChainInstrumentor
        route                             ← Python: LangGraph node (auto)
        retrieve                          ← Python: LangGraph node (auto)
          chromadb_search                 ← Python: RetrieverSpan with source docs (Splunk AO)
        generate                          ← Python: LangGraph node (auto)
          openai.chat                     ← Python: LLM span (auto, OpenAIInstrumentor)
```

## Prerequisites

| Requirement | Version |
|---|---|
| Docker + Docker Compose | 24+ |
| OpenAI API key | — |
| Splunk AO account + API key | [console.galileo.ai](https://console.galileo.ai) |

## Quick start

**1. Clone and configure**

```bash
git clone https://github.com/rungalileo/sdk-examples.git
cd sdk-examples/python/logging-samples/distributed-tracing-otel-python-java
cp .env.example .env
```

Edit `.env` and fill in your keys:

```ini
OPENAI_API_KEY=sk-...
SPLUNK_AO_API_KEY=...
SPLUNK_AO_PROJECT=distributed-tracing-demo
SPLUNK_AO_AGENT_STREAM=main
SPLUNK_AO_API_URL=https://api.galileo.ai
```

**2. Start all services**

```bash
docker compose up --build
```

On first run this builds the Java and Python images (~2–3 min) and seeds ChromaDB. Once you see `Started GatewayApplication`, everything is ready.

**3. Send a question**

```bash
curl -s -X POST http://localhost:8089/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the wire transfer limits?"}' | jq
```

Expected response:

```json
{
  "answer": "Domestic wire transfers are limited to $50,000 per business day...",
  "category": "FINANCIAL",
  "sources": ["wire-transfer-policy"]
}
```

**4. View traces in Splunk AO**

Open your Splunk AO project and navigate to the log stream you configured in `.env`. You should see a trace with the full span hierarchy shown above.

## Service ports

| Service | Host port | Purpose |
|---|---|---|
| Java gateway | 8089 | `POST /ask` — entry point |
| Python RAG service | 8099 | `POST /process` — internal |
| ChromaDB | 8299 | Vector store |

## Architecture

### Java gateway (`java-service/`)

- **Spring Boot 3.4.1 + Spring AI 1.0.0** — handles routing and LLM classification
- **OTel Java agent** (bundled in Docker image) — auto-instruments all HTTP calls and injects `traceparent` headers
- **Manual spans** — two spans with `gen_ai.*` attributes tell Splunk AO to render this as an agent with an LLM sub-call; Spring AI doesn't yet emit these automatically

### Python RAG service (`python-service/`)

- **FastAPI + LangGraph** — three-node graph: `route → retrieve → generate`
- **`LangChainInstrumentor` + `OpenAIInstrumentor`** — auto-create spans for each LangGraph node and every OpenAI call
- **`RetrieverSpan`** (Splunk AO) — wraps the ChromaDB query so retrieved documents appear as source context in Splunk AO
- **`WorkflowSpan`** (Splunk AO) — top-level span for the `/process` endpoint

### How spans reach Splunk AO

Both services export OTLP/HTTP to whatever endpoint `OTEL_EXPORTER_OTLP_ENDPOINT` points at. That endpoint is always an **OpenTelemetry Collector** — the collector batches, retries on failure, and forwards to Splunk AO with the right auth headers. Splunk AO credentials live in the collector config, not in the application code.

#### Using the bundled demo collector

For running this repo end-to-end on a laptop, `docker compose up` starts a minimal collector alongside the two services. Its config is in [`otel-collector/config.yaml`](./otel-collector/config.yaml). Services automatically point at it:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

This is a demo convenience — not something you deploy.

#### Using your own existing collector

In any real environment you almost certainly already run an OTel Collector. To point the services at it instead:

1. Add a Splunk AO exporter to your existing collector config (see [`otel-collector/config.yaml`](./otel-collector/config.yaml) for the `otlphttp/galileo` block to copy).
2. Set `OTEL_EXPORTER_OTLP_ENDPOINT` in `.env` (or your deployment config) to your collector's OTLP/HTTP endpoint, e.g. `https://otel-collector.internal.example.com:4318`.
3. Remove the `otel-collector` service from `docker-compose.yml` (or just stop pointing at it).

No application code changes. The instrumentation stays identical.

## Troubleshooting

**Java service fails to start**
- Check that `OPENAI_API_KEY` is set in `.env`
- Maven downloads dependencies on first build; allow 2–3 min

**No traces in Splunk AO**
- Verify `SPLUNK_AO_API_KEY` and `SPLUNK_AO_API_URL` in `.env`
- Check `SPLUNK_AO_PROJECT` and `SPLUNK_AO_AGENT_STREAM` match what you're looking at in the UI

**ChromaDB connection refused**
- Python service waits up to 60 s for ChromaDB; check `docker compose logs python-service`

**Empty answers**
- Confirm `OPENAI_API_KEY` is valid and has quota
- Try a question in the FINANCIAL category (e.g., "What is the minimum credit score for a mortgage?")

## Further reading

[Distributed Tracing with OpenTelemetry — Splunk AO Docs](https://agent-observability-docs.splunk.com/sdk-api/logging/distributed-tracing-otel)
