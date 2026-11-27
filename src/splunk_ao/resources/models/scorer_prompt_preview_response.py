from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.scorer_prompt_message import ScorerPromptMessage
    from ..models.scorer_prompt_preview_response_normalized_input_item import (
        ScorerPromptPreviewResponseNormalizedInputItem,
    )


T = TypeVar("T", bound="ScorerPromptPreviewResponse")


@_attrs_define
class ScorerPromptPreviewResponse:
    """
    Attributes:
        scorer_id (str):
        scorer_version_id (str):
        messages (list[ScorerPromptMessage]):
        normalized_input (list[ScorerPromptPreviewResponseNormalizedInputItem]):
        status (Literal['available'] | Unset):  Default: 'available'.
        label (Literal['Reconstructed evaluator prompt'] | Unset):  Default: 'Reconstructed evaluator prompt'.
        description (Literal['Uses the selected evaluator version with current run settings and log data.'] | Unset):
            Default: 'Uses the selected evaluator version with current run settings and log data.'.
    """

    scorer_id: str
    scorer_version_id: str
    messages: list[ScorerPromptMessage]
    normalized_input: list[ScorerPromptPreviewResponseNormalizedInputItem]
    status: Literal["available"] | Unset = "available"
    label: Literal["Reconstructed evaluator prompt"] | Unset = "Reconstructed evaluator prompt"
    description: Literal["Uses the selected evaluator version with current run settings and log data."] | Unset = (
        "Uses the selected evaluator version with current run settings and log data."
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        scorer_id = self.scorer_id

        scorer_version_id = self.scorer_version_id

        messages = []
        for messages_item_data in self.messages:
            messages_item = messages_item_data.to_dict()
            messages.append(messages_item)

        normalized_input = []
        for normalized_input_item_data in self.normalized_input:
            normalized_input_item = normalized_input_item_data.to_dict()
            normalized_input.append(normalized_input_item)

        status = self.status

        label = self.label

        description = self.description

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "scorer_id": scorer_id,
                "scorer_version_id": scorer_version_id,
                "messages": messages,
                "normalized_input": normalized_input,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if label is not UNSET:
            field_dict["label"] = label
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.scorer_prompt_message import ScorerPromptMessage
        from ..models.scorer_prompt_preview_response_normalized_input_item import (
            ScorerPromptPreviewResponseNormalizedInputItem,
        )

        d = dict(src_dict)
        scorer_id = d.pop("scorer_id")

        scorer_version_id = d.pop("scorer_version_id")

        messages = []
        _messages = d.pop("messages")
        for messages_item_data in _messages:
            messages_item = ScorerPromptMessage.from_dict(messages_item_data)

            messages.append(messages_item)

        normalized_input = []
        _normalized_input = d.pop("normalized_input")
        for normalized_input_item_data in _normalized_input:
            normalized_input_item = ScorerPromptPreviewResponseNormalizedInputItem.from_dict(normalized_input_item_data)

            normalized_input.append(normalized_input_item)

        status = cast(Literal["available"] | Unset, d.pop("status", UNSET))
        if status != "available" and not isinstance(status, Unset):
            raise ValueError(f"status must match const 'available', got '{status}'")

        label = cast(Literal["Reconstructed evaluator prompt"] | Unset, d.pop("label", UNSET))
        if label != "Reconstructed evaluator prompt" and not isinstance(label, Unset):
            raise ValueError(f"label must match const 'Reconstructed evaluator prompt', got '{label}'")

        description = cast(
            Literal["Uses the selected evaluator version with current run settings and log data."] | Unset,
            d.pop("description", UNSET),
        )
        if (
            description != "Uses the selected evaluator version with current run settings and log data."
            and not isinstance(description, Unset)
        ):
            raise ValueError(
                f"description must match const 'Uses the selected evaluator version with current run settings and log data.', got '{description}'"
            )

        scorer_prompt_preview_response = cls(
            scorer_id=scorer_id,
            scorer_version_id=scorer_version_id,
            messages=messages,
            normalized_input=normalized_input,
            status=status,
            label=label,
            description=description,
        )

        scorer_prompt_preview_response.additional_properties = d
        return scorer_prompt_preview_response

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
