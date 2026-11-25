from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.recommended_models_response_available import RecommendedModelsResponseAvailable
    from ..models.recommended_models_response_model_display_names import RecommendedModelsResponseModelDisplayNames
    from ..models.recommended_models_response_supported import RecommendedModelsResponseSupported


T = TypeVar("T", bound="RecommendedModelsResponse")


@_attrs_define
class RecommendedModelsResponse:
    """
    Attributes:
        supported (RecommendedModelsResponseSupported):
        available (RecommendedModelsResponseAvailable):
        model_display_names (RecommendedModelsResponseModelDisplayNames | Unset): UI labels keyed by the model aliases
            returned in supported and available.
    """

    supported: RecommendedModelsResponseSupported
    available: RecommendedModelsResponseAvailable
    model_display_names: RecommendedModelsResponseModelDisplayNames | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        supported = self.supported.to_dict()

        available = self.available.to_dict()

        model_display_names: dict[str, Any] | Unset = UNSET
        if not isinstance(self.model_display_names, Unset):
            model_display_names = self.model_display_names.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"supported": supported, "available": available})
        if model_display_names is not UNSET:
            field_dict["model_display_names"] = model_display_names

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.recommended_models_response_available import RecommendedModelsResponseAvailable
        from ..models.recommended_models_response_model_display_names import RecommendedModelsResponseModelDisplayNames
        from ..models.recommended_models_response_supported import RecommendedModelsResponseSupported

        d = dict(src_dict)
        supported = RecommendedModelsResponseSupported.from_dict(d.pop("supported"))

        available = RecommendedModelsResponseAvailable.from_dict(d.pop("available"))

        _model_display_names = d.pop("model_display_names", UNSET)
        model_display_names: RecommendedModelsResponseModelDisplayNames | Unset
        if isinstance(_model_display_names, Unset):
            model_display_names = UNSET
        else:
            model_display_names = RecommendedModelsResponseModelDisplayNames.from_dict(_model_display_names)

        recommended_models_response = cls(
            supported=supported, available=available, model_display_names=model_display_names
        )

        recommended_models_response.additional_properties = d
        return recommended_models_response

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
