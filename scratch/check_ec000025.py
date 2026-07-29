import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

from database import get_db

db = get_db()

print("=== INVOICE SEARCH EC-000025 ===")
inv_res = db.table("invoices").select("*").eq("invoice_number", "EC-000025").execute()

if inv_res.data:
    inv = inv_res.data[0]
    print("--- INVOICE DUMP ---")
    for k, v in sorted(inv.items()):
        print(f"{k}: {repr(v)}")

    invoice_id = inv["id"]

    print("\n=== WITNESS SIGNATURES TABLE ===")
    try:
        wit_res = db.table("witness_signatures").select("*").eq("invoice_id", invoice_id).execute()
        print("Witness signatures count (by invoice_id):", len(wit_res.data))
        for w in wit_res.data:
            print(json.dumps(w, indent=2, default=str))
    except Exception as e:
        print("Witness signatures query err:", e)

    print("\n=== SIGNING SESSIONS ===")
    try:
        sessions_res = db.table("signing_sessions").select("*").eq("invoice_id", invoice_id).execute()
        print("Signing sessions count:", len(sessions_res.data))
        for s in sessions_res.data:
            print(json.dumps(s, indent=2, default=str))
            wit_sess = db.table("witness_signatures").select("*").eq("session_id", s["id"]).execute()
            print("  Witness count for session:", len(wit_sess.data))
            for ws in wit_sess.data:
                print("  ", json.dumps(ws, indent=2, default=str))
    except Exception as e:
        print("Signing sessions query err:", e)

    print("\n=== LEGAL MATTERS ===")
    try:
        matters_res = db.table("legal_matters").select("*").eq("invoice_id", invoice_id).execute()
        print("Legal matters count:", len(matters_res.data))
        for m in matters_res.data:
            print(json.dumps(m, indent=2, default=str))
    except Exception as e:
        print("Legal matters query err:", e)
