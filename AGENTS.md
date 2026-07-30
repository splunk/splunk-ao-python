## Project Overview

Splunk Agent Observability Python SDK (`splunk-ao` on PyPI) — the official Python client library for Splunk Agent Observability (Splunk AO). It enables logging and tracing of LLM calls, experiments, datasets, prompt management, and more.

Successor to [`galileo-python`](https://github.com/rungalileo/galileo-python); migration notes in `splunk-ao-migration-tool/README.md`.

**Key characteristics:** PyPI SDK · `galileo-core` dependency · OpenAPI-generated client · LangChain / CrewAI / OpenAI Agents integrations · O11y Cloud or standalone deployment

### What is Splunk AO?

Splunk Agent Observability (Splunk AO) is an AI observability platform: developers instrument LLM/agent apps, send traces and metrics to Splunk AO, then inspect, debug, and evaluate runs in a console UI.

This repo is the **Python SDK** (`pip install splunk-ao`). Typical user flow:

1. Set deployment env vars (see **Deployment Modes** below).
2. Instrument code with `@log`, `splunk_ao_context`, framework handlers, or OpenTelemetry.
3. Traces land in a **project** → **agent stream** where users analyze them.

SDK-owned code lives under `src/splunk_ao/`; do not edit `galileo-core` or `src/splunk_ao/resources/` from this repo.

### Deployment Modes

| Mode | When | Auth | Endpoints |
|------|------|------|-----------|
| **O11y Cloud** | Splunk Observability Cloud customer | `SPLUNK_AO_REALM` + `SPLUNK_AO_SF_TOKEN` (ingest) / `SPLUNK_AO_SF_API_TOKEN` (CRUD, optional) | Derived from realm — CRUD at `https://app.{realm}.observability.splunkcloud.com/ao/api/`, OTLP at `https://ingest.{realm}.observability.splunkcloud.com/v2/trace/otlp` |
| **Standalone** | Self-hosted or legacy AO (e.g. `app.galileo.ai`) | `SPLUNK_AO_API_KEY` | `SPLUNK_AO_CONSOLE_URL` (+ optional `SPLUNK_AO_API_URL`); OTLP derived from console/API URL |

Detection: `src/splunk_ao/deployment.py::resolve_deployment()`. **Never mix** o11y and standalone env vars — raises `AmbiguousConfigurationError`. Do not set `SPLUNK_AO_CONSOLE_URL` / `SPLUNK_AO_API_URL` for O11y Cloud.

```
User app  →  SDK (SplunkAOLogger / @log / handlers / OTel)
                ├─ Telemetry  →  OTLP or batch ingest API  →  Splunk AO backend
                └─ CRUD       →  resources/ client (O11y: O11yApiClient + X-SF-Token; standalone: API key via galileo-core)
```

**Standalone variables**

| Variable | Required | Description |
|----------|----------|-------------|
| `SPLUNK_AO_API_KEY` | Yes | API key |
| `SPLUNK_AO_CONSOLE_URL` | Yes | Console URL |
| `SPLUNK_AO_API_URL` | No | API URL when not derivable from console |
| `SPLUNK_AO_PROJECT` | No | Default project |
| `SPLUNK_AO_AGENT_STREAM` | No | Default agent stream |
| `SPLUNK_AO_LOG_STREAM` | No | Deprecated alias for `SPLUNK_AO_AGENT_STREAM` |
| `SPLUNK_AO_LOGGING_DISABLED` | No | Disable trace collection |

**O11y Cloud variables**

| Variable | Required | Description |
|----------|----------|-------------|
| `SPLUNK_AO_REALM` | Yes | Realm (e.g. `us1`) |
| `SPLUNK_AO_SF_TOKEN` | Yes* | Ingest token for telemetry |
| `SPLUNK_AO_SF_API_TOKEN` | No | CRUD token when ingest token lacks API permissions |
| `SPLUNK_AO_PROJECT` | No | Default project |
| `SPLUNK_AO_AGENT_STREAM` | No | Default agent stream |

\*Required for telemetry export; CRUD-only may use `SPLUNK_AO_SF_API_TOKEN` alone.

**Gateway headers:** set `GALILEO_EXTRA_HEADERS` (JSON) or `SplunkAOConfig.get(extra_headers={...})` for API-gateway auth (e.g. IBM APIC). Applied to all egress paths via `galileo-core`.

### First Contribution Paths

| Task | Touch | Verify |
|------|-------|--------|
| **Framework handler** | `src/splunk_ao/handlers/<framework>/`, `logger/logger.py` | `poetry run pytest tests/test_langchain.py` (etc.) |
| **Regenerate API client** | See **Auto-Generated Code** below | `inv type-check`; `inv test` |
| **New env var** | `config.py::_BRIDGE`, `deployment.py`, `tests/conftest.py`, README | Config tests; grep old name |
| **Object-centric API** | `src/splunk_ao/__future__/` or `project.py`, `dataset.py`, … | Matching tests under `tests/` |
| **Public API** | `src/splunk_ao/__init__.py` | mypy; relevant `examples/` |

CI (`.github/workflows/ci-tests.yaml`): **mypy** + **pytest/coverage** on Python 3.11–3.14 × Linux/macOS/Windows. Pre-commit: ruff + mypy.

## Build & Development Commands

```bash
# Install dependencies (requires poetry)
poetry install --all-extras --no-root

# Full setup (install + pre-commit hooks)
inv setup

# Run all tests (parallel by default)
poetry run pytest

# Run single test file
poetry run pytest tests/test_decorator.py

# Run single test
poetry run pytest tests/test_decorator.py::test_function_name -v

# Run tests with coverage
inv test

# Type checking
inv type-check

# Linting (via pre-commit)
poetry run ruff check --fix src/
poetry run ruff format src/
```

## Architecture

### Package Structure

```
src/splunk_ao/
├── __future__/              # New object-centric API (WIP)
│   ├── project.py           # Project domain object
│   ├── dataset.py           # Dataset domain object
│   ├── experiment.py        # Experiment domain object
│   ├── prompt.py            # Prompt domain object
│   ├── configuration.py     # Configuration management
│   └── shared/              # Shared utilities (filters, sorting, base classes)
├── logger/                  # Core logging functionality
│   └── logger.py            # SplunkAOLogger - central trace/span management
├── handlers/                # Framework-specific integrations
│   ├── langchain/           # LangChain callback handler (SplunkAOCallback)
│   ├── crewai/              # CrewAI event listener
│   ├── openai_agents/       # OpenAI Agents SDK integration
│   └── agent_control/       # Agent control bridge
├── openai/                  # Drop-in OpenAI client wrapper (auto-logging)
├── middleware/              # Starlette tracing middleware (optional extra)
├── resources/               # Auto-generated API client (DO NOT EDIT)
├── schema/                  # Pydantic models for SDK-specific types
├── utils/                   # Utility functions and helpers
├── deployment.py            # O11y vs standalone deployment detection
├── otel.py                  # OpenTelemetry export helpers
├── agent_stream.py          # AgentStream domain object (__future__ API)
├── datasets.py              # Dataset service (current API)
├── experiments.py           # Experiment service (current API)
├── prompts.py               # Prompt service (current API)
├── projects.py              # Project service (current API)
├── agent_streams.py         # Agent stream service (current API)
├── decorator.py             # @log decorator and splunk_ao_context
└── config.py                # SplunkAOConfig configuration
```

### Core Components

**SplunkAOLogger** (`src/splunk_ao/logger/logger.py`): Central class for uploading traces to Splunk AO. Supports batch and streaming modes. Manages traces, spans (LLM, retriever, tool, workflow, agent), and sessions.

**Decorators** (`src/splunk_ao/decorator.py`): The `@log` decorator and `splunk_ao_context` context manager for automatic function tracing. Uses ContextVars for thread-safe nested span tracking.

**Handlers** (`src/splunk_ao/handlers/`): Framework-specific integrations:
- `langchain/` - LangChain callback handler (`SplunkAOCallback`, `SplunkAOAsyncCallback`)
- `crewai/` - CrewAI handler (uses lazy imports to avoid side effects)
- `openai_agents/` - OpenAI Agents SDK integration (`SplunkAOTracingProcessor`)

**OpenAI Wrapper** (`src/splunk_ao/openai/`): Drop-in replacement for OpenAI client that auto-logs calls.

**`__future__` Package** (`src/splunk_ao/__future__/`): New object-centric API implementing the "Golden Flow" patterns. Provides intuitive, Pythonic interfaces for domain objects (Project, Dataset, Prompt, Experiment, AgentStream). Released incrementally as stable.

### Auto-Generated Code

**Resources** (`src/splunk_ao/resources/`): Auto-generated API client from OpenAPI spec. **Excluded from linting/type-checking.** Never edit manually.

```bash
# Regenerate API client
./scripts/import-openapi-yaml.sh https://api.galileo.ai/client
./scripts/auto-generate-api-client.sh
```

Scheduled regeneration: `.github/workflows/regenerate-api-client.yaml`.

**Important:** The OpenAPI spec comes from the **Client API** (`/client`), not the main API (`/docs`). The Client API is a curated subset designed specifically for SDK consumption.

### Dependency on galileo-core

The SDK depends on `galileo-core` for shared schemas, helpers, and base classes:
- `galileo_core.schemas.logging.*` - Span types (LlmSpan, ToolSpan, etc.), Trace, Session
- `galileo_core.helpers.*` - API key management, execution utilities

**Env bridge:** `SplunkAOConfig` maps `SPLUNK_AO_*` → `GALILEO_*` for `galileo-core` (see `config.py::_BRIDGE` and **Deployment Modes** above).

**Note:** Ongoing work to reduce this dependency — see Known Issues.

## Key Patterns

### Object-Centric Design (`__future__` package)

Domain objects follow consistent patterns:

```python
from splunk_ao.__future__ import Project, Dataset

# Factory methods (class-level)
project = Project.get(name="my-project")      # Retrieve existing
projects = Project.list()                      # List all

# Instance creation with lifecycle
project = Project(name="new-project")          # LOCAL_ONLY state
project.create()                               # → SYNCED state

# Fluent creation
project = Project(name="new-project").create() # 2-in-1

# Relationship methods
agent_streams = project.list_agent_streams()
dataset = project.create_dataset(name="test-data", content=[...])

# Child → Parent navigation
dataset.project  # Returns parent Project object
```

### State Management

Objects have explicit sync states: `LOCAL_ONLY`, `SYNCED`, `DIRTY`, `FAILED_SYNC`, `DELETED`

```python
project = Project(name="test")     # LOCAL_ONLY
project.create()                    # → SYNCED
project.name = "renamed"            # → DIRTY
project.save()                      # → SYNCED
project.delete()                    # → DELETED
```

### Service Layer (Current API)

Services provide functional interfaces for those who prefer procedural style:

```python
from splunk_ao.datasets import create_dataset, get_dataset, list_datasets
from splunk_ao.experiments import run_experiment

dataset = create_dataset(name="test", content=[...])
results = run_experiment(
    experiment_name="eval-1",
    dataset=dataset,
    prompt_template=get_prompt(name="my-prompt"),
    metrics=["correctness"],
    project="my-project"
)
```

### Logging with Decorators

```python
from splunk_ao import log, splunk_ao_context

# Auto-trace function calls
@log
def my_workflow():
    call_llm()
    call_llm()

# Explicit span types
@log(span_type="retriever")
def retrieve_docs(query: str):
    return ["doc1", "doc2"]

# Context manager for explicit control
with splunk_ao_context(project="my-project", agent_stream="prod"):
    my_workflow()
```

### Handler Integrations

```python
# LangChain
from splunk_ao.handlers.langchain import SplunkAOCallback
callback = SplunkAOCallback()
llm = ChatOpenAI(callbacks=[callback])

# CrewAI
from splunk_ao.handlers.crewai import CrewAIEventListener
listener = CrewAIEventListener(project="my-project")
# Listener auto-registers; use auto_setup_listeners=False in tests

# OpenAI (drop-in wrapper)
from splunk_ao.openai import openai
client = openai.OpenAI()  # Auto-logs all calls
```

## Testing

Tests use pytest with these key fixtures from `tests/conftest.py`:
- `mock_request` - HTTP request mocking (from `galileo_core[testing]`)
- `mock_healthcheck`, `mock_login_api_key`, `mock_get_current_user` - Common API mocks

### Test Environment

Environment variables are set in `conftest.py` for pytest-xdist compatibility:
```python
SPLUNK_AO_CONSOLE_URL=http://fake.test:8088
SPLUNK_AO_API_KEY=api-1234567890
SPLUNK_AO_PROJECT=test-project
SPLUNK_AO_AGENT_STREAM=test-log-stream
```

Tests run with `--disable-socket` to prevent real network calls.

### Testing Guidelines

```python
def test_example(mock_request, mock_healthcheck, mock_login_api_key):
    # Mock API responses
    mock_request.post("/datasets").respond(json={"id": "123", "name": "test"})

    # Test SDK functionality
    dataset = create_dataset(name="test", content=[...])
    assert dataset.id == "123"
```

### Handler Testing (CrewAI)

CrewAI imports have global side effects. Use lazy imports and `auto_setup_listeners=False`:

```python
def test_crewai_handler():
    # Import inside test, not at module level
    from splunk_ao.handlers.crewai import CrewAIEventListener

    listener = CrewAIEventListener(
        project="test",
        auto_setup_listeners=False  # Prevents import side effects
    )
```

### Given/When/Then Testing Style

Use behavioral testing comments to structure tests clearly. Add inline comments before each section:

- `# Given: <description>` - Before setup/arrangement code. Describe the preconditions.
- `# When: <description>` - Before the action being tested. Describe what action is performed.
- `# Then: <description>` - Before assertions. Describe the expected outcome.

**Important rules:**

- Comments must include a human-readable description after the colon - never leave them empty
- Use sentence case for descriptions (e.g., "a user with admin permissions", not "A User With Admin Permissions")
- Keep descriptions concise but meaningful
- For tests where the action raises an exception, use `# When/Then: <description>` combined

```python
def test_create_project_success(mock_request, mock_healthcheck, mock_login_api_key):
    # Given: a valid project name and mocked API response
    mock_request.post("/projects").respond(json={"id": "123", "name": "test"})

    # When: creating a new project
    project = Project(name="test").create()

    # Then: the project is created with the expected ID
    assert project.id == "123"
    assert project.name == "test"
```

## Code Style & Conventions

- **Line length:** 120 characters
- **Linting:** ruff (replaces flake8, isort, etc.)
- **Type annotations:** Required for public functions (mypy)
- **Docstrings:** numpy convention
- **Pre-commit hooks:** Run ruff and mypy on commit

### Required Practices

- Use standard Python logging: `import logging; logger = logging.getLogger(__name__)`
- Duration variables must be suffixed with units: `timeout_seconds`, `delay_ms`
- Commit messages: `type(scope): description` (conventional commits)
- **Imports at top of file**: Always place imports at the module level, not inside functions
- Exception: Lazy imports for optional dependencies (e.g., crewai) - document why
- Use `from __future__ import annotations` for forward references

### Error Handling Architecture

The SDK distinguishes between two types of operations with different error handling needs:

**Resource Management Operations** (raise exceptions):
- Operations where users explicitly request an action and expect feedback
- Examples: `create_project()`, `get_dataset()`, `delete_agent_stream()`, `list_projects()`
- These operations should raise exceptions on failure for clear user feedback

**Telemetry/Ingestion Operations** (resilient):
- Background operations that observe user code without interfering
- Examples: `ingest_traces()`, `ingest_spans()`, `flush()`
- These operations swallow infrastructure errors gracefully
- Principle: Observability code should observe, not interfere

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Application                            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────┐                   ┌───────────────────────┐
│ Resource Mgmt     │                   │ Telemetry/Ingestion   │
│ (Raises on Error) │                   │ (Resilient)           │
├───────────────────┤                   ├───────────────────────┤
│ Projects          │                   │ Traces.ingest_*()     │
│ Datasets          │                   │ Traces.update_*()     │
│ AgentStreams      │                   │ Logger streaming      │
│ Stages            │                   │ @warn_catch_exception │
└───────────────────┘                   └───────────────────────┘
        │                                           │
        ▼                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Generated API Client                               │
│              (Always raises HTTP exceptions)                    │
└─────────────────────────────────────────────────────────────────┘
```

**HTTP-Specific Exceptions:**

| Status Code | Exception | Meaning |
|-------------|-----------|---------|
| 400 | `BadRequestError` | Invalid request parameters |
| 401 | `AuthenticationError` | Invalid or expired API key |
| 403 | `ForbiddenError` | Insufficient permissions |
| 404 | `NotFoundError` | Resource doesn't exist |
| 409 | `ConflictError` | Resource already exists |
| 422 | `HTTPValidationError` | Request body/params failed Pydantic validation |
| 429 | `RateLimitError` | Too many requests |
| 5xx | `ServerError` | Server-side error |

**Infrastructure Exceptions** (caught only in telemetry operations):
```python
INFRASTRUCTURE_EXCEPTIONS = (
    httpx.HTTPError,
    httpx.TimeoutException,
    httpx.ConnectError,
    ConnectionError,
    TimeoutError,
    OSError,
)
```

User errors like `TypeError`, `ValueError`, and `ValidationError` are never caught - they propagate immediately.

### Logging Convention

```python
import logging
logger = logging.getLogger(__name__)

# Log lifecycle events with context
logger.info("Project.create: name=%s – started", name)
logger.info("Project.create: id=%s – completed", project_id)
logger.error("Project.update: id=%s – failed: %s", project_id, error)

# Never log sensitive data (tokens, API keys, PII)
```

**When to Add Logging:**
- Service methods that perform writes (create, update, delete)
- Error conditions with full context when catching exceptions
- Long-running operations (start/completion with duration)

**What NOT to Log:**
- Sensitive data: Passwords, API keys, tokens, PII
- Large payloads: Don't log entire request/response bodies
- High-frequency loops: Use sampling or aggregate metrics

## Known Issues and Architectural Decisions

### 1. galileo-core Dependency

Deep dependency on private `galileo-core` (schemas, HTTP helpers, auth). Creates contributor friction and a split contract. Mitigation: migrate toward OpenAPI-generated types and SDK-owned abstractions.

### 2. Configuration State Management

Configuration exists in `Configuration` (`__future__` API), `os.environ` (incl. `_BRIDGE`), and `SplunkAOConfig._instance`. **Known issue:** `connect()` must be called explicitly; lazy init is incomplete.

### 3. Prompt Version Management

`Prompt.create_version()` creates a NEW prompt (name with timestamp suffix), not a new version of the same template. True version management requires API alignment.

### 4. Dataset Version Indexing

API uses **1-based** version indexing, not 0-based:
```python
# Correct: first version is index 1
version_content = dataset.get_version_content(index=1)

# Wrong: index 0 doesn't exist
version_content = dataset.get_version_content(index=0)  # Raises ValueError
```

### 5. Experiment-Playground Conflation

The SDK's `Experiment` class conflates two distinct API concepts:
- **Playground**: Interactive workspace for prompt iteration
- **Experiment**: Immutable logged run with recorded results

Version specification for datasets and prompts is implicit (uses "current" version).

### 6. Metadata Type Handling

SDK converts all metadata values to strings. API behavior varies:
- Trace API: Skips `None` values and non-primitives
- Dataset API: Keeps `None` as null, JSON-encodes nested dicts

## Release Process

Releases use python-semantic-release with conventional commits:

```bash
# Patch release triggers
fix:, perf:, chore:, docs:, style:, refactor:

# Version is managed in:
# - src/splunk_ao/__init__.py:__version__
# - pyproject.toml:project.version
```

## References

- **PyPI:** https://pypi.org/project/splunk-ao/
- **GitHub:** https://github.com/splunk/splunk-ao-python
- **Upstream (Galileo SDK):** https://github.com/rungalileo/galileo-python
- **Migration guide:** `splunk-ao-migration-tool/README.md`
- **Contributing:** `CONTRIBUTING.md`
- **OpenAPI Spec:** `openapi.yaml` (generated from Client API)
