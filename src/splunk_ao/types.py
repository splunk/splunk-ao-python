"""
Unified type definitions for the Splunk AO API.

This module provides type aliases that reduce friction when working with evaluators
and other Splunk AO objects.
"""

from splunk_ao.evaluator import Evaluator
from splunk_ao.schema.metrics import LocalMetricConfig, SplunkAOMetrics

# Unified metric type that accepts all valid metric specifications
MetricSpec = (
    SplunkAOMetrics  # Built-in scorer enum (e.g., SplunkAOMetrics.correctness)
    | Evaluator  # Custom or local evaluator object
    | LocalMetricConfig  # Legacy local metric config
    | str  # String name of built-in metric (e.g., "correctness")
)

__all__ = ["MetricSpec"]
