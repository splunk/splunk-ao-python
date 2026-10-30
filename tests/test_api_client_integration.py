from collections.abc import Callable

import pytest

from galileo_core.constants.request_method import RequestMethod
from galileo_core.helpers.api_client import ApiClient
from splunk_ao.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from splunk_ao.resources import errors
from splunk_ao.resources.api.health import healthcheck_healthcheck_get
from splunk_ao.resources.api.projects import get_projects_projects_get
from splunk_ao.resources.models.project_action import ProjectAction
from splunk_ao.resources.models.user_role import UserRole
from splunk_ao.resources.types import Unset


def test_common_http_errors_raise_specific_exceptions(mock_request: Callable) -> None:
    """
    Tests that common HTTP error codes raise specific exceptions with actionable messages.
    """
    client = ApiClient(host="https://api.galileo.ai/", jwt_token="dummy-token")

    # Test 400 Bad Request
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=400, text="Bad Request")
    with pytest.raises(BadRequestError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 400
    assert "Bad request" in str(exc_info.value)

    # Test 401 Unauthorized
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=401, text="Unauthorized")
    with pytest.raises(AuthenticationError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 401
    assert "Authentication failed" in str(exc_info.value)

    # Test 403 Forbidden
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=403, text="Forbidden")
    with pytest.raises(ForbiddenError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 403
    assert "Permission denied" in str(exc_info.value)

    # Test 404 Not Found
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=404, text="Not Found")
    with pytest.raises(NotFoundError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 404
    assert "Resource not found" in str(exc_info.value)

    # Test 409 Conflict
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=409, text="Conflict")
    with pytest.raises(ConflictError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 409
    assert "Resource conflict" in str(exc_info.value)

    # Test 429 Rate Limit
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=429, text="Too Many Requests")
    with pytest.raises(RateLimitError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in str(exc_info.value)

    # Test 500 Server Error
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=500, text="Internal Server Error")
    with pytest.raises(ServerError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 500
    assert "Server error" in str(exc_info.value)

    # Test 503 Service Unavailable (also covered by ServerError for >= 500)
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=503, text="Service Unavailable")
    with pytest.raises(ServerError) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 503


def test_unexpected_status_raises_for_unknown_codes(mock_request: Callable) -> None:
    """
    Tests that truly unexpected status codes raise UnexpectedStatus.
    """
    client = ApiClient(host="https://api.galileo.ai/", jwt_token="dummy-token")

    # Test 201 Created - unexpected for healthcheck endpoint
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=201, text="Created")
    with pytest.raises(errors.UnexpectedStatus) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 201

    # Test 418 I'm a teapot - truly unexpected
    mock_request(method=RequestMethod.GET, path="/healthcheck", status_code=418, text="I'm a teapot")
    with pytest.raises(errors.UnexpectedStatus) as exc_info:
        healthcheck_healthcheck_get.sync(client=client)
    assert exc_info.value.status_code == 418


@pytest.mark.parametrize("role", ["user", "capability_based", "future_role"])
def test_project_lookup_parses_new_enum_values_in_nested_run(mock_request: Callable, role: str) -> None:
    """A successful project lookup preserves enum values added by a newer API."""
    # Given: a project response with a run creator and enum values from a newer API
    timestamp = "2026-01-01T00:00:00+00:00"
    creator = {
        "id": "user-id",
        "email": "user@example.com",
        "organization_id": "org-id",
        "organization_name": "Test org",
        "created_at": timestamp,
        "updated_at": timestamp,
        "role": role,
    }
    run = {
        "id": "run-id",
        "created_by": creator["id"],
        "num_samples": 0,
        "winner": False,
        "last_updated_by": creator["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "creator": creator,
        "task_type": 999,
    }
    project = {
        "id": "project-id",
        "name": "demo",
        "created_by": creator["id"],
        "created_by_user": {"id": creator["id"], "email": creator["email"]},
        "runs": [run],
        "created_at": timestamp,
        "updated_at": timestamp,
        "permissions": [{"action": "rename", "allowed": True}, {"action": "future_action", "allowed": False}],
    }
    mock_request(method=RequestMethod.GET, path="/projects", status_code=200, json=[project])
    client = ApiClient(host="https://api.galileo.ai/", jwt_token="dummy-token")

    # When: parsing the successful project lookup through the generated endpoint
    parsed = get_projects_projects_get.sync(client=client, project_name="demo")

    # Then: new server enum values do not block session initialization
    assert isinstance(parsed, list)
    parsed_run = parsed[0].runs[0]
    assert not isinstance(parsed_run.creator.role, Unset)
    if role == "user":
        assert parsed_run.creator.role is UserRole.USER
    else:
        assert type(parsed_run.creator.role) is str
        assert parsed_run.creator.role == role
    assert not isinstance(parsed_run.task_type, Unset)
    assert parsed_run.task_type is not None
    assert type(parsed_run.task_type) is int
    assert parsed_run.task_type == 999
    assert not isinstance(parsed[0].permissions, Unset)
    assert parsed[0].permissions[0].action is ProjectAction.RENAME
    serialized = parsed[0].to_dict()
    assert serialized["runs"][0]["creator"]["role"] == role
    assert serialized["runs"][0]["task_type"] == 999
    assert serialized["permissions"] == project["permissions"]
