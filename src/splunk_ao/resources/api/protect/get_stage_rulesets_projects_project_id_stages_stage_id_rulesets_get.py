from http import HTTPStatus
from typing import Any, Optional

import httpx

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
from splunk_ao.utils.headers_data import get_sdk_header

from ... import errors
from ...models.http_validation_error import HTTPValidationError
from ...models.stage_rulesets_response import StageRulesetsResponse
from ...types import Response


def _get_kwargs(project_id: str, stage_id: str) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": RequestMethod.GET,
        "return_raw_response": True,
        "path": "/projects/{project_id}/stages/{stage_id}/rulesets".format(project_id=project_id, stage_id=stage_id),
    }

    headers["Splunk-AO-SDK"] = get_sdk_header()

    _kwargs["content_headers"] = headers
    return _kwargs


def _parse_response(*, client: ApiClient, response: httpx.Response) -> HTTPValidationError | StageRulesetsResponse:
    if response.status_code == 200:
        response_200 = StageRulesetsResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    # Handle common HTTP errors with actionable messages
    if response.status_code == 400:
        raise BadRequestError(response.status_code, response.content)
    if response.status_code == 401:
        raise AuthenticationError(response.status_code, response.content)
    if response.status_code == 403:
        raise ForbiddenError(response.status_code, response.content)
    if response.status_code == 404:
        raise NotFoundError(response.status_code, response.content)
    if response.status_code == 409:
        raise ConflictError(response.status_code, response.content)
    if response.status_code == 429:
        raise RateLimitError(response.status_code, response.content)
    if response.status_code >= 500:
        raise ServerError(response.status_code, response.content)
    raise errors.UnexpectedStatus(response.status_code, response.content)


def _build_response(
    *, client: ApiClient, response: httpx.Response
) -> Response[HTTPValidationError | StageRulesetsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    project_id: str, stage_id: str, *, client: ApiClient
) -> Response[HTTPValidationError | StageRulesetsResponse]:
    """Get Stage Rulesets

     Get the rulesets of a stage's current version, or a local stage's newest version.

    `StageDB` carries the version number but not the rulesets. This returns them, so a
    caller can export a stage's guardrails, for example to move them to Agent Control.

    For a central stage this is the version an invoke call applies when it names no
    version. A local stage has no current version: each invoke applies its own inline
    rulesets. For a local stage this returns the most recently created version, which is
    not always the set callers send now. After invokes with A, B and then A again, it is B.

    Args:
        project_id: Project the stage belongs to, resolved from the URL.
        stage_id: Stage to read.
        ctx: Async request context.

    Returns:
        The version and its rulesets. Protect stores no ruleset order, so the list order is
        not a priority.

    Raises:
        GalileoServerException: 404 if the stage belongs to a different project.

    Args:
        project_id (str):
        stage_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | StageRulesetsResponse]
    """

    kwargs = _get_kwargs(project_id=project_id, stage_id=stage_id)

    response = client.request(**kwargs)

    return _build_response(client=client, response=response)


def sync(project_id: str, stage_id: str, *, client: ApiClient) -> Optional[HTTPValidationError | StageRulesetsResponse]:
    """Get Stage Rulesets

     Get the rulesets of a stage's current version, or a local stage's newest version.

    `StageDB` carries the version number but not the rulesets. This returns them, so a
    caller can export a stage's guardrails, for example to move them to Agent Control.

    For a central stage this is the version an invoke call applies when it names no
    version. A local stage has no current version: each invoke applies its own inline
    rulesets. For a local stage this returns the most recently created version, which is
    not always the set callers send now. After invokes with A, B and then A again, it is B.

    Args:
        project_id: Project the stage belongs to, resolved from the URL.
        stage_id: Stage to read.
        ctx: Async request context.

    Returns:
        The version and its rulesets. Protect stores no ruleset order, so the list order is
        not a priority.

    Raises:
        GalileoServerException: 404 if the stage belongs to a different project.

    Args:
        project_id (str):
        stage_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | StageRulesetsResponse
    """

    return sync_detailed(project_id=project_id, stage_id=stage_id, client=client).parsed


async def asyncio_detailed(
    project_id: str, stage_id: str, *, client: ApiClient
) -> Response[HTTPValidationError | StageRulesetsResponse]:
    """Get Stage Rulesets

     Get the rulesets of a stage's current version, or a local stage's newest version.

    `StageDB` carries the version number but not the rulesets. This returns them, so a
    caller can export a stage's guardrails, for example to move them to Agent Control.

    For a central stage this is the version an invoke call applies when it names no
    version. A local stage has no current version: each invoke applies its own inline
    rulesets. For a local stage this returns the most recently created version, which is
    not always the set callers send now. After invokes with A, B and then A again, it is B.

    Args:
        project_id: Project the stage belongs to, resolved from the URL.
        stage_id: Stage to read.
        ctx: Async request context.

    Returns:
        The version and its rulesets. Protect stores no ruleset order, so the list order is
        not a priority.

    Raises:
        GalileoServerException: 404 if the stage belongs to a different project.

    Args:
        project_id (str):
        stage_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | StageRulesetsResponse]
    """

    kwargs = _get_kwargs(project_id=project_id, stage_id=stage_id)

    response = await client.arequest(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    project_id: str, stage_id: str, *, client: ApiClient
) -> Optional[HTTPValidationError | StageRulesetsResponse]:
    """Get Stage Rulesets

     Get the rulesets of a stage's current version, or a local stage's newest version.

    `StageDB` carries the version number but not the rulesets. This returns them, so a
    caller can export a stage's guardrails, for example to move them to Agent Control.

    For a central stage this is the version an invoke call applies when it names no
    version. A local stage has no current version: each invoke applies its own inline
    rulesets. For a local stage this returns the most recently created version, which is
    not always the set callers send now. After invokes with A, B and then A again, it is B.

    Args:
        project_id: Project the stage belongs to, resolved from the URL.
        stage_id: Stage to read.
        ctx: Async request context.

    Returns:
        The version and its rulesets. Protect stores no ruleset order, so the list order is
        not a priority.

    Raises:
        GalileoServerException: 404 if the stage belongs to a different project.

    Args:
        project_id (str):
        stage_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | StageRulesetsResponse
    """

    return (await asyncio_detailed(project_id=project_id, stage_id=stage_id, client=client)).parsed
