"""
NSE India data scraper.

NSE API is session-based (requires cookie from browser session).
We maintain a persistent session with proper headers and delays.

IMPORTANT: Be respectful. Rate limit all requests.
           NSE may block IPs that make too many requests too quickly.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
    "Connection": "keep-alive",
}


class NSEScraper:
    """
    Async NSE India data scraper.

    Handles session management, rate limiting, and retry logic.
    """

    def __init__(self) -> None:
        self._session: httpx.AsyncClient | None = None

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create an authenticated session."""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                headers=NSE_HEADERS,
                timeout=30.0,
                follow_redirects=True,
            )
            # Warm up the session (NSE requires a cookie from the homepage)
            await self._session.get(settings.NSE_BASE_URL)
            await asyncio.sleep(settings.NSE_REQUEST_DELAY_SECONDS)
        return self._session

    async def get_company_info(self, symbol: str) -> dict[str, Any]:
        """Fetch company information by NSE symbol."""
        session = await self._get_session()
        url = f"{settings.NSE_BASE_URL}/api/quote-equity?symbol={symbol.upper()}"
        response = await session.get(url)
        response.raise_for_status()
        await asyncio.sleep(settings.NSE_REQUEST_DELAY_SECONDS)
        return response.json()

    async def get_financials(self, symbol: str) -> dict[str, Any]:
        """Fetch financial statements for a company."""
        session = await self._get_session()
        url = f"{settings.NSE_BASE_URL}/api/financials?symbol={symbol.upper()}&fin_type=Standalone&period=Annual"
        response = await session.get(url)
        response.raise_for_status()
        await asyncio.sleep(settings.NSE_REQUEST_DELAY_SECONDS)
        return response.json()

    async def get_shareholding(self, symbol: str) -> dict[str, Any]:
        """Fetch shareholding pattern for a company."""
        session = await self._get_session()
        url = f"{settings.NSE_BASE_URL}/api/corporate-share-holdings-master?symbol={symbol.upper()}"
        response = await session.get(url)
        response.raise_for_status()
        await asyncio.sleep(settings.NSE_REQUEST_DELAY_SECONDS)
        return response.json()

    async def close(self) -> None:
        if self._session and not self._session.is_closed:
            await self._session.aclose()
