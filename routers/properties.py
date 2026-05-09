from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from models import PropertyCreate, PropertyUpdate, EstateVisibilityToggle
from database import get_db, db_execute
from routers.auth import verify_token

router = APIRouter()


@router.get("/")
async def list_properties(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("properties")\
        .select("*")\
        .eq("is_archived", False)\
        .order("name")\
        .execute()
    return result.data

@router.get("/archived")
async def list_archived_properties(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("properties")\
        .select("*")\
        .eq("is_archived", True)\
        .order("name")\
        .execute()
    return result.data


@router.post("/")
async def create_property(data: PropertyCreate, current_admin=Depends(verify_token)):
    db = get_db()
    # Use jsonable_encoder to handle Decimal/date types for Supabase
    property_data = jsonable_encoder(data, exclude_none=True)
    
    # Map to DB schema column name if migration hasn't been run
    if "starting_price" in property_data:
        property_data["total_price"] = property_data.pop("starting_price")
        
    result = await db_execute(lambda: db.table("properties").insert(property_data).execute())
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create property")
    return {"message": "Property created", "property": result.data[0]}


@router.put("/{property_id}")
async def update_property(property_id: str, data: PropertyUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    # Filter out None values and encode for Supabase
    update_data = jsonable_encoder(data, exclude_none=True)
    
    # Map to DB schema column name if migration hasn't been run
    if "starting_price" in update_data:
        update_data["total_price"] = update_data.pop("starting_price")
        
    result = await db_execute(lambda: db.table("properties").update(update_data).eq("id", property_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Property not found or update failed")
    return {"message": "Property updated", "property": result.data[0]}

@router.patch("/{property_id}/archive")
async def archive_property(property_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("properties").update({"is_archived": True}).eq("id", property_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Property archived", "property": result.data[0]}

@router.patch("/{property_id}/restore")
async def restore_property(property_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("properties").update({"is_archived": False, "is_active": True}).eq("id", property_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Property restored", "property": result.data[0]}
@router.get("/{property_id}")
async def get_property(property_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("properties").select("*").eq("id", property_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Property not found")
    return result.data[0]


@router.patch("/toggle-visibility")
async def toggle_estate_visibility(data: EstateVisibilityToggle, current_admin=Depends(verify_token)):
    """
    Hides an estate from public view.
    If no invoices are attached to a property, it is deleted.
    Otherwise, it's marked as inactive/archived.
    """
    db = get_db()
    
    # 1. Find all properties for this estate
    props_res = await db_execute(lambda: db.table("properties").select("id").eq("estate_name", data.estate_name).execute())
    if not props_res.data:
        return {"status": "success", "message": "No properties found for this estate", "deleted": 0, "archived": 0}
        
    prop_ids = [p["id"] for p in props_res.data]
    deleted_count = 0
    archived_count = 0
    
    for pid in prop_ids:
        # Check for invoices
        inv_res = await db_execute(lambda: db.table("invoices").select("id").eq("property_id", pid).limit(1).execute())
        
        if not inv_res.data:
            # DELETE
            await db_execute(lambda: db.table("properties").delete().eq("id", pid).execute())
            deleted_count += 1
        else:
            # ARCHIVE / MAKE PRIVATE
            # Setting is_active=False hides it from public marketing views
            # Setting is_archived=True is a fallback archive status
            await db_execute(lambda: db.table("properties").update({
                "is_active": data.is_active, 
                "is_archived": not data.is_active
            }).eq("id", pid).execute())
            archived_count += 1
            
    # 2. Handle draft revert and procurement expense re-linking
    if not data.is_active:
        # Get the draft ID first
        draft_res = await db_execute(lambda: db.table("estate_drafts").select("id").eq("name", data.estate_name).execute())
        if draft_res.data:
            draft_id = draft_res.data[0]["id"]
            # Revert draft status
            await db_execute(lambda: db.table("estate_drafts").update({"is_public": False}).eq("id", draft_id).execute())
            
            # Re-link expenses from properties back to the draft ID
            # This ensures procurement history is preserved even if the property record is deleted
            for pid in prop_ids:
                await db_execute(lambda: db.table("procurement_expenses")
                    .update({"property_id": None, "estate_draft_id": draft_id})
                    .eq("property_id", pid)
                    .execute())
    else:
        # If making public, we usually use the publish endpoint, but let's sync here too
        await db_execute(lambda: db.table("estate_drafts").update({"is_public": True}).eq("name", data.estate_name).execute())

    return {
        "status": "success", 
        "message": f"Processed {data.estate_name}", 
        "deleted": deleted_count, 
        "archived": archived_count
    }
