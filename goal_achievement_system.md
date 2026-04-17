# Goal Achievement Auto-Detection System
### HRM Module — ERP (Eximp & Cloves)

---

> **Document type:** Technical Design & Implementation Guide
> **Version:** 1.0
> **Date:** April 2026
> **Status:** Draft — Pending Engineering Review
> **Audience:** Engineering Team, HR Team, Product
> **Confidential:** Internal Use Only

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goal Type Framework](#3-goal-type-framework)
4. [Architecture](#4-architecture)
5. [Database Schema Changes](#5-database-schema-changes)
6. [ERP Data Source Mapping](#6-erp-data-source-mapping)
7. [Background Sync Engine](#7-background-sync-engine)
8. [Achievement Detection Logic](#8-achievement-detection-logic)
9. [Notifications & Escalations](#9-notifications--escalations)
10. [Performance Review Integration](#10-performance-review-integration)
11. [API Endpoints](#11-api-endpoints)
12. [KPI Template Library](#12-kpi-template-library)
13. [Department-Level Goals](#13-department-level-goals)
14. [Edge Cases & Rules](#14-edge-cases--rules)
15. [Migration Steps](#15-migration-steps)
16. [Implementation Checklist](#16-implementation-checklist)

---

## 1. Overview

This document defines the design and implementation plan for the **goal achievement auto-detection system** within the Eximp & Cloves ERP HRM module. The system enables the platform to automatically detect when a staff member or department has achieved, is on track, or is at risk of missing their monthly KPI goals — without requiring manual input from managers.

The approach is modelled on how top enterprise HRM/ERP platforms (SAP SuccessFactors, Workday, Oracle HCM) handle goal tracking: goals declare a `measurement_source`, and a background engine periodically syncs `actual_value` by querying the relevant ERP tables. Achievement status is computed automatically and feeds directly into performance reviews.

---

## 2. Problem Statement

The current `staff_goals` table stores `target_value` and `actual_value`, but `actual_value` is never populated automatically. The following gaps exist:

- There is no mechanism to detect when a goal has been met.
- Goals have no concept of measurement type (sales-based, client-based, qualitative, etc.).
- The performance review scoring (40% goals component) depends on `actual_value` but it is always `0` unless manually updated.
- There are no alerts when a goal is falling behind or has been achieved.
- Department-level goals have no rollup logic.

This system resolves all of the above.

---

## 3. Goal Type Framework

Goals are classified into two families: **quantitative** (auto-synced from ERP data) and **qualitative** (manually updated by the staff member or manager). Each goal type is defined in a `kpi_templates` record with a `measurement_source` field.

| Goal Type | `measurement_source` | Unit | ERP Source Table | Description |
|---|---|---|---|---|
| **Marketing Leads** | `mkt_leads_added` | Count | `marketing_contacts` + `clients` | Combined new leads added by staff via Marketing or CRM dashboards |
| **Lead Conversion** | `mkt_lead_conversion` | % | `marketing_contacts` | % of leads successfully converted to clients |
| **Properties Inspected** | `ops_appointments` | Count | `appointments` | Completed inspections coordinated by staff members |
| **Team Achievement**| `team_achievement` | % | `staff_goals` | (Manager KPI) % of direct reports hitting 100% of their month's goals |
| **Sales Revenue** | `sales_revenue` | NGN | `invoices` | Total value of paid invoices for assigned Reps |
| **Collection Rate** | `sales_collection_rate`| % | `payments` vs `invoices` | Ratio of collections vs total amount due for Rep's clients |
| **Lead Response Time**| `lead_response_time` | Hours | `activity_log` | (Marketing) Avg hours from lead entry to first staff interaction |

### 3.2 Qualitative Goal Types

These cannot be detected from data. The staff member or manager marks progress manually. `target_value` is always `1` (completed) and `actual_value` is set to `1` (done) or a progress decimal (0.5 = halfway).

| Goal Type | `measurement_source` | Examples |
|---|---|---|
| Training completed | `manual` | Complete compliance training, obtain certification |
| Process improvement | `manual` | Implement new client onboarding flow |
| Team contribution | `manual` | Mentor a junior staff member, lead a project |
| Strategic initiative | `manual` | Complete a market research report |

### 3.3 Scoring Weight by Type

Consistent with how SAP SuccessFactors weights goal categories:

| Category | Default Weight in Performance Score |
|---|---|
| Quantitative (sales/deals) | 60% of goals score |
| Quantitative (activity-based) | 25% of goals score |
| Qualitative | 15% of goals score |

> The combined goals component is 40% of the total performance review score, as defined in the existing `calculate_performance_score()` function in `routers/hr.py`.

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GOAL TYPES                           │
│  sales_revenue │ deals_closed │ clients_acquired │ manual│
└────────┬───────────────┬───────────────┬──────────┬──────┘
         │               │               │          │
         ▼               ▼               ▼          ▼
┌────────────────────────────────────────────────────────┐
│                  ERP DATA SOURCES                      │
│   invoices   │   payments   │   clients   │  (manual)  │
└─────────────────────────┬──────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│            BACKGROUND SYNC ENGINE                      │
│         sync_goal_actuals()  — runs nightly            │
│    Queries ERP → writes actual_value to staff_goals    │
└─────────────────────────┬──────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│           ACHIEVEMENT DETECTION                        │
│   actual ÷ target → achievement %                      │
│   ≥100% Achieved │ 70–99% On track │ <70% At risk      │
└──────────┬──────────────────────────────┬──────────────┘
           │                              │
           ▼                              ▼
┌─────────────────────┐      ┌───────────────────────────┐
│  ACHIEVED ACTIONS   │      │    AT-RISK ACTIONS         │
│  · Notify staff     │      │  · Alert manager           │
│  · Notify manager   │      │  · Dashboard flag          │
│  · Flag for review  │      │  · Escalate if critical    │
└──────────┬──────────┘      └──────────────┬────────────┘
           └──────────────┬─────────────────┘
                          ▼
┌────────────────────────────────────────────────────────┐
│              PERFORMANCE REVIEWS                       │
│   Goals score (40%) auto-calculated from actuals       │
│   Review shows per-KPI attainment with % breakdown     │
└────────────────────────────────────────────────────────┘
```

---

## 5. Database Schema Changes

### 5.1 Migration SQL

Run this migration in Supabase SQL editor. All changes are additive and non-breaking.

```sql
-- ============================================================
-- MIGRATION: Goal Achievement Auto-Detection
-- Version: 1.0
-- Date: April 2026
-- ============================================================

-- 1. Add measurement_source to kpi_templates
ALTER TABLE kpi_templates
  ADD COLUMN IF NOT EXISTS measurement_source VARCHAR(50)
    DEFAULT 'manual'
    CHECK (measurement_source IN (
      'sales_revenue',
      'deals_closed',
      'clients_acquired',
      'payments_collected',
      'properties_inspected',
      'contracts_signed',
      'leads_generated',
      'lead_conversion_pct',
      'lead_response_time',
      'lead_activity',
      'manual'
    )),
  ADD COLUMN IF NOT EXISTS default_unit VARCHAR(50) DEFAULT 'count',
  ADD COLUMN IF NOT EXISTS default_target NUMERIC DEFAULT 0;

-- 2. Add achievement tracking to staff_goals
ALTER TABLE staff_goals
  ADD COLUMN IF NOT EXISTS achievement_status VARCHAR(20)
    DEFAULT 'pending'
    CHECK (achievement_status IN ('pending', 'at_risk', 'on_track', 'achieved')),
  ADD COLUMN IF NOT EXISTS achievement_pct NUMERIC GENERATED ALWAYS AS
    (CASE WHEN target_value > 0 THEN ROUND((actual_value / target_value) * 100, 2) ELSE 0 END) STORED,
  ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS achieved_at TIMESTAMPTZ;

-- 3. Goal achievement notifications log
CREATE TABLE IF NOT EXISTS goal_achievement_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goal_id UUID NOT NULL REFERENCES staff_goals(id) ON DELETE CASCADE,
  staff_id UUID NOT NULL REFERENCES admins(id),
  event_type VARCHAR(30) NOT NULL
    CHECK (event_type IN ('achieved', 'at_risk', 'critical', 'on_track_update')),
  achievement_pct NUMERIC,
  actual_value NUMERIC,
  target_value NUMERIC,
  notified_staff BOOLEAN DEFAULT FALSE,
  notified_manager BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Index for fast syncing
CREATE INDEX IF NOT EXISTS idx_staff_goals_status_month
  ON staff_goals(status, month);

CREATE INDEX IF NOT EXISTS idx_staff_goals_achievement
  ON staff_goals(achievement_status, staff_id);

CREATE INDEX IF NOT EXISTS idx_goal_events_goal_id
  ON goal_achievement_events(goal_id, created_at DESC);

-- 5. Enable RLS
ALTER TABLE goal_achievement_events ENABLE ROW LEVEL SECURITY;
```

### 5.2 Updated Table Summary

**`kpi_templates`** (updated columns)

| Column | Type | Description |
|---|---|---|
| `measurement_source` | VARCHAR(50) | How actual value is measured. See Section 3. |
| `default_unit` | VARCHAR(50) | Default unit label (e.g. "NGN", "count", "%") |
| `default_target` | NUMERIC | Suggested default target value for this template |

**`staff_goals`** (updated columns)

| Column | Type | Description |
|---|---|---|
| `achievement_status` | VARCHAR(20) | `pending`, `at_risk`, `on_track`, `achieved` |
| `achievement_pct` | NUMERIC (generated) | `actual_value / target_value * 100`, auto-computed |
| `last_synced_at` | TIMESTAMPTZ | When the sync engine last updated `actual_value` |
| `achieved_at` | TIMESTAMPTZ | Timestamp when goal first crossed 100% |

---

## 6. ERP Data Source Mapping

This section defines exactly how each quantitative goal type reads from the existing ERP tables.

### 6.1 `sales_revenue`

```sql
SELECT COALESCE(SUM(i.amount), 0) AS actual_value
FROM invoices i
JOIN sales_reps sr ON sr.name = i.sales_rep_name
JOIN admins a ON a.id = :staff_id
-- Match rep to admin by name or linked rep record
WHERE i.status = 'paid'
  AND i.invoice_date >= :period_start
  AND i.invoice_date <= :period_end;
```

**Notes:**
- The `invoices` table stores `sales_rep_name` as a plain string. The sync engine resolves this to an `admins.id` via a name match or a `sales_rep_id` link (add `sales_rep_id UUID REFERENCES admins(id)` to `invoices` as a future improvement).
- Only `status = 'paid'` invoices count. `partial` and `unpaid` are excluded.
- `voided` invoices are always excluded.

### 6.2 `deals_closed`

```sql
SELECT COUNT(*) AS actual_value
FROM invoices
WHERE pipeline_stage = 'closed'
  AND sales_rep_name = :rep_name
  AND updated_at >= :period_start
  AND updated_at <= :period_end;
```

### 6.3 `clients_acquired`

```sql
SELECT COUNT(*) AS actual_value
FROM clients
WHERE created_by = :staff_id
  AND created_at >= :period_start
  AND created_at <= :period_end;
```

> **Note:** The `clients` table must have a `created_by UUID REFERENCES admins(id)` column populated when clients are created. Verify this is set in `routers/clients.py`.

### 6.4 `payments_collected`

```sql
SELECT COALESCE(SUM(p.amount), 0) AS actual_value
FROM payments p
WHERE p.recorded_by = :staff_id
  AND p.payment_date >= :period_start
  AND p.payment_date <= :period_end
  AND p.is_voided = FALSE;
```

### 6.5 `contracts_signed`

```sql
SELECT COUNT(*) AS actual_value
FROM invoices
WHERE sales_rep_name = :rep_name
  AND contract_signed_at >= :period_start
  AND contract_signed_at <= :period_end;
```

### 6.6 `leads_generated`

```sql
SELECT COUNT(*) AS actual_value
FROM clients
WHERE assigned_rep_id = :staff_id
  AND created_at >= :period_start
  AND created_at <= :period_end;
```

### 6.7 `lead_conversion_pct`

```sql
SELECT 
  CASE 
    WHEN COUNT(*) = 0 THEN 0 
    ELSE (COUNT(CASE WHEN pipeline_stage = 'closed' THEN 1 END) * 100.0 / COUNT(*))
  END AS actual_value
FROM clients
WHERE assigned_rep_id = :staff_id
  AND created_at >= :period_start
  AND created_at <= :period_end;
```

### 6.8 `lead_response_time` (Avg Hours)

```sql
WITH lead_first_activity AS (
  SELECT 
    c.id, 
    c.created_at, 
    MIN(a.created_at) as first_act
  FROM clients c
  JOIN activity_log a ON a.client_id = c.id
  WHERE c.assigned_rep_id = :staff_id
    AND c.created_at >= :period_start
    AND c.created_at <= :period_end
  GROUP BY c.id, c.created_at
)
SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (first_act - created_at))/3600), 0) as actual_value
FROM lead_first_activity;
```

### 6.9 `lead_activity`

```sql
SELECT COUNT(*) AS actual_value
FROM activity_log a
JOIN clients c ON c.id = a.client_id
WHERE c.assigned_rep_id = :staff_id
  AND a.created_at >= :period_start
  AND a.created_at <= :period_end;
```

### 6.10 Department-Level Goals

When `staff_id` is null and `department` is set, the sync engine aggregates across all staff in that department:

```sql
-- Example: department sales_revenue
SELECT COALESCE(SUM(i.amount), 0) AS actual_value
FROM invoices i
JOIN admins a ON a.name = i.sales_rep_name
WHERE a.department = :department
  AND i.status = 'paid'
  AND i.invoice_date >= :period_start
  AND i.invoice_date <= :period_end;
```

---

## 7. Background Sync Engine

### 7.1 Location

Add to `scheduler.py` as a new scheduled job. Register it in `start_scheduler()`.

### 7.2 Full Implementation

```python
# scheduler.py — add to existing file

from datetime import date, timedelta
import calendar

async def sync_goal_actuals():
    """
    Nightly job: queries ERP tables and updates actual_value
    on all Published staff_goals. Sets achievement_status accordingly.
    Fires achievement events when goals are first reached.
    """
    job_key = f"goal_sync_{date.today().strftime('%Y-%m-%d')}"
    if not await try_claim_job(job_key, threshold_mins=1380):  # 23 hrs
        logger.info("Goal sync already ran today, skipping.")
        return

    logger.info("Starting goal actuals sync...")
    db = get_db()

    # Fetch all active published goals with their KPI template
    goals_res = await db_execute(
        lambda: db.table("staff_goals")
            .select("*, kpi_templates(measurement_source, name)")
            .eq("status", "Published")
            .execute()
    )

    if not goals_res.data:
        logger.info("No published goals to sync.")
        return

    for goal in goals_res.data:
        try:
            await _sync_single_goal(db, goal)
        except Exception as e:
            logger.error(f"Failed to sync goal {goal['id']}: {e}")

    logger.info(f"Goal sync complete. Processed {len(goals_res.data)} goals.")


async def _sync_single_goal(db, goal: dict):
    goal_id = goal["id"]
    staff_id = goal.get("staff_id")
    department = goal.get("department")
    target = float(goal.get("target_value") or 1)
    month_date = goal["month"]  # e.g. "2026-04-01"
    template = goal.get("kpi_templates") or {}
    source = template.get("measurement_source", "manual")

    # Compute period bounds
    if isinstance(month_date, str):
        month_date = date.fromisoformat(month_date)
    period_start = month_date.replace(day=1).isoformat()
    last_day = calendar.monthrange(month_date.year, month_date.month)[1]
    period_end = month_date.replace(day=last_day).isoformat()

    if source == "manual":
        # Manual goals: do not overwrite actual_value, just recompute status
        actual = float(goal.get("actual_value") or 0)
    elif source == "sales_revenue":
        actual = await _fetch_sales_revenue(db, staff_id, department, period_start, period_end)
    elif source == "deals_closed":
        actual = await _fetch_deals_closed(db, staff_id, department, period_start, period_end)
    elif source == "clients_acquired":
        actual = await _fetch_clients_acquired(db, staff_id, department, period_start, period_end)
    elif source == "payments_collected":
        actual = await _fetch_payments_collected(db, staff_id, period_start, period_end)
    elif source == "contracts_signed":
        actual = await _fetch_contracts_signed(db, staff_id, department, period_start, period_end)
    elif source == "leads_generated":
        actual = await _fetch_leads_generated(db, staff_id, period_start, period_end)
    elif source == "lead_conversion_pct":
        actual = await _fetch_lead_conversion_pct(db, staff_id, period_start, period_end)
    elif source == "lead_response_time":
        actual = await _fetch_lead_response_time(db, staff_id, period_start, period_end)
    elif source == "lead_activity":
        actual = await _fetch_lead_activity(db, staff_id, period_start, period_end)
    else:
        return  # Unknown source — skip

    # Compute achievement status
    pct = actual / max(target, 0.01)
    if pct >= 1.0:
        new_status = "achieved"
    elif pct >= 0.7:
        new_status = "on_track"
    else:
        new_status = "at_risk"

    # Check if this is the first time the goal became achieved
    was_achieved = goal.get("achievement_status") == "achieved"
    now_achieved = new_status == "achieved"
    achieved_at = goal.get("achieved_at")
    if now_achieved and not was_achieved:
        achieved_at = datetime.utcnow().isoformat()

    # Update the goal record
    await db_execute(
        lambda: db.table("staff_goals").update({
            "actual_value": actual,
            "achievement_status": new_status,
            "last_synced_at": datetime.utcnow().isoformat(),
            **({"achieved_at": achieved_at} if achieved_at else {})
        }).eq("id", goal_id).execute()
    )

    # Log achievement event if status changed meaningfully
    old_status = goal.get("achievement_status", "pending")
    if new_status != old_status and new_status in ("achieved", "at_risk"):
        await _log_achievement_event(db, goal, new_status, actual, target, pct * 100)


async def _fetch_sales_revenue(db, staff_id, department, period_start, period_end) -> float:
    rep_name = await _get_rep_name(db, staff_id, department)
    if not rep_name:
        return 0.0
    res = await db_execute(
        lambda: db.table("invoices")
            .select("amount")
            .eq("sales_rep_name", rep_name)
            .eq("status", "paid")
            .neq("status", "voided")
            .gte("invoice_date", period_start)
            .lte("invoice_date", period_end)
            .execute()
    )
    return sum(float(r["amount"]) for r in (res.data or []))


async def _fetch_deals_closed(db, staff_id, department, period_start, period_end) -> float:
    rep_name = await _get_rep_name(db, staff_id, department)
    if not rep_name:
        return 0.0
    res = await db_execute(
        lambda: db.table("invoices")
            .select("id")
            .eq("pipeline_stage", "closed")
            .eq("sales_rep_name", rep_name)
            .gte("updated_at", period_start)
            .lte("updated_at", period_end)
            .execute()
    )
    return float(len(res.data or []))


async def _fetch_clients_acquired(db, staff_id, department, period_start, period_end) -> float:
    query = db.table("clients").select("id")
    if staff_id:
        query = query.eq("created_by", staff_id)
    query = query.gte("created_at", period_start).lte("created_at", period_end)
    res = await db_execute(lambda: query.execute())
    return float(len(res.data or []))


async def _fetch_payments_collected(db, staff_id, period_start, period_end) -> float:
    if not staff_id:
        return 0.0
    res = await db_execute(
        lambda: db.table("payments")
            .select("amount")
            .eq("recorded_by", staff_id)
            .eq("is_voided", False)
            .gte("payment_date", period_start)
            .lte("payment_date", period_end)
            .execute()
    )
    return sum(float(r["amount"]) for r in (res.data or []))


async def _fetch_contracts_signed(db, staff_id, department, period_start, period_end) -> float:
    rep_name = await _get_rep_name(db, staff_id, department)
    if not rep_name:
        return 0.0
    res = await db_execute(
        lambda: db.table("invoices")
            .select("id")
            .eq("sales_rep_name", rep_name)
            .not_.is_("contract_signed_at", "null")
            .gte("contract_signed_at", period_start)
            .lte("contract_signed_at", period_end)
            .execute()
    )
    return float(len(res.data or []))


async def _fetch_leads_generated(db, staff_id, period_start, period_end) -> float:
    if not staff_id: return 0.0
    res = await db_execute(lambda: db.table("clients").select("id", count="exact").eq("assigned_rep_id", staff_id).gte("created_at", period_start).lte("created_at", period_end).execute())
    return float(res.count or 0)


async def _fetch_lead_conversion_pct(db, staff_id, period_start, period_end) -> float:
    if not staff_id: return 0.0
    res = await db_execute(lambda: db.table("clients").select("id, pipeline_stage").eq("assigned_rep_id", staff_id).gte("created_at", period_start).lte("created_at", period_end).execute())
    data = res.data or []
    if not data: return 0.0
    closed = len([l for l in data if l["pipeline_stage"] == "closed"])
    return (closed / len(data)) * 100.0


async def _fetch_lead_response_time(db, staff_id, period_start, period_end) -> float:
    """Calculates average hours from lead creation to first activity log."""
    # Note: Complex join logic usually better served by a custom RPC in Supabase
    # For now, we perform a simplified fetch-and-compute
    if not staff_id: return 0.0
    leads = await db_execute(lambda: db.table("clients").select("id, created_at").eq("assigned_rep_id", staff_id).gte("created_at", period_start).lte("created_at", period_end).execute())
    if not leads.data: return 0.0
    
    total_hours = 0.0
    counted_leads = 0
    for lead in leads.data:
        acts = await db_execute(lambda: db.table("activity_log").select("created_at").eq("client_id", lead["id"]).order("created_at").limit(1).execute())
        if acts.data:
            dt_lead = datetime.fromisoformat(lead["created_at"].replace("Z", "+00:00"))
            dt_act = datetime.fromisoformat(acts.data[0]["created_at"].replace("Z", "+00:00"))
            diff = (dt_act - dt_lead).total_seconds() / 3600
            total_hours += diff
            counted_leads += 1
    
    return total_hours / counted_leads if counted_leads > 0 else 0.0


async def _fetch_lead_activity(db, staff_id, period_start, period_end) -> float:
    if not staff_id: return 0.0
    # Join activity_log with clients to filter by assigned_rep_id
    res = await db_execute(lambda: db.rpc("count_rep_activities", {
        "rep_id": staff_id, 
        "start_time": period_start, 
        "end_time": period_end
    }).execute())
    return float(res.data or 0)


async def _get_rep_name(db, staff_id, department) -> str | None:
    """Resolve staff_id to their name as stored in invoices.sales_rep_name."""
    if not staff_id:
        return None
    res = await db_execute(
        lambda: db.table("admins").select("full_name").eq("id", staff_id).execute()
    )
    if res.data:
        return res.data[0].get("full_name")
    return None


async def _log_achievement_event(db, goal, event_type, actual, target, pct):
    await db_execute(
        lambda: db.table("goal_achievement_events").insert({
            "goal_id": goal["id"],
            "staff_id": goal["staff_id"],
            "event_type": event_type,
            "achievement_pct": round(pct, 2),
            "actual_value": actual,
            "target_value": target,
        }).execute()
    )
    if event_type == "achieved":
        await _notify_achievement(db, goal, actual, target, pct)
    elif event_type == "at_risk":
        await _notify_at_risk(db, goal, actual, target, pct)
```

### 7.3 Scheduler Registration

In `start_scheduler()` inside `scheduler.py`, add:

```python
# Goal actuals sync — runs nightly at 01:00 UTC
scheduler.add_job(
    sync_goal_actuals,
    CronTrigger(hour=1, minute=0),
    id="goal_actuals_sync",
    replace_existing=True
)
```

### 7.4 On-Demand Trigger

Add a manual trigger endpoint so HR can force a sync after bulk data entry:

```python
# routers/hr.py
@router.post("/goals/sync", status_code=200)
async def trigger_goal_sync(current_admin: dict = Depends(verify_token)):
    """Manually trigger goal actuals sync. HR/admin only."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
        raise HTTPException(status_code=403, detail="HR only")
    from scheduler import sync_goal_actuals
    asyncio.create_task(sync_goal_actuals())
    return {"message": "Goal sync triggered. Results will update in the background."}
```

---

## 8. Achievement Detection Logic

### 8.1 Status Thresholds

| Achievement % | Status | Colour (UI) | Action |
|---|---|---|---|
| ≥ 100% | `achieved` | Green | Notify staff + manager, flag for review |
| 70% – 99% | `on_track` | Amber | No alert, shown on dashboard |
| 40% – 69% | `at_risk` | Red | Alert manager |
| < 40% with ≤ 7 days left in month | `critical` | Dark red | Escalate to HR admin |

### 8.2 Period Handling

- Goals are monthly. The period is always the calendar month of `staff_goals.month`.
- Sync runs nightly and always queries from `first day of month` to `today` for in-progress goals, or `first day` to `last day` for completed months.
- A goal in a past month that is still `Published` and `actual_value = 0` is treated as `at_risk` and included in the sync.

### 8.3 Achievement is Sticky

Once a goal reaches `achieved`, it stays `achieved` even if the value later decreases (e.g. a voided invoice reduces the revenue). The `achieved_at` timestamp is preserved. However, the `actual_value` continues to be updated so the dashboard always shows the current real value.

To override this behaviour (allow de-achievement), set a `sticky_achievement` flag on the template.

### 8.4 Weighted Goal Scoring

When calculating the goals component for a performance review, use the `weight` column on `staff_goals`:

```python
def calculate_goals_score(goals: list[dict]) -> float:
    """
    Returns a 0–100 score representing weighted goal attainment.
    Used as the 40% goals component in the performance review.
    """
    total_weight = sum(g.get("weight", 1) for g in goals)
    if total_weight == 0:
        return 0.0
    weighted_sum = 0.0
    for g in goals:
        pct = min(float(g.get("actual_value", 0)) / max(float(g.get("target_value", 1)), 0.01), 1.0)
        weighted_sum += pct * float(g.get("weight", 1))
    return round((weighted_sum / total_weight) * 100, 2)
```

---

## 9. Notifications & Escalations

### 9.1 Achievement Notification (to staff + manager)

```python
async def _notify_achievement(db, goal, actual, target, pct):
    staff_res = await db_execute(
        lambda: db.table("admins")
            .select("full_name, email, line_manager_id")
            .eq("id", goal["staff_id"])
            .execute()
    )
    if not staff_res.data:
        return
    staff = staff_res.data[0]

    subject = f"Goal Achieved: {goal.get('kpi_name', 'KPI')}"
    body = (
        f"Hi {staff['full_name']},\n\n"
        f"Congratulations! You have achieved your goal:\n\n"
        f"  KPI: {goal.get('kpi_name')}\n"
        f"  Target: {target}\n"
        f"  Actual: {actual}\n"
        f"  Achievement: {round(pct, 1)}%\n\n"
        f"This has been recorded and will be reflected in your performance review.\n\n"
        f"— HR System"
    )
    await send_email(staff["email"], subject, body)

    # Also notify manager
    if staff.get("line_manager_id"):
        mgr_res = await db_execute(
            lambda: db.table("admins")
                .select("full_name, email")
                .eq("id", staff["line_manager_id"])
                .execute()
        )
        if mgr_res.data:
            mgr = mgr_res.data[0]
            mgr_body = (
                f"Hi {mgr['full_name']},\n\n"
                f"{staff['full_name']} has achieved their goal for this period:\n\n"
                f"  KPI: {goal.get('kpi_name')}\n"
                f"  Achievement: {round(pct, 1)}%\n\n"
                f"— HR System"
            )
            await send_email(mgr["email"], f"Team Goal Achieved — {staff['full_name']}", mgr_body)
```

### 9.2 At-Risk Alert (to manager)

Fires when `achievement_status` transitions to `at_risk`. Sent to the line manager only.

### 9.3 Critical Escalation

When a goal is below 40% with 7 or fewer days remaining in the month, a critical alert is sent to the HR admin in addition to the manager. The `goal_achievement_events` table records the escalation.

### 9.4 No Duplicate Alerts

The `goal_achievement_events` table prevents duplicate notifications. Before firing a notification, check that no event of the same `event_type` for this `goal_id` exists within the last 24 hours.

---

## 10. Performance Review Integration

### 10.1 How Goals Feed into Reviews

The existing `calculate_performance_score()` function in `routers/hr.py` (line ~271) already computes the goals score from `actual_value / target_value`. Once the sync engine runs, this is always accurate.

The performance review endpoint `GET /api/hr/performance/score/{staff_id}` returns a `goals_score` field. This should now also return the per-goal breakdown:

```json
{
  "staff_id": "uuid",
  "period": "2026-04-01",
  "goals_score": 78.4,
  "goals_breakdown": [
    {
      "kpi_name": "Monthly Sales Revenue",
      "target": 5000000,
      "actual": 4200000,
      "achievement_pct": 84.0,
      "status": "on_track",
      "weight": 2.0
    },
    {
      "kpi_name": "New Clients",
      "target": 5,
      "actual": 6,
      "achievement_pct": 120.0,
      "status": "achieved",
      "weight": 1.0
    }
  ],
  "total_performance_score": 72.1
}
```

### 10.2 Review Preparation Agent (Recommended)

When a manager opens a performance review, pre-populate the review form with:

- All goals for the period with actual vs. target
- Achievement percentage per goal
- Whether each goal was auto-synced or manually updated
- Overall goals score as a pre-filled read-only field

This mirrors the SAP SuccessFactors Performance Preparation Agent pattern and removes the need for managers to calculate scores manually.

---

## 11. API Endpoints

### New Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/hr/goals/sync` | Manually trigger goal sync (HR admin only) |
| `GET` | `/api/hr/goals/{goal_id}/history` | Get sync history and achievement events for a goal |
| `GET` | `/api/hr/goals/at-risk` | List all at-risk goals (with staff and manager info) |
| `GET` | `/api/hr/goals/achieved` | List all achieved goals for current period |
| `GET` | `/api/hr/dashboard/goals-summary` | Aggregate summary for HR dashboard |

### Updated Endpoints

| Method | Path | Change |
|---|---|---|
| `GET` | `/api/hr/goals` | Now returns `achievement_status`, `achievement_pct`, `last_synced_at` |
| `GET` | `/api/hr/performance/score/{staff_id}` | Now includes `goals_breakdown` array |
| `POST` | `/api/hr/kpi-templates` | Now accepts `measurement_source`, `default_unit`, `default_target` |

---

## 12. KPI Template Library

Pre-seed these templates in `kpi_templates` via a migration or seed script. These are the recommended starting set based on the ERP's existing data model.

### Sales Department

| Template Name | `measurement_source` | Default Unit | Default Target |
|---|---|---|---|
| Monthly Sales Revenue | `sales_revenue` | NGN | 5,000,000 |
| Deals Closed | `deals_closed` | Count | 5 |
| Contracts Signed | `contracts_signed` | Count | 3 |
| New Clients Acquired | `clients_acquired` | Count | 4 |
| Payments Collected | `payments_collected` | NGN | 3,000,000 |

### Operations Department

| Template Name | `measurement_source` | Default Unit | Default Target |
|---|---|---|---|
| Properties Inspected | `properties_inspected` | Count | 10 |
| Client Follow-ups Completed | `manual` | Count | 20 |
| Document Processing Time | `manual` | Days | 2 |

### HR Department

| Template Name | `measurement_source` | Default Unit | Default Target |
|---|---|---|---|
| Staff Onboarding Completed | `manual` | Count | 2 |
| Leave Request Processing Time | `manual` | Days | 1 |
| Training Sessions Delivered | `manual` | Count | 1 |

### Seed Script

```python
# scripts/seed_kpi_templates.py

templates = [
    {"name": "Monthly Sales Revenue", "department": "Sales", "category": "Revenue",
     "measurement_source": "sales_revenue", "default_unit": "NGN", "default_target": 5000000,
     "description": "Total value of paid invoices attributed to this staff member in the month."},

    {"name": "Deals Closed", "department": "Sales", "category": "Activity",
     "measurement_source": "deals_closed", "default_unit": "count", "default_target": 5,
     "description": "Number of invoices reaching pipeline stage 'closed' in the month."},

    {"name": "Contracts Signed", "department": "Sales", "category": "Activity",
     "measurement_source": "contracts_signed", "default_unit": "count", "default_target": 3,
     "description": "Number of contracts signed (contract_signed_at populated) in the month."},

    {"name": "New Clients Acquired", "department": "Sales", "category": "Growth",
     "measurement_source": "clients_acquired", "default_unit": "count", "default_target": 4,
     "description": "Number of new client records created by this staff member."},

    {"name": "Payments Collected", "department": "Sales", "category": "Revenue",
     "measurement_source": "payments_collected", "default_unit": "NGN", "default_target": 3000000,
     "description": "Total payment amounts recorded by this staff member."},
]

for t in templates:
    supabase.table("kpi_templates").upsert(t, on_conflict="name").execute()
```

---

## 13. Department-Level Goals

When `staff_id` is null and `department` is set on a `staff_goals` record, the goal applies to the entire department.

### Rollup Logic

```python
async def _sync_department_goal(db, goal):
    """Aggregate actual values across all staff in the department."""
    dept = goal["department"]
    source = goal["kpi_templates"]["measurement_source"]

    # Get all staff in department
    staff_res = await db_execute(
        lambda: db.table("admins")
            .select("id")
            .eq("department", dept)
            .eq("is_active", True)
            .execute()
    )
    staff_ids = [s["id"] for s in (staff_res.data or [])]

    total = 0.0
    for sid in staff_ids:
        total += await _fetch_by_source(db, source, sid, None, goal["month"])

    return total
```

### Department Dashboard Widget

The HR dashboard should show a department-level goal card with:

- Department name
- Goal name and target
- Aggregated actual vs. target
- Progress bar
- Number of staff in the department who individually achieved vs. at-risk

---

## 14. Edge Cases & Rules

| Scenario | Handling |
|---|---|
| Staff member has no `sales_rep_name` match in invoices | `actual_value` stays at `0`, status becomes `at_risk`. HR is notified to fix the name mapping. |
| Goal period is in the future | Sync is skipped. Status remains `pending`. |
| Goal is in `Draft` status | Sync is skipped. Only `Published` goals are synced. |
| `target_value = 0` | Division guard: treated as `target = 0.01` to avoid divide-by-zero. Achievement % is capped at `100%`. |
| Voided invoice reduces revenue below target after achieving | `actual_value` is updated but `achievement_status` and `achieved_at` are preserved (sticky). |
| Staff member is deactivated mid-period | Goal continues to sync using their last known rep name until the period ends. |
| Multiple staff with the same `full_name` | The sync engine logs a warning and skips the goal. HR must resolve the naming conflict. |
| Manual goal `actual_value` set by manager | The sync engine does not overwrite `actual_value` for `manual` goals. Only status is recomputed. |
| Goal created after period has started | Sync immediately runs for the full period to catch up. |

---

## 15. Migration Steps

Follow these steps in order to deploy this feature safely.

**Step 1 — Run the schema migration**

Run the SQL in Section 5.1 in Supabase SQL editor. Verify all columns are added with `\d staff_goals` and `\d kpi_templates`.

**Step 2 — Add `measurement_source` to existing templates**

For each existing `kpi_templates` record, set `measurement_source`. Any template without it defaults to `'manual'`, which is safe.

**Step 3 — Seed the KPI template library**

Run `scripts/seed_kpi_templates.py` to insert the standard templates.

**Step 4 — Deploy updated `routers/hr.py`**

Deploy the fixed `hr.py` file (template_id remap fix, initiative_score fix, new sync trigger endpoint, updated goal response schema).

**Step 5 — Deploy updated `scheduler.py`**

Deploy with `sync_goal_actuals` job registered. It will trigger at 01:00 UTC the following night.

**Step 6 — Trigger a manual sync**

After deploy, call `POST /api/hr/goals/sync` as an HR admin to populate all current-period goals immediately.

**Step 7 — Verify**

Check that `actual_value`, `achievement_status`, and `last_synced_at` are populated on `Published` goals. Confirm at least one `goal_achievement_events` record was created for an achieved goal.

---

## 16. Implementation Checklist

### Schema
- [ ] Add `measurement_source` to `kpi_templates`
- [ ] Add `achievement_status`, `achievement_pct`, `last_synced_at`, `achieved_at` to `staff_goals`
- [ ] Create `goal_achievement_events` table
- [ ] Create required indexes

### Backend
- [ ] Implement `sync_goal_actuals()` in `scheduler.py`
- [ ] Implement all `_fetch_*` helper functions
- [ ] Register nightly cron job (01:00 UTC)
- [ ] Add `POST /api/hr/goals/sync` manual trigger endpoint
- [ ] Add `GET /api/hr/goals/at-risk` endpoint
- [ ] Add `GET /api/hr/goals/achieved` endpoint
- [ ] Update goal list response to include `achievement_status` and `achievement_pct`
- [ ] Update performance score response to include `goals_breakdown`
- [ ] Implement achievement notification emails
- [ ] Implement at-risk manager alert emails

### KPI Templates
- [ ] Add `measurement_source`, `default_unit`, `default_target` to `KPITemplateBase` Pydantic model
- [ ] Seed standard templates via seed script
- [ ] Update `kpi_templates` CRUD endpoints

### Testing
- [ ] Unit test `calculate_goals_score()` with weighted goals
- [ ] Integration test `sync_goal_actuals()` against test invoices
- [ ] Verify sticky achievement behaviour on voided invoice
- [ ] Verify department rollup aggregation
- [ ] Confirm no duplicate notifications are sent

---

*End of document. For questions contact the Engineering Team.*
