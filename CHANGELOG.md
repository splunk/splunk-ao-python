# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added the `distributed-tracing` extra and
  `instrument_distributed_tracing()` startup helper for supported upstream
  FastAPI/Starlette, Requests, HTTPX, and aiohttp-client instrumentation.
- Explicit SDK sessions now propagate across supported services as standard
  W3C `gen_ai.conversation.id` baggage. SDK routing, authentication, and
  application identity are not propagated.
- Added module-level `get_tracing_headers()` and
  `extract_tracing_context()` helpers for standard W3C `traceparent` and
  `tracestate` propagation. `TracingMiddleware` now extracts and scopes that
  OpenTelemetry context for Starlette/FastAPI requests.

### Changed

- The temporarily retained `mode="batch"` and `mode="distributed"` values now
  use identical scheduled OTLP batch export and W3C propagation. Concluding an
  operation ends and queues it; a per-operation `flush()` is not required.
- Callback handlers keep a live real root during framework execution so
  outbound W3C context uses the same identity and visible hierarchy that is
  exported at commit.
- Normal LangChain, CrewAI, Google ADK, and OpenAI Agents callbacks now enqueue
  each completed operation into the existing `BatchSpanProcessor` at that
  operation's end callback. The deprecated `ingestion_hook` retains its
  whole-tree compatibility behavior.
- Default logger-owned batching now honors standard OpenTelemetry
  `OTEL_BSP_*` configuration, matching caller-owned OTel paths. Explicit
  internal `BatchConfig` values remain authoritative when supplied.

### Removed

- **Breaking:** Removed `trace_id=` and `span_id=` from `SplunkAOLogger`, the
  logger-level proprietary `get_tracing_headers()` method, and custom
  `Splunk-AO-Trace-ID` / `Splunk-AO-Parent-ID` continuation. Use the new
  module-level W3C helpers instead.
- Removed the obsolete distributed-only REST streaming worker and task queue;
  normal telemetry in both retained modes uses the existing
  `BatchSpanProcessor` path.

## [0.2.1] - 2026-08-07

### Fixed

- Galileo multimodal URL and base64 data blocks now export as OpenTelemetry
  GenAI `uri` and `blob` message parts for both input and output messages while
  preserving modality, MIME type, and supported extension fields.

## [0.2.0] - 2026-08-06

### Fixed

- Agent Control spans exported over OTLP now include the control discriminator
  and complete `agent_control.*` field set required for backend classification
  and Controls-card rendering.

### Changed

- **Config file renamed** (HYBIM-918): The non-secret debug snapshot written to
  `~/.galileo/` on logout/reset is now named `splunk-ao-config.json` (was
  `galileo-python-config.json`). The old file can be deleted or ignored — it is
  never read back and has no effect on authentication or config resolution.
- **Evaluator terminology alignment in docs and errors**: Updated
  `SplunkAOEvaluators` docstrings, agent stream/evaluator API docstrings, and
  user-visible error messages to use evaluator and agent stream vocabulary following
  the `SplunkAOMetrics` → `SplunkAOEvaluators` rename. Enum values are documented
  as matching scorer labels via the legacy `/scorers` API paths. The public
  `metrics=` parameter name is unchanged for API compatibility. Renamed stale
  `test_galileo_metrics_*` and `test_lookup_by_galileo_metrics_enum` test identifiers.

## [0.1.1] - 2026-08-03

### Removed

- **Breaking:** `monitor_progress()` `job_id` parameter removed (HYBIM-931).
  The deprecated `job_id` keyword argument of `Experiment.monitor_progress()`
  has been fully removed. Callers passing `job_id=` must remove that argument.

## [0.1.0] - 2026-07-31

### Added

- Added deployment-aware configuration and authentication for Splunk
  Observability Cloud and standalone Agent Observability deployments.
- Added O11y Cloud configuration through `SPLUNK_AO_REALM`,
  `SPLUNK_AO_O11Y_TOKEN`, and the optional `SPLUNK_AO_O11Y_API_TOKEN`.
- Added native OTLP trace export for SDK handlers and standard OpenTelemetry or
  OpenInference instrumentations.
- Added Project and Agent Stream routing by name or ID in both OTLP request
  headers and OpenTelemetry Resource attributes.
- Added standard OpenTelemetry Resource detection, including a valid
  `service.name` fallback and support for `OTEL_SERVICE_NAME`.
- Added structured input and output capture for workflow, agent, LLM, tool, and
  retriever spans, including supported multimodal content.

### Changed

- Completed spans are queued immediately in an OpenTelemetry
  `BatchSpanProcessor` and exported on its configured schedule.
- `flush()` and `async_flush()` now drain completed spans without concluding an
  active operation.
- Independent top-level decorated calls own separate traces, while nested calls
  remain children of their outer operation.
- Exceptions from decorated functions, synchronous generators, and asynchronous
  generators are re-raised after telemetry finalization.
- Reserved Agent Observability routing keys in `OTEL_RESOURCE_ATTRIBUTES` are
  removed so SDK routing configuration remains consistent with request headers.

### Diagnostics

- Standard OpenTelemetry exporter logging reports transport,
  authentication, retry, and non-2xx HTTP failures.
- Successful HTTP responses that reject telemetry produce sanitized,
  rate-limited SDK error logs and a recovery log after a later accepted
  response.
- Exporters expose bounded, read-only receiver-acknowledgement health. Health is
  unknown before an acknowledgement and after ordinary transport or non-2xx
  failures; it is not a delivery guarantee.

[0.2.1]: https://pypi.org/project/splunk-ao/0.2.1/
[0.2.0]: https://pypi.org/project/splunk-ao/0.2.0/
[0.1.1]: https://pypi.org/project/splunk-ao/0.1.1/
[0.1.0]: https://pypi.org/project/splunk-ao/0.1.0/
