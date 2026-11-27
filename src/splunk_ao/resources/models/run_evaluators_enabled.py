from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.run_enabled_evaluator import RunEnabledEvaluator


T = TypeVar("T", bound="RunEvaluatorsEnabled")


@_attrs_define
class RunEvaluatorsEnabled:
    """
    Attributes:
        project_id (str):
        log_stream_id (str):
        evaluators (list[RunEnabledEvaluator]):
    """

    project_id: str
    log_stream_id: str
    evaluators: list[RunEnabledEvaluator]

    def to_dict(self) -> dict[str, Any]:
        project_id = self.project_id

        log_stream_id = self.log_stream_id

        evaluators = []
        for evaluators_item_data in self.evaluators:
            evaluators_item = evaluators_item_data.to_dict()
            evaluators.append(evaluators_item)

        field_dict: dict[str, Any] = {}

        field_dict.update({"project_id": project_id, "log_stream_id": log_stream_id, "evaluators": evaluators})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_enabled_evaluator import RunEnabledEvaluator

        d = dict(src_dict)
        project_id = d.pop("project_id")

        log_stream_id = d.pop("log_stream_id")

        evaluators = []
        _evaluators = d.pop("evaluators")
        for evaluators_item_data in _evaluators:
            evaluators_item = RunEnabledEvaluator.from_dict(evaluators_item_data)

            evaluators.append(evaluators_item)

        run_evaluators_enabled = cls(project_id=project_id, log_stream_id=log_stream_id, evaluators=evaluators)

        return run_evaluators_enabled
