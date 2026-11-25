# Changelog

## Unreleased

## 0.2.0

### Changed

- Raised the `python-dotenv` minimum version to `1.2.2` for the optional
  examples dependencies.

### Security

- Require `uv>=0.13.4` for development and use `uv 0.13.4` in CI, which
  removes trust in the compromised eMudhra certificate authorities
  (CVE-2026-111943).

## 0.1.0 - 2026-07-31

### Added

- Added automatic OpenTelemetry instrumentation for A2A client and server
  operations.
- Added W3C trace-context propagation through A2A message metadata so remote
  agents participate in one distributed trace.
- Added A2A task and context correlation, session grouping, and optional
  message-content capture.
- Added deployment-aware OTLP export for Splunk Observability Cloud and
  standalone Agent Observability through the core `splunk-ao` SDK.
