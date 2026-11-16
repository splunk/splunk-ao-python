from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="LunaPreviewDraftRef")


@_attrs_define
class LunaPreviewDraftRef:
    """
    Attributes:
        dataset_id (str):
        draft_revision (str):
        kind (Literal['draft'] | Unset):  Default: 'draft'.
    """

    dataset_id: str
    draft_revision: str
    kind: Literal["draft"] | Unset = "draft"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        dataset_id = self.dataset_id

        draft_revision = self.draft_revision

        kind = self.kind

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"dataset_id": dataset_id, "draft_revision": draft_revision})
        if kind is not UNSET:
            field_dict["kind"] = kind

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        dataset_id = d.pop("dataset_id")

        draft_revision = d.pop("draft_revision")

        kind = cast(Literal["draft"] | Unset, d.pop("kind", UNSET))
        if kind != "draft" and not isinstance(kind, Unset):
            raise ValueError(f"kind must match const 'draft', got '{kind}'")

        luna_preview_draft_ref = cls(dataset_id=dataset_id, draft_revision=draft_revision, kind=kind)

        luna_preview_draft_ref.additional_properties = d
        return luna_preview_draft_ref

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
