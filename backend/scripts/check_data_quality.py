import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB = "postgresql+asyncpg://isa_user:xospnQScUtWUlg3w56GntDiiYiXZqkEH@dpg-d9oulmks728c73fuvv9g-a.oregon-postgres.render.com/isa_db_xp27"

async def main():
    engine = create_async_engine(DB)
    async with engine.connect() as conn:
        q = """
            SELECT cnt, COUNT(*) as companies
            FROM (
                SELECT company_id, COUNT(*) as cnt
                FROM income_statements
                WHERE period_type = 'annual'
                GROUP BY company_id
            ) t
            GROUP BY cnt
            ORDER BY cnt
        """
        r = await conn.execute(text(q))
        print("Years of P&L | Companies")
        print("-" * 28)
        total = 0
        ge10 = 0
        for row in r.all():
            print(f"  {row[0]:>3} years  |  {row[1]}")
            total += row[1]
            if row[0] >= 10:
                ge10 += row[1]
        print("-" * 28)
        print(f"  Total      |  {total}")
        print(f"  10+ years  |  {ge10}")
        print(f"  < 10 years |  {total - ge10}")
    await engine.dispose()

asyncio.run(main())
