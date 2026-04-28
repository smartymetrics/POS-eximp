"""
Bio Data Router — /api/biodata
Handles HR form settings, invite management, public form submission,
document uploads to hr_documents/bio_data/ bucket, review workflow, and certificates.
"""
import os
import uuid
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from database import get_db, db_execute
from routers.auth import verify_token

router = APIRouter()
logger = logging.getLogger(__name__)

APP_BASE_URL = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com")
FROM_EMAIL = os.getenv("FROM_EMAIL", "hr@eximps-cloves.com")
HR_BIODATA_BUCKET = "hr-documents"
BIODATA_FOLDER = "bio_data"

# ─── EMAIL HELPER ────────────────────────────────────────────────────────────

async def _send_email(to: str, subject: str, html: str):
    try:
        import resend
        if not getattr(resend, "api_key", None):
            resend.api_key = os.getenv("RESEND_API_KEY")
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: resend.Emails.send({
            "from": f"Eximp & Cloves HR <{FROM_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": html,
        }))
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")


def _base_email_wrapper(body: str) -> str:
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:620px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
      <div style="background:#0B0C0F;padding:28px 32px;display:flex;align-items:center;gap:14px;">
        <div style="width:40px;height:40px;background:#C47D0A;border-radius:8px;display:flex;align-items:center;justify-content:center;">
          <span style="color:#fff;font-weight:900;font-size:18px;">E</span>
        </div>
        <div>
          <div style="color:#fff;font-weight:800;font-size:16px;">Eximp &amp; Cloves</div>
          <div style="color:#9CA3AF;font-size:12px;">Human Resources</div>
        </div>
      </div>
      {body}
      <div style="padding:20px 32px;background:#F9FAFB;border-top:1px solid #E5E7EB;font-size:11px;color:#9CA3AF;text-align:center;">
        Eximp &amp; Cloves Infrastructure Limited · 57B Isaac John Street, Yaba, Lagos<br>
        This is an automated HR system email.
      </div>
    </div>"""


def _invite_email_html(link: str, staff_name: str = None) -> str:
    greeting = f"Dear {staff_name}," if staff_name else "Hello,"
    return _base_email_wrapper(f"""
      <div style="padding:36px 32px;">
        <h2 style="color:#0B0C0F;margin:0 0 8px;font-size:22px;font-weight:800;">Employee Bio Data Form</h2>
        <div style="width:48px;height:4px;background:#C47D0A;border-radius:2px;margin-bottom:24px;"></div>
        <p style="color:#374151;line-height:1.7;margin:0 0 16px;">{greeting}</p>
        <p style="color:#374151;line-height:1.7;margin:0 0 16px;">
          HR has invited you to complete your <strong>Employee Bio Data Form</strong>. This information is required
          for your official HR records and must be submitted within <strong>7 days</strong>.
        </p>
        <p style="color:#374151;line-height:1.7;margin:0 0 28px;">
          Please ensure all fields are completed accurately, including your signature, passport photograph, and consent to location/device verification for <strong>proof of authenticity</strong>.
        </p>
        <a href="{link}" style="display:inline-block;background:#C47D0A;color:#fff;text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:700;font-size:14px;letter-spacing:0.5px;">
          Complete Bio Data Form →
        </a>
        <p style="color:#9CA3AF;font-size:12px;margin-top:28px;">
          If the button doesn't work, copy and paste this link into your browser:<br>
          <a href="{link}" style="color:#C47D0A;">{link}</a>
        </p>
        <p style="color:#9CA3AF;font-size:12px;">This link expires in 7 days.</p>
      </div>""")


def _approval_email_html(staff_name: str) -> str:
    return _base_email_wrapper(f"""
      <div style="padding:36px 32px;">
        <div style="width:60px;height:60px;background:#D1FAE5;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:20px;">
          <span style="font-size:28px;">✓</span>
        </div>
        <h2 style="color:#0B0C0F;margin:0 0 8px;font-size:22px;font-weight:800;">Bio Data Approved</h2>
        <div style="width:48px;height:4px;background:#10B981;border-radius:2px;margin-bottom:24px;"></div>
        <p style="color:#374151;line-height:1.7;">Dear <strong>{staff_name}</strong>,</p>
        <p style="color:#374151;line-height:1.7;">
          Your bio data submission has been <strong style="color:#10B981;">reviewed and approved</strong> by the HR department.
          Your profile has been updated with the information you provided.
        </p>
        <p style="color:#374151;line-height:1.7;">You can log in to the staff portal to view your updated profile at any time.</p>
        <p style="color:#6B7280;font-size:13px;margin-top:28px;">Thank you for completing your employee records.<br>— Eximp &amp; Cloves HR Team</p>
      </div>""")


def _rejection_email_html(staff_name: str, reason: str) -> str:
    return _base_email_wrapper(f"""
      <div style="padding:36px 32px;">
        <div style="width:60px;height:60px;background:#FEE2E2;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:20px;">
          <span style="font-size:28px;">✕</span>
        </div>
        <h2 style="color:#0B0C0F;margin:0 0 8px;font-size:22px;font-weight:800;">Bio Data Requires Revision</h2>
        <div style="width:48px;height:4px;background:#EF4444;border-radius:2px;margin-bottom:24px;"></div>
        <p style="color:#374151;line-height:1.7;">Dear <strong>{staff_name}</strong>,</p>
        <p style="color:#374151;line-height:1.7;">
          Your bio data submission requires some corrections. Please review the following feedback from HR and resubmit:
        </p>
        <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:16px 20px;margin:20px 0;color:#DC2626;font-size:13px;line-height:1.6;">
          {reason}
        </div>
        <p style="color:#374151;line-height:1.7;">Please use your original form link to resubmit or contact HR if you need a new link.</p>
      </div>""")


# ─── STORAGE HELPERS ─────────────────────────────────────────────────────────

def _extract_signed_url(res) -> str | None:
    """Robustly extract a signed URL string from any supabase-py response shape."""
    if res is None:
        return None
    # dict shape: {"signedURL": "...", "error": null}
    if isinstance(res, dict):
        url = res.get("signedURL") or res.get("signed_url") or res.get("url") or res.get("publicUrl")
        return url if url else None
    # supabase-py v2 returns an object with .signed_url or .url attribute
    for attr in ("signed_url", "signedURL", "url", "public_url"):
        val = getattr(res, attr, None)
        if val and isinstance(val, str) and val.startswith("http"):
            return val
    # Last resort: if it looks like a URL string
    s = str(res)
    if s.startswith("http"):
        return s
    logger.warning(f"Could not extract signed URL from response: {type(res)} — {s[:200]}")
    return None


def _upload_to_biodata(file_path_in_bucket: str, file_bytes: bytes, content_type: str) -> str | None:
    """Upload to hr_documents/bio_data/ and return a fresh signed URL."""
    try:
        db = get_db()
        # upsert=true so re-submissions overwrite cleanly
        db.storage.from_(HR_BIODATA_BUCKET).upload(
            path=file_path_in_bucket,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        # Use a long TTL (10 years ≈ 315 360 000 s) so stored URL stays valid
        res = db.storage.from_(HR_BIODATA_BUCKET).create_signed_url(file_path_in_bucket, 315_360_000)
        url = _extract_signed_url(res)
        if not url:
            logger.error(f"Signed URL generation returned no URL for [{file_path_in_bucket}]: {res}")
        return url
    except Exception as e:
        logger.error(f"Storage upload failed [{file_path_in_bucket}]: {e}")
        return None


# ─── SIGNED-URL REFRESH HELPER ───────────────────────────────────────────────

def _refresh_submission_urls(row: dict, ttl: int = 3600) -> dict:
    """
    Given a biodata_submissions row dict, refresh passport_photo_url and
    signature_url from their stored storage paths.  Mutates and returns row.
    Uses a short TTL (default 1 h) for list views; pass a longer TTL for
    detail/email views.
    """
    db = get_db()
    if row.get("passport_photo_path"):
        try:
            res = db.storage.from_(HR_BIODATA_BUCKET).create_signed_url(
                row["passport_photo_path"], ttl
            )
            url = _extract_signed_url(res)
            if url:
                row["passport_photo_url"] = url
        except Exception as e:
            logger.warning(f"Could not refresh passport URL for {row.get('id')}: {e}")

    if row.get("signature_path"):
        try:
            res = db.storage.from_(HR_BIODATA_BUCKET).create_signed_url(
                row["signature_path"], ttl
            )
            url = _extract_signed_url(res)
            if url:
                row["signature_url"] = url
        except Exception as e:
            logger.warning(f"Could not refresh signature URL for {row.get('id')}: {e}")

    return row


# ─── PYDANTIC MODELS ─────────────────────────────────────────────────────────


class SettingsUpdate(BaseModel):
    is_collecting: Optional[bool] = None
    form_message: Optional[str] = None

class InviteCreate(BaseModel):
    email: str

class ReviewAction(BaseModel):
    action: str  # "approve" | "reject"
    rejection_reason: Optional[str] = None

class EmailCertificate(BaseModel):
    to_email: str
    submission_id: str


# ─── SETTINGS ────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(token=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("biodata_settings").select("*").limit(1).execute())
    if not res.data:
        # Auto-create default row
        ins = await db_execute(lambda: db.table("biodata_settings").insert({"is_collecting": True}).execute())
        return ins.data[0] if ins.data else {}
    return res.data[0]


@router.patch("/settings")
async def update_settings(body: SettingsUpdate, token=Depends(verify_token)):
    db = get_db()
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    res = await db_execute(lambda: db.table("biodata_settings").update(update_data).neq("id", "00000000-0000-0000-0000-000000000000").execute())
    return res.data[0] if res.data else {}


# ─── INVITES ─────────────────────────────────────────────────────────────────

@router.get("/invites")
async def list_invites(token=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("biodata_invites").select("*").order("created_at", desc=True).execute())
    return res.data or []


@router.post("/invites")
async def send_invite(body: InviteCreate, token=Depends(verify_token)):
    db = get_db()
    email = body.email.strip().lower()

    # Check if staff exists
    staff_res = await db_execute(lambda: db.table("admins").select("id,full_name,email").ilike("email", email).limit(1).execute())
    staff = staff_res.data[0] if staff_res.data else None

    # Check for existing pending invite
    existing = await db_execute(lambda: db.table("biodata_invites").select("id,status,token").eq("email", email).eq("status", "pending").limit(1).execute())

    invite_token = str(uuid.uuid4()).replace("-", "") + str(uuid.uuid4()).replace("-", "")
    now = datetime.utcnow()
    expires = (now + timedelta(days=7)).isoformat()

    if existing.data:
        # Reuse existing token (resend)
        invite_token = existing.data[0]["token"]
        await db_execute(lambda: db.table("biodata_invites").update({"expires_at": expires}).eq("id", existing.data[0]["id"]).execute())
    else:
        invite_data = {
            "email": email,
            "token": invite_token,
            "staff_id": staff["id"] if staff else None,
            "invited_by": token.get("sub"),
            "expires_at": expires,
        }
        await db_execute(lambda: db.table("biodata_invites").insert(invite_data).execute())

    link = f"{APP_BASE_URL}/hr/?token={invite_token}"
    await _send_email(email, "Complete Your Employee Bio Data Form", _invite_email_html(link, staff["full_name"] if staff else None))

    return {"success": True, "email": email, "link": link, "staff_found": staff is not None}


@router.get("/general-link")
async def get_general_link(token=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("biodata_settings").select("general_link_token").limit(1).execute())
    if not res.data:
        raise HTTPException(404, "Settings not found")
    link_token = res.data[0]["general_link_token"]
    return {"link": f"{APP_BASE_URL}/hr/?token={link_token}", "token": link_token}


# ─── PUBLIC FORM ENDPOINTS (no auth) ─────────────────────────────────────────

@router.get("/public/check")
async def public_check_token(token: str, email: str = None):
    """Validate token and check if email is an existing staff."""
    db = get_db()

    # Check if collecting
    settings = await db_execute(lambda: db.table("biodata_settings").select("is_collecting,form_message,general_link_token").limit(1).execute())
    if not settings.data:
        raise HTTPException(404, "Form not found")

    s = settings.data[0]
    if not s["is_collecting"]:
        raise HTTPException(403, "Bio data collection is currently closed.")

    # Check if token is general link token
    is_general = token == s.get("general_link_token")
    invite = None

    if not is_general:
        # Look up specific invite
        inv_res = await db_execute(lambda: db.table("biodata_invites").select("*").eq("token", token).limit(1).execute())
        if not inv_res.data:
            raise HTTPException(404, "Invalid or expired link.")
        invite = inv_res.data[0]
        if invite["status"] == "submitted":
            raise HTTPException(400, "Your submission is already under review. Please wait for HR approval.")
        if invite["status"] == "approved":
            raise HTTPException(400, "This invitation has already been approved. No further action is required.")
        if invite["expires_at"] and datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00")) < datetime.utcnow().astimezone():
            raise HTTPException(400, "This invite link has expired. Please request a new one.")

    # Check if email matches an existing staff
    staff_info = None
    check_email = email or (invite["email"] if invite else None)
    if check_email:
        staff_res = await db_execute(lambda: db.table("admins").select("id,full_name,email,department,staff_profiles(job_title)").ilike("email", check_email.strip().lower()).limit(1).execute())
        if staff_res.data:
            s_data = staff_res.data[0]
            staff_info = {
                "id": s_data["id"],
                "full_name": s_data["full_name"],
                "email": s_data["email"],
                "department": s_data.get("department"),
                "job_title": (s_data.get("staff_profiles") or [{}])[0].get("job_title"),
            }

    # If rejected, fetch latest submission to pre-fill
    previous_data = None
    if invite and invite["status"] == "rejected":
        prev_res = await db_execute(lambda: db.table("biodata_submissions").select("*").eq("invite_id", invite["id"]).order("created_at", desc=True).limit(1).execute())
        if prev_res.data:
            previous_data = prev_res.data[0]

    return {
        "valid": True,
        "is_general": is_general,
        "invite_email": invite["email"] if invite else None,
        "staff_info": staff_info,
        "previous_data": previous_data,
        "form_message": s["form_message"],
    }


@router.post("/public/submit")
async def submit_biodata(
    request: Request,
    token: str = Form(...),
    email: str = Form(...),
    surname: str = Form(...),
    other_names: str = Form(...),
    marital_status: str = Form(...),
    gender: str = Form(...),
    job_title: str = Form(...),
    date_of_birth: str = Form(...),
    joining_date: str = Form(...),
    present_home_address: str = Form(...),
    mobile_phone: str = Form(...),
    house_phone: str = Form(""),
    next_of_kin_name: str = Form(...),
    next_of_kin_phone: str = Form(...),
    ip_address: str = Form(...),
    device_type: str = Form(...),
    user_agent: str = Form(...),
    coordinates_lat: str = Form(...),
    coordinates_lng: str = Form(...),
    coordinates_accuracy: str = Form(""),
    submitted_at: str = Form(...),
    passport_photo: UploadFile = File(None),
    signature_data: str = Form(...),  # base64 PNG from canvas
):
    db = get_db()

    # Validate token + collecting status
    settings = await db_execute(lambda: db.table("biodata_settings").select("is_collecting,general_link_token").limit(1).execute())
    if not settings.data or not settings.data[0]["is_collecting"]:
        raise HTTPException(403, "Bio data collection is currently closed.")

    s = settings.data[0]
    is_general = token == s.get("general_link_token")
    invite = None
    invite_id = None

    if not is_general:
        inv_res = await db_execute(lambda: db.table("biodata_invites").select("*").eq("token", token).limit(1).execute())
        if not inv_res.data:
            raise HTTPException(404, "Invalid or expired link.")
        invite = inv_res.data[0]
        if invite["status"] in ("submitted", "approved"):
            raise HTTPException(400, "Form already submitted.")
        invite_id = invite["id"]

    # Find staff by email
    email_clean = email.strip().lower()
    staff_res = await db_execute(lambda: db.table("admins").select("id").ilike("email", email_clean).limit(1).execute())
    staff_id = staff_res.data[0]["id"] if staff_res.data else None

    sub_id = str(uuid.uuid4())

    # Upload passport photo
    passport_path = None
    passport_url = None
    if passport_photo and passport_photo.size:
        photo_bytes = await passport_photo.read()
        ext = (passport_photo.filename or "photo.jpg").rsplit(".", 1)[-1].lower()
        path = f"{BIODATA_FOLDER}/{sub_id}/passport.{ext}"
        passport_url = _upload_to_biodata(path, photo_bytes, passport_photo.content_type or "image/jpeg")
        if passport_url:
            passport_path = path

    # Upload signature (base64 → bytes)
    sig_path = None
    sig_url = None
    if signature_data:
        try:
            sig_b64 = signature_data.split(",", 1)[-1] if "," in signature_data else signature_data
            sig_bytes = base64.b64decode(sig_b64)
            path = f"{BIODATA_FOLDER}/{sub_id}/signature.png"
            sig_url = _upload_to_biodata(path, sig_bytes, "image/png")
            if sig_url:
                sig_path = path
        except Exception as e:
            logger.error(f"Signature upload error: {e}")

    # Insert submission
    row = {
        "id": sub_id,
        "invite_id": invite_id,
        "staff_id": staff_id,
        "email": email_clean,
        "surname": surname,
        "other_names": other_names,
        "marital_status": marital_status,
        "gender": gender,
        "job_title": job_title,
        "date_of_birth": date_of_birth,
        "joining_date": joining_date,
        "present_home_address": present_home_address,
        "mobile_phone": mobile_phone,
        "house_phone": house_phone,
        "next_of_kin_name": next_of_kin_name,
        "next_of_kin_phone": next_of_kin_phone,
        "passport_photo_path": passport_path,
        "passport_photo_url": passport_url,
        "signature_path": sig_path,
        "signature_url": sig_url,
        "ip_address": ip_address,
        "device_type": device_type,
        "user_agent": user_agent,
        "coordinates_lat": float(coordinates_lat) if coordinates_lat else None,
        "coordinates_lng": float(coordinates_lng) if coordinates_lng else None,
        "coordinates_accuracy": float(coordinates_accuracy) if coordinates_accuracy else None,
        "submitted_at": submitted_at,
        "status": "pending",
    }
    await db_execute(lambda: db.table("biodata_submissions").insert(row).execute())

    # Mark invite as submitted
    if invite_id:
        await db_execute(lambda: db.table("biodata_invites").update({"status": "submitted", "used_at": datetime.utcnow().isoformat()}).eq("id", invite_id).execute())

    # Notify HR
    try:
        hr_res = await db_execute(lambda: db.table("admins").select("id,email").or_("role.ilike.*hr*,primary_role.ilike.*hr*").eq("is_active", True).limit(5).execute())
        for hr in (hr_res.data or []):
            if hr.get("email"):
                html = _base_email_wrapper(f"""
                  <div style="padding:32px;">
                    <h2 style="color:#0B0C0F;margin:0 0 16px;font-size:20px;font-weight:800;">New Bio Data Submission</h2>
                    <p style="color:#374151;line-height:1.7;">A new employee bio data form has been submitted and is awaiting your review.</p>
                    <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:13px;">
                      <tr><td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #F3F4F6;">Name</td><td style="padding:8px 0;color:#111827;font-weight:700;border-bottom:1px solid #F3F4F6;">{surname} {other_names}</td></tr>
                      <tr><td style="padding:8px 0;color:#6B7280;border-bottom:1px solid #F3F4F6;">Email</td><td style="padding:8px 0;color:#111827;border-bottom:1px solid #F3F4F6;">{email_clean}</td></tr>
                      <tr><td style="padding:8px 0;color:#6B7280;">Submitted</td><td style="padding:8px 0;color:#111827;">{submitted_at}</td></tr>
                    </table>
                    <a href="{APP_BASE_URL}" style="display:inline-block;background:#C47D0A;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:700;font-size:13px;">Review in HR Portal →</a>
                  </div>""")
                await _send_email(hr["email"], f"Bio Data Submitted: {surname} {other_names}", html)
    except Exception as e:
        logger.error(f"HR notification failed: {e}")

    return {"success": True, "submission_id": sub_id}


# ─── HR REVIEW ENDPOINTS ─────────────────────────────────────────────────────

@router.get("/submissions")
async def list_submissions(status: str = None, token=Depends(verify_token)):
    db = get_db()
    q = db.table("biodata_submissions").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    res = await db_execute(lambda: q.execute())
    rows = res.data or []
    # Refresh signed URLs so passport photos and signatures are always viewable
    for row in rows:
        _refresh_submission_urls(row, ttl=7200)  # 2-hour TTL is enough for list view
    return rows


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, token=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("biodata_submissions").select("*").eq("id", submission_id).limit(1).execute())
    if not res.data:
        raise HTTPException(404, "Submission not found")

    row = res.data[0]
    # Refresh with a longer TTL (24 h) so the modal never shows broken images
    _refresh_submission_urls(row, ttl=86400)
    return row


@router.post("/submissions/{submission_id}/review")
async def review_submission(submission_id: str, body: ReviewAction, token=Depends(verify_token)):
    db = get_db()

    sub_res = await db_execute(lambda: db.table("biodata_submissions").select("*").eq("id", submission_id).limit(1).execute())
    if not sub_res.data:
        raise HTTPException(404, "Submission not found")
    sub = sub_res.data[0]

    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "Invalid action")

    new_status = "approved" if body.action == "approve" else "rejected"
    reviewer_id = token.get("sub")

    await db_execute(lambda: db.table("biodata_submissions").update({
        "status": new_status,
        "reviewed_by": reviewer_id,
        "reviewed_at": datetime.utcnow().isoformat(),
        "rejection_reason": body.rejection_reason if body.action == "reject" else None,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", submission_id).execute())

    # Update invite status so they can/cannot re-submit
    if sub.get("invite_id"):
        await db_execute(lambda: db.table("biodata_invites").update({"status": new_status}).eq("id", sub["invite_id"]).execute())

    # If approved → update staff profile
    if body.action == "approve" and sub.get("staff_id"):
        staff_id = sub["staff_id"]
        try:
            # Update admins table name fields
            name_update = {}
            if sub.get("surname") or sub.get("other_names"):
                name_update["full_name"] = f"{sub.get('surname','')} {sub.get('other_names','')}".strip()
            if name_update:
                await db_execute(lambda: db.table("admins").update(name_update).eq("id", staff_id).execute())

            # Upsert staff_profiles
            profile_update = {
                "admin_id": staff_id,
                "gender": sub.get("gender"),
                "dob": sub.get("date_of_birth"),
                "marital_status": sub.get("marital_status"),
                "job_title": sub.get("job_title"),
                "phone_number": sub.get("mobile_phone"),
                "address": sub.get("present_home_address"),
                "emergency_contact": sub.get("next_of_kin_name"),
                "passport_photo_path": sub.get("passport_photo_path"),
                "signature_path": sub.get("signature_path"),
                "updated_at": datetime.utcnow().isoformat(),
            }
            # Check existing profile
            prof_res = await db_execute(lambda: db.table("staff_profiles").select("id").eq("admin_id", staff_id).limit(1).execute())
            if prof_res.data:
                await db_execute(lambda: db.table("staff_profiles").update({k: v for k, v in profile_update.items() if k != "admin_id"}).eq("admin_id", staff_id).execute())
            else:
                await db_execute(lambda: db.table("staff_profiles").insert(profile_update).execute())
        except Exception as e:
            logger.error(f"Profile update after biodata approval failed: {e}")

    # Send email notification
    full_name = f"{sub.get('surname', '')} {sub.get('other_names', '')}".strip() or sub.get("email")
    try:
        if body.action == "approve":
            await _send_email(sub["email"], "Your Bio Data Has Been Approved", _approval_email_html(full_name))
        else:
            await _send_email(sub["email"], "Your Bio Data Requires Revision", _rejection_email_html(full_name, body.rejection_reason or "Please contact HR for details."))
    except Exception as e:
        logger.error(f"Review notification email failed: {e}")

    return {"success": True, "status": new_status}


@router.post("/submissions/{submission_id}/email-certificate")
async def email_certificate(submission_id: str, body: EmailCertificate, token=Depends(verify_token)):
    db = get_db()
    sub_res = await db_execute(lambda: db.table("biodata_submissions").select("*").eq("id", submission_id).limit(1).execute())
    if not sub_res.data:
        raise HTTPException(404, "Not found")
    sub = sub_res.data[0]

    # Refresh both passport photo and signature with a 7-day TTL for email delivery
    _refresh_submission_urls(sub, ttl=604800)

    cert_html = _build_certificate_html(sub)
    await _send_email(
        body.to_email,
        f"Bio Data Authenticity Certificate — {sub.get('surname')} {sub.get('other_names')}",
        cert_html,
    )
    return {"success": True}


def _build_certificate_html(sub: dict) -> str:
    name = f"{sub.get('surname', '')} {sub.get('other_names', '')}".strip()
    submitted = sub.get("submitted_at", "")[:19].replace("T", " ") if sub.get("submitted_at") else "N/A"
    lat = sub.get("coordinates_lat")
    lng = sub.get("coordinates_lng")
    coords = f"{lat:.6f}, {lng:.6f}" if lat and lng else "Not captured"

    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;background:#fff;border:2px solid #C47D0A;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#0B0C0F 0%,#1A1D24 100%);padding:40px;text-align:center;">
        <div style="font-size:11px;letter-spacing:3px;color:#C47D0A;margin-bottom:8px;text-transform:uppercase;">Official Document</div>
        <h1 style="color:#fff;margin:0;font-size:26px;font-weight:900;letter-spacing:-0.5px;">Bio Data Authenticity Certificate</h1>
        <div style="color:#9CA3AF;font-size:13px;margin-top:8px;">Eximp &amp; Cloves Infrastructure Limited</div>
        <div style="width:80px;height:3px;background:#C47D0A;border-radius:2px;margin:16px auto 0;"></div>
      </div>
      <div style="padding:40px;">
        <p style="color:#374151;line-height:1.7;font-size:14px;margin:0 0 28px;">
          This certifies that the following employee bio data was electronically submitted and verified through the Eximp &amp; Cloves HR System with the following authenticity metadata:
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:28px;">
          <tr style="background:#F9FAFB;"><td style="padding:12px 16px;color:#6B7280;font-weight:600;width:45%;border-bottom:1px solid #E5E7EB;">Employee Name</td><td style="padding:12px 16px;color:#111827;font-weight:700;border-bottom:1px solid #E5E7EB;">{name}</td></tr>
          <tr><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">Email Address</td><td style="padding:12px 16px;color:#111827;border-bottom:1px solid #E5E7EB;">{sub.get('email','')}</td></tr>
          <tr style="background:#F9FAFB;"><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">Job Title</td><td style="padding:12px 16px;color:#111827;border-bottom:1px solid #E5E7EB;">{sub.get('job_title','')}</td></tr>
          <tr><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">Submission Timestamp</td><td style="padding:12px 16px;color:#111827;font-weight:700;border-bottom:1px solid #E5E7EB;">{submitted}</td></tr>
          <tr style="background:#F9FAFB;"><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">IP Address</td><td style="padding:12px 16px;color:#111827;font-family:monospace;border-bottom:1px solid #E5E7EB;">{sub.get('ip_address','N/A')}</td></tr>
          <tr><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">Device Type</td><td style="padding:12px 16px;color:#111827;border-bottom:1px solid #E5E7EB;">{sub.get('device_type','N/A')}</td></tr>
          <tr style="background:#F9FAFB;"><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">User Agent</td><td style="padding:12px 16px;color:#111827;font-size:11px;word-break:break-all;border-bottom:1px solid #E5E7EB;">{sub.get('user_agent','N/A')}</td></tr>
          <tr><td style="padding:12px 16px;color:#6B7280;font-weight:600;border-bottom:1px solid #E5E7EB;">GPS Coordinates</td><td style="padding:12px 16px;color:#111827;font-family:monospace;border-bottom:1px solid #E5E7EB;">{coords}</td></tr>
          <tr style="background:#F9FAFB;"><td style="padding:12px 16px;color:#6B7280;font-weight:600;">Review Status</td><td style="padding:12px 16px;"><span style="background:{'#D1FAE5' if sub.get('status')=='approved' else '#FEE2E2'};color:{'#065F46' if sub.get('status')=='approved' else '#991B1B'};padding:4px 12px;border-radius:99px;font-size:11px;font-weight:800;text-transform:uppercase;">{sub.get('status','pending')}</span></td></tr>
        </table>
        {f'<div style="margin-bottom:28px;padding:16px;background:#F9FAFB;border-radius:8px;border:1px solid #E5E7EB;"><div style="font-size:11px;color:#6B7280;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Employee Signature</div><img src="{sub["signature_url"]}" style="max-height:80px;max-width:300px;" /></div>' if sub.get("signature_url") else ""}
        <div style="border-top:2px solid #E5E7EB;padding-top:24px;text-align:center;">
          <div style="font-size:11px;color:#9CA3AF;line-height:1.8;">
            Certificate ID: {sub.get('id','')}<br>
            Issued by: Eximp &amp; Cloves HR System<br>
            This is an electronically generated certificate and is valid without a physical signature.
          </div>
        </div>
      </div>
    </div>"""


# ─── STAFF VIEW: own submission ───────────────────────────────────────────────

@router.get("/my-submission")
async def get_my_submission(token=Depends(verify_token)):
    db = get_db()
    staff_id = token.get("sub")
    res = await db_execute(lambda: db.table("biodata_submissions").select("*").eq("staff_id", staff_id).order("created_at", desc=True).limit(1).execute())
    if not res.data:
        return None
    return res.data[0]