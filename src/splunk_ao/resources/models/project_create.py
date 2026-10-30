from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.project_type import ProjectType
from ..types import UNSET, Unset

T = TypeVar("T", bound="ProjectCreate")


@_attrs_define
class ProjectCreate:
    """
    Attributes:
        name (str):
        created_by (None | str | Unset):
        type_ (ProjectType | str | Unset):
        create_example_templates (bool | Unset):  Default: False.
    """

    name: str
    created_by: None | str | Unset = UNSET
    type_: ProjectType | str | Unset = UNSET
    create_example_templates: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        created_by: None | str | Unset
        if isinstance(self.created_by, Unset):
            created_by = UNSET
        else:
            created_by = self.created_by

        type_: str | Unset
        if isinstance(self.type_, Unset):
            type_ = UNSET
        elif isinstance(self.type_, ProjectType):
            type_ = self.type_.value
        else:
            type_ = self.type_

        create_example_templates = self.create_example_templates

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"name": name})
        if created_by is not UNSET:
            field_dict["created_by"] = created_by
        if type_ is not UNSET:
            field_dict["type"] = type_
        if create_example_templates is not UNSET:
            field_dict["create_example_templates"] = create_example_templates

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        def _parse_created_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_by = _parse_created_by(d.pop("created_by", UNSET))

        def _parse_type_(data: object) -> ProjectType | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                type_type_0 = ProjectType(data)

                return type_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for type_")
            return cast(ProjectType | str | Unset, data)

        type_ = _parse_type_(d.pop("type", UNSET))

        create_example_templates = d.pop("create_example_templates", UNSET)

        project_create = cls(
            name=name, created_by=created_by, type_=type_, create_example_templates=create_example_templates
        )

        project_create.additional_properties = d
        return project_create

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
