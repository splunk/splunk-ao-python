# Changelog

## Unreleased

### Added

- Added automatic OpenTelemetry instrumentation for A2A client and server
  operations.
- Added W3C trace-context propagation through A2A message metadata so remote
  agents participate in one distributed trace.
- Added A2A task and context correlation, session grouping, and optional
  message-content capture.
- Added deployment-aware OTLP export for Splunk Observability Cloud and
  standalone Agent Observability through the core `splunk-ao` SDK.
