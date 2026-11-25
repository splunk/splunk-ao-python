from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.type_safe_integration_extra_type_0 import TypeSafeIntegrationExtraType0


T = TypeVar("T", bound="TypeSafeIntegration")


@_attrs_define
class TypeSafeIntegration:
    """
    Attributes:
        id (None | str | Unset):
        name (Literal['typesafe'] | Unset):  Default: 'typesafe'.
        provider (Literal['typesafe'] | Unset):  Default: 'typesafe'.
        extra (None | TypeSafeIntegrationExtraType0 | Unset):
    """

    id: None | str | Unset = UNSET
    name: Literal["typesafe"] | Unset = "typesafe"
    provider: Literal["typesafe"] | Unset = "typesafe"
    extra: None | TypeSafeIntegrationExtraType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.type_safe_integration_extra_type_0 import TypeSafeIntegrationExtraType0

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        name = self.name

        provider = self.provider

        extra: dict[str, Any] | None | Unset
        if isinstance(self.extra, Unset):
            extra = UNSET
        elif isinstance(self.extra, TypeSafeIntegrationExtraType0):
            extra = self.extra.to_dict()
        else:
            extra = self.extra

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if provider is not UNSET:
            field_dict["provider"] = provider
        if extra is not UNSET:
            field_dict["extra"] = extra

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.type_safe_integration_extra_type_0 import TypeSafeIntegrationExtraType0

        d = dict(src_dict)

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        name = cast(Literal["typesafe"] | Unset, d.pop("name", UNSET))
        if name != "typesafe" and not isinstance(name, Unset):
            raise ValueError(f"name must match const 'typesafe', got '{name}'")

        provider = cast(Literal["typesafe"] | Unset, d.pop("provider", UNSET))
        if provider != "typesafe" and not isinstance(provider, Unset):
            raise ValueError(f"provider must match const 'typesafe', got '{provider}'")

        def _parse_extra(data: object) -> None | TypeSafeIntegrationExtraType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                extra_type_0 = TypeSafeIntegrationExtraType0.from_dict(data)

                return extra_type_0
            except:  # noqa: E722
                pass
            return cast(None | TypeSafeIntegrationExtraType0 | Unset, data)

        extra = _parse_extra(d.pop("extra", UNSET))

        type_safe_integration = cls(id=id, name=name, provider=provider, extra=extra)

        type_safe_integration.additional_properties = d
        return type_safe_integration

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
