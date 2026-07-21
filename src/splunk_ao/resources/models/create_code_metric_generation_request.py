from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.output_type_enum import OutputTypeEnum
from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateCodeMetricGenerationRequest")


@_attrs_define
class CreateCodeMetricGenerationRequest:
    """Request to generate scorer code from a user message.

    Attributes:
        user_message (str): Natural language, code, or combination
        node_type (None | str | Unset): Selected scoreable node type (llm, retriever, trace, agent, workflow, tool,
            session)
        output_type (None | OutputTypeEnum | Unset): Selected output type (boolean, percentage, count, discrete,
            categorical, multilabel, freeform)
        model_name (None | str | Unset): Model alias to use for generation. Defaults to best available.
    """

    user_message: str
    node_type: None | str | Unset = UNSET
    output_type: None | OutputTypeEnum | Unset = UNSET
    model_name: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        user_message = self.user_message

        node_type: None | str | Unset
        if isinstance(self.node_type, Unset):
            node_type = UNSET
        else:
            node_type = self.node_type

        output_type: None | str | Unset
        if isinstance(self.output_type, Unset):
            output_type = UNSET
        elif isinstance(self.output_type, OutputTypeEnum):
            output_type = self.output_type.value
        else:
            output_type = self.output_type

        model_name: None | str | Unset
        if isinstance(self.model_name, Unset):
            model_name = UNSET
        else:
            model_name = self.model_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"user_message": user_message})
        if node_type is not UNSET:
            field_dict["node_type"] = node_type
        if output_type is not UNSET:
            field_dict["output_type"] = output_type
        if model_name is not UNSET:
            field_dict["model_name"] = model_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        user_message = d.pop("user_message")

        def _parse_node_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        node_type = _parse_node_type(d.pop("node_type", UNSET))

        def _parse_output_type(data: object) -> None | OutputTypeEnum | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                output_type_type_0 = OutputTypeEnum(data)

                return output_type_type_0
            except:  # noqa: E722
                pass
            return cast(None | OutputTypeEnum | Unset, data)

        output_type = _parse_output_type(d.pop("output_type", UNSET))

        def _parse_model_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        model_name = _parse_model_name(d.pop("model_name", UNSET))

        create_code_metric_generation_request = cls(
            user_message=user_message, node_type=node_type, output_type=output_type, model_name=model_name
        )

        create_code_metric_generation_request.additional_properties = d
        return create_code_metric_generation_request

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
