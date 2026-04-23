import asyncio
import os
from database import get_db

async def cleanup():
    db = get_db()
    
    # 1. Fetch untagged records
    res = await db.table("expenditure_requests").select("id, payment_type, vendors(type, name)").is_("payment_type", "null").execute()
    untagged = res.data
    print(f"Found {len(untagged)} untagged records.")
    
    for r in untagged:
        rid = r['id']
        v_type = (r.get('vendors') or {}).get('type')
        v_name = (r.get('vendors') or {}).get('name', '')
        
        new_tag = "office" if v_type == "company" else "reimbursement"
        
        print(f"Tagging {v_name} ({v_type}) as {new_tag}...")
        await db.table("expenditure_requests").update({"payment_type": new_tag}).eq("id", rid).execute()

    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
