from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.input_type_enum import InputTypeEnum
from ..models.multimodal_capability import MultimodalCapability
from ..models.output_type_enum import OutputTypeEnum
from ..models.roll_up_method_display_options import RollUpMethodDisplayOptions
from ..models.scorer_types import ScorerTypes
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
    from ..models.base_scorer_version_db import BaseScorerVersionDB
    from ..models.metadata_filter import MetadataFilter
    from ..models.modality_filter import ModalityFilter
    from ..models.node_name_filter import NodeNameFilter


T = TypeVar("T", bound="RuntimeScorerConfig")


@_attrs_define
class RuntimeScorerConfig:
    """Hydrated scorer config used at runtime. Never persisted directly.

    Produced by hydrate_scorer_config from a StoredScorerConfig + live DB rows.

        Attributes:
            id (str):
            scorer_version_id (None | str | Unset):
            filters (list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset): List of filters to apply to the
                scorer.
            roll_up_method (None | RollUpMethodDisplayOptions | Unset):
            name (None | str | Unset):
            scorer_type (None | ScorerTypes | Unset):
            model_name (None | str | Unset):
            num_judges (int | None | Unset):
            scorer_version (BaseScorerVersionDB | None | Unset): ScorerVersion to use for this scorer. If not provided, the
                latest version will be used.
            scoreable_node_types (list[str] | None | Unset): List of node types that can be scored by this scorer. Defaults
                to llm/chat.
            cot_enabled (bool | None | Unset): Whether to enable chain of thought for this scorer. Defaults to False for llm
                scorers.
            output_type (None | OutputTypeEnum | Unset): What type of output to use for model-based scorers (boolean,
                categorical, etc.).
            input_type (InputTypeEnum | None | Unset): What type of input to use for model-based scorers
                (sessions_normalized, trace_io_only, etc..).
            multimodal_capabilities (list[MultimodalCapability] | None | Unset): Multimodal capabilities which this scorer
                can utilize in its evaluation.
            roll_up_config (BaseMetricRollUpConfigDB | None | Unset):
            score_type (None | str | Unset): Return type of code scorers (e.g., 'bool', 'int', 'float', 'str').
    """

    id: str
    scorer_version_id: None | str | Unset = UNSET
    filters: list[MetadataFilter | ModalityFilter | NodeNameFilter] | None | Unset = UNSET
    roll_up_method: None | RollUpMethodDisplayOptions | Unset = UNSET
    name: None | str | Unset = UNSET
    scorer_type: None | ScorerTypes | Unset = UNSET
    model_name: None | str | Unset = UNSET
    num_judges: int | None | Unset = UNSET
    scorer_version: BaseScorerVersionDB | None | Unset = UNSET
    scoreable_node_types: list[str] | None | Unset = UNSET
    cot_enabled: bool | None | Unset = UNSET
    output_type: None | OutputTypeEnum | Unset = UNSET
    input_type: InputTypeEnum | None | Unset = UNSET
    multimodal_capabilities: list[MultimodalCapability] | None | Unset = UNSET
    roll_up_config: BaseMetricRollUpConfigDB | None | Unset = UNSET
    score_type: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
        from ..models.base_scorer_version_db import BaseScorerVersionDB
        from ..models.metadata_filter import MetadataFilter
        from ..models.node_name_filter import NodeNameFilter

        id = self.id

        scorer_version_id: None | str | Unset
        if isinstance(self.scorer_version_id, Unset):
            scorer_version_id = UNSET
        else:
            scorer_version_id = self.scorer_version_id

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

        roll_up_method: None | str | Unset
        if isinstance(self.roll_up_method, Unset):
            roll_up_method = UNSET
        elif isinstance(self.roll_up_method, RollUpMethodDisplayOptions):
            roll_up_method = self.roll_up_method.value
        else:
            roll_up_method = self.roll_up_method

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        scorer_type: None | str | Unset
        if isinstance(self.scorer_type, Unset):
            scorer_type = UNSET
        elif isinstance(self.scorer_type, ScorerTypes):
            scorer_type = self.scorer_type.value
        else:
            scorer_type = self.scorer_type

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

        scorer_version: dict[str, Any] | None | Unset
        if isinstance(self.scorer_version, Unset):
            scorer_version = UNSET
        elif isinstance(self.scorer_version, BaseScorerVersionDB):
            scorer_version = self.scorer_version.to_dict()
        else:
            scorer_version = self.scorer_version

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

        roll_up_config: dict[str, Any] | None | Unset
        if isinstance(self.roll_up_config, Unset):
            roll_up_config = UNSET
        elif isinstance(self.roll_up_config, BaseMetricRollUpConfigDB):
            roll_up_config = self.roll_up_config.to_dict()
        else:
            roll_up_config = self.roll_up_config

        score_type: None | str | Unset
        if isinstance(self.score_type, Unset):
            score_type = UNSET
        else:
            score_type = self.score_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"id": id})
        if scorer_version_id is not UNSET:
            field_dict["scorer_version_id"] = scorer_version_id
        if filters is not UNSET:
            field_dict["filters"] = filters
        if roll_up_method is not UNSET:
            field_dict["roll_up_method"] = roll_up_method
        if name is not UNSET:
            field_dict["name"] = name
        if scorer_type is not UNSET:
            field_dict["scorer_type"] = scorer_type
        if model_name is not UNSET:
            field_dict["model_name"] = model_name
        if num_judges is not UNSET:
            field_dict["num_judges"] = num_judges
        if scorer_version is not UNSET:
            field_dict["scorer_version"] = scorer_version
        if scoreable_node_types is not UNSET:
            field_dict["scoreable_node_types"] = scoreable_node_types
        if cot_enabled is not UNSET:
            field_dict["cot_enabled"] = cot_enabled
        if output_type is not UNSET:
            field_dict["output_type"] = output_type
        if input_type is not UNSET:
            field_dict["input_type"] = input_type
        if multimodal_capabilities is not UNSET:
            field_dict["multimodal_capabilities"] = multimodal_capabilities
        if roll_up_config is not UNSET:
            field_dict["roll_up_config"] = roll_up_config
        if score_type is not UNSET:
            field_dict["score_type"] = score_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
        from ..models.base_scorer_version_db import BaseScorerVersionDB
        from ..models.metadata_filter import MetadataFilter
        from ..models.modality_filter import ModalityFilter
        from ..models.node_name_filter import NodeNameFilter

        d = dict(src_dict)
        id = d.pop("id")

        def _parse_scorer_version_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scorer_version_id = _parse_scorer_version_id(d.pop("scorer_version_id", UNSET))

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

        def _parse_roll_up_method(data: object) -> None | RollUpMethodDisplayOptions | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                roll_up_method_type_0 = RollUpMethodDisplayOptions(data)

                return roll_up_method_type_0
            except:  # noqa: E722
                pass
            return cast(None | RollUpMethodDisplayOptions | Unset, data)

        roll_up_method = _parse_roll_up_method(d.pop("roll_up_method", UNSET))

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_scorer_type(data: object) -> None | ScorerTypes | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                scorer_type_type_0 = ScorerTypes(data)

                return scorer_type_type_0
            except:  # noqa: E722
                pass
            return cast(None | ScorerTypes | Unset, data)

        scorer_type = _parse_scorer_type(d.pop("scorer_type", UNSET))

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

        def _parse_scorer_version(data: object) -> BaseScorerVersionDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                scorer_version_type_0 = BaseScorerVersionDB.from_dict(data)

                return scorer_version_type_0
            except:  # noqa: E722
                pass
            return cast(BaseScorerVersionDB | None | Unset, data)

        scorer_version = _parse_scorer_version(d.pop("scorer_version", UNSET))

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

        def _parse_roll_up_config(data: object) -> BaseMetricRollUpConfigDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                roll_up_config_type_0 = BaseMetricRollUpConfigDB.from_dict(data)

                return roll_up_config_type_0
            except:  # noqa: E722
                pass
            return cast(BaseMetricRollUpConfigDB | None | Unset, data)

        roll_up_config = _parse_roll_up_config(d.pop("roll_up_config", UNSET))

        def _parse_score_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        score_type = _parse_score_type(d.pop("score_type", UNSET))

        runtime_scorer_config = cls(
            id=id,
            scorer_version_id=scorer_version_id,
            filters=filters,
            roll_up_method=roll_up_method,
            name=name,
            scorer_type=scorer_type,
            model_name=model_name,
            num_judges=num_judges,
            scorer_version=scorer_version,
            scoreable_node_types=scoreable_node_types,
            cot_enabled=cot_enabled,
            output_type=output_type,
            input_type=input_type,
            multimodal_capabilities=multimodal_capabilities,
            roll_up_config=roll_up_config,
            score_type=score_type,
        )

        runtime_scorer_config.additional_properties = d
        return runtime_scorer_config

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
