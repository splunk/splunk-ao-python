"""Deprecated: use splunk_ao.shared.utils instead of splunk_ao.__future__.shared.utils."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.utils is deprecated. Use splunk_ao.shared.utils instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.utils import classproperty  # noqa: E402

__all__ = ["classproperty"]
