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
        alias (str): Galileo model identifier used in settings and API requests to select this model.
        name (str): Provider model identifier used to match the model to its configured provider deployment or profile.
        display_name (str): Human-readable model name shown in the UI.
        input_modalities (list[ContentModality | str]):
        lifecycle_state (ModelLifecycleState | str | Unset):
        replacement_alias (None | str | Unset):
        deprecation_date (datetime.date | None | Unset):
        retirement_date (datetime.date | None | Unset):
        multimodal_capabilities (list[MultimodalCapability | str] | Unset):
    """

    alias: str
    name: str
    display_name: str
    input_modalities: list[ContentModality | str]
    lifecycle_state: ModelLifecycleState | str | Unset = UNSET
    replacement_alias: None | str | Unset = UNSET
    deprecation_date: datetime.date | None | Unset = UNSET
    retirement_date: datetime.date | None | Unset = UNSET
    multimodal_capabilities: list[MultimodalCapability | str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        alias = self.alias

        name = self.name

        display_name = self.display_name

        if not isinstance(self.input_modalities, list):
            raise TypeError("Unexpected value type for input_modalities")

        input_modalities = []
        for input_modalities_item_data in self.input_modalities:
            input_modalities_item: str
            if isinstance(input_modalities_item_data, ContentModality):
                input_modalities_item = input_modalities_item_data.value
            else:
                input_modalities_item = input_modalities_item_data
            input_modalities.append(input_modalities_item)

        lifecycle_state: str | Unset
        if isinstance(self.lifecycle_state, Unset):
            lifecycle_state = UNSET
        elif isinstance(self.lifecycle_state, ModelLifecycleState):
            lifecycle_state = self.lifecycle_state.value
        else:
            lifecycle_state = self.lifecycle_state

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
            if not isinstance(self.multimodal_capabilities, list):
                raise TypeError("Unexpected value type for multimodal_capabilities")

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
        field_dict.update(
            {"alias": alias, "name": name, "display_name": display_name, "input_modalities": input_modalities}
        )
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

        display_name = d.pop("display_name")

        input_modalities = []
        _input_modalities = d.pop("input_modalities")
        if not isinstance(_input_modalities, list):
            raise TypeError("Unexpected value type for input_modalities")

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

        def _parse_lifecycle_state(data: object) -> ModelLifecycleState | str | Unset:
            if isinstance(data, Unset):
                return data

            try:
                if not isinstance(data, str):
                    raise TypeError()
                lifecycle_state_type_0 = ModelLifecycleState(data)

                return lifecycle_state_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for lifecycle_state")
            return cast(ModelLifecycleState | str | Unset, data)

        lifecycle_state = _parse_lifecycle_state(d.pop("lifecycle_state", UNSET))

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
        multimodal_capabilities: list[MultimodalCapability | str] | Unset = UNSET
        if _multimodal_capabilities is not UNSET:
            if not isinstance(_multimodal_capabilities, list):
                raise TypeError("Unexpected value type for multimodal_capabilities")

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
            alias=alias,
            name=name,
            display_name=display_name,
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
