from database import get_db
import asyncio

async def check_schema():
    db = get_db()
    res = db.table("legal_matters").select("*").limit(1).execute()
    print("Columns in legal_matters:")
    for key in res.data[0].keys():
        print(f"- {key}")

if __name__ == "__main__":
    asyncio.run(check_schema())
