import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db

db = get_db()

print("=== SEARCHING SIGNED INVOICES FOR COMPARISON ===")
invs_res = db.table("invoices").select("*").not_.is_("contract_signature_url", "null").limit(10).execute()

print(f"Found {len(invs_res.data)} invoices with contract_signature_url:")
for inv in invs_res.data:
    inv_no = inv["invoice_number"]
    print(f"\n--- INVOICE {inv_no} ---")
    print("ID:", inv["id"])
    print("contract_signature_url:", inv.get("contract_signature_url"))
    print("contract_witness_signature_url:", inv.get("contract_witness_signature_url"))
    print("has custom_execution_html:", bool(inv.get("custom_execution_html")))
    
    if inv.get("custom_execution_html"):
        exec_html = inv["custom_execution_html"]
        print("custom_execution_html length:", len(exec_html))
        print("contains '&gt;':", "&gt;" in exec_html)
        print("contains 'witnesses|length':", "witnesses|length" in exec_html)
    
    # Check witness signatures for this invoice
    try:
        sess_res = db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", inv["id"]).execute()
        witnesses = []
        for s in sess_res.data:
            witnesses.extend(s.get("witness_signatures", []))
        print("witness_signatures count:", len(witnesses))
        for w in witnesses:
            print("  Witness:", w.get("full_name"), "| URL:", w.get("signature_base64"))
    except Exception as e:
        print("Error checking witnesses:", e)
