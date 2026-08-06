"""Embedding generation using an OpenAI-compatible embeddings endpoint.

IMPORTANT — Groq does not support embeddings.
If OPENAI_BASE_URL points to Groq, embeddings will fall back to the
official OpenAI API using OPENAI_EMBEDDING_API_KEY (or OPENAI_API_KEY).
Set OPENAI_EMBEDDING_API_KEY separately if you use Groq for LLMs but
need OpenAI for embeddings.
"""
from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)

_llm_client: AsyncOpenAI | None = None
_embedding_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    """Client pointed at OPENAI_BASE_URL (Groq / OpenAI / Ollama)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )
    return _llm_client


def get_embedding_client() -> AsyncOpenAI:
    """
    Client for embeddings.

    Always uses the official OpenAI endpoint because Groq and most
    alternative providers do not support the /v1/embeddings route.
    Falls back to OPENAI_API_KEY if no separate key is configured.
    """
    global _embedding_client
    if _embedding_client is None:
        # Use a separate key/URL for embeddings if provided, otherwise
        # assume OPENAI_API_KEY is a real OpenAI key with embeddings support.
        embedding_key = getattr(settings, "OPENAI_EMBEDDING_API_KEY", None) or settings.OPENAI_API_KEY
        _embedding_client = AsyncOpenAI(api_key=embedding_key)  # no base_url override
    return _embedding_client


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns a 1536-dimension vector."""
    client = get_embedding_client()
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts in a single API call."""
    if not texts:
        return []
    client = get_embedding_client()
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

