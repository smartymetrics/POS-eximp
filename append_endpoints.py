
import os

content_to_append = """

# --- ESTATE DRAFTS & PIPELINE ---
from models import EstateDraftCreate

@router.post("/estates")
async def create_estate_draft(data: EstateDraftCreate, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    payload = data.dict()
    payload["created_by"] = current_admin['sub']
    
    res = await db_execute(lambda: db.table("estate_drafts").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create estate draft")
    return res.data[0]

@router.get("/estates")
async def list_estate_drafts(current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("estate_drafts").select("*").order("created_at", desc=True).execute())
    return res.data

@router.post("/estates/{draft_id}/publish")
async def publish_estate(draft_id: str, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    
    # 1. Fetch Draft
    res = await db_execute(lambda: db.table("estate_drafts").select("*").eq("id", draft_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = res.data[0]
    if draft.get("is_public"):
        raise HTTPException(status_code=400, detail="Estate is already public")
        
    # 2. Create Properties for each variation
    variations = draft.get("variations", [])
    created_prop_ids = []
    
    for var in variations:
        prop_payload = {
            "name": f"{draft['name']} - {var['size_sqm']}SQM",
            "estate_name": draft['name'],
            "location": draft['location'],
            "description": draft['description'],
            "plot_size_sqm": var['size_sqm'],
            "starting_price": var['total_price'],
            "total_plots": var['total_plots'],
            "acquisition_cost": var.get('acquisition_cost', 0),
            "is_active": True
        }
        p_res = await db_execute(lambda: db.table("properties").insert(prop_payload).execute())
        if p_res.data:
            created_prop_ids.append(p_res.data[0]['id'])
            
    # 3. Update Draft Status
    await db_execute(lambda: db.table("estate_drafts").update({"is_public": True}).eq("id", draft_id).execute())
    
    # 4. Link existing expenses to the first property ID created
    if created_prop_ids:
        await db_execute(lambda: db.table("procurement_expenses").update({"property_id": created_prop_ids[0]}).eq("estate_draft_id", draft_id).execute())

    return {"status": "success", "properties_created": len(created_prop_ids)}
"""

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\routers\payouts.py"
with open(file_path, "a", encoding="utf-8") as f:
    f.write(content_to_append)
print("Appended successfully.")
