"""
Application configuration using Pydantic Settings.

All config is loaded from environment variables / .env file.
Never hard-code secrets. Always validate at startup.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Search order: project root first, then current dir (later overrides earlier).
        # This works whether you run from backend/, project root, or inside Docker.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "StockSage AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    ALLOWED_HOSTS: list[str] = ["*"]    # override in production via env var

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    # Leave empty to disable Redis caching (AI analysis falls back to PostgreSQL only).
    REDIS_URL: str = ""
    REDIS_CACHE_TTL: int = 3600               # 1 hour
    AI_ANALYSIS_CACHE_TTL: int = 86400        # 24 hours

    @property
    def redis_enabled(self) -> bool:
        return bool(self.REDIS_URL)

    # ── Qdrant (optional — not needed for Phase 1) ────────────────────────────
    # Set to empty string or omit to disable Qdrant entirely.
    # Required only for PDF annual report RAG and news sentiment features.
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_ANNUAL_REPORTS: str = "annual_reports"
    QDRANT_COLLECTION_NEWS: str = "company_news"
    QDRANT_COLLECTION_TRANSCRIPTS: str = "earnings_transcripts"

    # ── OpenAI-compatible ──────────────────────────────────────────────
    OPENAI_API_KEY: str = ""            # Required for AI features; set in Render dashboard
    OPENAI_BASE_URL: str | None = None   # Set to override endpoint (e.g. Groq, Azure, Ollama)
    OPENAI_ANALYSIS_MODEL: str = "gpt-4o"
    OPENAI_SUMMARY_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AI_PER_HOUR: int = 20

    # ── Celery ────────────────────────────────────────────────────────────────
    # Leave empty to disable background workers (dev mode — tasks run synchronously).
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # ── Data Sources ──────────────────────────────────────────────────────────
    NSE_BASE_URL: str = "https://www.nseindia.com"
    BSE_BASE_URL: str = "https://api.bseindia.com"
    NSE_REQUEST_DELAY_SECONDS: float = 2.0

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """
        Render (and some other providers) give a plain postgresql:// URL.
        SQLAlchemy asyncpg driver requires postgresql+asyncpg://.
        Auto-fix it here so no manual editing is needed.
        """
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def production_checks(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def qdrant_enabled(self) -> bool:
        """True only when a Qdrant URL is explicitly configured."""
        return bool(self.QDRANT_URL and self.QDRANT_URL.startswith("http"))


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Singleton throughout app lifetime."""
    return Settings()


settings = get_settings()
