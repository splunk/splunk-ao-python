#!/usr/bin/env python3
"""
splunk-ao-migrate
=================
Automatically migrate Python code from the galileo SDK to splunk-ao-python.

Usage
-----
  python -m splunk_ao_migrate.migrate src/                  # rewrite an entire directory in place
  python -m splunk_ao_migrate.migrate my_agent.py           # rewrite a single file
  python -m splunk_ao_migrate.migrate --dry-run src/        # preview changes without writing
  python -m splunk_ao_migrate.migrate requirements.txt .env # migrate dependency / env files

Once installed via pip:
  splunk-ao-migrate src/
  splunk-ao-migrate --dry-run src/

See splunk-ao-migration-tool/README.md for the complete migration guide.
"""

from __future__ import annotations

import argparse
import os
import py_compile
import shutil
import sys
import tempfile
from pathlib import Path

# Allow running directly without installing.
# __file__ is <package-root>/src/splunk_ao_migrate/migrate.py so parent.parent is src/.
_SRC_DIR = Path(__file__).parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from splunk_ao_migrate.reporter import FileResult, Reporter
from splunk_ao_migrate.rules import (
    DEP_RULES,
    DOC_PLACEHOLDER_RULES,
    DOC_PROSE_RULES,
    DOC_URL_RULES,
    ENV_FILE_RULES,
    PROTECT_SYMBOLS_PATTERN,
    PYTHON_RULES,
    WARNING_RULES,
)
from splunk_ao_migrate.transformer import transform, transform_urls

# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

_TOML_NAME = "pyproject.toml"


def _classify(path: Path) -> str:
    """Return 'python', 'dep', 'env', 'toml', 'doc', or 'skip'."""
    name = path.name.lower()
    if path.suffix == ".py":
        return "python"
    if name.startswith("requirements") and name.endswith(".txt"):
        return "dep"
    if name == _TOML_NAME:
        return "toml"
    if name.startswith(".env") or path.suffix in {".env"}:
        return "env"
    if path.suffix in {".md", ".rst"}:
        return "doc"
    return "skip"


# ---------------------------------------------------------------------------
# Per-file migration
# ---------------------------------------------------------------------------

def migrate_file(path: Path, dry_run: bool, protect_in_scope: bool = False) -> FileResult:
    result = FileResult(path=str(path))
    kind = _classify(path)

    if kind == "skip":
        result.skipped = True
        result.skip_reason = "not a recognised file type"
        return result

    try:
        with open(path, encoding="utf-8", newline="") as fh:
            content = fh.read()
    except UnicodeDecodeError:
        result.skipped = True
        result.skip_reason = "non-UTF-8 content"
        return result
    except OSError as exc:
        result.skipped = True
        result.skip_reason = str(exc)
        return result

    if kind == "doc":
        # Pass 1: rewrite full URLs (docs.galileo.ai → agent-observability-docs.splunk.com).
        # transform_urls bypasses the URL guard so URL-pattern rules actually match.
        url_tr = transform_urls(content, DOC_URL_RULES)
        # Pass 2: apply prose rules (brand names, symbols, env vars …) on the
        # already-URL-rewritten content, with the URL guard re-enabled.
        # DOC_PROSE_RULES excludes KWARG_RULES to avoid rewriting kwarg-style
        # tokens inside string values (e.g. "logstream=default" in TRACELOOP_HEADERS).
        prose_tr = transform(url_tr.content, DOC_PROSE_RULES, WARNING_RULES)
        # Pass 3: fix placeholder over-rewrites — "your-galileo-*" became
        # "your-splunk_ao-*" (underscore) via the import rule; correct to
        # "your-splunk-ao-*" (hyphen) as used in prose and code-fence examples.
        placeholder_tr = transform_urls(prose_tr.content, DOC_PLACEHOLDER_RULES)
        result.matches = url_tr.matches + prose_tr.matches + placeholder_tr.matches
        # Run warning pass against original content so line numbers are accurate.
        result.warnings = transform(content, [], WARNING_RULES).warnings
        tr_content = placeholder_tr.content
    elif kind == "python":
        tr = transform(content, PYTHON_RULES, WARNING_RULES, python_mode=True)
        result.matches = tr.matches
        result.warnings = tr.warnings
        tr_content = tr.content
        # Validate that rewritten Python still compiles; skip write if broken.
        if tr_content != content and not _python_compiles(path, tr_content):
            result.skipped = True
            result.skip_reason = "rewritten content does not compile — skipped; review manually"
            return result
    elif kind in ("dep", "toml"):
        # Do not pass WARNING_RULES here: in dep/toml files every "galileo" string
        # literal is the package name (already auto-renamed), never a non-SDK reference.
        # The Protect pre-scan warning is emitted at the CLI level, not per-file.
        tr = transform(content, DEP_RULES)
        result.matches = tr.matches
        result.warnings = []
        tr_content = tr.content
    else:  # env
        tr = transform(content, ENV_FILE_RULES)
        result.matches = tr.matches
        result.warnings = []
        tr_content = tr.content

    # Only write when content actually changed.
    if tr_content != content and not dry_run:
        _write_atomic(path, tr_content)

    return result


def _python_compiles(path: Path, content: str) -> bool:
    """Return True if *content* is valid Python, False otherwise (with a warning printed)."""
    fd, tmp = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        py_compile.compile(tmp, doraise=True)
        return True
    except py_compile.PyCompileError as exc:
        print(
            f"  ⚠ Migration of {path} would produce invalid Python: {exc}",
            file=sys.stderr,
        )
        return False
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _write_atomic(path: Path, content: str) -> None:
    """Write content to path atomically via a temp file, preserving permissions."""
    dir_ = path.parent
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".splunk_ao_migrate_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
        # Preserve original file permissions (mode, timestamps).
        shutil.copystat(path, tmp)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Directory walk
# ---------------------------------------------------------------------------

_SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".tox", "dist", "build",
    "site-packages", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".eggs",
}


def collect_paths(roots: list[str]) -> list[Path]:
    """Expand directories recursively; return deduplicated list of paths."""
    seen: set[Path] = set()
    out: list[Path] = []

    for root in roots:
        p = Path(root)
        if p.is_file():
            if p not in seen:
                seen.add(p)
                out.append(p)
        elif p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    if _classify(fp) != "skip" and fp not in seen:
                        seen.add(fp)
                        out.append(fp)
        else:
            print(f"Warning: {root!r} does not exist, skipping.", file=sys.stderr)

    return out


# ---------------------------------------------------------------------------
# Path renaming  (directories and files whose names contain "galileo")
# ---------------------------------------------------------------------------

_PATH_RENAMES: list[tuple[str, str]] = [
    # hyphenated package/dir names  (galileo-a2a → splunk-ao-a2a)
    ("galileo-adk", "splunk-ao-adk"),
    ("galileo-a2a", "splunk-ao-a2a"),
    # bare hyphenated galileo prefix in dir/file names  (galileo-* → splunk-ao-*)
    ("galileo-", "splunk-ao-"),
    # galileo preceded by a hyphen in the middle of a name (e.g. 03-using-galileo.md)
    # Must come before the bare 'galileo' rule to produce the hyphenated form.
    ("-galileo", "-splunk-ao"),
    # Python package/module dirs  (galileo_a2a → splunk_ao_a2a, galileo_ prefix)
    ("galileo_", "splunk_ao_"),
    # bare galileo dir/file name (last resort)
    ("galileo", "splunk_ao"),
]


def _rename_path_segment(name: str) -> str:
    """Return the renamed version of a single path segment, or the original if no match."""
    for old, new in _PATH_RENAMES:
        if old in name:
            return name.replace(old, new)
    return name


def collect_path_renames(roots: list[str]) -> list[tuple[Path, Path]]:
    """
    Walk roots and return (old_path, new_path) pairs for every filesystem entry
    whose name contains 'galileo'.  Pairs are ordered deepest-first so renames
    can be applied without invalidating parent paths.

    For a file argument only that file is considered — the parent directory is
    never walked.  Nonexistent paths are skipped.
    """
    candidates: list[Path] = []

    for root in roots:
        p = Path(root)
        if not p.exists():
            # Nonexistent path — skip (collect_paths already warned about it)
            continue
        if p.is_file():
            # Only rename the file itself, never walk its parent directory.
            if "galileo" in p.name.lower():
                candidates.append(p)
        else:
            # Directory: walk and collect all entries containing "galileo".
            # Check the root dir name itself (os.walk never yields the top entry).
            if "galileo" in p.name.lower():
                candidates.append(p)
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
                dp = Path(dirpath)
                for d in dirnames:
                    if "galileo" in d.lower():
                        candidates.append(dp / d)
                for f in filenames:
                    if "galileo" in f.lower():
                        candidates.append(dp / f)

    # deepest first so child renames happen before parent renames
    candidates.sort(key=lambda p: len(p.parts), reverse=True)

    renames: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for old in candidates:
        if old in seen:
            continue
        seen.add(old)
        new_name = _rename_path_segment(old.name)
        if new_name != old.name:
            renames.append((old, old.parent / new_name))

    return renames


def apply_path_renames(renames: list[tuple[Path, Path]], dry_run: bool) -> None:
    """Print and optionally apply filesystem renames."""
    if not renames:
        return

    if dry_run:
        print("\nPath renames (dry run — not applied):")
    else:
        print("\nRenamed paths:")

    for old, new in renames:
        rel_old = _rel(str(old))
        rel_new = _rel(str(new))
        print(f"  {rel_old}  →  {rel_new}")
        if not dry_run:
            old.rename(new)


# ---------------------------------------------------------------------------
# Dry-run diff printer
# ---------------------------------------------------------------------------

def _print_diff(file_result: FileResult) -> None:
    if not file_result.matches:
        return
    # Group matches by line number and show one before/after pair per line.
    by_line: dict[int, tuple[str, str]] = {}
    for m in file_result.matches:
        if m.line not in by_line:
            by_line[m.line] = (m.original, m.replacement)
        else:
            # Subsequent rules on the same line: keep first 'original', update 'replacement'.
            by_line[m.line] = (by_line[m.line][0], m.replacement)

    print(f"\n--- {_rel(file_result.path)}")
    for lineno in sorted(by_line):
        original, replacement = by_line[lineno]
        print(f"  line {lineno:>4}:  - {original}")
        print(f"           + {replacement}")


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:
        return path


# ---------------------------------------------------------------------------
# Protect pre-scan
# ---------------------------------------------------------------------------

def _scan_for_protect(paths: list[Path]) -> bool:
    """
    Return True if any Python file in *paths* imports a Protect symbol.

    When Protect is in scope the bare 'galileo' dependency must NOT be removed
    from requirements / pyproject.toml — Protect is not available in splunk-ao.
    """
    import re
    pat = re.compile(PROTECT_SYMBOLS_PATTERN)
    for p in paths:
        if p.suffix != ".py":
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pat.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="splunk-ao-migrate",
        description="Migrate Python code from galileo SDK to splunk-ao-python.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help="Files or directories to migrate.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without writing any files.",
    )
    p.add_argument(
        "--no-report",
        action="store_true",
        help="Suppress the summary report.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = collect_paths(args.paths)
    if not paths:
        print("No files found to migrate.", file=sys.stderr)
        return 1

    # Pre-scan for Protect usage before touching any dependency files.
    protect_in_scope = _scan_for_protect(paths)
    if protect_in_scope:
        print(
            "⚠ Protect feature usage detected. The 'galileo' dependency will NOT be "
            "removed from requirements / pyproject.toml — Protect is not available in "
            "splunk-ao. Review dependency files manually.",
            file=sys.stderr,
        )

    reporter = Reporter()

    for path in paths:
        file_result = migrate_file(path, dry_run=args.dry_run, protect_in_scope=protect_in_scope)
        reporter.add(file_result)
        if args.dry_run and file_result.changed:
            _print_diff(file_result)

    # Rename directories and files containing "galileo" in their name.
    # Runs after content rewrites so updated files land in the right place.
    renames = collect_path_renames(args.paths)
    apply_path_renames(renames, dry_run=args.dry_run)

    if not args.no_report:
        has_warnings = reporter.print_report(dry_run=args.dry_run)
    else:
        has_warnings = reporter.has_warnings

    # Return non-zero if warnings were emitted so the tool is usable in CI.
    return 1 if has_warnings else 0


if __name__ == "__main__":
    sys.exit(main())
