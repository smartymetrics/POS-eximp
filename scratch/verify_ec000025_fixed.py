import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db
import pdf_service

db = get_db()

print("=== VERIFYING FIX FOR INVOICE EC-000025 ===")

# 1. Fetch Invoice & Client
inv_res = db.table("invoices").select("*, clients(*)").eq("invoice_number", "EC-000025").execute()
invoice = inv_res.data[0]
client = invoice.get("clients") or {}

# 2. Fetch Session & Witnesses
sess_res = db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", invoice["id"]).order("created_at", desc=True).limit(1).execute()
witnesses = sess_res.data[0].get("witness_signatures", []) if sess_res.data else []

print("Invoice Number:", invoice["invoice_number"])
print("Client Name:", client.get("full_name"))
print("Client Signature URL:", invoice.get("contract_signature_url"))
print("Witness Name:", witnesses[0].get("full_name") if witnesses else None)
print("Witness Signature URL:", witnesses[0].get("signature_base64") if witnesses else None)

print("\n--- 1. Testing Draft Preview HTML ---")
html_draft = pdf_service.render_contract_html(
    invoice, client, witnesses=witnesses, is_draft=True, embed_images=False
)

has_client_sig_in_draft = invoice["contract_signature_url"] in html_draft
has_witness_sig_in_draft = witnesses[0]["signature_base64"] in html_draft

print("Client signature present in Live Draft HTML:", has_client_sig_in_draft)
print("Witness signature present in Live Draft HTML:", has_witness_sig_in_draft)

print("\n--- 2. Testing Contract PDF Generation ---")
pdf_bytes = pdf_service.generate_contract_pdf(
    invoice, client, witnesses=witnesses, is_draft=False
)

print("Contract PDF Generated Successfully!")
print("PDF Size:", len(pdf_bytes), "bytes")

if has_client_sig_in_draft and has_witness_sig_in_draft and len(pdf_bytes) > 50000:
    print("\n[SUCCESS] ALL VERIFICATIONS PASSED SUCCESSFULLY!")
else:
    print("\n[WARNING] Verification incomplete. Check outputs.")
