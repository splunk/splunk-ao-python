from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="MetricPending")


@_attrs_define
class MetricPending:
    """
    Attributes:
        status_type (Literal['pending'] | Unset):  Default: 'pending'.
        metric_key_alias (None | str | Unset):
    """

    status_type: Literal["pending"] | Unset = "pending"
    metric_key_alias: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status_type = self.status_type

        metric_key_alias: None | str | Unset
        if isinstance(self.metric_key_alias, Unset):
            metric_key_alias = UNSET
        else:
            metric_key_alias = self.metric_key_alias

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status_type is not UNSET:
            field_dict["status_type"] = status_type
        if metric_key_alias is not UNSET:
            field_dict["metric_key_alias"] = metric_key_alias

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status_type = cast(Literal["pending"] | Unset, d.pop("status_type", UNSET))
        if status_type != "pending" and not isinstance(status_type, Unset):
            raise ValueError(f"status_type must match const 'pending', got '{status_type}'")

        def _parse_metric_key_alias(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        metric_key_alias = _parse_metric_key_alias(d.pop("metric_key_alias", UNSET))

        metric_pending = cls(status_type=status_type, metric_key_alias=metric_key_alias)

        metric_pending.additional_properties = d
        return metric_pending

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
