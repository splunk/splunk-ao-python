from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.collaborator_role import CollaboratorRole
from ..types import UNSET, Unset

T = TypeVar("T", bound="ProjectCollaboratorUpdate")


@_attrs_define
class ProjectCollaboratorUpdate:
    """
    Attributes:
        role (CollaboratorRole):
        custom_access_level_id (None | str | Unset):
    """

    role: CollaboratorRole
    custom_access_level_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        role = self.role.value

        custom_access_level_id: None | str | Unset
        if isinstance(self.custom_access_level_id, Unset):
            custom_access_level_id = UNSET
        else:
            custom_access_level_id = self.custom_access_level_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"role": role})
        if custom_access_level_id is not UNSET:
            field_dict["custom_access_level_id"] = custom_access_level_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        role = CollaboratorRole(d.pop("role"))

        def _parse_custom_access_level_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        custom_access_level_id = _parse_custom_access_level_id(d.pop("custom_access_level_id", UNSET))

        project_collaborator_update = cls(role=role, custom_access_level_id=custom_access_level_id)

        project_collaborator_update.additional_properties = d
        return project_collaborator_update

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
