"""Forward compatibility of generated API enum parsing."""

from typing import Any

import pytest

from splunk_ao.resources.models.available_integrations import AvailableIntegrations
from splunk_ao.resources.models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
from splunk_ao.resources.models.categorical_roll_up_method import CategoricalRollUpMethod
from splunk_ao.resources.models.execution_status import ExecutionStatus
from splunk_ao.resources.models.log_records_export_request import LogRecordsExportRequest
from splunk_ao.resources.models.permission import Permission
from splunk_ao.resources.models.project_action import ProjectAction
from splunk_ao.resources.models.project_db import ProjectDB
from splunk_ao.resources.models.run_created_at_filter import RunCreatedAtFilter
from splunk_ao.resources.models.run_db import RunDB
from splunk_ao.resources.models.task_type import TaskType
from splunk_ao.resources.models.user_db import UserDB
from splunk_ao.resources.models.user_role import UserRole
from splunk_ao.resources.types import UNSET


@pytest.fixture
def user_payload() -> dict[str, Any]:
    """Return a complete user response with synthetic identity data."""
    return {
        "id": "user-id",
        "email": "user@example.com",
        "organization_id": "org-id",
        "organization_name": "Test org",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.mark.parametrize("role", ["future_role", "another_future_role"])
def test_unknown_user_role_is_a_raw_string(user_payload: dict[str, Any], role: str) -> None:
    # Given: a role added after this SDK's schema snapshot
    user_payload["role"] = role

    # When: parsing the user response
    user = UserDB.from_dict(user_payload)

    # Then: the exact string survives parsing and serialization
    assert type(user.role) is str
    assert user.role == role
    assert user.to_dict()["role"] == role
    with pytest.raises(ValueError):
        UserRole(role)


@pytest.mark.parametrize("role", ["user", "capability_based"])
def test_known_user_role_remains_an_enum(user_payload: dict[str, Any], role: str) -> None:
    # Given: a known role in the response
    user_payload["role"] = role

    # When: parsing the user response
    user = UserDB.from_dict(user_payload)

    # Then: existing enum comparisons and serialization keep working
    assert user.role is UserRole(role)
    assert user.to_dict()["role"] == role


@pytest.mark.parametrize("role", [None, 123, [], {}])
def test_user_role_rejects_wrong_primitive_types(user_payload: dict[str, Any], role: object) -> None:
    # Given: a malformed value in a string enum field
    user_payload["role"] = role

    # When/Then: open enum parsing still rejects the wrong primitive type
    with pytest.raises(TypeError, match="Unexpected value type for role"):
        UserDB.from_dict(user_payload)


def test_missing_user_role_stays_unset(user_payload: dict[str, Any]) -> None:
    # When: parsing a user response that omits the role
    user = UserDB.from_dict(user_payload)

    # Then: omission remains distinct from an unknown string value
    assert user.role is UNSET
    assert "role" not in user.to_dict()
    constructed = UserDB(**{**user_payload, "created_at": user.created_at, "updated_at": user.updated_at})
    assert constructed.role is UNSET


@pytest.mark.parametrize("task_type", [7, 999, None, True, 7.0, "7", [], {}])
def test_integer_enum_preserves_known_unknown_and_null_values(user_payload: dict[str, Any], task_type: object) -> None:
    # Given: a nullable integer enum in a run response
    payload = {
        "id": "run-id",
        "created_by": "user-id",
        "num_samples": 0,
        "winner": False,
        "last_updated_by": "user-id",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "creator": user_payload,
        "task_type": task_type,
    }

    # When/Then: numeric values and null survive, while other types are rejected
    if task_type is not None and type(task_type) is not int:
        with pytest.raises(TypeError, match="Unexpected value type for task_type"):
            RunDB.from_dict(payload)
    else:
        run = RunDB.from_dict(payload)
        if task_type == 7:
            assert run.task_type is TaskType.VALUE_7
        elif task_type is None:
            assert run.task_type is None
        else:
            assert type(run.task_type) is int
        assert run.to_dict()["task_type"] == task_type


def test_inline_enum_accepts_new_operator_while_discriminator_stays_fixed() -> None:
    # Given: a new operator in a model identified by a fixed name
    payload = {"operator": "future_operator", "value": "2026-01-01T00:00:00+00:00", "name": "created_at"}

    # When/Then: the inline enum stays extensible and the discriminator stays fixed
    assert RunCreatedAtFilter.from_dict(payload).to_dict() == payload
    with pytest.raises(ValueError, match="name must match const 'created_at'"):
        RunCreatedAtFilter.from_dict({**payload, "name": "future_field"})


@pytest.mark.parametrize("allowed", [True, False])
def test_permission_preserves_unknown_action_and_allow_decision(allowed: bool) -> None:
    # Given: an action added to the server after this SDK was generated
    payload = {"action": "future_permission_action", "allowed": allowed}

    # When: parsing a union of action enums
    permission = Permission.from_dict(payload)

    # Then: an unknown action keeps its name without an invented enum category
    assert type(permission.action) is str
    assert permission.action == "future_permission_action"
    assert permission.to_dict() == payload


@pytest.mark.parametrize("action", ["rename", "configure_rate_limit"])
def test_permission_uses_known_enum_before_raw_string_fallback(action: str) -> None:
    # Given: an action from a later enum in the permission union
    payload = {"action": action, "allowed": True}

    # When: parsing it alongside enums that do not declare the action
    permission = Permission.from_dict(payload)

    # Then: known values keep their existing enum type
    assert permission.action is ProjectAction(action)
    assert permission.to_dict() == payload


def test_request_serializes_new_service_enum_values() -> None:
    # Given: values supported by a newer service
    request = LogRecordsExportRequest(root_type="future_root", export_format="future_format")

    # When: serializing a request for the service to validate
    payload = request.to_dict()

    # Then: unknown strings survive without requiring new enum members
    assert payload["root_type"] == "future_root"
    assert payload["export_format"] == "future_format"


def test_execution_status_keeps_existing_case_normalization() -> None:
    # When: explicitly constructing a known status with legacy casing
    status = ExecutionStatus("FAILED")

    # Then: the existing custom enum behavior remains intact
    assert status is ExecutionStatus.FAILED
    assert str(status) == "failed"


@pytest.mark.parametrize("method", ["category_count", "future_method"])
def test_roll_up_methods_preserve_known_members_and_unknown_strings(method: str) -> None:
    """The first array alternative must not hide a known categorical member."""
    config = BaseMetricRollUpConfigDB.from_dict({"roll_up_methods": [method]})
    if method == "category_count":
        assert config.roll_up_methods[0] is CategoricalRollUpMethod.CATEGORY_COUNT
    else:
        assert type(config.roll_up_methods[0]) is str
    assert config.to_dict() == {"roll_up_methods": [method]}


@pytest.mark.parametrize("integrations", ["future_provider", {"future_provider": True}, 1])
def test_integration_enum_array_rejects_non_arrays(integrations: object) -> None:
    """The enclosing array shape stays strict when its items are extensible."""
    with pytest.raises(TypeError):
        AvailableIntegrations.from_dict({"integrations": integrations})


def test_project_lookup_preserves_future_labels() -> None:
    """Reusable single-member enums must support future server values."""
    payload = {
        "id": "project-id",
        "created_by": "user-id",
        "created_by_user": {"id": "user-id", "email": "user@example.com"},
        "runs": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "labels": ["future_label"],
    }
    project = ProjectDB.from_dict(payload)
    assert project.labels == ["future_label"]
    assert project.to_dict()["labels"] == ["future_label"]
