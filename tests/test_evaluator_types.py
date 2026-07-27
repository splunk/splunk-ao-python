"""
Tests for the refactored metric type hierarchy.

This module tests the four metric types:
- LlmEvaluator: Custom LLM-based metrics with prompt templates
- LocalEvaluator: Local function-based metrics
- CodeEvaluator: Code-based metrics (limited support)
- SplunkAOEvaluator: Built-in Galileo scorers
"""

from __future__ import annotations

import pytest

from galileo_core.schemas.logging.step import StepType
from splunk_ao.evaluator import CodeEvaluator, LlmEvaluator, LocalEvaluator, Evaluator, SplunkAOEvaluator
from splunk_ao.resources.models import OutputTypeEnum, ScorerTypes
from splunk_ao.shared.exceptions import ValidationError


class TestLlmMetric:
    """Tests for LlmEvaluator class."""

    def test_llm_metric_initialization(self):
        """Test basic LlmEvaluator initialization."""
        metric = LlmEvaluator(
            name="test_llm",
            prompt="Rate this response",
            model="gpt-4o-mini",
            judges=3,
            description="Test LLM metric",
            tags=["test", "quality"],
        )

        assert metric.name == "test_llm"
        assert metric.prompt == "Rate this response"
        assert metric.model == "gpt-4o-mini"
        assert metric.judges == 3
        assert metric.description == "Test LLM metric"
        assert metric.tags == ["test", "quality"]
        assert metric.scorer_type == ScorerTypes.LLM
        assert isinstance(metric, LlmEvaluator)
        assert isinstance(metric, Evaluator)

    def test_llm_metric_with_output_type_string(self):
        """Test LlmEvaluator with string output_type."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this", output_type="percentage")

        assert metric.output_type == OutputTypeEnum.PERCENTAGE

    def test_llm_metric_with_output_type_enum(self):
        """Test LlmEvaluator with enum output_type."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this", output_type=OutputTypeEnum.BOOLEAN)

        assert metric.output_type == OutputTypeEnum.BOOLEAN

    def test_llm_metric_backward_compatibility_aliases(self):
        """Test LlmEvaluator with deprecated parameter names."""
        metric = LlmEvaluator(name="test_llm", user_prompt="Old prompt param", model_name="gpt-3.5-turbo", num_judges=2)

        assert metric.prompt == "Old prompt param"
        assert metric.model == "gpt-3.5-turbo"
        assert metric.judges == 2

    def test_llm_metric_new_params_override_old(self):
        """Test that new parameter names override deprecated ones."""
        metric = LlmEvaluator(
            name="test_llm",
            prompt="New prompt",
            user_prompt="Old prompt",
            model="new-model",
            model_name="old-model",
            judges=5,
            num_judges=2,
        )

        assert metric.prompt == "New prompt"
        assert metric.model == "new-model"
        assert metric.judges == 5

    def test_llm_metric_requires_prompt(self):
        """Test that LlmEvaluator requires a prompt."""
        with pytest.raises(ValidationError, match="'prompt'.*must be provided"):
            LlmEvaluator(name="test_llm")

    def test_llm_metric_defaults(self):
        """Test LlmEvaluator default values."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this")

        assert metric.node_level == StepType.llm
        assert metric.cot_enabled is True
        assert metric.output_type == OutputTypeEnum.BOOLEAN

    def test_llm_metric_custom_node_level(self):
        """Test LlmEvaluator with custom node_level."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this", node_level=StepType.workflow)

        assert metric.node_level == StepType.workflow

    def test_llm_metric_cot_disabled(self):
        """Test LlmEvaluator with chain-of-thought disabled."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this", cot_enabled=False)

        assert metric.cot_enabled is False

    def test_llm_metric_repr(self):
        """Test LlmEvaluator string representation."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this", model="gpt-4o-mini", judges=3)

        repr_str = repr(metric)
        assert "LlmEvaluator" in repr_str
        assert "test_llm" in repr_str
        assert "gpt-4o-mini" in repr_str
        assert "3" in repr_str


class TestLocalMetric:
    """Tests for LocalEvaluator class."""

    def test_local_metric_initialization(self):
        """Test basic LocalEvaluator initialization."""

        def my_scorer(trace_or_span):
            return 0.5

        metric = LocalEvaluator(
            name="test_local",
            scorer_fn=my_scorer,
            scorable_types=[StepType.llm],
            aggregatable_types=[StepType.trace],
            description="Test local metric",
            tags=["local", "custom"],
        )

        assert metric.name == "test_local"
        assert metric.scorer_fn == my_scorer
        assert metric.scorable_types == [StepType.llm]
        assert metric.aggregatable_types == [StepType.trace]
        assert metric.description == "Test local metric"
        assert metric.tags == ["local", "custom"]
        assert metric.scorer_type is None
        assert isinstance(metric, LocalEvaluator)
        assert isinstance(metric, Evaluator)

    def test_local_metric_requires_scorer_fn(self):
        """Test that LocalEvaluator requires a scorer_fn."""
        with pytest.raises(ValidationError, match="'scorer_fn' must be provided"):
            LocalEvaluator(name="test_local", scorer_fn=None)

    def test_local_metric_default_types(self):
        """Test LocalEvaluator default scorable and aggregatable types."""

        def my_scorer(trace_or_span):
            return 1.0

        metric = LocalEvaluator(name="test_local", scorer_fn=my_scorer)

        assert metric.scorable_types == [StepType.llm]
        assert metric.aggregatable_types == [StepType.trace]

    def test_local_metric_to_local_metric_config(self):
        """Test conversion to LocalMetricConfig."""

        def my_scorer(trace_or_span):
            return 0.75

        metric = LocalEvaluator(
            name="test_local",
            scorer_fn=my_scorer,
            scorable_types=[StepType.llm, StepType.workflow],
            aggregatable_types=[StepType.trace],
        )

        config = metric.to_local_metric_config()

        assert config.name == "test_local"
        assert config.scorer_fn == my_scorer
        assert config.scorable_types == [StepType.llm, StepType.workflow]
        assert config.aggregatable_types == [StepType.trace]

    def test_local_metric_repr(self):
        """Test LocalEvaluator string representation."""

        def my_scorer(trace_or_span):
            return 0.5

        metric = LocalEvaluator(name="test_local", scorer_fn=my_scorer)

        repr_str = repr(metric)
        assert "LocalEvaluator" in repr_str
        assert "test_local" in repr_str
        assert "my_scorer" in repr_str


class TestCodeMetric:
    """Tests for CodeEvaluator class."""

    def test_code_metric_initialization(self, tmp_path):
        """Test basic CodeEvaluator initialization."""
        metric = CodeEvaluator(name="test_code", description="Test code metric", tags=["code"])

        assert metric.name == "test_code"
        assert metric.description == "Test code metric"
        assert metric.tags == ["code"]
        assert metric.scorer_type == ScorerTypes.CODE
        assert isinstance(metric, CodeEvaluator)
        assert isinstance(metric, Evaluator)

    def test_code_metric_create_not_implemented(self, tmp_path):
        """Test that CodeEvaluator.create() is now implemented."""
        # Create a temporary code file
        code_file = tmp_path / "scorer.py"
        code_file.write_text("def score(trace): return 1.0")

        metric = CodeEvaluator(name="test_code")

        # CodeEvaluator.create() is now implemented, so this test should be updated
        # to verify it works or test it separately
        assert hasattr(metric, "create")
        assert callable(metric.create)


class TestSplunkAOMetric:
    """Tests for SplunkAOEvaluator class."""

    def test_galileo_metric_initialization(self):
        """Test basic SplunkAOEvaluator initialization."""
        metric = SplunkAOEvaluator(name="test_galileo", description="Test Galileo metric", tags=["galileo"])

        assert metric.name == "test_galileo"
        assert metric.description == "Test Galileo metric"
        assert metric.tags == ["galileo"]
        assert isinstance(metric, SplunkAOEvaluator)
        assert isinstance(metric, Evaluator)


class TestMetricBase:
    """Tests for base Evaluator class."""

    def test_metric_has_scorers_attribute(self):
        """Test that Evaluator class has scorers attribute."""
        assert hasattr(Evaluator, "scorers")

    def test_metric_scorers_is_builtin_scorers(self):
        """Test that Evaluator.metrics is a BuiltInEvaluators instance and legacy 'scorers' still exists."""
        from splunk_ao.evaluator import BuiltInEvaluators

        assert isinstance(Evaluator.metrics, BuiltInEvaluators)
        # Legacy alias should still exist and point to the same instance
        assert Evaluator.scorers is Evaluator.metrics

    def test_metric_common_attributes(self, tmp_path):
        """Test that all metric types have common attributes."""

        def my_scorer(trace_or_span):
            return 0.5

        metrics = [
            LlmEvaluator(name="llm", prompt="Rate this"),
            LocalEvaluator(name="local", scorer_fn=my_scorer),
            CodeEvaluator(name="code"),
            SplunkAOEvaluator(name="galileo"),
        ]

        for metric in metrics:
            assert hasattr(metric, "id")
            assert hasattr(metric, "name")
            assert hasattr(metric, "scorer_type")
            assert hasattr(metric, "description")
            assert hasattr(metric, "tags")
            assert hasattr(metric, "created_at")
            assert hasattr(metric, "updated_at")
            assert hasattr(metric, "version")

    def test_metric_to_legacy_metric(self):
        """Test conversion to legacy Evaluator format."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this", version=1)
        legacy = metric.to_legacy_metric()

        assert legacy.name == "test_llm"
        assert legacy.version == 1

    def test_metric_str_representation(self):
        """Test Evaluator __str__ method."""
        metric = LlmEvaluator(name="test_llm", prompt="Rate this")
        str_repr = str(metric)

        assert "LlmEvaluator" in str_repr
        assert "test_llm" in str_repr

    def test_metric_delete_raises_for_local_metric(self):
        """Test that delete raises ValidationError for LocalEvaluator."""

        def my_scorer(trace_or_span):
            return 0.5

        metric = LocalEvaluator(name="test_local", scorer_fn=my_scorer)

        with pytest.raises(ValidationError, match="Local metrics don't exist on the server"):
            metric.delete()

    def test_metric_refresh_raises_for_local_metric(self):
        """Test that refresh raises ValidationError for LocalEvaluator."""

        def my_scorer(trace_or_span):
            return 0.5

        metric = LocalEvaluator(name="test_local", scorer_fn=my_scorer)

        with pytest.raises(ValidationError, match="Local metrics don't exist on the server"):
            metric.refresh()


class TestMetricInheritance:
    """Tests for metric type inheritance."""

    def test_all_metrics_inherit_from_base(self, tmp_path):
        """Test that all metric types inherit from Evaluator."""

        def my_scorer(trace_or_span):
            return 0.5

        # Create a temporary code file for CodeEvaluator
        code_file = tmp_path / "scorer.py"
        code_file.write_text("def score(trace): return 1.0")

        assert isinstance(LlmEvaluator(name="llm", prompt="Rate"), Evaluator)
        assert isinstance(LocalEvaluator(name="local", scorer_fn=my_scorer), Evaluator)
        assert isinstance(CodeEvaluator(name="code"), Evaluator)
        assert isinstance(SplunkAOEvaluator(name="galileo"), Evaluator)

    def test_metric_type_checking(self, tmp_path):
        """Test isinstance checks for different metric types."""

        def my_scorer(trace_or_span):
            return 0.5

        llm = LlmEvaluator(name="llm", prompt="Rate")
        local = LocalEvaluator(name="local", scorer_fn=my_scorer)
        code = CodeEvaluator(name="code")
        galileo = SplunkAOEvaluator(name="galileo")

        assert isinstance(llm, LlmEvaluator) and not isinstance(llm, LocalEvaluator)
        assert isinstance(local, LocalEvaluator) and not isinstance(local, LlmEvaluator)
        assert isinstance(code, CodeEvaluator) and not isinstance(code, LlmEvaluator)
        assert isinstance(galileo, SplunkAOEvaluator) and not isinstance(galileo, LlmEvaluator)


class TestMetricEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_llm_metric_with_minimal_prompt(self):
        """Test LlmEvaluator with minimal prompt."""
        # Minimal prompt that's not empty
        metric = LlmEvaluator(name="test", prompt="Rate")
        assert metric.prompt == "Rate"

    def test_metric_with_empty_tags(self):
        """Test metrics with empty tags list."""
        metric = LlmEvaluator(name="test", prompt="Rate", tags=[])
        assert metric.tags == []

    def test_metric_with_none_tags(self):
        """Test metrics with None tags (should default to empty list)."""
        metric = LlmEvaluator(name="test", prompt="Rate", tags=None)
        assert metric.tags == []

    def test_output_type_mapping(self):
        """Test all output_type string to enum mappings."""
        output_types = {
            "percentage": OutputTypeEnum.PERCENTAGE,
            "boolean": OutputTypeEnum.BOOLEAN,
            "categorical": OutputTypeEnum.CATEGORICAL,
            "count": OutputTypeEnum.COUNT,
            "discrete": OutputTypeEnum.DISCRETE,
            "freeform": OutputTypeEnum.FREEFORM,
            "multilabel": OutputTypeEnum.MULTILABEL,
        }

        for string_type, enum_type in output_types.items():
            metric = LlmEvaluator(name="test", prompt="Rate", output_type=string_type)
            assert metric.output_type == enum_type

    def test_output_type_unknown_string(self):
        """Test that unknown output_type string defaults to PERCENTAGE."""
        metric = LlmEvaluator(name="test", prompt="Rate", output_type="unknown_type")
        assert metric.output_type == OutputTypeEnum.PERCENTAGE

    def test_local_metric_with_multiple_scorable_types(self):
        """Test LocalEvaluator with multiple scorable types."""

        def my_scorer(trace_or_span):
            return 0.5

        metric = LocalEvaluator(
            name="test", scorer_fn=my_scorer, scorable_types=[StepType.llm, StepType.workflow, StepType.agent]
        )

        assert len(metric.scorable_types) == 3
        assert StepType.llm in metric.scorable_types
        assert StepType.workflow in metric.scorable_types
        assert StepType.agent in metric.scorable_types
