# Splunk Agent Observability Python SDK examples

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
