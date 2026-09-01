from __future__ import annotations

import json
import math
from datetime import datetime
from time import time
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf
from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import DBSession, OptionalUserID, RedisClient
from app.schemas.common import PaginationParams
from app.schemas.company import CompanyDetail, CompanySearchResult, PeerCompanyItem
from app.schemas.common import PaginatedResponse
from app.services.company_service import CompanyService

router = APIRouter()

_IST = ZoneInfo("Asia/Kolkata")

# ── In-process fallback caches (used when Redis is unavailable) ────────────
_ph_cache: dict[str, tuple[list[dict], float]] = {}   # key → (data, fetched_at)
_PH_TTL = 300  # 5 minutes

_lp_cache: dict[str, tuple[dict, float]] = {}   # symbol → (data, fetched_at)
_LP_TTL = 60  # 60 seconds

# yfinance period strings accepted by the API
_VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "3y", "5y"}

# Redis TTLs (slightly longer than in-process to amortise cold-start cost)
_REDIS_PH_TTL = 300   # 5 minutes — matches in-process TTL
_REDIS_LP_TTL = 60    # 60 seconds


@router.get("/{symbol}", response_model=CompanyDetail)
async def get_company(symbol: str, db: DBSession) -> CompanyDetail:
    """
    Get full company profile by NSE symbol or BSE code.

    This is the entry point to the company page.
    Returns complete company metadata including promoter holding,
    sector classification, and market data.
    """
    service = CompanyService(db)
    company = await service.get_by_symbol(symbol.upper())
    return CompanyDetail.model_validate(company)


@router.get("/{symbol}/peers", response_model=list[PeerCompanyItem])
async def get_peers(symbol: str, db: DBSession) -> list[PeerCompanyItem]:
    """
    Get peer companies for comparison.

    Peers are companies in the same industry, ordered by market cap.
    """
    service = CompanyService(db)
    return await service.get_peers(symbol.upper())


@router.get("/{symbol}/price-history")
async def get_price_history(
    symbol: str,
    redis: RedisClient,
    period: str = Query(default="1y", description="One of: 1mo 3mo 6mo 1y 3y 5y"),
) -> list[dict[str, Any]]:
    """
    Return daily OHLCV price history for a company.

    Fetched from Yahoo Finance and cached for 5 minutes in Redis (with
    in-process dict as fallback when Redis is unavailable).
    Data points: {date, open, high, low, close, volume}
    """
    if period not in _VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Must be one of {sorted(_VALID_PERIODS)}")

    sym = symbol.upper()
    cache_key = f"ph:{sym}:{period}"

    # 1. Try Redis (survives cold starts)
    if redis is not None:
        try:
            cached_raw = await redis.get(cache_key)
            if cached_raw:
                return json.loads(cached_raw)
        except Exception:
            pass

    # 2. Try in-process fallback
    if cache_key in _ph_cache:
        cached_data, fetched_at = _ph_cache[cache_key]
        if time() - fetched_at < _PH_TTL:
            return cached_data

    ticker = yf.Ticker(f"{sym}.NS")
    hist = ticker.history(period=period, interval="1d", auto_adjust=True)

    if hist.empty:
        raise HTTPException(status_code=404, detail=f"No price data found for {symbol}")

    result: list[dict[str, Any]] = []
    for idx, row in hist.iterrows():
        close = float(row["Close"])
        if math.isnan(close):
            continue
        result.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2) if not math.isnan(float(row["Open"])) else close,
            "high": round(float(row["High"]), 2) if not math.isnan(float(row["High"])) else close,
            "low": round(float(row["Low"]), 2) if not math.isnan(float(row["Low"])) else close,
            "close": round(close, 2),
            "volume": int(row["Volume"]) if not math.isnan(float(row["Volume"])) else 0,
        })

    _ph_cache[cache_key] = (result, time())
    if redis is not None:
        try:
            await redis.setex(cache_key, _REDIS_PH_TTL, json.dumps(result))
        except Exception:
            pass
    return result


@router.get("/{symbol}/live-price")
async def get_live_price(symbol: str, redis: RedisClient) -> dict[str, Any]:
    """
    Return the latest market price for a company using yfinance fast_info.

    Much faster than price-history — single lightweight API call.
    Cached for 60 seconds in Redis (in-process dict as fallback).
    Returns: {cmp, prev_close, change, change_pct, week52_high, week52_low,
              market_cap_cr, volume, as_of}
    """
    sym = symbol.upper()
    redis_key = f"lp:{sym}"

    # 1. Try Redis (survives cold starts)
    if redis is not None:
        try:
            cached_raw = await redis.get(redis_key)
            if cached_raw:
                return json.loads(cached_raw)
        except Exception:
            pass

    # 2. In-process fallback
    if sym in _lp_cache:
        cached, fetched_at = _lp_cache[sym]
        if time() - fetched_at < _LP_TTL:
            return cached

    ticker = yf.Ticker(f"{sym}.NS")

    try:
        fi = ticker.fast_info
        cmp        = _safe_float(fi.last_price)
        prev_close = _safe_float(fi.previous_close)
        w52h       = _safe_float(fi.year_high)
        w52l       = _safe_float(fi.year_low)
        mktcap     = _safe_float(fi.market_cap)
        volume     = _safe_int(fi.three_month_average_volume)

        if cmp is None:
            raise ValueError("No price data")

        change     = round(cmp - prev_close, 2) if prev_close else None
        change_pct = round((change / prev_close) * 100, 2) if (change is not None and prev_close) else None
        mktcap_cr  = round(mktcap / 1e7, 2) if mktcap else None

        result: dict[str, Any] = {
            "cmp":          round(cmp, 2),
            "prev_close":   round(prev_close, 2) if prev_close else None,
            "change":       change,
            "change_pct":   change_pct,
            "week52_high":  round(w52h, 2) if w52h else None,
            "week52_low":   round(w52l, 2) if w52l else None,
            "market_cap_cr": mktcap_cr,
            "volume":       volume,
            "as_of":        datetime.now(_IST).isoformat(),
        }
        _lp_cache[sym] = (result, time())
        if redis is not None:
            try:
                await redis.setex(redis_key, _REDIS_LP_TTL, json.dumps(result))
            except Exception:
                pass
        return result

    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Live price unavailable for {sym}: {exc}") from exc


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> int | None:
    try:
        f = float(v)
        return None if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return None
