from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.scorer_version_health_score_entry_secondary_type_0 import ScorerVersionHealthScoreEntrySecondaryType0


T = TypeVar("T", bound="ScorerVersionHealthScoreEntry")


@_attrs_define
class ScorerVersionHealthScoreEntry:
    """
    Attributes:
        id (str):
        scorer_version_id (str):
        scorer_version_number (int):
        dataset_id (str):
        health_score_type (str):
        score (float):
        secondary (None | ScorerVersionHealthScoreEntrySecondaryType0):
        computed_at (datetime.datetime):
    """

    id: str
    scorer_version_id: str
    scorer_version_number: int
    dataset_id: str
    health_score_type: str
    score: float
    secondary: None | ScorerVersionHealthScoreEntrySecondaryType0
    computed_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.scorer_version_health_score_entry_secondary_type_0 import (
            ScorerVersionHealthScoreEntrySecondaryType0,
        )

        id = self.id

        scorer_version_id = self.scorer_version_id

        scorer_version_number = self.scorer_version_number

        dataset_id = self.dataset_id

        health_score_type = self.health_score_type

        score = self.score

        secondary: dict[str, Any] | None
        if isinstance(self.secondary, ScorerVersionHealthScoreEntrySecondaryType0):
            secondary = self.secondary.to_dict()
        else:
            secondary = self.secondary

        computed_at = self.computed_at.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "scorer_version_id": scorer_version_id,
                "scorer_version_number": scorer_version_number,
                "dataset_id": dataset_id,
                "health_score_type": health_score_type,
                "score": score,
                "secondary": secondary,
                "computed_at": computed_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.scorer_version_health_score_entry_secondary_type_0 import (
            ScorerVersionHealthScoreEntrySecondaryType0,
        )

        d = dict(src_dict)
        id = d.pop("id")

        scorer_version_id = d.pop("scorer_version_id")

        scorer_version_number = d.pop("scorer_version_number")

        dataset_id = d.pop("dataset_id")

        health_score_type = d.pop("health_score_type")

        score = d.pop("score")

        def _parse_secondary(data: object) -> None | ScorerVersionHealthScoreEntrySecondaryType0:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                secondary_type_0 = ScorerVersionHealthScoreEntrySecondaryType0.from_dict(data)

                return secondary_type_0
            except:  # noqa: E722
                pass
            return cast(None | ScorerVersionHealthScoreEntrySecondaryType0, data)

        secondary = _parse_secondary(d.pop("secondary"))

        computed_at = datetime.datetime.fromisoformat(d.pop("computed_at"))

        scorer_version_health_score_entry = cls(
            id=id,
            scorer_version_id=scorer_version_id,
            scorer_version_number=scorer_version_number,
            dataset_id=dataset_id,
            health_score_type=health_score_type,
            score=score,
            secondary=secondary,
            computed_at=computed_at,
        )

        scorer_version_health_score_entry.additional_properties = d
        return scorer_version_health_score_entry

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
