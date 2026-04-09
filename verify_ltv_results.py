import asyncio
from database import get_db

async def verify_results():
    db = get_db()
    print("--- LTV Sync Results (Top 10) ---")
    res = db.table("marketing_contacts")\
        .select("email, total_revenue_attributed, tags")\
        .gt("total_revenue_attributed", 0)\
        .order("total_revenue_attributed", desc=True)\
        .limit(10)\
        .execute()
    
    if not res.data:
        print("No contacts found with attributed revenue.")
        return

    for c in res.data:
        email = c.get("email")
        ltv = c.get("total_revenue_attributed")
        tags = c.get("tags") or []
        print(f"Email: {email:30} | LTV: ₦{ltv:,.2f} | Tags: {tags}")

if __name__ == "__main__":
    asyncio.run(verify_results())
