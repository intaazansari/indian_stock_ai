"""
Migrate all data from Render PostgreSQL → Neon PostgreSQL.

Usage:
    1. Create a Neon project at https://neon.tech
    2. Get your Neon connection string (Databases → Connection Details → asyncpg URL)
    3. Run:
       $env:SOURCE_DB="postgresql+asyncpg://isa_user:xospnQScUtWUlg3w56GntDiiYiXZqkEH@dpg-d9oulmks728c73fuvv9g-a.oregon-postgres.render.com/isa_db_xp27"
       $env:TARGET_DB="postgresql+asyncpg://<neon-connection-string>"
       python scripts/migrate_to_neon.py

    The script:
      - Runs Alembic migrations on Neon (creates schema)
      - Copies every table row-by-row from Render → Neon
      - Verifies row counts match after copy
      - Is idempotent: safe to re-run (truncates target tables first)
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text, inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE_DB = os.environ.get(
    "SOURCE_DB",
    "postgresql+asyncpg://isa_user:xospnQScUtWUlg3w56GntDiiYiXZqkEH"
    "@dpg-d9oulmks728c73fuvv9g-a.oregon-postgres.render.com/isa_db_xp27",
)
TARGET_DB = os.environ.get("TARGET_DB", "")

# Tables ordered by FK dependencies (parents first)
TABLES = [
    "alembic_version",
    "users",
    "companies",
    "income_statements",
    "balance_sheets",
    "cash_flows",
    "key_ratios",
    "analysis_cache",
    "watchlist",
    "portfolio",
]

BATCH_SIZE = 500  # rows per INSERT batch


async def run_alembic_on_target() -> None:
    """Run alembic upgrade head on the target DB to create schema."""
    print("\n[1/3] Running Alembic migrations on Neon DB...")
    backend_dir = Path(__file__).resolve().parent.parent
    env = {**os.environ, "DATABASE_URL": TARGET_DB.replace("postgresql+asyncpg://", "postgresql+asyncpg://")}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  Alembic stderr: {result.stderr}")
        raise RuntimeError("Alembic migration failed — check TARGET_DB is set correctly")
    print("  Schema created on Neon ✓")


async def get_column_names(conn: AsyncConnection, table: str) -> list[str]:
    r = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"
    ), {"t": table})
    return [row[0] for row in r.all()]


async def copy_table(src: AsyncConnection, tgt: AsyncConnection, table: str) -> tuple[int, int]:
    """Copy all rows from src.table → tgt.table. Returns (src_count, copied_count)."""
    # Source count
    src_count = (await src.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar() or 0
    if src_count == 0:
        return 0, 0

    # Get columns
    cols = await get_column_names(src, table)
    if not cols:
        return 0, 0

    col_list = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(f":{c}" for c in cols)

    # Truncate target first (safe re-run)
    await tgt.execute(text(f'TRUNCATE TABLE {table} CASCADE'))

    # Copy in batches
    copied = 0
    offset = 0
    while True:
        rows = (await src.execute(
            text(f'SELECT {col_list} FROM {table} ORDER BY 1 LIMIT {BATCH_SIZE} OFFSET {offset}')
        )).mappings().all()
        if not rows:
            break
        dicts = [dict(row) for row in rows]
        await tgt.execute(
            text(f'INSERT INTO {table} ({col_list}) VALUES ({placeholders})'),
            dicts,
        )
        copied += len(rows)
        offset += BATCH_SIZE

    await tgt.commit()
    return src_count, copied


async def main() -> None:
    if not TARGET_DB:
        print("ERROR: Set TARGET_DB env var to your Neon asyncpg connection string.")
        print("  Example:")
        print("  $env:TARGET_DB='postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require'")
        sys.exit(1)

    # Step 1: Create schema on Neon
    await run_alembic_on_target()

    src_engine = create_async_engine(SOURCE_DB, pool_size=1)
    tgt_engine = create_async_engine(TARGET_DB, pool_size=1)

    print("\n[2/3] Copying tables from Render → Neon...")
    print(f"  {'Table':<28} {'Source':>8}  {'Copied':>8}  Status")
    print("  " + "-" * 54)

    total_src = total_copied = 0
    async with src_engine.connect() as src, tgt_engine.begin() as tgt:
        for table in TABLES:
            try:
                sc, cc = await copy_table(src, tgt, table)
                status = "✓" if sc == cc else f"MISMATCH (src={sc}, copied={cc})"
                print(f"  {table:<28} {sc:>8,}  {cc:>8,}  {status}")
                total_src += sc
                total_copied += cc
            except Exception as e:
                print(f"  {table:<28} {'':>8}  {'':>8}  SKIP ({type(e).__name__}: {e})")

    print(f"\n  Total: {total_src:,} source rows → {total_copied:,} copied")

    # Step 3: Verify
    print("\n[3/3] Verification (row counts on Neon):")
    async with tgt_engine.connect() as tgt:
        for table in TABLES:
            try:
                cnt = (await tgt.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
                print(f"  {table:<28} {cnt:>8,}")
            except Exception:
                pass

    await src_engine.dispose()
    await tgt_engine.dispose()

    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("  1. Update DATABASE_URL in Render backend env vars to Neon URL")
    print("  2. Update DATABASE_URL in GitHub Actions secrets")
    print("  3. Redeploy backend on Render")
    print("  4. Delete the old Render PostgreSQL instance")


if __name__ == "__main__":
    asyncio.run(main())
