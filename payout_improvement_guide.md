# Payout Dashboard — Debug Report & Improvement Guide

> **Codebase:** `POS-eximp-main` · **Target File:** `templates/payouts_dashboard.html` + `routers/payouts.py`

---

## 🔴 Root Cause: Why Commission Pulse & Operational Flow Show ₦0.00

---

### Bug #1 — Missing Fields in the Backend SQL Query *(Primary Cause)*

**File:** `routers/payouts.py` · **Line ~946**

The `/api/payouts/stats/summary` endpoint fetches expenditure records with this SELECT:

```python
.select("amount_gross, net_payout_amount, amount_paid, wht_amount, created_at,
         status, payout_method, vendors(name), admins!requester_id(full_name)")
```

Two critical fields are **absent**:

| Missing Field | Used On | Purpose |
|---|---|---|
| `payment_type` | Line 991 | Detects commission records via `p_type == 'commission'` |
| `vendors(type)` | Line 990 | Detects staff/commission vendors via `v_type == 'staff'` |

**The cascading effect:** Because both detection mechanisms return empty/default values, the categorisation engine (lines 988–1001) sends **every single record** into the `ops` bucket. The `commissions` and `reimbursements` buckets stay permanently at zero regardless of actual data in the database.

#### ✅ The Fix

Change line 946 to include the missing fields:

```python
.select("amount_gross, net_payout_amount, amount_paid, wht_amount, created_at,
         status, payout_method, payment_type, vendors(name, type),
         admins!requester_id(full_name)")
```

---

### Bug #2 — `commission_earnings` Table May Have No Data

Even after Bug #1 is fixed, Commission Pulse PAID/OWED also pulls from a **second separate query** on the `commission_earnings` table (lines 958–964). If that table is empty or has no records within the default 30-day window, the commission cards will remain zero.

**Verify with:**

```sql
SELECT COUNT(*), SUM(commission_amount)
FROM commission_earnings
WHERE is_voided = false;
```

If the count is 0, the `commission_earnings` table needs to be backfilled. The script `backfill_commissions.py` in the root of the project handles this.

---

### Bug #3 — Operational Flow "EXPENSES" Only Shows Disbursed Amounts

On the frontend (line 2593), EXPENSES maps to `seg.ops?.paid` — meaning only **fully disbursed** ops payments appear. Records in `approved` or `partially_paid` status are invisible. If no ops payments have been fully disbursed in the last 30 days, this card also shows ₦0.00.

**Decision needed:** Should EXPENSES show only what has been paid out, or total liability (paid + owed)?  
Recommended: Show `seg.ops?.paid + seg.ops?.owed` as the EXPENSES figure and rename it "TOTAL SPEND".

---

## 📋 Professional Improvement Guide

> Implement these in priority order. Items marked 🔧 require backend changes in `routers/payouts.py`. Items marked 🎨 are frontend-only in `payouts_dashboard.html`.

---

### Priority 1 — Decouple Segment Cards from Heavy Analytics Tab 🎨

**Problem:** `fetchStats()` is the same function that powers the full Intelligence & Reporting tab with 5 charts. When it errors or is slow, the top stat cards also fail silently.

**Fix:** Create a dedicated lightweight function:

```javascript
async function fetchSegmentPulse() {
    try {
        const res = await apiFetch('/api/payouts/stats/summary?days=30');
        const data = await res.json();
        const seg = data.segments || {};

        document.getElementById('stat-comm-paid').innerText  = '₦' + (seg.commissions?.paid || 0).toLocaleString();
        document.getElementById('stat-comm-owed').innerText  = '₦' + (seg.commissions?.owed || 0).toLocaleString();
        document.getElementById('stat-ops-paid').innerText   = '₦' + ((seg.ops?.paid || 0) + (seg.ops?.owed || 0)).toLocaleString();
        document.getElementById('stat-reimb-paid').innerText = '₦' + (seg.reimbursements?.paid || 0).toLocaleString();

        document.getElementById('pulse-last-updated').innerText = 'Updated ' + new Date().toLocaleTimeString();
    } catch (e) {
        ['stat-comm-paid','stat-comm-owed','stat-ops-paid','stat-reimb-paid'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = '<span title="Failed to load — click to retry" onclick="fetchSegmentPulse()" style="cursor:pointer;">— ⚠</span>';
        });
    }
}
```

Call `fetchSegmentPulse()` at page init alongside `fetchRequests()`, and keep `fetchStats()` only for when the Analytics tab is opened.

---

### Priority 2 — Commission Pulse Card Enhancements 🎨 + 🔧

#### Visual improvements:
- Add a **progress bar** showing `paid / (paid + owed)` as a green fill percentage
- Add a **"PENDING"** third metric (commissions earned but not yet in an approved payout request)
- Add a **click-through** that deep-links to the Commission Ledger tab pre-filtered
- Add a **trend arrow** comparing current period owed vs. prior period

#### Example card HTML structure:
```html
<div class="stat-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span>Commission Pulse</span>
        <a onclick="switchTab('commissions', event)" style="font-size:10px; color:var(--gold); cursor:pointer;">VIEW LEDGER →</a>
    </div>
    <div style="display:flex; justify-content:space-between; margin-top:10px;">
        <div>
            <div style="font-size:10px; color:var(--gray);">PAID</div>
            <h4 id="stat-comm-paid" style="font-size:16px;">₦0.00</h4>
        </div>
        <div>
            <div style="font-size:10px; color:var(--error);">OWED</div>
            <h4 id="stat-comm-owed" style="font-size:16px; color:var(--error);">₦0.00</h4>
        </div>
    </div>
    <!-- Progress bar -->
    <div style="height:3px; background:rgba(255,255,255,0.1); border-radius:2px; margin-top:10px;">
        <div id="comm-progress-bar" style="height:100%; background:var(--success); border-radius:2px; width:0%; transition:width 0.6s ease;"></div>
    </div>
    <div id="pulse-last-updated" style="font-size:9px; color:var(--gray); margin-top:6px;"></div>
</div>
```

#### Backend change needed:
Add `pending_count` to the segments response — a count of `commission_earnings` records where `is_paid = false` and no active `expenditure_request` exists for them.

---

### Priority 3 — Add a "Quick Reconcile" Modal 🎨 + 🔧

Add a `RECONCILE` button on the Commission Pulse card. When clicked it opens a modal listing:
- Every sales rep with outstanding owed commissions
- Their individual breakdown (property name, amount, date earned)
- A "Create Payout Request" CTA that pre-populates the expenditure request form

**New backend endpoint required:**
```
GET /api/payouts/stats/commission-breakdown
```
Returns rep-level data: `[{ rep_name, total_owed, oldest_unpaid_date, commissions: [...] }]`

---

### Priority 4 — Operational Flow Card Enhancements 🎨

#### Rename and clarify values:
| Current Label | Current Value | Recommended Label | Recommended Value |
|---|---|---|---|
| EXPENSES | `seg.ops.paid` | TOTAL SPEND | `seg.ops.paid + seg.ops.owed` |
| REIMB. | `seg.reimbursements.paid` | REIMBURSED | `seg.reimbursements.paid` |

#### Add a third column: PENDING CLAIMS
Shows reimbursement requests currently in `pending` status. Requires backend to return `seg.reimbursements.pending` count.

#### Add a mini donut chart:
A small 80px Chart.js doughnut inside the card showing the Ops vs Reimbursements split visually. Pass `seg.ops` and `seg.reimbursements` as the dataset.

---

### Priority 5 — Commission Health Summary Strip 🎨 + 🔧

Add a horizontal info strip **between the stat cards and the tabs**, always visible:

```
[ 🔴 4 reps with unpaid commissions ]  [ ⏱ Oldest unpaid: 14 days ago ]  [ ⚡ Avg payout time: 6.2 days ]
```

This requires the backend to return three new fields in the summary response:
- `reps_with_owed_count` — count of distinct reps with `is_paid = false` commissions
- `oldest_unpaid_days` — age in days of the oldest unpaid `commission_earnings` record
- `avg_payout_velocity` — average days between `commission_earnings.created_at` and the linked payout's `paid_at`

---

### Priority 6 — Loading States & Error Handling on Stat Cards 🎨

Currently when `fetchStats()` or `fetchSegmentPulse()` fails, all cards silently stay at ₦0.00 with no feedback.

**Improvements:**
- Show a shimmer/skeleton loader on each card value while the fetch is in-flight using `data-loading="true"` CSS
- On catch, replace values with `—` and a `⚠` icon with `title="Failed — click to retry"` and `onclick="fetchSegmentPulse()"`
- Add a subtle "last refreshed" timestamp below the cards: *"Updated 3 mins ago"*
- Use `setInterval(fetchSegmentPulse, 120000)` to auto-refresh every 2 minutes

---

### Priority 7 — Budget vs. Actual Tracking for Operational Flow 🎨 + 🔧

Add a monthly budget indicator to the Operational Flow card:
- Store `monthly_ops_budget` in a `system_config` table (key-value)
- Return `budget_limit` alongside `ops.paid` from the backend
- Render a colour-coded indicator:
  - 🟢 Green — under 70% of budget spent
  - 🟡 Amber — 70–90% spent
  - 🔴 Red — over 90% spent

---

### Priority 8 — Per-Segment CSV Export 🎨 + 🔧

The current export covers the full analytics view only. Add `⬇ CSV` buttons on each segment card.

**Backend change:** Extend the existing `/api/payouts/stats/export` endpoint with a new query parameter:
```
GET /api/payouts/stats/export?segment=commissions&days=30
```

**Frontend:** Add a small download icon to each card header:
```html
<span onclick="exportSegment('commissions')" title="Export CSV" style="cursor:pointer; font-size:11px; color:var(--gray);">⬇</span>
```

---

### Priority 9 — Responsive & Accessibility Polish 🎨

- Wrap the four stat cards in `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))` so they never overflow on small screens
- Add `aria-label` to all `<h3>` and `<h4>` stat elements for screen readers
- Colour-coded values (red for owed, green for reimbursed) must also carry icon indicators — never rely on colour alone:
  - Owed → `↑` icon in addition to red
  - Paid/Reimbursed → `✓` icon in addition to green
- Ensure all buttons have visible focus rings for keyboard navigation

---

### Priority 10 — Persistent Sidebar Mini-Summary (Desktop) 🎨

Add a collapsible right-side panel that stays visible while working in any tab:

```
┌─────────────────────┐
│  LIVE SUMMARY        │
│  Commission Owed: ₦X │
│  Ops Spend:      ₦X  │
│  Pending Requests: N │
│  WHT Liability:  ₦X  │
│  [↺ Refresh]         │
└─────────────────────┘
```

This keeps the finance officer oriented without scrolling back to the top stat cards. Only render on screens wider than 1200px using a CSS media query.

---

## 📌 Implementation Checklist

```
[ ] Fix routers/payouts.py line ~946 — add payment_type and vendors(name, type) to SELECT
[ ] Verify commission_earnings table has data (run backfill_commissions.py if empty)
[ ] Clarify EXPENSES display: paid-only vs total liability — update frontend accordingly
[ ] Decouple fetchSegmentPulse() from fetchStats()
[ ] Add progress bar and click-through to Commission Pulse card
[ ] Add Quick Reconcile modal with new /api/payouts/stats/commission-breakdown endpoint
[ ] Rename EXPENSES → TOTAL SPEND and update value calculation
[ ] Add Commission Health summary strip between cards and tabs
[ ] Add loading states and retry logic to all segment cards
[ ] Add auto-refresh interval (every 2 minutes)
[ ] Add per-segment CSV export with segment= query param on backend
[ ] Responsive grid + accessibility pass on stat cards
[ ] (Optional) Budget vs Actual tracking for Operational Flow
[ ] (Optional) Persistent sidebar mini-summary for desktop
```

---

*Guide generated against commit snapshot: `POS-eximp-main` · April 2026*