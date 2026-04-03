from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class CampaignCreate(BaseModel):
    title: str
    subject: str
    content_html: str
    target_audience: str = "all_clients" # all_clients, leads, property_owners, specific
    specific_emails: Optional[str] = None

class CampaignUpdate(BaseModel):
    title: Optional[str]
    subject: Optional[str]
    content_html: Optional[str]
    target_audience: Optional[str]
    specific_emails: Optional[str] = None

@router.get("/")
async def list_campaigns(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("marketing_campaigns").select("*, admins(full_name)").order("created_at", desc=True).execute()
    return result.data

@router.post("/")
async def create_campaign(data: CampaignCreate, current_admin=Depends(verify_token)):
    db = get_db()
    campaign_data = {
        "title": data.title,
        "subject": data.subject,
        "content_html": data.content_html,
        "target_audience": data.target_audience,
        "specific_emails": data.specific_emails,
        "status": "draft",
        "created_by": current_admin["sub"]
    }
    result = db.table("marketing_campaigns").insert(campaign_data).execute()
    
    await log_activity(
        "marketing_campaign_created",
        f"Marketing campaign '{data.title}' created as draft.",
        current_admin["sub"]
    )
    return result.data[0]

@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("marketing_campaigns").select("*, admins(full_name)").eq("id", campaign_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result.data[0]

@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, data: CampaignUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Check if sending or sent
    current = db.table("marketing_campaigns").select("status").eq("id", campaign_id).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if current.data[0]["status"] not in ["draft", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot edit a campaign that is already sent or sending.")

    update_dict = {k: v for k, v in data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    result = db.table("marketing_campaigns").update(update_dict).eq("id", campaign_id).execute()
    return result.data[0]

@router.post("/{campaign_id}/send")
async def send_campaign(campaign_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Fetch Campaign
    camp_res = db.table("marketing_campaigns").select("*").eq("id", campaign_id).execute()
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = camp_res.data[0]
    
    if campaign["status"] in ["sending", "sent"]:
        raise HTTPException(status_code=400, detail="Campaign already sent or currently sending.")

    # 2. Determine Audience
    recipients = []
    if campaign["target_audience"] == "specific":
        if not campaign["specific_emails"]:
            raise HTTPException(status_code=400, detail="Specific emails are required for this audience type.")
        emails = [e.strip() for e in campaign["specific_emails"].split(",") if e.strip()]
        recipients = [{"email": e, "full_name": "Valued Guest"} for e in emails]
    else:
        audience_query = db.table("clients").select("id, full_name, email")
        if campaign["target_audience"] == "leads":
            # Potential placeholder logic for leads (e.g., clients with no confirmed payments)
            pass
        elif campaign["target_audience"] == "property_owners":
            # Potential placeholder logic for owners
            pass
        
        db_res = audience_query.execute()
        recipients = db_res.data

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients found for the selected audience.")

    # 3. Update status to sending
    db.table("marketing_campaigns").update({
        "status": "sending", 
        "total_recipients": len(recipients)
    }).eq("id", campaign_id).execute()

    # 4. Queue background task
    from email_service import broadcast_campaign_email
    background_tasks.add_task(
        broadcast_campaign_email,
        campaign,
        recipients,
        current_admin["sub"]
    )

    await log_activity(
        "marketing_campaign_sent",
        f"Broadcast started for campaign: {campaign['title']} to {len(recipients)} recipients.",
        current_admin["sub"]
    )

    return {"message": "Campaign broadcast started", "recipient_count": len(recipients)}
