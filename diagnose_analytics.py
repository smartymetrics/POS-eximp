import os
import asyncio
from datetime import date
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def diagnose_analytics_data():
    db = get_db()
    
    tables = ["admins", "clients", "properties", "invoices", "payments", "sales_reps"]
    print("Row counts for all tables:")
    for table in tables:
        try:
            count = db.table(table).select("id", count="exact").execute().count
            print(f" - {table}: {count}")
        except Exception as e:
            print(f" - {table}: ERROR ({e})")
    
    # Check invoices specifically
    try:
        sample = db.table("invoices").select("*").limit(5).execute().data
        print(f"\nSample invoices: {sample}")
    except Exception as e:
        print(f"Error fetching sample invoices: {e}")

    # Check date range for invoices
    start = "2026-02-19"
    end = "2026-03-21"
    try:
        inv_range = db.table("invoices").select("*").filter("invoice_date", "gte", start).filter("invoice_date", "lte", end).execute().data
        print(f"\nInvoices in range {start} to {end}: {len(inv_range)}")
    except Exception as e:
        print(f"Error filtering invoices: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_analytics_data())
