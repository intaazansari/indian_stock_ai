import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

DB = "postgresql+asyncpg://isa_user:xospnQScUtWUlg3w56GntDiiYiXZqkEH@dpg-d9oulmks728c73fuvv9g-a.oregon-postgres.render.com/isa_db_xp27"

async def main():
    engine = create_async_engine(DB)
    async with engine.connect() as conn:

        # 1. Total DB size
        r = await conn.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database())) AS total_size,"
            " pg_database_size(current_database()) AS bytes"
        ))
        row = r.one()
        print(f"=== TOTAL DB SIZE: {row[0]} ({row[1]:,} bytes) ===\n")

        # 2. Per-table size breakdown
        r = await conn.execute(text("""
            SELECT
                relname AS table_name,
                pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
                pg_size_pretty(pg_relation_size(c.oid)) AS data_size,
                pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) AS index_size,
                pg_total_relation_size(c.oid) AS bytes
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            ORDER BY bytes DESC
        """))
        print(f"{'Table':<30} {'Total':>10} {'Data':>10} {'Indexes':>10}")
        print("-" * 64)
        for row in r.all():
            print(f"{row[0]:<30} {row[1]:>10} {row[2]:>10} {row[3]:>10}")

        # 3. Row counts
        print()
        tables = [
            "companies", "income_statements", "balance_sheets",
            "cash_flows", "key_ratios", "users", "watchlists", "analysis_cache"
        ]
        print(f"{'Table':<30} {'Rows':>10}")
        print("-" * 42)
        for t in tables:
            try:
                cnt = (await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))).scalar()
                print(f"{t:<30} {cnt:>10,}")
            except Exception as e:
                print(f"{t:<30}   ERROR: {e}")

        # 4. Analysis cache breakdown
        print()
        r = await conn.execute(text("""
            SELECT agent_type, COUNT(*) as count,
                   MAX(generated_at) as latest
            FROM analysis_cache
            GROUP BY agent_type ORDER BY count DESC
        """))
        rows = r.all()
        if rows:
            print(f"{'Agent type':<25} {'Count':>8}  Latest")
            print("-" * 55)
            for row in rows:
                print(f"{row[0]:<25} {row[1]:>8}  {str(row[2])[:19]}")

    await engine.dispose()

asyncio.run(main())
