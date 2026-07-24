import os
import sys
import json
sys.path.append(os.getcwd())

from database import supabase

print("Querying invoice EC-000033 and its payments...")
try:
    # 1. Fetch invoice details
    inv_res = supabase.table("invoices").select("id, invoice_number, status, amount, amount_paid, balance_due, due_date, invoice_date, property_name, client_id").eq("invoice_number", "EC-000033").execute()
    
    if not inv_res.data:
        print("Invoice EC-000033 not found in database.")
        sys.exit(0)
        
    inv = inv_res.data[0]
    inv_id = inv["id"]
    print("\n--- INVOICE ---")
    for k, v in inv.items():
        print(f"  {k}: {v}")
        
    # 2. Fetch payments for this invoice
    pmt_res = supabase.table("payments").select("*").eq("invoice_id", inv_id).execute()
    print("\n--- PAYMENTS ---")
    if pmt_res.data:
        print(f"Found {len(pmt_res.data)} payment(s):")
        for i, pmt in enumerate(pmt_res.data, 1):
            print(f"\n  Payment #{i}:")
            for k, v in pmt.items():
                print(f"    {k}: {v}")
    else:
        print("No payments found for this invoice.")
        
except Exception as e:
    print(f"Error: {e}")
