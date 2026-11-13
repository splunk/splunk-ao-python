from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_dataset_preview_error_detail import LunaDatasetPreviewErrorDetail
    from ..models.luna_dataset_preview_request_validation_error import LunaDatasetPreviewRequestValidationError
    from ..models.standard_error import StandardError


T = TypeVar("T", bound="LunaDatasetPreviewErrorResponse")


@_attrs_define
class LunaDatasetPreviewErrorResponse:
    """Catalog failures and ordinary request-validation failures returned by preview routes.

    Attributes:
        detail (list[LunaDatasetPreviewRequestValidationError] | LunaDatasetPreviewErrorDetail | str):
        standard_error (None | StandardError | Unset):
    """

    detail: list[LunaDatasetPreviewRequestValidationError] | LunaDatasetPreviewErrorDetail | str
    standard_error: None | StandardError | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.luna_dataset_preview_error_detail import LunaDatasetPreviewErrorDetail
        from ..models.standard_error import StandardError

        detail: dict[str, Any] | list[dict[str, Any]] | str
        if isinstance(self.detail, LunaDatasetPreviewErrorDetail):
            detail = self.detail.to_dict()
        elif isinstance(self.detail, list):
            detail = []
            for detail_type_2_item_data in self.detail:
                detail_type_2_item = detail_type_2_item_data.to_dict()
                detail.append(detail_type_2_item)

        else:
            detail = self.detail

        standard_error: dict[str, Any] | None | Unset
        if isinstance(self.standard_error, Unset):
            standard_error = UNSET
        elif isinstance(self.standard_error, StandardError):
            standard_error = self.standard_error.to_dict()
        else:
            standard_error = self.standard_error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"detail": detail})
        if standard_error is not UNSET:
            field_dict["standard_error"] = standard_error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_preview_error_detail import LunaDatasetPreviewErrorDetail
        from ..models.luna_dataset_preview_request_validation_error import LunaDatasetPreviewRequestValidationError
        from ..models.standard_error import StandardError

        d = dict(src_dict)

        def _parse_detail(
            data: object,
        ) -> list[LunaDatasetPreviewRequestValidationError] | LunaDatasetPreviewErrorDetail | str:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                detail_type_1 = LunaDatasetPreviewErrorDetail.from_dict(data)

                return detail_type_1
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                detail_type_2 = []
                _detail_type_2 = data
                for detail_type_2_item_data in _detail_type_2:
                    detail_type_2_item = LunaDatasetPreviewRequestValidationError.from_dict(detail_type_2_item_data)

                    detail_type_2.append(detail_type_2_item)

                return detail_type_2
            except:  # noqa: E722
                pass
            return cast(list[LunaDatasetPreviewRequestValidationError] | LunaDatasetPreviewErrorDetail | str, data)

        detail = _parse_detail(d.pop("detail"))

        def _parse_standard_error(data: object) -> None | StandardError | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                standard_error_type_0 = StandardError.from_dict(data)

                return standard_error_type_0
            except:  # noqa: E722
                pass
            return cast(None | StandardError | Unset, data)

        standard_error = _parse_standard_error(d.pop("standard_error", UNSET))

        luna_dataset_preview_error_response = cls(detail=detail, standard_error=standard_error)

        luna_dataset_preview_error_response.additional_properties = d
        return luna_dataset_preview_error_response

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
