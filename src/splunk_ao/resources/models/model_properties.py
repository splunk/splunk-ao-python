from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.content_modality import ContentModality
from ..models.multimodal_capability import MultimodalCapability
from ..types import UNSET, Unset

T = TypeVar("T", bound="ModelProperties")


@_attrs_define
class ModelProperties:
    """
    Attributes:
        alias (str):
        name (str):
        input_modalities (list[ContentModality | str]):
        multimodal_capabilities (list[MultimodalCapability | str] | Unset):
    """

    alias: str
    name: str
    input_modalities: list[ContentModality | str]
    multimodal_capabilities: list[MultimodalCapability | str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        alias = self.alias

        name = self.name

        input_modalities = []
        for input_modalities_item_data in self.input_modalities:
            input_modalities_item: str
            if isinstance(input_modalities_item_data, ContentModality):
                input_modalities_item = input_modalities_item_data.value
            else:
                input_modalities_item = input_modalities_item_data
            input_modalities.append(input_modalities_item)

        multimodal_capabilities: list[str] | Unset = UNSET
        if not isinstance(self.multimodal_capabilities, Unset):
            multimodal_capabilities = []
            for multimodal_capabilities_item_data in self.multimodal_capabilities:
                multimodal_capabilities_item: str
                if isinstance(multimodal_capabilities_item_data, MultimodalCapability):
                    multimodal_capabilities_item = multimodal_capabilities_item_data.value
                else:
                    multimodal_capabilities_item = multimodal_capabilities_item_data
                multimodal_capabilities.append(multimodal_capabilities_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"alias": alias, "name": name, "input_modalities": input_modalities})
        if multimodal_capabilities is not UNSET:
            field_dict["multimodal_capabilities"] = multimodal_capabilities

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        alias = d.pop("alias")

        name = d.pop("name")

        input_modalities = []
        _input_modalities = d.pop("input_modalities")
        for input_modalities_item_data in _input_modalities:

            def _parse_input_modalities_item(data: object) -> ContentModality | str:
                try:
                    if not isinstance(data, str):
                        raise TypeError()
                    input_modalities_item_type_0 = ContentModality(data)

                    return input_modalities_item_type_0
                except:  # noqa: E722
                    pass
                if type(data) not in (str,):
                    raise TypeError("Unexpected value type for input_modalities_item")
                return cast(ContentModality | str, data)

            input_modalities_item = _parse_input_modalities_item(input_modalities_item_data)

            input_modalities.append(input_modalities_item)

        _multimodal_capabilities = d.pop("multimodal_capabilities", UNSET)
        multimodal_capabilities: list[MultimodalCapability | str] | Unset = UNSET
        if _multimodal_capabilities is not UNSET:
            multimodal_capabilities = []
            for multimodal_capabilities_item_data in _multimodal_capabilities:

                def _parse_multimodal_capabilities_item(data: object) -> MultimodalCapability | str:
                    try:
                        if not isinstance(data, str):
                            raise TypeError()
                        multimodal_capabilities_item_type_0 = MultimodalCapability(data)

                        return multimodal_capabilities_item_type_0
                    except:  # noqa: E722
                        pass
                    if type(data) not in (str,):
                        raise TypeError("Unexpected value type for multimodal_capabilities_item")
                    return cast(MultimodalCapability | str, data)

                multimodal_capabilities_item = _parse_multimodal_capabilities_item(multimodal_capabilities_item_data)

                multimodal_capabilities.append(multimodal_capabilities_item)

        model_properties = cls(
            alias=alias, name=name, input_modalities=input_modalities, multimodal_capabilities=multimodal_capabilities
        )

        model_properties.additional_properties = d
        return model_properties

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
