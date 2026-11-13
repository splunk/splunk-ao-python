from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_dataset_preview_row_values import LunaDatasetPreviewRowValues


T = TypeVar("T", bound="LunaDatasetPreviewRow")


@_attrs_define
class LunaDatasetPreviewRow:
    """
    Attributes:
        row_ref (str):
        values (LunaDatasetPreviewRowValues):
        truncated_columns (list[str] | Unset):
    """

    row_ref: str
    values: LunaDatasetPreviewRowValues
    truncated_columns: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        row_ref = self.row_ref

        values = self.values.to_dict()

        truncated_columns: list[str] | Unset = UNSET
        if not isinstance(self.truncated_columns, Unset):
            truncated_columns = self.truncated_columns

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"row_ref": row_ref, "values": values})
        if truncated_columns is not UNSET:
            field_dict["truncated_columns"] = truncated_columns

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_preview_row_values import LunaDatasetPreviewRowValues

        d = dict(src_dict)
        row_ref = d.pop("row_ref")

        values = LunaDatasetPreviewRowValues.from_dict(d.pop("values"))

        truncated_columns = cast(list[str], d.pop("truncated_columns", UNSET))

        luna_dataset_preview_row = cls(row_ref=row_ref, values=values, truncated_columns=truncated_columns)

        luna_dataset_preview_row.additional_properties = d
        return luna_dataset_preview_row

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
