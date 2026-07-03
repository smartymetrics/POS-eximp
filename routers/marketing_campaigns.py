from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Query
from typing import List, Optional
from pydantic import BaseModel
from database import get_db, db_execute, supabase
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime, timedelta
from marketing_service import broadcast_campaign, send_marketing_email, get_daily_quota_stats
import time
import io
from PIL import Image

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
    preview_text_b: Optional[str] = None
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
    preview_text_b: Optional[str] = None
    html_body_a: Optional[str] = None
    html_body_b: Optional[str] = None
    is_ab_test: Optional[bool] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    actual_spend: Optional[float] = None
    
    class Config:
        extra = "ignore"

class CampaignTest(BaseModel):
    email: Optional[str] = None
    segment_id: Optional[str] = None
    force_external_test: Optional[bool] = False
    subject_a: Optional[str] = None
    subject_b: Optional[str] = None
    preview_text: Optional[str] = None
    preview_text_b: Optional[str] = None
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
async def get_marketing_audit_logs(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    q: Optional[str] = None,
    admin: dict = Depends(verify_token)
):
    """Fetches the audit log of all marketing actions for the dashboard with pagination and filtering."""
    db = get_db()
    query = db.table("activity_log").select("*, admins(full_name)")
    
    # Filter to marketing actions
    query = query.ilike("event_type", "marketing_%")
    
    # Apply category filter
    if category:
        if category == "campaign":
            query = query.ilike("event_type", "marketing_campaign_%")
        elif category == "contact":
            query = query.or_("event_type.ilike.marketing_contact%,event_type.ilike.marketing_contacts%,event_type.ilike.marketing_bulk%")
        elif category == "segment":
            query = query.ilike("event_type", "marketing_segment_%")
        elif category == "quota":
            query = query.or_("event_type.ilike.%quota%,event_type.ilike.%settings%")
        elif category == "sequence":
            query = query.ilike("event_type", "marketing_sequence_%")
            
    # Apply search filter
    if q:
        query = query.or_(f"description.ilike.%{q}%,event_type.ilike.%{q}%")
        
    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    res = await db_execute(lambda: query.execute())
    
    logs = []
    for item in (res.data or []):
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
        
        if data.preview_text_b: campaign["preview_text"] = data.preview_text_b
        elif campaign.get("preview_text_b"): campaign["preview_text"] = campaign["preview_text_b"]
    else:
        if data.subject_a: campaign["subject_a"] = data.subject_a
        if data.html_body_a: campaign["html_body_a"] = data.html_body_a
        if data.preview_text: campaign["preview_text"] = data.preview_text
    
    recipients_list = []
    preview_note = ""
    target_desc = ""

    if data.segment_id:
        from marketing_service import resolve_target_recipients
        contacts = await resolve_target_recipients([data.segment_id], None)
        if not contacts:
            raise HTTPException(status_code=400, detail="Selected segment has no recipients.")
        
        # SAFETY BLOCK: Prevent sending test segment emails to real clients unless forced
        if not data.force_external_test:
            allowed_domains = ["eximps-cloves.com", "resend.dev", "smartymetrics.com"]
            allowed_emails = ["chkscaleb.ifeanyi@outlook.com", "eximpcloves@gmail.com", "smartymetric@gmail.com"]
            
            external_contacts = []
            for c in contacts:
                email = c.get("email", "").lower().strip()
                domain = email.split("@")[-1] if "@" in email else ""
                if domain not in allowed_domains and email not in allowed_emails:
                    external_contacts.append(email)
            if external_contacts:
                raise HTTPException(
                    status_code=403,
                    detail=f"Safety Block: Test segment send contains {len(external_contacts)} external contact(s) (e.g. {external_contacts[0]}). "
                           f"To prevent accidental spam, test segment sends containing external clients are blocked. "
                           f"Please check the safety override option to proceed."
                )

        recipients_list = contacts
        target_desc = f"segment '{data.segment_id}' ({len(contacts)} contacts)"
        preview_note = f"segment send"
    elif data.email:
        # Look up the real contact by email so all tags (first_name, financial, etc.) resolve
        # exactly as they would in a real campaign send.
        contact_res = await db_execute(lambda: db.table("marketing_contacts").select("*").eq("email", data.email.strip().lower()).limit(1).execute())
        if contact_res.data:
            # Real contact found — use their full record so every tag personalises correctly
            contact = contact_res.data[0]
            # Force the send through even if they are unsubscribed (it's a test, not a broadcast)
            contact = {**contact, "is_subscribed": True}
            preview_note = "with real contact data"
        else:
            # No contact found for this email — fall back to a clearly-labelled placeholder
            # so the tester knows tags won't be fully resolved
            contact = {
                "id": "test-id",
                "first_name": "[First Name]",
                "last_name": "[Last Name]",
                "email": data.email,
                "phone": "[Phone]",
                "is_subscribed": True,
            }
            preview_note = "no contact found for this email — tag values are placeholders"
        recipients_list = [contact]
        target_desc = f"'{data.email}'"
    else:
        raise HTTPException(status_code=400, detail="Either email or segment_id must be provided.")

    sent_count = 0
    for contact in recipients_list:
        success = await send_marketing_email(campaign, contact)
        if success:
            sent_count += 1

    if sent_count > 0:
        await log_activity(
            "marketing_campaign_test_sent",
            f"Test email (Variant {data.variant}) sent to {target_desc} for campaign '{campaign.get('name', id)}'.",
            current_admin["sub"]
        )
        return {"message": f"Test email (Variant {data.variant}) sent to {sent_count} recipient(s) ({preview_note})"}
    
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
    has_targets = target and (target.segment_ids or target.manual_emails)
    if not has_targets:
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
            
            await db_execute(lambda: db.table("email_campaigns").update({
                "status": "scheduled",
                "scheduled_for": target.scheduled_at,
                "target_config": target.dict(exclude={'scheduled_at'})
            }).eq("id", id).execute())

            await log_activity(
                "marketing_campaign_scheduled",
                f"Campaign '{id}' scheduled for {target.scheduled_at}.",
                current_admin["sub"]
            )
            return {"message": f"Broadcast scheduled for {target.scheduled_at}"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

    # Mark as sending (about to send immediately)
    await db_execute(lambda: db.table("email_campaigns").update({
        "status": "sending",
        "scheduled_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute())

    background_tasks.add_task(broadcast_campaign, id, target.segment_ids if target else None, target.manual_emails if target else None)
    
    # Fetch campaign name for a more descriptive log
    camp_name_res = await db_execute(lambda: db.table("email_campaigns").select("name").eq("id", id).execute())
    camp_name = camp_name_res.data[0].get("name", id) if camp_name_res.data else id

    # Estimate recipient count
    estimated_count = 0
    if target and target.segment_ids:
        for sid in target.segment_ids:
            count_res = await db_execute(lambda: db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True).execute())
            estimated_count += count_res.count or 0
    elif target and target.manual_emails:
        estimated_count = len(target.manual_emails)

    await log_activity(
        "marketing_campaign_broadcast_started",
        f"Broadcast initiated for campaign '{camp_name}' targeting {estimated_count} estimated recipient(s).",
        current_admin["sub"]
    )
    
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

    # Fetch campaign name for a descriptive log
    paused_res = await db_execute(lambda: db.table("email_campaigns").select("name, total_sent, total_recipients").eq("id", id).execute())
    camp_name = paused_res.data[0].get("name", id) if paused_res.data else id
    sent_so_far = paused_res.data[0].get("total_sent", "?") if paused_res.data else "?"
    total = paused_res.data[0].get("total_recipients", "?") if paused_res.data else "?"

    await log_activity(
        "marketing_campaign_paused",
        f"Campaign '{camp_name}' paused mid-send ({sent_so_far}/{total} sent so far).",
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

    # Fetch campaign name for a descriptive log
    resumed_res = await db_execute(lambda: db.table("email_campaigns").select("name").eq("id", id).execute())
    camp_name = resumed_res.data[0].get("name", id) if resumed_res.data else id
    
    await log_activity(
        "marketing_campaign_resumed",
        f"Campaign '{camp_name}' resumed. {pending_count} recipient(s) still pending.",
        current_admin["sub"]
    )
    return {"message": f"Campaign resumed. {pending_count} recipients remaining.", "pending": pending_count}

@router.post("/{id}/sync")
async def sync_campaign_stats(id: str, current_admin=Depends(verify_token)):
    """Manually recalculates stats for a campaign from the recipients table.
    Also corrects total_sent and total_recipients to reflect actual deliveries only."""
    db = get_db()
    
    # 1. Count actual delivered emails (Resend webhook sets 'delivered' after confirming delivery;
    #    the broadcast loop sets 'sent' but webhooks overwrite it with 'delivered'.)
    sent_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "delivered").execute())
    actual_sent = sent_res.count or 0

    # 2. Count variant A and B delivered
    sent_a_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "delivered").eq("variant", "A").execute())
    sent_b_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "delivered").eq("variant", "B").execute())
    variant_a_sent = sent_a_res.count or 0
    variant_b_sent = sent_b_res.count or 0

    # 3. Mark any stuck "pending" rows for suppressed-domain emails as "skipped"
    pending_res = await db_execute(lambda: db.table("campaign_recipients")\
        .select("id, contact_id, marketing_contacts(email)")\
        .eq("campaign_id", id).eq("status", "pending").execute())
    from marketing_service import SUPPRESSED_DOMAINS
    skipped_at = datetime.utcnow().isoformat()
    for row in (pending_res.data or []):
        contact_email = ""
        contact_data = row.get("marketing_contacts")
        if isinstance(contact_data, dict):
            contact_email = (contact_data.get("email") or "").lower()
        elif isinstance(contact_data, list) and contact_data:
            contact_email = (contact_data[0].get("email") or "").lower()
        if any(d in contact_email for d in SUPPRESSED_DOMAINS):
            await db_execute(lambda: db.table("campaign_recipients").update({
                "status": "failed", "failed_at": skipped_at
            }).eq("id", row["id"]).execute())
    
    # 4. Count Opens (unique contacts who opened)
    opens_res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id", count="exact").eq("campaign_id", id).not_.is_("opened_at", "null").execute())
    total_opens = opens_res.count or 0
    
    # 5. Count Clicks (unique contacts who clicked)
    clicks_res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id", count="exact").eq("campaign_id", id).not_.is_("clicked_at", "null").execute())
    total_clicks = clicks_res.count or 0
    
    # 6. Count Attributed revenue (sum of amount_paid of non-voided invoices linked to this campaign)
    revenue_res = await db_execute(lambda: db.table("invoices").select("amount_paid").eq("marketing_campaign_id", id).neq("status", "voided").execute())
    total_revenue = sum([i["amount_paid"] for i in revenue_res.data]) if revenue_res.data else 0
    
    # 7. Update Campaign Table with corrected counts
    db.table("email_campaigns").update({
        "total_sent": actual_sent,
        "total_recipients": actual_sent,
        "variant_a_sent": variant_a_sent,
        "variant_b_sent": variant_b_sent,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "attributed_revenue": total_revenue,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", id).execute()
    
    camp_name_sync = (await db_execute(lambda: db.table("email_campaigns").select("name").eq("id", id).execute())).data
    name_label = camp_name_sync[0].get("name", id) if camp_name_sync else id
    await log_activity(
        "marketing_campaign_stats_synced",
        f"Stats manually re-synced for campaign '{name_label}': {actual_sent} delivered, {total_opens} opens, {total_clicks} clicks.",
        current_admin["sub"]
    )

    return {
        "id": id,
        "total_sent": actual_sent,
        "total_recipients": actual_sent,
        "variant_a_sent": variant_a_sent,
        "variant_b_sent": variant_b_sent,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "attributed_revenue": total_revenue
    }
    


@router.post("/{id}/reset-failed-recipients")
async def reset_failed_recipients(id: str, current_admin=Depends(verify_token)):
    """Clears all 'failed' recipient records for a campaign so they can be retried.
    Use this when contacts were incorrectly marked failed due to a system crash (not a real email bounce)."""
    db = get_db()
    res = await db_execute(lambda: db.table("email_campaigns").select("status, name").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await db_execute(lambda: db.table("campaign_recipients")
        .delete().eq("campaign_id", id).eq("status", "failed").execute())

    cleared = len(result.data) if result.data else 0

    await log_activity(
        "marketing_campaign_failed_recipients_cleared",
        f"Cleared {cleared} failed recipient record(s) from campaign '{res.data[0].get('name', id)}'.",
        current_admin["sub"]
    )
    return {"message": f"Cleared {cleared} failed recipient record(s). Those contacts can now receive this campaign again.", "cleared": cleared}

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
async def duplicate_campaign(
    id: str,
    name: Optional[str] = Query(None),
    current_admin=Depends(verify_token)
):
    """Creates a new draft copy of an existing campaign with an optional custom name."""
    db = get_db()
    
    # 1. Fetch source
    res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    source = res.data[0]
    
    # 2. Create copy data using safe fallbacks for NULLs and missing keys
    copy_name = name.strip() if name and name.strip() else f"{source.get('name') or 'Untitled Campaign'} (Copy)"
    copy_data = {
        "name": copy_name,
        "subject_a": source.get("subject_a") or "",
        "subject_b": source.get("subject_b"),
        "preview_text": source.get("preview_text") or "",
        "preview_text_b": source.get("preview_text_b"),
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
    
    status_text = 'enabled' if enabled else 'disabled'
    await log_activity(
        "marketing_quota_settings_updated",
        f"Daily email quota {status_text}. Limit set to {limit} emails/day.",
        current_admin["sub"]
    )
    return {"message": "Marketing quota settings updated.", "settings": new_value}


def generate_animated_gif(image_bytes_list, duration=1500):
    frames = []
    target_size = (600, 400)
    for img_bytes in image_bytes_list:
        try:
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert('RGBA')
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Create a centered transparent/white canvas
            background = Image.new('RGBA', target_size, (255, 255, 255, 0))
            offset = ((target_size[0] - img.size[0]) // 2, (target_size[1] - img.size[1]) // 2)
            background.paste(img, offset, img)
            frames.append(background.convert('RGB'))
        except Exception as e:
            print(f"Skipping frame generation for a file: {e}")
            continue

    if not frames:
        return None

    out = io.BytesIO()
    # Save GIF with looping enabled
    frames[0].save(out, format='GIF', save_all=True, append_images=frames[1:], duration=duration, loop=0)
    out.seek(0)
    return out.getvalue()


@router.post("/assets/generate-gif")
async def generate_gif_route(files: List[UploadFile] = File(...), duration: int = 1500, current_admin=Depends(verify_token)):
    image_bytes_list = []
    for file in files:
        content = await file.read()
        image_bytes_list.append(content)
        
    gif_data = generate_animated_gif(image_bytes_list, duration=duration)
    if not gif_data:
        raise HTTPException(status_code=400, detail="No valid images were provided to build a GIF.")
    
    # Upload to Supabase bucket
    file_name = f"carousel_{int(time.time())}.gif"
    try:
        supabase.storage.from_("marketing").upload(
            path=file_name,
            file=gif_data,
            file_options={"content-type": "image/gif"}
        )
        # Get public url
        public_url = supabase.storage.from_("marketing").get_public_url(file_name)
        return {"url": public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save generated GIF to storage: {str(e)}")


@router.post("/{id}/resend")
async def resend_failed_campaign_emails(
    id: str,
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    """Resets failed recipient statuses to pending and resumes broadcasting them."""
    db = get_db()
    
    # 1. Fetch Campaign
    camp_res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    campaign = camp_res.data[0]
    if campaign["status"] not in ["sent", "failed"]:
        raise HTTPException(status_code=400, detail="Only completed sent or failed campaigns can be resent to undelivered contacts.")
        
    # 2. Find failed and pending recipient records along with their email addresses
    recs_res = await db_execute(lambda: db.table("campaign_recipients").select("id, contact_id, status, marketing_contacts(email)").eq("campaign_id", id).in_("status", ["failed", "pending"]).execute())
    
    from marketing_service import SUPPRESSED_DOMAINS
    
    valid_failed_ids = []
    pending_count = 0
    
    for r in (recs_res.data or []):
        contact = r.get("marketing_contacts") or {}
        email = (contact.get("email") or "").lower().strip()
        is_supp = any(d in email for d in SUPPRESSED_DOMAINS)
        if not is_supp:
            if r["status"] == "failed":
                valid_failed_ids.append(r["id"])
            elif r["status"] == "pending":
                pending_count += 1
            
    total_resend_count = len(valid_failed_ids) + pending_count
    if total_resend_count == 0:
        raise HTTPException(status_code=400, detail="No valid (non-suppressed) failed or pending recipients found for this campaign.")
        
    # 3. Reset failed rows back to pending if any exist
    if valid_failed_ids:
        batch_size = 100
        for i in range(0, len(valid_failed_ids), batch_size):
            batch_ids = valid_failed_ids[i:i+batch_size]
            await db_execute(lambda: db.table("campaign_recipients").update({
                "status": "pending",
                "failed_at": None
            }).in_("id", batch_ids).execute())
    
    # 4. Set campaign status back to sending
    await db_execute(lambda: db.table("email_campaigns").update({
        "status": "sending"
    }).eq("id", id).execute())
    
    # 5. Trigger background broadcast job
    background_tasks.add_task(broadcast_campaign, id, None, None)
    
    await log_activity(
        "marketing_campaign_resend_initiated",
        f"Resending/resuming campaign '{campaign.get('name', id)}' for {total_resend_count} recipient(s).",
        current_admin["sub"]
    )
    
    return {"message": f"Resend initiated for {total_resend_count} recipient(s) in the background.", "total_resend_count": total_resend_count}


@router.post("/{id}/resend-single")
async def resend_campaign_to_single_recipient(
    id: str,
    contact_id: str = Query(...),
    current_admin=Depends(verify_token)
):
    """Resends a campaign to a single recipient."""
    db = get_db()
    
    # 1. Fetch Campaign
    camp_res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = camp_res.data[0]
    
    # 2. Fetch Contact
    contact_res = await db_execute(lambda: db.table("marketing_contacts").select("*").eq("id", contact_id).execute())
    if not contact_res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact = contact_res.data[0]
    
    # 3. Check if contact is suppressed
    from marketing_service import is_suppressed, send_marketing_email
    if is_suppressed(contact):
        raise HTTPException(status_code=400, detail="Cannot send to a suppressed domain contact.")
        
    # 4. Check or create recipient record
    rec_res = await db_execute(lambda: db.table("campaign_recipients").select("*").eq("campaign_id", id).eq("contact_id", contact_id).execute())
    
    # Determine variant to use (if existing record exists, use that variant; otherwise assign one)
    variant_label = "A"
    if rec_res.data:
        variant_label = rec_res.data[0].get("variant") or "A"
    else:
        # Determine variant randomly if A/B
        import random
        if campaign.get("is_ab_test") and campaign.get("subject_b") and campaign.get("html_body_b"):
            variant_label = random.choice(["A", "B"])
        else:
            variant_label = "A"
        
    # 5. Send email
    # Customize campaign body/subject if variant is B
    camp_copy = dict(campaign)
    if variant_label == "B" and campaign.get("is_ab_test"):
        if campaign.get("subject_b"):
            camp_copy["subject_a"] = campaign["subject_b"]
        if campaign.get("html_body_b"):
            camp_copy["html_body_a"] = campaign["html_body_b"]
        if campaign.get("preview_text_b"):
            camp_copy["preview_text"] = campaign["preview_text_b"]
            
    success = await send_marketing_email(camp_copy, contact)
    if not success:
        # Update or insert status as failed
        update_payload = {
            "campaign_id": id,
            "contact_id": contact_id,
            "status": "failed",
            "variant": variant_label,
            "failed_at": datetime.utcnow().isoformat()
        }
        if rec_res.data:
            await db_execute(lambda: db.table("campaign_recipients").update(update_payload).eq("id", rec_res.data[0]["id"]).execute())
        else:
            await db_execute(lambda: db.table("campaign_recipients").insert(update_payload).execute())
        raise HTTPException(status_code=500, detail="Mail delivery failed.")
        
    # On success: update or insert status as sent
    update_payload = {
        "campaign_id": id,
        "contact_id": contact_id,
        "status": "sent",  # Initial status for successfully sent but webhook pending
        "variant": variant_label,
        "sent_at": datetime.utcnow().isoformat(),
        "failed_at": None
    }
    if rec_res.data:
        await db_execute(lambda: db.table("campaign_recipients").update(update_payload).eq("id", rec_res.data[0]["id"]).execute())
    else:
        await db_execute(lambda: db.table("campaign_recipients").insert(update_payload).execute())
        
    # Update aggregates on campaign
    delivered_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "delivered").execute())
    actual_delivered = delivered_res.count or 0
    
    delivered_a_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "delivered").eq("variant", "A").execute())
    variant_a = delivered_a_res.count or 0
    
    delivered_b_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).eq("status", "delivered").eq("variant", "B").execute())
    variant_b = delivered_b_res.count or 0
    
    total_recs_res = await db_execute(lambda: db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", id).execute())
    total_remaining = total_recs_res.count or 0
    
    await db_execute(lambda: db.table("email_campaigns").update({
        "total_sent": actual_delivered,
        "total_recipients": total_remaining,
        "variant_a_sent": variant_a,
        "variant_b_sent": variant_b
    }).eq("id", id).execute())
    
    await log_activity(
        "marketing_campaign_single_resend",
        f"Resent campaign '{campaign.get('name', id)}' to contact {contact.get('email')}.",
        current_admin["sub"]
    )
    
    return {"message": "Email sent successfully to single recipient.", "status": "sent"}


@router.get("/contacts/suppressed-list")
async def get_suppressed_contacts(
    search: Optional[str] = Query(None),
    current_admin=Depends(verify_token)
):
    """Returns a list of all bounced, unsubscribed, and placeholder suppressed contacts."""
    db = get_db()
    
    # Fetch contacts
    query = db.table("marketing_contacts").select("id, first_name, last_name, email, is_bounced, is_subscribed, created_at, source")
    res = await db_execute(lambda: query.execute())
    contacts = res.data or []
    
    from marketing_service import SUPPRESSED_DOMAINS
    
    suppressed_list = []
    for c in contacts:
        email = (c.get("email") or "").lower().strip()
        is_supp_domain = any(d in email for d in SUPPRESSED_DOMAINS)
        is_bounced = bool(c.get("is_bounced"))
        is_unsub = not bool(c.get("is_subscribed"))
        
        if is_supp_domain or is_bounced or is_unsub:
            reasons = []
            if is_supp_domain:
                reasons.append("Suppressed Domain")
            if is_bounced:
                reasons.append("Hard Bounce")
            if is_unsub:
                reasons.append("Unsubscribed")
                
            c["suppression_reasons"] = reasons
            
            if search:
                term = search.lower()
                name = f"{c.get('first_name') or ''} {c.get('last_name') or ''}".lower()
                if term not in email and term not in name:
                    continue
                    
            suppressed_list.append(c)
            
    suppressed_list.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return suppressed_list


@router.post("/contacts/{contact_id}/remove-suppression")
async def remove_contact_suppression(
    contact_id: str,
    current_admin=Depends(verify_token)
):
    """Resets the bounce and subscription flags for a contact to allow re-mailing."""
    db = get_db()
    
    contact_res = await db_execute(lambda: db.table("marketing_contacts").select("id, email").eq("id", contact_id).execute())
    if not contact_res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    contact = contact_res.data[0]
    email = (contact.get("email") or "").lower().strip()
    
    from marketing_service import SUPPRESSED_DOMAINS
    if any(d in email for d in SUPPRESSED_DOMAINS):
         raise HTTPException(status_code=400, detail="Cannot remove suppression for a placeholder domain email address.")
         
    await db_execute(lambda: db.table("marketing_contacts").update({
        "is_bounced": False,
        "is_subscribed": True,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", contact_id).execute())
    
    await log_activity(
        "marketing_contact_suppression_removed",
        f"Suppression removed for contact '{email}'.",
        current_admin["sub"]
    )
    
    return {"message": f"Suppression restriction removed for {email}."}