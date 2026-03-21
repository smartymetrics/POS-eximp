import os
import asyncio
from datetime import date
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def diagnose_analytics_data():
    db = get_db()
    start = "2026-02-19"
    end = "2026-03-21"
    
    print(f"Checking data between {start} and {end}...")
    
    # 1. Total Invoices
    inv_count = db.table("invoices").select("id", count="exact").execute().count
    print(f"Total invoices in DB: {inv_count}")
    
    # 2. Invoices in range
    inv_range = db.table("invoices").select("*").filter("invoice_date", "gte", start).filter("invoice_date", "lte", end).execute().data
    print(f"Invoices in range: {len(inv_range)}")
    if inv_range:
        print(f"Sample invoice date: {inv_range[0]['invoice_date']}")
    
    # 3. Payments in range
    pay_range = db.table("payments").select("*").filter("payment_date", "gte", start).filter("payment_date", "lte", end).execute().data
    print(f"Payments in range: {len(pay_range)}")
    
    # 4. Check a few invoices without filter
    recent = db.table("invoices").select("invoice_date").limit(5).order("created_at", desc=True).execute().data
    print(f"Recent invoice dates: {[i['invoice_date'] for i in recent]}")

if __name__ == "__main__":
    asyncio.run(diagnose_analytics_data())
