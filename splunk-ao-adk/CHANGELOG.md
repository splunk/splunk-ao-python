# Changelog

## Unreleased

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
