from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime

router = APIRouter()

class SegmentCreate(BaseModel):
    name: str
    description: Optional[str]
    segment_type: str = "static" # static / dynamic
    filter_rules: Optional[Dict[str, Any]]

@router.get("/")
async def list_segments(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("marketing_segments").select("*").execute()
    return result.data

@router.post("/")
async def create_segment(data: SegmentCreate, current_admin=Depends(verify_token)):
    db = get_db()
    segment_data = {
        **data.dict(),
        "created_by": current_admin["sub"]
    }
    result = db.table("marketing_segments").insert(segment_data).execute()
    
    await log_activity(
        "marketing_segment_created",
        f"New marketing segment '{data.name}' created.",
        current_admin["sub"]
    )
    return result.data[0]

@router.delete("/{id}")
async def delete_segment(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    db.table("marketing_segments").delete().eq("id", id).execute()
    return {"status": "ok"}

@router.get("/{id}/contacts")
async def preview_segment_contacts(id: str, current_admin=Depends(verify_token)):
    """Preview contacts who match a dynamic or static segment."""
    db = get_db()
    # 1. Fetch Segment
    seg_res = db.table("marketing_segments").select("*").eq("id", id).execute()
    if not seg_res.data:
        raise HTTPException(status_code=404, detail="Segment not found")
    segment = seg_res.data[0]
    
    # 2. Dynamic Filtering Logic (Simplification for now)
    # real dynamic filtering would use the filter_rules JSONB to build a Supabase query
    if segment["segment_type"] == "static":
        # logic for manual contacts in join table
        return []
    
    contacts = db.table("marketing_contacts").select("*").eq("is_subscribed", True).execute().data
    return contacts[:50] # return first 50 as preview
