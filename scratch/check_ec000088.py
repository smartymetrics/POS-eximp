import os, sys, json

# Read-only check for invoice EC-000088
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')

if not url or not key:
    print('ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY')
    sys.exit(1)

sb = create_client(url, key)

print("\n=== INVOICE EC-000088 ===")
inv = sb.table('invoices').select('*, clients(*), payments(*)').eq('invoice_number', 'EC-000088').execute()

if not inv.data:
    print("NOT FOUND. Searching for invoices containing '88'...")
    inv_like = sb.table('invoices').select('id, invoice_number, amount, amount_paid, balance_due, status, source, created_at').ilike('invoice_number', '%88%').order('created_at', desc=True).execute()
    print(json.dumps(inv_like.data, indent=2, default=str))
    sys.exit(0)

invoice = inv.data[0]
print(f"Invoice Number : {invoice.get('invoice_number')}")
print(f"Status         : {invoice.get('status')}")
print(f"Source         : {invoice.get('source')}")
print(f"Property       : {invoice.get('property_name')}")
print(f"Payment Terms  : {invoice.get('payment_terms')}")
print(f"Total Amount   : {invoice.get('amount')}")
print(f"Amount Paid    : {invoice.get('amount_paid')}")
print(f"Balance Due    : {invoice.get('balance_due')}")
print(f"Invoice Date   : {invoice.get('invoice_date')}")
print(f"Sales Rep Name : {invoice.get('sales_rep_name')}")
print(f"Created At     : {invoice.get('created_at')}")
print(f"Payment Proof  : {invoice.get('payment_proof_url')}")
print(f"Signature URL  : {invoice.get('signature_url')}")

client = invoice.get('clients') or {}
print(f"\n--- CLIENT ---")
print(f"  Name  : {client.get('full_name')}")
print(f"  Email : {client.get('email')}")
print(f"  Phone : {client.get('phone')}")

payments = invoice.get('payments') or []
print(f"\n--- PAYMENTS ({len(payments)} record(s)) ---")
for p in payments:
    print(f"  ID         : {p.get('id')}")
    print(f"  Amount     : {p.get('amount')}")
    print(f"  Date       : {p.get('payment_date')}")
    print(f"  Reference  : {p.get('reference')}")
    print(f"  Method     : {p.get('payment_method')}")
    print(f"  Type       : {p.get('payment_type')}")
    print(f"  Voided     : {p.get('is_voided')}")
    print(f"  Notes      : {p.get('notes')}")
    print()

print(f"\n--- PENDING VERIFICATION ---")
inv_id = invoice['id']
pv = sb.table('pending_verifications').select('*').eq('invoice_id', inv_id).execute()
if pv.data:
    for v in pv.data:
        print(f"  Verification ID   : {v.get('id')}")
        print(f"  Status            : {v.get('status')}")
        print(f"  Deposit Amount    : {v.get('deposit_amount')}")
        print(f"  Payment Date      : {v.get('payment_date')}")
        print(f"  Sales Rep Name    : {v.get('sales_rep_name')}")
        print(f"  Payment Proof URL : {v.get('payment_proof_url')}")
        print(f"  Reviewed By       : {v.get('reviewed_by')}")
        print(f"  Reviewed At       : {v.get('reviewed_at')}")
        print(f"  Created At        : {v.get('created_at')}")
        print()
else:
    print("  No verification record found for this invoice.")
