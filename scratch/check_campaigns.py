import asyncio
from database import get_db, db_execute

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table('email_campaigns').select('name, status, total_sent').order('created_at', desc=True).limit(5).execute())
    if res.data:
        for r in res.data:
            print(f"{r['name']}: {r['status']}, total_sent: {r['total_sent']}")

asyncio.run(check())
