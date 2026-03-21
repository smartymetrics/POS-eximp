import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def verify_schema():
    db = get_db()
    tables = [
        "admins", "clients", "properties", "invoices", "payments", 
        "activity_log", "sales_reps", "unmatched_reps", 
        "pending_verifications", "void_log", "report_schedules"
    ]
    
    print("Schema Verification:")
    for table in tables:
        try:
            db.table(table).select("count", count="exact").limit(1).execute()
            print(f" ✅ {table}: Found")
        except Exception as e:
            print(f" ❌ {table}: NOT FOUND ({e})")

if __name__ == "__main__":
    asyncio.run(verify_schema())
