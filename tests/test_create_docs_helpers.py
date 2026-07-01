"""Tests for MDX helper functions in scripts/create_docs.py.

These functions are duplicated here to avoid importing the full script,
which depends on docstring_parser (not a project dev dependency).
The implementations must stay in sync with scripts/create_docs.py.
"""

import re


def _escape_curly_braces(text: str) -> str:
    triple_segments = re.split(r"(```.*?```)", text, flags=re.DOTALL)
    for i, triple_seg in enumerate(triple_segments):
        if triple_seg.startswith("```"):
            continue
        single_segments = re.split(r"(`[^`]*`)", triple_seg)
        for j, single_seg in enumerate(single_segments):
            if not single_seg.startswith("`"):
                single_seg = single_seg.replace("{", r"\{").replace("}", r"\}")
            single_segments[j] = single_seg
        triple_segments[i] = "".join(single_segments)
    return "".join(triple_segments)


def _convert_rst_code_blocks(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.rstrip().endswith("::"):
            stripped = line.rstrip()[:-2].rstrip()
            out.append(stripped)
            i += 1
            block: list[str] = []
            while i < len(lines) and (lines[i].strip() == "" or lines[i].startswith("    ")):
                block.append(lines[i])
                i += 1
            while block and block[-1].strip() == "":
                block.pop()
            if block:
                out.append("```python")
                for bl in block:
                    out.append(bl[4:] if bl.startswith("    ") else bl)
                out.append("```")
        else:
            out.append(line)
            i += 1
    return "\n".join(out)


def _sanitize_description(text: str) -> str:
    text = _convert_rst_code_blocks(text)
    text = _escape_curly_braces(text)
    return text


class TestEscapeCurlyBraces:
    def test_plain_text_unchanged(self):
        assert _escape_curly_braces("hello world") == "hello world"

    def test_bare_braces_escaped(self):
        assert _escape_curly_braces("foo {bar} baz") == r"foo \{bar\} baz"

    def test_inline_code_not_escaped(self):
        result = _escape_curly_braces("use `{key}` here")
        assert result == "use `{key}` here"

    def test_fenced_code_block_not_escaped(self):
        text = '```python\nd = {"key": 1}\n```'
        assert _escape_curly_braces(text) == text

    def test_braces_outside_fenced_block_escaped(self):
        text = "Before {x}.\n```python\n{y}\n```\nAfter {z}."
        result = _escape_curly_braces(text)
        assert r"\{x\}" in result
        assert "{y}" in result
        assert r"\{z\}" in result

    def test_empty_string(self):
        assert _escape_curly_braces("") == ""

    def test_multiple_inline_code_spans(self):
        result = _escape_curly_braces("use `{a}` and `{b}` but escape {c}")
        assert "`{a}`" in result
        assert "`{b}`" in result
        assert r"\{c\}" in result


class TestConvertRstCodeBlocks:
    def test_no_rst_blocks_unchanged(self):
        text = "Regular paragraph.\n\nAnother paragraph."
        assert _convert_rst_code_blocks(text) == text

    def test_basic_rst_block_converted(self):
        text = "Example::\n\n    result = foo()\n    return result\n"
        result = _convert_rst_code_blocks(text)
        assert "```python" in result
        assert "result = foo()" in result
        assert "return result" in result
        assert "::" not in result

    def test_standalone_double_colon_removed(self):
        text = "::\n\n    code_here()\n"
        result = _convert_rst_code_blocks(text)
        assert "```python" in result
        assert "code_here()" in result
        assert "::" not in result

    def test_trailing_blank_lines_stripped_from_block(self):
        text = "Example::\n\n    foo()\n\n\n"
        result = _convert_rst_code_blocks(text)
        lines = result.strip().split("\n")
        assert lines[-1] == "```"

    def test_indentation_stripped(self):
        text = "Example::\n\n    indented_line()\n"
        result = _convert_rst_code_blocks(text)
        assert "    indented_line()" not in result
        assert "indented_line()" in result

    def test_empty_string(self):
        assert _convert_rst_code_blocks("") == ""


class TestSanitizeDescription:
    def test_rst_and_braces_both_handled(self):
        text = "Set config using {value}.\n\nExample::\n\n    config({key: val})\n"
        result = _sanitize_description(text)
        assert r"\{value\}" in result
        assert "```python" in result
        assert "{key: val}" in result

    def test_plain_text_passthrough(self):
        assert _sanitize_description("simple text") == "simple text"

    def test_empty_string(self):
        assert _sanitize_description("") == ""
