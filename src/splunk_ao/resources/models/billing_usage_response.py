from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

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
        total (Union[Unset, int]):  Default: 0.
        projects (Union[Unset, list['ProjectBillingUsage']]):
        available (Union[Unset, bool]):  Default: True.
        unavailable_reason (Union[None, Unset, str]):
    """

    metric: BillingUsageMetric
    total: Union[Unset, int] = 0
    projects: Union[Unset, list["ProjectBillingUsage"]] = UNSET
    available: Union[Unset, bool] = True
    unavailable_reason: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        metric = self.metric.value

        total = self.total

        projects: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.projects, Unset):
            projects = []
            for projects_item_data in self.projects:
                projects_item = projects_item_data.to_dict()
                projects.append(projects_item)

        available = self.available

        unavailable_reason: Union[None, Unset, str]
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

        projects = []
        _projects = d.pop("projects", UNSET)
        for projects_item_data in _projects or []:
            projects_item = ProjectBillingUsage.from_dict(projects_item_data)

            projects.append(projects_item)

        available = d.pop("available", UNSET)

        def _parse_unavailable_reason(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

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
