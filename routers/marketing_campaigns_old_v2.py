from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from database import get_db, db_execute
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime, timedelta
from marketing_service import broadcast_campaign, send_marketing_email, get_daily_quota_stats

router = APIRouter()

class CampaignSendTarget(BaseModel):
    segment_ids: Optional[List[str]] = None
    manual_emails: Optional[List[str]] = None
    scheduled_at: Optional[str] = None # ISO format datetime

class CampaignCreate(BaseModel):
    name: str # Internal name
    subject_a: str
    subject_b: Optional[str] = None
    preview_text: Optional[str]
    html_body_a: str
    html_body_b: Optional[str] = None
    is_ab_test: Optional[bool] = False
    from_name: Optional[str] = 'Eximp & Cloves'
    reply_to: Optional[str] = 'marketing@mail.eximps-cloves.com'
    budget: Optional[float] = 0

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject_a: Optional[str] = None
    subject_b: Optional[str] = None
    preview_text: Optional[str] = None
    html_body_a: Optional[str] = None
    html_body_b: Optional[str] = None
    is_ab_test: Optional[bool] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    actual_spend: Optional[float] = None
    
    class Config:
        extra = "ignore"

class CampaignTest(BaseModel):
    email: str
    subject_a: Optional[str] = None
    subject_b: Optional[str] = None
    html_body_a: Optional[str] = None
    html_body_b: Optional[str] = None
    variant: Optional[str] = 'A'

    class Config:
        extra = "ignore"

@router.get("/")
async def list_campaigns(current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("email_campaigns").select("*, admins(full_name)").order("created_at", desc=True).execute())
    return result.data

@router.post("/")
async def create_campaign(data: CampaignCreate, current_admin=Depends(verify_token)):
    db = get_db()
    campaign_data = {
        **data.dict(),
        "status": "draft",
        "created_by": current_admin["sub"]
    }
    result = await db_execute(lambda: db.table("email_campaigns").insert(campaign_data).execute())
    
    await log_activity(
        "marketing_campaign_created",
        f"Marketing campaign '{data.name}' created as draft.",
        current_admin["sub"]
    )
    return result.data[0]

@router.get("/audit-logs")
async def get_marketing_audit_logs(limit: int = 50, admin: dict = Depends(verify_token)):
    """Fetches the audit log of all marketing actions for the dashboard."""
    db = get_db()
    query = db.table("activity_log").select("*, admins(full_name)").ilike("event_type", "marketing_%").order("created_at", desc=True).limit(limit)
    res = await db_execute(lambda: query.execute())
    
    logs = []
    for item in res.data:
        logs.append({
            "id": item["id"],
            "event_type": item["event_type"],
            "description": item["description"],
            "performed_by_name": item["admins"].get("full_name") if item.get("admins") else "System",
            "created_at": item["created_at"]
        })
    return logs

@router.get("/{id}")
async def get_campaign(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("email_campaigns").select("*, admins(full_name)").eq("id", id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result.data[0]

@router.put("/{id}")
async def update_campaign(id: str, data: CampaignUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Check status - restrict everything EXCEPT budget/spend for sent campaigns
    current = await db_execute(lambda: db.table("email_campaigns").select("status").eq("id", id).execute())
    if not current.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    is_locked = current.data[0]["status"] in ["sent", "sending"]
    update_dict = {k: v for k, v in data.dict().items() if v is not None}
    
    if is_locked:
        # Only allow budget and actual_spend updates if already sent
        allowed = {"budget", "actual_spend"}
        final_update = {k: v for k, v in update_dict.items() if k in allowed}
        if not final_update:
            raise HTTPException(status_code=400, detail="Cannot edit campaign content after it has been sent. Only investment (Budget/Spend) can be updated.")
        update_dict = final_update
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    result = await db_execute(lambda: db.table("email_campaigns").update(update_dict).eq("id", id).execute())
    
    # Log the save action
    if result.data:
        campaign_name = result.data[0].get("name", "Unknown Campaign")
        action = "financials updated" if is_locked else "saved/edited"
        await log_activity(
            "marketing_campaign_saved",
            f"Campaign '{campaign_name}' {action}.",
            current_admin["sub"]
        )
        
    return result.data[0]

@router.post("/{id}/send-test")
async def send_test_email(id: str, data: CampaignTest, current_admin=Depends(verify_token)):
    """Sends a single test email of the campaign with real-time editor content."""
    db = get_db()
    camp_res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = camp_res.data[0]
    campaign["status"] = "test"
    
    # Override with real-time editor content if provided
    if data.variant == 'B':
        if data.subject_b: campaign["subject_a"] = data.subject_b
        elif campaign.get("subject_b"): campaign["subject_a"] = campaign["subject_b"]
        
        if data.html_body_b: campaign["html_body_a"] = data.html_body_b
        elif campaign.get("html_body_b"): campaign["html_body_a"] = campaign["html_body_b"]
    else:
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
        return {"message": f"Test email (Variant {data.variant}) sent to {data.email}"}
    raise HTTPException(status_code=500, detail="Failed to send test email")

@router.post("/{id}/send")
async def send_campaign_broadcast(id: str, target: Optional[CampaignSendTarget], background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    """Starts the background task to broadcast the campaign with optional targeting."""
    db = get_db()
    
    # Check status
    camp_res = await db_execute(lambda: db.table("email_campaigns").select("status").eq("id", id).execute())
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if camp_res.data[0]["status"] != "draft":
        raise HTTPException(status_code=400, detail="Campaign must be in draft status to send.")

    # TASK 8: Pre-send validation checklist
    campaign_full = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
    if not campaign_full.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    camp = campaign_full.data[0]

    errors = []

    # 1. Subject line must not be empty
    if not camp.get("subject_a") or not camp["subject_a"].strip():
        errors.append("Subject line cannot be empty.")

    # 2. HTML body must not be empty
    if not camp.get("html_body_a") or not camp["html_body_a"].strip():
        errors.append("Email body cannot be empty.")

    # 3. Must have at least one segment or manual emails provided
    if not (target and (target.segment_ids or target.manual_emails)):
        errors.append("You must select at least one segment or provide recipient emails.")

    # 4. Unsubscribe link must be present
    if camp.get("html_body_a") and "unsubscribe" not in camp["html_body_a"].lower():
        errors.append("Email body must contain an unsubscribe link.")

    # 5. Detect broken variables (unreplaced {{variable}} patterns)
    import re
    broken_vars = re.findall(r'\{\{(\w+)\}\}', camp.get("html_body_a", ""))
    known_vars = {"first_name", "last_name", "full_name", "email", "phone", "unsubscribe_url",
                  "outstanding", "amount_paid", "total_invoiced", "property_name", "due_date", "invoice_number"}
    bad_vars = [v for v in broken_vars if v not in known_vars]
    if bad_vars:
        errors.append(f"Unknown template variables found: {', '.join(['{{'+ v +'}}' for v in bad_vars])}. Check for typos.")

    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

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
    
    # TASK 8: Estimate recipient count
    estimated_count = 0
    if target and target.segment_ids:
        for sid in target.segment_ids:
            count_res = await db_execute(lambda: db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True).execute())
            estimated_count += count_res.count or 0
    elif target and target.manual_emails:
        estimated_count = len(target.manual_emails)

    return {"message": "Broadcast started in the background.", "estimated_recipients": estimated_count}

@router.post("/{id}/cancel-schedule")
async def cancel_scheduled_broadcast(id: str, current_admin=Depends(verify_token)):
    """Cancels a scheduled broadcast and returns it to draft status."""
    db = get_db()
    
    # Check status
    camp_res = await db_execute(lambda: db.table("email_campaigns").select("status").eq("id", id).execute())
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

@router.post("/{id}/pause")
async def pause_campaign(id: str, current_admin=Depends(verify_token)):
    """TASK 2A: Pause an actively sending campaign."""
    db = get_db()
    res = await db_execute(lambda: db.table("email_campaigns").select("status").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if res.data[0]["status"] != "sending":
        raise HTTPException(status_code=400, detail="Only actively sending campaigns can be paused.")
    
    await db_execute(lambda: db.table("email_campaigns").update({"status": "paused"}).eq("id", id).execute())
    
    await log_activity(
        "marketing_campaign_paused",
        f"Campaign '{id}' paused mid-send.",
        current_admin["sub"]
    )
    return {"message": "Campaign paused. Sending will stop after the current batch."}

@router.post("/{id}/resume")
async def resume_campaign(id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    """TASK 2B: Resume a paused campaign."""
    db = get_db()
    res = await db_execute(lambda: db.table("email_campaigns").select("status").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if res.data[0]["status"] != "paused":
        raise HTTPException(status_code=400, detail="Only paused campaigns can be resumed.")
    
    # Count pending recipients
    pending_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "pending").execute())
    pending_count = pending_res.count or 0
    
    await db_execute(lambda: db.table("email_campaigns").update({"status": "sending"}).eq("id", id).execute())
    
    # Use re-run broadcast_campaign
    background_tasks.add_task(broadcast_campaign, id, None, None)
    
    await log_activity(
        "marketing_campaign_resumed",
        f"Campaign '{id}' resumed. {pending_count} recipients remaining.",
        current_admin["sub"]
    )
    return {"message": f"Campaign resumed. {pending_count} recipients remaining.", "pending": pending_count}

@router.post("/{id}/sync")
async def sync_campaign_stats(id: str, current_admin=Depends(verify_token)):
    """Manually recalculates stats for a campaign from the recipients table."""
    db = get_db()
    
    # 1. Count Opens (unique contacts who opened)
    opens_res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id", count="exact").eq("campaign_id", id).not_.is_("opened_at", "null").execute())
    total_opens = opens_res.count or 0
    
    # 2. Count Clicks (unique contacts who clicked)
    clicks_res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id", count="exact").eq("campaign_id", id).not_.is_("clicked_at", "null").execute())
    total_clicks = clicks_res.count or 0
    
    # 3. Count Attributed revenue (sum of paid invoices linked to this campaign)
    revenue_res = await db_execute(lambda: db.table("invoices").select("amount").eq("marketing_campaign_id", id).eq("status", "paid").execute())
    total_revenue = sum([i["amount"] for i in revenue_res.data]) if revenue_res.data else 0
    
    # 4. Update Campaign Table
    db.table("email_campaigns").update({
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "attributed_revenue": total_revenue,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()
    
    return {
        "id": id,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "attributed_revenue": total_revenue
    }
    

@router.post("/{id}/force-complete")
async def force_complete_stuck_campaign(id: str, current_admin=Depends(verify_token)):
    """Admin tool: Force a stuck 'sending' campaign to 'sent' status.
    Use this for campaigns that finished sending but got stuck due to a crash.
    It recalculates total_sent from the campaign_recipients table first."""
    db = get_db()
    
    res = await db_execute(lambda: db.table("email_campaigns").select("status, name").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    camp = res.data[0]
    if camp["status"] not in ["sending", "failed"]:
        raise HTTPException(status_code=400, detail=f"Campaign is '{camp['status']}' — only 'sending' or 'failed' campaigns can be force-completed.")

    # Recount actual sent emails from the recipients table
    sent_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "sent").execute())
    actual_sent = sent_res.count or 0
    
    # Mark any remaining 'pending' recipients as 'failed' (they were never sent)
    await db_execute(lambda: db.table("campaign_recipients").update({"status": "failed"}).eq("campaign_id", id).eq("status", "pending").execute())

    db.table("email_campaigns").update({
        "status": "sent",
        "total_sent": actual_sent,
        "sent_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()
    
    await log_activity(
        "marketing_campaign_force_completed",
        f"Campaign '{camp.get('name', id)}' force-completed by admin. Actual sent count: {actual_sent}.",
        current_admin["sub"]
    )
    
    return {"message": f"Campaign marked as sent. Actual emails delivered: {actual_sent}.", "total_sent": actual_sent}

@router.post("/{id}/duplicate")
async def duplicate_campaign(id: str, current_admin=Depends(verify_token)):
    """Creates a new draft copy of an existing campaign."""
    db = get_db()
    
    # 1. Fetch source
    res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    source = res.data[0]
    
    # 2. Create copy data using safe fallbacks for NULLs and missing keys
    copy_data = {
        "name": f"{source.get('name') or 'Untitled Campaign'} (Copy)",
        "subject_a": source.get("subject_a") or "",
        "subject_b": source.get("subject_b"),
        "preview_text": source.get("preview_text") or "",
        "html_body_a": source.get("html_body_a") or "",
        "html_body_b": source.get("html_body_b"),
        "is_ab_test": source.get("is_ab_test") or False,
        "from_name": source.get("from_name") or "Eximp & Cloves",
        "reply_to": source.get("reply_to") or "marketing@mail.eximps-cloves.com",
        "status": "draft",
        "created_by": current_admin["sub"]
    }
    
    # 3. Save
    result = await db_execute(lambda: db.table("email_campaigns").insert(copy_data).execute())
    
    await log_activity(
        "marketing_campaign_duplicated",
        f"Campaign '{source.get('name', 'Untitled')}' duplicated as '{copy_data['name']}'",
        current_admin["sub"]
    )
    
    return result.data[0]

@router.get("/calendar/events")
async def list_calendar_events(current_admin=Depends(verify_token)):
    """Fetches the automated marketing calendar."""
    from calendar_service import get_marketing_calendar
    events = get_marketing_calendar()
    return events
@router.get("/settings/quota")
async def get_quota_settings(current_admin=Depends(verify_token)):
    """Returns the current daily quota configuration and usage."""
    stats = await get_daily_quota_stats()
    return stats

@router.post("/settings/quota")
async def update_quota_settings(enabled: bool, limit: Optional[int] = 80, current_admin=Depends(verify_token)):
    """Updates the global daily quota safety brake settings."""
    db = get_db()
    new_value = {"enabled": enabled, "limit": limit, "reset_hour": 0}
    
    # Safe update using .eq() to bypass upsert unique constraint issues
    res = await db_execute(lambda: db.table("marketing_settings").update({
        "value": new_value,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("key", "daily_quota").execute())
    
    if not res.data:
        # Fallback if the migration hasn't initialized the row yet
        await db_execute(lambda: db.table("marketing_settings").insert({
            "key": "daily_quota",
            "value": new_value,
            "updated_at": datetime.utcnow().isoformat()
        }).execute())
    
    return {"message": "Marketing quota settings updated.", "settings": new_value}
