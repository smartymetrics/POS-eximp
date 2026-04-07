from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel
from database import get_db
from models import ExpenditureRequestCreate, PayoutReview, AssetCreate, VendorCreate
from routers.auth import verify_token, has_any_role
from email_service import send_payout_receipt_email, send_portal_invite_email
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import json
import uuid

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
        "requester_id": current_admin['id'],
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
async def list_expenditure_requests(status: Optional[str] = None, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("expenditure_requests").select("*, vendors(*), admins!requester_id(full_name)")
    if status:
        query = query.eq("status", status)
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
        "reviewed_by": current_admin['id'],
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

    # TRIGGER AUTOMATED RECEIPT EMAIL
    if data.status == 'approved' and updated_req.get('vendor_id'):
        vendor = req.get('vendors')
        if vendor and vendor.get('email'):
            # Fetch fresh version of request for the receipt (includes updated WHT/amounts)
            bg_tasks.add_task(send_payout_receipt_email, updated_req, vendor, current_admin['full_name'])

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

@router.post("/requests/portal-invite")
async def trigger_portal_invite(data: PortalInvite, bg_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    """Triggers a professional system email invitation to a partner."""
    bg_tasks.add_task(send_portal_invite_email, data.email, current_admin['full_name'])
    return {"status": "success", "message": f"Invitation queued for {data.email}"}


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
