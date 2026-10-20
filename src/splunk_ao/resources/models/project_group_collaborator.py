from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.collaborator_role import CollaboratorRole
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.permission import Permission
    from ..models.project_custom_access_level_summary import ProjectCustomAccessLevelSummary


T = TypeVar("T", bound="ProjectGroupCollaborator")


@_attrs_define
class ProjectGroupCollaborator:
    """
    Attributes:
        id (str):
        role (CollaboratorRole):
        created_at (datetime.datetime):
        group_id (str):
        group_name (str):
        permissions (list[Permission] | Unset):
        custom_access_level_id (None | str | Unset):
        custom_access_level (None | ProjectCustomAccessLevelSummary | Unset):
    """

    id: str
    role: CollaboratorRole
    created_at: datetime.datetime
    group_id: str
    group_name: str
    permissions: list[Permission] | Unset = UNSET
    custom_access_level_id: None | str | Unset = UNSET
    custom_access_level: None | ProjectCustomAccessLevelSummary | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.project_custom_access_level_summary import ProjectCustomAccessLevelSummary

        id = self.id

        role = self.role.value

        created_at = self.created_at.isoformat()

        group_id = self.group_id

        group_name = self.group_name

        permissions: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.permissions, Unset):
            permissions = []
            for permissions_item_data in self.permissions:
                permissions_item = permissions_item_data.to_dict()
                permissions.append(permissions_item)

        custom_access_level_id: None | str | Unset
        if isinstance(self.custom_access_level_id, Unset):
            custom_access_level_id = UNSET
        else:
            custom_access_level_id = self.custom_access_level_id

        custom_access_level: dict[str, Any] | None | Unset
        if isinstance(self.custom_access_level, Unset):
            custom_access_level = UNSET
        elif isinstance(self.custom_access_level, ProjectCustomAccessLevelSummary):
            custom_access_level = self.custom_access_level.to_dict()
        else:
            custom_access_level = self.custom_access_level

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {"id": id, "role": role, "created_at": created_at, "group_id": group_id, "group_name": group_name}
        )
        if permissions is not UNSET:
            field_dict["permissions"] = permissions
        if custom_access_level_id is not UNSET:
            field_dict["custom_access_level_id"] = custom_access_level_id
        if custom_access_level is not UNSET:
            field_dict["custom_access_level"] = custom_access_level

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.permission import Permission
        from ..models.project_custom_access_level_summary import ProjectCustomAccessLevelSummary

        d = dict(src_dict)
        id = d.pop("id")

        role = CollaboratorRole(d.pop("role"))

        created_at = datetime.datetime.fromisoformat(d.pop("created_at"))

        group_id = d.pop("group_id")

        group_name = d.pop("group_name")

        _permissions = d.pop("permissions", UNSET)
        permissions: list[Permission] | Unset = UNSET
        if _permissions is not UNSET:
            permissions = []
            for permissions_item_data in _permissions:
                permissions_item = Permission.from_dict(permissions_item_data)

                permissions.append(permissions_item)

        def _parse_custom_access_level_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        custom_access_level_id = _parse_custom_access_level_id(d.pop("custom_access_level_id", UNSET))

        def _parse_custom_access_level(data: object) -> None | ProjectCustomAccessLevelSummary | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                custom_access_level_type_0 = ProjectCustomAccessLevelSummary.from_dict(data)

                return custom_access_level_type_0
            except:  # noqa: E722
                pass
            return cast(None | ProjectCustomAccessLevelSummary | Unset, data)

        custom_access_level = _parse_custom_access_level(d.pop("custom_access_level", UNSET))

        project_group_collaborator = cls(
            id=id,
            role=role,
            created_at=created_at,
            group_id=group_id,
            group_name=group_name,
            permissions=permissions,
            custom_access_level_id=custom_access_level_id,
            custom_access_level=custom_access_level,
        )

        project_group_collaborator.additional_properties = d
        return project_group_collaborator

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
