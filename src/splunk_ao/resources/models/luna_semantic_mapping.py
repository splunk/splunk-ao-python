from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.luna_semantic_mapping_target_field import LunaSemanticMappingTargetField

T = TypeVar("T", bound="LunaSemanticMapping")


@_attrs_define
class LunaSemanticMapping:
    """
    Attributes:
        source_column (str):
        target_field (LunaSemanticMappingTargetField):
    """

    source_column: str
    target_field: LunaSemanticMappingTargetField

    def to_dict(self) -> dict[str, Any]:
        source_column = self.source_column

        target_field = self.target_field.value

        field_dict: dict[str, Any] = {}

        field_dict.update({"source_column": source_column, "target_field": target_field})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        source_column = d.pop("source_column")

        target_field = LunaSemanticMappingTargetField(d.pop("target_field"))

        luna_semantic_mapping = cls(source_column=source_column, target_field=target_field)

        return luna_semantic_mapping
