"""W3C trace-context middleware for Starlette-based applications.

``TracingMiddleware`` extracts ``traceparent`` and ``tracestate`` through the
configured OpenTelemetry propagator. Applications explicitly own the local
Splunk AO logger and trace lifecycle::

    app.add_middleware(TracingMiddleware)

    @app.post("/process")
    async def process_request(data: dict):
        logger = get_request_logger()
        try:
            logger.start_trace(input=str(data), name="request")
            logger.add_workflow_span(input=str(data), name="process")
            result = await process(data)
            logger.conclude(output=str(result), conclude_all=True)
            return {"result": result}
        finally:
            logger.terminate()
"""

import logging
from typing import Any, NoReturn

from opentelemetry import context as otel_context

from splunk_ao.logger import SplunkAOLogger
from splunk_ao.tracing import extract_tracing_context

_logger = logging.getLogger(__name__)

INSTALL_ERR_MSG = (
    "Starlette is not installed. Install optional middleware dependencies with: pip install splunk-ao[middleware]"
)

try:
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp
except ImportError:
    # Keep imports available without the optional Starlette dependency.
    class BaseHTTPMiddleware:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> NoReturn:
            raise ImportError(INSTALL_ERR_MSG)

    class Request:  # type: ignore[no-redef]
        pass

    class Response:  # type: ignore[no-redef]
        pass

    class RequestResponseEndpoint:  # type: ignore[no-redef]
        pass

    class ASGIApp:  # type: ignore[no-redef]
        pass


class TracingMiddleware(BaseHTTPMiddleware):
    """Attach incoming W3C trace context for the duration of each request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Extract, attach, and reliably detach the request's trace context."""
        extracted = extract_tracing_context(request.headers)
        token = otel_context.attach(extracted)
        try:
            return await call_next(request)
        finally:
            otel_context.detach(token)


def get_request_logger() -> SplunkAOLogger:
    """Create a request-scoped logger under the middleware's active context.

    The caller must explicitly call ``start_trace()`` before adding spans and
    should call ``terminate()`` in ``finally``. With an extracted W3C parent,
    the first real local operation becomes its descendant; without one, it
    starts a new trace.
    """
    return SplunkAOLogger()
