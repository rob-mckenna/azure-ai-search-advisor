"""API middleware."""

from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from azure_ai_search_advisor.core.logging import reset_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)
CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach correlation IDs and request lifecycle logs to every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid4())
        request.state.correlation_id = correlation_id
        token = set_correlation_id(correlation_id)
        started_at = perf_counter()

        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            reset_correlation_id(token)

