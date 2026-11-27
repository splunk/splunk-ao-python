from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.user_lifecycle_state import UserLifecycleState
from ..types import UNSET, Unset

T = TypeVar("T", bound="UserInfo")


@_attrs_define
class UserInfo:
    """A user's basic information, used for display purposes.

    Attributes:
        id (str):
        email (str):
        lifecycle_state (UserLifecycleState | Unset): Retention state, separate from invitation, verification, and sign-
            in status.

            Active identities are neither deactivated nor removed. Deactivated identities retain
            their profile with access revoked. Removed identities have an anonymized live profile.
        first_name (None | str | Unset):
        last_name (None | str | Unset):
    """

    id: str
    email: str
    lifecycle_state: UserLifecycleState | Unset = UNSET
    first_name: None | str | Unset = UNSET
    last_name: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        email = self.email

        lifecycle_state: str | Unset = UNSET
        if not isinstance(self.lifecycle_state, Unset):
            lifecycle_state = self.lifecycle_state.value

        first_name: None | str | Unset
        if isinstance(self.first_name, Unset):
            first_name = UNSET
        else:
            first_name = self.first_name

        last_name: None | str | Unset
        if isinstance(self.last_name, Unset):
            last_name = UNSET
        else:
            last_name = self.last_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"id": id, "email": email})
        if lifecycle_state is not UNSET:
            field_dict["lifecycle_state"] = lifecycle_state
        if first_name is not UNSET:
            field_dict["first_name"] = first_name
        if last_name is not UNSET:
            field_dict["last_name"] = last_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        email = d.pop("email")

        _lifecycle_state = d.pop("lifecycle_state", UNSET)
        lifecycle_state: UserLifecycleState | Unset
        if isinstance(_lifecycle_state, Unset):
            lifecycle_state = UNSET
        else:
            lifecycle_state = UserLifecycleState(_lifecycle_state)

        def _parse_first_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        first_name = _parse_first_name(d.pop("first_name", UNSET))

        def _parse_last_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_name = _parse_last_name(d.pop("last_name", UNSET))

        user_info = cls(id=id, email=email, lifecycle_state=lifecycle_state, first_name=first_name, last_name=last_name)

        user_info.additional_properties = d
        return user_info

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
