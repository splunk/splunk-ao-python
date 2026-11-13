from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.luna_dataset_mappings import LunaDatasetMappings
    from ..models.luna_semantic_mapping import LunaSemanticMapping


T = TypeVar("T", bound="LunaDatasetPreviewRequest")


@_attrs_define
class LunaDatasetPreviewRequest:
    """
    Attributes:
        mappings (list[LunaSemanticMapping] | LunaDatasetMappings):
    """

    mappings: list[LunaSemanticMapping] | LunaDatasetMappings

    def to_dict(self) -> dict[str, Any]:
        from ..models.luna_dataset_mappings import LunaDatasetMappings

        mappings: dict[str, Any] | list[dict[str, Any]]
        if isinstance(self.mappings, LunaDatasetMappings):
            mappings = self.mappings.to_dict()
        else:
            mappings = []
            for mappings_type_1_item_data in self.mappings:
                mappings_type_1_item = mappings_type_1_item_data.to_dict()
                mappings.append(mappings_type_1_item)

        field_dict: dict[str, Any] = {}

        field_dict.update({"mappings": mappings})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_mappings import LunaDatasetMappings
        from ..models.luna_semantic_mapping import LunaSemanticMapping

        d = dict(src_dict)

        def _parse_mappings(data: object) -> list[LunaSemanticMapping] | LunaDatasetMappings:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                mappings_type_0 = LunaDatasetMappings.from_dict(data)

                return mappings_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, list):
                raise TypeError()
            mappings_type_1 = []
            _mappings_type_1 = data
            for mappings_type_1_item_data in _mappings_type_1:
                mappings_type_1_item = LunaSemanticMapping.from_dict(mappings_type_1_item_data)

                mappings_type_1.append(mappings_type_1_item)

            return mappings_type_1

        mappings = _parse_mappings(d.pop("mappings"))

        luna_dataset_preview_request = cls(mappings=mappings)

        return luna_dataset_preview_request
