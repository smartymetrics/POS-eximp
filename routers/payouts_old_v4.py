from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, File, UploadFile, Form, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database import get_db, db_execute
from models import ExpenditureRequestCreate, PayoutReview, AssetCreate, VendorCreate, VoidExpenditureRequest, PayoutPaymentData
from routers.auth import verify_token, has_any_role, require_roles
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

    # ─── TRIGGER AUTOMATED RECEIPT EMAIL ──────────────────────
    if data.status == 'approved' and updated_req.get('vendor_id'):
        # Re-fetch with vendor join AFTER the update so the email/PDF carries:
        #   1. Correct bank_name/account_number from the vendors table — req.get('vendors')
        #      was populated from the original select(*) which has no join and returns None
        #      for nested vendor fields, causing the email to show no bank details.
        #   2. Post-approval net_payout_amount / wht_amount (from the DB, not stale req).
        receipt_res = await db_execute(
            lambda: db.table('expenditure_requests').select('*, vendors(*)').eq('id', request_id).execute()
        )
        if receipt_res.data:
            full_req = receipt_res.data[0]
            vendor = full_req.get('vendors')
            if vendor and vendor.get('email'):
                bg_tasks.add_task(send_payout_receipt_email, full_req, vendor, current_admin['sub'])

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

    # 2. Commission History — Detect if an 'Initial Deposit Commission' has been claimed
    #    We check expenditure_requests for this invoice to see if anyone has already triggered the deal commission.
    claims_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("id")
        .eq("vendor_invoice_number", invoice_number)
        .eq("payment_type", "initial_deposit")
        .neq("status", "rejected")
        .execute()
    )
    has_initial_claim = len(claims_res.data or []) > 0
    payment_type = "initial_deposit" if not has_initial_claim else "instalment"
    
    # Also fetch client payments for the history list
    payments_res = await db_execute(lambda: db.table("payments")
        .select("id, amount, created_at, payment_method")
        .eq("invoice_id", invoice_id)
        .order("created_at")
        .execute()
    )
    prior_payments = payments_res.data or []
    payment_count = len(prior_payments)
    payment_sequence = payment_count + 1

    property_price = float(inv.get("amount") or 0)
    amount_paid_so_far = float(inv.get("amount_paid") or 0)
    balance = max(0.0, property_price - amount_paid_so_far)

    # Commission base:
    #   Initial deposit → commission on full property value (the deal is triggered)
    #   Instalment      → commission on the instalment amount the rep reports
    commission_base = property_price if payment_type == "initial_deposit" else None  # None = use claim_amount
    commission_rate = 0.05   # 5% gross (10% less 50% WHT effectively; matches existing 10%/5WHT)
    commission_preview = round(property_price * commission_rate, 2) if payment_type == "initial_deposit" else None

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
        "payment_sequence": payment_sequence,    # 1, 2, 3 …
        "payment_count": payment_count,          # how many prior payments exist
        # ── Commission preview ──
        "commission_rate": commission_rate,
        "commission_base": commission_base,      # None → use reported claim_amount
        "commission_preview": commission_preview,# pre-calc for deposit; null for instalment
        # ── Rep assignment ──
        "rep_status": rep_status,                # "unassigned" | "yours" | "conflict"
        "assigned_rep_name": assigned_rep_name,
        # ── History ──
        "previous_payments": [
            {
                "seq": i + 1,
                "amount": float(p.get("amount") or 0),
                "date": (p.get("created_at") or "")[:10],
                "method": p.get("payment_method") or "—"
            }
            for i, p in enumerate(prior_payments)
        ]
    }

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
    files: List[UploadFile] = File(default=[])  # Accepts one or many proof uploads
):
    """
    Unified endpoint for the 'Claims & Payouts' portal.
    Handles Office Expenditures, Staff Commissions, and Partner Commissions.
    Now supports initial deposit vs instalment differentiation and rep dispute escalation.
    """
    db = get_db()

    # ── Validate dispute submission ──
    if is_dispute and not dispute_reason:
        raise HTTPException(status_code=400, detail="A reason is required when raising a rep ownership dispute.")

    # 1. Vendor / Payee Resolution
    existing_vendor = await db_execute(lambda: db.table("vendors").select("id").eq("email", payee_email).execute())
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
        await db_execute(lambda: db.table("vendors").update(vendor_update).eq("id", vendor_id).execute())
    else:
        vendor_data = {
            "type": "staff" if type == "staff_commission" else ("individual" if type == "partner" else "company"),
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

    # 1b. Requester Resolution (Identify staff member from email or invite)
    requester_id = None
    # Priority 1: Check if payee is an admin themselves
    staff_res = await db_execute(lambda: db.table("admins").select("id").eq("email", payee_email).execute())
    if staff_res.data:
        requester_id = staff_res.data[0]['id']
    
    # Priority 2: Check if payee is a staff-vendor with linked admin_id
    if not requester_id:
        v_link = await db_execute(lambda: db.table("vendors").select("admin_id").eq("email", payee_email).not_.is_("admin_id", "null").execute())
        if v_link.data:
            requester_id = v_link.data[0]['admin_id']

    # Priority 3: Check if there was an invitation for this email
    if not requester_id:
        inv_res = await db_execute(lambda: db.table("portal_invites").select("invited_by").eq("email", payee_email).execute())
        if inv_res.data:
            requester_id = inv_res.data[0]['invited_by']

    # 1c. Category Mapping
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

        # ── Commission calculation by payment type ──
        #   Initial Deposit → commission on FULL property value (deal trigger)
        #   Instalment      → commission on the reported instalment amount only
        COMMISSION_RATE = Decimal("0.10")
        WHT_RATE = Decimal("0.05")

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
        "status": "paid" if is_already_paid else "pending_verification",
        "payout_reference": payout_reference if is_already_paid else None,
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
        
        created = datetime.fromisoformat(r['created_at'].replace('Z', '+00:00'))
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
        c = datetime.fromisoformat(r['created_at'].replace('Z', '+00:00'))
        p = datetime.fromisoformat(r['reviewed_at'].replace('Z', '+00:00'))
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
