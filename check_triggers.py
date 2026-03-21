import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def check_triggers():
    db = get_db()
    
    print("Checking triggers on 'invoices':")
    try:
        # Use RPC if available or a raw query if we can
        # Supabase doesn't easily allow raw SQL via the client without RPC
        # But we can try to query information_schema if it's exposed
        res = db.table("invoices").select("*").limit(1).execute()
        print("Successfully queried 'invoices'")
        
        # Let's try to see if there's any trigger info we can get via RPC
        # Most Supabase instances have a way to run SQL but not through the standard client
        # I'll try to just catch the error more specifically
    except Exception as e:
        print(f"Error querying invoices: {e}")

    # Let's try to insert ONE simplified row to see where it breaks precisely
    try:
        print("\nAttempting minimal insert into 'invoices'...")
        # Get a real client_id first
        client = db.table("clients").select("id").limit(1).execute().data[0]
        cid = client["id"]
        
        test_inv = {
            "invoice_number": "TEST-123456",
            "client_id": cid,
            "amount": 100,
            "due_date": "2026-12-31",
            "sales_rep_name": "Test Rep"
        }
        db.table("invoices").insert(test_inv).execute()
        print(" ✅ Minimal insert SUCCESS")
    except Exception as e:
        print(f" ❌ Minimal insert FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(check_triggers())
