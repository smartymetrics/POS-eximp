from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime, timedelta
from marketing_service import apply_segment_filters

router = APIRouter()

class SegmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    segment_type: str = "static" # static / dynamic
    filter_rules: Optional[List[Dict[str, Any]]] = None

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
async def get_segment_contacts(id: str, current_admin=Depends(verify_token)):
    """Preview contacts who match a dynamic or static segment."""
    db = get_db()
    
    # Handle Smart Segments
    if id == 'engaged':
        res = db.table("marketing_contacts").select("*").gt("total_emails_opened", 0).eq("is_subscribed", True).execute()
        return res.data
    elif id == 'hot':
        res = db.table("marketing_contacts").select("*").gt("engagement_score", 50).eq("is_subscribed", True).execute()
        return res.data
    elif id == 'recent':
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        res = db.table("marketing_contacts").select("*").gt("created_at", thirty_days_ago).eq("is_subscribed", True).execute()
        return res.data

    # Handle Custom Segments
    seg_res = db.table("marketing_segments").select("*").eq("id", id).execute()
    if not seg_res.data:
        raise HTTPException(status_code=404, detail="Segment not found")
    segment = seg_res.data[0]
    
    if segment["segment_type"] == "static":
        return []
    
    rules = segment.get("filter_rules") or []
    query = db.table("marketing_contacts").select("*").eq("is_subscribed", True)
    query = apply_segment_filters(query, rules)
    result = query.limit(100).execute()
    return result.data

@router.post("/preview")
async def preview_segment_rules(rules: List[Dict[str, Any]], current_admin=Depends(verify_token)):
    """Count contacts who match provided rules (without saving segment)."""
    db = get_db()
    query = db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True)
    query = apply_segment_filters(query, rules)
    result = query.execute()
    return {"count": result.count or 0}

@router.get("/{id}/count")
async def get_segment_count(id: str, current_admin=Depends(verify_token)):
    """Get total count for an existing segment."""
    db = get_db()
    seg_res = db.table("marketing_segments").select("*").eq("id", id).execute()
    if not seg_res.data:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    segment = seg_res.data[0]
    rules = segment.get("filter_rules") or []
    query = db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True)
    query = apply_segment_filters(query, rules)
    result = query.execute()
    return {"count": result.count or 0}
