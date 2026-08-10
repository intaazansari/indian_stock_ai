#!/usr/bin/env python3
"""
Daily price refresh script — updates cmp and market_cap_cr for all seeded companies.

Uses yfinance .fast_info for a lightweight single-field fetch (much faster than
fetching full financials). Typically completes in 2-5 minutes for 500 companies.

Usage (run from backend/ directory):

    # Refresh all seeded companies
    python -m scripts.refresh_prices

    # Refresh specific symbols only
    python -m scripts.refresh_prices --symbols TCS INFY RELIANCE

    # Dry run — print what would be updated, no DB writes
    python -m scripts.refresh_prices --dry-run

    # See verbose per-company output
    python -m scripts.refresh_prices --verbose
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

import yfinance as yf
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tabulate import tabulate
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.models.company import Company
from app.models.financials import IncomeStatement, KeyRatio

setup_logging()
logger = structlog.get_logger(__name__)


def _fetch_price(nse_symbol: str) -> dict[str, Any]:
    """
    Fetch current price, market cap, and 52W high/low for one NSE symbol via yfinance.
    Returns a dict with keys: cmp, market_cap_cr, week52_high, week52_low, error.
    """
    ticker_symbol = f"{nse_symbol}.NS"
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.fast_info          # lightweight — no full financials

        price = getattr(info, "last_price", None)
        mkt_cap = getattr(info, "market_cap", None)
        year_high = getattr(info, "year_high", None)
        year_low  = getattr(info, "year_low", None)

        if price is None or price <= 0:
            return {"cmp": None, "market_cap_cr": None, "week52_high": None, "week52_low": None, "error": "no price data"}

        mkt_cap_cr = round(mkt_cap / 1e7, 2) if mkt_cap else None  # ₹ → ₹ Crore

        return {
            "cmp": round(float(price), 2),
            "market_cap_cr": mkt_cap_cr,
            "week52_high": round(float(year_high), 2) if year_high else None,
            "week52_low":  round(float(year_low), 2)  if year_low  else None,
            "error": None,
        }
    except Exception as exc:
        return {"cmp": None, "market_cap_cr": None, "week52_high": None, "week52_low": None, "error": str(exc)[:80]}


async def refresh_prices(
    symbols: list[str] | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # ── Load companies to refresh ─────────────────────────────────────────────
    async with session_factory() as session:
        stmt = select(Company.id, Company.nse_symbol, Company.name, Company.cmp, Company.market_cap_cr)
        if symbols:
            stmt = stmt.where(Company.nse_symbol.in_([s.upper() for s in symbols]))
        else:
            stmt = stmt.where(Company.nse_symbol.isnot(None))

        result = await session.execute(stmt)
        companies = result.all()

    if not companies:
        print("No companies found. Have you seeded the database?")
        return

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Refreshing prices for {len(companies)} companies\n")

    results: list[dict] = []
    start = time.time()

    with tqdm(companies, unit="co", colour="cyan") as pbar:
        for row in pbar:
            symbol = row.nse_symbol
            company_id = row.id
            pbar.set_description(f"{symbol:<12}")

            fetched = _fetch_price(symbol)

            result_row = {
                "symbol": symbol,
                "name":   (row.name or "")[:28],
                "old_cmp": float(row.cmp) if row.cmp else None,
                "new_cmp": fetched["cmp"],
                "old_mcap": float(row.market_cap_cr) if row.market_cap_cr else None,
                "new_mcap": fetched["market_cap_cr"],
                "status": "ok" if fetched["error"] is None else "error",
                "error": fetched["error"] or "",
            }
            results.append(result_row)

            if not dry_run and fetched["cmp"] is not None:
                async with session_factory() as session:
                    update_vals: dict[str, Any] = {}
                    if fetched["cmp"] is not None:
                        update_vals["cmp"] = Decimal(str(fetched["cmp"]))
                    if fetched["market_cap_cr"] is not None:
                        update_vals["market_cap_cr"] = Decimal(str(fetched["market_cap_cr"]))
                    if fetched["week52_high"] is not None:
                        update_vals["week52_high"] = Decimal(str(fetched["week52_high"]))
                    if fetched["week52_low"] is not None:
                        update_vals["week52_low"] = Decimal(str(fetched["week52_low"]))
                    # Always stamp updated_at so the UI can show last-sync time
                    update_vals["updated_at"] = datetime.now(timezone.utc)
                    if update_vals:
                        await session.execute(
                            update(Company)
                            .where(Company.nse_symbol == symbol)
                            .values(**update_vals)
                        )

                    # ── Update live P/E in key_ratios ─────────────────────────
                    try:
                        from sqlalchemy import desc as sa_desc, func as sa_func
                        eps_scalar = (await session.execute(
                            select(IncomeStatement.eps_basic)
                            .where(
                                IncomeStatement.company_id == company_id,
                                IncomeStatement.period_type == "annual",
                                IncomeStatement.eps_basic.isnot(None),
                            )
                            .order_by(sa_desc(IncomeStatement.period_year))
                            .limit(1)
                        )).scalar_one_or_none()

                        if eps_scalar and float(eps_scalar) > 0:
                            live_pe = round(fetched["cmp"] / float(eps_scalar), 2)
                            latest_yr = (await session.execute(
                                select(sa_func.max(KeyRatio.period_year))
                                .where(
                                    KeyRatio.company_id == company_id,
                                    KeyRatio.period_type == "annual",
                                )
                            )).scalar_one_or_none()
                            if latest_yr:
                                await session.execute(
                                    update(KeyRatio)
                                    .where(
                                        KeyRatio.company_id == company_id,
                                        KeyRatio.period_type == "annual",
                                        KeyRatio.period_year == latest_yr,
                                    )
                                    .values(pe_ratio=Decimal(str(live_pe)))
                                )
                    except Exception as pe_exc:
                        logger.warning("refresh.pe_update.failed", symbol=symbol, error=str(pe_exc))

                    await session.commit()

    await engine.dispose()

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    ok  = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'─' * 70}")
    print(f"  Done in {elapsed}s  |  ✓ {ok} updated  |  ✗ {err} failed")
    print(f"{'─' * 70}\n")

    if verbose or err:
        # Show all rows in verbose mode; otherwise only failures
        rows_to_show = results if verbose else [r for r in results if r["status"] == "error"]
        table = [
            [
                r["symbol"],
                r["name"],
                f"₹{r['old_cmp']:.0f}" if r["old_cmp"] else "—",
                f"₹{r['new_cmp']:.0f}" if r["new_cmp"] else "—",
                r["status"],
                r["error"],
            ]
            for r in rows_to_show
        ]
        print(tabulate(
            table,
            headers=["Symbol", "Name", "Old CMP", "New CMP", "Status", "Error"],
            tablefmt="rounded_outline",
        ))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh CMP and market cap for all seeded companies."
    )
    parser.add_argument(
        "--symbols", nargs="+", metavar="SYMBOL",
        help="Refresh only these NSE symbols",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch prices but do not write to the database",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-company results even on success",
    )
    args = parser.parse_args()

    asyncio.run(refresh_prices(
        symbols=args.symbols,
        dry_run=args.dry_run,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    main()
