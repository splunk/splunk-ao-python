"""Forward compatibility of generated API enum parsing."""

from typing import Any

import pytest

from splunk_ao.resources.models.execution_status import ExecutionStatus
from splunk_ao.resources.models.log_records_export_request import LogRecordsExportRequest
from splunk_ao.resources.models.permission import Permission
from splunk_ao.resources.models.project_action import ProjectAction
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


@pytest.mark.parametrize("role", ["capability_based", "future_role"])
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


def test_known_user_role_remains_an_enum(user_payload: dict[str, Any]) -> None:
    # Given: a known role in the response
    user_payload["role"] = "user"

    # When: parsing the user response
    user = UserDB.from_dict(user_payload)

    # Then: existing enum comparisons and serialization keep working
    assert user.role is UserRole.USER
    assert user.to_dict()["role"] == "user"


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
    payload = {"action": "configure_rate_limit", "allowed": allowed}

    # When: parsing a union of action enums
    permission = Permission.from_dict(payload)

    # Then: an unknown action keeps its name without an invented enum category
    assert type(permission.action) is str
    assert permission.action == "configure_rate_limit"
    assert permission.to_dict() == payload


def test_permission_uses_known_enum_before_raw_string_fallback() -> None:
    # Given: an action from a later enum in the permission union
    payload = {"action": "rename", "allowed": True}

    # When: parsing it alongside enums that do not declare the action
    permission = Permission.from_dict(payload)

    # Then: known values keep their existing enum type
    assert permission.action is ProjectAction.RENAME
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
