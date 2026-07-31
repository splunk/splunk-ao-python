## Project Overview

Splunk Agent Observability Python SDK (`splunk-ao` on PyPI) — the official Python client for Splunk Agent Observability. Instrument LLM/agent apps, send traces and metrics, manage projects, datasets, experiments, and prompts.

Successor to [`galileo-python`](https://github.com/rungalileo/galileo-python); migration notes in `splunk-ao-migration-tool/README.md`.

SDK code lives under `src/splunk_ao/`. Do not edit `galileo-core` or `src/splunk_ao/resources/` (auto-generated).

### Deployment Modes

| Mode | Auth | Notes |
|------|------|-------|
| **O11y Cloud** | `SPLUNK_AO_REALM` + `SPLUNK_AO_SF_TOKEN` | Do not set `SPLUNK_AO_CONSOLE_URL` / `SPLUNK_AO_API_URL` |
| **Standalone** | `SPLUNK_AO_API_KEY` + `SPLUNK_AO_CONSOLE_URL` | Self-hosted or legacy AO |

Detection: `src/splunk_ao/deployment.py::resolve_deployment()`. Never mix o11y and standalone env vars.

Optional defaults: `SPLUNK_AO_PROJECT`, `SPLUNK_AO_AGENT_STREAM` (deprecated alias: `SPLUNK_AO_LOG_STREAM`).

`SplunkAOConfig` bridges `SPLUNK_AO_*` → `GALILEO_*` for `galileo-core` (see `config.py::_BRIDGE`).

## Build & Development

```bash
poetry install --all-extras --no-root   # or: inv setup
poetry run pytest                       # single file: poetry run pytest tests/test_foo.py
inv test                                # with coverage
inv type-check                          # mypy
poetry run ruff check --fix src/        # lint + format
```

CI: mypy + pytest on Python 3.11–3.14 × Linux/macOS/Windows. Pre-commit: ruff + mypy.

## Architecture

```
src/splunk_ao/
├── project.py, dataset.py, experiment.py, prompt.py  # Object-centric API (import via splunk_ao.__future__)
├── logger/              # SplunkAOLogger — trace/span management
├── handlers/            # LangChain, CrewAI, OpenAI Agents integrations
├── openai/              # Drop-in OpenAI client wrapper
├── resources/           # Auto-generated API client — DO NOT EDIT
├── decorator.py         # @log, splunk_ao_context
├── config.py            # SplunkAOConfig
└── deployment.py        # O11y vs standalone detection
```

**Regenerate API client:**
```bash
./scripts/import-openapi-yaml.sh https://api.galileo.ai/client
./scripts/auto-generate-api-client.sh
```

Uses OpenAPI **Client API** (`/client`), not the main API (`/docs`).

Depends on `galileo-core` for shared schemas and helpers; ongoing work to reduce this.

## Key Patterns

**Object-centric API** (`__future__`):
```python
from splunk_ao.__future__ import Project
project = Project.get(name="my-project")       # retrieve
project = Project(name="new").create()         # create
agent_streams = project.list_agent_streams()
```

**Service layer** (procedural):
```python
from splunk_ao.datasets import create_dataset
from splunk_ao.experiments import run_experiment
```

**Logging:**
```python
from splunk_ao import log, splunk_ao_context

@log
def my_workflow(): ...

with splunk_ao_context(project="my-project", agent_stream="prod"):
    my_workflow()
```

**Handlers:** `splunk_ao.handlers.langchain` (`SplunkAOCallback`), `splunk_ao.handlers.crewai` (`CrewAIEventListener`), `splunk_ao.openai` (drop-in wrapper).

## Testing

Fixtures in `tests/conftest.py`: `mock_request`, `mock_healthcheck`, `mock_login_api_key`. Tests use `--disable-socket`; env vars set in conftest for pytest-xdist.

CrewAI wraps stdout/stderr at import time. In tests, patch `_crewai_imports_resolved` / `CREWAI_AVAILABLE`, mock `AgentStreams`/`Projects`/`Traces`, and pass a mock `SplunkAOLogger` (see `tests/test_crewai_handler.py`).

Use Given/When/Then comments in tests (`# Given: …`, `# When: …`, `# Then: …`).

## Code Style

- Line length 120; ruff + mypy; numpy docstrings
- Conventional commits: `type(scope): description`
- Imports at module level (exception: lazy imports for optional deps like crewai)
- Duration vars need units: `timeout_seconds`, `delay_ms`
- Use `logging.getLogger(__name__)`; never log secrets or large payloads

**Error handling:** Resource ops (`create_project`, `get_dataset`, …) raise on failure. Telemetry/ingestion (`ingest_traces`, `flush`, `@log`) swallows infra errors — observability should not break user code.

## Known Issues

1. **galileo-core dependency** — private package, contributor friction
2. **Config state** — split across `Configuration`, `os.environ`, `SplunkAOConfig`; `connect()` must be called explicitly
3. **Dataset versions** — API is 1-based, not 0-based
4. **Experiment vs Playground** — SDK `Experiment` conflates two API concepts
5. **Metadata** — SDK stringifies values in handlers; Trace vs Dataset APIs behave differently

## References

- PyPI: https://pypi.org/project/splunk-ao/
- GitHub: https://github.com/splunk/splunk-ao-python
- Migration: `splunk-ao-migration-tool/README.md`
- Contributing: `CONTRIBUTING.md`
