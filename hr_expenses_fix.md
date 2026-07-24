# HRM Portal — Expense Receipt Fix

## Root Cause

The 404 error happens because:

1. Files uploaded through the **payout portal** are saved to **Supabase private storage** under the path `portal_claims/<vendor_id>_<uuid>.jpeg`.  
2. `receipt_url` in the DB stores only the **raw storage path** (e.g. `portal_claims/47986eb1-e652-490f-8a8d-9eb104ffa206_1e5f04647c9347e69058bc49e085ecd2.jpeg`), **not** a full public URL.
3. The HRM portal frontend does `<a href={e.receipt_url}>` — so the browser navigates to `/hr/portal_claims/xxx.jpeg`, which hits the FastAPI static file mount (`hrm-portal/dist`) → **404 Not Found**.
4. The **payout dashboard** correctly routes through `/payouts/requests/{id}/view-document/{type}`, which generates a **Supabase signed URL** on the fly. The HR expenses tab has no equivalent endpoint.

---

## Fix — Two Parts

### Part 1 — Backend (`routers/hr.py`)

Add two new endpoints **after** the existing `PATCH /expenses/{expense_id}` block (just before `@router.get("/peer-reviews")`):

```python
# ─── EXPENSE RECEIPT ENDPOINTS ──────────────────────────────────────────────

@router.get("/expenses/{expense_id}/view-receipt")
async def view_expense_receipt(
    expense_id: str,
    file_index: int = 0,
    current_admin: dict = Depends(verify_token),
):
    """
    Securely serves an expense receipt/proof document via a Supabase signed URL.
    Mirrors the payout dashboard /view-document endpoint so HR staff can view
    proof files uploaded by staff without them being 404'd by the static server.

    receipt_url may be:
      - A plain storage path:  "portal_claims/abc.jpeg"
      - A JSON array of paths: '["portal_claims/a.jpeg","portal_claims/b.pdf"]'
      - A full https:// URL (external — redirect directly)
    """
    import json
    from fastapi.responses import RedirectResponse
    from storage_service import generate_signed_url

    db = get_db()
    res = await db_execute(
        lambda: db.table("expenditure_requests")
        .select("receipt_url, proforma_url")
        .eq("id", expense_id)
        .maybe_single()
        .execute()
    )
    if not res or not res.data:
        raise HTTPException(status_code=404, detail="Expense record not found")

    raw = res.data.get("receipt_url") or res.data.get("proforma_url")
    if not raw:
        raise HTTPException(status_code=404, detail="No receipt document attached to this expense")

    # Resolve single path vs JSON array
    path = raw
    if raw.startswith("["):
        try:
            paths = json.loads(raw)
            if isinstance(paths, list) and paths:
                idx = max(0, min(file_index, len(paths) - 1))
                path = paths[idx]
        except (ValueError, json.JSONDecodeError):
            pass  # fall through — treat as plain string

    # External URL → redirect directly
    if path.startswith("http"):
        return RedirectResponse(url=path)

    # Private Supabase storage → generate signed URL
    signed_url = generate_signed_url("Cloud Infrastructure", path)
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate secure access link for receipt")

    return RedirectResponse(url=signed_url)


@router.post("/expenses/upload-receipt")
async def upload_expense_receipt(
    file: UploadFile = File(...),
    current_admin: dict = Depends(verify_token),
):
    """
    Uploads a proof/receipt file for an expense claim to Supabase private storage
    (same bucket as payout portal: 'Cloud Infrastructure').
    Returns the storage path so the frontend can POST it as receipt_url when
    submitting a new expense, or PATCH it onto an existing one.
    """
    from storage_service import upload_portal_file

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    # Namespace under portal_claims/ to match payout dashboard convention
    file_path = f"portal_claims/{uuid.uuid4().hex}.{file_ext}"
    file_bytes = await file.read()

    ok = upload_portal_file(file_path, file_bytes, file.content_type)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to upload receipt file. Please retry.")

    return {"path": file_path}
```

---

### Part 2 — Frontend (`hrm-portal/src/App.jsx`)

There are **four** places to update inside `ExpensesManager`. Apply each diff below.

---

#### 2a — Add state for the receipt viewer modal

Find the existing state declarations block near line 9285 (inside `ExpensesManager`), just after:
```jsx
const [payModal, setPayModal] = useState(null);
```
Add:
```jsx
// ── Receipt / proof document viewer (mirrors payout dashboard) ──
const [viewingReceipt, setViewingReceipt] = useState(null); // { id, receipt_url, description }
```

---

#### 2b — Receipt modal component (add just before the closing `</div>` of ExpensesManager's return)

Find the block that ends with:
```jsx
    </div>
  );
}


// ─── BIO DATA COMPONENTS
```

Insert this **before** the `);` that closes the `return`:
```jsx
      {/* ══════════════════════ RECEIPT VIEWER MODAL ══════════════════════ */}
      {viewingReceipt && (() => {
        const raw = viewingReceipt.receipt_url || "";
        let paths = [];
        if (raw.startsWith("[")) {
          try { paths = JSON.parse(raw); } catch { paths = [raw]; }
        } else if (raw) {
          paths = [raw];
        }
        return (
          <Modal onClose={() => setViewingReceipt(null)} title="Expense Proof Documents" width={760}>
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div style={{ padding: 14, background: `${T.orange}0D`, borderRadius: 12, border: `1px solid ${T.orange}22` }}>
                <div style={{ fontSize: 11, color: C.sub, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                  Proof Documentation — {viewingReceipt.description || "Expense Claim"}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  {paths.length > 0 ? paths.map((p, i) => (
                    <a
                      key={i}
                      href={`${API_BASE}/hr/expenses/${viewingReceipt.id}/view-receipt?file_index=${i}`}
                      target="_blank"
                      rel="noreferrer"
                      className="bg"
                      style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", textDecoration: "none" }}
                    >
                      <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span style={{ fontSize: 12 }}>
                        {p.startsWith("http") ? `File #${i + 1}` : `RECEIPT #${i + 1}`}
                      </span>
                    </a>
                  )) : (
                    <div style={{ fontSize: 13, color: C.muted }}>No proof files attached to this expense.</div>
                  )}
                </div>
              </div>
              <div style={{ height: 360, background: "#000", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", color: "#666" }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>📄</div>
                  <div style={{ fontSize: 14 }}>Click a file above to open the proof document</div>
                  <div style={{ fontSize: 11, marginTop: 4, color: "#444" }}>Served via Secure Signed URL</div>
                </div>
              </div>
            </div>
          </Modal>
        );
      })()}
```

---

#### 2c — Fix the "Receipt" link in the expenses table (line ~9666)

**Replace:**
```jsx
{e.receipt_url && <a href={e.receipt_url} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 10, padding: "4px 10px" }}>Receipt</a>}
```
**With:**
```jsx
{e.receipt_url && (
  <button
    className="bg"
    style={{ fontSize: 10, padding: "4px 10px", cursor: "pointer", border: "none" }}
    onClick={() => setViewingReceipt({ id: e.id, receipt_url: e.receipt_url, description: e.description })}
  >
    📎 Receipt
  </button>
)}
```

---

#### 2d — Fix the "📎 View Attached Document" link in the detail drawer (line ~9932)

**Replace:**
```jsx
{(detail.receipt_url || detail.proforma_url) && (
  <a href={detail.receipt_url || detail.proforma_url} target="_blank" rel="noreferrer" className="bp" style={{ textDecoration: "none", textAlign: "center", fontSize: 13, padding: "10px 0" }}>📎 View Attached Document</a>
)}
```
**With:**
```jsx
{(detail.receipt_url || detail.proforma_url) && (
  <button
    className="bp"
    style={{ textDecoration: "none", textAlign: "center", fontSize: 13, padding: "10px 0", cursor: "pointer", border: "none", width: "100%" }}
    onClick={() => setViewingReceipt({ id: detail.id, receipt_url: detail.receipt_url || detail.proforma_url, description: detail.description })}
  >
    📎 View Attached Document
  </button>
)}
```

---

#### 2e — Replace the "Receipt URL" text input with a file upload input in the new expense form (line ~10080)

**Replace:**
```jsx
<div><Lbl>Receipt URL</Lbl><input className="inp" value={form.receipt_url} onChange={e => setForm(f => ({ ...f, receipt_url: e.target.value }))} placeholder="https://…" /></div>
```
**With:**
```jsx
<div>
  <Lbl>Receipt / Proof</Lbl>
  <input
    type="file"
    accept="image/*,application/pdf"
    className="inp"
    style={{ paddingTop: 6 }}
    onChange={async (ev) => {
      const file = ev.target.files?.[0];
      if (!file) return;
      const fd = new FormData();
      fd.append("file", file);
      try {
        const res = await fetch(`${API_BASE}/hr/expenses/upload-receipt`, {
          method: "POST",
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
          body: fd,
        });
        const data = await res.json();
        if (data.path) setForm(f => ({ ...f, receipt_url: data.path }));
        else alert("Upload failed — try again");
      } catch {
        alert("Upload failed — check your connection");
      }
    }}
  />
  {form.receipt_url && (
    <div style={{ fontSize: 10, color: "#10B981", marginTop: 4 }}>
      ✓ File uploaded — will be attached on submit
    </div>
  )}
</div>
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `routers/hr.py` | Add `GET /hr/expenses/{id}/view-receipt` — generates Supabase signed URL for receipt (mirrors payout dashboard) |
| `routers/hr.py` | Add `POST /hr/expenses/upload-receipt` — uploads proof file to private storage, returns path |
| `hrm-portal/src/App.jsx` | Add `viewingReceipt` state + Receipt Viewer Modal (mirrors payout "Document Intelligence" modal) |
| `hrm-portal/src/App.jsx` | Replace bare `<a href={e.receipt_url}>` in table row with button that opens modal |
| `hrm-portal/src/App.jsx` | Replace bare `<a href={detail.receipt_url}>` in detail drawer with button that opens modal |
| `hrm-portal/src/App.jsx` | Replace "Receipt URL" text input with file upload input + auto-upload on select |

> **No DB migration needed.** The `receipt_url` column already exists on `expenditure_requests` and stores the path string. The new endpoints simply add secure serving on top of what is already stored.