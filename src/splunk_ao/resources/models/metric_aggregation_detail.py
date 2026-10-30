from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.metric_aggregation import MetricAggregation

T = TypeVar("T", bound="MetricAggregationDetail")


@_attrs_define
class MetricAggregationDetail:
    """
    Attributes:
        id (str): Identifier for the metric in the response (e.g., 'w1', 'w2')
        metric_name (str): Name of the metric to aggregate
        aggregation (MetricAggregation | str): Aggregation type to apply
    """

    id: str
    metric_name: str
    aggregation: MetricAggregation | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        metric_name = self.metric_name

        aggregation: str
        if isinstance(self.aggregation, MetricAggregation):
            aggregation = self.aggregation.value
        else:
            aggregation = self.aggregation

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"id": id, "metric_name": metric_name, "aggregation": aggregation})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        metric_name = d.pop("metric_name")

        def _parse_aggregation(data: object) -> MetricAggregation | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                aggregation_type_0 = MetricAggregation(data)

                return aggregation_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for aggregation")
            return cast(MetricAggregation | str, data)

        aggregation = _parse_aggregation(d.pop("aggregation"))

        metric_aggregation_detail = cls(id=id, metric_name=metric_name, aggregation=aggregation)

        metric_aggregation_detail.additional_properties = d
        return metric_aggregation_detail

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
