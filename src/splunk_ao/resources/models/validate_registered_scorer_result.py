from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.invalid_result import InvalidResult
    from ..models.valid_result import ValidResult


T = TypeVar("T", bound="ValidateRegisteredScorerResult")


@_attrs_define
class ValidateRegisteredScorerResult:
    """
    Attributes:
        result (InvalidResult | ValidResult):
        task_id (None | str | Unset):
        scorer_sha256 (None | str | Unset):
    """

    result: InvalidResult | ValidResult
    task_id: None | str | Unset = UNSET
    scorer_sha256: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.valid_result import ValidResult

        result: dict[str, Any]
        if isinstance(self.result, ValidResult):
            result = self.result.to_dict()
        else:
            result = self.result.to_dict()

        task_id: None | str | Unset
        if isinstance(self.task_id, Unset):
            task_id = UNSET
        else:
            task_id = self.task_id

        scorer_sha256: None | str | Unset
        if isinstance(self.scorer_sha256, Unset):
            scorer_sha256 = UNSET
        else:
            scorer_sha256 = self.scorer_sha256

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"result": result})
        if task_id is not UNSET:
            field_dict["task_id"] = task_id
        if scorer_sha256 is not UNSET:
            field_dict["scorer_sha256"] = scorer_sha256

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.invalid_result import InvalidResult
        from ..models.valid_result import ValidResult

        d = dict(src_dict)

        def _parse_result(data: object) -> InvalidResult | ValidResult:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                result_type_0 = ValidResult.from_dict(data)

                return result_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            result_type_1 = InvalidResult.from_dict(data)

            return result_type_1

        result = _parse_result(d.pop("result"))

        def _parse_task_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        task_id = _parse_task_id(d.pop("task_id", UNSET))

        def _parse_scorer_sha256(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scorer_sha256 = _parse_scorer_sha256(d.pop("scorer_sha256", UNSET))

        validate_registered_scorer_result = cls(result=result, task_id=task_id, scorer_sha256=scorer_sha256)

        validate_registered_scorer_result.additional_properties = d
        return validate_registered_scorer_result

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
