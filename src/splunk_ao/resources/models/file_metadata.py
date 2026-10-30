from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.content_modality import ContentModality
from ..models.file_source import FileSource
from ..models.file_status import FileStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="FileMetadata")


@_attrs_define
class FileMetadata:
    """Enriched file metadata returned to UI/SDK.

    Contains presigned URLs and properties for displaying multimodal
    content in the Galileo console and SDKs.

        Attributes:
            file_id (str):
            modality (ContentModality | str):
            source (FileSource | str):
            status (FileStatus | str):
            content_type (None | str | Unset):
            url (None | str | Unset): Presigned S3 URL or external URL
            url_expires_at (datetime.datetime | None | Unset): Expiration time
            size_bytes (int | None | Unset):
            filename (None | str | Unset):
    """

    file_id: str
    modality: ContentModality | str
    source: FileSource | str
    status: FileStatus | str
    content_type: None | str | Unset = UNSET
    url: None | str | Unset = UNSET
    url_expires_at: datetime.datetime | None | Unset = UNSET
    size_bytes: int | None | Unset = UNSET
    filename: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file_id = self.file_id

        modality: str
        if isinstance(self.modality, ContentModality):
            modality = self.modality.value
        else:
            modality = self.modality

        source: str
        if isinstance(self.source, FileSource):
            source = self.source.value
        else:
            source = self.source

        status: str
        if isinstance(self.status, FileStatus):
            status = self.status.value
        else:
            status = self.status

        content_type: None | str | Unset
        if isinstance(self.content_type, Unset):
            content_type = UNSET
        else:
            content_type = self.content_type

        url: None | str | Unset
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

        url_expires_at: None | str | Unset
        if isinstance(self.url_expires_at, Unset):
            url_expires_at = UNSET
        elif isinstance(self.url_expires_at, datetime.datetime):
            url_expires_at = self.url_expires_at.isoformat()
        else:
            url_expires_at = self.url_expires_at

        size_bytes: int | None | Unset
        if isinstance(self.size_bytes, Unset):
            size_bytes = UNSET
        else:
            size_bytes = self.size_bytes

        filename: None | str | Unset
        if isinstance(self.filename, Unset):
            filename = UNSET
        else:
            filename = self.filename

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({"file_id": file_id, "modality": modality, "source": source, "status": status})
        if content_type is not UNSET:
            field_dict["content_type"] = content_type
        if url is not UNSET:
            field_dict["url"] = url
        if url_expires_at is not UNSET:
            field_dict["url_expires_at"] = url_expires_at
        if size_bytes is not UNSET:
            field_dict["size_bytes"] = size_bytes
        if filename is not UNSET:
            field_dict["filename"] = filename

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        file_id = d.pop("file_id")

        def _parse_modality(data: object) -> ContentModality | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                modality_type_0 = ContentModality(data)

                return modality_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for modality")
            return cast(ContentModality | str, data)

        modality = _parse_modality(d.pop("modality"))

        def _parse_source(data: object) -> FileSource | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                source_type_0 = FileSource(data)

                return source_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for source")
            return cast(FileSource | str, data)

        source = _parse_source(d.pop("source"))

        def _parse_status(data: object) -> FileStatus | str:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_0 = FileStatus(data)

                return status_type_0
            except:  # noqa: E722
                pass
            if type(data) not in (str,):
                raise TypeError("Unexpected value type for status")
            return cast(FileStatus | str, data)

        status = _parse_status(d.pop("status"))

        def _parse_content_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        content_type = _parse_content_type(d.pop("content_type", UNSET))

        def _parse_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        url = _parse_url(d.pop("url", UNSET))

        def _parse_url_expires_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                url_expires_at_type_0 = datetime.datetime.fromisoformat(data)

                return url_expires_at_type_0
            except:  # noqa: E722
                pass
            return cast(datetime.datetime | None | Unset, data)

        url_expires_at = _parse_url_expires_at(d.pop("url_expires_at", UNSET))

        def _parse_size_bytes(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        size_bytes = _parse_size_bytes(d.pop("size_bytes", UNSET))

        def _parse_filename(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filename = _parse_filename(d.pop("filename", UNSET))

        file_metadata = cls(
            file_id=file_id,
            modality=modality,
            source=source,
            status=status,
            content_type=content_type,
            url=url,
            url_expires_at=url_expires_at,
            size_bytes=size_bytes,
            filename=filename,
        )

        file_metadata.additional_properties = d
        return file_metadata

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
