"""Tests for MDX helper functions in scripts/create_docs.py.

Covers _escape_curly_braces, _convert_rst_code_blocks, and _sanitize_description —
the helpers that fix MDX brace escaping and RST code block conversion in generated docs.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from create_docs import _escape_curly_braces, _convert_rst_code_blocks, _sanitize_description


class TestEscapeCurlyBraces:
    """Tests for _escape_curly_braces — escapes { } outside fenced/inline code for MDX."""

    def test_plain_text_unchanged(self):
        """Text with no braces is returned as-is."""
        assert _escape_curly_braces("hello world") == "hello world"

    def test_bare_braces_escaped(self):
        """Bare braces in prose are escaped."""
        assert _escape_curly_braces("foo {bar} baz") == r"foo \{bar\} baz"

    def test_inline_code_not_escaped(self):
        """Braces inside inline code spans are left alone."""
        assert _escape_curly_braces("use `{key}` here") == "use `{key}` here"

    def test_fenced_code_block_not_escaped(self):
        """Braces inside a fenced code block are left alone."""
        text = '```python\nd = {"key": 1}\n```'
        assert _escape_curly_braces(text) == text

    def test_braces_outside_fenced_block_escaped(self):
        """Only braces outside fenced blocks are escaped."""
        text = "Before {x}.\n```python\n{y}\n```\nAfter {z}."
        result = _escape_curly_braces(text)
        assert r"\{x\}" in result
        assert "{y}" in result  # inside fence — untouched
        assert r"\{z\}" in result

    def test_two_adjacent_fenced_blocks_with_braces_between(self):
        """Braces between two fenced blocks are escaped; content inside each is not."""
        text = "```python\n{a}\n```\n{between}\n```python\n{b}\n```"
        result = _escape_curly_braces(text)
        assert "{a}" in result
        assert r"\{between\}" in result
        assert "{b}" in result

    def test_multiple_inline_code_spans(self):
        """Multiple inline code spans on one line — braces inside each left alone."""
        result = _escape_curly_braces("use `{a}` and `{b}` but escape {c}")
        assert "`{a}`" in result
        assert "`{b}`" in result
        assert r"\{c\}" in result

    def test_inline_and_prose_braces_on_same_line(self):
        """Inline code braces and prose braces mixed on one line."""
        result = _escape_curly_braces("prefix {p} `mid {m}` suffix {s}")
        assert r"\{p\}" in result
        assert "`mid {m}`" in result
        assert r"\{s\}" in result

    def test_empty_string(self):
        """Empty input returns empty string."""
        assert _escape_curly_braces("") == ""


class TestConvertRstCodeBlocks:
    """Tests for _convert_rst_code_blocks — converts RST :: blocks to fenced ```python."""

    def test_no_rst_blocks_unchanged(self):
        """Text without :: markers is returned as-is."""
        text = "Regular paragraph.\n\nAnother paragraph."
        assert _convert_rst_code_blocks(text) == text

    def test_basic_rst_block_converted(self):
        """A :: paragraph produces a fenced python block with de-indented code."""
        text = "Example::\n\n    result = foo()\n    return result\n"
        result = _convert_rst_code_blocks(text)
        assert "```python" in result
        assert "result = foo()" in result
        assert "return result" in result
        assert "::" not in result

    def test_standalone_double_colon_removed(self):
        """A standalone :: line is removed; blank separator line appears inside the fence."""
        text = "::\n\n    code_here()\n"
        result = _convert_rst_code_blocks(text)
        assert result == "\n```python\n\ncode_here()\n```"

    def test_trailing_blank_lines_stripped_from_block(self):
        """Trailing blank lines after the block content are not emitted inside the fence."""
        text = "Example::\n\n    foo()\n\n\n"
        result = _convert_rst_code_blocks(text)
        assert result == "Example\n```python\n\nfoo()\n```"

    def test_indentation_stripped(self):
        """Four-space indentation is removed from block lines."""
        text = "Example::\n\n    indented_line()\n"
        result = _convert_rst_code_blocks(text)
        assert "    indented_line()" not in result
        assert "indented_line()" in result

    def test_prose_after_block_preserved(self):
        """Lines after the RST block (unindented) continue to appear correctly."""
        text = "Example::\n\n    foo()\n\nMore prose here."
        result = _convert_rst_code_blocks(text)
        assert "```python" in result
        assert "foo()" in result
        assert "More prose here." in result
        lines = result.split("\n")
        fence_close = lines.index("```")
        prose_idx = lines.index("More prose here.")
        assert prose_idx > fence_close

    def test_empty_string(self):
        """Empty input returns empty string."""
        assert _convert_rst_code_blocks("") == ""


class TestSanitizeDescription:
    """Tests for _sanitize_description — RST conversion then brace escaping."""

    def test_rst_and_braces_both_handled(self):
        """RST block is fenced first; braces inside the fence are preserved, outside are escaped."""
        text = "Set config using {value}.\n\nExample::\n\n    config({key: val})\n"
        result = _sanitize_description(text)
        assert r"\{value\}" in result       # prose brace escaped
        assert "```python" in result        # RST block converted
        assert "{key: val}" in result       # brace inside fence left alone

    def test_ordering_rst_before_braces(self):
        """_convert_rst_code_blocks runs before _escape_curly_braces so fenced braces are safe."""
        text = "Example::\n\n    d = {1: 2}\n"
        result = _sanitize_description(text)
        assert "{1: 2}" in result      # inside fence — must NOT be escaped
        assert r"\{1" not in result

    def test_plain_text_passthrough(self):
        """Plain text with no RST or braces is unchanged."""
        assert _sanitize_description("simple text") == "simple text"

    def test_empty_string(self):
        """Empty input returns empty string."""
        assert _sanitize_description("") == ""
