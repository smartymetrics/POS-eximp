import os
import sys
sys.path.append(os.getcwd())

from database import supabase

print("Scanning for mismatched invoices in Supabase (status = 'paid' but amount_paid < amount)...")
try:
    res = supabase.table("invoices").select("id, invoice_number, status, amount, amount_paid, balance_due, due_date, property_name, client_id, clients(full_name)").execute()
    if res.data:
        mismatched = []
        for inv in res.data:
            amt = float(inv.get("amount") or 0)
            paid = float(inv.get("amount_paid") or 0)
            status = inv.get("status")
            
            # Mismatch: Stored status is 'paid', but actually paid amount is less than total amount
            if status == "paid" and paid < amt:
                mismatched.append(inv)
                
        print(f"\nScan completed. Found {len(mismatched)} mismatched invoice(s):")
        for i, inv in enumerate(mismatched, 1):
            client_name = inv.get("clients", {}).get("full_name", "Unknown Client") if inv.get("clients") else "Unknown Client"
            print(f"\n  Mismatched Invoice #{i}:")
            print(f"    ID: {inv['id']}")
            print(f"    Invoice Number: {inv['invoice_number']}")
            print(f"    Client: {client_name}")
            print(f"    Property: {inv.get('property_name')}")
            print(f"    Amount: ₦{inv.get('amount'):,.2f}")
            print(f"    Amount Paid: ₦{inv.get('amount_paid'):,.2f}")
            print(f"    Balance Due: ₦{float(inv.get('balance_due') or 0):,.2f}")
            print(f"    Stored Status: {inv.get('status')}")
    else:
        print("No invoices found in database.")
except Exception as e:
    print(f"Error: {e}")
