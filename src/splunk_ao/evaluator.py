from __future__ import annotations

import builtins
import json
import logging
import os
import time
from abc import ABC
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from splunk_ao.model import Model

from galileo_core.schemas.logging.span import Span
from galileo_core.schemas.logging.step import StepType
from galileo_core.schemas.logging.trace import Trace
from galileo_core.schemas.shared.metric import MetricValueType
from splunk_ao.config import SplunkAOConfig
from splunk_ao.configuration import Configuration
from splunk_ao.evaluators import Evaluators
from splunk_ao.resources.api.data import (
    create_code_scorer_version_scorers_scorer_id_version_code_post,
    create_scorers_post,
    get_validate_code_scorer_task_result_scorers_code_validate_task_id_get,
    update_scorers_scorer_id_patch,
    validate_code_scorer_scorers_code_validate_post,
)
from splunk_ao.resources.models import (
    BodyCreateCodeScorerVersionScorersScorerIdVersionCodePost,
    BodyValidateCodeScorerScorersCodeValidatePost,
    CreateScorerRequest,
    HTTPValidationError,
    OutputTypeEnum,
    ScorerTypes,
    TaskResultStatus,
    UpdateScorerRequest,
)
from splunk_ao.resources.models.invalid_result import InvalidResult
from splunk_ao.resources.types import UNSET, File, Unset
from splunk_ao.schema.metrics import LocalMetricConfig, SplunkAOMetrics
from splunk_ao.schema.metrics import Metric as SchemaMetric
from splunk_ao.scorers import Scorers
from splunk_ao.shared.base import StateManagementMixin, SyncState
from splunk_ao.shared.exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)

# Code validation polling parameters are configurable via Configuration:
#   - Configuration.code_validation_timeout (env: SPLUNK_AO_CODE_VALIDATION_TIMEOUT) - default: 60.0s
#   - Configuration.code_validation_initial_delay (env: SPLUNK_AO_CODE_VALIDATION_INITIAL_DELAY) - default: 5.0s
#   - Configuration.code_validation_max_delay (env: SPLUNK_AO_CODE_VALIDATION_MAX_DELAY) - default: 30.0s
#   - Configuration.code_validation_backoff_multiplier (env: SPLUNK_AO_CODE_VALIDATION_BACKOFF_MULTIPLIER) - default: 1.5


class BuiltInEvaluators:
    """
    Provides convenient access to built-in Splunk AO evaluators (formerly "scorers").

    Examples
    --------
        from splunk_ao import Evaluator

        # Access built-in evaluators
        Evaluator.metrics.correctness
        Evaluator.metrics.completeness
        Evaluator.metrics.toxicity
    """

    def __getattr__(self, name: str) -> SplunkAOMetrics:
        """Allow attribute-style access to built-in metrics."""
        # Try to find the metric by name (enum names match UI-visible names)
        for scorer in SplunkAOMetrics:
            if scorer.name == name:
                return scorer
        raise AttributeError(f"Built-in metric '{name}' not found. Available: {[s.name for s in SplunkAOMetrics]}")

    def __dir__(self) -> list[str]:
        """Return list of available metric names for autocomplete."""
        return [scorer.name for scorer in SplunkAOMetrics]


# Backwards-compatible alias
BuiltInScorers = BuiltInEvaluators


class Evaluator(StateManagementMixin, ABC):
    """
    Base class for all Splunk AO evaluators.

    This is an abstract base class that defines common attributes and methods
    for all metric types. Use one of the concrete metric classes instead:

    - **SplunkAOEvaluator**: Built-in Splunk AO evaluators (access via Evaluator.metrics)
    - **LlmEvaluator**: Custom LLM-based metrics with prompt templates
    - **LocalEvaluator**: Local function-based metrics
    - **CodeEvaluator**: Code-based metrics (future support)

    Common Attributes
    -----------------
        id (str | None): The unique metric identifier (UUID).
        name (str): The metric name.
        scorer_type (ScorerTypes | None): The type of scorer.
        description (str): Description of the metric.
        tags (list[str]): Tags associated with the metric.
        created_at (datetime | None): When the metric was created.
        updated_at (datetime | None): When the metric was last updated.
        version (int | None): Evaluator version number.

    Class Attributes
    ----------------
        metrics (BuiltInEvaluators): Access built-in Splunk AO evaluators.

    Examples
    --------
        # 1. Use built-in Splunk AO evaluators
        from splunk_ao import Evaluator, SplunkAOEvaluator, LlmEvaluator, LocalEvaluator, AgentStream

        agent_stream = AgentStream.get(name="my-stream", project_name="my-project")
        agent_stream.set_metrics([
            Evaluator.metrics.correctness,
            Evaluator.metrics.completeness,
        ])

        # 2. Create custom LLM metric
        llm_metric = LlmEvaluator(
            name="response_quality",
            prompt="Rate the quality...",
            model="gpt-4o-mini",
            judges=3,
        ).create()

        # 3. Create local function-based metric
        def my_scorer(trace_or_span):
            return 0.5

        local_metric = LocalEvaluator(
            name="response_length",
            scorer_fn=my_scorer,
        )
    """

    # Class attribute for built-in metrics (preferred name)
    metrics = BuiltInEvaluators()

    # Backwards-compatible property for legacy name
    scorers = metrics

    # Type annotations for common instance attributes
    id: str | None
    name: str
    scorer_type: ScorerTypes | None
    description: str
    tags: list[str]
    created_at: datetime | None
    updated_at: datetime | None
    version: int | None

    # Scorer defaults - available for LLM and built-in Splunk AO evaluators
    # These are returned by the API in the ScorerDefaults object
    model: str | None
    judges: int | None
    cot_enabled: bool | None

    def __init__(
        self, name: str, *, description: str = "", tags: list[str] | None = None, version: int | None = None
    ) -> None:
        """
        Initialize a base Evaluator instance with common attributes.

        Args:
            name: The name of the metric.
            description: Description of the metric.
            tags: Tags associated with the metric.
            version: Specific version to reference (for existing metrics).
        """
        super().__init__()
        self.name = name
        self.description = description
        self.tags = tags if tags is not None else []
        self.version = version
        self.id = None
        self.created_at = None
        self.updated_at = None
        self.scorer_type = None

        # Initialize scorer defaults (populated from API for LLM and Splunk AO evaluators)
        self.model = None
        self.judges = None
        self.cot_enabled = None

        self._set_state(SyncState.LOCAL_ONLY)

    @staticmethod
    def _parse_output_type(
        output_type: str | OutputTypeEnum | None, default: OutputTypeEnum | None = None
    ) -> OutputTypeEnum | None:
        """Map a string or OutputTypeEnum to OutputTypeEnum, with an optional fallback default."""
        if output_type is None:
            return default
        if isinstance(output_type, OutputTypeEnum):
            return output_type
        _map = {
            "percentage": OutputTypeEnum.PERCENTAGE,
            "boolean": OutputTypeEnum.BOOLEAN,
            "categorical": OutputTypeEnum.CATEGORICAL,
            "count": OutputTypeEnum.COUNT,
            "discrete": OutputTypeEnum.DISCRETE,
            "freeform": OutputTypeEnum.FREEFORM,
            "multilabel": OutputTypeEnum.MULTILABEL,
        }
        return _map.get(output_type.lower(), default)

    @classmethod
    def _create_metric_from_type(cls, scorer_type: ScorerTypes) -> Evaluator:
        """
        Create the appropriate Evaluator subclass instance based on scorer_type.

        This is a factory method that centralizes the logic for instantiating
        the correct metric subclass based on the scorer type returned from the API.

        Args:
            scorer_type: The scorer type from the API response.

        Returns
        -------
            Evaluator: An uninitialized instance of the appropriate subclass
                   (LlmEvaluator, CodeEvaluator, or SplunkAOEvaluator).

        Examples
        --------
            instance = Evaluator._create_metric_from_type(ScorerTypes.LLM)
            # Returns: LlmEvaluator instance
        """
        if scorer_type == ScorerTypes.LLM:
            return LlmEvaluator.__new__(LlmEvaluator)
        if scorer_type == ScorerTypes.CODE:
            return CodeEvaluator.__new__(CodeEvaluator)
        # Default to SplunkAOEvaluator for built-in scorers (LUNA, PRESET, etc.)
        return SplunkAOEvaluator.__new__(SplunkAOEvaluator)

    @classmethod
    def get(cls, *, id: str | None = None, name: str | None = None) -> Evaluator | None:
        """
        Get an existing metric by ID or name.

        Returns the appropriate subclass instance based on scorer_type.

        Args:
            id: The metric ID (UUID).
            name: The metric name.

        Returns
        -------
            Optional[Evaluator]: The metric if found (SplunkAOEvaluator, LlmEvaluator, or CodeEvaluator), None otherwise.

        Raises
        ------
            ValidationError: If neither or both id and name are provided.

        Examples
        --------
            # Get by name - returns appropriate subclass
            metric = Evaluator.get(name="factuality-checker")

            # Get by ID
            metric = Evaluator.get(id="abc-123-def")
        """
        if id is not None and name is not None:
            raise ValidationError("Cannot specify both id and name")
        if id is None and name is None:
            raise ValidationError("Must specify either id or name")

        scorers_service = Scorers()

        if name is not None:
            scorers = scorers_service.list(name=name)
            if not scorers:
                return None
            retrieved_scorer = next((s for s in scorers if s.name == name), None)
            if retrieved_scorer is None:
                return None
        else:
            assert id is not None
            scorers = scorers_service.list()
            retrieved_scorer = next((s for s in scorers if s.id == id), None)
            if retrieved_scorer is None:
                return None

        # Create appropriate subclass instance based on scorer_type
        instance = cls._create_metric_from_type(retrieved_scorer.scorer_type)
        StateManagementMixin.__init__(instance)
        instance._populate_from_scorer_response(retrieved_scorer)
        instance._set_state(SyncState.SYNCED)
        return instance

    @classmethod
    def list(
        cls, *, name_filter: str | None = None, scorer_types: list[ScorerTypes] | None = None
    ) -> builtins.list[Evaluator]:
        """
        List metrics with optional filtering.

        Returns appropriate subclass instances based on scorer_type.

        Args:
            name_filter: Filter metrics by exact name match.
            scorer_types: Filter by scorer types.

        Returns
        -------
            list[Evaluator]: List of metrics matching the criteria (with appropriate subclass types).

        Examples
        --------
            # List all metrics
            metrics = Evaluator.list()

            # List LLM metrics only
            metrics = Evaluator.list(scorer_types=[ScorerTypes.LLM])

            # List by name
            metrics = Evaluator.list(name_filter="factuality")
        """
        logger.debug(f"Evaluator.list: name_filter='{name_filter}' types={scorer_types} - started")
        scorers_service = Scorers()
        retrieved_scorers = scorers_service.list(name=name_filter, types=scorer_types)
        logger.debug(f"Evaluator.list: found {len(retrieved_scorers)} metrics - completed")

        result: builtins.list[Evaluator] = []
        for retrieved_scorer in retrieved_scorers:
            # Create appropriate subclass instance based on scorer_type
            instance = cls._create_metric_from_type(retrieved_scorer.scorer_type)
            StateManagementMixin.__init__(instance)
            instance._populate_from_scorer_response(retrieved_scorer)
            instance._set_state(SyncState.SYNCED)
            result.append(instance)

        return result

    @classmethod
    def delete_by_name(cls, name: str) -> None:
        """
        Delete a metric by name without retrieving it first.

        This is more efficient than calling `Evaluator.get(name=...).delete()`
        when you only need to delete and don't need the metric object.

        Args:
            name: The name of the metric to delete.

        Raises
        ------
            ValueError: If no metric with the given name exists.

        Examples
        --------
            # Delete without retrieving first
            Evaluator.delete_by_name("old-metric")

            # Alternative (less efficient)
            metric = Evaluator.get(name="old-metric")
            metric.delete()
        """
        logger.info(f"Evaluator.delete_by_name: name='{name}' - started")
        try:
            metrics_service = Evaluators()
            metrics_service.delete_evaluator(name=name)
            logger.info(f"Evaluator.delete_by_name: name='{name}' - completed")
        except Exception as e:
            logger.error(f"Evaluator.delete_by_name: name='{name}' - failed: {e}")
            raise

    def _populate_from_scorer_response(self, scorer_response: Any) -> None:
        """Populate instance attributes from a ScorerResponse object."""
        # Pre-compute optional common attributes
        description = (
            ""
            if isinstance(scorer_response.description, Unset) or scorer_response.description is None
            else scorer_response.description
        )
        created_at = None if isinstance(scorer_response.created_at, Unset) else scorer_response.created_at
        updated_at = None if isinstance(scorer_response.updated_at, Unset) else scorer_response.updated_at

        # Extract defaults - available for LLM and built-in Splunk AO evaluators
        # These are returned by the API for preset scorers too
        if not isinstance(scorer_response.defaults, Unset) and scorer_response.defaults is not None:
            model = scorer_response.defaults.model_name if hasattr(scorer_response.defaults, "model_name") else None
            judges = scorer_response.defaults.num_judges if hasattr(scorer_response.defaults, "num_judges") else None
            cot_enabled = (
                scorer_response.defaults.cot_enabled if hasattr(scorer_response.defaults, "cot_enabled") else None
            )
        else:
            model = None
            judges = None
            cot_enabled = None

        self._sync_attrs(
            id=scorer_response.id,
            name=scorer_response.name,
            scorer_type=scorer_response.scorer_type,
            tags=scorer_response.tags,
            version=None,
            description=description,
            created_at=created_at,
            updated_at=updated_at,
            model=model,
            judges=judges,
            cot_enabled=cot_enabled,
        )

        # LLM-specific attributes (only set if this is an LlmEvaluator)
        if isinstance(self, LlmEvaluator):
            output_type = None if isinstance(scorer_response.output_type, Unset) else scorer_response.output_type
            prompt = None if isinstance(scorer_response.user_prompt, Unset) else scorer_response.user_prompt

            # Extract scoreable node types
            if not isinstance(scorer_response.scoreable_node_types, Unset) and scorer_response.scoreable_node_types:
                try:
                    node_level = StepType(scorer_response.scoreable_node_types[0])
                except (ValueError, IndexError):
                    node_level = None
            else:
                node_level = None

            ground_truth = (
                False
                if isinstance(scorer_response.ground_truth, Unset) or scorer_response.ground_truth is None
                else scorer_response.ground_truth
            )

            self._sync_attrs(output_type=output_type, prompt=prompt, node_level=node_level, ground_truth=ground_truth)

        # Code-specific attributes (only set if this is a CodeEvaluator)
        if isinstance(self, CodeEvaluator):
            # Extract scoreable node types
            if not isinstance(scorer_response.scoreable_node_types, Unset) and scorer_response.scoreable_node_types:
                try:
                    code_node_level = StepType(scorer_response.scoreable_node_types[0])
                except (ValueError, IndexError):
                    code_node_level = None
            else:
                code_node_level = None

            code_output_type = None if isinstance(scorer_response.output_type, Unset) else scorer_response.output_type

            self._sync_attrs(node_level=code_node_level, output_type=code_output_type)

    def update(self, **kwargs: Any) -> Evaluator:
        """
        Update this metric's properties on the API.

        Only ``name``, ``description``, and ``tags`` can be updated via this method.
        On success the instance is updated with the API response and returned in SYNCED state.

        Parameters
        ----------
        **kwargs : Any
            Fields to update. Supported keys: ``name``, ``description``, ``tags``.

        Returns
        -------
            Evaluator: This metric instance with updated attributes from the API.

        Raises
        ------
            ValidationError: If this is a local metric.
            ValueError: If the metric ID is not set, the metric is deleted,
                or the metric is in FAILED_SYNC state.
            ValueError: If any unsupported fields are passed.
            APIError: If the API returns a validation error or empty response.
            Exception: If the API call fails (state is set to FAILED_SYNC).

        Examples
        --------
            metric = Evaluator.get(name="factuality-checker")
            metric.update(name="new-name", description="Updated description")
            assert metric.is_synced()
        """
        if isinstance(self, LocalEvaluator):
            raise ValidationError("Local metrics don't exist on the server and can't be updated.")
        if self.id is None:
            raise ValueError("Evaluator ID is not set. Cannot update a local-only metric.")
        if self.sync_state == SyncState.DELETED:
            raise ValueError("Cannot update a deleted metric.")
        if self.sync_state == SyncState.FAILED_SYNC:
            raise ValueError(
                "Cannot update a metric in FAILED_SYNC state. "
                "Call refresh() to re-sync from the API, then retry your changes."
            )

        valid_fields = {"name", "description", "tags"}
        invalid_fields = set(kwargs) - valid_fields
        if invalid_fields:
            raise ValueError(f"Invalid update fields: {sorted(invalid_fields)!r}. Valid fields: {sorted(valid_fields)}")

        body = UpdateScorerRequest(
            name=kwargs.get("name", UNSET), description=kwargs.get("description", UNSET), tags=kwargs.get("tags", UNSET)
        )

        logger.info(f"Evaluator.update: id='{self.id}' name='{self.name}' - started")
        try:
            config = SplunkAOConfig.get()
            response = update_scorers_scorer_id_patch.sync(scorer_id=self.id, client=config.api_client, body=body)
        except Exception as e:
            self._set_state(SyncState.FAILED_SYNC, error=e)
            logger.error(f"Evaluator.update: id='{self.id}' - failed: {e}")
            raise

        if isinstance(response, HTTPValidationError):
            raise APIError(f"Evaluator update validation error: {response.detail}")
        if response is None:
            raise APIError(f"Evaluator update returned empty response for id '{self.id}'")

        self._populate_from_scorer_response(response)
        self._set_state(SyncState.SYNCED)
        logger.info(f"Evaluator.update: id='{self.id}' - completed")
        return self

    def delete(self) -> None:
        """
        Delete this metric.

        Only works for server-side metrics. Local metrics don't need deletion.

        Raises
        ------
            ValidationError: If this is a local metric.
            ValueError: If the metric is not synced.

        Examples
        --------
            metric = Evaluator.get(name="factuality-checker")
            metric.delete()
        """
        if isinstance(self, LocalEvaluator):
            raise ValidationError("Local metrics don't exist on the server and can't be deleted.")

        if self.id is None:
            raise ValueError("Evaluator ID is not set. Cannot delete a local-only metric.")

        try:
            logger.info(f"Evaluator.delete: id='{self.id}' name='{self.name}' - started")
            metrics_service = Evaluators()
            metrics_service.delete_evaluator(name=self.name)
            self._set_state(SyncState.DELETED)
            logger.info(f"Evaluator.delete: id='{self.id}' - completed")
        except Exception as e:
            self._set_state(SyncState.FAILED_SYNC, error=e)
            logger.error(f"Evaluator.delete: id='{self.id}' - failed: {e}")
            raise

    def refresh(self) -> None:
        """
        Refresh this metric's state from the API.

        Updates all attributes with the latest values from the remote API.

        Raises
        ------
            ValidationError: If this is a local metric.
            ValueError: If the metric is not synced.
            Exception: If the API call fails or the metric no longer exists.

        Examples
        --------
            metric.refresh()
            assert metric.is_synced()
        """
        if isinstance(self, LocalEvaluator):
            raise ValidationError("Local metrics don't exist on the server and can't be refreshed.")

        if self.id is None:
            raise ValueError("Evaluator ID is not set. Cannot refresh a local-only metric.")

        try:
            logger.debug(f"Evaluator.refresh: id='{self.id}' - started")
            scorers_service = Scorers()
            scorers = scorers_service.list()
            retrieved_scorer = next((s for s in scorers if s.id == self.id), None)

            if retrieved_scorer is None:
                raise ValueError(f"Evaluator with id '{self.id}' no longer exists")

            self._populate_from_scorer_response(retrieved_scorer)
            self._set_state(SyncState.SYNCED)
            logger.debug(f"Evaluator.refresh: id='{self.id}' - completed")
        except Exception as e:
            self._set_state(SyncState.FAILED_SYNC, error=e)
            logger.error(f"Evaluator.refresh: id='{self.id}' - failed: {e}")
            raise

    def to_legacy_metric(self) -> SchemaMetric:
        """
        Convert to legacy splunk_ao.schema.metrics.Evaluator format.

        This enables backward compatibility with existing code that uses
        the legacy Evaluator class.

        Returns
        -------
            SchemaMetric: Legacy metric object with name and version.

        Examples
        --------
            metric = Evaluator.get(name="my-metric")
            legacy = metric.to_legacy_metric()
            # Use with existing APIs
        """
        return SchemaMetric(name=self.name, version=self.version)

    def __str__(self) -> str:
        """String representation of the metric."""
        type_name = self.__class__.__name__
        scorer_type_str = self.scorer_type.value if self.scorer_type else "unknown"
        return f"{type_name}(name='{self.name}', id='{self.id}', scorer_type='{scorer_type_str}')"

    def __repr__(self) -> str:
        """Detailed string representation of the metric."""
        type_name = self.__class__.__name__
        return f"{type_name}(name='{self.name}', id='{self.id}')"


# ============================================================================
# Concrete Evaluator Types
# ============================================================================


class LlmEvaluator(Evaluator):
    """
    LLM-based metric with custom prompt templates.

    This metric type allows you to create custom metrics evaluated by an LLM
    judge using a prompt template.

    Attributes
    ----------
        prompt (str | None): Prompt template for the LLM scorer.
        model (str | None): Model name/alias to use for scoring (stored as string).
        judges (int | None): Number of judges to use for scoring.
        cot_enabled (bool | None): Whether chain-of-thought is enabled.
        node_level (StepType | None): Node level for the metric.
        output_type (OutputTypeEnum | None): Output type for the metric.

    Configuration
    -------------
        Default values for `model` and `judges` can be configured via:
        - Configuration.default_scorer_model (env: SPLUNK_AO_DEFAULT_SCORER_MODEL)
        - Configuration.default_scorer_judges (env: SPLUNK_AO_DEFAULT_SCORER_JUDGES)

    Examples
    --------
        # Create custom LLM metric with string model name
        metric = LlmEvaluator(
            name="response_quality",
            prompt='''
            Rate the quality of this response on a scale of 1-10.

            Question: {input}
            Answer: {output}

            Return only the numerical score (1-10).
            ''',
            model="gpt-4o-mini",  # String model name
            judges=3,
            node_level=StepType.llm,
            description="Rates response quality",
            tags=["quality", "custom"],
            output_type=OutputTypeEnum.PERCENTAGE,
            cot_enabled=True,
        ).create()

        # Or use a Model object from Integration
        from splunk_ao.integration import Integration
        gpt_model = Integration.openai.get_model(alias="gpt-4o-mini")
        metric = LlmEvaluator(
            name="response_quality",
            prompt="Rate quality 1-10: {input} -> {output}",
            model=gpt_model,  # Model object
            judges=3,
        ).create()
    """

    # Type annotations for LLM-specific attributes
    prompt: str | None
    model: str | None
    judges: int | None
    cot_enabled: bool | None
    node_level: StepType | None
    output_type: OutputTypeEnum | None
    ground_truth: bool

    def __init__(
        self,
        name: str,
        *,
        # LLM metric parameters (improved API)
        prompt: str | None = None,
        model: Model | str | None = None,
        judges: int | None = None,
        # Backward compatibility aliases
        user_prompt: str | None = None,
        model_name: str | None = None,
        num_judges: int | None = None,
        # LLM-specific parameters
        node_level: StepType | None = None,
        cot_enabled: bool | None = None,
        output_type: str | OutputTypeEnum | None = None,
        ground_truth: bool = False,
        # Common parameters
        description: str = "",
        tags: list[str] | None = None,
        version: int | None = None,
    ) -> None:
        """
        Initialize an LLM metric.

        Args:
            name: The name of the metric.
            prompt: Prompt template for LLM scorers (preferred over user_prompt).
            model: Model object or model name string to use (preferred over model_name).
                   Defaults to Configuration.default_scorer_model.
            judges: Number of judges (preferred over num_judges). Defaults to Configuration.default_scorer_judges.
            user_prompt: [Deprecated] Use 'prompt' instead.
            model_name: [Deprecated] Use 'model' instead.
            num_judges: [Deprecated] Use 'judges' instead.
            node_level: Node level for the metric. Defaults to StepType.llm.
            cot_enabled: Whether chain-of-thought is enabled. Defaults to True.
            output_type: Output type ("percentage", "boolean", etc.).
            ground_truth: Whether the scorer requires ground truth (``reference_output``) from the dataset.
                When True, the judge LLM receives the row's ground-truth value in its prompt.
            description: Description of the metric.
            tags: Tags associated with the metric.
            version: Specific version to reference (for existing metrics).

        Raises
        ------
            ValidationError: If prompt is not provided.
        """
        super().__init__(name=name, description=description, tags=tags, version=version)

        # Handle parameter aliases (new names preferred)
        final_prompt = prompt or user_prompt

        # Handle model parameter - extract alias from Model object if needed
        if model is not None:
            # Local import to avoid circular dependency
            from splunk_ao.model import Model

            final_model = model.alias if isinstance(model, Model) else model
        else:
            final_model = model_name or Configuration.default_scorer_model

        final_judges = (
            judges
            if judges is not None
            else (num_judges if num_judges is not None else Configuration.default_scorer_judges)
        )

        if final_prompt is None:
            raise ValidationError("'prompt' (or 'user_prompt') must be provided for LLM-based metrics.")

        # Initialize LLM-specific attributes
        self.prompt = final_prompt
        self.model = final_model  # Now always a string (alias)
        self.judges = final_judges
        self.node_level = node_level or StepType.llm
        self.cot_enabled = cot_enabled if cot_enabled is not None else True

        # Handle output_type (accept string or enum)
        if isinstance(output_type, str):
            self.output_type = Evaluator._parse_output_type(output_type, default=OutputTypeEnum.PERCENTAGE)
        else:
            self.output_type = output_type or OutputTypeEnum.BOOLEAN

        self.ground_truth = ground_truth

        self.scorer_type = ScorerTypes.LLM

    def create(self) -> LlmEvaluator:
        """
        Persist this LLM metric to the API.

        Returns
        -------
            LlmEvaluator: This metric instance with updated attributes from the API.

        Raises
        ------
            ValidationError: If configuration is invalid.
            Exception: If the API call fails.

        Examples
        --------
            metric = LlmEvaluator(
                name="quality_check",
                prompt="Rate the quality...",
                model="gpt-4o-mini"
            ).create()
            assert metric.is_synced()
        """
        try:
            logger.info(f"LlmEvaluator.create: name='{self.name}' - started")

            metrics_service = Evaluators()
            created_version = metrics_service.create_custom_llm_evaluator(
                name=self.name,
                user_prompt=self.prompt or "",
                node_level=self.node_level if self.node_level is not None else StepType.llm,
                cot_enabled=self.cot_enabled if self.cot_enabled is not None else True,
                model_name=self.model if self.model is not None else Configuration.default_scorer_model,
                num_judges=self.judges if self.judges is not None else Configuration.default_scorer_judges,
                description=self.description,
                tags=self.tags,
                output_type=self.output_type
                if isinstance(self.output_type, OutputTypeEnum)
                else OutputTypeEnum.BOOLEAN,
                ground_truth=self.ground_truth,
            )

            # Update attributes from response without triggering dirty-tracking
            self._sync_attrs(
                id=str(created_version.scorer_id),
                created_at=created_version.created_at,
                updated_at=created_version.updated_at,
            )

            # Refresh to get full scorer details
            self.refresh()

            logger.info(f"LlmEvaluator.create: id='{self.id}' - completed")
            return self
        except ValidationError:
            raise
        except Exception as e:
            self._set_state(SyncState.FAILED_SYNC, error=e)
            logger.error(f"LlmEvaluator.create: name='{self.name}' - failed: {e}")
            raise

    def __repr__(self) -> str:
        """Detailed string representation of the metric."""
        return f"LlmEvaluator(name='{self.name}', id='{self.id}', model='{self.model}', judges={self.judges})"


class CodeEvaluator(Evaluator):
    r"""
    Code-based metric.

    This metric type is for code-based scorers that execute custom code
    to evaluate traces/spans.

    Attributes
    ----------
        node_level (StepType | None): Node level for the metric.
        code (str | None): The Python code for the scorer.
        output_type (OutputTypeEnum | None): Output type for the metric.

    Examples
    --------
        # Get existing code metric
        metric = Evaluator.get(name="my-code-metric")
        assert isinstance(metric, CodeEvaluator)

        # Create code metric with inline code
        metric = CodeEvaluator(
            name="custom_code_scorer",
            code="def scorer_fn(step_object):\\n    return 1.0",
            description="Custom code-based scorer",
            tags=["custom", "code"],
            node_level=StepType.llm,
            output_type=OutputTypeEnum.PERCENTAGE,
        ).create()

        # Load code from file
        metric = CodeEvaluator(
            name="custom_code_scorer",
            node_level=StepType.llm,
        ).load_code("./scorers/my_scorer.py").create()
    """

    # Type annotations for code-specific attributes
    node_level: StepType | None
    code: str | None
    output_type: OutputTypeEnum | None
    required_metrics: list[str] | None

    def __init__(
        self,
        name: str,
        *,
        code: str | None = None,
        node_level: StepType | None = None,
        output_type: str | OutputTypeEnum | None = None,
        required_metrics: list[str] | None = None,
        description: str = "",
        tags: list[str] | None = None,
        version: int | None = None,
    ) -> None:
        """
        Initialize a Code metric.

        Args:
            name: The name of the metric.
            code: The Python code for the scorer (optional, can be set later or loaded from file).
            node_level: Node level for the metric. Defaults to StepType.llm.
            output_type: Output type for the metric ("percentage", "boolean", "categorical",
                "count", "discrete"). Accepts string or OutputTypeEnum.
            required_metrics: List of metric names that this code metric depends on.
            description: Description of the metric.
            tags: Tags associated with the metric.
            version: Specific version to reference (for existing metrics).
        """
        super().__init__(name=name, description=description, tags=tags, version=version)

        self.code = code
        self.node_level = node_level or StepType.llm
        self.required_metrics = required_metrics
        self.scorer_type = ScorerTypes.CODE

        self.output_type = Evaluator._parse_output_type(output_type)

    def load_code(self, code_file_path: str) -> CodeEvaluator:
        """
        Load code from a file into this metric instance.

        Args:
            code_file_path: Path to the Python file containing the scorer code.

        Returns
        -------
            CodeEvaluator: This metric instance with code loaded from the file (for chaining).

        Raises
        ------
            ValidationError: If the code file doesn't exist or can't be read.

        Examples
        --------
            # Load code from file
            metric = CodeEvaluator(
                name="custom_code_scorer",
                node_level=StepType.llm,
            ).load_code("./scorers/my_scorer.py").create()
        """
        if not os.path.isfile(code_file_path):
            raise ValidationError(f"Code file not found: {code_file_path}")

        try:
            with open(code_file_path, encoding="utf-8") as f:
                self.code = f.read()
        except Exception as e:
            raise ValidationError(f"Failed to read code file {code_file_path}: {e}")

        return self

    def _validate_code(self, config: SplunkAOConfig) -> str:
        """
        Validate the code by submitting it to the validation endpoint and polling for results.

        Args:
            config: The Splunk AO configuration with API client.

        Returns
        -------
            str: The validation result as a JSON string to pass to create_code_scorer_version.

        Raises
        ------
            ValidationError: If validation fails or the code is invalid.
            ValueError: If the API returns an unexpected response.
        """
        assert self.code is not None
        assert self.node_level is not None

        # Step 1: Submit the code for validation
        code_bytes = self.code.encode("utf-8")
        code_file = File(payload=code_bytes, file_name="scorer.py")
        validate_body = BodyValidateCodeScorerScorersCodeValidatePost(
            file=code_file, scoreable_node_types=[self.node_level.value], required_scorers=self.required_metrics
        )

        validate_response = validate_code_scorer_scorers_code_validate_post.sync(
            client=config.api_client, body=validate_body
        )

        if validate_response is None:
            logger.debug("CodeEvaluator._validate_code: No response from validate_code_scorer")
            raise ValueError("Failed to validate code: No response from API")

        task_id = validate_response.task_id
        logger.debug(f"CodeEvaluator._validate_code: task_id='{task_id}' - validation started")

        # Step 2: Poll for validation result with time-based timeout
        start_time_seconds = time.time()
        attempt = 0
        while True:
            elapsed_seconds = time.time() - start_time_seconds
            timeout_seconds = Configuration.code_validation_timeout
            if elapsed_seconds >= timeout_seconds:
                raise ValidationError(f"Code validation timed out after {timeout_seconds:.0f} seconds")

            task_result = get_validate_code_scorer_task_result_scorers_code_validate_task_id_get.sync(
                task_id=task_id, client=config.api_client
            )

            if task_result is None:
                logger.debug(f"CodeEvaluator._validate_code: No response for task_id='{task_id}'")
                raise ValueError("Failed to get validation result: No response from API")

            if task_result.status == TaskResultStatus.COMPLETED:
                logger.debug(f"CodeEvaluator._validate_code: task_id='{task_id}' - validation completed")

                # Extract and validate the result
                result = task_result.result

                # Handle string result (already serialized)
                if isinstance(result, str):
                    return result

                # Handle ValidateRegisteredScorerResult or similar objects with to_dict
                if hasattr(result, "to_dict"):
                    # Check if it's an invalid result (has error_message in nested result)
                    if hasattr(result, "result") and isinstance(result.result, InvalidResult):
                        raise ValidationError(f"Code validation failed: {result.result.error_message}")
                    # Return the result as JSON string
                    return json.dumps(result.to_dict())

                raise ValueError(f"Unexpected validation result type: {type(result)}")

            if task_result.status == TaskResultStatus.FAILED:
                error_msg = "Code validation failed"
                if isinstance(task_result.result, str):
                    error_msg = f"Code validation failed: {task_result.result}"
                raise ValidationError(error_msg)

            if task_result.status == TaskResultStatus.PENDING:
                # Calculate delay with exponential backoff
                delay_seconds = min(
                    Configuration.code_validation_initial_delay
                    * (Configuration.code_validation_backoff_multiplier**attempt),
                    Configuration.code_validation_max_delay,
                )

                logger.debug(
                    f"CodeEvaluator._validate_code: task_id='{task_id}' - pending "
                    f"(elapsed: {elapsed_seconds:.1f}s/{timeout_seconds:.0f}s, next delay: {delay_seconds:.2f}s)"
                )
                time.sleep(delay_seconds)
                attempt += 1
            else:
                raise ValueError(f"Unknown task status: {task_result.status}")

    def create(self) -> CodeEvaluator:
        r"""
        Persist this Code metric to the API.

        This method validates the code first by submitting it to the validation
        endpoint, polling for the result, and then creating the scorer with the
        validated result.

        Returns
        -------
            CodeEvaluator: This metric instance with updated attributes from the API.

        Raises
        ------
            ValidationError: If code is not set, validation fails, or configuration is invalid.
            Exception: If the API call fails.

        Examples
        --------
            # Create with inline code
            metric = CodeEvaluator(
                name="custom_code_scorer",
                code="def scorer_fn(step_object):\\n    return 1.0",
                node_level=StepType.llm,
            ).create()
            assert metric.is_synced()

            # Create by loading from file
            metric = CodeEvaluator(
                name="custom_code_scorer",
                node_level=StepType.llm,
            ).load_code("./scorers/my_scorer.py").create()
            assert metric.is_synced()
        """
        # Validate that code is set
        if self.code is None:
            raise ValidationError(
                "Code is not set. Either pass 'code' to __init__() or use CodeEvaluator.load_code() to load from a file."
            )

        try:
            logger.info(f"CodeEvaluator.create: name='{self.name}' - started")

            config = SplunkAOConfig.get()

            # Ensure node_level is set (should always be set in __init__, but checking for type safety)
            assert self.node_level is not None

            # Step 1: Validate the code and get validation result
            logger.debug(f"CodeEvaluator.create: name='{self.name}' - validating code")
            validation_result = self._validate_code(config)
            logger.debug(f"CodeEvaluator.create: name='{self.name}' - code validated successfully")

            # Step 2: Create the scorer
            scorer_request = CreateScorerRequest(
                name=self.name,
                scorer_type=ScorerTypes.CODE,
                description=self.description,
                tags=self.tags,
                scoreable_node_types=[self.node_level.value],
                output_type=self.output_type,
                required_scorers=self.required_metrics,
            )

            scorer_response = create_scorers_post.sync(client=config.api_client, body=scorer_request)

            if scorer_response is None:
                logger.debug("CodeEvaluator.create: No response from create_scorers_post")
                raise ValueError("Failed to create code-based metric: No response from API")

            # Step 3: Create the code scorer version with file upload and validation result
            # Convert the code string to bytes for file upload
            code_bytes = self.code.encode("utf-8")
            code_file = File(payload=code_bytes, file_name="scorer.py")
            version_body = BodyCreateCodeScorerVersionScorersScorerIdVersionCodePost(
                file=code_file, validation_result=validation_result
            )

            created_version = create_code_scorer_version_scorers_scorer_id_version_code_post.sync(
                scorer_id=scorer_response.id, client=config.api_client, body=version_body
            )

            if created_version is None:
                logger.debug(
                    "CodeEvaluator.create: No response from create_code_scorer_version_scorers_scorer_id_version_code_post"
                )
                raise ValueError("Failed to create code-based metric: No response from API")

            # Update attributes from response
            self.id = str(scorer_response.id)
            self.created_at = scorer_response.created_at
            self.updated_at = scorer_response.updated_at

            # Refresh to get full scorer details
            self.refresh()

            logger.info(f"CodeEvaluator.create: id='{self.id}' - completed")
            return self
        except ValidationError:
            raise
        except Exception as e:
            self._set_state(SyncState.FAILED_SYNC, error=e)
            logger.error(f"CodeEvaluator.create: name='{self.name}' - failed: {e}")
            raise

    def __repr__(self) -> str:
        """Detailed string representation of the metric."""
        return f"CodeEvaluator(name='{self.name}', id='{self.id}'')"


class SplunkAOEvaluator(Evaluator):
    """
    Built-in Splunk AO evaluator.

    This evaluator type represents Splunk AO's built-in scorers like correctness,
    completeness, toxicity, etc. Access these via `Evaluator.metrics`.

    Examples
    --------
        # Access built-in scorers
        from splunk_ao import Evaluator, AgentStream

        agent_stream = AgentStream.get(name="my-stream", project_name="my-project")
        agent_stream.set_metrics([
            Evaluator.metrics.correctness,
            Evaluator.metrics.completeness,
            Evaluator.metrics.toxicity,
        ])

        # Or get by name
        metric = Evaluator.get(name="correctness")
        assert isinstance(metric, SplunkAOEvaluator)
    """

    def __init__(
        self, name: str, *, description: str = "", tags: list[str] | None = None, version: int | None = None
    ) -> None:
        """
        Initialize a Splunk AO evaluator.

        Args:
            name: The name of the metric.
            description: Description of the metric.
            tags: Tags associated with the metric.
            version: Specific version to reference (for existing metrics).
        """
        super().__init__(name=name, description=description, tags=tags, version=version)
        # Splunk AO evaluators can have various scorer types, set during population


class LocalEvaluator(Evaluator):
    """
    Local function-based metric.

    This metric type uses a Python function to score traces/spans locally
    without making API calls. Useful for simple, deterministic metrics.

    Attributes
    ----------
        scorer_fn (Callable): Scoring function that takes a Trace or Span and returns either a
            score, or a ``(score, metadata)`` tuple — when a tuple is returned, the metadata dict
            is attached to the step under ``{name}_metadata`` for explainability.
        scorable_types (list[StepType]): Types that can be scored.
        aggregatable_types (list[StepType]): Types that can be aggregated.

    Examples
    --------
        # Create local function-based metric
        def response_length_scorer(trace_or_span):
            if hasattr(trace_or_span, "output") and trace_or_span.output:
                return min(len(trace_or_span.output) / 100.0, 1.0)
            return 0.0

        local_metric = LocalEvaluator(
            name="response_length",
            scorer_fn=response_length_scorer,
            scorable_types=[StepType.llm],
            aggregatable_types=[StepType.trace],
        )

        # Or return (score, metadata) for explainability
        EXPECTED = ["relevance", "accuracy", "completeness"]
        def keyword_coverage(trace_or_span):
            text = getattr(trace_or_span, "output", "") or ""
            matched = [k for k in EXPECTED if k in text]
            return len(matched) / len(EXPECTED), {
                "matched": matched,
                "missing": [k for k in EXPECTED if k not in text],
            }

        # Use with log stream
        log_stream.set_metrics([local_metric])
    """

    # Type annotations for local metric attributes
    scorer_fn: Callable[[Trace | Span], MetricValueType | tuple[MetricValueType, dict[str, Any]]]
    scorable_types: list[StepType]
    aggregatable_types: list[StepType]

    def __init__(
        self,
        name: str,
        *,
        scorer_fn: Callable[[Trace | Span], MetricValueType | tuple[MetricValueType, dict[str, Any]]],
        scorable_types: list[StepType] | None = None,
        aggregatable_types: list[StepType] | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> None:
        """
        Initialize a local function-based metric.

        Args:
            name: The name of the metric.
            scorer_fn: Scoring function for the metric. May return either a bare score, or a
                ``(score, metadata)`` tuple where ``metadata`` is a JSON-serializable dict
                surfaced under ``{name}_metadata`` on the step.
            scorable_types: Step types that can be scored. Defaults to [StepType.llm].
            aggregatable_types: Step types for aggregation. Defaults to [StepType.trace].
            description: Description of the metric.
            tags: Tags associated with the metric.

        Raises
        ------
            ValidationError: If scorer_fn is not provided.
        """
        super().__init__(name=name, description=description, tags=tags)

        if scorer_fn is None:
            raise ValidationError("'scorer_fn' must be provided for local metrics.")

        self.scorer_fn = scorer_fn
        self.scorable_types = scorable_types or [StepType.llm]
        self.aggregatable_types = aggregatable_types or [StepType.trace]
        self.scorer_type = None  # Local metrics don't have a scorer_type

    def to_local_metric_config(self) -> LocalMetricConfig:
        """
        Convert to LocalMetricConfig format.

        Returns
        -------
            LocalMetricConfig: Local metric configuration for use with the logger.

        Examples
        --------
            def my_scorer(trace):
                return 0.5

            metric = LocalEvaluator(name="test", scorer_fn=my_scorer)
            config = metric.to_local_metric_config()
        """
        return LocalMetricConfig(
            name=self.name,
            scorer_fn=self.scorer_fn,
            scorable_types=self.scorable_types,
            aggregatable_types=self.aggregatable_types,
        )

    def __repr__(self) -> str:
        """Detailed string representation of the metric."""
        # Handle callables that don't have __name__ (partials, lambdas, callable instances)
        fn_name = getattr(self.scorer_fn, "__name__", f"<{type(self.scorer_fn).__name__}>")
        return f"LocalEvaluator(name='{self.name}', scorer_fn={fn_name})"
