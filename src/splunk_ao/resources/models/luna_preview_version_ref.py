from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="LunaPreviewVersionRef")


@_attrs_define
class LunaPreviewVersionRef:
    """
    Attributes:
        dataset_id (str):
        version_index (int):
        kind (Literal['version'] | Unset):  Default: 'version'.
    """

    dataset_id: str
    version_index: int
    kind: Literal["version"] | Unset = "version"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        dataset_id = self.dataset_id

        version_index = self.version_index

        kind = self.kind

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"dataset_id": dataset_id, "version_index": version_index})
        if kind is not UNSET:
            field_dict["kind"] = kind

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        dataset_id = d.pop("dataset_id")

        version_index = d.pop("version_index")

        kind = cast(Literal["version"] | Unset, d.pop("kind", UNSET))
        if kind != "version" and not isinstance(kind, Unset):
            raise ValueError(f"kind must match const 'version', got '{kind}'")

        luna_preview_version_ref = cls(dataset_id=dataset_id, version_index=version_index, kind=kind)

        luna_preview_version_ref.additional_properties = d
        return luna_preview_version_ref

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
