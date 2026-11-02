from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_luna_3_scorer_version_request_class_name_to_vocab_ix import (
        CreateLuna3ScorerVersionRequestClassNameToVocabIx,
    )


T = TypeVar("T", bound="CreateLuna3ScorerVersionRequest")


@_attrs_define
class CreateLuna3ScorerVersionRequest:
    """Immutable LUNA 3 execution fields for a new scorer version.

    Attributes:
        instruction (str):
        adapter_path (str):
        class_name_to_vocab_ix (CreateLuna3ScorerVersionRequestClassNameToVocabIx):
        threshold (float | None | Unset):
    """

    instruction: str
    adapter_path: str
    class_name_to_vocab_ix: CreateLuna3ScorerVersionRequestClassNameToVocabIx
    threshold: float | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        instruction = self.instruction

        adapter_path = self.adapter_path

        class_name_to_vocab_ix = self.class_name_to_vocab_ix.to_dict()

        threshold: float | None | Unset
        if isinstance(self.threshold, Unset):
            threshold = UNSET
        else:
            threshold = self.threshold

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {"instruction": instruction, "adapter_path": adapter_path, "class_name_to_vocab_ix": class_name_to_vocab_ix}
        )
        if threshold is not UNSET:
            field_dict["threshold"] = threshold

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_luna_3_scorer_version_request_class_name_to_vocab_ix import (
            CreateLuna3ScorerVersionRequestClassNameToVocabIx,
        )

        d = dict(src_dict)
        instruction = d.pop("instruction")

        adapter_path = d.pop("adapter_path")

        class_name_to_vocab_ix = CreateLuna3ScorerVersionRequestClassNameToVocabIx.from_dict(
            d.pop("class_name_to_vocab_ix")
        )

        def _parse_threshold(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        threshold = _parse_threshold(d.pop("threshold", UNSET))

        create_luna_3_scorer_version_request = cls(
            instruction=instruction,
            adapter_path=adapter_path,
            class_name_to_vocab_ix=class_name_to_vocab_ix,
            threshold=threshold,
        )

        create_luna_3_scorer_version_request.additional_properties = d
        return create_luna_3_scorer_version_request

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
