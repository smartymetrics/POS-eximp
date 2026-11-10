from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from models import PropertyCreate, PropertyUpdate
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
    property_data = jsonable_encoder(data)
    result = await db_execute(lambda: db.table("properties").insert(property_data).execute())
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create property")
    return {"message": "Property created", "property": result.data[0]}


@router.put("/{property_id}")
async def update_property(property_id: str, data: PropertyUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    # Filter out None values and encode for Supabase
    update_data = jsonable_encoder(data, exclude_none=True)
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
