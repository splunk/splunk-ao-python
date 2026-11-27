from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="DecisionModelProperties")


@_attrs_define
class DecisionModelProperties:
    """One decision model that a custom integration serves. The registry entry of the same name supplies the rest.

    Attributes:
        name (str): Name of a decision model that a custom integration can serve, such as 'kairos-jev'.
    """

    name: str

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        field_dict: dict[str, Any] = {}

        field_dict.update({"name": name})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        decision_model_properties = cls(name=name)

        return decision_model_properties
