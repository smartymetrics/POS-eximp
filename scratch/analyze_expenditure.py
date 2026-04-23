import asyncio
import os
from database import get_db

async def analyze():
    db = get_db()
    res = await db.table("expenditure_requests").select("payment_type, status, payout_method, vendors(type, name)").execute()
    data = res.data
    
    analysis = {}
    for r in data:
        p_type = r.get('payment_type')
        p_method = r.get('payout_method')
        v_type = (r.get('vendors') or {}).get('type')
        status = r.get('status')
        
        key = f"PType:{p_type} | PMeth:{p_method} | VType:{v_type} | Status:{status}"
        analysis[key] = analysis.get(key, 0) + 1
        
    for k, v in sorted(analysis.items()):
        print(f"{v}x | {k}")

if __name__ == "__main__":
    asyncio.run(analyze())
