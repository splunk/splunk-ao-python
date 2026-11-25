from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.luna_dataset_preview_request_validation_error_ctx_type_0 import (
        LunaDatasetPreviewRequestValidationErrorCtxType0,
    )


T = TypeVar("T", bound="LunaDatasetPreviewRequestValidationError")


@_attrs_define
class LunaDatasetPreviewRequestValidationError:
    """
    Attributes:
        loc (list[int | str]):
        msg (str):
        type_ (str):
        input_ (Any | None | Unset):
        ctx (LunaDatasetPreviewRequestValidationErrorCtxType0 | None | Unset):
    """

    loc: list[int | str]
    msg: str
    type_: str
    input_: Any | None | Unset = UNSET
    ctx: LunaDatasetPreviewRequestValidationErrorCtxType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.luna_dataset_preview_request_validation_error_ctx_type_0 import (
            LunaDatasetPreviewRequestValidationErrorCtxType0,
        )

        loc = []
        for loc_item_data in self.loc:
            loc_item: int | str
            loc_item = loc_item_data
            loc.append(loc_item)

        msg = self.msg

        type_ = self.type_

        input_: Any | None | Unset
        if isinstance(self.input_, Unset):
            input_ = UNSET
        else:
            input_ = self.input_

        ctx: dict[str, Any] | None | Unset
        if isinstance(self.ctx, Unset):
            ctx = UNSET
        elif isinstance(self.ctx, LunaDatasetPreviewRequestValidationErrorCtxType0):
            ctx = self.ctx.to_dict()
        else:
            ctx = self.ctx

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"loc": loc, "msg": msg, "type": type_})
        if input_ is not UNSET:
            field_dict["input"] = input_
        if ctx is not UNSET:
            field_dict["ctx"] = ctx

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.luna_dataset_preview_request_validation_error_ctx_type_0 import (
            LunaDatasetPreviewRequestValidationErrorCtxType0,
        )

        d = dict(src_dict)
        loc = []
        _loc = d.pop("loc")
        for loc_item_data in _loc:

            def _parse_loc_item(data: object) -> int | str:
                return cast(int | str, data)

            loc_item = _parse_loc_item(loc_item_data)

            loc.append(loc_item)

        msg = d.pop("msg")

        type_ = d.pop("type")

        def _parse_input_(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        input_ = _parse_input_(d.pop("input", UNSET))

        def _parse_ctx(data: object) -> LunaDatasetPreviewRequestValidationErrorCtxType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                ctx_type_0 = LunaDatasetPreviewRequestValidationErrorCtxType0.from_dict(data)

                return ctx_type_0
            except:  # noqa: E722
                pass
            return cast(LunaDatasetPreviewRequestValidationErrorCtxType0 | None | Unset, data)

        ctx = _parse_ctx(d.pop("ctx", UNSET))

        luna_dataset_preview_request_validation_error = cls(loc=loc, msg=msg, type_=type_, input_=input_, ctx=ctx)

        luna_dataset_preview_request_validation_error.additional_properties = d
        return luna_dataset_preview_request_validation_error

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
