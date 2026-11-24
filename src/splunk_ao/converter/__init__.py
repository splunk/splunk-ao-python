"""Conversion helpers shared by Splunk AO telemetry paths."""

from splunk_ao.converter.attribute_mapping import build_span_attributes
from splunk_ao.converter.span_converter import SpanConverter

__all__ = ["SpanConverter", "build_span_attributes"]
