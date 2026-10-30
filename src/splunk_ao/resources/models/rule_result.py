from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.execution_status import ExecutionStatus
from ..models.rule_operator import RuleOperator
from ..types import UNSET, Unset

T = TypeVar("T", bound="RuleResult")


@_attrs_define
class RuleResult:
    """
    Attributes:
        metric (str): Name of the metric.
        operator (RuleOperator | str): Operator to use for comparison.
        target_value (float | int | list[Any] | None | str): Value to compare with for this metric (right hand side).
        status (ExecutionStatus | str | Unset):
        value (Any | None | Unset): Result of the metric computation.
        execution_time (float | None | Unset): Execution time for the rule in seconds.
    """

    metric: str
    operator: RuleOperator | str
    target_value: float | int | list[Any] | None | str
    status: ExecutionStatus | str | Unset = UNSET
    value: Any | None | Unset = UNSET
    execution_time: float | None | Unset = UNSET
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

        status: str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        elif isinstance(self.status, ExecutionStatus):
            status = self.status.value
        else:
            status = self.status

        value: Any | None | Unset
        if isinstance(self.value, Unset):
            value = UNSET
        else:
            value = self.value

        execution_time: float | None | Unset
        if isinstance(self.execution_time, Unset):
            execution_time = UNSET
        else:
            execution_time = self.execution_time

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"metric": metric, "operator": operator, "target_value": target_value})
        if status is not UNSET:
            field_dict["status"] = status
        if value is not UNSET:
            field_dict["value"] = value
        if execution_time is not UNSET:
            field_dict["execution_time"] = execution_time

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

        def _parse_status(data: object) -> ExecutionStatus | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_0 = ExecutionStatus(data)

                return status_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for status")
            return cast(ExecutionStatus | str | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_value(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        value = _parse_value(d.pop("value", UNSET))

        def _parse_execution_time(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        execution_time = _parse_execution_time(d.pop("execution_time", UNSET))

        rule_result = cls(
            metric=metric,
            operator=operator,
            target_value=target_value,
            status=status,
            value=value,
            execution_time=execution_time,
        )

        rule_result.additional_properties = d
        return rule_result

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
