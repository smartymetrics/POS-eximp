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
        res = await db_execute(lambda: db.table("campaign_recipients").select("id, contact_id, open_count").eq("resend_message_id", message_id).execute())
        if res.data:
            rec = res.data[0]
            new_count = (rec.get("open_count") or 0) + 1
            db.table("campaign_recipients").update({
                "open_count": new_count,
                "opened_at": rec.get("opened_at") or datetime.utcnow().isoformat(),
                "last_opened_at": datetime.utcnow().isoformat()
            }).eq("id", rec["id"]).execute()
            
            # Update contact engagement (PRD 3.4)
            await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": rec["contact_id"], "amount": 5}).execute())
            
            # Increment total opens for campaign and contact
            campaign_id = (await db_execute(lambda: db.table("campaign_recipients").select("campaign_id").eq("id", rec["id"]).execute())).data[0]["campaign_id"]
            await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "open"}).execute())
            await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": rec["contact_id"], "event_type": "open"}).execute())
            
            # Closing the Loop: Attribution on Open (HubSpot Standard)
            db.table("marketing_contacts").update({
                "last_campaign_id": campaign_id,
                "last_interaction_at": datetime.utcnow().isoformat()
            }).eq("id", rec["contact_id"]).execute()

    elif event_type == "email.clicked":
        # Similar logic for clicks
        res = await db_execute(lambda: db.table("campaign_recipients").select("id, contact_id, click_count").eq("resend_message_id", message_id).execute())
        if res.data:
            rec = res.data[0]
            db.table("campaign_recipients").update({
                "click_count": (rec.get("click_count") or 0) + 1,
                "clicked_at": rec.get("clicked_at") or datetime.utcnow().isoformat(),
                "last_clicked_at": datetime.utcnow().isoformat()
            }).eq("id", rec["id"]).execute()
            await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": rec["contact_id"], "amount": 10}).execute())
            
            # Increment total clicks for campaign and contact
            campaign_id = (await db_execute(lambda: db.table("campaign_recipients").select("campaign_id").eq("id", rec["id"]).execute())).data[0]["campaign_id"]
            await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "click"}).execute())
            await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": rec["contact_id"], "event_type": "click"}).execute())

    elif event_type == "email.bounced":
        await db_execute(lambda: db.table("campaign_recipients").update({"status": "bounced"}).eq("resend_message_id", message_id).execute())
        # Suppress contact
        res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id").eq("resend_message_id", message_id).execute())
        if res.data:
            db.table("marketing_contacts").update({
                "is_subscribed": False,
                "is_bounced": True,
                "bounced_at": datetime.utcnow().isoformat()
            }).eq("id", res.data[0]["contact_id"]).execute()

    elif event_type == "email.unsubscribed":
        res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id").eq("resend_message_id", message_id).execute())
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
    await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 5}).execute())
    
    # Increment total opens for campaign and contact
    await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "open"}).execute())
    await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": contact_id, "event_type": "open"}).execute())
    
    # Closing the Loop: Attribution on Pixel Open
    db.table("marketing_contacts").update({
        "last_campaign_id": campaign_id,
        "last_interaction_at": datetime.utcnow().isoformat()
    }).eq("id", contact_id).execute()
    
    # Return a 1x1 transparent PNG
    pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=pixel_data, media_type="image/png")

@router.get("/c/{campaign_id}/{contact_id}")
async def click_tracking(campaign_id: str, contact_id: str, url: str, request: Request):
    """Log the click event, handle auto-tagging, and redirect."""
    db = get_db()
    
    # 1. Log the click event
    db.table("email_click_events").insert({
        "campaign_id": campaign_id,
        "contact_id": contact_id,
        "original_url": url,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }).execute()
    
    # 2. Update recipient status & scoring
    db.table("campaign_recipients").update({
        "last_clicked_at": datetime.utcnow().isoformat(),
        # click_count handled via RPC or simple update
    }).eq("campaign_id", campaign_id).eq("contact_id", contact_id).execute()
    
    # Update score (+10 for click)
    await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 10}).execute())
    
    # Update campaign/contact stats
    await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "click"}).execute())
    await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": contact_id, "event_type": "click"}).execute())

    # 3. INTEREST TAGGING (Industrial Grade)
    # Check if URL has a tag parameter (e.g. ?tag=Lekki)
    if "tag=" in url:
        try:
            # Simple tag extraction
            tag = url.split("tag=")[1].split("&")[0]
            # Fetch existing tags and append
            contact_res = await db_execute(lambda: db.table("marketing_contacts").select("tags").eq("id", contact_id).execute())
            if contact_res.data:
                tags = contact_res.data[0].get("tags") or []
                if tag not in tags:
                    tags.append(tag)
                    await db_execute(lambda: db.table("marketing_contacts").update({"tags": tags}).eq("id", contact_id).execute())
        except: pass
        
    # 4. REVENUE ATTRIBUTION TRACKING
    try:
        db.table("marketing_contacts").update({
            "last_campaign_id": campaign_id,
            "last_interaction_at": datetime.utcnow().isoformat()
        }).eq("id", contact_id).execute()
    except: pass

    return RedirectResponse(url=url)

@router.post("/api/marketing/track")
async def site_tracking(request: Request):
    """Deep Site Tracking endpoint for track.js."""
    try:
        payload = await request.json()
        contact_id = payload.get("contact_id")
        url = payload.get("url")
        title = payload.get("title")

        if not contact_id: return {"status": "ignored"}
        
        db = get_db()
        
        # 1. Log behavior in activity log
        db.table("activity_log").insert({
            "event_type": "site_view",
            "description": f"Viewed listing: {title or url}",
            "client_id": None, # Non-client lead activity
            "metadata": {"url": url, "title": title}
        }).execute()

        # 2. Increment score (+2 for browsing)
        await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 2}).execute())

        return {"status": "tracked"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_page(token: str):
    """Handle the public unsubscribe page with a survey."""
    db = get_db()
    
    # Verify contact exists
    res = await db_execute(lambda: db.table("marketing_contacts").select("first_name, email").eq("id", token).execute())
    contact = res.data[0] if res.data else None
    
    name = contact.get("first_name", "there") if contact else "there"
    email = contact.get("email", "") if contact else ""

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unsubscribe | Eximp & Cloves</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #f9fafb; color: #1f2937; margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }}
            .card {{ background: white; max-width: 440px; width: 100%; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; }}
            .logo {{ color: #C47D0A; font-weight: 700; font-size: 1.2rem; letter-spacing: 0.1em; display: block; margin-bottom: 30px; text-decoration: none; text-align: center; }}
            h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 12px; color: #111; text-align: center; }}
            p {{ font-size: 0.95rem; line-height: 1.6; color: #6b7280; margin-bottom: 24px; text-align: center; }}
            form {{ display: flex; flex-direction: column; gap: 12px; }}
            label {{ font-size: 0.85rem; font-weight: 600; color: #374151; }}
            select, textarea {{ padding: 12px; border-radius: 8px; border: 1px solid #d1d5db; outline: none; font-family: inherit; font-size: 0.9rem; }}
            select:focus, textarea:focus {{ border-color: #C47D0A; ring: 2px solid #C47D0A; }}
            button {{ background: #C47D0A; color: white; border: none; padding: 14px; border-radius: 8px; font-weight: 700; cursor: pointer; transition: 0.2s; margin-top: 10px; }}
            button:hover {{ background: #A66908; transform: translateY(-1px); }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 0.75rem; color: #9ca3af; }}
        </style>
    </head>
    <body>
        <div class="card">
            <a href="https://eximps-cloves.com" class="logo">EXIMP & CLOVES</a>
            <h1>We're sorry to see you go</h1>
            <p>Hi {name}, if you'd like to unsubscribe from our marketing emails ({email}), please confirm below.</p>
            
            <form action="/api/marketing/unsubscribe/confirm" method="POST">
                <input type="hidden" name="token" value="{token}">
                <label>Why are you leaving? (Optional)</label>
                <select name="reason">
                    <option value="too_many">Receiving too many emails</option>
                    <option value="not_relevant">Content isn't relevant to me</option>
                    <option value="bought_already">I've already purchased</option>
                    <option value="other">Other</option>
                </select>
                <textarea name="feedback" rows="3" placeholder="Any other feedback?"></textarea>
                <button type="submit">Unsubscribe Me</button>
            </form>
            
            <div class="footer">
                &copy; 2026 Eximp & Cloves Infrastructure Limited
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.post("/api/marketing/unsubscribe/confirm")
async def process_unsubscribe(request: Request):
    """Handle the unsubscribe confirmation and save the reason."""
    form_data = await request.form()
    token = form_data.get("token")
    reason = form_data.get("reason")
    feedback = form_data.get("feedback", "")
    
    if not token:
        raise HTTPException(status_code=400, detail="Missing unsubscribe token")
    
    db = get_db()
    
    # 1. Update contact global status
    timestamp = datetime.utcnow().isoformat()
    db.table("marketing_contacts").update({
        "is_subscribed": False,
        "unsubscribed_at": timestamp,
        "unsubscribe_reason": f"{reason}: {feedback}" if feedback else reason
    }).eq("id", token).execute()
    
    # 2. Log to unsubscribe table (PRD 3.5)
    contact_res = await db_execute(lambda: db.table("marketing_contacts").select("email").eq("id", token).execute())
    if contact_res.data:
        db.table("marketing_unsubscribes").insert({
            "contact_id": token,
            "email": contact_res.data[0]["email"],
            "reason": reason,
            "unsubscribed_at": timestamp
        }).execute()
    
    # Return success page
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Success | Eximp & Cloves</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #f9fafb; color: #1f2937; margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }}
            .card {{ background: white; max-width: 440px; width: 100%; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; text-align: center; }}
            .icon {{ font-size: 3rem; margin-bottom: 20px; }}
            h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 12px; color: #111; }}
            p {{ font-size: 0.95rem; line-height: 1.6; color: #6b7280; margin-bottom: 30px; }}
            .btn {{ display: inline-block; background: #111; color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h1>Successfully Unsubscribed</h1>
            <p>Your preferences have been updated. You will no longer receive marketing emails from us.</p>
            <a href="https://eximps-cloves.com" class="btn">Return to Site</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
