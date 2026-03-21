import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def final_count():
    db = get_db()
    tables = ["clients", "invoices", "payments", "pending_verifications", "sales_reps", "unmatched_reps"]
    
    print("FINAL DATABASE COUNTS:")
    for table in tables:
        try:
            res = db.table(table).select("*", count="exact").execute()
            print(f" - {table}: {res.count}")
            # Also print the last 2 names for verification
            if table == "clients":
                names = [r["full_name"] for r in res.data[-2:]]
                print(f"   Last 2: {names}")
            if table == "invoices":
                nums = [r["invoice_number"] for r in res.data[-2:]]
                print(f"   Last 2: {nums}")
        except Exception as e:
            print(f" - {table}: Error ({e})")

if __name__ == "__main__":
    asyncio.run(final_count())
