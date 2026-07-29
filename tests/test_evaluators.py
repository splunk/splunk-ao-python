import datetime
import re
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from galileo_core.schemas.logging.step import StepType
from splunk_ao.evaluators import Evaluators, create_custom_llm_evaluator, delete_evaluator, get_evaluators
from splunk_ao.resources.models import (
    BucketedMetrics,
    HTTPValidationError,
    LogRecordsMetricsResponse,
    LogRecordsMetricsResponseAggregateMetrics,
    LogRecordsMetricsResponseBucketedMetrics,
    ValidationError,
)
from splunk_ao.resources.models.base_scorer_version_response import BaseScorerVersionResponse
from splunk_ao.resources.models.create_llm_scorer_version_request import CreateLLMScorerVersionRequest
from splunk_ao.resources.models.create_scorer_request import CreateScorerRequest
from splunk_ao.resources.models.output_type_enum import OutputTypeEnum
from splunk_ao.resources.models.scorer_defaults import ScorerDefaults
from splunk_ao.resources.models.scorer_response import ScorerResponse
from splunk_ao.resources.models.scorer_types import ScorerTypes

FIXED_PROJECT_ID = str(uuid4())


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
