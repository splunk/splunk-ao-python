"""Deprecated: use splunk_ao.shared.filter instead of splunk_ao.__future__.shared.filter."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.shared.filter is deprecated. Use splunk_ao.shared.filter instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.shared.filter import (  # noqa: E402
    BooleanFilter,
    DateFilter,
    Filter,
    NumberFilter,
    TextFilter,
    boolean,
    date,
    number,
    text,
)

__all__ = ["BooleanFilter", "DateFilter", "Filter", "NumberFilter", "TextFilter", "boolean", "date", "number", "text"]
