from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.annotation_queue_settings import AnnotationQueueSettings


T = TypeVar("T", bound="AnnotationQueueSettingsResponse")


@_attrs_define
class AnnotationQueueSettingsResponse:
    """
    Attributes:
        annotation_queue_id (str):
        settings (AnnotationQueueSettings): What annotators see in the annotator view. Stored as JSON; defaults apply to
            missing keys.
    """

    annotation_queue_id: str
    settings: AnnotationQueueSettings
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        annotation_queue_id = self.annotation_queue_id

        settings = self.settings.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"annotation_queue_id": annotation_queue_id, "settings": settings})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.annotation_queue_settings import AnnotationQueueSettings

        d = dict(src_dict)
        annotation_queue_id = d.pop("annotation_queue_id")

        settings = AnnotationQueueSettings.from_dict(d.pop("settings"))

        annotation_queue_settings_response = cls(annotation_queue_id=annotation_queue_id, settings=settings)

        annotation_queue_settings_response.additional_properties = d
        return annotation_queue_settings_response

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
