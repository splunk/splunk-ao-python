from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.code_metric_policy_state import CodeMetricPolicyState

if TYPE_CHECKING:
    from ..models.policy_package_notice import PolicyPackageNotice


T = TypeVar("T", bound="CodeMetricPolicyStatus")


@_attrs_define
class CodeMetricPolicyStatus:
    """The package-policy state of one code metric's default version.

    Attributes:
        scorer_id (str):
        scorer_name (str):
        scorer_version_id (None | str):
        state (CodeMetricPolicyState):
        message (str):
        packages (list[PolicyPackageNotice]):
    """

    scorer_id: str
    scorer_name: str
    scorer_version_id: None | str
    state: CodeMetricPolicyState
    message: str
    packages: list[PolicyPackageNotice]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        scorer_id = self.scorer_id

        scorer_name = self.scorer_name

        scorer_version_id: None | str
        scorer_version_id = self.scorer_version_id

        state = self.state.value

        message = self.message

        packages = []
        for packages_item_data in self.packages:
            packages_item = packages_item_data.to_dict()
            packages.append(packages_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "scorer_id": scorer_id,
                "scorer_name": scorer_name,
                "scorer_version_id": scorer_version_id,
                "state": state,
                "message": message,
                "packages": packages,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.policy_package_notice import PolicyPackageNotice

        d = dict(src_dict)
        scorer_id = d.pop("scorer_id")

        scorer_name = d.pop("scorer_name")

        def _parse_scorer_version_id(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        scorer_version_id = _parse_scorer_version_id(d.pop("scorer_version_id"))

        state = CodeMetricPolicyState(d.pop("state"))

        message = d.pop("message")

        packages = []
        _packages = d.pop("packages")
        for packages_item_data in _packages:
            packages_item = PolicyPackageNotice.from_dict(packages_item_data)

            packages.append(packages_item)

        code_metric_policy_status = cls(
            scorer_id=scorer_id,
            scorer_name=scorer_name,
            scorer_version_id=scorer_version_id,
            state=state,
            message=message,
            packages=packages,
        )

        code_metric_policy_status.additional_properties = d
        return code_metric_policy_status

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
