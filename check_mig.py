from database import supabase
res = supabase.table('invoices').select('invoice_number, signature_url').order('created_at', desc=True).limit(5).execute()
print('--- Migration Results ---')
for r in res.data:
    print(f"INV {r['invoice_number']}: {r['signature_url'][:100]}...")
