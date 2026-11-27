from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.code_metric_policy_status import CodeMetricPolicyStatus


T = TypeVar("T", bound="CodeMetricPolicyNoticesResponse")


@_attrs_define
class CodeMetricPolicyNoticesResponse:
    """
    Attributes:
        notices (list[CodeMetricPolicyStatus]):
        total (int):
    """

    notices: list[CodeMetricPolicyStatus]
    total: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        notices = []
        for notices_item_data in self.notices:
            notices_item = notices_item_data.to_dict()
            notices.append(notices_item)

        total = self.total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"notices": notices, "total": total})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.code_metric_policy_status import CodeMetricPolicyStatus

        d = dict(src_dict)
        notices = []
        _notices = d.pop("notices")
        for notices_item_data in _notices:
            notices_item = CodeMetricPolicyStatus.from_dict(notices_item_data)

            notices.append(notices_item)

        total = d.pop("total")

        code_metric_policy_notices_response = cls(notices=notices, total=total)

        code_metric_policy_notices_response.additional_properties = d
        return code_metric_policy_notices_response

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
