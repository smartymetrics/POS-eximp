import asyncio
import json
import sys
from typing import List, Dict

from database import get_db, db_execute


async def fetch_admin_by_name(name: str):
    db = get_db()
    res = await db_execute(lambda: db.table("admins").select("id, full_name").execute())
    admins = res.data or []
    matches = [a for a in admins if name.lower() in (a.get("full_name") or "").lower()]
    return matches


async def fetch_invoices_for_rep(admin_id: str, full_name: str) -> List[Dict]:
    db = get_db()
    invoices = []
    # By rep id
    try:
        r1 = await db_execute(lambda: db.table("invoices").select("id, client_id, amount, amount_paid, status").eq("sales_rep_id", admin_id).neq("status", "voided").execute())
        invoices.extend(r1.data or [])
    except Exception:
        pass
    # By rep name fallback
    try:
        r2 = await db_execute(lambda: db.table("invoices").select("id, client_id, amount, amount_paid, status").eq("sales_rep_name", full_name).neq("status", "voided").execute())
        invoices.extend(r2.data or [])
    except Exception:
        pass
    # Deduplicate by invoice id
    seen = set()
    unique = []
    for inv in invoices:
        if not inv or not inv.get("id"): continue
        if inv["id"] in seen: continue
        seen.add(inv["id"])
        unique.append(inv)
    return unique


async def fetch_commissions_for_rep(admin_id: str, full_name: str) -> List[Dict]:
    db = get_db()
    comms = []
    try:
        c1 = await db_execute(lambda: db.table("commission_earnings").select("commission_amount, is_voided").eq("sales_rep_id", admin_id).eq("is_voided", False).execute())
        comms.extend(c1.data or [])
    except Exception:
        pass
    try:
        c2 = await db_execute(lambda: db.table("commission_earnings").select("commission_amount, is_voided").eq("sales_rep_name", full_name).eq("is_voided", False).execute())
        comms.extend(c2.data or [])
    except Exception:
        pass
    # Deduplicate not strictly necessary; sum amounts
    return comms


async def count_assigned_leads(admin_id: str, full_name: str) -> int:
    db = get_db()
    # Prefer id-based count
    try:
        r = await db_execute(lambda: db.table("clients").select("id").eq("assigned_rep_id", admin_id).execute())
        return len(r.data or [])
    except Exception:
        # Fallback: count clients whose assigned_rep_id maps to this full_name
        try:
            all_clients = (await db_execute(lambda: db.table("clients").select("id, assigned_rep_id").execute())).data or []
            admins = (await db_execute(lambda: db.table("admins").select("id, full_name").execute())).data or []
            id_to_name = {a["id"]: a["full_name"] for a in admins}
            return sum(1 for c in all_clients if id_to_name.get(c.get("assigned_rep_id")) == full_name)
        except Exception:
            return 0


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_rep.py \"Full Name (or partial)\"")
        sys.exit(1)

    name = sys.argv[1]
    matches = await fetch_admin_by_name(name)
    if not matches:
        print(json.dumps({"error": "No admin found matching: %s" % name}))
        return

    admin = matches[0]
    admin_id = admin.get("id")
    full_name = admin.get("full_name")

    invoices = await fetch_invoices_for_rep(admin_id, full_name)
    commissions = await fetch_commissions_for_rep(admin_id, full_name)
    assigned = await count_assigned_leads(admin_id, full_name)

    total_deals = len(invoices)
    total_revenue = sum(float(i.get("amount") or 0) for i in invoices)
    total_collected = sum(float(i.get("amount_paid") or 0) for i in invoices)
    closed_clients = set(i.get("client_id") for i in invoices if i.get("status") == "paid" and i.get("client_id"))
    closed_deals = len(closed_clients)
    conversion_rate = round((closed_deals / assigned) * 100, 1) if assigned else 0.0

    total_commission = sum(float(c.get("commission_amount") or 0) for c in commissions)

    output = {
        "admin_id": admin_id,
        "full_name": full_name,
        "assigned_leads": assigned,
        "total_deals": total_deals,
        "closed_deals": closed_deals,
        "conversion_rate": conversion_rate,
        "total_revenue": total_revenue,
        "total_collected": total_collected,
        "total_commission": total_commission,
        "sample_invoices_count": min(10, total_deals)
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
