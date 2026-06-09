"""Temporary compatibility shim for the legacy ``galileo`` namespace."""

from __future__ import annotations

import sys
import warnings
from importlib import import_module
from typing import Any

if not getattr(sys, "_splunk_ao_suppress_galileo_deprecation_warning", False):
    warnings.warn(
        "The 'galileo' namespace is deprecated and will be removed in a future HYBIM task; "
        "use 'splunk_ao' instead.",
        DeprecationWarning,
        stacklevel=2,
    )


def __getattr__(name: str) -> Any:
    return getattr(import_module("splunk_ao"), name)


def __dir__() -> list[str]:
    target = import_module("splunk_ao")
    return sorted(set(globals()) | set(getattr(target, "__all__", [])))
