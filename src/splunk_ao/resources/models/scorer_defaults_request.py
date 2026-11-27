from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.input_type_enum import InputTypeEnum
from ..models.output_type_enum import OutputTypeEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.metadata_filter import MetadataFilter
    from ..models.modality_filter import ModalityFilter
    from ..models.node_name_filter import NodeNameFilter
    from ..models.scorer_invocation_config import ScorerInvocationConfig
    from ..models.scorer_metadata_selection import ScorerMetadataSelection
    from ..models.span_input_selection_request import SpanInputSelectionRequest


T = TypeVar("T", bound="ScorerDefaultsRequest")


@_attrs_define
class ScorerDefaultsRequest:
    """Apply span selection limits to new settings while allowing stored defaults to load.

    Attributes:
        model_name (None | str | Unset):
        num_judges (int | None | Unset):
        filters (list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset): List of filters to apply to the
            scorer.
        child_span_filters (list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset): Filters applied to
            descendants of the trace.
        scoreable_node_types (list[str] | None | Unset): List of node types that can be scored by this scorer. Defaults
            to llm/chat.
        cot_enabled (bool | None | Unset): Whether to enable chain of thought for this scorer. Defaults to False for llm
            scorers.
        output_type (None | OutputTypeEnum | Unset): What type of output to use for model-based scorers (boolean,
            categorical, etc.).
        input_type (InputTypeEnum | None | Unset): What type of input to use for model-based scorers
            (sessions_normalized, trace_io_only, etc..).
        metadata_selection (None | ScorerMetadataSelection | Unset):
        span_input_selections (list[SpanInputSelectionRequest] | None | Unset):
        require_matching_span (bool | Unset): For trace scorers with named span selections, require a matching child
            span. Default: False.
        invocation (None | ScorerInvocationConfig | Unset): Deprecated compatibility location for direct-invocation
            metadata. Use ScorerInfo.invocation or BaseScorerDB.invocation instead.
    """

    model_name: None | str | Unset = UNSET
    num_judges: int | None | Unset = UNSET
    filters: list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset = UNSET
    child_span_filters: list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset = UNSET
    scoreable_node_types: list[str] | None | Unset = UNSET
    cot_enabled: bool | None | Unset = UNSET
    output_type: None | OutputTypeEnum | Unset = UNSET
    input_type: InputTypeEnum | None | Unset = UNSET
    metadata_selection: None | ScorerMetadataSelection | Unset = UNSET
    span_input_selections: list[SpanInputSelectionRequest] | None | Unset = UNSET
    require_matching_span: bool | Unset = False
    invocation: None | ScorerInvocationConfig | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.metadata_filter import MetadataFilter
        from ..models.node_name_filter import NodeNameFilter
        from ..models.scorer_invocation_config import ScorerInvocationConfig
        from ..models.scorer_metadata_selection import ScorerMetadataSelection

        model_name: None | str | Unset
        if isinstance(self.model_name, Unset):
            model_name = UNSET
        else:
            model_name = self.model_name

        num_judges: int | None | Unset
        if isinstance(self.num_judges, Unset):
            num_judges = UNSET
        else:
            num_judges = self.num_judges

        filters: list[dict[str, Any]] | None | Unset
        if isinstance(self.filters, Unset):
            filters = UNSET
        elif isinstance(self.filters, list):
            filters = []
            for filters_type_0_item_data in self.filters:
                filters_type_0_item: dict[str, Any]
                if isinstance(filters_type_0_item_data, NodeNameFilter):
                    filters_type_0_item = filters_type_0_item_data.to_dict()
                elif isinstance(filters_type_0_item_data, MetadataFilter):
                    filters_type_0_item = filters_type_0_item_data.to_dict()
                else:
                    filters_type_0_item = filters_type_0_item_data.to_dict()

                filters.append(filters_type_0_item)

        else:
            filters = self.filters

        child_span_filters: list[dict[str, Any]] | None | Unset
        if isinstance(self.child_span_filters, Unset):
            child_span_filters = UNSET
        elif isinstance(self.child_span_filters, list):
            child_span_filters = []
            for child_span_filters_type_0_item_data in self.child_span_filters:
                child_span_filters_type_0_item: dict[str, Any]
                if isinstance(child_span_filters_type_0_item_data, NodeNameFilter):
                    child_span_filters_type_0_item = child_span_filters_type_0_item_data.to_dict()
                elif isinstance(child_span_filters_type_0_item_data, MetadataFilter):
                    child_span_filters_type_0_item = child_span_filters_type_0_item_data.to_dict()
                else:
                    child_span_filters_type_0_item = child_span_filters_type_0_item_data.to_dict()

                child_span_filters.append(child_span_filters_type_0_item)

        else:
            child_span_filters = self.child_span_filters

        scoreable_node_types: list[str] | None | Unset
        if isinstance(self.scoreable_node_types, Unset):
            scoreable_node_types = UNSET
        elif isinstance(self.scoreable_node_types, list):
            scoreable_node_types = self.scoreable_node_types

        else:
            scoreable_node_types = self.scoreable_node_types

        cot_enabled: bool | None | Unset
        if isinstance(self.cot_enabled, Unset):
            cot_enabled = UNSET
        else:
            cot_enabled = self.cot_enabled

        output_type: None | str | Unset
        if isinstance(self.output_type, Unset):
            output_type = UNSET
        elif isinstance(self.output_type, OutputTypeEnum):
            output_type = self.output_type.value
        else:
            output_type = self.output_type

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

        span_input_selections: list[dict[str, Any]] | None | Unset
        if isinstance(self.span_input_selections, Unset):
            span_input_selections = UNSET
        elif isinstance(self.span_input_selections, list):
            span_input_selections = []
            for span_input_selections_type_0_item_data in self.span_input_selections:
                span_input_selections_type_0_item = span_input_selections_type_0_item_data.to_dict()
                span_input_selections.append(span_input_selections_type_0_item)

        else:
            span_input_selections = self.span_input_selections

        require_matching_span = self.require_matching_span

        invocation: dict[str, Any] | None | Unset
        if isinstance(self.invocation, Unset):
            invocation = UNSET
        elif isinstance(self.invocation, ScorerInvocationConfig):
            invocation = self.invocation.to_dict()
        else:
            invocation = self.invocation

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if model_name is not UNSET:
            field_dict["model_name"] = model_name
        if num_judges is not UNSET:
            field_dict["num_judges"] = num_judges
        if filters is not UNSET:
            field_dict["filters"] = filters
        if child_span_filters is not UNSET:
            field_dict["child_span_filters"] = child_span_filters
        if scoreable_node_types is not UNSET:
            field_dict["scoreable_node_types"] = scoreable_node_types
        if cot_enabled is not UNSET:
            field_dict["cot_enabled"] = cot_enabled
        if output_type is not UNSET:
            field_dict["output_type"] = output_type
        if input_type is not UNSET:
            field_dict["input_type"] = input_type
        if metadata_selection is not UNSET:
            field_dict["metadata_selection"] = metadata_selection
        if span_input_selections is not UNSET:
            field_dict["span_input_selections"] = span_input_selections
        if require_matching_span is not UNSET:
            field_dict["require_matching_span"] = require_matching_span
        if invocation is not UNSET:
            field_dict["invocation"] = invocation

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.metadata_filter import MetadataFilter
        from ..models.modality_filter import ModalityFilter
        from ..models.node_name_filter import NodeNameFilter
        from ..models.scorer_invocation_config import ScorerInvocationConfig
        from ..models.scorer_metadata_selection import ScorerMetadataSelection
        from ..models.span_input_selection_request import SpanInputSelectionRequest

        d = dict(src_dict)

        def _parse_model_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        model_name = _parse_model_name(d.pop("model_name", UNSET))

        def _parse_num_judges(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        num_judges = _parse_num_judges(d.pop("num_judges", UNSET))

        def _parse_filters(data: object) -> list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                filters_type_0 = []
                _filters_type_0 = data
                for filters_type_0_item_data in _filters_type_0:

                    def _parse_filters_type_0_item(data: object) -> MetadataFilter | ModalityFilter | NodeNameFilter:
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            filters_type_0_item_type_0 = NodeNameFilter.from_dict(data)

                            return filters_type_0_item_type_0
                        except:  # noqa: E722
                            pass
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            filters_type_0_item_type_1 = MetadataFilter.from_dict(data)

                            return filters_type_0_item_type_1
                        except:  # noqa: E722
                            pass
                        if not isinstance(data, dict):
                            raise TypeError()
                        filters_type_0_item_type_2 = ModalityFilter.from_dict(data)

                        return filters_type_0_item_type_2

                    filters_type_0_item = _parse_filters_type_0_item(filters_type_0_item_data)

                    filters_type_0.append(filters_type_0_item)

                return filters_type_0
            except:  # noqa: E722
                pass
            return cast(list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset, data)

        filters = _parse_filters(d.pop("filters", UNSET))

        def _parse_child_span_filters(
            data: object,
        ) -> list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                child_span_filters_type_0 = []
                _child_span_filters_type_0 = data
                for child_span_filters_type_0_item_data in _child_span_filters_type_0:

                    def _parse_child_span_filters_type_0_item(
                        data: object,
                    ) -> MetadataFilter | ModalityFilter | NodeNameFilter:
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            child_span_filters_type_0_item_type_0 = NodeNameFilter.from_dict(data)

                            return child_span_filters_type_0_item_type_0
                        except:  # noqa: E722
                            pass
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            child_span_filters_type_0_item_type_1 = MetadataFilter.from_dict(data)

                            return child_span_filters_type_0_item_type_1
                        except:  # noqa: E722
                            pass
                        if not isinstance(data, dict):
                            raise TypeError()
                        child_span_filters_type_0_item_type_2 = ModalityFilter.from_dict(data)

                        return child_span_filters_type_0_item_type_2

                    child_span_filters_type_0_item = _parse_child_span_filters_type_0_item(
                        child_span_filters_type_0_item_data
                    )

                    child_span_filters_type_0.append(child_span_filters_type_0_item)

                return child_span_filters_type_0
            except:  # noqa: E722
                pass
            return cast(list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset, data)

        child_span_filters = _parse_child_span_filters(d.pop("child_span_filters", UNSET))

        def _parse_scoreable_node_types(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                scoreable_node_types_type_0 = cast(list[str], data)

                return scoreable_node_types_type_0
            except:  # noqa: E722
                pass
            return cast(list[str] | None | Unset, data)

        scoreable_node_types = _parse_scoreable_node_types(d.pop("scoreable_node_types", UNSET))

        def _parse_cot_enabled(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        cot_enabled = _parse_cot_enabled(d.pop("cot_enabled", UNSET))

        def _parse_output_type(data: object) -> None | OutputTypeEnum | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                output_type_type_0 = OutputTypeEnum(data)

                return output_type_type_0
            except:  # noqa: E722
                pass
            return cast(None | OutputTypeEnum | Unset, data)

        output_type = _parse_output_type(d.pop("output_type", UNSET))

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

        def _parse_span_input_selections(data: object) -> list[SpanInputSelectionRequest] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                span_input_selections_type_0 = []
                _span_input_selections_type_0 = data
                for span_input_selections_type_0_item_data in _span_input_selections_type_0:
                    span_input_selections_type_0_item = SpanInputSelectionRequest.from_dict(
                        span_input_selections_type_0_item_data
                    )

                    span_input_selections_type_0.append(span_input_selections_type_0_item)

                return span_input_selections_type_0
            except:  # noqa: E722
                pass
            return cast(list[SpanInputSelectionRequest] | None | Unset, data)

        span_input_selections = _parse_span_input_selections(d.pop("span_input_selections", UNSET))

        require_matching_span = d.pop("require_matching_span", UNSET)

        def _parse_invocation(data: object) -> None | ScorerInvocationConfig | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                invocation_type_0 = ScorerInvocationConfig.from_dict(data)

                return invocation_type_0
            except:  # noqa: E722
                pass
            return cast(None | ScorerInvocationConfig | Unset, data)

        invocation = _parse_invocation(d.pop("invocation", UNSET))

        scorer_defaults_request = cls(
            model_name=model_name,
            num_judges=num_judges,
            filters=filters,
            child_span_filters=child_span_filters,
            scoreable_node_types=scoreable_node_types,
            cot_enabled=cot_enabled,
            output_type=output_type,
            input_type=input_type,
            metadata_selection=metadata_selection,
            span_input_selections=span_input_selections,
            require_matching_span=require_matching_span,
            invocation=invocation,
        )

        scorer_defaults_request.additional_properties = d
        return scorer_defaults_request

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
