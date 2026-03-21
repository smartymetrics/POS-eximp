# Product Requirements Document — Addendum
## Eximp & Cloves Infrastructure Limited
### Post-PRD3 Changes & Additions
### Version 1.0

---

## Overview

This document covers all feature additions and clarifications discussed after PRD 3 was written. It should be read alongside PRD 1, PRD 2, and PRD 3 — not as a standalone document. Where this addendum conflicts with any earlier PRD, this document takes precedence.

---

## 1. Invoice Due Date for Installment Clients

### 1.1 The Requirement

Every invoice must have a `due_date` representing when the full outstanding balance must be cleared. For outright payments, the due date equals the payment date. For installment clients, the due date is calculated by adding the payment duration (in months) to the deposit date.

### 1.2 Due Date Calculation

Add `python-dateutil` to `requirements.txt`:
```
python-dateutil==2.9.0
```

Add this utility function to the webhook handler (`routers/webhooks.py`):

```python
from dateutil.relativedelta import relativedelta
from datetime import datetime

def calculate_due_date(payment_date_str: str, payment_duration: str) -> str:
    """
    Calculate final due date from deposit date + installment duration.

    payment_date_str:  "3/18/2026" (Google Form format MM/DD/YYYY)
    payment_duration:  "3 months", "6 months", "Outright", etc.

    Returns: ISO date string "YYYY-MM-DD"
    """
    if not payment_duration or payment_duration.strip().lower() == "outright":
        try:
            base = datetime.strptime(payment_date_str.strip(), "%m/%d/%Y")
            return base.strftime("%Y-%m-%d")
        except:
            return payment_date_str

    try:
        months = int(
            payment_duration.lower()
            .replace("months", "")
            .replace("month", "")
            .strip()
        )
        base = datetime.strptime(payment_date_str.strip(), "%m/%d/%Y")
        due = base + relativedelta(months=months)
        return due.strftime("%Y-%m-%d")
    except:
        return payment_date_str
```

Call this function in the webhook handler when building the invoice payload:

```python
due_date = calculate_due_date(
    payment_date_str=data.payment_date,
    payment_duration=data.payment_duration
)
```

Pass `due_date` when inserting the invoice into Supabase.

### 1.3 Invoice Status — Four States

The invoice `status` field must support four values. Update the CHECK constraint in the schema:

```sql
ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_status_check;
ALTER TABLE invoices ADD CONSTRAINT invoices_status_check
    CHECK (status IN ('unpaid', 'partial', 'paid', 'overdue'));
```

Status must be **resolved dynamically** at query time — never stored as "overdue" permanently, because an invoice becomes overdue overnight without any system action. Add a helper function to the backend that is called whenever invoice data is returned to the frontend:

```python
from datetime import date

def resolve_invoice_status(invoice: dict) -> str:
    """
    Dynamically calculate the correct status for an invoice.
    Overrides the stored status if the due date has passed.
    """
    balance = float(invoice.get("balance_due") or 0)
    amount_paid = float(invoice.get("amount_paid") or 0)
    due_date_str = invoice.get("due_date")

    if balance <= 0:
        return "paid"

    if due_date_str:
        try:
            due = date.fromisoformat(str(due_date_str))
            if date.today() > due:
                return "overdue"
        except:
            pass

    if amount_paid > 0:
        return "partial"

    return "unpaid"
```

Apply this function in every endpoint that returns invoice data before sending the response.

### 1.4 Invoice PDF — Due Date Display

Update `pdf_templates/invoice.html` to show the due date clearly in the invoice details block:

```
Invoice Date:     20 Mar 2026
Payment Plan:     3 Months Installment
Deposit Date:     20 Mar 2026
Final Due Date:   20 Jun 2026        ← new line
```

For outright payments, show:
```
Invoice Date:     20 Mar 2026
Payment Terms:    Outright
Due Date:         20 Mar 2026
```

### 1.5 Dashboard — Outstanding KPI Card Update (PRD 2 Addition)

Update the Outstanding Balance KPI card (from PRD 2) to include an overdue sub-label:

```
Outstanding Balance
NGN 3,450,000.00
↳ 3 overdue · 8 partial
```

The overdue count is returned from the `/api/analytics/kpis` endpoint. Add `overdue_count` and `partial_count` to the KPI response:

```json
{
  "outstanding_balance": 3450000,
  "overdue_count": 3,
  "partial_count": 8,
  ...
}
```

### 1.6 Payment Status Doughnut Chart (PRD 2 Addition)

Update the Payment Status doughnut chart (from PRD 2) to show four segments:

| Segment | Colour |
|---|---|
| Paid | Green `#2ecc71` |
| Partial | Amber `#f39c12` |
| Unpaid | Blue `#3498db` |
| Overdue | Red `#e74c3c` |

Update the `/api/analytics/payment-status` endpoint response:

```json
{
  "paid": 8,
  "partial": 4,
  "unpaid": 2,
  "overdue": 3
}
```

### 1.7 Outstanding Payments Report (PRD 3 Addition)

Update the Outstanding Payments Report (PRD 3, Report 3) to include:

- A **"Days Overdue"** column — calculated as `today - due_date` for overdue invoices, blank for non-overdue
- Sort order: overdue invoices first (sorted by days overdue descending), then partial, then unpaid
- In the PDF version: overdue rows highlighted with a light red background (`#fdecea`)
- In the Excel version: overdue rows with red font in the "Days Overdue" column

---

## 2. Google Form — One Submission Per Client Clarification

### 2.1 Clarification

Every client fills the Google Form **exactly once**. There is no scenario where the same client resubmits the form. Subsequent installment payments are handled entirely through the admin dashboard (admin manually records payments via the "Record Payment" modal).

### 2.2 Impact on Webhook Logic

Remove the "find existing invoice" logic that was discussed as a possibility. The webhook should always:

1. Create or update the client record (upsert by email)
2. **Always create a new invoice** — never attach to an existing one
3. Create a new pending verification
4. Send invoice email to client
5. Send admin alert email

There is no duplicate invoice risk because each form submission is a unique property purchase.

---

## 3. Properties — Archive, Restore, and Edit

### 3.1 Schema Changes

```sql
-- Add missing columns to properties table
ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT false;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS available_plot_sizes TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS description TEXT;

-- Rename total_price to starting_price for clarity
-- Only run if column exists as total_price
ALTER TABLE properties RENAME COLUMN total_price TO starting_price;
```

### 3.2 Starting Price — Behaviour and Labelling

The `starting_price` column is **reference data only** — it is never enforced on any invoice. Its sole purposes are:

1. **Auto-fill helper** — when admin creates a manual invoice and selects a property from the dropdown, the price field pre-fills with `starting_price`. Admin can change it freely before saving.
2. **Quick reference** — staff can see current pricing on the Properties page without asking management.

The UI must display this label next to the starting price field everywhere it appears:

> *"Reference only — actual invoice price is set per transaction and may differ."*

This label must appear:
- On the Properties page (next to the price column header)
- In the Add/Edit Property modal (below the price input field)
- In the New Invoice modal (below the pre-filled amount field as a hint)

### 3.3 Updated Pydantic Models

Update `models.py`:

```python
class PropertyCreate(BaseModel):
    name: str
    location: str
    estate_name: Optional[str] = None
    description: Optional[str] = None
    available_plot_sizes: Optional[str] = None  # e.g. "300 sqm, 500 sqm, 1000 sqm"
    starting_price: Optional[Decimal] = None
    is_active: bool = True

class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    estate_name: Optional[str] = None
    description: Optional[str] = None
    available_plot_sizes: Optional[str] = None
    starting_price: Optional[Decimal] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
```

### 3.4 New and Updated API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/properties/` | List active properties | JWT |
| GET | `/api/properties/archived` | List archived properties | JWT |
| POST | `/api/properties/` | Create new property | JWT |
| PUT | `/api/properties/{id}` | Edit property details | JWT |
| PATCH | `/api/properties/{id}/archive` | Archive a property | JWT |
| PATCH | `/api/properties/{id}/restore` | Restore archived property | JWT |

The existing `GET /api/properties/` endpoint must only return properties where `is_archived = false`. A separate endpoint handles archived properties.

### 3.5 Properties Page — Updated UI

**Active properties section:**

Table columns:
| Estate Name | Location | Plot Sizes | Starting Price | Status | Actions |
|---|---|---|---|---|---|

Starting Price column header must include a tooltip or sub-label: *"Reference only"*

Actions per active property row:
- **Edit** — opens edit modal
- **Archive** — opens confirmation modal

**Edit Property Modal:**

Fields:
- Estate Name (required)
- Location (required)
- Description (optional, textarea)
- Available Plot Sizes (optional, e.g. "300 sqm, 500 sqm")
- Starting Price (optional, number input)
- Label below starting price input: *"Reference only — actual invoice price may differ"*

**Archive Confirmation Modal:**

> "Are you sure you want to archive [Estate Name]? It will no longer appear in the invoice creation dropdown. All existing invoices referencing this estate are unaffected."

Buttons: Cancel | Archive

**Archived properties section:**

Collapsible section at the bottom of the page — same pattern as archived team members in the Team Management page. Shows a count badge next to the section header.

Columns: Estate Name | Location | Archived Date | Actions

Actions per archived row:
- **Restore** — restores to active immediately, no confirmation needed, shows success toast

**Invoice Creation Dropdown:**

The property dropdown in the New Invoice modal must only show properties where `is_archived = false AND is_active = true`. Archived or inactive properties must never appear in this dropdown.

---

## 4. Sales Rep — Edit Functionality Confirmation

This was already specified in PRD 3 (Section 2.5, Actions per row: Edit) and the `SalesRepUpdate` Pydantic model in Section 6. This addendum confirms the edit modal fields explicitly:

**Edit Sales Rep Modal fields:**
- Full Name (required)
- Phone Number (optional)
- Email Address (optional)
- Region (optional, default "Lagos")

No other fields are editable from the dashboard. The `admin_id` link (for future rep login) is set programmatically, not manually.

The edit button must be visible for both **active and inactive** reps so admin can correct a name spelling even on a deactivated rep.

---

## 5. Summary of All Files Changed by This Addendum

```
requirements.txt          → Add python-dateutil==2.9.0
schema.sql                → Update invoices status CHECK constraint
                          → Add is_archived, available_plot_sizes,
                            description to properties
                          → Rename total_price → starting_price
models.py                 → Update PropertyCreate, PropertyUpdate
routers/webhooks.py       → Add calculate_due_date() function
                          → Remove "find existing invoice" logic
                          → Pass due_date when creating invoice
routers/invoices.py       → Apply resolve_invoice_status() to all
                            invoice query responses
routers/properties.py     → Add archive, restore, archived list endpoints
                          → Update edit endpoint
routers/analytics.py      → Add overdue_count, partial_count to KPI response
                          → Add overdue segment to payment-status endpoint
pdf_templates/invoice.html → Add due date / final due date display
templates/dashboard.html  → Update Properties section UI
                          → Add archive/restore buttons and modals
                          → Add edit modal for properties
                          → Update outstanding KPI card sub-label
                          → Update payment status chart to 4 segments
```

---

## 6. Testing Checklist

- [ ] Submit Google Form → invoice created with correct `due_date` (deposit date + payment duration months)
- [ ] Submit Google Form with "Outright" payment → `due_date` equals `payment_date`
- [ ] Invoice with passed due date and outstanding balance → status resolves to "overdue" dynamically
- [ ] Invoice with balance paid in full → status resolves to "paid" regardless of due date
- [ ] Invoice PDF shows "Final Due Date" line for installment, "Due Date" for outright
- [ ] Outstanding KPI card shows overdue count and partial count sub-label
- [ ] Payment status doughnut shows 4 segments (paid, partial, unpaid, overdue)
- [ ] Outstanding Payments Report shows Days Overdue column, overdue rows sorted first
- [ ] Properties page shows edit button per row → modal pre-fills with existing data
- [ ] Editing a property updates all fields correctly
- [ ] Archive button shows confirmation modal with correct estate name
- [ ] Archived property disappears from active properties table
- [ ] Archived property appears in collapsible archived section
- [ ] Archived property does NOT appear in invoice creation dropdown
- [ ] Restore button restores property to active list immediately
- [ ] Starting price label "Reference only" appears in properties table, edit modal, and new invoice modal
- [ ] Edit Sales Rep modal pre-fills with existing rep data
- [ ] Editing rep name updates the display on the leaderboard and rep profile page

---

## 7. Admin-Editable Fields Across All Entities

This section specifies every field that should be editable after creation, who can edit it, and how.

---

### 7.1 Invoice Editable Fields

Accessible via an **"Edit Invoice"** button on the invoice row and invoice detail view. Only visible when `status ≠ 'paid'` — a fully paid invoice is locked and cannot be edited.

| Field | Who Can Edit | Notes |
|---|---|---|
| Due date | Admin + Staff | Staff must provide a mandatory reason. Logged in `due_date_changes` table. |
| Payment terms | Admin only | e.g. change "3 Months" to "6 Months". Logged in `activity_log`. |
| Notes | Admin + Staff | Internal notes not shown on client-facing documents. |
| Sales rep name | Admin only | Correct if client typed wrong rep name on form. Updates `sales_rep_name` and re-runs fuzzy match to update `sales_rep_id`. |
| Property name | Admin only | Fix typo or wrong estate. Logged in `activity_log`. |

**Edit Invoice Modal fields (what the modal shows):**
- Due Date (date picker) — with label "Final payment due date"
- Payment Terms (text input or dropdown)
- Sales Rep Name (text input)
- Property Name (text input)
- Notes (textarea — multi-line)

**Backend endpoint:**
```
PATCH /api/invoices/{id}/edit
Body: {
  "due_date": "2026-07-04",
  "payment_terms": "6 months",
  "sales_rep_name": "Funke Adeyemi",
  "property_name": "Coinfield Estate",
  "notes": "Client called 15 Apr, extension granted",
  "reason": "Client requested extension"   ← required if due_date changes
}
Auth: JWT — role checked per field in backend
```

The backend must enforce field-level role restrictions:
- If `payment_terms`, `sales_rep_name`, or `property_name` are in the request body and the caller is Staff → return `403`
- `due_date` and `notes` are allowed for both roles

---

### 7.2 Client Editable Fields

Accessible via an **"Edit Client"** button on the client row and client profile page. Available to both Admin and Staff.

| Field | Who Can Edit |
|---|---|
| Full name | Admin + Staff |
| Email address | Admin only — changing email affects document delivery |
| Phone number | Admin + Staff |
| Residential address | Admin + Staff |
| Occupation | Admin + Staff |
| Marital status | Admin + Staff |
| Nationality | Admin + Staff |
| Next of kin name | Admin + Staff |
| Next of kin phone | Admin + Staff |
| Next of kin email | Admin + Staff |
| Next of kin occupation | Admin + Staff |
| Next of kin relationship | Admin + Staff |
| Next of kin address | Admin + Staff |
| NIN / ID Number | Admin only — sensitive KYC data |
| Passport photo URL | Admin only |
| ID document URL | Admin only |

**Backend endpoint:**
```
PUT /api/clients/{id}
Body: { all editable fields as optional }
Auth: JWT — role checked per field in backend
```

Email and KYC fields return `403` if caller is Staff.

---

### 7.3 Payment Editable Fields

Accessible via an **"Edit"** button on each payment row within an invoice detail view. Admin only — Staff cannot edit recorded payments.

| Field | Notes |
|---|---|
| Payment date | Correct if entered wrongly |
| Payment reference | Fix typo in teller/transfer ref |
| Payment method | Correct if wrong method selected |
| Amount | Admin only — changing amount triggers recalculation of `invoice.amount_paid` and `invoice.balance_due` and `invoice.status` |
| Notes | Add context |

**Important:** When `amount` is edited, the backend must:
1. Update the payment record
2. Recalculate `invoices.amount_paid` = sum of all non-voided payments for this invoice
3. Recalculate `invoices.balance_due` = `invoices.amount` − `invoices.amount_paid`
4. Recalculate `invoices.status` using `resolve_invoice_status()`
5. Log the change in `activity_log`

**Backend endpoint:**
```
PATCH /api/payments/{id}
Body: {
  "payment_date": "2026-03-20",
  "reference": "TXN-8821944",
  "payment_method": "Bank Transfer",
  "amount": 250000,
  "notes": "Corrected teller reference"
}
Auth: JWT — Admin only
```

---

### 7.4 Pending Verification Editable Fields

Accessible via an **"Edit"** button on each pending verification row. Admin + Staff.

| Field | Who Can Edit | Notes |
|---|---|---|
| Payment proof URL | Admin + Staff | Replace blurry proof with clearer one client resent |
| Deposit amount | Admin only | Correct if client typed wrong amount on form |
| Payment date | Admin only | Correct if client entered wrong date |

**Backend endpoint:**
```
PATCH /api/verifications/{id}/edit
Body: {
  "payment_proof_url": "https://drive.google.com/...",
  "deposit_amount": 200000,
  "payment_date": "2026-03-18"
}
Auth: JWT — role checked per field
```

---

### 7.5 Due Date Change — Staff Permission

Staff **can** change invoice due dates. This decision is based on operational practicality — staff are the primary point of contact with clients and should not need to escalate routine extension requests to admin.

**Rules:**
- A reason is **mandatory** for all due date changes regardless of role
- Minimum 10 characters for the reason field
- Every change is logged in `due_date_changes` table with: old date, new date, reason, changed by, timestamp
- Admins can view the full `due_date_changes` log from the invoice detail view
- The reason field placeholder text: *"e.g. Client requested 2-week extension, confirmed via call"*

---

## 8. Role-Based UI — Complete Hidden Elements Specification

### 8.1 Implementation Pattern

A single CSS class `admin-only` is applied to every element that should be completely invisible to Staff. A JavaScript function runs immediately after `checkAuth()` resolves and hides all such elements if the current user is Staff.

```javascript
function applyRoleRestrictions(role) {
  if (role !== 'admin') {
    // Hide every element marked admin-only
    document.querySelectorAll('.admin-only').forEach(el => {
      el.style.display = 'none';
      el.setAttribute('aria-hidden', 'true');
    });

    // Redirect if staff tries to access admin-only section directly
    const adminSections = ['team', 'analytics-revenue', 'analytics-clients',
                           'analytics-estates', 'reports', 'sales-reps'];
    adminSections.forEach(section => {
      const el = document.getElementById('section-' + section);
      if (el) el.style.display = 'none';
    });
  }
}
```

Call this in `checkAuth()` after the role is known:

```javascript
async function checkAuth() {
  // ... existing auth code ...
  currentUserRole = admin.role;
  applyRoleRestrictions(admin.role);  // ← add this line
}
```

The backend **always** enforces role restrictions independently via JWT role checks. Frontend hiding is purely for UX — a Staff member should never see a button they cannot use. The real security gate is always the API.

---

### 8.2 Complete `admin-only` Elements List

Every element below must have `class="admin-only"` (or include it in existing class list) in `dashboard.html`.

**Sidebar Navigation Items**
```
- Team Members nav item
- Analytics nav section label
- Revenue Analysis nav item
- Client Analysis nav item
- Estate Analysis nav item
- Reports nav item
- Sales Reps nav item
```

**Dashboard KPI Cards (entire cards)**
```
- Total Revenue card
- Amount Collected card
- Outstanding Balance card
- Avg Deal Size card
- Collection Rate card
```

**Dashboard Charts (entire chart containers)**
```
- Revenue Trend chart container
- Estate Breakdown chart container
- Payment Status chart container
- Referral Sources chart container
```

**Dashboard Sections**
```
- Sales Rep Leaderboard section (entire div)
```

**Invoices Table — Action Buttons**
```
- "Void Receipt" button (per row)
- "Edit Payment Terms" option in edit modal
- "Edit Sales Rep" option in edit modal
- "Edit Property Name" option in edit modal
```

**Invoice Edit Modal — Fields**
```
- Payment Terms field + label
- Sales Rep Name field + label
- Property Name field + label
```

**Payments — Actions**
```
- "Edit Payment" button (entire payments edit functionality)
```

**Pending Verifications**
```
- "Edit Deposit Amount" field in edit modal
- "Edit Payment Date" field in edit modal
```

**Clients**
```
- "Edit Email" field in client edit modal
- NIN / ID Number field in client edit modal
- Passport Photo URL field in client edit modal
- ID Document URL field in client edit modal
```

**Team Management**
```
- Entire #section-team div
```

**Reports**
```
- Entire #section-reports div (if it exists as a section)
- Reports nav item
```

**Analytics**
```
- Entire #section-analytics-revenue div
- Entire #section-analytics-clients div
- Entire #section-analytics-estates div
```

---

### 8.3 Staff-Only Elements

Conversely, some elements should only be visible to Staff and hidden from Admins. Use class `staff-only` for these.

Currently there are none — but this class should be available for future use if Staff-specific UI elements are needed (e.g. a "Request Admin Approval" button for actions that exceed Staff permissions).

---

### 8.4 Role Badge in Sidebar

The existing sidebar footer shows the logged-in user's name and role. Update the role display to be visually distinct:

**Admin:**
```
Role badge: gold background, dark text — "Admin"
```

**Staff:**
```
Role badge: blue background, white text — "Staff"
```

This makes it immediately obvious to the user what role they are operating under, reducing confusion if someone has multiple accounts.

```javascript
// In checkAuth(), after role is known:
const roleEl = document.getElementById('adminRole');
if (admin.role === 'admin') {
  roleEl.innerHTML = '<span style="background:var(--gold);color:var(--dark);padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">Admin</span>';
} else {
  roleEl.innerHTML = '<span style="background:#3498db;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">Staff</span>';
}
```

---

### 8.5 Section Guard Function

Add a guard to `showSection()` so if a Staff user somehow triggers navigation to an admin-only section (e.g. via browser console), they are silently redirected to the dashboard instead of seeing a broken page:

```javascript
const ADMIN_ONLY_SECTIONS = [
  'team', 'analytics-revenue', 'analytics-clients',
  'analytics-estates', 'reports', 'sales-reps'
];

function showSection(name) {
  // Guard: redirect Staff away from admin sections
  if (ADMIN_ONLY_SECTIONS.includes(name) && currentUserRole !== 'admin') {
    toast('You do not have permission to access this section', 'error');
    showSection('dashboard');
    return;
  }
  // ... rest of existing showSection() code ...
}
```

---

## 9. Updated Testing Checklist (Sections 7 and 8)

### Editable Fields
- [ ] Admin can edit invoice due date — change saved, logged in `due_date_changes`
- [ ] Staff can edit invoice due date — requires mandatory reason (min 10 chars)
- [ ] Staff cannot edit invoice payment terms — field hidden in modal, `403` from API if attempted
- [ ] Staff cannot edit invoice sales rep — field hidden, API blocks it
- [ ] Admin can edit client email — field visible and saves correctly
- [ ] Staff cannot edit client email — field completely hidden in edit modal
- [ ] Staff cannot edit client NIN/ID fields — fields completely hidden
- [ ] Admin can edit payment amount — invoice `amount_paid`, `balance_due`, and `status` recalculate correctly
- [ ] Staff cannot access payment edit — button not shown, API returns `403`
- [ ] Admin can update pending verification deposit amount
- [ ] Staff can update pending verification payment proof URL
- [ ] Staff cannot update pending verification deposit amount — field hidden

### Role-Based UI
- [ ] Staff logs in — all `admin-only` elements invisible (not just disabled, fully gone)
- [ ] Staff logs in — sidebar shows no Team, Analytics, Reports, Sales Reps nav items
- [ ] Staff logs in — dashboard shows no revenue KPI cards
- [ ] Staff logs in — dashboard shows no charts (revenue, estate, payment status, referral)
- [ ] Staff logs in — dashboard shows no leaderboard
- [ ] Staff logs in — invoices table shows no "Void Receipt" button
- [ ] Staff types `/dashboard` with `showSection('reports')` in console — redirected to dashboard with error toast
- [ ] Admin logs in — all elements visible, no restrictions
- [ ] Role badge in sidebar shows gold "Admin" or blue "Staff" correctly
- [ ] Switching between admin and staff test accounts shows correct UI for each

---

*End of Addendum — Eximp & Cloves Infrastructure Limited*
*Read alongside PRD 1, PRD 2, and PRD 3*