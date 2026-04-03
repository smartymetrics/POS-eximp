from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_db
from routers.auth import verify_token
from datetime import datetime, timedelta

router = APIRouter()

class SequenceStepCreate(BaseModel):
    step_number: int
    delay_days: int
    campaign_id: str

class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_event: str = 'manual'
    steps: List[SequenceStepCreate]

@router.get("/")
async def list_sequences(current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("marketing_sequences").select("*").execute()
    return res.data

@router.post("/")
async def create_sequence(data: SequenceCreate, current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Create Sequence header
    seq_res = db.table("marketing_sequences").insert({
        "name": data.name,
        "description": data.description,
        "trigger_event": data.trigger_event
    }).execute()
    
    if not seq_res.data:
        raise HTTPException(status_code=500, detail="Failed to create sequence")
    
    seq_id = seq_res.data[0]["id"]
    
    # 2. Create Steps
    step_entries = []
    for step in data.steps:
        step_entries.append({
            "sequence_id": seq_id,
            "step_number": step.step_number,
            "delay_days": step.delay_days,
            "campaign_id": step.campaign_id
        })
    
    if step_entries:
        db.table("sequence_steps").insert(step_entries).execute()
        
    return {"id": seq_id, "message": "Sequence and steps created successfully."}

@router.get("/{id}")
async def get_sequence(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    seq_res = db.table("marketing_sequences").select("*, sequence_steps(*)").eq("id", id).execute()
    if not seq_res.data:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq_res.data[0]

@router.post("/{id}/enroll")
async def enroll_contact(id: str, contact_id: str, current_admin=Depends(verify_token)):
    """Manually enroll a contact into a sequence."""
    db = get_db()
    
    # 1. Check if already enrolled
    existing = db.table("contact_sequence_status").select("*").eq("contact_id", contact_id).eq("sequence_id", id).execute()
    if existing.data:
        return {"message": "Contact already in this sequence."}
        
    # 2. Enroll starting at step 1
    # Next send date = today (since step 1 delay is usually 0 for welcome)
    res = db.table("contact_sequence_status").insert({
        "contact_id": contact_id,
        "sequence_id": id,
        "current_step": 1,
        "status": "active",
        "next_send_date": datetime.utcnow().date().isoformat()
    }).execute()
    
    return {"message": "Contact enrolled successfully.", "data": res.data[0] if res.data else None}

@router.delete("/{id}")
async def delete_sequence(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    db.table("marketing_sequences").delete().eq("id", id).execute()
    return {"message": "Sequence deleted."}
