from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="LunaDatasetPreviewColumn")


@_attrs_define
class LunaDatasetPreviewColumn:
    """
    Attributes:
        key (str):
        label (str):
        source_columns (list[str]):
        source_column (None | str | Unset):
        samples (list[Any] | Unset):
        group (None | str | Unset):
        scorer_id (None | str | Unset):
    """

    key: str
    label: str
    source_columns: list[str]
    source_column: None | str | Unset = UNSET
    samples: list[Any] | Unset = UNSET
    group: None | str | Unset = UNSET
    scorer_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        key = self.key

        label = self.label

        source_columns = self.source_columns

        source_column: None | str | Unset
        if isinstance(self.source_column, Unset):
            source_column = UNSET
        else:
            source_column = self.source_column

        samples: list[Any] | Unset = UNSET
        if not isinstance(self.samples, Unset):
            samples = self.samples

        group: None | str | Unset
        if isinstance(self.group, Unset):
            group = UNSET
        else:
            group = self.group

        scorer_id: None | str | Unset
        if isinstance(self.scorer_id, Unset):
            scorer_id = UNSET
        else:
            scorer_id = self.scorer_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"key": key, "label": label, "source_columns": source_columns})
        if source_column is not UNSET:
            field_dict["source_column"] = source_column
        if samples is not UNSET:
            field_dict["samples"] = samples
        if group is not UNSET:
            field_dict["group"] = group
        if scorer_id is not UNSET:
            field_dict["scorer_id"] = scorer_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        key = d.pop("key")

        label = d.pop("label")

        source_columns = cast(list[str], d.pop("source_columns"))

        def _parse_source_column(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source_column = _parse_source_column(d.pop("source_column", UNSET))

        samples = cast(list[Any], d.pop("samples", UNSET))

        def _parse_group(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        group = _parse_group(d.pop("group", UNSET))

        def _parse_scorer_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scorer_id = _parse_scorer_id(d.pop("scorer_id", UNSET))

        luna_dataset_preview_column = cls(
            key=key,
            label=label,
            source_columns=source_columns,
            source_column=source_column,
            samples=samples,
            group=group,
            scorer_id=scorer_id,
        )

        luna_dataset_preview_column.additional_properties = d
        return luna_dataset_preview_column

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
