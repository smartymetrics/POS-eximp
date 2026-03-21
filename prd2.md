# Product Requirements Document 3
## Eximp & Cloves Infrastructure Limited — Sales Rep Module, Reports & Scheduled Emails
### Version 1.0

---

## 1. Overview

This PRD covers three interconnected features:

1. **Sales Rep Module** — a full management layer for external sales representatives who currently have no system accounts but are tracked by name on invoices. Designed from the start to support future rep logins without requiring a rebuild.
2. **Reports Module** — downloadable PDF and Excel reports covering revenue, sales performance, client data, and outstanding payments. Two modes: instant internal download and scheduled email delivery to management/investors.
3. **Scheduled Report Emails** — an automated job that sends configured reports to a list of recipients on a configurable schedule (weekly, monthly, custom).

---

## 2. Sales Rep Module

### 2.1 The Core Problem

Sales rep names currently arrive as free text from the Google Form (typed by clients). The same rep may appear as:
- "Funke Adeyemi"
- "funke adeyemi"
- "Miss Funke"
- "Funke A."
- "Funke Adeyemi "  (trailing space)

Without normalisation, analytics will show these as five different people. This PRD introduces a `sales_reps` table and a name-matching system.

### 2.2 Sales Reps Table

```sql
CREATE TABLE IF NOT EXISTS sales_reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    region VARCHAR(100) DEFAULT 'Lagos',   -- future expansion
    is_active BOOLEAN DEFAULT true,
    admin_id UUID REFERENCES admins(id),   -- linked when rep gets login in future
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE sales_reps ENABLE ROW LEVEL SECURITY;

-- Add rep_id foreign key to invoices
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS sales_rep_id UUID REFERENCES sales_reps(id);
```

`sales_rep_name` (text) remains on the `invoices` table as the raw captured value. `sales_rep_id` is the resolved foreign key after matching.

### 2.3 Name Normalisation Logic

When a form submission arrives at the webhook, after saving the invoice the system attempts to match `sales_rep_name` to an existing `sales_reps` record.

**Matching algorithm (Python, backend):**

```python
import re
from difflib import SequenceMatcher

def normalise_name(name: str) -> str:
    """Lowercase, strip whitespace and titles."""
    name = name.lower().strip()
    titles = ['mr.', 'mrs.', 'ms.', 'miss', 'dr.', 'prof.']
    for t in titles:
        name = name.replace(t, '').strip()
    return re.sub(r'\s+', ' ', name)

def find_rep_match(raw_name: str, all_reps: list, threshold: float = 0.75):
    """
    Fuzzy match raw_name against all known rep names.
    Returns the best matching rep dict, or None if no match above threshold.
    """
    norm_input = normalise_name(raw_name)
    best_score = 0
    best_rep = None
    for rep in all_reps:
        norm_rep = normalise_name(rep['full_name'])
        score = SequenceMatcher(None, norm_input, norm_rep).ratio()
        if score > best_score:
            best_score = score
            best_rep = rep
    if best_score >= threshold:
        return best_rep
    return None
```

**Matching outcomes:**
- **Match found (score ≥ 0.75)** → set `invoices.sales_rep_id` to the matched rep's ID
- **No match found** → set `sales_rep_id = NULL`, set `sales_rep_name` to the raw value, create a `unmatched_reps` log entry for admin review

### 2.4 Unmatched Reps Log

```sql
CREATE TABLE IF NOT EXISTS unmatched_reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    raw_name VARCHAR(255) NOT NULL,
    invoice_id UUID REFERENCES invoices(id),
    resolved_rep_id UUID REFERENCES sales_reps(id),
    resolved_by UUID REFERENCES admins(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

When a rep name cannot be matched, a record is inserted here. Admins resolve it from the Sales Rep section of the dashboard by assigning the invoice to the correct rep manually.

### 2.5 Sales Rep Management Page (Admin Only)

**Location in sidebar:** Under "Analytics" nav section — "Sales Reps"

**Page layout:**

**Top section — Rep Cards**
For each active rep, a card showing:
- Rep name and region
- Total deals all-time
- Total value all-time
- This month's deals and value
- "View Profile" button

**Bottom section — Rep Table**
Columns: Name | Phone | Email | Region | Total Deals | Total Value | Active | Actions

Actions per row:
- Edit (update name, phone, email, region)
- Deactivate (soft delete — `is_active = false`)
- View Profile

**"Add Rep" button** (top right) — opens a modal to add a new sales rep manually:
- Full Name (required)
- Phone
- Email
- Region (default: Lagos)

**Unmatched Names Panel**
A collapsible section at the bottom of the page showing all unresolved `unmatched_reps` entries. For each row:
- Raw name captured from form
- Invoice number it came from
- "Assign to Rep" dropdown showing all active reps
- "Create New Rep from This" button
- "Ignore" button (marks as intentionally unmatched — e.g. "N/A" or blank)

### 2.6 Sales Rep Profile Page

Accessible by clicking a rep's name from the leaderboard or the rep management page.

**URL pattern:** Navigated to via JavaScript — no separate route needed. Pass rep ID as a JS state variable.

**Page sections:**

**Header**
- Rep name, region, phone, email
- Active since date (created_at)
- Performance tier badge: Platinum (top 10% by value), Gold (top 30%), Silver (top 60%), Bronze (rest)

**Summary KPI Cards (filtered by timeframe)**
- Total Deals
- Total Value
- Amount Collected from their deals
- Collection Rate
- Avg Deal Size
- Best Month

**Charts**
- Monthly sales bar chart (their deals per month, last 12 months)
- Estate preference doughnut (which estates they sell most)

**Deals Table**
All invoices attributed to this rep. Columns:
Invoice No | Client Name | Estate | Plot Size | Total Value | Deposit | Balance | Status | Date

Filterable by status and date range.

---

## 3. Reports Module

### 3.1 Reports Page (Admin Only)

**Location:** "Reports" in sidebar (Admin only). Staff cannot access this section.

**Page layout:**

A grid of report cards — one per report type. Each card shows:
- Report name
- Description (one line)
- Format options: PDF button and Excel button
- "Schedule" button (to set up automated email delivery)

### 3.2 Report Types

#### Report 1 — Monthly Revenue Report
**Description:** All invoices and payments for a selected month.
**Contents:**
- Summary section: Total invoiced, total collected, outstanding, number of deals
- Invoice-by-invoice breakdown table: Invoice No, Client, Estate, Plot Size, Total Price, Deposit, Balance, Status, Sales Rep
- Payment records table: Payment reference, client, amount, date, method
- Estate summary table: Total revenue per estate for the month
- Sales rep summary table: Total deals and value per rep for the month

**Filter:** Month + Year selector

#### Report 2 — Sales Rep Performance Report
**Description:** All reps ranked by performance for a given period.
**Contents:**
- Period summary: Total deals, total value, total collected across all reps
- Ranked leaderboard table: Rank, Rep Name, Deals, Total Value, Avg Deal Size, Top Estate, Collected, Collection Rate
- Per-rep detail sections: one section per rep with their individual deal list

**Filter:** Timeframe selector (same options as dashboard)

#### Report 3 — Outstanding Payments Report
**Description:** All invoices with unpaid or partial balances.
**Contents:**
- Summary: Total outstanding across all clients, number of clients with balance
- Table: Invoice No, Client Name, Client Phone, Client Email, Estate, Total Price, Amount Paid, Balance Due, Invoice Date, Sales Rep
- Sorted by: Balance Due descending (largest outstanding first)
- Colour coded in PDF: Red rows for overdue (invoice date > 30 days ago and still unpaid), amber for partial

**Filter:** Estate filter, Status filter (unpaid only / partial only / both)

#### Report 4 — Client Register
**Description:** Full list of all registered clients with KYC summary.
**Contents:**
- Table: Full Name, Email, Phone, Address, State, Estate Purchased, Plot Size, Payment Status, Sales Rep, Date Joined, NIN (last 4 digits only for privacy)
- One row per client

**Filter:** Date range (joined between), status, estate

**Note:** PDF version omits NIN entirely. Excel version includes last 4 digits only. Full NIN is never exported.

#### Report 5 — Estate Sales Report
**Description:** Performance breakdown per estate.
**Contents:**
- Per-estate section: Estate name, total deals, total value, total collected, outstanding, avg deal size, list of all clients who bought in that estate
- Summary comparison table at the end

**Filter:** Date range, specific estate or all estates

#### Report 6 — Custom Report
**Description:** User-defined report with configurable columns and filters.
**Contents:** Admin selects:
- Data source: Invoices / Payments / Clients / All
- Columns to include (checkbox list)
- Filters: date range, estate, status, sales rep
- Format: PDF or Excel

This generates a flat table with exactly the chosen columns.

---

### 3.3 Report Generation — Backend

**New router:** `routers/reports.py`

**Register in main.py:**
```python
from routers import reports
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
```

**Endpoints:**

```
GET /api/reports/revenue?month=YYYY-MM&format=pdf|excel       → Admin only
GET /api/reports/rep-performance?start=&end=&format=pdf|excel → Admin only
GET /api/reports/outstanding?estate=&status=&format=pdf|excel → Admin only
GET /api/reports/client-register?start=&end=&estate=&format=pdf|excel → Admin only
GET /api/reports/estate-sales?start=&end=&estate=&format=pdf|excel → Admin only
POST /api/reports/custom → Admin only (body contains column/filter config)
```

All endpoints return a file download response with appropriate `Content-Disposition` headers:
- PDF: `Content-Type: application/pdf`
- Excel: `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

**PDF generation:** Use the existing `xhtml2pdf` pattern. Create HTML templates for each report in `pdf_templates/reports/`.

**Excel generation:** Use `openpyxl` library.

```
pip install openpyxl
```

Add `openpyxl` to `requirements.txt`.

**Excel styling:**
- Header row: dark background (`1A1A1A`), gold text (`F5A623`), bold
- Alternating row colours: white and light grey (`F9F9F9`)
- Company name and report title in the first two rows
- Auto-column width
- Freeze top row (header row)
- Number columns formatted as NGN currency (no symbol — just comma-formatted numbers)
- Date columns formatted as DD/MM/YYYY

**PDF report styling:**
- Same branding as invoice/receipt templates (gold header bar, company logo text, footer)
- Tables use the existing styling pattern
- Page numbers in footer: "Page X of Y"
- Report title, period, and generated date/time in the header

---

### 3.4 Report Templates (xhtml2pdf)

Create a base report template that all reports extend:

**File:** `pdf_templates/reports/base_report.html`
```html
<!-- Shared header, footer, and table styles for all reports -->
<!-- Header: company logo + report title + period + generated date -->
<!-- Footer: company address + page number -->
<!-- Table: dark header row, alternating rows, NGN formatting -->
```

Each report has its own template inheriting from this base:
- `pdf_templates/reports/revenue_report.html`
- `pdf_templates/reports/rep_performance_report.html`
- `pdf_templates/reports/outstanding_report.html`
- `pdf_templates/reports/client_register_report.html`
- `pdf_templates/reports/estate_sales_report.html`

---

## 4. Scheduled Report Emails

### 4.1 Overview

Admins configure reports to be automatically emailed to a list of recipients on a schedule. Examples:
- Every Monday at 8am → Outstanding Payments Report → finance@eximps-cloves.com
- First day of each month → Monthly Revenue Report → CEO email, investor email
- Every Friday at 5pm → Sales Rep Performance (This Week) → management email

### 4.2 Report Schedule Table

```sql
CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_type VARCHAR(100) NOT NULL,
    schedule_type VARCHAR(50) NOT NULL
        CHECK (schedule_type IN ('weekly', 'monthly', 'custom_cron')),
    schedule_day INTEGER,       -- 1-7 for weekly (1=Monday), 1-31 for monthly
    schedule_time TIME DEFAULT '08:00:00',
    format VARCHAR(10) DEFAULT 'pdf' CHECK (format IN ('pdf', 'excel', 'both')),
    recipients JSONB NOT NULL,  -- array of email addresses
    filters JSONB,              -- report-specific filters (estate, status, etc.)
    subject_template VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES admins(id),
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE report_schedules ENABLE ROW LEVEL SECURITY;
```

**Example recipients JSONB:**
```json
["ceo@eximps-cloves.com", "investor1@email.com", "finance@eximps-cloves.com"]
```

**Example filters JSONB:**
```json
{"estate": "Coinfield Estate", "status": "unpaid"}
```

### 4.3 Scheduled Report Management UI

A **"Scheduled Reports"** sub-section on the Reports page. Shows a table of all configured schedules:

Columns: Report Type | Schedule | Recipients | Format | Last Sent | Status | Actions

Actions: Edit | Pause/Resume | Send Now (manual trigger) | Delete

**"Add Schedule" button** opens a modal:

1. Select report type (dropdown of all 6 report types)
2. Select format (PDF / Excel / Both)
3. Schedule:
   - Weekly → day of week selector (Mon–Sun) + time picker
   - Monthly → day of month selector (1–28) + time picker
4. Recipients — text inputs for email addresses (add/remove dynamically, max 10)
5. Subject line template — with variables: `{report_name}`, `{period}`, `{date}`
   - Default: `"Eximp & Cloves — {report_name} — {period}"`
6. Save

### 4.4 Scheduler Implementation (APScheduler)

Use `APScheduler` to run scheduled jobs within the FastAPI process.

```
pip install apscheduler
```

Add `apscheduler` to `requirements.txt`.

**Setup in main.py:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    await init_db()
    await load_report_schedules()  # Load all active schedules from DB
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
```

**Loading schedules from DB:**
```python
async def load_report_schedules():
    """Load all active schedules from DB and register with APScheduler."""
    db = get_db()
    schedules = db.table("report_schedules").select("*").eq("is_active", True).execute()
    for sched in schedules.data:
        register_schedule(sched)

def register_schedule(sched: dict):
    """Register a single schedule with APScheduler."""
    if sched['schedule_type'] == 'weekly':
        trigger = CronTrigger(
            day_of_week=sched['schedule_day'] - 1,  # APScheduler: 0=Monday
            hour=sched['schedule_time'].split(':')[0],
            minute=sched['schedule_time'].split(':')[1]
        )
    elif sched['schedule_type'] == 'monthly':
        trigger = CronTrigger(
            day=sched['schedule_day'],
            hour=sched['schedule_time'].split(':')[0],
            minute=sched['schedule_time'].split(':')[1]
        )
    scheduler.add_job(
        send_scheduled_report,
        trigger=trigger,
        args=[sched['id']],
        id=str(sched['id']),
        replace_existing=True
    )
```

**When a schedule is created or edited via the API**, call `register_schedule()` immediately so the new schedule takes effect without restarting the server.

**When a schedule is deleted or paused**, call `scheduler.remove_job(str(sched_id))`.

### 4.5 Scheduled Report Email Function

```python
async def send_scheduled_report(schedule_id: str):
    """
    Called by APScheduler at the configured time.
    Generates the report, emails it to all recipients.
    """
    db = get_db()
    sched = db.table("report_schedules").select("*").eq("id", schedule_id).execute().data[0]

    # Determine date range based on schedule type
    today = date.today()
    if sched['schedule_type'] == 'weekly':
        start = today - timedelta(days=7)
        period_label = f"Week of {start.strftime('%d %b %Y')}"
    elif sched['schedule_type'] == 'monthly':
        first = today.replace(day=1)
        start = (first - timedelta(days=1)).replace(day=1)
        period_label = start.strftime('%B %Y')

    # Generate report file(s)
    report_bytes = await generate_report(sched['report_type'], start, today, sched['filters'], sched['format'])

    # Build subject
    subject = sched.get('subject_template', 'Eximp & Cloves — {report_name} — {period}')
    subject = subject.replace('{report_name}', sched['report_type'].replace('_', ' ').title())
    subject = subject.replace('{period}', period_label)
    subject = subject.replace('{date}', today.strftime('%d %b %Y'))

    # Send to all recipients
    for recipient in sched['recipients']:
        resend.Emails.send({
            "from": f"Eximp & Cloves Reports <{FROM_EMAIL}>",
            "to": [recipient],
            "subject": subject,
            "html": build_scheduled_report_email_html(sched['report_type'], period_label),
            "attachments": report_bytes  # list of {filename, content} dicts
        })

    # Update last_sent_at
    db.table("report_schedules").update({"last_sent_at": datetime.utcnow().isoformat()}).eq("id", schedule_id).execute()
```

### 4.6 Scheduled Report Email Body Template

A clean, simple email:

**Subject:** `Eximp & Cloves — Monthly Revenue Report — March 2026`

**Body:**
> Dear Team,
>
> Please find attached the **[Report Name]** for **[Period]**.
>
> [Summary table with 3-4 key numbers from the report — e.g. Total Revenue: NGN X,XXX,XXX | Deals: 14 | Collected: NGN X,XXX,XXX]
>
> This report was automatically generated and sent by the Eximp & Cloves Finance System.
>
> [Footer with company address]

The summary numbers in the email body are generated at the same time as the report, so they match the attached document exactly.

---

## 5. New API Endpoints Summary

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/sales-reps/` | List all reps | Admin |
| POST | `/api/sales-reps/` | Create new rep | Admin |
| PUT | `/api/sales-reps/{id}` | Update rep | Admin |
| PATCH | `/api/sales-reps/{id}/deactivate` | Deactivate rep | Admin |
| GET | `/api/sales-reps/{id}/profile` | Rep profile + stats | Admin |
| GET | `/api/sales-reps/unmatched` | List unmatched names | Admin |
| PATCH | `/api/sales-reps/unmatched/{id}/resolve` | Assign to rep | Admin |
| GET | `/api/reports/revenue` | Generate revenue report | Admin |
| GET | `/api/reports/rep-performance` | Generate rep report | Admin |
| GET | `/api/reports/outstanding` | Generate outstanding report | Admin |
| GET | `/api/reports/client-register` | Generate client register | Admin |
| GET | `/api/reports/estate-sales` | Generate estate report | Admin |
| POST | `/api/reports/custom` | Generate custom report | Admin |
| GET | `/api/report-schedules/` | List all schedules | Admin |
| POST | `/api/report-schedules/` | Create new schedule | Admin |
| PUT | `/api/report-schedules/{id}` | Update schedule | Admin |
| PATCH | `/api/report-schedules/{id}/toggle` | Pause / resume | Admin |
| POST | `/api/report-schedules/{id}/send-now` | Manual trigger | Admin |
| DELETE | `/api/report-schedules/{id}` | Delete schedule | Admin |

---

## 6. New Pydantic Models

Add to `models.py`:

```python
class SalesRepCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    region: str = "Lagos"

class SalesRepUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None

class UnmatchedRepResolve(BaseModel):
    rep_id: str  # UUID of the sales_reps record to assign this to

class ReportScheduleCreate(BaseModel):
    report_type: str
    schedule_type: str  # weekly | monthly
    schedule_day: int
    schedule_time: str  # HH:MM
    format: str = "pdf"  # pdf | excel | both
    recipients: list[str]
    filters: Optional[dict] = None
    subject_template: Optional[str] = None

class ReportScheduleUpdate(BaseModel):
    schedule_day: Optional[int] = None
    schedule_time: Optional[str] = None
    format: Optional[str] = None
    recipients: Optional[list[str]] = None
    filters: Optional[dict] = None
    subject_template: Optional[str] = None
    is_active: Optional[bool] = None
```

---

## 7. Dashboard UI Changes

### Sidebar additions
- Under **Analytics**: "Sales Reps" (Admin only)
- Under main nav: "Reports" (Admin only)

### Reports page
- Grid of 6 report cards
- Each card: name, description, PDF button, Excel button, Schedule button
- "Scheduled Reports" collapsible section below the grid

### Sales Reps page
- Rep cards row (one per active rep)
- Full rep table
- Add Rep modal
- Unmatched Names collapsible panel

### Rep Profile page
- Navigated to from leaderboard or rep table
- Header with rep info and tier badge
- KPI cards (filtered by timeframe)
- Two charts (monthly sales bar, estate doughnut)
- Deals table

---

## 8. File Structure Changes

```
eximp-cloves/
├── routers/
│   ├── reports.py          ← NEW
│   └── sales_reps.py       ← NEW
├── pdf_templates/
│   └── reports/            ← NEW directory
│       ├── base_report.html
│       ├── revenue_report.html
│       ├── rep_performance_report.html
│       ├── outstanding_report.html
│       ├── client_register_report.html
│       └── estate_sales_report.html
├── report_service.py       ← NEW — report generation logic (PDF + Excel)
├── scheduler.py            ← NEW — APScheduler setup and job functions
├── models.py               ← UPDATE
├── main.py                 ← UPDATE — register new routers, start scheduler
├── requirements.txt        ← UPDATE — add openpyxl, apscheduler
└── schema.sql              ← UPDATE — new tables
```

---

## 9. Requirements.txt Additions

```
openpyxl==3.1.2
apscheduler==3.10.4
```

---

## 10. Future-Proofing Notes

### Rep Login (Future)
The `sales_reps` table has an `admin_id` column that will link to the `admins` table when reps get login access. The migration path is:
1. Create an admin account for the rep (role = "rep" — add this to the CHECK constraint)
2. Set `sales_reps.admin_id` = their admin account ID
3. Build the rep-facing dashboard (a restricted view showing only their own data)

The analytics endpoints already filter by `sales_rep_id` — adding a "rep" role that can only see their own rep ID in the query is a small change.

### Multiple Offices (Future)
The `sales_reps.region` field and the proposed `branch` field on invoices (mentioned in PRD 2) mean analytics can be split by office/branch with a simple filter addition. No schema migration needed.

### Client Portal (Future)
The `clients` table already stores email. Adding auth for clients means:
1. A `client_auth` table (email + password hash + client_id)
2. A separate login route for clients
3. A read-only portal showing their invoices, receipts, and statements
4. No changes to existing admin auth or data structures

---

## 11. Testing Checklist

### Sales Reps
- [ ] Add a new rep manually from the dashboard
- [ ] Submit a Google Form with a known rep name → confirm it matches and `sales_rep_id` is set
- [ ] Submit a form with a misspelled rep name → confirm it appears in unmatched panel
- [ ] Resolve an unmatched name by assigning to correct rep
- [ ] Deactivate a rep → confirm they no longer appear in leaderboard
- [ ] Rep profile page shows correct stats for selected timeframe
- [ ] Rep profile deals table filters correctly by status and date

### Reports
- [ ] Generate Monthly Revenue Report as PDF → download works
- [ ] Generate Monthly Revenue Report as Excel → download works, formatting correct
- [ ] Excel header row has dark background and gold text
- [ ] Excel columns auto-sized
- [ ] Outstanding report shows correct balance calculations
- [ ] Client register does NOT expose full NIN
- [ ] Custom report generates with only selected columns

### Scheduled Emails
- [ ] Create a weekly schedule → confirm job registered in APScheduler
- [ ] "Send Now" button → report email arrives at recipients
- [ ] Pause a schedule → job removed from scheduler
- [ ] Resume a schedule → job re-registered
- [ ] Delete a schedule → job removed and record deleted
- [ ] After server restart → all active schedules re-registered from DB
- [ ] `last_sent_at` updates after each send
- [ ] Recipients receive email with correct subject and report attached
- [ ] Summary numbers in email body match the attached report

---

*End of PRD 3 — Eximp & Cloves Infrastructure Limited Sales Rep Module & Reports*