"""Repo-level test-support helpers shared across the main package and the
sibling integration packages (galileo-adk, galileo-a2a).

This package is intentionally NOT shipped (it lives outside ``src/``) and is
not a pytest test package — it only holds importable helpers. It sits at the
repo root, rather than under ``tests/``, so the sibling packages (which have
their own top-level ``tests`` package) can import it without a package-name
collision.
"""
