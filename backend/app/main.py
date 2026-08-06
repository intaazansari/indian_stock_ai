"""
Application entry point.

Architecture note:
  - Middleware order matters. Inner middleware runs last on request, first on response.
  - Lifespan context manager handles startup/shutdown cleanly (no deprecated events).
  - Never expose /docs or /redoc in production.
"""
from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.db.session import init_db, close_db

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle — startup and graceful shutdown."""
    logger.info("application.startup", version=settings.APP_VERSION, env=settings.ENVIRONMENT)
    await init_db()

    # Qdrant is optional — only initialise when explicitly configured.
    # On Render (or local dev without Docker), QDRANT_URL is empty → skip silently.
    if settings.qdrant_enabled:
        try:
            from app.vector_store.client import ensure_collections
            await ensure_collections()
            logger.info("qdrant.ready")
        except Exception as exc:
            # Non-fatal: log and continue. RAG features will be unavailable.
            logger.warning("qdrant.init_failed", error=str(exc))
    else:
        logger.info("qdrant.disabled", reason="QDRANT_URL not configured")

    yield
    logger.info("application.shutdown")
    await close_db()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered Indian Stock Fundamental Analysis Platform",
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Security: only allow known hosts (prevents Host header attacks) ────────
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    # ── CORS: tightly scoped ───────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ── Custom middleware ──────────────────────────────────────────────────────
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RateLimitMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    application.include_router(api_v1_router, prefix="/api/v1")

    # ── Global exception handler ──────────────────────────────────────────────
    @application.exception_handler(ApplicationError)
    async def application_error_handler(request, exc: ApplicationError) -> JSONResponse:
        logger.warning("application.error", status_code=exc.status_code, detail=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return application


app = create_application()


@app.get("/health", tags=["Infrastructure"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": settings.APP_VERSION}
