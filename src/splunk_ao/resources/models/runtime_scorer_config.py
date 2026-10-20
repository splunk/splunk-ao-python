from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.input_type_enum import InputTypeEnum
from ..models.luna_input_type_enum import LunaInputTypeEnum
from ..models.luna_output_type_enum import LunaOutputTypeEnum
from ..models.model_type import ModelType
from ..models.multimodal_capability import MultimodalCapability
from ..models.output_type_enum import OutputTypeEnum
from ..models.roll_up_method_display_options import RollUpMethodDisplayOptions
from ..models.roll_up_strategy import RollUpStrategy
from ..models.scorer_types import ScorerTypes
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
    from ..models.base_scorer_version_db import BaseScorerVersionDB
    from ..models.chain_poll_template import ChainPollTemplate
    from ..models.decision_boolean_criteria import DecisionBooleanCriteria
    from ..models.decision_choice import DecisionChoice
    from ..models.decision_level import DecisionLevel
    from ..models.metadata_filter import MetadataFilter
    from ..models.modality_filter import ModalityFilter
    from ..models.node_name_filter import NodeNameFilter
    from ..models.runtime_scorer_config_class_name_to_vocab_ix_type_0 import RuntimeScorerConfigClassNameToVocabIxType0
    from ..models.runtime_scorer_config_class_name_to_vocab_ix_type_1 import RuntimeScorerConfigClassNameToVocabIxType1
    from ..models.scorer_invocation_config import ScorerInvocationConfig


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
            model_type (ModelType | None | Unset):
            invocation (None | ScorerInvocationConfig | Unset): Trusted intrinsic input requirements for synchronous direct
                invocation.
            chainpoll_template (ChainPollTemplate | None | Unset):
            metric_name (None | str | Unset):
            scorer_path_name (None | str | Unset):
            user_code (None | str | Unset):
            registered_scorer_id (None | str | Unset):
            model_alias (None | str | Unset):
            ground_truth (bool | Unset):  Default: False.
            requires_tools_in_llm_span (bool | Unset):  Default: False.
            default_model_alias (None | str | Unset):
            roll_up_strategy (None | RollUpStrategy | Unset):
            required_scorers (list[str] | None | Unset):
            required_metric_ids (list[str] | None | Unset):
            instruction (None | str | Unset):
            adapter (None | str | Unset):
            threshold (float | Unset):  Default: 0.5.
            prompt (None | str | Unset):
            lora_task_id (int | None | Unset):
            lora_weights_path (None | str | Unset):
            luna_input_type (LunaInputTypeEnum | None | Unset):
            luna_output_type (LunaOutputTypeEnum | None | Unset):
            class_name_to_vocab_ix (None | RuntimeScorerConfigClassNameToVocabIxType0 |
                RuntimeScorerConfigClassNameToVocabIxType1 | Unset):
            decision_question (None | str | Unset):
            decision_answer_options (DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None
                | Unset):
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
    model_type: ModelType | None | Unset = UNSET
    invocation: None | ScorerInvocationConfig | Unset = UNSET
    chainpoll_template: ChainPollTemplate | None | Unset = UNSET
    metric_name: None | str | Unset = UNSET
    scorer_path_name: None | str | Unset = UNSET
    user_code: None | str | Unset = UNSET
    registered_scorer_id: None | str | Unset = UNSET
    model_alias: None | str | Unset = UNSET
    ground_truth: bool | Unset = False
    requires_tools_in_llm_span: bool | Unset = False
    default_model_alias: None | str | Unset = UNSET
    roll_up_strategy: None | RollUpStrategy | Unset = UNSET
    required_scorers: list[str] | None | Unset = UNSET
    required_metric_ids: list[str] | None | Unset = UNSET
    instruction: None | str | Unset = UNSET
    adapter: None | str | Unset = UNSET
    threshold: float | Unset = 0.5
    prompt: None | str | Unset = UNSET
    lora_task_id: int | None | Unset = UNSET
    lora_weights_path: None | str | Unset = UNSET
    luna_input_type: LunaInputTypeEnum | None | Unset = UNSET
    luna_output_type: LunaOutputTypeEnum | None | Unset = UNSET
    class_name_to_vocab_ix: (
        None | RuntimeScorerConfigClassNameToVocabIxType0 | RuntimeScorerConfigClassNameToVocabIxType1 | Unset
    ) = UNSET
    decision_question: None | str | Unset = UNSET
    decision_answer_options: (
        DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
        from ..models.base_scorer_version_db import BaseScorerVersionDB
        from ..models.chain_poll_template import ChainPollTemplate
        from ..models.decision_boolean_criteria import DecisionBooleanCriteria
        from ..models.metadata_filter import MetadataFilter
        from ..models.node_name_filter import NodeNameFilter
        from ..models.runtime_scorer_config_class_name_to_vocab_ix_type_0 import (
            RuntimeScorerConfigClassNameToVocabIxType0,
        )
        from ..models.runtime_scorer_config_class_name_to_vocab_ix_type_1 import (
            RuntimeScorerConfigClassNameToVocabIxType1,
        )
        from ..models.scorer_invocation_config import ScorerInvocationConfig

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

        model_type: None | str | Unset
        if isinstance(self.model_type, Unset):
            model_type = UNSET
        elif isinstance(self.model_type, ModelType):
            model_type = self.model_type.value
        else:
            model_type = self.model_type

        invocation: dict[str, Any] | None | Unset
        if isinstance(self.invocation, Unset):
            invocation = UNSET
        elif isinstance(self.invocation, ScorerInvocationConfig):
            invocation = self.invocation.to_dict()
        else:
            invocation = self.invocation

        chainpoll_template: dict[str, Any] | None | Unset
        if isinstance(self.chainpoll_template, Unset):
            chainpoll_template = UNSET
        elif isinstance(self.chainpoll_template, ChainPollTemplate):
            chainpoll_template = self.chainpoll_template.to_dict()
        else:
            chainpoll_template = self.chainpoll_template

        metric_name: None | str | Unset
        if isinstance(self.metric_name, Unset):
            metric_name = UNSET
        else:
            metric_name = self.metric_name

        scorer_path_name: None | str | Unset
        if isinstance(self.scorer_path_name, Unset):
            scorer_path_name = UNSET
        else:
            scorer_path_name = self.scorer_path_name

        user_code: None | str | Unset
        if isinstance(self.user_code, Unset):
            user_code = UNSET
        else:
            user_code = self.user_code

        registered_scorer_id: None | str | Unset
        if isinstance(self.registered_scorer_id, Unset):
            registered_scorer_id = UNSET
        else:
            registered_scorer_id = self.registered_scorer_id

        model_alias: None | str | Unset
        if isinstance(self.model_alias, Unset):
            model_alias = UNSET
        else:
            model_alias = self.model_alias

        ground_truth = self.ground_truth

        requires_tools_in_llm_span = self.requires_tools_in_llm_span

        default_model_alias: None | str | Unset
        if isinstance(self.default_model_alias, Unset):
            default_model_alias = UNSET
        else:
            default_model_alias = self.default_model_alias

        roll_up_strategy: None | str | Unset
        if isinstance(self.roll_up_strategy, Unset):
            roll_up_strategy = UNSET
        elif isinstance(self.roll_up_strategy, RollUpStrategy):
            roll_up_strategy = self.roll_up_strategy.value
        else:
            roll_up_strategy = self.roll_up_strategy

        required_scorers: list[str] | None | Unset
        if isinstance(self.required_scorers, Unset):
            required_scorers = UNSET
        elif isinstance(self.required_scorers, list):
            required_scorers = self.required_scorers

        else:
            required_scorers = self.required_scorers

        required_metric_ids: list[str] | None | Unset
        if isinstance(self.required_metric_ids, Unset):
            required_metric_ids = UNSET
        elif isinstance(self.required_metric_ids, list):
            required_metric_ids = self.required_metric_ids

        else:
            required_metric_ids = self.required_metric_ids

        instruction: None | str | Unset
        if isinstance(self.instruction, Unset):
            instruction = UNSET
        else:
            instruction = self.instruction

        adapter: None | str | Unset
        if isinstance(self.adapter, Unset):
            adapter = UNSET
        else:
            adapter = self.adapter

        threshold = self.threshold

        prompt: None | str | Unset
        if isinstance(self.prompt, Unset):
            prompt = UNSET
        else:
            prompt = self.prompt

        lora_task_id: int | None | Unset
        if isinstance(self.lora_task_id, Unset):
            lora_task_id = UNSET
        else:
            lora_task_id = self.lora_task_id

        lora_weights_path: None | str | Unset
        if isinstance(self.lora_weights_path, Unset):
            lora_weights_path = UNSET
        else:
            lora_weights_path = self.lora_weights_path

        luna_input_type: None | str | Unset
        if isinstance(self.luna_input_type, Unset):
            luna_input_type = UNSET
        elif isinstance(self.luna_input_type, LunaInputTypeEnum):
            luna_input_type = self.luna_input_type.value
        else:
            luna_input_type = self.luna_input_type

        luna_output_type: None | str | Unset
        if isinstance(self.luna_output_type, Unset):
            luna_output_type = UNSET
        elif isinstance(self.luna_output_type, LunaOutputTypeEnum):
            luna_output_type = self.luna_output_type.value
        else:
            luna_output_type = self.luna_output_type

        class_name_to_vocab_ix: dict[str, Any] | None | Unset
        if isinstance(self.class_name_to_vocab_ix, Unset):
            class_name_to_vocab_ix = UNSET
        elif isinstance(self.class_name_to_vocab_ix, RuntimeScorerConfigClassNameToVocabIxType0):
            class_name_to_vocab_ix = self.class_name_to_vocab_ix.to_dict()
        elif isinstance(self.class_name_to_vocab_ix, RuntimeScorerConfigClassNameToVocabIxType1):
            class_name_to_vocab_ix = self.class_name_to_vocab_ix.to_dict()
        else:
            class_name_to_vocab_ix = self.class_name_to_vocab_ix

        decision_question: None | str | Unset
        if isinstance(self.decision_question, Unset):
            decision_question = UNSET
        else:
            decision_question = self.decision_question

        decision_answer_options: dict[str, Any] | list[dict[str, Any]] | list[str] | None | Unset
        if isinstance(self.decision_answer_options, Unset):
            decision_answer_options = UNSET
        elif isinstance(self.decision_answer_options, list):
            decision_answer_options = self.decision_answer_options

        elif isinstance(self.decision_answer_options, list):
            decision_answer_options = []
            for decision_answer_options_type_1_item_data in self.decision_answer_options:
                decision_answer_options_type_1_item = decision_answer_options_type_1_item_data.to_dict()
                decision_answer_options.append(decision_answer_options_type_1_item)

        elif isinstance(self.decision_answer_options, list):
            decision_answer_options = []
            for decision_answer_options_type_2_item_data in self.decision_answer_options:
                decision_answer_options_type_2_item = decision_answer_options_type_2_item_data.to_dict()
                decision_answer_options.append(decision_answer_options_type_2_item)

        elif isinstance(self.decision_answer_options, DecisionBooleanCriteria):
            decision_answer_options = self.decision_answer_options.to_dict()
        else:
            decision_answer_options = self.decision_answer_options

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
        if model_type is not UNSET:
            field_dict["model_type"] = model_type
        if invocation is not UNSET:
            field_dict["invocation"] = invocation
        if chainpoll_template is not UNSET:
            field_dict["chainpoll_template"] = chainpoll_template
        if metric_name is not UNSET:
            field_dict["metric_name"] = metric_name
        if scorer_path_name is not UNSET:
            field_dict["scorer_path_name"] = scorer_path_name
        if user_code is not UNSET:
            field_dict["user_code"] = user_code
        if registered_scorer_id is not UNSET:
            field_dict["registered_scorer_id"] = registered_scorer_id
        if model_alias is not UNSET:
            field_dict["model_alias"] = model_alias
        if ground_truth is not UNSET:
            field_dict["ground_truth"] = ground_truth
        if requires_tools_in_llm_span is not UNSET:
            field_dict["requires_tools_in_llm_span"] = requires_tools_in_llm_span
        if default_model_alias is not UNSET:
            field_dict["default_model_alias"] = default_model_alias
        if roll_up_strategy is not UNSET:
            field_dict["roll_up_strategy"] = roll_up_strategy
        if required_scorers is not UNSET:
            field_dict["required_scorers"] = required_scorers
        if required_metric_ids is not UNSET:
            field_dict["required_metric_ids"] = required_metric_ids
        if instruction is not UNSET:
            field_dict["instruction"] = instruction
        if adapter is not UNSET:
            field_dict["adapter"] = adapter
        if threshold is not UNSET:
            field_dict["threshold"] = threshold
        if prompt is not UNSET:
            field_dict["prompt"] = prompt
        if lora_task_id is not UNSET:
            field_dict["lora_task_id"] = lora_task_id
        if lora_weights_path is not UNSET:
            field_dict["lora_weights_path"] = lora_weights_path
        if luna_input_type is not UNSET:
            field_dict["luna_input_type"] = luna_input_type
        if luna_output_type is not UNSET:
            field_dict["luna_output_type"] = luna_output_type
        if class_name_to_vocab_ix is not UNSET:
            field_dict["class_name_to_vocab_ix"] = class_name_to_vocab_ix
        if decision_question is not UNSET:
            field_dict["decision_question"] = decision_question
        if decision_answer_options is not UNSET:
            field_dict["decision_answer_options"] = decision_answer_options

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.base_metric_roll_up_config_db import BaseMetricRollUpConfigDB
        from ..models.base_scorer_version_db import BaseScorerVersionDB
        from ..models.chain_poll_template import ChainPollTemplate
        from ..models.decision_boolean_criteria import DecisionBooleanCriteria
        from ..models.decision_choice import DecisionChoice
        from ..models.decision_level import DecisionLevel
        from ..models.metadata_filter import MetadataFilter
        from ..models.modality_filter import ModalityFilter
        from ..models.node_name_filter import NodeNameFilter
        from ..models.runtime_scorer_config_class_name_to_vocab_ix_type_0 import (
            RuntimeScorerConfigClassNameToVocabIxType0,
        )
        from ..models.runtime_scorer_config_class_name_to_vocab_ix_type_1 import (
            RuntimeScorerConfigClassNameToVocabIxType1,
        )
        from ..models.scorer_invocation_config import ScorerInvocationConfig

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

        def _parse_model_type(data: object) -> ModelType | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                model_type_type_0 = ModelType(data)

                return model_type_type_0
            except:  # noqa: E722
                pass
            return cast(ModelType | None | Unset, data)

        model_type = _parse_model_type(d.pop("model_type", UNSET))

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

        def _parse_chainpoll_template(data: object) -> ChainPollTemplate | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                chainpoll_template_type_0 = ChainPollTemplate.from_dict(data)

                return chainpoll_template_type_0
            except:  # noqa: E722
                pass
            return cast(ChainPollTemplate | None | Unset, data)

        chainpoll_template = _parse_chainpoll_template(d.pop("chainpoll_template", UNSET))

        def _parse_metric_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        metric_name = _parse_metric_name(d.pop("metric_name", UNSET))

        def _parse_scorer_path_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scorer_path_name = _parse_scorer_path_name(d.pop("scorer_path_name", UNSET))

        def _parse_user_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        user_code = _parse_user_code(d.pop("user_code", UNSET))

        def _parse_registered_scorer_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        registered_scorer_id = _parse_registered_scorer_id(d.pop("registered_scorer_id", UNSET))

        def _parse_model_alias(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        model_alias = _parse_model_alias(d.pop("model_alias", UNSET))

        ground_truth = d.pop("ground_truth", UNSET)

        requires_tools_in_llm_span = d.pop("requires_tools_in_llm_span", UNSET)

        def _parse_default_model_alias(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        default_model_alias = _parse_default_model_alias(d.pop("default_model_alias", UNSET))

        def _parse_roll_up_strategy(data: object) -> None | RollUpStrategy | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                roll_up_strategy_type_0 = RollUpStrategy(data)

                return roll_up_strategy_type_0
            except:  # noqa: E722
                pass
            return cast(None | RollUpStrategy | Unset, data)

        roll_up_strategy = _parse_roll_up_strategy(d.pop("roll_up_strategy", UNSET))

        def _parse_required_scorers(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                required_scorers_type_0 = cast(list[str], data)

                return required_scorers_type_0
            except:  # noqa: E722
                pass
            return cast(list[str] | None | Unset, data)

        required_scorers = _parse_required_scorers(d.pop("required_scorers", UNSET))

        def _parse_required_metric_ids(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                required_metric_ids_type_0 = cast(list[str], data)

                return required_metric_ids_type_0
            except:  # noqa: E722
                pass
            return cast(list[str] | None | Unset, data)

        required_metric_ids = _parse_required_metric_ids(d.pop("required_metric_ids", UNSET))

        def _parse_instruction(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        instruction = _parse_instruction(d.pop("instruction", UNSET))

        def _parse_adapter(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        adapter = _parse_adapter(d.pop("adapter", UNSET))

        threshold = d.pop("threshold", UNSET)

        def _parse_prompt(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        prompt = _parse_prompt(d.pop("prompt", UNSET))

        def _parse_lora_task_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        lora_task_id = _parse_lora_task_id(d.pop("lora_task_id", UNSET))

        def _parse_lora_weights_path(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        lora_weights_path = _parse_lora_weights_path(d.pop("lora_weights_path", UNSET))

        def _parse_luna_input_type(data: object) -> LunaInputTypeEnum | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                luna_input_type_type_0 = LunaInputTypeEnum(data)

                return luna_input_type_type_0
            except:  # noqa: E722
                pass
            return cast(LunaInputTypeEnum | None | Unset, data)

        luna_input_type = _parse_luna_input_type(d.pop("luna_input_type", UNSET))

        def _parse_luna_output_type(data: object) -> LunaOutputTypeEnum | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                luna_output_type_type_0 = LunaOutputTypeEnum(data)

                return luna_output_type_type_0
            except:  # noqa: E722
                pass
            return cast(LunaOutputTypeEnum | None | Unset, data)

        luna_output_type = _parse_luna_output_type(d.pop("luna_output_type", UNSET))

        def _parse_class_name_to_vocab_ix(
            data: object,
        ) -> None | RuntimeScorerConfigClassNameToVocabIxType0 | RuntimeScorerConfigClassNameToVocabIxType1 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                class_name_to_vocab_ix_type_0 = RuntimeScorerConfigClassNameToVocabIxType0.from_dict(data)

                return class_name_to_vocab_ix_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                class_name_to_vocab_ix_type_1 = RuntimeScorerConfigClassNameToVocabIxType1.from_dict(data)

                return class_name_to_vocab_ix_type_1
            except:  # noqa: E722
                pass
            return cast(
                None | RuntimeScorerConfigClassNameToVocabIxType0 | RuntimeScorerConfigClassNameToVocabIxType1 | Unset,
                data,
            )

        class_name_to_vocab_ix = _parse_class_name_to_vocab_ix(d.pop("class_name_to_vocab_ix", UNSET))

        def _parse_decision_question(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        decision_question = _parse_decision_question(d.pop("decision_question", UNSET))

        def _parse_decision_answer_options(
            data: object,
        ) -> DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                decision_answer_options_type_0 = cast(list[str], data)

                return decision_answer_options_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                decision_answer_options_type_1 = []
                _decision_answer_options_type_1 = data
                for decision_answer_options_type_1_item_data in _decision_answer_options_type_1:
                    decision_answer_options_type_1_item = DecisionChoice.from_dict(
                        decision_answer_options_type_1_item_data
                    )

                    decision_answer_options_type_1.append(decision_answer_options_type_1_item)

                return decision_answer_options_type_1
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                decision_answer_options_type_2 = []
                _decision_answer_options_type_2 = data
                for decision_answer_options_type_2_item_data in _decision_answer_options_type_2:
                    decision_answer_options_type_2_item = DecisionLevel.from_dict(
                        decision_answer_options_type_2_item_data
                    )

                    decision_answer_options_type_2.append(decision_answer_options_type_2_item)

                return decision_answer_options_type_2
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                decision_answer_options_type_3 = DecisionBooleanCriteria.from_dict(data)

                return decision_answer_options_type_3
            except:  # noqa: E722
                pass
            return cast(
                DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset, data
            )

        decision_answer_options = _parse_decision_answer_options(d.pop("decision_answer_options", UNSET))

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
            model_type=model_type,
            invocation=invocation,
            chainpoll_template=chainpoll_template,
            metric_name=metric_name,
            scorer_path_name=scorer_path_name,
            user_code=user_code,
            registered_scorer_id=registered_scorer_id,
            model_alias=model_alias,
            ground_truth=ground_truth,
            requires_tools_in_llm_span=requires_tools_in_llm_span,
            default_model_alias=default_model_alias,
            roll_up_strategy=roll_up_strategy,
            required_scorers=required_scorers,
            required_metric_ids=required_metric_ids,
            instruction=instruction,
            adapter=adapter,
            threshold=threshold,
            prompt=prompt,
            lora_task_id=lora_task_id,
            lora_weights_path=lora_weights_path,
            luna_input_type=luna_input_type,
            luna_output_type=luna_output_type,
            class_name_to_vocab_ix=class_name_to_vocab_ix,
            decision_question=decision_question,
            decision_answer_options=decision_answer_options,
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
