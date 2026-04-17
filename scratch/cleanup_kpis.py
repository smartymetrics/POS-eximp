import asyncio
from database import get_db, db_execute

async def cleanup():
    db = get_db()
    print("SEARCHING: Fetching all KPI templates...")
    res = await db_execute(lambda: db.table("kpi_templates").select("id, name, department, created_at").execute())
    templates = res.data
    
    seen = {} # (name, department) -> id
    to_delete = []
    
    for t in templates:
        key = (t["name"], t["department"])
        if key in seen:
            print(f"DUPLICATE FOUND: {t['name']} ({t['department']}) [ID: {t['id']}]")
            to_delete.append(t["id"])
        else:
            seen[key] = t["id"]
            
    if not to_delete:
        print("CLEAN: No duplicates found.")
        return
        
    print(f"CLEANING: Deleting {len(to_delete)} duplicate(s)...")
    for tid in to_delete:
        await db_execute(lambda: db.table("kpi_templates").delete().eq("id", tid).execute())
        
    print("DONE: Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
