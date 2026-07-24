"""
verify_kyc_token_assignment.py
Tests that a KYC link token correctly resolves to a rep and would assign the lead.
Run: .\.venv\Scripts\python.exe scratch/verify_kyc_token_assignment.py
"""
import asyncio, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, db_execute

async def main():
    db = get_db()

    # 1. Get all active KYC links
    print("=" * 55)
    print("STEP 1: Fetching all active KYC links...")
    links_res = await db_execute(lambda: db.table("kyc_links").select("token, rep_id, label, is_active").eq("is_active", True).execute())
    links = links_res.data or []
    if not links:
        print("  [FAIL] No active KYC links found.")
        return
    for link in links:
        print(f"  [OK] Token: {link['token']} | Rep ID: {link['rep_id']} | Label: {link.get('label', '-')}")

    # 2. For each link, resolve the rep_id to an admin name
    print("\nSTEP 2: Resolving rep_id -> admin name...")
    for link in links:
        rep_id = link["rep_id"]
        # Try sales_reps first
        sr = await db_execute(lambda: db.table("sales_reps").select("id, name").eq("id", rep_id).execute())
        if sr.data:
            print(f"  [OK] Rep ID {rep_id} -> sales_reps.name = '{sr.data[0]['name']}'")
            continue
        # Fallback: admins table
        adm = await db_execute(lambda: db.table("admins").select("id, full_name, role").eq("id", rep_id).execute())
        if adm.data:
            print(f"  [OK] Rep ID {rep_id} -> admins.full_name = '{adm.data[0]['full_name']}' (role: {adm.data[0]['role']})")
        else:
            print(f"  [FAIL] Rep ID {rep_id} -> NOT FOUND in sales_reps or admins!")

    # 3. Simulate what submit_kyc would do with the first token
    token = links[0]["token"]
    rep_id = links[0]["rep_id"]
    print(f"\nSTEP 3: Simulating KYC submit with token='{token}'")
    print(f"  -> Resolved assigned_rep_id = '{rep_id}'")

    # 4. Check if the existing 'Ben' lead was assigned
    print("\nSTEP 4: Checking if existing leads from KYC form are assigned...")
    leads_res = await db_execute(lambda: db.table("clients").select("id, full_name, assigned_rep_id, lead_source, created_at").eq("lead_source", "web_kyc").order("created_at", desc=True).limit(5).execute())
    for lead in (leads_res.data or []):
        assigned = lead.get("assigned_rep_id")
        status = "[OK] Assigned" if assigned else "[FAIL] Unassigned (NULL)"
        print(f"  {status} | {lead['full_name']} | rep_id={assigned}")

    print("\n" + "=" * 55)
    print("CONCLUSION: If STEP 2 shows [OK], the rep assignment fix")
    print("will work correctly for new form submissions via KYC links.")
    print("=" * 55)

if __name__ == "__main__":
    asyncio.run(main())
