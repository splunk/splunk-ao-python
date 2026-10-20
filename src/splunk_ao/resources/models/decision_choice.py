from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="DecisionChoice")


@_attrs_define
class DecisionChoice:
    """One option of a choice question, with an optional description of when it applies.

    Extra fields are forbidden, so a level, which has a ``level`` field, never validates as a choice.

        Attributes:
            label (str):
            description (None | str | Unset):
    """

    label: str
    description: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        label = self.label

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        field_dict: dict[str, Any] = {}

        field_dict.update({"label": label})
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        label = d.pop("label")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        decision_choice = cls(label=label, description=description)

        return decision_choice
