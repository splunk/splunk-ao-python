# Changelog

## Unreleased

### Breaking Changes

- **`monitor_progress()` `job_id` parameter removed**: The deprecated
  `job_id` keyword argument of `Experiment.monitor_progress()` has been fully removed.
  Callers passing `job_id=` must remove that argument.

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

- **Evaluator terminology alignment in docs and errors**: Updated
  `SplunkAOEvaluators` docstrings, agent stream/evaluator API docstrings, and
  user-visible error messages to use evaluator and agent stream vocabulary following
  the `SplunkAOMetrics` → `SplunkAOEvaluators` rename. Enum values are documented
  as matching scorer labels via the legacy `/scorers` API paths. The public
  `metrics=` parameter name is unchanged for API compatibility. Renamed stale
  `test_galileo_metrics_*` and `test_lookup_by_galileo_metrics_enum` test identifiers.
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
