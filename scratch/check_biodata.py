
from database import get_db, db_execute
import asyncio

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table("biodata_submissions").select("id, status, email").execute())
    print(f"Total Submissions: {len(res.data)}")
    approved = [r for r in res.data if r["status"] == "approved"]
    pending = [r for r in res.data if r["status"] == "pending"]
    print(f"Approved: {len(approved)}")
    print(f"Pending: {len(pending)}")
    if approved:
        print("Sample approved emails:", [r["email"] for r in approved[:5]])

if __name__ == "__main__":
    asyncio.run(check())
