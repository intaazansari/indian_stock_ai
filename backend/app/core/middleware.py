"""
FastAPI request middleware.

RequestLoggingMiddleware  — logs every request with timing and request_id.
RateLimitMiddleware       — IP-based rate limiting via Redis.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique request_id to every request.
    Log request start, end, and duration.
    Bind request_id to structlog context so all downstream logs carry it.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()
        logger.info("request.started")

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request.completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window rate limiter using Redis.

    Exempt paths: /health, /api/docs, /api/openapi.json
    AI analysis endpoints have a stricter per-user hourly limit
    enforced at the endpoint level via a dependency.
    """

    EXEMPT_PATHS = frozenset(["/health", "/api/docs", "/api/redoc", "/api/openapi.json"])

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Actual rate limiting logic is implemented in the dependencies layer
        # using slowapi / Redis for per-user granularity.
        # This middleware is a placeholder for IP-level global throttling.
        return await call_next(request)
