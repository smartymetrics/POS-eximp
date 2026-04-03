from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime, timedelta
from marketing_service import broadcast_campaign, send_marketing_email

router = APIRouter()

class CampaignSendTarget(BaseModel):
    segment_ids: Optional[List[str]] = None
    manual_emails: Optional[List[str]] = None

class CampaignCreate(BaseModel):
    name: str # Internal name
    subject_a: str
    preview_text: Optional[str]
    html_body_a: str
    from_name: Optional[str] = 'Eximp & Cloves'
    reply_to: Optional[str] = 'marketing@mail.eximps-cloves.com'

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject_a: Optional[str] = None
    preview_text: Optional[str] = None
    html_body_a: Optional[str] = None
    status: Optional[str] = None
    
    class Config:
        extra = "ignore"

class CampaignTest(BaseModel):
    email: str
    subject_a: Optional[str] = None
    html_body_a: Optional[str] = None

    class Config:
        extra = "ignore"

@router.get("/")
async def list_campaigns(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("email_campaigns").select("*, admins(full_name)").order("created_at", desc=True).execute()
    return result.data

@router.post("/")
async def create_campaign(data: CampaignCreate, current_admin=Depends(verify_token)):
    db = get_db()
    campaign_data = {
        **data.dict(),
        "status": "draft",
        "created_by": current_admin["sub"]
    }
    result = db.table("email_campaigns").insert(campaign_data).execute()
    
    await log_activity(
        "marketing_campaign_created",
        f"Marketing campaign '{data.name}' created as draft.",
        current_admin["sub"]
    )
    return result.data[0]

@router.get("/{id}")
async def get_campaign(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("email_campaigns").select("*, admins(full_name)").eq("id", id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result.data[0]

@router.put("/{id}")
async def update_campaign(id: str, data: CampaignUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Check status
    current = db.table("email_campaigns").select("status").eq("id", id).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if current.data[0]["status"] in ["sent", "sending"]:
        raise HTTPException(status_code=400, detail="Cannot edit a campaign that is already sent or sending.")

    update_dict = {k: v for k, v in data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    result = db.table("email_campaigns").update(update_dict).eq("id", id).execute()
    return result.data[0]

@router.post("/{id}/send-test")
async def send_test_email(id: str, data: CampaignTest, current_admin=Depends(verify_token)):
    """Sends a single test email of the campaign with real-time editor content."""
    db = get_db()
    camp_res = db.table("email_campaigns").select("*").eq("id", id).execute()
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = camp_res.data[0]
    campaign["status"] = "test"
    
    # Override with real-time editor content if provided
    if data.subject_a: campaign["subject_a"] = data.subject_a
    if data.html_body_a: campaign["html_body_a"] = data.html_body_a
    
    # Dummy contact for testing
    contact = {
        "id": "test-id",
        "first_name": "Test",
        "last_name": "User",
        "email": data.email
    }
    
    res = await send_marketing_email(campaign, contact)
    if res:
        return {"message": f"Test email sent to {data.email}"}
    raise HTTPException(status_code=500, detail="Failed to send test email")

@router.post("/{id}/send")
async def send_campaign_broadcast(id: str, target: Optional[CampaignSendTarget], background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    """Starts the background task to broadcast the campaign with optional targeting."""
    db = get_db()
    
    # Check status
    camp_res = db.table("email_campaigns").select("status").eq("id", id).execute()
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if camp_res.data[0]["status"] != "draft":
        raise HTTPException(status_code=400, detail="Campaign must be in draft status to send.")

    # Mark as scheduled (about to send)
    db.table("email_campaigns").update({
        "status": "scheduled",
        "scheduled_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()

    segment_ids = target.segment_ids if target else None
    manual_emails = target.manual_emails if target else None

    background_tasks.add_task(broadcast_campaign, id, segment_ids, manual_emails)
    
    await log_activity(
        "marketing_campaign_broadcast_started",
        f"Broadcast initiated for campaign ID: {id}. Targets: {segment_ids or 'All'}",
        current_admin["sub"]
    )
    
    return {"message": "Broadcast started in the background."}

@router.get("/calendar/events")
async def list_calendar_events(current_admin=Depends(verify_token)):
    """Fetches the automated marketing calendar."""
    from calendar_service import get_marketing_calendar
    events = get_marketing_calendar()
    return events
