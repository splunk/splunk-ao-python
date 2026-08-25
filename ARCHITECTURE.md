# Splunk Agent Observability Python SDK Architecture

This document is the progressive-disclosure companion to `AGENTS.md`. It describes stable, public repository
architecture rather than plans or release sequencing. Read only the sections relevant to the change, then inspect the
referenced code and tests; code remains authoritative.

## Repository Topology

The repository contains four independently built and released packages:

| Package | Source | Purpose | Tooling |
|---|---|---|---|
| `splunk-ao` | `src/splunk_ao/` | Core API, logging, integrations, CRUD, OTLP export | Poetry |
| `splunk-ao-a2a` | `splunk-ao-a2a/src/splunk_ao_a2a/` | A2A client/server native OTel instrumentation | uv/Hatch |
| `splunk-ao-adk` | `splunk-ao-adk/src/splunk_ao_adk/` | Google ADK handler/plugin integration | uv/Hatch |
| `splunk-ao-migrate` | `splunk-ao-migration-tool/splunk_ao_migrate/src/splunk_ao_migrate/` | galileo → splunk-ao migration CLI | uv/Hatch |

`splunk-ao-migration-tool/` is a uv workspace; `splunk_ao_migrate/pyproject.toml` defines the `splunk-ao-migrate` package. `docs/` contains repository
documentation; generated API references are produced by `scripts/create_docs.py`.

## Core SDK Layers

| Layer | Primary locations | Responsibility |
|---|---|---|
| Public facade | `__init__.py`, `__future__/` | Stable exports and compatibility aliases |
| Object API | singular resource modules | Stateful create/get/update/delete workflows |
| Service API | plural resource modules | Procedural operations and orchestration |
| Generated transport | `resources/` | OpenAPI models and HTTP calls; generated as one unit |
| Instrumentation | `logger/`, `decorator.py`, `handlers/`, `openai/` | Capture application operations and content |
| Native OTel | `otel.py` | Span creation and processor registration for OTel users |
| Conversion | `converter/attribute_mapping.py`, `converter/span_converter.py` | Internal completed steps to OTel `ReadableSpan` data |
| Export | `exporter/` | Routing, immutable normalization, OTLP transport, diagnostics |
| Configuration | `config.py`, `configuration.py`, `deployment.py` | Deployment detection, compatibility bridge, endpoint/auth selection |

Object resources use lifecycle states through `StateManagementMixin` (`SyncState.LOCAL_ONLY`, `SyncState.SYNCED`,
`SyncState.DIRTY`, `SyncState.FAILED_SYNC`, and `SyncState.DELETED`). Keep object behavior and procedural helpers
consistent. The generated transport is an implementation detail; public callers should normally enter through the SDK
APIs.

## Telemetry Data Flow

There are three supported ingress paths. They have different export wiring, ownership, and conversion rules.

```text
Path 1 (default OTLP): decorator / logger / handlers / OpenAI / ADK
        -> internal LoggedTrace + completed steps
        -> SpanConverter
        -> OTel ReadableSpan copies
        -> SDK-owned SpanSink
        -> NormalizingSpanExporter -> deployment-aware OTLP exporter -> backend

        The compatibility ingestion_hook captures Path 1 output before OTLP export.

Path 2: start_splunk_ao_span()
        -> SDK-created OTel spans on the provider in context, or the global provider
        -> processors/exporters configured on that provider

Path 3: external OTel/OpenInference + A2A
        -> caller TracerProvider
        -> add_splunk_ao_span_processor(provider)
        -> NormalizingSpanExporter -> deployment-aware OTLP exporter -> backend
```

### Path 1: internal step model

`SplunkAOLogger`, `@log`, LangChain, CrewAI, OpenAI Agents, the drop-in OpenAI wrapper, and ADK build the established
internal trace/step model. Stable OTel context is associated with actual operations. Completed steps are converted to
OTel spans; the `LoggedTrace` envelope remains an internal lifecycle container and must not become a wire span.

Do not bypass this path when extending an existing handler. It centralizes lifecycle behavior, content conversion,
session handling, and compatibility hooks. Conversion changes must cover workflow, agent, LLM, tool, retriever, and
Agent Control kinds that they affect.

### Path 2: SDK-native OTel

`start_splunk_ao_span()` creates spans through SDK OTel support and applies SDK semantic attributes at completion. It is
useful when a caller wants explicit OTel spans without the internal step model. It does not configure export: the
provider's registered processors/exporters control where spans go. When a Splunk AO processor is registered, export
normalizes an immutable copy; never mutate an ended span.

### Path 3: caller-owned OTel

`add_splunk_ao_span_processor(provider)` attaches export to a provider supplied by the application. Standard OTel and
OpenInference instrumentations can then flow directly to the backend. A2A follows this path and manages A2A-specific
client/server wrapping and message-context propagation.

The SDK may add processors, but it must never silently replace the global tracer provider. The application owns the
provider and calls `shutdown()`; SDK-owned logger/export resources use their own termination path.

## Span Lifecycle and Export Ownership

`SpanSink` owns the SDK's private provider and `BatchSpanProcessor` for internal telemetry. A completed operation is
enqueued immediately, allowing scheduled export without an explicit flush.

- `flush()` / `async_flush()` drain completed work and do not end an active trace.
- `terminate()` drains completed work, shuts down SDK-owned telemetry resources, and releases unfinished state.
- Caller-owned OTel providers are not terminated by the SDK; their owner calls `shutdown()`.
- Completion, emission, and state release are separate operations. Preserve idempotency under retries and cleanup.
- Telemetry failures are diagnostic events, not reasons to fail the instrumented application.

OTel `ReadableSpan` data is effectively immutable after end. `exporter/span_transform.py` creates normalized copies;
never change private span fields in place. This protects concurrent exporters and caller-owned processors.

## Attributes, Content, and Routing

Standard GenAI attributes and structured content are the interoperability contract. Preserve upstream `gen_ai.*`
values unless a documented SDK rule fills or sanitizes them. SDK-specific wire attributes belong under `splunk_ao.*`.

Routing is transport metadata, not an ordinary per-span override:

1. Resolve Project and Agent Stream by name XOR ID.
2. Apply precedence: explicit call, active `splunk_ao_context`, environment, deployment default.
3. Capture routing when the exporter is built.
4. Stamp the authoritative selection in both request headers and OTel Resource attributes.
5. Ignore/remove conflicting reserved keys from `OTEL_RESOURCE_ATTRIBUTES`.

Changing routing requires tests for precedence, name/ID exclusivity, headers, Resource attributes, and both deployment
modes. It also requires attention to when exporters/configuration singletons are constructed and reset.

## Deployment and Configuration

`deployment.py::resolve_deployment()` selects a mode by environment-variable presence:

| Mode | CRUD auth | Telemetry auth/endpoints |
|---|---|---|
| O11y Cloud | `SPLUNK_AO_O11Y_TOKEN` when permitted, or a dedicated `SPLUNK_AO_O11Y_API_TOKEN` | realm-derived endpoint plus `SPLUNK_AO_O11Y_TOKEN` |
| Standalone | `SPLUNK_AO_API_KEY` | console/API configuration and deployment-derived OTLP endpoint |

O11y also requires `SPLUNK_AO_REALM`; standalone requires `SPLUNK_AO_CONSOLE_URL`. The primary O11y token can authorize
both telemetry and CRUD when it has the required permissions; the API token provides separate CRUD credentials when
needed. Do not combine deployment modes.

Configuration has compatibility state in more than one layer:

- `Configuration` is the user-facing facade and synchronizes supported settings with the environment.
- `SplunkAOConfig` extends the `galileo-core` configuration and bridges selected `SPLUNK_AO_*` inputs.
- exporter and API-client instances may capture resolved settings.

Tests that mutate configuration must establish environment state before importing the SDK, then reset the environment,
configuration facades, cached singletons, and exporter state. Never read or print real developer credentials in tests.

## Error Model

The SDK has two intentional failure policies:

| Operation | Expected behavior |
|---|---|
| CRUD/resource operations | Raise actionable errors; callers requested the operation and need its result |
| Telemetry capture/export/flush | Contain infrastructure failures so observability does not break business code |

Containment does not mean silence. Exporters log sanitized transport/auth/rejection diagnostics, rate-limit repetitive
receiver failures, and expose bounded acknowledgement health. Do not log secrets or raw application content.

## Integration Boundaries

### LangChain, CrewAI, and OpenAI Agents

These handlers adapt framework events into the internal Path 1 model. Keep optional dependencies lazy and imports free
of surprising side effects. CrewAI is excluded on Python 3.14; code and tests must support the unavailable path.

### OpenAI wrapper

`src/splunk_ao/openai/` is a drop-in wrapper. Preserve the upstream caller experience and sync/async response semantics.
Telemetry failures must not change an OpenAI call's application-visible outcome.

### A2A

A2A is independently released and native OTel (Path 3). Instrumentation and uninstrumentation must be idempotent.
Streaming, early close/cancellation, client/server parentage, and message metadata context all need focused coverage.

### ADK

ADK is independently released but handler-based (Path 1). Its plugin, observer, span tracker, manager, trace builder, and
data conversion layers share session and lifecycle state; changes must preserve concurrency and cleanup behavior.

### Agent Control

Agent Control bridges control execution into the core telemetry model. Classification attributes and input/output fields
are a backend contract. Test its public helpers and its final OTLP representation when changing the bridge.

## Generated Client Boundary

`openapi.yaml` and the scripts under `scripts/` define regeneration. The generated `resources/` tree is replaced as a
unit and post-processed by repository scripts/templates. Never patch an individual generated file to fix a public API;
change the source contract, template, or post-processing step and regenerate only with explicit approval.

The generated client is not a deployment-aware public facade. Public operations should select deployment/auth through
SDK configuration, then call the appropriate generated transport internally.

## Test Architecture

Root pytest configuration enables xdist, disables non-local sockets, injects fake credentials, and sets timeouts.
`tests/conftest.py` provides HTTP/auth fixtures, global reset logic, a fast configuration-validation fixture, and a
legacy ingestion-hook capture for compatibility tests.

For telemetry changes, select tests by path and lifecycle rather than testing only the changed function:

- Conversion: internal schema -> converter -> final OTel attributes/content.
- SDK-native OTel: start/end, exceptions, context nesting, immutable export copy.
- Caller-owned OTel/A2A: processor registration, provider ownership, propagation, streaming cleanup.
- Logger/decorator: sync, async, generator, async generator, nesting, flush, termination.
- Configuration: both deployments, precedence, invalid mixed state, singleton reset, sanitized diagnostics.
- Integrations: installed and missing optional dependency behavior; no real service calls.

Use Given/When/Then comments, deterministic IDs/clocks where needed, and explicit cleanup. A passing focused test is not
sufficient if the change crosses a package or telemetry-path boundary.

## Change-Impact Map

| Change | Inspect together | Minimum evidence to seek approval to run |
|---|---|---|
| Auth, realm, endpoints | `deployment.py`, config facades, `exporter/o11y.py`, `exporter/standalone.py` | both modes; invalid/mixed env; no secret logging |
| Routing/context | context APIs, config, exporter builder, Resource transform | precedence; name/ID; header/Resource agreement |
| Span attributes/content | schemas, `converter/attribute_mapping.py`, converter, span transform | Path 1 plus any affected native/external path |
| IDs or propagation | `tracing.py`, logger context, middleware, A2A metadata | local/nested/distributed parentage; malformed input |
| Flush/termination | logger, sink, processors/exporters | active work, completed work, failures, repeated cleanup |
| Object/service API | singular and plural modules, exports, generated transport | state transitions; sync/async; public import tests |
| Handler integration | handler, logger/converter, optional dependency tests | success/error/streaming; installed/unavailable modes |
| Generated API | `openapi.yaml`, scripts, templates, complete `resources/` diff | regeneration plus public wrapper regression tests |
| A2A or ADK | package source, package tests, package pyproject/CI | that package's targeted test, mypy, lint; core tests if shared |

## Public Compatibility Checklist

Before calling a change complete, inspect whether it changes:

- root or `__future__` imports;
- method signatures, defaults, enum values, or return types;
- environment variables, auth headers, routing, or endpoint construction;
- OTel span names, kinds, parents, attributes, events, status, or structured content;
- logger/provider ownership, flushing, shutdown, or background work;
- supported Python/framework versions or optional dependency behavior;
- examples, README guidance, generated docs, migration guidance, or changelog entries.

Public behavior changes should be documented and tested in the same change. Compatibility aliases and deprecated
parameters are still public surfaces until their removal is explicitly authorized.
