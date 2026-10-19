import datetime
import logging
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from galileo_core.schemas.logging.step import StepType
from splunk_ao.config import SplunkAOConfig
from splunk_ao.exceptions import EvaluatorPermissionError, ForbiddenError, SplunkAOAPIError
from splunk_ao.resources.api.data import (
    create_decision_scorer_version_scorers_scorer_id_version_decision_post,
    create_llm_scorer_version_scorers_scorer_id_version_llm_post,
    create_scorers_post,
    delete_scorer_scorers_scorer_id_delete,
)
from splunk_ao.resources.api.trace import query_metrics_projects_project_id_metrics_search_post
from splunk_ao.resources.models import (
    HTTPValidationError,
    LogRecordsMetricsQueryRequest,
    LogRecordsMetricsResponse,
    ScorerTypes,
)
from splunk_ao.resources.models.base_scorer_version_response import BaseScorerVersionResponse
from splunk_ao.resources.models.create_decision_scorer_version_request import CreateDecisionScorerVersionRequest
from splunk_ao.resources.models.create_llm_scorer_version_request import CreateLLMScorerVersionRequest
from splunk_ao.resources.models.create_scorer_request import CreateScorerRequest
from splunk_ao.resources.models.decision_level import DecisionLevel
from splunk_ao.resources.models.input_type_enum import InputTypeEnum
from splunk_ao.resources.models.output_type_enum import OutputTypeEnum
from splunk_ao.resources.models.scorer_defaults import ScorerDefaults
from splunk_ao.resources.types import UNSET, Unset
from splunk_ao.scorers import Scorers
from splunk_ao.search import FilterType
from splunk_ao.shared.exceptions import NotFoundError, ValidationError, _resolve_project_identifiers
from splunk_ao.shared.project_resolver import _resolve_project

_logger = logging.getLogger(__name__)

DecisionAnswerOptions = Sequence[str] | Sequence[DecisionLevel | Mapping[str, Any]]


def normalize_decision_answer_options(
    answer_options: DecisionAnswerOptions | Unset | None,
) -> list[str] | list[DecisionLevel] | None:
    """Convert user-facing answer options into the request shape.

    Strings pass through (categorical). ``DecisionLevel`` objects and ``{level, label, description}`` dicts
    become ``DecisionLevel`` (discrete). ``None`` stays ``None`` (boolean_probability).
    """
    if answer_options is None or isinstance(answer_options, Unset):
        return None
    if isinstance(answer_options, str | bytes | Mapping):
        raise ValueError("answer_options must be a list, not a single string or dict.")
    options = list(answer_options)
    if not options:
        raise ValueError("answer_options must not be empty; pass None for boolean_probability.")
    if all(isinstance(option, str) for option in options):
        return [str(option) for option in options]
    levels: list[DecisionLevel] = []
    for index, option in enumerate(options):
        if isinstance(option, DecisionLevel):
            levels.append(option)
        elif isinstance(option, Mapping):
            missing = [key for key in ("level", "label") if key not in option]
            if missing:
                raise ValueError(f"answer_options[{index}] is missing required key(s): {', '.join(missing)}.")
            level, label = option["level"], option["label"]
            if isinstance(level, bool) or not isinstance(level, int) or not isinstance(label, str):
                raise ValueError(f"answer_options[{index}] needs an integer 'level' and a string 'label'.")
            levels.append(DecisionLevel(level=level, label=label, description=option.get("description") or UNSET))
        else:
            raise ValueError(
                "answer_options must be a list of strings (categorical) or a list of DecisionLevel / "
                f"{{level, label, description}} dicts (discrete); got {type(option).__name__} at index {index}."
            )
    return levels


class DecisionVersionOutcomeUnknownError(RuntimeError):
    """The version request failed without a definitive rejection, so the scorer was kept.

    A rate limit (429) is also treated as unknown, so it leaves a scorer without a version; delete it by id
    before retrying with the same name.

    Attributes
    ----------
        scorer_id (str): The scorer that may or may not have a version.
    """

    def __init__(self, scorer_id: str, cause: Exception) -> None:
        self.scorer_id = scorer_id
        super().__init__(
            f"Creating the decision evaluator version failed with an unknown outcome; scorer_id={scorer_id} "
            f"was kept and may have a version: {cause}"
        )


_GLOBAL_CREATE_DENIED_HINT = (
    "Only org admins can create global evaluators. Pass project_ids=[...] to scope the evaluator to your projects, "
    "or set SPLUNK_AO_PROJECT / SPLUNK_AO_PROJECT_ID so it defaults to one."
)
_SCOPED_CREATE_DENIED_HINT = (
    "Creating a project-scoped evaluator needs the owner or editor role on every project in project_ids "
    "(or on the current project when it is the default). Ask a project owner for access, or choose other projects."
)
_SCOPE_CHANGE_DENIED_HINT = (
    "Changing an evaluator's scope needs the owner or editor role on each project added or removed; "
    "making it global needs the org admin role."
)


def _edit_denied_hint(action: str) -> str:
    """Hint for a 403 when updating or deleting an evaluator."""
    return (
        f"You can't {action} this evaluator. It needs the owner or editor role on one of the evaluator's projects "
        "(org admin for a global evaluator)."
    )


def _create_denied_hint(scope_is_global: bool | Unset) -> str:
    """Hint for a 403 on create, chosen from the scope that was actually sent."""
    return _SCOPED_CREATE_DENIED_HINT if scope_is_global is False else _GLOBAL_CREATE_DENIED_HINT


@contextmanager
def _translate_forbidden(hint: str) -> Iterator[None]:
    """Re-raise a 403 from the wrapped call as an ``EvaluatorPermissionError`` carrying ``hint``."""
    try:
        yield
    except EvaluatorPermissionError:
        raise
    except ForbiddenError as error:
        raise EvaluatorPermissionError(error.status_code, error.content, hint) from error


REJECTION_STATUS_CODES = frozenset({400, 403, 404, 422})


class _VersionRejected(ValueError):
    """The server answered the version request with a validation error or no body, so no version exists."""


DECISION_OUTPUT_TYPES = (OutputTypeEnum.BOOLEAN_PROBABILITY, OutputTypeEnum.CATEGORICAL, OutputTypeEnum.DISCRETE)


def resolve_decision_output_type(
    output_type: OutputTypeEnum | str | None, answer_options: list[str] | list[DecisionLevel] | None
) -> OutputTypeEnum:
    """Return the explicit output type, or infer it from the normalized answer options.

    ``None`` options mean ``boolean_probability``, strings mean ``categorical`` and levels mean ``discrete``.
    An explicit value wins, and the request validation then rejects a mismatch with the options.
    """
    if output_type is not None:
        try:
            resolved = OutputTypeEnum(output_type.lower() if isinstance(output_type, str) else output_type)
        except ValueError:
            resolved = None
        if resolved not in DECISION_OUTPUT_TYPES:
            raise ValueError(
                f"output_type must be one of {[t.value for t in DECISION_OUTPUT_TYPES]} for decision evaluators; "
                f"got {output_type!r}."
            )
        return resolved
    if answer_options is None:
        return OutputTypeEnum.BOOLEAN_PROBABILITY
    if all(isinstance(option, str) for option in answer_options):
        return OutputTypeEnum.CATEGORICAL
    return OutputTypeEnum.DISCRETE


MAX_QUESTION_LENGTH = 2000


def validate_decision_request(
    output_type: OutputTypeEnum, answer_options: list[str] | list[DecisionLevel] | None, question: str | None = None
) -> None:
    """Reject requests the server would refuse, before anything is created.

    Checks the question length (1-2,000 characters when given) and that the answer options match the output
    type: none for boolean_probability, 2-255 unique labels for categorical, 2-10 levels numbered 0, 1, 2 and
    so on in order for discrete.
    """
    if question is not None and not 1 <= len(question) <= MAX_QUESTION_LENGTH:
        raise ValueError(f"question must be 1-{MAX_QUESTION_LENGTH} characters; got {len(question)}.")
    if output_type == OutputTypeEnum.BOOLEAN_PROBABILITY:
        if answer_options is not None:
            raise ValueError("answer_options must be None for boolean_probability.")
    elif output_type == OutputTypeEnum.CATEGORICAL:
        if not answer_options or not all(isinstance(option, str) for option in answer_options):
            raise ValueError("answer_options must be a list of label strings for categorical.")
        if not 2 <= len(answer_options) <= 255 or len(set(answer_options)) != len(answer_options):
            raise ValueError("answer_options must hold 2-255 unique labels for categorical.")
    else:
        if not answer_options or not all(isinstance(option, DecisionLevel) for option in answer_options):
            raise ValueError("answer_options must be a list of levels (DecisionLevel or dict) for discrete.")
        if not 2 <= len(answer_options) <= 10:
            raise ValueError("answer_options must hold 2-10 levels for discrete.")
        if [level.level for level in answer_options if isinstance(level, DecisionLevel)] != list(
            range(len(answer_options))
        ):
            raise ValueError("discrete levels must be numbered 0, 1, 2 and so on in order.")


def _build_decision_version_request(
    model_name: str, question: str, answer_options: list[str] | list[DecisionLevel] | None
) -> CreateDecisionScorerVersionRequest:
    """Build the version request, serializing discrete levels ourselves.

    The generated ``CreateDecisionScorerVersionRequest.to_dict`` has two identical ``isinstance(list)``
    branches for ``list[str] | list[DecisionLevel]``, so it never calls ``DecisionLevel.to_dict`` and would
    send raw objects. ``additional_properties`` is merged into the body verbatim, so levels go there.
    Fixing the codegen template would touch many unrelated generated models.
    """
    if answer_options and all(isinstance(level, DecisionLevel) for level in answer_options):
        request = CreateDecisionScorerVersionRequest(model_name=model_name, question=question)
        request.additional_properties["answer_options"] = [
            level.to_dict() for level in answer_options if isinstance(level, DecisionLevel)
        ]
        return request
    return CreateDecisionScorerVersionRequest(model_name=model_name, question=question, answer_options=answer_options)


def _resolve_create_scope(
    project_ids: list[str] | None, is_global: bool | None
) -> tuple[bool | Unset, list[str] | Unset]:
    """
    Resolve the ``(is_global, project_ids)`` pair to send when creating an evaluator.

    Explicit arguments win. Otherwise the scope defaults to the current project, taken from
    the decorator context, then ``SPLUNK_AO_PROJECT_ID``, then ``SPLUNK_AO_PROJECT``. When
    none of those is set and nothing was passed, no scope is sent and the server default
    (global, org admins only) applies.

    Parameters
    ----------
    project_ids
        Projects to scope the evaluator to.
    is_global
        Whether the evaluator is global. Cannot be combined with ``project_ids``.

    Returns
    -------
    tuple[bool | Unset, list[str] | Unset]
        The values for ``CreateScorerRequest.is_global`` and ``CreateScorerRequest.project_ids``.

    Raises
    ------
    ValidationError
        If the arguments conflict, ``project_ids`` is empty, or ``is_global=False`` is passed
        with no project to scope to.
    NotFoundError
        If a current project is set but cannot be found.
    """
    if is_global is True:
        if project_ids:
            raise ValidationError("An evaluator cannot be both global and scoped: pass is_global=True or project_ids.")
        return True, UNSET

    if project_ids is not None:
        # Typed as object so the str guard is not flagged unreachable for a list[str] parameter.
        requested: object = project_ids
        if isinstance(requested, str):
            raise ValidationError("project_ids must be a list of project ids, not a single string.")
        if not project_ids:
            raise ValidationError("project_ids must not be empty. Pass is_global=True for a global evaluator.")
        return False, list(dict.fromkeys(project_ids))

    # Imported here because decorator.py imports modules that depend on this one.
    from splunk_ao.decorator import splunk_ao_context

    context_project = (splunk_ao_context.get_current_project() or "").strip() or None
    project_id: str | None
    project_name: str | None
    if context_project:
        project_id, project_name = None, context_project
    else:
        project_id, project_name = _resolve_project_identifiers(None, None)

    if project_id or project_name:
        try:
            return False, [_resolve_project(project_id, project_name).id]
        except NotFoundError as e:
            raise type(e)(
                "Evaluator scope defaults to the current project (decorator context, SPLUNK_AO_PROJECT_ID or "
                f"SPLUNK_AO_PROJECT), which was not found. Pass project_ids=[...] or is_global=True. {e}"
            ) from e

    if is_global is False:
        raise ValidationError("is_global=False needs project_ids or a current project.")
    return UNSET, UNSET


class Evaluators:
    config: SplunkAOConfig

    def __init__(self) -> None:
        self.config = SplunkAOConfig.get()

    def delete_evaluator(self, name: str) -> None:
        scorers_to_delete = Scorers().list(name=name)
        if not scorers_to_delete:
            raise ValueError(f"Evaluator with name '{name}' not found, or not shared with your projects.")

        for scorer in scorers_to_delete:
            with _translate_forbidden(_edit_denied_hint("delete")):
                response = delete_scorer_scorers_scorer_id_delete.sync(
                    scorer_id=scorer.id, client=self.config.api_client
                )

            if isinstance(response, HTTPValidationError):
                raise ValueError(response.detail)
            if response is None:
                raise ValueError("Failed to delete metric.")

    def create_custom_llm_evaluator(
        self,
        name: str,
        user_prompt: str,
        node_level: StepType = StepType.llm,
        cot_enabled: bool = True,
        model_name: str = "gpt-4.1-mini",
        num_judges: int = 3,
        description: str = "",
        tags: list[str] | None = None,
        output_type: OutputTypeEnum = OutputTypeEnum.BOOLEAN,
        ground_truth: bool = False,
        project_ids: list[str] | None = None,
        is_global: bool | None = None,
    ) -> BaseScorerVersionResponse:
        """
        Create a custom LLM metric.

        Parameters
        ----------
        name: str
            Name of the metric.
        user_prompt: str
            User prompt for the metric.
        node_level: StepType
            Node level for the metric.
        cot_enabled: bool
            Whether chain-of-thought is enabled.
        model_name: str
            Model name to use.
        num_judges: int
            Number of judges for the metric.
        description: str
            Description of the metric.
        tags: List[str]
            Tags associated with the metric.
        output_type: OutputTypeEnum
            Output type for the metric.
        ground_truth: bool
            Whether the scorer requires ground truth (``reference_output``) from the dataset.
            When True, the judge LLM receives the row's ground-truth value in its prompt.
        project_ids: List[str]
            Projects to scope the metric to. Defaults to the current project (decorator context,
            ``SPLUNK_AO_PROJECT_ID``, or ``SPLUNK_AO_PROJECT``) when one is set.
        is_global: bool
            Create a global metric, visible to every project. Requires the org admin role and
            cannot be combined with ``project_ids``.

        Returns
        -------
        BaseScorerVersionResponse
            Response containing the created metric details.

        Raises
        ------
        ValidationError
            If the scope arguments conflict, ``project_ids`` is empty, or ``is_global=False`` is
            passed with no project to scope to.
        EvaluatorPermissionError
            If the API answers 403: org admins only for a global evaluator, owner or editor role on the
            projects for a scoped one.
        NotFoundError
            If the current project is set but cannot be found.
        """
        if tags is None:
            tags = []
        scope_is_global, scope_project_ids = _resolve_create_scope(project_ids, is_global)
        create_scorer_request = CreateScorerRequest(
            name=name,
            scorer_type=ScorerTypes.LLM,
            description=description,
            tags=tags,
            defaults=ScorerDefaults(model_name=model_name, num_judges=num_judges, cot_enabled=cot_enabled),
            scoreable_node_types=[node_level],
            output_type=output_type,
            ground_truth=ground_truth,
            is_global=scope_is_global,
            project_ids=scope_project_ids,
        )

        with _translate_forbidden(_create_denied_hint(scope_is_global)):
            scorer = create_scorers_post.sync(body=create_scorer_request, client=self.config.api_client)
        if isinstance(scorer, HTTPValidationError):
            raise ValueError(scorer.detail)
        if scorer is None:
            raise ValueError("Failed to create custom LLM evaluator.")

        version_req = CreateLLMScorerVersionRequest(user_prompt=user_prompt)
        version_resp = create_llm_scorer_version_scorers_scorer_id_version_llm_post.sync(
            scorer_id=scorer.id, body=version_req, client=self.config.api_client
        )

        _logger.info("Created custom LLM metric: %s", name)

        return version_resp

    def create_decision_evaluator(
        self,
        name: str,
        question: str,
        node_level: StepType = StepType.llm,
        model_name: str = "jev-1.13.0",
        output_type: OutputTypeEnum | str | None = None,
        answer_options: DecisionAnswerOptions | None = None,
        input_type: InputTypeEnum | None = None,
        description: str = "",
        tags: list[str] | None = None,
        ground_truth: bool = False,
        project_ids: list[str] | None = None,
        is_global: bool | None = None,
    ) -> BaseScorerVersionResponse:
        """
        Create a decision evaluator.

        Parameters
        ----------
        name: str
            Name of the evaluator.
        question: str
            The question the decision model answers (1-2,000 characters).
        node_level: StepType
            The single node type the evaluator scores.
        model_name: str
            Decision model registry version, for example ``jev-1.13.0``.
        output_type: OutputTypeEnum | str | None
            ``BOOLEAN_PROBABILITY``, ``CATEGORICAL`` or ``DISCRETE``. When ``None``, it is inferred from
            ``answer_options``: ``None`` gives ``BOOLEAN_PROBABILITY``, strings give ``CATEGORICAL`` and levels
            give ``DISCRETE``. An explicit value that does not match ``answer_options`` raises ``ValueError``.
        answer_options: list[str] | list[DecisionLevel | dict] | None
            ``None`` for ``BOOLEAN_PROBABILITY``. For ``CATEGORICAL``, a list of 2-255 unique labels. For
            ``DISCRETE``, 2-10 ``DecisionLevel`` objects (or ``{level, label, description}`` dicts) numbered
            0, 1, 2 and so on in order.
        input_type: InputTypeEnum | None
            What the model sees. When ``None``, the server picks a default for the node type.
        description: str
            Description of the evaluator.
        tags: List[str]
            Tags associated with the evaluator.
        ground_truth: bool
            Whether the scorer requires ground truth (``reference_output``) from the dataset.
        project_ids: List[str]
            Projects to scope the evaluator to. Defaults to the current project (decorator context,
            ``SPLUNK_AO_PROJECT_ID``, or ``SPLUNK_AO_PROJECT``) when one is set.
        is_global: bool
            Create a global evaluator, visible to every project. Requires the org admin role and
            cannot be combined with ``project_ids``.

        Returns
        -------
        BaseScorerVersionResponse
            Response containing the created evaluator version.

        Raises
        ------
        ValidationError
            If the scope arguments conflict, ``project_ids`` is empty, or ``is_global=False`` is
            passed with no project to scope to.
        EvaluatorPermissionError
            If the API answers 403: org admins only for a global evaluator, owner or editor role on the
            projects for a scoped one.
        NotFoundError
            If the current project is set but cannot be found.
        ValueError
            If an argument is invalid or the API answers with a validation error. If the scorer was created
            but its version was rejected, the scorer is deleted before the error is raised.
        SplunkAOAPIError
            For a definitive rejection (400, 403, 404, 422), for example 403 when the feature is not enabled.
            The scorer is deleted before the error is raised.
        DecisionVersionOutcomeUnknownError
            For a timeout, network error, 5xx or any other failure. The version may have been saved, so the
            scorer is kept and the error names its id.
        """
        normalized_options = normalize_decision_answer_options(answer_options)
        output_type = resolve_decision_output_type(output_type, normalized_options)
        validate_decision_request(output_type, normalized_options, question)
        version_req = _build_decision_version_request(
            model_name=model_name, question=question, answer_options=normalized_options
        )
        scope_is_global, scope_project_ids = _resolve_create_scope(project_ids, is_global)
        create_scorer_request = CreateScorerRequest(
            name=name,
            scorer_type=ScorerTypes.DECISION,
            description=description,
            tags=tags if tags is not None else [],
            scoreable_node_types=[node_level],
            output_type=output_type,
            input_type=input_type if input_type is not None else UNSET,
            ground_truth=ground_truth,
            is_global=scope_is_global,
            project_ids=scope_project_ids,
        )

        create_hint = _create_denied_hint(scope_is_global)
        with _translate_forbidden(create_hint):
            scorer = create_scorers_post.sync(body=create_scorer_request, client=self.config.api_client)
        if isinstance(scorer, HTTPValidationError):
            raise ValueError(scorer.detail)
        if scorer is None:
            raise ValueError("Failed to create decision evaluator.")

        try:
            version_resp = create_decision_scorer_version_scorers_scorer_id_version_decision_post.sync(
                scorer_id=scorer.id, body=version_req, client=self.config.api_client
            )
            if isinstance(version_resp, HTTPValidationError):
                raise _VersionRejected(version_resp.detail)
            if version_resp is None:
                raise _VersionRejected("Failed to create decision evaluator version.")
        except Exception as error:
            if self._was_rejected(error):
                self._delete_scorer_quietly(scorer.id)
                with _translate_forbidden(create_hint):
                    raise
            _logger.warning(
                "Decision evaluator version request failed with an unknown outcome; scorer_id=%s was kept: %s",
                scorer.id,
                error,
            )
            raise DecisionVersionOutcomeUnknownError(str(scorer.id), error) from error

        _logger.info("Created decision evaluator: %s", name)

        return version_resp

    @staticmethod
    def _was_rejected(error: Exception) -> bool:
        """True when the server clearly refused the request, so no version exists.

        Only 400, 403, 404 and 422 are definitive. Timeouts, network errors, 5xx and rate limits are unknown
        outcomes: the version may have been saved, so the scorer stays.
        """
        if isinstance(error, SplunkAOAPIError):
            return error.status_code in REJECTION_STATUS_CODES
        return isinstance(error, _VersionRejected)

    def _delete_scorer_quietly(self, scorer_id: str) -> None:
        """Best-effort cleanup so a failed create does not leave an empty scorer behind."""
        try:
            response = delete_scorer_scorers_scorer_id_delete.sync(scorer_id=scorer_id, client=self.config.api_client)
        except Exception as error:
            _logger.warning(
                "Evaluators.create_decision_evaluator: scorer_id=%s - cleanup delete failed: %s", scorer_id, error
            )
            return
        if isinstance(response, HTTPValidationError) or response is None:
            _logger.warning(
                "Evaluators.create_decision_evaluator: scorer_id=%s - cleanup delete was not confirmed: %s",
                scorer_id,
                getattr(response, "detail", response),
            )

    def query(
        self,
        project_id: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        experiment_id: str | None = None,
        agent_stream_id: str | None = None,
        filters: list[FilterType] | None = None,
        group_by: str | None = None,
        interval: int = 5,
    ) -> LogRecordsMetricsResponse:
        body = LogRecordsMetricsQueryRequest(
            start_time=start_time,
            end_time=end_time,
            experiment_id=experiment_id,
            log_stream_id=agent_stream_id,
            filters=filters or [],
            group_by=group_by,
            interval=interval,
        )

        response = query_metrics_projects_project_id_metrics_search_post.sync(
            client=self.config.api_client, project_id=str(project_id), body=body
        )

        if isinstance(response, HTTPValidationError):
            raise ValueError(response.detail)
        if response is None:
            raise ValueError("Failed to query for metrics.")

        return response


# Public functions
def create_custom_llm_evaluator(
    name: str,
    user_prompt: str,
    node_level: StepType = StepType.llm,
    cot_enabled: bool = True,
    model_name: str = "gpt-4.1-mini",
    num_judges: int = 3,
    description: str = "",
    tags: list[str] | None = None,
    output_type: OutputTypeEnum = OutputTypeEnum.BOOLEAN,
    ground_truth: bool = False,
    project_ids: list[str] | None = None,
    is_global: bool | None = None,
) -> BaseScorerVersionResponse:
    """
    Create a custom LLM metric.

    Parameters
    ----------
    name: str
        Name of the metric.
    user_prompt: str
        User prompt for the metric.
    node_level: StepType
        Node level for the metric.
    cot_enabled: bool
        Whether chain-of-thought is enabled.
    model_name: str
        Model name to use.
    num_judges: int
        Number of judges for the metric.
    description: str
        Description of the metric.
    tags: List[str]
        Tags associated with the metric.
    output_type: OutputTypeEnum
        Output type for the metric.
    ground_truth: bool
        Whether the scorer requires ground truth (``reference_output``) from the dataset.
        When True, the judge LLM receives the row's ground-truth value in its prompt.
    project_ids: List[str]
        Projects to scope the metric to. Defaults to the current project (decorator context,
        ``SPLUNK_AO_PROJECT_ID``, or ``SPLUNK_AO_PROJECT``) when one is set.
    is_global: bool
        Create a global metric, visible to every project. Requires the org admin role and
        cannot be combined with ``project_ids``.

    Returns
    -------
    BaseScorerVersionResponse
        Response containing the created metric details.

    Raises
    ------
    ValidationError
        If the scope arguments conflict, ``project_ids`` is empty, or ``is_global=False`` is
        passed with no project to scope to.
    EvaluatorPermissionError
        If the API answers 403: org admins only for a global evaluator, owner or editor role on the
        projects for a scoped one.
    NotFoundError
        If the current project is set but cannot be found.
    """
    if tags is None:
        tags = []
    return Evaluators().create_custom_llm_evaluator(
        name,
        user_prompt,
        node_level,
        cot_enabled,
        model_name,
        num_judges,
        description,
        tags,
        output_type,
        ground_truth,
        project_ids=project_ids,
        is_global=is_global,
    )


def create_decision_evaluator(
    name: str,
    question: str,
    node_level: StepType = StepType.llm,
    model_name: str = "jev-1.13.0",
    output_type: OutputTypeEnum | str | None = None,
    answer_options: DecisionAnswerOptions | None = None,
    input_type: InputTypeEnum | None = None,
    description: str = "",
    tags: list[str] | None = None,
    ground_truth: bool = False,
    project_ids: list[str] | None = None,
    is_global: bool | None = None,
) -> BaseScorerVersionResponse:
    """
    Create a decision evaluator.

    A decision evaluator asks a decision model one typed question and
    scores the node with the probabilities of the answers.

    Parameters
    ----------
    name: str
        Name of the evaluator.
    question: str
        The question the decision model answers (1-2,000 characters).
    node_level: StepType
        The single node type the evaluator scores.
    model_name: str
        Decision model registry version, for example ``jev-1.13.0``.
    output_type: OutputTypeEnum | str | None
        ``BOOLEAN_PROBABILITY``, ``CATEGORICAL`` or ``DISCRETE``. When ``None``, it is inferred from
        ``answer_options``: ``None`` gives ``BOOLEAN_PROBABILITY``, strings give ``CATEGORICAL`` and levels
        give ``DISCRETE``. An explicit value that does not match ``answer_options`` raises ``ValueError``.
    answer_options: list[str] | list[DecisionLevel | dict] | None
        ``None`` for ``BOOLEAN_PROBABILITY``. For ``CATEGORICAL``, a list of 2-255 unique labels. For
        ``DISCRETE``, 2-10 ``DecisionLevel`` objects (or ``{level, label, description}`` dicts) numbered
        0, 1, 2 and so on in order.
    input_type: InputTypeEnum | None
        What the model sees. When ``None``, the server picks a default for the node type.
    description: str
        Description of the evaluator.
    tags: List[str]
        Tags associated with the evaluator.
    ground_truth: bool
        Whether the scorer requires ground truth (``reference_output``) from the dataset.
    project_ids: List[str]
        Projects to scope the evaluator to. Defaults to the current project (decorator context,
        ``SPLUNK_AO_PROJECT_ID``, or ``SPLUNK_AO_PROJECT``) when one is set.
    is_global: bool
        Create a global evaluator, visible to every project. Requires the org admin role and
        cannot be combined with ``project_ids``.

    Returns
    -------
    BaseScorerVersionResponse
        Response containing the created evaluator version.

    Raises
    ------
    ValidationError
        If the scope arguments conflict, ``project_ids`` is empty, or ``is_global=False`` is
        passed with no project to scope to.
    EvaluatorPermissionError
        If the API answers 403: org admins only for a global evaluator, owner or editor role on the
        projects for a scoped one.
    NotFoundError
        If the current project is set but cannot be found.
    ValueError
        If an argument is invalid or the API answers with a validation error. If the scorer was created
        but its version was rejected, the scorer is deleted before the error is raised.
    SplunkAOAPIError
        For a definitive rejection (400, 403, 404, 422), for example 403 when the feature is not enabled.
        The scorer is deleted before the error is raised.
    DecisionVersionOutcomeUnknownError
        For a timeout, network error, 5xx or any other failure. The version may have been saved, so the
        scorer is kept and the error names its id.

    Examples
    --------
        from splunk_ao.evaluators import create_decision_evaluator
        from splunk_ao.resources.models import OutputTypeEnum

        create_decision_evaluator(
            name="tone",
            question="Is the tone of this response professional?",
            output_type=OutputTypeEnum.CATEGORICAL,
            answer_options=["professional", "casual", "rude"],
        )
    """
    return Evaluators().create_decision_evaluator(
        name=name,
        question=question,
        node_level=node_level,
        model_name=model_name,
        output_type=output_type,
        answer_options=answer_options,
        input_type=input_type,
        description=description,
        tags=tags,
        ground_truth=ground_truth,
        project_ids=project_ids,
        is_global=is_global,
    )


def get_evaluators(
    project_id: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    experiment_id: str | None = None,
    agent_stream_id: str | None = None,
    filters: list[FilterType] | None = None,
    group_by: str | None = None,
    interval: int = 5,
) -> LogRecordsMetricsResponse:
    """Queries for metrics in a project.

    Parameters
    ----------
    project_id
        The unique identifier of the project.
    start_time
        The start of the time range for the query.
    end_time
        The end of the time range for the query.
    experiment_id
        Filter records by a specific experiment ID.
    agent_stream_id
        Filter records by a specific agent stream ID.
    filters
        A list of filters to apply to the query.
    group_by
        The field to group the results by.
    interval
        The time interval for the query in seconds.

    Returns
    -------
    LogRecordsMetricsResponse
        A LogRecordsMetricsResponse object containing the query results, or None if the query fails.
    """
    return Evaluators().query(
        project_id=project_id,
        start_time=start_time,
        end_time=end_time,
        experiment_id=experiment_id,
        agent_stream_id=agent_stream_id,
        filters=filters,
        group_by=group_by,
        interval=interval,
    )


def delete_evaluator(name: str) -> None:
    """
    Deletes a metric by its name.

    Parameters
    ----------
    name
        The name of the metric to delete.
    """
    Evaluators().delete_evaluator(name)
