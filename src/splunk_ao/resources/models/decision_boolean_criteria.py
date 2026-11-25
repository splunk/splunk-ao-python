from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="DecisionBooleanCriteria")


@_attrs_define
class DecisionBooleanCriteria:
    """What a true answer and a false answer mean, for a yes/no question. The two are set together.

    Attributes:
        true_ (str):
        false_ (str):
    """

    true_: str
    false_: str

    def to_dict(self) -> dict[str, Any]:
        true_ = self.true_

        false_ = self.false_

        field_dict: dict[str, Any] = {}

        field_dict.update({"true": true_, "false": false_})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        true_ = d.pop("true")

        false_ = d.pop("false")

        decision_boolean_criteria = cls(true_=true_, false_=false_)

        return decision_boolean_criteria
