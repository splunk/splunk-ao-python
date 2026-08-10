# Splunk Agent Observability Python SDK Agent Guide

This guide covers the entire repository. All paths are repository-root relative. Read `README.md` for supported user
workflows and `ARCHITECTURE.md` before changing telemetry, configuration, lifecycle, or integration behavior.

## Permission Model

- Read-only discovery is allowed without approval: file reads, `rg`, `git status`, and `git diff`.
- Before running any project command, show the exact command, explain its scope, and ask. This includes tests, lint,
  formatting, type checks, builds, installs, lock updates, scripts, code generation, and documentation generation.
- A requested implementation authorizes scoped file edits, not unrelated cleanup or expansion.
- Never stage or commit changes unless explicitly requested. Never push, publish, release, or bump a version without an
  explicit request and separate confirmation of the exact action.
- Do not dispatch, rerun, cancel, or otherwise operate a GitHub Actions workflow unless the task explicitly requests it.
  You may identify a relevant workflow as an optional next step, but do not seek approval to run it unless the user asks
  to proceed. When execution is requested, show the exact workflow, ref, inputs, and command and wait for approval.
- Never expose credentials, tokens, `.env` contents, customer payloads, or private/internal planning material.

## Subagents

- Use subagents only for concrete, bounded, independent work where parallelism materially improves speed or quality.
  Prefer read-heavy exploration, review, triage, and independent package analysis.
- Do not delegate trivial, tightly coupled, or sequential work. Avoid concurrent edits to the same files.
- The main agent owns scope, architectural decisions, integration, and final review. It must read task-defining
  instructions itself rather than outsourcing its understanding.
- Give each subagent an explicit scope, relevant paths, constraints, and expected output. Require a concise,
  evidence-backed handoff.
- Subagents inherit every permission boundary in this guide. Delegation must never bypass approval for project commands,
  GitHub workflows, staging, commits, releases, or publishing.
- When subagents edit files, assign non-overlapping ownership and review the combined diff before completion.

## Commands (Reference Only—Ask Before Running)

Root SDK (`splunk-ao`, Poetry 2.4.1):

```bash
poetry install --all-extras --no-root
poetry run pytest tests/test_deployment.py -n 0       # targeted, deterministic
poetry run pytest                                     # full unit suite
poetry run invoke test                                # full suite with terminal coverage
poetry run invoke type-check                          # configured mypy run
poetry run ruff check --no-fix src tests              # non-mutating lint
poetry run ruff format --check src tests              # non-mutating format check
poetry build
```

A2A and ADK packages use uv/Hatch. Each block starts independently from the repository root.

A2A:

```bash
cd splunk-ao-a2a
uv sync --dev
uv run pytest
uv run mypy src/
uv run ruff check src tests
uv build
```

ADK:

```bash
cd splunk-ao-adk
uv sync --dev
uv run pytest
uv run mypy src/
uv run ruff check src tests
uv build
```

Potentially mutating commands require approval and a clean diff first:

```bash
poetry run ruff check --fix <changed-paths>
poetry run ruff format <changed-paths>
poetry run pre-commit run --files <changed-files>
poetry run python scripts/create_docs.py
```

Regenerate the low-level API client only when the task explicitly changes the Client OpenAPI contract, and still ask:

```bash
./scripts/import-openapi-yaml.sh https://api.galileo.ai/client
./scripts/auto-generate-api-client.sh
```

The generator replaces `src/splunk_ao/resources/`; review the complete generated diff. It uses the Client API (`/client`),
not the main API documentation contract.

## Stack and Package Map

| Area | Stack and responsibility |
|---|---|
| `src/splunk_ao/` | Python 3.11–3.14, Pydantic v2, OpenTelemetry 1.38, `galileo-core` 4.x; public SDK |
| `tests/` | pytest 9, xdist, respx, socket blocking, timeout and coverage plugins |
| `splunk-ao-a2a/` | Independently released native-OTel A2A instrumentation; uv/Hatch |
| `splunk-ao-adk/` | Independently released Google ADK handler integration; uv/Hatch |
| `splunk-ao-migration-tool/` | Migration documentation and examples, not a buildable package |
| `src/splunk_ao/resources/` | OpenAPI-generated transport client; never hand-edit |

The three buildable packages have independent versions, lockfiles, CI, and release workflows. Validate every package a
change touches. CI supports Python 3.11–3.14; root CI also spans Linux, macOS, and Windows.

## Architecture and Public Surfaces

- `src/splunk_ao/__init__.py` defines supported root imports. `src/splunk_ao/__future__/` is a compatibility/re-export
  surface; do not assume object APIs are available only there.
- Singular modules (`project.py`, `dataset.py`, `experiment.py`, and peers) implement stateful object APIs. Plural modules
  (`projects.py`, `datasets.py`, `experiments.py`, and peers) implement procedural/service APIs. Preserve both.
- `logger/`, `decorator.py`, `handlers/`, and `openai/` instrument applications. `otel.py` is the native OTel entry point.
- `exporter/` owns deployment-aware OTLP export, span normalization, lifecycle, and diagnostics.
- `config.py` bridges selected `SPLUNK_AO_*` variables to legacy `GALILEO_*` inputs used by `galileo-core`.
- `galileo-core` is an external dependency. Do not edit or vendor it here; adapt at this repository's boundary.
- See `ARCHITECTURE.md` for telemetry paths, ownership rules, and a change-impact map.

## Configuration and Routing Invariants

| Deployment | Required authentication |
|---|---|
| O11y Cloud | `SPLUNK_AO_REALM` plus `SPLUNK_AO_O11Y_TOKEN`; that token may serve CRUD when permitted, or use a dedicated `SPLUNK_AO_O11Y_API_TOKEN` |
| Standalone | `SPLUNK_AO_API_KEY` plus `SPLUNK_AO_CONSOLE_URL`; `SPLUNK_AO_API_URL` is optional |

- Detection lives in `deployment.py::resolve_deployment()`. Never mix O11y and standalone variable sets.
- Project/Agent Stream selection is name XOR ID. Precedence is explicit argument, active context, environment, then
  deployment defaults. Routing must agree in OTLP headers and Resource attributes.
- `OTEL_RESOURCE_ATTRIBUTES` is not an SDK routing override. Remove reserved routing keys before merging it.
- Configuration is stateful across `Configuration`, environment variables, and `SplunkAOConfig`; tests that change it
  must reset all affected state and singleton instances.
- Never log auth headers, tokens, raw prompts, completions, embeddings, or large payloads.

## Telemetry and Error Boundaries

- Handler/decorator/OpenAI/ADK telemetry uses the internal logged-step path and converts completed steps to immutable
  OTel spans. The internal trace envelope is never exported as a span.
- `start_splunk_ao_span()` is SDK-native OTel. `add_splunk_ao_span_processor()` and A2A instrument caller-owned OTel.
- Never replace the process-global tracer provider. Register processors on the provided provider; respect ownership.
- Treat ended `ReadableSpan` objects as immutable. Normalize by copying at export, never by mutating private fields.
- Completed spans enqueue immediately. `flush()` drains completed work without ending active work; `terminate()` drains,
  shuts down SDK-owned resources, and discards unfinished state. Caller-owned providers use `shutdown()`.
- CRUD/resource operations raise useful failures. Telemetry infrastructure failures must not break instrumented business
  code; sanitize and rate-limit diagnostics.
- Preserve standard `gen_ai.*` attributes. New SDK-owned attributes use `splunk_ao.*`; do not introduce new proprietary
  `galileo.*` wire attributes.
- Changes to propagation, IDs, parents, content schemas, or routing need coverage across every affected telemetry path.

## Code Style

- Line length 120; Ruff for lint/format; mypy for typing; NumPy-style public docstrings.
- Keep imports at module scope except intentional lazy imports for optional integrations.
- Use `logging.getLogger(__name__)`, typed signatures, and unit-bearing names such as `timeout_seconds` or `delay_ms`.
- Prefer the smallest compatible change. Do not combine feature work with drive-by formatting or generated diffs.
- Maintain sync, async, generator, and async-generator semantics where an API supports them.

Tests should show intent explicitly:

```python
def test_flush_does_not_end_active_trace(mock_request) -> None:
    # Given: an active trace with one completed child span
    # When: completed telemetry is flushed
    # Then: the child is exported and the active trace remains open
    ...
```

## Testing Rules

- Add the closest focused regression test first; ask before running it. Run broader suites only after targeted confidence.
- Root tests inherit `-n auto`, network blocking, a 120-second timeout, and fake standalone credentials from pytest config.
  Use `-n 0` for deterministic focused debugging.
- Set test environment variables before importing `splunk_ao`; xdist workers and Python 3.14 expose import-order leaks.
- Reuse `tests/conftest.py` fixtures such as `mock_request`, `mock_healthcheck`, and `mock_login_api_key`. Mock all network.
- Reset global OTel context, providers/processors, SDK configuration, loggers, and background resources after tests.
- Exercise success, exceptions, cancellation/early generator close, and cleanup for lifecycle-sensitive instrumentation.
- CrewAI is optional and excluded on Python 3.14. Preserve lazy imports and test both installed/unavailable behavior.
- Dataset version numbers are API-facing and 1-based.

## Change Workflow and Git

1. Read the public API, implementation, adjacent tests, and relevant architecture section before editing.
2. Identify ownership: public wrapper, integration, converter, exporter, generated client, or external dependency.
3. Preserve compatibility unless the task explicitly authorizes a breaking change. Update exports, docstrings, README usage,
   tests, and `CHANGELOG.md` when public behavior changes.
4. Ask before running the exact validation commands. Report what ran, what did not run, and why.
5. Review `git diff` for secrets, unrelated rewrites, generated churn, and platform-specific assumptions.

Use conventional commit subjects (`type(scope): description`) only when a commit is explicitly requested. Do not edit
versions, release workflows, or lockfiles as incidental cleanup.

## Hard Boundaries

- Do not hand-edit `src/splunk_ao/resources/`, generated reference docs, or generated lock content.
- Do not change release/publish configuration, dependency pins, or public compatibility aliases without task scope.
- Do not silently add network calls, global state, import-time side effects, unbounded queues, or non-daemon threads.
- Do not make tests depend on real credentials, live services, ordering, timing luck, or another test's state.
- Do not document unavailable internal context. Repository documentation must stand alone for public contributors.

## Progressive References

- `README.md`: installation, authentication, supported APIs, and integration examples.
- `ARCHITECTURE.md`: package boundaries, telemetry data flow, lifecycle, and change-impact routing.
- `CONTRIBUTING.md`: contribution setup and generated-client workflow.
- `src/splunk_ao/README_API_CLIENT.md`: generated client's capabilities and limitations.
- `splunk-ao-migration-tool/README.md`: migration guidance from `galileo-python`.
