from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.base_finetuned_scorer_db import BaseFinetunedScorerDB
    from ..models.base_generated_scorer_db import BaseGeneratedScorerDB
    from ..models.base_luna_3_scorer_db import BaseLuna3ScorerDB
    from ..models.base_registered_scorer_db import BaseRegisteredScorerDB
    from ..models.decision_scorer_db import DecisionScorerDB


T = TypeVar("T", bound="BaseScorerVersionDB")


@_attrs_define
class BaseScorerVersionDB:
    """Scorer version from the scorer_versions table.

    Attributes:
        id (str):
        version (int):
        scorer_id (str):
        generated_scorer (BaseGeneratedScorerDB | None | Unset):
        registered_scorer (BaseRegisteredScorerDB | None | Unset):
        finetuned_scorer (BaseFinetunedScorerDB | None | Unset):
        luna3_scorer (BaseLuna3ScorerDB | None | Unset):
        decision_scorer (DecisionScorerDB | None | Unset):
        model_name (None | str | Unset):
        num_judges (int | None | Unset):
        cot_enabled (bool | None | Unset): Whether to enable chain of thought for this scorer. Defaults to False for llm
            scorers.
        runtime (None | str | Unset): The runtime a code metric version runs on, such as python3.14. Null for a version
            saved before runtimes were recorded, which runs on the legacy Python 3.12 runtime.
        code_sha256 (None | str | Unset): SHA-256 of the code bytes uploaded for a code metric version. Null for a
            version saved before digests were recorded.
    """

    id: str
    version: int
    scorer_id: str
    generated_scorer: BaseGeneratedScorerDB | None | Unset = UNSET
    registered_scorer: BaseRegisteredScorerDB | None | Unset = UNSET
    finetuned_scorer: BaseFinetunedScorerDB | None | Unset = UNSET
    luna3_scorer: BaseLuna3ScorerDB | None | Unset = UNSET
    decision_scorer: DecisionScorerDB | None | Unset = UNSET
    model_name: None | str | Unset = UNSET
    num_judges: int | None | Unset = UNSET
    cot_enabled: bool | None | Unset = UNSET
    runtime: None | str | Unset = UNSET
    code_sha256: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.base_finetuned_scorer_db import BaseFinetunedScorerDB
        from ..models.base_generated_scorer_db import BaseGeneratedScorerDB
        from ..models.base_luna_3_scorer_db import BaseLuna3ScorerDB
        from ..models.base_registered_scorer_db import BaseRegisteredScorerDB
        from ..models.decision_scorer_db import DecisionScorerDB

        id = self.id

        version = self.version

        scorer_id = self.scorer_id

        generated_scorer: dict[str, Any] | None | Unset
        if isinstance(self.generated_scorer, Unset):
            generated_scorer = UNSET
        elif isinstance(self.generated_scorer, BaseGeneratedScorerDB):
            generated_scorer = self.generated_scorer.to_dict()
        else:
            generated_scorer = self.generated_scorer

        registered_scorer: dict[str, Any] | None | Unset
        if isinstance(self.registered_scorer, Unset):
            registered_scorer = UNSET
        elif isinstance(self.registered_scorer, BaseRegisteredScorerDB):
            registered_scorer = self.registered_scorer.to_dict()
        else:
            registered_scorer = self.registered_scorer

        finetuned_scorer: dict[str, Any] | None | Unset
        if isinstance(self.finetuned_scorer, Unset):
            finetuned_scorer = UNSET
        elif isinstance(self.finetuned_scorer, BaseFinetunedScorerDB):
            finetuned_scorer = self.finetuned_scorer.to_dict()
        else:
            finetuned_scorer = self.finetuned_scorer

        luna3_scorer: dict[str, Any] | None | Unset
        if isinstance(self.luna3_scorer, Unset):
            luna3_scorer = UNSET
        elif isinstance(self.luna3_scorer, BaseLuna3ScorerDB):
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

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"id": id, "version": version, "scorer_id": scorer_id})
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

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.base_finetuned_scorer_db import BaseFinetunedScorerDB
        from ..models.base_generated_scorer_db import BaseGeneratedScorerDB
        from ..models.base_luna_3_scorer_db import BaseLuna3ScorerDB
        from ..models.base_registered_scorer_db import BaseRegisteredScorerDB
        from ..models.decision_scorer_db import DecisionScorerDB

        d = dict(src_dict)
        id = d.pop("id")

        version = d.pop("version")

        scorer_id = d.pop("scorer_id")

        def _parse_generated_scorer(data: object) -> BaseGeneratedScorerDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                generated_scorer_type_0 = BaseGeneratedScorerDB.from_dict(data)

                return generated_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(BaseGeneratedScorerDB | None | Unset, data)

        generated_scorer = _parse_generated_scorer(d.pop("generated_scorer", UNSET))

        def _parse_registered_scorer(data: object) -> BaseRegisteredScorerDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                registered_scorer_type_0 = BaseRegisteredScorerDB.from_dict(data)

                return registered_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(BaseRegisteredScorerDB | None | Unset, data)

        registered_scorer = _parse_registered_scorer(d.pop("registered_scorer", UNSET))

        def _parse_finetuned_scorer(data: object) -> BaseFinetunedScorerDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                finetuned_scorer_type_0 = BaseFinetunedScorerDB.from_dict(data)

                return finetuned_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(BaseFinetunedScorerDB | None | Unset, data)

        finetuned_scorer = _parse_finetuned_scorer(d.pop("finetuned_scorer", UNSET))

        def _parse_luna3_scorer(data: object) -> BaseLuna3ScorerDB | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                luna3_scorer_type_0 = BaseLuna3ScorerDB.from_dict(data)

                return luna3_scorer_type_0
            except:  # noqa: E722
                pass
            return cast(BaseLuna3ScorerDB | None | Unset, data)

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

        base_scorer_version_db = cls(
            id=id,
            version=version,
            scorer_id=scorer_id,
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
        )

        base_scorer_version_db.additional_properties = d
        return base_scorer_version_db

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
