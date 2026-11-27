from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ScorerMetadataSelection")


@_attrs_define
class ScorerMetadataSelection:
    """Select all metadata or specific user-metadata keys for trace and span inputs.

    Attributes:
        trace (bool | list[str] | Unset):  Default: False.
        spans (bool | list[str] | None | Unset): Omit or set to null to follow the named span fields. Set to false to
            disable span metadata.
    """

    trace: bool | list[str] | Unset = False
    spans: bool | list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        trace: bool | list[str] | Unset
        if isinstance(self.trace, Unset):
            trace = UNSET
        elif isinstance(self.trace, list):
            trace = self.trace

        else:
            trace = self.trace

        spans: bool | list[str] | None | Unset
        if isinstance(self.spans, Unset):
            spans = UNSET
        elif isinstance(self.spans, list):
            spans = self.spans

        else:
            spans = self.spans

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if trace is not UNSET:
            field_dict["trace"] = trace
        if spans is not UNSET:
            field_dict["spans"] = spans

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_trace(data: object) -> bool | list[str] | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                trace_type_1 = cast(list[str], data)

                return trace_type_1
            except:  # noqa: E722
                pass
            return cast(bool | list[str] | Unset, data)

        trace = _parse_trace(d.pop("trace", UNSET))

        def _parse_spans(data: object) -> bool | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                spans_type_1 = cast(list[str], data)

                return spans_type_1
            except:  # noqa: E722
                pass
            return cast(bool | list[str] | None | Unset, data)

        spans = _parse_spans(d.pop("spans", UNSET))

        scorer_metadata_selection = cls(trace=trace, spans=spans)

        scorer_metadata_selection.additional_properties = d
        return scorer_metadata_selection

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
