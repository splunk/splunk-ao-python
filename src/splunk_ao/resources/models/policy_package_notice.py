from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.violation_reason import ViolationReason

T = TypeVar("T", bound="PolicyPackageNotice")


@_attrs_define
class PolicyPackageNotice:
    """
    Attributes:
        package (str):
        version (str):
        reason (ViolationReason):
        advisory_id (None | str):
        blocked_from (datetime.date | None):
    """

    package: str
    version: str
    reason: ViolationReason
    advisory_id: None | str
    blocked_from: datetime.date | None
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        package = self.package

        version = self.version

        reason = self.reason.value

        advisory_id: None | str
        advisory_id = self.advisory_id

        blocked_from: None | str
        if isinstance(self.blocked_from, datetime.date):
            blocked_from = self.blocked_from.isoformat()
        else:
            blocked_from = self.blocked_from

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "package": package,
                "version": version,
                "reason": reason,
                "advisory_id": advisory_id,
                "blocked_from": blocked_from,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        package = d.pop("package")

        version = d.pop("version")

        reason = ViolationReason(d.pop("reason"))

        def _parse_advisory_id(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        advisory_id = _parse_advisory_id(d.pop("advisory_id"))

        def _parse_blocked_from(data: object) -> datetime.date | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                blocked_from_type_0 = datetime.date.fromisoformat(data)

                return blocked_from_type_0
            except:  # noqa: E722
                pass
            return cast(datetime.date | None, data)

        blocked_from = _parse_blocked_from(d.pop("blocked_from"))

        policy_package_notice = cls(
            package=package, version=version, reason=reason, advisory_id=advisory_id, blocked_from=blocked_from
        )

        policy_package_notice.additional_properties = d
        return policy_package_notice

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
