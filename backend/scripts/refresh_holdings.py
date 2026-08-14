#!/usr/bin/env python3
"""
Weekly holdings refresh — updates promoter/FII/DII/public holding percentages
for all seeded companies using Screener.in.

Runs after market close every Sunday. Only refreshes companies that already have
financial data (key_ratios), which are the meaningfully seeded ones (~50 Nifty).

Usage (run from backend/ directory):

    # Refresh all seeded companies
    python -m scripts.refresh_holdings

    # Refresh specific symbols
    python -m scripts.refresh_holdings --symbols TCS INFY RELIANCE

    # Include all 500+ companies (slow, ~30 min)
    python -m scripts.refresh_holdings --all

    # Dry run — print what would change, no DB writes
    python -m scripts.refresh_holdings --dry-run

    # Verbose output
    python -m scripts.refresh_holdings --verbose
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

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tabulate import tabulate
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.models.company import Company
from app.models.financials import KeyRatio

setup_logging()
logger = structlog.get_logger(__name__)


def _fetch_holdings(nse_symbol: str, bse_code: str | None) -> dict[str, Any]:
    """Fetch promoter/FII/DII holdings from Screener.in (with BSE code fallback)."""
    # Import here to avoid circular issues when running as __main__
    from scripts.fetchers.screener_fetcher import ScreenerFetcher  # type: ignore[import]
    try:
        scraper = ScreenerFetcher(delay=1.5)
        data = scraper.fetch_holding_data(nse_symbol, bse_code=bse_code)
        if not data:
            return {"error": "empty response from Screener"}
        return {
            "promoter_holding_pct": data.get("promoter_holding_pct"),
            "fii_holding_pct":      data.get("fii_holding_pct"),
            "dii_holding_pct":      data.get("dii_holding_pct"),
            "public_holding_pct":   data.get("public_holding_pct"),
            "bse_code_found":       data.get("bse_code"),
            "error": None,
        }
    except Exception as exc:
        return {"error": str(exc)[:100]}


async def refresh_holdings(
    symbols: list[str] | None,
    refresh_all: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # ── Load companies to refresh ─────────────────────────────────────────────
    async with session_factory() as session:
        stmt = select(
            Company.id,
            Company.nse_symbol,
            Company.bse_code,
            Company.name,
            Company.promoter_holding_pct,
        )
        if symbols:
            stmt = stmt.where(Company.nse_symbol.in_([s.upper() for s in symbols]))
        elif refresh_all:
            stmt = stmt.where(Company.nse_symbol.isnot(None))
        else:
            # Default: only companies that have been fully seeded (have key ratios)
            seeded_ids = select(KeyRatio.company_id).distinct()
            stmt = stmt.where(
                Company.nse_symbol.isnot(None),
                Company.id.in_(seeded_ids),
            )

        result = await session.execute(stmt)
        companies = result.all()

    if not companies:
        print("No companies found. Have you seeded the database?")
        return

    mode = "[DRY RUN] " if dry_run else ""
    scope = "all" if refresh_all else ("selected" if symbols else "seeded")
    print(f"\n{mode}Refreshing holdings for {len(companies)} {scope} companies\n")

    results: list[dict] = []
    start = time.time()

    with tqdm(companies, unit="co", colour="cyan") as pbar:
        for row in pbar:
            symbol  = row.nse_symbol
            bse     = row.bse_code
            pbar.set_description(f"{symbol:<12}")

            fetched = _fetch_holdings(symbol, bse)

            result_row: dict[str, Any] = {
                "symbol":      symbol,
                "name":        (row.name or "")[:28],
                "old_promoter": float(row.promoter_holding_pct) if row.promoter_holding_pct else None,
                "new_promoter": float(fetched["promoter_holding_pct"]) if fetched.get("promoter_holding_pct") else None,
                "status": "ok" if fetched["error"] is None else "error",
                "error":  fetched.get("error") or "",
            }
            results.append(result_row)

            if not dry_run and fetched.get("error") is None:
                async with session_factory() as session:
                    update_vals: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

                    for field in ("promoter_holding_pct", "fii_holding_pct", "dii_holding_pct", "public_holding_pct"):
                        val = fetched.get(field)
                        if val is not None:
                            update_vals[field] = Decimal(str(val))

                    # If Screener returned a BSE code we didn't have, save it
                    if fetched.get("bse_code_found") and not bse:
                        update_vals["bse_code"] = fetched["bse_code_found"]

                    await session.execute(
                        update(Company)
                        .where(Company.nse_symbol == symbol)
                        .values(**update_vals)
                    )
                    await session.commit()

                logger.info(
                    "holdings.updated",
                    symbol=symbol,
                    promoter=result_row["new_promoter"],
                )

    await engine.dispose()

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    ok  = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'─' * 70}")
    print(f"  Done in {elapsed}s  |  ✓ {ok} updated  |  ✗ {err} failed")
    print(f"{'─' * 70}\n")

    rows_to_show = results if verbose else [r for r in results if r["status"] == "error"]
    if rows_to_show:
        table = [
            [
                r["symbol"],
                r["name"],
                f"{r['old_promoter']:.1f}%" if r["old_promoter"] else "—",
                f"{r['new_promoter']:.1f}%" if r["new_promoter"] else "—",
                r["status"],
                r["error"],
            ]
            for r in rows_to_show
        ]
        print(tabulate(
            table,
            headers=["Symbol", "Name", "Old Promoter%", "New Promoter%", "Status", "Error"],
            tablefmt="rounded_outline",
        ))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh promoter/FII/DII holdings from Screener.in for seeded companies."
    )
    parser.add_argument(
        "--symbols", nargs="+", metavar="SYMBOL",
        help="Refresh only these NSE symbols (e.g. --symbols TCS INFY)",
    )
    parser.add_argument(
        "--all", action="store_true", dest="refresh_all",
        help="Refresh all 500+ companies, not just the seeded ones (slow)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and print results without writing to DB",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show all companies in the summary table",
    )
    args = parser.parse_args()
    asyncio.run(refresh_holdings(
        symbols=args.symbols,
        refresh_all=args.refresh_all,
        dry_run=args.dry_run,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    main()
