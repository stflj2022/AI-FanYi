import asyncio, sys
sys.path.insert(0, "/home/wu/桌面/AI-FanYi/src")
async def main():
    from sqlalchemy import text
    from filmdub.orchestrator.database import engine
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id, name, status FROM projects"))
        rows = r.fetchall()
        print("projects 行数:", len(rows))
        for row in rows:
            print(" ", row)
        r2 = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tabs = [x[0] for x in r2.fetchall()]
        print("表:", tabs)
    await engine.dispose()
asyncio.run(main())
