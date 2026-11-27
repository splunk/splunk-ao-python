from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="SavedEvaluatorReference")


@_attrs_define
class SavedEvaluatorReference:
    """A saved Evaluator and the optional exact version selected by its caller.

    Attributes:
        scorer_id (str):
        scorer_version_id (None | str | Unset):
    """

    scorer_id: str
    scorer_version_id: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        scorer_id = self.scorer_id

        scorer_version_id: None | str | Unset
        if isinstance(self.scorer_version_id, Unset):
            scorer_version_id = UNSET
        else:
            scorer_version_id = self.scorer_version_id

        field_dict: dict[str, Any] = {}

        field_dict.update({"scorer_id": scorer_id})
        if scorer_version_id is not UNSET:
            field_dict["scorer_version_id"] = scorer_version_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        scorer_id = d.pop("scorer_id")

        def _parse_scorer_version_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scorer_version_id = _parse_scorer_version_id(d.pop("scorer_version_id", UNSET))

        saved_evaluator_reference = cls(scorer_id=scorer_id, scorer_version_id=scorer_version_id)

        return saved_evaluator_reference
