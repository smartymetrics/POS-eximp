import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db
import pdf_service

db = get_db()

# 1. Fetch invoice EC-000025
inv_res = db.table("invoices").select("*, clients(*)").eq("invoice_number", "EC-000025").execute()
invoice = inv_res.data[0]
client = invoice.get("clients") or {}

# 2. Fetch session and witnesses
session_res = db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", invoice["id"]).order("created_at", desc=True).limit(1).execute()
witnesses = session_res.data[0].get("witness_signatures", []) if session_res.data else []

print("Invoice ID:", invoice["id"])
print("Client:", client.get("full_name"))
print("contract_signature_url:", invoice.get("contract_signature_url"))
print("Witnesses count:", len(witnesses))
if witnesses:
    print("Witness 1 details:", witnesses[0])

print("\n--- TESTING HTML DRAFT (embed_images=False) ---")
html_draft = pdf_service.render_contract_html(
    invoice, client, witnesses=witnesses, is_draft=True, embed_images=False
)

# Search for purchaser & witness image tags or placeholders in html_draft
print("Searching HTML Draft for signature terms...")
for line in html_draft.splitlines():
    if any(k in line.lower() for k in ["purchaser", "witness", "sig-placeholder", "sig-purchaser-img", "signatures."]):
        print("  ", line.strip())

print("\n--- TESTING PDF HTML (embed_images=True) ---")
html_pdf = pdf_service.render_contract_html(
    invoice, client, witnesses=witnesses, is_draft=False, embed_images=True
)

print("Searching PDF HTML for signature terms...")
for line in html_pdf.splitlines():
    if any(k in line.lower() for k in ["purchaser", "witness", "sig-placeholder", "sig-purchaser-img", "data:image"]):
        # Print truncated line
        print("  ", line.strip()[:150])
