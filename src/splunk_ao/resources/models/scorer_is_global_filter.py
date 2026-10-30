from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.scorer_is_global_filter_operator import ScorerIsGlobalFilterOperator
from ..types import UNSET, Unset

T = TypeVar("T", bound="ScorerIsGlobalFilter")


@_attrs_define
class ScorerIsGlobalFilter:
    """Filters on the access scope tier: is_global=True (global metrics) vs
    is_global=False (project-scoped metrics).

        Attributes:
            value (bool):
            name (Literal['is_global'] | Unset):  Default: 'is_global'.
            operator (ScorerIsGlobalFilterOperator | str | Unset):  Default: ScorerIsGlobalFilterOperator.EQ.
    """

    value: bool
    name: Literal["is_global"] | Unset = "is_global"
    operator: ScorerIsGlobalFilterOperator | str | Unset = ScorerIsGlobalFilterOperator.EQ
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = self.value

        name = self.name

        operator: str | Unset
        if isinstance(self.operator, Unset):
            operator = UNSET
        elif isinstance(self.operator, ScorerIsGlobalFilterOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"value": value})
        if name is not UNSET:
            field_dict["name"] = name
        if operator is not UNSET:
            field_dict["operator"] = operator

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        value = d.pop("value")

        name = cast(Literal["is_global"] | Unset, d.pop("name", UNSET))
        if name != "is_global" and not isinstance(name, Unset):
            raise ValueError(f"name must match const 'is_global', got '{name}'")

        def _parse_operator(data: object) -> ScorerIsGlobalFilterOperator | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = ScorerIsGlobalFilterOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(ScorerIsGlobalFilterOperator | str | Unset, data)

        operator = _parse_operator(d.pop("operator", UNSET))

        scorer_is_global_filter = cls(value=value, name=name, operator=operator)

        scorer_is_global_filter.additional_properties = d
        return scorer_is_global_filter

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
