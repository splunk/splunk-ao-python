"""
Collects per-file results and prints the final migration report.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .transformer import Match


@dataclass
class FileResult:
    path: str
    matches: list[Match] = field(default_factory=list)
    warnings: list[Match] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.matches)

    @property
    def substitution_count(self) -> int:
        return len(self.matches)


class Reporter:
    def __init__(self) -> None:
        self._results: list[FileResult] = []

    def add(self, result: FileResult) -> None:
        self._results.append(result)

    @property
    def has_warnings(self) -> bool:
        return any(r.warnings for r in self._results)

    def print_report(self, dry_run: bool = False) -> bool:
        """Print the migration report and return True if any warnings were emitted."""
        changed = [r for r in self._results if r.changed]
        skipped = [r for r in self._results if r.skipped]
        warnings_all = [r for r in self._results if r.warnings]
        total_subs = sum(r.substitution_count for r in changed)
        total_scanned = len(self._results)

        action = "Would change" if dry_run else "Changed"
        changed_label = "Files would change:" if dry_run else "Files changed:    "

        print()
        print("splunk-ao-migrate — Migration Report")
        print("=" * 45)
        print(f"Files scanned:    {total_scanned}")
        print(f"{changed_label} {len(changed)}")
        print(f"Files skipped:    {len(skipped)}")
        print(f"Substitutions:    {total_subs}")

        if changed:
            print(f"\n{action} files:")
            for r in changed:
                rel = _rel(r.path)
                print(f"  {rel:<55} {r.substitution_count} substitution(s)")

        if skipped:
            print("\nSkipped files:")
            for r in skipped:
                print(f"  {_rel(r.path)}  — {r.skip_reason}")

        if warnings_all:
            print("\nWarnings (manual review required):")
            for r in warnings_all:
                for w in r.warnings:
                    print(f"  {_rel(r.path)}:{w.line}  — {w.rule_description}")

        print()
        print("Next steps:")
        if dry_run:
            print("  1. Re-run without --dry-run to apply changes")
            print("  2. What gets migrated and warnings reference: splunk_ao_migrate/README.md")
        else:
            print("  1. Review the diff:  git diff")
            print('  2. Install splunk-ao:')
            print('       pip install "splunk-ao @ git+https://github.com/splunk/splunk-ao-python.git"')
            print("  3. Upgrade Python to >= 3.11 if not already done")
            print("     Also ensure requires-python = \">=3.11\" in pyproject.toml (auto-updated by this tool)")
            print("  4. What gets migrated and warnings reference: splunk_ao_migrate/README.md")
        print()

        return bool(warnings_all)


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:
        return path
