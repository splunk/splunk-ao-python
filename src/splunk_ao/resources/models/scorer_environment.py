from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.environment_tier import EnvironmentTier
from ..types import UNSET, Unset

T = TypeVar("T", bound="ScorerEnvironment")


@_attrs_define
class ScorerEnvironment:
    """Which execution environment the validated scorer was classified into.

    Produced by the runners validation job, which resolves the scorer's
    dependencies against the standard environment using the same uv binary and
    package index the executor installs from. Absent when the deployment has
    no standard environment configured, which is the default.

    The API does **not** trust the copy a client posts back at save time; it
    re-reads this from the stored task result. The fields travel here so the
    runner has somewhere to persist them, not as an input to the save.

        Attributes:
            tier (EnvironmentTier | str):
            env_hash (str):
            runtime (None | str | Unset):
            lockfile (None | str | Unset):
            includes_standard (bool | Unset):  Default: True.
    """

    tier: EnvironmentTier | str
    env_hash: str
    runtime: None | str | Unset = UNSET
    lockfile: None | str | Unset = UNSET
    includes_standard: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        tier: str
        if isinstance(self.tier, EnvironmentTier):
            tier = self.tier.value
        else:
            tier = self.tier

        env_hash = self.env_hash

        runtime: None | str | Unset
        if isinstance(self.runtime, Unset):
            runtime = UNSET
        else:
            runtime = self.runtime

        lockfile: None | str | Unset
        if isinstance(self.lockfile, Unset):
            lockfile = UNSET
        else:
            lockfile = self.lockfile

        includes_standard = self.includes_standard

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"tier": tier, "env_hash": env_hash})
        if runtime is not UNSET:
            field_dict["runtime"] = runtime
        if lockfile is not UNSET:
            field_dict["lockfile"] = lockfile
        if includes_standard is not UNSET:
            field_dict["includes_standard"] = includes_standard

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_tier(data: object) -> EnvironmentTier | str:

            try:
                if not isinstance(data, str):
                    raise TypeError()
                tier_type_0 = EnvironmentTier(data)

                return tier_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for tier")
            return cast(EnvironmentTier | str, data)

        tier = _parse_tier(d.pop("tier"))

        env_hash = d.pop("env_hash")

        def _parse_runtime(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data

            return cast(None | str | Unset, data)

        runtime = _parse_runtime(d.pop("runtime", UNSET))

        def _parse_lockfile(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data

            return cast(None | str | Unset, data)

        lockfile = _parse_lockfile(d.pop("lockfile", UNSET))

        includes_standard = d.pop("includes_standard", UNSET)

        scorer_environment = cls(
            tier=tier, env_hash=env_hash, runtime=runtime, lockfile=lockfile, includes_standard=includes_standard
        )

        scorer_environment.additional_properties = d
        return scorer_environment

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
