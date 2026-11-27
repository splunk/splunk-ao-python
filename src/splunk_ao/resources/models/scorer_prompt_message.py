from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.scorer_prompt_message_content_type_1_item import ScorerPromptMessageContentType1Item


T = TypeVar("T", bound="ScorerPromptMessage")


@_attrs_define
class ScorerPromptMessage:
    """
    Attributes:
        role (str):
        content (list[ScorerPromptMessageContentType1Item] | str):
    """

    role: str
    content: list[ScorerPromptMessageContentType1Item] | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        role = self.role

        content: list[dict[str, Any]] | str
        if isinstance(self.content, list):
            content = []
            for content_type_1_item_data in self.content:
                content_type_1_item = content_type_1_item_data.to_dict()
                content.append(content_type_1_item)

        else:
            content = self.content

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"role": role, "content": content})

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.scorer_prompt_message_content_type_1_item import ScorerPromptMessageContentType1Item

        d = dict(src_dict)
        role = d.pop("role")

        def _parse_content(data: object) -> list[ScorerPromptMessageContentType1Item] | str:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                content_type_1 = []
                _content_type_1 = data
                for content_type_1_item_data in _content_type_1:
                    content_type_1_item = ScorerPromptMessageContentType1Item.from_dict(content_type_1_item_data)

                    content_type_1.append(content_type_1_item)

                return content_type_1
            except:  # noqa: E722
                pass
            return cast(list[ScorerPromptMessageContentType1Item] | str, data)

        content = _parse_content(d.pop("content"))

        scorer_prompt_message = cls(role=role, content=content)

        scorer_prompt_message.additional_properties = d
        return scorer_prompt_message

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
