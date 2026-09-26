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
from ...models.generated_scorer_validation_response import GeneratedScorerValidationResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": RequestMethod.POST,
        "return_raw_response": True,
        "path": "/scorers/llm/validate",
    }

    headers["Splunk-AO-SDK"] = get_sdk_header()

    _kwargs["content_headers"] = headers
    return _kwargs


def _parse_response(*, client: ApiClient, response: httpx.Response) -> GeneratedScorerValidationResponse:
    if response.status_code == 200:
        response_200 = GeneratedScorerValidationResponse.from_dict(response.json())

        return response_200

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


def _build_response(*, client: ApiClient, response: httpx.Response) -> Response[GeneratedScorerValidationResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(*, client: ApiClient) -> Response[GeneratedScorerValidationResponse]:
    """Manual Llm Validate

     Validate an LLM scorer manually, with query/response passed inline (no file uploads).

    Args:
        request: Raw request; body is parsed into a GeneratedScorerValidationRequest.
        ctx: Async request context with the authenticated user and read session.

    Returns:
        A pending task result the caller can poll for validation results.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GeneratedScorerValidationResponse]
    """

    kwargs = _get_kwargs()

    response = client.request(**kwargs)

    return _build_response(client=client, response=response)


def sync(*, client: ApiClient) -> Optional[GeneratedScorerValidationResponse]:
    """Manual Llm Validate

     Validate an LLM scorer manually, with query/response passed inline (no file uploads).

    Args:
        request: Raw request; body is parsed into a GeneratedScorerValidationRequest.
        ctx: Async request context with the authenticated user and read session.

    Returns:
        A pending task result the caller can poll for validation results.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GeneratedScorerValidationResponse
    """

    return sync_detailed(client=client).parsed


async def asyncio_detailed(*, client: ApiClient) -> Response[GeneratedScorerValidationResponse]:
    """Manual Llm Validate

     Validate an LLM scorer manually, with query/response passed inline (no file uploads).

    Args:
        request: Raw request; body is parsed into a GeneratedScorerValidationRequest.
        ctx: Async request context with the authenticated user and read session.

    Returns:
        A pending task result the caller can poll for validation results.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GeneratedScorerValidationResponse]
    """

    kwargs = _get_kwargs()

    response = await client.arequest(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(*, client: ApiClient) -> Optional[GeneratedScorerValidationResponse]:
    """Manual Llm Validate

     Validate an LLM scorer manually, with query/response passed inline (no file uploads).

    Args:
        request: Raw request; body is parsed into a GeneratedScorerValidationRequest.
        ctx: Async request context with the authenticated user and read session.

    Returns:
        A pending task result the caller can poll for validation results.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GeneratedScorerValidationResponse
    """

    return (await asyncio_detailed(client=client)).parsed
