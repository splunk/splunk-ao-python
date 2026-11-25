# Banking agent with Agent Streams

The sample runs three banking queries in one named session. `@log` captures the
agent workflow and simulated tools; the wrapped OpenAI client captures LLM calls.
The code follows the original sample's structure, including a module-level client,
`load_dotenv("../.env")`, and the original context manager around the three queries.
The tools use mock accounts and a demonstration eligibility rule.

## Configuration

Create `examples/logging-samples/.env` with:

```dotenv
OPENAI_API_KEY=your-openai-api-key
SPLUNK_AO_PROJECT=your-project-name
SPLUNK_AO_AGENT_STREAM=your-agent-stream-name
```

Add the credentials for **one** deployment:

- **Standalone:** `SPLUNK_AO_API_KEY` and `SPLUNK_AO_CONSOLE_URL`.
- **O11y Cloud:** `SPLUNK_AO_REALM` and `SPLUNK_AO_O11Y_TOKEN`.
  Session creation requires CRUD permissions on the ingest token or a separate
  `SPLUNK_AO_O11Y_API_TOKEN` with those permissions.

See the repository's [setup guide](../../../README.md#setup) for deployment details.

## Run

Run from the sample directory:

```shell
cd examples/logging-samples/banking-agent-sample
uv run sample_app.py
```

Running the example calls OpenAI and sends telemetry to the configured Splunk
Agent Observability deployment. Inspect the session in your project's Agent Stream
to compare tool selection and context adherence across the three queries.
