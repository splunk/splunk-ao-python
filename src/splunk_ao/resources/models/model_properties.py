from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.content_modality import ContentModality
from ..models.model_lifecycle_state import ModelLifecycleState
from ..models.multimodal_capability import MultimodalCapability
from ..types import UNSET, Unset

T = TypeVar("T", bound="ModelProperties")


@_attrs_define
class ModelProperties:
    """
    Attributes:
        alias (str):
        name (str):
        input_modalities (list[ContentModality]):
        lifecycle_state (ModelLifecycleState | Unset):
        replacement_alias (None | str | Unset):
        deprecation_date (datetime.date | None | Unset):
        retirement_date (datetime.date | None | Unset):
        multimodal_capabilities (list[MultimodalCapability] | Unset):
    """

    alias: str
    name: str
    input_modalities: list[ContentModality]
    lifecycle_state: ModelLifecycleState | Unset = UNSET
    replacement_alias: None | str | Unset = UNSET
    deprecation_date: datetime.date | None | Unset = UNSET
    retirement_date: datetime.date | None | Unset = UNSET
    multimodal_capabilities: list[MultimodalCapability] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        alias = self.alias

        name = self.name

        input_modalities = []
        for input_modalities_item_data in self.input_modalities:
            input_modalities_item = input_modalities_item_data.value
            input_modalities.append(input_modalities_item)

        lifecycle_state: str | Unset = UNSET
        if not isinstance(self.lifecycle_state, Unset):
            lifecycle_state = self.lifecycle_state.value

        replacement_alias: None | str | Unset
        if isinstance(self.replacement_alias, Unset):
            replacement_alias = UNSET
        else:
            replacement_alias = self.replacement_alias

        deprecation_date: None | str | Unset
        if isinstance(self.deprecation_date, Unset):
            deprecation_date = UNSET
        elif isinstance(self.deprecation_date, datetime.date):
            deprecation_date = self.deprecation_date.isoformat()
        else:
            deprecation_date = self.deprecation_date

        retirement_date: None | str | Unset
        if isinstance(self.retirement_date, Unset):
            retirement_date = UNSET
        elif isinstance(self.retirement_date, datetime.date):
            retirement_date = self.retirement_date.isoformat()
        else:
            retirement_date = self.retirement_date

        multimodal_capabilities: list[str] | Unset = UNSET
        if not isinstance(self.multimodal_capabilities, Unset):
            multimodal_capabilities = []
            for multimodal_capabilities_item_data in self.multimodal_capabilities:
                multimodal_capabilities_item = multimodal_capabilities_item_data.value
                multimodal_capabilities.append(multimodal_capabilities_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"alias": alias, "name": name, "input_modalities": input_modalities})
        if lifecycle_state is not UNSET:
            field_dict["lifecycle_state"] = lifecycle_state
        if replacement_alias is not UNSET:
            field_dict["replacement_alias"] = replacement_alias
        if deprecation_date is not UNSET:
            field_dict["deprecation_date"] = deprecation_date
        if retirement_date is not UNSET:
            field_dict["retirement_date"] = retirement_date
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
            input_modalities_item = ContentModality(input_modalities_item_data)

            input_modalities.append(input_modalities_item)

        _lifecycle_state = d.pop("lifecycle_state", UNSET)
        lifecycle_state: ModelLifecycleState | Unset
        if isinstance(_lifecycle_state, Unset):
            lifecycle_state = UNSET
        else:
            lifecycle_state = ModelLifecycleState(_lifecycle_state)

        def _parse_replacement_alias(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        replacement_alias = _parse_replacement_alias(d.pop("replacement_alias", UNSET))

        def _parse_deprecation_date(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                deprecation_date_type_0 = datetime.date.fromisoformat(data)

                return deprecation_date_type_0
            except:  # noqa: E722
                pass
            return cast(datetime.date | None | Unset, data)

        deprecation_date = _parse_deprecation_date(d.pop("deprecation_date", UNSET))

        def _parse_retirement_date(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                retirement_date_type_0 = datetime.date.fromisoformat(data)

                return retirement_date_type_0
            except:  # noqa: E722
                pass
            return cast(datetime.date | None | Unset, data)

        retirement_date = _parse_retirement_date(d.pop("retirement_date", UNSET))

        _multimodal_capabilities = d.pop("multimodal_capabilities", UNSET)
        multimodal_capabilities: list[MultimodalCapability] | Unset = UNSET
        if _multimodal_capabilities is not UNSET:
            multimodal_capabilities = []
            for multimodal_capabilities_item_data in _multimodal_capabilities:
                multimodal_capabilities_item = MultimodalCapability(multimodal_capabilities_item_data)

                multimodal_capabilities.append(multimodal_capabilities_item)

        model_properties = cls(
            alias=alias,
            name=name,
            input_modalities=input_modalities,
            lifecycle_state=lifecycle_state,
            replacement_alias=replacement_alias,
            deprecation_date=deprecation_date,
            retirement_date=retirement_date,
            multimodal_capabilities=multimodal_capabilities,
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
