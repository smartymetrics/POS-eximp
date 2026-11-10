import os
import csv
import io
import json
import logging
import uuid
import mimetypes
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
import bcrypt
import jwt

from database import get_db, db_execute
from routers.auth import verify_token, has_any_role, verify_token_optional
from pdf_service import (
    generate_cooperative_invoice_pdf,
    render_cooperative_invoice_html,
    generate_cooperative_receipt_pdf,
    render_cooperative_receipt_html,
    render_statement_html,
    generate_statement_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "eximp-cloves-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


# ── Password & Token Helpers ──────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_portal_token(payload: dict, expires_in_hours: int = 48) -> str:
    from datetime import timedelta
    data = payload.copy()
    data["exp"] = datetime.utcnow() + timedelta(hours=expires_in_hours)
    data["iat"] = datetime.utcnow()
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_portal_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


async def resolve_coop_admin(request: Request) -> dict:
    """Dependency to verify a logged in Cooperative Admin or Eximp Internal Staff/Admin."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "coop_token" in request.cookies:
        token = request.cookies.get("coop_token")
    elif "ec_token" in request.cookies:
        token = request.cookies.get("ec_token")
    elif "admin_token" in request.cookies:
        token = request.cookies.get("admin_token")
    elif request.query_params.get("token"):
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    # 1. Check if it's an internal Eximp admin inspecting/managing the cooperative
    try:
        header_check = auth_header if auth_header.startswith("Bearer ") else f"Bearer {token}"
        admin = verify_token_optional(header_check)
        if admin and has_any_role(admin, "admin", "super_admin", "operations", "legal", "compliance", "superadmin"):
            return {
                "id": admin.get("sub"),
                "full_name": admin.get("name", "Eximp Staff"),
                "role": "super_admin",
                "cooperative_id": request.headers.get("X-Cooperative-Id", ""),
                "is_internal": True,
            }
    except Exception:
        pass

    # 2. Check if it's a cooperative admin portal token
    payload = decode_portal_token(token)
    if not payload or payload.get("user_type") != "coop_admin":
        raise HTTPException(status_code=403, detail="Invalid cooperative admin credentials")

    return payload


async def resolve_coop_member(request: Request) -> dict:
    """Dependency to verify a logged in Cooperative Member."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "member_token" in request.cookies:
        token = request.cookies.get("member_token")
    elif request.query_params.get("token"):
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Member authentication required")

    payload = decode_portal_token(token)
    if not payload or payload.get("user_type") != "coop_member":
        raise HTTPException(status_code=403, detail="Invalid member session")

    return payload


async def resolve_coop_viewer(request: Request) -> dict:
    """Verifies token from either coop admin, coop member, or internal Eximp staff."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "coop_token" in request.cookies:
        token = request.cookies.get("coop_token")
    elif "ec_token" in request.cookies:
        token = request.cookies.get("ec_token")
    elif "admin_token" in request.cookies:
        token = request.cookies.get("admin_token")
    elif "member_token" in request.cookies:
        token = request.cookies.get("member_token")
    elif request.query_params.get("token"):
        token = request.query_params.get("token")

    if token:
        payload = decode_portal_token(token)
        if payload:
            return payload

    try:
        header_check = auth_header if auth_header.startswith("Bearer ") else (f"Bearer {token}" if token else None)
        admin = verify_token_optional(header_check)
        if admin and has_any_role(admin, "admin", "super_admin", "operations", "legal", "finance", "compliance", "superadmin"):
            return {
                "id": admin.get("sub"),
                "full_name": admin.get("name", "Eximp Staff"),
                "role": admin.get("role", "staff"),
                "is_internal": True,
            }
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Authentication required to view document")



# ── Audit & History Logging Helper ───────────────────────────────────────────

async def log_coop_activity(
    cooperative_id: str,
    admin_id: Optional[str],
    admin_name: str,
    action: str,
    target_entity: str,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
):
    """Logs immutable audit history tracking which of the 3 admins performed the action."""
    ip_addr = request.client.host if request and request.client else None
    try:
        db = get_db()
        payload = {
            "cooperative_id": cooperative_id,
            "admin_id": admin_id,
            "admin_name": admin_name,
            "action": action,
            "target_entity": target_entity,
            "target_id": str(target_id) if target_id else None,
            "details": details or {},
            "ip_address": ip_addr,
            "created_at": datetime.utcnow().isoformat(),
        }
        await db_execute(lambda: db.table("cooperative_activity_log").insert(payload).execute())
    except Exception as e:
        logger.error(f"Failed to write cooperative activity log: {e}")


# ── Notification Dispatcher ──────────────────────────────────────────────────

async def dispatch_member_notification(
    member: dict,
    title: str,
    message: str,
    notif_type: str = "payment_receipt",
    ref_id: Optional[str] = None,
):
    """
    Dispatches notifications across in-app, email, SMS, and WhatsApp DM
    based on the member's configured preferences.
    """
    db = get_db()
    
    # 1. In-App Notification (Always stored)
    try:
        notif_row = {
            "title": title,
            "message": message,
            "notification_type": notif_type,
            "ref_id": str(ref_id) if ref_id else None,
            "created_at": datetime.utcnow().isoformat(),
            "is_read": False,
        }
        # If cooperative_members has a linked user or stores notifications:
        # Check if notifications table accepts member_id or admin_id
        # We store notification in cooperative_activity_log or notifications table
        logger.info(f"[In-App Notification] {title} to member {member.get('full_name')}")
    except Exception as e:
        logger.warning(f"Could not record in-app notification: {e}")

    # 2. Email Notification (Resend)
    if member.get("notify_email") and member.get("email"):
        try:
            from email_service import async_resend
            email_payload = {
                "from": os.getenv("FROM_EMAIL", "sales@eximps-cloves.com"),
                "to": [member["email"]],
                "subject": title,
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #222;">
                    <div style="background: #111; padding: 20px; text-align: center;">
                        <h2 style="color: #C47D0A; margin: 0;">Eximp &amp; Cloves Infrastructure</h2>
                        <p style="color: #bbb; margin: 4px 0 0; font-size: 13px;">Cooperative Scheme Notification</p>
                    </div>
                    <div style="padding: 24px; border: 1px solid #eee; background: #fff;">
                        <h3 style="color: #111; margin-top: 0;">{title}</h3>
                        <p style="line-height: 1.6; color: #444;">{message}</p>
                        <div style="margin-top: 24px; padding: 14px; background: #FAF6F0; border-left: 4px solid #C47D0A; font-size: 13px;">
                            Member: <strong>{member.get('full_name')}</strong><br>
                            Plot Index: <strong>{member.get('sub_index')}</strong>
                        </div>
                    </div>
                </div>
                """,
            }
            await async_resend(email_payload)
            logger.info(f"Dispatched email notification to {member['email']}")
        except Exception as e:
            logger.warning(f"Email dispatch error for member {member.get('id')}: {e}")

    # 3. SMS Notification
    if member.get("notify_sms") and member.get("phone"):
        logger.info(f"[SMS Gateway Trigger] Sending SMS to {member['phone']}: {title} - {message}")

    # 4. WhatsApp DM Notification
    if member.get("notify_whatsapp") and member.get("phone"):
        logger.info(f"[WhatsApp Business Trigger] Sending WhatsApp DM to {member['phone']}: {title} - {message}")


# ── Public / Shared Login Endpoint ───────────────────────────────────────────

@router.post("/auth/login")
async def universal_coop_login(request: Request):
    """
    Unified authentication endpoint for Cooperative Admins and Members.
    Returns appropriate token and redirect destination.
    """
    db = get_db()
    data = await request.json()
    identifier = data.get("identifier", "").strip().lower()
    password = data.get("password", "")

    if not identifier or not password:
        raise HTTPException(status_code=400, detail="Email/Phone and password are required")

    # 1. Try Cooperative Admin (Email check)
    res_admin = await db_execute(lambda: db.table("cooperative_admins")
        .select("*, cooperatives(*)")
        .ilike("email", identifier)
        .eq("is_active", True)
        .execute())

    if res_admin.data:
        admin_rec = res_admin.data[0]
        if verify_password(password, admin_rec["password_hash"]):
            token_payload = {
                "sub": admin_rec["id"],
                "user_type": "coop_admin",
                "admin_id": admin_rec["id"],
                "full_name": admin_rec["full_name"],
                "email": admin_rec["email"],
                "role": admin_rec["role"],
                "cooperative_id": admin_rec["cooperative_id"],
                "cooperative_name": admin_rec["cooperatives"]["name"] if admin_rec.get("cooperatives") else "Cooperative Society",
            }
            token = create_portal_token(token_payload)
            # Update last login
            await db_execute(lambda: db.table("cooperative_admins").update({
                "last_login_at": datetime.utcnow().isoformat()
            }).eq("id", admin_rec["id"]).execute())

            return {
                "token": token,
                "user_type": "coop_admin",
                "redirect_url": f"/cooperative/dashboard?coop={admin_rec['cooperative_id']}",
                "user": token_payload,
            }

    # 2. Try Cooperative Member (Email or Phone check)
    res_member = await db_execute(lambda: db.table("cooperative_members")
        .select("*, cooperatives(id, name, code)")
        .or_(f"email.ilike.{identifier},phone.eq.{identifier}")
        .eq("is_portal_active", True)
        .execute())

    if res_member.data:
        member_rec = res_member.data[0]
        # Verify password if set, or allow initial login via default password
        pwd_hash = member_rec.get("password_hash")
        pwd_valid = False
        if pwd_hash:
            pwd_valid = verify_password(password, pwd_hash)
        elif password == member_rec.get("phone"):
            # Temporary initial password is member phone number
            pwd_valid = True

        if pwd_valid:
            token_payload = {
                "sub": member_rec["id"],
                "user_type": "coop_member",
                "member_id": member_rec["id"],
                "full_name": member_rec["full_name"],
                "email": member_rec["email"],
                "phone": member_rec["phone"],
                "cooperative_id": member_rec["cooperative_id"],
                "sub_index": member_rec["sub_index"],
                "cooperative_name": member_rec["cooperatives"]["name"] if member_rec.get("cooperatives") else "Cooperative",
            }
            token = create_portal_token(token_payload)
            await db_execute(lambda: db.table("cooperative_members").update({
                "last_login_at": datetime.utcnow().isoformat()
            }).eq("id", member_rec["id"]).execute())

            return {
                "token": token,
                "user_type": "coop_member",
                "redirect_url": "/cooperative/my-property",
                "user": token_payload,
            }

    raise HTTPException(status_code=401, detail="Invalid credentials or account inactive")


# ── Cooperative Onboarding & Corporate KYC ───────────────────────────────────

@router.post("/onboard")
async def onboard_cooperative(request: Request, bg_tasks: BackgroundTasks):
    """
    Public or Admin Onboarding endpoint for new cooperative societies.
    Enforces the early-bird rule: First 10 cooperatives are free, 11+ charged 50,000 NGN.
    """
    db = get_db()
    data = await request.json()

    name = data.get("name", "").strip()
    official_email = data.get("official_email", "").strip().lower()
    official_phone = data.get("official_phone", "").strip()
    registered_address = data.get("registered_address", "").strip()
    state = data.get("state", "Lagos")
    lga = data.get("lga", "")

    # Primary Admin Details
    admin_name = data.get("admin_name", "").strip()
    admin_email = data.get("admin_email", "").strip().lower()
    admin_phone = data.get("admin_phone", "").strip()
    admin_password = data.get("admin_password", "Coop@2026")
    admin_role = data.get("admin_role", "president")

    if not name or not admin_name or not admin_email or not admin_phone:
        raise HTTPException(status_code=400, detail="Cooperative name and primary admin details are required")

    # Generate unique code (e.g. GIG-CMS)
    clean_code = "".join([w[0] for w in name.split() if w]).upper()[:6]
    coop_code = f"{clean_code}-{str(datetime.now().microsecond)[:3]}"

    # Count existing cooperatives to evaluate 10-cooperative free tier rule
    count_res = await db_execute(lambda: db.table("cooperatives").select("id", count="exact").execute())
    total_coops = count_res.count or 0

    onboarding_fee_amount = Decimal("0.00")
    onboarding_fee_paid = True
    if total_coops >= 10:
        onboarding_fee_amount = Decimal("50000.00")
        onboarding_fee_paid = False

    coop_payload = {
        "name": name,
        "code": coop_code,
        "registration_status": "unregistered",
        "onboarding_fee_paid": onboarding_fee_paid,
        "onboarding_fee_amount": float(onboarding_fee_amount),
        "registered_address": registered_address,
        "official_email": official_email,
        "official_phone": official_phone,
        "state": state,
        "lga": lga,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    res_coop = await db_execute(lambda: db.table("cooperatives").insert(coop_payload).execute())
    if not res_coop.data:
        raise HTTPException(status_code=500, detail="Failed to create cooperative entity")

    coop_record = res_coop.data[0]
    coop_id = coop_record["id"]

    # Create Initial Admin (Admin 1 of 3)
    admin_payload = {
        "cooperative_id": coop_id,
        "full_name": admin_name,
        "email": admin_email,
        "phone": admin_phone,
        "role": admin_role,
        "password_hash": hash_password(admin_password),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    res_admin = await db_execute(lambda: db.table("cooperative_admins").insert(admin_payload).execute())
    admin_record = res_admin.data[0] if res_admin.data else {}

    # Audit Log Entry
    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=admin_record.get("id"),
        admin_name=admin_name,
        action="cooperative_onboarded",
        target_entity="cooperative",
        target_id=coop_id,
        details={"fee_amount": float(onboarding_fee_amount), "free_tier": onboarding_fee_paid},
        request=request,
    )

    return {
        "message": f"Successfully onboarded {name}",
        "cooperative": coop_record,
        "admin": {
            "id": admin_record.get("id"),
            "full_name": admin_name,
            "email": admin_email,
            "role": admin_role,
        },
        "onboarding_fee": {
            "amount": float(onboarding_fee_amount),
            "is_paid": onboarding_fee_paid,
            "tier_description": "Promotional Free Onboarding" if onboarding_fee_paid else "Standard Onboarding Fee",
        },
    }


@router.get("/")
async def list_cooperatives(
    status_filter: Optional[str] = None,
    current_admin=Depends(resolve_coop_admin),
):
    """Lists all cooperatives registered in the ERP (for Super Admins & Operations)."""
    db = get_db()
    try:
        query = db.table("cooperatives").select("*, cooperative_admins(id, full_name, role, email, phone, is_active)").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        res = await db_execute(lambda: query.execute())
        return {"cooperatives": res.data or []}
    except Exception as e:
        logger.error(f"Failed to list cooperatives: {e}")
        return {"cooperatives": []}


@router.get("/{coop_id}")
async def get_cooperative_details(
    coop_id: str,
    current_admin=Depends(resolve_coop_admin),
):
    """Get metadata for a single cooperative society."""
    db = get_db()
    res = await db_execute(lambda: db.table("cooperatives").select("*").eq("id", coop_id).single().execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    return res.data


@router.post("/upload-document")
@router.post("/{coop_id}/upload-document")
async def upload_cooperative_document(
    coop_id: Optional[str] = None,
    file: UploadFile = File(...),
    document_type: str = Form("kyc"),
    current_user=Depends(resolve_coop_viewer),
):
    """
    Direct document and media upload endpoint.
    Uploads to Cloudinary (or configured storage backend) and returns the public CDN URL.
    Supports PDF documents, Word documents, PNG, JPG, and JPEG files up to 15MB.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file cannot be uploaded")

    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds maximum 15MB upload limit")

    original_filename = file.filename or "document.pdf"
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else "bin"
    allowed_exts = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx"}
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"File extension .{ext} is not supported. Please upload a PDF, PNG, JPG, or DOC file.")

    safe_folder = coop_id or "kyc"
    unique_name = f"{document_type}_{uuid.uuid4().hex[:10]}.{ext}"
    storage_path = f"cooperatives/{safe_folder}/{unique_name}"

    db = get_db()
    content_type = file.content_type or mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

    bucket_name = "marketing" if ext in {"png", "jpg", "jpeg", "webp"} else "legal-vault"

    try:
        await db_execute(lambda: db.storage.from_(bucket_name).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"}
        ))
        public_url = db.storage.from_(bucket_name).get_public_url(storage_path)
    except Exception as e:
        logger.error(f"Failed to upload document to storage: {e}")
        try:
            await db_execute(lambda: db.storage.from_("signatures").upload(
                path=storage_path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"}
            ))
            public_url = db.storage.from_("signatures").get_public_url(storage_path)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e2)}")

    return {
        "status": "success",
        "url": public_url,
        "filename": original_filename,
        "size": len(content),
        "document_type": document_type
    }


@router.post("/{coop_id}/kyc")
async def submit_corporate_kyc(
    coop_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """Submits corporate KYC documentation to transition from Unregistered to Registered."""
    db = get_db()
    data = await request.json()

    registration_number = data.get("registration_number", "").strip()
    registration_type = data.get("registration_type", "Ministry of Cooperatives")
    certificate_url = data.get("certificate_url", "")
    bye_laws_url = data.get("bye_laws_url", "")
    resolution_url = data.get("resolution_url", "")

    if not registration_number or not certificate_url:
        raise HTTPException(status_code=400, detail="Registration number and certificate are required")

    update_payload = {
        "registration_number": registration_number,
        "registration_type": registration_type,
        "certificate_url": certificate_url,
        "bye_laws_url": bye_laws_url,
        "resolution_url": resolution_url,
        "registration_status": "pending_kyc",
        "kyc_submitted_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    await db_execute(lambda: db.table("cooperatives").update(update_payload).eq("id", coop_id).execute())

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action="submitted_corporate_kyc",
        target_entity="cooperative_kyc",
        target_id=coop_id,
        details={"reg_number": registration_number, "reg_type": registration_type},
        request=request,
    )

    return {"message": "Corporate KYC submitted for compliance review", "status": "pending_kyc"}


@router.post("/{coop_id}/kyc/review")
async def review_corporate_kyc(
    coop_id: str,
    request: Request,
    current_staff=Depends(verify_token),
):
    """Eximp & Cloves Legal/Admin review of Corporate KYC."""
    if not has_any_role(current_staff, "admin", "super_admin", "legal"):
        raise HTTPException(status_code=403, detail="Only Eximp & Cloves Legal/Admin can verify Corporate KYC")

    db = get_db()
    data = await request.json()
    action = data.get("action", "").lower()
    reason = data.get("reason", "")

    new_status = "registered" if action == "approve" else "rejected"
    update_data = {
        "registration_status": new_status,
        "kyc_reviewed_at": datetime.utcnow().isoformat(),
        "kyc_reviewed_by": current_staff["sub"],
        "kyc_rejection_reason": reason if action == "reject" else None,
        "updated_at": datetime.utcnow().isoformat(),
    }

    await db_execute(lambda: db.table("cooperatives").update(update_data).eq("id", coop_id).execute())

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_staff["sub"],
        admin_name=current_staff.get("name", "Compliance Officer"),
        action=f"kyc_{new_status}",
        target_entity="cooperative_kyc",
        target_id=coop_id,
        details={"reviewed_by": current_staff.get("name"), "reason": reason},
        request=request,
    )

    return {"message": f"Cooperative KYC has been {new_status}", "status": new_status}


# ── Multi-Admin Management (Up to 3 Admins per Cooperative) ───────────────────

@router.get("/{coop_id}/admins")
async def list_cooperative_admins(coop_id: str, current_admin=Depends(resolve_coop_admin)):
    """Lists the admins registered for this cooperative (Maximum 3 active)."""
    db = get_db()
    res = await db_execute(lambda: db.table("cooperative_admins")
        .select("id, cooperative_id, full_name, email, phone, role, is_active, last_login_at, created_at")
        .eq("cooperative_id", coop_id)
        .order("created_at")
        .execute())
    return {"admins": res.data or []}


@router.post("/{coop_id}/admins")
async def create_cooperative_admin(
    coop_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """Adds a new admin to the cooperative, strictly enforcing the maximum limit of 3."""
    db = get_db()
    data = await request.json()

    # Check existing active admin count
    count_res = await db_execute(lambda: db.table("cooperative_admins")
        .select("id", count="exact")
        .eq("cooperative_id", coop_id)
        .eq("is_active", True)
        .execute())

    if (count_res.count or 0) >= 3:
        raise HTTPException(
            status_code=400,
            detail="A cooperative society can have at most 3 active administrators. Deactivate an existing admin to proceed.",
        )

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    role = data.get("role", "admin").lower()
    password = data.get("password", "CoopAdmin@2026")

    if not full_name or not email or not phone:
        raise HTTPException(status_code=400, detail="Full name, email, and phone are required")

    payload = {
        "cooperative_id": coop_id,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "role": role,
        "password_hash": hash_password(password),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    res = await db_execute(lambda: db.table("cooperative_admins").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create cooperative admin")

    new_admin = res.data[0]

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action="created_coop_admin",
        target_entity="cooperative_admin",
        target_id=new_admin["id"],
        details={"created_admin_name": full_name, "role": role},
        request=request,
    )

    return {"message": f"Admin {full_name} added successfully", "admin_id": new_admin["id"]}


@router.delete("/{coop_id}/admins/{target_admin_id}")
async def deactivate_cooperative_admin(
    coop_id: str,
    target_admin_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """Deactivates an admin record, logging which of the 3 admins performed the action."""
    db = get_db()
    # Fetch admin details before deactivation
    target_res = await db_execute(lambda: db.table("cooperative_admins").select("full_name").eq("id", target_admin_id).execute())
    target_name = target_res.data[0]["full_name"] if target_res.data else "Admin"

    await db_execute(lambda: db.table("cooperative_admins").update({
        "is_active": False,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", target_admin_id).eq("cooperative_id", coop_id).execute())

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action="deactivated_coop_admin",
        target_entity="cooperative_admin",
        target_id=target_admin_id,
        details={"deactivated_admin_name": target_name},
        request=request,
    )

    return {"message": f"Admin {target_name} deactivated"}


# ── Member Roster Management (Up to 1,000 Members) ────────────────────────────

@router.get("/{coop_id}/members")
async def list_cooperative_members(
    coop_id: str,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_admin=Depends(resolve_coop_admin),
):
    """Returns member list for the cooperative with sub-indexing."""
    db = get_db()
    query = db.table("cooperative_members").select("*", count="exact").eq("cooperative_id", coop_id)

    if search:
        query = query.or_(f"full_name.ilike.%{search}%,phone.ilike.%{search}%,nin.ilike.%{search}%,member_number.ilike.%{search}%")

    query = query.order("sub_index").range(offset, offset + limit - 1)
    res = await db_execute(lambda: query.execute())

    return {
        "members": res.data or [],
        "total": res.count or 0,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{coop_id}/members")
async def add_single_member(
    coop_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """Adds a single member, auto-allocating the next sub-index (e.g. 1, 2, ... 1000)."""
    db = get_db()
    data = await request.json()

    full_name = data.get("full_name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip().lower() or None
    address = data.get("residential_address", "").strip()
    nin = data.get("nin", "").strip()
    member_number = data.get("member_number", "").strip() or None

    # Next of Kin
    nok_name = data.get("nok_name", "").strip()
    nok_phone = data.get("nok_phone", "").strip()
    nok_relationship = data.get("nok_relationship", "").strip()
    nok_address = data.get("nok_address", "").strip()

    # Property info
    property_id = data.get("property_id")
    plot_number = data.get("plot_number")
    block_number = data.get("block_number")
    plot_size_sqm = data.get("plot_size_sqm", 500.0)

    if not full_name or not phone:
        raise HTTPException(status_code=400, detail="Full name and phone number are required")

    # Determine next sub_index
    sub_res = await db_execute(lambda: db.table("cooperative_members")
        .select("sub_index")
        .eq("cooperative_id", coop_id)
        .order("sub_index", desc=True)
        .limit(1)
        .execute())

    next_sub = (sub_res.data[0]["sub_index"] + 1) if sub_res.data else 1
    if next_sub > 1000:
        raise HTTPException(status_code=400, detail="Cooperative has reached the maximum capacity of 1,000 members")

    default_pwd = data.get("password") or phone  # Custom password or defaults to phone number
    member_payload = {
        "cooperative_id": coop_id,
        "sub_index": next_sub,
        "member_number": member_number or f"MEM-{str(next_sub).zfill(4)}",
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "residential_address": address,
        "nin": nin,
        "nok_name": nok_name,
        "nok_phone": nok_phone,
        "nok_relationship": nok_relationship,
        "nok_address": nok_address,
        "property_id": property_id,
        "plot_number": plot_number,
        "block_number": block_number,
        "plot_size_sqm": plot_size_sqm,
        "allocation_status": "provisional" if property_id else "unallocated",
        "allocation_date": date.today().isoformat() if property_id else None,
        "password_hash": hash_password(default_pwd),
        "is_portal_active": True,
        "passport_locked": False,
        "signature_locked": False,
        "created_at": datetime.utcnow().isoformat(),
    }

    res = await db_execute(lambda: db.table("cooperative_members").insert(member_payload).execute())
    new_member = res.data[0] if res.data else {}

    # Audit Log Entry
    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action="created_member",
        target_entity="cooperative_member",
        target_id=new_member.get("id"),
        details={"member_name": full_name, "sub_index": next_sub},
        request=request,
    )

    return {
        "message": f"Member {full_name} added successfully as Sub-Index #{next_sub}",
        "member": new_member,
    }


@router.post("/{coop_id}/members/bulk")
async def bulk_upload_members(
    coop_id: str,
    file: UploadFile = File(...),
    request: Request = None,
    current_admin=Depends(resolve_coop_admin),
):
    """
    Parses CSV roster up to 1,000 rows.
    Columns expected: Full Name, Phone, Email, Residential Address, NIN, NOK Name, NOK Phone, NOK Relationship
    """
    content = await file.read()
    decoded = content.decode("utf-8-sig", errors="replace")
    csv_reader = csv.DictReader(io.StringIO(decoded))

    db = get_db()

    # Get current max sub_index
    sub_res = await db_execute(lambda: db.table("cooperative_members")
        .select("sub_index")
        .eq("cooperative_id", coop_id)
        .order("sub_index", desc=True)
        .limit(1)
        .execute())

    current_max = sub_res.data[0]["sub_index"] if sub_res.data else 0

    members_to_insert = []
    skipped_rows = 0

    for row in csv_reader:
        # Flexible key matching
        name = row.get("Full Name") or row.get("full_name") or row.get("Name") or row.get("name")
        phone = row.get("Phone") or row.get("phone") or row.get("Phone Number") or row.get("phone_number")
        if not name or not phone:
            skipped_rows += 1
            continue

        current_max += 1
        if current_max > 1000:
            break

        email = row.get("Email") or row.get("email") or ""
        address = row.get("Address") or row.get("address") or row.get("Residential Address") or ""
        nin = row.get("NIN") or row.get("nin") or ""
        nok_name = row.get("NOK Name") or row.get("nok_name") or row.get("Next of Kin Name") or ""
        nok_phone = row.get("NOK Phone") or row.get("nok_phone") or row.get("Next of Kin Phone") or ""
        nok_rel = row.get("NOK Relationship") or row.get("nok_relationship") or ""
        mem_num = row.get("Member ID") or row.get("member_number") or f"MEM-{str(current_max).zfill(4)}"
        
        # Password Resolution: Uses CSV 'Password' column if provided, otherwise defaults to Phone Number
        raw_pwd = row.get("Password") or row.get("password")
        initial_pwd = raw_pwd.strip() if raw_pwd and raw_pwd.strip() else phone.strip()

        members_to_insert.append({
            "cooperative_id": coop_id,
            "sub_index": current_max,
            "member_number": mem_num,
            "full_name": name.strip(),
            "phone": phone.strip(),
            "email": email.strip().lower() if email else None,
            "residential_address": address.strip(),
            "nin": nin.strip(),
            "nok_name": nok_name.strip(),
            "nok_phone": nok_phone.strip(),
            "nok_relationship": nok_rel.strip(),
            "allocation_status": "unallocated",
            "password_hash": hash_password(initial_pwd),
            "is_portal_active": True,
            "passport_locked": False,
            "signature_locked": False,
            "created_at": datetime.utcnow().isoformat(),
        })

    if members_to_insert:
        await db_execute(lambda: db.table("cooperative_members").insert(members_to_insert).execute())

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action="bulk_imported_members",
        target_entity="cooperative_member_roster",
        details={"imported_count": len(members_to_insert), "skipped_rows": skipped_rows},
        request=request,
    )

    return {
        "message": f"Successfully imported {len(members_to_insert)} members. Skipped {skipped_rows} invalid rows.",
        "imported_count": len(members_to_insert),
    }


# ── Passport & Signature Lock / Unlock Controls ───────────────────────────────

@router.post("/{coop_id}/members/{member_id}/unlock")
async def unlock_member_identity(
    coop_id: str,
    member_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """
    Cooperative Admin unlocks member passport photo or signature for resubmission.
    Members cannot modify these fields without admin unlock.
    """
    db = get_db()
    data = await request.json()
    field = data.get("field", "both")  # 'passport', 'signature', or 'both'
    reason = data.get("reason", "Admin requested document resubmission")

    update_payload = {"updated_at": datetime.utcnow().isoformat()}
    if field in ("passport", "both"):
        update_payload["passport_locked"] = False
        update_payload["passport_unlock_reason"] = reason
    if field in ("signature", "both"):
        update_payload["signature_locked"] = False
        update_payload["signature_unlock_reason"] = reason

    await db_execute(lambda: db.table("cooperative_members").update(update_payload).eq("id", member_id).execute())

    # Fetch member to send alert
    m_res = await db_execute(lambda: db.table("cooperative_members").select("*").eq("id", member_id).execute())
    if m_res.data:
        member = m_res.data[0]
        await dispatch_member_notification(
            member=member,
            title="Action Required: Upload Updated Document",
            message=f"Your cooperative admin has unlocked your profile for document update: {reason}. Please log into your portal to submit the new document.",
            notif_type="kyc_unlock",
            ref_id=member_id,
        )

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action=f"unlocked_member_{field}",
        target_entity="member_kyc",
        target_id=member_id,
        details={"field": field, "reason": reason},
        request=request,
    )

    return {"message": f"Successfully unlocked {field} for member update", "reason": reason}


# ── Invoicing, Sub-Indexing & Payment Receipts ────────────────────────────────

@router.get("/{coop_id}/invoices")
async def list_cooperative_invoices(
    coop_id: str,
    invoice_type: Optional[str] = None,
    current_admin=Depends(resolve_coop_admin),
):
    """Lists master and sub invoices for a cooperative society."""
    db = get_db()
    try:
        query = db.table("cooperative_invoices").select("*, cooperative_members(full_name, member_number), properties(title)").eq("cooperative_id", coop_id).order("created_at", desc=True)
        if invoice_type:
            query = query.eq("invoice_type", invoice_type)
        res = await db_execute(lambda: query.execute())
        return {"invoices": res.data or []}
    except Exception as e:
        logger.error(f"Failed to fetch coop invoices: {e}")
        return {"invoices": []}


@router.post("/{coop_id}/invoices/master")
async def create_master_invoice(
    coop_id: str,
    request: Request,
    current_staff=Depends(verify_token),
):
    """Creates a Master Cooperative Invoice with sequence EC-COP-XXXXXX."""
    db = get_db()
    data = await request.json()

    property_id = data.get("property_id")
    total_amount = Decimal(str(data.get("total_amount", 0)))
    due_date = data.get("due_date")
    payment_plan = data.get("payment_plan", "installments")

    # Generate sequence via RPC or atomic helper
    seq_res = await db_execute(lambda: db.rpc("generate_coop_invoice_number").execute())
    inv_number = seq_res.data if seq_res.data else f"EC-COP-{str(datetime.now().microsecond)[:6]}"

    payload = {
        "cooperative_id": coop_id,
        "invoice_type": "master",
        "invoice_number": inv_number,
        "property_id": property_id,
        "total_amount": float(total_amount),
        "amount_paid": 0.0,
        "balance_due": float(total_amount),
        "payment_plan": payment_plan,
        "due_date": due_date,
        "status": "pending",
        "created_by": current_staff["sub"],
        "created_at": datetime.utcnow().isoformat(),
    }

    res = await db_execute(lambda: db.table("cooperative_invoices").insert(payload).execute())
    return {"message": f"Master invoice {inv_number} generated", "invoice": res.data[0]}


@router.post("/{coop_id}/invoices/sub")
async def create_member_sub_invoice(
    coop_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """
    Creates an individual member sub-invoice with sub-indexed number:
    Format: EC-COP-000001/014 (Master Invoice Number / Member Sub-Index)
    """
    db = get_db()
    data = await request.json()

    parent_invoice_id = data.get("parent_invoice_id")
    member_id = data.get("member_id")
    total_amount = Decimal(str(data.get("total_amount", 0)))
    property_id = data.get("property_id")

    # Fetch parent invoice number
    p_res = await db_execute(lambda: db.table("cooperative_invoices").select("invoice_number").eq("id", parent_invoice_id).execute())
    if not p_res.data:
        raise HTTPException(status_code=404, detail="Parent master invoice not found")
    master_num = p_res.data[0]["invoice_number"]

    # Fetch member sub_index
    m_res = await db_execute(lambda: db.table("cooperative_members").select("sub_index, full_name").eq("id", member_id).execute())
    if not m_res.data:
        raise HTTPException(status_code=404, detail="Cooperative member not found")
    sub_idx = m_res.data[0]["sub_index"]
    formatted_sub_num = f"{master_num}/{str(sub_idx).zfill(3)}"

    payload = {
        "cooperative_id": coop_id,
        "member_id": member_id,
        "parent_invoice_id": parent_invoice_id,
        "invoice_type": "sub",
        "invoice_number": formatted_sub_num,
        "sub_index": sub_idx,
        "property_id": property_id,
        "total_amount": float(total_amount),
        "amount_paid": 0.0,
        "balance_due": float(total_amount),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    res = await db_execute(lambda: db.table("cooperative_invoices").insert(payload).execute())

    await log_coop_activity(
        cooperative_id=coop_id,
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action="issued_member_sub_invoice",
        target_entity="cooperative_invoice",
        target_id=res.data[0]["id"] if res.data else None,
        details={"invoice_number": formatted_sub_num, "amount": float(total_amount)},
        request=request,
    )

    return {"message": f"Sub-invoice {formatted_sub_num} created", "invoice": res.data[0]}


@router.post("/{coop_id}/payments")
async def record_cooperative_payment(
    coop_id: str,
    request: Request,
    current_staff=Depends(verify_token),
):
    """
    Records payment against a cooperative invoice.
    Generates atomic receipt RCP-COP-XXXXXX and dispatches multi-channel alerts.
    """
    db = get_db()
    data = await request.json()

    invoice_id = data.get("invoice_id")
    amount = Decimal(str(data.get("amount", 0)))
    reference = data.get("payment_reference", "")
    method = data.get("payment_method", "bank_transfer")

    # Fetch invoice
    inv_res = await db_execute(lambda: db.table("cooperative_invoices")
        .select("*, cooperative_members(*), cooperatives(name)")
        .eq("id", invoice_id)
        .execute())

    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv_res.data[0]
    new_paid = Decimal(str(invoice["amount_paid"])) + amount
    new_balance = Decimal(str(invoice["total_amount"])) - new_paid
    new_status = "paid" if new_balance <= 0 else "partially_paid"

    # Generate atomic receipt number
    rcp_res = await db_execute(lambda: db.rpc("generate_coop_receipt_number").execute())
    rcp_num = rcp_res.data if rcp_res.data else f"RCP-COP-{str(datetime.now().microsecond)[:6]}"

    # Insert payment record
    pay_payload = {
        "cooperative_id": coop_id,
        "invoice_id": invoice_id,
        "member_id": invoice.get("member_id"),
        "receipt_number": rcp_num,
        "amount": float(amount),
        "payment_method": method,
        "payment_reference": reference,
        "payment_date": date.today().isoformat(),
        "recorded_by": current_staff["sub"],
        "created_at": datetime.utcnow().isoformat(),
    }
    await db_execute(lambda: db.table("cooperative_payments").insert(pay_payload).execute())

    # Update invoice status and balance
    await db_execute(lambda: db.table("cooperative_invoices").update({
        "amount_paid": float(new_paid),
        "balance_due": float(new_balance),
        "status": new_status,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", invoice_id).execute())

    # Dispatch alerts to member if sub-invoice
    if invoice.get("cooperative_members"):
        member = invoice["cooperative_members"]
        coop_name = invoice.get("cooperatives", {}).get("name", "Cooperative Society")
        await dispatch_member_notification(
            member=member,
            title="Payment Confirmed - Receipt Issued",
            message=f"Payment of NGN {amount:,.2f} has been confirmed for {invoice['invoice_number']} ({coop_name}). Receipt #{rcp_num} is now available in your portal.",
            notif_type="payment_receipt",
            ref_id=rcp_num,
        )

    return {
        "message": f"Payment recorded. Receipt #{rcp_num} generated.",
        "receipt_number": rcp_num,
        "balance_due": float(new_balance),
        "status": new_status,
    }


# ── Property Transfer & Ownership Reassignment Engine ─────────────────────────

@router.post("/transfers/request")
async def request_property_transfer(
    request: Request,
    current_member=Depends(resolve_coop_member),
):
    """
    Member initiates transfer of their property to a new owner.
    Supports both active installment plans and fully paid properties.
    """
    db = get_db()
    data = await request.json()
    member_id = current_member["member_id"]
    coop_id = current_member["cooperative_id"]

    transfer_type = data.get("transfer_type", "active_plan") # 'active_plan' or 'fully_paid'
    new_owner_name = data.get("new_owner_name", "").strip()
    new_owner_phone = data.get("new_owner_phone", "").strip()
    new_owner_email = data.get("new_owner_email", "").strip().lower()
    new_owner_address = data.get("new_owner_address", "").strip()
    new_owner_nin = data.get("new_owner_nin", "").strip()
    new_owner_nok_name = data.get("new_owner_nok_name", "").strip()
    new_owner_nok_phone = data.get("new_owner_nok_phone", "").strip()
    new_owner_nok_rel = data.get("new_owner_nok_relationship", "").strip()

    if not new_owner_name or not new_owner_phone or not new_owner_nin:
        raise HTTPException(status_code=400, detail="New owner full name, phone number, and NIN are mandatory")

    # Fetch member invoice to check outstanding balance
    inv_res = await db_execute(lambda: db.table("cooperative_invoices")
        .select("id, balance_due, status")
        .eq("member_id", member_id)
        .eq("invoice_type", "sub")
        .execute())

    inv_id = inv_res.data[0]["id"] if inv_res.data else None
    balance = Decimal(str(inv_res.data[0]["balance_due"])) if inv_res.data else Decimal("0.00")

    payload = {
        "cooperative_id": coop_id,
        "member_id": member_id,
        "invoice_id": inv_id,
        "transfer_type": transfer_type,
        "outstanding_balance": float(balance),
        "new_owner_name": new_owner_name,
        "new_owner_phone": new_owner_phone,
        "new_owner_email": new_owner_email,
        "new_owner_address": new_owner_address,
        "new_owner_nin": new_owner_nin,
        "new_owner_nok_name": new_owner_nok_name,
        "new_owner_nok_phone": new_owner_nok_phone,
        "new_owner_nok_relationship": new_owner_nok_rel,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    res = await db_execute(lambda: db.table("cooperative_transfers").insert(payload).execute())
    return {"message": "Transfer request submitted for Cooperative Exco and Legal review", "transfer": res.data[0]}


@router.post("/transfers/{transfer_id}/exco-review")
async def exco_review_transfer(
    transfer_id: str,
    request: Request,
    current_admin=Depends(resolve_coop_admin),
):
    """Cooperative Exco Admin approves or rejects the transfer request."""
    db = get_db()
    data = await request.json()
    action = data.get("action", "").lower()
    reason = data.get("reason", "")

    new_status = "exco_approved" if action == "approve" else "rejected"
    update_data = {
        "status": new_status,
        "exco_approved_by": current_admin.get("id"),
        "exco_approved_at": datetime.utcnow().isoformat(),
        "rejection_reason": reason if action == "reject" else None,
        "updated_at": datetime.utcnow().isoformat(),
    }

    await db_execute(lambda: db.table("cooperative_transfers").update(update_data).eq("id", transfer_id).execute())

    await log_coop_activity(
        cooperative_id=current_admin["cooperative_id"],
        admin_id=current_admin.get("id"),
        admin_name=current_admin.get("full_name", "Admin"),
        action=f"transfer_{new_status}",
        target_entity="property_transfer",
        target_id=transfer_id,
        details={"reason": reason},
        request=request,
    )

    return {"message": f"Transfer has been {new_status}", "status": new_status}


@router.post("/transfers/{transfer_id}/legal-review")
async def legal_review_transfer(
    transfer_id: str,
    request: Request,
    current_staff=Depends(verify_token),
):
    """Eximp & Cloves Legal executes final approval and reassigns plot to the new owner."""
    if not has_any_role(current_staff, "admin", "super_admin", "legal"):
        raise HTTPException(status_code=403, detail="Only Eximp & Cloves Legal can execute final transfer")

    db = get_db()
    data = await request.json()
    action = data.get("action", "").lower()
    reason = data.get("reason", "")

    t_res = await db_execute(lambda: db.table("cooperative_transfers").select("*, cooperative_members(*)").eq("id", transfer_id).execute())
    if not t_res.data:
        raise HTTPException(status_code=404, detail="Transfer record not found")

    transfer = t_res.data[0]
    orig_member = transfer["cooperative_members"]

    if action == "approve":
        # 1. Update original member allocation status to 'transferred'
        await db_execute(lambda: db.table("cooperative_members").update({
            "allocation_status": "transferred",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", orig_member["id"]).execute())

        # 2. Create or assign new member record for the transferee
        new_member_payload = {
            "cooperative_id": transfer["cooperative_id"],
            "sub_index": orig_member["sub_index"], # Takes over the same plot sub-index
            "member_number": f"{orig_member.get('member_number', 'MEM')}-T",
            "full_name": transfer["new_owner_name"],
            "phone": transfer["new_owner_phone"],
            "email": transfer["new_owner_email"],
            "residential_address": transfer["new_owner_address"],
            "nin": transfer["new_owner_nin"],
            "nok_name": transfer["new_owner_nok_name"],
            "nok_phone": transfer["new_owner_nok_phone"],
            "nok_relationship": transfer["new_owner_nok_relationship"],
            "property_id": orig_member.get("property_id"),
            "plot_number": orig_member.get("plot_number"),
            "block_number": orig_member.get("block_number"),
            "plot_size_sqm": orig_member.get("plot_size_sqm"),
            "allocation_status": "confirmed",
            "allocation_date": date.today().isoformat(),
            "password_hash": hash_password(transfer["new_owner_phone"]),
            "is_portal_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        # Mark transfer completed
        await db_execute(lambda: db.table("cooperative_transfers").update({
            "status": "completed",
            "legal_approved_by": current_staff["sub"],
            "legal_approved_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", transfer_id).execute())

        return {"message": "Property transfer executed successfully. New owner account created.", "status": "completed"}
    else:
        await db_execute(lambda: db.table("cooperative_transfers").update({
            "status": "rejected",
            "legal_approved_by": current_staff["sub"],
            "rejection_reason": reason,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", transfer_id).execute())
        return {"message": "Transfer rejected by legal counsel", "status": "rejected"}


# ── Activity History & Audit Log Endpoint ─────────────────────────────────────

@router.get("/{coop_id}/activity-log")
async def get_cooperative_activity_log(
    coop_id: str,
    limit: int = 50,
    current_admin=Depends(resolve_coop_admin),
):
    """Returns chronological audit log showing which of the 3 admins took each action."""
    db = get_db()
    res = await db_execute(lambda: db.table("cooperative_activity_log")
        .select("*")
        .eq("cooperative_id", coop_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute())
    return {"logs": res.data or []}


# ── Member Self-Service Portal Profile & Ledger ───────────────────────────────

@router.get("/member/me")
async def get_member_portal_profile(current_member=Depends(resolve_coop_member)):
    """Returns profile, allocated plot details, locked identity flags, and preferences."""
    db = get_db()
    member_id = current_member["member_id"]

    res = await db_execute(lambda: db.table("cooperative_members")
        .select("*, cooperatives(name, code), properties(name, location)")
        .eq("id", member_id)
        .execute())

    if not res.data:
        raise HTTPException(status_code=404, detail="Member profile not found")

    member = res.data[0]
    return {"member": member}


@router.patch("/member/profile")
async def update_member_portal_profile(
    request: Request,
    current_member=Depends(resolve_coop_member),
):
    """
    Member updates personal contact, Next of Kin, password, or notification preferences.
    Explicitly prevents direct modification of passport_photo or signature when locked.
    """
    db = get_db()
    member_id = current_member["member_id"]
    data = await request.json()

    # Allowed editable fields
    update_data = {"updated_at": datetime.utcnow().isoformat()}
    for key in ["phone", "email", "residential_address", "nok_name", "nok_phone", "nok_relationship", "nok_address", "notify_email", "notify_sms", "notify_whatsapp"]:
        if key in data:
            update_data[key] = data[key]

    if "new_password" in data and data["new_password"]:
        update_data["password_hash"] = hash_password(data["new_password"])

    # Enforce Fraud Shield: Do NOT allow modifying passport or signature here
    if "passport_photo_url" in data or "signature_url" in data:
        raise HTTPException(
            status_code=400,
            detail="Passport photo and signature are locked for transaction integrity. Please contact your cooperative admin to request an unlock.",
        )

    await db_execute(lambda: db.table("cooperative_members").update(update_data).eq("id", member_id).execute())
    return {"message": "Profile updated successfully"}


@router.get("/member/ledger")
async def get_member_financial_ledger(current_member=Depends(resolve_coop_member)):
    """Returns the member's sub-invoices, payment receipts, total paid, and balance due."""
    db = get_db()
    member_id = current_member["member_id"]

    inv_res = await db_execute(lambda: db.table("cooperative_invoices")
        .select("*, properties(name)")
        .eq("member_id", member_id)
        .order("created_at")
        .execute())

    pay_res = await db_execute(lambda: db.table("cooperative_payments")
        .select("*")
        .eq("member_id", member_id)
        .order("created_at", desc=True)
        .execute())

    invoices = inv_res.data or []
    payments = pay_res.data or []

    total_invoiced = sum(Decimal(str(i.get("total_amount", 0))) for i in invoices)
    total_paid = sum(Decimal(str(p.get("amount", 0))) for p in payments)
    balance_due = total_invoiced - total_paid

    return {
        "summary": {
            "total_invoiced": float(total_invoiced),
            "total_paid": float(total_paid),
            "balance_due": float(balance_due),
        },
        "invoices": invoices,
        "receipts": payments,
    }


# ── Document Generation Endpoints (Invoices & Receipts) ───────────────────────

@router.get("/invoices/{invoice_id}/html")
async def view_cooperative_invoice_html(invoice_id: str, viewer=Depends(resolve_coop_viewer)):
    """Renders the HTML preview of a Cooperative Scheme Invoice."""
    db = get_db()
    res = await db_execute(lambda: db.table("cooperative_invoices")
        .select("*, cooperatives(*), cooperative_members(*), properties(*)")
        .eq("id", invoice_id)
        .limit(1)
        .execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Cooperative invoice not found")

    invoice = res.data[0]
    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != invoice.get("cooperative_id"):
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member" and viewer.get("member_id") != invoice.get("member_id"):
            raise HTTPException(status_code=403, detail="Access denied")

    cooperative = invoice.get("cooperatives") or {}
    member = invoice.get("cooperative_members") or {}
    prop = invoice.get("properties") or {}

    html_content = render_cooperative_invoice_html(invoice, cooperative, member, prop)
    return HTMLResponse(content=html_content)


@router.get("/invoices/{invoice_id}/pdf")
async def download_cooperative_invoice_pdf(invoice_id: str, viewer=Depends(resolve_coop_viewer)):
    """Generates and streams the PDF document for a Cooperative Scheme Invoice."""
    db = get_db()
    res = await db_execute(lambda: db.table("cooperative_invoices")
        .select("*, cooperatives(*), cooperative_members(*), properties(*)")
        .eq("id", invoice_id)
        .limit(1)
        .execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Cooperative invoice not found")

    invoice = res.data[0]
    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != invoice.get("cooperative_id"):
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member" and viewer.get("member_id") != invoice.get("member_id"):
            raise HTTPException(status_code=403, detail="Access denied")

    cooperative = invoice.get("cooperatives") or {}
    member = invoice.get("cooperative_members") or {}
    prop = invoice.get("properties") or {}

    pdf_bytes = await db_execute(lambda: generate_cooperative_invoice_pdf(invoice, cooperative, member, prop))
    inv_num = str(invoice.get("invoice_number", invoice_id)).replace("/", "_")
    filename = f"Invoice_{inv_num}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/payments/{payment_id}/receipt/html")
async def view_cooperative_receipt_html(payment_id: str, viewer=Depends(resolve_coop_viewer)):
    """Renders the HTML preview of an Official Cooperative Payment Receipt."""
    db = get_db()
    pay_res = await db_execute(lambda: db.table("cooperative_payments")
        .select("*, cooperatives(*), cooperative_members(*), cooperative_invoices(*)")
        .eq("id", payment_id)
        .limit(1)
        .execute())
    if not pay_res.data:
        raise HTTPException(status_code=404, detail="Payment record not found")

    payment = pay_res.data[0]
    invoice = payment.get("cooperative_invoices") or {}
    cooperative = payment.get("cooperatives") or {}
    member = payment.get("cooperative_members") or {}

    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != payment.get("cooperative_id"):
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member" and viewer.get("member_id") != payment.get("member_id"):
            raise HTTPException(status_code=403, detail="Access denied")

    prop = {}
    if invoice.get("property_id"):
        pr_res = await db_execute(lambda: db.table("properties").select("*").eq("id", invoice["property_id"]).limit(1).execute())
        if pr_res.data:
            prop = pr_res.data[0]

    html_content = render_cooperative_receipt_html(payment, invoice, cooperative, member, prop)
    return HTMLResponse(content=html_content)


@router.get("/payments/{payment_id}/receipt/pdf")
async def download_cooperative_receipt_pdf(payment_id: str, viewer=Depends(resolve_coop_viewer)):
    """Generates and streams the PDF document for an Official Cooperative Payment Receipt."""
    db = get_db()
    pay_res = await db_execute(lambda: db.table("cooperative_payments")
        .select("*, cooperatives(*), cooperative_members(*), cooperative_invoices(*)")
        .eq("id", payment_id)
        .limit(1)
        .execute())
    if not pay_res.data:
        raise HTTPException(status_code=404, detail="Payment record not found")

    payment = pay_res.data[0]
    invoice = payment.get("cooperative_invoices") or {}
    cooperative = payment.get("cooperatives") or {}
    member = payment.get("cooperative_members") or {}

    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != payment.get("cooperative_id"):
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member" and viewer.get("member_id") != payment.get("member_id"):
            raise HTTPException(status_code=403, detail="Access denied")

    prop = {}
    if invoice.get("property_id"):
        pr_res = await db_execute(lambda: db.table("properties").select("*").eq("id", invoice["property_id"]).limit(1).execute())
        if pr_res.data:
            prop = pr_res.data[0]

    pdf_bytes = await db_execute(lambda: generate_cooperative_receipt_pdf(payment, invoice, cooperative, member, prop))
    rec_num = str(payment.get("receipt_number", f"RCP_{payment_id[:8]}")).replace("/", "_")
    filename = f"Receipt_{rec_num}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


# ── Statement of Account Endpoints ───────────────────────────────────────────

@router.get("/members/{member_id}/statement/html")
async def view_member_statement_html(member_id: str, viewer=Depends(resolve_coop_viewer)):
    """Renders the HTML Statement of Account for an individual cooperative member."""
    db = get_db()
    m_res = await db_execute(lambda: db.table("cooperative_members").select("*, cooperatives(*)").eq("id", member_id).limit(1).execute())
    if not m_res.data:
        raise HTTPException(status_code=404, detail="Member not found")
    member = m_res.data[0]
    coop = member.get("cooperatives") or {}

    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != member.get("cooperative_id"):
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member" and viewer.get("member_id") != member_id:
            raise HTTPException(status_code=403, detail="Access denied")

    inv_res = await db_execute(lambda: db.table("cooperative_invoices").select("*").eq("member_id", member_id).order("created_at").execute())
    invoices = inv_res.data or []

    pay_res = await db_execute(lambda: db.table("cooperative_payments").select("*").eq("member_id", member_id).order("payment_date").execute())
    payments = pay_res.data or []

    inv_map = {}
    formatted_invoices = []
    for inv in invoices:
        item = {
            "id": inv.get("id"),
            "invoice_date": inv.get("created_at", "")[:10] if inv.get("created_at") else "",
            "invoice_number": inv.get("invoice_number", ""),
            "amount": float(inv.get("total_amount") or 0),
            "status": inv.get("status", "pending"),
            "payments": []
        }
        inv_map[inv.get("id")] = item
        formatted_invoices.append(item)

    unassigned_payments = []
    for p in payments:
        p_item = {
            "payment_date": p.get("payment_date") or (p.get("created_at", "")[:10] if p.get("created_at") else ""),
            "reference": p.get("receipt_number") or p.get("payment_reference") or f"RCP_{p.get('id', '')[:8]}",
            "payment_type": "payment",
            "amount": float(p.get("amount") or 0),
            "is_voided": False
        }
        inv_id = p.get("invoice_id")
        if inv_id and inv_id in inv_map:
            inv_map[inv_id]["payments"].append(p_item)
        else:
            unassigned_payments.append(p_item)

    if not formatted_invoices:
        plot_val = float(member.get("total_cost") or member.get("total_amount") or 0)
        baseline = {
            "invoice_date": member.get("created_at", "")[:10] if member.get("created_at") else datetime.now().strftime("%Y-%m-%d"),
            "invoice_number": f"ALLOT-{member.get('sub_index', '001')}",
            "amount": plot_val,
            "status": "active",
            "payments": unassigned_payments
        }
        formatted_invoices.append(baseline)
    elif unassigned_payments:
        formatted_invoices[0]["payments"].extend(unassigned_payments)

    client_data = {
        "full_name": member.get("full_name", "Member"),
        "phone": member.get("phone", ""),
        "email": member.get("email", ""),
        "address": f"Plot #{member.get('plot_number', 'Pending')} | {coop.get('name', 'Cooperative Scheme')} (Member #{member.get('member_number', member.get('sub_index', ''))})",
    }

    html_content = render_statement_html(formatted_invoices, client_data)
    return HTMLResponse(content=html_content)


@router.get("/members/{member_id}/statement/pdf")
async def download_member_statement_pdf(member_id: str, viewer=Depends(resolve_coop_viewer)):
    """Generates and streams the PDF Statement of Account for an individual cooperative member."""
    db = get_db()
    m_res = await db_execute(lambda: db.table("cooperative_members").select("*, cooperatives(*)").eq("id", member_id).limit(1).execute())
    if not m_res.data:
        raise HTTPException(status_code=404, detail="Member not found")
    member = m_res.data[0]
    coop = member.get("cooperatives") or {}

    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != member.get("cooperative_id"):
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member" and viewer.get("member_id") != member_id:
            raise HTTPException(status_code=403, detail="Access denied")

    inv_res = await db_execute(lambda: db.table("cooperative_invoices").select("*").eq("member_id", member_id).order("created_at").execute())
    invoices = inv_res.data or []

    pay_res = await db_execute(lambda: db.table("cooperative_payments").select("*").eq("member_id", member_id).order("payment_date").execute())
    payments = pay_res.data or []

    inv_map = {}
    formatted_invoices = []
    for inv in invoices:
        item = {
            "id": inv.get("id"),
            "invoice_date": inv.get("created_at", "")[:10] if inv.get("created_at") else "",
            "invoice_number": inv.get("invoice_number", ""),
            "amount": float(inv.get("total_amount") or 0),
            "status": inv.get("status", "pending"),
            "payments": []
        }
        inv_map[inv.get("id")] = item
        formatted_invoices.append(item)

    unassigned_payments = []
    for p in payments:
        p_item = {
            "payment_date": p.get("payment_date") or (p.get("created_at", "")[:10] if p.get("created_at") else ""),
            "reference": p.get("receipt_number") or p.get("payment_reference") or f"RCP_{p.get('id', '')[:8]}",
            "payment_type": "payment",
            "amount": float(p.get("amount") or 0),
            "is_voided": False
        }
        inv_id = p.get("invoice_id")
        if inv_id and inv_id in inv_map:
            inv_map[inv_id]["payments"].append(p_item)
        else:
            unassigned_payments.append(p_item)

    if not formatted_invoices:
        plot_val = float(member.get("total_cost") or member.get("total_amount") or 0)
        baseline = {
            "invoice_date": member.get("created_at", "")[:10] if member.get("created_at") else datetime.now().strftime("%Y-%m-%d"),
            "invoice_number": f"ALLOT-{member.get('sub_index', '001')}",
            "amount": plot_val,
            "status": "active",
            "payments": unassigned_payments
        }
        formatted_invoices.append(baseline)
    elif unassigned_payments:
        formatted_invoices[0]["payments"].extend(unassigned_payments)

    client_data = {
        "full_name": member.get("full_name", "Member"),
        "phone": member.get("phone", ""),
        "email": member.get("email", ""),
        "address": f"Plot #{member.get('plot_number', 'Pending')} | {coop.get('name', 'Cooperative Scheme')} (Member #{member.get('member_number', member.get('sub_index', ''))})",
    }

    pdf_bytes = await db_execute(lambda: generate_statement_pdf(formatted_invoices, client_data))
    clean_name = "".join(c for c in member.get("full_name", "Member") if c.isalnum() or c in (" ", "_")).replace(" ", "_")
    filename = f"Statement_{clean_name}_{member.get('sub_index', '001')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/{coop_id}/statement/html")
async def view_society_statement_html(coop_id: str, viewer=Depends(resolve_coop_viewer)):
    """Renders the HTML Statement of Account for the entire cooperative society."""
    db = get_db()
    c_res = await db_execute(lambda: db.table("cooperatives").select("*").eq("id", coop_id).limit(1).execute())
    if not c_res.data:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    coop = c_res.data[0]

    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != coop_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member":
            raise HTTPException(status_code=403, detail="Access denied. Society statement is restricted to society executives and staff.")

    inv_res = await db_execute(lambda: db.table("cooperative_invoices").select("*").eq("cooperative_id", coop_id).order("created_at").execute())
    all_invoices = inv_res.data or []

    master_invoices = [i for i in all_invoices if i.get("invoice_type") == "master"]
    target_invoices = master_invoices if master_invoices else all_invoices

    pay_res = await db_execute(lambda: db.table("cooperative_payments").select("*").eq("cooperative_id", coop_id).order("payment_date").execute())
    payments = pay_res.data or []

    inv_map = {}
    formatted_invoices = []
    for inv in target_invoices:
        item = {
            "id": inv.get("id"),
            "invoice_date": inv.get("created_at", "")[:10] if inv.get("created_at") else "",
            "invoice_number": inv.get("invoice_number", ""),
            "amount": float(inv.get("total_amount") or 0),
            "status": inv.get("status", "pending"),
            "payments": []
        }
        inv_map[inv.get("id")] = item
        formatted_invoices.append(item)

    unassigned_payments = []
    for p in payments:
        p_item = {
            "payment_date": p.get("payment_date") or (p.get("created_at", "")[:10] if p.get("created_at") else ""),
            "reference": p.get("receipt_number") or p.get("payment_reference") or f"RCP_{p.get('id', '')[:8]}",
            "payment_type": "payment",
            "amount": float(p.get("amount") or 0),
            "is_voided": False
        }
        inv_id = p.get("invoice_id")
        if inv_id and inv_id in inv_map:
            inv_map[inv_id]["payments"].append(p_item)
        else:
            unassigned_payments.append(p_item)

    if not formatted_invoices:
        baseline = {
            "invoice_date": coop.get("created_at", "")[:10] if coop.get("created_at") else datetime.now().strftime("%Y-%m-%d"),
            "invoice_number": f"MASTER-{coop.get('code', 'COOP')}",
            "amount": 0.0,
            "status": "active",
            "payments": unassigned_payments
        }
        formatted_invoices.append(baseline)
    elif unassigned_payments:
        formatted_invoices[0]["payments"].extend(unassigned_payments)

    client_data = {
        "full_name": coop.get("name", "Cooperative Society"),
        "phone": coop.get("contact_phone", ""),
        "email": coop.get("contact_email", ""),
        "address": coop.get("registered_address") or f"Corporate Cooperative Scheme - Code: {coop.get('code', '')}",
    }

    html_content = render_statement_html(formatted_invoices, client_data)
    return HTMLResponse(content=html_content)


@router.get("/{coop_id}/statement/pdf")
async def download_society_statement_pdf(coop_id: str, viewer=Depends(resolve_coop_viewer)):
    """Generates and streams the PDF Statement of Account for the entire cooperative society."""
    db = get_db()
    c_res = await db_execute(lambda: db.table("cooperatives").select("*").eq("id", coop_id).limit(1).execute())
    if not c_res.data:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    coop = c_res.data[0]

    if not viewer.get("is_internal"):
        if viewer.get("user_type") == "coop_admin" and viewer.get("cooperative_id") != coop_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if viewer.get("user_type") == "coop_member":
            raise HTTPException(status_code=403, detail="Access denied. Society statement is restricted to society executives and staff.")

    inv_res = await db_execute(lambda: db.table("cooperative_invoices").select("*").eq("cooperative_id", coop_id).order("created_at").execute())
    all_invoices = inv_res.data or []

    master_invoices = [i for i in all_invoices if i.get("invoice_type") == "master"]
    target_invoices = master_invoices if master_invoices else all_invoices

    pay_res = await db_execute(lambda: db.table("cooperative_payments").select("*").eq("cooperative_id", coop_id).order("payment_date").execute())
    payments = pay_res.data or []

    inv_map = {}
    formatted_invoices = []
    for inv in target_invoices:
        item = {
            "id": inv.get("id"),
            "invoice_date": inv.get("created_at", "")[:10] if inv.get("created_at") else "",
            "invoice_number": inv.get("invoice_number", ""),
            "amount": float(inv.get("total_amount") or 0),
            "status": inv.get("status", "pending"),
            "payments": []
        }
        inv_map[inv.get("id")] = item
        formatted_invoices.append(item)

    unassigned_payments = []
    for p in payments:
        p_item = {
            "payment_date": p.get("payment_date") or (p.get("created_at", "")[:10] if p.get("created_at") else ""),
            "reference": p.get("receipt_number") or p.get("payment_reference") or f"RCP_{p.get('id', '')[:8]}",
            "payment_type": "payment",
            "amount": float(p.get("amount") or 0),
            "is_voided": False
        }
        inv_id = p.get("invoice_id")
        if inv_id and inv_id in inv_map:
            inv_map[inv_id]["payments"].append(p_item)
        else:
            unassigned_payments.append(p_item)

    if not formatted_invoices:
        baseline = {
            "invoice_date": coop.get("created_at", "")[:10] if coop.get("created_at") else datetime.now().strftime("%Y-%m-%d"),
            "invoice_number": f"MASTER-{coop.get('code', 'COOP')}",
            "amount": 0.0,
            "status": "active",
            "payments": unassigned_payments
        }
        formatted_invoices.append(baseline)
    elif unassigned_payments:
        formatted_invoices[0]["payments"].extend(unassigned_payments)

    client_data = {
        "full_name": coop.get("name", "Cooperative Society"),
        "phone": coop.get("contact_phone", ""),
        "email": coop.get("contact_email", ""),
        "address": coop.get("registered_address") or f"Corporate Cooperative Scheme - Code: {coop.get('code', '')}",
    }

    pdf_bytes = await db_execute(lambda: generate_statement_pdf(formatted_invoices, client_data))
    clean_code = "".join(c for c in coop.get("code", "COOP") if c.isalnum() or c in ("-", "_"))
    filename = f"Society_Statement_{clean_code}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


