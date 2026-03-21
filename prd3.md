# Product Requirements Document 4
## Eximp & Cloves Infrastructure Limited — Commission Management System
### Version 1.0

---

## 1. Overview

This PRD covers the complete commission management system for Eximp & Cloves sales representatives. Commission is earned per verified payment — not per sale — meaning reps earn incrementally as clients make installment payments. Rates vary per rep per estate. Every commission record is permanently locked at the time of payment verification and is never retroactively affected by future rate changes.

---

## 2. Core Business Rules

1. **Commission is earned when a payment is verified by admin** — not when the invoice is created and not when the form is submitted
2. **Commission is calculated on the verified payment amount** — not the total invoice value
3. **The rate used is the rep's active rate for that specific estate on the date of verification**
4. **Rate changes never affect previously earned commission** — all historical records are locked
5. **Rates vary per rep per estate** — Funke may earn 5% on Coinfield but 7% on Prime Circle
6. **A company-wide default rate applies** to any rep/estate combination that has no specific rate set
7. **Admin can manually adjust any commission amount** after it is calculated — adjustments are logged
8. **Reps are notified by email** every time they earn commission from a verified payment
9. **Admin tracks payouts** — the system shows what is owed, admin marks as paid when payment is made outside the system

---

## 3. Database Schema

### 3.1 Company Default Commission Rate

```sql
-- Store the company-wide default rate as a system setting
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_by UUID REFERENCES admins(id),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default commission rate (admin can update this)
INSERT INTO system_settings (key, value) VALUES ('default_commission_rate', '5.00')
ON CONFLICT (key) DO NOTHING;
```

### 3.2 Commission Rates Table

Stores each rep's rate per estate, with full history via effective dates.

```sql
CREATE TABLE IF NOT EXISTS commission_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sales_rep_id UUID NOT NULL REFERENCES sales_reps(id),
    estate_name VARCHAR(255) NOT NULL,  -- matches invoices.property_name
    rate DECIMAL(5,2) NOT NULL,         -- percentage e.g. 5.00 means 5%
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,                  -- NULL means currently active
    reason VARCHAR(255),                -- e.g. "Promoted to senior rep"
    set_by UUID NOT NULL REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- A rep can only have one active rate per estate at a time
-- (effective_to IS NULL means active)
CREATE UNIQUE INDEX idx_commission_rates_active
    ON commission_rates(sales_rep_id, estate_name)
    WHERE effective_to IS NULL;

ALTER TABLE commission_rates ENABLE ROW LEVEL SECURITY;
```

### 3.3 Commission Earnings Table

One row per verified payment. Locked at the time of verification.

```sql
CREATE TABLE IF NOT EXISTS commission_earnings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sales_rep_id UUID NOT NULL REFERENCES sales_reps(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    payment_id UUID NOT NULL REFERENCES payments(id),
    client_id UUID NOT NULL REFERENCES clients(id),

    -- Locked at time of verification — never changes
    estate_name VARCHAR(255) NOT NULL,
    payment_amount DECIMAL(15,2) NOT NULL,   -- the verified payment amount
    commission_rate DECIMAL(5,2) NOT NULL,   -- rate at time of verification
    commission_amount DECIMAL(15,2) NOT NULL, -- payment_amount × rate / 100

    -- Manual adjustment by admin
    adjusted_amount DECIMAL(15,2),           -- NULL if not adjusted
    adjustment_reason TEXT,
    adjusted_by UUID REFERENCES admins(id),
    adjusted_at TIMESTAMPTZ,

    -- Final amount owed (adjusted_amount if set, else commission_amount)
    -- Computed column — always use this for display and totals
    final_amount DECIMAL(15,2) GENERATED ALWAYS AS (
        COALESCE(adjusted_amount, commission_amount)
    ) STORED,

    -- Payout tracking
    is_paid BOOLEAN DEFAULT false,
    paid_at TIMESTAMPTZ,
    paid_by UUID REFERENCES admins(id),
    payout_reference VARCHAR(255),          -- bank transfer ref or payment note
    payout_batch_id UUID,                   -- groups multiple earnings paid together

    -- Notification tracking
    rep_notified BOOLEAN DEFAULT false,
    rep_notified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_commission_earnings_rep ON commission_earnings(sales_rep_id);
CREATE INDEX idx_commission_earnings_invoice ON commission_earnings(invoice_id);
CREATE INDEX idx_commission_earnings_unpaid ON commission_earnings(sales_rep_id, is_paid)
    WHERE is_paid = false;

ALTER TABLE commission_earnings ENABLE ROW LEVEL SECURITY;
```

### 3.4 Payout Batches Table

When admin pays a rep, they can pay multiple earnings at once as a single batch.

```sql
CREATE TABLE IF NOT EXISTS payout_batches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sales_rep_id UUID NOT NULL REFERENCES sales_reps(id),
    total_amount DECIMAL(15,2) NOT NULL,
    reference VARCHAR(255),             -- bank transfer ref
    notes TEXT,
    paid_by UUID NOT NULL REFERENCES admins(id),
    paid_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE payout_batches ENABLE ROW LEVEL SECURITY;
```

---

## 4. Commission Rate Lookup Logic

When a payment is verified and commission needs to be calculated, the backend uses this lookup order:

```python
def get_commission_rate(sales_rep_id: str, estate_name: str,
                        verification_date: date, db) -> float:
    """
    Look up the commission rate for a rep on a specific estate
    on a specific date. Falls back to company default if no
    specific rate is found.

    Lookup order:
    1. Rep-specific rate for this estate, active on verification_date
    2. Company-wide default rate from system_settings
    """
    # 1. Look for rep+estate specific rate active on this date
    result = db.table("commission_rates")\
        .select("rate")\
        .eq("sales_rep_id", sales_rep_id)\
        .eq("estate_name", estate_name)\
        .lte("effective_from", str(verification_date))\
        .or_(f"effective_to.is.null,effective_to.gte.{verification_date}")\
        .order("effective_from", desc=True)\
        .limit(1)\
        .execute()

    if result.data:
        return float(result.data[0]["rate"])

    # 2. Fall back to company default
    default = db.table("system_settings")\
        .select("value")\
        .eq("key", "default_commission_rate")\
        .execute()

    return float(default.data[0]["value"]) if default.data else 5.0
```

---

## 5. Commission Calculation — Where It Happens

Commission is calculated **inside the payment verification flow** — specifically in `routers/verifications.py`, in the `confirm` endpoint, after the payment is recorded.

### Updated Confirm Payment Flow

```python
@router.patch("/{verification_id}/confirm")
async def confirm_verification(verification_id: str, current_admin=Depends(verify_token)):
    db = get_db()

    # 1. Get the verification record
    verif = db.table("pending_verifications")\
        .select("*, invoices(*, clients(*))")\
        .eq("id", verification_id)\
        .execute().data[0]

    invoice = verif["invoices"]
    client = invoice["clients"]

    # 2. Record the payment in payments table
    payment = db.table("payments").insert({
        "invoice_id": invoice["id"],
        "client_id": invoice["client_id"],
        "reference": f"{verif['payment_date']}_verified",
        "amount": float(verif["deposit_amount"]),
        "payment_date": verif["payment_date"],
        "recorded_by": current_admin["sub"]
    }).execute().data[0]

    # 3. Update invoice amount_paid, balance_due, status
    # (existing logic)

    # 4. Calculate and record commission
    if invoice.get("sales_rep_id"):
        rate = get_commission_rate(
            sales_rep_id=invoice["sales_rep_id"],
            estate_name=invoice["property_name"],
            verification_date=date.today(),
            db=db
        )
        commission_amount = round(float(verif["deposit_amount"]) * rate / 100, 2)

        earning = db.table("commission_earnings").insert({
            "sales_rep_id": invoice["sales_rep_id"],
            "invoice_id": invoice["id"],
            "payment_id": payment["id"],
            "client_id": invoice["client_id"],
            "estate_name": invoice["property_name"],
            "payment_amount": float(verif["deposit_amount"]),
            "commission_rate": rate,
            "commission_amount": commission_amount,
        }).execute().data[0]

        # 5. Send commission notification email to rep (background task)
        rep = db.table("sales_reps")\
            .select("*")\
            .eq("id", invoice["sales_rep_id"])\
            .execute().data[0]

        if rep.get("email"):
            background_tasks.add_task(
                send_commission_earned_email,
                rep=rep,
                client=client,
                invoice=invoice,
                earning=earning
            )

    # 6. Send receipt + statement to client
    # (existing logic)

    # 7. Update pending_verifications status
    db.table("pending_verifications")\
        .update({"status": "confirmed", "reviewed_by": current_admin["sub"],
                 "reviewed_at": datetime.utcnow().isoformat()})\
        .eq("id", verification_id)\
        .execute()

    return {"message": "Payment confirmed, commission recorded"}
```

---

## 6. Commission Email to Sales Rep

Sent every time a payment is verified and commission is earned. Sent to `sales_reps.email`.

**Subject:** `Commission Earned — [Client Name] | Eximp & Cloves`

**Email body:**

```
Dear [Rep Name],

Great news! A payment has been verified for one of your clients,
and your commission has been recorded.

─────────────────────────────────────────
CLIENT:          [Client Full Name]
PROPERTY:        [Estate Name] — [Plot Size]
INVOICE:         [EC-XXXXXX]
PAYMENT AMOUNT:  NGN X,XXX,XXX.00
─────────────────────────────────────────
YOUR COMMISSION
Rate:            [X]%
Amount Earned:   NGN XX,XXX.00
─────────────────────────────────────────

Your commission will be processed in the next payout cycle.
Contact finance@eximps-cloves.com for any enquiries.

[Company footer]
```

If the client still has an outstanding balance, add:

```
Note: This client has a remaining balance of NGN XXX,XXX.00
due by [due_date]. Additional commission will be earned
when further payments are verified.
```

---

## 7. New API Endpoints

All endpoints are Admin only unless stated otherwise.

### 7.1 Commission Rates Management

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/commission/rates/{rep_id}` | Get all rates for a rep (all estates, full history) |
| POST | `/api/commission/rates` | Set a new rate for rep + estate |
| GET | `/api/commission/default-rate` | Get company default rate |
| PATCH | `/api/commission/default-rate` | Update company default rate |

### 7.2 Commission Earnings

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/commission/earnings` | List all earnings (filterable by rep, estate, date, paid status) |
| GET | `/api/commission/earnings/{rep_id}` | All earnings for a specific rep |
| PATCH | `/api/commission/earnings/{id}/adjust` | Manually adjust a commission amount |
| GET | `/api/commission/owed` | Summary of unpaid commission per rep |
| GET | `/api/commission/owed/{rep_id}` | Detailed unpaid earnings for one rep |

### 7.3 Payout Management

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/commission/payout` | Mark one or more earnings as paid (creates payout batch) |
| GET | `/api/commission/payouts` | List all payout batches |
| GET | `/api/commission/payouts/{rep_id}` | Payout history for a rep |

---

## 8. New Pydantic Models

Add to `models.py`:

```python
class CommissionRateCreate(BaseModel):
    sales_rep_id: str
    estate_name: str
    rate: Decimal           # e.g. 5.00 for 5%
    effective_from: date
    reason: Optional[str] = None

class CommissionAdjustment(BaseModel):
    adjusted_amount: Decimal
    adjustment_reason: str   # required — must explain why

class CommissionPayout(BaseModel):
    sales_rep_id: str
    earning_ids: list[str]  # UUIDs of commission_earnings to mark paid
    reference: Optional[str] = None
    notes: Optional[str] = None

class DefaultRateUpdate(BaseModel):
    rate: Decimal
    reason: Optional[str] = None
```

---

## 9. Commission Management UI

### 9.1 Where Commission Lives in the Dashboard

Commission management is split across two places:

**Sales Rep Profile Page (PRD 3)** — add a Commission tab:
- Commission summary for this rep
- Rate configuration per estate
- Earnings history
- Payout history

**Commission Overview Page (new)** — accessible from the Analytics sidebar:
- Company-wide commission summary
- Who is owed what
- Bulk payout tools

### 9.2 Sales Rep Profile — Commission Tab

Add a **"Commission"** tab to the Rep Profile page alongside the existing deals/charts content.

**Tab sections:**

**Current Rates card**

Shows all active commission rates for this rep:

```
Estate               Rate    Effective From    Set By
─────────────────────────────────────────────────────
Coinfield Estate     5.00%   01 Jan 2026       Admin
Prime Circle Estate  7.00%   01 Mar 2026       Admin
Xylara Court         5.00%   01 Jan 2026       Admin
All other estates    5.00%   (company default)
```

"Edit Rate" button per row → opens rate edit modal
"Add Rate for New Estate" button → opens new rate modal

**Commission Summary cards (filtered by timeframe)**

```
[Earned This Period]  [Paid This Period]  [Currently Owed]  [All Time Earned]
NGN 45,500            NGN 32,500          NGN 13,000         NGN 284,000
```

**Earnings Table**

All commission earnings for this rep, newest first.

Columns:
| Date | Client | Estate | Payment Amount | Rate | Commission | Adjustment | Final | Status | Actions |
|---|---|---|---|---|---|---|---|---|---|

- "Adjustment" column shows the adjusted amount in amber if manually changed, blank otherwise
- "Final" column always shows `final_amount` (adjusted or original)
- Status badge: Unpaid (red) / Paid (green)
- Actions: "Adjust" button (opens adjustment modal)

**Payouts Table**

All payout batches for this rep.

Columns: Date | Amount | Reference | Paid By | Earnings Count

---

### 9.3 Set / Edit Commission Rate Modal

Opens when admin clicks "Edit Rate" or "Add Rate for New Estate" on the Rep Profile commission tab.

**Fields:**
- Estate Name (dropdown of all active properties — from properties table)
- Commission Rate (number input, %) — placeholder: "e.g. 5.00"
- Effective From (date picker — defaults to today)
- Reason (text input — e.g. "Promoted to senior rep", "New estate launch rate")

**On save:**
1. Set `effective_to = today - 1 day` on the current active rate for this rep + estate
2. Insert new rate row with `effective_from = selected date` and `effective_to = NULL`
3. Show success toast: "Rate updated. Applies to all payments verified from [date] onwards."
4. Existing earned commission is never affected

**Warning message shown in modal:**
> "This rate will apply to all payments verified from the effective date onwards. Previously earned commission is not affected."

---

### 9.4 Commission Adjustment Modal

Opens when admin clicks "Adjust" on an earnings row.

**Fields:**
- Current calculated amount (read-only, displayed prominently)
- Adjusted Amount (number input — pre-filled with current final_amount)
- Reason (textarea — **required**, minimum 20 characters)
  - Placeholder: "e.g. Bonus for closing highest deal this month / Reduced due to cancellation fee"

**On save:**
1. Update `commission_earnings.adjusted_amount` and `adjustment_reason`
2. Log in `activity_log`: "Commission for [Rep Name] on [Invoice] adjusted from NGN X to NGN Y by [Admin]. Reason: [reason]"
3. Show toast: "Commission adjusted successfully"

**Warning shown if adjusted amount > original:**
> "You are increasing this commission above the calculated rate. Please ensure this has been approved."

**Warning shown if adjusted amount = 0:**
> "Setting commission to NGN 0.00 means this rep earns nothing from this payment. Are you sure?"

---

### 9.5 Mark as Paid Flow

**From Rep Profile Commission Tab:**

1. Admin selects one or more unpaid earnings using checkboxes in the earnings table
2. "Mark Selected as Paid" button appears at the top of the table (only when items are checked)
3. A summary modal shows:
   - Rep name
   - Number of earnings selected
   - Total amount to be paid: NGN XX,XXX.00
   - Reference field (bank transfer ref — optional)
   - Notes field (optional)
4. Admin clicks "Confirm Payment"
5. Backend:
   - Creates a `payout_batches` record
   - Updates all selected `commission_earnings` rows: `is_paid = true`, `paid_at = now`, `payout_batch_id = new batch id`
6. Toast: "NGN XX,XXX.00 marked as paid to [Rep Name]"

**"Pay All Owed" shortcut button:**
A single button that selects ALL unpaid earnings for this rep automatically, then proceeds to the same confirmation modal. Saves admin from manually ticking each row.

---

### 9.6 Commission Overview Page (Admin Only)

**Location:** Sidebar under Analytics → "Commission Overview"

**Page layout:**

**Summary KPI cards (top row)**
```
[Total Owed (All Reps)]  [Paid This Month]  [Earned This Month]  [Reps with Balance]
NGN 284,000              NGN 150,000        NGN 45,500            7
```

**"Who Is Owed" Table**

One row per rep with outstanding commission.

Columns: Rep Name | Estate(s) | Deals This Period | Earned | Paid | Owed | Last Payout | Actions

Actions per row:
- "View Details" → goes to Rep Profile Commission tab
- "Pay All" → opens the Mark as Paid modal pre-loaded with all unpaid earnings for this rep

Sorted by: Owed amount descending (most owed at top)

**Recent Payouts table (bottom)**

Last 20 payout batches across all reps.

Columns: Date | Rep Name | Amount | Reference | Paid By

---

## 10. Commission in Reports (PRD 3 Addition)

Add commission data to the existing Sales Rep Performance Report (PRD 3, Report 2):

Additional columns in the report:
- Commission Rate (current rate for their primary estate)
- Total Commission Earned (in period)
- Total Commission Paid (in period)
- Commission Outstanding

Add a new report type to PRD 3:

**Report 7 — Commission Report**
- Description: Full commission earnings and payout summary for all reps
- Contents:
  - Summary: Total earned, total paid, total outstanding across all reps
  - Per-rep section: all earnings with client names, amounts, rates, paid/unpaid status
  - Payout history section: all payouts made in the period
- Filter: Date range, specific rep or all reps, paid/unpaid/both
- Format: PDF + Excel

Add `openpyxl` formula for Excel version:
- Auto-sum at bottom of each rep's section
- Grand total row at the very bottom
- Conditional formatting: unpaid rows in light red, paid rows in light green

---

## 11. Scheduled Commission Report (PRD 3 Addition)

Add "Commission Report" as an option in the Report Schedules dropdown (PRD 3, Section 4.3).

Suggested default schedule for commission:
- Monthly, 1st of each month, 8am
- Recipients: finance@eximps-cloves.com
- Subject: `Eximp & Cloves — Commission Report — {period}`

The email body summary for commission reports:

```
Total Earned:      NGN XXX,XXX.00
Total Paid:        NGN XXX,XXX.00
Total Outstanding: NGN XXX,XXX.00
Reps with Balance: X
```

---

## 12. File Structure Changes

```
eximp-cloves/
├── routers/
│   └── commission.py        ← NEW — all commission endpoints
├── email_service.py         ← UPDATE — add send_commission_earned_email()
├── routers/verifications.py ← UPDATE — trigger commission calculation on confirm
├── models.py                ← UPDATE — add commission models
├── main.py                  ← UPDATE — register commission router
├── templates/
│   └── dashboard.html       ← UPDATE — Rep Profile commission tab,
│                                        Commission Overview page,
│                                        Set Rate modal,
│                                        Adjustment modal,
│                                        Mark as Paid modal
└── schema.sql               ← UPDATE — new tables
```

Register in `main.py`:
```python
from routers import commission
app.include_router(commission.router, prefix="/api/commission", tags=["commission"])
```

---

## 13. Edge Cases and Rules

| Scenario | Behaviour |
|---|---|
| Rep has no rate set for the estate | Use company default rate |
| Rep has no email address | Skip notification email, log warning |
| Commission amount rounds to NGN 0.00 | Still create the record, mark as paid immediately (no payout needed) |
| Payment is voided after commission is earned | Commission earning is NOT automatically reversed — admin must manually adjust to NGN 0.00 with reason |
| Invoice has no `sales_rep_id` (walk-in client, no rep) | No commission record created |
| Admin adjusts commission to NGN 0.00 | Allowed — must provide reason — logged permanently |
| Rep is deactivated | Their historical commission records remain intact and owed |
| Same rep, same estate, two active rates | Prevented by unique index — `effective_to` must be set on old rate before new one is inserted |
| Payout marked in error | No automatic reversal — admin must create a negative adjustment on the affected earnings |

---

## 14. Testing Checklist

### Commission Rates
- [ ] Admin sets rep rate for a specific estate — saves with effective date
- [ ] Admin sets different rate for same rep on different estate — both saved independently
- [ ] Admin updates a rate — old rate gets `effective_to` set, new rate inserted with `effective_from`
- [ ] Rep with no estate-specific rate uses company default rate
- [ ] Company default rate can be updated from Commission Overview page
- [ ] Rate change does NOT affect previously earned commission

### Commission Earning
- [ ] Admin confirms a payment → commission record created with correct rate and amount
- [ ] Commission rate used is the one active on the date of verification, not today's rate
- [ ] Installment client pays 3 times → 3 separate commission records created
- [ ] Invoice with no `sales_rep_id` → no commission record created
- [ ] Commission email sent to rep's email address on each verification
- [ ] Rep with no email → no crash, just skipped

### Commission Adjustment
- [ ] Admin adjusts commission → `adjusted_amount` saved, reason required
- [ ] `final_amount` always reflects adjusted amount when set
- [ ] Adjustment logged in `activity_log` with old and new amounts
- [ ] Adjustment to NGN 0.00 shows warning modal
- [ ] Adjustment above original shows warning modal

### Mark as Paid
- [ ] Admin selects multiple earnings → "Mark Selected as Paid" button appears
- [ ] "Pay All Owed" button selects all unpaid earnings for rep
- [ ] Confirmation modal shows correct total
- [ ] After confirming — all selected earnings show "Paid" status
- [ ] Payout batch record created with correct total and reference
- [ ] Commission owed total on Rep Profile updates immediately

### Commission Overview Page
- [ ] "Who Is Owed" table shows correct outstanding totals per rep
- [ ] Sorted by owed amount descending
- [ ] "Pay All" button from overview pre-loads correct rep's earnings
- [ ] Recent payouts table shows last 20 batches

### Reports
- [ ] Commission Report generates correctly as PDF
- [ ] Commission Report generates correctly as Excel
- [ ] Excel has auto-sum totals and conditional formatting
- [ ] Commission data appears in Sales Rep Performance Report

---

*End of PRD 4 — Eximp & Cloves Infrastructure Limited Commission Management System*
*Read alongside PRD 1, PRD 2, PRD 3, and the Addendum*