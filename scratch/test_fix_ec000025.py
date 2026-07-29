import sys
import os
import html
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db
import pdf_service

db = get_db()

# Fetch EC-000025
inv_res = db.table("invoices").select("*, clients(*)").eq("invoice_number", "EC-000025").execute()
invoice = inv_res.data[0]
client = invoice.get("clients") or {}

sess_res = db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", invoice["id"]).order("created_at", desc=True).limit(1).execute()
witnesses = sess_res.data[0].get("witness_signatures", []) if sess_res.data else []

# Fix custom_execution_html by replacing &gt; with > and &lt; with < inside Jinja tags
exec_html = invoice.get("custom_execution_html", "")
fixed_exec_html = exec_html.replace("&gt;", ">").replace("&lt;", "<")

# Update invoice dict in memory
invoice_copy = invoice.copy()
invoice_copy["custom_execution_html"] = fixed_exec_html

print("--- TESTING DRAFT PREVIEW WITH FIXED HTML ---")
html_draft = pdf_service.render_contract_html(
    invoice_copy, client, witnesses=witnesses, is_draft=True, embed_images=False
)

has_purchaser_url = invoice["contract_signature_url"] in html_draft
has_witness_url = witnesses[0]["signature_base64"] in html_draft

print("Purchaser signature URL found in rendered draft HTML:", has_purchaser_url)
print("Witness signature URL found in rendered draft HTML:", has_witness_url)

print("\n--- TESTING PDF GENERATION WITH FIXED HTML ---")
try:
    pdf_bytes = pdf_service.generate_contract_pdf(
        invoice_copy, client, witnesses=witnesses, is_draft=False
    )
    print("PDF generated successfully! Size:", len(pdf_bytes), "bytes")
except Exception as e:
    print("PDF generation error:", e)
