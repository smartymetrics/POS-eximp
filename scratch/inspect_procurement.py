import asyncio
from database import get_db
import json

async def main():
    db = get_db()
    try:
        res = db.table('procurement_expenses').select('*').limit(1).execute()
        print(json.dumps(res.data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
