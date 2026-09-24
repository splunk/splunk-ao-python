# Upload precomputed experiment scores

This focused example reconstructs two historical LLM traces and uploads scores that were calculated before Splunk AO
ingestion. It demonstrates the temporary structured-ingestion compatibility path discussed in
`.local/specs-v2/architecture/experiment-precomputed-scores-otlp-confluence.html`.

It intentionally does not use `run_experiment()`, a platform evaluator, or `LocalMetricConfig`. The example creates an
experiment, records a small historical trace, assigns precomputed values to `trace.metrics`, and sends the complete
`LoggedTrace` through the structured trace API.

## Why two loggers are used

- The **collector** has an `ingestion_hook`. It keeps complete proprietary trace objects until `flush()`.
- The **ingestor** owns deployment authentication and forwards the resulting `TracesIngestRequest` to
  `POST /v2/projects/{project_id}/traces`.

This bypasses the current OTLP limitation for arbitrary client-precomputed scores. In this compatibility mode,
`flush()` is required and is not merely an OTLP drain operation.

## Setup

```shell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python upload_precomputed_scores.py
```

Choose exactly one deployment block in `.env`:

- Standalone: `SPLUNK_AO_API_KEY` and `SPLUNK_AO_CONSOLE_URL`.
- O11y: `SPLUNK_AO_REALM` and an API-authorized token. A dedicated `SPLUNK_AO_O11Y_API_TOKEN` is recommended for this
  structured API upload. `SPLUNK_AO_O11Y_TOKEN` can also be used when it has the required CRUD/log-data permission.

Both modes require `SPLUNK_AO_PROJECT`.

## Does this affect other SDK instrumentation?

Not when it is isolated as shown here. The ingestion hook belongs only to the explicit collector instance. It does not
intercept arbitrary OpenTelemetry spans, replace the global tracer provider, or change separately created
`SplunkAOLogger` instances.

It can affect other instrumentation if the collector is installed into a shared application context, passed to a
framework handler used by unrelated requests, or reused as the application's normal logger. In that case, telemetry
created through that same logger is retained for structured batch upload instead of following the normal OTLP path.

Keep the workaround scoped to offline experiment upload:

- Do not put the collector in a process-global logger/context used by live traffic.
- Do not pass it to unrelated handlers or integrations.
- Continue using normal SDK/OTel instrumentation for the rest of the application.
- Keep agent-stream instrumentation on the standard OTLP path.
- Keep the ingestor alive until the collector has flushed.

If a registered server-side scorer uses the same name as a precomputed metric, define which result should win or use a
different metric name to avoid an overwrite/conflict.
