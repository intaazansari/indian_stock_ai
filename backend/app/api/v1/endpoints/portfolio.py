"""Portfolio endpoints — add holdings, list with P&L, remove."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete

from app.core.dependencies import CurrentUserID, DBSession
from app.models.watchlist import Portfolio
from app.models.company import Company

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class AddHoldingRequest(BaseModel):
    symbol: str = Field(..., description="NSE symbol e.g. TCS")
    buy_price: Decimal = Field(..., gt=0, description="Average buy price in ₹")
    quantity: Decimal = Field(..., gt=0, description="Number of shares")
    buy_date: date | None = None
    notes: str | None = Field(None, max_length=1000)


class HoldingItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    nse_symbol: str
    name: str
    sector: str | None
    buy_price: float
    quantity: float
    buy_date: date | None
    notes: str | None
    # current price
    cmp: float | None
    # P&L fields
    invested_value: float
    current_value: float | None
    gain_loss: float | None
    gain_loss_pct: float | None

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    total_invested: float
    total_current_value: float | None
    total_gain_loss: float | None
    total_gain_loss_pct: float | None
    holdings: list[HoldingItem]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_pnl(holding: Portfolio, cmp: Decimal | None) -> HoldingItem:
    buy_price = float(holding.buy_price)
    quantity = float(holding.quantity)
    invested = round(buy_price * quantity, 2)

    current_value: float | None = None
    gain_loss: float | None = None
    gain_loss_pct: float | None = None

    if cmp is not None:
        cv = round(float(cmp) * quantity, 2)
        current_value = cv
        gain_loss = round(cv - invested, 2)
        gain_loss_pct = round((gain_loss / invested) * 100, 2) if invested else None

    return HoldingItem(
        id=holding.id,
        company_id=holding.company_id,
        nse_symbol=holding.company.nse_symbol,
        name=holding.company.name,
        sector=holding.company.sector,
        buy_price=buy_price,
        quantity=quantity,
        buy_date=holding.buy_date.date() if holding.buy_date else None,
        notes=holding.notes,
        cmp=float(cmp) if cmp is not None else None,
        invested_value=invested,
        current_value=current_value,
        gain_loss=gain_loss,
        gain_loss_pct=gain_loss_pct,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PortfolioSummary)
async def list_portfolio(user_id: CurrentUserID, db: DBSession) -> PortfolioSummary:
    """Return all holdings for the authenticated user with live P&L."""
    uid = uuid.UUID(user_id)

    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == uid)
        .order_by(Portfolio.created_at.desc())
    )
    holdings_orm = result.scalars().all()

    # Eager-load company for each holding
    # (relationship is already declared, just fetch company data)
    company_ids = [h.company_id for h in holdings_orm]
    if company_ids:
        co_result = await db.execute(
            select(Company).where(Company.id.in_(company_ids))
        )
        companies_map = {c.id: c for c in co_result.scalars().all()}
        for h in holdings_orm:
            h.company = companies_map.get(h.company_id)  # type: ignore[assignment]

    items = [_compute_pnl(h, h.company.cmp if h.company else None) for h in holdings_orm]

    total_invested = sum(i.invested_value for i in items)
    total_current = (
        sum(i.current_value for i in items if i.current_value is not None)
        if any(i.current_value is not None for i in items)
        else None
    )
    total_gl = round(total_current - total_invested, 2) if total_current is not None else None
    total_gl_pct = (
        round((total_gl / total_invested) * 100, 2)
        if total_gl is not None and total_invested
        else None
    )

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        total_current_value=total_current,
        total_gain_loss=total_gl,
        total_gain_loss_pct=total_gl_pct,
        holdings=items,
    )


@router.post("", status_code=201, response_model=HoldingItem)
async def add_holding(
    body: AddHoldingRequest,
    user_id: CurrentUserID,
    db: DBSession,
) -> HoldingItem:
    """Add a new holding to the portfolio."""
    uid = uuid.UUID(user_id)

    company = (await db.execute(
        select(Company).where(Company.nse_symbol == body.symbol.upper())
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{body.symbol}' not found")

    from datetime import datetime
    buy_dt = (
        datetime.combine(body.buy_date, datetime.min.time())
        if body.buy_date else None
    )

    holding = Portfolio(
        user_id=uid,
        company_id=company.id,
        buy_price=body.buy_price,
        quantity=body.quantity,
        buy_date=buy_dt,
        notes=body.notes,
    )
    holding.company = company  # type: ignore[assignment]
    db.add(holding)
    await db.commit()
    await db.refresh(holding)

    return _compute_pnl(holding, company.cmp)


@router.delete("/{holding_id}", status_code=200)
async def remove_holding(
    holding_id: uuid.UUID,
    user_id: CurrentUserID,
    db: DBSession,
) -> dict:
    """Remove a holding from the portfolio."""
    uid = uuid.UUID(user_id)

    result = await db.execute(
        delete(Portfolio).where(
            Portfolio.id == holding_id,
            Portfolio.user_id == uid,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Holding not found")
    await db.commit()
    return {"message": "Holding removed"}
