"""
Diagnoses a "broken image" signature URL by hitting it directly and
reporting the real HTTP response — distinguishes:
  - 404 (object genuinely missing from storage)
  - 400/403 (bucket not public / RLS blocking anonymous read)
  - 200 with a non-image content-type (misconfigured upload)
  - 200 with a tiny/zero-byte body (empty or corrupted file)

Usage:
    python scratch/diagnose_signature_url.py EC-000061
"""
import sys
import os
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_db


def check_url(label, url):
    if not url:
        print(f"  {label}: (empty/null in DB)")
        return
    print(f"  {label}: {url}")
    try:
        res = requests.get(url, timeout=15)
        print(f"    -> status={res.status_code}  content-type={res.headers.get('Content-Type')}  bytes={len(res.content)}")
        if res.status_code != 200:
            print(f"    -> body snippet: {res.text[:300]}")
    except Exception as e:
        print(f"    -> request failed: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_signature_url.py <invoice_number>")
        return

    inv_num = sys.argv[1]
    db = get_db()

    inv_res = db.table("invoices").select("*").eq("invoice_number", inv_num).execute()
    if not inv_res.data:
        print(f"Invoice {inv_num} not found")
        return
    invoice = inv_res.data[0]

    print(f"=== {inv_num} ===")
    check_url("client signature (contract_signature_url)", invoice.get("contract_signature_url"))

    sess_res = db.table("contract_signing_sessions").select("id").eq("invoice_id", invoice["id"]).execute()
    for sess in sess_res.data or []:
        wit_res = db.table("witness_signatures").select("*").eq("session_id", sess["id"]).order("witness_number").execute()
        for w in wit_res.data or []:
            check_url(f"witness {w.get('witness_number')} ({w.get('full_name')})", w.get("signature_base64"))


if __name__ == "__main__":
    main()