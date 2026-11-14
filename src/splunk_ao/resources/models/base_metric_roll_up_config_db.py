from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.categorical_roll_up_method import CategoricalRollUpMethod
from ..models.numeric_roll_up_method import NumericRollUpMethod

T = TypeVar("T", bound="BaseMetricRollUpConfigDB")


@_attrs_define
class BaseMetricRollUpConfigDB:
    """Configuration for rolling up metrics to parent/trace/session.

    Attributes:
        roll_up_methods (list[CategoricalRollUpMethod | NumericRollUpMethod | str]): List of roll up methods to apply to
            the metric. For numeric scorers we support doing multiple roll up types per metric.
    """

    roll_up_methods: list[CategoricalRollUpMethod | NumericRollUpMethod | str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        if not isinstance(self.roll_up_methods, list):
            raise TypeError("Unexpected value type for roll_up_methods")

        roll_up_methods: list[str]
        if isinstance(self.roll_up_methods, list):
            if not isinstance(self.roll_up_methods, list):
                raise TypeError("Unexpected value type for roll_up_methods_type_0")

            roll_up_methods = []
            for roll_up_methods_type_0_item_data in self.roll_up_methods:
                roll_up_methods_type_0_item: str
                if isinstance(roll_up_methods_type_0_item_data, NumericRollUpMethod):
                    roll_up_methods_type_0_item = roll_up_methods_type_0_item_data.value
                elif isinstance(roll_up_methods_type_0_item_data, CategoricalRollUpMethod):
                    roll_up_methods_type_0_item = roll_up_methods_type_0_item_data.value
                else:
                    roll_up_methods_type_0_item = roll_up_methods_type_0_item_data
                roll_up_methods.append(roll_up_methods_type_0_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"roll_up_methods": roll_up_methods})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_roll_up_methods(data: object) -> list[CategoricalRollUpMethod | NumericRollUpMethod | str]:
            if not isinstance(data, list):
                raise TypeError("Unexpected value type for roll_up_methods")

            if not isinstance(data, list):
                raise TypeError()
            roll_up_methods_type_0 = []
            _roll_up_methods_type_0 = data
            if not isinstance(_roll_up_methods_type_0, list):
                raise TypeError("Unexpected value type for roll_up_methods_type_0")

            for roll_up_methods_type_0_item_data in _roll_up_methods_type_0:

                def _parse_roll_up_methods_type_0_item(
                    data: object,
                ) -> CategoricalRollUpMethod | NumericRollUpMethod | str:

                    try:
                        if not isinstance(data, str):
                            raise TypeError()
                        roll_up_methods_type_0_item_type_0 = NumericRollUpMethod(data)

                        return roll_up_methods_type_0_item_type_0
                    except:  # noqa: E722
                        pass
                    try:
                        if not isinstance(data, str):
                            raise TypeError()
                        roll_up_methods_type_0_item_type_1 = CategoricalRollUpMethod(data)

                        return roll_up_methods_type_0_item_type_1
                    except:  # noqa: E722
                        pass
                    if type(data) not in (str,):
                        raise TypeError("Unexpected value type for roll_up_methods_type_0_item")
                    return cast(CategoricalRollUpMethod | NumericRollUpMethod | str, data)

                roll_up_methods_type_0_item = _parse_roll_up_methods_type_0_item(roll_up_methods_type_0_item_data)

                roll_up_methods_type_0.append(roll_up_methods_type_0_item)

            return roll_up_methods_type_0

        roll_up_methods = _parse_roll_up_methods(d.pop("roll_up_methods"))

        base_metric_roll_up_config_db = cls(roll_up_methods=roll_up_methods)

        base_metric_roll_up_config_db.additional_properties = d
        return base_metric_roll_up_config_db

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
