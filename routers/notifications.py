from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from database import get_db, db_execute
from routers.auth import verify_token
from datetime import datetime

router = APIRouter()

class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str = "general"
    reference_id: Optional[str] = None

class NotificationResponse(NotificationBase):
    id: str
    is_read: bool
    created_at: str

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(unread_only: bool = False, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("notifications").select("*").eq("admin_id", current_admin["sub"]).order("created_at", desc=True).limit(50)
    
    if unread_only:
        query = query.eq("is_read", False)
        
    res = await db_execute(lambda: query.execute())
    return res.data

@router.patch("/{notification_id}/read")
async def mark_as_read(notification_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("admin_id", current_admin["sub"]).execute())
    return {"status": "ok"}

@router.post("/mark-all-read")
async def mark_all_read(current_admin=Depends(verify_token)):
    db = get_db()
    await db_execute(lambda: db.table("notifications").update({"is_read": True}).eq("admin_id", current_admin["sub"]).eq("is_read", False).execute())
    return {"status": "ok"}

# Utility function for other routers to create notifications
async def create_notification(admin_id: str, title: str, message: str, n_type: str = "general", ref_id: Optional[str] = None):
    db = get_db()
    await db_execute(lambda: db.table("notifications").insert({
        "admin_id": admin_id,
        "title": title,
        "message": message,
        "notification_type": n_type,
        "reference_id": ref_id
    }).execute())
