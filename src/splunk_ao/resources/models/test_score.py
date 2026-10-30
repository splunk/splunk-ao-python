from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.node_type import NodeType
from ..types import UNSET, Unset

T = TypeVar("T", bound="TestScore")


@_attrs_define
class TestScore:
    """
    Attributes:
        node_type (NodeType | str):
        score (bool | float | int | None | str | Unset):
    """

    node_type: NodeType | str
    score: bool | float | int | None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        node_type: str
        if isinstance(self.node_type, NodeType):
            node_type = self.node_type.value
        else:
            node_type = self.node_type

        score: bool | float | int | None | str | Unset
        if isinstance(self.score, Unset):
            score = UNSET
        else:
            score = self.score

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"node_type": node_type})
        if score is not UNSET:
            field_dict["score"] = score

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_node_type(data: object) -> NodeType | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                node_type_type_0 = NodeType(data)

                return node_type_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for node_type")
            return cast(NodeType | str, data)

        node_type = _parse_node_type(d.pop("node_type"))

        def _parse_score(data: object) -> bool | float | int | None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | float | int | None | str | Unset, data)

        score = _parse_score(d.pop("score", UNSET))

        test_score = cls(node_type=node_type, score=score)

        test_score.additional_properties = d
        return test_score

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
