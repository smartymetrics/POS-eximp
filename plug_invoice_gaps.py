import os
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

MISSING_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 30]

def plug_gaps():
    print("Fetching a valid client ID...")
    res = supabase.table("clients").select("id").limit(1).execute()
    if not res.data:
        print("Error: No clients found in the database. Cannot create dummy invoices.")
        return
    client_id = res.data[0]["id"]
    
    print("Fetching a valid admin ID...")
    res = supabase.table("admins").select("id").limit(1).execute()
    admin_id = res.data[0]["id"] if res.data else None

    print(f"Plugging gaps for missing numbers: {MISSING_NUMBERS}")
    
    for num in MISSING_NUMBERS:
        invoice_number = f"EC-{str(num).zfill(6)}"
        
        # Check if it already exists
        check = supabase.table("invoices").select("id").eq("invoice_number", invoice_number).execute()
        if check.data:
            print(f"{invoice_number} already exists, skipping.")
            continue
            
        print(f"Creating dummy voided record for {invoice_number}...")
        dummy_data = {
            "invoice_number": invoice_number,
            "client_id": client_id,
            "amount": 0,
            "unit_price": 0,
            "quantity": 1,
            "amount_paid": 0,
            "status": "voided",
            "notes": "Test record deleted during system cleanup. Gap plugged manually for audit trail.",
            "invoice_date": datetime.date.today().isoformat(),
            "due_date": datetime.date.today().isoformat(),
            "created_by": admin_id
        }
        
        try:
            supabase.table("invoices").insert(dummy_data).execute()
            print(f"Successfully inserted {invoice_number}")
        except Exception as e:
            print(f"Failed to insert {invoice_number}: {e}")

if __name__ == "__main__":
    plug_gaps()
    print("Done.")
