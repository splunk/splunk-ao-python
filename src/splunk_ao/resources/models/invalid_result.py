from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="InvalidResult")


@_attrs_define
class InvalidResult:
    """
    Attributes:
        error_message (str):
        result_type (Literal['invalid'] | Unset):  Default: 'invalid'.
        error_code (Literal['environment_preparing'] | None | Unset):
    """

    error_message: str
    result_type: Literal["invalid"] | Unset = "invalid"
    error_code: Literal["environment_preparing"] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        error_message = self.error_message

        result_type = self.result_type

        error_code: Literal["environment_preparing"] | None | Unset
        if isinstance(self.error_code, Unset):
            error_code = UNSET
        else:
            error_code = self.error_code

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"error_message": error_message})
        if result_type is not UNSET:
            field_dict["result_type"] = result_type
        if error_code is not UNSET:
            field_dict["error_code"] = error_code

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        error_message = d.pop("error_message")

        result_type = cast(Literal["invalid"] | Unset, d.pop("result_type", UNSET))
        if result_type != "invalid" and not isinstance(result_type, Unset):
            raise ValueError(f"result_type must match const 'invalid', got '{result_type}'")

        def _parse_error_code(data: object) -> Literal["environment_preparing"] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            error_code_type_0 = cast(Literal["environment_preparing"], data)
            if error_code_type_0 != "environment_preparing":
                raise ValueError(
                    f"error_code_type_0 must match const 'environment_preparing', got '{error_code_type_0}'"
                )
            return error_code_type_0
            return cast(Literal["environment_preparing"] | None | Unset, data)

        error_code = _parse_error_code(d.pop("error_code", UNSET))

        invalid_result = cls(error_message=error_message, result_type=result_type, error_code=error_code)

        invalid_result.additional_properties = d
        return invalid_result

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
