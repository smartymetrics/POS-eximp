import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db

db = get_db()

print("=== FIXING EC-000025 INVOICE RECORD IN DB ===")
inv_res = db.table("invoices").select("id, invoice_number, custom_execution_html").eq("invoice_number", "EC-000025").execute()

if not inv_res.data:
    print("Invoice EC-000025 not found!")
    sys.exit(1)

inv = inv_res.data[0]
print("Invoice ID:", inv["id"])

old_html = inv.get("custom_execution_html", "")
if not old_html:
    print("custom_execution_html is empty!")
else:
    new_html = old_html.replace("&gt;", ">").replace("&lt;", "<")
    if old_html == new_html:
        print("No changes needed. custom_execution_html already clean.")
    else:
        print(f"Replacing HTML entities in custom_execution_html (length {len(old_html)} -> {len(new_html)})...")
        update_res = db.table("invoices").update({"custom_execution_html": new_html}).eq("id", inv["id"]).execute()
        print("Database update successful! Updated rows:", len(update_res.data))
