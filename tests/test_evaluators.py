import datetime
import re
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from galileo_core.schemas.logging.step import StepType
from splunk_ao.decorator import _project_context
from splunk_ao.evaluators import (
    DecisionVersionOutcomeUnknownError,
    Evaluators,
    _resolve_create_scope,
    create_custom_llm_evaluator,
    create_decision_evaluator,
    delete_evaluator,
    get_evaluators,
)
from splunk_ao.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SplunkAOAPIError,
)
from splunk_ao.resources.models import (
    BucketedMetrics,
    HTTPValidationError,
    LogRecordsMetricsResponse,
    LogRecordsMetricsResponseAggregateMetrics,
    LogRecordsMetricsResponseBucketedMetrics,
    ValidationError,
)
from splunk_ao.resources.models.base_scorer_version_response import BaseScorerVersionResponse
from splunk_ao.resources.models.create_decision_scorer_version_request import CreateDecisionScorerVersionRequest
from splunk_ao.resources.models.create_llm_scorer_version_request import CreateLLMScorerVersionRequest
from splunk_ao.resources.models.create_scorer_request import CreateScorerRequest
from splunk_ao.resources.models.decision_level import DecisionLevel
from splunk_ao.resources.models.input_type_enum import InputTypeEnum
from splunk_ao.resources.models.output_type_enum import OutputTypeEnum
from splunk_ao.resources.models.scorer_defaults import ScorerDefaults
from splunk_ao.resources.models.scorer_response import ScorerResponse
from splunk_ao.resources.models.scorer_types import ScorerTypes
from splunk_ao.resources.types import UNSET
from splunk_ao.shared.exceptions import ValidationError as SplunkAOValidationError

FIXED_PROJECT_ID = str(uuid4())


pytestmark = pytest.mark.usefixtures("no_current_project")


@pytest.fixture
def mock_projects():
    """Patch the project lookup used to resolve the current project; the found project has id ``project-id-1``."""
    with patch("splunk_ao.shared.project_resolver.Projects") as projects_class:
        project = MagicMock()
        project.id = "project-id-1"
        projects_class.return_value.get_with_env_fallbacks.return_value = project
        yield projects_class.return_value


@pytest.fixture
def mock_scorer_response():
    """Mock scorer response for testing."""
    return ScorerResponse(
        id=UUID("12345678-1234-5678-9012-123456789abc"),
        name="test_metric",
        scorer_type=ScorerTypes.LLM,
        description="Test metric description",
        tags=["test", "custom"],
        defaults=ScorerDefaults(model_name="gpt-4.1-mini", num_judges=3),
        created_at="2025-01-01T00:00:00Z",
        created_by=UUID("87654321-4321-8765-2109-987654321cba"),
        updated_at="2025-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_scorer_version_response():
    """Mock scorer version response for testing."""
    mock_response = MagicMock(spec=BaseScorerVersionResponse)
    mock_response.id = UUID("12345678-1234-5678-9012-123456789def")
    mock_response.version = 1
    mock_response.scorer_id = UUID("12345678-1234-5678-9012-123456789abc")
    mock_response.user_prompt = "Test prompt"
    mock_response.scoreable_node_types = [StepType.llm]
    mock_response.cot_enabled = True
    mock_response.model_name = "gpt-4.1-mini"
    mock_response.num_judges = 3
    return mock_response


def _log_records_metrics_response_factory() -> LogRecordsMetricsResponse:
    """Creates a realistic LogRecordsMetricsResponse for testing."""
    now = datetime.datetime.now()
    agg_metrics = LogRecordsMetricsResponseAggregateMetrics()
    agg_metrics["total_cost"] = 15.50
    agg_metrics["total_tokens"] = 2500

    bucketed_metrics_data = LogRecordsMetricsResponseBucketedMetrics()
    bucketed_metrics_data["total_cost"] = [
        BucketedMetrics(start_bucket_time=now, end_bucket_time=now + datetime.timedelta(minutes=5)),
        BucketedMetrics(
            start_bucket_time=now + datetime.timedelta(minutes=5), end_bucket_time=now + datetime.timedelta(minutes=10)
        ),
    ]

    return LogRecordsMetricsResponse(
        aggregate_metrics=agg_metrics, bucketed_metrics=bucketed_metrics_data, group_by_columns=[]
    )


class TestMetrics:
    """Test cases for the Evaluators class."""

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_create_custom_llm_metric_success(
        self, mock_create_scorer, mock_create_version, mock_scorer_response, mock_scorer_version_response
    ) -> None:
        """Test successful creation of a custom LLM metric."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        metrics = Evaluators()

        # Test with default parameters
        result = metrics.create_custom_llm_evaluator(name="test_metric", user_prompt="Rate the quality of this response")

        # Verify the result
        assert result == mock_scorer_version_response

        # Verify create_scorer was called with correct parameters
        mock_create_scorer.sync.assert_called_once()
        create_scorer_call = mock_create_scorer.sync.call_args
        scorer_request = create_scorer_call.kwargs["body"]

        assert isinstance(scorer_request, CreateScorerRequest)
        assert scorer_request.name == "test_metric"
        assert scorer_request.scorer_type == ScorerTypes.LLM
        assert scorer_request.description == ""
        assert scorer_request.tags == []
        assert scorer_request.defaults.model_name == "gpt-4.1-mini"
        assert scorer_request.defaults.num_judges == 3
        assert scorer_request.output_type == OutputTypeEnum.BOOLEAN
        assert scorer_request.defaults.cot_enabled is True
        assert scorer_request.scoreable_node_types == [StepType.llm]
        assert scorer_request.ground_truth is False

        # Verify create_version was called with correct parameters
        mock_create_version.sync.assert_called_once()
        create_version_call = mock_create_version.sync.call_args
        version_request = create_version_call.kwargs["body"]

        assert isinstance(version_request, CreateLLMScorerVersionRequest)
        assert version_request.user_prompt == "Rate the quality of this response"
        assert create_version_call.kwargs["scorer_id"] == mock_scorer_response.id

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_create_custom_llm_metric_with_custom_parameters(
        self, mock_create_scorer, mock_create_version, mock_scorer_response, mock_scorer_version_response
    ) -> None:
        """Test creation of a custom LLM metric with custom parameters."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        metrics = Evaluators()

        # Test with custom parameters
        result = metrics.create_custom_llm_evaluator(
            name="custom_metric",
            user_prompt="Custom prompt for evaluation",
            node_level=StepType.workflow,
            cot_enabled=False,
            model_name="GPT-3.5-turbo",
            num_judges=5,
            description="Custom metric description",
            tags=["custom", "evaluation", "quality"],
            output_type=OutputTypeEnum.CATEGORICAL,
            ground_truth=True,
        )

        # Verify the result
        assert result == mock_scorer_version_response

        # Verify create_scorer was called with correct parameters
        scorer_request = mock_create_scorer.sync.call_args.kwargs["body"]
        assert scorer_request.name == "custom_metric"
        assert scorer_request.description == "Custom metric description"
        assert scorer_request.tags == ["custom", "evaluation", "quality"]
        assert scorer_request.defaults.model_name == "GPT-3.5-turbo"
        assert scorer_request.defaults.num_judges == 5
        assert scorer_request.output_type == OutputTypeEnum.CATEGORICAL
        assert scorer_request.defaults.cot_enabled is False
        assert scorer_request.scoreable_node_types == [StepType.workflow]
        assert scorer_request.ground_truth is True

        # Verify create_version was called with correct parameters
        version_request = mock_create_version.sync.call_args.kwargs["body"]
        assert version_request.user_prompt == "Custom prompt for evaluation"

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_create_custom_llm_metric_scorer_creation_failure(self, mock_create_scorer, mock_create_version) -> None:
        """Test handling of scorer creation failure."""
        # Setup mock to raise exception
        mock_create_scorer.sync.side_effect = Exception("Scorer creation failed")

        metrics = Evaluators()

        # Test that exception is propagated
        with pytest.raises(Exception, match="Scorer creation failed"):
            metrics.create_custom_llm_evaluator(name="test_metric", user_prompt="Test prompt")

        # Verify create_version was not called
        mock_create_version.sync.assert_not_called()

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_create_custom_llm_metric_version_creation_failure(
        self, mock_create_scorer, mock_create_version, mock_scorer_response
    ) -> None:
        """Test handling of version creation failure."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.side_effect = Exception("Version creation failed")

        metrics = Evaluators()

        # Test that exception is propagated
        with pytest.raises(Exception, match="Version creation failed"):
            metrics.create_custom_llm_evaluator(name="test_metric", user_prompt="Test prompt")

        # Verify create_scorer was called but create_version failed
        mock_create_scorer.sync.assert_called_once()
        mock_create_version.sync.assert_called_once()

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    @patch("splunk_ao.evaluators._logger")
    def test_create_custom_llm_metric_logging(
        self, mock_logger, mock_create_scorer, mock_create_version, mock_scorer_response, mock_scorer_version_response
    ) -> None:
        """Test that successful metric creation is logged."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        metrics = Evaluators()

        # Create metric
        metrics.create_custom_llm_evaluator(name="test_metric", user_prompt="Test prompt")

        # Verify logging was called
        mock_logger.info.assert_called_once_with("Created custom LLM metric: %s", "test_metric")

    @patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
    @patch("splunk_ao.scorers.Scorers.list")
    def test_delete_metric_success(self, mock_list_scorers, mock_delete_scorer, mock_scorer_response) -> None:
        """Test successful deletion of a metric."""
        mock_list_scorers.return_value = [mock_scorer_response]
        metrics = Evaluators()
        metrics.delete_evaluator(name="test_metric")

        mock_list_scorers.assert_called_once_with(name="test_metric")
        mock_delete_scorer.sync.assert_called_once_with(
            scorer_id=mock_scorer_response.id, client=metrics.config.api_client
        )

    @patch("splunk_ao.scorers.Scorers.list")
    def test_delete_metric_not_found(self, mock_list_scorers) -> None:
        """Test deleting a metric that does not exist."""
        mock_list_scorers.return_value = []
        metrics = Evaluators()

        with pytest.raises(ValueError, match="Scorer with name test_metric not found."):
            metrics.delete_evaluator(name="test_metric")

    @patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
    @patch("splunk_ao.scorers.Scorers.list")
    def test_delete_metric_api_failure(self, mock_list_scorers, mock_delete_scorer, mock_scorer_response) -> None:
        """Test API failure when deleting a metric."""
        mock_list_scorers.return_value = [mock_scorer_response]
        mock_delete_scorer.sync.return_value = None
        metrics = Evaluators()

        with pytest.raises(ValueError, match="Failed to delete metric."):
            metrics.delete_evaluator(name="test_metric")


class TestPublicFunctions:
    """Test cases for public functions."""

    @patch("splunk_ao.evaluators.Evaluators")
    def test_create_custom_llm_metric_function(self, mock_metrics_class) -> None:
        """Test the public create_custom_llm_evaluator function."""
        # Setup mock
        mock_metrics_instance = Mock()
        mock_metrics_class.return_value = mock_metrics_instance
        mock_result = Mock(spec=BaseScorerVersionResponse)
        mock_metrics_instance.create_custom_llm_evaluator.return_value = mock_result

        # Call the public function
        result = create_custom_llm_evaluator(
            name="test_metric",
            user_prompt="Test prompt",
            node_level=StepType.workflow,
            cot_enabled=False,
            model_name="GPT-3.5-turbo",
            num_judges=5,
            description="Test description",
            tags=["test"],
            output_type=OutputTypeEnum.CATEGORICAL,
            ground_truth=True,
        )

        # Verify Evaluators class was instantiated
        mock_metrics_class.assert_called_once()

        # Verify the method was called with correct parameters
        mock_metrics_instance.create_custom_llm_evaluator.assert_called_once_with(
            "test_metric",
            "Test prompt",
            StepType.workflow,
            False,
            "GPT-3.5-turbo",
            5,
            "Test description",
            ["test"],
            OutputTypeEnum.CATEGORICAL,
            True,
            project_ids=None,
            is_global=None,
        )

        # Verify the result is returned
        assert result == mock_result

    @patch("splunk_ao.evaluators.Evaluators")
    def test_create_custom_llm_metric_function_default_parameters(self, mock_metrics_class) -> None:
        """Test the public function with default parameters."""
        # Setup mock
        mock_metrics_instance = Mock()
        mock_metrics_class.return_value = mock_metrics_instance
        mock_result = Mock(spec=BaseScorerVersionResponse)
        mock_metrics_instance.create_custom_llm_evaluator.return_value = mock_result

        # Call the public function with minimal parameters
        result = create_custom_llm_evaluator(name="test_metric", user_prompt="Test prompt")

        # Verify the method was called with default parameters
        mock_metrics_instance.create_custom_llm_evaluator.assert_called_once_with(
            "test_metric",
            "Test prompt",
            StepType.llm,  # default
            True,  # default
            "gpt-4.1-mini",  # default
            3,  # default
            "",  # default
            [],  # default
            OutputTypeEnum.BOOLEAN,  # default
            False,  # default ground_truth
            project_ids=None,
            is_global=None,
        )

        # Verify the result is returned
        assert result == mock_result

    @patch("splunk_ao.evaluators.Evaluators")
    def test_delete_metric_function(self, mock_metrics_class) -> None:
        """Test the public delete_evaluator function."""
        mock_metrics_instance = Mock()
        mock_metrics_class.return_value = mock_metrics_instance

        delete_evaluator(name="test_metric")
        mock_metrics_class.assert_called_once()
        mock_metrics_instance.delete_evaluator.assert_called_once_with("test_metric")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_empty_string_parameters(
        self, mock_create_scorer, mock_create_version, mock_scorer_response, mock_scorer_version_response
    ) -> None:
        """Test creation with empty string parameters."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        metrics = Evaluators()

        # Test with empty strings
        result = metrics.create_custom_llm_evaluator(
            name="",  # Empty name
            user_prompt="",  # Empty prompt
            description="",
            tags=[],
        )

        # Verify the result
        assert result == mock_scorer_version_response

        # Verify parameters were passed correctly
        scorer_request = mock_create_scorer.sync.call_args.kwargs["body"]
        assert scorer_request.name == ""
        assert scorer_request.description == ""

        version_request = mock_create_version.sync.call_args.kwargs["body"]
        assert version_request.user_prompt == ""

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_large_num_judges(
        self, mock_create_scorer, mock_create_version, mock_scorer_response, mock_scorer_version_response
    ) -> None:
        """Test creation with large number of judges."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        metrics = Evaluators()

        # Test with large number of judges
        result = metrics.create_custom_llm_evaluator(name="test_metric", user_prompt="Test prompt", num_judges=100)

        # Verify the result
        assert result == mock_scorer_version_response

        # Verify num_judges was set correctly
        scorer_request = mock_create_scorer.sync.call_args.kwargs["body"]
        assert scorer_request.defaults.num_judges == 100

        version_request = mock_create_version.sync.call_args.kwargs["body"]
        assert version_request.user_prompt == "Test prompt"

    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_long_tag_list(
        self, mock_create_scorer, mock_create_version, mock_scorer_response, mock_scorer_version_response
    ) -> None:
        """Test creation with a long list of tags."""
        # Setup mocks
        mock_create_scorer.sync.return_value = mock_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        metrics = Evaluators()

        # Test with many tags
        long_tag_list = [f"tag_{i}" for i in range(50)]
        result = metrics.create_custom_llm_evaluator(name="test_metric", user_prompt="Test prompt", tags=long_tag_list)

        # Verify the result
        assert result == mock_scorer_version_response

        # Verify tags were set correctly
        scorer_request = mock_create_scorer.sync.call_args.kwargs["body"]
        assert scorer_request.tags == long_tag_list
        assert len(scorer_request.tags) == 50


class TestGetMetrics:
    @patch("splunk_ao.evaluators.query_metrics_projects_project_id_metrics_search_post.sync")
    def test_successful_call(self, mock_api_call):
        mock_response = _log_records_metrics_response_factory()
        mock_api_call.return_value = mock_response

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)

        response = get_evaluators(project_id=FIXED_PROJECT_ID, start_time=start_time, end_time=end_time)

        mock_api_call.assert_called_once()
        assert FIXED_PROJECT_ID in mock_api_call.call_args[1]["project_id"]
        assert response == mock_response

    @patch("splunk_ao.evaluators.query_metrics_projects_project_id_metrics_search_post.sync")
    def test_api_failure_raises_value_error(self, mock_api_call):
        mock_api_call.return_value = None

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)

        with pytest.raises(ValueError, match="Failed to query for metrics."):
            get_evaluators(project_id=FIXED_PROJECT_ID, start_time=start_time, end_time=end_time)

        mock_api_call.assert_called_once()

    @patch("splunk_ao.evaluators.query_metrics_projects_project_id_metrics_search_post.sync")
    def test_http_validation_error_raises_exception(self, mock_api_call):
        detail = [ValidationError(loc=["body", "project_id"], msg="value is not a valid uuid", type_="type_error.uuid")]
        mock_api_call.return_value = HTTPValidationError(detail=detail)

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)

        with pytest.raises(ValueError, match=re.escape(str(detail))):
            get_evaluators(project_id=FIXED_PROJECT_ID, start_time=start_time, end_time=end_time)

    @patch("splunk_ao.evaluators.query_metrics_projects_project_id_metrics_search_post.sync")
    def test_passes_all_parameters_correctly(self, mock_api_call):
        mock_api_call.return_value = _log_records_metrics_response_factory()

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)
        experiment_id = str(uuid4())
        agent_stream_id = "test_stream"
        filters = [Mock()]
        group_by = "some_column"
        interval = 10

        get_evaluators(
            project_id=FIXED_PROJECT_ID,
            start_time=start_time,
            end_time=end_time,
            experiment_id=experiment_id,
            agent_stream_id=agent_stream_id,
            filters=filters,
            group_by=group_by,
            interval=interval,
        )

        mock_api_call.assert_called_once()
        called_kwargs = mock_api_call.call_args[1]
        body = called_kwargs["body"]

        assert called_kwargs["project_id"] == FIXED_PROJECT_ID
        assert body.start_time == start_time
        assert body.end_time == end_time
        assert body.experiment_id == experiment_id
        assert body.log_stream_id == agent_stream_id
        assert body.filters == filters
        assert body.group_by == group_by
        assert body.interval == interval


class TestResolveCreateScope:
    """Scope resolution for evaluator creation."""

    def test_project_id_env_defaults_to_that_project(self, monkeypatch, mock_projects) -> None:
        # Given only SPLUNK_AO_PROJECT_ID is set
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")

        # When resolving with no explicit scope
        result = _resolve_create_scope(None, None)

        # Then it is scoped to the project looked up by id
        assert result == (False, ["project-id-1"])
        mock_projects.get_with_env_fallbacks.assert_called_once_with(id="env-id", name=None)

    def test_project_name_env_is_resolved_to_id(self, monkeypatch, mock_projects) -> None:
        # Given only SPLUNK_AO_PROJECT is set
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "my-project")

        # When resolving with no explicit scope
        result = _resolve_create_scope(None, None)

        # Then the name is looked up and its id is used
        assert result == (False, ["project-id-1"])
        mock_projects.get_with_env_fallbacks.assert_called_once_with(id=None, name="my-project")

    def test_context_project_wins_over_env(self, monkeypatch, mock_projects) -> None:
        # Given a context project and both env vars
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "env-name")
        _project_context.set("context-project")

        # When resolving with no explicit scope
        result = _resolve_create_scope(None, None)

        # Then the context project name is the one looked up
        assert result == (False, ["project-id-1"])
        mock_projects.get_with_env_fallbacks.assert_called_once_with(id=None, name="context-project")

    def test_project_id_env_wins_over_project_name_env(self, monkeypatch, mock_projects) -> None:
        # Given both env vars
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "env-name")

        # When resolving with no explicit scope
        _resolve_create_scope(None, None)

        # Then the id is the one looked up
        mock_projects.get_with_env_fallbacks.assert_called_once_with(id="env-id", name=None)

    def test_explicit_project_ids_override_context_and_env(self, monkeypatch, mock_projects) -> None:
        # Given a context project and env vars
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        _project_context.set("context-project")

        # When explicit project ids are passed, with a duplicate
        result = _resolve_create_scope(["a", "b", "a"], None)

        # Then they are used as-is (deduplicated, order kept) and no lookup happens
        assert result == (False, ["a", "b"])
        mock_projects.get_with_env_fallbacks.assert_not_called()

    def test_explicit_project_ids_with_is_global_false(self, mock_projects) -> None:
        # Given explicit ids and is_global=False
        # When resolving
        result = _resolve_create_scope(["a"], False)

        # Then the ids are used
        assert result == (False, ["a"])

    def test_empty_project_ids_with_is_global_true_is_global(self, mock_projects) -> None:
        # Given is_global=True and an empty list, which does not conflict
        # When resolving
        result = _resolve_create_scope([], True)

        # Then the evaluator is global
        assert result == (True, UNSET)

    def test_is_global_true_sends_no_project_ids_even_with_current_project(self, monkeypatch, mock_projects) -> None:
        # Given a current project
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")

        # When is_global=True is passed
        result = _resolve_create_scope(None, True)

        # Then the evaluator is global and no lookup happens
        assert result == (True, UNSET)
        mock_projects.get_with_env_fallbacks.assert_not_called()

    def test_nothing_set_sends_no_scope(self, mock_projects) -> None:
        # Given no arguments, context project or env vars
        # When resolving
        result = _resolve_create_scope(None, None)

        # Then no scope is sent and no lookup happens
        assert result == (UNSET, UNSET)
        mock_projects.get_with_env_fallbacks.assert_not_called()

    def test_whitespace_context_project_counts_as_unset(self, mock_projects) -> None:
        # Given a whitespace-only context project and nothing else
        _project_context.set("   ")

        # When resolving
        result = _resolve_create_scope(None, None)

        # Then it is treated as no current project
        assert result == (UNSET, UNSET)

    def test_whitespace_env_counts_as_unset(self, monkeypatch, mock_projects) -> None:
        # Given a whitespace-only SPLUNK_AO_PROJECT
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "   ")

        # When resolving
        result = _resolve_create_scope(None, None)

        # Then it is treated as no current project
        assert result == (UNSET, UNSET)

    def test_global_and_project_ids_conflict(self, mock_projects) -> None:
        # Given is_global=True together with project ids
        # Then resolving fails
        with pytest.raises(SplunkAOValidationError, match="both global and scoped"):
            _resolve_create_scope(["a"], True)

    def test_empty_project_ids_rejected(self, monkeypatch, mock_projects) -> None:
        # Given a current project, which must not paper over an explicit empty list
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")

        with pytest.raises(SplunkAOValidationError, match="must not be empty"):
            _resolve_create_scope([], None)

    def test_string_project_ids_rejected(self, mock_projects) -> None:
        with pytest.raises(SplunkAOValidationError, match="not a single string"):
            _resolve_create_scope("3f2a", None)  # type: ignore[arg-type]

    def test_is_global_false_without_any_project_rejected(self, mock_projects) -> None:
        # Given is_global=False and no project anywhere
        # Then resolving fails
        with pytest.raises(SplunkAOValidationError, match="is_global=False needs project_ids"):
            _resolve_create_scope(None, False)

    def test_is_global_false_uses_current_project(self, monkeypatch, mock_projects) -> None:
        # Given a current project
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")

        # When is_global=False is passed with no ids
        result = _resolve_create_scope(None, False)

        # Then the current project is used
        assert result == (False, ["project-id-1"])

    def test_current_project_not_found_raises_not_found(self, monkeypatch, mock_projects) -> None:
        # Given a current project that does not exist
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "missing")
        mock_projects.get_with_env_fallbacks.return_value = None

        # Then there is no silent fallback to global, and the error says why a project was looked up
        with pytest.raises(NotFoundError, match="missing") as exc_info:
            _resolve_create_scope(None, None)
        assert "defaults to the current project" in str(exc_info.value)
        assert "is_global=True" in str(exc_info.value)


class TestCreateCustomLlmEvaluatorScope:
    """The scope reaches the CreateScorerRequest on both public create paths."""

    @staticmethod
    def _create(use_function: bool, **kwargs):
        if use_function:
            return create_custom_llm_evaluator("m", "prompt", **kwargs)
        return Evaluators().create_custom_llm_evaluator(name="m", user_prompt="prompt", **kwargs)

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_defaults_to_current_project(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects, mock_scorer_response
    ) -> None:
        # Given a current project from the environment
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        mock_create_scorer.sync.return_value = mock_scorer_response

        # When creating with no explicit scope
        self._create(use_function)

        # Then the request is scoped to that project
        body = mock_create_scorer.sync.call_args.kwargs["body"]
        assert body.is_global is False
        assert body.project_ids == ["project-id-1"]

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_explicit_project_ids_override_current_project(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects, mock_scorer_response
    ) -> None:
        # Given a current project from the environment
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        mock_create_scorer.sync.return_value = mock_scorer_response

        # When creating with explicit project ids
        self._create(use_function, project_ids=["a", "b"])

        # Then the explicit ids are sent
        body = mock_create_scorer.sync.call_args.kwargs["body"]
        assert body.is_global is False
        assert body.project_ids == ["a", "b"]

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_explicit_global_overrides_current_project(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects, mock_scorer_response
    ) -> None:
        # Given a current project from the environment
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        mock_create_scorer.sync.return_value = mock_scorer_response

        # When creating with is_global=True
        self._create(use_function, is_global=True)

        # Then the request is global with no project ids
        body = mock_create_scorer.sync.call_args.kwargs["body"]
        assert body.is_global is True
        assert "project_ids" not in body.to_dict()

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_no_current_project_sends_no_scope(
        self, mock_create_scorer, mock_create_version, use_function, mock_projects, mock_scorer_response
    ) -> None:
        # Given no current project
        mock_create_scorer.sync.return_value = mock_scorer_response

        # When creating with no scope
        self._create(use_function)

        # Then no scope fields are sent
        body_dict = mock_create_scorer.sync.call_args.kwargs["body"].to_dict()
        assert "is_global" not in body_dict
        assert "project_ids" not in body_dict

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @pytest.mark.parametrize(
        "kwargs", [{"is_global": True, "project_ids": ["a"]}, {"project_ids": []}, {"is_global": False}]
    )
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_invalid_scope_fails_before_any_http_call(
        self, mock_create_scorer, kwargs, use_function, mock_projects
    ) -> None:
        # Given an invalid scope
        # When creating
        with pytest.raises(SplunkAOValidationError):
            self._create(use_function, **kwargs)

        # Then nothing is sent
        mock_create_scorer.sync.assert_not_called()

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @patch("splunk_ao.evaluators.create_scorers_post")
    def test_current_project_not_found_sends_no_create_request(
        self, mock_create_scorer, use_function, monkeypatch, mock_projects
    ) -> None:
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "missing")
        mock_projects.get_with_env_fallbacks.return_value = None

        with pytest.raises(NotFoundError):
            self._create(use_function)

        mock_create_scorer.sync.assert_not_called()

    @patch("splunk_ao.evaluators.Evaluators")
    def test_module_function_keeps_positional_order_and_forwards_scope_by_keyword(self, mock_evaluators_class) -> None:
        create_custom_llm_evaluator(
            "m", "prompt", StepType.llm, True, "gpt-4o", 5, "desc", ["t"], OutputTypeEnum.PERCENTAGE, True, ["a"], False
        )

        mock_evaluators_class.return_value.create_custom_llm_evaluator.assert_called_once_with(
            "m", "prompt", StepType.llm, True, "gpt-4o", 5, "desc", ["t"], OutputTypeEnum.PERCENTAGE, True,
            project_ids=["a"], is_global=False,
        )  # fmt: skip


@pytest.fixture
def decision_scorer_response():
    return ScorerResponse(
        id=UUID("12345678-1234-5678-9012-123456789abc"),
        name="tone",
        scorer_type=ScorerTypes.DECISION,
        tags=[],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )


@patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
@patch("splunk_ao.evaluators.create_decision_scorer_version_scorers_scorer_id_version_decision_post")
@patch("splunk_ao.evaluators.create_scorers_post")
class TestCreateDecisionEvaluator:
    def test_boolean_probability_defaults(
        self,
        mock_create_scorer,
        mock_create_version,
        mock_delete,
        decision_scorer_response,
        mock_scorer_version_response,
    ) -> None:
        # Given: both endpoints succeed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        # When: creating a decision evaluator with only the required arguments
        result = create_decision_evaluator(name="tone", question="Is the tone professional?")

        # Then: the scorer and version requests carry the defaults and the version response is returned
        assert result is mock_scorer_version_response
        scorer_request = mock_create_scorer.sync.call_args.kwargs["body"]
        assert isinstance(scorer_request, CreateScorerRequest)
        assert scorer_request.name == "tone"
        assert scorer_request.scorer_type == ScorerTypes.DECISION
        assert scorer_request.output_type == OutputTypeEnum.BOOLEAN_PROBABILITY
        assert scorer_request.scoreable_node_types == [StepType.llm]
        assert scorer_request.ground_truth is False
        assert "input_type" not in scorer_request.to_dict()
        assert "defaults" not in scorer_request.to_dict()

        version_call = mock_create_version.sync.call_args
        version_request = version_call.kwargs["body"]
        assert isinstance(version_request, CreateDecisionScorerVersionRequest)
        assert version_request.model_name == "jev-1.13.0"
        assert version_request.question == "Is the tone professional?"
        assert version_request.answer_options is None
        assert version_call.kwargs["scorer_id"] == decision_scorer_response.id
        mock_delete.sync.assert_not_called()

    def test_categorical_with_options_and_node_level(
        self,
        mock_create_scorer,
        mock_create_version,
        mock_delete,
        decision_scorer_response,
        mock_scorer_version_response,
    ) -> None:
        # Given: both endpoints succeed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        # When: creating a categorical evaluator on trace nodes with every optional argument set
        create_decision_evaluator(
            name="tone",
            question="Which tone?",
            node_level=StepType.trace,
            output_type=OutputTypeEnum.CATEGORICAL,
            answer_options=["a", "b"],
            input_type=InputTypeEnum.TRACE_IO_ONLY,
            description="d",
            tags=["t"],
            ground_truth=True,
        )

        # Then: the node level is a single-element list and the labels are sent as strings
        scorer_request = mock_create_scorer.sync.call_args.kwargs["body"]
        assert scorer_request.scoreable_node_types == [StepType.trace]
        assert scorer_request.output_type == OutputTypeEnum.CATEGORICAL
        assert scorer_request.input_type == InputTypeEnum.TRACE_IO_ONLY
        assert scorer_request.description == "d"
        assert scorer_request.tags == ["t"]
        assert scorer_request.ground_truth is True
        version_request = mock_create_version.sync.call_args.kwargs["body"]
        assert version_request.to_dict()["answer_options"] == ["a", "b"]

    def test_discrete_accepts_levels_and_dicts(
        self,
        mock_create_scorer,
        mock_create_version,
        mock_delete,
        decision_scorer_response,
        mock_scorer_version_response,
    ) -> None:
        # Given: both endpoints succeed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        # When: creating a discrete evaluator from a DecisionLevel and a plain dict
        create_decision_evaluator(
            name="quality",
            question="How good?",
            output_type=OutputTypeEnum.DISCRETE,
            answer_options=[DecisionLevel(level=0, label="bad"), {"level": 1, "label": "good", "description": "ok"}],
        )

        # Then: the request body holds JSON-ready level dicts
        version_request = mock_create_version.sync.call_args.kwargs["body"]
        assert version_request.to_dict()["answer_options"] == [
            {"level": 0, "label": "bad"},
            {"level": 1, "label": "good", "description": "ok"},
        ]

    @pytest.mark.parametrize(
        ("answer_options", "message"),
        [
            ("yes", "single string"),
            ({"level": 0, "label": "x"}, "single string or dict"),
            ([], "must not be empty"),
            ([{"label": "bad"}, {"label": "good"}], r"answer_options\[0\] is missing required key\(s\): level"),
            ([1, 2], "got int"),
        ],
    )
    def test_invalid_answer_options_raise_before_any_request(
        self, mock_create_scorer, mock_create_version, mock_delete, answer_options, message
    ) -> None:
        # When/Then: malformed answer options raise ValueError and no request is sent
        with pytest.raises(ValueError, match=message):
            create_decision_evaluator(
                name="q", question="q", output_type=OutputTypeEnum.DISCRETE, answer_options=answer_options
            )
        mock_create_scorer.sync.assert_not_called()

    @pytest.mark.parametrize(
        "version_result",
        [
            HTTPValidationError(detail="unknown model jev-9"),
            None,
            BadRequestError(400, b"bad"),
            ForbiddenError(403, b"no"),
            NotFoundError(404, b"gone"),
            SplunkAOAPIError(422, b"unprocessable", "Unprocessable"),
        ],
    )
    def test_rejected_version_deletes_scorer(
        self, mock_create_scorer, mock_create_version, mock_delete, decision_scorer_response, version_result
    ) -> None:
        # Given: the scorer is created and the version request is clearly rejected
        mock_create_scorer.sync.return_value = decision_scorer_response
        if isinstance(version_result, Exception):
            mock_create_version.sync.side_effect = version_result
        else:
            mock_create_version.sync.return_value = version_result

        # When/Then: the error surfaces and the scorer is deleted
        with pytest.raises((ValueError, SplunkAOAPIError)):
            create_decision_evaluator(name="tone", question="q", model_name="jev-9")
        mock_delete.sync.assert_called_once()
        assert mock_delete.sync.call_args.kwargs["scorer_id"] == decision_scorer_response.id

    def test_http_validation_error_detail_is_in_the_message(
        self, mock_create_scorer, mock_create_version, mock_delete, decision_scorer_response
    ) -> None:
        # Given: the version request fails validation
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = HTTPValidationError(detail="unknown model jev-9")

        # When/Then: the API detail reaches the caller
        with pytest.raises(ValueError, match="unknown model jev-9"):
            create_decision_evaluator(name="tone", question="q", model_name="jev-9")

    @pytest.mark.parametrize(
        "error",
        [
            ServerError(502, b"bad gateway"),
            RateLimitError(429, b"slow"),
            ConflictError(409, b"conflict"),
            TimeoutError("timed out"),
        ],
    )
    def test_unknown_outcome_keeps_scorer(
        self, mock_create_scorer, mock_create_version, mock_delete, decision_scorer_response, error
    ) -> None:
        # Given: the version request fails in a way that may have saved the version
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.side_effect = error

        # When/Then: the error names the kept scorer, chains the cause, and the scorer is not deleted
        with pytest.raises(DecisionVersionOutcomeUnknownError, match=str(decision_scorer_response.id)) as raised:
            create_decision_evaluator(name="tone", question="q")
        assert raised.value.__cause__ is error
        assert raised.value.scorer_id == str(decision_scorer_response.id)
        mock_delete.sync.assert_not_called()

    @pytest.mark.parametrize(
        "delete_behavior",
        [
            {"side_effect": RuntimeError("delete failed")},
            {"return_value": None},
            {"return_value": HTTPValidationError(detail="no")},
        ],
    )
    def test_failed_cleanup_does_not_mask_original_error(
        self, mock_create_scorer, mock_create_version, mock_delete, decision_scorer_response, delete_behavior
    ) -> None:
        # Given: the version is rejected and the cleanup delete fails or is not confirmed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = HTTPValidationError(detail="bad options")
        mock_delete.sync.configure_mock(**delete_behavior)

        # When/Then: the original error still surfaces
        with pytest.raises(ValueError, match="bad options"):
            create_decision_evaluator(name="tone", question="q")

    @pytest.mark.parametrize("scorer_result", [HTTPValidationError(detail="name taken"), None])
    def test_scorer_failure_raises_without_version_call(
        self, mock_create_scorer, mock_create_version, mock_delete, scorer_result
    ) -> None:
        # Given: the scorer request fails
        mock_create_scorer.sync.return_value = scorer_result

        # When/Then: ValueError is raised and neither the version nor the delete endpoint is called
        with pytest.raises(ValueError):
            create_decision_evaluator(name="tone", question="q")
        mock_create_version.sync.assert_not_called()
        mock_delete.sync.assert_not_called()


@patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
@patch("splunk_ao.evaluators.create_decision_scorer_version_scorers_scorer_id_version_decision_post")
@patch("splunk_ao.evaluators.create_scorers_post")
class TestCreateDecisionEvaluatorGuards:
    @pytest.mark.parametrize(
        ("output_type", "answer_options"),
        [
            (OutputTypeEnum.PERCENTAGE, None),
            (OutputTypeEnum.BOOLEAN_PROBABILITY, ["a", "b"]),
            (OutputTypeEnum.CATEGORICAL, None),
            (OutputTypeEnum.CATEGORICAL, [{"level": 0, "label": "x"}, {"level": 1, "label": "y"}]),
            (OutputTypeEnum.DISCRETE, ["a", "b"]),
            (OutputTypeEnum.DISCRETE, None),
        ],
    )
    def test_mismatched_output_type_and_options_create_nothing(
        self, mock_create_scorer, mock_create_version, mock_delete, output_type, answer_options
    ) -> None:
        # When/Then: a request the server would refuse raises before the scorer is created
        with pytest.raises(ValueError):
            create_decision_evaluator(name="q", question="q", output_type=output_type, answer_options=answer_options)
        mock_create_scorer.sync.assert_not_called()

    def test_unparseable_success_response_keeps_scorer(
        self, mock_create_scorer, mock_create_version, mock_delete, decision_scorer_response
    ) -> None:
        # Given: the server saved the version but the 200 body cannot be parsed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")

        # When/Then: the error surfaces and the scorer is kept, since the version may exist
        with pytest.raises(DecisionVersionOutcomeUnknownError, match="Expecting value"):
            create_decision_evaluator(name="tone", question="q")
        mock_delete.sync.assert_not_called()

    @pytest.mark.parametrize(
        ("answer_options", "expected"),
        [
            (None, OutputTypeEnum.BOOLEAN_PROBABILITY),
            (["a", "b"], OutputTypeEnum.CATEGORICAL),
            ([{"level": 0, "label": "x"}, {"level": 1, "label": "y"}], OutputTypeEnum.DISCRETE),
            ([DecisionLevel(level=0, label="x"), DecisionLevel(level=1, label="y")], OutputTypeEnum.DISCRETE),
        ],
    )
    def test_output_type_is_inferred_from_answer_options(
        self,
        mock_create_scorer,
        mock_create_version,
        mock_delete,
        decision_scorer_response,
        mock_scorer_version_response,
        answer_options,
        expected,
    ) -> None:
        # Given: both endpoints succeed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        # When: creating without an output_type
        create_decision_evaluator(name="q", question="q", answer_options=answer_options)

        # Then: the scorer is created with the output type that matches the options
        assert mock_create_scorer.sync.call_args.kwargs["body"].output_type == expected

    def test_explicit_output_type_that_matches_options_is_kept(
        self,
        mock_create_scorer,
        mock_create_version,
        mock_delete,
        decision_scorer_response,
        mock_scorer_version_response,
    ) -> None:
        # Given: both endpoints succeed
        mock_create_scorer.sync.return_value = decision_scorer_response
        mock_create_version.sync.return_value = mock_scorer_version_response

        # When: output_type is given as a string that matches the options
        create_decision_evaluator(name="q", question="q", output_type="categorical", answer_options=["a", "b"])

        # Then: it is sent as the enum value
        assert mock_create_scorer.sync.call_args.kwargs["body"].output_type == OutputTypeEnum.CATEGORICAL

    def test_unknown_output_type_string_raises(self, mock_create_scorer, mock_create_version, mock_delete) -> None:
        # When/Then: an unknown output type raises before any request
        with pytest.raises(ValueError, match="output_type"):
            create_decision_evaluator(name="q", question="q", output_type="categorial", answer_options=["a", "b"])
        mock_create_scorer.sync.assert_not_called()

    @pytest.mark.parametrize(
        ("question", "answer_options"),
        [
            ("", None),
            ("x" * 2001, None),
            ("q", ["only"]),
            ("q", ["a", "a"]),
            ("q", [f"l{i}" for i in range(256)]),
            ("q", [{"level": 1, "label": "x"}, {"level": 2, "label": "y"}]),
            ("q", [{"level": 0, "label": "x"}, {"level": 0, "label": "y"}]),
            ("q", [{"level": i, "label": str(i)} for i in range(11)]),
        ],
    )
    def test_server_limits_are_checked_before_any_request(
        self, mock_create_scorer, mock_create_version, mock_delete, question, answer_options
    ) -> None:
        # When/Then: inputs the server would reject with 422 raise before the scorer is created
        with pytest.raises(ValueError):
            create_decision_evaluator(name="q", question=question, answer_options=answer_options)
        mock_create_scorer.sync.assert_not_called()


@patch("splunk_ao.evaluators.create_decision_scorer_version_scorers_scorer_id_version_decision_post")
@patch("splunk_ao.evaluators.create_scorers_post")
class TestCreateDecisionEvaluatorScope:
    """The scope reaches the CreateScorerRequest on both decision create paths."""

    @staticmethod
    def _create(use_function: bool, **kwargs):
        if use_function:
            return create_decision_evaluator("tone", "Is the tone professional?", **kwargs)
        return Evaluators().create_decision_evaluator(name="tone", question="Is the tone professional?", **kwargs)

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    def test_defaults_to_current_project(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects, decision_scorer_response
    ) -> None:
        # Given a current project from the environment
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        mock_create_scorer.sync.return_value = decision_scorer_response

        # When creating with no explicit scope
        self._create(use_function)

        # Then the request is scoped to that project
        body = mock_create_scorer.sync.call_args.kwargs["body"]
        assert body.is_global is False
        assert body.project_ids == ["project-id-1"]

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    def test_explicit_project_ids_override_current_project(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects, decision_scorer_response
    ) -> None:
        # Given a current project and explicit ids with a duplicate
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        mock_create_scorer.sync.return_value = decision_scorer_response

        # When creating
        self._create(use_function, project_ids=["a", "b", "a"])

        # Then the explicit ids win, deduplicated
        body = mock_create_scorer.sync.call_args.kwargs["body"]
        assert body.is_global is False
        assert body.project_ids == ["a", "b"]

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    def test_explicit_global_overrides_current_project(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects, decision_scorer_response
    ) -> None:
        # Given a current project
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "env-id")
        mock_create_scorer.sync.return_value = decision_scorer_response

        # When is_global=True is passed
        self._create(use_function, is_global=True)

        # Then the request is global with no project_ids
        body = mock_create_scorer.sync.call_args.kwargs["body"]
        assert body.is_global is True
        assert "project_ids" not in body.to_dict()

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    def test_no_current_project_sends_no_scope(
        self, mock_create_scorer, mock_create_version, use_function, mock_projects, decision_scorer_response
    ) -> None:
        mock_create_scorer.sync.return_value = decision_scorer_response

        self._create(use_function)

        body_dict = mock_create_scorer.sync.call_args.kwargs["body"].to_dict()
        assert "is_global" not in body_dict
        assert "project_ids" not in body_dict

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @pytest.mark.parametrize(
        "kwargs", [{"is_global": True, "project_ids": ["a"]}, {"project_ids": []}, {"is_global": False}]
    )
    def test_invalid_scope_fails_before_any_http_call(
        self, mock_create_scorer, mock_create_version, kwargs, use_function, mock_projects
    ) -> None:
        with pytest.raises(SplunkAOValidationError):
            self._create(use_function, **kwargs)

        mock_create_scorer.sync.assert_not_called()
        mock_create_version.sync.assert_not_called()

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    def test_current_project_not_found_sends_no_create_request(
        self, mock_create_scorer, mock_create_version, use_function, monkeypatch, mock_projects
    ) -> None:
        monkeypatch.setenv("SPLUNK_AO_PROJECT", "missing")
        mock_projects.get_with_env_fallbacks.return_value = None

        with pytest.raises(NotFoundError):
            self._create(use_function)

        mock_create_scorer.sync.assert_not_called()
