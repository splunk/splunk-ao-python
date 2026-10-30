from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.run_created_by_filter_operator import RunCreatedByFilterOperator
from ..types import UNSET, Unset

T = TypeVar("T", bound="RunCreatedByFilter")


@_attrs_define
class RunCreatedByFilter:
    """
    Attributes:
        value (list[str] | str):
        name (Literal['created_by'] | Unset):  Default: 'created_by'.
        operator (RunCreatedByFilterOperator | str | Unset):  Default: RunCreatedByFilterOperator.EQ.
    """

    value: list[str] | str
    name: Literal["created_by"] | Unset = "created_by"
    operator: RunCreatedByFilterOperator | str | Unset = RunCreatedByFilterOperator.EQ
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value: list[str] | str
        if isinstance(self.value, list):
            value = []
            for value_type_1_item_data in self.value:
                value_type_1_item: str
                value_type_1_item = value_type_1_item_data
                value.append(value_type_1_item)

        else:
            value = self.value

        name = self.name

        operator: str | Unset
        if isinstance(self.operator, Unset):
            operator = UNSET
        elif isinstance(self.operator, RunCreatedByFilterOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"value": value})
        if name is not UNSET:
            field_dict["name"] = name
        if operator is not UNSET:
            field_dict["operator"] = operator

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_value(data: object) -> list[str] | str:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                value_type_1 = []
                _value_type_1 = data
                for value_type_1_item_data in _value_type_1:

                    def _parse_value_type_1_item(data: object) -> str:
                        return cast(str, data)

                    value_type_1_item = _parse_value_type_1_item(value_type_1_item_data)

                    value_type_1.append(value_type_1_item)

                return value_type_1
            except:  # noqa: E722
                pass
            return cast(list[str] | str, data)

        value = _parse_value(d.pop("value"))

        name = cast(Literal["created_by"] | Unset, d.pop("name", UNSET))
        if name != "created_by" and not isinstance(name, Unset):
            raise ValueError(f"name must match const 'created_by', got '{name}'")

        def _parse_operator(data: object) -> RunCreatedByFilterOperator | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = RunCreatedByFilterOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(RunCreatedByFilterOperator | str | Unset, data)

        operator = _parse_operator(d.pop("operator", UNSET))

        run_created_by_filter = cls(value=value, name=name, operator=operator)

        run_created_by_filter.additional_properties = d
        return run_created_by_filter

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
