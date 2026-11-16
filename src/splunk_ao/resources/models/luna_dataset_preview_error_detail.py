from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_dataset_preview_field_error import LunaDatasetPreviewFieldError


T = TypeVar("T", bound="LunaDatasetPreviewErrorDetail")


@_attrs_define
class LunaDatasetPreviewErrorDetail:
    """
    Attributes:
        code (str):
        message (None | str | Unset):
        current_revision (None | str | Unset):
        field_errors (list[LunaDatasetPreviewFieldError] | None | Unset):
    """

    code: str
    message: None | str | Unset = UNSET
    current_revision: None | str | Unset = UNSET
    field_errors: list[LunaDatasetPreviewFieldError] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        code = self.code

        message: None | str | Unset
        if isinstance(self.message, Unset):
            message = UNSET
        else:
            message = self.message

        current_revision: None | str | Unset
        if isinstance(self.current_revision, Unset):
            current_revision = UNSET
        else:
            current_revision = self.current_revision

        field_errors: list[dict[str, Any]] | None | Unset
        if isinstance(self.field_errors, Unset):
            field_errors = UNSET
        elif isinstance(self.field_errors, list):
            field_errors = []
            for field_errors_type_0_item_data in self.field_errors:
                field_errors_type_0_item = field_errors_type_0_item_data.to_dict()
                field_errors.append(field_errors_type_0_item)

        else:
            field_errors = self.field_errors

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"code": code})
        if message is not UNSET:
            field_dict["message"] = message
        if current_revision is not UNSET:
            field_dict["current_revision"] = current_revision
        if field_errors is not UNSET:
            field_dict["field_errors"] = field_errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_preview_field_error import LunaDatasetPreviewFieldError

        d = dict(src_dict)
        code = d.pop("code")

        def _parse_message(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message = _parse_message(d.pop("message", UNSET))

        def _parse_current_revision(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        current_revision = _parse_current_revision(d.pop("current_revision", UNSET))

        def _parse_field_errors(data: object) -> list[LunaDatasetPreviewFieldError] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                field_errors_type_0 = []
                _field_errors_type_0 = data
                for field_errors_type_0_item_data in _field_errors_type_0:
                    field_errors_type_0_item = LunaDatasetPreviewFieldError.from_dict(field_errors_type_0_item_data)

                    field_errors_type_0.append(field_errors_type_0_item)

                return field_errors_type_0
            except:  # noqa: E722
                pass
            return cast(list[LunaDatasetPreviewFieldError] | None | Unset, data)

        field_errors = _parse_field_errors(d.pop("field_errors", UNSET))

        luna_dataset_preview_error_detail = cls(
            code=code, message=message, current_revision=current_revision, field_errors=field_errors
        )

        luna_dataset_preview_error_detail.additional_properties = d
        return luna_dataset_preview_error_detail

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
