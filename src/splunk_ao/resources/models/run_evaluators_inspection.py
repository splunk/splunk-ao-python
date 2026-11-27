from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.run_evaluator_binding import RunEvaluatorBinding


T = TypeVar("T", bound="RunEvaluatorsInspection")


@_attrs_define
class RunEvaluatorsInspection:
    """
    Attributes:
        project_id (str):
        log_stream_id (str):
        log_stream_name (str):
        bindings (list[RunEvaluatorBinding]):
    """

    project_id: str
    log_stream_id: str
    log_stream_name: str
    bindings: list[RunEvaluatorBinding]

    def to_dict(self) -> dict[str, Any]:
        project_id = self.project_id

        log_stream_id = self.log_stream_id

        log_stream_name = self.log_stream_name

        bindings = []
        for bindings_item_data in self.bindings:
            bindings_item = bindings_item_data.to_dict()
            bindings.append(bindings_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "project_id": project_id,
                "log_stream_id": log_stream_id,
                "log_stream_name": log_stream_name,
                "bindings": bindings,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_evaluator_binding import RunEvaluatorBinding

        d = dict(src_dict)
        project_id = d.pop("project_id")

        log_stream_id = d.pop("log_stream_id")

        log_stream_name = d.pop("log_stream_name")

        bindings = []
        _bindings = d.pop("bindings")
        for bindings_item_data in _bindings:
            bindings_item = RunEvaluatorBinding.from_dict(bindings_item_data)

            bindings.append(bindings_item)

        run_evaluators_inspection = cls(
            project_id=project_id, log_stream_id=log_stream_id, log_stream_name=log_stream_name, bindings=bindings
        )

        return run_evaluators_inspection
