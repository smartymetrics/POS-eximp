# KPI Auto-Grading Implementation Brief
### Eximps & Cloves ERP — HRM Portal
**Project:** Automatic goal grading from live invoice, client, appointment, and support ticket data
**Scope:** Schema migrations + backend sync engine + one frontend fix
**Status of this document:** Ready to build — all tables verified, all queries designed

---

## Overview

The HRM portal already has the goal/KPI architecture in place (`staff_goals`, `kpi_templates`, `achievement_status`, `last_synced_at`). What it lacks is a sync engine that actually reads live business data and writes scores back. This document specifies every change needed — schema, backend, and frontend — for a developer or AI coding agent to implement without ambiguity.

**KPI types being auto-graded:**
1. `sales_revenue` — total invoiced amount paid by rep's clients
2. `sales_deals_closed` — number of invoices with any payment from rep's clients
3. `mkt_leads_added` — new marketing contacts created by staff member
4. `mkt_lead_conversion` — % of rep's assigned clients who have made at least one payment
5. `sales_collection_rate` — total payments collected ÷ total invoiced for rep's clients
6. `ops_appointments` — appointments created by staff with status `completed`
7. `admin_ticket_esc` — support tickets assigned to staff that were resolved
8. `team_achievement` — % of a manager's direct reports whose goals hit 100%

---

## Part 1 — Schema Changes (Run First)

Three small migrations. All are `ALTER TABLE` only — no existing data is modified.

---

### Migration 1: Link `admins` to `sales_reps`

**File:** `migrations/031_link_admins_to_sales_reps.sql`

**Why:** `staff_goals.staff_id` references `admins.id`. Invoices reference `sales_reps.id`. Without this link, revenue KPIs can only be resolved via fragile name/email string matching. This adds one column to create a direct, reliable UUID join.

**Important:** This column is nullable. Staff who are not sales reps (e.g. HR managers, accountants) simply have `NULL` here. The sync engine skips revenue KPIs for them gracefully.

```sql
-- Add sales_rep_id to admins table
ALTER TABLE public.admins
  ADD COLUMN IF NOT EXISTS sales_rep_id UUID REFERENCES public.sales_reps(id) ON DELETE SET NULL;

-- Index for the join used by the sync engine
CREATE INDEX IF NOT EXISTS idx_admins_sales_rep_id ON public.admins(sales_rep_id);

COMMENT ON COLUMN public.admins.sales_rep_id IS
  'Links this staff member to their sales_reps record for commission and KPI tracking. NULL if this admin is not a sales rep.';
```

**After running:** In the dashboard Sales Reps section, wire the existing rep management UI to write this field when a rep is linked to an admin account. This is a one-time setup per rep — no ongoing automation needed.

---

### Migration 2: Add `resolved_at` to `support_tickets`

**File:** `migrations/032_support_tickets_resolved_at.sql`

**Why:** The `resolve_ticket` endpoint only writes `updated_at`. If a ticket is edited after being resolved, `updated_at` shifts and the KPI sync counts it in the wrong month. `resolved_at` is written once, never updated.

```sql
-- Add resolved_at timestamp, written once when ticket is first resolved
ALTER TABLE public.support_tickets
  ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ NULL;

-- Index for date-range queries in the sync engine
CREATE INDEX IF NOT EXISTS idx_support_tickets_resolved_at
  ON public.support_tickets(assigned_admin_id, resolved_at)
  WHERE resolved_at IS NOT NULL;

COMMENT ON COLUMN public.support_tickets.resolved_at IS
  'Set once when status first changes to resolved. Never updated after that.';
```

**After running:** Update `routers/support.py` in the `resolve_ticket` function (line ~235):

```python
# BEFORE:
res = await db_execute(lambda: db.table("support_tickets").update({
    "status": "resolved",
    "updated_at": datetime.utcnow().isoformat()
}).eq("id", ticket_id).execute())

# AFTER:
now = datetime.utcnow().isoformat()
res = await db_execute(lambda: db.table("support_tickets").update({
    "status": "resolved",
    "updated_at": now,
    "resolved_at": now          # ← add this line only
}).eq("id", ticket_id).execute())
```

Also update the `respond_to_ticket` function (line ~217) where it auto-resolves based on message content:

```python
# Find this block and add resolved_at in the same way:
update_payload = {
    "status": "resolved" if "resolved" in data.message.lower() else "pending",
    "updated_at": datetime.utcnow().isoformat()
}
if "resolved" in data.message.lower():
    update_payload["resolved_at"] = datetime.utcnow().isoformat()

await db_execute(lambda: db.table("support_tickets").update(update_payload).eq("id", ticket_id).execute())
```

---

### Migration 3: Populate `marketing_contacts.created_by`

**Why:** The `marketing_contacts` table already has a `created_by UUID REFERENCES admins(id)` column (added in `hrm_goal_automation.sql`) but `marketing_logic.py`'s `sync_client_to_marketing()` function never writes it. The column is NULL for all existing rows.

**File:** `marketing_logic.py` — update the `sync_client_to_marketing` function signature and insert:

```python
# BEFORE (in marketing_logic.py):
async def sync_client_to_marketing(client_data: dict):
    ...
    marketing_data = {
        "client_id": client_id,
        "email": email,
        # ... other fields
    }

# AFTER — accept optional created_by and pass it through:
async def sync_client_to_marketing(client_data: dict, created_by: str = None):
    ...
    marketing_data = {
        "client_id": client_id,
        "email": email,
        # ... other fields
    }
    if created_by:
        marketing_data["created_by"] = created_by
```

Then in `routers/clients.py`, pass the current admin's ID when calling `sync_client_to_marketing`. There are two call sites (lines ~88 and ~138):

```python
# BEFORE:
await sync_client_to_marketing(result.data[0])

# AFTER:
await sync_client_to_marketing(result.data[0], created_by=str(current_admin.get("sub")))
```

No SQL migration needed — the column already exists.

---

## Part 2 — The Sync Engine

**File:** `routers/hr.py` — add or replace the `sync_goal_actuals()` function used by `POST /api/hr/goals/sync`.

The function already exists as a stub. Replace its body with the implementation below.

### Core Logic

For each goal being synced:
1. Identify which `measurement_source` the KPI uses
2. Run the appropriate query against live data
3. Compute `actual_value` and `achievement_pct`
4. Determine `achievement_status` from thresholds
5. Write back to `staff_goals`

### Achievement Status Thresholds

```
actual ≥ target          → "achieved"
actual ≥ target × 0.75  → "on_track"
actual ≥ target × 0.50  → "at_risk"
actual < target × 0.50  → "behind"
```

### Helper: Resolve Sales Rep ID

Used by all sales KPIs. Returns the `sales_reps.id` UUID for a given admin, or `None` if they have no linked rep.

```python
async def _resolve_sales_rep_id(admin_id: str) -> str | None:
    """
    Returns the sales_reps.id for this admin, using the direct FK if set,
    falling back to email match, then phone match.
    The direct FK (admins.sales_rep_id) is preferred — set it during onboarding.
    """
    db = get_db()

    # Step 1: Direct FK (most reliable)
    admin_res = await db_execute(
        lambda: db.table("admins")
            .select("sales_rep_id, email")
            .eq("id", admin_id)
            .single()
            .execute()
    )
    if not admin_res.data:
        return None

    if admin_res.data.get("sales_rep_id"):
        return str(admin_res.data["sales_rep_id"])

    # Step 2: Email fallback (for reps whose FK was never set)
    admin_email = admin_res.data.get("email")
    if admin_email:
        rep_res = await db_execute(
            lambda: db.table("sales_reps")
                .select("id")
                .eq("email", admin_email)
                .limit(1)
                .execute()
        )
        if rep_res.data:
            return str(rep_res.data[0]["id"])

    # Step 3: Phone fallback
    profile_res = await db_execute(
        lambda: db.table("staff_profiles")
            .select("phone_number")
            .eq("admin_id", admin_id)
            .single()
            .execute()
    )
    if profile_res.data and profile_res.data.get("phone_number"):
        phone = profile_res.data["phone_number"]
        rep_res = await db_execute(
            lambda: db.table("sales_reps")
                .select("id")
                .eq("phone", phone)
                .limit(1)
                .execute()
        )
        if rep_res.data:
            return str(rep_res.data[0]["id"])

    return None
```

---

### KPI Query Functions

Each function below takes `staff_id` (admin UUID) and `period` (a dict with `start` and `end` as ISO strings for the month being evaluated) and returns a float.

---

#### `sales_revenue` — Total Amount Paid on Rep's Invoices

```python
async def _compute_sales_revenue(staff_id: str, period: dict) -> float:
    """
    Sum of amount_paid on all invoices assigned to this rep's sales_reps record,
    where at least one payment exists in the period.
    Uses amount_paid (not amount) so partial payments are counted — matching
    the business definition: "any payment counts as revenue".
    """
    rep_id = await _resolve_sales_rep_id(staff_id)
    if not rep_id:
        return 0.0

    db = get_db()
    res = await db_execute(
        lambda: db.table("invoices")
            .select("amount_paid")
            .eq("sales_rep_id", rep_id)
            .neq("status", "voided")
            .gte("invoice_date", period["start"])
            .lte("invoice_date", period["end"])
            .execute()
    )
    return sum(float(r.get("amount_paid") or 0) for r in (res.data or []))
```

---

#### `sales_deals_closed` — Number of Invoices with Any Payment

```python
async def _compute_sales_deals_closed(staff_id: str, period: dict) -> float:
    """
    Count of distinct invoices assigned to this rep where status is 'paid' or 'partial',
    within the period. A deal is "closed" if any money has been collected.
    """
    rep_id = await _resolve_sales_rep_id(staff_id)
    if not rep_id:
        return 0.0

    db = get_db()
    res = await db_execute(
        lambda: db.table("invoices")
            .select("id")
            .eq("sales_rep_id", rep_id)
            .in_("status", ["paid", "partial"])
            .gte("invoice_date", period["start"])
            .lte("invoice_date", period["end"])
            .execute()
    )
    return float(len(res.data or []))
```

---

#### `mkt_leads_added` — Marketing Contacts Created by Staff

```python
async def _compute_mkt_leads_added(staff_id: str, period: dict) -> float:
    """
    Count of marketing_contacts rows where created_by = this admin
    and created_at falls within the period.

    NOTE: Requires the marketing_logic.py fix (Part 1, Migration 3) to be
    in place. Contacts created before that fix will have created_by = NULL
    and won't be counted here — this is expected and correct going forward.
    """
    db = get_db()
    res = await db_execute(
        lambda: db.table("marketing_contacts")
            .select("id", count="exact")
            .eq("created_by", staff_id)
            .gte("created_at", period["start"])
            .lte("created_at", period["end"])
            .execute()
    )
    return float(res.count or 0)
```

---

#### `mkt_lead_conversion` — % of Assigned Clients Who Have Paid

```python
async def _compute_mkt_lead_conversion(staff_id: str, period: dict) -> float:
    """
    Conversion rate = (clients assigned to rep with ≥1 payment) ÷ (total assigned clients)
    expressed as a percentage (0–100).

    "Converted" = client has at least one non-voided, non-refund payment on any invoice.
    This matches the business definition: partial payment counts as converted.

    Period filter applies to when the client was assigned (clients.created_at),
    not when the payment was made.
    """
    db = get_db()

    # All clients assigned to this rep in the period
    clients_res = await db_execute(
        lambda: db.table("clients")
            .select("id")
            .eq("assigned_rep_id", staff_id)
            .gte("created_at", period["start"])
            .lte("created_at", period["end"])
            .execute()
    )
    client_ids = [c["id"] for c in (clients_res.data or [])]
    if not client_ids:
        return 0.0

    total = len(client_ids)

    # Of those clients, how many have at least one payment on any invoice?
    # Query: invoices for these clients that have amount_paid > 0
    ids_csv = ",".join(f'"{cid}"' for cid in client_ids)
    invoices_res = await db_execute(
        lambda: db.table("invoices")
            .select("client_id")
            .in_("client_id", client_ids)
            .neq("status", "voided")
            .gt("amount_paid", 0)
            .execute()
    )

    converted_clients = set(r["client_id"] for r in (invoices_res.data or []))
    converted = len(converted_clients)

    return round((converted / total) * 100, 2)
```

---

#### `sales_collection_rate` — Payments Collected ÷ Total Invoiced

```python
async def _compute_sales_collection_rate(staff_id: str, period: dict) -> float:
    """
    Collection rate = sum(amount_paid) ÷ sum(amount) for all non-voided invoices
    assigned to this rep in the period, expressed as a percentage (0–100).
    """
    rep_id = await _resolve_sales_rep_id(staff_id)
    if not rep_id:
        return 0.0

    db = get_db()
    res = await db_execute(
        lambda: db.table("invoices")
            .select("amount, amount_paid")
            .eq("sales_rep_id", rep_id)
            .neq("status", "voided")
            .gte("invoice_date", period["start"])
            .lte("invoice_date", period["end"])
            .execute()
    )

    rows = res.data or []
    total_invoiced = sum(float(r.get("amount") or 0) for r in rows)
    total_paid = sum(float(r.get("amount_paid") or 0) for r in rows)

    if total_invoiced == 0:
        return 0.0

    return round((total_paid / total_invoiced) * 100, 2)
```

---

#### `ops_appointments` — Completed Appointments Created by Staff

```python
async def _compute_ops_appointments(staff_id: str, period: dict) -> float:
    """
    Count of appointments where:
    - created_by = this admin (appointments.created_by → admins.id)
    - status = 'completed'
    - scheduled_at falls within the period

    Table: public.appointments
    Relevant columns: id, created_by (UUID → admins.id), status ('scheduled'|'completed'|
    'cancelled'|'no_show'), scheduled_at (TIMESTAMPTZ)
    """
    db = get_db()
    res = await db_execute(
        lambda: db.table("appointments")
            .select("id", count="exact")
            .eq("created_by", staff_id)
            .eq("status", "completed")
            .gte("scheduled_at", period["start"])
            .lte("scheduled_at", period["end"])
            .execute()
    )
    return float(res.count or 0)
```

---

#### `admin_ticket_esc` — Support Tickets Resolved by Staff

```python
async def _compute_admin_ticket_esc(staff_id: str, period: dict) -> float:
    """
    Count of support_tickets where:
    - assigned_admin_id = this admin
    - status = 'resolved'
    - resolved_at falls within the period

    Requires Migration 2 (resolved_at column) to be in place.
    Falls back to updated_at if resolved_at is NULL (covers tickets resolved
    before the migration was run).
    """
    db = get_db()

    # Primary: use resolved_at (accurate)
    res = await db_execute(
        lambda: db.table("support_tickets")
            .select("id", count="exact")
            .eq("assigned_admin_id", staff_id)
            .eq("status", "resolved")
            .gte("resolved_at", period["start"])
            .lte("resolved_at", period["end"])
            .execute()
    )
    count_with_resolved_at = res.count or 0

    # Fallback: tickets resolved before migration (resolved_at is NULL)
    res2 = await db_execute(
        lambda: db.table("support_tickets")
            .select("id", count="exact")
            .eq("assigned_admin_id", staff_id)
            .eq("status", "resolved")
            .is_("resolved_at", "null")
            .gte("updated_at", period["start"])
            .lte("updated_at", period["end"])
            .execute()
    )
    count_fallback = res2.count or 0

    return float(count_with_resolved_at + count_fallback)
```

---

#### `team_achievement` — Manager's Team Goal Completion Rate

```python
async def _compute_team_achievement(staff_id: str, period: dict) -> float:
    """
    For managers: % of direct reports whose goals for the period hit 100% achievement.
    Direct reports = staff where manager_id = this admin's id.

    Returns a percentage (0–100).
    """
    db = get_db()

    # Get all direct reports
    reports_res = await db_execute(
        lambda: db.table("admins")
            .select("id")
            .eq("manager_id", staff_id)
            .execute()
    )
    report_ids = [r["id"] for r in (reports_res.data or [])]
    if not report_ids:
        return 0.0

    total = len(report_ids)

    # Count how many have at least one goal at 100%+ for this period
    goals_res = await db_execute(
        lambda: db.table("staff_goals")
            .select("staff_id")
            .in_("staff_id", report_ids)
            .gte("achievement_pct", 100)
            .gte("period_start", period["start"])
            .lte("period_end", period["end"])
            .execute()
    )

    achieved_staff = set(r["staff_id"] for r in (goals_res.data or []))
    return round((len(achieved_staff) / total) * 100, 2)
```

---

### Main Sync Dispatcher

This is the function that `POST /api/hr/goals/sync` calls. It replaces the existing stub in `hr.py`.

```python
MEASUREMENT_SOURCE_MAP = {
    "sales_revenue":        _compute_sales_revenue,
    "sales_deals_closed":   _compute_sales_deals_closed,
    "mkt_leads_added":      _compute_mkt_leads_added,
    "mkt_lead_conversion":  _compute_mkt_lead_conversion,
    "sales_collection_rate":_compute_sales_collection_rate,
    "ops_appointments":     _compute_ops_appointments,
    "admin_ticket_esc":     _compute_admin_ticket_esc,
    "team_achievement":     _compute_team_achievement,
}

def _compute_achievement_status(actual: float, target: float) -> str:
    if target == 0:
        return "achieved" if actual > 0 else "behind"
    ratio = actual / target
    if ratio >= 1.0:
        return "achieved"
    elif ratio >= 0.75:
        return "on_track"
    elif ratio >= 0.50:
        return "at_risk"
    else:
        return "behind"

async def sync_goal_actuals(
    staff_id: str = None,   # None = sync all active goals system-wide
    goal_id: str = None     # None = sync all goals for the staff member
):
    """
    Core sync engine. Called by:
    - POST /api/hr/goals/sync          (manual trigger, syncs all)
    - POST /api/hr/goals/{id}/sync     (single goal refresh)
    - Scheduler (nightly cron)

    For each qualifying staff_goal row:
    1. Determine the goal's period (period_start, period_end)
    2. Look up the kpi_templates.measurement_source
    3. Call the appropriate compute function
    4. Write actual_value, achievement_pct, achievement_status, last_synced_at
    """
    db = get_db()
    now = datetime.utcnow().isoformat()

    # Build query for goals to sync
    query = db.table("staff_goals")\
        .select("id, staff_id, target_value, period_start, period_end, kpi_templates(measurement_source)")\
        .eq("is_active", True)

    if staff_id:
        query = query.eq("staff_id", staff_id)
    if goal_id:
        query = query.eq("id", goal_id)

    goals_res = await db_execute(lambda: query.execute())
    goals = goals_res.data or []

    synced = 0
    errors = []

    for goal in goals:
        try:
            measurement_source = (goal.get("kpi_templates") or {}).get("measurement_source")
            if not measurement_source:
                continue

            compute_fn = MEASUREMENT_SOURCE_MAP.get(measurement_source)
            if not compute_fn:
                # measurement_source is "manual" or unrecognized — skip
                continue

            period = {
                "start": goal["period_start"],
                "end": goal["period_end"]
            }

            actual = await compute_fn(goal["staff_id"], period)
            target = float(goal.get("target_value") or 0)
            pct = round((actual / target * 100), 2) if target > 0 else (100.0 if actual > 0 else 0.0)
            status = _compute_achievement_status(actual, target)

            await db_execute(
                lambda: db.table("staff_goals").update({
                    "actual_value":       actual,
                    "achievement_pct":    pct,
                    "achievement_status": status,
                    "last_synced_at":     now
                }).eq("id", goal["id"]).execute()
            )
            synced += 1

        except Exception as e:
            errors.append({"goal_id": goal["id"], "error": str(e)})
            continue

    return {
        "synced": synced,
        "skipped_manual": len(goals) - synced - len(errors),
        "errors": errors,
        "timestamp": now
    }
```

---

## Part 3 — Scheduler (Nightly Sync)

**File:** `scheduler.py` — the nightly job that already exists. Ensure the call to `sync_goal_actuals()` is wired without arguments so it sweeps all active goals:

```python
# In the existing nightly job (already scheduled):
async def nightly_goal_sync():
    try:
        result = await sync_goal_actuals()
        logger.info(f"Nightly KPI sync complete: {result['synced']} goals updated, {len(result['errors'])} errors")
    except Exception as e:
        logger.error(f"Nightly KPI sync failed: {e}")
```

---

## Part 4 — HRM Portal UI (No Changes Needed)

The HRM portal (`hrm-portal/src/App.jsx`) already:
- Displays `achievement_status` with the correct badge colours
- Shows `last_synced_at` as the "last updated" timestamp
- Renders `achievement_pct` as a progress bar
- Distinguishes auto vs manual KPIs with a badge
- Has a "Sync Now" button that calls `POST /api/hr/goals/sync`

No UI changes are needed. The sync engine writes to the same columns the UI already reads.

---

## Part 5 — Admin Dashboard: Link Rep to Staff Member

One small UI addition is needed in `dashboard.html` in the Sales Reps section. When an admin views or edits a sales rep record, there should be a dropdown to select which HRM staff member (from `admins`) this rep corresponds to. Selecting one writes `admins.sales_rep_id = sales_reps.id` via a `PATCH /api/hr/staff/{admin_id}` call.

This is a one-time setup action per rep, not an automated sync. It only needs to be done once for each rep who also has an HRM login.

**Endpoint to add to `hr.py`:**

```python
@router.patch("/staff/{admin_id}/link-rep")
async def link_sales_rep(admin_id: str, data: dict, current_admin=Depends(verify_token)):
    """
    Links an admin to a sales_reps record.
    Body: { "sales_rep_id": "uuid-of-sales-rep" }
    Only callable by admins with role 'admin' or 'super_admin'.
    """
    db = get_db()
    await db_execute(
        lambda: db.table("admins").update({
            "sales_rep_id": data.get("sales_rep_id")  # Pass null to unlink
        }).eq("id", admin_id).execute()
    )
    return {"message": "Rep link updated"}
```

---

## Implementation Order

Do these in this exact sequence to avoid dependency issues:

1. **Run Migration 1** (`031_link_admins_to_sales_reps.sql`) — adds `admins.sales_rep_id`
2. **Run Migration 2** (`032_support_tickets_resolved_at.sql`) — adds `support_tickets.resolved_at`
3. **Fix `marketing_logic.py`** — update function signature and call sites in `clients.py`
4. **Fix `support.py`** — add `resolved_at` writes to `resolve_ticket` and `respond_to_ticket`
5. **Add `link-rep` endpoint** to `hr.py`
6. **Replace `sync_goal_actuals()`** in `hr.py` with the full implementation above
7. **Wire the scheduler** to call `sync_goal_actuals()` nightly
8. **Go to Sales Reps section** in the dashboard and link each rep to their HRM admin account
9. **Test** by manually triggering sync on one staff member and verifying the scores match what you see in the invoices

---

## Edge Cases to Be Aware Of

**Rep with no linked `sales_rep_id` and no email match:** All revenue/deals/collection KPIs return 0. The sync engine won't error — it just scores them as 0 and marks `achievement_status = "behind"`. Fix by linking them via the new UI.

**Goals with `target_value = 0`:** A target of zero is treated as "achieved if any actual value > 0, otherwise behind". This prevents division-by-zero.

**`mkt_leads_added` for old contacts:** Any marketing contact created before the `marketing_logic.py` fix has `created_by = NULL`. Those contacts won't be counted. This is correct and expected — the KPI only counts leads from the point the fix was deployed forward.

**Appointments created by a different admin than the one who conducted them:** The `appointments.created_by` column records who booked the appointment, not necessarily who conducted it. For KPI purposes this is fine — the business intent is to track appointments coordinated by each staff member, and `created_by` is the correct column for that.

**`team_achievement` for non-managers:** Staff with no direct reports (`manager_id` pointing to them) return 0. Set the goal type `team_achievement` only for managers in the HRM portal to avoid misleading scores.
