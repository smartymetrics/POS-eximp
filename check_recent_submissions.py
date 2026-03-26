import asyncio
import os
from dotenv import load_dotenv
from database import get_db

load_dotenv()

async def check_recent_submissions():
    print("--- Checking Recent Submissions ---")
    db = get_db()
    
    # Check recent clients
    try:
        res = db.table("clients").select("id, full_name, email, created_at").order("created_at", desc=True).limit(3).execute()
        print("\nRecent Clients:")
        for client in res.data:
            print(f"- {client['full_name']} ({client['email']}) created at {client['created_at']}")
    except Exception as e:
        print(f"Error checking clients: {e}")

    # Check recent invoices
    try:
        res = db.table("invoices").select("id, invoice_number, amount, created_at, source").order("created_at", desc=True).limit(3).execute()
        print("\nRecent Invoices:")
        for inv in res.data:
            print(f"- Inv #{inv['invoice_number']} ({inv['amount']}) from {inv['source']} at {inv['created_at']}")
    except Exception as e:
        print(f"Error checking invoices: {e}")

if __name__ == "__main__":
    asyncio.run(check_recent_submissions())
