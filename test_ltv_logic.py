import asyncio
from database import get_db
from marketing_ltv_engine import refresh_marketing_ltv_stats

async def test_ltv():
    db = get_db()
    
    # 1. State before
    print("--- Before Sync ---")
    contacts = db.table("marketing_contacts").select("email, total_revenue_attributed, tags").limit(5).execute().data
    for c in contacts:
        print(f"Email: {c['email']}, LTV: {c.get('total_revenue_attributed')}, Tags: {c.get('tags')}")

    # 2. Run Engine
    print("\nRunning LTV Engine...")
    await refresh_marketing_ltv_stats()

    # 3. State after
    print("\n--- After Sync ---")
    contacts_after = db.table("marketing_contacts").select("email, total_revenue_attributed, tags").limit(5).execute().data
    for c in contacts_after:
        print(f"Email: {c['email']}, LTV: {c.get('total_revenue_attributed')}, Tags: {c.get('tags')}")

if __name__ == "__main__":
    asyncio.run(test_ltv())
