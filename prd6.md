# ECOMS – PRD 6: Email Marketing Dashboard
**Eximp & Cloves Infrastructure Limited**  
Version 1.0 | 2026  
_Read alongside PRD 1–5 and the Addendum_

---

## ⚠️ Important Deviation from Original PRD

The original PRD specified **SendGrid for marketing emails**. After review, we are **using Resend for both transactional and marketing emails** at this stage.

**Reason:** Current volume is fewer than 50 emails per week (~200/month). Resend's permanent free tier covers 3,000 emails/month with no expiry and no credit card required. SendGrid has discontinued its free plan as of May 2025 — new accounts only get a 60-day trial before paid plans start at $19.95/month.

**Architecture rule:** Even though both email types use Resend now, keep the marketing send logic in a **completely separate service layer** (`marketing_service.py`) from the transactional layer (PRD 1). When volume grows and we migrate marketing to SendGrid, it will be a config swap, not a refactor.

---

## 1. Overview

This PRD specifies a full-featured email marketing dashboard built into ECOMS. The system allows the Eximp & Cloves marketing and sales team to design, schedule, send, and analyse professional email campaigns to clients, leads, and custom audience segments — all without leaving the ECOMS platform, styled with Eximp & Cloves brand identity.

The email marketing module is built to a standard comparable to Mailchimp, Klaviyo, and SendGrid Marketing Campaigns, designed to scale from the current client base to tens of thousands of contacts without requiring a platform change.

---

## 2. Sending Infrastructure

### 2.1 Provider: Resend (replaces SendGrid for now)

Use the existing Resend integration from PRD 1. Add a **dedicated marketing API key** and route all marketing sends through `marketing_service.py` — never through the transactional service.

### 2.2 New Environment Variables

```
RESEND_MARKETING_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxx
MARKETING_FROM_EMAIL=hello@mail.eximps-cloves.com
MARKETING_FROM_NAME=Eximp & Cloves
MARKETING_REPLY_TO=marketing@mail.eximps-cloves.com
MARKETING_BCC_EMAIL=marketing@mail.eximps-cloves.com
RESEND_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxx
APP_BASE_URL=https://app.eximps-cloves.com
```

> Use a **different from address** for marketing vs transactional:
> - Marketing from: `hello@mail.eximps-cloves.com`
> - Marketing reply-to: `marketing@mail.eximps-cloves.com`
> - Transactional: `noreply@mail.eximps-cloves.com` (existing, from PRD 1)
>
> This keeps sender reputation separate even on the same platform.
>
> **Important:** All from addresses must use `@mail.eximps-cloves.com` — this is the verified domain in Resend. Using any other domain will cause sends to fail or fail DKIM.
>
> **Why Reply-To is different from From:** The From address (`hello@`) is what recipients see and builds brand trust. The Reply-To (`marketing@`) is where replies land so the team can monitor and respond. They are intentionally separate.
>
> **On CC:** Do not use CC on bulk marketing campaigns — every recipient would see every other recipient's email address, which is a serious privacy violation. Instead, use BCC to send a silent copy to an internal address (`MARKETING_BCC_EMAIL`) so the team can monitor outgoing campaigns without exposing recipient lists.

### 2.3 Install

```
resend (already in requirements.txt from PRD 1 — no new dependency needed)
```

### 2.4 Sending Limits & Warmup Schedule

Sending too many emails too fast from a new domain damages sender reputation. Follow this warmup:

| Week | Max Emails/Day | Strategy |
|------|---------------|----------|
| Week 1 | 50 | Existing clients only — people who know Eximp & Cloves |
| Week 2 | 200 | All existing clients |
| Week 3 | 500 | Add leads and imported contacts |
| Week 4+ | Unlimited (within plan) | Full list — monitor bounce rate, keep below 2% |

> Bounce rate above 5% risks account suspension. Auto-suppress bounced addresses immediately on bounce webhook receipt.

### 2.5 Domain Authentication — ✅ Already Done

`mail.eximps-cloves.com` is **already verified** in Resend (status: Verified, region: Ireland eu-west-1). No DNS changes needed.

**Tracking is also already configured on the domain:**
- ✅ Click Tracking — enabled
- ✅ Open Tracking — enabled

> Open Tracking is marked "Not Recommended" by Resend because Gmail and Apple Mail sometimes pre-fetch images, causing slightly inflated open counts. This is an industry-wide limitation affecting Mailchimp, Klaviyo, and all other tools equally. Keep it enabled — the data is still valuable for engagement trends and scoring.

### 2.6 Separation from Transactional Emails

| Email Type | Examples | From Address | Unsubscribe Applies? |
|-----------|---------|--------|---------------------|
| Transactional | Invoice, Receipt, Statement, Contract link | `noreply@mail.eximps-cloves.com` | No — always delivered |
| Marketing | Estate launches, promos, newsletters, reminders | `hello@mail.eximps-cloves.com` | Yes — suppression list enforced |

> A client who unsubscribes from marketing emails must still receive invoices, receipts, and contract documents. These are separate services and separate opt-out lists.

---

## 3. Contact Management

### 3.1 Contact Sources

Marketing contacts are stored in a **separate `marketing_contacts` table**, not the existing clients table. This is because marketing contacts include leads who are not yet clients.

| Source | How Added | Type |
|--------|-----------|------|
| ECOMS Clients | Auto-synced from clients table on client creation | Client |
| Google Form Leads | Manual import or future form webhook | Lead |
| CSV Import | Admin uploads CSV — name, email, phone, tags | Lead / Client |
| Manual Entry | Admin adds single contact from dashboard | Lead / Client |

### 3.2 Database Schema

```sql
CREATE TABLE IF NOT EXISTS marketing_contacts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id UUID REFERENCES clients(id), -- NULL for non-client leads
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(50),
  tags TEXT[], -- e.g. {'coinfield', 'hot-lead', 'vip'}
  source VARCHAR(100), -- 'ecoms_client', 'csv_import', 'manual', 'form'
  contact_type VARCHAR(50) DEFAULT 'lead' CHECK (contact_type IN ('client', 'lead')),
  is_subscribed BOOLEAN DEFAULT true,
  unsubscribed_at TIMESTAMPTZ,
  unsubscribe_reason TEXT,
  bounce_count INTEGER DEFAULT 0,
  is_bounced BOOLEAN DEFAULT false,
  bounced_at TIMESTAMPTZ,
  engagement_score INTEGER DEFAULT 0, -- 0-100
  last_opened_at TIMESTAMPTZ,
  last_clicked_at TIMESTAMPTZ,
  total_emails_received INTEGER DEFAULT 0,
  total_emails_opened INTEGER DEFAULT 0,
  total_emails_clicked INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_marketing_contacts_email ON marketing_contacts(email);
CREATE INDEX idx_marketing_contacts_subscribed ON marketing_contacts(is_subscribed) WHERE is_subscribed = true;
CREATE INDEX idx_marketing_contacts_score ON marketing_contacts(engagement_score DESC);
ALTER TABLE marketing_contacts ENABLE ROW LEVEL SECURITY;
```

### 3.3 CSV Import Flow

1. Admin uploads CSV file from the Contacts page
2. System shows a column mapping screen — "Which column is email? Which is first name?"
3. Validates all email addresses — skips malformed ones and shows a count
4. Checks for duplicates — skips or updates existing contacts
5. Shows preview: "Ready to import 247 contacts. 3 skipped (invalid email). 12 already exist."
6. Admin confirms — contacts inserted in bulk
7. Assigns a tag based on import batch name (e.g. `march-2026-import`)

**Required CSV columns:** `email` (required), `first_name` (optional), `last_name` (optional), `phone` (optional), `tags` (optional — comma separated)

### 3.4 Engagement Scoring

Every contact has an `engagement_score` from 0–100. Recalculated after every email event.

| Action | Score Change | Notes |
|--------|-------------|-------|
| Email opened | +5 | Same campaign counted once only |
| Link clicked | +10 | Higher weight than opens |
| Multiple opens, same campaign | +2 each | Repeated opens show strong interest |
| No opens for 30 days | -5 per month | Gradual decay |
| No opens for 90 days | Score halved | Marked as cold |
| No opens for 180 days | Score = 0 | Marked as dormant |
| Unsubscribed | Score = 0 | Removed from all marketing |
| Email bounced | Score = 0 | Removed from all marketing |

**Engagement tiers:**

| Tier | Score | Label | Recommended Action |
|------|-------|-------|-------------------|
| Hot | 70–100 | Highly Engaged | Priority for new estate launches, VIP offers |
| Warm | 40–69 | Engaged | Standard campaigns, nurture sequences |
| Cold | 10–39 | Low Engagement | Re-engagement campaign before removing |
| Dormant | 0–9 | Inactive | Final re-engagement attempt or archive |

---

## 4. Audience Segmentation

### 4.1 Segment Types

| Type | Description | Example |
|------|-------------|---------|
| Static | Fixed list — manually curated | "VIP Clients" — admin manually adds/removes |
| Dynamic | Rule-based — contacts auto enter/leave based on conditions. Recalculated before every send | "Clients with outstanding balance" — auto-updates as payments are made |

### 4.2 Dynamic Segment Filter Conditions

Admin can combine any of these conditions using AND/OR logic:

| Filter Category | Available Conditions |
|----------------|---------------------|
| Contact Type | Is Client / Is Lead |
| Estate Purchased | Bought in [Estate Name] / Has not bought |
| Payment Status | Fully paid / Has outstanding balance / Overdue / Unpaid |
| Payment Plan | Outright / Installment |
| Sales Rep | Was referred by [Rep Name] |
| Engagement Score | Score greater than X / less than X / between X and Y |
| Engagement Tier | Is Hot / Warm / Cold / Dormant |
| Last Opened | Opened in last X days / Never opened |
| Location/State | Address contains [State Name] |
| Date Joined | Joined before / after / between [dates] |
| Tags | Has tag [X] / Does not have tag [X] |
| Campaign History | Received campaign [X] / Did not receive |
| Subscription Status | Subscribed / Unsubscribed (audit only) |

> Every campaign automatically excludes unsubscribed and bounced contacts regardless of segment — enforced at the backend send layer, not just in the UI.

### 4.3 Pre-Built Default Segments

- All Subscribed Contacts
- All Clients
- All Leads
- Clients with Outstanding Balance (dynamic — links to invoices table)
- Hot Leads (engagement score 70+)
- Dormant Contacts (score below 10, no opens in 90 days)
- Recent Subscribers (joined in last 30 days)

### 4.4 Behaviour-Based Segments

The engagement data captured by the Resend webhook feeds directly into segmentation, allowing campaigns to be targeted at contacts based on exactly how they have interacted with previous emails:

| Segment Name | Filter Logic | Use Case |
|-------------|-------------|---------|
| Highly Engaged | Opened last 3 campaigns | Send VIP estate launch first — hottest leads |
| Clickers Only | `total_emails_clicked > 0` | Clicked at least once — ready for a stronger CTA |
| Openers Never Clicked | `total_emails_opened > 0` AND `total_emails_clicked = 0` | Interested but not converting — try a different CTA |
| Never Opened | `total_emails_opened = 0` | Cold contacts — send a re-engagement campaign |
| Opened in Last 30 Days | `last_opened_at > now - 30 days` | Recently active — good time for a follow-up |
| Inactive 60+ Days | `last_opened_at < now - 60 days` | At risk of going dormant — send a win-back campaign |

> The full flow: **Resend fires webhook → ECOMS saves event → contact timestamps and score update → dynamic segment recalculates → next campaign targets only contacts matching that behaviour.** This is automatic — no manual work needed once the system is built.

---

## 5. Campaign Builder — Drag and Drop Email Editor

### 5.1 Technology: GrapesJS

Use **GrapesJS** — free, open-source, production-grade drag-and-drop HTML builder (used by Webflow, Jimdo, and hundreds of SaaS products). Loaded from CDN, embedded as a full-page editor in ECOMS. Outputs clean HTML used as the email body.

Do NOT build a drag-and-drop editor from scratch. Do NOT use Unlayer/Stripo (paid, $99+/month).

### 5.2 Email Templates

All templates use Eximp & Cloves brand colours and fonts. Admin picks a template, then customises it.

| Template Name | Use Case | Layout |
|--------------|---------|--------|
| Estate Launch | Announce a new property/estate | Hero image, headline, property details, CTA button |
| Promotional Offer | Limited-time pricing, seasonal sale (Eid/Easter) | Bold offer block, urgency, CTA |
| Payment Reminder | Outstanding balance reminder | Account summary block, balance due, pay now CTA |
| Newsletter | Monthly company update | Multi-section with text + image columns |
| Welcome Email | First email to new lead/subscriber | Warm welcome, company intro, what to expect |
| Re-engagement | Win back dormant contacts | "We miss you" message, special offer, unsubscribe option prominent |
| Event Invitation | Site inspection or open day invite | Date, location, RSVP button |
| Blank | Start from scratch | Empty canvas |

### 5.3 Email Building Blocks (Drag and Drop)

| Block | Description |
|-------|-------------|
| Header | Company logo + brand colour banner — pre-filled with Eximp & Cloves branding, **locked** |
| Hero Image | Full-width image with optional overlay text |
| Heading | Large text — H1/H2/H3 sizes |
| Text Block | Rich text paragraph — bold, italic, links, font size |
| Image Block | Single image, drag-and-drop to upload, set alt text, link destination |
| Two Column | Side-by-side layout — image left/text right or two text blocks |
| Three Column | Three equal columns for feature lists |
| Button | CTA button — text, link, colour (defaults to gold), border radius |
| Divider | Horizontal line separator |
| Spacer | Adjustable blank space |
| Property Card | Pre-styled estate listing card — image, name, location, price, CTA |
| Account Summary | Dynamic block — shows client name, invoice amount, balance due |
| Social Links | Facebook, Instagram, Twitter/X, WhatsApp icons with links |
| Footer | Locked — company address, phone, website, unsubscribe link (**cannot be removed**) |

> Header and Footer are **locked**. The footer always contains the unsubscribe link. This is a legal requirement and cannot be bypassed.

### 5.4 Image Handling

- Drag image file directly onto any image block in the editor, OR
- Click block → "Upload Image" from block settings, OR
- Select from Media Library (previously uploaded images)

**Rules:**
- Accepted formats: JPG, PNG, WebP, GIF
- Maximum file size: 5MB per image
- Uploaded to Supabase Storage (or CDN bucket)
- Auto-resized to max width 600px to prevent oversized email payloads
- Media Library shows all uploaded images with thumbnails — click to reuse

### 5.5 Personalisation Variables

Inserted anywhere in the email, replaced with each recipient's data at send time:

| Variable | Replaced With | Example Output |
|---------|--------------|---------------|
| `{{first_name}}` | Contact's first name | Dear Adebayo, |
| `{{full_name}}` | Contact's full name | Dear Adebayo Okonkwo, |
| `{{estate_name}}` | Last purchased estate | Your plot at Coinfield Estate |
| `{{balance_due}}` | Current outstanding balance | NGN 450,000.00 |
| `{{due_date}}` | Invoice due date | 20 Jun 2026 |
| `{{sales_rep}}` | Assigned sales rep name | Your rep: Funke Adeyemi |
| `{{unsubscribe_link}}` | Unique unsubscribe URL (auto-inserted in footer) | Click here to unsubscribe |

> If a variable has no value for a contact (e.g. a lead with no purchase), it renders as blank — never as `{{estate_name}}`. Replace all unfound variables with empty strings before sending.

### 5.6 Subject Line & Preview Text

Every campaign requires:
- **Subject Line** — supports personalisation variables. Max 60 characters recommended. Show character counter.
- **Preview Text** — grey preheader text shown after subject in email clients. Max 90 characters. If not set, email clients pull first line of email body (often looks bad).
- **From Name** — defaults to "Eximp & Cloves" — admin can customise per campaign
- **From Email** — fixed to `hello@mail.eximps-cloves.com` — not editable by admin (must match verified domain)
- **Reply-To Email** — defaults to `marketing@mail.eximps-cloves.com` — admin can change per campaign if needed
- **BCC** — defaults to `marketing@mail.eximps-cloves.com` — sends a silent internal copy to the team. Admin can change or clear per campaign. Never visible to recipients.

### 5.7 A/B Testing

Admin enables A/B test toggle on the campaign settings screen:
- Variant A — 50% of audience
- Variant B — 50% of audience

After 24 hours, analytics show which variant had higher open/click rate. Admin can then "Send Winner."

What can be A/B tested:
- Subject line only (same body)
- Subject line + email body (completely different emails)
- Send time (same email, different times)

---

## 6. Campaign Sending

### 6.1 Send Options

| Option | Description |
|--------|-------------|
| Send Now | Immediately queues all emails — throttled to protect reputation |
| Schedule | Admin picks future date/time — sent automatically via APScheduler (from PRD 3) |
| Send Test | Sends preview to admin's email only — no tracking, variables shown as-is |
| Save as Draft | Saves without sending — editable and sendable later |

### 6.2 Pre-Send Checklist

Before "Send Now" is enabled, validate:
1. Subject line is not empty
2. At least one segment is selected
3. Email body is not blank
4. Footer with unsubscribe link is present
5. No broken personalisation variables (e.g. `{{first_nme}}` typo check)
6. Estimated recipient count is shown: "This campaign will be sent to 247 contacts"
7. A test email has been sent (soft warning — can be bypassed)

> Estimated recipient count **excludes** unsubscribed, bounced, and duplicate email addresses automatically.

### 6.3 Throttled Sending

| Campaign Size | Batch Strategy |
|--------------|----------------|
| Under 500 | One batch over 5 minutes |
| 500–5,000 | Batches of 200 per minute |
| 5,000+ | Batches of 500 per minute — auto-pause if bounce rate exceeds 2% |

Show real-time progress bar on campaign detail page: "X of Y emails sent."

### 6.4 Campaign Status Flow

| Status | Meaning |
|--------|---------|
| Draft | Being built — not sent |
| Scheduled | Set to send at future time |
| Sending | Currently dispatching in batches |
| Sent | All emails dispatched |
| Paused | Admin manually paused mid-send — can resume |
| Failed | Critical error — no emails sent |

---

## 7. Open & Click Tracking

### 7.1 Open Tracking

Invisible 1×1 pixel image inserted into every email. When the recipient's email client loads it, an open event is recorded. Each URL is unique per recipient per campaign:

```
https://track.eximps-cloves.com/o/{campaign_id}/{contact_id}/{unique_token}.png
```

> **Known limitation:** Gmail, Apple Mail, and Outlook pre-fetch images or use proxies, so some "opens" are recorded by the email client rather than the real human. Open rates are approximate — use them for trends, not absolute counts. This affects Mailchimp, Klaviyo, and all other tools equally.

### 7.2 Click Tracking

Every link in a marketing email is replaced with a tracked redirect URL before sending:

```
Original:  https://www.eximps-cloves.com/coinfield-estate
Replaced:  https://track.eximps-cloves.com/c/{campaign_id}/{contact_id}/{link_hash}
```

When recipient clicks, the tracking server records the event and immediately redirects to the original URL (under 100ms — imperceptible to user). More reliable than open tracking since it requires real human action.

### 7.3 Resend Webhook Events

Webhook endpoint registered in Resend dashboard:
```
POST /api/marketing/webhooks/resend
```

**All 11 email events are subscribed to in Resend.** Handle every one in `marketing_webhooks.py`:

| Event | Action in ECOMS |
|-------|----------------|
| `email.sent` | Update `campaign_recipients.status = 'sent'`, set `sent_at` |
| `email.delivered` | Update `campaign_recipients.status = 'delivered'`, set `delivered_at` |
| `email.opened` | Increment `open_count`, set `opened_at` (first) / `last_opened_at`, update engagement score |
| `email.clicked` | Increment `click_count`, set `clicked_at`, insert `email_click_events` row, update engagement score |
| `email.bounced` | Set status = 'bounced', set `marketing_contacts.is_bounced = true`, `is_subscribed = false` |
| `email.complained` | Set `spam_reported_at`, set `is_subscribed = false` immediately |
| `email.delivery_delayed` | Log the event — no action needed unless it eventually becomes a bounce |
| `email.failed` | Update status = 'failed', flag campaign for admin review |
| `email.unsubscribed` | Set `is_subscribed = false`, insert into `marketing_unsubscribes` |
| (remaining events) | Log and ignore silently |

**Webhook handler pattern:**
```python
@router.post("/webhooks/resend")
async def resend_webhook(payload: dict, request: Request):
    # CRITICAL: Always verify signature first
    signature = request.headers.get("resend-signature")
    verify_resend_signature(signature, await request.body(), RESEND_WEBHOOK_SECRET)
    
    event_type = payload.get("type")
    
    if event_type == "email.sent":
        # update status to sent
    elif event_type == "email.delivered":
        # update status to delivered
    elif event_type == "email.opened":
        # update open count + engagement score
    elif event_type == "email.clicked":
        # update click count + log click event + engagement score
    elif event_type == "email.bounced":
        # suppress contact permanently
    elif event_type == "email.complained":
        # suppress contact immediately
    elif event_type == "email.delivery_delayed":
        # log only
    elif event_type == "email.failed":
        # flag for admin
    elif event_type == "email.unsubscribed":
        # update is_subscribed
    else:
        pass  # ignore remaining events silently
```

> **Security:** The webhook endpoint must verify Resend's signature using `RESEND_WEBHOOK_SECRET` on every incoming request before processing anything. Reject any request that fails verification.

> **Free plan data retention:** Resend only retains event data for **1 day** on the free plan. This is why it is critical that your webhook endpoint captures and saves every event into your own Postgres database immediately on receipt. Once saved to your database, the data is yours permanently regardless of Resend's retention limits.

---

## 8. Database Schema

```sql
CREATE TABLE IF NOT EXISTS email_campaigns (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  subject_a VARCHAR(500) NOT NULL,
  subject_b VARCHAR(500), -- NULL if not A/B test
  preview_text VARCHAR(500),
  from_name VARCHAR(255) DEFAULT 'Eximp & Cloves',
  from_email VARCHAR(255) DEFAULT 'hello@mail.eximps-cloves.com',
  reply_to VARCHAR(255) DEFAULT 'marketing@mail.eximps-cloves.com',
  bcc_email VARCHAR(255) DEFAULT 'marketing@mail.eximps-cloves.com', -- internal monitoring copy, never visible to recipients
  html_body_a TEXT NOT NULL,
  html_body_b TEXT,
  status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft','scheduled','sending','sent','paused','failed')),
  is_ab_test BOOLEAN DEFAULT false,
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  total_recipients INTEGER DEFAULT 0,
  total_sent INTEGER DEFAULT 0,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_segments (
  campaign_id UUID REFERENCES email_campaigns(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES marketing_segments(id),
  PRIMARY KEY (campaign_id, segment_id)
);

CREATE TABLE IF NOT EXISTS campaign_recipients (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID NOT NULL REFERENCES email_campaigns(id),
  contact_id UUID NOT NULL REFERENCES marketing_contacts(id),
  variant CHAR(1) DEFAULT 'A', -- A or B for A/B tests
  resend_message_id VARCHAR(255), -- replaces sendgrid_message_id
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending','sent','delivered','bounced','failed')),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,       -- first open
  last_opened_at TIMESTAMPTZ,  -- most recent open
  open_count INTEGER DEFAULT 0,
  clicked_at TIMESTAMPTZ,      -- first click
  last_clicked_at TIMESTAMPTZ,
  click_count INTEGER DEFAULT 0,
  bounced_at TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  spam_reported_at TIMESTAMPTZ,
  UNIQUE(campaign_id, contact_id)
);

CREATE TABLE IF NOT EXISTS email_click_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID NOT NULL REFERENCES email_campaigns(id),
  contact_id UUID NOT NULL REFERENCES marketing_contacts(id),
  original_url TEXT NOT NULL,
  clicked_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address VARCHAR(50),
  user_agent TEXT
);

CREATE TABLE IF NOT EXISTS marketing_segments (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  segment_type VARCHAR(20) DEFAULT 'dynamic' CHECK (segment_type IN ('dynamic', 'static')),
  filter_rules JSONB,
  contact_count INTEGER DEFAULT 0,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS marketing_unsubscribes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  contact_id UUID NOT NULL REFERENCES marketing_contacts(id),
  email VARCHAR(255) NOT NULL,
  campaign_id UUID REFERENCES email_campaigns(id), -- NULL if unsubscribed manually
  reason TEXT,
  unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS media_library (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  filename VARCHAR(500) NOT NULL,
  original_filename VARCHAR(500),
  file_url TEXT NOT NULL,
  file_size INTEGER,
  mime_type VARCHAR(100),
  width INTEGER,
  height INTEGER,
  uploaded_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. Analytics Dashboard

### 9.1 Campaign Overview Page

All campaigns listed with summary stats:

| Column | Description |
|--------|-------------|
| Campaign Name | Name given by admin |
| Status | Draft / Scheduled / Sending / Sent — colour coded badge |
| Sent Date | When sent or scheduled |
| Recipients | Total contacts who received the email |
| Open Rate | (Total opens / Total sent) × 100% — with trend arrow vs last campaign |
| Click Rate | (Total clicks / Total sent) × 100% |
| Unsubscribes | Count who unsubscribed from this campaign |
| Actions | View Report / Duplicate / Delete |

### 9.2 Individual Campaign Report

**Summary KPI Cards:** Sent, Delivered (%), Opened (unique + %), Clicked (unique + %), Unsubscribed (count + %), Bounced (count + %)

**Open Rate Over Time Chart:** Line chart showing cumulative opens over 48 hours after send.

**Click Map:** Visual email showing which links were clicked most — click count and percentage overlay per link/button.

**Device & Client Breakdown:** Doughnut charts for Device (Mobile/Desktop/Tablet) and Email Client (Gmail/Yahoo/Outlook/Apple Mail/Other).

**Recipient Activity Table:** Searchable table of all recipients — Contact Name, Email, Status, Opens, Clicks, First Opened, Last Activity. Filterable by: opened, not opened, clicked, bounced, unsubscribed.

### 9.3 Marketing Overview Dashboard

KPI cards: Total Contacts (subscribed vs unsubscribed), Campaigns Sent (this month), Average Open Rate (last 5 campaigns), Average Click Rate (last 5 campaigns), Hot Contacts Count (score 70+), New Subscribers (this month).

Charts: Contact growth over time (line), Open rate trend — last 10 campaigns (bar), Engagement score distribution — contacts per tier (histogram), Top clicked links across all campaigns.

---

## 10. Automated Email Sequences

### 10.1 Sequence Triggers

| Trigger | Description | Example |
|---------|-------------|---------|
| Contact added to segment | Fires when contact joins a dynamic segment | Contact becomes "Dormant" → start re-engagement sequence |
| Tag added to contact | Fires when specific tag is added | Tag "interested-coinfield" → send Coinfield estate sequence |
| Contact created | Fires when new lead is added | Welcome sequence for new leads |
| Invoice created | Fires on first client invoice | Post-purchase welcome sequence |
| Outstanding balance > X days | Fires when invoice is overdue | Payment reminder sequence |
| Manual enrolment | Admin manually adds contacts | For targeted campaigns |

### 10.2 Sequence Builder

Visual timeline builder. Each step is an email or a delay:
- **Trigger** — what starts the sequence
- **Email Step** — pick a pre-built email or compose a new one
- **Wait Step** — wait X hours/days before next email
- **Condition Step** — if opened previous email → go to Step A, if not → go to Step B
- **End** — sequence complete

**Example: Payment Reminder Sequence**

| Step | Type | Content | Timing |
|------|------|---------|--------|
| 1 | Trigger | Invoice overdue by 7 days | Automatic |
| 2 | Email | Friendly reminder — "Just a reminder, your balance is due" | Day 0 |
| 3 | Wait | 3 days | — |
| 4 | Email | Second reminder — "Your account has an outstanding balance" | Day 3 |
| 5 | Wait | 7 days | — |
| 6 | Condition | Has client paid? If yes → end. If no → next step | Day 10 |
| 7 | Email | Final notice — "Urgent: Please settle your outstanding balance" | Day 10 |
| 8 | End | — | — |

> Sequences must auto-stop for a contact if they unsubscribe, their email bounces, or they complete the trigger condition (e.g. they pay the outstanding balance).

---

## 11. Unsubscribe Management & Compliance

### 11.1 Unsubscribe Flow

Every marketing email contains an unsubscribe link in the locked footer. When clicked:

1. Recipient is taken to branded page: `app.eximps-cloves.com/unsubscribe/{token}`
2. Page shows: "You have been unsubscribed from Eximp & Cloves marketing emails. You will still receive important emails about your property transactions."
3. `is_subscribed` set to `false` immediately
4. Row inserted into `marketing_unsubscribes`
5. Engagement score set to 0
6. Excluded from all future campaign sends automatically

> Transactional emails (invoices, receipts, statements, contract links) are **never** affected by unsubscribes. They are sent via a separate Resend service layer and are not subject to marketing opt-out.

### 11.2 List Hygiene

- Bounced contacts → automatically suppressed on bounce event
- Spam reporters → automatically suppressed immediately
- Contacts with 3+ consecutive campaigns unopened → auto-moved to Dormant tier
- Admin prompted monthly to review Dormant contacts
- Hard bounces (invalid email) → permanently suppressed, cannot be re-subscribed
- Soft bounces (full inbox, server down) → retried up to 3 times before suppression

---

## 12. API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/marketing/contacts` | JWT | List all marketing contacts with filters |
| POST | `/api/marketing/contacts` | JWT | Add single contact manually |
| POST | `/api/marketing/contacts/import` | JWT | CSV import — multipart file upload |
| PUT | `/api/marketing/contacts/{id}` | JWT | Update contact details or tags |
| PATCH | `/api/marketing/contacts/{id}/unsubscribe` | JWT | Manually unsubscribe a contact |
| PATCH | `/api/marketing/contacts/{id}/resubscribe` | JWT Admin | Manually re-subscribe a contact |
| GET | `/api/marketing/segments` | JWT | List all segments |
| POST | `/api/marketing/segments` | JWT | Create new segment |
| GET | `/api/marketing/segments/{id}/contacts` | JWT | Preview contacts in a segment |
| GET | `/api/marketing/campaigns` | JWT | List all campaigns with stats |
| POST | `/api/marketing/campaigns` | JWT | Create new campaign (draft) |
| PUT | `/api/marketing/campaigns/{id}` | JWT | Update campaign content/settings |
| POST | `/api/marketing/campaigns/{id}/send` | JWT | Send or schedule campaign |
| POST | `/api/marketing/campaigns/{id}/send-test` | JWT | Send test email to admin |
| POST | `/api/marketing/campaigns/{id}/pause` | JWT | Pause mid-send campaign |
| POST | `/api/marketing/campaigns/{id}/resume` | JWT | Resume paused campaign |
| POST | `/api/marketing/campaigns/{id}/duplicate` | JWT | Clone campaign as new draft |
| GET | `/api/marketing/campaigns/{id}/report` | JWT | Full analytics for one campaign |
| GET | `/api/marketing/campaigns/{id}/recipients` | JWT | Per-recipient activity table |
| POST | `/api/marketing/webhooks/resend` | Webhook secret | Receive events from Resend |
| GET | `/o/{campaign_id}/{contact_id}/{token}.png` | None (public) | Open tracking pixel |
| GET | `/c/{campaign_id}/{contact_id}/{link_hash}` | None (public) | Click tracking redirect |
| GET | `/unsubscribe/{token}` | None (public) | Unsubscribe confirmation page |
| GET | `/api/marketing/media` | JWT | List media library |
| POST | `/api/marketing/media/upload` | JWT | Upload image to media library |
| DELETE | `/api/marketing/media/{id}` | JWT | Delete image from media library |
| GET | `/api/marketing/analytics/overview` | JWT Admin | Marketing overview dashboard stats |
| GET | `/api/marketing/sequences` | JWT | List all sequences |
| POST | `/api/marketing/sequences` | JWT | Create new sequence |
| PATCH | `/api/marketing/sequences/{id}/toggle` | JWT | Enable or disable sequence |

---

## 13. File Structure

```
eximp-cloves/
├── routers/
│   ├── marketing_contacts.py       ← NEW
│   ├── marketing_campaigns.py      ← NEW
│   ├── marketing_segments.py       ← NEW
│   ├── marketing_analytics.py      ← NEW
│   ├── marketing_sequences.py      ← NEW
│   ├── marketing_webhooks.py       ← NEW (Resend webhook + tracking endpoints)
│   └── marketing_media.py          ← NEW (image upload)
├── marketing_service.py            ← NEW (core send logic, personalisation,
│                                          click wrapping, tracking pixel)
├── templates/
│   ├── marketing_editor.html       ← NEW (GrapesJS full-page editor)
│   ├── marketing_dashboard.html    ← NEW (overview + campaigns list)
│   ├── unsubscribe.html            ← NEW (public unsubscribe page)
│   └── dashboard.html              ← UPDATE (add Marketing nav section)
├── main.py                         ← UPDATE (register new routers)
├── requirements.txt                ← no changes needed (resend already installed)
└── schema.sql                      ← UPDATE (add all new tables)
```

### Register Routers in main.py

```python
from routers import (
    marketing_contacts,
    marketing_campaigns,
    marketing_segments,
    marketing_analytics,
    marketing_sequences,
    marketing_webhooks,
    marketing_media
)

app.include_router(marketing_contacts.router, prefix="/api/marketing/contacts", tags=["marketing"])
app.include_router(marketing_campaigns.router, prefix="/api/marketing/campaigns", tags=["marketing"])
app.include_router(marketing_segments.router, prefix="/api/marketing/segments", tags=["marketing"])
app.include_router(marketing_analytics.router, prefix="/api/marketing/analytics", tags=["marketing"])
app.include_router(marketing_sequences.router, prefix="/api/marketing/sequences", tags=["marketing"])
app.include_router(marketing_webhooks.router, tags=["webhooks"])  # tracking at root level
app.include_router(marketing_media.router, prefix="/api/marketing/media", tags=["marketing"])
```

---

## 14. Dashboard UI

### 14.1 Sidebar Navigation

Add "Marketing" section — **Admin only, entirely hidden from Staff:**
- Overview
- Campaigns
- Contacts
- Segments
- Sequences
- Media Library

### 14.2 Campaign Editor Page

Full-page experience (sidebar collapses or hides):
- **Left panel** — Block library for drag and drop
- **Centre** — Email canvas (GrapesJS, rendered at 600px to simulate inbox)
- **Right panel** — Selected block settings (font, colour, link, padding, etc.)
- **Top toolbar** — Template picker, undo/redo, preview, send test, save draft, next step

"Next Step" advances to the Campaign Settings screen.

### 14.3 Campaign Settings Screen

- Campaign Name (internal — not shown to recipients)
- Subject Line A — with personalisation variable picker
- Subject Line B — only if A/B test enabled
- Preview Text
- From Name — defaults to "Eximp & Cloves" — editable per campaign
- From Email — fixed to `hello@mail.eximps-cloves.com` — shown as read-only, not editable
- Reply-To Email — defaults to `marketing@mail.eximps-cloves.com` — editable per campaign
- BCC — defaults to `marketing@mail.eximps-cloves.com` — editable or clearable per campaign. Shown with a note: "This address receives a silent copy of every email sent. Never visible to recipients."
- Audience — segment selector (multi-select), shows estimated recipient count live
- Send Time — Send Now / Schedule (date + time picker)
- A/B Test toggle

### 14.4 Contact Profile Page

Extends existing client profile (PRD 2):
- Engagement score with tier badge (Hot / Warm / Cold / Dormant)
- Subscription status — subscribed / unsubscribed with date
- Tags — show all, admin can add or remove inline
- Email History — table of all campaigns received, opened, clicked
- Engagement sparkline — score history over time

---

## 15. Email Design Standards

> Based on competitive analysis of Land Republic's email campaigns (a Nigerian real estate competitor). Beat them on every visual dimension while matching their conversational tone.

### What to do better than competitors

| Issue in Competitor Emails | How ECOMS Fixes It |
|---------------------------|-------------------|
| Broken/missing images (question mark placeholder) | Images hosted on CDN, auto-resized to 600px, always load correctly |
| No CTA buttons — everything is plain text | Styled gold CTA buttons in all templates — dramatically improves click rate |
| No visual hierarchy — plain text only | GrapesJS templates with brand colours, hero images, property cards |
| Generic plain footer — no proper address or clear unsubscribe | Branded footer with full company info, unsubscribe link always present |
| No engagement tracking per contact | Full open/click tracking per recipient, engagement scoring, hot lead identification |

### Tone Guidelines

- Keep the **conversational, story-driven tone** that works for Nigerian real estate audiences (e.g. "let's talk real talk", CEO story format)
- Always personalise with `{{first_name}}` in subject line AND email body
- Use a consistent sender persona — e.g. "Tolu from Eximp & Cloves" — not just a company name
- Subject lines should feel personal and curiosity-driven, not corporate: "You're seeing this first, {{first_name}}" outperforms "New Estate Launch"
- Every email must have one clear CTA — not multiple competing links

---

## 16. Testing Checklist

### Contact Management
- [ ] Add single contact manually — appears in contacts list
- [ ] CSV import — valid file imports correctly, shows skipped count for invalid emails
- [ ] CSV import — duplicate emails are not double-inserted
- [ ] Auto-sync from ECOMS clients — when new client is created, appears in marketing contacts
- [ ] Unsubscribe a contact — removed from all future sends, transactional emails unaffected
- [ ] Bounce webhook — contact marked as bounced and suppressed automatically

### Segments
- [ ] Create a dynamic segment with conditions — correct contacts returned
- [ ] Dynamic segment excludes unsubscribed and bounced contacts
- [ ] Segment contact count updates when contacts are added or removed
- [ ] Estimated send count on campaign settings reflects segment size correctly

### Campaign Builder
- [ ] All block types drag-and-drop correctly into the canvas
- [ ] Image block — drag and drop image file onto block, uploads and renders (no broken images)
- [ ] Image block — select from media library works
- [ ] Personalisation variables render correctly in preview
- [ ] Personalisation variables replace correctly per-recipient at send time
- [ ] Missing variables render as blank, not as `{{variable_name}}`
- [ ] Footer unsubscribe link cannot be deleted
- [ ] Header block cannot be deleted
- [ ] Save as draft — reopening draft loads full email content
- [ ] A/B test — two subject lines saved correctly

### Sending
- [ ] Send test email — arrives at admin email, variables shown as-is (not replaced)
- [ ] Send campaign — all contacts in selected segments receive email
- [ ] Unsubscribed contacts do not receive campaign even if in selected segment
- [ ] Bounced contacts do not receive campaign
- [ ] Schedule campaign — does not send until scheduled time
- [ ] Pause mid-send — sending stops, resume continues from where it stopped
- [ ] Pre-send checklist blocks send if subject line is empty

### Tracking
- [ ] Open tracking pixel loads correctly in email
- [ ] Opening email increments `open_count` in `campaign_recipients`
- [ ] Opening email increments contact `engagement_score`
- [ ] Clicking a tracked link redirects to correct destination
- [ ] Click event recorded in `email_click_events` table
- [ ] Click count increments in `campaign_recipients`
- [ ] Resend webhook: delivered event updates status correctly
- [ ] Resend webhook: bounce event suppresses contact immediately
- [ ] Resend webhook: spam complaint suppresses contact immediately
- [ ] Resend webhook: unsubscribe event updates `is_subscribed`

### Analytics
- [ ] Campaign report shows correct open rate and click rate
- [ ] Recipient activity table shows correct per-contact status
- [ ] Click map shows correct click counts per link
- [ ] Device breakdown chart shows accurate data
- [ ] Marketing overview page loads all KPI cards correctly

### Unsubscribe
- [ ] Clicking unsubscribe link in email loads branded unsubscribe page
- [ ] Confirming unsubscribe sets `is_subscribed = false` immediately
- [ ] Unsubscribed contact does not appear in future send counts
- [ ] Unsubscribed contact still receives transactional emails normally
- [ ] Admin can manually re-subscribe with logged reason

---

## 17. Future Migration to SendGrid

When contact list grows beyond ~5,000 or weekly sends exceed 500, migrate the marketing layer to SendGrid:

1. Add `SENDGRID_API_KEY` to environment variables
2. In `marketing_service.py`, swap Resend API calls for SendGrid API calls
3. Update webhook endpoint from `/api/marketing/webhooks/resend` to `/api/marketing/webhooks/sendgrid`
4. Update webhook signature verification to use SendGrid's method
5. Add DNS records for SendGrid domain authentication in GoDaddy
6. No changes needed to the database, frontend, or any other service

Everything else stays identical.

---

_End of PRD 6 — Eximp & Cloves Infrastructure Limited — ECOMS_  
_Read alongside PRD 1 through PRD 5 and the Addendum_