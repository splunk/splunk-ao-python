from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.log_records_id_filter_operator import LogRecordsIDFilterOperator
from ..types import UNSET, Unset

T = TypeVar("T", bound="LogRecordsIDFilter")


@_attrs_define
class LogRecordsIDFilter:
    """
    Attributes:
        column_id (str): ID of the column to filter.
        value (list[str] | str):
        operator (LogRecordsIDFilterOperator | str | Unset):  Default: LogRecordsIDFilterOperator.EQ.
        type_ (Literal['id'] | Unset):  Default: 'id'.
    """

    column_id: str
    value: list[str] | str
    operator: LogRecordsIDFilterOperator | str | Unset = LogRecordsIDFilterOperator.EQ
    type_: Literal["id"] | Unset = "id"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        column_id = self.column_id

        value: list[str] | str
        if isinstance(self.value, list):
            value = []
            for value_type_1_item_data in self.value:
                value_type_1_item: str
                value_type_1_item = value_type_1_item_data
                value.append(value_type_1_item)

        else:
            value = self.value

        operator: str | Unset
        if isinstance(self.operator, Unset):
            operator = UNSET
        elif isinstance(self.operator, LogRecordsIDFilterOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"column_id": column_id, "value": value})
        if operator is not UNSET:
            field_dict["operator"] = operator
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        column_id = d.pop("column_id")

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

        def _parse_operator(data: object) -> LogRecordsIDFilterOperator | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = LogRecordsIDFilterOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(LogRecordsIDFilterOperator | str | Unset, data)

        operator = _parse_operator(d.pop("operator", UNSET))

        type_ = cast(Literal["id"] | Unset, d.pop("type", UNSET))
        if type_ != "id" and not isinstance(type_, Unset):
            raise ValueError(f"type must match const 'id', got '{type_}'")

        log_records_id_filter = cls(column_id=column_id, value=value, operator=operator, type_=type_)

        log_records_id_filter.additional_properties = d
        return log_records_id_filter

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
