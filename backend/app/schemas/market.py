"""Pydantic schemas for market-wide endpoints (indices, gainers/losers)."""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class MarketMoverItem(BaseModel):
    symbol: str
    company: str
    close: Decimal
    previous_close: Decimal
    change_pct: Decimal
    rank: int

    model_config = {"from_attributes": True}


class MarketMoversResponse(BaseModel):
    date: date_type | None
    gainers: list[MarketMoverItem]
    losers: list[MarketMoverItem]
