from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.input_type_enum import InputTypeEnum
from ..models.output_type_enum import OutputTypeEnum
from ..models.step_type import StepType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.scorer_metadata_selection import ScorerMetadataSelection


T = TypeVar("T", bound="DecisionScorerTestConfiguration")


@_attrs_define
class DecisionScorerTestConfiguration:
    """The evaluator settings of a decision Test request, the same place as the LLM scorer_configuration.

    scoreable_node_types holds exactly one node type. input_type defaults to the decision default
    for it (get_decision_input_type).

        Attributes:
            output_type (OutputTypeEnum): Enumeration of output types.
            scoreable_node_types (list[StepType]):
            input_type (InputTypeEnum | None | Unset):
            ground_truth (bool | Unset):  Default: False.
            metadata_selection (None | ScorerMetadataSelection | Unset):
    """

    output_type: OutputTypeEnum
    scoreable_node_types: list[StepType]
    input_type: InputTypeEnum | None | Unset = UNSET
    ground_truth: bool | Unset = False
    metadata_selection: None | ScorerMetadataSelection | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.scorer_metadata_selection import ScorerMetadataSelection

        output_type = self.output_type.value

        scoreable_node_types = []
        for scoreable_node_types_item_data in self.scoreable_node_types:
            scoreable_node_types_item = scoreable_node_types_item_data.value
            scoreable_node_types.append(scoreable_node_types_item)

        input_type: None | str | Unset
        if isinstance(self.input_type, Unset):
            input_type = UNSET
        elif isinstance(self.input_type, InputTypeEnum):
            input_type = self.input_type.value
        else:
            input_type = self.input_type

        ground_truth = self.ground_truth

        metadata_selection: dict[str, Any] | None | Unset
        if isinstance(self.metadata_selection, Unset):
            metadata_selection = UNSET
        elif isinstance(self.metadata_selection, ScorerMetadataSelection):
            metadata_selection = self.metadata_selection.to_dict()
        else:
            metadata_selection = self.metadata_selection

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"output_type": output_type, "scoreable_node_types": scoreable_node_types})
        if input_type is not UNSET:
            field_dict["input_type"] = input_type
        if ground_truth is not UNSET:
            field_dict["ground_truth"] = ground_truth
        if metadata_selection is not UNSET:
            field_dict["metadata_selection"] = metadata_selection

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.scorer_metadata_selection import ScorerMetadataSelection

        d = dict(src_dict)
        output_type = OutputTypeEnum(d.pop("output_type"))

        scoreable_node_types = []
        _scoreable_node_types = d.pop("scoreable_node_types")
        for scoreable_node_types_item_data in _scoreable_node_types:
            scoreable_node_types_item = StepType(scoreable_node_types_item_data)

            scoreable_node_types.append(scoreable_node_types_item)

        def _parse_input_type(data: object) -> InputTypeEnum | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                input_type_type_0 = InputTypeEnum(data)

                return input_type_type_0
            except:  # noqa: E722
                pass
            return cast(InputTypeEnum | None | Unset, data)

        input_type = _parse_input_type(d.pop("input_type", UNSET))

        ground_truth = d.pop("ground_truth", UNSET)

        def _parse_metadata_selection(data: object) -> None | ScorerMetadataSelection | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metadata_selection_type_0 = ScorerMetadataSelection.from_dict(data)

                return metadata_selection_type_0
            except:  # noqa: E722
                pass
            return cast(None | ScorerMetadataSelection | Unset, data)

        metadata_selection = _parse_metadata_selection(d.pop("metadata_selection", UNSET))

        decision_scorer_test_configuration = cls(
            output_type=output_type,
            scoreable_node_types=scoreable_node_types,
            input_type=input_type,
            ground_truth=ground_truth,
            metadata_selection=metadata_selection,
        )

        decision_scorer_test_configuration.additional_properties = d
        return decision_scorer_test_configuration

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
