"""Market overview endpoint — live index data via yfinance."""
from __future__ import annotations

import asyncio
import math
from time import time
from typing import Any

import yfinance as yf
from fastapi import APIRouter

router = APIRouter()

# Simple in-process cache: (data, fetched_at)
_cache: dict[str, Any] = {}
_CACHE_TTL = 60  # seconds

INDICES = [
    {"symbol": "^NSEI",       "name": "NIFTY 50",    "short": "NIFTY"},
    {"symbol": "^BSESN",      "name": "SENSEX",       "short": "SENSEX"},
    {"symbol": "^NSEBANK",    "name": "NIFTY Bank",   "short": "BANK"},
    {"symbol": "^CNXIT",      "name": "NIFTY IT",     "short": "IT"},
    {"symbol": "^CNXPHARMA",  "name": "NIFTY Pharma", "short": "PHARMA"},
]


def _fetch_all_indices() -> list[dict]:
    """Bulk-download last 2 days of OHLCV for all index symbols.

    Using yf.download() is more reliable than individual Ticker.fast_info
    calls on cloud servers where per-ticker requests may be rate-limited.
    """
    symbols = [idx["symbol"] for idx in INDICES]
    data = yf.download(
        symbols,
        period="5d",
        interval="1d",
        progress=False,
        auto_adjust=True,
    )

    close = data["Close"] if "Close" in data.columns.get_level_values(0) else data

    out = []
    for idx in INDICES:
        sym = idx["symbol"]
        try:
            col = close[sym].dropna()
            if len(col) < 1:
                raise ValueError("no data")
            price = float(col.iloc[-1])
            prev  = float(col.iloc[-2]) if len(col) >= 2 else price
            if math.isnan(price):
                raise ValueError("NaN price")
            change     = round(price - prev, 2)
            change_pct = round((change / prev * 100) if prev else 0.0, 2)
            out.append({**idx, "price": round(price, 2), "change": change, "change_pct": change_pct})
        except Exception:
            out.append({**idx, "price": None, "change": None, "change_pct": None})

    return out


@router.get("/indices", tags=["Market"])
async def get_market_indices() -> list[dict]:
    global _cache
    now = time()
    if "data" in _cache and now - _cache.get("ts", 0) < _CACHE_TTL:
        return _cache["data"]

    loop = asyncio.get_event_loop()
    out = await loop.run_in_executor(None, _fetch_all_indices)

    _cache = {"data": out, "ts": now}
    return out
