from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.scorer_invocation_config_required_inputs_item import ScorerInvocationConfigRequiredInputsItem
from ..models.scorer_invocation_payload_format import ScorerInvocationPayloadFormat
from ..types import UNSET, Unset

T = TypeVar("T", bound="ScorerInvocationConfig")


@_attrs_define
class ScorerInvocationConfig:
    """How the direct scorer-invoke API validates and serializes inputs.

    Attributes:
        payload_format (ScorerInvocationPayloadFormat):
        required_inputs (list[ScorerInvocationConfigRequiredInputsItem] | Unset):
    """

    payload_format: ScorerInvocationPayloadFormat
    required_inputs: list[ScorerInvocationConfigRequiredInputsItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload_format = self.payload_format.value

        required_inputs: list[str] | Unset = UNSET
        if not isinstance(self.required_inputs, Unset):
            required_inputs = []
            for required_inputs_item_data in self.required_inputs:
                required_inputs_item = required_inputs_item_data.value
                required_inputs.append(required_inputs_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"payload_format": payload_format})
        if required_inputs is not UNSET:
            field_dict["required_inputs"] = required_inputs

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        payload_format = ScorerInvocationPayloadFormat(d.pop("payload_format"))

        _required_inputs = d.pop("required_inputs", UNSET)
        required_inputs: list[ScorerInvocationConfigRequiredInputsItem] | Unset = UNSET
        if _required_inputs is not UNSET:
            required_inputs = []
            for required_inputs_item_data in _required_inputs:
                required_inputs_item = ScorerInvocationConfigRequiredInputsItem(required_inputs_item_data)

                required_inputs.append(required_inputs_item)

        scorer_invocation_config = cls(payload_format=payload_format, required_inputs=required_inputs)

        scorer_invocation_config.additional_properties = d
        return scorer_invocation_config

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
