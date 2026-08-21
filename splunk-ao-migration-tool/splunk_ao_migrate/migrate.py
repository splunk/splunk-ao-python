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

See splunk-ao-migration-tool/PROPOSAL.md for full design details.
See splunk-ao-migration-tool/README.md for the complete migration guide.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Allow running directly (python splunk_ao_migrate/migrate.py) without installing.
# __file__ is <tool-root>/splunk_ao_migrate/migrate.py so parent.parent is <tool-root>.
_TOOL_ROOT = Path(__file__).parent.parent
if str(_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOOL_ROOT))

from splunk_ao_migrate.reporter import FileResult, Reporter
from splunk_ao_migrate.rules import (
    DEP_RULES,
    DOC_PLACEHOLDER_RULES,
    DOC_PROSE_RULES,
    DOC_URL_RULES,
    ENV_FILE_RULES,
    PYTHON_RULES,
    WARNING_RULES,
)
from splunk_ao_migrate.transformer import transform, transform_urls

# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

_DEP_NAMES = {"requirements.txt", "requirements-dev.txt", "requirements-test.txt"}
_DEP_GLOB = "requirements*.txt"
_ENV_SUFFIXES = {".env"}
_ENV_PREFIXES = {".env"}
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
    if name.startswith(".env") or path.suffix in _ENV_SUFFIXES:
        return "env"
    if path.suffix in {".md", ".rst"}:
        return "doc"
    return "skip"


# ---------------------------------------------------------------------------
# Per-file migration
# ---------------------------------------------------------------------------

def migrate_file(path: Path, dry_run: bool) -> FileResult:
    result = FileResult(path=str(path))
    kind = _classify(path)

    if kind == "skip":
        result.skipped = True
        result.skip_reason = "not a recognised file type"
        return result

    try:
        content = path.read_text(encoding="utf-8")
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
        result.warnings = prose_tr.warnings
        tr_content = placeholder_tr.content
    elif kind == "python":
        tr = transform(content, PYTHON_RULES, WARNING_RULES)
        result.matches = tr.matches
        result.warnings = tr.warnings
        tr_content = tr.content
    elif kind in ("dep", "toml"):
        tr = transform(content, DEP_RULES)
        result.matches = tr.matches
        result.warnings = []
        tr_content = tr.content
    else:  # env
        tr = transform(content, ENV_FILE_RULES)
        result.matches = tr.matches
        result.warnings = []
        tr_content = tr.content

    if result.matches and not dry_run:
        _write_atomic(path, tr_content)

    return result


def _write_atomic(path: Path, content: str) -> None:
    """Write content to path atomically via a temp file in the same directory."""
    dir_ = path.parent
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".splunk_ao_migrate_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
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

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "dist", "build"}


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
    """
    candidates: list[Path] = []

    for root in roots:
        p = Path(root)
        base = p if p.is_dir() else p.parent
        # Check the root itself — os.walk never yields the top-level dir as an entry
        if "galileo" in p.name.lower():
            candidates.append(p)
        for dirpath, dirnames, filenames in os.walk(base):
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
    print(f"\n--- {_rel(file_result.path)}")
    for m in file_result.matches:
        print(f"  line {m.line:>4}:  - {m.original}")
        print(f"           + {m.replacement}")


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:
        return path


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

    reporter = Reporter()

    for path in paths:
        file_result = migrate_file(path, dry_run=args.dry_run)
        reporter.add(file_result)
        if args.dry_run and file_result.changed:
            _print_diff(file_result)

    # Rename directories and files containing "galileo" in their name.
    # Runs after content rewrites so updated files land in the right place.
    renames = collect_path_renames(args.paths)
    apply_path_renames(renames, dry_run=args.dry_run)

    if not args.no_report:
        reporter.print_report(dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
