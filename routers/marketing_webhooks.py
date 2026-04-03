from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Optional
from database import get_db
from datetime import datetime
import os
import logging
import json
import io

router = APIRouter()
logger = logging.getLogger(__name__)

# Webhook Secret from Resend
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET")

@router.post("/api/marketing/webhooks/resend")
async def resend_webhook(request: Request):
    """Handle incoming webhooks from Resend."""
    # TODO: Verify Signature using RESEND_WEBHOOK_SECRET
    # signature = request.headers.get("resend-signature")
    # For now, we'll log it.
    
    payload = await request.json()
    event_type = payload.get("type")
    data = payload.get("data", {})
    message_id = data.get("email_id")
    
    db = get_db()
    
    if event_type == "email.delivered":
        db.table("campaign_recipients").update({
            "status": "delivered",
            "delivered_at": datetime.utcnow().isoformat()
        }).eq("resend_message_id", message_id).execute()
        
    elif event_type == "email.opened":
        # Increment open count and update engagement score
        res = db.table("campaign_recipients").select("id, contact_id, open_count").eq("resend_message_id", message_id).execute()
        if res.data:
            rec = res.data[0]
            new_count = (rec.get("open_count") or 0) + 1
            db.table("campaign_recipients").update({
                "open_count": new_count,
                "opened_at": rec.get("opened_at") or datetime.utcnow().isoformat(),
                "last_opened_at": datetime.utcnow().isoformat()
            }).eq("id", rec["id"]).execute()
            
            # Update contact engagement (PRD 3.4)
            db.rpc("increment_engagement_score", {"cid": rec["contact_id"], "amount": 5}).execute()
            
            # Increment total opens for campaign and contact
            campaign_id = db.table("campaign_recipients").select("campaign_id").eq("id", rec["id"]).execute().data[0]["campaign_id"]
            db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "open"}).execute()
            db.rpc("increment_contact_stats", {"cont_id": rec["contact_id"], "event_type": "open"}).execute()

    elif event_type == "email.clicked":
        # Similar logic for clicks
        res = db.table("campaign_recipients").select("id, contact_id, click_count").eq("resend_message_id", message_id).execute()
        if res.data:
            rec = res.data[0]
            db.table("campaign_recipients").update({
                "click_count": (rec.get("click_count") or 0) + 1,
                "clicked_at": rec.get("clicked_at") or datetime.utcnow().isoformat(),
                "last_clicked_at": datetime.utcnow().isoformat()
            }).eq("id", rec["id"]).execute()
            db.rpc("increment_engagement_score", {"cid": rec["contact_id"], "amount": 10}).execute()
            
            # Increment total clicks for campaign and contact
            campaign_id = db.table("campaign_recipients").select("campaign_id").eq("id", rec["id"]).execute().data[0]["campaign_id"]
            db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "click"}).execute()
            db.rpc("increment_contact_stats", {"cont_id": rec["contact_id"], "event_type": "click"}).execute()

    elif event_type == "email.bounced":
        db.table("campaign_recipients").update({"status": "bounced"}).eq("resend_message_id", message_id).execute()
        # Suppress contact
        res = db.table("campaign_recipients").select("contact_id").eq("resend_message_id", message_id).execute()
        if res.data:
            db.table("marketing_contacts").update({
                "is_subscribed": False,
                "is_bounced": True,
                "bounced_at": datetime.utcnow().isoformat()
            }).eq("id", res.data[0]["contact_id"]).execute()

    elif event_type == "email.unsubscribed":
        res = db.table("campaign_recipients").select("contact_id").eq("resend_message_id", message_id).execute()
        if res.data:
            contact_id = res.data[0]["contact_id"]
            db.table("marketing_contacts").update({
                "is_subscribed": False,
                "unsubscribed_at": datetime.utcnow().isoformat()
            }).eq("id", contact_id).execute()
            
            db.table("marketing_unsubscribes").insert({
                "contact_id": contact_id,
                "email": data.get("to", ""),
                "reason": "Unsubscribed via Resend"
            }).execute()

    return {"status": "ok"}

@router.get("/o/{campaign_id}/{contact_id}/{pixel_id}.png")
async def tracking_pixel(campaign_id: str, contact_id: str):
    """Serve a 1x1 transparent tracking pixel and log the open."""
    db = get_db()
    # Log open event directly from pixel (as a fallback or primary measurement)
    # We update the first and last opened timestamps
    db.table("campaign_recipients").update({
        "last_opened_at": datetime.utcnow().isoformat(),
        # opened_at is handled by COALESCE logic in a real app or just by checking if null
    }).eq("campaign_id", campaign_id).eq("contact_id", contact_id).execute()
    
    # Increment contact score
    db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 5}).execute()
    
    # Increment total opens for campaign and contact
    db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "open"}).execute()
    db.rpc("increment_contact_stats", {"cont_id": contact_id, "event_type": "open"}).execute()
    
    # Return a 1x1 transparent PNG
    pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=pixel_data, media_type="image/png")

@router.get("/c/{campaign_id}/{contact_id}")
async def click_tracking(campaign_id: str, contact_id: str, url: str, request: Request):
    """Log the click event and redirect the user to the target URL."""
    db = get_db()
    
    # Log the click
    db.table("email_click_events").insert({
        "campaign_id": campaign_id,
        "contact_id": contact_id,
        "original_url": url,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }).execute()
    
    # Update recipient stats
    db.table("campaign_recipients").update({
        "last_clicked_at": datetime.utcnow().isoformat(),
        # click_count handled via RPC or simple update
    }).eq("campaign_id", campaign_id).eq("contact_id", contact_id).execute()
    
    # Update score
    db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 10}).execute()
    
    # Increment total clicks for campaign and contact
    db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "click"}).execute()
    db.rpc("increment_contact_stats", {"cont_id": contact_id, "event_type": "click"}).execute()
    
    return RedirectResponse(url=url)

@router.get("/unsubscribe/{token}")
async def confirm_unsubscribe(token: str):
    """Handle the public unsubscribe page."""
    # In a real app, 'token' would be a signed JWT or similar. 
    # For now we assume 'token' is the contact_id.
    db = get_db()
    db.table("marketing_contacts").update({
        "is_subscribed": False,
        "unsubscribed_at": datetime.utcnow().isoformat()
    }).eq("id", token).execute()
    
    # Return unsubscribe confirmation page
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
            <h2>You Have Been Unsubscribed</h2>
            <p>You will no longer receive marketing emails from Eximp & Cloves.</p>
            <p>You will still receive important transactional emails related to your property holdings.</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html)
