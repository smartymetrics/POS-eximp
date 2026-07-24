import asyncio
from database import get_db, db_execute

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table('campaign_recipients').select('*').order('created_at', desc=True).limit(5).execute())
    if res.data:
        for r in res.data:
            print(f"Status: {r['status']}, SentAt: {r['sent_at']}, CreatedAt: {r['created_at']}")
    else:
        print("No recent recipients")

asyncio.run(check())
