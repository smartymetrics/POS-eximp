import sys
import os
import json
import urllib.request
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db

db = get_db()

print("=== INVOICE FULL DETAILS ===")
inv_res = db.table("invoices").select("*").eq("invoice_number", "EC-000025").execute()
inv = inv_res.data[0]
invoice_id = inv["id"]

print("Invoice Keys & Values:")
for k in sorted(inv.keys()):
    v = inv[k]
    print(f"  {k}: {repr(v)}")

print("\n=== CONTRACT SIGNING SESSIONS ===")
try:
    sess_res = db.table("contract_signing_sessions").select("*").eq("invoice_id", invoice_id).execute()
    print("Sessions count:", len(sess_res.data))
    for s in sess_res.data:
        print(json.dumps(s, indent=2, default=str))
        # Check witness signatures for this session
        try:
            wit_sess = db.table("witness_signatures").select("*").eq("session_id", s["id"]).execute()
            print(" Witness count for session:", len(wit_sess.data))
            for ws in wit_sess.data:
                print("  Witness:", json.dumps(ws, indent=2, default=str))
        except Exception as e:
            print(" Error querying witness_signatures by session_id:", e)
except Exception as e:
    print("Error querying contract_signing_sessions:", e)

print("\n=== WITNESS SIGNATURES (ALL RECORDS) ===")
try:
    wit_all = db.table("witness_signatures").select("*").limit(10).execute()
    if wit_all.data:
        print("Sample witness_signatures row columns:", list(wit_all.data[0].keys()))
        for w in wit_all.data:
            print("  ", w)
    else:
        print("No witness_signatures rows found.")
except Exception as e:
    print("Error querying witness_signatures:", e)

print("\n=== URL ACCESSIBILITY CHECK ===")
urls_to_test = {
    "signature_url": inv.get("signature_url"),
    "contract_signature_url": inv.get("contract_signature_url"),
    "contract_witness_signature_url": inv.get("contract_witness_signature_url"),
}

for label, url in urls_to_test.items():
    if not url:
        print(f"{label}: NONE")
        continue
    print(f"{label}: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"  HTTP Status: {resp.status}, Content-Type: {resp.headers.get('Content-Type')}, Length: {len(resp.read())}")
    except Exception as e:
        print(f"  FETCH ERROR: {e}")
