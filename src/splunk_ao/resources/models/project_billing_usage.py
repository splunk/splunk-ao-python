from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.billing_usage_data_point import BillingUsageDataPoint


T = TypeVar("T", bound="ProjectBillingUsage")


@_attrs_define
class ProjectBillingUsage:
    """
    Attributes:
        project_id (str):
        project_name (str):
        total (Union[Unset, int]):  Default: 0.
        data_points (Union[Unset, list['BillingUsageDataPoint']]):
    """

    project_id: str
    project_name: str
    total: Union[Unset, int] = 0
    data_points: Union[Unset, list["BillingUsageDataPoint"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        project_id = self.project_id

        project_name = self.project_name

        total = self.total

        data_points: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.data_points, Unset):
            data_points = []
            for data_points_item_data in self.data_points:
                data_points_item = data_points_item_data.to_dict()
                data_points.append(data_points_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"project_id": project_id, "project_name": project_name})
        if total is not UNSET:
            field_dict["total"] = total
        if data_points is not UNSET:
            field_dict["data_points"] = data_points

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.billing_usage_data_point import BillingUsageDataPoint

        d = dict(src_dict)
        project_id = d.pop("project_id")

        project_name = d.pop("project_name")

        total = d.pop("total", UNSET)

        data_points = []
        _data_points = d.pop("data_points", UNSET)
        for data_points_item_data in _data_points or []:
            data_points_item = BillingUsageDataPoint.from_dict(data_points_item_data)

            data_points.append(data_points_item)

        project_billing_usage = cls(
            project_id=project_id, project_name=project_name, total=total, data_points=data_points
        )

        project_billing_usage.additional_properties = d
        return project_billing_usage

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
