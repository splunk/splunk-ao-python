"""Deprecated: use splunk_ao.collaborator instead of splunk_ao.__future__.collaborator."""

import warnings

warnings.warn(
    "Importing from splunk_ao.__future__.collaborator is deprecated. Use splunk_ao.collaborator instead.",
    DeprecationWarning,
    stacklevel=2,
)

from splunk_ao.collaborator import Collaborator, CollaboratorRole  # noqa: E402

__all__ = ["Collaborator", "CollaboratorRole"]
