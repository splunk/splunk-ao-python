"""
Unified type definitions for the Splunk AO API.

This module provides type aliases that reduce friction when working with evaluators
and other Splunk AO objects.
"""

from splunk_ao.evaluator import Evaluator
from splunk_ao.schema.metrics import LocalMetricConfig, SplunkAOEvaluators

# Unified evaluator specification type that accepts all valid evaluator inputs
MetricSpec = (
    SplunkAOEvaluators  # Built-in evaluator enum (e.g., SplunkAOEvaluators.correctness)
    | Evaluator  # Custom or local evaluator object
    | LocalMetricConfig  # Legacy local evaluator config
    | str  # String name of built-in evaluator (e.g., "correctness")
)

__all__ = ["MetricSpec"]
