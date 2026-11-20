from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

T = TypeVar("T", bound="CodeMetricPolicyStatusRequest")


@_attrs_define
class CodeMetricPolicyStatusRequest:
    """
    Attributes:
        scorer_ids (list[str]):
    """

    scorer_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        scorer_ids = self.scorer_ids

        field_dict: dict[str, Any] = {}

        field_dict.update({"scorer_ids": scorer_ids})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        scorer_ids = cast(list[str], d.pop("scorer_ids"))

        code_metric_policy_status_request = cls(scorer_ids=scorer_ids)

        return code_metric_policy_status_request
