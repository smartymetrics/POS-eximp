from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database import get_db
from models import ExpenditureRequestCreate, PayoutReview, AssetCreate, VendorCreate, VoidExpenditureRequest
from routers.auth import verify_token, has_any_role
from email_service import send_payout_receipt_email, send_portal_invite_email, send_report_email
from report_service import ReportService
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json
import uuid
import pandas as pd
import io

router = APIRouter()

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

# ─── VENDORS ──────────────────────────────────────────────────
@router.post("/vendors")
async def create_vendor(data: VendorCreate, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("vendors").insert(data.dict()).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create vendor")
    return res.data[0]

@router.get("/vendors")
async def list_vendors(type: Optional[str] = None, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("vendors").select("*")
    if type:
        query = query.eq("type", type)
    res = query.order("name").execute()
    return res.data

# ─── EXPENDITURE REQUESTS ─────────────────────────────────────
@router.post("/requests")
async def submit_payout_request(data: ExpenditureRequestCreate, current_admin=Depends(verify_token)):
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
        "status": "pending"
    }
    
    res = db.table("expenditure_requests").insert(payload).execute()
    return res.data[0]

@router.get("/requests")
async def list_expenditure_requests(status: Optional[str] = None, show_voided: bool = False, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("expenditure_requests").select("*, vendors(*), admins!requester_id(full_name)")
    
    if status:
        query = query.eq("status", status)
    
    if not show_voided:
        query = query.neq("status", "voided")
        
    res = query.order("created_at", desc=True).execute()
    return res.data

@router.put("/requests/{request_id}/review")
async def review_payout_request(request_id: str, data: PayoutReview, bg_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
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
            # Fetch admin profile for the "Sent By" name
            admin_res = db.table("admins").select("full_name").eq("id", current_admin['sub']).execute()
            admin_name = admin_res.data[0]['full_name'] if admin_res.data else "Finance Team"
            
            # Fetch fresh version of request for the receipt (includes updated WHT/amounts)
            bg_tasks.add_task(send_payout_receipt_email, updated_req, vendor, admin_name)

    return updated_req

# ─── ASSETS ───────────────────────────────────────────────────
@router.post("/assets")
async def record_company_asset(data: AssetCreate, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("company_assets").insert(data.dict()).execute()
    return res.data[0]

@router.get("/assets")
async def list_assets(assigned_to: Optional[str] = None, current_admin=Depends(verify_token)):
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
async def view_secure_payout_document(request_id: str, doc_type: str, current_admin=Depends(verify_token)):
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
        raise HTTPException(status_code=404, detail="Document path not found for this request")
        
    # Redirect to external URLs directly
    if path.startswith("http"):
        return RedirectResponse(url=path)
        
    # Generate signed URL for private Supabase bucket 'expenditures'
    signed_url = generate_signed_url("expenditures", path)
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate secure access link")
        
    return RedirectResponse(url=signed_url)


# ─── PORTAL AUTOMATION ────────────────────────────────────────

class PortalInvite(BaseModel):
    email: str
    category: str # 'staff', 'company', or 'individual'

@router.post("/requests/portal-invite")
async def trigger_portal_invite(data: PortalInvite, bg_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
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
    
    bg_tasks.add_task(send_portal_invite_email, data.email, admin_name)
    
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
        db.storage.from_("expenditures").upload(file_path, content)
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
        "status": "pending"
    }
    
    db.table("expenditure_requests").insert(req_payload).execute()
    
    return {"status": "success", "message": "Claim submitted successfully. Our finance team will review it shortly."}


@router.patch("/requests/{request_id}/void")
async def void_payout_request(request_id: str, data: VoidExpenditureRequest, current_admin=Depends(verify_token)):
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
    from routers.analytics import log_activity
    await log_activity(
        "expenditure_voided",
        f"Expenditure request '{req_res.data[0]['title']}' voided by Admin. Reason: {data.reason}",
        current_admin['sub'],
        metadata={"request_id": request_id}
    )
    
    return {"status": "success", "message": "Expenditure request voided successfully"}


# ─── ANALYTICS & REPORTING ───────────────────────────────────

@router.get("/stats/summary")
async def get_payout_stats(current_admin=Depends(verify_token)):
    """Aggregated stats for the dashboard charts."""
    db = get_db()
    
    # 1. Monthly Spend Trend (Last 6 Months)
    res = db.table("expenditure_requests")\
        .select("amount_gross, net_payout_amount, wht_amount, created_at, status")\
        .eq("status", "paid")\
        .execute()
        
    data = res.data or []
    
    # Simple aggregation for Chart.js
    monthly_totals = {}
    for r in data:
        month = r['created_at'][:7] # YYYY-MM
        monthly_totals[month] = monthly_totals.get(month, 0) + float(r['amount_gross'])
        
    sorted_months = sorted(monthly_totals.keys())[-6:]
    trend = [{"month": m, "total": monthly_totals[m]} for m in sorted_months]
    
    # 2. Category Breakdown
    cat_res = db.table("expenditure_requests")\
        .select("amount_gross, payout_method")\
        .eq("status", "paid")\
        .execute()
        
    cat_data = cat_res.data or []
    categories = {}
    for r in cat_data:
        m = r['payout_method'] or 'Unknown'
        categories[m] = categories.get(m, 0) + float(r['amount_gross'])
        
    # 3. Liability Summary
    liability = sum(float(r['wht_amount'] or 0) for r in data)
    
    return {
        "trend": trend,
        "categories": categories,
        "total_wht_liability": liability,
        "total_payout_count": len(data)
    }

@router.get("/stats/export")
async def export_payout_report(
    report_type: str = "payout_audit",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(verify_token)
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

class SendReportRequest(BaseModel):
    report_type: str
    email: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.post("/stats/send-email")
async def send_on_demand_report(
    data: SendReportRequest, 
    bg_tasks: BackgroundTasks, 
    current_admin=Depends(verify_token)
):
    """Triggers an immediate report email via background task."""
    bg_tasks.add_task(send_report_email, data.report_type, [data.email], data.start_date, data.end_date)
    return {"status": "success", "message": f"Report queued for delivery to {data.email}"}

class ScheduleRequest(BaseModel):
    report_type: str
    frequency: str # weekly, monthly
    recipients: List[str]
    is_active: bool = True

@router.post("/stats/schedule")
async def save_report_schedule(data: ScheduleRequest, current_admin=Depends(verify_token)):
    """Saves or updates a report schedule."""
    db = get_db()
    payload = {
        "report_type": data.report_type,
        "frequency": data.frequency,
        "recipients": data.recipients,
        "is_active": data.is_active,
        "owner_id": current_admin['sub']
    }
    
    # Basic upsert logic
    res = db.table("report_schedules").upsert(payload).execute()
    return res.data[0]
