"""Deprecated: use splunk_ao.prompt instead of splunk_ao.__future__.prompt."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.prompt is deprecated. Use splunk_ao.prompt instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.prompt import Prompt, PromptVersion, _parse_template_to_messages  # noqa: E402

__all__ = ["Prompt", "PromptVersion", "_parse_template_to_messages"]
