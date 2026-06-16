"""Fast SplunkAOConfig validation for tests.

Building ``SplunkAOConfig`` runs 3 async validation requests
(healthcheck/login/current_user) through galileo_core's ``async_run`` /
``EventLoopThreadPool``, whose Windows IOCP poll is ~11x slower on Python
3.11+. In tests these endpoints are already mocked, so they add no coverage —
only event-loop cost. ``fast_config_validation`` replaces them with canned,
await-free results so the per-test config build is trivial.

Scope the context manager to the per-test config build only; test bodies still
exercise the real validation/connect code with their own mocks.

Shared by the autouse ``set_validated_config`` fixtures in the main package and
in galileo-adk.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from galileo_core.helpers.api_client import ApiClient
from galileo_core.schemas.core.user import User
from galileo_core.schemas.core.user_role import UserRole


def fast_validation_payload(endpoint: Any) -> dict:
    """Canned response for the 3 config-validation endpoints."""
    ep = str(endpoint)
    if "login" in ep or "token" in ep:
        return {"access_token": "secret_jwt_token"}
    if "current_user" in ep:
        return User.model_validate({"id": uuid4(), "email": "user@example.com", "role": UserRole.user}).model_dump(
            mode="json"
        )
    return {"status": "ok"}


@contextmanager
def fast_config_validation() -> Generator[None, None, None]:
    """Stub the async config-validation round-trips with canned, await-free
    results so the per-test ``SplunkAOConfig`` build is cheap.

    Scoped to the config build only; test bodies still exercise the real
    validation/connect code.
    """

    async def _stub_make_request(request_method: Any, base_url: str, endpoint: Any, **kwargs: Any) -> dict:
        return fast_validation_payload(endpoint)

    def _stub_request(self: Any, request_method: Any, path: Any = None, **kwargs: Any) -> dict:
        return fast_validation_payload(path)

    with (
        patch.object(ApiClient, "make_request", staticmethod(_stub_make_request)),
        patch.object(ApiClient, "request", _stub_request),
    ):
        yield
