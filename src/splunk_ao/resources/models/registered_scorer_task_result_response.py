from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.registered_scorer_validation_stage import RegisteredScorerValidationStage
from ..models.task_result_status import TaskResultStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.validate_registered_scorer_result import ValidateRegisteredScorerResult


T = TypeVar("T", bound="RegisteredScorerTaskResultResponse")


@_attrs_define
class RegisteredScorerTaskResultResponse:
    """
    Attributes:
        id (str):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
        status (TaskResultStatus):
        result (None | str | Unset | ValidateRegisteredScorerResult):
        stage (None | RegisteredScorerValidationStage | Unset):
        stage_started_at (datetime.datetime | None | Unset):
    """

    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    status: TaskResultStatus
    result: None | str | Unset | ValidateRegisteredScorerResult = UNSET
    stage: None | RegisteredScorerValidationStage | Unset = UNSET
    stage_started_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.validate_registered_scorer_result import ValidateRegisteredScorerResult

        id = self.id

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        status = self.status.value

        result: dict[str, Any] | None | str | Unset
        if isinstance(self.result, Unset):
            result = UNSET
        elif isinstance(self.result, ValidateRegisteredScorerResult):
            result = self.result.to_dict()
        else:
            result = self.result

        stage: None | str | Unset
        if isinstance(self.stage, Unset):
            stage = UNSET
        elif isinstance(self.stage, RegisteredScorerValidationStage):
            stage = self.stage.value
        else:
            stage = self.stage

        stage_started_at: None | str | Unset
        if isinstance(self.stage_started_at, Unset):
            stage_started_at = UNSET
        elif isinstance(self.stage_started_at, datetime.datetime):
            stage_started_at = self.stage_started_at.isoformat()
        else:
            stage_started_at = self.stage_started_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"id": id, "created_at": created_at, "updated_at": updated_at, "status": status})
        if result is not UNSET:
            field_dict["result"] = result
        if stage is not UNSET:
            field_dict["stage"] = stage
        if stage_started_at is not UNSET:
            field_dict["stage_started_at"] = stage_started_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.validate_registered_scorer_result import ValidateRegisteredScorerResult

        d = dict(src_dict)
        id = d.pop("id")

        created_at = datetime.datetime.fromisoformat(d.pop("created_at"))

        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))

        status = TaskResultStatus(d.pop("status"))

        def _parse_result(data: object) -> None | str | Unset | ValidateRegisteredScorerResult:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                result_type_0 = ValidateRegisteredScorerResult.from_dict(data)

                return result_type_0
            except:  # noqa: E722
                pass
            return cast(None | str | Unset | ValidateRegisteredScorerResult, data)

        result = _parse_result(d.pop("result", UNSET))

        def _parse_stage(data: object) -> None | RegisteredScorerValidationStage | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                stage_type_0 = RegisteredScorerValidationStage(data)

                return stage_type_0
            except:  # noqa: E722
                pass
            return cast(None | RegisteredScorerValidationStage | Unset, data)

        stage = _parse_stage(d.pop("stage", UNSET))

        def _parse_stage_started_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                stage_started_at_type_0 = datetime.datetime.fromisoformat(data)

                return stage_started_at_type_0
            except:  # noqa: E722
                pass
            return cast(datetime.datetime | None | Unset, data)

        stage_started_at = _parse_stage_started_at(d.pop("stage_started_at", UNSET))

        registered_scorer_task_result_response = cls(
            id=id,
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            result=result,
            stage=stage,
            stage_started_at=stage_started_at,
        )

        registered_scorer_task_result_response.additional_properties = d
        return registered_scorer_task_result_response

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
