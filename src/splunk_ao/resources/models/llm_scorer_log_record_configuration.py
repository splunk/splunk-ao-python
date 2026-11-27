from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.input_type_enum import InputTypeEnum
from ..models.multimodal_capability import MultimodalCapability
from ..models.output_type_enum import OutputTypeEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.scorer_metadata_selection import ScorerMetadataSelection


T = TypeVar("T", bound="LLMScorerLogRecordConfiguration")


@_attrs_define
class LLMScorerLogRecordConfiguration:
    """
    Attributes:
        model_alias (str | Unset):  Default: 'gpt-4.1-mini'.
        num_judges (int | Unset):  Default: 3.
        output_type (OutputTypeEnum | Unset): Enumeration of output types.
        scoreable_node_types (list[str] | Unset): Types of nodes that can be scored by this scorer.
        cot_enabled (bool | Unset): Whether chain of thought is enabled for this scorer. Default: False.
        ground_truth (bool | Unset): Whether ground truth is enabled for this scorer. Default: False.
        multimodal_capabilities (list[MultimodalCapability] | None | Unset): Multimodal capabilities required by this
            scorer.
        input_type (InputTypeEnum | None | Unset):
        metadata_selection (None | ScorerMetadataSelection | Unset):
    """

    model_alias: str | Unset = "gpt-4.1-mini"
    num_judges: int | Unset = 3
    output_type: OutputTypeEnum | Unset = UNSET
    scoreable_node_types: list[str] | Unset = UNSET
    cot_enabled: bool | Unset = False
    ground_truth: bool | Unset = False
    multimodal_capabilities: list[MultimodalCapability] | None | Unset = UNSET
    input_type: InputTypeEnum | None | Unset = UNSET
    metadata_selection: None | ScorerMetadataSelection | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.scorer_metadata_selection import ScorerMetadataSelection

        model_alias = self.model_alias

        num_judges = self.num_judges

        output_type: str | Unset = UNSET
        if not isinstance(self.output_type, Unset):
            output_type = self.output_type.value

        scoreable_node_types: list[str] | Unset = UNSET
        if not isinstance(self.scoreable_node_types, Unset):
            scoreable_node_types = self.scoreable_node_types

        cot_enabled = self.cot_enabled

        ground_truth = self.ground_truth

        multimodal_capabilities: list[str] | None | Unset
        if isinstance(self.multimodal_capabilities, Unset):
            multimodal_capabilities = UNSET
        elif isinstance(self.multimodal_capabilities, list):
            multimodal_capabilities = []
            for multimodal_capabilities_type_0_item_data in self.multimodal_capabilities:
                multimodal_capabilities_type_0_item = multimodal_capabilities_type_0_item_data.value
                multimodal_capabilities.append(multimodal_capabilities_type_0_item)

        else:
            multimodal_capabilities = self.multimodal_capabilities

        input_type: None | str | Unset
        if isinstance(self.input_type, Unset):
            input_type = UNSET
        elif isinstance(self.input_type, InputTypeEnum):
            input_type = self.input_type.value
        else:
            input_type = self.input_type

        metadata_selection: dict[str, Any] | None | Unset
        if isinstance(self.metadata_selection, Unset):
            metadata_selection = UNSET
        elif isinstance(self.metadata_selection, ScorerMetadataSelection):
            metadata_selection = self.metadata_selection.to_dict()
        else:
            metadata_selection = self.metadata_selection

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if model_alias is not UNSET:
            field_dict["model_alias"] = model_alias
        if num_judges is not UNSET:
            field_dict["num_judges"] = num_judges
        if output_type is not UNSET:
            field_dict["output_type"] = output_type
        if scoreable_node_types is not UNSET:
            field_dict["scoreable_node_types"] = scoreable_node_types
        if cot_enabled is not UNSET:
            field_dict["cot_enabled"] = cot_enabled
        if ground_truth is not UNSET:
            field_dict["ground_truth"] = ground_truth
        if multimodal_capabilities is not UNSET:
            field_dict["multimodal_capabilities"] = multimodal_capabilities
        if input_type is not UNSET:
            field_dict["input_type"] = input_type
        if metadata_selection is not UNSET:
            field_dict["metadata_selection"] = metadata_selection

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.scorer_metadata_selection import ScorerMetadataSelection

        d = dict(src_dict)
        model_alias = d.pop("model_alias", UNSET)

        num_judges = d.pop("num_judges", UNSET)

        _output_type = d.pop("output_type", UNSET)
        output_type: OutputTypeEnum | Unset
        if isinstance(_output_type, Unset):
            output_type = UNSET
        else:
            output_type = OutputTypeEnum(_output_type)

        scoreable_node_types = cast(list[str], d.pop("scoreable_node_types", UNSET))

        cot_enabled = d.pop("cot_enabled", UNSET)

        ground_truth = d.pop("ground_truth", UNSET)

        def _parse_multimodal_capabilities(data: object) -> list[MultimodalCapability] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                multimodal_capabilities_type_0 = []
                _multimodal_capabilities_type_0 = data
                for multimodal_capabilities_type_0_item_data in _multimodal_capabilities_type_0:
                    multimodal_capabilities_type_0_item = MultimodalCapability(multimodal_capabilities_type_0_item_data)

                    multimodal_capabilities_type_0.append(multimodal_capabilities_type_0_item)

                return multimodal_capabilities_type_0
            except:  # noqa: E722
                pass
            return cast(list[MultimodalCapability] | None | Unset, data)

        multimodal_capabilities = _parse_multimodal_capabilities(d.pop("multimodal_capabilities", UNSET))

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

        llm_scorer_log_record_configuration = cls(
            model_alias=model_alias,
            num_judges=num_judges,
            output_type=output_type,
            scoreable_node_types=scoreable_node_types,
            cot_enabled=cot_enabled,
            ground_truth=ground_truth,
            multimodal_capabilities=multimodal_capabilities,
            input_type=input_type,
            metadata_selection=metadata_selection,
        )

        llm_scorer_log_record_configuration.additional_properties = d
        return llm_scorer_log_record_configuration

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
