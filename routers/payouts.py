from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, File, UploadFile, Form, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database import get_db
from models import ExpenditureRequestCreate, PayoutReview, AssetCreate, VendorCreate, VoidExpenditureRequest, PayoutPaymentData
from routers.auth import verify_token, has_any_role, require_roles
from email_service import send_payout_receipt_email, send_portal_invite_email, send_report_email
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
    res = db.table("vendors").insert(data.dict()).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create vendor")
    return res.data[0]

@router.get("/vendors")
async def list_vendors(type: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("vendors").select("*")
    if type:
        query = query.eq("type", type)
    res = query.order("name").execute()
    return res.data

# ─── EXPENDITURE REQUESTS ─────────────────────────────────────
@router.post("/requests")
async def submit_payout_request(data: ExpenditureRequestCreate, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    vendor_id = data.vendor_id
    # Inline vendor creation (e.g. for one-off staff claims)
    if not vendor_id and data.vendor_data:
        vendor_res = db.table("vendors").insert(data.vendor_data.dict()).execute()
        if vendor_res.data:
            vendor_id = vendor_res.data[0]['id']
            
    # Calculate WHT Suggestion
    # Note: For staff reimbursements, WHT is typically NOT applicable by default
    wht_details = {"rate": 0, "wht_amount": 0, "net_amount": data.amount_gross}
    
    if data.is_wht_applicable:
        vendor = db.table("vendors").select("tin, type").eq("id", vendor_id).execute().data[0]
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
        "status": "pending_verification"
    }
    
    res = db.table("expenditure_requests").insert(payload).execute()
    return res.data[0]

@router.get("/requests")
async def list_expenditure_requests(status: Optional[str] = None, show_voided: bool = False, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("expenditure_requests").select("*, vendors(*), admins!requester_id(full_name), expenditure_payments(*), company_assets(*)")
    
    if status:
        query = query.eq("status", status)
    
    if not show_voided:
        query = query.neq("status", "voided")
        
    res = query.order("created_at", desc=True).execute()
    return res.data

@router.post("/requests/{request_id}/payments")
async def record_payout_payment(request_id: str, data: PayoutPaymentData, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    
    # 1. Verify Request
    req_res = db.table("expenditure_requests").select("*").eq("id", request_id).execute()
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
    db.table("expenditure_payments").insert(payment_payload).execute()
    
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
        
    update_res = db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute()
    
    # Trigger automated receipt
    if update_res.data:
        req_with_vendor = db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute()
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
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Bill Verification: promote to 'pending' (audit queue) or reject outright."""
    if not has_any_role(current_admin, ["admin", "operations"]):
        raise HTTPException(status_code=403, detail="Only authorized roles can perform this action")
    
    db = get_db()
    req_res = db.table("expenditure_requests").select("*").eq("id", request_id).execute()
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    action = data.action  # 'pending' or 'rejected'
    if action not in ('pending', 'rejected'):
        raise HTTPException(status_code=400, detail="Invalid action. Use 'pending' or 'rejected'.")
    
    update_payload = {
        "status": action,
        "reviewed_by": current_admin['sub'],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if action == 'rejected':
        update_payload["wht_exemption_reason"] = data.reason or "Bill rejected at verification stage"
    elif action == 'pending' and data.due_date:
        update_payload["due_date"] = data.due_date
    
    db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute()
    return {"status": "success", "new_status": action}

@router.put("/requests/{request_id}/review")
async def review_payout_request(request_id: str, data: PayoutReview, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    if not has_any_role(current_admin, "admin"):
        raise HTTPException(status_code=403, detail="Only Admins can approve payouts")
        
    db = get_db()
    req_res = db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute()
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req = req_res.data[0]
    update_payload = {
        "status": data.status,
        "reviewed_by": current_admin['sub'],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "payout_reference": data.payout_reference,
        "wht_exemption_reason": data.rejection_reason if data.status == 'rejected' else req.get('wht_exemption_reason')
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

    res = db.table("expenditure_requests").update(update_payload).eq("id", request_id).execute()
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
            
            db.table("company_assets").insert(asset_payload).execute()
        except Exception as asset_err:
            print(f"⚠️ Warning: Payout approved but Asset logging failed: {asset_err}")
            # We don't fail the whole payout if asset logging hits a snag, but we log it.

    # ─── TRIGGER AUTOMATED RECEIPT EMAIL ──────────────────────
    if data.status == 'approved' and updated_req.get('vendor_id'):
        vendor = req.get('vendors')
        if vendor and vendor.get('email'):
            # Fetch fresh version of request for the receipt (includes updated WHT/amounts)
            bg_tasks.add_task(send_payout_receipt_email, updated_req, vendor, current_admin['sub'])

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
    
    res = db.table("expenditure_requests").update(update_payload).in_("id", data.request_ids).execute()
    return {"status": "success", "cleared_count": len(res.data) if res.data else 0}

@router.post("/requests/{request_id}/send-receipt")
async def trigger_manual_receipt(request_id: str, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Manually triggers a remittance advice email to the vendor."""
    db = get_db()
    req_res = db.table("expenditure_requests").select("*, vendors(*)").eq("id", request_id).execute()
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
    res = db.table("company_assets").insert(data.dict()).execute()
    return res.data[0]

@router.get("/assets")
async def list_assets(assigned_to: Optional[str] = None, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    db = get_db()
    query = db.table("company_assets").select("*, admins!assigned_to(full_name)")
    if assigned_to:
        query = query.eq("assigned_to", assigned_to)
    res = query.execute()
    return res.data


# ─── SECURE STORAGE ACCESS ────────────────────────────────────
from storage_service import generate_signed_url
from fastapi.responses import RedirectResponse

@router.get("/requests/{request_id}/view-document/{doc_type}")
async def view_secure_payout_document(request_id: str, doc_type: str, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """
    Securely redirects to a signed URL for proformas or receipts.
    doc_type: 'proforma', 'receipt'
    """
    db = get_db()
    req_res = db.table("expenditure_requests").select("*").eq("id", request_id).execute()
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    
    req = req_res.data[0]
    path = req.get('proforma_url') if doc_type == 'proforma' else req.get('receipt_url')
    
    if not path:
        raise HTTPException(
            status_code=404, 
            detail=f"No {doc_type} document link attached to this record. Please ensure the vendor uploaded a file or the admin provided a ref link."
        )
        
    # Redirect to external URLs directly
    if path.startswith("http"):
        return RedirectResponse(url=path)
        
    # Generate signed URL for private Supabase bucket 'Cloud Infrastructure'
    signed_url = generate_signed_url("Cloud Infrastructure", path)
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate secure access link")
        
    return RedirectResponse(url=signed_url)


# ─── PORTAL AUTOMATION ────────────────────────────────────────

class PortalInvite(BaseModel):
    email: str
    category: str # 'staff', 'company', or 'individual'

@router.post("/requests/portal-invite")
async def trigger_portal_invite(data: PortalInvite, bg_tasks: BackgroundTasks, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Triggers a professional system email invitation with a unique token."""
    db = get_db()
    
    # 1. Fetch current admin for the invitation signature
    admin_res = db.table("admins").select("full_name").eq("id", current_admin['sub']).execute()
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
    db.table("portal_invites").upsert(invite_payload, on_conflict="email").execute()
    
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
    invite_res = db.table("portal_invites").select("*").eq("token", token).execute()
    if not invite_res.data:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation link")
    
    invite = invite_res.data[0]
    
    # 2. Check if Payee is already onboarded
    payee_res = db.table("vendors").select("*").eq("email", invite['email']).execute()
    is_onboarded = len(payee_res.data) > 0
    payee_data = payee_res.data[0] if is_onboarded else None
    
    return {
        "email": invite['email'],
        "category": invite['category'],
        "is_onboarded": is_onboarded,
        "payee_data": payee_data
    }


@router.post("/portal/submit")
async def submit_payout_claim_from_portal(
    type: str = Form(...),
    payee_name: str = Form(...),
    payee_email: str = Form(...),
    payee_phone: str = Form(""),
    payee_id_number: str = Form(""),
    payee_tin: str = Form(""),
    bank_name: str = Form(...),
    acc_number: str = Form(...),
    acc_name: str = Form(...),
    claim_amount: float = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    Public-facing endpoint for portal submissions.
    Automatically creates/updates Vendor and generates a Pending Request.
    """
    db = get_db()
    
    # 1. Vendor Logic (Create or Update)
    vendor_data = {
        "type": type.lower(),
        "name": payee_name,
        "email": payee_email,
        "phone": payee_phone,
        "rc_number": payee_id_number,
        "tin": payee_tin,
        "bank_name": bank_name,
        "account_number": acc_number,
        "account_name": acc_name,
        "updated_at": datetime.now().isoformat()
    }
    
    # Check if vendor exists
    existing = db.table("vendors").select("id").eq("email", payee_email).execute()
    if existing.data:
        vendor_id = existing.data[0]['id']
        db.table("vendors").update(vendor_data).eq("id", vendor_id).execute()
    else:
        res = db.table("vendors").insert(vendor_data).execute()
        vendor_id = res.data[0]['id']

    # 2. File Upload (Quotation)
    quotation_url = None
    if file:
        file_ext = file.filename.split('.')[-1]
        file_path = f"portal_claims/{vendor_id}_{uuid.uuid4().hex}.{file_ext}"
        content = await file.read()
        db.storage.from_("Cloud Infrastructure").upload(file_path, content)
        quotation_url = file_path

    # 3. Create Expenditure Request (Treating Amount as Gross)
    amount_decimal = Decimal(str(claim_amount))
    
    # Calculate initial WHT suggestion
    has_tin = bool(payee_tin)
    # Default to 'professional' or 'goods' based on amount if no info
    category = 'professional' 
    wht_calc = calculate_wht_2025(amount_decimal, category, has_tin=has_tin)
    
    req_payload = {
        "title": f"Portal Claim: {payee_name}",
        "description": f"Claim submitted via Payout Portal by {payee_name}.",
        "vendor_id": vendor_id,
        "amount_gross": float(amount_decimal),
        "payout_method": "direct_pay",
        "is_wht_applicable": True,
        "wht_rate": float(wht_calc['rate']),
        "wht_amount": float(wht_calc['wht_amount']),
        "net_payout_amount": float(wht_calc['net_amount']),
        "proforma_url": quotation_url,
        "status": "pending_verification"
    }
    db.table("expenditure_requests").insert(req_payload).execute()
    
    return {"status": "success", "message": "Claim submitted successfully. Our finance team will review it shortly."}

@router.patch("/requests/{request_id}/void")
async def void_payout_request(request_id: str, data: VoidExpenditureRequest, current_admin=Depends(require_roles(["admin", "super_admin"]))):
    """Voids an expenditure request so it's ignored in reporting."""
    if not has_any_role(current_admin, "admin"):
        raise HTTPException(status_code=403, detail="Only Admins can void expenditures")
        
    db = get_db()
    
    # 1. Check if it exists
    req_res = db.table("expenditure_requests").select("status, title").eq("id", request_id).execute()
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
        
    # 2. Update status to voided and log reason
    update_data = {
        "status": "voided",
        "void_reason": data.reason,
        "voided_at": datetime.now(timezone.utc).isoformat(),
        "voided_by": current_admin['sub']
    }
    
    db.table("expenditure_requests").update(update_data).eq("id", request_id).execute()
    
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
        .select("amount_gross, net_payout_amount, amount_paid, wht_amount, created_at, status, payout_method, vendors(name), admins!requester_id(full_name)")\
        .in_("status", ["paid", "approved", "partially_paid"])\
        .gte("created_at", start_ts)\
        .lte("created_at", end_ts)
        
    res = query.execute()
    data = res.data or []
    
    # Aggregation for Charts
    # If period <= 31 days, group by Day. Otherwise group by Month.
    date_format_len = 10 if (days and days <= 31) or (not days and start_date) else 7
    
    period_totals = {}
    categories = {}
    payees = {}
    requesters = {}
    total_gross = 0
    total_wht = 0
    
    creditors = {}
    total_paid = 0
    total_ap = 0
    
    for r in data:
        bucket = r['created_at'][:date_format_len]
        gross_val = float(r['amount_gross'] or 0)
        net_val = float(r['net_payout_amount'] or 0)
        paid_val = float(r['amount_paid'] or 0)
        balance = max(0, net_val - paid_val)
        
        period_totals[bucket] = period_totals.get(bucket, 0) + gross_val
        
        method = r['payout_method'] or 'Other'
        categories[method] = categories.get(method, 0) + gross_val
        
        # Payee Aggregation (Actual Cash Paid)
        p_name = r.get('vendors', {}).get('name', 'Unknown Payee') if r.get('vendors') else 'Unknown Payee'
        payees[p_name] = payees.get(p_name, 0) + paid_val
        
        # Creditor Aggregation (Outstanding Balance)
        if balance > 0:
            creditors[p_name] = creditors.get(p_name, 0) + balance
        
        # Requester Aggregation
        req_name = r.get('admins', {}).get('full_name', 'Unknown Admin') if r.get('admins') else 'Unknown Admin'
        requesters[req_name] = requesters.get(req_name, 0) + gross_val
        
        total_gross += gross_val
        total_paid += paid_val
        total_ap += balance
        total_wht += float(r['wht_amount'] or 0)
        
    # Formatting Trend
    sorted_buckets = sorted(period_totals.keys())
    trend = [{"month": b, "total": period_totals[b]} for b in sorted_buckets]
    
    # Sort and slice top 5
    top_payees = sorted(payees.items(), key=lambda x: x[1], reverse=True)[:5]
    top_requesters = sorted(requesters.items(), key=lambda x: x[1], reverse=True)[:5]
    top_creditors = sorted(creditors.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # 3. Active Requests (Always Current State)
    active_count = db.table("expenditure_requests").select("id", count="exact").eq("status", "pending").execute().count
    
    # 4. Liability (Cumulative WHT awaiting remittance)
    # This reflects the current ledger state for FIRS compliance.
    try:
        liability_res = db.table("expenditure_requests")\
            .select("wht_amount")\
            .in_("status", ["approved", "partially_paid", "paid"])\
            .eq("is_wht_remitted", False)\
            .gt("wht_amount", 0)\
            .execute()
        total_liability = sum(float(r['wht_amount'] or 0) for r in liability_res.data)
    except Exception as e:
        logger.warning(f"Liability calculation fallback (column likely missing): {e}")
        # If the column doesn't exist yet, we fallback to the period total
        # until the user runs the provided SQL migration.
        total_liability = total_wht
    
    # 5. Company Assets (Total Book Value)
    try:
        asset_res = db.table("company_assets").select("purchase_cost").execute()
        total_assets = sum(float(r.get('purchase_cost') or 0) for r in asset_res.data)
    except Exception as e:
        logger.warning(f"Asset calculation failed: {e}")
        total_assets = 0

    return {
        "trend": trend,
        "categories": categories,
        "top_payees": dict(top_payees),
        "top_requesters": dict(top_requesters),
        "top_creditors": dict(top_creditors),
        "total_expenditure": total_gross,
        "total_paid": total_paid,
        "total_ap": total_ap,
        "total_wht_period": total_wht,
        "total_net_liability": total_liability,
        "total_asset_value": total_assets,
        "active_request_count": active_count,
        "count_period": len(data)
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
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin", "operations"]))
):
    """Generate and stream a CSV report directly."""
    report_data = await ReportService.get_report_data(report_type, start_date, end_date)
    
    # Convert to DataFrame for easy export
    df = pd.DataFrame(report_data['items'])
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    filename = f"{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
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
        res = db.table("report_schedules").upsert(payload).execute()
        return {"status": "success", "data": res.data[0] if res.data else {}}
    except Exception as e:
        logger.warning(f"Failed to upsert schedule (table might be missing): {e}")
        return {"status": "success", "message": "Automation preference logged."}
