from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.annotation_queue_updated_at_filter_operator import AnnotationQueueUpdatedAtFilterOperator
from ..types import UNSET, Unset

T = TypeVar("T", bound="AnnotationQueueUpdatedAtFilter")


@_attrs_define
class AnnotationQueueUpdatedAtFilter:
    """
    Attributes:
        operator (AnnotationQueueUpdatedAtFilterOperator | str):
        value (datetime.datetime):
        name (Literal['updated_at'] | Unset):  Default: 'updated_at'.
    """

    operator: AnnotationQueueUpdatedAtFilterOperator | str
    value: datetime.datetime
    name: Literal["updated_at"] | Unset = "updated_at"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operator: str
        if isinstance(self.operator, AnnotationQueueUpdatedAtFilterOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        value = self.value.isoformat()

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"operator": operator, "value": value})
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_operator(data: object) -> AnnotationQueueUpdatedAtFilterOperator | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = AnnotationQueueUpdatedAtFilterOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(AnnotationQueueUpdatedAtFilterOperator | str, data)

        operator = _parse_operator(d.pop("operator"))

        value = datetime.datetime.fromisoformat(d.pop("value"))

        name = cast(Literal["updated_at"] | Unset, d.pop("name", UNSET))
        if name != "updated_at" and not isinstance(name, Unset):
            raise ValueError(f"name must match const 'updated_at', got '{name}'")

        annotation_queue_updated_at_filter = cls(operator=operator, value=value, name=name)

        annotation_queue_updated_at_filter.additional_properties = d
        return annotation_queue_updated_at_filter

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
