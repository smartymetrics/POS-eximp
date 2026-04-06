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

BRAND_LOGO_URL = "https://scsdnstqtrqjsosbmxyf.supabase.co/storage/v1/object/public/marketing/logo_dark.svg"
BRAND_FOOTER_HTML = f"""
<table width="100%" cellpadding="0" cellspacing="0" style="background:#1A1A1A; margin-top:20px;">
    <tr><td style="padding: 30px; text-align: center; border-top: 1px solid #333;">
      <img src="{BRAND_LOGO_URL}" alt="Eximp &amp; Cloves" style="height:36px; margin-bottom:16px;" />
      <div style="margin-bottom:16px;">
        <a href="https://www.linkedin.com/company/eximp-cloves" style="color:#C47D0A;text-decoration:none;margin:0 10px;font-family:'Inter',sans-serif;font-size:13px;">LinkedIn</a>
        <a href="https://x.com/eximp_cloves" style="color:#C47D0A;text-decoration:none;margin:0 10px;font-family:'Inter',sans-serif;font-size:13px;">X</a>
        <a href="https://instagram.com/eximp.cloves" style="color:#C47D0A;text-decoration:none;margin:0 10px;font-family:'Inter',sans-serif;font-size:13px;">Instagram</a>
        <a href="https://facebook.com/eximp.cloves" style="color:#C47D0A;text-decoration:none;margin:0 10px;font-family:'Inter',sans-serif;font-size:13px;">Facebook</a>
        <a href="https://tiktok.com/@eximp.cloves" style="color:#C47D0A;text-decoration:none;margin:0 10px;font-family:'Inter',sans-serif;font-size:13px;">TikTok</a>
      </div>
      <div style="color:#666; font-family:'Inter',sans-serif; font-size:12px; line-height:1.7;">
        Eximp &amp; Cloves Infrastructure Limited<br>
        57B, Isaac John Street, Yaba, Lagos, Nigeria<br>
        📞 +234 912 686 4383 &nbsp;|&nbsp; 📧 <a href="mailto:admin@eximps-cloves.com" style="color:#C47D0A;">admin@eximps-cloves.com</a><br>
        🌐 <a href="https://eximps-cloves.com" style="color:#C47D0A;">eximps-cloves.com</a>
      </div>
      <div style="margin-top:16px; padding-top:16px; border-top:1px solid #2a2a2a;">
        <a href="{{{{unsubscribe_url}}}}" style="color:#555; font-family:'Inter',sans-serif; font-size:11px; text-decoration:underline;">Unsubscribe from marketing emails</a>
      </div>
    </td></tr>
</table>
"""

def personalize_content(html: str, contact: Dict[str, Any]) -> str:
    """Replaces {{variable}} with contact data and live financial context."""
    db = get_db()
    unsub_token = contact.get("id") or "test-id"
    unsub_url = f"{APP_BASE_URL}/unsubscribe/{unsub_token}"

    # Basic Tags
    vars = {
        "first_name": contact.get("first_name") or "there",
        "last_name": contact.get("last_name") or "",
        "full_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or "Valued Client",
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "unsubscribe_url": unsub_url
    }

    # Financial Tags (Conditional)
    client_id = contact.get("client_id")
    if client_id:
        try:
            # Fetch latest active invoice for this client
            inv_res = db.table("invoices").select("*, properties(name)")\
                .eq("client_id", client_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if inv_res.data:
                inv = inv_res.data[0]
                prop = inv.get("properties") or {}
                
                # Formatters
                fmt = lambda x: f"₦{float(x or 0):,.2f}"
                
                vars.update({
                    "outstanding": fmt(inv.get("balance_due")),
                    "amount_paid": fmt(inv.get("amount_paid")),
                    "total_invoiced": fmt(inv.get("amount")),
                    "property_name": prop.get("name") or inv.get("property_name") or "Your Property",
                    "due_date": inv.get("due_date") or "N/A",
                    "invoice_number": inv.get("invoice_number") or "N/A"
                })
        except Exception as e:
            logger.error(f"Financial personalization error for {client_id}: {e}")

    # Apply replacements
    for key, val in vars.items():
        html = html.replace(f"{{{{{key}}}}}", str(val))
    
    # Clean up any unreplaced variables or placeholders like [BALANCE]
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

def sanitize_urls(html: str) -> str:
    """Replaces any localhost or development URLs with the public APP_BASE_URL."""
    # Matches http://127.0.0.1:8000/ or http://localhost:8000/ or alike
    pattern = r"http://(?:localhost|127\.0\.0\.1):\d+/"
    return re.sub(pattern, f"{APP_BASE_URL.rstrip('/')}/", html)

async def send_marketing_email(campaign: Dict[str, Any], contact: Dict[str, Any]):
    """Sends a single personalized marketing email with tracking."""
    campaign_id = campaign["id"]
    contact_id = contact["id"]
    
    # 0. GLOBAL SUPPRESSION CHECK (Anti-Spam Compliance)
    # If the contact is not subscribed, DO NOT SEND.
    if not contact.get("is_subscribed", True):
        logger.warning(f"Aborting send to {contact['email']} - Contact is UNSUBSCRIBED.")
        return None

    # 1. Personalize & Sanitize
    html = personalize_content(campaign["html_body_a"], contact)
    html = sanitize_urls(html)
    
    # 2. Tracking (only for real campaigns, not tests)
    if campaign.get("status") != "test":
        html = wrap_links(html, campaign_id, contact_id)
        html = inject_tracking_pixel(html, campaign_id, contact_id)
        
        # Check for presence of "unsubscribe" in the HTML.
        # Use a more assertive check: if they have the {{unsubscribe_url}} tag OR the word unsubscribe in a link.
        has_unsubscribe = "unsubscribe" in html.lower()
        has_address = "Isaac John Street" in html
        
        if not has_address:
            # Re-inject the professional brand footer if it was accidentally removed
            logger.info(f"Re-injecting official brand footer for campaign {campaign_id}")
            if "</body>" in html:
                idx = html.rfind("</body>")
                html = html[:idx] + BRAND_FOOTER_HTML + html[idx:]
            else:
                html += BRAND_FOOTER_HTML
        elif not has_unsubscribe:
            # If the address is there but unsubscribe is MISSING, add the minimal fallback
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
                        # 5. Static segments use the join table
                        res = db.table("marketing_segment_contacts")\
                            .select("marketing_contacts(*)")\
                            .eq("segment_id", sid)\
                            .execute()
                        if res.data:
                            # Flatten the joined structure
                            all_contacts.extend([r["marketing_contacts"] for r in res.data if r.get("marketing_contacts")])
        
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
