# Contributing to splunk-ao-adk

Thank you for your interest in contributing to splunk-ao-adk!

## Project Structure

This package is part of the [splunk-ao-python](https://github.com/splunk/splunk-ao-python) monorepo:

```
splunk-ao-python/
├── src/splunk_ao/        ← Main Splunk AO SDK
└── splunk-ao-adk/
    ├── src/splunk_ao_adk/
    ├── tests/
    ├── pyproject.toml
    └── README.md
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Google ADK                                     │
│                                                                          │
│  ┌─────────────────────────┐          ┌─────────────────────────┐        │
│  │   SplunkAOADKPlugin     │          │   SplunkAOADKCallback   │        │
│  │    (Runner plugins)     │          │   (Agent callbacks)     │        │
│  │                         │          │                         │        │
│  │  on_user_msg            │          │  before/after_agent     │        │
│  │  before/after_agent     │          │  before/after_model     │        │
│  │  before/after_model     │          │  before/after_tool      │        │
│  │  before/after_tool      │          │                         │        │
│  │  on_error               │          │                         │        │
│  └───────────┬─────────────┘          └───────────┬─────────────┘        │
│              │                                    │                      │
│              └──────────────┬─────────────────────┘                      │
│                             ▼                                            │
│                  ┌────────────────────┐                                  │
│                  │   SpanTracker      │  ← Run ID correlation            │
│                  └─────────┬──────────┘                                  │
│                            ▼                                             │
│                  ┌────────────────────┐                                  │
│                  │  SplunkAOObserver  │  ← Shared logic + metadata       │
│                  └─────────┬──────────┘                                  │
│                            ▼                                             │
│                  ┌────────────────────┐                                  │
│                  │    SpanManager     │  ← Trace hierarchy               │
│                  └─────────┬──────────┘                                  │
│                            ▼                                             │
│                  ┌────────────────────┐                                  │
│                  │ SplunkAOBaseHandler│  ← From splunk-ao lib            │
│                  └─────────┬──────────┘                                  │
└────────────────────────────┼─────────────────────────────────────────────┘
                             ▼
                ┌────────────────────────┐
                │   Splunk AO Backend    │
                │   (or ingestion_hook)  │
                └────────────────────────┘
```

### TraceBuilder vs SplunkAOLogger

The plugin supports two modes of operation:

| Mode | Logger | When to Use |
|------|--------|-------------|
| **Normal** | `SplunkAOLogger` | Traces sent directly to Splunk AO backend |
| **Hook** | `TraceBuilder` | Traces passed to custom `ingestion_hook` callback |

**TraceBuilder** is a lightweight alternative to `SplunkAOLogger` that:
- Implements the same trace-building interface (spans, traces, metadata)
- Requires no Splunk AO credentials or backend connectivity
- Passes completed traces to the `ingestion_hook` consumer
- Delegates session management to the hook consumer via `session_external_id`

```
Normal mode:                          Hook mode:
┌─────────────────┐                  ┌─────────────────┐
│ SplunkAOObserver│                  │ SplunkAOObserver│
└────────┬────────┘                  └────────┬────────┘
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│ SplunkAOLogger  │                  │ TraceBuilder    │
└────────┬────────┘                  └────────┬────────┘
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│ Splunk AO Backend│                 │ ingestion_hook  │
└─────────────────┘                  └─────────────────┘
```

**Trace Hierarchy (Plugin mode):**

```
invocation [agent_name]           ← Run span (workflow wrapper)
└── agent_run [agent_name]        ← Agent span
    ├── call_llm                  ← LLM span (with tool_calls)
    └── execute_tool [tool_name]  ← Tool span
        └── (nested invocation)   ← Sub-agent if tool invokes agent
```

## Development Setup

### Prerequisites

- Python 3.13+ (recommended)
- [UV](https://docs.astral.sh/uv/) package manager

### Setup

```bash
cd splunk-ao-adk
uv sync --dev
```

This installs `splunk-ao` in **editable mode** from `../src/splunk_ao/`. Changes to either package are immediately available without reinstalling.

### Running Tests

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run tests
pytest tests -v

# Run with coverage
pytest tests --cov=splunk_ao_adk --cov-report=term-missing

# Run linting
ruff check src/

# Run type checking
mypy src/
```

### Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Line length: 120 characters
- Type hints are required for public functions

Format your code before committing:

```bash
ruff check --fix src/
ruff format src/
```

## Publishing

The `[tool.uv].sources` configuration is **dev-only** and ignored when building wheels. Published packages use the standard `dependencies` from `pyproject.toml`.

### Release Sequence

When both `splunk-ao` and `splunk-ao-adk` have changes:

1. Merge changes to `splunk-ao` (main SDK)
2. Wait for `splunk-ao` to publish to PyPI
3. Update `splunk-ao-adk/pyproject.toml` dependency constraint if needed:
   ```toml
   dependencies = [
       "splunk-ao>=0.1.0,<1.0.0",  # bump minimum version
   ]
   ```
4. Merge and publish `splunk-ao-adk`

### Triggering a Release

Releases are triggered via GitHub Actions:

1. Go to **Actions** > **Release splunk-ao-adk**
2. Click **Run workflow**
3. Either leave version empty for automatic semantic versioning, or specify a version (e.g., `1.0.0`, `1.1.0-beta.1`)
4. Click **Run workflow**

## Pull Request Guidelines

1. Create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Ensure tests pass and coverage is maintained
4. Update documentation if needed
5. Submit a PR with a clear description of changes

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(adk): add support for streaming responses
fix(adk): handle empty tool results
docs(adk): update configuration examples
```

## Questions?

- Open an issue on [GitHub](https://github.com/splunk/splunk-ao-python/issues)
- Check the [Splunk Observability Documentation](https://docs.splunk.com/observability/)
