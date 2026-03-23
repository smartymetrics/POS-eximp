from database import supabase
import json

def debug_payments(inv_no):
    print(f"\n--- Debugging Payments for {inv_no} ---")
    res_inv = supabase.table('invoices').select('id, amount, amount_paid').eq('invoice_number', inv_no).execute()
    if not res_inv.data:
        print("Invoice not found")
        return
    
    inv = res_inv.data[0]
    print(f"Invoice Info: Total={inv['amount']}, Paid={inv['amount_paid']}")
    
    res_pay = supabase.table('payments').select('*').eq('invoice_id', inv['id']).execute()
    for p in res_pay.data:
        print(f"Payment: ID={p['id']}, Amt={p['amount']}, Type={p['payment_type']}, Ref={p['reference']}, Method={p['payment_method']}")

debug_payments('EC-000016')
