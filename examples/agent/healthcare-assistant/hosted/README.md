# Healthcare Assistant — Hosted / K8s Deployment

Runs the instrumented healthcare assistant as a Kubernetes CronJob that sends telemetry to Splunk Observability Cloud (lab0 / any O11y realm).

Each run fires two agent queries and one intentional hallucination — all under a single session ID — producing three traces in the configured agent stream.

## What runs

`run_demo_session.py` is the entrypoint. It:

1. Loads `agent-with-instrumentation.py` (LangGraph + `SplunkAOAsyncCallback`)
2. Reads the two example queries from `../config.yaml` (`ui.example_queries`)
3. Fires both queries through the agent in the same session
4. Logs one hallucination from `../config.yaml` (`demo_hallucinations[0]`)

Telemetry is routed via `SPLUNK_AO_REALM` + `SPLUNK_AO_O11Y_TOKEN` to:
```
https://ingest.<realm>.observability.splunkcloud.com/v2/trace/otlp
```

## Prerequisites

Existing k8s namespace `healthcare-assistant` with:

| Secret | Keys used |
|---|---|
| `splunk-ao-secrets` | `realm`, `o11y-token`, `o11y-api-token` |
| `openai-secrets` | `api-key` |
| `healthcare-assistant-lab0-openai` | `azure-openai-endpoint` |
| `postgres-credentials` | `POSTGRES_PASSWORD` |

| ConfigMap | Used for |
|---|---|
| `postgres-config` | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_DB` |

## Configuration

All runtime config is in the `healthcare-assistant-instrumented-config` ConfigMap inside `k8s.yaml`. Override these to point at a different project or agent stream:

| Variable | Default | Description |
|---|---|---|
| `SPLUNK_AO_PROJECT` | `demo-healthcare` | Splunk AO project name |
| `SPLUNK_AO_AGENT_STREAM` | `hosted` | Agent stream name |
| `OTEL_SERVICE_NAME` | `healthcare-assistant-hosted` | OTel service name |
| `AZURE_CHAT_DEPLOYMENT` | `gpt-4.1-mini` | Azure OpenAI chat deployment |
| `AZURE_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` | Azure OpenAI embedding deployment |
| `QUERY_DELAY_SECONDS` | `3` | Delay between queries |

## Build

Build context is the repo root. The SDK is installed from `src/` (local source, not PyPI).

```bash
# from repo root
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f examples/agent/healthcare-assistant/hosted/Dockerfile \
  -t <your-registry>/healthcare-assistant-agent-loadgen:latest \
  --push \
  .
```

## Deploy

```bash
kubectl apply -f examples/agent/healthcare-assistant/hosted/k8s.yaml
```

## Trigger manually (one-shot test)

```bash
kubectl create job healthcare-assistant-instrumented-test \
  --from=cronjob/healthcare-assistant-instrumented \
  -n healthcare-assistant

# Follow logs
kubectl logs -n healthcare-assistant -l job-name=healthcare-assistant-instrumented-test --follow
```

## Validate

Check Splunk Observability Cloud → Agent Observability → your project → your agent stream.

Each run produces:
- 1 trace for **"What is the dosage and common side effects of Lisinopril?"** — RAG retrieval via `search_medicine_qa`
- 1 trace for **"Can you look up information for patient P001?"** — text-to-SQL via `get_patient_info`
- 1 hallucination trace for the Lisinopril question with answer `"Common dosage is 100mg daily. Common side effects are rashes, itching, and swelling."`
