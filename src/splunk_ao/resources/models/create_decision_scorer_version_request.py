from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.input_type_enum import InputTypeEnum
from ..models.output_type_enum import OutputTypeEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.decision_level import DecisionLevel


T = TypeVar("T", bound="CreateDecisionScorerVersionRequest")


@_attrs_define
class CreateDecisionScorerVersionRequest:
    """The question and model for a new decision scorer version.

    The inherited scoreable_node_types, output_type and input_type are optional, but each must
    match the scorer when sent. The service checks these fields, and it checks answer_options
    against the stored output_type.

        Attributes:
            model_name (str):
            question (str):
            num_judges (int | None | Unset):
            scoreable_node_types (list[str] | None | Unset):
            cot_enabled (bool | None | Unset):
            output_type (None | OutputTypeEnum | str | Unset):
            input_type (InputTypeEnum | None | str | Unset):
            answer_options (list[DecisionLevel] | list[str] | None | Unset):
    """

    model_name: str
    question: str
    num_judges: int | None | Unset = UNSET
    scoreable_node_types: list[str] | None | Unset = UNSET
    cot_enabled: bool | None | Unset = UNSET
    output_type: None | OutputTypeEnum | str | Unset = UNSET
    input_type: InputTypeEnum | None | str | Unset = UNSET
    answer_options: list[DecisionLevel] | list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        model_name = self.model_name

        question = self.question

        num_judges: int | None | Unset
        if isinstance(self.num_judges, Unset):
            num_judges = UNSET
        else:
            num_judges = self.num_judges

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

        answer_options: list[dict[str, Any]] | list[str] | None | Unset
        if isinstance(self.answer_options, Unset):
            answer_options = UNSET
        elif isinstance(self.answer_options, list):
            answer_options = self.answer_options

        elif isinstance(self.answer_options, list):
            answer_options = []
            for answer_options_type_1_item_data in self.answer_options:
                answer_options_type_1_item = answer_options_type_1_item_data.to_dict()
                answer_options.append(answer_options_type_1_item)

        else:
            answer_options = self.answer_options

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"model_name": model_name, "question": question})
        if num_judges is not UNSET:
            field_dict["num_judges"] = num_judges
        if scoreable_node_types is not UNSET:
            field_dict["scoreable_node_types"] = scoreable_node_types
        if cot_enabled is not UNSET:
            field_dict["cot_enabled"] = cot_enabled
        if output_type is not UNSET:
            field_dict["output_type"] = output_type
        if input_type is not UNSET:
            field_dict["input_type"] = input_type
        if answer_options is not UNSET:
            field_dict["answer_options"] = answer_options

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.decision_level import DecisionLevel

        d = dict(src_dict)
        model_name = d.pop("model_name")

        question = d.pop("question")

        def _parse_num_judges(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        num_judges = _parse_num_judges(d.pop("num_judges", UNSET))

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

        def _parse_output_type(data: object) -> None | OutputTypeEnum | str | Unset:
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
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for output_type")
            return cast(None | OutputTypeEnum | str | Unset, data)

        output_type = _parse_output_type(d.pop("output_type", UNSET))

        def _parse_input_type(data: object) -> InputTypeEnum | None | str | Unset:
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
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for input_type")
            return cast(InputTypeEnum | None | str | Unset, data)

        input_type = _parse_input_type(d.pop("input_type", UNSET))

        def _parse_answer_options(data: object) -> list[DecisionLevel] | list[str] | None | Unset:
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
                    answer_options_type_1_item = DecisionLevel.from_dict(answer_options_type_1_item_data)

                    answer_options_type_1.append(answer_options_type_1_item)

                return answer_options_type_1
            except:  # noqa: E722
                pass
            return cast(list[DecisionLevel] | list[str] | None | Unset, data)

        answer_options = _parse_answer_options(d.pop("answer_options", UNSET))

        create_decision_scorer_version_request = cls(
            model_name=model_name,
            question=question,
            num_judges=num_judges,
            scoreable_node_types=scoreable_node_types,
            cot_enabled=cot_enabled,
            output_type=output_type,
            input_type=input_type,
            answer_options=answer_options,
        )

        create_decision_scorer_version_request.additional_properties = d
        return create_decision_scorer_version_request

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
