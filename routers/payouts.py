from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, File, UploadFile, Form, Body, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from database import get_db, db_execute
from models import ExpenditureRequestCreate, PayoutReview, AssetCreate, VendorCreate, VoidExpenditureRequest, PayoutPaymentData
from routers.auth import verify_token, has_any_role, require_roles, resolve_admin_token
from email_service import send_payout_receipt_email, send_portal_invite_email, send_report_email, send_receipt_email
from commission_service import sync_invoice_commissions
from report_service import ReportService
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json
import uuid
import pandas as pd
import io
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

# ─── WHT 2025 HELPER ──────────────────────────────────────────
def calculate_wht_2025(amount: Decimal, category: str, has_tin: bool = True, is_resident: bool = True) -> dict:
    """
    Implements Nigerian WHT Regulations 2024 (Effective Jan 2025).
    Category: 'professional', 'goods', 'construction', 'rent', 'commission'
    """
    # 1. Base Rates (Resident)
    base_rates = {
        'professional': Decimal('0.05'),
        'goods': Decimal('0.02'),
        'construction': Decimal('0.02'),
        'rent': Decimal('0.10'),
        'commission': Decimal('0.05'),
        'other': Decimal('0.02')
    }
    
    # 2. Base Rates (Non-Resident)
    non_resident_rates = {
        'professional': Decimal('0.10'),
        'goods': Decimal('0.05'),
        'construction': Decimal('0.05'),
        'rent': Decimal('0.10'),
        'commission': Decimal('0.10'),
        'other': Decimal('0.05')
    }
    
    rate = base_rates.get(category, Decimal('0.02')) if is_resident else non_resident_rates.get(category, Decimal('0.05'))
    
    # 3. Penalty for No TIN (Double the rate)
    if not has_tin:
        rate = rate * 2
        
    wht_amount = amount * rate
    return {
        "rate": rate,
        "wht_amount": wht_amount,
        "net_amount": amount - wht_amount
    }

class PayoutPaymentData(BaseModel):
    amount: float
    payment_method: str = "transfer"
    reference: Optional[str] = None

class VerifyRequest(BaseModel):
    action: str
    reason: Optional[str] = None
    due_date: Optional[str] = None

@router.post("/vendors")
async def create_vendor(data: VendorCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("vendors").insert(data.dict()).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create vendor")
    return res.data[0]

@router.patch("/vendors/{vendor_id}/commission-config")
async def update_vendor_commission_config(vendor_id: str, payload: dict, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    update_data = {}
    if "is_commission_partner" in payload: update_data["is_commission_partner"] = bool(payload["is_commission_partner"])
    if "gross_commission_rate" in payload: update_data["gross_commission_rate"] = float(payload["gross_commission_rate"])
    if "wht_rate" in payload: update_data["wht_rate"] = float(payload["wht_rate"])
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No configuration provided")
        
    res = await db_execute(lambda: db.table("vendors").update(update_data).eq("id", vendor_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    return res.data[0]

@router.get("/vendors")
async def list_vendors(type: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("vendors").select("*")
    if type:
        query = query.eq("type", type)
    res = await db_execute(lambda: query.order("name").execute())
    return res.data

# ─── EXPENDITURE REQUESTS ─────────────────────────────────────
@router.post("/requests")
async def submit_payout_request(data: ExpenditureRequestCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    vendor_id = data.vendor_id
    # Inline vendor creation (e.g. for one-off staff claims)
    if not vendor_id and data.vendor_data:
        vendor_res = await db_execute(lambda: db.table("vendors").insert(data.vendor_data.dict()).execute())
        if vendor_res.data:
            vendor_id = vendor_res.data[0]['id']
            
    # Calculate WHT Suggestion
    # Note: For staff reimbursements, WHT is typically NOT applicable by default
    wht_details = {"rate": 0, "wht_amount": 0, "net_amount": data.amount_gross}
    
    if data.is_wht_applicable:
        vendor_res = await db_execute(lambda: db.table("vendors").select("tin, type").eq("id", vendor_id).execute())
        vendor = vendor_res.data[0]
        has_tin = bool(vendor.get('tin'))
        # Default to 'professional' for services, 'goods' if mentioned
        cat = 'goods' if 'get' in data.title.lower() or 'buy' in data.title.lower() else 'professional'
        wht_details = calculate_wht_2025(data.amount_gross, cat, has_tin=has_tin)

    payload = {
        "title": data.title,
        "description": data.description,
        "vendor_invoice_number": data.vendor_invoice_number,
        "requester_id": current_admin['sub'],
        "vendor_id": vendor_id,
        "amount_gross": float(data.amount_gross),
        "payout_method": data.payout_method,
        "is_wht_applicable": data.is_wht_applicable,
        "wht_rate": float(wht_details['rate']),
        "wht_amount": float(wht_details['wht_amount']),
        "wht_exemption_reason": data.wht_exemption_reason,
        "net_payout_amount": float(wht_details['net_amount']),
        "proforma_url": data.proforma_url,
        "receipt_url": data.receipt_url,
        "category": data.category or "General",
        "property_id": data.property_id,
        "development_category": data.development_category,
        "status": "pending_verification"
    }
    
    res = await db_execute(lambda: db.table("expenditure_requests").insert(payload).execute())
    return res.data[0]

@router.get("/requests")
async def list_expenditure_requests(status: Optional[str] = None, show_voided: bool = False, vendor_type: Optional[str] = None, payout_method: Optional[str] = None, payment_type: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("expenditure_requests").select("*, vendors(*), admins!requester_id(full_name), expenditure_payments(*), company_assets(*)")
    
    if status:
        query = query.eq("status", status)
    
    if not show_voided:
        query = query.neq("status", "voided")

    if payout_method:
        query = query.eq("payout_method", payout_method)

    if payment_type:
        query = query.eq("payment_type", payment_type)
        
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    data = res.data

    # Filter by vendor type in Python (vendors is a joined object, not a direct column)
    if vendor_type:
        data = [r for r in data if (r.get("vendors") or {}).get("type") == vendor_type]

    return data

@router.post("/requests/{request_id}/payments")
async def record_payout_payment(request_id: str, data: PayoutPaymentData, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    # 1. Verify Request
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    
    amount_to_pay = float(data.amount)
    current_paid = float(req.get('amount_paid', 0))
    net_payout = float(req.get('net_payout_amount', 0))
    
    # Ensure amount doesn't wildly exceed balance
    if current_paid + amount_to_pay > net_payout + 0.05: # Float fuzziness
        raise HTTPException(status_code=400, detail="Payment amount exceeds remaining balance.")
        
    # 2. Insert Payment Record
    payment_payload = {
        "request_id": request_id,
        "amount": amount_to_pay,
        "payment_method": data.payment_method,
        "reference": data.reference,
        "paid_by": current_admin['sub']
    }
    await db_execute(lambda: db.table("expenditure_payments").insert(payment_payload).execute())
    
    # 3. Update Request
    new_paid = current_paid + amount_to_pay
    new_status = "paid" if new_paid >= net_payout - 0.05 else "partially_paid"
    
    update_payload = {
        "amount_paid": new_paid,
        "status": new_status,
        "payout_reference": data.reference,
    }
    
    if new_status == "paid":
        update_payload["paid_at"] = datetime.now(timezone.utc).isoformat()
        
    update_res = await db_execute(lambda: db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute())
    
    # Trigger automated receipt
    if update_res.data:
        req_with_vendor = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
        if req_with_vendor.data:
            full_req = req_with_vendor.data[0]
            vendor = full_req.get('vendors')
            if vendor and vendor.get('email'):
                bg_tasks.add_task(send_payout_receipt_email, full_req, vendor, current_admin['sub'], payment_amount=amount_to_pay)

    return {"status": "success", "new_status": new_status, "amount_paid": new_paid}

@router.patch("/requests/{request_id}/verify")
async def verify_bill_request(
    request_id: str,
    data: VerifyRequest,
    bg_tasks: BackgroundTasks,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """
    Bill Verification: promotion to 'pending' (audit queue) triggers revenue sync for portal claims.
    """
    if not has_any_role(current_admin, ["admin", "operations"]):
        raise HTTPException(status_code=403, detail="Only authorized roles can perform this action")
    
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    req = req_res.data[0]
    action = data.action  # 'pending' or 'rejected'
    
    if action == 'pending':
        # --- BI-DIRECTIONAL SYNC (Revenue CRM) ---
        if req.get("invoice_id"):
            inv_id = req["invoice_id"]
            # Fetch Invoice and Client for receipting
            inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", inv_id).execute())
            if inv_res.data:
                invoice = inv_res.data[0]
                client = invoice.get("clients")
                # 1. Update Invoice Balance
                # Note: We need the client's payment amount, not the commission (gross).
                # The commission_base is what we want. We'll try to extract it from the claim or metadata.
                # For now, if it's a commission claim, we reverse-calc the payment amount from the gross commission.
                is_commission = req.get("payment_type") in ["initial_deposit", "instalment"]
                client_payment_amount = float(req["amount_gross"])
                if is_commission:
                    # gross = payment * rate -> payment = gross / rate
                    # BUG FIX: Handle wht_rate as a decimal (0.05) or percentage (5.0)
                    rate = float(req.get("wht_rate", 0.1))
                    if rate > 1.0: rate = rate / 100.0
                    
                    if rate > 0:
                        client_payment_amount = float(req["amount_gross"]) / rate
                    else:
                        client_payment_amount = float(req["amount_gross"])
                    # Actually, let's use the property_price if initial_deposit, else try to find the payment amount
                    # I'll update the portal submit to store the payment_amount in metadata
                    client_payment_amount = float(req.get("description", "").split("Amt: ")[-1].split()[0]) if "Amt: " in req.get("description", "") else float(req["amount_gross"])
                
                new_paid = float(invoice.get("amount_paid", 0)) + client_payment_amount
                await db_execute(lambda: db.table("invoices").update({"amount_paid": new_paid, "status": "paid" if new_paid >= float(invoice["amount"]) else "partial"}).eq("id", inv_id).execute())

                # 2. Assign Rep if missing
                if not invoice.get("sales_rep_id"):
                    vendor = req.get("vendors")
                    if vendor and vendor.get("email"):
                        rep_res = await db_execute(lambda: db.table("sales_reps").select("id").eq("email", vendor["email"]).execute())
                        if rep_res.data:
                            await db_execute(lambda: db.table("invoices").update({"sales_rep_id": rep_res.data[0]["id"]}).eq("id", inv_id).execute())

                # 3. Log CRM Payment
                payment_payload = {
                    "client_id": invoice["client_id"],
                    "invoice_id": inv_id,
                    "amount": client_payment_amount,
                    "payment_method": "portal_reported",
                    "reference": f"CLAIM-{req['id'][:8]}",
                    "payment_date": datetime.now(timezone.utc).isoformat(),
                }
                await db_execute(lambda: db.table("payments").insert(payment_payload).execute())

                # 4. Sync Commission Ledger (Option A)
                # This will create the commission_earnings record for the rep
                bg_tasks.add_task(sync_invoice_commissions, inv_id, db, current_admin['sub'])

                # 5. Notify Client (Automated Receipt)
                if client and client.get("email"):
                    bg_tasks.add_task(send_receipt_email, invoice, client, current_admin['sub'])

    # Update Expenditure Status
    update_payload = {
        "status": action,
        "reviewed_by": current_admin['sub'],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if action == 'rejected':
        update_payload["rejection_reason"] = data.reason or "Bill rejected at verification stage"
    elif action == 'pending' and data.due_date:
        update_payload["due_date"] = data.due_date
    
    await db_execute(lambda: db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute())
    return {"status": "success", "new_status": action}

@router.put("/requests/{request_id}/review")
async def review_payout_request(request_id: str, data: PayoutReview, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    if not has_any_role(current_admin, "admin"):
        raise HTTPException(status_code=403, detail="Only Admins can approve payouts")
        
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    update_payload = {
        "status": data.status,
        "reviewed_by": current_admin['sub'],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "payout_reference": data.payout_reference,
        "rejection_reason": data.rejection_reason if data.status == 'rejected' else req.get('rejection_reason'),
        "wht_exemption_reason": req.get('wht_exemption_reason')
    }
    
    # Handle WHT Override (as requested by user)
    if not data.apply_wht and data.status == 'approved':
        update_payload["is_wht_applicable"] = False
        update_payload["wht_rate"] = 0
        update_payload["wht_amount"] = 0
        update_payload["net_payout_amount"] = req['amount_gross']
    elif data.manual_wht_rate is not None and data.status == 'approved':
        rate = data.manual_wht_rate
        amt = Decimal(str(req['amount_gross'])) * rate
        update_payload["wht_rate"] = float(rate)
        update_payload["wht_amount"] = float(amt)
        update_payload["net_payout_amount"] = float(Decimal(str(req['amount_gross'])) - amt)

    if data.status == 'approved':
        update_payload['paid_at'] = datetime.now(timezone.utc).isoformat()

    res = await db_execute(lambda: db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute())
    updated_req = res.data[0]

    # ─── ASSET AUTOMATION ────────────────────────────────────
    # If this was a procurement/tool request, auto-log it as a company asset
    if data.status == 'approved' and req.get('payout_method') == 'procurement':
        try:
            # Generate a simple unique Asset ID
            asset_slug = "".join([w[0] for w in req['title'].split() if w]).upper()[:4]
            asset_id_code = f"EC-{asset_slug}-{str(uuid.uuid4())[:4].upper()}"
            
            asset_payload = {
                "asset_id": asset_id_code,
                "name": req['title'],
                "category": "Equipment", # Default, can be refined in Asset view
                "purchase_cost": float(req['amount_gross']),
                "purchase_date": datetime.now(timezone.utc).date().isoformat(),
                "procurement_id": request_id,
                "assigned_to": req.get('requester_id'),
                "current_status": "assigned",
                "notes": f"Auto-logged via Procurement Approval. Ref: {request_id}"
            }
            
            await db_execute(lambda: db.table("company_assets").insert(asset_payload).execute())
        except Exception as asset_err:
            print(f"⚠️ Warning: Payout approved but Asset logging failed: {asset_err}")
            # We don't fail the whole payout if asset logging hits a snag, but we log it.

    # ─── TRIGGER APPROVAL NOTIFICATION EMAIL ──────────────────────
    # On approve: send an approval notification (not a payment receipt — no money has moved yet).
    # The payment receipt is sent separately when /payments is called.
    if data.status == 'approved' and updated_req.get('vendor_id'):
        # Re-fetch with vendor join AFTER the update so net_payout_amount / wht_amount
        # reflect the post-approval values (WHT overrides applied above).
        receipt_res = await db_execute(
            lambda: db.table('expenditure_requests').select('*, vendors(*)').eq('id', request_id).execute()
        )
        if receipt_res.data:
            full_req = receipt_res.data[0]
            vendor = full_req.get('vendors')
            if vendor and vendor.get('email'):
                from email_service import send_expense_approval_email
                bg_tasks.add_task(send_expense_approval_email, full_req, vendor, current_admin['sub'])

    return updated_req

class WhtRemittanceData(BaseModel):
    receipt_reference: str
    request_ids: List[str]

@router.post("/requests/remit-wht")
async def record_wht_remittance(data: WhtRemittanceData, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Batch clears WHT liabilities by marking them remitted to FIRS."""
    db = get_db()
    if not data.request_ids:
        raise HTTPException(status_code=400, detail="No requests selected for remittance")
        
    update_payload = {
        "is_wht_remitted": True,
        "wht_remittance_ref": data.receipt_reference,
        "wht_remitted_at": datetime.now(timezone.utc).isoformat(),
        "wht_remitted_by": current_admin['sub']
    }
    
    res = await db_execute(lambda: db.table("expenditure_requests").update(update_payload).in_("id", data.request_ids).execute())
    return {"status": "success", "cleared_count": len(res.data) if res.data else 0}

@router.post("/requests/{request_id}/send-receipt")
async def trigger_manual_receipt(request_id: str, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Manually triggers a remittance advice email to the vendor."""
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    vendor = req.get('vendors')
    if not vendor or not vendor.get('email'):
        raise HTTPException(status_code=400, detail="Vendor has no email address on file")
        
    bg_tasks.add_task(send_payout_receipt_email, req, vendor, current_admin['sub'])
    return {"status": "success", "message": f"Receipt queued for {vendor['email']}"}

# ─── ASSETS ───────────────────────────────────────────────────
@router.post("/assets")
async def record_company_asset(data: AssetCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    # 1. Insert the asset
    asset_data = data.dict(exclude={"auto_expense"})
    res = await db_execute(lambda: db.table("company_assets").insert(asset_data).execute())
    new_asset = res.data[0]
    
    # 2. Automated Expense Flow (Option 2)
    if data.auto_expense and data.purchase_cost and data.purchase_cost > 0:
        expense_payload = {
            "title": f"Asset Purchase: {data.name}",
            "description": f"Automated expense log for {data.category} (SN: {data.serial_number or 'N/A'})",
            "amount_gross": float(data.purchase_cost),
            "amount_paid": float(data.purchase_cost),
            "net_payout_amount": float(data.purchase_cost),
            "status": "paid",
            "payout_method": "direct_pay",
            "requester_id": current_admin['sub'],
            "category": "Capital Expenditure",
            "is_wht_applicable": False,
            "created_at": data.purchase_date.isoformat() if data.purchase_date else datetime.now().isoformat()
        }
        await db_execute(lambda: db.table("expenditure_requests").insert(expense_payload).execute())
        
    return new_asset

@router.get("/assets")
async def list_assets(assigned_to: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("company_assets").select("*, admins!assigned_to(full_name)")
    if assigned_to:
        query = query.eq("assigned_to", assigned_to)
    res = await db_execute(lambda: query.execute())
    return res.data


# ─── SECURE STORAGE ACCESS ────────────────────────────────────
from storage_service import generate_signed_url, upload_portal_file
from fastapi.responses import RedirectResponse

@router.get("/requests/{request_id}/view-document/{doc_type}")
async def view_secure_payout_document(
    request_id: str,
    doc_type: str,
    file_index: int = 0,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    """
    Securely redirects to a signed URL for proformas or receipts.
    doc_type: 'proforma', 'receipt'
    file_index: for multi-file receipts (JSON array stored in receipt_url), selects which file to view.
    """
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = req_res.data[0]
    raw_path = req.get('proforma_url') if doc_type == 'proforma' else req.get('receipt_url')

    if not raw_path:
        raise HTTPException(
            status_code=404,
            detail=f"No {doc_type} document attached to this record."
        )

    # Resolve path — may be a single string or a JSON array (multi-file upload)
    path = raw_path
    if raw_path.startswith('['):
        try:
            paths = json.loads(raw_path)
            if not isinstance(paths, list) or len(paths) == 0:
                raise ValueError
            # Clamp index to valid range
            idx = max(0, min(file_index, len(paths) - 1))
            path = paths[idx]
        except (ValueError, json.JSONDecodeError):
            pass  # Fall through — treat raw_path as a plain string

    # Redirect to external URLs directly
    if path.startswith("http"):
        return RedirectResponse(url=path)

    # Generate signed URL for private Supabase bucket 'Cloud Infrastructure'
    signed_url = generate_signed_url("Cloud Infrastructure", path)
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate secure access link")

    return RedirectResponse(url=signed_url)


@router.get("/requests/{request_id}/proof-files")
async def list_proof_files(request_id: str, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """
    Returns the list of proof file paths for a request.
    For single-file records returns a 1-element array.
    For multi-file records (receipt_url is a JSON array) returns all entries.
    """
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("receipt_url, proforma_url, title").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = req_res.data[0]
    receipt_raw = req.get('receipt_url') or ''
    proforma_raw = req.get('proforma_url') or ''

    def parse_paths(raw: str) -> list:
        if not raw:
            return []
        if raw.startswith('['):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, list) else [raw]
            except (ValueError, json.JSONDecodeError):
                pass
        return [raw]

    return {
        "id": request_id,
        "title": req.get('title', ''),
        "receipt_files": parse_paths(receipt_raw),
        "proforma_files": parse_paths(proforma_raw),
        "total": len(parse_paths(receipt_raw)) + len(parse_paths(proforma_raw)),
    }


# ─── PORTAL AUTOMATION ────────────────────────────────────────

class PortalInvite(BaseModel):
    email: str
    category: str # 'staff', 'company', or 'individual'

@router.post("/requests/portal-invite")
async def trigger_portal_invite(data: PortalInvite, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Triggers a professional system email invitation with a unique token."""
    db = get_db()
    
    # 1. Fetch current admin for the invitation signature
    admin_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", current_admin['sub']).execute())
    admin_name = admin_res.data[0]['full_name'] if admin_res.data else "Eximp & Cloves Finance"
    
    # 2. Generate or Update Invite Token
    token = str(uuid.uuid4())
    invite_payload = {
        "email": data.email,
        "category": data.category,
        "token": token,
        "invited_by": current_admin['sub'],
        "is_used": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert the invite (so re-inviting updates the token/category)
    await db_execute(lambda: db.table("portal_invites").upsert(invite_payload, on_conflict="email").execute())
    
    # 3. Generate Link
    # Note: In production, window.location.origin would be used on frontend, 
    # here we assume the portal is at /payout/portal/{token}
    
    bg_tasks.add_task(send_portal_invite_email, data.email, admin_name, token)
    
    return {
        "status": "success", 
        "message": f"Invitation queued for {data.email}",
        "token": token
    }

@router.get("/payout/portal/invite/{token}")
async def resolve_portal_invite(token: str):
    """Checks the validity of an invitation token and returns the context."""
    db = get_db()
    
    # 1. Validate Token
    invite_res = await db_execute(lambda: db.table("portal_invites").select("*").eq("token", token).execute())
    if not invite_res.data:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation link")
    
    invite = invite_res.data[0]
    
    # 2. Check if Payee is already onboarded
    payee_res = await db_execute(lambda: db.table("vendors").select("*").eq("email", invite['email']).execute())
    is_onboarded = len(payee_res.data) > 0
    payee_data = payee_res.data[0] if is_onboarded else None
    
    return {
        "email": invite['email'],
        "category": invite['category'],
        "is_onboarded": is_onboarded,
        "payee_data": payee_data
    }

@router.get("/portal/lookup-invoice")
async def portal_lookup_invoice(invoice_number: str, claimant_email: Optional[str] = None):
    """
    Rich invoice lookup for commission claims.
    Returns payment type (initial_deposit vs instalment), rep conflict status,
    payment history, and commission preview.
    """
    db = get_db()

    # 1. Fetch invoice with client data
    res = await db_execute(lambda: db.table("invoices")
        .select("id, client_id, amount, amount_paid, property_name, sales_rep_id, sales_rep_name, clients(full_name)")
        .eq("invoice_number", invoice_number)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Invoice not found. Please check the number and try again.")

    inv = res.data[0]
    invoice_id = inv["id"]

    # 2. Fetch ALL actual confirmed client payments for this invoice (oldest first).
    #    This is the ground truth — we use real payments, not portal claims, to decide
    #    what has and hasn't been claimed yet.
    payments_res = await db_execute(lambda: db.table("payments")
        .select("id, amount, created_at, payment_method")
        .eq("invoice_id", invoice_id)
        .order("created_at")
        .execute()
    )
    all_payments = payments_res.data or []
    payment_count = len(all_payments)

    property_price     = float(inv.get("amount") or 0)
    amount_paid_so_far = float(inv.get("amount_paid") or 0)
    balance            = max(0.0, property_price - amount_paid_so_far)

    # 3. Find which payments have already been claimed.
    #    Source A: commission_earnings ledger (dashboard-verified commissions).
    #    Source B: expenditure_requests portal claims (self-reported, pending approval).
    commission_earnings_res = await db_execute(lambda: db.table("commission_earnings")
        .select("payment_id")
        .eq("invoice_id", invoice_id)
        .execute()
    )
    ledger_claimed_payment_ids = {
        e["payment_id"] for e in (commission_earnings_res.data or []) if e.get("payment_id")
    }

    portal_claims_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("id, payment_type, status")
        .eq("vendor_invoice_number", invoice_number)
        .neq("status", "rejected")
        .execute()
    )
    portal_claims = portal_claims_res.data or []
    # Count how many initial_deposit and instalment claims already exist in the portal
    portal_initial_count    = len([c for c in portal_claims if c.get("payment_type") == "initial_deposit"])
    portal_instalment_count = len([c for c in portal_claims if c.get("payment_type") == "instalment"])

    # 4. Build the unclaimed payments list.
    #    payment index 0 = initial deposit, 1+ = instalments.
    unclaimed_payments = []
    instalment_portal_used = 0
    for i, p in enumerate(all_payments):
        ptype = "initial_deposit" if i == 0 else "instalment"

        # Check ledger first (most authoritative)
        if p["id"] in ledger_claimed_payment_ids:
            continue

        # Check portal claims by type+sequence
        if ptype == "initial_deposit" and portal_initial_count > 0:
            continue
        if ptype == "instalment":
            if instalment_portal_used < portal_instalment_count:
                instalment_portal_used += 1
                continue

        comm_base = property_price if ptype == "initial_deposit" else float(p.get("amount") or 0)
        unclaimed_payments.append({
            "seq":            i + 1,
            "payment_id":     p["id"],
            "amount":         float(p.get("amount") or 0),
            "date":           (p.get("created_at") or "")[:10],
            "method":         p.get("payment_method") or "—",
            "payment_type":   ptype,
            "commission_base": comm_base,
        })

    # 5. Determine what to present to the claimant.
    #    - If unclaimed payments exist, point them at the OLDEST unclaimed one first.
    #    - payment_sequence reflects the NEXT UNCLAIMED payment position, not total count.
    if unclaimed_payments:
        next_unclaimed   = unclaimed_payments[0]
        payment_type     = next_unclaimed["payment_type"]
        commission_base  = next_unclaimed["commission_base"]
        payment_sequence = next_unclaimed["seq"]  # actual position in payment history
    else:
        # All confirmed payments are already claimed
        payment_type     = "instalment"
        commission_base  = None
        payment_sequence = payment_count + 1

    # ── Resolve display commission rate for the preview card ──
    # Read global defaults from system_settings so the preview matches what submit will calculate.
    _prev_sys_res = await db_execute(lambda: db.table("system_settings")
        .select("key, value")
        .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
        .execute()
    )
    _prev_sys = {s["key"]: s["value"] for s in (_prev_sys_res.data or [])}

    # Check vendor-specific rate first
    _prev_vrate_res = await db_execute(lambda: db.table("vendors")
        .select("gross_commission_rate, wht_rate, is_commission_partner")
        .eq("email", claimant_email)
        .execute()
    )
    _prev_vdata = ((_prev_vrate_res.data or [None])[0]) or {}
    _is_partner = bool(_prev_vdata.get("is_commission_partner"))

    def _pct(val, fallback):
        try:
            v = float(val)
            return v / 100 if v > 1 else v
        except Exception:
            return fallback

    if _prev_vdata.get("gross_commission_rate"):
        _display_gross_rate = _pct(_prev_vdata["gross_commission_rate"], 0.15 if _is_partner else 0.10)
        _display_wht_rate   = _pct(_prev_vdata.get("wht_rate") or 5, 0.05)
    elif _is_partner and _prev_sys.get("default_partner_commission_rate"):
        _display_gross_rate = _pct(_prev_sys["default_partner_commission_rate"], 0.15)
        _display_wht_rate   = _pct(_prev_sys.get("default_wht_rate") or 5, 0.05)
    elif not _is_partner and _prev_sys.get("default_commission_rate"):
        _display_gross_rate = _pct(_prev_sys["default_commission_rate"], 0.10)
        _display_wht_rate   = _pct(_prev_sys.get("default_wht_rate") or 5, 0.05)
    else:
        _display_gross_rate = 0.15 if _is_partner else 0.10
        _display_wht_rate   = 0.05

    commission_rate    = round(_display_gross_rate, 4)
    commission_wht     = round(_display_wht_rate, 4)
    commission_preview = round(commission_base * commission_rate, 2) if (payment_type == "initial_deposit" and commission_base) else None

    # 3. Sales rep conflict detection
    rep_status = "unassigned"
    assigned_rep_name = None
    assigned_rep_email = None

    if inv.get("sales_rep_id"):
        rep_res = await db_execute(lambda: db.table("sales_reps")
            .select("id, name, email")
            .eq("id", inv["sales_rep_id"])
            .execute()
        )
        if rep_res.data:
            rep = rep_res.data[0]
            assigned_rep_name = rep.get("name") or inv.get("sales_rep_name") or "Unknown Rep"
            assigned_rep_email = (rep.get("email") or "").lower()

            if claimant_email:
                rep_status = "yours" if claimant_email.lower() == assigned_rep_email else "conflict"
            else:
                rep_status = "conflict"
    elif inv.get("sales_rep_name"):
        # Name recorded but no ID link yet
        assigned_rep_name = inv.get("sales_rep_name")
        # If claimant name can be verified against vendor table
        if claimant_email:
            vendor_check = await db_execute(lambda: db.table("vendors")
                .select("name")
                .eq("email", claimant_email)
                .execute()
            )
            if vendor_check.data:
                vendor_name = vendor_check.data[0].get("name", "").lower()
                rep_status = "yours" if assigned_rep_name.lower() in vendor_name or vendor_name in assigned_rep_name.lower() else "conflict"
            else:
                rep_status = "conflict"
        else:
            rep_status = "conflict"

    client_name = inv["clients"]["full_name"] if inv.get("clients") else "Unknown Client"

    return {
        "status": "success",
        "invoice_id": invoice_id,
        "client_name": client_name,
        "property_name": inv.get("property_name") or "—",
        "property_price": property_price,
        "amount_paid": amount_paid_so_far,
        "balance": balance,
        # ── Payment type intelligence ──
        "payment_type": payment_type,            # "initial_deposit" | "instalment"
        "payment_sequence": payment_sequence,    # total payments + 1
        "payment_count": payment_count,          # how many confirmed client payments exist
        # ── Commission preview ──
        "commission_rate": commission_rate,       # gross rate as decimal e.g. 0.15
        "commission_wht":  commission_wht,        # WHT rate as decimal e.g. 0.05
        "commission_net_rate": round(commission_rate * (1 - commission_wht), 6),
        "commission_rate_pct": f"{round(commission_rate * 100, 2):.4g}%",  # display e.g. "15%"
        "commission_base": commission_base,       # None → use reported claim_amount
        "commission_preview": commission_preview, # pre-calc for deposit; null for instalment
        # ── Rep assignment ──
        "rep_status": rep_status,                # "unassigned" | "yours" | "conflict"
        "assigned_rep_name": assigned_rep_name,
        # ── Unclaimed payments ──
        # Full list of confirmed client payments that have no commission claim yet.
        # Frontend uses this to warn the claimant about missed commissions.
        "unclaimed_payments": unclaimed_payments,
        "unclaimed_count": len(unclaimed_payments),
        # Portal claims that are pending verification/approval (not yet paid, not rejected)
        # Frontend shows these so the claimant knows what's already in the queue.
        "pending_portal_claims": [
            {
                "payment_type": c.get("payment_type"),
                "status": c.get("status"),
            }
            for c in portal_claims
            if c.get("status") not in ("rejected", "paid")
        ],
        # ── Full payment history with per-payment commission status ──
        "previous_payments": _build_previous_payments(all_payments, ledger_claimed_payment_ids, unclaimed_payments, inv),
    }


def _build_previous_payments(all_payments, ledger_claimed_ids, unclaimed_payments, inv):
    """Build per-payment history list with commission_status for the portal table."""
    _unclaimed_ids = {u["payment_id"] for u in unclaimed_payments}
    result = []
    for i, p in enumerate(all_payments):
        result.append({
            "seq": i + 1,
            "payment_id": p["id"],
            "amount": float(p.get("amount") or 0),
            "date": (p.get("created_at") or "")[:10],
            "method": p.get("payment_method") or "—",
            "payment_type": "initial_deposit" if i == 0 else "instalment",
            "commission_status": (
                "claimed"   if p["id"] in ledger_claimed_ids else
                "unclaimed" if p["id"] in _unclaimed_ids else
                "pending"
            ),
            "commission_base": (
                float(inv.get("amount") or 0) if i == 0
                else float(p.get("amount") or 0)
            ),
        })
    return result

@router.get("/portal/fetch-vendor")
async def portal_fetch_vendor(email: str):
    """Fetches existing vendor details to auto-fill the portal for returning users."""
    db = get_db()
    res = await db_execute(lambda: db.table("vendors").select("*").eq("email", email).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Vendor not found")
    # Return non-sensitive contact and bank details for auto-fill
    v = res.data[0]
    return {
        "status": "success", 
        "data": {
            "name": v.get("name"),
            "phone": v.get("phone"),
            "rc_number": v.get("rc_number"),
            "tin": v.get("tin"),
            "bank_name": v.get("bank_name"),
            "account_number": v.get("account_number"),
            "account_name": v.get("account_name")
        }
    }


@router.post("/portal/submit")
async def submit_payout_claim_from_portal(
    type: str = Form(...), # office, staff_commission, partner
    payee_name: str = Form(...),
    payee_email: str = Form(...),
    payee_phone: str = Form(""),
    payee_id: str = Form(""),
    payee_tin: str = Form(""),
    claim_amount: float = Form(...),
    remarks: str = Form(""),
    invoice_number: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    acc_number: Optional[str] = Form(None),
    acc_name: Optional[str] = Form(None),
    is_already_paid: bool = Form(False),
    payout_reference: Optional[str] = Form(None),
    # ── NEW: payment type & dispute fields ──
    payment_type: Optional[str] = Form(None),        # "initial_deposit" | "instalment"
    property_price: Optional[float] = Form(None),    # full property value (for deposit commission)
    is_dispute: bool = Form(False),                  # True when another rep is already assigned
    dispute_reason: Optional[str] = Form(None),      # required when is_dispute=True
    # ── Portal payment verification field ──
    # Only sent when the invoice has no existing unpaid commission claim.
    # Represents the actual amount the client paid (not the commission).
    client_paid_amount: Optional[float] = Form(None),
    files: List[UploadFile] = File(default=[])  # Accepts one or many proof uploads
):
    """
    Unified endpoint for the 'Claims & Payouts' portal.
    Handles Office Expenditures, Staff Commissions, and Partner Commissions.
    Now supports initial deposit vs instalment differentiation and rep dispute escalation.
    """
    db = get_db()
    
    # Default status logic
    final_status = "paid" if is_already_paid else "pending_verification"

    # ── Validate dispute submission ──
    if is_dispute and not dispute_reason:
        raise HTTPException(status_code=400, detail="A reason is required when raising a rep ownership dispute.")

    # 1a. Check if this payee is a known staff member (admin) FIRST — before vendor
    #     resolution. This lets us set vendor.type='staff' correctly for ALL submission
    #     types (office, disbursement, staff_commission), fixing the mismatch where
    #     office expenditures from known staff were being stored as vendor.type='company',
    #     making them invisible to the HR expenses tab which filters on vendors.type='staff'.
    staff_check = await db_execute(lambda: db.table("admins").select("id").eq("email", payee_email).execute())
    is_known_staff = bool(staff_check.data)
    requester_id = staff_check.data[0]['id'] if is_known_staff else None

    # Resolve the correct vendor type up front
    def resolve_vendor_type(submission_type: str, known_staff: bool) -> str:
        if known_staff or submission_type == "staff_commission":
            return "staff"
        if submission_type == "partner":
            return "individual"
        return "company"

    correct_vendor_type = resolve_vendor_type(type, is_known_staff)

    # 1b. Vendor / Payee Resolution
    existing_vendor = await db_execute(lambda: db.table("vendors").select("id, type").eq("email", payee_email).execute())
    if existing_vendor.data:
        vendor_id = existing_vendor.data[0]['id']
        vendor_update = {
            "name": payee_name,
            "phone": payee_phone,
            "rc_number": payee_id,
            "tin": payee_tin,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if bank_name and acc_number:
            vendor_update.update({
                "bank_name": bank_name,
                "account_number": acc_number,
                "account_name": acc_name
            })
        # Correct the vendor type if it was previously wrong (e.g. 'company' for a staff member).
        # This retroactively fixes existing vendors so their past records become visible in HR tab.
        if existing_vendor.data[0].get('type') != correct_vendor_type and correct_vendor_type == "staff":
            vendor_update["type"] = "staff"
            if requester_id:
                vendor_update["admin_id"] = requester_id
        await db_execute(lambda: db.table("vendors").update(vendor_update).eq("id", vendor_id).execute())
    else:
        vendor_data = {
            "type": correct_vendor_type,
            "name": payee_name,
            "email": payee_email,
            "phone": payee_phone,
            "rc_number": payee_id,
            "tin": payee_tin,
            "bank_name": bank_name,
            "account_number": acc_number,
            "account_name": acc_name
        }
        v_res = await db_execute(lambda: db.table("vendors").insert(vendor_data).execute())
        vendor_id = v_res.data[0]['id']

    # 1c. Requester Resolution — admin check already done above (staff_check).
    #     Fall back to vendor admin_id link or invite record if not found.
    if not requester_id:
        v_link = await db_execute(lambda: db.table("vendors").select("admin_id").eq("email", payee_email).not_.is_("admin_id", "null").execute())
        if v_link.data:
            requester_id = v_link.data[0]['admin_id']
    
    # Final safety check: if we still don't have requester_id, try a direct email lookup on admins table one last time
    if not requester_id:
        final_staff_check = await db_execute(lambda: db.table("admins").select("id").eq("email", payee_email).execute())
        if final_staff_check.data:
            requester_id = final_staff_check.data[0]['id']

    if not requester_id:
        inv_res = await db_execute(lambda: db.table("portal_invites").select("invited_by").eq("email", payee_email).execute())
        if inv_res.data:
            requester_id = inv_res.data[0]['invited_by']

    # 1d. Category Mapping
    category_map = {
        "office": "Office Expenditure",
        "staff_commission": "Sales Commission",
        "partner": "Partner Payout",
        "company": "Company Expenditure",
        "contractor": "Contractor Payout",
        "disbursement": "Office Expenditure"
    }
    category = category_map.get(type, "General Expenditure")

    # 2. Commission Logic (Staff & Partner) & Fraud/Dispute Shield
    is_high_risk = False
    risk_notes = []
    linked_invoice_id = None

    if type in ["staff_commission", "partner"] and invoice_number:
        inv_res = await db_execute(lambda: db.table("invoices")
            .select("id, client_id, sales_rep_id, sales_rep_name, amount, clients(full_name, email)")
            .eq("invoice_number", invoice_number)
            .execute()
        )
        if inv_res.data:
            inv = inv_res.data[0]
            linked_invoice_id = inv["id"]

            # --- SMART ANALYSIS: Flagging instead of Blocking to avoid 'Glitches' ---
            
            # 1. Check Dashboard for existing verified payments
            check_earn = await db_execute(lambda: db.table("commission_earnings")
                .select("id, created_at, is_paid")
                .eq("invoice_id", linked_invoice_id)
                .eq("payment_amount", claim_amount)
                .execute())
            
            if check_earn.data:
                match = check_earn.data[0]
                is_high_risk = True # Mark for attention
                verified_date = match["created_at"][:10]
                status_label = "PAID" if match["is_paid"] else "VERIFIED/UNPAID"
                risk_notes.append(
                    f"🔍 SYSTEM MATCH: A dashboard record for this amount (₦{claim_amount:,.0f}) was already {status_label} on {verified_date}. "
                    "HR should verify if this is a duplicate or a new instalment."
                )

            # 2. Check Portal for existing claims (Pending/Approved)
            check_portal = await db_execute(lambda: db.table("expenditure_requests")
                .select("id, status, created_at")
                .eq("invoice_id", linked_invoice_id)
                .eq("category", "Sales Commission")
                .neq("status", "rejected")
                .execute())
            
            if check_portal.data:
                is_high_risk = True
                risk_notes.append(
                    f"🚩 POTENTIAL DUPLICATE: {len(check_portal.data)} other claim(s) exist in the portal for this invoice. "
                    "Please cross-check before approving."
                )

            # ── Rep dispute escalation ──
            if is_dispute:
                is_high_risk = True
                existing_rep = inv.get("sales_rep_name") or f"Rep ID {inv.get('sales_rep_id', 'unknown')}"
                risk_notes.append(
                    f"⚠️ REP OWNERSHIP DISPUTE: {payee_name} ({payee_email}) is challenging "
                    f"existing assignment to '{existing_rep}'. "
                    f"Reason given: {dispute_reason}"
                )
            else:
                # Standard fraud checks
                if inv.get("clients"):
                    cid = inv["client_id"]
                    act_res = await db_execute(lambda: db.table("activity_log")
                        .select("id").eq("client_id", cid).execute()
                    )
                    if not act_res.data:
                        is_high_risk = True
                        risk_notes.append("🚩 NO CRM HISTORY: Client exists but has zero logged activity.")
                else:
                    is_high_risk = True
                    risk_notes.append("🚩 ANONYMOUS INVOICE: Not yet linked to a verified client record.")

        # ── Commission rate resolution (3-tier waterfall) ──
        #
        # Tier 1 — Vendor's own rate (per-partner override set in dashboard)
        # Tier 2 — system_settings global defaults
        #           · default_partner_commission_rate  (partners)
        #           · default_commission_rate          (staff)
        #           · default_wht_rate                 (both)
        # Tier 3 — hardcoded fallback: Partners = 15%, Staff = 10%, WHT = 5%

        # Fetch global settings once (used as Tier 2 fallback)
        _sys_res = await db_execute(lambda: db.table("system_settings")
            .select("key, value")
            .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
            .execute()
        )
        _sys = {s["key"]: s["value"] for s in (_sys_res.data or [])}

        def _to_dec(pct_str, fallback):
            """Convert a stored percentage string e.g. '15' or '0.15' to a Decimal fraction."""
            try:
                v = Decimal(str(pct_str))
                return v / 100 if v > 1 else v
            except Exception:
                return Decimal(str(fallback))

        if type == "partner":
            # Tier 1: vendor's own rate
            _vrate_res = await db_execute(lambda: db.table("vendors")
                .select("gross_commission_rate, wht_rate")
                .eq("email", payee_email)
                .execute()
            )
            _vdata = (_vrate_res.data or [None])[0] or {}
            if _vdata.get("gross_commission_rate"):
                COMMISSION_RATE = _to_dec(_vdata["gross_commission_rate"], 0.15)
                WHT_RATE        = _to_dec(_vdata.get("wht_rate") or 5, 0.05)
            elif _sys.get("default_partner_commission_rate"):
                # Tier 2: global partner default from system_settings
                COMMISSION_RATE = _to_dec(_sys["default_partner_commission_rate"], 0.15)
                WHT_RATE        = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
            else:
                # Tier 3: hardcoded
                COMMISSION_RATE = Decimal("0.15")
                WHT_RATE        = Decimal("0.05")
        else:
            # Staff: no per-vendor override — use global setting or hardcoded
            if _sys.get("default_commission_rate"):
                COMMISSION_RATE = _to_dec(_sys["default_commission_rate"], 0.10)
                WHT_RATE        = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
            else:
                COMMISSION_RATE = Decimal("0.10")
                WHT_RATE        = Decimal("0.05")

        if payment_type == "initial_deposit" and property_price and property_price > 0:
            commission_base = Decimal(str(property_price))
            payment_type_label = "Initial Deposit Commission"
        else:
            commission_base = Decimal(str(claim_amount))
            payment_type_label = "Instalment Commission" if payment_type == "instalment" else "Commission"

        gross = commission_base * COMMISSION_RATE
        wht = gross * WHT_RATE
        net = gross - wht

        title = (
            f"{'Staff' if type == 'staff_commission' else 'Partner'} "
            f"{payment_type_label}: {invoice_number}"
        )
    else:
        # Office / Company / Contractor Expenditure
        gross = Decimal(str(claim_amount))
        wht = Decimal("0")
        net = gross
        title = f"{category}: {payee_name}"

    # 3. File Upload — supports multiple proof files.
    # Each file is uploaded to the 'Cloud Infrastructure' private bucket.
    # receipt_url is stored as a plain path string (1 file) or a JSON array (2+ files).
    file_url = None
    if files:
        uploaded_paths = []
        upload_errors = []
        for f in files:
            if f and f.filename:  # guard against empty slots
                file_ext = f.filename.rsplit('.', 1)[-1] if '.' in f.filename else 'bin'
                file_path = f"portal_claims/{vendor_id}_{uuid.uuid4().hex}.{file_ext}"
                file_bytes = await f.read()
                ok = upload_portal_file(file_path, file_bytes, f.content_type)
                if ok:
                    uploaded_paths.append(file_path)
                else:
                    upload_errors.append(f.filename)

        if upload_errors:
            # Surface partial failures — do not silently swallow them
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload proof file(s): {', '.join(upload_errors)}. Please retry."
            )

        if len(uploaded_paths) == 1:
            file_url = uploaded_paths[0]          # plain string — fully backward-compatible
        elif len(uploaded_paths) > 1:
            file_url = json.dumps(uploaded_paths)  # JSON array for multi-file

    # 4. Create Record
    payload = {
        "title": title,
        "description": f"Portal submission via {type}\nAmt: {gross}",
        "remarks": remarks or None,
        "vendor_id": vendor_id,
        "invoice_id": linked_invoice_id,
        "amount_gross": float(gross),
        "wht_rate": 5 if type in ["staff_commission", "partner"] else 0,
        "wht_amount": float(wht),
        "net_payout_amount": float(net),
        "receipt_url": file_url,
        "status": final_status,
        "payout_reference": payout_reference if final_status == "paid" else None,
        "paid_at": datetime.now(timezone.utc).isoformat() if is_already_paid else None,
        "is_high_risk": is_high_risk,
        "risk_notes": "\n".join(risk_notes) if risk_notes else None,
        "source_platform": "payout_portal",
        "requester_id": requester_id,
        "category": category,
        # ── NEW fields ──
        "payment_type": payment_type,           # "initial_deposit" | "instalment" | null
        "is_disputed": is_dispute,
        "dispute_reason": dispute_reason if is_dispute else None,
        "vendor_invoice_number": invoice_number,
    }

    await db_execute(lambda: db.table("expenditure_requests").insert(payload).execute())

    # ── Portal Payment Verification ──
    # When the claimant supplies a client_paid_amount (only shown when the invoice
    # has no existing unpaid commission claim), create a pending_verifications row
    # so Finance can confirm it in the Verifications tab — badged as "Portal".
    if client_paid_amount and client_paid_amount > 0 and linked_invoice_id and type in ("partner", "staff_commission"):
        try:
            inv_for_verif = await db_execute(lambda: db.table("invoices").select("client_id").eq("id", linked_invoice_id).execute())
            verif_client_id = inv_for_verif.data[0]["client_id"] if inv_for_verif.data else None
            if verif_client_id:
                verif_payload = {
                    "invoice_id": linked_invoice_id,
                    "client_id": verif_client_id,
                    "deposit_amount": float(client_paid_amount),
                    "payment_proof_url": file_url,
                    "payment_date": datetime.now(timezone.utc).date().isoformat(),
                    "sales_rep_name": payee_name,
                    "status": "pending",
                    "source": "portal",
                    "submission_type": type,  # "partner" or "staff_commission"
                }
                await db_execute(lambda: db.table("pending_verifications").insert(verif_payload).execute())
        except Exception as verif_err:
            print(f"[WARN] Failed to create pending_verifications row for portal submission: {verif_err}")

    # Notify all HRM admins of new payout/commission submission
    try:
        from routers.hr import notify_hr_admins
        is_commission_req = (type == "staff_commission")
        notif_type = "payout_commission_request" if is_commission_req else "payout_reimbursement_request"
        amount_str = f"₦{float(claim_amount):,.0f}" if claim_amount else "an amount"
        if is_commission_req:
            notif_title = "Commission Request Submitted"
            notif_message = f"💼 Commission request: {payee_name} submitted a claim for {amount_str}. Review in Commissions."
        else:
            notif_title = "Reimbursement Request Submitted"
            notif_message = f"🧾 Reimbursement request: {payee_name} submitted a claim for {amount_str}. Review in Expenses."
        await notify_hr_admins(title=notif_title, message=notif_message, notification_type=notif_type)
    except Exception as notif_err:
        print(f"[WARN] Payout notification dispatch failed: {notif_err}")

    # 5. Auto-assign rep on uncontested claims (rep_status was "unassigned")
    #    Only assign if this is NOT a dispute and NOT already assigned.
    if linked_invoice_id and not is_dispute and not is_high_risk:
        # Check if invoice still has no rep
        check_inv = await db_execute(lambda: db.table("invoices").select("sales_rep_id").eq("id", linked_invoice_id).execute())
        if check_inv.data and not check_inv.data[0].get("sales_rep_id"):
            rep_res = await db_execute(lambda: db.table("sales_reps")
                .select("id")
                .eq("email", payee_email)
                .execute()
            )
            if rep_res.data:
                await db_execute(lambda: db.table("invoices")
                    .update({"sales_rep_id": rep_res.data[0]["id"], "sales_rep_name": payee_name})
                    .eq("id", linked_invoice_id)
                    .execute()
                )

    status_message = (
        "Dispute lodged. Finance will review and contact both parties."
        if is_dispute
        else "Record submitted successfully."
    )
    return {"status": "success", "message": status_message, "is_dispute": is_dispute}


# ─────────────────────────────────────────────────────────────────────────────
# PORTAL BULK SUBMIT  — multiple commission claims from the payment history table
# ─────────────────────────────────────────────────────────────────────────────
class BulkClaimItem(BaseModel):
    payment_id: str
    payment_type: str           # "initial_deposit" | "instalment"
    amount: float               # the actual payment amount (instalment) or 0 (deposit uses property_price)
    commission_base: float      # resolved by frontend from lookup-invoice data


class BulkSubmitPayload(BaseModel):
    # Claimant identity
    type: str                   # "staff_commission" | "partner"
    payee_name: str
    payee_email: str
    payee_phone: str = ""
    payee_id: str = ""
    payee_tin: str = ""
    bank_name: Optional[str] = None
    acc_number: Optional[str] = None
    acc_name: Optional[str] = None
    # Invoice context
    invoice_number: str
    invoice_id: str
    property_price: float
    is_dispute: bool = False
    dispute_reason: Optional[str] = None
    remarks: str = ""
    # Selections from the payment history table
    claims: List[BulkClaimItem]
    # Optional new-payment log
    new_payment_amount: Optional[float] = None
    claim_on_new_payment: bool = False


@router.post("/portal/submit-bulk")
async def submit_payout_claims_bulk(payload: BulkSubmitPayload):
    """
    Bulk commission claim endpoint for the portal payment history table.
    Creates one expenditure_request per selected payment row so Finance can
    approve each one individually. Also optionally creates a pending_verifications
    row for a new client payment not yet in the system.
    """
    db = get_db()

    if not payload.claims and not payload.new_payment_amount:
        raise HTTPException(status_code=400, detail="No claims selected.")

    if payload.is_dispute and not payload.dispute_reason:
        raise HTTPException(status_code=400, detail="A reason is required for a dispute claim.")

    # ── Vendor / Requester resolution (same logic as portal/submit) ──
    staff_check = await db_execute(lambda: db.table("admins").select("id").eq("email", payload.payee_email).execute())
    is_known_staff = bool(staff_check.data)
    requester_id = staff_check.data[0]["id"] if is_known_staff else None

    correct_vendor_type = "staff" if (is_known_staff or payload.type == "staff_commission") else "individual"

    existing_vendor = await db_execute(lambda: db.table("vendors").select("id, type").eq("email", payload.payee_email).execute())
    if existing_vendor.data:
        vendor_id = existing_vendor.data[0]["id"]
        upd: dict = {"name": payload.payee_name, "phone": payload.payee_phone, "updated_at": datetime.now(timezone.utc).isoformat()}
        if payload.bank_name and payload.acc_number:
            upd.update({"bank_name": payload.bank_name, "account_number": payload.acc_number, "account_name": payload.acc_name})
        if existing_vendor.data[0].get("type") != correct_vendor_type and correct_vendor_type == "staff":
            upd["type"] = "staff"
            if requester_id:
                upd["admin_id"] = requester_id
        await db_execute(lambda: db.table("vendors").update(upd).eq("id", vendor_id).execute())
    else:
        vd = {
            "type": correct_vendor_type, "name": payload.payee_name, "email": payload.payee_email,
            "phone": payload.payee_phone, "rc_number": payload.payee_id, "tin": payload.payee_tin,
            "bank_name": payload.bank_name, "account_number": payload.acc_number, "account_name": payload.acc_name,
        }
        v_res = await db_execute(lambda: db.table("vendors").insert(vd).execute())
        vendor_id = v_res.data[0]["id"]

    if not requester_id:
        v_link = await db_execute(lambda: db.table("vendors").select("admin_id").eq("email", payload.payee_email).not_.is_("admin_id", "null").execute())
        if v_link.data:
            requester_id = v_link.data[0]["admin_id"]

    # ── Commission rate resolution (same 3-tier waterfall) ──
    _sys_res = await db_execute(lambda: db.table("system_settings")
        .select("key, value")
        .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
        .execute()
    )
    _sys = {s["key"]: s["value"] for s in (_sys_res.data or [])}

    def _to_dec(pct_str, fallback):
        try:
            v = Decimal(str(pct_str))
            return v / 100 if v > 1 else v
        except Exception:
            return Decimal(str(fallback))

    if payload.type == "partner":
        _vrate_res = await db_execute(lambda: db.table("vendors").select("gross_commission_rate, wht_rate").eq("email", payload.payee_email).execute())
        _vdata = ((_vrate_res.data or [None])[0]) or {}
        if _vdata.get("gross_commission_rate"):
            COMMISSION_RATE = _to_dec(_vdata["gross_commission_rate"], 0.15)
            WHT_RATE = _to_dec(_vdata.get("wht_rate") or 5, 0.05)
        elif _sys.get("default_partner_commission_rate"):
            COMMISSION_RATE = _to_dec(_sys["default_partner_commission_rate"], 0.15)
            WHT_RATE = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
        else:
            COMMISSION_RATE = Decimal("0.15")
            WHT_RATE = Decimal("0.05")
    else:
        if _sys.get("default_commission_rate"):
            COMMISSION_RATE = _to_dec(_sys["default_commission_rate"], 0.10)
            WHT_RATE = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
        else:
            COMMISSION_RATE = Decimal("0.10")
            WHT_RATE = Decimal("0.05")

    category = "Partner Payout" if payload.type == "partner" else "Sales Commission"
    created_ids = []

    # ── Resolve sales_rep_id for commission_earnings ──
    # We need it to write the ledger entry. Look up via vendor email → sales_reps table.
    _rep_res = await db_execute(lambda: db.table("sales_reps").select("id").eq("email", payload.payee_email).execute())
    _rep_id = _rep_res.data[0]["id"] if _rep_res.data else None

    # Fetch invoice client_id once — used in commission_earnings and pending_verifications
    _inv_meta = await db_execute(lambda: db.table("invoices").select("client_id, property_name").eq("id", payload.invoice_id).execute())
    _client_id     = _inv_meta.data[0]["client_id"]    if _inv_meta.data else None
    _property_name = _inv_meta.data[0]["property_name"] if _inv_meta.data else ""

    # ── Create one expenditure_request per selected claim ──
    # For payments already confirmed in the system, also write commission_earnings
    # immediately so the ledger is up to date without Finance needing a second action.
    for claim in payload.claims:
        base = Decimal(str(claim.commission_base))
        gross = base * COMMISSION_RATE
        wht = gross * WHT_RATE
        net = gross - wht
        ptype_label = "Initial Deposit Commission" if claim.payment_type == "initial_deposit" else "Instalment Commission"
        title = f"{'Partner' if payload.type == 'partner' else 'Staff'} {ptype_label}: {payload.invoice_number}"

        row = {
            "title": title,
            "description": f"Bulk portal submission via {payload.type}\nPayment ID: {claim.payment_id}",
            "remarks": payload.remarks or None,
            "vendor_id": vendor_id,
            "invoice_id": payload.invoice_id,
            "amount_gross": float(gross),
            "wht_rate": 5,
            "wht_amount": float(wht),
            "net_payout_amount": float(net),
            "status": "pending_verification",
            "source_platform": "payout_portal",
            "requester_id": requester_id,
            "category": category,
            "payment_type": claim.payment_type,
            "is_disputed": payload.is_dispute,
            "dispute_reason": payload.dispute_reason if payload.is_dispute else None,
            "vendor_invoice_number": payload.invoice_number,
        }
        res = await db_execute(lambda: db.table("expenditure_requests").insert(row).execute())
        if res.data:
            created_ids.append(res.data[0]["id"])

        # Write commission_earnings for already-confirmed payments.
        # claim.payment_id is the real payments.id — the money is confirmed in the system.
        # This populates the Commissions tab in the payouts dashboard immediately.
        if _rep_id and _client_id and claim.payment_id and not payload.is_dispute:
            try:
                # Guard: skip if already in ledger for this payment
                existing = await db_execute(lambda: db.table("commission_earnings")
                    .select("id").eq("payment_id", claim.payment_id).eq("sales_rep_id", _rep_id).execute()
                )
                if not existing.data:
                    await db_execute(lambda: db.table("commission_earnings").insert({
                        "sales_rep_id":    _rep_id,
                        "invoice_id":      payload.invoice_id,
                        "payment_id":      claim.payment_id,
                        "client_id":       _client_id,
                        "estate_name":     _property_name,
                        "payment_amount":  claim.amount,
                        "commission_rate": float(COMMISSION_RATE * 100),
                        "commission_amount": float(net),
                        "gross_commission":  float(gross),
                        "wht_amount":        float(wht),
                        "net_commission":    float(net),
                        "is_paid": False,
                    }).execute())
            except Exception as ce:
                print(f"[WARN] commission_earnings insert failed for payment {claim.payment_id}: {ce}")

    # ── Optional: new client payment log ──
    file_url = None  # bulk endpoint doesn't handle file uploads — rep attaches separately
    if payload.new_payment_amount and payload.new_payment_amount > 0:
        try:
            inv_for_verif = await db_execute(lambda: db.table("invoices").select("client_id").eq("id", payload.invoice_id).execute())
            verif_client_id = inv_for_verif.data[0]["client_id"] if inv_for_verif.data else None
            if verif_client_id:
                verif_payload = {
                    "invoice_id": payload.invoice_id,
                    "client_id": verif_client_id,
                    "deposit_amount": float(payload.new_payment_amount),
                    "payment_date": datetime.now(timezone.utc).date().isoformat(),
                    "sales_rep_name": payload.payee_name,
                    "status": "pending",
                    "source": "portal",
                    "submission_type": payload.type,
                }
                await db_execute(lambda: db.table("pending_verifications").insert(verif_payload).execute())

                # If rep also wants to claim commission on the new payment, create one more request
                if payload.claim_on_new_payment:
                    base = Decimal(str(payload.new_payment_amount))
                    gross = base * COMMISSION_RATE
                    wht = gross * WHT_RATE
                    net = gross - wht
                    row = {
                        "title": f"{'Partner' if payload.type == 'partner' else 'Staff'} Commission (Pending Payment): {payload.invoice_number}",
                        "description": f"Commission claim on portal-reported payment of ₦{payload.new_payment_amount:,.0f}. Held pending Finance verification.",
                        "remarks": payload.remarks or None,
                        "vendor_id": vendor_id,
                        "invoice_id": payload.invoice_id,
                        "amount_gross": float(gross),
                        "wht_rate": 5,
                        "wht_amount": float(wht),
                        "net_payout_amount": float(net),
                        "status": "pending_verification",
                        "source_platform": "payout_portal",
                        "requester_id": requester_id,
                        "category": category,
                        "payment_type": "instalment",
                        "vendor_invoice_number": payload.invoice_number,
                    }
                    res = await db_execute(lambda: db.table("expenditure_requests").insert(row).execute())
                    if res.data:
                        created_ids.append(res.data[0]["id"])
        except Exception as ve:
            print(f"[WARN] Failed to create pending_verifications for bulk submission: {ve}")

    # Notifications
    try:
        from routers.hr import notify_hr_admins
        notif_type = "payout_commission_request"
        count = len(created_ids)
        await notify_hr_admins(
            title="Commission Request Submitted",
            message=f"💼 {payload.payee_name} submitted {count} commission claim(s) via portal. Review in Commissions.",
            notification_type=notif_type
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"{len(created_ids)} claim(s) submitted successfully.",
        "created_ids": created_ids,
    }


@router.patch("/requests/{request_id}")
async def update_payout_request_status(request_id: str, body: dict, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Simple status update for payout requests (approve/reject from HRM portal)."""
    db = get_db()
    allowed = {"approved", "rejected", "pending"}
    new_status = body.get("status")
    if not new_status or new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(allowed)}")
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("id").eq("id", request_id).limit(1).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    await db_execute(lambda: db.table("expenditure_requests").update({
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", request_id).execute())

    # --- Notification Bridge ---
    # Since HR mostly uses the Expenses tab, we ensure this endpoint also triggers notifications
    # if the claimant is a staff member (requester_id is present).
    try:
        from routers.hr import send_notification
        req_full = await db_execute(lambda: db.table("expenditure_requests")
            .select("*, vendors(name)").eq("id", request_id).maybe_single().execute())
        
        if req_full.data and req_full.data.get("requester_id"):
            exp = req_full.data
            requester_id = exp["requester_id"]
            raw_category = exp.get("category") or ""
            is_commission = "commission" in raw_category.lower() or "commission" in (exp.get("title") or "").lower()
            category_label = "Commission Claim" if is_commission else "Reimbursement Claim"
            amount = exp.get("amount_gross") or 0
            
            status_verb = "approved" if new_status == "approved" else "paid" if new_status == "paid" else "rejected"
            amount_str = f"₦{float(amount):,.0f}"
            
            if new_status == "rejected":
                status_msg = f"❌ Your {category_label} for {amount_str} was declined by HR."
            elif new_status == "paid":
                status_msg = f"✅ Your {category_label} for {amount_str} has been paid successfully."
            else:
                status_msg = f"📩 Your {category_label} for {amount_str} has been {status_verb}."

            await send_notification(requester_id, "Claim Status Update", status_msg, "expense_update")
    except Exception as e:
        print(f"[WARN] Payout notification bridge failed: {e}")

    return {"status": "ok", "new_status": new_status}

@router.patch("/requests/{request_id}/void")
async def void_payout_request(request_id: str, data: VoidExpenditureRequest, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Voids an expenditure request so it's ignored in reporting."""
    if not has_any_role(current_admin, "admin"):
        raise HTTPException(status_code=403, detail="Only Admins can void expenditures")
        
    db = get_db()
    
    # 1. Check if it exists
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("status, title").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    # 2. Update status to voided and log reason
    update_data = {
        "status": "voided",
        "void_reason": data.reason,
        "voided_at": datetime.now(timezone.utc).isoformat(),
        "voided_by": current_admin['sub']
    }
    
    await db_execute(lambda: db.table("expenditure_requests").update(update_data).eq("id", request_id).execute())
    
    # 3. Log Activity
    try:
        from routers.analytics import log_activity
        await log_activity(
            "expenditure_voided",
            f"Expenditure request '{req_res.data[0]['title']}' voided by Admin. Reason: {data.reason}",
            current_admin['sub'],
            metadata={"request_id": request_id}
        )
    except: pass
    
    return {"status": "success", "message": "Expenditure request voided successfully"}


# ─── ANALYTICS & REPORTING ───────────────────────────────────

class SendReportRequest(BaseModel):
    report_type: str
    email: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ScheduleRequest(BaseModel):
    report_type: str
    frequency: str # weekly, monthly
    recipients: List[str]
    is_active: bool = True

@router.get("/stats/summary")
async def get_payout_stats(
    days: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Aggregated stats for the dashboard charts and summary cards with flexible timeframes."""
    db = get_db()
    
    # 1. Date Logic
    if days:
        start_ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        end_ts = datetime.now(timezone.utc).isoformat()
    elif start_date and end_date:
        start_ts = f"{start_date}T00:00:00Z"
        end_ts = f"{end_date}T23:59:59Z"
    else:
        # Default to 30 days if nothing specified
        start_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        end_ts = datetime.now(timezone.utc).isoformat()

    # 2. Main Expenditure Query (Paid & Approved & Partially Paid)
    query = db.table("expenditure_requests")\
        .select("amount_gross, net_payout_amount, amount_paid, wht_amount, created_at, status, payout_method, payment_type, vendors(name, type), admins!requester_id(full_name)")\
        .in_("status", ["paid", "approved", "partially_paid"])\
        .gte("created_at", start_ts)\
        .lte("created_at", end_ts)
        
    res = await db_execute(lambda: query.execute())
    exp_data = res.data or []

    # 2b. Commission Earnings Query (The Earned Ledger)
    comm_query = db.table("commission_earnings")\
        .select("*, sales_reps(name)")\
        .eq("is_voided", False)\
        .gte("created_at", start_ts)\
        .lte("created_at", end_ts)
    
    comm_res = await db_execute(lambda: comm_query.execute())
    comm_data = comm_res.data or []

    # Initialize Intelligence
    segment_stats = {
        "commissions": {"paid": 0, "owed": 0},
        "reimbursements": {"paid": 0, "owed": 0},
        "ops": {"paid": 0, "owed": 0}
    }
    
    payees = {}; requesters = {}; creditors = {}; period_totals = {}
    total_gross = 0; total_paid = 0; total_ap = 0; total_wht = 0
    
    date_format_len = 10 if (days and days <= 31) or (not days and start_date) else 7
    
    # PROCESS EXPENDITURE REQUESTS
    for r in exp_data:
        # Date Bucketing
        bucket = (r.get('created_at') or datetime.now().isoformat())[:date_format_len]
        
        # Financial Parsing
        gross = float(r.get('amount_gross') or 0)
        net = float(r.get('net_payout_amount') or 0)
        paid = float(r.get('amount_paid') or 0)
        wht = float(r.get('wht_amount') or 0)
        owed = max(0, net - paid)
        
        # Categorization
        v_info = r.get('vendors') or {}
        v_type = v_info.get('type', 'company')
        p_type = (r.get('payment_type') or '').lower()
        p_method = (r.get('payout_method') or '').lower()
        
        if p_method == 'reimbursement' or p_type == 'reimbursement':
            cat = "reimbursements"
        elif p_type in ['commission', 'initial_deposit', 'instalment']:
            cat = "commissions"
        elif v_type == 'staff' and p_type == '':
            # Untagged staff payments are treated as reimbursements per user confirmation
            cat = "reimbursements"
        else:
            # Everything else (Company vendors or tagged 'office') defaults to operational expenses
            cat = "ops"
            
        # 1. Payout Aggregation (Cash Flow)
        segment_stats[cat]["paid"] += paid
        total_paid += paid
        
        # 2. Liability Aggregation (Owed) - Mutually Exclusive
        # Commissions are handled in the second loop (the ledger)
        if cat != "commissions":
            segment_stats[cat]["owed"] += owed
            total_ap += owed
        
        # Analytics
        p_name = v_info.get('name', 'General Vendor')
        r_name = (r.get('admins') or {}).get('full_name', 'System')
        payees[p_name] = payees.get(p_name, 0) + paid
        requesters[r_name] = requesters.get(r_name, 0) + gross
        if cat != "commissions" and owed > 0: 
            creditors[p_name] = creditors.get(p_name, 0) + owed
        
        total_gross += gross; total_wht += wht
        period_totals[bucket] = period_totals.get(bucket, 0) + gross

    # PROCESS COMMISSION EARNINGS (The Ledger of Liability & Legacy Payouts)
    for c in comm_data:
        bucket = (c.get('created_at') or datetime.now().isoformat())[:date_format_len]
        gross = float(c.get('gross_commission') or c.get('commission_amount') or 0)
        net = float(c.get('net_commission') or c.get('final_amount') or gross)
        paid_in_ledger = float(c.get('amount_paid') or 0)
        wht_in_ledger = float(c.get('wht_amount') or 0)
        owed = max(0, net - paid_in_ledger)
        
        # Commissions Paid: Aggregate from ledger (catches legacy) + Loop 1 (catches portal partials)
        segment_stats["commissions"]["paid"] += paid_in_ledger
        total_paid += paid_in_ledger
        total_wht += wht_in_ledger
        
        # Commissions Owed: The Ledger is the ONLY source for this to avoid claim/earning double counting.
        segment_stats["commissions"]["owed"] += owed
        total_ap += owed
        
        rep_name = (c.get('sales_reps') or {}).get('name', 'Staff Partner')
        payees[rep_name] = payees.get(rep_name, 0) + paid_in_ledger
        if owed > 0: 
            creditors[rep_name] = creditors.get(rep_name, 0) + owed
        
        total_gross += gross
        period_totals[bucket] = period_totals.get(bucket, 0) + gross

    # 4. ADVANCED ANALYTICS (Aging, Compliance, Velocity)
    aging = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    compliance = {"remitted": 0, "pending": 0}
    pay_times = []
    
    # We need a broader query for aging (all unpaid regardless of date filter)
    aging_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("amount_gross, net_payout_amount, amount_paid, created_at, status")
        .in_("status", ["approved", "partially_paid", "pending"])
        .execute())
    
    now = datetime.now(timezone.utc)
    for r in (aging_res.data or []):
        unpaid = float(r['net_payout_amount'] or 0) - float(r['amount_paid'] or 0)
        if unpaid <= 0: continue
        
        # Use robust pandas parsing for Python 3.10 compatibility with variable subseconds
        created = pd.to_datetime(r['created_at']).to_pydatetime()
        age_days = (now - created).days
        
        if age_days <= 30: aging["0-30"] += unpaid
        elif age_days <= 60: aging["31-60"] += unpaid
        elif age_days <= 90: aging["61-90"] += unpaid
        else: aging["90+"] += unpaid

    # WHT Compliance (from Paid records)
    comp_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("wht_amount, is_wht_remitted")
        .gt("wht_amount", 0)
        .in_("status", ["paid", "partially_paid"])
        .execute())
    for r in (comp_res.data or []):
        val = float(r['wht_amount'] or 0)
        if r.get('is_wht_remitted'): compliance["remitted"] += val
        else: compliance["pending"] += val

    # Global Metrics (Current Snapshot)
    active_res = await db_execute(lambda: db.table("expenditure_requests").select("id", count="exact").eq("status", "pending").execute())
    active_count = active_res.count or 0
    
    asset_res = await db_execute(lambda: db.table("company_assets").select("purchase_cost").execute())
    total_assets = sum(float(r.get('purchase_cost') or 0) for r in (asset_res.data or []))

    # Efficiency (Time to Pay)
    eff_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("created_at, reviewed_at")
        .eq("status", "paid")
        .not_.is_("reviewed_at", "null")
        .limit(50)
        .execute())
    for r in (eff_res.data or []):
        c = pd.to_datetime(r['created_at']).to_pydatetime()
        p = pd.to_datetime(r['reviewed_at']).to_pydatetime()
        pay_times.append((p - c).total_seconds() / 3600)
    avg_speed = sum(pay_times) / len(pay_times) if pay_times else 0

    # Sort Analytics
    top_payees = dict(sorted(payees.items(), key=lambda x: x[1], reverse=True)[:5])
    top_requesters = dict(sorted(requesters.items(), key=lambda x: x[1], reverse=True)[:5])
    top_creditors = dict(sorted(creditors.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "overview": {
            "total_paid": total_paid,
            "total_owed": total_ap,
            "total_wht": compliance["pending"],
            "active_requests": active_count,
            "total_assets": total_assets,
            "avg_pay_hours": round(avg_speed, 1)
        },
        "segments": segment_stats,
        "analytics": {
            "top_payees": top_payees,
            "top_requesters": top_requesters,
            "top_creditors": top_creditors,
            "categories": {k.title(): (v["paid"] + v["owed"]) for k, v in segment_stats.items() if (v["paid"] + v["owed"]) > 0},
            "aging": aging,
            "compliance": compliance
        },
        "trend": [{"month": b, "total": period_totals[b]} for b in sorted(period_totals.keys())]
    }

@router.post("/stats/send-email")
async def send_on_demand_report(
    data: SendReportRequest, 
    bg_tasks: BackgroundTasks, 
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Triggers an immediate report email via background task."""
    try:
        report_data = await ReportService.get_report_data(data.report_type, data.start_date, data.end_date)
        pdf_io = ReportService.generate_pdf(report_data, f"Requested Report: {data.report_type}")
        
        bg_tasks.add_task(
            send_report_email,
            email=data.email,
            subject=f"Requested {data.report_type.replace('_', ' ').title()}",
            report_name=f"{data.report_type}_{datetime.now().strftime('%Y%m%d')}.pdf",
            pdf_bytes=pdf_io.getvalue()
        )
        return {"status": "success", "message": f"Report queued for delivery to {data.email}"}
    except Exception as e:
        logger.error(f"On-demand report failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate or send report")

@router.get("/stats/export")
async def export_payout_report(
    report_type: str = "payout_audit",
    ledger: Optional[str] = None, # new parameter for specific tab export
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Generates CSV export for the specified report type or ledger view."""
    db = get_db()
    
    if ledger:
        # Specialized exports for each dashboard tab
        if ledger == 'commissions':
            res = await db_execute(lambda: db.table("commission_earnings").select("created_at, sales_reps(name), commission_amount, wht_amount, net_commission, is_paid").execute())
            df = pd.DataFrame(res.data)
        elif ledger == 'staff':
            res = await db_execute(lambda: db.table("expenditure_requests").select("created_at, vendors(name), title, category, amount_gross, net_payout_amount, status").eq("vendors.type", "staff").execute())
            df = pd.DataFrame(res.data)
        elif ledger == 'vendors':
            res = await db_execute(lambda: db.table("expenditure_requests").select("created_at, vendors!inner(name, type), title, category, amount_gross, wht_amount, net_payout_amount, status").in_("vendors.type", ["company", "individual"]).execute())
            rows = [r for r in res.data if r.get("vendors") and r["vendors"].get("type") in ("company", "individual")]
            df = pd.DataFrame(rows)
        else:
            res = await db_execute(lambda: db.table("expenditure_requests").select("*").execute())
            df = pd.DataFrame(res.data)
    else:
        # Standard Audit Report
        report_data = await ReportService.get_report_data(report_type, start_date, end_date)
        df = pd.DataFrame(report_data)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data found for the selected criteria")

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    filename = f"{ledger or report_type}_export_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(stream.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/stats/schedule")
async def save_report_schedule(data: ScheduleRequest, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Saves or updates a report schedule."""
    db = get_db()
    payload = {
        "report_type": data.report_type,
        "frequency": data.frequency,
        "recipients": data.recipients,
        "is_active": data.is_active,
        "owner_id": current_admin.get('id')
    }
    
    try:
        res = await db_execute(lambda: db.table("report_schedules").upsert(payload).execute())
        return {"status": "success", "data": res.data[0] if res.data else {}}
    except Exception as e:
        logger.warning(f"Failed to upsert schedule (table might be missing): {e}")
        return {"status": "success", "message": "Automation preference logged."}


# ─── PROCUREMENT EXPENSES ─────────────────────────────────────
from models import ProcurementExpenseCreate

@router.post("/procurement-expenses")
async def create_procurement_expense(data: ProcurementExpenseCreate, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    payload = data.dict(exclude_none=True)
    payload["created_by"] = current_admin['sub']
    
    res = await db_execute(lambda: db.table("procurement_expenses").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to record procurement expense")
    return res.data[0]

@router.get("/procurement-expenses")
async def list_procurement_expenses(property_id: Optional[str] = None, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    query = db.table("procurement_expenses").select("*")
    if property_id:
        query = query.eq("property_id", property_id)
    res = await db_execute(lambda: query.order("expense_date", desc=True).execute())
    return res.data

@router.patch("/procurement-expenses/{expense_id}")
async def update_procurement_expense(expense_id: str, payload: dict, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    update_data = {}
    if "title" in payload: update_data["title"] = payload["title"]
    if "amount" in payload: update_data["amount"] = float(payload["amount"])
    if "category" in payload: update_data["category"] = payload["category"]
    if "amount_paid" in payload: update_data["amount_paid"] = float(payload["amount_paid"])
    if "status" in payload: update_data["status"] = payload["status"]
    if "notes" in payload: update_data["notes"] = payload["notes"]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided")
        
    res = await db_execute(lambda: db.table("procurement_expenses").update(update_data).eq("id", expense_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Expense not found")
    return res.data[0]

@router.post("/procurement-expenses/import")
async def import_procurement_expenses(
    file: UploadFile = File(...),
    property_id: Optional[str] = Form(None),
    estate_draft_id: Optional[str] = Form(None),
    current_admin=Depends(require_roles(["super_admin"]))
):
    """
    Intelligent procurement import engine.
    Detects section headers, metadata, and maps non-standard vendor columns.
    """
    db = get_db()
    content = await file.read()
    
    try:
        # Load data
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content), header=None).fillna('')
        else:
            df = pd.read_excel(io.BytesIO(content), header=None).fillna('')
        
        all_records = []
        current_category = "General"
        project_metadata = {}
        mapping = {}
        mapping_header_row_idx = -1
        
        # KEYWORD DEFINITIONS
        section_keywords = ['QUOTATION FOR', 'WORKS', 'SECTION', 'CATEGORY', 'PROPOSAL']
        header_keywords = {
            'title': ['item', 'description', 'particulars', 'title', 'name'],
            'amount': ['total cost', 'total amount', 'amount', 'grand total', 'final cost'],
            'unit_price': ['unit price', 'rate', 'unit cost', 'price per'],
            'paid': ['paid', 'payment', 'actual'],
            'quantity': ['qty', 'quantity', 'units', 'number', 'count'],
            'duration': ['duration', 'days', 'weeks', 'months', 'period'],
            'budget': ['budget', 'estimate', 'allocation'],
            'vendor': ['vendor', 'supplier', 'contractor', 'company']
        }
        meta_keywords = {
            'location': ['location', 'site', 'project'],
            'date': ['date', 'quotation date'],
            'company': ['company', 'vendor', 'contractor']
        }

        # PASS 1: SCAN FOR METADATA & DATA
        for i, row in df.iterrows():
            row_list = [str(v).strip() for v in row]
            row_text = ' '.join([v for v in row_list if v]).upper()
            
            # 1. Extract Project Metadata (from top rows)
            if i < 15: # Usually in header
                for key, aliases in meta_keywords.items():
                    if key not in project_metadata:
                        for alias in aliases:
                            if alias.upper() in row_text:
                                # Try to get value from next cell or after colon
                                for cell in row_list:
                                    if alias.upper() in cell.upper() and ':' in cell:
                                        val = cell.split(':', 1)[1].strip()
                                        if key == 'date':
                                            try:
                                                std_date = pd.to_datetime(val, dayfirst=True, errors='coerce')
                                                if not pd.isna(std_date):
                                                    val = std_date.strftime('%Y-%m-%d')
                                            except: pass
                                        project_metadata[key] = val
                                        break
                                if key not in project_metadata:
                                    for cell in row_list:
                                        if found_alias and cell:
                                            val = cell
                                            if key == 'date':
                                                # Standardize Date: DD/MM/YYYY -> YYYY-MM-DD
                                                try:
                                                    # Try common formats, dayfirst=True is critical for DD/MM/YYYY
                                                    std_date = pd.to_datetime(val, dayfirst=True, errors='coerce')
                                                    if not pd.isna(std_date):
                                                        val = std_date.strftime('%Y-%m-%d')
                                                except: pass
                                            project_metadata[key] = val
                                            break
                                        if alias.upper() in cell.upper():
                                            found_alias = True
            
            # 2. Detect Section Headers (e.g. "FENCING QUOTATION")
            # If row has text but very few columns filled, it might be a section
            non_empty_cells = [v for v in row_list if v and v != 'nan']
            if 1 <= len(non_empty_cells) <= 2:
                if any(k in row_text for k in section_keywords):
                    current_category = ' '.join(non_empty_cells).title()
                    # Reset mapping for new section if headers repeat
                    mapping = {} 
                    continue

            # 3. Detect Table Headers (S/N, Description, etc.)
            temp_mapping = {}
            for target, aliases in header_keywords.items():
                for idx, val in enumerate(row_list):
                    clean_val = val.lower()
                    if any(a in clean_val for a in aliases):
                        temp_mapping[target] = idx
                        break
            
            if 'title' in temp_mapping and 'amount' in temp_mapping:
                mapping = temp_mapping
                mapping_header_row_idx = i
                continue

            # 4. Extract Data Rows
            if mapping and i > mapping_header_row_idx:
                title_idx = mapping.get('title')
                amount_idx = mapping.get('amount')
                
                if title_idx is None or amount_idx is None: continue
                
                title_val = row_list[title_idx]
                amount_val = row_list[amount_idx]
                
                if not title_val or title_val.lower() in ['total', 'grand total', 'subtotal', 'nan']:
                    continue
                
                # S/N Check (often the first cell is numeric for data rows)
                first_cell = row_list[0]
                if not first_cell.isdigit() and len(non_empty_cells) < 3:
                    # Might be a spacer or sub-header
                    continue

                # Parse numeric amount
                try:
                    amount = float(str(amount_val).replace('₦', '').replace(',', '').strip())
                except:
                    continue # Skip if no valid amount
                
                if amount <= 0: continue

                # Parse budget if exists
                budget = 0
                if mapping.get('budget') is not None:
                    try:
                        budget_val = row_list[mapping['budget']]
                        budget = float(str(budget_val).replace('₦', '').replace(',', '').strip())
                    except: pass
                
                # Vendor detection
                vendor_name = project_metadata.get('company')
                if mapping.get('vendor') is not None:
                    vendor_name = row_list[mapping['vendor']]

                # Build Metadata
                extra_metadata = {
                    "Import Source": file.filename,
                    "Project Location": project_metadata.get('location', 'Unknown'),
                    "Quotation Date": project_metadata.get('date', 'Unknown')
                }
                
                # Standardize key fields in metadata for frontend badges
                if mapping.get('quantity') is not None:
                    extra_metadata["Quantity"] = row_list[mapping['quantity']]
                if mapping.get('duration') is not None:
                    extra_metadata["Duration"] = row_list[mapping['duration']]
                if mapping.get('unit_price') is not None:
                    extra_metadata["Unit Price"] = row_list[mapping['unit_price']]
                
                # Capture all other columns as generic metadata
                for idx, val in enumerate(row_list):
                    if idx in mapping.values() or not val or val == 'nan': continue
                    try:
                        header_name = str(df.iloc[mapping_header_row_idx, idx]).strip()
                        if not header_name or header_name == 'nan': header_name = f"Field_{idx}"
                        extra_metadata[header_name] = val
                    except:
                        extra_metadata[f"Col_{idx}"] = val

                # Clean paid
                paid = 0
                if mapping.get('paid') is not None:
                    try:
                        paid_val = row_list[mapping['paid']]
                        paid = float(str(paid_val).replace('₦', '').replace(',', '').strip())
                    except: pass

                # Final Date Validation
                final_date = project_metadata.get('date')
                try:
                    # Ensure it's in YYYY-MM-DD
                    valid_date = pd.to_datetime(final_date, dayfirst=True, errors='coerce')
                    if pd.isna(valid_date):
                        final_date = datetime.now().strftime('%Y-%m-%d')
                    else:
                        final_date = valid_date.strftime('%Y-%m-%d')
                except:
                    final_date = datetime.now().strftime('%Y-%m-%d')

                all_records.append({
                    "created_by": current_admin['sub'],
                    "property_id": property_id,
                    "estate_draft_id": estate_draft_id,
                    "title": title_val,
                    "amount": amount,
                    "budget": budget or amount, # Default budget to amount if missing
                    "category": current_category,
                    "metadata": extra_metadata,
                    "amount_paid": paid,
                    "vendor_name": vendor_name,
                    "status": "paid" if paid >= amount - 1 and amount > 0 else ("partial" if paid > 0 else "pending"),
                    "expense_date": final_date
                })

        if not all_records:
            raise HTTPException(status_code=400, detail="No valid records found. Ensure your file has 'Description' and 'Amount' columns.")

        try:
            res = await db_execute(lambda: db.table("procurement_expenses").insert(all_records).execute())
        except Exception as insert_err:
            # Fallback: Try without created_by if it's missing from schema
            if "created_by" in str(insert_err):
                for r in all_records: r.pop("created_by", None)
                res = await db_execute(lambda: db.table("procurement_expenses").insert(all_records).execute())
            else:
                raise insert_err
        
        return {
            "status": "success", 
            "imported": len(res.data) if res.data else 0,
            "metadata": project_metadata
        }
        
    except Exception as e:
        logger.error(f"Procurement Import Error: {e}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@router.delete("/procurement-expenses/wipe")
async def wipe_procurement_ledger(
    property_id: Optional[str] = Query(None),
    estate_draft_id: Optional[str] = Query(None),
    current_admin=Depends(require_roles(["super_admin"]))
):
    db = get_db()
    if not property_id and not estate_draft_id:
        raise HTTPException(status_code=400, detail="Must provide property_id or estate_draft_id")
    
    query = db.table("procurement_expenses").delete()
    if property_id:
        query = query.eq("property_id", property_id)
    else:
        query = query.eq("estate_draft_id", estate_draft_id)
        
    res = await db_execute(lambda: query.execute())
    return {"status": "success", "wiped": len(res.data) if res.data else 0}

# --- ESTATE DRAFTS & PIPELINE ---
from models import EstateDraftCreate

@router.post("/estates")
async def create_estate_draft(data: EstateDraftCreate, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    payload = data.dict()
    payload["created_by"] = current_admin['sub']
    
    res = await db_execute(lambda: db.table("estate_drafts").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create estate draft")
    return res.data[0]

@router.get("/estates")
async def list_estate_drafts(current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("estate_drafts").select("*").order("created_at", desc=True).execute())
    return res.data

@router.patch("/estates/{draft_id}")
async def update_estate_draft(draft_id: str, data: dict, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("estate_drafts").update(data).eq("id", draft_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    return res.data[0]

@router.post("/estates/{draft_id}/publish")
async def publish_estate(draft_id: str, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    
    # 1. Fetch Draft
    res = await db_execute(lambda: db.table("estate_drafts").select("*").eq("id", draft_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = res.data[0]
    if draft.get("is_public"):
        raise HTTPException(status_code=400, detail="Estate is already public")
        
    # 2. Create Properties for each variation
    variations = draft.get("variations", [])
    created_prop_ids = []
    
    for var in variations:
        outright = float(var.get('outright_price', 0))
        installment = float(var.get('installment_price', 0))
        size = var['size_sqm']
        
        # 1. Create Outright Listing
        outright_payload = {
            "name": draft['name'],
            "estate_name": draft['name'],
            "location": draft['location'],
            "description": "Outright Payment Plan",
            "plot_size_sqm": size,
            "plot_size_sqm": size,
            "total_price": outright,
            "total_plots": var['total_plots'],
            "acquisition_cost": var.get('acquisition_cost', 0),
            "budget": float(draft.get('total_budget', 0)) if not created_prop_ids else 0, # Put budget on the first variation only to avoid double counting
            "is_active": True
        }
        o_res = await db_execute(lambda: db.table("properties").insert(outright_payload).execute())
        if o_res.data:
            created_prop_ids.append(o_res.data[0]['id'])
            
        # 2. Create Installment Listing (Optional)
        if installment > 0:
            inst_payload = {
                "name": draft['name'],
                "estate_name": draft['name'],
                "location": draft['location'],
                "description": "Installment Payment Plan",
                "plot_size_sqm": size,
                "total_price": installment,
                "total_plots": var['total_plots'],
                "acquisition_cost": 0,
                "is_active": True
            }
            i_res = await db_execute(lambda: db.table("properties").insert(inst_payload).execute())
            if i_res.data:
                created_prop_ids.append(i_res.data[0]['id'])
            
    # 3. Update Draft Status
    await db_execute(lambda: db.table("estate_drafts").update({"is_public": True}).eq("id", draft_id).execute())
    
    # 4. Link existing expenses to the first property ID created
    if created_prop_ids:
        await db_execute(lambda: db.table("procurement_expenses").update({"property_id": created_prop_ids[0]}).eq("estate_draft_id", draft_id).execute())

    return {"status": "success", "properties_created": len(created_prop_ids)}

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, File, UploadFile, Form, Body, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from database import get_db, db_execute
from models import ExpenditureRequestCreate, PayoutReview, AssetCreate, VendorCreate, VoidExpenditureRequest, PayoutPaymentData
from routers.auth import verify_token, has_any_role, require_roles, resolve_admin_token
from email_service import send_payout_receipt_email, send_portal_invite_email, send_report_email, send_receipt_email
from commission_service import sync_invoice_commissions
from report_service import ReportService
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json
import uuid
import pandas as pd
import io
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

@router.get("/procurement-dashboard", response_class=HTMLResponse)
async def procurement_dashboard(
    request: Request, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["super_admin"]))
):
    """
    Estate Development & Procurement Dashboard.
    Only accessible by Super Admins.
    """
    analytics = await ReportService.get_procurement_analytics(start_date, end_date)
    return templates.TemplateResponse("procurement_dashboard.html", {
        "request": request,
        "admin": current_admin,
        "analytics": analytics
    })



# ─── WHT 2025 HELPER ──────────────────────────────────────────
def calculate_wht_2025(amount: Decimal, category: str, has_tin: bool = True, is_resident: bool = True) -> dict:
    """
    Implements Nigerian WHT Regulations 2024 (Effective Jan 2025).
    Category: 'professional', 'goods', 'construction', 'rent', 'commission'
    """
    # 1. Base Rates (Resident)
    base_rates = {
        'professional': Decimal('0.05'),
        'goods': Decimal('0.02'),
        'construction': Decimal('0.02'),
        'rent': Decimal('0.10'),
        'commission': Decimal('0.05'),
        'other': Decimal('0.02')
    }
    
    # 2. Base Rates (Non-Resident)
    non_resident_rates = {
        'professional': Decimal('0.10'),
        'goods': Decimal('0.05'),
        'construction': Decimal('0.05'),
        'rent': Decimal('0.10'),
        'commission': Decimal('0.10'),
        'other': Decimal('0.05')
    }
    
    rate = base_rates.get(category, Decimal('0.02')) if is_resident else non_resident_rates.get(category, Decimal('0.05'))
    
    # 3. Penalty for No TIN (Double the rate)
    if not has_tin:
        rate = rate * 2
        
    wht_amount = amount * rate
    return {
        "rate": rate,
        "wht_amount": wht_amount,
        "net_amount": amount - wht_amount
    }

class PayoutPaymentData(BaseModel):
    amount: float
    payment_method: str = "transfer"
    reference: Optional[str] = None

class VerifyRequest(BaseModel):
    action: str
    reason: Optional[str] = None
    due_date: Optional[str] = None

@router.post("/vendors")
async def create_vendor(data: VendorCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("vendors").insert(data.dict()).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create vendor")
    return res.data[0]

@router.patch("/vendors/{vendor_id}/commission-config")
async def update_vendor_commission_config(vendor_id: str, payload: dict, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    update_data = {}
    if "is_commission_partner" in payload: update_data["is_commission_partner"] = bool(payload["is_commission_partner"])
    if "gross_commission_rate" in payload: update_data["gross_commission_rate"] = float(payload["gross_commission_rate"])
    if "wht_rate" in payload: update_data["wht_rate"] = float(payload["wht_rate"])
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No configuration provided")
        
    res = await db_execute(lambda: db.table("vendors").update(update_data).eq("id", vendor_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    return res.data[0]

@router.get("/vendors")
async def list_vendors(type: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("vendors").select("*")
    if type:
        query = query.eq("type", type)
    res = await db_execute(lambda: query.order("name").execute())
    return res.data

# ─── EXPENDITURE REQUESTS ─────────────────────────────────────
@router.post("/requests")
async def submit_payout_request(data: ExpenditureRequestCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    vendor_id = data.vendor_id
    # Inline vendor creation (e.g. for one-off staff claims)
    if not vendor_id and data.vendor_data:
        vendor_res = await db_execute(lambda: db.table("vendors").insert(data.vendor_data.dict()).execute())
        if vendor_res.data:
            vendor_id = vendor_res.data[0]['id']
            
    # Calculate WHT Suggestion
    # Note: For staff reimbursements, WHT is typically NOT applicable by default
    wht_details = {"rate": 0, "wht_amount": 0, "net_amount": data.amount_gross}
    
    if data.is_wht_applicable:
        vendor_res = await db_execute(lambda: db.table("vendors").select("tin, type").eq("id", vendor_id).execute())
        vendor = vendor_res.data[0]
        has_tin = bool(vendor.get('tin'))
        # Default to 'professional' for services, 'goods' if mentioned
        cat = 'goods' if 'get' in data.title.lower() or 'buy' in data.title.lower() else 'professional'
        wht_details = calculate_wht_2025(data.amount_gross, cat, has_tin=has_tin)

    payload = {
        "title": data.title,
        "description": data.description,
        "vendor_invoice_number": data.vendor_invoice_number,
        "requester_id": current_admin['sub'],
        "vendor_id": vendor_id,
        "amount_gross": float(data.amount_gross),
        "payout_method": data.payout_method,
        "is_wht_applicable": data.is_wht_applicable,
        "wht_rate": float(wht_details['rate']),
        "wht_amount": float(wht_details['wht_amount']),
        "wht_exemption_reason": data.wht_exemption_reason,
        "net_payout_amount": float(wht_details['net_amount']),
        "proforma_url": data.proforma_url,
        "receipt_url": data.receipt_url,
        "category": data.category or "General",
        "property_id": data.property_id,
        "development_category": data.development_category,
        "status": "pending_verification"
    }
    
    res = await db_execute(lambda: db.table("expenditure_requests").insert(payload).execute())
    return res.data[0]

@router.get("/requests")
async def list_expenditure_requests(status: Optional[str] = None, show_voided: bool = False, vendor_type: Optional[str] = None, payout_method: Optional[str] = None, payment_type: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("expenditure_requests").select("*, vendors(*), admins!requester_id(full_name), expenditure_payments(*), company_assets(*)")
    
    if status:
        query = query.eq("status", status)
    
    if not show_voided:
        query = query.neq("status", "voided")

    if payout_method:
        query = query.eq("payout_method", payout_method)

    if payment_type:
        query = query.eq("payment_type", payment_type)
        
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    data = res.data

    # Filter by vendor type in Python (vendors is a joined object, not a direct column)
    if vendor_type:
        data = [r for r in data if (r.get("vendors") or {}).get("type") == vendor_type]

    return data

@router.post("/requests/{request_id}/payments")
async def record_payout_payment(request_id: str, data: PayoutPaymentData, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    # 1. Verify Request
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    
    amount_to_pay = float(data.amount)
    current_paid = float(req.get('amount_paid', 0))
    net_payout = float(req.get('net_payout_amount', 0))
    
    # Ensure amount doesn't wildly exceed balance
    if current_paid + amount_to_pay > net_payout + 0.05: # Float fuzziness
        raise HTTPException(status_code=400, detail="Payment amount exceeds remaining balance.")
        
    # 2. Insert Payment Record
    payment_payload = {
        "request_id": request_id,
        "amount": amount_to_pay,
        "payment_method": data.payment_method,
        "reference": data.reference,
        "paid_by": current_admin['sub']
    }
    await db_execute(lambda: db.table("expenditure_payments").insert(payment_payload).execute())
    
    # 3. Update Request
    new_paid = current_paid + amount_to_pay
    new_status = "paid" if new_paid >= net_payout - 0.05 else "partially_paid"
    
    update_payload = {
        "amount_paid": new_paid,
        "status": new_status,
        "payout_reference": data.reference,
    }
    
    if new_status == "paid":
        update_payload["paid_at"] = datetime.now(timezone.utc).isoformat()
        
    update_res = await db_execute(lambda: db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute())
    
    # Trigger automated receipt
    if update_res.data:
        req_with_vendor = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
        if req_with_vendor.data:
            full_req = req_with_vendor.data[0]
            vendor = full_req.get('vendors')
            if vendor and vendor.get('email'):
                bg_tasks.add_task(send_payout_receipt_email, full_req, vendor, current_admin['sub'], payment_amount=amount_to_pay)

    return {"status": "success", "new_status": new_status, "amount_paid": new_paid}

@router.patch("/requests/{request_id}/verify")
async def verify_bill_request(
    request_id: str,
    data: VerifyRequest,
    bg_tasks: BackgroundTasks,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """
    Bill Verification: promotion to 'pending' (audit queue) triggers revenue sync for portal claims.
    """
    if not has_any_role(current_admin, ["admin", "operations"]):
        raise HTTPException(status_code=403, detail="Only authorized roles can perform this action")
    
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    req = req_res.data[0]
    action = data.action  # 'pending' or 'rejected'
    
    if action == 'pending':
        # --- UNIFIED VERIFICATION WORKFLOW ---
        if req.get("invoice_id"):
            inv_id = req["invoice_id"]
            
            # 1. Resolve or Create the Client Payment record
            payment_id = req.get("payment_id")
            client_payment_amount = 0
            
            # Scenario A: Claiming on a new payment reported via portal
            if not payment_id and req.get("pending_verification_id"):
                p_verif_id = req["pending_verification_id"]
                # Confirm the verification record (mirrors verifications.py logic)
                verif_res = await db_execute(lambda: db.table("pending_verifications").select("*").eq("id", p_verif_id).execute())
                if verif_res.data:
                    verif = verif_res.data[0]
                    client_payment_amount = float(verif.get("deposit_amount", 0))
                    
                    # Create the payments record
                    pay_res = await db_execute(lambda: db.table("payments").insert({
                        "invoice_id": inv_id,
                        "client_id": verif["client_id"],
                        "amount": client_payment_amount,
                        "payment_method": "portal_reported",
                        "reference": f"CONF-{p_verif_id[:8]}",
                        "payment_date": verif.get("payment_date") or datetime.now(timezone.utc).isoformat(),
                        "recorded_by": current_admin['sub']
                    }).execute())
                    
                    if pay_res.data:
                        payment_id = pay_res.data[0]["id"]
                        # Mark verification as confirmed
                        await db_execute(lambda: db.table("pending_verifications").update({
                            "status": "confirmed",
                            "reviewed_by": current_admin['sub'],
                            "reviewed_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", p_verif_id).execute())
            
            # Scenario B: Claiming on an already confirmed payment
            elif payment_id:
                p_res = await db_execute(lambda: db.table("payments").select("amount").eq("id", payment_id).execute())
                if p_res.data:
                    client_payment_amount = float(p_res.data[0]["amount"])
            
            # Scenario C: Fallback (Legacy parsing)
            else:
                desc = req.get("description", "")
                if "Payment ID: " in desc:
                    legacy_pid = desc.split("Payment ID: ")[-1].split("\n")[0].strip()
                    if legacy_pid and len(legacy_pid) > 30: # Check if it looks like a UUID
                        payment_id = legacy_pid
                        p_res = await db_execute(lambda: db.table("payments").select("amount").eq("id", payment_id).execute())
                        if p_res.data:
                            client_payment_amount = float(p_res.data[0]["amount"])

            # 2. Update Invoice and Ledger if we have a valid payment
            if payment_id:
                # Sync Invoice Balance (if it wasn't already synced by payment trigger)
                from commission_service import sync_invoice_commissions
                bg_tasks.add_task(sync_invoice_commissions, inv_id, db, current_admin['sub'])
                
                # 3. Create structural Commission Ledger entry
                if vendor.get("id"):
                    # Check if already exists to prevent duplicates
                    existing_ce = await db_execute(lambda: db.table("commission_earnings")
                        .select("id")
                        .eq("payment_id", payment_id)
                        .or_(f"vendor_id.eq.{vendor['id']},sales_rep_id.not.is.null") # Basic check
                        .execute())
                    
                    if not existing_ce.data:
                        # Look for sales rep first if email exists
                        sales_rep_id = None
                        if payee_email:
                            rep_res = await db_execute(lambda: db.table("sales_reps").select("id").eq("email", payee_email).execute())
                            sales_rep_id = rep_res.data[0]["id"] if (rep_res.data and len(rep_res.data) > 0) else None
                        
                        # Create the earnings record
                        earning_payload = {
                            "invoice_id": inv_id,
                            "payment_id": payment_id,
                            "client_id": req["client_id"] if req.get("client_id") else None, 
                            "estate_name": req.get("title", "").split(": ")[-1], # Fallback
                            "payment_amount": client_payment_amount,
                            "commission_rate": float(req.get("wht_rate") or 5.0) * 2, # Rough estimate
                            "commission_amount": float(req["net_payout_amount"]),
                            "gross_commission": float(req["amount_gross"]),
                            "wht_amount": float(req.get("wht_amount") or 0),
                            "net_commission": float(req["net_payout_amount"]),
                            "is_paid": False,
                        }
                        
                        if sales_rep_id:
                            earning_payload["sales_rep_id"] = sales_rep_id
                        else:
                            earning_payload["vendor_id"] = vendor.get("id")
                        
                        # Try to fetch missing client_id/estate from invoice
                        inv_meta = await db_execute(lambda: db.table("invoices").select("client_id, property_name").eq("id", inv_id).execute())
                        if inv_meta.data:
                            earning_payload["client_id"] = inv_meta.data[0]["client_id"]
                            earning_payload["estate_name"] = inv_meta.data[0]["property_name"]

                        # INSERT
                        await db_execute(lambda: db.table("commission_earnings").insert(earning_payload).execute())

    # Update Expenditure Status
    update_payload = {
        "status": action,
        "reviewed_by": current_admin['sub'],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if action == 'rejected':
        update_payload["rejection_reason"] = data.reason or "Bill rejected at verification stage"
    elif action == 'pending' and data.due_date:
        update_payload["due_date"] = data.due_date
    
    await db_execute(lambda: db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute())
    return {"status": "success", "new_status": action}

@router.put("/requests/{request_id}/review")
async def review_payout_request(request_id: str, data: PayoutReview, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    if not has_any_role(current_admin, "admin"):
        raise HTTPException(status_code=403, detail="Only Admins can approve payouts")
        
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    update_payload = {
        "status": data.status,
        "reviewed_by": current_admin['sub'],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "payout_reference": data.payout_reference,
        "rejection_reason": data.rejection_reason if data.status == 'rejected' else req.get('rejection_reason'),
        "wht_exemption_reason": req.get('wht_exemption_reason')
    }
    
    # Handle WHT Override (as requested by user)
    if not data.apply_wht and data.status == 'approved':
        update_payload["is_wht_applicable"] = False
        update_payload["wht_rate"] = 0
        update_payload["wht_amount"] = 0
        update_payload["net_payout_amount"] = req['amount_gross']
    elif data.manual_wht_rate is not None and data.status == 'approved':
        rate = data.manual_wht_rate
        amt = Decimal(str(req['amount_gross'])) * rate
        update_payload["wht_rate"] = float(rate)
        update_payload["wht_amount"] = float(amt)
        update_payload["net_payout_amount"] = float(Decimal(str(req['amount_gross'])) - amt)

    if data.status == 'approved':
        update_payload['paid_at'] = datetime.now(timezone.utc).isoformat()

    res = await db_execute(lambda: db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute())
    updated_req = res.data[0]

    # ─── ASSET AUTOMATION ────────────────────────────────────
    # If this was a procurement/tool request, auto-log it as a company asset
    if data.status == 'approved' and req.get('payout_method') == 'procurement':
        try:
            # Generate a simple unique Asset ID
            asset_slug = "".join([w[0] for w in req['title'].split() if w]).upper()[:4]
            asset_id_code = f"EC-{asset_slug}-{str(uuid.uuid4())[:4].upper()}"
            
            asset_payload = {
                "asset_id": asset_id_code,
                "name": req['title'],
                "category": "Equipment", # Default, can be refined in Asset view
                "purchase_cost": float(req['amount_gross']),
                "purchase_date": datetime.now(timezone.utc).date().isoformat(),
                "procurement_id": request_id,
                "assigned_to": req.get('requester_id'),
                "current_status": "assigned",
                "notes": f"Auto-logged via Procurement Approval. Ref: {request_id}"
            }
            
            await db_execute(lambda: db.table("company_assets").insert(asset_payload).execute())
        except Exception as asset_err:
            print(f"⚠️ Warning: Payout approved but Asset logging failed: {asset_err}")
            # We don't fail the whole payout if asset logging hits a snag, but we log it.

    # ─── TRIGGER APPROVAL NOTIFICATION EMAIL ──────────────────────
    # On approve: send an approval notification (not a payment receipt — no money has moved yet).
    # The payment receipt is sent separately when /payments is called.
    if data.status == 'approved' and updated_req.get('vendor_id'):
        # Re-fetch with vendor join AFTER the update so net_payout_amount / wht_amount
        # reflect the post-approval values (WHT overrides applied above).
        receipt_res = await db_execute(
            lambda: db.table('expenditure_requests').select('*, vendors(*)').eq('id', request_id).execute()
        )
        if receipt_res.data:
            full_req = receipt_res.data[0]
            vendor = full_req.get('vendors')
            if vendor and vendor.get('email'):
                from email_service import send_expense_approval_email
                bg_tasks.add_task(send_expense_approval_email, full_req, vendor, current_admin['sub'])

    return updated_req

class WhtRemittanceData(BaseModel):
    receipt_reference: str
    request_ids: List[str]

@router.post("/requests/remit-wht")
async def record_wht_remittance(data: WhtRemittanceData, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Batch clears WHT liabilities by marking them remitted to FIRS."""
    db = get_db()
    if not data.request_ids:
        raise HTTPException(status_code=400, detail="No requests selected for remittance")
        
    update_payload = {
        "is_wht_remitted": True,
        "wht_remittance_ref": data.receipt_reference,
        "wht_remitted_at": datetime.now(timezone.utc).isoformat(),
        "wht_remitted_by": current_admin['sub']
    }
    
    res = await db_execute(lambda: db.table("expenditure_requests").update(update_payload).in_("id", data.request_ids).execute())
    return {"status": "success", "cleared_count": len(res.data) if res.data else 0}

@router.post("/requests/{request_id}/send-receipt")
async def trigger_manual_receipt(request_id: str, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Manually triggers a remittance advice email to the vendor."""
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    vendor = req.get('vendors')
    if not vendor or not vendor.get('email'):
        raise HTTPException(status_code=400, detail="Vendor has no email address on file")
        
    bg_tasks.add_task(send_payout_receipt_email, req, vendor, current_admin['sub'])
    return {"status": "success", "message": f"Receipt queued for {vendor['email']}"}

# ─── ASSETS ───────────────────────────────────────────────────
@router.post("/assets")
async def record_company_asset(data: AssetCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    # 1. Insert the asset
    asset_data = data.dict(exclude={"auto_expense"})
    res = await db_execute(lambda: db.table("company_assets").insert(asset_data).execute())
    new_asset = res.data[0]
    
    # 2. Automated Expense Flow (Option 2)
    if data.auto_expense and data.purchase_cost and data.purchase_cost > 0:
        expense_payload = {
            "title": f"Asset Purchase: {data.name}",
            "description": f"Automated expense log for {data.category} (SN: {data.serial_number or 'N/A'})",
            "amount_gross": float(data.purchase_cost),
            "amount_paid": float(data.purchase_cost),
            "net_payout_amount": float(data.purchase_cost),
            "status": "paid",
            "payout_method": "direct_pay",
            "requester_id": current_admin['sub'],
            "category": "Capital Expenditure",
            "is_wht_applicable": False,
            "created_at": data.purchase_date.isoformat() if data.purchase_date else datetime.now().isoformat()
        }
        await db_execute(lambda: db.table("expenditure_requests").insert(expense_payload).execute())
        
    return new_asset

@router.get("/assets")
async def list_assets(assigned_to: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("company_assets").select("*, admins!assigned_to(full_name)")
    if assigned_to:
        query = query.eq("assigned_to", assigned_to)
    res = await db_execute(lambda: query.execute())
    return res.data


# ─── SECURE STORAGE ACCESS ────────────────────────────────────
from storage_service import generate_signed_url, upload_portal_file
from fastapi.responses import RedirectResponse

@router.get("/requests/{request_id}/view-document/{doc_type}")
async def view_secure_payout_document(
    request_id: str,
    doc_type: str,
    file_index: int = 0,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    """
    Securely redirects to a signed URL for proformas or receipts.
    doc_type: 'proforma', 'receipt'
    file_index: for multi-file receipts (JSON array stored in receipt_url), selects which file to view.
    """
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("*").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = req_res.data[0]
    raw_path = req.get('proforma_url') if doc_type == 'proforma' else req.get('receipt_url')

    if not raw_path:
        raise HTTPException(
            status_code=404,
            detail=f"No {doc_type} document attached to this record."
        )

    # Resolve path — may be a single string or a JSON array (multi-file upload)
    path = raw_path
    if raw_path.startswith('['):
        try:
            paths = json.loads(raw_path)
            if not isinstance(paths, list) or len(paths) == 0:
                raise ValueError
            # Clamp index to valid range
            idx = max(0, min(file_index, len(paths) - 1))
            path = paths[idx]
        except (ValueError, json.JSONDecodeError):
            pass  # Fall through — treat raw_path as a plain string

    # Redirect to external URLs directly
    if path.startswith("http"):
        return RedirectResponse(url=path)

    # Generate signed URL for private Supabase bucket 'Cloud Infrastructure'
    signed_url = generate_signed_url("Cloud Infrastructure", path)
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate secure access link")

    return RedirectResponse(url=signed_url)


@router.get("/requests/{request_id}/proof-files")
async def list_proof_files(request_id: str, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """
    Returns the list of proof file paths for a request.
    For single-file records returns a 1-element array.
    For multi-file records (receipt_url is a JSON array) returns all entries.
    """
    db = get_db()
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("receipt_url, proforma_url, title").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = req_res.data[0]
    receipt_raw = req.get('receipt_url') or ''
    proforma_raw = req.get('proforma_url') or ''

    def parse_paths(raw: str) -> list:
        if not raw:
            return []
        if raw.startswith('['):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, list) else [raw]
            except (ValueError, json.JSONDecodeError):
                pass
        return [raw]

    return {
        "id": request_id,
        "title": req.get('title', ''),
        "receipt_files": parse_paths(receipt_raw),
        "proforma_files": parse_paths(proforma_raw),
        "total": len(parse_paths(receipt_raw)) + len(parse_paths(proforma_raw)),
    }


# ─── PORTAL AUTOMATION ────────────────────────────────────────

class PortalInvite(BaseModel):
    email: str
    category: str # 'staff', 'company', or 'individual'

@router.post("/requests/portal-invite")
async def trigger_portal_invite(data: PortalInvite, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Triggers a professional system email invitation with a unique token."""
    db = get_db()
    
    # 1. Fetch current admin for the invitation signature
    admin_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", current_admin['sub']).execute())
    admin_name = admin_res.data[0]['full_name'] if admin_res.data else "Eximp & Cloves Finance"
    
    # 2. Generate or Update Invite Token
    token = str(uuid.uuid4())
    invite_payload = {
        "email": data.email,
        "category": data.category,
        "token": token,
        "invited_by": current_admin['sub'],
        "is_used": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert the invite (so re-inviting updates the token/category)
    await db_execute(lambda: db.table("portal_invites").upsert(invite_payload, on_conflict="email").execute())
    
    # 3. Generate Link
    # Note: In production, window.location.origin would be used on frontend, 
    # here we assume the portal is at /payout/portal/{token}
    
    bg_tasks.add_task(send_portal_invite_email, data.email, admin_name, token)
    
    return {
        "status": "success", 
        "message": f"Invitation queued for {data.email}",
        "token": token
    }

@router.get("/payout/portal/invite/{token}")
async def resolve_portal_invite(token: str):
    """Checks the validity of an invitation token and returns the context."""
    db = get_db()
    
    # 1. Validate Token
    invite_res = await db_execute(lambda: db.table("portal_invites").select("*").eq("token", token).execute())
    if not invite_res.data:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation link")
    
    invite = invite_res.data[0]
    
    # 2. Check if Payee is already onboarded
    payee_res = await db_execute(lambda: db.table("vendors").select("*").eq("email", invite['email']).execute())
    is_onboarded = len(payee_res.data) > 0
    payee_data = payee_res.data[0] if is_onboarded else None
    
    return {
        "email": invite['email'],
        "category": invite['category'],
        "is_onboarded": is_onboarded,
        "payee_data": payee_data
    }

@router.get("/portal/lookup-invoice")
async def portal_lookup_invoice(invoice_number: str, claimant_email: Optional[str] = None):
    """
    Rich invoice lookup for commission claims.
    Returns payment type (initial_deposit vs instalment), rep conflict status,
    payment history, and commission preview.
    """
    db = get_db()

    # 1. Fetch invoice with client data
    res = await db_execute(lambda: db.table("invoices")
        .select("id, client_id, amount, amount_paid, property_name, sales_rep_id, sales_rep_name, clients(full_name)")
        .eq("invoice_number", invoice_number)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Invoice not found. Please check the number and try again.")

    inv = res.data[0]
    invoice_id = inv["id"]

    # 2. Fetch ALL actual confirmed client payments for this invoice (oldest first).
    #    This is the ground truth — we use real payments, not portal claims, to decide
    #    what has and hasn't been claimed yet.
    payments_res = await db_execute(lambda: db.table("payments")
        .select("id, amount, created_at, payment_method")
        .eq("invoice_id", invoice_id)
        .order("created_at")
        .execute()
    )
    all_payments = payments_res.data or []
    payment_count = len(all_payments)

    property_price     = float(inv.get("amount") or 0)
    amount_paid_so_far = float(inv.get("amount_paid") or 0)
    balance            = max(0.0, property_price - amount_paid_so_far)

    # 3. Find which payments have already been claimed.
    #    Source A: commission_earnings ledger (dashboard-verified commissions).
    #    Source B: expenditure_requests portal claims (self-reported, pending approval).
    commission_earnings_res = await db_execute(lambda: db.table("commission_earnings")
        .select("payment_id")
        .eq("invoice_id", invoice_id)
        .execute()
    )
    ledger_claimed_payment_ids = {
        e["payment_id"] for e in (commission_earnings_res.data or []) if e.get("payment_id")
    }

    portal_claims_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("id, payment_type, status")
        .eq("vendor_invoice_number", invoice_number)
        .neq("status", "rejected")
        .execute()
    )
    portal_claims = portal_claims_res.data or []
    # Count how many initial_deposit and instalment claims already exist in the portal
    portal_initial_count    = len([c for c in portal_claims if c.get("payment_type") == "initial_deposit"])
    portal_instalment_count = len([c for c in portal_claims if c.get("payment_type") == "instalment"])

    # 4. Build the unclaimed payments list.
    #    payment index 0 = initial deposit, 1+ = instalments.
    unclaimed_payments = []
    instalment_portal_used = 0
    for i, p in enumerate(all_payments):
        ptype = "initial_deposit" if i == 0 else "instalment"

        # Check ledger first (most authoritative)
        if p["id"] in ledger_claimed_payment_ids:
            continue

        # Check portal claims by type+sequence
        if ptype == "initial_deposit" and portal_initial_count > 0:
            continue
        if ptype == "instalment":
            if instalment_portal_used < portal_instalment_count:
                instalment_portal_used += 1
                continue

        comm_base = property_price if ptype == "initial_deposit" else float(p.get("amount") or 0)
        unclaimed_payments.append({
            "seq":            i + 1,
            "payment_id":     p["id"],
            "amount":         float(p.get("amount") or 0),
            "date":           (p.get("created_at") or "")[:10],
            "method":         p.get("payment_method") or "—",
            "payment_type":   ptype,
            "commission_base": comm_base,
        })

    # 5. Determine what to present to the claimant.
    #    - If unclaimed payments exist, point them at the OLDEST unclaimed one first.
    #    - payment_sequence reflects the NEXT UNCLAIMED payment position, not total count.
    if unclaimed_payments:
        next_unclaimed   = unclaimed_payments[0]
        payment_type     = next_unclaimed["payment_type"]
        commission_base  = next_unclaimed["commission_base"]
        payment_sequence = next_unclaimed["seq"]  # actual position in payment history
    else:
        # All confirmed payments are already claimed
        payment_type     = "instalment"
        commission_base  = None
        payment_sequence = payment_count + 1

    # ── Resolve display commission rate for the preview card ──
    # Read global defaults from system_settings so the preview matches what submit will calculate.
    _prev_sys_res = await db_execute(lambda: db.table("system_settings")
        .select("key, value")
        .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
        .execute()
    )
    _prev_sys = {s["key"]: s["value"] for s in (_prev_sys_res.data or [])}

    # Check vendor-specific rate first
    _prev_vrate_res = await db_execute(lambda: db.table("vendors")
        .select("gross_commission_rate, wht_rate, is_commission_partner")
        .eq("email", claimant_email)
        .execute()
    )
    _prev_vdata = ((_prev_vrate_res.data or [None])[0]) or {}
    _is_partner = bool(_prev_vdata.get("is_commission_partner"))

    def _pct(val, fallback):
        try:
            v = float(val)
            return v / 100 if v > 1 else v
        except Exception:
            return fallback

    if _prev_vdata.get("gross_commission_rate"):
        _display_gross_rate = _pct(_prev_vdata["gross_commission_rate"], 0.15 if _is_partner else 0.10)
        _display_wht_rate   = _pct(_prev_vdata.get("wht_rate") or 5, 0.05)
    elif _is_partner and _prev_sys.get("default_partner_commission_rate"):
        _display_gross_rate = _pct(_prev_sys["default_partner_commission_rate"], 0.15)
        _display_wht_rate   = _pct(_prev_sys.get("default_wht_rate") or 5, 0.05)
    elif not _is_partner and _prev_sys.get("default_commission_rate"):
        _display_gross_rate = _pct(_prev_sys["default_commission_rate"], 0.10)
        _display_wht_rate   = _pct(_prev_sys.get("default_wht_rate") or 5, 0.05)
    else:
        _display_gross_rate = 0.15 if _is_partner else 0.10
        _display_wht_rate   = 0.05

    commission_rate    = round(_display_gross_rate, 4)
    commission_wht     = round(_display_wht_rate, 4)
    commission_preview = round(commission_base * commission_rate, 2) if (payment_type == "initial_deposit" and commission_base) else None

    # 3. Sales rep conflict detection
    rep_status = "unassigned"
    assigned_rep_name = None
    assigned_rep_email = None

    if inv.get("sales_rep_id"):
        rep_res = await db_execute(lambda: db.table("sales_reps")
            .select("id, name, email")
            .eq("id", inv["sales_rep_id"])
            .execute()
        )
        if rep_res.data:
            rep = rep_res.data[0]
            assigned_rep_name = rep.get("name") or inv.get("sales_rep_name") or "Unknown Rep"
            assigned_rep_email = (rep.get("email") or "").lower()

            if claimant_email:
                rep_status = "yours" if claimant_email.lower() == assigned_rep_email else "conflict"
            else:
                rep_status = "conflict"
    elif inv.get("sales_rep_name"):
        # Name recorded but no ID link yet
        assigned_rep_name = inv.get("sales_rep_name")
        # If claimant name can be verified against vendor table
        if claimant_email:
            vendor_check = await db_execute(lambda: db.table("vendors")
                .select("name")
                .eq("email", claimant_email)
                .execute()
            )
            if vendor_check.data:
                vendor_name = vendor_check.data[0].get("name", "").lower()
                rep_status = "yours" if assigned_rep_name.lower() in vendor_name or vendor_name in assigned_rep_name.lower() else "conflict"
            else:
                rep_status = "conflict"
        else:
            rep_status = "conflict"

    client_name = inv["clients"]["full_name"] if inv.get("clients") else "Unknown Client"

    return {
        "status": "success",
        "invoice_id": invoice_id,
        "client_name": client_name,
        "property_name": inv.get("property_name") or "—",
        "property_price": property_price,
        "amount_paid": amount_paid_so_far,
        "balance": balance,
        # ── Payment type intelligence ──
        "payment_type": payment_type,            # "initial_deposit" | "instalment"
        "payment_sequence": payment_sequence,    # total payments + 1
        "payment_count": payment_count,          # how many confirmed client payments exist
        # ── Commission preview ──
        "commission_rate": commission_rate,       # gross rate as decimal e.g. 0.15
        "commission_wht":  commission_wht,        # WHT rate as decimal e.g. 0.05
        "commission_net_rate": round(commission_rate * (1 - commission_wht), 6),
        "commission_rate_pct": f"{round(commission_rate * 100, 2):.4g}%",  # display e.g. "15%"
        "commission_base": commission_base,       # None → use reported claim_amount
        "commission_preview": commission_preview, # pre-calc for deposit; null for instalment
        # ── Rep assignment ──
        "rep_status": rep_status,                # "unassigned" | "yours" | "conflict"
        "assigned_rep_name": assigned_rep_name,
        # ── Unclaimed payments ──
        # Full list of confirmed client payments that have no commission claim yet.
        # Frontend uses this to warn the claimant about missed commissions.
        "unclaimed_payments": unclaimed_payments,
        "unclaimed_count": len(unclaimed_payments),
        # Portal claims that are pending verification/approval (not yet paid, not rejected)
        # Frontend shows these so the claimant knows what's already in the queue.
        "pending_portal_claims": [
            {
                "payment_type": c.get("payment_type"),
                "status": c.get("status"),
            }
            for c in portal_claims
            if c.get("status") not in ("rejected", "paid")
        ],
        # ── Full payment history with per-payment commission status ──
        "previous_payments": _build_previous_payments(all_payments, ledger_claimed_payment_ids, unclaimed_payments, inv),
    }


def _build_previous_payments(all_payments, ledger_claimed_ids, unclaimed_payments, inv):
    """Build per-payment history list with commission_status for the portal table."""
    _unclaimed_ids = {u["payment_id"] for u in unclaimed_payments}
    result = []
    for i, p in enumerate(all_payments):
        result.append({
            "seq": i + 1,
            "payment_id": p["id"],
            "amount": float(p.get("amount") or 0),
            "date": (p.get("created_at") or "")[:10],
            "method": p.get("payment_method") or "—",
            "payment_type": "initial_deposit" if i == 0 else "instalment",
            "commission_status": (
                "claimed"   if p["id"] in ledger_claimed_ids else
                "unclaimed" if p["id"] in _unclaimed_ids else
                "pending"
            ),
            "commission_base": (
                float(inv.get("amount") or 0) if i == 0
                else float(p.get("amount") or 0)
            ),
        })
    return result

@router.get("/portal/fetch-vendor")
async def portal_fetch_vendor(email: str):
    """Fetches existing vendor details to auto-fill the portal for returning users."""
    db = get_db()
    res = await db_execute(lambda: db.table("vendors").select("*").eq("email", email).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Vendor not found")
    # Return non-sensitive contact and bank details for auto-fill
    v = res.data[0]
    return {
        "status": "success", 
        "data": {
            "name": v.get("name"),
            "phone": v.get("phone"),
            "rc_number": v.get("rc_number"),
            "tin": v.get("tin"),
            "bank_name": v.get("bank_name"),
            "account_number": v.get("account_number"),
            "account_name": v.get("account_name")
        }
    }


@router.post("/portal/submit")
async def submit_payout_claim_from_portal(
    type: str = Form(...), # office, staff_commission, partner
    payee_name: str = Form(...),
    payee_email: str = Form(...),
    payee_phone: str = Form(""),
    payee_id: str = Form(""),
    payee_tin: str = Form(""),
    claim_amount: float = Form(...),
    remarks: str = Form(""),
    invoice_number: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    acc_number: Optional[str] = Form(None),
    acc_name: Optional[str] = Form(None),
    is_already_paid: bool = Form(False),
    payout_reference: Optional[str] = Form(None),
    # ── NEW: payment type & dispute fields ──
    payment_type: Optional[str] = Form(None),        # "initial_deposit" | "instalment"
    property_price: Optional[float] = Form(None),    # full property value (for deposit commission)
    is_dispute: bool = Form(False),                  # True when another rep is already assigned
    dispute_reason: Optional[str] = Form(None),      # required when is_dispute=True
    # ── Portal payment verification field ──
    # Only sent when the invoice has no existing unpaid commission claim.
    # Represents the actual amount the client paid (not the commission).
    client_paid_amount: Optional[float] = Form(None),
    files: List[UploadFile] = File(default=[])  # Accepts one or many proof uploads
):
    """
    Unified endpoint for the 'Claims & Payouts' portal.
    Handles Office Expenditures, Staff Commissions, and Partner Commissions.
    Now supports initial deposit vs instalment differentiation and rep dispute escalation.
    """
    db = get_db()
    
    # Default status logic
    final_status = "paid" if is_already_paid else "pending_verification"

    # ── Validate dispute submission ──
    if is_dispute and not dispute_reason:
        raise HTTPException(status_code=400, detail="A reason is required when raising a rep ownership dispute.")

    # 1a. Check if this payee is a known staff member (admin) FIRST — before vendor
    #     resolution. This lets us set vendor.type='staff' correctly for ALL submission
    #     types (office, disbursement, staff_commission), fixing the mismatch where
    #     office expenditures from known staff were being stored as vendor.type='company',
    #     making them invisible to the HR expenses tab which filters on vendors.type='staff'.
    staff_check = await db_execute(lambda: db.table("admins").select("id").eq("email", payee_email).execute())
    is_known_staff = bool(staff_check.data)
    requester_id = staff_check.data[0]['id'] if is_known_staff else None

    # Resolve the correct vendor type up front
    def resolve_vendor_type(submission_type: str, known_staff: bool) -> str:
        if known_staff or submission_type == "staff_commission":
            return "staff"
        if submission_type == "partner":
            return "individual"
        return "company"

    correct_vendor_type = resolve_vendor_type(type, is_known_staff)

    # 1b. Vendor / Payee Resolution
    existing_vendor = await db_execute(lambda: db.table("vendors").select("id, type").eq("email", payee_email).execute())
    if existing_vendor.data:
        vendor_id = existing_vendor.data[0]['id']
        vendor_update = {
            "name": payee_name,
            "phone": payee_phone,
            "rc_number": payee_id,
            "tin": payee_tin,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if bank_name and acc_number:
            vendor_update.update({
                "bank_name": bank_name,
                "account_number": acc_number,
                "account_name": acc_name
            })
        # Correct the vendor type if it was previously wrong (e.g. 'company' for a staff member).
        # This retroactively fixes existing vendors so their past records become visible in HR tab.
        if existing_vendor.data[0].get('type') != correct_vendor_type and correct_vendor_type == "staff":
            vendor_update["type"] = "staff"
            if requester_id:
                vendor_update["admin_id"] = requester_id
        await db_execute(lambda: db.table("vendors").update(vendor_update).eq("id", vendor_id).execute())
    else:
        vendor_data = {
            "type": correct_vendor_type,
            "name": payee_name,
            "email": payee_email,
            "phone": payee_phone,
            "rc_number": payee_id,
            "tin": payee_tin,
            "bank_name": bank_name,
            "account_number": acc_number,
            "account_name": acc_name
        }
        v_res = await db_execute(lambda: db.table("vendors").insert(vendor_data).execute())
        vendor_id = v_res.data[0]['id']

    # 1c. Requester Resolution — admin check already done above (staff_check).
    #     Fall back to vendor admin_id link or invite record if not found.
    if not requester_id:
        v_link = await db_execute(lambda: db.table("vendors").select("admin_id").eq("email", payee_email).not_.is_("admin_id", "null").execute())
        if v_link.data:
            requester_id = v_link.data[0]['admin_id']
    
    # Final safety check: if we still don't have requester_id, try a direct email lookup on admins table one last time
    if not requester_id:
        final_staff_check = await db_execute(lambda: db.table("admins").select("id").eq("email", payee_email).execute())
        if final_staff_check.data:
            requester_id = final_staff_check.data[0]['id']

    if not requester_id:
        inv_res = await db_execute(lambda: db.table("portal_invites").select("invited_by").eq("email", payee_email).execute())
        if inv_res.data:
            requester_id = inv_res.data[0]['invited_by']

    # 1d. Category Mapping
    category_map = {
        "office": "Office Expenditure",
        "staff_commission": "Sales Commission",
        "partner": "Partner Payout",
        "company": "Company Expenditure",
        "contractor": "Contractor Payout",
        "disbursement": "Office Expenditure"
    }
    category = category_map.get(type, "General Expenditure")

    # 2. Commission Logic (Staff & Partner) & Fraud/Dispute Shield
    is_high_risk = False
    risk_notes = []
    linked_invoice_id = None

    if type in ["staff_commission", "partner"] and invoice_number:
        inv_res = await db_execute(lambda: db.table("invoices")
            .select("id, client_id, sales_rep_id, sales_rep_name, amount, clients(full_name, email)")
            .eq("invoice_number", invoice_number)
            .execute()
        )
        if inv_res.data:
            inv = inv_res.data[0]
            linked_invoice_id = inv["id"]

            # --- SMART ANALYSIS: Flagging instead of Blocking to avoid 'Glitches' ---
            
            # 1. Check Dashboard for existing verified payments
            check_earn = await db_execute(lambda: db.table("commission_earnings")
                .select("id, created_at, is_paid")
                .eq("invoice_id", linked_invoice_id)
                .eq("payment_amount", claim_amount)
                .execute())
            
            if check_earn.data:
                match = check_earn.data[0]
                is_high_risk = True # Mark for attention
                verified_date = match["created_at"][:10]
                status_label = "PAID" if match["is_paid"] else "VERIFIED/UNPAID"
                risk_notes.append(
                    f"🔍 SYSTEM MATCH: A dashboard record for this amount (₦{claim_amount:,.0f}) was already {status_label} on {verified_date}. "
                    "HR should verify if this is a duplicate or a new instalment."
                )

            # 2. Check Portal for existing claims (Pending/Approved)
            check_portal = await db_execute(lambda: db.table("expenditure_requests")
                .select("id, status, created_at")
                .eq("invoice_id", linked_invoice_id)
                .eq("category", "Sales Commission")
                .neq("status", "rejected")
                .execute())
            
            if check_portal.data:
                is_high_risk = True
                risk_notes.append(
                    f"🚩 POTENTIAL DUPLICATE: {len(check_portal.data)} other claim(s) exist in the portal for this invoice. "
                    "Please cross-check before approving."
                )

            # ── Rep dispute escalation ──
            if is_dispute:
                is_high_risk = True
                existing_rep = inv.get("sales_rep_name") or f"Rep ID {inv.get('sales_rep_id', 'unknown')}"
                risk_notes.append(
                    f"⚠️ REP OWNERSHIP DISPUTE: {payee_name} ({payee_email}) is challenging "
                    f"existing assignment to '{existing_rep}'. "
                    f"Reason given: {dispute_reason}"
                )
            else:
                # Standard fraud checks
                if inv.get("clients"):
                    cid = inv["client_id"]
                    act_res = await db_execute(lambda: db.table("activity_log")
                        .select("id").eq("client_id", cid).execute()
                    )
                    if not act_res.data:
                        is_high_risk = True
                        risk_notes.append("🚩 NO CRM HISTORY: Client exists but has zero logged activity.")
                else:
                    is_high_risk = True
                    risk_notes.append("🚩 ANONYMOUS INVOICE: Not yet linked to a verified client record.")

        # ── Commission rate resolution (3-tier waterfall) ──
        #
        # Tier 1 — Vendor's own rate (per-partner override set in dashboard)
        # Tier 2 — system_settings global defaults
        #           · default_partner_commission_rate  (partners)
        #           · default_commission_rate          (staff)
        #           · default_wht_rate                 (both)
        # Tier 3 — hardcoded fallback: Partners = 15%, Staff = 10%, WHT = 5%

        # Fetch global settings once (used as Tier 2 fallback)
        _sys_res = await db_execute(lambda: db.table("system_settings")
            .select("key, value")
            .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
            .execute()
        )
        _sys = {s["key"]: s["value"] for s in (_sys_res.data or [])}

        def _to_dec(pct_str, fallback):
            """Convert a stored percentage string e.g. '15' or '0.15' to a Decimal fraction."""
            try:
                v = Decimal(str(pct_str))
                return v / 100 if v > 1 else v
            except Exception:
                return Decimal(str(fallback))

        if type == "partner":
            # Tier 1: vendor's own rate
            _vrate_res = await db_execute(lambda: db.table("vendors")
                .select("gross_commission_rate, wht_rate")
                .eq("email", payee_email)
                .execute()
            )
            _vdata = (_vrate_res.data or [None])[0] or {}
            if _vdata.get("gross_commission_rate"):
                COMMISSION_RATE = _to_dec(_vdata["gross_commission_rate"], 0.15)
                WHT_RATE        = _to_dec(_vdata.get("wht_rate") or 5, 0.05)
            elif _sys.get("default_partner_commission_rate"):
                # Tier 2: global partner default from system_settings
                COMMISSION_RATE = _to_dec(_sys["default_partner_commission_rate"], 0.15)
                WHT_RATE        = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
            else:
                # Tier 3: hardcoded
                COMMISSION_RATE = Decimal("0.15")
                WHT_RATE        = Decimal("0.05")
        else:
            # Staff: no per-vendor override — use global setting or hardcoded
            if _sys.get("default_commission_rate"):
                COMMISSION_RATE = _to_dec(_sys["default_commission_rate"], 0.10)
                WHT_RATE        = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
            else:
                COMMISSION_RATE = Decimal("0.10")
                WHT_RATE        = Decimal("0.05")

        if payment_type == "initial_deposit" and property_price and property_price > 0:
            commission_base = Decimal(str(property_price))
            payment_type_label = "Initial Deposit Commission"
        else:
            commission_base = Decimal(str(claim_amount))
            payment_type_label = "Instalment Commission" if payment_type == "instalment" else "Commission"

        gross = commission_base * COMMISSION_RATE
        wht = gross * WHT_RATE
        net = gross - wht

        title = (
            f"{'Staff' if type == 'staff_commission' else 'Partner'} "
            f"{payment_type_label}: {invoice_number}"
        )
    else:
        # Office / Company / Contractor Expenditure
        gross = Decimal(str(claim_amount))
        wht = Decimal("0")
        net = gross
        title = f"{category}: {payee_name}"

    # 3. File Upload — supports multiple proof files.
    # Each file is uploaded to the 'Cloud Infrastructure' private bucket.
    # receipt_url is stored as a plain path string (1 file) or a JSON array (2+ files).
    file_url = None
    if files:
        uploaded_paths = []
        upload_errors = []
        for f in files:
            if f and f.filename:  # guard against empty slots
                file_ext = f.filename.rsplit('.', 1)[-1] if '.' in f.filename else 'bin'
                file_path = f"portal_claims/{vendor_id}_{uuid.uuid4().hex}.{file_ext}"
                file_bytes = await f.read()
                ok = upload_portal_file(file_path, file_bytes, f.content_type)
                if ok:
                    uploaded_paths.append(file_path)
                else:
                    upload_errors.append(f.filename)

        if upload_errors:
            # Surface partial failures — do not silently swallow them
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload proof file(s): {', '.join(upload_errors)}. Please retry."
            )

        if len(uploaded_paths) == 1:
            file_url = uploaded_paths[0]          # plain string — fully backward-compatible
        elif len(uploaded_paths) > 1:
            file_url = json.dumps(uploaded_paths)  # JSON array for multi-file

    # ── Portal Payment Verification ──
    # When the claimant supplies a client_paid_amount (only shown when the invoice
    # has no existing unpaid commission claim), create a pending_verifications row
    # so Finance can confirm it in the Verifications tab — badged as "Portal".
    pending_verif_id = None
    if client_paid_amount and client_paid_amount > 0 and linked_invoice_id and type in ("partner", "staff_commission"):
        try:
            inv_for_verif = await db_execute(lambda: db.table("invoices").select("client_id").eq("id", linked_invoice_id).execute())
            verif_client_id = inv_for_verif.data[0]["client_id"] if inv_for_verif.data else None
            if verif_client_id:
                verif_payload = {
                    "invoice_id": linked_invoice_id,
                    "client_id": verif_client_id,
                    "deposit_amount": float(client_paid_amount),
                    "payment_proof_url": file_url,
                    "payment_date": datetime.now(timezone.utc).date().isoformat(),
                    "sales_rep_name": payee_name,
                    "status": "pending",
                    "source": "portal",
                    "submission_type": type,  # "partner" or "staff_commission"
                }
                v_res = await db_execute(lambda: db.table("pending_verifications").insert(verif_payload).execute())
                if v_res.data:
                    pending_verif_id = v_res.data[0]["id"]
        except Exception as verif_err:
            print(f"[WARN] Failed to create pending_verifications row for portal submission: {verif_err}")

    # 4. Create Record
    payload = {
        "title": title,
        "description": f"Portal submission via {type}\nAmt: {gross}",
        "remarks": remarks or None,
        "vendor_id": vendor_id,
        "invoice_id": linked_invoice_id,
        "amount_gross": float(gross),
        "wht_rate": 5 if type in ["staff_commission", "partner"] else 0,
        "wht_amount": float(wht),
        "net_payout_amount": float(net),
        "receipt_url": file_url,
        "status": final_status,
        "payout_reference": payout_reference if final_status == "paid" else None,
        "paid_at": datetime.now(timezone.utc).isoformat() if is_already_paid else None,
        "is_high_risk": is_high_risk,
        "risk_notes": "\n".join(risk_notes) if risk_notes else None,
        "source_platform": "payout_portal",
        "requester_id": requester_id,
        "category": category,
        # ── NEW fields ──
        "payment_type": payment_type,           # "initial_deposit" | "instalment" | null
        "is_disputed": is_dispute,
        "dispute_reason": dispute_reason if is_dispute else None,
        "vendor_invoice_number": invoice_number,
        "pending_verification_id": pending_verif_id, # Structural link for unified workflow
    }

    await db_execute(lambda: db.table("expenditure_requests").insert(payload).execute())

    # Notify all HRM admins of new payout/commission submission
    try:
        from routers.hr import notify_hr_admins
        is_commission_req = (type == "staff_commission")
        notif_type = "payout_commission_request" if is_commission_req else "payout_reimbursement_request"
        amount_str = f"₦{float(claim_amount):,.0f}" if claim_amount else "an amount"
        if is_commission_req:
            notif_title = "Commission Request Submitted"
            notif_message = f"💼 Commission request: {payee_name} submitted a claim for {amount_str}. Review in Commissions."
        else:
            notif_title = "Reimbursement Request Submitted"
            notif_message = f"🧾 Reimbursement request: {payee_name} submitted a claim for {amount_str}. Review in Expenses."
        await notify_hr_admins(title=notif_title, message=notif_message, notification_type=notif_type)
    except Exception as notif_err:
        print(f"[WARN] Payout notification dispatch failed: {notif_err}")

    # 5. Auto-assign rep on uncontested claims (rep_status was "unassigned")
    #    Only assign if this is NOT a dispute and NOT already assigned.
    if linked_invoice_id and not is_dispute and not is_high_risk:
        # Check if invoice still has no rep
        check_inv = await db_execute(lambda: db.table("invoices").select("sales_rep_id").eq("id", linked_invoice_id).execute())
        if check_inv.data and not check_inv.data[0].get("sales_rep_id"):
            rep_res = await db_execute(lambda: db.table("sales_reps")
                .select("id")
                .eq("email", payee_email)
                .execute()
            )
            if rep_res.data:
                await db_execute(lambda: db.table("invoices")
                    .update({"sales_rep_id": rep_res.data[0]["id"], "sales_rep_name": payee_name})
                    .eq("id", linked_invoice_id)
                    .execute()
                )

    status_message = (
        "Dispute lodged. Finance will review and contact both parties."
        if is_dispute
        else "Record submitted successfully."
    )
    return {"status": "success", "message": status_message, "is_dispute": is_dispute}


# ─────────────────────────────────────────────────────────────────────────────
# PORTAL BULK SUBMIT  — multiple commission claims from the payment history table
# ─────────────────────────────────────────────────────────────────────────────
class BulkClaimItem(BaseModel):
    payment_id: str
    payment_type: str           # "initial_deposit" | "instalment"
    amount: float               # the actual payment amount (instalment) or 0 (deposit uses property_price)
    commission_base: float      # resolved by frontend from lookup-invoice data


class BulkSubmitPayload(BaseModel):
    # Claimant identity
    type: str                   # "staff_commission" | "partner"
    payee_name: str
    payee_email: str
    payee_phone: str = ""
    payee_id: str = ""
    payee_tin: str = ""
    bank_name: Optional[str] = None
    acc_number: Optional[str] = None
    acc_name: Optional[str] = None
    # Invoice context
    invoice_number: str
    invoice_id: str
    property_price: float
    is_dispute: bool = False
    dispute_reason: Optional[str] = None
    remarks: str = ""
    # Selections from the payment history table
    claims: List[BulkClaimItem]
    # Optional new-payment log
    new_payment_amount: Optional[float] = None
    claim_on_new_payment: bool = False


@router.post("/portal/submit-bulk")
async def submit_payout_claims_bulk(payload: BulkSubmitPayload):
    """
    Bulk commission claim endpoint for the portal payment history table.
    Creates one expenditure_request per selected payment row so Finance can
    approve each one individually. Also optionally creates a pending_verifications
    row for a new client payment not yet in the system.
    """
    db = get_db()

    if not payload.claims and not payload.new_payment_amount:
        raise HTTPException(status_code=400, detail="No claims selected.")

    if payload.is_dispute and not payload.dispute_reason:
        raise HTTPException(status_code=400, detail="A reason is required for a dispute claim.")

    # ── Vendor / Requester resolution (same logic as portal/submit) ──
    staff_check = await db_execute(lambda: db.table("admins").select("id").eq("email", payload.payee_email).execute())
    is_known_staff = bool(staff_check.data)
    requester_id = staff_check.data[0]["id"] if is_known_staff else None

    correct_vendor_type = "staff" if (is_known_staff or payload.type == "staff_commission") else "individual"

    existing_vendor = await db_execute(lambda: db.table("vendors").select("id, type").eq("email", payload.payee_email).execute())
    if existing_vendor.data:
        vendor_id = existing_vendor.data[0]["id"]
        upd: dict = {"name": payload.payee_name, "phone": payload.payee_phone, "updated_at": datetime.now(timezone.utc).isoformat()}
        if payload.bank_name and payload.acc_number:
            upd.update({"bank_name": payload.bank_name, "account_number": payload.acc_number, "account_name": payload.acc_name})
        if existing_vendor.data[0].get("type") != correct_vendor_type and correct_vendor_type == "staff":
            upd["type"] = "staff"
            if requester_id:
                upd["admin_id"] = requester_id
        await db_execute(lambda: db.table("vendors").update(upd).eq("id", vendor_id).execute())
    else:
        vd = {
            "type": correct_vendor_type, "name": payload.payee_name, "email": payload.payee_email,
            "phone": payload.payee_phone, "rc_number": payload.payee_id, "tin": payload.payee_tin,
            "bank_name": payload.bank_name, "account_number": payload.acc_number, "account_name": payload.acc_name,
        }
        v_res = await db_execute(lambda: db.table("vendors").insert(vd).execute())
        vendor_id = v_res.data[0]["id"]

    if not requester_id:
        v_link = await db_execute(lambda: db.table("vendors").select("admin_id").eq("email", payload.payee_email).not_.is_("admin_id", "null").execute())
        if v_link.data:
            requester_id = v_link.data[0]["admin_id"]

    # ── Commission rate resolution (same 3-tier waterfall) ──
    _sys_res = await db_execute(lambda: db.table("system_settings")
        .select("key, value")
        .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
        .execute()
    )
    _sys = {s["key"]: s["value"] for s in (_sys_res.data or [])}

    def _to_dec(pct_str, fallback):
        try:
            v = Decimal(str(pct_str))
            return v / 100 if v > 1 else v
        except Exception:
            return Decimal(str(fallback))

    if payload.type == "partner":
        _vrate_res = await db_execute(lambda: db.table("vendors").select("gross_commission_rate, wht_rate").eq("email", payload.payee_email).execute())
        _vdata = ((_vrate_res.data or [None])[0]) or {}
        if _vdata.get("gross_commission_rate"):
            COMMISSION_RATE = _to_dec(_vdata["gross_commission_rate"], 0.15)
            WHT_RATE = _to_dec(_vdata.get("wht_rate") or 5, 0.05)
        elif _sys.get("default_partner_commission_rate"):
            COMMISSION_RATE = _to_dec(_sys["default_partner_commission_rate"], 0.15)
            WHT_RATE = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
        else:
            COMMISSION_RATE = Decimal("0.15")
            WHT_RATE = Decimal("0.05")
    else:
        if _sys.get("default_commission_rate"):
            COMMISSION_RATE = _to_dec(_sys["default_commission_rate"], 0.10)
            WHT_RATE = _to_dec(_sys.get("default_wht_rate") or 5, 0.05)
        else:
            COMMISSION_RATE = Decimal("0.10")
            WHT_RATE = Decimal("0.05")

    category = "Partner Payout" if payload.type == "partner" else "Sales Commission"
    created_ids = []

    # ── Resolve sales_rep_id for commission_earnings ──
    # We need it to write the ledger entry. Look up via vendor email → sales_reps table.
    _rep_res = await db_execute(lambda: db.table("sales_reps").select("id").eq("email", payload.payee_email).execute())
    _rep_id = _rep_res.data[0]["id"] if _rep_res.data else None

    # Fetch invoice client_id once — used in commission_earnings and pending_verifications
    _inv_meta = await db_execute(lambda: db.table("invoices").select("client_id, property_name").eq("id", payload.invoice_id).execute())
    _client_id     = _inv_meta.data[0]["client_id"]    if _inv_meta.data else None
    _property_name = _inv_meta.data[0]["property_name"] if _inv_meta.data else ""

    # ── Create one expenditure_request per selected claim ──
    # For payments already confirmed in the system, also write commission_earnings
    # immediately so the ledger is up to date without Finance needing a second action.
    for claim in payload.claims:
        base = Decimal(str(claim.commission_base))
        gross = base * COMMISSION_RATE
        wht = gross * WHT_RATE
        net = gross - wht
        ptype_label = "Initial Deposit Commission" if claim.payment_type == "initial_deposit" else "Instalment Commission"
        title = f"{'Partner' if payload.type == 'partner' else 'Staff'} {ptype_label}: {payload.invoice_number}"

        row = {
            "title": title,
            "description": f"Bulk portal submission via {payload.type}\nPayment ID: {claim.payment_id}",
            "remarks": payload.remarks or None,
            "vendor_id": vendor_id,
            "invoice_id": payload.invoice_id,
            "amount_gross": float(gross),
            "wht_rate": 5,
            "wht_amount": float(wht),
            "net_payout_amount": float(net),
            "status": "pending_verification",
            "source_platform": "payout_portal",
            "requester_id": requester_id,
            "category": category,
            "payment_type": claim.payment_type,
            "is_disputed": payload.is_dispute,
            "dispute_reason": payload.dispute_reason if payload.is_dispute else None,
            "vendor_invoice_number": payload.invoice_number,
            "payment_id": claim.payment_id, # Structural link for unified workflow
        }
        res = await db_execute(lambda: db.table("expenditure_requests").insert(row).execute())
        if res.data:
            created_ids.append(res.data[0]["id"])

        # NOTE: In the unified workflow, we NO LONGER write to commission_earnings here.
        # The ledger entry is created ONLY when Finance clicks 'Verify' in the Payouts Dashboard.

    # ── Optional: new client payment log ──
    file_url = None  # bulk endpoint doesn't handle file uploads — rep attaches separately
    if payload.new_payment_amount and payload.new_payment_amount > 0:
        try:
            inv_for_verif = await db_execute(lambda: db.table("invoices").select("client_id").eq("id", payload.invoice_id).execute())
            verif_client_id = inv_for_verif.data[0]["client_id"] if inv_for_verif.data else None
            if verif_client_id:
                verif_payload = {
                    "invoice_id": payload.invoice_id,
                    "client_id": verif_client_id,
                    "deposit_amount": float(payload.new_payment_amount),
                    "payment_date": datetime.now(timezone.utc).date().isoformat(),
                    "sales_rep_name": payload.payee_name,
                    "status": "pending",
                    "source": "portal",
                    "submission_type": payload.type,
                }
                v_res = await db_execute(lambda: db.table("pending_verifications").insert(verif_payload).execute())
                pending_verif_id = v_res.data[0]["id"] if (v_res.data and len(v_res.data) > 0) else None

                # If rep also wants to claim commission on the new payment, create one more request
                if payload.claim_on_new_payment:
                    base = Decimal(str(payload.new_payment_amount))
                    gross = base * COMMISSION_RATE
                    wht = gross * WHT_RATE
                    net = gross - wht
                    row = {
                        "title": f"{'Partner' if payload.type == 'partner' else 'Staff'} Commission (Pending Payment): {payload.invoice_number}",
                        "description": f"Commission claim on portal-reported payment of ₦{payload.new_payment_amount:,.0f}. Held pending Finance verification.",
                        "remarks": payload.remarks or None,
                        "vendor_id": vendor_id,
                        "invoice_id": payload.invoice_id,
                        "amount_gross": float(gross),
                        "wht_rate": 5,
                        "wht_amount": float(wht),
                        "net_payout_amount": float(net),
                        "status": "pending_verification",
                        "source_platform": "payout_portal",
                        "requester_id": requester_id,
                        "category": category,
                        "payment_type": "instalment",
                        "vendor_invoice_number": payload.invoice_number,
                        "pending_verification_id": pending_verif_id, # Structural link for unified workflow
                    }
                    res = await db_execute(lambda: db.table("expenditure_requests").insert(row).execute())
                    if res.data:
                        created_ids.append(res.data[0]["id"])
        except Exception as ve:
            print(f"[WARN] Failed to create pending_verifications for bulk submission: {ve}")

    # Notifications
    try:
        from routers.hr import notify_hr_admins
        notif_type = "payout_commission_request"
        count = len(created_ids)
        await notify_hr_admins(
            title="Commission Request Submitted",
            message=f"💼 {payload.payee_name} submitted {count} commission claim(s) via portal. Review in Commissions.",
            notification_type=notif_type
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"{len(created_ids)} claim(s) submitted successfully.",
        "created_ids": created_ids,
    }


@router.patch("/requests/{request_id}")
async def update_payout_request_status(request_id: str, body: dict, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Simple status update for payout requests (approve/reject from HRM portal)."""
    db = get_db()
    allowed = {"approved", "rejected", "pending"}
    new_status = body.get("status")
    if not new_status or new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(allowed)}")
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("id").eq("id", request_id).limit(1).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    await db_execute(lambda: db.table("expenditure_requests").update({
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", request_id).execute())

    # --- Notification Bridge ---
    # Since HR mostly uses the Expenses tab, we ensure this endpoint also triggers notifications
    # if the claimant is a staff member (requester_id is present).
    try:
        from routers.hr import send_notification
        req_full = await db_execute(lambda: db.table("expenditure_requests")
            .select("*, vendors(name)").eq("id", request_id).maybe_single().execute())
        
        if req_full.data and req_full.data.get("requester_id"):
            exp = req_full.data
            requester_id = exp["requester_id"]
            raw_category = exp.get("category") or ""
            is_commission = "commission" in raw_category.lower() or "commission" in (exp.get("title") or "").lower()
            category_label = "Commission Claim" if is_commission else "Reimbursement Claim"
            amount = exp.get("amount_gross") or 0
            
            status_verb = "approved" if new_status == "approved" else "paid" if new_status == "paid" else "rejected"
            amount_str = f"₦{float(amount):,.0f}"
            
            if new_status == "rejected":
                status_msg = f"❌ Your {category_label} for {amount_str} was declined by HR."
            elif new_status == "paid":
                status_msg = f"✅ Your {category_label} for {amount_str} has been paid successfully."
            else:
                status_msg = f"📩 Your {category_label} for {amount_str} has been {status_verb}."

            await send_notification(requester_id, "Claim Status Update", status_msg, "expense_update")
    except Exception as e:
        print(f"[WARN] Payout notification bridge failed: {e}")

    return {"status": "ok", "new_status": new_status}

@router.patch("/requests/{request_id}/void")
async def void_payout_request(request_id: str, data: VoidExpenditureRequest, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Voids an expenditure request so it's ignored in reporting."""
    if not has_any_role(current_admin, "admin"):
        raise HTTPException(status_code=403, detail="Only Admins can void expenditures")
        
    db = get_db()
    
    # 1. Check if it exists
    req_res = await db_execute(lambda: db.table("expenditure_requests").select("status, title").eq("id", request_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    # 2. Update status to voided and log reason
    update_data = {
        "status": "voided",
        "void_reason": data.reason,
        "voided_at": datetime.now(timezone.utc).isoformat(),
        "voided_by": current_admin['sub']
    }
    
    await db_execute(lambda: db.table("expenditure_requests").update(update_data).eq("id", request_id).execute())
    
    # 3. Log Activity
    try:
        from routers.analytics import log_activity
        await log_activity(
            "expenditure_voided",
            f"Expenditure request '{req_res.data[0]['title']}' voided by Admin. Reason: {data.reason}",
            current_admin['sub'],
            metadata={"request_id": request_id}
        )
    except: pass
    
    return {"status": "success", "message": "Expenditure request voided successfully"}


# ─── ANALYTICS & REPORTING ───────────────────────────────────

class SendReportRequest(BaseModel):
    report_type: str
    email: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ScheduleRequest(BaseModel):
    report_type: str
    frequency: str # weekly, monthly
    recipients: List[str]
    is_active: bool = True

@router.get("/stats/summary")
async def get_payout_stats(
    days: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Aggregated stats for the dashboard charts and summary cards with flexible timeframes."""
    db = get_db()
    
    # 1. Date Logic
    if days:
        start_ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        end_ts = datetime.now(timezone.utc).isoformat()
    elif start_date and end_date:
        start_ts = f"{start_date}T00:00:00Z"
        end_ts = f"{end_date}T23:59:59Z"
    else:
        # Default to 30 days if nothing specified
        start_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        end_ts = datetime.now(timezone.utc).isoformat()

    # 2. Main Expenditure Query (Paid & Approved & Partially Paid)
    query = db.table("expenditure_requests")\
        .select("amount_gross, net_payout_amount, amount_paid, wht_amount, created_at, status, payout_method, payment_type, vendors(name, type), admins!requester_id(full_name)")\
        .in_("status", ["paid", "approved", "partially_paid"])\
        .gte("created_at", start_ts)\
        .lte("created_at", end_ts)
        
    res = await db_execute(lambda: query.execute())
    exp_data = res.data or []

    # 2b. Commission Earnings Query (The Earned Ledger)
    comm_query = db.table("commission_earnings")\
        .select("*, sales_reps(name)")\
        .eq("is_voided", False)\
        .gte("created_at", start_ts)\
        .lte("created_at", end_ts)
    
    comm_res = await db_execute(lambda: comm_query.execute())
    comm_data = comm_res.data or []

    # Initialize Intelligence
    segment_stats = {
        "commissions": {"paid": 0, "owed": 0},
        "reimbursements": {"paid": 0, "owed": 0},
        "ops": {"paid": 0, "owed": 0}
    }
    
    payees = {}; requesters = {}; creditors = {}; period_totals = {}
    total_gross = 0; total_paid = 0; total_ap = 0; total_wht = 0
    
    date_format_len = 10 if (days and days <= 31) or (not days and start_date) else 7
    
    # PROCESS EXPENDITURE REQUESTS
    for r in exp_data:
        # Date Bucketing
        bucket = (r.get('created_at') or datetime.now().isoformat())[:date_format_len]
        
        # Financial Parsing
        gross = float(r.get('amount_gross') or 0)
        net = float(r.get('net_payout_amount') or 0)
        paid = float(r.get('amount_paid') or 0)
        wht = float(r.get('wht_amount') or 0)
        owed = max(0, net - paid)
        
        # Categorization
        v_info = r.get('vendors') or {}
        v_type = v_info.get('type', 'company')
        p_type = (r.get('payment_type') or '').lower()
        p_method = (r.get('payout_method') or '').lower()
        
        if p_method == 'reimbursement' or p_type == 'reimbursement':
            cat = "reimbursements"
        elif p_type in ['commission', 'initial_deposit', 'instalment']:
            cat = "commissions"
        elif v_type == 'staff' and p_type == '':
            # Untagged staff payments are treated as reimbursements per user confirmation
            cat = "reimbursements"
        else:
            # Everything else (Company vendors or tagged 'office') defaults to operational expenses
            cat = "ops"
            
        # Analytics Setup
        p_name = v_info.get('name', 'General Vendor')
        r_name = (r.get('admins') or {}).get('full_name', 'System')

        # 1. Payout Aggregation (Cash Flow) & Liability Aggregation (Owed)
        # Commissions are handled exclusively in the second loop (the ledger) to avoid double counting
        if cat != "commissions":
            segment_stats[cat]["paid"] += paid
            total_paid += paid
            segment_stats[cat]["owed"] += owed
            total_ap += owed
            total_wht += wht
            total_gross += gross
            if owed > 0: 
                creditors[p_name] = creditors.get(p_name, 0) + owed
        
        # Analytics (Always track payees/requesters regardless of cat)
        payees[p_name] = payees.get(p_name, 0) + paid
        requesters[r_name] = requesters.get(r_name, 0) + gross
        
        period_totals[bucket] = period_totals.get(bucket, 0) + gross

    # PROCESS COMMISSION EARNINGS (The Ledger of Liability & Legacy Payouts)
    for c in comm_data:
        bucket = (c.get('created_at') or datetime.now().isoformat())[:date_format_len]
        gross = float(c.get('gross_commission') or c.get('commission_amount') or 0)
        net = float(c.get('net_commission') or c.get('final_amount') or gross)
        paid_in_ledger = float(c.get('amount_paid') or 0)
        wht_in_ledger = float(c.get('wht_amount') or 0)
        owed = max(0, net - paid_in_ledger)
        
        # Commissions Paid: Aggregate from ledger (catches legacy) + Loop 1 (catches portal partials)
        segment_stats["commissions"]["paid"] += paid_in_ledger
        total_paid += paid_in_ledger
        total_wht += wht_in_ledger
        
        # Commissions Owed: The Ledger is the ONLY source for this to avoid claim/earning double counting.
        segment_stats["commissions"]["owed"] += owed
        total_ap += owed
        
        rep_name = (c.get('sales_reps') or {}).get('name', 'Staff Partner')
        payees[rep_name] = payees.get(rep_name, 0) + paid_in_ledger
        if owed > 0: 
            creditors[rep_name] = creditors.get(rep_name, 0) + owed
        
        total_gross += gross
        period_totals[bucket] = period_totals.get(bucket, 0) + gross

    # 4. ADVANCED ANALYTICS (Aging, Compliance, Velocity)
    aging = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    compliance = {"remitted": 0, "pending": 0}
    pay_times = []
    
    # We need a broader query for aging (all unpaid regardless of date filter)
    aging_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("amount_gross, net_payout_amount, amount_paid, created_at, status")
        .in_("status", ["approved", "partially_paid", "pending"])
        .execute())
    
    now = datetime.now(timezone.utc)
    for r in (aging_res.data or []):
        unpaid = float(r['net_payout_amount'] or 0) - float(r['amount_paid'] or 0)
        if unpaid <= 0: continue
        
        # Use robust pandas parsing for Python 3.10 compatibility with variable subseconds
        created = pd.to_datetime(r['created_at']).to_pydatetime()
        age_days = (now - created).days
        
        if age_days <= 30: aging["0-30"] += unpaid
        elif age_days <= 60: aging["31-60"] += unpaid
        elif age_days <= 90: aging["61-90"] += unpaid
        else: aging["90+"] += unpaid

    # WHT Compliance (Unified: Expenditures + Commissions)
    # 1. Expenditures
    comp_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("wht_amount, is_wht_remitted")
        .gt("wht_amount", 0)
        .in_("status", ["paid", "partially_paid"])
        .execute())
    for r in (comp_res.data or []):
        val = float(r['wht_amount'] or 0)
        if r.get('is_wht_remitted'): compliance["remitted"] += val
        else: compliance["pending"] += val

    # 2. Commissions
    try:
        comm_comp_res = await db_execute(lambda: db.table("commission_earnings")
            .select("wht_amount, is_wht_remitted")
            .gt("wht_amount", 0)
            .eq("is_paid", True)
            .execute())
        for c in (comm_comp_res.data or []):
            val = float(c.get('wht_amount') or 0)
            if c.get('is_wht_remitted'): compliance["remitted"] += val
            else: compliance["pending"] += val
    except Exception as e:
        if "is_wht_remitted" in str(e):
            # Fallback: Count all paid commission WHT as pending
            comm_pending_res = await db_execute(lambda: db.table("commission_earnings")
                .select("wht_amount")
                .gt("wht_amount", 0)
                .eq("is_paid", True)
                .execute())
            for c in (comm_pending_res.data or []):
                compliance["pending"] += float(c.get('wht_amount') or 0)
        else:
            raise

    # Global Metrics (Current Snapshot)
    active_res = await db_execute(lambda: db.table("expenditure_requests").select("id", count="exact").eq("status", "pending").execute())
    active_count = active_res.count or 0
    
    asset_res = await db_execute(lambda: db.table("company_assets").select("purchase_cost").execute())
    total_assets = sum(float(r.get('purchase_cost') or 0) for r in (asset_res.data or []))

    # Efficiency (Time to Pay)
    eff_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("created_at, reviewed_at")
        .eq("status", "paid")
        .not_.is_("reviewed_at", "null")
        .limit(50)
        .execute())
    for r in (eff_res.data or []):
        c = pd.to_datetime(r['created_at']).to_pydatetime()
        p = pd.to_datetime(r['reviewed_at']).to_pydatetime()
        pay_times.append((p - c).total_seconds() / 3600)
    avg_speed = sum(pay_times) / len(pay_times) if pay_times else 0

    # Sort Analytics
    top_payees = dict(sorted(payees.items(), key=lambda x: x[1], reverse=True)[:5])
    top_requesters = dict(sorted(requesters.items(), key=lambda x: x[1], reverse=True)[:5])
    top_creditors = dict(sorted(creditors.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "overview": {
            "total_paid": total_paid,
            "total_owed": total_ap,
            "total_wht": compliance["pending"],
            "active_requests": active_count,
            "total_assets": total_assets,
            "avg_pay_hours": round(avg_speed, 1)
        },
        "segments": segment_stats,
        "analytics": {
            "top_payees": top_payees,
            "top_requesters": top_requesters,
            "top_creditors": top_creditors,
            "categories": {k.title(): (v["paid"] + v["owed"]) for k, v in segment_stats.items() if (v["paid"] + v["owed"]) > 0},
            "aging": aging,
            "compliance": compliance
        },
        "trend": [{"month": b, "total": period_totals[b]} for b in sorted(period_totals.keys())]
    }

@router.post("/stats/send-email")
async def send_on_demand_report(
    data: SendReportRequest, 
    bg_tasks: BackgroundTasks, 
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Triggers an immediate report email via background task."""
    try:
        report_data = await ReportService.get_report_data(data.report_type, data.start_date, data.end_date)
        pdf_io = ReportService.generate_pdf(report_data, f"Requested Report: {data.report_type}")
        
        bg_tasks.add_task(
            send_report_email,
            email=data.email,
            subject=f"Requested {data.report_type.replace('_', ' ').title()}",
            report_name=f"{data.report_type}_{datetime.now().strftime('%Y%m%d')}.pdf",
            pdf_bytes=pdf_io.getvalue()
        )
        return {"status": "success", "message": f"Report queued for delivery to {data.email}"}
    except Exception as e:
        logger.error(f"On-demand report failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate or send report")

@router.get("/stats/export")
async def export_payout_report(
    report_type: str = "payout_audit",
    ledger: Optional[str] = None, # new parameter for specific tab export
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Generates CSV export for the specified report type or ledger view."""
    db = get_db()
    
    if ledger:
        # Specialized exports for each dashboard tab
        if ledger == 'commissions':
            res = await db_execute(lambda: db.table("commission_earnings").select("created_at, sales_reps(name), commission_amount, wht_amount, net_commission, is_paid").execute())
            df = pd.DataFrame(res.data)
        elif ledger == 'staff':
            res = await db_execute(lambda: db.table("expenditure_requests").select("created_at, vendors(name), title, category, amount_gross, net_payout_amount, status").eq("vendors.type", "staff").execute())
            df = pd.DataFrame(res.data)
        elif ledger == 'vendors':
            res = await db_execute(lambda: db.table("expenditure_requests").select("created_at, vendors!inner(name, type), title, category, amount_gross, wht_amount, net_payout_amount, status").in_("vendors.type", ["company", "individual"]).execute())
            rows = [r for r in res.data if r.get("vendors") and r["vendors"].get("type") in ("company", "individual")]
            df = pd.DataFrame(rows)
        else:
            res = await db_execute(lambda: db.table("expenditure_requests").select("*").execute())
            df = pd.DataFrame(res.data)
    else:
        # Standard Audit Report
        report_data = await ReportService.get_report_data(report_type, start_date, end_date)
        df = pd.DataFrame(report_data)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data found for the selected criteria")

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    filename = f"{ledger or report_type}_export_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(stream.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/stats/schedule")
async def save_report_schedule(data: ScheduleRequest, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Saves or updates a report schedule."""
    db = get_db()
    payload = {
        "report_type": data.report_type,
        "frequency": data.frequency,
        "recipients": data.recipients,
        "is_active": data.is_active,
        "owner_id": current_admin.get('id')
    }
    
    try:
        res = await db_execute(lambda: db.table("report_schedules").upsert(payload).execute())
        return {"status": "success", "data": res.data[0] if res.data else {}}
    except Exception as e:
        logger.warning(f"Failed to upsert schedule (table might be missing): {e}")
        return {"status": "success", "message": "Automation preference logged."}


# ─── PROCUREMENT EXPENSES ─────────────────────────────────────
from models import ProcurementExpenseCreate

@router.post("/procurement-expenses")
async def create_procurement_expense(data: ProcurementExpenseCreate, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    payload = data.dict(exclude_none=True)
    payload["created_by"] = current_admin['sub']
    
    res = await db_execute(lambda: db.table("procurement_expenses").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to record procurement expense")
    return res.data[0]

@router.get("/procurement-expenses")
async def list_procurement_expenses(property_id: Optional[str] = None, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    query = db.table("procurement_expenses").select("*")
    if property_id:
        query = query.eq("property_id", property_id)
    res = await db_execute(lambda: query.order("expense_date", desc=True).execute())
    return res.data

@router.patch("/procurement-expenses/{expense_id}")
async def update_procurement_expense(expense_id: str, payload: dict, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    update_data = {}
    if "title" in payload: update_data["title"] = payload["title"]
    if "amount" in payload: update_data["amount"] = float(payload["amount"])
    if "category" in payload: update_data["category"] = payload["category"]
    if "amount_paid" in payload: update_data["amount_paid"] = float(payload["amount_paid"])
    if "status" in payload: update_data["status"] = payload["status"]
    if "notes" in payload: update_data["notes"] = payload["notes"]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided")
        
    res = await db_execute(lambda: db.table("procurement_expenses").update(update_data).eq("id", expense_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Expense not found")
    return res.data[0]

@router.post("/procurement-expenses/import")
async def import_procurement_expenses(
    file: UploadFile = File(...),
    property_id: Optional[str] = Form(None),
    estate_draft_id: Optional[str] = Form(None),
    current_admin=Depends(require_roles(["super_admin"]))
):
    """
    Intelligent procurement import engine.
    Detects section headers, metadata, and maps non-standard vendor columns.
    """
    db = get_db()
    content = await file.read()
    
    try:
        # Load data
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content), header=None).fillna('')
        else:
            df = pd.read_excel(io.BytesIO(content), header=None).fillna('')
        
        all_records = []
        current_category = "General"
        project_metadata = {}
        mapping = {}
        mapping_header_row_idx = -1
        
        # KEYWORD DEFINITIONS
        section_keywords = ['QUOTATION FOR', 'WORKS', 'SECTION', 'CATEGORY', 'PROPOSAL']
        header_keywords = {
            'title': ['item', 'description', 'particulars', 'title', 'name'],
            'amount': ['total cost', 'total amount', 'amount', 'grand total', 'final cost'],
            'unit_price': ['unit price', 'rate', 'unit cost', 'price per'],
            'paid': ['paid', 'payment', 'actual'],
            'quantity': ['qty', 'quantity', 'units', 'number', 'count'],
            'duration': ['duration', 'days', 'weeks', 'months', 'period'],
            'budget': ['budget', 'estimate', 'allocation'],
            'vendor': ['vendor', 'supplier', 'contractor', 'company']
        }
        meta_keywords = {
            'location': ['location', 'site', 'project'],
            'date': ['date', 'quotation date'],
            'company': ['company', 'vendor', 'contractor']
        }

        # PASS 1: SCAN FOR METADATA & DATA
        for i, row in df.iterrows():
            row_list = [str(v).strip() for v in row]
            row_text = ' '.join([v for v in row_list if v]).upper()
            
            # 1. Extract Project Metadata (from top rows)
            if i < 15: # Usually in header
                for key, aliases in meta_keywords.items():
                    if key not in project_metadata:
                        for alias in aliases:
                            if alias.upper() in row_text:
                                # Try to get value from next cell or after colon
                                for cell in row_list:
                                    if alias.upper() in cell.upper() and ':' in cell:
                                        val = cell.split(':', 1)[1].strip()
                                        if key == 'date':
                                            try:
                                                std_date = pd.to_datetime(val, dayfirst=True, errors='coerce')
                                                if not pd.isna(std_date):
                                                    val = std_date.strftime('%Y-%m-%d')
                                            except: pass
                                        project_metadata[key] = val
                                        break
                                if key not in project_metadata:
                                    for cell in row_list:
                                        if found_alias and cell:
                                            val = cell
                                            if key == 'date':
                                                # Standardize Date: DD/MM/YYYY -> YYYY-MM-DD
                                                try:
                                                    # Try common formats, dayfirst=True is critical for DD/MM/YYYY
                                                    std_date = pd.to_datetime(val, dayfirst=True, errors='coerce')
                                                    if not pd.isna(std_date):
                                                        val = std_date.strftime('%Y-%m-%d')
                                                except: pass
                                            project_metadata[key] = val
                                            break
                                        if alias.upper() in cell.upper():
                                            found_alias = True
            
            # 2. Detect Section Headers (e.g. "FENCING QUOTATION")
            # If row has text but very few columns filled, it might be a section
            non_empty_cells = [v for v in row_list if v and v != 'nan']
            if 1 <= len(non_empty_cells) <= 2:
                if any(k in row_text for k in section_keywords):
                    current_category = ' '.join(non_empty_cells).title()
                    # Reset mapping for new section if headers repeat
                    mapping = {} 
                    continue

            # 3. Detect Table Headers (S/N, Description, etc.)
            temp_mapping = {}
            for target, aliases in header_keywords.items():
                for idx, val in enumerate(row_list):
                    clean_val = val.lower()
                    if any(a in clean_val for a in aliases):
                        temp_mapping[target] = idx
                        break
            
            if 'title' in temp_mapping and 'amount' in temp_mapping:
                mapping = temp_mapping
                mapping_header_row_idx = i
                continue

            # 4. Extract Data Rows
            if mapping and i > mapping_header_row_idx:
                title_idx = mapping.get('title')
                amount_idx = mapping.get('amount')
                
                if title_idx is None or amount_idx is None: continue
                
                title_val = row_list[title_idx]
                amount_val = row_list[amount_idx]
                
                if not title_val or title_val.lower() in ['total', 'grand total', 'subtotal', 'nan']:
                    continue
                
                # S/N Check (often the first cell is numeric for data rows)
                first_cell = row_list[0]
                if not first_cell.isdigit() and len(non_empty_cells) < 3:
                    # Might be a spacer or sub-header
                    continue

                # Parse numeric amount
                try:
                    amount = float(str(amount_val).replace('₦', '').replace(',', '').strip())
                except:
                    continue # Skip if no valid amount
                
                if amount <= 0: continue

                # Parse budget if exists
                budget = 0
                if mapping.get('budget') is not None:
                    try:
                        budget_val = row_list[mapping['budget']]
                        budget = float(str(budget_val).replace('₦', '').replace(',', '').strip())
                    except: pass
                
                # Vendor detection
                vendor_name = project_metadata.get('company')
                if mapping.get('vendor') is not None:
                    vendor_name = row_list[mapping['vendor']]

                # Build Metadata
                extra_metadata = {
                    "Import Source": file.filename,
                    "Project Location": project_metadata.get('location', 'Unknown'),
                    "Quotation Date": project_metadata.get('date', 'Unknown')
                }
                
                # Standardize key fields in metadata for frontend badges
                if mapping.get('quantity') is not None:
                    extra_metadata["Quantity"] = row_list[mapping['quantity']]
                if mapping.get('duration') is not None:
                    extra_metadata["Duration"] = row_list[mapping['duration']]
                if mapping.get('unit_price') is not None:
                    extra_metadata["Unit Price"] = row_list[mapping['unit_price']]
                
                # Capture all other columns as generic metadata
                for idx, val in enumerate(row_list):
                    if idx in mapping.values() or not val or val == 'nan': continue
                    try:
                        header_name = str(df.iloc[mapping_header_row_idx, idx]).strip()
                        if not header_name or header_name == 'nan': header_name = f"Field_{idx}"
                        extra_metadata[header_name] = val
                    except:
                        extra_metadata[f"Col_{idx}"] = val

                # Clean paid
                paid = 0
                if mapping.get('paid') is not None:
                    try:
                        paid_val = row_list[mapping['paid']]
                        paid = float(str(paid_val).replace('₦', '').replace(',', '').strip())
                    except: pass

                # Final Date Validation
                final_date = project_metadata.get('date')
                try:
                    # Ensure it's in YYYY-MM-DD
                    valid_date = pd.to_datetime(final_date, dayfirst=True, errors='coerce')
                    if pd.isna(valid_date):
                        final_date = datetime.now().strftime('%Y-%m-%d')
                    else:
                        final_date = valid_date.strftime('%Y-%m-%d')
                except:
                    final_date = datetime.now().strftime('%Y-%m-%d')

                all_records.append({
                    "created_by": current_admin['sub'],
                    "property_id": property_id,
                    "estate_draft_id": estate_draft_id,
                    "title": title_val,
                    "amount": amount,
                    "budget": budget or amount, # Default budget to amount if missing
                    "category": current_category,
                    "metadata": extra_metadata,
                    "amount_paid": paid,
                    "vendor_name": vendor_name,
                    "status": "paid" if paid >= amount - 1 and amount > 0 else ("partial" if paid > 0 else "pending"),
                    "expense_date": final_date
                })

        if not all_records:
            raise HTTPException(status_code=400, detail="No valid records found. Ensure your file has 'Description' and 'Amount' columns.")

        try:
            res = await db_execute(lambda: db.table("procurement_expenses").insert(all_records).execute())
        except Exception as insert_err:
            # Fallback: Try without created_by if it's missing from schema
            if "created_by" in str(insert_err):
                for r in all_records: r.pop("created_by", None)
                res = await db_execute(lambda: db.table("procurement_expenses").insert(all_records).execute())
            else:
                raise insert_err
        
        return {
            "status": "success", 
            "imported": len(res.data) if res.data else 0,
            "metadata": project_metadata
        }
        
    except Exception as e:
        logger.error(f"Procurement Import Error: {e}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@router.delete("/procurement-expenses/wipe")
async def wipe_procurement_ledger(
    property_id: Optional[str] = Query(None),
    estate_draft_id: Optional[str] = Query(None),
    current_admin=Depends(require_roles(["super_admin"]))
):
    db = get_db()
    if not property_id and not estate_draft_id:
        raise HTTPException(status_code=400, detail="Must provide property_id or estate_draft_id")
    
    query = db.table("procurement_expenses").delete()
    if property_id:
        query = query.eq("property_id", property_id)
    else:
        query = query.eq("estate_draft_id", estate_draft_id)
        
    res = await db_execute(lambda: query.execute())
    return {"status": "success", "wiped": len(res.data) if res.data else 0}

# --- ESTATE DRAFTS & PIPELINE ---
from models import EstateDraftCreate

@router.post("/estates")
async def create_estate_draft(data: EstateDraftCreate, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    payload = data.dict()
    payload["created_by"] = current_admin['sub']
    
    res = await db_execute(lambda: db.table("estate_drafts").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create estate draft")
    return res.data[0]

@router.get("/estates")
async def list_estate_drafts(current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("estate_drafts").select("*").order("created_at", desc=True).execute())
    return res.data

@router.patch("/estates/{draft_id}")
async def update_estate_draft(draft_id: str, data: dict, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    res = await db_execute(lambda: db.table("estate_drafts").update(data).eq("id", draft_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    return res.data[0]

@router.post("/estates/{draft_id}/publish")
async def publish_estate(draft_id: str, current_admin=Depends(require_roles(["super_admin"]))):
    db = get_db()
    
    # 1. Fetch Draft
    res = await db_execute(lambda: db.table("estate_drafts").select("*").eq("id", draft_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = res.data[0]
    if draft.get("is_public"):
        raise HTTPException(status_code=400, detail="Estate is already public")
        
    # 2. Create Properties for each variation
    variations = draft.get("variations", [])
    created_prop_ids = []
    
    for var in variations:
        outright = float(var.get('outright_price', 0))
        installment = float(var.get('installment_price', 0))
        size = var['size_sqm']
        
        # 1. Create Outright Listing
        outright_payload = {
            "name": draft['name'],
            "estate_name": draft['name'],
            "location": draft['location'],
            "description": "Outright Payment Plan",
            "plot_size_sqm": size,
            "plot_size_sqm": size,
            "total_price": outright,
            "total_plots": var['total_plots'],
            "acquisition_cost": var.get('acquisition_cost', 0),
            "budget": float(draft.get('total_budget', 0)) if not created_prop_ids else 0, # Put budget on the first variation only to avoid double counting
            "is_active": True
        }
        o_res = await db_execute(lambda: db.table("properties").insert(outright_payload).execute())
        if o_res.data:
            created_prop_ids.append(o_res.data[0]['id'])
            
        # 2. Create Installment Listing (Optional)
        if installment > 0:
            inst_payload = {
                "name": draft['name'],
                "estate_name": draft['name'],
                "location": draft['location'],
                "description": "Installment Payment Plan",
                "plot_size_sqm": size,
                "total_price": installment,
                "total_plots": var['total_plots'],
                "acquisition_cost": 0,
                "is_active": True
            }
            i_res = await db_execute(lambda: db.table("properties").insert(inst_payload).execute())
            if i_res.data:
                created_prop_ids.append(i_res.data[0]['id'])
            
    # 3. Update Draft Status
    await db_execute(lambda: db.table("estate_drafts").update({"is_public": True}).eq("id", draft_id).execute())
    
    # 4. Link existing expenses to the first property ID created
    if created_prop_ids:
        await db_execute(lambda: db.table("procurement_expenses").update({"property_id": created_prop_ids[0]}).eq("estate_draft_id", draft_id).execute())

    return {"status": "success", "properties_created": len(created_prop_ids)}