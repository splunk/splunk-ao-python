from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.integration_provider import IntegrationProvider

T = TypeVar("T", bound="AvailableIntegrations")


@_attrs_define
class AvailableIntegrations:
    """
    Attributes:
        integrations (list[IntegrationProvider | str]):
    """

    integrations: list[IntegrationProvider | str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        integrations = []
        for integrations_item_data in self.integrations:
            integrations_item: str
            if isinstance(integrations_item_data, IntegrationProvider):
                integrations_item = integrations_item_data.value
            else:
                integrations_item = integrations_item_data
            integrations.append(integrations_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"integrations": integrations})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        integrations = []
        _integrations = d.pop("integrations")
        for integrations_item_data in _integrations:

            def _parse_integrations_item(data: object) -> IntegrationProvider | str:
                try:
                    if not isinstance(data, str):
                        raise TypeError()
                    integrations_item_type_0 = IntegrationProvider(data)

                    return integrations_item_type_0
                except:  # noqa: E722
                    pass
                if type(data) not in (str,):
                    raise TypeError("Unexpected value type for integrations_item")
                return cast(IntegrationProvider | str, data)

            integrations_item = _parse_integrations_item(integrations_item_data)

            integrations.append(integrations_item)

        available_integrations = cls(integrations=integrations)

        available_integrations.additional_properties = d
        return available_integrations

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
