from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.billing_usage_metric import BillingUsageMetric
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.project_billing_usage import ProjectBillingUsage


T = TypeVar("T", bound="BillingUsageResponse")


@_attrs_define
class BillingUsageResponse:
    """
    Attributes:
        metric (BillingUsageMetric):
        total (int | Unset):  Default: 0.
        projects (list[ProjectBillingUsage] | Unset):
        available (bool | Unset):  Default: True.
        unavailable_reason (None | str | Unset):
    """

    metric: BillingUsageMetric
    total: int | Unset = 0
    projects: list[ProjectBillingUsage] | Unset = UNSET
    available: bool | Unset = True
    unavailable_reason: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        metric = self.metric.value

        total = self.total

        projects: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.projects, Unset):
            projects = []
            for projects_item_data in self.projects:
                projects_item = projects_item_data.to_dict()
                projects.append(projects_item)

        available = self.available

        unavailable_reason: None | str | Unset
        if isinstance(self.unavailable_reason, Unset):
            unavailable_reason = UNSET
        else:
            unavailable_reason = self.unavailable_reason

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"metric": metric})
        if total is not UNSET:
            field_dict["total"] = total
        if projects is not UNSET:
            field_dict["projects"] = projects
        if available is not UNSET:
            field_dict["available"] = available
        if unavailable_reason is not UNSET:
            field_dict["unavailable_reason"] = unavailable_reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.project_billing_usage import ProjectBillingUsage

        d = dict(src_dict)
        metric = BillingUsageMetric(d.pop("metric"))

        total = d.pop("total", UNSET)

        _projects = d.pop("projects", UNSET)
        projects: list[ProjectBillingUsage] | Unset = UNSET
        if _projects is not UNSET:
            projects = []
            for projects_item_data in _projects:
                projects_item = ProjectBillingUsage.from_dict(projects_item_data)

                projects.append(projects_item)

        available = d.pop("available", UNSET)

        def _parse_unavailable_reason(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        unavailable_reason = _parse_unavailable_reason(d.pop("unavailable_reason", UNSET))

        billing_usage_response = cls(
            metric=metric, total=total, projects=projects, available=available, unavailable_reason=unavailable_reason
        )

        billing_usage_response.additional_properties = d
        return billing_usage_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
