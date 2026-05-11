# ══════════════════════════════════════════════════════════════════════════
# procurement_submissions.py  —  Add to routers/ directory
#
# Endpoints:
#   POST   /api/payouts/procurement-submissions        (portal → submit)
#   GET    /api/payouts/procurement-submissions        (dashboard → list)
#   GET    /api/payouts/procurement-submissions/{id}   (dashboard → detail)
#   PATCH  /api/payouts/procurement-submissions/{id}   (dashboard → approve/reject/pay)
#
# When a submission is APPROVED, line items are automatically fanned out
# into procurement_expenses so they appear in the existing dashboard analytics.
# ══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from database import get_db, db_execute
from routers.auth import require_roles, resolve_admin_token
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import logging
import os
import mimetypes
from storage_service import upload_portal_file, generate_signed_url
from email_service import (
    send_procurement_invite_email,
    send_procurement_received_email,
    send_procurement_approval_email,
    send_procurement_rejection_email
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Pydantic models ───────────────────────────────────────────────────────

class LineItem(BaseModel):
    description: str
    category: Optional[str] = "General"
    qty: Optional[float] = 1
    unit: Optional[str] = "Pcs"
    unitPrice: Optional[float] = 0
    amount: Optional[float] = 0


class ProcurementSubmissionCreate(BaseModel):
    """
    Posted by the vendor-facing Procurement Portal.
    All vendor and bank details are snapshot-copied so audit history
    is preserved even if the vendor record is later changed.
    """
    ref: str                          # e.g. PCQ-ABC123 (generated client-side)
    title: str
    project: Optional[str] = None    # project key e.g. 'green-hills'
    projectName: Optional[str] = None

    # Vendor identity
    vendor_name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    rc_number: Optional[str] = None
    tin: Optional[str] = None

    # Bank
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None

    # Financials
    total_amount: float
    notes: Optional[str] = None
    line_items: List[LineItem] = []
    attachments: Optional[List[str]] = []


class SubmissionStatusUpdate(BaseModel):
    status: str                           # approved | rejected | paid
    rejection_reason: Optional[str] = None
    pay_reference: Optional[str] = None


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


# ── Helper: resolve project linkage ──────────────────────────────────────

async def resolve_project(project_key: Optional[str], db) -> dict:
    """
    Given a project key (e.g. 'green-hills'), try to find a matching
    estate_draft or property to populate property_id / estate_draft_id.
    Returns a dict with whichever fields were resolved.
    """
    if not project_key:
        return {}

    result = {}

    # 1. Try estate_drafts first (pre-launch)
    try:
        drafts = await db_execute(
            lambda: db.table("estate_drafts")
            .select("id, name")
            .ilike("name", f"%{project_key.replace('-', ' ')}%")
            .limit(1)
            .execute()
        )
        if drafts.data:
            result["estate_draft_id"] = drafts.data[0]["id"]
            return result
    except Exception:
        pass

    # 2. Try properties (live estates)
    try:
        props = await db_execute(
            lambda: db.table("properties")
            .select("id, name")
            .ilike("name", f"%{project_key.replace('-', ' ')}%")
            .limit(1)
            .execute()
        )
        if props.data:
            result["property_id"] = props.data[0]["id"]
    except Exception:
        pass

    return result


# ── Helper: find or create vendor ────────────────────────────────────────

async def get_or_create_vendor(data: ProcurementSubmissionCreate, db) -> Optional[str]:
    """
    Look up an existing vendor by name (case-insensitive).
    If not found, create a new one. Returns the vendor UUID.
    """
    if not data.vendor_name:
        return None

    try:
        existing = await db_execute(
            lambda: db.table("vendors")
            .select("id")
            .ilike("name", data.vendor_name.strip())
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]["id"]

        # Create new vendor
        vendor_payload = {
            "name": data.vendor_name.strip(),
            "type": "company",
            "rc_number": data.rc_number or None,
            "tin": data.tin or None,
            "email": data.email or None,
            "phone": data.phone or None,
            "bank_name": data.bank_name or None,
            "account_number": data.account_number or None,
            "account_name": data.account_name or None,
        }
        created = await db_execute(
            lambda: db.table("vendors").insert(vendor_payload).execute()
        )
        if created.data:
            return created.data[0]["id"]
    except Exception as e:
        logger.warning(f"Vendor lookup/create failed: {e}")

    return None


# ── Helper: fan out to procurement_expenses ───────────────────────────────

async def fan_out_to_expenses(submission: dict, admin_id: str, db):
    """
    When a submission is approved, write each line item into
    procurement_expenses so the existing dashboard analytics pick them up.
    """
    line_items = submission.get("line_items") or []
    if not line_items:
        return

    records = []
    expense_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for item in line_items:
        amount = float(item.get("amount") or 0)
        if amount <= 0:
            continue
        records.append({
            "title": item.get("description") or item.get("title") or "—",
            "category": item.get("category") or "General",
            "amount": amount,
            "amount_paid": 0,
            "status": "pending",
            "budget": amount,
            "vendor_name": submission.get("vendor_name"),
            "vendor_id": submission.get("vendor_id"),
            "property_id": submission.get("property_id"),
            "estate_draft_id": submission.get("estate_draft_id"),
            "expense_date": expense_date,
            "notes": f"From submission {submission.get('ref')}",
            "metadata": {
                "procurement_ref": submission.get("ref"),
                "qty": item.get("qty"),
                "unit": item.get("unit"),
                "unit_price": item.get("unitPrice"),
                "bank": submission.get("bank_name"),
                "account": submission.get("account_number"),
            },
            "created_by": admin_id,
        })

    if records:
        try:
            await db_execute(
                lambda: db.table("procurement_expenses").insert(records).execute()
            )
            logger.info(f"Fanned out {len(records)} expense records for submission {submission.get('ref')}")
        except Exception as e:
            logger.error(f"Fan-out to procurement_expenses failed: {e}")


# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

# ── POST /procurement-submissions  (portal → submit) ─────────────────────
@router.post("/procurement-submissions")
async def create_procurement_submission(data: ProcurementSubmissionCreate):
    """
    Public-ish endpoint called by the Procurement Portal.
    No admin auth required — vendors don't have admin tokens.
    We validate the ref is unique and store the snapshot.
    """
    db = get_db()

    # Check ref uniqueness
    existing = await db_execute(
        lambda: db.table("procurement_submissions")
        .select("id")
        .eq("ref", data.ref)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Submission reference already exists.")

    # Resolve project linkage
    project_links = await resolve_project(data.project or data.projectName, db)

    # Find/create vendor
    vendor_id = await get_or_create_vendor(data, db)

    payload = {
        "ref": data.ref,
        "title": data.title,
        "status": "pending",
        "vendor_id": vendor_id,
        "vendor_name": data.vendor_name,
        "contact_name": data.contact_name,
        "phone": data.phone,
        "email": data.email,
        "rc_number": data.rc_number,
        "tin": data.tin,
        "bank_name": data.bank_name,
        "account_number": data.account_number,
        "account_name": data.account_name,
        "total_amount": float(data.total_amount),
        "notes": data.notes,
        "line_items": [item.dict() for item in data.line_items],
        "attachments": data.attachments or [],
        **project_links,
    }

    res = await db_execute(
        lambda: db.table("procurement_submissions").insert(payload).execute()
    )
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to save submission.")

    submission = res.data[0]
    
    # ── Send Receipt Email ────────────────────────────────────────────────
    try:
        await send_procurement_received_email(
            email_addr=submission.get("email"),
            vendor_name=submission.get("vendor_name"),
            submission_ref=submission.get("ref"),
            project_name=submission.get("projectName") or submission.get("project") or "Eximp & Cloves Project",
            total_amount=submission.get("total_amount")
        )
    except Exception as e:
        logger.error(f"Failed to send submission receipt email: {e}")

    return submission


# ── GET /procurement-submissions  (dashboard → list) ─────────────────────
@router.get("/procurement-submissions")
async def list_procurement_submissions(
    status: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    db = get_db()
    query = db.table("procurement_submissions").select("*")
    if status:
        query = query.eq("status", status)
    res = await db_execute(lambda: query.order("submitted_at", desc=True).execute())
    return res.data


# ── GET /procurement-submissions/{id}  (dashboard → detail) ──────────────
@router.get("/procurement-submissions/{submission_id}")
async def get_procurement_submission(
    submission_id: str,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    db = get_db()
    query = db.table("procurement_submissions").select("*")
    
    if is_valid_uuid(submission_id):
        query = query.eq("id", submission_id)
    else:
        query = query.eq("ref", submission_id)
        
    res = await db_execute(lambda: query.single().execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return res.data


# ── PATCH /procurement-submissions/{id}  (dashboard → approve/reject/pay) ─
@router.patch("/procurement-submissions/{submission_id}")
async def update_procurement_submission(
    submission_id: str,
    data: SubmissionStatusUpdate,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    db = get_db()

    allowed = {"pending", "approved", "rejected", "paid"}
    if data.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {allowed}")

    # Fetch current submission
    query = db.table("procurement_submissions").select("*")
    if is_valid_uuid(submission_id):
        query = query.eq("id", submission_id)
    else:
        query = query.eq("ref", submission_id)

    existing_res = await db_execute(lambda: query.single().execute())
    if not existing_res.data:
        raise HTTPException(status_code=404, detail="Submission not found.")

    submission = existing_res.data

    update_payload = {
        "status": data.status,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": current_admin["sub"],
    }
    if data.rejection_reason:
        update_payload["rejection_reason"] = data.rejection_reason
    if data.pay_reference:
        update_payload["pay_reference"] = data.pay_reference

    update_query = db.table("procurement_submissions").update(update_payload)
    if is_valid_uuid(submission_id):
        update_query = update_query.eq("id", submission_id)
    else:
        update_query = update_query.eq("ref", submission_id)

    res = await db_execute(lambda: update_query.execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to update submission.")

    updated = res.data[0]

    # ── Fan out to procurement_expenses on approval ───────────────────────
    if data.status == "approved":
        await fan_out_to_expenses(updated, current_admin["sub"], db)
        
        # ── Send Approval Email ───────────────────────────────────────────
        try:
            await send_procurement_approval_email(
                email_addr=updated.get("email"),
                vendor_name=updated.get("vendor_name"),
                submission_ref=updated.get("ref"),
                project_name=updated.get("projectName") or updated.get("project") or "the project",
                total_amount=updated.get("total_amount"),
                pay_ref=updated.get("pay_reference") or ""
            )
        except Exception as e:
            logger.error(f"Failed to send approval email: {e}")

    elif data.status == "rejected":
        # ── Send Rejection Email ──────────────────────────────────────────
        try:
            await send_procurement_rejection_email(
                email_addr=updated.get("email"),
                vendor_name=updated.get("vendor_name"),
                submission_ref=updated.get("ref"),
                project_name=updated.get("projectName") or updated.get("project") or "the project",
                reason=data.rejection_reason or "Your quotation did not meet our current requirements."
            )
        except Exception as e:
            logger.error(f"Failed to send rejection email: {e}")

    return updated


# ══════════════════════════════════════════════════════════════════════════
# PROCUREMENT INVITES & VENDOR LOOKUP
# ══════════════════════════════════════════════════════════════════════════


class ProcurementInviteCreate(BaseModel):
    """Admin creates an invitation to send to a vendor"""
    vendor_email: str
    vendor_id: Optional[str] = None
    project: Optional[str] = None
    message: Optional[str] = None


# ── POST /procurement-invites  (admin → generate invite link) ──────────────
@router.post("/procurement-invites")
async def create_procurement_invite(
    data: ProcurementInviteCreate,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    """
    Admin generates a unique invite token for a vendor.
    The vendor receives an email with a link like:
    /procurement/portal?token={token}
    """
    db = get_db()
    
    token = str(uuid.uuid4())
    
    # Store in DB with 30-day expiry
    invite_payload = {
        "token": token,
        "vendor_email": data.vendor_email.lower(),
        "vendor_id": data.vendor_id or None,
        "project": data.project or None,
        "message": data.message or None,
        "created_by": current_admin["sub"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "status": "pending"  # pending | accepted | expired
    }
    
    res = await db_execute(
        lambda: db.table("procurement_invites").insert(invite_payload).execute()
    )
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create invite")
    
    invite = res.data[0]
    base_url = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com").rstrip("/")
    invite_url = f"{base_url}/procurement/portal?token={token}"
    
    # ── Send Invitation Email ─────────────────────────────────────────────
    try:
        # Get admin name for branding
        admin_name = "The Procurement Team"
        try:
            admin_res = await db_execute(lambda: db.table("staff_profiles").select("full_name").eq("id", current_admin["sub"]).single().execute())
            if admin_res.data:
                admin_name = admin_res.data["full_name"]
        except: pass

        await send_procurement_invite_email(
            email_addr=data.vendor_email,
            admin_name=admin_name,
            invite_url=invite_url,
            project_name=data.project or ""
        )
    except Exception as e:
        logger.error(f"Failed to send procurement invite email: {e}")
    
    return {
        "status": "success",
        "token": token,
        "invite_url": invite_url,
        "email": data.vendor_email,
        "created_at": invite_payload["created_at"],
        "expires_at": invite_payload["expires_at"]
    }


# ── GET /procurement-invites  (admin → list pending invites) ───────────────
@router.get("/procurement-invites")
async def list_procurement_invites(
    status: Optional[str] = None,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    """
    List all procurement invites. Can filter by status (pending, accepted, expired).
    """
    db = get_db()
    query = db.table("procurement_invites").select("*")
    
    if status:
        query = query.eq("status", status)
    
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return res.data or []


# ── GET /procurement-portal/invite/{token}  (public → check invite & pre-fill) ─
@router.get("/procurement-portal/invite/{token}")
async def check_procurement_invitation(token: str):
    """
    Public endpoint (no auth required).
    Vendor clicks invite link → frontend calls this to:
    1. Validate the token is not expired
    2. Return vendor email (pre-filled, read-only)
    3. Return vendor data if already in system (auto-fill form)
    """
    db = get_db()
    
    # 1. Find and validate invite
    invite_res = await db_execute(
        lambda: db.table("procurement_invites")
        .select("*")
        .eq("token", token)
        .single()
        .execute()
    )
    
    if not invite_res.data:
        raise HTTPException(status_code=404, detail="Invitation not found or invalid")
    
    invite = invite_res.data
    
    # 2. Check if expired
    expires_at = datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired")
    
    # 3. Try to find existing vendor by email
    vendor = None
    try:
        vendor_res = await db_execute(
            lambda: db.table("vendors")
            .select("*")
            .ilike("email", invite["vendor_email"])
            .limit(1)
            .execute()
        )
        if vendor_res.data:
            vendor = vendor_res.data[0]
    except Exception as e:
        logger.warning(f"Vendor lookup failed: {e}")
    
    return {
        "status": "success",
        "email": invite["vendor_email"],  # Pre-filled, read-only in portal
        "project": invite.get("project"),
        "message": invite.get("message"),
        "vendor": {
            "id": vendor["id"],
            "name": vendor.get("name"),
            "phone": vendor.get("phone"),
            "rc_number": vendor.get("rc_number"),
            "tin": vendor.get("tin"),
            "bank_name": vendor.get("bank_name"),
            "account_number": vendor.get("account_number"),
            "account_name": vendor.get("account_name"),
        } if vendor else None
    }


# ── GET /portal/fetch-vendor  (public → lookup vendor by email) ────────────
@router.get("/portal/fetch-vendor")
async def fetch_vendor_by_email(email: str = Query(...)):
    """
    Public endpoint (no auth required).
    Used by both payout and procurement portals for email lookup.
    When vendor enters their email and clicks "Identify", this fetches their data.
    """
    db = get_db()
    
    email = email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    try:
        vendor_res = await db_execute(
            lambda: db.table("vendors")
            .select("*")
            .ilike("email", email)
            .limit(1)
            .execute()
        )
        
        if vendor_res.data:
            v = vendor_res.data[0]
            return {
                "status": "success",
                "data": {
                    "id": v.get("id"),
                    "name": v.get("name"),
                    "phone": v.get("phone"),
                    "rc_number": v.get("rc_number"),
                    "tin": v.get("tin"),
                    "bank_name": v.get("bank_name"),
                    "account_number": v.get("account_number"),
                    "account_name": v.get("account_name"),
                    "email": v.get("email"),
                }
            }
        else:
            return {
                "status": "not_found",
                "data": None
            }
    except Exception as e:
        logger.error(f"Error fetching vendor: {e}")
        raise HTTPException(status_code=500, detail="Error looking up vendor")


# ── GET /procurement-portal/submissions  (public → list submissions for vendor) ─
@router.get("/procurement-portal/submissions")
async def list_vendor_submissions(email: str = Query(...)):
    """
    Public endpoint for the Procurement Portal to fetch submissions for a vendor email.
    """
    db = get_db()
    email = email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    try:
        res = await db_execute(
            lambda: db.table("procurement_submissions")
            .select("*")
            .ilike("email", email)
            .order("submitted_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error(f"Error fetching vendor submissions: {e}")
        raise HTTPException(status_code=500, detail="Error loading submissions")


# ── GET /procurement-portal/projects (public → list projects) ────────────
@router.get("/procurement-portal/projects")
async def get_procurement_projects():
    """
    Public endpoint to fetch active projects (properties and estate drafts)
    for the procurement portal selection.
    """
    db = get_db()
    try:
        # 1. Fetch properties
        props_res = await db_execute(lambda: db.table("properties")
            .select("id, name, estate_name, is_archived")
            .order("name")
            .execute())
        
        # 2. Fetch estate drafts (only unpublished)
        drafts_res = await db_execute(lambda: db.table("estate_drafts")
            .select("id, name")
            .eq("is_public", False)
            .order("name")
            .execute())
            
        projects = []
        seen_estates = set()
        
        # Combine properties (Deduplicate by base estate name)
        for p in (props_res.data or []):
            p_name = p.get("name") or ""
            estate_name = p.get("estate_name")
            
            # Fallback parsing if estate_name is not set
            if not estate_name and p_name:
                estate_name = p_name.split(" - ")[0]
                for suffix in [" (Outright)", " (Installment)", " (Outright Payment)", " (Installment Payment)"]:
                    if suffix in estate_name:
                        estate_name = estate_name.split(suffix)[0]
                        break
            
            if estate_name and estate_name not in seen_estates:
                seen_estates.add(estate_name)
                display_name = estate_name
                if p.get("is_archived"):
                    display_name += " (Private/Archived)"
                projects.append({"id": p["id"], "name": display_name, "type": "property"})
            
        # Combine drafts (Avoid duplicates if somehow name matches a property)
        for d in (drafts_res.data or []):
            d_name = d.get("name")
            if d_name and d_name not in seen_estates:
                seen_estates.add(d_name)
                projects.append({"id": d["id"], "name": f"{d_name} (Draft)", "type": "draft"})
            
        # Add "Other" as a fallback
        projects.append({"id": "other", "name": "Other / Admin", "type": "other"})
        
        return {"status": "success", "data": projects}
    except Exception as e:
        logger.error(f"Error fetching projects: {e}")
        return {"status": "error", "message": "Failed to load project list"}


# ── POST /procurement-portal/upload  (public → upload attachment) ──────────
@router.post("/procurement-portal/upload")
async def upload_procurement_attachment(file: UploadFile = File(...)):
    """
    Public endpoint for vendors to upload supporting documents.
    Returns the storage path.
    """
    try:
        # 1. Read file bytes
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")

        # 2. Generate unique filename
        ext = mimetypes.guess_extension(file.content_type) or ".bin"
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{unique_id}{ext}"
        storage_path = f"procurement_attachments/{filename}"

        # 3. Upload to storage
        success = upload_portal_file(storage_path, file_bytes, file.content_type)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")

        return {
            "status": "success",
            "path": storage_path,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Procurement upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))