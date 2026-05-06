"""
routers/guarantor.py  — DROP-IN REPLACEMENT

Key fixes vs. original:
  1. /public/save-partial now accepts passport_photo + id_document as
     optional UploadFile fields so guarantor photos are stored correctly.
  2. /public/check returns both submission AND staff_info even when a
     submission already exists (needed by the frontend relay-link flow).
  3. /general-link builds the URL from APP_BASE_URL correctly for any
     deployment (no hard-coded trailing /hr assumption).
  4. /submissions/{id}/review supports section-level accept/reject
     (sections a, b, c) AND overall status changes.
  5. New endpoint: POST /submissions/{id}/bulk-review — approve or reject
     all sections in one call (used by "Approve All / Reject All" in the HR modal).
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
import uuid
import os
import base64
import json
from datetime import datetime, timedelta, timezone
from storage_service import upload_portal_file, generate_signed_url, PORTAL_CLAIMS_BUCKET
from typing import Optional

router = APIRouter()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_base_url(request: Request) -> str:
    """Return APP_BASE_URL env var, or derive it from the request."""
    base = os.getenv("APP_BASE_URL", "").rstrip("/")
    if base:
        return base
    # Derive from request (works for local dev)
    return str(request.base_url).rstrip("/")


def _sign_sub(sub: dict) -> dict:
    """Generate signed URLs for a submission dict in-place."""
    sub["employee_signature_url"] = generate_signed_url(
        PORTAL_CLAIMS_BUCKET, sub.get("employee_signature_url")
    )
    return sub


def _sign_guarantor(g: dict) -> dict:
    for field in ["passport_photo_url", "id_document_url", "signature_url"]:
        g[field] = generate_signed_url(PORTAL_CLAIMS_BUCKET, g.get(field))
    return g


# ── Admin Endpoints ───────────────────────────────────────────────────────────

@router.get("/submissions")
async def get_submissions(current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    res = await db_execute(
        lambda: db.table("guarantor_submissions")
        .select("*, guarantors(count)")
        .order("submitted_at", desc=True)
        .execute()
    )
    for item in res.data:
        item["guarantors_count"] = (
            item["guarantors"][0]["count"] if item.get("guarantors") else 0
        )
        item.pop("guarantors", None)
    return res.data


@router.get("/submissions/{id}")
async def get_submission_detail(id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()

    sub_res = await db_execute(
        lambda: db.table("guarantor_submissions").select("*").eq("id", id).execute()
    )
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub = sub_res.data[0]
    _sign_sub(sub)

    g_res = await db_execute(
        lambda: db.table("guarantors")
        .select("*")
        .eq("submission_id", id)
        .order("slot_number")
        .execute()
    )

    sub["guarantor1"] = None
    sub["guarantor2"] = None
    for g in g_res.data:
        _sign_guarantor(g)
        slot = g.get("slot_number", 1)
        sub[f"guarantor{slot}"] = g

    return sub


@router.post("/submissions/{id}/review")
async def review_submission(id: str, data: dict, current_admin=Depends(verify_token)):
    """
    Section-level or overall review.
    data = { section: "a" | "b" | "c" | "overall", status: "approved"|"rejected"|"pending", reason?: str }
    """
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    section = data.get("section")
    status  = data.get("status")
    reason  = data.get("reason", "")

    if status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")

    db = get_db()

    update = {
        "reviewed_at": datetime.utcnow().isoformat(),
        "reviewed_by": current_admin["sub"],
    }

    if section in ("a", "b", "c"):
        update[f"section_{section}_status"] = status
        update[f"section_{section}_reason"] = reason
    else:
        # Overall status
        update["status"] = status

    res = await db_execute(
        lambda: db.table("guarantor_submissions").update(update).eq("id", id).execute()
    )

    # Notify employee
    try:
        sub_res = await db_execute(
            lambda: db.table("guarantor_submissions")
            .select("employee_email")
            .eq("id", id)
            .execute()
        )
        if sub_res.data:
            emp_email = sub_res.data[0]["employee_email"]
            admin_res = await db_execute(
                lambda: db.table("admins").select("id").eq("email", emp_email).execute()
            )
            if admin_res.data:
                labels = {"a": "Employee Details", "b": "Guarantor 1", "c": "Guarantor 2"}
                sec_label = labels.get(section, "Submission")
                msg = f"Your Guarantor Form ({sec_label}) has been {status}."
                if status == "rejected" and reason:
                    msg += f" Reason: {reason}"
                await db_execute(
                    lambda: db.table("notifications").insert({
                        "staff_id": admin_res.data[0]["id"],
                        "type": "guarantor_update",
                        "message": msg,
                    }).execute()
                )
    except Exception:
        pass  # Notification failure should not block the review

    return res.data[0] if res.data else {"status": "ok"}


@router.post("/submissions/{id}/bulk-review")
async def bulk_review_submission(id: str, data: dict, current_admin=Depends(verify_token)):
    """
    Approve or reject ALL sections (a, b, c) plus overall status in one call.
    data = { status: "approved" | "rejected", reason?: str }
    """
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    status = data.get("status")
    reason = data.get("reason", "")
    if status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be 'approved' or 'rejected'")

    db = get_db()
    update = {
        "reviewed_at": datetime.utcnow().isoformat(),
        "reviewed_by": current_admin["sub"],
        "status": status,
        "section_a_status": status,
        "section_a_reason": reason,
        "section_b_status": status,
        "section_b_reason": reason,
        "section_c_status": status,
        "section_c_reason": reason,
    }

    res = await db_execute(
        lambda: db.table("guarantor_submissions").update(update).eq("id", id).execute()
    )

    # Notify employee
    try:
        sub_res = await db_execute(
            lambda: db.table("guarantor_submissions")
            .select("employee_email")
            .eq("id", id)
            .execute()
        )
        if sub_res.data:
            emp_email = sub_res.data[0]["employee_email"]
            admin_res = await db_execute(
                lambda: db.table("admins").select("id").eq("email", emp_email).execute()
            )
            if admin_res.data:
                msg = f"Your Guarantor Form has been {status} by HR."
                if status == "rejected" and reason:
                    msg += f" Reason: {reason}"
                await db_execute(
                    lambda: db.table("notifications").insert({
                        "staff_id": admin_res.data[0]["id"],
                        "type": "guarantor_update",
                        "message": msg,
                    }).execute()
                )
    except Exception:
        pass

    return res.data[0] if res.data else {"status": "ok"}


@router.get("/invites")
async def get_invites(current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    res = await db_execute(
        lambda: db.table("guarantor_invites").select("*").order("created_at", desc=True).execute()
    )
    return res.data


@router.post("/invites")
async def create_invite(data: dict, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    email = data.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    token      = str(uuid.uuid4())
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

    res = await db_execute(
        lambda: db.table("guarantor_invites").insert({
            "email":      email,
            "token":      token,
            "expires_at": expires_at,
            "created_by": current_admin["sub"],
        }).execute()
    )
    return res.data[0]


@router.get("/general-link")
async def get_general_link(request: Request):
    db = get_db()
    settings_res = await db_execute(
        lambda: db.table("guarantor_settings").select("*").limit(1).execute()
    )
    if not settings_res.data:
        return {"link": "", "is_collecting": False}

    settings = settings_res.data[0]
    base_url  = _build_base_url(request)

    # The frontend serves the guarantor form at /?guarantor_token=... (not /hr)
    # Use APP_BASE_URL env var to configure the correct public URL for your deployment.
    link = f"{base_url}?guarantor_token={settings['general_link_token']}"

    return {
        "link":         link,
        "is_collecting": settings["is_collecting"],
    }


@router.patch("/settings")
async def update_settings(data: dict, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()

    update_data = {}
    if "is_collecting" in data:
        update_data["is_collecting"] = data["is_collecting"]

    settings_res = await db_execute(
        lambda: db.table("guarantor_settings").select("id").limit(1).execute()
    )
    if not settings_res.data:
        raise HTTPException(status_code=404, detail="Settings record not found")

    res = await db_execute(
        lambda: db.table("guarantor_settings")
        .update(update_data)
        .eq("id", settings_res.data[0]["id"])
        .execute()
    )
    return res.data[0]


# ── Public Endpoints ──────────────────────────────────────────────────────────

@router.get("/public/check")
async def check_public_token(token: str, email: str):
    db = get_db()
    settings_res = await db_execute(
        lambda: db.table("guarantor_settings").select("*").limit(1).execute()
    )
    if not settings_res.data or not settings_res.data[0]["is_collecting"]:
        raise HTTPException(
            status_code=403,
            detail="Guarantor form collection is currently closed. Please contact HR.",
        )

    settings   = settings_res.data[0]
    is_general = token == settings["general_link_token"]

    if not is_general:
        invite_res = await db_execute(
            lambda: db.table("guarantor_invites")
            .select("*")
            .eq("token", token)
            .eq("email", email)
            .execute()
        )
        if not invite_res.data:
            raise HTTPException(
                status_code=404, detail="Invalid invitation link or email address."
            )
        invite = invite_res.data[0]
        if invite["status"] != "pending":
            raise HTTPException(
                status_code=400, detail="This invitation link has already been used."
            )
        expires_at = datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="This invitation link has expired.")

    # Load submission (if any) for this email
    sub_res = await db_execute(
        lambda: db.table("guarantor_submissions")
        .select("*, guarantors(*)")
        .eq("employee_email", email)
        .execute()
    )

    submission = None
    if sub_res.data:
        submission = sub_res.data[0]
        _sign_sub(submission)

        guarantors = submission.pop("guarantors", []) or []
        submission["g1"] = next((g for g in guarantors if g["slot_number"] == 1), None)
        submission["g2"] = next((g for g in guarantors if g["slot_number"] == 2), None)
        for key in ("g1", "g2"):
            if submission[key]:
                _sign_guarantor(submission[key])

    # Always try to load staff info (used to pre-fill the form)
    staff_info = None
    staff_res = await db_execute(
        lambda: db.table("admins")
        .select("id, full_name, role, department")
        .eq("email", email)
        .execute()
    )
    if staff_res.data:
        staff_info = staff_res.data[0]
        profile_res = await db_execute(
            lambda: db.table("staff_profiles")
            .select("*")
            .eq("admin_id", staff_info["id"])
            .execute()
        )
        profile = profile_res.data[0] if profile_res.data else {}
        staff_info["staff_id"]  = profile.get("staff_id", "")
        staff_info["job_title"] = profile.get("job_title") or staff_info.get("role", "")

    return {
        "status":     "ok",
        "staff_info": staff_info,
        "submission": submission,
        "is_general": is_general,
    }


@router.post("/public/save-partial")
async def save_partial_submission(
    request:        Request,
    token:          str           = Form(...),
    email:          str           = Form(...),
    section:        str           = Form(...),   # "employee" | "g1" | "g2"
    data:           str           = Form(...),   # JSON string
    passport_photo: Optional[UploadFile] = File(None),
    id_document:    Optional[UploadFile] = File(None),
):
    fields = json.loads(data)
    db     = get_db()

    # Resolve or create submission ID
    sub_res = await db_execute(
        lambda: db.table("guarantor_submissions")
        .select("id")
        .eq("employee_email", email)
        .execute()
    )
    submission_id = sub_res.data[0]["id"] if sub_res.data else str(uuid.uuid4())

    async def _upload_file(file: Optional[UploadFile], name: str) -> Optional[str]:
        if not file:
            return None
        try:
            content = await file.read()
            path    = f"guarantors/{submission_id}/{name}_{file.filename}"
            upload_portal_file(path, content, file.content_type)
            return path
        except Exception:
            return None

    def _upload_sig(b64: Optional[str], name: str) -> Optional[str]:
        if not b64 or "," not in b64:
            return None
        try:
            img_data = base64.b64decode(b64.split(",")[1])
            path     = f"guarantors/{submission_id}/{name}.png"
            upload_portal_file(path, img_data, "image/png")
            return path
        except Exception:
            return None

    # ── EMPLOYEE SECTION ──────────────────────────────────────────────────
    if section == "employee":
        sig_path = _upload_sig(fields.get("signature"), "employee_sig")

        payload: dict = {
            "id":                   submission_id,
            "employee_name":        fields.get("full_name"),
            "employee_email":       email,
            "position":             fields.get("position"),
            "staff_id":             fields.get("staff_id"),
            "date_of_employment":   fields.get("date_of_employment"),
            "employee_phone":       fields.get("phone"),
            "employee_address":     fields.get("address"),
            "section_a_status":     "pending",
            "submitted_at":         datetime.utcnow().isoformat(),
        }
        if sig_path:
            payload["employee_signature_url"] = sig_path

        await db_execute(
            lambda: db.table("guarantor_submissions").upsert(payload).execute()
        )

    # ── GUARANTOR SECTIONS ────────────────────────────────────────────────
    elif section in ("g1", "g2"):
        slot    = 1 if section == "g1" else 2
        sig_key = f"g{slot}_sig"

        sig_path      = _upload_sig(fields.get("signature"), sig_key)
        passport_path = await _upload_file(passport_photo, f"g{slot}_passport")
        id_doc_path   = await _upload_file(id_document,    f"g{slot}_id")

        g_payload: dict = {
            "submission_id":    submission_id,
            "slot_number":      slot,
            "full_name":        fields.get("full_name"),
            "relationship":     fields.get("relationship"),
            "address":          fields.get("address"),
            "occupation":       fields.get("occupation"),
            "employer_name":    fields.get("employer_name"),
            "position_held":    fields.get("position_held"),
            "years_at_job":     fields.get("years_at_job"),
            "phone":            fields.get("phone"),
            "email":            fields.get("email"),
            "id_type":          fields.get("id_type"),
            "id_number":        fields.get("id_number"),
            "witness_name":     fields.get("witness_name"),
            "witness_occupation": fields.get("witness_occupation"),
            "witness_phone":    fields.get("witness_phone"),
            "witness_address":  fields.get("witness_address"),
            "witness_date":     fields.get("witness_date"),
        }
        if sig_path:
            g_payload["signature_url"] = sig_path
        if passport_path:
            g_payload["passport_photo_url"] = passport_path
        if id_doc_path:
            g_payload["id_document_url"] = id_doc_path

        await db_execute(
            lambda: db.table("guarantors")
            .upsert(g_payload, on_conflict="submission_id, slot_number")
            .execute()
        )

        # Reset section status to pending (so HR knows to re-review)
        sec_col = "section_b_status" if section == "g1" else "section_c_status"
        await db_execute(
            lambda: db.table("guarantor_submissions")
            .update({sec_col: "pending"})
            .eq("id", submission_id)
            .execute()
        )

        # Notify employee
        try:
            admin_res = await db_execute(
                lambda: db.table("admins").select("id").eq("email", email).execute()
            )
            if admin_res.data:
                g_name = fields.get("full_name") or f"Guarantor {slot}"
                await db_execute(
                    lambda: db.table("notifications").insert({
                        "staff_id": admin_res.data[0]["id"],
                        "type":     "guarantor_submission",
                        "message":  f"{g_name} has completed their part of your Guarantor Form.",
                    }).execute()
                )
        except Exception:
            pass

    # Build relay link using APP_BASE_URL
    base_url   = _build_base_url(request)
    relay_link = f"{base_url}?guarantor_token={token}&email={email}"

    return {
        "status":        "success",
        "submission_id": submission_id,
        "relay_link":    relay_link,
    }


@router.get("/company-info")
async def get_company_info():
    return {
        "name":       "Eximp & Cloves Infrastructure Limited",
        "address":    "57B, Isaac John Street, Yaba, Lagos",
        "rc":         "RC 8311800",
        "phone":      "+234 912 686 4383",
        "email_addr": "hr@eximps-cloves.com",
    }