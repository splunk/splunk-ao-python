"""
Applies migration rules to a string of source code.

Each rule's pattern is treated as a plain string by default.
Patterns that begin with r"\" or contain regex metacharacters are used as-is;
plain strings are escaped before compiling so that dots, parentheses etc. in
class names are matched literally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .rules import Rule, PROTECT_SYMBOLS_PATTERN


@dataclass
class Match:
    """A single substitution that was (or would be) applied."""
    line: int
    original: str
    replacement: str
    rule_description: str


@dataclass
class TransformResult:
    content: str
    matches: list[Match] = field(default_factory=list)
    warnings: list[Match] = field(default_factory=list)


def _compile(rule: Rule) -> re.Pattern[str]:
    """
    Compile a rule pattern.

    If the pattern string starts with r'\b' or contains any regex
    metacharacter (other than \b word boundaries), treat it as a raw regex.
    Otherwise escape it for a literal match.
    """
    raw_meta = re.compile(r"[.^$*+?{}[\]|()]|\\[bBdDwWsS]")
    if raw_meta.search(rule.pattern):
        return re.compile(rule.pattern)
    return re.compile(re.escape(rule.pattern))


# Matches a full URL token so substitutions can avoid rewriting inside URLs.
_URL_RE = re.compile(r"https?://\S+")

# Matches the start of an inline comment — a '#' that is not inside a string.
# We use a simple heuristic: find the first '#' that is not preceded by an odd
# number of quotes on the same line.  For the vast majority of real Python code
# this is accurate enough; pathological cases are caught by py_compile anyway.
_COMMENT_RE = re.compile(r"(?:\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|\"[^\"]*\"|\'[^\']*\')|#", re.DOTALL)


def _comment_start(line: str) -> int:
    """
    Return the character index of the first unquoted '#' on *line*, or
    len(line) if the line contains no comment.
    """
    for m in _COMMENT_RE.finditer(line):
        if m.group() == "#":
            return m.start()
    return len(line)


def _is_docstring_line(line: str) -> bool:
    """Return True if the line is purely a docstring / string-literal line."""
    stripped = line.lstrip()
    return stripped.startswith(('"""', "'''", '"', "'"))

# Rules whose replacements are Metric/Evaluator variants should not fire on
# any line in a file that imports from galileo_core — those types are internal
# and must not be renamed.  The suppression is file-scoped (not line-scoped)
# because call sites like `metrics=Metrics(...)` appear on lines that do not
# themselves contain 'galileo_core', yet the name was imported from it.
# This set matches the .replacement values of those rules.
_GALILEO_CORE_SKIP_REPLACEMENTS = frozenset({
    "Evaluators", "Evaluator", "BuiltInEvaluators",
    "LocalEvaluator", "CodeEvaluator", "LlmEvaluator",
})

_GALILEO_CORE_IMPORT_RE = re.compile(r"\bgalileo_core\b")

# Lines importing Protect symbols must not be renamed — Protect must stay
# imported from 'galileo', not 'splunk_ao'.
_PROTECT_LINE_RE = re.compile(PROTECT_SYMBOLS_PATTERN)


def _url_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of every URL found in *line*."""
    return [(m.start(), m.end()) for m in _URL_RE.finditer(line)]


def _sub_outside_urls(
    compiled: re.Pattern[str],
    replacement: str,
    line: str,
    brand: bool = False,
    python: bool = False,
) -> tuple[str, int]:
    """
    Like compiled.subn(replacement, line) but skips matches that fall
    inside a URL so that external links are never rewritten.

    When *brand* is True and *python* is True, also skips matches that fall
    in a code-token position — i.e. before the first unquoted '#' on the line
    on a non-docstring line.  This prevents "Galileo = 1" becoming
    "Splunk AO = 1" (SyntaxError) while still rewriting "# Galileo logger"
    and docstring lines correctly.  In doc/prose mode (*python* is False),
    brand renames are always applied (no code-position guard needed).
    """
    url_spans = _url_spans(line)
    comment_pos = _comment_start(line) if (brand and python) else len(line)
    is_doc = _is_docstring_line(line) if (brand and python) else False

    def _skip(start: int, end: int) -> bool:
        # Always skip matches inside URLs.
        if any(us <= start and end <= ue for us, ue in url_spans):
            return True
        # For brand rules in Python files: skip matches before the first '#'
        # on a non-docstring line to avoid SyntaxErrors in code-token positions.
        if brand and python and not is_doc and start < comment_pos:
            return True
        return False

    if not url_spans and not brand:
        return compiled.subn(replacement, line)

    out: list[str] = []
    count = 0
    prev = 0
    for m in compiled.finditer(line):
        if _skip(m.start(), m.end()):
            out.append(line[prev:m.end()])
        else:
            out.append(line[prev:m.start()])
            out.append(m.expand(replacement))
            count += 1
        prev = m.end()
    out.append(line[prev:])
    return "".join(out), count


def transform_urls(content: str, rules: list[Rule]) -> TransformResult:
    """
    Apply *rules* directly to *content* without skipping URL tokens.

    Use this exclusively for URL-rewrite rules (e.g. DOC_URL_RULES) where the
    pattern itself *is* a URL and the URL-guard in :func:`transform` would
    suppress the match.  Matches and the updated content are returned in a
    :class:`TransformResult`; no warning collection is performed.
    """
    result = TransformResult(content=content)
    lines = content.splitlines(keepends=True)

    for rule in rules:
        compiled = _compile(rule)
        new_lines: list[str] = []
        for lineno, line in enumerate(lines, start=1):
            new_line, n = compiled.subn(rule.replacement, line)
            if n:
                result.matches.append(Match(
                    line=lineno,
                    original=line.rstrip("\n"),
                    replacement=new_line.rstrip("\n"),
                    rule_description=rule.description,
                ))
            new_lines.append(new_line)
        lines = new_lines

    result.content = "".join(lines)
    return result


def transform(
    content: str,
    rules: list[Rule],
    warning_rules: list[Rule] | None = None,
    python_mode: bool = False,
) -> TransformResult:
    """
    Apply *rules* to *content* in order.

    Returns a TransformResult with the rewritten content, a list of applied
    substitutions, and a list of warnings (from warning_rules).
    URL tokens (https?://...) are never rewritten regardless of the rule.

    *python_mode* activates code-position gating for brand rules (``is_brand=True``):
    matches before the first unquoted ``#`` on a non-docstring line are skipped
    to avoid producing syntactically invalid Python (e.g. ``GALILEO = 1`` must
    not become ``SPLUNK AO = 1``).  Leave False for doc/prose content where brand
    names may appear freely anywhere on the line.

    Special behaviour: rules whose replacement is a bare Metric/Evaluator
    variant (e.g. "Evaluators", "Evaluator") are suppressed for the entire
    file if the file imports from galileo_core — those types are galileo_core
    internals and must not be renamed.  The check is file-scoped (not
    line-scoped) because call sites like ``metrics=Metrics(...)`` appear on
    lines that do not themselves contain 'galileo_core'.
    """
    result = TransformResult(content=content)
    lines = content.splitlines(keepends=True)

    # File-level flag: suppress Metric→Evaluator renames across the whole file
    # if any line imports from galileo_core.
    file_has_galileo_core = _GALILEO_CORE_IMPORT_RE.search(content) is not None

    for rule in rules:
        # Warning-only rules in a rule list are skipped during substitution;
        # they are collected separately via the warning_rules parameter.
        if rule.is_warning:
            continue
        # Suppress Metric→Evaluator rules for the entire file when galileo_core
        # is imported — those types are internal and must not be renamed.
        if file_has_galileo_core and rule.replacement in _GALILEO_CORE_SKIP_REPLACEMENTS:
            continue
        compiled = _compile(rule)
        new_lines: list[str] = []
        for lineno, line in enumerate(lines, start=1):
            # Never rewrite lines that import Protect symbols — those must remain
            # as `from galileo import invoke_protect …`.
            if _PROTECT_LINE_RE.search(line) and "galileo" in line:
                new_lines.append(line)
                continue
            new_line, n = _sub_outside_urls(
                compiled, rule.replacement, line, brand=rule.is_brand, python=python_mode
            )
            if n:
                result.matches.append(Match(
                    line=lineno,
                    original=line.rstrip("\n"),
                    replacement=new_line.rstrip("\n"),
                    rule_description=rule.description,
                ))
            new_lines.append(new_line)
        lines = new_lines

    result.content = "".join(lines)

    # Collect warnings (never modify content)
    if warning_rules:
        for rule in warning_rules:
            compiled = _compile(rule)
            for lineno, line in enumerate(content.splitlines(keepends=True), start=1):
                if compiled.search(line):
                    result.warnings.append(Match(
                        line=lineno,
                        original=line.rstrip("\n"),
                        replacement="",
                        rule_description=rule.description,
                    ))

    return result
