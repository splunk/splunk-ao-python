# Healthcare Assistant

A healthcare-domain Streamlit chat app built with **LangGraph**, **PostgreSQL/pgvector**, and the **Splunk Agent Observability Python SDK**. Demonstrates real-time agent tracing, RAG retrieval, text-to-SQL, and intentional hallucination logging.

## What's inside

| File / Dir | Purpose |
|---|---|
| `app.py` | Streamlit UI and chat loop |
| `agent-with-instrumentation.py` | LangGraph agent with `SplunkAOAsyncCallback` |
| `agent.py` | Plain LangGraph agent (no instrumentation) |
| `rag.py` | RAG retrieval chain (pgvector) |
| `config.py` | Azure OpenAI / OpenAI factory functions |
| `config.yaml` | App settings — model, RAG, UI queries, hallucination examples |
| `system_prompt.json` | Agent system prompt |
| `tools/logic.py` | `get_patient_info`, `delete_patient_record`, `search_medicine_qa` |
| `tools/schema.json` | Tool JSON schemas |
| `helpers/` | pgvector, SQL, text-to-SQL, hallucination, and setup utilities |
| `docs/` | Source data — `qa.csv` (medicine FAQ), `relational_patient.csv` |
| `hosted/` | Kubernetes CronJob deployment — see [hosted/README.md](hosted/README.md) |

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — package manager and runner
- [Docker](https://docs.docker.com/get-docker/) — for the local PostgreSQL container
- Azure OpenAI or OpenAI API key
- Splunk Agent Observability account (O11y Cloud or standalone)

### Splunk AO authentication

The `.env.example` file includes environment variables for use with **Splunk Observability (O11y) Cloud** or with **On-Premises Splunk Agent Observability**.

O11y Cloud tokens:

| Variable | Required | Purpose |
|---|---|---|
| `SPLUNK_AO_REALM` | ✅ | Your O11y Cloud realm (`us0`, `eu0`, `lab0`, …) |
| `SPLUNK_AO_O11Y_TOKEN` | ✅ | Ingest token — exports telemetry via OTLP |
| `SPLUNK_AO_O11Y_API_TOKEN` | optional | Dedicated CRUD token — enables evaluators (Correctness, Context Adherence) |

`SPLUNK_AO_O11Y_TOKEN` is used for both telemetry ingest and CRUD when no API token is set. Set `SPLUNK_AO_O11Y_API_TOKEN` separately if your ingest token is read-only. For more information, see [this SDK doc section](https://github.com/splunk/splunk-ao-python#splunk-observability-o11y-cloud).

More information about on-premises environment variables are in [this SDK doc section](https://github.com/splunk/splunk-ao-python#on-premises-agent-observability).


## Setup

Run all commands from the `healthcare-assistant/` directory.

### 1. Start PostgreSQL

```bash
docker run \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=vectordb \
  --name healthcare-postgres \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16

docker exec healthcare-postgres \
  psql -U postgres -d vectordb \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Install dependencies

```bash
uv venv
uv pip install -r requirements.txt
```

Or with the editable local SDK (repo root):

```bash
uv venv
uv sync
```

### 3. Configure environment

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Minimum required values:

```bash
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large

SPLUNK_AO_REALM=us0
SPLUNK_AO_O11Y_TOKEN=<your-ingest-token>
SPLUNK_AO_PROJECT=<your-project>
SPLUNK_AO_AGENT_STREAM=healthcare-assistant

POSTGRES_PASSWORD=<your-postgres-password>
```

### 4. Load vector and relational data

```bash
uv run python helpers/setup_vectordb.py local
```

Or:

```bash
./start_vectordb.sh
```

### 5. Run the app

```bash
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

## Example queries

- **"What is the dosage and common side effects of Lisinopril?"** — RAG over medicine FAQ (`search_medicine_qa`)
- **"Can you look up information for patient P001?"** — text-to-SQL patient lookup (`get_patient_info`)

Use **Log Hallucination** in the sidebar to intentionally log a wrong Lisinopril answer for demo purposes.

## Deployment

See [hosted/README.md](hosted/README.md) for the Kubernetes CronJob deployment that runs the demo session automatically.
