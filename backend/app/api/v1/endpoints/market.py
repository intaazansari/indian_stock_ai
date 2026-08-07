"""Market overview endpoint — live index data via yfinance."""
from __future__ import annotations

import asyncio
from functools import lru_cache
from time import time
from typing import Any

import yfinance as yf
from fastapi import APIRouter

router = APIRouter()

# Simple in-process cache: (data, fetched_at)
_cache: dict[str, Any] = {}
_CACHE_TTL = 60  # seconds

INDICES = [
    {"symbol": "^NSEI",        "name": "NIFTY 50",     "short": "NIFTY"},
    {"symbol": "^BSESN",       "name": "SENSEX",        "short": "SENSEX"},
    {"symbol": "^NSEBANK",     "name": "NIFTY Bank",    "short": "BANK"},
    {"symbol": "NIFTYIT.NS",   "name": "NIFTY IT",      "short": "IT"},
    {"symbol": "^CNXPHARMA",  "name": "NIFTY Pharma",  "short": "PHARMA"},
]


def _fetch_index(ticker_symbol: str) -> dict[str, Any]:
    t = yf.Ticker(ticker_symbol)
    info = t.fast_info
    price = float(info.last_price or 0)

    # fast_info.previous_close is unreliable for some Indian indices —
    # fall back to the last two rows of 1d history if price or prev is zero.
    prev = float(info.previous_close or 0)
    if price == 0 or prev == 0:
        hist = t.history(period="5d", interval="1d")
        if len(hist) >= 2:
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2])
        elif len(hist) == 1:
            price = float(hist["Close"].iloc[-1])
            prev  = price

    if price == 0:
        raise ValueError(f"No price data for {ticker_symbol}")

    change = price - prev
    change_pct = (change / prev * 100) if prev else 0.0
    return {
        "price":      round(price, 2),
        "change":     round(change, 2),
        "change_pct": round(change_pct, 2),
    }


@router.get("/indices", tags=["Market"])
async def get_market_indices() -> list[dict]:
    global _cache
    now = time()
    if "data" in _cache and now - _cache.get("ts", 0) < _CACHE_TTL:
        return _cache["data"]

    loop = asyncio.get_event_loop()

    async def fetch_one(idx: dict) -> dict:
        data = await loop.run_in_executor(None, _fetch_index, idx["symbol"])
        return {**idx, **data}

    results = await asyncio.gather(*[fetch_one(i) for i in INDICES], return_exceptions=True)
    out = []
    for r, meta in zip(results, INDICES):
        if isinstance(r, Exception):
            out.append({**meta, "price": None, "change": None, "change_pct": None})
        else:
            out.append(r)

    _cache = {"data": out, "ts": now}
    return out
