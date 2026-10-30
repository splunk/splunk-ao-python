from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.output_type_enum import OutputTypeEnum
from ..models.step_type import StepType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.compute_health_score_request_mgt_overlay import ComputeHealthScoreRequestMgtOverlay


T = TypeVar("T", bound="ComputeHealthScoreRequest")


@_attrs_define
class ComputeHealthScoreRequest:
    """
    Attributes:
        scorer_id (str):
        output_type (OutputTypeEnum | str): The scorer's output type, used to dispatch the correct metric.
        scoreable_node_types (list[StepType | str] | Unset): The scorer's scoreable_node_types. Determines which record
            type carries the score.
        mgt_overlay (ComputeHealthScoreRequestMgtOverlay | Unset): Client-side pending MGT edits: {row_id: value}.
            Overrides committed dataset values.
    """

    scorer_id: str
    output_type: OutputTypeEnum | str
    scoreable_node_types: list[StepType | str] | Unset = UNSET
    mgt_overlay: ComputeHealthScoreRequestMgtOverlay | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        scorer_id = self.scorer_id

        output_type: str
        if isinstance(self.output_type, OutputTypeEnum):
            output_type = self.output_type.value
        else:
            output_type = self.output_type

        scoreable_node_types: list[str] | Unset = UNSET
        if not isinstance(self.scoreable_node_types, Unset):
            scoreable_node_types = []
            for scoreable_node_types_item_data in self.scoreable_node_types:
                scoreable_node_types_item: str
                if isinstance(scoreable_node_types_item_data, StepType):
                    scoreable_node_types_item = scoreable_node_types_item_data.value
                else:
                    scoreable_node_types_item = scoreable_node_types_item_data
                scoreable_node_types.append(scoreable_node_types_item)

        mgt_overlay: dict[str, Any] | Unset = UNSET
        if not isinstance(self.mgt_overlay, Unset):
            mgt_overlay = self.mgt_overlay.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"scorer_id": scorer_id, "output_type": output_type})
        if scoreable_node_types is not UNSET:
            field_dict["scoreable_node_types"] = scoreable_node_types
        if mgt_overlay is not UNSET:
            field_dict["mgt_overlay"] = mgt_overlay

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.compute_health_score_request_mgt_overlay import ComputeHealthScoreRequestMgtOverlay

        d = dict(src_dict)
        scorer_id = d.pop("scorer_id")

        def _parse_output_type(data: object) -> OutputTypeEnum | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                output_type_type_0 = OutputTypeEnum(data)

                return output_type_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for output_type")
            return cast(OutputTypeEnum | str, data)

        output_type = _parse_output_type(d.pop("output_type"))

        _scoreable_node_types = d.pop("scoreable_node_types", UNSET)
        scoreable_node_types: list[StepType | str] | Unset = UNSET
        if _scoreable_node_types is not UNSET:
            scoreable_node_types = []
            for scoreable_node_types_item_data in _scoreable_node_types:

                def _parse_scoreable_node_types_item(data: object) -> StepType | str:
                    try:
                        if not isinstance(data, str):
                            raise TypeError()
                        scoreable_node_types_item_type_0 = StepType(data)

                        return scoreable_node_types_item_type_0
                    except:  # noqa: E722
                        pass
                    if type(data) not in (str,):
                        raise TypeError("Unexpected value type for scoreable_node_types_item")
                    return cast(StepType | str, data)

                scoreable_node_types_item = _parse_scoreable_node_types_item(scoreable_node_types_item_data)

                scoreable_node_types.append(scoreable_node_types_item)

        _mgt_overlay = d.pop("mgt_overlay", UNSET)
        mgt_overlay: ComputeHealthScoreRequestMgtOverlay | Unset
        if isinstance(_mgt_overlay, Unset):
            mgt_overlay = UNSET
        else:
            mgt_overlay = ComputeHealthScoreRequestMgtOverlay.from_dict(_mgt_overlay)

        compute_health_score_request = cls(
            scorer_id=scorer_id,
            output_type=output_type,
            scoreable_node_types=scoreable_node_types,
            mgt_overlay=mgt_overlay,
        )

        compute_health_score_request.additional_properties = d
        return compute_health_score_request

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
