# Vercel AI SDK — Splunk AO Trace Export

Demonstrates how to send traces from the [Vercel AI SDK](https://sdk.vercel.ai/) to Splunk AO using OpenTelemetry.

The Vercel AI SDK has built-in OTel support via `experimental_telemetry`. Traces are exported directly to Splunk AO's OTLP endpoint — no Python SDK import needed.

The example defines a `FinanceWeatherAgent` prompt with two tools (`getWeather`, `getStockPrice`) and runs a single multi-step query that triggers both tools before generating a final answer.

## Setup

```bash
cp .env.example .env
# fill in SPLUNK_AO_API_KEY, SPLUNK_AO_PROJECT, SPLUNK_AO_AGENT_STREAM, OPENAI_API_KEY

npm install
```

## Run

```bash
npm start
# or: npx tsx main.ts
```

## What to expect in Splunk AO

- **LLM span** for the initial tool-selection call
- **Tool call spans** for `getWeather` and `getStockPrice`
- **LLM span** for the final answer generation
- Spans arrive via raw OTLP — no Python SDK involved

## Reference SDK (galileo-python)

Swap the OTLP endpoint and headers to run against `galileo-python` on staging:

```typescript
const exporter = new OTLPTraceExporter({
  url: "https://api.staging.galileo.ai/otel/v1/traces",
  headers: {
    "Galileo-API-Key": process.env.GALILEO_API_KEY!,
    project: process.env.GALILEO_PROJECT!,
    logstream: process.env.GALILEO_LOG_STREAM!,
  },
});
```
