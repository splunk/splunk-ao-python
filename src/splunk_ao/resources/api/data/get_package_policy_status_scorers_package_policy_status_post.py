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
from ...models.code_metric_policy_status_request import CodeMetricPolicyStatusRequest
from ...models.code_metric_policy_status_response import CodeMetricPolicyStatusResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(*, body: CodeMetricPolicyStatusRequest) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": RequestMethod.POST,
        "return_raw_response": True,
        "path": "/scorers/package-policy-status",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    headers["Splunk-AO-SDK"] = get_sdk_header()
    headers["X-Galileo-Scorer-Capabilities"] = get_scorer_capabilities_header()

    _kwargs["content_headers"] = headers
    return _kwargs


def _parse_response(
    *, client: ApiClient, response: httpx.Response
) -> CodeMetricPolicyStatusResponse | HTTPValidationError:
    if response.status_code == 200:
        response_200 = CodeMetricPolicyStatusResponse.from_dict(response.json())

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
) -> Response[CodeMetricPolicyStatusResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *, client: ApiClient, body: CodeMetricPolicyStatusRequest
) -> Response[CodeMetricPolicyStatusResponse | HTTPValidationError]:
    """Get Package Policy Status

     The code-metric package-policy state of each listed code metric that has one and that the caller can
    read.

    Args:
        body (CodeMetricPolicyStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CodeMetricPolicyStatusResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(body=body)

    response = client.request(**kwargs)

    return _build_response(client=client, response=response)


def sync(
    *, client: ApiClient, body: CodeMetricPolicyStatusRequest
) -> Optional[CodeMetricPolicyStatusResponse | HTTPValidationError]:
    """Get Package Policy Status

     The code-metric package-policy state of each listed code metric that has one and that the caller can
    read.

    Args:
        body (CodeMetricPolicyStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CodeMetricPolicyStatusResponse | HTTPValidationError
    """

    return sync_detailed(client=client, body=body).parsed


async def asyncio_detailed(
    *, client: ApiClient, body: CodeMetricPolicyStatusRequest
) -> Response[CodeMetricPolicyStatusResponse | HTTPValidationError]:
    """Get Package Policy Status

     The code-metric package-policy state of each listed code metric that has one and that the caller can
    read.

    Args:
        body (CodeMetricPolicyStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CodeMetricPolicyStatusResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(body=body)

    response = await client.arequest(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *, client: ApiClient, body: CodeMetricPolicyStatusRequest
) -> Optional[CodeMetricPolicyStatusResponse | HTTPValidationError]:
    """Get Package Policy Status

     The code-metric package-policy state of each listed code metric that has one and that the caller can
    read.

    Args:
        body (CodeMetricPolicyStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CodeMetricPolicyStatusResponse | HTTPValidationError
    """

    return (await asyncio_detailed(client=client, body=body)).parsed
