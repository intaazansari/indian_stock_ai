"""Market overview endpoint — live index data via yfinance."""
from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, time as dt_time
from time import time
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf
from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.dependencies import DBSession, RedisClient
from app.models.market_mover import MarketMover
from app.schemas.market import MarketMoversResponse, MarketMoverItem

router = APIRouter()

_IST = ZoneInfo("Asia/Kolkata")

# In-process fallback cache: (data, fetched_at)
_cache: dict[str, Any] = {}
_CACHE_TTL_OPEN   =    60  # seconds — live during trading hours
_CACHE_TTL_CLOSED = 4 * 3600  # 4 h — data doesn't change when market is closed

_REDIS_KEY = "market:indices"


def _is_market_open() -> bool:
    now = datetime.now(_IST)
    if now.weekday() >= 5:          # Saturday / Sunday
        return False
    t = now.time()
    return dt_time(9, 15) <= t <= dt_time(15, 30)

INDICES = [
    {"symbol": "^NSEI",       "name": "NIFTY 50",    "short": "NIFTY"},
    {"symbol": "^BSESN",      "name": "SENSEX",       "short": "SENSEX"},
    {"symbol": "^NSEBANK",    "name": "NIFTY Bank",   "short": "BANK"},
    {"symbol": "^CNXIT",      "name": "NIFTY IT",     "short": "IT"},
    {"symbol": "^CNXPHARMA",  "name": "NIFTY Pharma", "short": "PHARMA"},
]


def _fetch_all_indices() -> list[dict]:
    """Bulk-download last 5 days of OHLCV for all index symbols.

    Uses yf.download() for reliability on cloud servers.
    Falls back to individual Ticker.history() for any symbol with missing data.
    """
    symbols = [idx["symbol"] for idx in INDICES]

    # --- Primary: bulk download ---
    bulk: dict[str, tuple[float, float]] = {}  # symbol -> (price, prev)
    try:
        data = yf.download(
            symbols,
            period="5d",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        close = data["Close"]
        for sym in symbols:
            try:
                col = close[sym].dropna()
                if len(col) >= 1:
                    price = float(col.iloc[-1])
                    prev  = float(col.iloc[-2]) if len(col) >= 2 else price
                    if not math.isnan(price):
                        bulk[sym] = (price, prev)
            except Exception:
                pass
    except Exception:
        pass  # all symbols will fall through to individual fetch

    # --- Fallback: individual Ticker.history() for missing symbols ---
    for sym in symbols:
        if sym not in bulk:
            try:
                hist = yf.Ticker(sym).history(period="5d", interval="1d")
                col = hist["Close"].dropna()
                if len(col) >= 1:
                    price = float(col.iloc[-1])
                    prev  = float(col.iloc[-2]) if len(col) >= 2 else price
                    bulk[sym] = (price, prev)
            except Exception:
                pass

    out = []
    for idx in INDICES:
        sym = idx["symbol"]
        if sym in bulk:
            price, prev = bulk[sym]
            change     = round(price - prev, 2)
            change_pct = round((change / prev * 100) if prev else 0.0, 2)
            out.append({**idx, "price": round(price, 2), "change": change, "change_pct": change_pct})
        else:
            out.append({**idx, "price": None, "change": None, "change_pct": None})

    return out


@router.get("/indices", tags=["Market"])
async def get_market_indices(redis: RedisClient) -> list[dict]:
    global _cache
    now = time()
    ttl = _CACHE_TTL_OPEN if _is_market_open() else _CACHE_TTL_CLOSED

    # 1. Try Redis (survives cold starts)
    if redis is not None:
        try:
            cached_raw = await redis.get(_REDIS_KEY)
            if cached_raw:
                return json.loads(cached_raw)
        except Exception:
            pass

    # 2. In-process fallback
    if "data" in _cache and now - _cache.get("ts", 0) < ttl:
        return _cache["data"]

    loop = asyncio.get_event_loop()
    indices = await loop.run_in_executor(None, _fetch_all_indices)

    # Attach a human-readable timestamp so the frontend can show "as of HH:MM"
    as_of = datetime.now(_IST).strftime("%d %b %I:%M %p IST")
    out = [{**idx, "as_of": as_of} for idx in indices]

    _cache = {"data": out, "ts": now}
    if redis is not None:
        try:
            await redis.setex(_REDIS_KEY, ttl, json.dumps(out))
        except Exception:
            pass
    return out


@router.get("/movers", response_model=MarketMoversResponse, tags=["Market"])
async def get_market_movers(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=50),
) -> MarketMoversResponse:
    """
    Top Gainers / Losers for the most recent trading day we have data for.

    Rows are populated once per trading day by `scripts/refresh_prices.py`
    (Mon-Fri after NSE close; NSE holidays are skipped automatically).
    """
    latest_date = (
        await db.execute(select(func.max(MarketMover.date)))
    ).scalar_one_or_none()

    if latest_date is None:
        return MarketMoversResponse(date=None, gainers=[], losers=[])

    async def _fetch(mover_type: str) -> list[MarketMoverItem]:
        stmt = (
            select(MarketMover)
            .where(MarketMover.date == latest_date, MarketMover.type == mover_type)
            .order_by(MarketMover.rank.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [MarketMoverItem.model_validate(row) for row in result.scalars().all()]

    gainers = await _fetch("gainer")
    losers = await _fetch("loser")

    return MarketMoversResponse(date=latest_date, gainers=gainers, losers=losers)
