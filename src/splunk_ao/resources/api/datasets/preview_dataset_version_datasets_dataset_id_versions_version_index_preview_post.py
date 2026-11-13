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
from ...models.luna_dataset_preview import LunaDatasetPreview
from ...models.luna_dataset_preview_error_response import LunaDatasetPreviewErrorResponse
from ...models.luna_dataset_preview_request import LunaDatasetPreviewRequest
from ...types import UNSET, Response, Unset


def _get_kwargs(
    dataset_id: str,
    version_index: int,
    *,
    body: LunaDatasetPreviewRequest,
    limit: int | Unset = 10,
    cursor: None | str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["limit"] = limit

    json_cursor: None | str | Unset
    if isinstance(cursor, Unset):
        json_cursor = UNSET
    else:
        json_cursor = cursor
    params["cursor"] = json_cursor

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": RequestMethod.POST,
        "return_raw_response": True,
        "path": "/datasets/{dataset_id}/versions/{version_index}/preview".format(
            dataset_id=dataset_id, version_index=version_index
        ),
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    headers["Splunk-AO-SDK"] = get_sdk_header()

    _kwargs["content_headers"] = headers
    return _kwargs


def _parse_response(
    *, client: ApiClient, response: httpx.Response
) -> LunaDatasetPreview | LunaDatasetPreviewErrorResponse:
    if response.status_code == 200:
        response_200 = LunaDatasetPreview.from_dict(response.json())

        return response_200

    if response.status_code == 404:
        response_404 = LunaDatasetPreviewErrorResponse.from_dict(response.json())

        return response_404

    if response.status_code == 412:
        response_412 = LunaDatasetPreviewErrorResponse.from_dict(response.json())

        return response_412

    if response.status_code == 422:
        response_422 = LunaDatasetPreviewErrorResponse.from_dict(response.json())

        return response_422

    if response.status_code == 428:
        response_428 = LunaDatasetPreviewErrorResponse.from_dict(response.json())

        return response_428

    if response.status_code == 503:
        response_503 = LunaDatasetPreviewErrorResponse.from_dict(response.json())

        return response_503

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
) -> Response[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    dataset_id: str,
    version_index: int,
    *,
    client: ApiClient,
    body: LunaDatasetPreviewRequest,
    limit: int | Unset = 10,
    cursor: None | str | Unset = UNSET,
) -> Response[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]:
    """Preview Dataset Version

    Args:
        dataset_id (str):
        version_index (int):
        limit (int | Unset):  Default: 10.
        cursor (None | str | Unset):
        body (LunaDatasetPreviewRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]
    """

    kwargs = _get_kwargs(dataset_id=dataset_id, version_index=version_index, body=body, limit=limit, cursor=cursor)

    response = client.request(**kwargs)

    return _build_response(client=client, response=response)


def sync(
    dataset_id: str,
    version_index: int,
    *,
    client: ApiClient,
    body: LunaDatasetPreviewRequest,
    limit: int | Unset = 10,
    cursor: None | str | Unset = UNSET,
) -> Optional[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]:
    """Preview Dataset Version

    Args:
        dataset_id (str):
        version_index (int):
        limit (int | Unset):  Default: 10.
        cursor (None | str | Unset):
        body (LunaDatasetPreviewRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        LunaDatasetPreview | LunaDatasetPreviewErrorResponse
    """

    return sync_detailed(
        dataset_id=dataset_id, version_index=version_index, client=client, body=body, limit=limit, cursor=cursor
    ).parsed


async def asyncio_detailed(
    dataset_id: str,
    version_index: int,
    *,
    client: ApiClient,
    body: LunaDatasetPreviewRequest,
    limit: int | Unset = 10,
    cursor: None | str | Unset = UNSET,
) -> Response[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]:
    """Preview Dataset Version

    Args:
        dataset_id (str):
        version_index (int):
        limit (int | Unset):  Default: 10.
        cursor (None | str | Unset):
        body (LunaDatasetPreviewRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]
    """

    kwargs = _get_kwargs(dataset_id=dataset_id, version_index=version_index, body=body, limit=limit, cursor=cursor)

    response = await client.arequest(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    dataset_id: str,
    version_index: int,
    *,
    client: ApiClient,
    body: LunaDatasetPreviewRequest,
    limit: int | Unset = 10,
    cursor: None | str | Unset = UNSET,
) -> Optional[LunaDatasetPreview | LunaDatasetPreviewErrorResponse]:
    """Preview Dataset Version

    Args:
        dataset_id (str):
        version_index (int):
        limit (int | Unset):  Default: 10.
        cursor (None | str | Unset):
        body (LunaDatasetPreviewRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        LunaDatasetPreview | LunaDatasetPreviewErrorResponse
    """

    return (
        await asyncio_detailed(
            dataset_id=dataset_id, version_index=version_index, client=client, body=body, limit=limit, cursor=cursor
        )
    ).parsed
