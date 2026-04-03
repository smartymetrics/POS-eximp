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
    scheduled_at: Optional[str] = None # ISO format datetime

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

    # Handle Scheduling
    if target and target.scheduled_at:
        try:
            scheduled_dt = datetime.fromisoformat(target.scheduled_at.replace('Z', '+00:00'))
            if scheduled_dt <= datetime.now(scheduled_dt.tzinfo):
                 raise HTTPException(status_code=400, detail="Scheduled time must be in the future.")
            
            db.table("email_campaigns").update({
                "status": "scheduled",
                "scheduled_for": target.scheduled_at,
                "target_config": target.dict(exclude={'scheduled_at'})
            }).eq("id", id).execute()

            await log_activity(
                "marketing_campaign_scheduled",
                f"Campaign '{id}' scheduled for {target.scheduled_at}.",
                current_admin["sub"]
            )
            return {"message": f"Broadcast scheduled for {target.scheduled_at}"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

    # Mark as scheduled (about to send immediately)
    db.table("email_campaigns").update({
        "status": "scheduled",
        "scheduled_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()

    background_tasks.add_task(broadcast_campaign, id, target.segment_ids if target else None, target.manual_emails if target else None)
    
    await log_activity(
        "marketing_campaign_broadcast_started",
        f"Broadcast initiated for campaign ID: {id}.",
        current_admin["sub"]
    )
    
    return {"message": "Broadcast started in the background."}

@router.post("/{id}/cancel-schedule")
async def cancel_scheduled_broadcast(id: str, current_admin=Depends(verify_token)):
    """Cancels a scheduled broadcast and returns it to draft status."""
    db = get_db()
    
    # Check status
    camp_res = db.table("email_campaigns").select("status").eq("id", id).execute()
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if camp_res.data[0]["status"] != "scheduled":
        raise HTTPException(status_code=400, detail="Only scheduled campaigns can be cancelled.")

    db.table("email_campaigns").update({
        "status": "draft",
        "scheduled_for": None,
        "target_config": None
    }).eq("id", id).execute()

    await log_activity(
        "marketing_campaign_unscheduled",
        f"Campaign '{id}' broadcast cancelled and returned to draft.",
        current_admin["sub"]
    )
    
    return {"message": "Schedule cancelled. Campaign is back in draft."}

@router.post("/{id}/sync")
async def sync_campaign_stats(id: str, current_admin=Depends(verify_token)):
    """Manually recalculates stats for a campaign from the recipients table."""
    db = get_db()
    
    # 1. Count Opens (unique contacts who opened)
    opens_res = db.table("campaign_recipients").select("contact_id", count="exact").eq("campaign_id", id).not_.is_("opened_at", "null").execute()
    total_opens = opens_res.count or 0
    
    # 2. Count Clicks (unique contacts who clicked)
    clicks_res = db.table("campaign_recipients").select("contact_id", count="exact").eq("campaign_id", id).not_.is_("clicked_at", "null").execute()
    total_clicks = clicks_res.count or 0
    
    # 3. Update Campaign Table
    db.table("email_campaigns").update({
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()
    
    return {
        "id": id,
        "total_opens": total_opens,
        "total_clicks": total_clicks
    }
    
@router.post("/{id}/duplicate")
async def duplicate_campaign(id: str, current_admin=Depends(verify_token)):
    """Creates a new draft copy of an existing campaign."""
    db = get_db()
    
    # 1. Fetch source
    res = db.table("email_campaigns").select("*").eq("id", id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    source = res.data[0]
    
    # 2. Create copy data
    copy_data = {
        "name": f"{source['name']} (Copy)",
        "subject_a": source["subject_a"],
        "preview_text": source["preview_text"],
        "html_body_a": source["html_body_a"],
        "from_name": source["from_name"],
        "reply_to": source["reply_to"],
        "status": "draft",
        "created_by": current_admin["sub"]
    }
    
    # 3. Save
    result = db.table("email_campaigns").insert(copy_data).execute()
    
    await log_activity(
        "marketing_campaign_duplicated",
        f"Campaign '{source['name']}' duplicated as '{copy_data['name']}'",
        current_admin["sub"]
    )
    
    return result.data[0]

@router.get("/calendar/events")
async def list_calendar_events(current_admin=Depends(verify_token)):
    """Fetches the automated marketing calendar."""
    from calendar_service import get_marketing_calendar
    events = get_marketing_calendar()
    return events
