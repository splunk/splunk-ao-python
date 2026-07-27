"""Tests that all migrated symbols remain importable from splunk_ao.__future__ and resolve to the same objects."""


def test_project_is_same_class():
    from splunk_ao.__future__ import Project as FutureProject
    from splunk_ao.project import Project as RootProject

    assert FutureProject is RootProject


def test_collaborator_is_same_class():
    from splunk_ao.__future__ import Collaborator as FutureCollaborator
    from splunk_ao.collaborator import Collaborator as RootCollaborator

    assert FutureCollaborator is RootCollaborator


def test_collaborator_role_is_same_class():
    from splunk_ao.__future__ import CollaboratorRole as FutureRole
    from splunk_ao.collaborator import CollaboratorRole as RootRole

    assert FutureRole is RootRole


def test_sync_state_is_same_class():
    from splunk_ao.__future__.shared.base import SyncState as FutureSyncState
    from splunk_ao.shared.base import SyncState as RootSyncState

    assert FutureSyncState is RootSyncState


def test_state_management_mixin_is_same_class():
    from splunk_ao.__future__.shared.base import StateManagementMixin as FutureMixin
    from splunk_ao.shared.base import StateManagementMixin as RootMixin

    assert FutureMixin is RootMixin


def test_exceptions_are_same_classes():
    from splunk_ao.__future__.shared.exceptions import APIError as FutureAPIError
    from splunk_ao.__future__.shared.exceptions import ConfigurationError as FutureConfigError
    from splunk_ao.__future__.shared.exceptions import IntegrationNotConfiguredError as FutureIntError
    from splunk_ao.__future__.shared.exceptions import ResourceConflictError as FutureConflictError
    from splunk_ao.__future__.shared.exceptions import ResourceNotFoundError as FutureNotFoundError
    from splunk_ao.__future__.shared.exceptions import SplunkAOFutureError as FutureBaseError
    from splunk_ao.__future__.shared.exceptions import SyncError as FutureSyncError
    from splunk_ao.__future__.shared.exceptions import ValidationError as FutureValidationError
    from splunk_ao.shared.exceptions import (
        APIError,
        ConfigurationError,
        IntegrationNotConfiguredError,
        ResourceConflictError,
        ResourceNotFoundError,
        SplunkAOFutureError,
        SyncError,
        ValidationError,
    )

    assert FutureAPIError is APIError
    assert FutureConfigError is ConfigurationError
    assert FutureBaseError is SplunkAOFutureError
    assert FutureIntError is IntegrationNotConfiguredError
    assert FutureConflictError is ResourceConflictError
    assert FutureNotFoundError is ResourceNotFoundError
    assert FutureSyncError is SyncError
    assert FutureValidationError is ValidationError


def test_root_init_exports():
    """Test that the new exports are available from the galileo package root."""
    from splunk_ao import Collaborator, CollaboratorRole, Project, SyncState

    assert Project is not None
    assert Collaborator is not None
    assert CollaboratorRole is not None
    assert SyncState is not None


def test_configuration_is_same_class():
    from splunk_ao.__future__.configuration import Configuration as FutureConfiguration
    from splunk_ao.configuration import Configuration as RootConfiguration

    assert FutureConfiguration is RootConfiguration


def test_model_is_same_class():
    from splunk_ao.__future__.model import Model as FutureModel
    from splunk_ao.model import Model as RootModel

    assert FutureModel is RootModel


def test_dataset_is_same_class():
    from splunk_ao.__future__.dataset import Dataset as FutureDataset
    from splunk_ao.dataset import Dataset as RootDataset

    assert FutureDataset is RootDataset


def test_prompt_is_same_class():
    from splunk_ao.__future__.prompt import Prompt as FuturePrompt
    from splunk_ao.prompt import Prompt as RootPrompt

    assert FuturePrompt is RootPrompt


def test_integration_is_same_class():
    from splunk_ao.__future__.integration import Integration as FutureIntegration
    from splunk_ao.integration import Integration as RootIntegration

    assert FutureIntegration is RootIntegration


def test_provider_classes_are_same():
    from splunk_ao.__future__.provider import AnthropicProvider as FutureAnthropic
    from splunk_ao.__future__.provider import AzureProvider as FutureAzure
    from splunk_ao.__future__.provider import BedrockProvider as FutureBedrock
    from splunk_ao.__future__.provider import OpenAIProvider as FutureOpenAI
    from splunk_ao.__future__.provider import Provider as FutureProvider
    from splunk_ao.provider import AnthropicProvider, AzureProvider, BedrockProvider, OpenAIProvider, Provider

    assert FutureAnthropic is AnthropicProvider
    assert FutureAzure is AzureProvider
    assert FutureBedrock is BedrockProvider
    assert FutureOpenAI is OpenAIProvider
    assert FutureProvider is Provider


def test_metric_classes_are_same():
    from splunk_ao.__future__ import CodeEvaluator as FutureCodeMetric
    from splunk_ao.__future__ import LlmEvaluator as FutureLlmMetric
    from splunk_ao.__future__ import LocalEvaluator as FutureLocalMetric
    from splunk_ao.__future__ import Evaluator as FutureMetric
    from splunk_ao.__future__ import SplunkAOEvaluator as FutureSplunkAOMetric
    from splunk_ao.evaluator import CodeEvaluator, LlmEvaluator, LocalEvaluator, Evaluator, SplunkAOEvaluator

    assert FutureMetric is Evaluator
    assert FutureCodeMetric is CodeEvaluator
    assert FutureSplunkAOMetric is SplunkAOEvaluator
    assert FutureLlmMetric is LlmEvaluator
    assert FutureLocalMetric is LocalEvaluator


def test_experiment_is_same_class():
    from splunk_ao.__future__.experiment import Experiment as FutureExperiment
    from splunk_ao.experiment import Experiment as RootExperiment

    assert FutureExperiment is RootExperiment


def test_log_stream_is_same_class():
    from splunk_ao.__future__ import AgentStream as FutureLogStream
    from splunk_ao.agent_stream import AgentStream as RootLogStream

    assert FutureLogStream is RootLogStream


def test_shared_filter_functions_are_same():
    from splunk_ao.__future__.shared.filter import boolean as future_boolean
    from splunk_ao.__future__.shared.filter import date as future_date
    from splunk_ao.__future__.shared.filter import number as future_number
    from splunk_ao.__future__.shared.filter import text as future_text
    from splunk_ao.shared.filter import boolean, date, number, text

    assert future_boolean is boolean
    assert future_date is date
    assert future_number is number
    assert future_text is text


def test_shared_sort_is_same():
    from splunk_ao.__future__.shared.sort import sort as future_sort
    from splunk_ao.shared.sort import sort

    assert future_sort is sort


def test_shared_column_classes_are_same():
    from splunk_ao.__future__.shared.column import Column as FutureColumn
    from splunk_ao.__future__.shared.column import ColumnCollection as FutureColumnCollection
    from splunk_ao.shared.column import Column, ColumnCollection

    assert FutureColumn is Column
    assert FutureColumnCollection is ColumnCollection


def test_shared_query_result_is_same():
    from splunk_ao.__future__.shared.query_result import QueryResult as FutureQueryResult
    from splunk_ao.shared.query_result import QueryResult

    assert FutureQueryResult is QueryResult


def test_shared_experiment_result_classes_are_same():
    from splunk_ao.__future__.shared.experiment_result import ExperimentRunResult as FutureRunResult
    from splunk_ao.__future__.shared.experiment_result import ExperimentStatusInfo as FutureStatusInfo
    from splunk_ao.shared.experiment_result import ExperimentRunResult, ExperimentStatusInfo

    assert FutureRunResult is ExperimentRunResult
    assert FutureStatusInfo is ExperimentStatusInfo


def test_types_metric_spec_is_same():
    from splunk_ao.__future__.types import MetricSpec as FutureMetricSpec
    from splunk_ao.types import MetricSpec

    assert FutureMetricSpec is MetricSpec


def test_provider_generic_and_unconfigured_are_same():
    from splunk_ao.__future__.provider import GenericProvider as FutureGeneric
    from splunk_ao.__future__.provider import UnconfiguredProvider as FutureUnconfigured
    from splunk_ao.provider import GenericProvider, UnconfiguredProvider

    assert FutureGeneric is GenericProvider
    assert FutureUnconfigured is UnconfiguredProvider


def test_metric_builtin_metrics_is_same():
    from splunk_ao.__future__ import BuiltInEvaluators as FutureBuiltIn
    from splunk_ao.evaluator import BuiltInEvaluators

    assert FutureBuiltIn is BuiltInEvaluators


def test_prompt_private_symbols_are_same():
    from splunk_ao.__future__.prompt import PromptVersion as FuturePromptVersion
    from splunk_ao.__future__.prompt import _parse_template_to_messages as future_parse
    from splunk_ao.prompt import PromptVersion, _parse_template_to_messages

    assert FuturePromptVersion is PromptVersion
    assert future_parse is _parse_template_to_messages


def test_shared_column_unwrap_unset_is_same():
    from splunk_ao.__future__.shared.column import _unwrap_unset as future_unwrap
    from splunk_ao.shared.column import _unwrap_unset

    assert future_unwrap is _unwrap_unset


def test_shared_query_result_flatten_dict_is_same():
    from splunk_ao.__future__.shared.query_result import _flatten_dict as future_flatten
    from splunk_ao.shared.query_result import _flatten_dict

    assert future_flatten is _flatten_dict


def test_shared_experiment_result_phase_info_is_same():
    from splunk_ao.__future__.shared.experiment_result import ExperimentPhaseInfo as FuturePhaseInfo
    from splunk_ao.shared.experiment_result import ExperimentPhaseInfo

    assert FuturePhaseInfo is ExperimentPhaseInfo


def test_shared_utils_classproperty_is_same():
    from splunk_ao.__future__.shared.utils import classproperty as future_classproperty
    from splunk_ao.shared.utils import classproperty

    assert future_classproperty is classproperty


def test_configuration_private_symbols_are_same():
    from splunk_ao.__future__.configuration import _CONFIGURATION_KEYS as future_keys
    from splunk_ao.__future__.configuration import VALID_LOG_LEVELS as future_levels
    from splunk_ao.__future__.configuration import parse_log_level as future_parse
    from splunk_ao.configuration import _CONFIGURATION_KEYS, VALID_LOG_LEVELS, parse_log_level

    assert future_keys is _CONFIGURATION_KEYS
    assert future_levels is VALID_LOG_LEVELS
    assert future_parse is parse_log_level


def test_shared_sort_class_is_same():
    from splunk_ao.__future__.shared.sort import Sort as FutureSort
    from splunk_ao.shared.sort import Sort

    assert FutureSort is Sort


def test_root_init_has_new_exports():
    """Test that all newly migrated domain objects are available from splunk_ao package root."""
    from splunk_ao import (
        AnthropicProvider,
        AzureProvider,
        BedrockProvider,
        CodeEvaluator,
        Configuration,
        Dataset,
        Experiment,
        Integration,
        LlmEvaluator,
        LocalEvaluator,
        AgentStream,
        Evaluator,
        MetricSpec,
        Model,
        OpenAIProvider,
        Prompt,
        Provider,
        SplunkAOEvaluator,
    )

    assert Configuration is not None
    assert Dataset is not None
    assert Experiment is not None
    assert Integration is not None
    assert AgentStream is not None
    assert Evaluator is not None
    assert CodeEvaluator is not None
    assert SplunkAOEvaluator is not None
    assert LlmEvaluator is not None
    assert LocalEvaluator is not None
    assert MetricSpec is not None
    assert Model is not None
    assert Prompt is not None
    assert Provider is not None
    assert AnthropicProvider is not None
    assert AzureProvider is not None
    assert BedrockProvider is not None
    assert OpenAIProvider is not None
