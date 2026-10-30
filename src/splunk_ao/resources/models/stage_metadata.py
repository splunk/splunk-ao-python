from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.stage_type import StageType

T = TypeVar("T", bound="StageMetadata")


@_attrs_define
class StageMetadata:
    """
    Attributes:
        project_id (str):
        stage_id (str):
        stage_name (str):
        stage_version (int):
        stage_type (StageType | str):
    """

    project_id: str
    stage_id: str
    stage_name: str
    stage_version: int
    stage_type: StageType | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        project_id = self.project_id

        stage_id = self.stage_id

        stage_name = self.stage_name

        stage_version = self.stage_version

        stage_type: str
        if isinstance(self.stage_type, StageType):
            stage_type = self.stage_type.value
        else:
            stage_type = self.stage_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "project_id": project_id,
                "stage_id": stage_id,
                "stage_name": stage_name,
                "stage_version": stage_version,
                "stage_type": stage_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        project_id = d.pop("project_id")

        stage_id = d.pop("stage_id")

        stage_name = d.pop("stage_name")

        stage_version = d.pop("stage_version")

        def _parse_stage_type(data: object) -> StageType | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                stage_type_type_0 = StageType(data)

                return stage_type_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for stage_type")
            return cast(StageType | str, data)

        stage_type = _parse_stage_type(d.pop("stage_type"))

        stage_metadata = cls(
            project_id=project_id,
            stage_id=stage_id,
            stage_name=stage_name,
            stage_version=stage_version,
            stage_type=stage_type,
        )

        stage_metadata.additional_properties = d
        return stage_metadata

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
