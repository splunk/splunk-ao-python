# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Standalone custom console domains now derive a consistent `api.` hostname
  for both CRUD operations and OTLP trace export unless `SPLUNK_AO_API_URL` is
  set explicitly.
- Agent Control spans exported over OTLP now include the control discriminator
  and complete `agent_control.*` field set required for backend classification
  and Controls-card rendering.

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

[0.1.1]: https://pypi.org/project/splunk-ao/0.1.1/
[0.1.0]: https://pypi.org/project/splunk-ao/0.1.0/
