# Splunk Agent Observability Python SDK examples

## Agent examples

| Example | Framework | Description |
|---|---|---|
| [healthcare-assistant](agent/healthcare-assistant/README.md) | LangGraph + Streamlit | Full-stack chat app with RAG, text-to-SQL, hallucination demo, and Splunk AO tracing |

## Preconditions

Install `uv`, we use inline dependency inside scripts.

## How to run

First of all create `.env` file and add required env vars based on `.env.sample`.

Then just run `uv`:

```bash
uv run --env-file=examples/langgraph/.env examples/langgraph/with_openai.py
```

or

```bash
uv run --env-file=examples/langgraph/.env examples/langgraph/basic_langgraph.py
```
