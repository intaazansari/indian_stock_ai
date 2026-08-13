from __future__ import annotations

import math
from time import time
from typing import Any

import yfinance as yf
from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import DBSession, OptionalUserID
from app.schemas.common import PaginationParams
from app.schemas.company import CompanyDetail, CompanySearchResult, PeerCompanyItem
from app.schemas.common import PaginatedResponse
from app.services.company_service import CompanyService

router = APIRouter()

# ── Price-history in-process cache ────────────────────────────────────────
_ph_cache: dict[str, tuple[list[dict], float]] = {}   # key → (data, fetched_at)
_PH_TTL = 300  # 5 minutes

# yfinance period strings accepted by the API
_VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "3y", "5y"}


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
    period: str = Query(default="1y", description="One of: 1mo 3mo 6mo 1y 3y 5y"),
) -> list[dict[str, Any]]:
    """
    Return daily OHLCV price history for a company.

    Fetched from Yahoo Finance and cached for 5 minutes.
    Data points: {date, open, high, low, close, volume}
    """
    if period not in _VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Must be one of {sorted(_VALID_PERIODS)}")

    cache_key = f"{symbol.upper()}:{period}"
    if cache_key in _ph_cache:
        cached_data, fetched_at = _ph_cache[cache_key]
        if time() - fetched_at < _PH_TTL:
            return cached_data

    ticker_symbol = f"{symbol.upper()}.NS"
    ticker = yf.Ticker(ticker_symbol)
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
    return result
