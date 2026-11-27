from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="RunEvaluatorBinding")


@_attrs_define
class RunEvaluatorBinding:
    """
    Attributes:
        scorer_id (str):
        name (str):
        label (None | str):
        enabled (bool):
        compatible (bool):
        output_type (None | str):
        scoreable_node_types (list[str]):
        required_metric_ids (list[str]):
        filters (list[Any] | None):
        scorer_version_id (None | str | Unset):
    """

    scorer_id: str
    name: str
    label: None | str
    enabled: bool
    compatible: bool
    output_type: None | str
    scoreable_node_types: list[str]
    required_metric_ids: list[str]
    filters: list[Any] | None
    scorer_version_id: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        scorer_id = self.scorer_id

        name = self.name

        label: None | str
        label = self.label

        enabled = self.enabled

        compatible = self.compatible

        output_type: None | str
        output_type = self.output_type

        scoreable_node_types = self.scoreable_node_types

        required_metric_ids = self.required_metric_ids

        filters: list[Any] | None
        if isinstance(self.filters, list):
            filters = self.filters

        else:
            filters = self.filters

        scorer_version_id: None | str | Unset
        if isinstance(self.scorer_version_id, Unset):
            scorer_version_id = UNSET
        else:
            scorer_version_id = self.scorer_version_id

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "scorer_id": scorer_id,
                "name": name,
                "label": label,
                "enabled": enabled,
                "compatible": compatible,
                "output_type": output_type,
                "scoreable_node_types": scoreable_node_types,
                "required_metric_ids": required_metric_ids,
                "filters": filters,
            }
        )
        if scorer_version_id is not UNSET:
            field_dict["scorer_version_id"] = scorer_version_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        scorer_id = d.pop("scorer_id")

        name = d.pop("name")

        def _parse_label(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        label = _parse_label(d.pop("label"))

        enabled = d.pop("enabled")

        compatible = d.pop("compatible")

        def _parse_output_type(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        output_type = _parse_output_type(d.pop("output_type"))

        scoreable_node_types = cast(list[str], d.pop("scoreable_node_types"))

        required_metric_ids = cast(list[str], d.pop("required_metric_ids"))

        def _parse_filters(data: object) -> list[Any] | None:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                filters_type_0 = cast(list[Any], data)

                return filters_type_0
            except:  # noqa: E722
                pass
            return cast(list[Any] | None, data)

        filters = _parse_filters(d.pop("filters"))

        def _parse_scorer_version_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scorer_version_id = _parse_scorer_version_id(d.pop("scorer_version_id", UNSET))

        run_evaluator_binding = cls(
            scorer_id=scorer_id,
            name=name,
            label=label,
            enabled=enabled,
            compatible=compatible,
            output_type=output_type,
            scoreable_node_types=scoreable_node_types,
            required_metric_ids=required_metric_ids,
            filters=filters,
            scorer_version_id=scorer_version_id,
        )

        return run_evaluator_binding
