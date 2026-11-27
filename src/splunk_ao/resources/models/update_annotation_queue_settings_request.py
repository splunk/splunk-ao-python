from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.annotator_view_span_type import AnnotatorViewSpanType
from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateAnnotationQueueSettingsRequest")


@_attrs_define
class UpdateAnnotationQueueSettingsRequest:
    """PUT body. Rejects unknown keys; the base model must not, since it also validates stored JSON on GET.

    Attributes:
        show_full_session (bool | Unset):  Default: True.
        show_conversation_history (bool | Unset):  Default: True.
        show_span_types (bool | Unset):  Default: True.
        span_types (list[AnnotatorViewSpanType] | Unset):
        show_parameters (bool | Unset):  Default: True.
        show_span_metadata (bool | Unset):  Default: True.
        show_evaluators (bool | Unset):  Default: True.
    """

    show_full_session: bool | Unset = True
    show_conversation_history: bool | Unset = True
    show_span_types: bool | Unset = True
    span_types: list[AnnotatorViewSpanType] | Unset = UNSET
    show_parameters: bool | Unset = True
    show_span_metadata: bool | Unset = True
    show_evaluators: bool | Unset = True

    def to_dict(self) -> dict[str, Any]:
        show_full_session = self.show_full_session

        show_conversation_history = self.show_conversation_history

        show_span_types = self.show_span_types

        span_types: list[str] | Unset = UNSET
        if not isinstance(self.span_types, Unset):
            span_types = []
            for span_types_item_data in self.span_types:
                span_types_item = span_types_item_data.value
                span_types.append(span_types_item)

        show_parameters = self.show_parameters

        show_span_metadata = self.show_span_metadata

        show_evaluators = self.show_evaluators

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if show_full_session is not UNSET:
            field_dict["show_full_session"] = show_full_session
        if show_conversation_history is not UNSET:
            field_dict["show_conversation_history"] = show_conversation_history
        if show_span_types is not UNSET:
            field_dict["show_span_types"] = show_span_types
        if span_types is not UNSET:
            field_dict["span_types"] = span_types
        if show_parameters is not UNSET:
            field_dict["show_parameters"] = show_parameters
        if show_span_metadata is not UNSET:
            field_dict["show_span_metadata"] = show_span_metadata
        if show_evaluators is not UNSET:
            field_dict["show_evaluators"] = show_evaluators

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        show_full_session = d.pop("show_full_session", UNSET)

        show_conversation_history = d.pop("show_conversation_history", UNSET)

        show_span_types = d.pop("show_span_types", UNSET)

        _span_types = d.pop("span_types", UNSET)
        span_types: list[AnnotatorViewSpanType] | Unset = UNSET
        if _span_types is not UNSET:
            span_types = []
            for span_types_item_data in _span_types:
                span_types_item = AnnotatorViewSpanType(span_types_item_data)

                span_types.append(span_types_item)

        show_parameters = d.pop("show_parameters", UNSET)

        show_span_metadata = d.pop("show_span_metadata", UNSET)

        show_evaluators = d.pop("show_evaluators", UNSET)

        update_annotation_queue_settings_request = cls(
            show_full_session=show_full_session,
            show_conversation_history=show_conversation_history,
            show_span_types=show_span_types,
            span_types=span_types,
            show_parameters=show_parameters,
            show_span_metadata=show_span_metadata,
            show_evaluators=show_evaluators,
        )

        return update_annotation_queue_settings_request
