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

from .rules import Rule


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


def _url_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of every URL found in *line*."""
    return [(m.start(), m.end()) for m in _URL_RE.finditer(line)]


def _sub_outside_urls(compiled: re.Pattern[str], replacement: str, line: str) -> tuple[str, int]:
    """
    Like compiled.subn(replacement, line) but skips matches that fall
    inside a URL so that external links are never rewritten.
    """
    url_spans = _url_spans(line)
    if not url_spans:
        return compiled.subn(replacement, line)

    def _in_url(start: int, end: int) -> bool:
        return any(us <= start and end <= ue for us, ue in url_spans)

    out: list[str] = []
    count = 0
    prev = 0
    for m in compiled.finditer(line):
        if _in_url(m.start(), m.end()):
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


def transform(content: str, rules: list[Rule], warning_rules: list[Rule] | None = None) -> TransformResult:
    """
    Apply *rules* to *content* in order.

    Returns a TransformResult with the rewritten content, a list of applied
    substitutions, and a list of warnings (from warning_rules).
    URL tokens (https?://...) are never rewritten regardless of the rule.
    """
    result = TransformResult(content=content)
    lines = content.splitlines(keepends=True)

    for rule in rules:
        compiled = _compile(rule)
        new_lines: list[str] = []
        for lineno, line in enumerate(lines, start=1):
            new_line, n = _sub_outside_urls(compiled, rule.replacement, line)
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
