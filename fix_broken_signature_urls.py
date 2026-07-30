"""
Repairs invoices/witness rows whose signature URL was saved as a hardcoded
Supabase public-storage URL (the pre-Cloudinary-migration format) even
though the actual file was uploaded to Cloudinary.

This does NOT re-upload anything — the files already exist wherever
db.storage.from_("signatures").upload(...) actually put them. It just
re-resolves the same file_path through the (Cloudinary-aware) storage
client and rewrites the DB column to the correct, resolvable URL.

Usage:
    python scratch/fix_broken_signature_urls.py EC-000043 EC-000061
    python scratch/fix_broken_signature_urls.py --all     # scan every invoice
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_db, SUPABASE_URL

OLD_PREFIX = f"{SUPABASE_URL}/storage/v1/object/public/signatures/"


def fix_invoice(db, invoice):
    changed = False
    invoice_id = invoice["id"]
    inv_num = invoice.get("invoice_number", invoice_id)

    # --- Client / purchaser signature on the invoice row ---
    client_url = invoice.get("contract_signature_url")
    if client_url and client_url.startswith(OLD_PREFIX):
        file_path = client_url[len(OLD_PREFIX):]
        new_url = db.storage.from_("signatures").get_public_url(file_path)
        if new_url and new_url != client_url:
            db.table("invoices").update(
                {"contract_signature_url": new_url}
            ).eq("id", invoice_id).execute()
            print(f"[{inv_num}] client signature: {client_url} -> {new_url}")
            changed = True
        else:
            print(f"[{inv_num}] client signature still unresolved for {file_path} (check Cloudinary asset exists)")

    # --- Witness signatures, via the signing session(s) for this invoice ---
    sess_res = db.table("contract_signing_sessions").select("id").eq("invoice_id", invoice_id).execute()
    for sess in sess_res.data or []:
        wit_res = db.table("witness_signatures").select("*").eq("session_id", sess["id"]).execute()
        for w in wit_res.data or []:
            wurl = w.get("signature_base64")
            if wurl and wurl.startswith(OLD_PREFIX):
                file_path = wurl[len(OLD_PREFIX):]
                new_url = db.storage.from_("signatures").get_public_url(file_path)
                if new_url and new_url != wurl:
                    db.table("witness_signatures").update(
                        {"signature_base64": new_url}
                    ).eq("id", w["id"]).execute()
                    print(f"[{inv_num}] witness {w.get('witness_number')}: {wurl} -> {new_url}")
                    changed = True
                else:
                    print(f"[{inv_num}] witness {w.get('witness_number')} still unresolved for {file_path}")

    if not changed:
        print(f"[{inv_num}] nothing to fix")


def main():
    db = get_db()
    args = sys.argv[1:]

    if not args or args == ["--all"]:
        res = db.table("invoices").select("*").execute()
        invoices = res.data or []
    else:
        invoices = []
        for inv_num in args:
            res = db.table("invoices").select("*").eq("invoice_number", inv_num).execute()
            if res.data:
                invoices.append(res.data[0])
            else:
                print(f"Invoice {inv_num} not found")

    for inv in invoices:
        fix_invoice(db, inv)


if __name__ == "__main__":
    main()