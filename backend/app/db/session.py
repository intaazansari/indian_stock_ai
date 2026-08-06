"""
Async SQLAlchemy session factory.

Uses AsyncEngine with connection pooling tuned for PostgreSQL.
"""
from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Create the async engine and session factory. Called once on startup."""
    global _engine, _session_factory

    _engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,                    # Detect stale connections
        echo=settings.DEBUG,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,               # Avoid lazy-loading after commit
        autocommit=False,
        autoflush=False,
    )

    logger.info("database.connected", pool_size=settings.DATABASE_POOL_SIZE)


async def close_db() -> None:
    """Dispose the engine pool on shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("database.disconnected")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a session and handles commit/rollback.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(...)
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
