import datetime
from http import HTTPStatus
from typing import Any, Optional
from uuid import UUID

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
from ...models.billing_usage_metric import BillingUsageMetric
from ...models.billing_usage_response import BillingUsageResponse
from ...models.cost_interval import CostInterval
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    metric: BillingUsageMetric,
    *,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    interval: CostInterval,
    project_id: None | Unset | UUID = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    json_interval = interval.value
    params["interval"] = json_interval

    json_project_id: None | str | Unset
    if isinstance(project_id, Unset):
        json_project_id = UNSET
    elif isinstance(project_id, UUID):
        json_project_id = str(project_id)
    else:
        json_project_id = project_id
    params["project_id"] = json_project_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": RequestMethod.GET,
        "return_raw_response": True,
        "path": "/billing/usage/{metric}".format(metric=metric),
        "params": params,
    }

    headers["Splunk-AO-SDK"] = get_sdk_header()

    _kwargs["content_headers"] = headers
    return _kwargs


def _parse_response(*, client: ApiClient, response: httpx.Response) -> BillingUsageResponse | HTTPValidationError:
    if response.status_code == 200:
        response_200 = BillingUsageResponse.from_dict(response.json())

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
) -> Response[BillingUsageResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    metric: BillingUsageMetric,
    *,
    client: ApiClient,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    interval: CostInterval,
    project_id: None | Unset | UUID = UNSET,
) -> Response[BillingUsageResponse | HTTPValidationError]:
    """Get Billing Usage

    Args:
        metric (BillingUsageMetric):
        start_time (datetime.datetime): Start of time range (UTC)
        end_time (datetime.datetime): End of time range (UTC)
        interval (CostInterval):
        project_id (None | Unset | UUID): Optional project filter

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BillingUsageResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        metric=metric, start_time=start_time, end_time=end_time, interval=interval, project_id=project_id
    )

    response = client.request(**kwargs)

    return _build_response(client=client, response=response)


def sync(
    metric: BillingUsageMetric,
    *,
    client: ApiClient,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    interval: CostInterval,
    project_id: None | Unset | UUID = UNSET,
) -> Optional[BillingUsageResponse | HTTPValidationError]:
    """Get Billing Usage

    Args:
        metric (BillingUsageMetric):
        start_time (datetime.datetime): Start of time range (UTC)
        end_time (datetime.datetime): End of time range (UTC)
        interval (CostInterval):
        project_id (None | Unset | UUID): Optional project filter

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BillingUsageResponse | HTTPValidationError
    """

    return sync_detailed(
        metric=metric, client=client, start_time=start_time, end_time=end_time, interval=interval, project_id=project_id
    ).parsed


async def asyncio_detailed(
    metric: BillingUsageMetric,
    *,
    client: ApiClient,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    interval: CostInterval,
    project_id: None | Unset | UUID = UNSET,
) -> Response[BillingUsageResponse | HTTPValidationError]:
    """Get Billing Usage

    Args:
        metric (BillingUsageMetric):
        start_time (datetime.datetime): Start of time range (UTC)
        end_time (datetime.datetime): End of time range (UTC)
        interval (CostInterval):
        project_id (None | Unset | UUID): Optional project filter

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[BillingUsageResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        metric=metric, start_time=start_time, end_time=end_time, interval=interval, project_id=project_id
    )

    response = await client.arequest(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    metric: BillingUsageMetric,
    *,
    client: ApiClient,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    interval: CostInterval,
    project_id: None | Unset | UUID = UNSET,
) -> Optional[BillingUsageResponse | HTTPValidationError]:
    """Get Billing Usage

    Args:
        metric (BillingUsageMetric):
        start_time (datetime.datetime): Start of time range (UTC)
        end_time (datetime.datetime): End of time range (UTC)
        interval (CostInterval):
        project_id (None | Unset | UUID): Optional project filter

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        BillingUsageResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            metric=metric,
            client=client,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            project_id=project_id,
        )
    ).parsed
