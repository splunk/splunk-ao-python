# Changelog

## Unreleased

## 0.2.0

### Added

- Capture the image/audio token breakdown that Gemini reports in
  `prompt_tokens_details` / `candidates_tokens_details` on LLM spans, so
  per-modality pricing applies to the span's cost. Carry the counts through
  both the OpenTelemetry and compatibility ingestion-hook paths. Missing or
  unreadable breakdowns remain unknown without dropping the LLM span.

### Security

- Require `uv>=0.13.4` for development and use `uv 0.13.4` in CI, which
  removes trust in the compromised eMudhra certificate authorities
  (CVE-2026-111943).

## 0.1.0 - 2026-07-31

### Added

- Added automatic tracing for Google ADK agent runs, model calls, tool calls,
  and retriever operations.
- Added session correlation through ADK session IDs and support for ADK
  `RunConfig.custom_metadata`.
- Added plugin and callback integration modes with structured and multimodal
  content capture.
- Added deployment-aware OTLP export for Splunk Observability Cloud and
  standalone Agent Observability through the core `splunk-ao` SDK.
- Retained the proprietary ingestion hook as deprecated migration
  compatibility; new custom pipelines should use OpenTelemetry extension
  points.
