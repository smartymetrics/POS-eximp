import asyncio
from database import get_db, db_execute

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table('legal_matters').select('id, title, status, content_html').order('created_at', desc=True).limit(5).execute())
    for row in res.data:
        content = row.get('content_html')
        has_content = bool(content and content.strip())
        print(f"ID: {row['id']} | Title: {row['title']} | Status: {row['status']} | Has Content: {has_content}")
        if has_content:
            print(f"Content Start: {content[:100]}")
        print("-" * 40)

asyncio.run(check())
