from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="LunaMappingConfig")


@_attrs_define
class LunaMappingConfig:
    """
    Attributes:
        columns (list[str]):
        flatten (bool | Unset):  Default: True.
    """

    columns: list[str]
    flatten: bool | Unset = True

    def to_dict(self) -> dict[str, Any]:
        columns = self.columns

        flatten = self.flatten

        field_dict: dict[str, Any] = {}

        field_dict.update({"columns": columns})
        if flatten is not UNSET:
            field_dict["flatten"] = flatten

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        columns = cast(list[str], d.pop("columns"))

        flatten = d.pop("flatten", UNSET)

        luna_mapping_config = cls(columns=columns, flatten=flatten)

        return luna_mapping_config
