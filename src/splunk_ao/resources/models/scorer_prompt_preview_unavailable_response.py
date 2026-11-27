from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.scorer_prompt_preview_unavailable_reason import ScorerPromptPreviewUnavailableReason
from ..types import UNSET, Unset

T = TypeVar("T", bound="ScorerPromptPreviewUnavailableResponse")


@_attrs_define
class ScorerPromptPreviewUnavailableResponse:
    """
    Attributes:
        scorer_id (str):
        scorer_version_id (str):
        reason (ScorerPromptPreviewUnavailableReason):
        message (str):
        status (Literal['unavailable'] | Unset):  Default: 'unavailable'.
    """

    scorer_id: str
    scorer_version_id: str
    reason: ScorerPromptPreviewUnavailableReason
    message: str
    status: Literal["unavailable"] | Unset = "unavailable"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        scorer_id = self.scorer_id

        scorer_version_id = self.scorer_version_id

        reason = self.reason.value

        message = self.message

        status = self.status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {"scorer_id": scorer_id, "scorer_version_id": scorer_version_id, "reason": reason, "message": message}
        )
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        scorer_id = d.pop("scorer_id")

        scorer_version_id = d.pop("scorer_version_id")

        reason = ScorerPromptPreviewUnavailableReason(d.pop("reason"))

        message = d.pop("message")

        status = cast(Literal["unavailable"] | Unset, d.pop("status", UNSET))
        if status != "unavailable" and not isinstance(status, Unset):
            raise ValueError(f"status must match const 'unavailable', got '{status}'")

        scorer_prompt_preview_unavailable_response = cls(
            scorer_id=scorer_id, scorer_version_id=scorer_version_id, reason=reason, message=message, status=status
        )

        scorer_prompt_preview_unavailable_response.additional_properties = d
        return scorer_prompt_preview_unavailable_response

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
