"""Watchlist endpoints — add, list, and remove companies from a user's watchlist."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.dependencies import CurrentUserID, DBSession
from app.models.watchlist import Watchlist
from app.models.company import Company
from sqlalchemy import select, delete

router = APIRouter()


class WatchlistItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    nse_symbol: str | None
    name: str | None
    sector: str | None
    market_cap_cr: float | None
    cmp: float | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[WatchlistItem])
async def list_watchlist(user_id: CurrentUserID, db: DBSession) -> list[WatchlistItem]:
    """Return all companies in the authenticated user's watchlist."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(Watchlist, Company)
        .join(Company, Watchlist.company_id == Company.id)
        .where(Watchlist.user_id == uid)
        .order_by(Watchlist.created_at.desc())
    )
    rows = result.all()
    return [
        WatchlistItem(
            id=wl.id,
            company_id=wl.company_id,
            nse_symbol=co.nse_symbol,
            name=co.name,
            sector=co.sector,
            market_cap_cr=float(co.market_cap_cr) if co.market_cap_cr is not None else None,
            cmp=float(co.cmp) if co.cmp is not None else None,
        )
        for wl, co in rows
    ]


@router.post("/{company_id}", status_code=201)
async def add_to_watchlist(
    company_id: uuid.UUID,
    user_id: CurrentUserID,
    db: DBSession,
) -> dict:
    """Add a company to the user's watchlist."""
    uid = uuid.UUID(user_id)

    # Verify company exists
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check for duplicate
    existing = (await db.execute(
        select(Watchlist).where(Watchlist.user_id == uid, Watchlist.company_id == company_id)
    )).scalar_one_or_none()
    if existing:
        return {"message": "Already in watchlist"}

    item = Watchlist(user_id=uid, company_id=company_id)
    db.add(item)
    await db.commit()
    return {"message": "Added to watchlist", "id": str(item.id)}


@router.delete("/{company_id}", status_code=200)
async def remove_from_watchlist(
    company_id: uuid.UUID,
    user_id: CurrentUserID,
    db: DBSession,
) -> dict:
    """Remove a company from the user's watchlist."""
    uid = uuid.UUID(user_id)
    await db.execute(
        delete(Watchlist).where(
            Watchlist.user_id == uid, Watchlist.company_id == company_id
        )
    )
    await db.commit()
    return {"message": "Removed from watchlist"}
