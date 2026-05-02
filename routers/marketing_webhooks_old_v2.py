from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from database import get_db, db_execute
from datetime import datetime
import os
import logging
import json
import io
import hmac
import hashlib

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

# Webhook Secret from Resend
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET")

@router.post("/api/marketing/webhooks/resend")
async def resend_webhook(request: Request):
    """Handle incoming webhooks from Resend."""
    # TASK 1: Verify Signature using RESEND_WEBHOOK_SECRET
    raw_body = await request.body()
    
    if RESEND_WEBHOOK_SECRET:
        signature_header = request.headers.get("svix-signature")
        if not signature_header:
            logger.warning("Missing svix-signature header")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        try:
            # Resend/Svix signature format: v1,<base64_hmac>
            # Actually, Resend uses svix-signature which has multiple parts.
            # But the PRD says: v1,<base64_hmac> and signed content is raw body.
            # Let's follow the PRD instructions exactly.
            parts = signature_header.split(",")
            if len(parts) < 2 or not parts[0] == "v1":
                raise ValueError("Invalid signature format")
            
            received_sig = parts[1]
            # PRD: Compute HMAC-SHA256 of the raw body using RESEND_WEBHOOK_SECRET
            # Note: Svix usually signs (msg_id + "." + timestamp + "." + body). 
            # But PRD says "signed content is the raw request body".
            expected_sig = hmac.new(
                RESEND_WEBHOOK_SECRET.encode(),
                raw_body,
                hashlib.sha256
            ).hexdigest()
            
            # Note: PRD says base64_hmac in header, but hexdigest is more common for webhooks.
            # However, if it's base64, I'd need to b64encode it.
            # Let's check common practices or just follow "Compare against the signature in the header"
            if not hmac.compare_digest(expected_sig, received_sig):
                # Try base64 version if hex fails? No, let's stick to PRD logic.
                import base64
                expected_sig_b64 = base64.b64encode(hmac.new(
                    RESEND_WEBHOOK_SECRET.encode(),
                    raw_body,
                    hashlib.sha256
                ).digest()).decode()
                
                if not hmac.compare_digest(expected_sig_b64, received_sig):
                    logger.warning("Invalid webhook signature")
                    raise HTTPException(status_code=401, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("RESEND_WEBHOOK_SECRET not set. Skipping signature verification.")

    payload = json.loads(raw_body)
    event_type = payload.get("type")
    data = payload.get("data", {})
    message_id = data.get("email_id")

    db = get_db()

    if event_type == "email.delivered":
        await db_execute(lambda: db.table("campaign_recipients").update({
            "status": "delivered",
            "delivered_at": datetime.utcnow().isoformat()
        }).eq("resend_message_id", message_id).execute())

    elif event_type == "email.opened":
        # Increment open count and update engagement score
        res = await db_execute(lambda: db.table("campaign_recipients").select("id, contact_id, open_count, variant").eq("resend_message_id", message_id).execute())
        if res.data:
            rec = res.data[0]
            new_count = (rec.get("open_count") or 0) + 1
            await db_execute(lambda: db.table("campaign_recipients").update({
                "open_count": new_count,
                "opened_at": rec.get("opened_at") or datetime.utcnow().isoformat(),
                "last_opened_at": datetime.utcnow().isoformat()
            }).eq("id", rec["id"]).execute())

            # Update contact engagement (PRD 3.4)
            await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": rec["contact_id"], "amount": 5}).execute())

            # Increment total opens for campaign and contact
            campaign_id = (await db_execute(lambda: db.table("campaign_recipients").select("campaign_id").eq("id", rec["id"]).execute())).data[0]["campaign_id"]
            
            # TASK 6: Update variant-specific opens
            variant = rec.get("variant", "A")
            v_col = "variant_a_opens" if variant == "A" else "variant_b_opens"
            
            # We use a combined RPC or multiple updates. For now, let's just do a direct update for the variant
            # (In high scale, an RPC is better to avoid race conditions, but this is fine for now)
            await db_execute(lambda: db.rpc("increment_campaign_variant_stats", {
                "camp_id": campaign_id, 
                "col_name": v_col
            }).execute())

            await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "open"}).execute())
            await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": rec["contact_id"], "event_type": "open"}).execute())

            # Closing the Loop: Attribution on Open (HubSpot Standard)
            await db_execute(lambda: db.table("marketing_contacts").update({
                "last_campaign_id": campaign_id,
                "last_interaction_at": datetime.utcnow().isoformat()
            }).eq("id", rec["contact_id"]).execute())

    elif event_type == "email.clicked":
        # Similar logic for clicks
        res = await db_execute(lambda: db.table("campaign_recipients").select("id, contact_id, click_count, variant").eq("resend_message_id", message_id).execute())
        if res.data:
            rec = res.data[0]
            await db_execute(lambda: db.table("campaign_recipients").update({
                "click_count": (rec.get("click_count") or 0) + 1,
                "clicked_at": rec.get("clicked_at") or datetime.utcnow().isoformat(),
                "last_clicked_at": datetime.utcnow().isoformat()
            }).eq("id", rec["id"]).execute())
            await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": rec["contact_id"], "amount": 10}).execute())

            # Increment total clicks for campaign and contact
            campaign_id = (await db_execute(lambda: db.table("campaign_recipients").select("campaign_id").eq("id", rec["id"]).execute())).data[0]["campaign_id"]
            
            # TASK 6: Update variant-specific clicks
            variant = rec.get("variant", "A")
            v_col = "variant_a_clicks" if variant == "A" else "variant_b_clicks"
            await db_execute(lambda: db.rpc("increment_campaign_variant_stats", {
                "camp_id": campaign_id, 
                "col_name": v_col
            }).execute())

            await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "click"}).execute())
            await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": rec["contact_id"], "event_type": "click"}).execute())

    elif event_type == "email.bounced":
        # TASK 10: Hard vs Soft Bounce Distinction
        bounce_type = data.get("bounce", {}).get("type", "hard")  # Resend returns "hard" or "soft"
        
        await db_execute(lambda: db.table("campaign_recipients").update({
            "status": "bounced"
        }).eq("resend_message_id", message_id).execute())
        
        res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id, bounce_count").eq("resend_message_id", message_id).execute())
        if res.data:
            contact_id = res.data[0]["contact_id"]
            bounce_count = (res.data[0].get("bounce_count") or 0) + 1
            
            if bounce_type == "hard":
                # Hard bounce: permanent suppression immediately
                await db_execute(lambda: db.table("marketing_contacts").update({
                    "is_subscribed": False,
                    "is_bounced": True,
                    "bounced_at": datetime.utcnow().isoformat()
                }).eq("id", contact_id).execute())
            else:
                # Soft bounce: only suppress after 3 attempts
                await db_execute(lambda: db.table("campaign_recipients").update({
                    "bounce_count": bounce_count
                }).eq("resend_message_id", message_id).execute())
                
                if bounce_count >= 3:
                    await db_execute(lambda: db.table("marketing_contacts").update({
                        "is_subscribed": False,
                        "is_bounced": True,
                        "bounced_at": datetime.utcnow().isoformat()
                    }).eq("id", contact_id).execute())

    elif event_type == "email.unsubscribed":
        res = await db_execute(lambda: db.table("campaign_recipients").select("contact_id").eq("resend_message_id", message_id).execute())
        if res.data:
            contact_id = res.data[0]["contact_id"]
            await db_execute(lambda: db.table("marketing_contacts").update({
                "is_subscribed": False,
                "unsubscribed_at": datetime.utcnow().isoformat()
            }).eq("id", contact_id).execute())

            await db_execute(lambda: db.table("marketing_unsubscribes").insert({
                "contact_id": contact_id,
                "email": data.get("to", ""),
                "reason": "Unsubscribed via Resend"
            }).execute())

    return {"status": "ok"}

@router.get("/o/{campaign_id}/{contact_id}/{pixel_id}.png")
async def tracking_pixel(campaign_id: str, contact_id: str):
    """Serve a 1x1 transparent tracking pixel and log the open."""
    db = get_db()
    # Log open event directly from pixel (as a fallback or primary measurement)
    # We update the first and last opened timestamps
    await db_execute(lambda: db.table("campaign_recipients").update({
        "last_opened_at": datetime.utcnow().isoformat(),
        # opened_at is handled by COALESCE logic in a real app or just by checking if null
    }).eq("campaign_id", campaign_id).eq("contact_id", contact_id).execute())

    # Increment contact score
    await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 5}).execute())

    # Increment total opens for campaign and contact
    await db_execute(lambda: db.rpc("increment_campaign_stats", {"camp_id": campaign_id, "event_type": "open"}).execute())
    await db_execute(lambda: db.rpc("increment_contact_stats", {"cont_id": contact_id, "event_type": "open"}).execute())

    # Closing the Loop: Attribution on Pixel Open
    await db_execute(lambda: db.table("marketing_contacts").update({
        "last_campaign_id": campaign_id,
        "last_interaction_at": datetime.utcnow().isoformat()
    }).eq("id", contact_id).execute())

    # Return a 1x1 transparent PNG
    pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=pixel_data, media_type="image/png")

@router.get("/c/{campaign_id}/{contact_id}")
async def click_tracking(campaign_id: str, contact_id: str, url: str, request: Request):
    """Log the click event, handle auto-tagging, and redirect."""
    db = get_db()

    # 1. Log the click event
    await db_execute(lambda: db.table("email_click_events").insert({
        "campaign_id": campaign_id,
        "contact_id": contact_id,
        "original_url": url,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }).execute())

    # 2. Update recipient status & scoring
    await db_execute(lambda: db.table("campaign_recipients").update({
        "last_clicked_at": datetime.utcnow().isoformat(),
        # click_count handled via RPC or simple update
    }).eq("campaign_id", campaign_id).eq("contact_id", contact_id).execute())

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
        await db_execute(lambda: db.table("marketing_contacts").update({
            "last_campaign_id": campaign_id,
            "last_interaction_at": datetime.utcnow().isoformat()
        }).eq("id", contact_id).execute())
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
        await db_execute(lambda: db.table("activity_log").insert({
            "event_type": "site_view",
            "description": f"Viewed listing: {title or url}",
            "client_id": None, # Non-client lead activity
            "metadata": {"url": url, "title": title}
        }).execute())

        # 2. Increment score (+2 for browsing)
        await db_execute(lambda: db.rpc("increment_engagement_score", {"cid": contact_id, "amount": 2}).execute())

        return {"status": "tracked"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/unsubscribe/{token}")
async def unsubscribe_page(token: str, request: Request):
    """Handle the public unsubscribe page with a survey."""
    db = get_db()

    # Verify contact exists
    res = await db_execute(lambda: db.table("marketing_contacts").select("first_name, email").eq("id", token).execute())
    contact = res.data[0] if res.data else None

    name = contact.get("first_name", "there") if contact else "there"
    email = contact.get("email", "") if contact else ""

    # TASK 7B: Return Jinja2 template
    return templates.TemplateResponse("unsubscribe.html", {
        "request": request,
        "name": name,
        "email": email,
        "token": token
    })

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
    await db_execute(lambda: db.table("marketing_contacts").update({
        "is_subscribed": False,
        "unsubscribed_at": timestamp,
        "unsubscribe_reason": f"{reason}: {feedback}" if feedback else reason
    }).eq("id", token).execute())

    # 2. Log to unsubscribe table (PRD 3.5)
    contact_res = await db_execute(lambda: db.table("marketing_contacts").select("email").eq("id", token).execute())
    if contact_res.data:
        await db_execute(lambda: db.table("marketing_unsubscribes").insert({
            "contact_id": token,
            "email": contact_res.data[0]["email"],
            "reason": reason,
            "unsubscribed_at": timestamp
        }).execute())

    # TASK 7B: Return success page via template
    return templates.TemplateResponse("unsubscribe_success.html", {"request": request})
