from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_dataset_preview_column import LunaDatasetPreviewColumn
    from ..models.luna_dataset_preview_row import LunaDatasetPreviewRow
    from ..models.luna_preview_draft_ref import LunaPreviewDraftRef
    from ..models.luna_preview_version_ref import LunaPreviewVersionRef


T = TypeVar("T", bound="LunaDatasetPreview")


@_attrs_define
class LunaDatasetPreview:
    """
    Attributes:
        dataset (LunaPreviewDraftRef | LunaPreviewVersionRef):
        columns (list[LunaDatasetPreviewColumn]):
        rows (list[LunaDatasetPreviewRow]):
        total_row_count (int):
        column_count (int):
        next_cursor (None | str | Unset):
    """

    dataset: LunaPreviewDraftRef | LunaPreviewVersionRef
    columns: list[LunaDatasetPreviewColumn]
    rows: list[LunaDatasetPreviewRow]
    total_row_count: int
    column_count: int
    next_cursor: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.luna_preview_draft_ref import LunaPreviewDraftRef

        dataset: dict[str, Any]
        if isinstance(self.dataset, LunaPreviewDraftRef):
            dataset = self.dataset.to_dict()
        else:
            dataset = self.dataset.to_dict()

        columns = []
        for columns_item_data in self.columns:
            columns_item = columns_item_data.to_dict()
            columns.append(columns_item)

        rows = []
        for rows_item_data in self.rows:
            rows_item = rows_item_data.to_dict()
            rows.append(rows_item)

        total_row_count = self.total_row_count

        column_count = self.column_count

        next_cursor: None | str | Unset
        if isinstance(self.next_cursor, Unset):
            next_cursor = UNSET
        else:
            next_cursor = self.next_cursor

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "dataset": dataset,
                "columns": columns,
                "rows": rows,
                "total_row_count": total_row_count,
                "column_count": column_count,
            }
        )
        if next_cursor is not UNSET:
            field_dict["next_cursor"] = next_cursor

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_preview_column import LunaDatasetPreviewColumn
        from ..models.luna_dataset_preview_row import LunaDatasetPreviewRow
        from ..models.luna_preview_draft_ref import LunaPreviewDraftRef
        from ..models.luna_preview_version_ref import LunaPreviewVersionRef

        d = dict(src_dict)

        def _parse_dataset(data: object) -> LunaPreviewDraftRef | LunaPreviewVersionRef:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                dataset_type_0 = LunaPreviewDraftRef.from_dict(data)

                return dataset_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            dataset_type_1 = LunaPreviewVersionRef.from_dict(data)

            return dataset_type_1

        dataset = _parse_dataset(d.pop("dataset"))

        columns = []
        _columns = d.pop("columns")
        for columns_item_data in _columns:
            columns_item = LunaDatasetPreviewColumn.from_dict(columns_item_data)

            columns.append(columns_item)

        rows = []
        _rows = d.pop("rows")
        for rows_item_data in _rows:
            rows_item = LunaDatasetPreviewRow.from_dict(rows_item_data)

            rows.append(rows_item)

        total_row_count = d.pop("total_row_count")

        column_count = d.pop("column_count")

        def _parse_next_cursor(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        next_cursor = _parse_next_cursor(d.pop("next_cursor", UNSET))

        luna_dataset_preview = cls(
            dataset=dataset,
            columns=columns,
            rows=rows,
            total_row_count=total_row_count,
            column_count=column_count,
            next_cursor=next_cursor,
        )

        luna_dataset_preview.additional_properties = d
        return luna_dataset_preview

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
