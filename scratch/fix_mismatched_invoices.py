import os
import sys
sys.path.append(os.getcwd())

from database import supabase

print("Starting Supabase invoice status alignment script (ASCII mode)...")

try:
    res = supabase.table("invoices").select("id, invoice_number, status, amount, amount_paid").execute()
    if not res.data:
        print("No invoices found.")
        sys.exit(0)

    updated_count = 0
    for inv in res.data:
        inv_id = inv["id"]
        inv_num = inv["invoice_number"]
        current_status = inv["status"]
        amount = float(inv["amount"] or 0)
        amount_paid = float(inv["amount_paid"] or 0)

        # Skip voided invoices as they are explicitly voided by admins
        if current_status == "voided":
            continue

        # Determine correct payment-based status
        if amount_paid >= amount and amount > 0:
            expected_status = "paid"
        elif amount_paid > 0:
            expected_status = "partial"
        else:
            expected_status = "unpaid"

        if current_status != expected_status:
            print(f"\nMismatch found for Invoice {inv_num}:")
            print(f"  Amount: {amount}")
            print(f"  Amount Paid: {amount_paid}")
            print(f"  Current DB Status: '{current_status}'")
            print(f"  Expected Status: '{expected_status}'")
            
            # Perform update
            update_res = supabase.table("invoices").update({"status": expected_status}).eq("id", inv_id).execute()
            if update_res.data:
                print(f"  [OK] Successfully updated status of {inv_num} to '{expected_status}'")
                updated_count += 1
            else:
                print(f"  [ERROR] Failed to update status of {inv_num}")

    print(f"\nAlignment complete. Corrected {updated_count} invoice(s).")

except Exception as e:
    print(f"Error during status alignment: {e}")
