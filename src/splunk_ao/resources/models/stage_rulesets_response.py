from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.stage_type import StageType

if TYPE_CHECKING:
    from ..models.ruleset import Ruleset


T = TypeVar("T", bound="StageRulesetsResponse")


@_attrs_define
class StageRulesetsResponse:
    """The rulesets of a stage's current version, or a local stage's newest version.

    Attributes:
        stage_id (str):
        stage_type (StageType | str):
        version (int | None): The stage version the rulesets come from. None for a local stage that no invoke has
            reached yet.
        rulesets (list[Ruleset]): The rulesets of the version. Protect stores no ruleset order, so the list order is not
            a priority.
    """

    stage_id: str
    stage_type: StageType | str
    version: int | None
    rulesets: list[Ruleset]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        stage_id = self.stage_id

        stage_type: str
        if isinstance(self.stage_type, StageType):
            stage_type = self.stage_type.value
        else:
            stage_type = self.stage_type

        version: int | None
        version = self.version

        rulesets = []
        for rulesets_item_data in self.rulesets:
            rulesets_item = rulesets_item_data.to_dict()
            rulesets.append(rulesets_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"stage_id": stage_id, "stage_type": stage_type, "version": version, "rulesets": rulesets})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ruleset import Ruleset

        d = dict(src_dict)
        stage_id = d.pop("stage_id")

        def _parse_stage_type(data: object) -> StageType | str:

            try:
                if not isinstance(data, str):
                    raise TypeError()
                stage_type_type_0 = StageType(data)

                return stage_type_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for stage_type")
            return cast(StageType | str, data)

        stage_type = _parse_stage_type(d.pop("stage_type"))

        def _parse_version(data: object) -> int | None:
            if data is None:
                return data

            return cast(int | None, data)

        version = _parse_version(d.pop("version"))

        rulesets = []
        _rulesets = d.pop("rulesets")

        for rulesets_item_data in _rulesets:
            rulesets_item = Ruleset.from_dict(rulesets_item_data)

            rulesets.append(rulesets_item)

        stage_rulesets_response = cls(stage_id=stage_id, stage_type=stage_type, version=version, rulesets=rulesets)

        stage_rulesets_response.additional_properties = d
        return stage_rulesets_response

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
