from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.column_mapping_config import ColumnMappingConfig
    from ..models.column_mapping_mgt_type_0 import ColumnMappingMgtType0


T = TypeVar("T", bound="ColumnMapping")


@_attrs_define
class ColumnMapping:
    """
    Attributes:
        input_ (ColumnMappingConfig | list[str] | None | Unset):
        output (ColumnMappingConfig | list[str] | None | Unset):
        generated_output (ColumnMappingConfig | list[str] | None | Unset):
        metadata (ColumnMappingConfig | list[str] | None | Unset):
        mgt (ColumnMappingMgtType0 | None | Unset):
    """

    input_: ColumnMappingConfig | list[str] | None | Unset = UNSET
    output: ColumnMappingConfig | list[str] | None | Unset = UNSET
    generated_output: ColumnMappingConfig | list[str] | None | Unset = UNSET
    metadata: ColumnMappingConfig | list[str] | None | Unset = UNSET
    mgt: ColumnMappingMgtType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.column_mapping_config import ColumnMappingConfig
        from ..models.column_mapping_mgt_type_0 import ColumnMappingMgtType0

        input_: dict[str, Any] | list[str] | None | Unset
        if isinstance(self.input_, Unset):
            input_ = UNSET
        elif isinstance(self.input_, ColumnMappingConfig):
            input_ = self.input_.to_dict()
        elif isinstance(self.input_, list):
            input_ = self.input_

        else:
            input_ = self.input_

        output: dict[str, Any] | list[str] | None | Unset
        if isinstance(self.output, Unset):
            output = UNSET
        elif isinstance(self.output, ColumnMappingConfig):
            output = self.output.to_dict()
        elif isinstance(self.output, list):
            output = self.output

        else:
            output = self.output

        generated_output: dict[str, Any] | list[str] | None | Unset
        if isinstance(self.generated_output, Unset):
            generated_output = UNSET
        elif isinstance(self.generated_output, ColumnMappingConfig):
            generated_output = self.generated_output.to_dict()
        elif isinstance(self.generated_output, list):
            generated_output = self.generated_output

        else:
            generated_output = self.generated_output

        metadata: dict[str, Any] | list[str] | None | Unset
        if isinstance(self.metadata, Unset):
            metadata = UNSET
        elif isinstance(self.metadata, ColumnMappingConfig):
            metadata = self.metadata.to_dict()
        elif isinstance(self.metadata, list):
            metadata = self.metadata

        else:
            metadata = self.metadata

        mgt: dict[str, Any] | None | Unset
        if isinstance(self.mgt, Unset):
            mgt = UNSET
        elif isinstance(self.mgt, ColumnMappingMgtType0):
            mgt = self.mgt.to_dict()
        else:
            mgt = self.mgt

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if input_ is not UNSET:
            field_dict["input"] = input_
        if output is not UNSET:
            field_dict["output"] = output
        if generated_output is not UNSET:
            field_dict["generated_output"] = generated_output
        if metadata is not UNSET:
            field_dict["metadata"] = metadata
        if mgt is not UNSET:
            field_dict["mgt"] = mgt

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.column_mapping_config import ColumnMappingConfig
        from ..models.column_mapping_mgt_type_0 import ColumnMappingMgtType0

        d = dict(src_dict)

        def _parse_input_(data: object) -> ColumnMappingConfig | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                input_type_0 = ColumnMappingConfig.from_dict(data)

                return input_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                input_type_1 = cast(list[str], data)

                return input_type_1
            except:  # noqa: E722
                pass
            return cast(ColumnMappingConfig | list[str] | None | Unset, data)

        input_ = _parse_input_(d.pop("input", UNSET))

        def _parse_output(data: object) -> ColumnMappingConfig | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                output_type_0 = ColumnMappingConfig.from_dict(data)

                return output_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                output_type_1 = cast(list[str], data)

                return output_type_1
            except:  # noqa: E722
                pass
            return cast(ColumnMappingConfig | list[str] | None | Unset, data)

        output = _parse_output(d.pop("output", UNSET))

        def _parse_generated_output(data: object) -> ColumnMappingConfig | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                generated_output_type_0 = ColumnMappingConfig.from_dict(data)

                return generated_output_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                generated_output_type_1 = cast(list[str], data)

                return generated_output_type_1
            except:  # noqa: E722
                pass
            return cast(ColumnMappingConfig | list[str] | None | Unset, data)

        generated_output = _parse_generated_output(d.pop("generated_output", UNSET))

        def _parse_metadata(data: object) -> ColumnMappingConfig | list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metadata_type_0 = ColumnMappingConfig.from_dict(data)

                return metadata_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                metadata_type_1 = cast(list[str], data)

                return metadata_type_1
            except:  # noqa: E722
                pass
            return cast(ColumnMappingConfig | list[str] | None | Unset, data)

        metadata = _parse_metadata(d.pop("metadata", UNSET))

        def _parse_mgt(data: object) -> ColumnMappingMgtType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                mgt_type_0 = ColumnMappingMgtType0.from_dict(data)

                return mgt_type_0
            except:  # noqa: E722
                pass
            return cast(ColumnMappingMgtType0 | None | Unset, data)

        mgt = _parse_mgt(d.pop("mgt", UNSET))

        column_mapping = cls(
            input_=input_, output=output, generated_output=generated_output, metadata=metadata, mgt=mgt
        )

        column_mapping.additional_properties = d
        return column_mapping

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
