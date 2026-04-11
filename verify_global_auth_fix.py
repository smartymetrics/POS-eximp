import asyncio
from database import get_db, db_execute

async def verify_fixes():
    db = get_db()
    
    # 1. Check marketing_events
    try:
        res = await db_execute(lambda: db.table("marketing_events").select("*").limit(1).execute())
        print("✅ marketing_events table exists.")
    except Exception as e:
        print(f"❌ marketing_events check failed: {e}")

    # 2. Check other tables existence
    tables = ["properties", "documents", "campaigns"]
    for t in tables:
        try:
            await db_execute(lambda: db.table(t).select("*").limit(1).execute())
            print(f"✅ {t} table exists.")
        except Exception as e:
            print(f"❌ {t} check failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_fixes())
