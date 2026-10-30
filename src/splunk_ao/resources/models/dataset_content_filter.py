from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.dataset_content_filter_operator import DatasetContentFilterOperator
from ..types import UNSET, Unset

T = TypeVar("T", bound="DatasetContentFilter")


@_attrs_define
class DatasetContentFilter:
    """
    Attributes:
        column_name (str):
        value (str):
        operator (DatasetContentFilterOperator | str | Unset):
    """

    column_name: str
    value: str
    operator: DatasetContentFilterOperator | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        column_name = self.column_name

        value = self.value

        operator: str | Unset
        if isinstance(self.operator, Unset):
            operator = UNSET
        elif isinstance(self.operator, DatasetContentFilterOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"column_name": column_name, "value": value})
        if operator is not UNSET:
            field_dict["operator"] = operator

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        column_name = d.pop("column_name")

        value = d.pop("value")

        def _parse_operator(data: object) -> DatasetContentFilterOperator | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = DatasetContentFilterOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(DatasetContentFilterOperator | str | Unset, data)

        operator = _parse_operator(d.pop("operator", UNSET))

        dataset_content_filter = cls(column_name=column_name, value=value, operator=operator)

        dataset_content_filter.additional_properties = d
        return dataset_content_filter

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
