"""Tests for MDX helper functions in scripts/create_docs.py.

Covers _escape_curly_braces, _convert_rst_code_blocks, _sanitize_description, and _render_examples —
the helpers that fix MDX brace escaping and RST code block conversion in generated docs.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from create_docs import (
    _convert_rst_code_blocks,
    _escape_curly_braces,
    _render_examples,
    _sanitize_description,
    _strip_doctest_prompts,
    write_module,
)


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

    def test_prose_ending_in_double_colon_no_indented_block(self):
        """Prose line ending in :: with no indented block following loses the :: but is otherwise intact."""
        text = "Refer to namespace::\n\nNext paragraph (not indented)."
        result = _convert_rst_code_blocks(text)
        assert "```" not in result
        assert "Refer to namespace" in result
        assert "Next paragraph (not indented)." in result

    def test_double_colon_mid_line_not_treated_as_rst(self):
        """:: mid-line (e.g. namespace::method) does not trigger RST block conversion."""
        text = "Use namespace::method() here.\n\nMore text."
        assert _convert_rst_code_blocks(text) == text

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


class TestStripDoctestPrompts:
    """Tests for _strip_doctest_prompts — removes >>> / ... prompts from every line."""

    def test_all_lines_stripped(self):
        """Prompts are removed from the first and subsequent lines."""
        assert _strip_doctest_prompts(">>> a = 1\n... b = 2") == "a = 1\nb = 2"

    def test_bare_prompt_becomes_blank_line(self):
        """A prompt with no code becomes an empty line."""
        assert _strip_doctest_prompts(">>> a\n...\n>>> b") == "a\n\nb"

    def test_indented_ellipsis_placeholder_preserved(self):
        """An indented bare ``...`` (a Python placeholder body) is code, not a prompt."""
        code = "def f():\n    ...\n\nclass A: ..."
        assert _strip_doctest_prompts(code) == code

    def test_indented_prompts_keep_indentation(self):
        """Prompts inside an indented RST block are stripped without losing the indent."""
        assert _strip_doctest_prompts("    >>> a = 1\n    ... b = 2") == "    a = 1\n    b = 2"

    def test_bare_code_unchanged(self):
        """Code without prompts is returned as-is."""
        assert _strip_doctest_prompts("x = 1\ny = 2") == "x = 1\ny = 2"


class TestRenderExamples:
    """Tests for _render_examples — every example must come out as a fenced python block."""

    @staticmethod
    def _render(examples):
        parts: list[str] = []
        _render_examples(parts, examples)
        return "\n".join(parts)

    def test_bare_example_is_fenced(self):
        """A bare example (no >>> and no parsed snippet) is fenced, not emitted as prose."""
        out = self._render([{"code": "ds = get_dataset()\nds.add(1)", "had_snippet": False}])
        assert "```python\nds = get_dataset()\nds.add(1)\n```" in out

    def test_doctest_example_is_fenced_and_stripped(self):
        """A doctest example is fenced and loses its prompts on every line."""
        out = self._render([{"code": ">>> a = 1\n... b = 2", "had_snippet": False}])
        assert "```python\na = 1\nb = 2\n```" in out
        assert ">>>" not in out

    def test_mixed_example_is_fenced_once(self):
        """Prose-free mixed bare + doctest lines land in one block with prompts stripped."""
        out = self._render([{"code": "x = 1\n>>> y = 2", "had_snippet": True}])
        assert out.count("```python") == 1
        assert "x = 1\ny = 2" in out

    def test_already_fenced_example_passes_through(self):
        """An example that already has a fence is not wrapped a second time."""
        code = "```python\nx = 1\n```"
        out = self._render([{"code": code}])
        assert out.count("```") == 2

    def test_braces_inside_fence_not_escaped(self):
        """Braces in an example stay literal because the fence protects them from MDX."""
        out = self._render([{"code": 'cfg = {"a": 1}'}])
        assert 'cfg = {"a": 1}' in out
        assert "\\{" not in out

    def test_multiple_examples_each_fenced(self):
        """Each example gets its own block."""
        out = self._render([{"code": "a = 1"}, {"code": "b = 2"}])
        assert out.count("```python") == 2

    def test_empty_examples_skipped(self):
        """Examples without code produce no block."""
        out = self._render([{"code": ""}, {"code": None}])
        assert "```" not in out
        assert out.startswith("**Examples**")


class TestEscapeCurlyBracesMultiBacktick:
    """Braces inside double-backtick (RST-style) inline code must stay literal."""

    def test_double_backtick_span_not_escaped(self):
        """Braces inside a ``double-backtick`` span are left alone."""
        assert _escape_curly_braces('use ``"a/{id}"`` here') == 'use ``"a/{id}"`` here'

    def test_prose_next_to_double_backtick_span_escaped(self):
        """Prose braces are still escaped when a double-backtick span is on the same line."""
        assert _escape_curly_braces("``{a}`` and {b}") == r"``{a}`` and \{b\}"

    def test_mixed_single_and_double_spans(self):
        """Single and double spans can appear together."""
        assert _escape_curly_braces("`{x}` ``{y}`` {z}") == r"`{x}` ``{y}`` \{z\}"


class TestWriteModuleExamples:
    """Module-level docstring examples must be rendered, not silently dropped."""

    def test_module_examples_are_rendered_fenced(self):
        """A module docstring example appears in the output as a fenced python block."""
        from types import SimpleNamespace

        doc = {"description": "Module docs.", "examples": [{"code": "import x\nx.run({'a': 1})"}]}
        fd = SimpleNamespace(module=SimpleNamespace(doc=doc))
        parts: list[str] = []
        write_module(fd, parts)
        out = "\n".join(parts)
        assert "**Examples**" in out
        assert "```python\nimport x\nx.run({'a': 1})\n```" in out


class TestRstLiteralBlockExamples:
    """RST ``::`` lead-in examples fence only the code, not the prose."""

    RST = (
        "Poll until a specific metric is computed, then assert::\n\n"
        "    while agg(x) is None:\n"
        "        cfg = {'a': 1}\n"
    )

    def test_prose_stays_outside_fence_and_marker_removed(self):
        """The lead-in sentence is prose, the ``::`` marker is dropped, and only the code is fenced."""
        parts: list[str] = []
        _render_examples(parts, [{"code": self.RST}])
        out = "\n".join(parts)
        assert "Poll until a specific metric is computed, then assert\n```python" in out
        assert "::" not in out
        assert "while agg(x) is None:\n    cfg = {'a': 1}\n```" in out
        assert out.count("```python") == 1

    def test_doctest_prompts_inside_rst_block_are_stripped(self):
        """``>>>`` / ``...`` prompts inside a ``::`` block do not leak into the fenced code."""
        parts: list[str] = []
        _render_examples(parts, [{"code": "Call it::\n\n    >>> a = 1\n    ... b = 2\n"}])
        out = "\n".join(parts)
        assert ">>>" not in out
        assert "a = 1" in out
        assert "b = 2" in out

    def test_note_with_rst_block_is_fenced_and_braces_kept(self):
        """A ``::`` block inside a note is converted to a fence so its braces stay literal."""
        from types import SimpleNamespace

        doc = {"description": "d", "notes": [{"note": "Use it like so::\n\n    x = {'k': 1}\n and {prose}"}]}
        fd = SimpleNamespace(module=SimpleNamespace(doc=doc))
        parts: list[str] = []
        write_module(fd, parts)
        out = "\n".join(parts)
        assert "```python\n" in out
        assert "x = {'k': 1}\n```" in out
        assert r"\{prose\}" in out


class TestProseBulletListExamples:
    """Bullet-list examples are prose and must not be fenced as Python."""

    BULLETS = (
        '- If "my-template" doesn\'t exist \u2192 returns "my-template"\n'
        '- If "my-template" exists \u2192 returns "my-template (1)"'
    )

    @staticmethod
    def _render(code):
        parts: list[str] = []
        _render_examples(parts, [{"code": code}])
        return "\n".join(parts)

    def test_bullet_list_stays_a_list(self):
        """A bullet-only example is emitted as a Markdown list, not a python block."""
        out = self._render(self.BULLETS)
        assert "```" not in out
        assert '- If "my-template" exists' in out

    def test_braces_in_bullet_list_are_escaped(self):
        """Prose bullets still get MDX brace escaping."""
        assert r"\{x\}" in self._render("- use {x}\n- or {y}")

    def test_yaml_list_example_stays_fenced(self):
        """A YAML-style list is code, so it keeps its python fence."""
        out = self._render("- name: a\n- name: b")
        assert out.count("```python") == 1

    def test_mixed_bullets_and_code_stay_fenced(self):
        """A bullet line next to code is not a pure list, so the example is fenced."""
        assert "```python" in self._render("- note\nx = 1")
