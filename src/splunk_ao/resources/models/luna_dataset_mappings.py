from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_dataset_mappings_mgt import LunaDatasetMappingsMgt
    from ..models.luna_mapping_config import LunaMappingConfig


T = TypeVar("T", bound="LunaDatasetMappings")


@_attrs_define
class LunaDatasetMappings:
    """Semantic mappings shared by preview, validation, and dataset finalization.

    Attributes:
        input_ (LunaMappingConfig | None | Unset):
        output (LunaMappingConfig | None | Unset):
        label (LunaMappingConfig | None | Unset):
        evaluator_ground_truth (LunaMappingConfig | None | Unset):
        metadata (LunaMappingConfig | None | Unset):
        tools (LunaMappingConfig | None | Unset):
        documents (LunaMappingConfig | None | Unset):
        mgt (LunaDatasetMappingsMgt | Unset):
    """

    input_: LunaMappingConfig | None | Unset = UNSET
    output: LunaMappingConfig | None | Unset = UNSET
    label: LunaMappingConfig | None | Unset = UNSET
    evaluator_ground_truth: LunaMappingConfig | None | Unset = UNSET
    metadata: LunaMappingConfig | None | Unset = UNSET
    tools: LunaMappingConfig | None | Unset = UNSET
    documents: LunaMappingConfig | None | Unset = UNSET
    mgt: LunaDatasetMappingsMgt | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        from ..models.luna_mapping_config import LunaMappingConfig

        input_: dict[str, Any] | None | Unset
        if isinstance(self.input_, Unset):
            input_ = UNSET
        elif isinstance(self.input_, LunaMappingConfig):
            input_ = self.input_.to_dict()
        else:
            input_ = self.input_

        output: dict[str, Any] | None | Unset
        if isinstance(self.output, Unset):
            output = UNSET
        elif isinstance(self.output, LunaMappingConfig):
            output = self.output.to_dict()
        else:
            output = self.output

        label: dict[str, Any] | None | Unset
        if isinstance(self.label, Unset):
            label = UNSET
        elif isinstance(self.label, LunaMappingConfig):
            label = self.label.to_dict()
        else:
            label = self.label

        evaluator_ground_truth: dict[str, Any] | None | Unset
        if isinstance(self.evaluator_ground_truth, Unset):
            evaluator_ground_truth = UNSET
        elif isinstance(self.evaluator_ground_truth, LunaMappingConfig):
            evaluator_ground_truth = self.evaluator_ground_truth.to_dict()
        else:
            evaluator_ground_truth = self.evaluator_ground_truth

        metadata: dict[str, Any] | None | Unset
        if isinstance(self.metadata, Unset):
            metadata = UNSET
        elif isinstance(self.metadata, LunaMappingConfig):
            metadata = self.metadata.to_dict()
        else:
            metadata = self.metadata

        tools: dict[str, Any] | None | Unset
        if isinstance(self.tools, Unset):
            tools = UNSET
        elif isinstance(self.tools, LunaMappingConfig):
            tools = self.tools.to_dict()
        else:
            tools = self.tools

        documents: dict[str, Any] | None | Unset
        if isinstance(self.documents, Unset):
            documents = UNSET
        elif isinstance(self.documents, LunaMappingConfig):
            documents = self.documents.to_dict()
        else:
            documents = self.documents

        mgt: dict[str, Any] | Unset = UNSET
        if not isinstance(self.mgt, Unset):
            mgt = self.mgt.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if input_ is not UNSET:
            field_dict["input"] = input_
        if output is not UNSET:
            field_dict["output"] = output
        if label is not UNSET:
            field_dict["label"] = label
        if evaluator_ground_truth is not UNSET:
            field_dict["evaluator_ground_truth"] = evaluator_ground_truth
        if metadata is not UNSET:
            field_dict["metadata"] = metadata
        if tools is not UNSET:
            field_dict["tools"] = tools
        if documents is not UNSET:
            field_dict["documents"] = documents
        if mgt is not UNSET:
            field_dict["mgt"] = mgt

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_mappings_mgt import LunaDatasetMappingsMgt
        from ..models.luna_mapping_config import LunaMappingConfig

        d = dict(src_dict)

        def _parse_input_(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                input_type_0 = LunaMappingConfig.from_dict(data)

                return input_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        input_ = _parse_input_(d.pop("input", UNSET))

        def _parse_output(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                output_type_0 = LunaMappingConfig.from_dict(data)

                return output_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        output = _parse_output(d.pop("output", UNSET))

        def _parse_label(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                label_type_0 = LunaMappingConfig.from_dict(data)

                return label_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        label = _parse_label(d.pop("label", UNSET))

        def _parse_evaluator_ground_truth(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                evaluator_ground_truth_type_0 = LunaMappingConfig.from_dict(data)

                return evaluator_ground_truth_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        evaluator_ground_truth = _parse_evaluator_ground_truth(d.pop("evaluator_ground_truth", UNSET))

        def _parse_metadata(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metadata_type_0 = LunaMappingConfig.from_dict(data)

                return metadata_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        metadata = _parse_metadata(d.pop("metadata", UNSET))

        def _parse_tools(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                tools_type_0 = LunaMappingConfig.from_dict(data)

                return tools_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        tools = _parse_tools(d.pop("tools", UNSET))

        def _parse_documents(data: object) -> LunaMappingConfig | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                documents_type_0 = LunaMappingConfig.from_dict(data)

                return documents_type_0
            except:  # noqa: E722
                pass
            return cast(LunaMappingConfig | None | Unset, data)

        documents = _parse_documents(d.pop("documents", UNSET))

        _mgt = d.pop("mgt", UNSET)
        mgt: LunaDatasetMappingsMgt | Unset
        if isinstance(_mgt, Unset):
            mgt = UNSET
        else:
            mgt = LunaDatasetMappingsMgt.from_dict(_mgt)

        luna_dataset_mappings = cls(
            input_=input_,
            output=output,
            label=label,
            evaluator_ground_truth=evaluator_ground_truth,
            metadata=metadata,
            tools=tools,
            documents=documents,
            mgt=mgt,
        )

        return luna_dataset_mappings
