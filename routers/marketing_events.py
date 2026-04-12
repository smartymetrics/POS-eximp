from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import get_db, db_execute
from routers.auth import verify_token
from datetime import date

router = APIRouter()

class EventCreate(BaseModel):
    name: str
    event_date: date
    action: Optional[str] = None
    event_type: str = "custom"
    is_recurring: bool = False
    frequency: Optional[str] = None
    end_date: Optional[date] = None

@router.post("/")
async def create_event(event: EventCreate, current_admin=Depends(verify_token)):
    """Add a custom business event to the marketing calendar."""
    db = get_db()
    
    data = {
        "name": event.name,
        "event_date": event.event_date.isoformat(),
        "action": event.action,
        "event_type": event.event_type,
        "is_recurring": event.is_recurring,
        "frequency": event.frequency,
        "end_date": event.end_date.isoformat() if event.end_date else None,
        "created_by": current_admin.get("sub")
    }
    
    res = await db_execute(lambda: db.table("marketing_events").insert(data).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create event")
    return res.data[0]

@router.delete("/{id}")
async def delete_event(id: str, current_admin=Depends(verify_token)):
    """Delete a custom business event."""
    db = get_db()
    res = await db_execute(lambda: db.table("marketing_events").delete().eq("id", id).execute())
    return {"status": "ok"}
