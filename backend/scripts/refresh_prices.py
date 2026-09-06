#!/usr/bin/env python3
"""
Daily price refresh script — updates cmp and market_cap_cr for all seeded companies,
and stores the day's Top Gainers/Losers snapshot in `market_movers`.

Uses yfinance .fast_info for a lightweight single-field fetch (much faster than
fetching full financials). Typically completes in 2-5 minutes for 500 companies.

Automatically skips weekends and NSE trading holidays (see app.core.nse_holidays) —
safe to schedule to run every day; it's a no-op when the market was closed.

Usage (run from backend/ directory):

    # Refresh all seeded companies (skips automatically on weekends/NSE holidays)
    python -m scripts.refresh_prices

    # Refresh specific symbols only
    python -m scripts.refresh_prices --symbols TCS INFY RELIANCE

    # Dry run — print what would be updated, no DB writes
    python -m scripts.refresh_prices --dry-run

    # See verbose per-company output
    python -m scripts.refresh_prices --verbose

    # Run even on a weekend/holiday (e.g. backfill/testing)
    python -m scripts.refresh_prices --force

    # Store top 10 (instead of default 15) gainers/losers per side
    python -m scripts.refresh_prices --movers-count 10
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

import yfinance as yf
import structlog
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tabulate import tabulate
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.nse_holidays import holiday_name, is_trading_day
from app.models.company import Company
from app.models.financials import IncomeStatement, KeyRatio
from app.models.market_mover import MarketMover

setup_logging()
logger = structlog.get_logger(__name__)

_IST = ZoneInfo("Asia/Kolkata")


def _fetch_price(nse_symbol: str) -> dict[str, Any]:
    """
    Fetch current price, previous close, market cap, and 52W high/low for one
    NSE symbol via yfinance.
    Returns a dict with keys: cmp, previous_close, market_cap_cr, week52_high,
    week52_low, error.
    """
    ticker_symbol = f"{nse_symbol}.NS"
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.fast_info          # lightweight — no full financials

        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", None)
        mkt_cap = getattr(info, "market_cap", None)
        year_high = getattr(info, "year_high", None)
        year_low  = getattr(info, "year_low", None)

        if price is None or price <= 0:
            return {"cmp": None, "previous_close": None, "market_cap_cr": None, "week52_high": None, "week52_low": None, "error": "no price data"}

        mkt_cap_cr = round(mkt_cap / 1e7, 2) if mkt_cap else None  # ₹ → ₹ Crore

        return {
            "cmp": round(float(price), 2),
            "previous_close": round(float(prev_close), 2) if prev_close else None,
            "market_cap_cr": mkt_cap_cr,
            "week52_high": round(float(year_high), 2) if year_high else None,
            "week52_low":  round(float(year_low), 2)  if year_low  else None,
            "error": None,
        }
    except Exception as exc:
        return {"cmp": None, "previous_close": None, "market_cap_cr": None, "week52_high": None, "week52_low": None, "error": str(exc)[:80]}


async def _persist_market_movers(
    session_factory: async_sessionmaker[AsyncSession],
    results: list[dict],
    movers_date: date,
    movers_count: int,
    dry_run: bool,
) -> tuple[list[dict], list[dict]]:
    """
    Compute Top-N Gainers/Losers from this run's fetched prices and persist
    them to the `market_movers` table (one row per symbol per type per date).

    Change % = ((close - previous_close) / previous_close) * 100.
    Re-running for the same date overwrites that date's rows (idempotent).
    """
    movable = [
        r for r in results
        if r["status"] == "ok" and r["change_pct"] is not None
    ]

    gainers = sorted(movable, key=lambda r: r["change_pct"], reverse=True)[:movers_count]
    losers = sorted(movable, key=lambda r: r["change_pct"])[:movers_count]

    if dry_run:
        return gainers, losers

    async with session_factory() as session:
        # Idempotent: wipe any existing rows for this date before inserting.
        await session.execute(delete(MarketMover).where(MarketMover.date == movers_date))

        rows = []
        for mover_type, ranked in (("gainer", gainers), ("loser", losers)):
            for rank, r in enumerate(ranked, start=1):
                rows.append(
                    MarketMover(
                        date=movers_date,
                        symbol=r["symbol"],
                        company=r["full_name"],
                        close=Decimal(str(r["new_cmp"])),
                        previous_close=Decimal(str(r["previous_close"])),
                        change_pct=Decimal(str(r["change_pct"])),
                        type=mover_type,
                        rank=rank,
                    )
                )
        session.add_all(rows)
        await session.commit()

    return gainers, losers


async def refresh_prices(
    symbols: list[str] | None,
    dry_run: bool,
    verbose: bool,
    force: bool,
    skip_movers: bool,
    movers_count: int,
) -> None:
    today = datetime.now(_IST).date()

    if not force and not is_trading_day(today):
        reason = holiday_name(today) or "weekend"
        print(f"\nNSE is closed today ({today.isoformat()} — {reason}). Skipping refresh.")
        print("Pass --force to run anyway (e.g. for backfill/testing).\n")
        return

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

            change_pct = None
            if fetched["cmp"] is not None and fetched["previous_close"]:
                change_pct = round(
                    (fetched["cmp"] - fetched["previous_close"]) / fetched["previous_close"] * 100,
                    2,
                )

            result_row = {
                "symbol": symbol,
                "name":   (row.name or "")[:28],
                "full_name": row.name or "",
                "old_cmp": float(row.cmp) if row.cmp else None,
                "new_cmp": fetched["cmp"],
                "previous_close": fetched["previous_close"],
                "change_pct": change_pct,
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

    if not skip_movers:
        gainers, losers = await _persist_market_movers(
            session_factory=session_factory,
            results=results,
            movers_date=today,
            movers_count=movers_count,
            dry_run=dry_run,
        )
    else:
        gainers, losers = [], []

    await engine.dispose()

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    ok  = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'─' * 70}")
    print(f"  Done in {elapsed}s  |  ✓ {ok} updated  |  ✗ {err} failed")
    print(f"{'─' * 70}\n")

    if not skip_movers:
        print(f"Top {len(gainers)} Gainers:")
        print(tabulate(
            [[i + 1, g['symbol'], g['name'][:28], f"₹{g['new_cmp']:.2f}", f"+{g['change_pct']:.2f}%"] for i, g in enumerate(gainers)],
            headers=["#", "Symbol", "Name", "Close", "Change %"],
            tablefmt="rounded_outline",
        ))
        print(f"\nTop {len(losers)} Losers:")
        print(tabulate(
            [[i + 1, l['symbol'], l['name'][:28], f"₹{l['new_cmp']:.2f}", f"{l['change_pct']:.2f}%"] for i, l in enumerate(losers)],
            headers=["#", "Symbol", "Name", "Close", "Change %"],
            tablefmt="rounded_outline",
        ))
        print()

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
    parser.add_argument(
        "--force", action="store_true",
        help="Run even if today is a weekend or NSE holiday (e.g. backfill/testing)",
    )
    parser.add_argument(
        "--skip-movers", action="store_true",
        help="Skip computing/storing the Top Gainers/Losers snapshot",
    )
    parser.add_argument(
        "--movers-count", type=int, default=15, metavar="N",
        help="How many top gainers/losers to store per side (default: 15)",
    )
    args = parser.parse_args()

    asyncio.run(refresh_prices(
        symbols=args.symbols,
        dry_run=args.dry_run,
        verbose=args.verbose,
        force=args.force,
        skip_movers=args.skip_movers,
        movers_count=args.movers_count,
    ))


if __name__ == "__main__":
    main()
