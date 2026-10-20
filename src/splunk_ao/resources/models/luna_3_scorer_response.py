from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_3_scorer_response_class_name_to_vocab_ix import Luna3ScorerResponseClassNameToVocabIx


T = TypeVar("T", bound="Luna3ScorerResponse")


@_attrs_define
class Luna3ScorerResponse:
    """
    Attributes:
        instruction (str):
        adapter_path (str):
        class_name_to_vocab_ix (Luna3ScorerResponseClassNameToVocabIx):
        id (str):
        organization_id (str):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
        threshold (float | None | Unset):
        created_by (None | str | Unset):
    """

    instruction: str
    adapter_path: str
    class_name_to_vocab_ix: Luna3ScorerResponseClassNameToVocabIx
    id: str
    organization_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    threshold: float | None | Unset = UNSET
    created_by: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        instruction = self.instruction

        adapter_path = self.adapter_path

        class_name_to_vocab_ix = self.class_name_to_vocab_ix.to_dict()

        id = self.id

        organization_id = self.organization_id

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        threshold: float | None | Unset
        if isinstance(self.threshold, Unset):
            threshold = UNSET
        else:
            threshold = self.threshold

        created_by: None | str | Unset
        if isinstance(self.created_by, Unset):
            created_by = UNSET
        else:
            created_by = self.created_by

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "instruction": instruction,
                "adapter_path": adapter_path,
                "class_name_to_vocab_ix": class_name_to_vocab_ix,
                "id": id,
                "organization_id": organization_id,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if threshold is not UNSET:
            field_dict["threshold"] = threshold
        if created_by is not UNSET:
            field_dict["created_by"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_3_scorer_response_class_name_to_vocab_ix import Luna3ScorerResponseClassNameToVocabIx

        d = dict(src_dict)
        instruction = d.pop("instruction")

        adapter_path = d.pop("adapter_path")

        class_name_to_vocab_ix = Luna3ScorerResponseClassNameToVocabIx.from_dict(d.pop("class_name_to_vocab_ix"))

        id = d.pop("id")

        organization_id = d.pop("organization_id")

        created_at = datetime.datetime.fromisoformat(d.pop("created_at"))

        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))

        def _parse_threshold(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        threshold = _parse_threshold(d.pop("threshold", UNSET))

        def _parse_created_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_by = _parse_created_by(d.pop("created_by", UNSET))

        luna_3_scorer_response = cls(
            instruction=instruction,
            adapter_path=adapter_path,
            class_name_to_vocab_ix=class_name_to_vocab_ix,
            id=id,
            organization_id=organization_id,
            created_at=created_at,
            updated_at=updated_at,
            threshold=threshold,
            created_by=created_by,
        )

        luna_3_scorer_response.additional_properties = d
        return luna_3_scorer_response

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
