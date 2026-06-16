"""Deprecated: use splunk_ao.provider instead of splunk_ao.__future__.provider."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.provider is deprecated. Use splunk_ao.provider instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.provider import (  # noqa: E402
    AnthropicProvider,
    AzureProvider,
    BedrockProvider,
    GenericProvider,
    Model,
    OpenAIProvider,
    Provider,
    UnconfiguredProvider,
)

__all__ = [
    "AnthropicProvider",
    "AzureProvider",
    "BedrockProvider",
    "GenericProvider",
    "Model",
    "OpenAIProvider",
    "Provider",
    "UnconfiguredProvider",
]
