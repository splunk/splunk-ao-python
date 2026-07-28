"""Conversion helpers shared by Splunk AO telemetry paths."""

from splunk_ao.converter.attribute_mapping import (
    CONTENT_ALIAS_BY_GEN_AI,
    SPLUNK_ALIAS_BY_GEN_AI,
    build_span_attributes,
    normalize_attributes_for_export,
)

__all__ = [
    "CONTENT_ALIAS_BY_GEN_AI",
    "SPLUNK_ALIAS_BY_GEN_AI",
    "build_span_attributes",
    "normalize_attributes_for_export",
]
