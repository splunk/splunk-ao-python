# Changelog

## Unreleased

### Breaking Changes

- Local configuration directory renamed from `~/.galileo` to `~/.splunk`. The override environment variable is now `SPLUNK_AO_HOME_DIR` (previously `GALILEO_HOME_DIR`).

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
