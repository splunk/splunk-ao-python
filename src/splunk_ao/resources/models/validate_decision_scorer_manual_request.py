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


T = TypeVar("T", bound="ValidateDecisionScorerManualRequest")


@_attrs_define
class ValidateDecisionScorerManualRequest:
    """Test a decision evaluator on one query and response that the user types, before it is saved.

    The input is text only. The job scores a synthetic trace with one LLM span, or the span alone, at the
    one node type of scorer_configuration. reference_output is the ground truth. It is needed when
    scorer_configuration.ground_truth is true, and ignored otherwise.

        Attributes:
            model_name (str):
            question (str):
            scorer_configuration (DecisionScorerTestConfiguration): The evaluator settings of a decision Test request, the
                same place as the LLM scorer_configuration.

                scoreable_node_types holds exactly one node type. input_type defaults to the decision default
                for it (get_decision_input_type).
            query (str):
            response (str):
            answer_options (DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None |
                Unset):
            reference_output (None | str | Unset):
    """

    model_name: str
    question: str
    scorer_configuration: DecisionScorerTestConfiguration
    query: str
    response: str
    answer_options: DecisionBooleanCriteria | list[DecisionChoice] | list[DecisionLevel] | list[str] | None | Unset = (
        UNSET
    )
    reference_output: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.decision_boolean_criteria import DecisionBooleanCriteria

        model_name = self.model_name

        question = self.question

        scorer_configuration = self.scorer_configuration.to_dict()

        query = self.query

        response = self.response

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

        reference_output: None | str | Unset
        if isinstance(self.reference_output, Unset):
            reference_output = UNSET
        else:
            reference_output = self.reference_output

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "model_name": model_name,
                "question": question,
                "scorer_configuration": scorer_configuration,
                "query": query,
                "response": response,
            }
        )
        if answer_options is not UNSET:
            field_dict["answer_options"] = answer_options
        if reference_output is not UNSET:
            field_dict["reference_output"] = reference_output

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.decision_boolean_criteria import DecisionBooleanCriteria
        from ..models.decision_choice import DecisionChoice
        from ..models.decision_level import DecisionLevel
        from ..models.decision_scorer_test_configuration import DecisionScorerTestConfiguration

        d = dict(src_dict)
        model_name = d.pop("model_name")

        question = d.pop("question")

        scorer_configuration = DecisionScorerTestConfiguration.from_dict(d.pop("scorer_configuration"))

        query = d.pop("query")

        response = d.pop("response")

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

        def _parse_reference_output(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        reference_output = _parse_reference_output(d.pop("reference_output", UNSET))

        validate_decision_scorer_manual_request = cls(
            model_name=model_name,
            question=question,
            scorer_configuration=scorer_configuration,
            query=query,
            response=response,
            answer_options=answer_options,
            reference_output=reference_output,
        )

        validate_decision_scorer_manual_request.additional_properties = d
        return validate_decision_scorer_manual_request

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
