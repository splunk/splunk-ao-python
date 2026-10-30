from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.rule_operator import RuleOperator

T = TypeVar("T", bound="Rule")


@_attrs_define
class Rule:
    """
    Attributes:
        metric (str): Name of the metric.
        operator (RuleOperator | str): Operator to use for comparison.
        target_value (float | int | list[Any] | None | str): Value to compare with for this metric (right hand side).
    """

    metric: str
    operator: RuleOperator | str
    target_value: float | int | list[Any] | None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        metric = self.metric

        operator: str
        if isinstance(self.operator, RuleOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        target_value: float | int | list[Any] | None | str
        if isinstance(self.target_value, list):
            target_value = self.target_value

        else:
            target_value = self.target_value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"metric": metric, "operator": operator, "target_value": target_value})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        metric = d.pop("metric")

        def _parse_operator(data: object) -> RuleOperator | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = RuleOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(RuleOperator | str, data)

        operator = _parse_operator(d.pop("operator"))

        def _parse_target_value(data: object) -> float | int | list[Any] | None | str:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                target_value_type_3 = cast(list[Any], data)

                return target_value_type_3
            except:  # noqa: E722
                pass
            return cast(float | int | list[Any] | None | str, data)

        target_value = _parse_target_value(d.pop("target_value"))

        rule = cls(metric=metric, operator=operator, target_value=target_value)

        rule.additional_properties = d
        return rule

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
