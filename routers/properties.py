from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from models import PropertyCreate, PropertyUpdate
from database import get_db
from routers.auth import verify_token

router = APIRouter()


@router.get("/")
async def list_properties(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("properties").select("*").eq("is_active", True).order("name").execute()
    return result.data


@router.post("/")
async def create_property(data: PropertyCreate, current_admin=Depends(verify_token)):
    db = get_db()
    # Use jsonable_encoder to handle Decimal/date types for Supabase
    property_data = jsonable_encoder(data)
    result = db.table("properties").insert(property_data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create property")
    return {"message": "Property created", "property": result.data[0]}


@router.put("/{property_id}")
async def update_property(property_id: str, data: PropertyUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    # Filter out None values and encode for Supabase
    update_data = jsonable_encoder(data, exclude_none=True)
    result = db.table("properties").update(update_data).eq("id", property_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Property not found or update failed")
    return {"message": "Property updated", "property": result.data[0]}
