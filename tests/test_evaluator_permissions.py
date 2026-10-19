"""Clear errors for evaluator permission denials, and ``Evaluator.set_scope``."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

import splunk_ao
from splunk_ao.evaluator import CodeEvaluator, DecisionEvaluator, Evaluator, LlmEvaluator, LocalEvaluator
from splunk_ao.evaluators import Evaluators, create_custom_llm_evaluator, create_decision_evaluator
from splunk_ao.exceptions import EvaluatorPermissionError, ForbiddenError, NotFoundError
from splunk_ao.resources.models import (
    HTTPValidationError,
    ScorerResponse,
    ScorerScopeProjectRef,
    UpdateScorerScopeRequest,
)
from splunk_ao.resources.types import UNSET
from splunk_ao.shared.base import SyncState
from splunk_ao.shared.exceptions import APIError, ValidationError

pytestmark = pytest.mark.usefixtures("no_current_project")

SERVER_BODY = b'{"detail": "denied by server"}'
UNSET_GLOBAL_HINT = (
    "Only org admins can create global evaluators. Pass project_ids=[...] to scope the evaluator to your projects, "
    "or set SPLUNK_AO_PROJECT / SPLUNK_AO_PROJECT_ID so it defaults to one."
)
EXPLICIT_GLOBAL_HINT = "Only org admins can create global evaluators. Drop is_global=True and pass project_ids=[...]"
SCOPED_HINT = "owner or editor role on every project in project_ids"
DECISION_ENABLED_HINT = "Decision evaluators may also not be enabled for your organization."
UPDATE_HINT = "Updating an evaluator needs the owner or editor role on one of its projects (org admin for a global"
DELETE_HINT = "Deleting an evaluator needs the owner or editor role on one of its projects (org admin for a global"
SCOPE_HINT = (
    "owner or editor role on one of its current projects and on each project added or removed. "
    "Making it global, or changing the scope of a global evaluator, needs the org admin role."
)
GLOBAL_CASES = [({}, UNSET_GLOBAL_HINT), ({"is_global": True}, EXPLICIT_GLOBAL_HINT)]
GLOBAL_IDS = ["unset_scope", "explicit_global"]
ALL_CREATE_CASES = [*GLOBAL_CASES, ({"project_ids": ["p1"]}, SCOPED_HINT)]
ALL_CREATE_IDS = [*GLOBAL_IDS, "scoped"]


def _forbidden() -> ForbiddenError:
    return ForbiddenError(403, SERVER_BODY)


def _assert_permission_error(error: BaseException, hint: str) -> None:
    assert isinstance(error, EvaluatorPermissionError)
    assert isinstance(error, ForbiddenError)
    assert error.status_code == 403
    assert hint in error.message
    assert str(error).startswith(error.message)
    assert "denied by server" in str(error)


def _scorer_response(scorer_id: str, **extra: Any) -> ScorerResponse:
    row: dict[str, Any] = {
        "id": scorer_id,
        "name": "ev",
        "scorer_type": "llm",
        "tags": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(extra)
    return ScorerResponse.from_dict(row)


def _synced(evaluator: Evaluator) -> Evaluator:
    evaluator._sync_attrs(id=str(uuid4()))
    evaluator._set_state(SyncState.SYNCED)
    return evaluator


class TestEvaluatorPermissionErrorClass:
    def test_is_forbidden_error_and_exported(self) -> None:
        # Given: the error built the way the SDK builds it
        # When: it is created and formatted
        error = EvaluatorPermissionError(403, SERVER_BODY, "Only org admins can do this.")

        # Then: it is a ForbiddenError with the hint first and the server body after it, and it is exported
        assert isinstance(error, ForbiddenError)
        assert error.status_code == 403
        assert str(error).startswith("Only org admins can do this. (HTTP 403)")
        assert "denied by server" in str(error)
        assert "EvaluatorPermissionError" in splunk_ao.exceptions.__all__
        assert splunk_ao.EvaluatorPermissionError is EvaluatorPermissionError
        assert "EvaluatorPermissionError" in splunk_ao.__all__


@patch("splunk_ao.evaluators.create_llm_scorer_version_scorers_scorer_id_version_llm_post")
@patch("splunk_ao.evaluators.create_scorers_post")
class TestCreateLlmDenied:
    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @pytest.mark.parametrize(("kwargs", "hint"), GLOBAL_CASES, ids=GLOBAL_IDS)
    def test_global_create_403_names_admins_and_the_fix(
        self, mock_create_scorer, mock_create_version, use_function, kwargs, hint
    ) -> None:
        # Given: the server refuses a create whose scope is unset or global
        mock_create_scorer.sync.side_effect = _forbidden()
        create = create_custom_llm_evaluator if use_function else Evaluators().create_custom_llm_evaluator

        # When: the evaluator is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            create(name="m", user_prompt="prompt", **kwargs)

        # Then: the error says only org admins can create global evaluators and how to scope, with no version request
        _assert_permission_error(exc_info.value, hint)
        mock_create_version.sync.assert_not_called()

    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    def test_scoped_create_403_names_the_project_role(
        self, mock_create_scorer, mock_create_version, use_function
    ) -> None:
        # Given: a scoped create the server refuses
        mock_create_scorer.sync.side_effect = _forbidden()
        create = create_custom_llm_evaluator if use_function else Evaluators().create_custom_llm_evaluator

        # When: the evaluator is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            create(name="m", user_prompt="prompt", project_ids=["p1"])

        # Then: the message is about the project role, not about admins
        _assert_permission_error(exc_info.value, SCOPED_HINT)
        assert "org admins" not in str(exc_info.value)

    def test_hint_follows_the_resolved_scope_not_the_instance(
        self, mock_create_scorer, mock_create_version, monkeypatch
    ) -> None:
        # Given: no explicit scope, but a current project that resolves the scope to that project
        monkeypatch.setenv("SPLUNK_AO_PROJECT_ID", "proj-1")
        mock_create_scorer.sync.side_effect = _forbidden()

        # When: the evaluator is created
        with patch("splunk_ao.evaluators._resolve_project", return_value=MagicMock(id="proj-1")):
            with pytest.raises(EvaluatorPermissionError) as exc_info:
                Evaluators().create_custom_llm_evaluator(name="m", user_prompt="prompt")

        # Then: the scoped hint is used because the resolved scope is not global
        _assert_permission_error(exc_info.value, SCOPED_HINT)

    def test_already_translated_error_is_not_wrapped_again(self, mock_create_scorer, mock_create_version) -> None:
        # Given: a permission error with its own hint raised from the endpoint
        original = EvaluatorPermissionError(403, b"x", "Custom hint.")
        mock_create_scorer.sync.side_effect = original

        # When: the evaluator is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            Evaluators().create_custom_llm_evaluator(name="m", user_prompt="prompt", is_global=True)

        # Then: the same object comes out, with no cause chained
        assert exc_info.value is original
        assert exc_info.value.__cause__ is None

    def test_422_is_raised_as_value_error(self, mock_create_scorer, mock_create_version) -> None:
        # Given: the scorer post answers with a validation error
        mock_create_scorer.sync.return_value = HTTPValidationError(detail="bad name")

        # When/Then: the detail surfaces as ValueError and no version request is made
        with pytest.raises(ValueError, match="bad name"):
            Evaluators().create_custom_llm_evaluator(name="m", user_prompt="prompt", is_global=True)
        mock_create_version.sync.assert_not_called()

    def test_empty_response_is_raised_as_value_error(self, mock_create_scorer, mock_create_version) -> None:
        # Given: the scorer post returns nothing
        mock_create_scorer.sync.return_value = None

        # When/Then: a ValueError is raised instead of reading .id off None
        with pytest.raises(ValueError, match="Failed to create custom LLM evaluator"):
            Evaluators().create_custom_llm_evaluator(name="m", user_prompt="prompt", is_global=True)

    def test_llm_evaluator_create_keeps_the_error_and_marks_failed(
        self, mock_create_scorer, mock_create_version
    ) -> None:
        # Given: an LlmEvaluator with the default (global) scope the server refuses
        mock_create_scorer.sync.side_effect = _forbidden()
        evaluator = LlmEvaluator(name="m", prompt="p")

        # When: it is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            evaluator.create()

        # Then: the permission error is raised once (its cause is the plain 403) and the state is FAILED_SYNC
        _assert_permission_error(exc_info.value, UNSET_GLOBAL_HINT)
        assert type(exc_info.value.__cause__) is ForbiddenError
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    def test_llm_evaluator_create_with_projects_says_owner_or_editor(
        self, mock_create_scorer, mock_create_version
    ) -> None:
        # Given: an LlmEvaluator scoped to a project the server refuses
        mock_create_scorer.sync.side_effect = _forbidden()

        # When: it is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            LlmEvaluator(name="m", prompt="p", project_ids=["p1"]).create()

        # Then: the hint names the project role
        _assert_permission_error(exc_info.value, SCOPED_HINT)


@patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
@patch("splunk_ao.evaluators.create_decision_scorer_version_scorers_scorer_id_version_decision_post")
@patch("splunk_ao.evaluators.create_scorers_post")
class TestCreateDecisionDenied:
    @pytest.mark.parametrize("use_function", [False, True], ids=["method", "module_function"])
    @pytest.mark.parametrize(("kwargs", "hint"), ALL_CREATE_CASES, ids=ALL_CREATE_IDS)
    def test_scorer_post_403_is_translated(
        self, mock_create_scorer, mock_create_version, mock_delete, use_function, kwargs, hint
    ) -> None:
        # Given: the scorer post is refused
        mock_create_scorer.sync.side_effect = _forbidden()
        create = create_decision_evaluator if use_function else Evaluators().create_decision_evaluator

        # When: the decision evaluator is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            create(name="tone", question="q", **kwargs)

        # Then: the hint matches the resolved scope, mentions the feature gate, and nothing else was called
        _assert_permission_error(exc_info.value, hint)
        assert DECISION_ENABLED_HINT in exc_info.value.message
        mock_create_version.sync.assert_not_called()
        mock_delete.sync.assert_not_called()

    def test_version_post_403_is_translated_and_the_scorer_is_still_deleted(
        self, mock_create_scorer, mock_create_version, mock_delete
    ) -> None:
        # Given: the scorer is created, then the version post is refused
        scorer = _scorer_response(str(uuid4()), scorer_type="decision")
        mock_create_scorer.sync.return_value = scorer
        mock_create_version.sync.side_effect = _forbidden()

        # When: the decision evaluator is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            create_decision_evaluator(name="tone", question="q", project_ids=["p1"])

        # Then: the error explains the refused version (not a create-scope problem) and the orphan scorer is deleted
        _assert_permission_error(exc_info.value, "refused to save the decision evaluator's configuration")
        assert SCOPED_HINT not in str(exc_info.value)
        assert "org admins" not in str(exc_info.value)
        mock_delete.sync.assert_called_once()
        assert mock_delete.sync.call_args.kwargs["scorer_id"] == scorer.id

    def test_decision_evaluator_create_raises_one_permission_error(
        self, mock_create_scorer, mock_create_version, mock_delete
    ) -> None:
        # Given: a DecisionEvaluator with the default scope the server refuses
        mock_create_scorer.sync.side_effect = _forbidden()
        evaluator = DecisionEvaluator(name="tone", question="q")

        # When: it is created
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            evaluator.create()

        # Then: one permission error (cause is the plain 403) and FAILED_SYNC
        _assert_permission_error(exc_info.value, UNSET_GLOBAL_HINT)
        assert type(exc_info.value.__cause__) is ForbiddenError
        assert evaluator.sync_state == SyncState.FAILED_SYNC


@patch("splunk_ao.evaluator.SplunkAOConfig.get")
@patch("splunk_ao.evaluator.create_scorers_post")
class TestCreateCodeDenied:
    @pytest.mark.parametrize(("kwargs", "hint"), ALL_CREATE_CASES, ids=ALL_CREATE_IDS)
    def test_403_is_translated_by_resolved_scope(self, mock_create_scorers, mock_config, kwargs, hint) -> None:
        # Given: code validation passes and the scorer post is refused
        mock_create_scorers.sync.side_effect = _forbidden()
        evaluator = CodeEvaluator(name="c", code="def f(): pass", **kwargs)

        # When: the code evaluator is created
        with patch.object(CodeEvaluator, "_validate_code", return_value="{}"):
            with pytest.raises(EvaluatorPermissionError) as exc_info:
                evaluator.create()

        # Then: the hint matches the resolved scope and the state is FAILED_SYNC
        _assert_permission_error(exc_info.value, hint)
        assert type(exc_info.value.__cause__) is ForbiddenError
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    def test_422_is_raised_as_value_error(self, mock_create_scorers, mock_config) -> None:
        # Given: the scorer post answers with a validation error
        mock_create_scorers.sync.return_value = HTTPValidationError(detail="bad code scorer")

        # When/Then: the detail surfaces instead of an AttributeError on .id
        with patch.object(CodeEvaluator, "_validate_code", return_value="{}"):
            with pytest.raises(ValueError, match="bad code scorer"):
                CodeEvaluator(name="c", code="x", is_global=True).create()


class TestUpdateAndDeleteDenied:
    @patch("splunk_ao.evaluator.update_scorers_scorer_id_patch")
    @patch("splunk_ao.evaluator.SplunkAOConfig.get")
    def test_update_403_is_translated_and_marks_failed(self, mock_config, mock_patch) -> None:
        # Given: a synced evaluator the caller cannot edit
        evaluator = _synced(LlmEvaluator(name="m", prompt="p"))
        mock_patch.sync.side_effect = _forbidden()

        # When: it is updated
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            evaluator.update(name="new")

        # Then: the edit hint is raised and the state is FAILED_SYNC
        _assert_permission_error(exc_info.value, UPDATE_HINT)
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    @patch("splunk_ao.evaluator.update_scorers_scorer_id_patch")
    @patch("splunk_ao.evaluator.SplunkAOConfig.get")
    def test_update_404_stays_not_found(self, mock_config, mock_patch) -> None:
        # Given: the server answers 404 (it hides evaluators outside the caller's projects)
        evaluator = _synced(LlmEvaluator(name="m", prompt="p"))
        mock_patch.sync.side_effect = NotFoundError(404, b"gone")

        # When: the evaluator is updated
        with pytest.raises(NotFoundError) as exc_info:
            evaluator.update(name="new")

        # Then: it stays a NotFoundError, never a permission error, and the state is FAILED_SYNC as before
        assert not isinstance(exc_info.value, EvaluatorPermissionError)
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    @patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
    @patch("splunk_ao.scorers.Scorers.list")
    def test_delete_evaluator_403_is_translated(self, mock_list, mock_delete) -> None:
        # Given: a listed scorer whose delete the server refuses
        mock_list.return_value = [_scorer_response(str(uuid4()))]
        mock_delete.sync.side_effect = _forbidden()

        # When: it is deleted by name through the service
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            Evaluators().delete_evaluator(name="ev")

        # Then: the delete hint is raised
        _assert_permission_error(exc_info.value, DELETE_HINT)

    @patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
    @patch("splunk_ao.scorers.Scorers.list")
    def test_delete_by_name_403_is_translated(self, mock_list, mock_delete) -> None:
        # Given: a listed scorer whose delete the server refuses
        mock_list.return_value = [_scorer_response(str(uuid4()))]
        mock_delete.sync.side_effect = _forbidden()

        # When: Evaluator.delete_by_name is called
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            Evaluator.delete_by_name("ev")

        # Then: the delete hint is raised
        _assert_permission_error(exc_info.value, DELETE_HINT)

    @patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
    @patch("splunk_ao.scorers.Scorers.list")
    def test_instance_delete_403_is_translated_and_marks_failed(self, mock_list, mock_delete) -> None:
        # Given: a synced evaluator whose delete the server refuses
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        mock_list.return_value = [_scorer_response(str(uuid4()))]
        mock_delete.sync.side_effect = _forbidden()

        # When: it is deleted
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            evaluator.delete()

        # Then: the delete hint is raised and the state is FAILED_SYNC
        _assert_permission_error(exc_info.value, DELETE_HINT)
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    @patch("splunk_ao.evaluators.delete_scorer_scorers_scorer_id_delete")
    @patch("splunk_ao.scorers.Scorers.list")
    def test_delete_404_stays_not_found(self, mock_list, mock_delete) -> None:
        # Given: the server answers 404 to the delete
        mock_list.return_value = [_scorer_response(str(uuid4()))]
        mock_delete.sync.side_effect = NotFoundError(404, b"gone")

        # When: the evaluator is deleted
        with pytest.raises(NotFoundError) as exc_info:
            Evaluators().delete_evaluator(name="ev")

        # Then: it stays a NotFoundError, never a permission error
        assert not isinstance(exc_info.value, EvaluatorPermissionError)


class TestNotFoundWording:
    @patch("splunk_ao.scorers.Scorers.list", return_value=[])
    def test_delete_evaluator_name_not_in_list(self, mock_list) -> None:
        # Given: no scorer with that name is visible
        # When/Then: the error says it may simply not be shared with the caller's projects
        with pytest.raises(ValueError, match="not found, or not shared with your projects"):
            Evaluators().delete_evaluator(name="ghost")

    @patch("splunk_ao.evaluator.Scorers")
    def test_refresh_id_not_in_list(self, mock_scorers) -> None:
        # Given: a synced evaluator whose id is no longer in the visible list
        evaluator = _synced(LlmEvaluator(name="m", prompt="p"))
        mock_scorers.return_value.list.return_value = []

        # When/Then: refresh says it may not be shared with the caller's projects
        with pytest.raises(ValueError, match="not found, or not shared with your projects"):
            evaluator.refresh()

    @patch("splunk_ao.evaluator.Scorers")
    def test_get_still_returns_none_and_documents_why(self, mock_scorers) -> None:
        # Given: no visible scorers
        mock_scorers.return_value.list.return_value = []

        # When/Then: get returns None by name and id, and its docstring explains the sharing case
        assert Evaluator.get(name="ghost") is None
        assert Evaluator.get(id="ghost-id") is None
        assert "isn't shared with the caller's projects" in (Evaluator.get.__doc__ or "")


@patch("splunk_ao.evaluator.set_scorer_scope_scorers_scorer_id_scope_put")
@patch("splunk_ao.evaluator.SplunkAOConfig.get")
class TestSetScope:
    def test_scoped_request_populates_instance_and_returns_self(self, mock_config, mock_put) -> None:
        # Given: a synced evaluator created with its own (private) scope request
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p", project_ids=["old"]))
        mock_put.sync.return_value = _scorer_response(
            evaluator.id, is_global=False, scope_projects=[{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
        )

        # When: its scope is replaced, with a duplicate id in the request
        result = evaluator.set_scope(project_ids=["a", "b", "a"])

        # Then: the request is deduplicated, the response is applied, and the create-time scope is untouched
        assert result is evaluator
        kwargs = mock_put.sync.call_args.kwargs
        assert kwargs["scorer_id"] == evaluator.id
        assert kwargs["client"] is mock_config.return_value.api_client
        body = kwargs["body"]
        assert isinstance(body, UpdateScorerScopeRequest)
        assert body.is_global is False
        assert body.project_ids == ["a", "b"]
        assert evaluator.is_global is False
        assert [p.id for p in evaluator.scope_projects] == ["a", "b"]
        assert all(isinstance(p, ScorerScopeProjectRef) for p in evaluator.scope_projects)
        assert evaluator.is_synced()
        assert evaluator._create_project_ids == ["old"]
        assert evaluator._create_is_global is None

    def test_global_request_sends_no_project_ids(self, mock_config, mock_put) -> None:
        # Given: a synced evaluator and a server that reports it global
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        mock_put.sync.return_value = _scorer_response(evaluator.id, is_global=True, scope_projects=[])

        # When: it is made global
        evaluator.set_scope(is_global=True)

        # Then: the request carries is_global=True and no project_ids, and the response is applied
        body = mock_put.sync.call_args.kwargs["body"]
        assert body.is_global is True
        assert body.project_ids is UNSET
        assert "project_ids" not in body.to_dict()
        assert evaluator.is_global is True
        assert evaluator.is_synced()

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"is_global": True, "project_ids": ["a"]}, "both global and scoped"),
            ({"is_global": False}, "must not be empty"),
            ({"project_ids": []}, "must not be empty"),
            ({"project_ids": None, "is_global": False}, "must not be empty"),
            ({"project_ids": "a-single-id"}, "not a single string"),
            ({"project_ids": "a-single-id", "is_global": True}, "both global and scoped"),
        ],
    )
    def test_invalid_arguments_make_no_request_and_keep_state(self, mock_config, mock_put, kwargs, message) -> None:
        # Given: a synced evaluator
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))

        # When: set_scope gets conflicting, missing, empty or bare-string project ids
        with pytest.raises(ValidationError, match=message):
            evaluator.set_scope(**kwargs)

        # Then: no request was made and the state is unchanged
        mock_put.sync.assert_not_called()
        assert evaluator.is_synced()

    def test_local_evaluator_is_rejected(self, mock_config, mock_put) -> None:
        # Given: a local-only evaluator
        local = LocalEvaluator(name="local", scorer_fn=lambda trace: 1.0)

        # When/Then: set_scope refuses before any request
        with pytest.raises(ValidationError, match="Local evaluators"):
            local.set_scope(project_ids=["a"])
        mock_put.sync.assert_not_called()

    def test_missing_id_is_rejected(self, mock_config, mock_put) -> None:
        # Given: an evaluator that was never created
        evaluator = LlmEvaluator(name="ev", prompt="p")

        # When/Then: set_scope refuses before any request
        with pytest.raises(ValueError, match="ID is not set"):
            evaluator.set_scope(project_ids=["a"])
        mock_put.sync.assert_not_called()

    @pytest.mark.parametrize("state", [SyncState.DELETED, SyncState.FAILED_SYNC])
    def test_deleted_and_failed_sync_are_rejected(self, mock_config, mock_put, state) -> None:
        # Given: an evaluator in a state that cannot be changed
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        evaluator._set_state(state)

        # When/Then: set_scope refuses before any request
        with pytest.raises(ValueError, match=r"deleted|FAILED_SYNC"):
            evaluator.set_scope(project_ids=["a"])
        mock_put.sync.assert_not_called()

    @pytest.mark.parametrize("kwargs", [{"project_ids": ["a"]}, {"is_global": True}], ids=["scoped", "global"])
    def test_403_is_translated_and_marks_failed(self, mock_config, mock_put, kwargs) -> None:
        # Given: a synced evaluator whose scope change the server refuses
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        mock_put.sync.side_effect = _forbidden()

        # When: its scope is changed
        with pytest.raises(EvaluatorPermissionError) as exc_info:
            evaluator.set_scope(**kwargs)

        # Then: the scope-change hint is raised and the state is FAILED_SYNC
        _assert_permission_error(exc_info.value, SCOPE_HINT)
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    def test_404_stays_not_found(self, mock_config, mock_put) -> None:
        # Given: the server answers 404 (it hides evaluators outside the caller's projects)
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        mock_put.sync.side_effect = NotFoundError(404, b"gone")

        # When: its scope is changed
        with pytest.raises(NotFoundError) as exc_info:
            evaluator.set_scope(project_ids=["a"])

        # Then: it stays a NotFoundError, never a permission error, and the state is FAILED_SYNC
        assert not isinstance(exc_info.value, EvaluatorPermissionError)
        assert evaluator.sync_state == SyncState.FAILED_SYNC

    def test_validation_error_response_raises_api_error(self, mock_config, mock_put) -> None:
        # Given: the server answers with a validation error
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        mock_put.sync.return_value = HTTPValidationError(detail="unknown project")

        # When/Then: an APIError carries the detail
        with pytest.raises(APIError, match="unknown project"):
            evaluator.set_scope(project_ids=["a"])

    def test_empty_response_raises_api_error(self, mock_config, mock_put) -> None:
        # Given: the server returns nothing
        evaluator = _synced(LlmEvaluator(name="ev", prompt="p"))
        mock_put.sync.return_value = None

        # When/Then: an APIError reports the empty response
        with pytest.raises(APIError, match="empty response"):
            evaluator.set_scope(project_ids=["a"])
