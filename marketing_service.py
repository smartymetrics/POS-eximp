import resend
import os
import re
import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import get_db

logger = logging.getLogger(__name__)

# Config
RESEND_API_KEY = os.getenv("RESEND_MARKETING_API_KEY") or os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

APP_BASE_URL = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com")
MARKETING_FROM_EMAIL = os.getenv("MARKETING_FROM_EMAIL", "hello@mail.eximps-cloves.com")
MARKETING_FROM_NAME = os.getenv("MARKETING_FROM_NAME", "Eximp & Cloves")
MARKETING_REPLY_TO = os.getenv("MARKETING_REPLY_TO", "marketing@mail.eximps-cloves.com")
MARKETING_BCC_EMAIL = os.getenv("MARKETING_BCC_EMAIL", "marketing@mail.eximps-cloves.com")

def personalize_content(html: str, contact: Dict[str, Any]) -> str:
    """Replaces {{variable}} with contact data."""
    unsub_token = contact.get("id") or "test-id"
    unsub_url = f"{APP_BASE_URL}/unsubscribe/{unsub_token}"

    vars = {
        "first_name": contact.get("first_name") or "there",
        "last_name": contact.get("last_name") or "",
        "full_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or "Valued Client",
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "unsubscribe_url": unsub_url
    }
    
    for key, val in vars.items():
        html = html.replace(f"{{{{{key}}}}}", str(val))
    
    # Clean up any unreplaced variables
    html = re.sub(r"\{\{.*?\}\}", "", html)
    return html

def wrap_links(html: str, campaign_id: str, contact_id: str) -> str:
    """Wraps all <a> tags with click tracking redirects."""
    def replace_link(match):
        url = match.group(2)
        # Skip mailto, tel, and anchors
        if url.startswith(("mailto:", "tel:", "#")):
            return match.group(0)
        
        # Avoid double wrapping or tracking the tracking links themselves
        if "/c/" in url:
            return match.group(0)

        tracking_url = f"{APP_BASE_URL}/c/{campaign_id}/{contact_id}?url={url}"
        return f'{match.group(1)}="{tracking_url}"'

    # Matches href="url" or href='url'
    return re.sub(r'(href)\s*=\s*["\'](.*?)["\']', replace_link, html)

def inject_tracking_pixel(html: str, campaign_id: str, contact_id: str) -> str:
    """Injects a 1x1 transparent tracking pixel before </body>."""
    pixel_id = str(uuid.uuid4())
    pixel_url = f"{APP_BASE_URL}/o/{campaign_id}/{contact_id}/{pixel_id}.png"
    pixel_tag = f'<img src="{pixel_url}" width="1" height="1" style="display:none !important;" />'
    
    if "</body>" in html:
        idx = html.rfind("</body>")
        return html[:idx] + pixel_tag + html[idx:]
    return html + pixel_tag

async def send_marketing_email(campaign: Dict[str, Any], contact: Dict[str, Any]):
    """Sends a single personalized marketing email with tracking."""
    campaign_id = campaign["id"]
    contact_id = contact["id"]
    
    # 1. Personalize
    html = personalize_content(campaign["html_body_a"], contact)
    
    # 2. Tracking (only for real campaigns, not tests)
    if campaign.get("status") != "test":
        html = wrap_links(html, campaign_id, contact_id)
        html = inject_tracking_pixel(html, campaign_id, contact_id)
        
        # Check for presence of "unsubscribe" in the HTML.
        # Use a more assertive check: if they have the {{unsubscribe_url}} tag OR the word unsubscribe in a link.
        has_unsubscribe = "unsubscribe" in html.lower()
        
        if not has_unsubscribe:
            unsub_token = contact.get("id") or "test-id"
            unsub_url = f"{APP_BASE_URL}/unsubscribe/{unsub_token}"
            unsub_footer = f'<div style="margin-top:40px; padding-top:20px; border-top:1px solid #eee; font-size:11px; color:#999; text-align:center;">' \
                           f'You are receiving this because you subscribed to Eximp & Cloves marketing. ' \
                           f'<a href="{unsub_url}" style="color:#C47D0A;">Unsubscribe here</a>.</div>'
            
            if "</body>" in html:
                idx = html.rfind("</body>")
                html = html[:idx] + unsub_footer + html[idx:]
            else:
                html += unsub_footer

    try:
        res = resend.Emails.send({
            "from": f"{MARKETING_FROM_NAME} <{MARKETING_FROM_EMAIL}>",
            "to": [contact["email"]],
            "subject": personalize_content(campaign["subject_a"], contact),
            "html": html,
            "reply_to": MARKETING_REPLY_TO,
            "bcc": [MARKETING_BCC_EMAIL] if MARKETING_BCC_EMAIL else []
        })
        
        # Log success in campaign_recipients if not test
        if campaign.get("status") != "test":
            db = get_db()
            db.table("campaign_recipients").upsert({
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "resend_message_id": res.get("id"),
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            }).execute()
            
        return res
    except Exception as e:
        logger.error(f"Error sending marketing email to {contact['email']}: {e}")
        if campaign.get("status") != "test":
            db = get_db()
            db.table("campaign_recipients").upsert({
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "status": "failed",
                "sent_at": datetime.utcnow().isoformat()
            }).execute()
        return None

def apply_segment_filters(query, rules: List[Dict[str, Any]]):
    """
    Applies JSON rules to a Supabase query object.
    Rule format: {"field": "status", "op": "eq", "val": "active"}
    """
    if not rules:
        return query

    for rule in rules:
        field = rule.get("field")
        op = rule.get("op")
        val = rule.get("val")

        if not field or not op:
            continue

        # Date-based relative logic
        if op == "in_last":
            try:
                days = int(val)
                limit = (datetime.utcnow() - timedelta(days=days)).isoformat()
                query = query.gte(field, limit)
                continue
            except: pass
        elif op == "older_than":
            try:
                days = int(val)
                limit = (datetime.utcnow() - timedelta(days=days)).isoformat()
                query = query.lt(field, limit)
                continue
            except: pass
        elif op == "exactly":
            try:
                days = int(val)
                start = (datetime.utcnow() - timedelta(days=days)).replace(hour=0, minute=0, second=0).isoformat()
                end = (datetime.utcnow() - timedelta(days=days-1)).replace(hour=0, minute=0, second=0).isoformat()
                query = query.gte(field, start).lt(field, end)
                continue
            except: pass

        # Behavioral Subqueries (Industrial Grade)
        if field == "has_opened":
            # Contacts who opened specific campaign (val is UUID) or ANY (val is 'any')
            if val == "any":
                query = query.filter("id", "in", "(select contact_id from campaign_recipients where opened_at is not null)")
            else:
                query = query.filter("id", "in", f"(select contact_id from campaign_recipients where campaign_id = '{val}' and opened_at is not null)")
            continue
        
        if field == "has_clicked":
            if val == "any":
                query = query.filter("id", "in", "(select contact_id from campaign_recipients where clicked_at is not null)")
            else:
                query = query.filter("id", "in", f"(select contact_id from campaign_recipients where campaign_id = '{val}' and clicked_at is not null)")
            continue

        if op == "eq":
            query = query.eq(field, val)
        elif op == "neq":
            query = query.neq(field, val)
        elif op == "gt":
            query = query.gt(field, val)
        elif op == "lt":
            query = query.lt(field, val)
        elif op == "gte":
            query = query.gte(field, val)
        elif op == "lte":
            query = query.lte(field, val)
        elif op == "contains":
            # For tags (array): use 'cs' (contains)
            if field == "tags":
                query = query.filter("tags", "cs", f"{{{val}}}") 
            else:
                query = query.ilike(field, f"%{val}%")
        elif op == "in":
            query = query.in_(field, val if isinstance(val, list) else [val])
        elif op == "is_null":
            query = query.is_(field, "null")
    return query

def get_financial_segment_contacts(segment_id: str) -> List[Dict[str, Any]]:
    """Resolves financial status from invoices and maps them to marketing contacts."""
    db = get_db()
    
    # 1. Fetch active invoices with client details
    invoices_res = db.table("invoices")\
        .select("amount, amount_paid, due_date, status, clients(email)")\
        .neq("status", "voided")\
        .execute()
        
    invoices = invoices_res.data or []
    
    client_financials = {}
    today = datetime.utcnow().date().isoformat()
    
    # 2. Aggregate per-client financial state
    for inv in invoices:
        client = inv.get("clients")
        if not client: continue
        email = client.get("email")
        if not email: continue
        
        email = email.lower().strip()
        if email not in client_financials:
            client_financials[email] = {
                "total_invoiced": 0,
                "total_paid": 0,
                "has_overdue": False
            }
        
        amount = float(inv.get("amount") or 0)
        paid = float(inv.get("amount_paid") or 0)
        due_date = inv.get("due_date", "")
        
        client_financials[email]["total_invoiced"] += amount
        client_financials[email]["total_paid"] += paid
        
        if paid < amount and due_date and due_date < today:
            client_financials[email]["has_overdue"] = True
            
    # 3. Filter matched emails based on requested segment
    target_emails = []
    for email, stats in client_financials.items():
        outstanding = stats["total_invoiced"] - stats["total_paid"]
        
        if segment_id == "financial_overdue" and stats["has_overdue"]:
            target_emails.append(email)
        elif segment_id == "financial_outstanding" and outstanding > 0:
            target_emails.append(email)
        elif segment_id == "financial_paid_fully" and outstanding <= 0 and stats["total_invoiced"] > 0:
            target_emails.append(email)
            
    if not target_emails:
        return []
        
    # 4. Fetch the actual marketing_contacts for these emails
    contacts_res = db.table("marketing_contacts").select("*").in_("email", target_emails).eq("is_subscribed", True).execute()
    return contacts_res.data or []

async def resolve_target_recipients(segment_ids: List[str] = None, manual_emails: List[str] = None) -> List[Dict[str, Any]]:
    """Resolves a list of contacts based on segments or specific emails."""
    db = get_db()
    
    # Priority 1: Manual Emails (specific manual reach-out)
    if manual_emails:
        # 1. Clean and normalize emails
        clean_emails = list(set([e.strip().lower() for e in manual_emails if e.strip()]))
        if not clean_emails:
            return []

        # 2. Find existing contacts
        existing_res = db.table("marketing_contacts").select("*").in_("email", clean_emails).execute()
        existing_contacts = existing_res.data or []
        existing_emails = {c["email"].lower() for c in existing_contacts}

        # 3. Identify and Create missing contacts (as leads)
        missing_emails = [e for e in clean_emails if e not in existing_emails]
        if missing_emails:
            new_contacts_data = [
                {
                    "email": e,
                    "contact_type": "lead",
                    "source": "manual_broadcast",
                    "is_subscribed": True,
                    "engagement_score": 0
                }
                for e in missing_emails
            ]
            try:
                new_res = db.table("marketing_contacts").insert(new_contacts_data).execute()
                if new_res.data:
                    existing_contacts.extend(new_res.data)
            except Exception as e:
                logger.error(f"Error auto-creating marketing contacts for manual broadcast: {e}")
                # Fallback: re-fetch in case a race condition occurred
                refetch = db.table("marketing_contacts").select("*").in_("email", missing_emails).execute()
                if refetch.data:
                    existing_contacts.extend(refetch.data)

        return existing_contacts

    # Priority 2: Segments
    if segment_ids:
        # For now, we support 'special' common segment IDs or actual UUIDs
        all_contacts = []
        for sid in segment_ids:
            if sid == 'engaged':
                # Contacts who have opened at least one email
                res = db.table("marketing_contacts").select("*").gt("total_emails_opened", 0).eq("is_subscribed", True).execute()
                all_contacts.extend(res.data)
            elif sid == 'recent':
                # Contacts joined in last 30 days
                res = db.table("marketing_contacts").select("*").gt("created_at", (datetime.utcnow() - timedelta(days=30)).isoformat()).eq("is_subscribed", True).execute()
                all_contacts.extend(res.data)
            elif sid == 'hot':
                # High engagement score
                res = db.table("marketing_contacts").select("*").gt("engagement_score", 50).eq("is_subscribed", True).execute()
                all_contacts.extend(res.data)
            elif sid in ['financial_overdue', 'financial_outstanding', 'financial_paid_fully']:
                # Financial data aggregation
                fin_contacts = get_financial_segment_contacts(sid)
                all_contacts.extend(fin_contacts)
            else:
                # 4. Custom Dynamic Segment from DB
                seg_res = db.table("marketing_segments").select("*").eq("id", sid).execute()
                if seg_res.data:
                    segment = seg_res.data[0]
                    rules = segment.get("filter_rules") or []
                    query = db.table("marketing_contacts").select("*").eq("is_subscribed", True)
                    
                    if segment["segment_type"] == "dynamic":
                        query = apply_segment_filters(query, rules)
                        res = query.execute()
                        all_contacts.extend(res.data)
                    else:
                        # Static segments would use a join table (future PRD)
                        pass
        
        # De-duplicate by ID
        unique_contacts = {c['id']: c for c in all_contacts}.values()
        return list(unique_contacts)

    # Default: All subscribed
    res = db.table("marketing_contacts").select("*").eq("is_subscribed", True).execute()
    return res.data

async def broadcast_campaign(campaign_id: str, segment_ids: List[str] = None, manual_emails: List[str] = None):
    """Broadcasts a campaign to targeted recipients with throttling."""
    db = get_db()
    
    # 1. Fetch Campaign
    camp_res = db.table("email_campaigns").select("*").eq("id", campaign_id).execute()
    if not camp_res.data:
        return logger.error(f"Campaign {campaign_id} not found")
    campaign = camp_res.data[0]
    
    if campaign["status"] not in ["scheduled", "sending"]:
        return logger.info(f"Campaign {campaign_id} is in {campaign['status']} status, skipping broadcast.")

    # 2. Fetch Recipients
    recipients = await resolve_target_recipients(segment_ids, manual_emails)
    
    if not recipients:
        db.table("email_campaigns").update({"status": "failed"}).eq("id", campaign_id).execute()
        return logger.error(f"No recipients for campaign {campaign_id} with targets {segment_ids} / {manual_emails}")

    # 3. Update status to sending
    db.table("email_campaigns").update({
        "status": "sending",
        "total_recipients": len(recipients)
    }).eq("id", campaign_id).execute()

    # 4. Batch Send (Throttled)
    batch_size = 50
    sent_count = 0
    
    for i in range(0, len(recipients), batch_size):
        batch = recipients[i:i+batch_size]
        tasks = [send_marketing_email(campaign, r) for r in batch]
        results = await asyncio.gather(*tasks)
        
        # Only count successful sends if we want to be precise, 
        # but usually we log 'sent' even if delivery fails later via webhooks
        sent_count += len([r for r in results if r is not None])
        
        db.table("email_campaigns").update({"total_sent": sent_count}).eq("id", campaign_id).execute()
        
        if i + batch_size < len(recipients):
            await asyncio.sleep(1) # Rate limit safety

    # 5. Finalize
    db.table("email_campaigns").update({
        "status": "sent",
        "total_sent": sent_count,
        "sent_at": datetime.utcnow().isoformat()
    }).eq("id", campaign_id).execute()
    
    logger.info(f"Campaign {campaign_id} broadcast complete. Targeted {len(recipients)}, Sent {sent_count}.")
