from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.output_type_enum import OutputTypeEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chain_poll_template import ChainPollTemplate
    from ..models.create_update_registered_scorer_response import CreateUpdateRegisteredScorerResponse
    from ..models.decision_scorer_db import DecisionScorerDB
    from ..models.fine_tuned_scorer_response import FineTunedScorerResponse
    from ..models.generated_scorer_response import GeneratedScorerResponse
    from ..models.luna_3_scorer_response import Luna3ScorerResponse


T = TypeVar("T", bound="BaseScorerVersionResponse")


@_attrs_define
class BaseScorerVersionResponse:
    """
    Attributes:
        id (str):
        version (int):
        scorer_id (str):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
        generated_scorer (GeneratedScorerResponse | None | Unset):
        registered_scorer (CreateUpdateRegisteredScorerResponse | None | Unset):
        finetuned_scorer (FineTunedScorerResponse | None | Unset):
        luna3_scorer (Luna3ScorerResponse | None | Unset):
        decision_scorer (DecisionScorerDB | None | Unset):
        model_name (None | str | Unset):
        num_judges (int | None | Unset):
        cot_enabled (bool | None | Unset):
        runtime (None | str | Unset): The runtime a code metric version runs on, such as python3.14. Null for a version
            saved before runtimes were recorded, which runs on the legacy Python 3.12 runtime.
        code_sha256 (None | str | Unset): SHA-256 of the code bytes uploaded for a code metric version. Null for a
            version saved before digests were recorded.
        chain_poll_template (ChainPollTemplate | None | Unset):
        scoreable_node_types (list[str] | None | Unset):
        output_type (None | OutputTypeEnum | Unset):
        allowed_model (bool | None | Unset):
        created_by (None | str | Unset):
        validation_task_id (None | str | Unset):
        request_id (None | str | Unset):
    """

    id: str
    version: int
    scorer_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    generated_scorer: GeneratedScorerResponse | None | Unset = UNSET
    registered_scorer: CreateUpdateRegisteredScorerResponse | None | Unset = UNSET
    finetuned_scorer: FineTunedScorerResponse | None | Unset = UNSET
    luna3_scorer: Luna3ScorerResponse | None | Unset = UNSET
    decision_scorer: DecisionScorerDB | None | Unset = UNSET
    model_name: None | str | Unset = UNSET
    num_judges: int | None | Unset = UNSET
    cot_enabled: bool | None | Unset = UNSET
    runtime: None | str | Unset = UNSET
    code_sha256: None | str | Unset = UNSET
    chain_poll_template: ChainPollTemplate | None | Unset = UNSET
    scoreable_node_types: list[str] | None | Unset = UNSET
    output_type: None | OutputTypeEnum | Unset = UNSET
    allowed_model: bool | None | Unset = UNSET
    created_by: None | str | Unset = UNSET
    validation_task_id: None | str | Unset = UNSET
    request_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.chain_poll_template import ChainPollTemplate
        from ..models.create_update_registered_scorer_response import CreateUpdateRegisteredScorerResponse
        from ..models.decision_scorer_db import DecisionScorerDB
        from ..models.fine_tuned_scorer_response import FineTunedScorerResponse
        from ..models.generated_scorer_response import GeneratedScorerResponse
        from ..models.luna_3_scorer_response import Luna3ScorerResponse

        id = self.id

        version = self.version

        scorer_id = self.scorer_id

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        generated_scorer: dict[str, Any] | None | Unset
        if isinstance(self.generated_scorer, Unset):
            generated_scorer = UNSET
        elif isinstance(self.generated_scorer, GeneratedScorerResponse):
            generated_scorer = self.generated_scorer.to_dict()
        else:
            generated_scorer = self.generated_scorer

        registered_scorer: dict[str, Any] | None | Unset
        if isinstance(self.registered_scorer, Unset):
            registered_scorer = UNSET
        elif isinstance(self.registered_scorer, CreateUpdateRegisteredScorerResponse):
            registered_scorer = self.registered_scorer.to_dict()
        else:
            registered_scorer = self.registered_scorer

        finetuned_scorer: dict[str, Any] | None | Unset
        if isinstance(self.finetuned_scorer, Unset):
            finetuned_scorer = UNSET
        elif isinstance(self.finetuned_scorer, FineTunedScorerResponse):
            finetuned_scorer = self.finetuned_scorer.to_dict()
        else:
            finetuned_scorer = self.finetuned_scorer

        luna3_scorer: dict[str, Any] | None | Unset
        if isinstance(self.luna3_scorer, Unset):
            luna3_scorer = UNSET
        elif isinstance(self.luna3_scorer, Luna3ScorerResponse):
            luna3_scorer = self.luna3_scorer.to_dict()
        else:
            luna3_scorer = self.luna3_scorer

        decision_scorer: dict[str, Any] | None | Unset
        if isinstance(self.decision_scorer, Unset):
            decision_scorer = UNSET
        elif isinstance(self.decision_scorer, DecisionScorerDB):
            decision_scorer = self.decision_scorer.to_dict()
        else:
            decision_scorer = self.decision_scorer

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

        cot_enabled: bool | None | Unset
        if isinstance(self.cot_enabled, Unset):
            cot_enabled = UNSET
        else:
            cot_enabled = self.cot_enabled

        runtime: None | str | Unset
        if isinstance(self.runtime, Unset):
            runtime = UNSET
        else:
            runtime = self.runtime

        code_sha256: None | str | Unset
        if isinstance(self.code_sha256, Unset):
            code_sha256 = UNSET
        else:
            code_sha256 = self.code_sha256

        chain_poll_template: dict[str, Any] | None | Unset
        if isinstance(self.chain_poll_template, Unset):
            chain_poll_template = UNSET
        elif isinstance(self.chain_poll_template, ChainPollTemplate):
            chain_poll_template = self.chain_poll_template.to_dict()
        else:
            chain_poll_template = self.chain_poll_template

        scoreable_node_types: list[str] | None | Unset
        if isinstance(self.scoreable_node_types, Unset):
            scoreable_node_types = UNSET
        elif isinstance(self.scoreable_node_types, list):
            scoreable_node_types = self.scoreable_node_types

        else:
            scoreable_node_types = self.scoreable_node_types

        output_type: None | str | Unset
        if isinstance(self.output_type, Unset):
            output_type = UNSET
        elif isinstance(self.output_type, OutputTypeEnum):
            output_type = self.output_type.value
        else:
            output_type = self.output_type

        allowed_model: bool | None | Unset
        if isinstance(self.allowed_model, Unset):
            allowed_model = UNSET
        else:
            allowed_model = self.allowed_model

        created_by: None | str | Unset
        if isinstance(self.created_by, Unset):
            created_by = UNSET
        else:
            created_by = self.created_by

        validation_task_id: None | str | Unset
        if isinstance(self.validation_task_id, Unset):
            validation_task_id = UNSET
        else:
            validation_task_id = self.validation_task_id

        request_id: None | str | Unset
        if isinstance(self.request_id, Unset):
            request_id = UNSET
        else:
            request_id = self.request_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {"id": id, "version": version, "scorer_id": scorer_id, "created_at": created_at, "updated_at": updated_at}
        )
        if generated_scorer is not UNSET:
            field_dict["generated_scorer"] = generated_scorer
        if registered_scorer is not UNSET:
            field_dict["registered_scorer"] = registered_scorer
        if finetuned_scorer is not UNSET:
            field_dict["finetuned_scorer"] = finetuned_scorer
        if luna3_scorer is not UNSET:
            field_dict["luna3_scorer"] = luna3_scorer
        if decision_scorer is not UNSET:
            field_dict["decision_scorer"] = decision_scorer
        if model_name is not UNSET:
            field_dict["model_name"] = model_name
        if num_judges is not UNSET:
            field_dict["num_judges"] = num_judges
        if cot_enabled is not UNSET:
            field_dict["cot_enabled"] = cot_enabled
        if runtime is not UNSET:
            field_dict["runtime"] = runtime
        if code_sha256 is not UNSET:
            field_dict["code_sha256"] = code_sha256
        if chain_poll_template is not UNSET:
            field_dict["chain_poll_template"] = chain_poll_template
        if scoreable_node_types is not UNSET:
            field_dict["scoreable_node_types"] = scoreable_node_types
        if output_type is not UNSET:
            field_dict["output_type"] = output_type
        if allowed_model is not UNSET:
            field_dict["allowed_model"] = allowed_model
        if created_by is not UNSET:
            field_dict["created_by"] = created_by
        if validation_task_id is not UNSET:
            field_dict["validation_task_id"] = validation_task_id
        if request_id is not UNSET:
            field_dict["request_id"] = request_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chain_poll_template import ChainPollTemplate
        from ..models.create_update_registered_scorer_response import CreateUpdateRegisteredScorerResponse
        from ..models.decision_scorer_db import DecisionScorerDB
        from ..models.fine_tuned_scorer_response import FineTunedScorerResponse
        from ..models.generated_scorer_response import GeneratedScorerResponse
        from ..models.luna_3_scorer_response import Luna3ScorerResponse

        d = dict(src_dict)
        id = d.pop("id")

        version = d.pop("version")

        scorer_id = d.pop("scorer_id")

        created_at = datetime.datetime.fromisoformat(d.pop("created_at"))

        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))

        def _parse_generated_scorer(data: object) -> GeneratedScorerResponse | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                generated_scorer_type_0 = GeneratedScorerResponse.from_dict(data)

                return generated_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(GeneratedScorerResponse | None | Unset, data)

        generated_scorer = _parse_generated_scorer(d.pop("generated_scorer", UNSET))

        def _parse_registered_scorer(data: object) -> CreateUpdateRegisteredScorerResponse | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                registered_scorer_type_0 = CreateUpdateRegisteredScorerResponse.from_dict(data)

                return registered_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(CreateUpdateRegisteredScorerResponse | None | Unset, data)

        registered_scorer = _parse_registered_scorer(d.pop("registered_scorer", UNSET))

        def _parse_finetuned_scorer(data: object) -> FineTunedScorerResponse | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                finetuned_scorer_type_0 = FineTunedScorerResponse.from_dict(data)

                return finetuned_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(FineTunedScorerResponse | None | Unset, data)

        finetuned_scorer = _parse_finetuned_scorer(d.pop("finetuned_scorer", UNSET))

        def _parse_luna3_scorer(data: object) -> Luna3ScorerResponse | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                luna3_scorer_type_0 = Luna3ScorerResponse.from_dict(data)

                return luna3_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(Luna3ScorerResponse | None | Unset, data)

        luna3_scorer = _parse_luna3_scorer(d.pop("luna3_scorer", UNSET))

        def _parse_decision_scorer(data: object) -> DecisionScorerDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                decision_scorer_type_0 = DecisionScorerDB.from_dict(data)

                return decision_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(DecisionScorerDB | None | Unset, data)

        decision_scorer = _parse_decision_scorer(d.pop("decision_scorer", UNSET))

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

        def _parse_cot_enabled(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        cot_enabled = _parse_cot_enabled(d.pop("cot_enabled", UNSET))

        def _parse_runtime(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        runtime = _parse_runtime(d.pop("runtime", UNSET))

        def _parse_code_sha256(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        code_sha256 = _parse_code_sha256(d.pop("code_sha256", UNSET))

        def _parse_chain_poll_template(data: object) -> ChainPollTemplate | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                chain_poll_template_type_0 = ChainPollTemplate.from_dict(data)

                return chain_poll_template_type_0
            except:  # noqa: E722
                pass
            return cast(ChainPollTemplate | None | Unset, data)

        chain_poll_template = _parse_chain_poll_template(d.pop("chain_poll_template", UNSET))

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

        def _parse_allowed_model(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        allowed_model = _parse_allowed_model(d.pop("allowed_model", UNSET))

        def _parse_created_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_by = _parse_created_by(d.pop("created_by", UNSET))

        def _parse_validation_task_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        validation_task_id = _parse_validation_task_id(d.pop("validation_task_id", UNSET))

        def _parse_request_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        request_id = _parse_request_id(d.pop("request_id", UNSET))

        base_scorer_version_response = cls(
            id=id,
            version=version,
            scorer_id=scorer_id,
            created_at=created_at,
            updated_at=updated_at,
            generated_scorer=generated_scorer,
            registered_scorer=registered_scorer,
            finetuned_scorer=finetuned_scorer,
            luna3_scorer=luna3_scorer,
            decision_scorer=decision_scorer,
            model_name=model_name,
            num_judges=num_judges,
            cot_enabled=cot_enabled,
            runtime=runtime,
            code_sha256=code_sha256,
            chain_poll_template=chain_poll_template,
            scoreable_node_types=scoreable_node_types,
            output_type=output_type,
            allowed_model=allowed_model,
            created_by=created_by,
            validation_task_id=validation_task_id,
            request_id=request_id,
        )

        base_scorer_version_response.additional_properties = d
        return base_scorer_version_response

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
