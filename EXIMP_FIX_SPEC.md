# Eximps & Cloves CRM — Phase 2 Fix Spec
**Priority:** Fix all broken functionality before any new features  
**Files to edit:** `routers/crm_professional.py`, `routers/crm.py`, `templates/professional_crm.html`  
**Do not touch:** Any other router, schema.sql, rbac_migration.sql

---

## BUG FIXES (Must fix first, in order)

---

### FIX 1 — Hot Leads "Access Denied" for Sales Rep
**File:** `routers/crm_professional.py`  
**Function:** `score_all_leads` (~line 80)  
**Root cause:** Line 89 filters `client_type = "lead"` but most clients in the system have `client_type = "client"` or `"subscriber"`. Sales reps have assigned clients but zero match this filter, so the endpoint returns an empty object. The frontend reads `data.detail` on this and shows "Access denied" even though the server returned 200.

**Fix — remove the `client_type` filter entirely:**
```python
# BEFORE (line 89):
query = db.table("clients").select("id, full_name, email, assigned_rep_id").eq("client_type", "lead")

# AFTER:
query = db.table("clients").select("id, full_name, email, assigned_rep_id")
```

**Also fix the frontend check in `loadLeads()` in `professional_crm.html`:**
```javascript
// BEFORE:
if (data.detail) {
    document.getElementById("hotLeadsTable").innerHTML = `<tr>...<td>${data.detail}</td>...</tr>`;
    return;
}

// AFTER — only show error if HTTP response was not ok:
// Remove the data.detail check entirely. The endpoint now always returns a valid object.
// If prioritized_leads is empty, show a friendly empty state instead:
if (!prioritized.length) {
    document.getElementById("hotLeadsTable").innerHTML = `
        <tr><td colspan="6" style="text-align:center; padding:40px; color:#666;">
            No leads assigned to you yet.
        </td></tr>`;
    hidePageLoader();
    return;
}
```

---

### FIX 2 — Outstanding Panel Crashes (SyntaxError: JSON.parse)
**File:** `routers/crm_professional.py`  
**Function:** `get_outstanding_payments` (~line 1184)  
**Root cause:** The nested Supabase join `clients(admins(id, full_name))` via `assigned_rep_id` is ambiguous — Supabase cannot resolve which FK relationship to use between `clients.assigned_rep_id` and `admins.id`. It returns an HTML error page instead of JSON, which breaks `JSON.parse` in the frontend.

**Fix — split into two queries:**
```python
@router.get("/manager/outstanding")
async def get_outstanding_payments(current_admin=Depends(verify_token)):
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    if not any(r in ["admin", "operations", "super_admin", "sales_manager"] for r in roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    # Query 1: Get all non-voided invoices with client info only (no nested admin join)
    invoices = (await db_execute(lambda: db.table("invoices")
        .select("client_id, amount, amount_paid, clients(id, full_name, pipeline_stage, last_contacted_at, assigned_rep_id)")
        .neq("status", "voided")
        .execute())).data or []
    
    # Aggregate by client
    client_map = {}
    rep_ids = set()
    for inv in invoices:
        client = inv.get("clients") or {}
        cid = inv.get("client_id")
        if not cid:
            continue
        if cid not in client_map:
            assigned_rep_id = client.get("assigned_rep_id")
            client_map[cid] = {
                "client_id": cid,
                "client_name": client.get("full_name"),
                "pipeline_stage": client.get("pipeline_stage"),
                "last_contacted_at": client.get("last_contacted_at"),
                "assigned_rep_id": assigned_rep_id,
                "assigned_rep_name": "Unassigned",
                "total_amount": 0,
                "total_paid": 0,
            }
            if assigned_rep_id:
                rep_ids.add(assigned_rep_id)
        client_map[cid]["total_amount"] += float(inv.get("amount") or 0)
        client_map[cid]["total_paid"] += float(inv.get("amount_paid") or 0)
    
    # Query 2: Fetch rep names separately using collected rep_ids
    rep_name_map = {}
    if rep_ids:
        reps = (await db_execute(lambda: db.table("admins")
            .select("id, full_name")
            .in_("id", list(rep_ids))
            .execute())).data or []
        rep_name_map = {r["id"]: r["full_name"] for r in reps}
    
    # Enrich with rep names and filter to outstanding only
    outstanding = []
    for c in client_map.values():
        balance = c["total_amount"] - c["total_paid"]
        if balance > 0:
            c["outstanding"] = balance
            c["assigned_rep_name"] = rep_name_map.get(c["assigned_rep_id"], "Unassigned")
            del c["assigned_rep_id"]  # clean up internal field
            outstanding.append(c)
    
    outstanding.sort(key=lambda x: x["outstanding"], reverse=True)
    return outstanding
```

---

### FIX 3 — `showNotification` is Undefined
**File:** `templates/professional_crm.html`  
**Root cause:** `showNotification()` is called in three places inside the support desk section but only `showToast()` is defined. This silently breaks ticket resolution, group chat invitations, and task creation success messages.

**Fix — add one line immediately after the `showToast` function definition:**
```javascript
// Add this line right after the closing brace of showToast():
const showNotification = (msg, type) => showToast(msg, type);
```

---

### FIX 4 — Lead Detail Modal Stage Dropdown Has Wrong Stages
**File:** `templates/professional_crm.html`  
**Element:** `<select id="detail-lead-stage">`  
**Root cause:** The dropdown options are `lead, offer, contract, closed (Won)` — the old stage names. The actual pipeline uses `lead, nurturing, interest, paid, closed`. Saving from this modal writes the wrong stage value to the database and breaks Kanban grouping.

**Fix — replace the select options:**
```html
<!-- FIND this select element (id="detail-lead-stage") and replace its options: -->
<select id="detail-lead-stage" onchange="saveLeadStage()" style="...existing styles...">
    <option value="lead">1. Lead</option>
    <option value="nurturing">2. Nurturing</option>
    <option value="interest">3. Interest</option>
    <option value="paid">4. Paid</option>
    <option value="closed">5. Closed</option>
</select>
```

---

### FIX 5 — Manager Feed Nested Join May Also Fail
**File:** `routers/crm_professional.py`  
**Function:** `get_manager_feed` (~line 1137)  
**Root cause:** The select includes `admins(id, full_name)` joined from `activity_log.performed_by → admins.id`. This join should work since `performed_by` is a direct FK to `admins`, but verify it uses the correct Supabase join syntax.

**Fix — ensure the select string is explicit:**
```python
# FIND in get_manager_feed:
query = db.table("activity_log")\
    .select("id, event_type, description, created_at, metadata, clients(id, full_name, pipeline_stage), admins(id, full_name)")\

# REPLACE WITH (explicit FK hint for performed_by):
query = db.table("activity_log")\
    .select("id, event_type, description, created_at, metadata, performed_by, client_id, clients(id, full_name, pipeline_stage), admins!activity_log_performed_by_fkey(id, full_name)")\
```

---

## UX IMPROVEMENTS

---

### UX 1 — Sales Rep Needs a Persistent Task Indicator
**Problem:** Tasks are loaded and shown only inside the `leads` view. If a rep navigates away, they lose sight of tasks. There is no badge or indicator telling them tasks exist.

**File:** `templates/professional_crm.html`

**Fix A — Add a task badge on the sidebar "Hot Leads" nav link:**

Find the Hot Leads nav link in the sidebar and add a badge span:
```html
<!-- FIND: -->
<div class="nav-link active" onclick="switchView('leads')">
    <i class="fas fa-fire"></i> Hot Leads
</div>

<!-- REPLACE WITH: -->
<div class="nav-link active" onclick="switchView('leads')">
    <i class="fas fa-fire"></i> Hot Leads
    <span id="tasksBadge" style="display:none; background:#ef4444; color:#fff; border-radius:10px; font-size:10px; font-weight:700; padding:1px 7px; margin-left:auto;"></span>
</div>
```

**Fix B — Update `loadMyTasks()` to show/hide the badge:**
```javascript
// At the end of loadMyTasks(), after rendering tasks, add:
const badge = document.getElementById('tasksBadge');
if (badge) {
    if (tasks.length > 0) {
        badge.textContent = tasks.length;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}
```

**Fix C — Call `loadMyTasks()` on every page load (not just when switching to leads view):**
```javascript
// In the DOMContentLoaded block at the bottom of the script, add:
loadMyTasks(); // load tasks on initial page open so badge shows immediately
```

---

### UX 2 — Manager Needs a Standalone "Assign Task" Button
**Problem:** The only way a manager can assign a task is through the Activity Feed or Outstanding Panel. Both have issues (Feed requires scrolling to find a client row, Outstanding was broken). There is no proactive "I want to assign a task to a rep for a specific client" flow.

**File:** `templates/professional_crm.html`

**Fix — Add an "Assign Task" button to the Manager Feed header:**
```html
<!-- FIND the manager-feed header-section div and add a button: -->
<div class="header-section">
    <div>
        <h1 class="page-title">Activity Feed</h1>
        <p style="color:#888; margin-top:4px;">All rep activity — calls, notes, stage moves, in real time</p>
    </div>
    <!-- ADD THIS: -->
    <button onclick="openAssignTaskModal('', '')" class="btn btn-primary">
        <i class="fas fa-plus mr-2"></i> Assign Task
    </button>
</div>
```

When `openAssignTaskModal('', '')` is called with empty strings, the modal opens with no client pre-selected. The manager can then pick a rep and type in the task without needing to start from a specific client row. The `assignTaskClientLabel` will show "General Task" which is already handled in the existing `openAssignTaskModal()` function.

---

### UX 3 — Rep Name on Kanban Card
**Problem:** You can't see who a lead is assigned to without opening the detail modal. Managers reviewing the pipeline are blind to assignment at a glance.

**File:** `templates/professional_crm.html`  
**Function:** `loadPipeline()` card render

**Fix — add assigned rep name below the client name on each card:**

Find where `lead.full_name` is rendered in the card HTML and add a rep line below it:
```javascript
// FIND in the card HTML template inside loadPipeline():
<div style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px;">${lead.full_name || 'Unknown Client'}</div>

// ADD immediately after it:
${lead.assigned_rep_name ? 
    `<div style="font-size:10px; color:#888; margin-bottom:4px;">
        <i class="fas fa-user" style="font-size:9px; color:#555;"></i> ${lead.assigned_rep_name}
    </div>` 
    : ''}
```

This works because `GET /api/crm/pipeline` in `crm.py` already returns `assigned_rep_id` per lead. You need to also add `assigned_rep_name` to the pipeline endpoint response. Update `get_sales_pipeline` in `crm.py`:

```python
# After the existing section that builds fin_map, add a rep_name lookup:

# Collect all assigned_rep_ids
rep_ids = list(set(l["assigned_rep_id"] for l in all_leads if l.get("assigned_rep_id")))
rep_name_map = {}
if rep_ids:
    reps = (await db_execute(lambda: db.table("admins")
        .select("id, full_name")
        .in_("id", rep_ids)
        .execute())).data or []
    rep_name_map = {r["id"]: r["full_name"] for r in reps}

# Then in the loop where you build each lead dict, add:
lead["assigned_rep_name"] = rep_name_map.get(lead.get("assigned_rep_id"), "")
```

---

### UX 4 — Hot Leads Auto-Loads on Page Open
**Problem:** The Hot Leads page shows zero data until the user clicks "Analyze All Leads". First impression is a broken page.

**File:** `templates/professional_crm.html`  
**Function:** `DOMContentLoaded` block

**Fix — `loadLeads()` is already called in DOMContentLoaded. The issue is that it returns early when `prioritized_leads` is empty.** After Fix 1 above removes the `client_type` filter, this will start working automatically. No additional change needed here beyond Fix 1.

---

### UX 5 — `team/assignable` Endpoint Excludes `sales_manager` Role
**File:** `routers/crm_professional.py`  
**Function:** `get_assignable_team` (~line 1057)  
**Problem:** The endpoint only returns admins with roles `sales`, `operations`, or `customer_support`. A `sales_manager` cannot be assigned leads or tasks because they don't appear in the dropdown.

**Fix:**
```python
# BEFORE:
if any(r in ["sales", "operations", "customer_support"] for r in roles):

# AFTER:
if any(r in ["sales", "sales_manager", "operations", "customer_support"] for r in roles):
```

---

### UX 6 — Activity Logs Rep Filter Excludes `sales_manager`
**File:** `templates/professional_crm.html`  
**Function:** `loadActivityLogs()`

The rep filter dropdown is currently only shown when `role === "admin"` or `role === "legal"`. Operations and sales_manager are excluded.

**Fix — update the role check:**
```javascript
// FIND in loadActivityLogs():
if (role === "admin" || role === "legal") {

// REPLACE WITH:
const logsRoles = role ? role.split(',').map(r => r.trim().toLowerCase()) : [];
if (logsRoles.some(r => ['admin', 'super_admin', 'operations', 'sales_manager'].includes(r))) {
```

---

## IMPLEMENTATION ORDER

1. **Fix 1** — Remove `client_type` filter + fix frontend empty state check
2. **Fix 2** — Split outstanding query into two separate queries
3. **Fix 3** — Add `showNotification` alias
4. **Fix 4** — Correct stage dropdown options in lead detail modal
5. **Fix 5** — Explicit FK hint in manager feed query
6. **UX 5** — Add `sales_manager` to assignable team endpoint
7. **UX 6** — Fix activity log rep filter role check
8. **UX 1** — Task badge on sidebar nav link
9. **UX 2** — Standalone Assign Task button in manager feed header
10. **UX 3** — Rep name on Kanban card (requires pipeline endpoint update in crm.py)
11. **UX 4** — Auto-resolves after Fix 1, no extra work needed

---

## WHAT IS WORKING CORRECTLY (Do not change)

- Pipeline lock toggle — working
- Call `tel:` button on Kanban and Contacts list — working
- WhatsApp button — working
- Pre-call modal with localStorage pending — working
- Call outcome logging endpoint — working
- `last_contacted_at` update on call and note — working
- Contacts list view with search and stage filter — working
- Task creation endpoint (`POST /tasks`) — working
- Task status update endpoint (`PATCH /tasks/{id}`) — working
- Role upgrade endpoint (`PATCH /team/{admin_id}/role`) — working
- Role manager UI in Team view — working
- Migration SQL (already run or ready to run) — correct
- `sanitizePhoneForWhatsApp()` — working
- `formatTimeAgo()` — working
- `showToast()` — working
- Pipeline RBAC (rep sees only assigned leads) — working
- `sales_manager` RBAC across most endpoints — working