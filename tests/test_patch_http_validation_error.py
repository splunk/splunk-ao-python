"""Tests for scripts/patch_http_validation_error.py."""

import sys
from pathlib import Path

import pytest

# Add scripts/ to sys.path so we can import the module directly
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from patch_http_validation_error import patch  # noqa: E402

# Minimal from_dict body as produced by openapi-python-client 0.29.x,
# constructed from the regex in the patch script itself.
_UNPATCHED_0_29 = """\
    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.validation_error import ValidationError

        d = dict(src_dict)
        _detail = d.pop("detail", UNSET)
        detail: list[ValidationError] | Unset = UNSET
        if _detail is not UNSET:
            detail = []
            for detail_item_data in _detail:
                detail_item = ValidationError.from_dict(detail_item_data)

                detail.append(detail_item)

        http_validation_error = cls(detail=detail)
        return http_validation_error
"""

_ALREADY_PATCHED = """\
    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.validation_error import ValidationError

        d = dict(src_dict)
        _detail = d.pop("detail", UNSET)
        detail: list[ValidationError] | Unset = UNSET
        if isinstance(_detail, list):
            detail = [ValidationError.from_dict(item) for item in _detail]
        elif isinstance(_detail, str) and _detail:
            detail = [ValidationError(loc=[], msg=_detail, type_="server_error")]

        http_validation_error = cls(detail=detail)
        return http_validation_error
"""


def test_patch_rewrites_0_29_loop():
    """patch() replaces the 0.29 for-loop with the isinstance-guarded block."""
    result, success = patch(_UNPATCHED_0_29)

    assert success
    assert "isinstance(_detail, list)" in result
    assert "isinstance(_detail, str)" in result
    # Original for-loop is gone
    assert "for detail_item_data in _detail:" not in result
    assert "if _detail is not UNSET:" not in result


def test_patch_is_idempotent():
    """patch() on already-patched content returns success without modifying content."""
    result, success = patch(_ALREADY_PATCHED)

    assert success
    assert result == _ALREADY_PATCHED


def test_patch_returns_false_for_unknown_format():
    """patch() returns failure when neither pattern is present."""
    unrecognised = """\
    @classmethod
    def from_dict(cls, src_dict):
        d = dict(src_dict)
        detail = d.pop("detail", None)
        return cls(detail=detail)
"""
    _, success = patch(unrecognised)

    assert not success


def test_patch_preserves_indentation():
    """patch() uses the same indentation level as the source."""
    result, success = patch(_UNPATCHED_0_29)

    assert success
    # Replacement lines should start with the same 8-space indent as the input
    for line in result.splitlines():
        if "isinstance(_detail" in line:
            assert line.startswith("        ")
            break


def test_patch_committed_file_is_already_patched(tmp_path):
    """The checked-in http_validation_error.py already carries the patch sentinel."""
    committed = (
        Path(__file__).parent.parent
        / "src/splunk_ao/resources/models/http_validation_error.py"
    )
    content = committed.read_text(encoding="utf-8")

    _, success = patch(content)

    assert success
