from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.decision_boolean_criteria import DecisionBooleanCriteria
    from ..models.decision_choice import DecisionChoice
    from ..models.decision_level import DecisionLevel
    from ..models.decision_scorer_test_configuration import DecisionScorerTestConfiguration


T = TypeVar("T", bound="ValidateDecisionScorerDatasetRequest")


@_attrs_define
class ValidateDecisionScorerDatasetRequest:
    """Test a decision evaluator on dataset rows. The dataset fields select the rows.

    dataset_id, dataset_version_index, limit and starting_token have the same meaning and defaults
    as in the LLM dataset request. scoreable_node_types must be trace or llm.

        Attributes:
            dataset_id (str):
            model_name (str):
            question (str):
            scorer_configuration (DecisionScorerTestConfiguration): The evaluator settings of a decision Test request, the
                same place as the LLM scorer_configuration.

                scoreable_node_types holds exactly one node type. input_type defaults to the decision default
                for it (get_decision_input_type).
            dataset_version_index (int | None | Unset):
            limit (int | Unset): Maximum number of dataset rows to process. Default: 100.
            starting_token (int | None | Unset): Pagination offset into dataset rows.
            answer_options (DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None |
                Unset):
    """

    dataset_id: str
    model_name: str
    question: str
    scorer_configuration: DecisionScorerTestConfiguration
    dataset_version_index: int | None | Unset = UNSET
    limit: int | Unset = 100
    starting_token: int | None | Unset = UNSET
    answer_options: DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset = (
        UNSET
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.decision_boolean_criteria import DecisionBooleanCriteria

        dataset_id = self.dataset_id

        model_name = self.model_name

        question = self.question

        scorer_configuration = self.scorer_configuration.to_dict()

        dataset_version_index: int | None | Unset
        if isinstance(self.dataset_version_index, Unset):
            dataset_version_index = UNSET
        else:
            dataset_version_index = self.dataset_version_index

        limit = self.limit

        starting_token: int | None | Unset
        if isinstance(self.starting_token, Unset):
            starting_token = UNSET
        else:
            starting_token = self.starting_token

        answer_options: dict[str, Any] | list[dict[str, Any]] | list[str] | None | Unset
        if isinstance(self.answer_options, Unset):
            answer_options = UNSET
        elif isinstance(self.answer_options, list):
            answer_options = self.answer_options

        elif isinstance(self.answer_options, list):
            answer_options = []
            for answer_options_type_1_item_data in self.answer_options:
                answer_options_type_1_item = answer_options_type_1_item_data.to_dict()
                answer_options.append(answer_options_type_1_item)

        elif isinstance(self.answer_options, list):
            answer_options = []
            for answer_options_type_2_item_data in self.answer_options:
                answer_options_type_2_item = answer_options_type_2_item_data.to_dict()
                answer_options.append(answer_options_type_2_item)

        elif isinstance(self.answer_options, DecisionBooleanCriteria):
            answer_options = self.answer_options.to_dict()
        else:
            answer_options = self.answer_options

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "dataset_id": dataset_id,
                "model_name": model_name,
                "question": question,
                "scorer_configuration": scorer_configuration,
            }
        )
        if dataset_version_index is not UNSET:
            field_dict["dataset_version_index"] = dataset_version_index
        if limit is not UNSET:
            field_dict["limit"] = limit
        if starting_token is not UNSET:
            field_dict["starting_token"] = starting_token
        if answer_options is not UNSET:
            field_dict["answer_options"] = answer_options

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.decision_boolean_criteria import DecisionBooleanCriteria
        from ..models.decision_choice import DecisionChoice
        from ..models.decision_level import DecisionLevel
        from ..models.decision_scorer_test_configuration import DecisionScorerTestConfiguration

        d = dict(src_dict)
        dataset_id = d.pop("dataset_id")

        model_name = d.pop("model_name")

        question = d.pop("question")

        scorer_configuration = DecisionScorerTestConfiguration.from_dict(d.pop("scorer_configuration"))

        def _parse_dataset_version_index(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        dataset_version_index = _parse_dataset_version_index(d.pop("dataset_version_index", UNSET))

        limit = d.pop("limit", UNSET)

        def _parse_starting_token(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        starting_token = _parse_starting_token(d.pop("starting_token", UNSET))

        def _parse_answer_options(
            data: object,
        ) -> DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                answer_options_type_0 = cast(list[str], data)

                return answer_options_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                answer_options_type_1 = []
                _answer_options_type_1 = data
                for answer_options_type_1_item_data in _answer_options_type_1:
                    answer_options_type_1_item = DecisionChoice.from_dict(answer_options_type_1_item_data)

                    answer_options_type_1.append(answer_options_type_1_item)

                return answer_options_type_1
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                answer_options_type_2 = []
                _answer_options_type_2 = data
                for answer_options_type_2_item_data in _answer_options_type_2:
                    answer_options_type_2_item = DecisionLevel.from_dict(answer_options_type_2_item_data)

                    answer_options_type_2.append(answer_options_type_2_item)

                return answer_options_type_2
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                answer_options_type_3 = DecisionBooleanCriteria.from_dict(data)

                return answer_options_type_3
            except:  # noqa: E722
                pass
            return cast(
                DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset, data
            )

        answer_options = _parse_answer_options(d.pop("answer_options", UNSET))

        validate_decision_scorer_dataset_request = cls(
            dataset_id=dataset_id,
            model_name=model_name,
            question=question,
            scorer_configuration=scorer_configuration,
            dataset_version_index=dataset_version_index,
            limit=limit,
            starting_token=starting_token,
            answer_options=answer_options,
        )

        validate_decision_scorer_dataset_request.additional_properties = d
        return validate_decision_scorer_dataset_request

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
