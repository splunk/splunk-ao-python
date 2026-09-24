# Experiment execution and scoring paths

These focused examples show the three experiment use cases that are easy to conflate:

| Example | Where the application runs | Where scoring runs |
|---|---|---|
| `prompt_template.py` | Splunk AO platform | Splunk AO platform |
| `runner_function.py` | Your local Python process | Splunk AO platform |
| `local_metric.py` | Your local Python process | Client-side by design; see the current limitation below |

The SDK has two experiment execution paths: prompt-template and runner-function. `LocalMetricConfig` is a client-side
scoring option for the runner-function path, not a third executor.

## Setup

Create a virtual environment, install the example dependencies, and copy the environment template:

```shell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Choose exactly one deployment block in `.env`:

- Standalone requires `SPLUNK_AO_API_KEY` and `SPLUNK_AO_CONSOLE_URL`.
- O11y Cloud always requires `SPLUNK_AO_REALM`. The prompt-template example can use an API-capable
  `SPLUNK_AO_O11Y_TOKEN` or a CRUD-only `SPLUNK_AO_O11Y_API_TOKEN`. The runner-function and local-metric examples also
  require `SPLUNK_AO_O11Y_TOKEN` because they emit telemetry. Use both tokens when CRUD has dedicated credentials.

Both modes require `SPLUNK_AO_PROJECT`. The prompt-template example also needs a model integration in Splunk AO whose
alias matches `SPLUNK_AO_PROMPT_MODEL_ALIAS`. The runner-function example needs `OPENAI_API_KEY` and uses the
Splunk AO OpenAI wrapper so its model call is traced.

Run one example at a time:

```shell
python prompt_template.py
python runner_function.py
python local_metric.py
```

## Current `LocalMetricConfig` limitation

The public `LocalMetricConfig` API remains available only for locally run function experiments. It is rejected for
prompt-template experiments. The current OTLP telemetry path does not preserve local score values and metadata, so
`local_metric.py` demonstrates the retained API shape but its score will not appear in the experiment UI. Platform
evaluators such as `SplunkAOEvaluators.correctness` are not affected because they run after telemetry is ingested.
