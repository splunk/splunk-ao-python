from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.categorical_color_constraint_operator import CategoricalColorConstraintOperator
from ..models.metric_color import MetricColor

T = TypeVar("T", bound="CategoricalColorConstraint")


@_attrs_define
class CategoricalColorConstraint:
    """A color constraint for categorical or multi-label metric values.

    Assigns a color when a categorical score matches the given operator and value.

    Operators and expected value shapes:
      - eq: value must be a single string.
      - one_of: value must be a list of strings.

    Example:
        {"color": "green", "operator": "eq", "value": "pass"}
        {"color": "red", "operator": "one_of", "value": ["fail", "error"]}

        Attributes:
            color (MetricColor | str):
            operator (CategoricalColorConstraintOperator | str):
            value (list[str] | str):
    """

    color: MetricColor | str
    operator: CategoricalColorConstraintOperator | str
    value: list[str] | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        color: str
        if isinstance(self.color, MetricColor):
            color = self.color.value
        else:
            color = self.color

        operator: str
        if isinstance(self.operator, CategoricalColorConstraintOperator):
            operator = self.operator.value
        else:
            operator = self.operator

        value: list[str] | str
        if isinstance(self.value, list):
            value = self.value

        else:
            value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"color": color, "operator": operator, "value": value})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_color(data: object) -> MetricColor | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                color_type_0 = MetricColor(data)

                return color_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for color")
            return cast(MetricColor | str, data)

        color = _parse_color(d.pop("color"))

        def _parse_operator(data: object) -> CategoricalColorConstraintOperator | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                operator_type_0 = CategoricalColorConstraintOperator(data)

                return operator_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for operator")
            return cast(CategoricalColorConstraintOperator | str, data)

        operator = _parse_operator(d.pop("operator"))

        def _parse_value(data: object) -> list[str] | str:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                value_type_1 = cast(list[str], data)

                return value_type_1
            except:  # noqa: E722
                pass
            return cast(list[str] | str, data)

        value = _parse_value(d.pop("value"))

        categorical_color_constraint = cls(color=color, operator=operator, value=value)

        categorical_color_constraint.additional_properties = d
        return categorical_color_constraint

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
