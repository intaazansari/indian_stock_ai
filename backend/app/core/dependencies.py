"""
FastAPI dependency injection.

Provides reusable dependencies for:
  - Database sessions
  - Redis client
  - Authenticated user context
  - AI rate limiting
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AIRateLimitExceededError, UnauthorizedError
from app.core.security import TokenType, get_subject_from_token
from app.db.session import get_async_session

logger = structlog.get_logger(__name__)

# ── Database ──────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Redis ─────────────────────────────────────────────────────────────────────

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return a Redis client, or None if REDIS_URL is not configured."""
    global _redis_pool
    if not settings.redis_enabled:
        return None
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,   # fail fast when Redis is unavailable
            socket_timeout=0.5,
        )
    return _redis_pool


RedisClient = Annotated[aioredis.Redis | None, Depends(get_redis)]


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """
    Extract and validate the authenticated user ID from the Bearer token.
    Raises UnauthorizedError for missing or invalid tokens.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Authorization header missing or malformed")
    token = authorization.removeprefix("Bearer ")
    return get_subject_from_token(token, expected_type=TokenType.ACCESS)


CurrentUserID = Annotated[str, Depends(get_current_user_id)]


async def get_optional_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """
    Return the user ID if a valid token is provided, otherwise None.
    Use for endpoints accessible to both guests and authenticated users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.removeprefix("Bearer ")
        return get_subject_from_token(token, expected_type=TokenType.ACCESS)
    except UnauthorizedError:
        return None


OptionalUserID = Annotated[str | None, Depends(get_optional_user_id)]


# ── AI Rate Limiting ──────────────────────────────────────────────────────────

async def check_ai_rate_limit(
    user_id: OptionalUserID,
    redis: RedisClient,
) -> None:
    """
    Enforce per-user hourly limit on AI analysis requests.
    Uses a Redis counter with a 1-hour TTL.
    Skips gracefully when Redis is unavailable or user is unauthenticated.
    """
    if not user_id:
        return  # unauthenticated users bypass rate limit in dev
    try:
        key = f"ai_rate_limit:{user_id}"
        count_str: str | None = await redis.get(key)
        count = int(count_str) if count_str else 0

        if count >= settings.RATE_LIMIT_AI_PER_HOUR:
            raise AIRateLimitExceededError(
                f"You have reached the limit of {settings.RATE_LIMIT_AI_PER_HOUR} "
                "AI analyses per hour. Please try again later."
            )

        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)
        await pipe.execute()
    except AIRateLimitExceededError:
        raise
    except Exception:
        pass  # Redis unavailable — skip rate limiting


AIRateLimitDep = Depends(check_ai_rate_limit)
