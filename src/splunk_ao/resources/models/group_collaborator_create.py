from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.collaborator_role import CollaboratorRole
from ..types import UNSET, Unset

T = TypeVar("T", bound="GroupCollaboratorCreate")


@_attrs_define
class GroupCollaboratorCreate:
    """
    Attributes:
        group_id (str):
        role (CollaboratorRole | str | Unset):
    """

    group_id: str
    role: CollaboratorRole | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        group_id = self.group_id

        role: str | Unset
        if isinstance(self.role, Unset):
            role = UNSET
        elif isinstance(self.role, CollaboratorRole):
            role = self.role.value
        else:
            role = self.role

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"group_id": group_id})
        if role is not UNSET:
            field_dict["role"] = role

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        group_id = d.pop("group_id")

        def _parse_role(data: object) -> CollaboratorRole | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                role_type_0 = CollaboratorRole(data)

                return role_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for role")
            return cast(CollaboratorRole | str | Unset, data)

        role = _parse_role(d.pop("role", UNSET))

        group_collaborator_create = cls(group_id=group_id, role=role)

        group_collaborator_create.additional_properties = d
        return group_collaborator_create

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
