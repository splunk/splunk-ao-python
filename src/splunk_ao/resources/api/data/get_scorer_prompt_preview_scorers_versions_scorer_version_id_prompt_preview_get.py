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
from splunk_ao.utils.headers_data import get_scorer_capabilities_header, get_sdk_header

from ... import errors
from ...models.http_validation_error import HTTPValidationError
from ...models.scorer_prompt_preview_response import ScorerPromptPreviewResponse
from ...models.scorer_prompt_preview_unavailable_response import ScorerPromptPreviewUnavailableResponse
from ...types import UNSET, Response


def _get_kwargs(scorer_version_id: str, *, project_id: str, run_id: str, record_id: str) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["project_id"] = project_id

    params["run_id"] = run_id

    params["record_id"] = record_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": RequestMethod.GET,
        "return_raw_response": True,
        "path": "/scorers/versions/{scorer_version_id}/prompt-preview".format(scorer_version_id=scorer_version_id),
        "params": params,
    }

    headers["Splunk-AO-SDK"] = get_sdk_header()
    headers["X-Galileo-Scorer-Capabilities"] = get_scorer_capabilities_header()

    _kwargs["content_headers"] = headers
    return _kwargs


def _parse_response(
    *, client: ApiClient, response: httpx.Response
) -> HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = ScorerPromptPreviewResponse.from_dict(data)

                return response_200_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_1 = ScorerPromptPreviewUnavailableResponse.from_dict(data)

            return response_200_type_1

        response_200 = _parse_response_200(response.json())

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
) -> Response[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    scorer_version_id: str, *, client: ApiClient, project_id: str, run_id: str, record_id: str
) -> Response[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]:
    """Get Scorer Prompt Preview

     Return this version's prompt using the run's effective scorer settings.

    Args:
        scorer_version_id (str):
        project_id (str):
        run_id (str):
        record_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]
    """

    kwargs = _get_kwargs(scorer_version_id=scorer_version_id, project_id=project_id, run_id=run_id, record_id=record_id)

    response = client.request(**kwargs)

    return _build_response(client=client, response=response)


def sync(
    scorer_version_id: str, *, client: ApiClient, project_id: str, run_id: str, record_id: str
) -> Optional[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]:
    """Get Scorer Prompt Preview

     Return this version's prompt using the run's effective scorer settings.

    Args:
        scorer_version_id (str):
        project_id (str):
        run_id (str):
        record_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse
    """

    return sync_detailed(
        scorer_version_id=scorer_version_id, client=client, project_id=project_id, run_id=run_id, record_id=record_id
    ).parsed


async def asyncio_detailed(
    scorer_version_id: str, *, client: ApiClient, project_id: str, run_id: str, record_id: str
) -> Response[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]:
    """Get Scorer Prompt Preview

     Return this version's prompt using the run's effective scorer settings.

    Args:
        scorer_version_id (str):
        project_id (str):
        run_id (str):
        record_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]
    """

    kwargs = _get_kwargs(scorer_version_id=scorer_version_id, project_id=project_id, run_id=run_id, record_id=record_id)

    response = await client.arequest(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    scorer_version_id: str, *, client: ApiClient, project_id: str, run_id: str, record_id: str
) -> Optional[HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse]:
    """Get Scorer Prompt Preview

     Return this version's prompt using the run's effective scorer settings.

    Args:
        scorer_version_id (str):
        project_id (str):
        run_id (str):
        record_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ScorerPromptPreviewResponse | ScorerPromptPreviewUnavailableResponse
    """

    return (
        await asyncio_detailed(
            scorer_version_id=scorer_version_id,
            client=client,
            project_id=project_id,
            run_id=run_id,
            record_id=record_id,
        )
    ).parsed
