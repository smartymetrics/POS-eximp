# ECOMS — PRD 6 Implementation Prompt
# Email Marketing Dashboard — Missing Features
# Paste this into your AI coding assistant (Cursor, Claude, etc.)

---

## CONTEXT

You are working on **ECOMS**, a FastAPI + Supabase backend for Eximp & Cloves Infrastructure Limited. The email marketing module uses **Resend** (not SendGrid) for sending. The database is Supabase (PostgreSQL). Auth is handled by `verify_token` from `routers/auth.py`. DB calls use `get_db()` and `db_execute()` from `database.py`.

All marketing routers are in `routers/`. The main send logic is in `marketing_service.py`.

---

## TASK 1 — Enable Resend Webhook Signature Verification
**File: `routers/marketing_webhooks.py`**

Find the `resend_webhook` function at the top. It currently has this commented-out block:

```python
@router.post("/api/marketing/webhooks/resend")
async def resend_webhook(request: Request):
    """Handle incoming webhooks from Resend."""
    # TODO: Verify Signature using RESEND_WEBHOOK_SECRET
    # signature = request.headers.get("resend-signature")
    # For now, we'll log it.

    payload = await request.json()
```

Replace it with proper HMAC-SHA256 signature verification. The `RESEND_WEBHOOK_SECRET` env var is already defined at the top of the file as:
```python
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET")
```

The Resend webhook sends the signature in the header `svix-signature` (format: `v1,<base64_hmac>`). The signed content is the raw request body. Use `hmac` and `hashlib` from Python's stdlib.

- Read the raw body bytes BEFORE calling `request.json()`
- Compute HMAC-SHA256 of the raw body using `RESEND_WEBHOOK_SECRET`
- Compare against the signature in the header
- If it doesn't match or the header is missing, return HTTP 401
- If `RESEND_WEBHOOK_SECRET` is not set, log a warning and skip verification (dev mode)
- After verification, parse the body as JSON and continue with the existing event handling logic below

---

## TASK 2 — Add Campaign Pause & Resume Endpoints
**File: `routers/marketing_campaigns.py`**

Add two new endpoints after the existing `cancel-schedule` endpoint. The `email_campaigns` table already has `status` with a CHECK constraint that includes `'paused'`.

### 2A — Pause endpoint
```
POST /campaigns/{id}/pause
```
- Fetch the campaign. If not found, raise 404.
- If status is not `'sending'`, raise 400 with message: `"Only actively sending campaigns can be paused."`
- Update status to `'paused'` in `email_campaigns`
- Log activity: event `"marketing_campaign_paused"`, description `f"Campaign '{id}' paused mid-send."`
- Return `{"message": "Campaign paused. Sending will stop after the current batch."}`

### 2B — Resume endpoint
```
POST /campaigns/{id}/resume
```
- Fetch the campaign. If not found, raise 404.
- If status is not `'paused'`, raise 400 with message: `"Only paused campaigns can be resumed."`
- Count pending recipients: query `campaign_recipients` where `campaign_id = id` AND `status = 'pending'`. This tells us how many are left.
- Update campaign status back to `'sending'`
- Use `background_tasks` (add `BackgroundTasks` to the function signature) to re-run `broadcast_campaign(id, None, None)`
- Log activity: event `"marketing_campaign_resumed"`, description `f"Campaign '{id}' resumed. {pending_count} recipients remaining."`
- Return `{"message": f"Campaign resumed. {pending_count} recipients remaining.", "pending": pending_count}`

### 2C — Update `broadcast_campaign` in `marketing_service.py`
The `broadcast_campaign` function currently sends all batches without checking if the campaign was paused mid-send. After the `asyncio.sleep(1)` line in the batch loop, add a check:

```python
# Re-fetch campaign status to detect pause signal
fresh = db.table("email_campaigns").select("status").eq("id", campaign_id).execute()
if fresh.data and fresh.data[0]["status"] == "paused":
    logger.info(f"Campaign {campaign_id} paused mid-send at batch {i}. Stopping.")
    return  # Exit without marking as sent
```

Also, before inserting into `campaign_recipients` in `send_marketing_email`, the status is currently hardcoded as `"sent"`. Change it to `"pending"` initially so that `resume` can count remaining contacts. Update it to `"sent"` after successful send.

---

## TASK 3 — Add Manual Unsubscribe & Resubscribe Endpoints
**File: `routers/marketing_contacts.py`**

Add these two endpoints after the existing `PUT /{id}` endpoint.

### 3A — Unsubscribe
```
PATCH /contacts/{id}/unsubscribe
```
```python
@router.patch("/{id}/unsubscribe")
async def unsubscribe_contact(id: str, current_admin=Depends(verify_token)):
```
- Fetch contact by id. If not found, raise 404.
- If `is_subscribed` is already `False`, raise 400: `"Contact is already unsubscribed."`
- Update `marketing_contacts`: set `is_subscribed=False`, `unsubscribed_at=datetime.utcnow().isoformat()`, `engagement_score=0`
- Insert into `marketing_unsubscribes`: `contact_id=id`, `email=<contact email>`, `reason="manual_admin"`, `unsubscribed_at=<timestamp>`
- Log activity: event `"marketing_contact_unsubscribed"`, description `f"Contact {contact email} manually unsubscribed by admin."`
- Return `{"message": "Contact unsubscribed.", "contact_id": id}`

### 3B — Resubscribe
```
PATCH /contacts/{id}/resubscribe
```
```python
@router.patch("/{id}/resubscribe")
async def resubscribe_contact(id: str, current_admin=Depends(verify_token)):
```
- Fetch contact by id. If not found, raise 404.
- If `is_subscribed` is already `True`, raise 400: `"Contact is already subscribed."`
- If `is_bounced` is `True`, raise 400: `"Cannot resubscribe a hard-bounced contact. The email address is invalid."`
- Update `marketing_contacts`: set `is_subscribed=True`, `unsubscribed_at=None`, `unsubscribe_reason=None`
- Log activity: event `"marketing_contact_resubscribed"`, description `f"Contact {contact email} manually resubscribed by admin {current_admin['sub']}."`
- Return `{"message": "Contact resubscribed.", "contact_id": id}`

---

## TASK 4 — Add Sequence Enable/Disable Toggle
**File: `routers/marketing_sequences.py`**

### 4A — Schema change
The `marketing_sequences` table does not have an `is_active` column. Add a migration. Create a new file `migrations/add_sequence_is_active.sql`:
```sql
ALTER TABLE marketing_sequences ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
```

### 4B — Toggle endpoint
Add this endpoint after the existing `DELETE /{id}` endpoint:
```
PATCH /sequences/{id}/toggle
```
```python
@router.patch("/{id}/toggle")
async def toggle_sequence(id: str, current_admin=Depends(verify_token)):
```
- Fetch the sequence. If not found, raise 404.
- Flip `is_active`: if currently `True`, set to `False`. If `False`, set to `True`.
- Update `marketing_sequences` with the new `is_active` value.
- Return `{"message": f"Sequence {'enabled' if new_value else 'disabled'}.", "is_active": new_value}`

### 4C — Update the sequencer engine guard
**File: `marketing_sequencer_engine.py`**

Find the main loop that iterates over due sequence enrollments. Before sending each step, add a check:

```python
# Fetch sequence is_active status
seq_res = db.table("marketing_sequences").select("is_active").eq("id", enrollment["sequence_id"]).execute()
if seq_res.data and not seq_res.data[0].get("is_active", True):
    logger.info(f"Skipping sequence {enrollment['sequence_id']} — sequence is disabled.")
    continue

# Fetch contact subscribed/bounced status
contact_res = db.table("marketing_contacts").select("is_subscribed, is_bounced").eq("id", enrollment["contact_id"]).execute()
if contact_res.data:
    contact = contact_res.data[0]
    if not contact.get("is_subscribed") or contact.get("is_bounced"):
        logger.info(f"Stopping sequence for contact {enrollment['contact_id']} — unsubscribed or bounced.")
        db.table("contact_sequence_status").update({"status": "exited"}).eq("id", enrollment["id"]).execute()
        continue
```

---

## TASK 5 — Add Delete Media Endpoint
**File: `routers/marketing_media.py`**

Add this endpoint after the existing `GET /` list endpoint.

```
DELETE /media/{id}
```
```python
@router.delete("/{id}")
async def delete_media(id: str, current_admin=Depends(verify_token)):
```
- Fetch the media record from `media_library` by `id`. If not found, raise 404.
- Extract the storage path from `file_url`. The URL format is:
  `{SUPABASE_URL}/storage/v1/object/public/marketing/{date_folder}/{filename}`
  Strip the base to get the storage path: everything after `/marketing/`
- Delete from Supabase Storage: `db.storage.from_("marketing").remove([storage_path])`
- Delete the row from `media_library` where `id = id`
- Return `{"message": "Media deleted.", "id": id}`

Import `SUPABASE_URL` — it's already imported at the top of the file.

---

## TASK 6 — Fix A/B Test Send Logic
**File: `marketing_service.py`**

Find the `broadcast_campaign` function. Currently it only sends using `subject_a` and `html_body_a`. Add A/B split logic.

After the recipients list is resolved (after `resolve_target_recipients` call), add:

```python
is_ab = campaign.get("is_ab_test", False)
subject_b = campaign.get("subject_b")
html_body_b = campaign.get("html_body_b")

if is_ab and subject_b and html_body_b:
    # Split recipients 50/50
    midpoint = len(recipients) // 2
    group_a = recipients[:midpoint]
    group_b = recipients[midpoint:]
else:
    group_a = recipients
    group_b = []
```

Then update the batch loop to handle both groups:

```python
async def send_variant(contact, variant_label, subject_override=None, body_override=None):
    camp_copy = dict(campaign)
    if subject_override:
        camp_copy["subject_a"] = subject_override
    if body_override:
        camp_copy["html_body_a"] = body_override
    result = await send_marketing_email(camp_copy, contact)
    # After sending, record the variant
    if result and campaign.get("status") != "test":
        db = get_db()
        db.table("campaign_recipients").update({"variant": variant_label}).eq("campaign_id", campaign_id).eq("contact_id", contact["id"]).execute()
    return result
```

Then send group_a with variant A and group_b with variant B using the same existing batch/throttle logic.

---

## TASK 7 — Extract Unsubscribe Page to Template File
**File: `routers/marketing_webhooks.py`, new file `templates/unsubscribe.html`**

### 7A — Create the template
Create `templates/unsubscribe.html`. Copy the existing HTML string from inside `unsubscribe_page()` function into this file. Replace the Python f-string variables with Jinja2 template variables:
- `{name}` → `{{ name }}`
- `{email}` → `{{ email }}`
- `{token}` → `{{ token }}`

Do the same for the success page — create `templates/unsubscribe_success.html` from the HTML in `process_unsubscribe()`.

### 7B — Update the webhook router
At the top of `marketing_webhooks.py`, add:
```python
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
```

Update `unsubscribe_page` function signature to accept `request: Request` (it already does) and change the return to:
```python
return templates.TemplateResponse("unsubscribe.html", {
    "request": request,
    "name": name,
    "email": email,
    "token": token
})
```

Update `process_unsubscribe` to return:
```python
return templates.TemplateResponse("unsubscribe_success.html", {"request": request})
```

Remove the `response_class=HTMLResponse` decorator from both endpoints — Jinja2Templates handles the content type.

---

## TASK 8 — Pre-Send Validation Checklist
**File: `routers/marketing_campaigns.py`**

Find the `send_campaign_broadcast` function. Currently it only checks that status is `'draft'`. Add a validation block immediately after the status check, before handling scheduling:

```python
# Pre-send validation checklist
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
```

Also estimate recipient count and include it in the success response. After resolving recipients (not now — this is done in the background task), for the immediate response add an estimate:

```python
# Estimate recipient count (lightweight — just count, don't fetch full records)
estimated_count = 0
if target and target.segment_ids:
    for sid in target.segment_ids:
        count_res = await db_execute(lambda: db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True).execute())
        estimated_count += count_res.count or 0
elif target and target.manual_emails:
    estimated_count = len(target.manual_emails)

# Include in response
return {"message": "Broadcast started in the background.", "estimated_recipients": estimated_count}
```

---

## TASK 9 — Seed Default Segments
**Create new file: `scripts/seed_marketing_segments.py`**

```python
"""
Run once to seed the 7 default marketing segments.
Usage: python scripts/seed_marketing_segments.py
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db

DEFAULT_SEGMENTS = [
    {
        "name": "All Subscribed Contacts",
        "description": "Every contact who is currently subscribed to marketing emails.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "All Clients",
        "description": "Contacts identified as ECOMS clients.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "contact_type", "op": "eq", "val": "client"}, {"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "All Leads",
        "description": "Contacts who are leads but not yet clients.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "contact_type", "op": "eq", "val": "lead"}, {"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "Hot Leads",
        "description": "Leads with engagement score of 70 or higher.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "contact_type", "op": "eq", "val": "lead"}, {"field": "engagement_score", "op": "gte", "val": 70}, {"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "Dormant Contacts",
        "description": "Subscribed contacts who have not interacted in over 90 days.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}, {"field": "engagement_score", "op": "lt", "val": 10}, {"field": "last_interaction_at", "op": "older_than", "val": 90}]
    },
    {
        "name": "Recent Subscribers",
        "description": "Contacts who joined in the last 30 days.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}, {"field": "created_at", "op": "in_last", "val": 30}]
    },
    {
        "name": "Clients with Outstanding Balance",
        "description": "Clients who have unpaid invoices. Uses financial segment resolver.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "financial_status", "op": "eq", "val": "financial_outstanding"}]
    }
]

def seed():
    db = get_db()
    for seg in DEFAULT_SEGMENTS:
        # Check if it already exists by name
        existing = db.table("marketing_segments").select("id").eq("name", seg["name"]).execute()
        if existing.data:
            print(f"  SKIP — already exists: {seg['name']}")
            continue
        result = db.table("marketing_segments").insert(seg).execute()
        if result.data:
            print(f"  CREATED: {seg['name']}")
        else:
            print(f"  FAILED: {seg['name']}")

if __name__ == "__main__":
    print("Seeding default marketing segments...")
    seed()
    print("Done.")
```

---

## TASK 10 — Hard vs Soft Bounce Distinction
**File: `routers/marketing_webhooks.py`**

Find the `email.bounced` handler block inside `resend_webhook`. Currently it suppresses all bounces permanently. Update it:

```python
elif event_type == "email.bounced":
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
```

Also add `bounce_count INTEGER DEFAULT 0` column to `campaign_recipients` — create `migrations/add_bounce_count.sql`:
```sql
ALTER TABLE campaign_recipients ADD COLUMN IF NOT EXISTS bounce_count INTEGER DEFAULT 0;
```

---

## NOTES FOR THE AI

- Do not change any existing working functionality — only add to it.
- All new endpoints must use `Depends(verify_token)` for auth.
- Follow the exact same code style as the existing routers: `db_execute(lambda: ...)` pattern for all Supabase calls.
- Do not install any new packages. All tasks use existing imports: `os`, `hmac`, `hashlib`, `re`, `datetime`, `asyncio`.
- For Task 1, `hmac` and `hashlib` are Python stdlib — just import them at the top of `marketing_webhooks.py`.
- After completing all tasks, confirm which files were modified and list any SQL migration files that need to be run in Supabase.