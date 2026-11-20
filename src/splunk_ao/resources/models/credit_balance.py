from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreditBalance")


@_attrs_define
class CreditBalance:
    """
    Attributes:
        organization_id (UUID):
        granted_tokens (int):
        consumed_tokens (int):
        reserved_tokens (int):
        available_tokens (int):
        exhausted (bool):
        unit (Literal['input_tokens'] | Unset):  Default: 'input_tokens'.
        eligible (bool | Unset):  Default: True.
    """

    organization_id: UUID
    granted_tokens: int
    consumed_tokens: int
    reserved_tokens: int
    available_tokens: int
    exhausted: bool
    unit: Literal["input_tokens"] | Unset = "input_tokens"
    eligible: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        organization_id = str(self.organization_id)

        granted_tokens = self.granted_tokens

        consumed_tokens = self.consumed_tokens

        reserved_tokens = self.reserved_tokens

        available_tokens = self.available_tokens

        exhausted = self.exhausted

        unit = self.unit

        eligible = self.eligible

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "organization_id": organization_id,
                "granted_tokens": granted_tokens,
                "consumed_tokens": consumed_tokens,
                "reserved_tokens": reserved_tokens,
                "available_tokens": available_tokens,
                "exhausted": exhausted,
            }
        )
        if unit is not UNSET:
            field_dict["unit"] = unit
        if eligible is not UNSET:
            field_dict["eligible"] = eligible

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        organization_id = UUID(d.pop("organization_id"))

        granted_tokens = d.pop("granted_tokens")

        consumed_tokens = d.pop("consumed_tokens")

        reserved_tokens = d.pop("reserved_tokens")

        available_tokens = d.pop("available_tokens")

        exhausted = d.pop("exhausted")

        unit = cast(Literal["input_tokens"] | Unset, d.pop("unit", UNSET))
        if unit != "input_tokens" and not isinstance(unit, Unset):
            raise ValueError(f"unit must match const 'input_tokens', got '{unit}'")

        eligible = d.pop("eligible", UNSET)

        credit_balance = cls(
            organization_id=organization_id,
            granted_tokens=granted_tokens,
            consumed_tokens=consumed_tokens,
            reserved_tokens=reserved_tokens,
            available_tokens=available_tokens,
            exhausted=exhausted,
            unit=unit,
            eligible=eligible,
        )

        credit_balance.additional_properties = d
        return credit_balance

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
