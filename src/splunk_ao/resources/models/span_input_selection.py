from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.span_input_selection_fields_item import SpanInputSelectionFieldsItem
from ..types import UNSET, Unset

T = TypeVar("T", bound="SpanInputSelection")


@_attrs_define
class SpanInputSelection:
    """Select the input fields included for spans with this name.

    Attributes:
        span_name (str):
        fields (list[SpanInputSelectionFieldsItem] | Unset):
    """

    span_name: str
    fields: list[SpanInputSelectionFieldsItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        span_name = self.span_name

        fields: list[str] | Unset = UNSET
        if not isinstance(self.fields, Unset):
            fields = []
            for fields_item_data in self.fields:
                fields_item = fields_item_data.value
                fields.append(fields_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"span_name": span_name})
        if fields is not UNSET:
            field_dict["fields"] = fields

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        span_name = d.pop("span_name")

        _fields = d.pop("fields", UNSET)
        fields: list[SpanInputSelectionFieldsItem] | Unset = UNSET
        if _fields is not UNSET:
            fields = []
            for fields_item_data in _fields:
                fields_item = SpanInputSelectionFieldsItem(fields_item_data)

                fields.append(fields_item)

        span_input_selection = cls(span_name=span_name, fields=fields)

        span_input_selection.additional_properties = d
        return span_input_selection

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
