from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.saved_evaluator_reference import SavedEvaluatorReference


T = TypeVar("T", bound="RunEvaluatorsRequest")


@_attrs_define
class RunEvaluatorsRequest:
    """
    Attributes:
        evaluators (list[SavedEvaluatorReference]):
    """

    evaluators: list[SavedEvaluatorReference]

    def to_dict(self) -> dict[str, Any]:
        evaluators = []
        for evaluators_item_data in self.evaluators:
            evaluators_item = evaluators_item_data.to_dict()
            evaluators.append(evaluators_item)

        field_dict: dict[str, Any] = {}

        field_dict.update({"evaluators": evaluators})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.saved_evaluator_reference import SavedEvaluatorReference

        d = dict(src_dict)
        evaluators = []
        _evaluators = d.pop("evaluators")
        for evaluators_item_data in _evaluators:
            evaluators_item = SavedEvaluatorReference.from_dict(evaluators_item_data)

            evaluators.append(evaluators_item)

        run_evaluators_request = cls(evaluators=evaluators)

        return run_evaluators_request
