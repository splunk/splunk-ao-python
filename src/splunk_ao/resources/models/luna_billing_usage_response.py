from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.credit_balance import CreditBalance
    from ..models.project_billing_usage import ProjectBillingUsage


T = TypeVar("T", bound="LunaBillingUsageResponse")


@_attrs_define
class LunaBillingUsageResponse:
    """
    Attributes:
        total (int | None):
        credits_ (CreditBalance | None):
        credits_unavailable_reason (None | str):
        metric (Literal['luna_decision_input_tokens'] | Unset):  Default: 'luna_decision_input_tokens'.
        projects (list[ProjectBillingUsage] | Unset):
        available (bool | Unset):  Default: True.
        unavailable_reason (None | str | Unset):
    """

    total: int | None
    credits_: CreditBalance | None
    credits_unavailable_reason: None | str
    metric: Literal["luna_decision_input_tokens"] | Unset = "luna_decision_input_tokens"
    projects: list[ProjectBillingUsage] | Unset = UNSET
    available: bool | Unset = True
    unavailable_reason: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.credit_balance import CreditBalance

        total: int | None
        total = self.total

        credits_: dict[str, Any] | None
        if isinstance(self.credits_, CreditBalance):
            credits_ = self.credits_.to_dict()
        else:
            credits_ = self.credits_

        credits_unavailable_reason: None | str
        credits_unavailable_reason = self.credits_unavailable_reason

        metric = self.metric

        projects: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.projects, Unset):
            projects = []
            for projects_item_data in self.projects:
                projects_item = projects_item_data.to_dict()
                projects.append(projects_item)

        available = self.available

        unavailable_reason: None | str | Unset
        if isinstance(self.unavailable_reason, Unset):
            unavailable_reason = UNSET
        else:
            unavailable_reason = self.unavailable_reason

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {"total": total, "credits": credits_, "credits_unavailable_reason": credits_unavailable_reason}
        )
        if metric is not UNSET:
            field_dict["metric"] = metric
        if projects is not UNSET:
            field_dict["projects"] = projects
        if available is not UNSET:
            field_dict["available"] = available
        if unavailable_reason is not UNSET:
            field_dict["unavailable_reason"] = unavailable_reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.credit_balance import CreditBalance
        from ..models.project_billing_usage import ProjectBillingUsage

        d = dict(src_dict)

        def _parse_total(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        total = _parse_total(d.pop("total"))

        def _parse_credits_(data: object) -> CreditBalance | None:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                credits_type_0 = CreditBalance.from_dict(data)

                return credits_type_0
            except:  # noqa: E722
                pass
            return cast(CreditBalance | None, data)

        credits_ = _parse_credits_(d.pop("credits"))

        def _parse_credits_unavailable_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        credits_unavailable_reason = _parse_credits_unavailable_reason(d.pop("credits_unavailable_reason"))

        metric = cast(Literal["luna_decision_input_tokens"] | Unset, d.pop("metric", UNSET))
        if metric != "luna_decision_input_tokens" and not isinstance(metric, Unset):
            raise ValueError(f"metric must match const 'luna_decision_input_tokens', got '{metric}'")

        _projects = d.pop("projects", UNSET)
        projects: list[ProjectBillingUsage] | Unset = UNSET
        if _projects is not UNSET:
            projects = []
            for projects_item_data in _projects:
                projects_item = ProjectBillingUsage.from_dict(projects_item_data)

                projects.append(projects_item)

        available = d.pop("available", UNSET)

        def _parse_unavailable_reason(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        unavailable_reason = _parse_unavailable_reason(d.pop("unavailable_reason", UNSET))

        luna_billing_usage_response = cls(
            total=total,
            credits_=credits_,
            credits_unavailable_reason=credits_unavailable_reason,
            metric=metric,
            projects=projects,
            available=available,
            unavailable_reason=unavailable_reason,
        )

        luna_billing_usage_response.additional_properties = d
        return luna_billing_usage_response

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
