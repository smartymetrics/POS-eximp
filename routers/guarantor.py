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
    """
    Return the public frontend base URL.
    The Vite app is built with base: '/hr/' so all links must include /hr/.
    Set APP_BASE_URL=https://yourapp.com in .env — the /hr/ is appended automatically.
    Example result: https://yourapp.com/hr
    """
    base = os.getenv("APP_BASE_URL", "").rstrip("/")
    if not base:
        # Derive from request origin (works for local dev / reverse proxy)
        base = str(request.base_url).rstrip("/")
    # The frontend is always mounted at /hr/ (vite base: '/hr/')
    if not base.endswith("/hr"):
        base = f"{base}/hr"
    return base


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

@router.get("/my-submission")
async def get_my_submission(current_user=Depends(verify_token)):
    """Fetch the guarantor submission and invite token for the current logged-in staff."""
    db = get_db()
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="User email not found in token")

    # 1. Get submission
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

    # 2. Get invite token (to build the re-fill link)
    inv_res = await db_execute(
        lambda: db.table("guarantor_invites")
        .select("token")
        .eq("email", email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    token = inv_res.data[0]["token"] if inv_res.data else None

    # 3. Get general link if no personal token exists
    if not token:
        settings_res = await db_execute(
            lambda: db.table("guarantor_settings").select("general_link_token").limit(1).execute()
        )
        if settings_res.data:
            token = settings_res.data[0]["general_link_token"]

    return {
        "submission": submission,
        "token": token,
        "email": email
    }

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

            # Send rejection email with a direct re-fill link
            if status == "rejected":
                inv_res = await db_execute(
                    lambda: db.table("guarantor_invites")
                    .select("token")
                    .eq("email", emp_email)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if inv_res.data:
                    invite_token = inv_res.data[0]["token"]
                    base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
                    if not base_url.endswith("/hr"):
                        base_url = f"{base_url}/hr"
                    form_link = f"{base_url}/?guarantor_token={invite_token}&email={emp_email}"
                    labels = {"a": "Employee Details (Section A)", "b": "Guarantor 1 (Section B)", "c": "Guarantor 2 (Section C)"}
                    sec_label = labels.get(section, "a section")
                    await _send_guarantor_rejection_email(
                        emp_email, sec_label, reason, form_link
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

            # Send rejection email with a direct re-fill link for all sections
            if status == "rejected":
                inv_res = await db_execute(
                    lambda: db.table("guarantor_invites")
                    .select("token")
                    .eq("email", emp_email)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if inv_res.data:
                    invite_token = inv_res.data[0]["token"]
                    base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
                    if not base_url.endswith("/hr"):
                        base_url = f"{base_url}/hr"
                    form_link = f"{base_url}/?guarantor_token={invite_token}&email={emp_email}"
                    await _send_guarantor_rejection_email(
                        emp_email, "All Sections", reason, form_link
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
async def create_invite(data: dict, request: Request, current_admin=Depends(verify_token)):
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

    # ── Send the invite email ───────────────────────────────────────────────
    try:
        base_url   = _build_base_url(request)
        form_link  = f"{base_url}/?guarantor_token={token}&email={email}"
        inviter_name = current_admin.get("name") or current_admin.get("email") or "HR"
        await _send_guarantor_invite_email(email, inviter_name, form_link)
    except Exception as e:
        # Log but don't fail — the invite is already saved; HR can share the link manually
        import logging
        logging.getLogger(__name__).error(f"Guarantor invite email failed for {email}: {e}")

    return res.data[0]



async def _send_guarantor_rejection_email(
    email_addr: str, section_label: str, reason: str, form_link: str
):
    """Send a rejection email to the employee with a direct link to re-fill the rejected section(s)."""
    import resend
    resend.api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "hr@eximps-cloves.com")

    reason_block = f"""
                <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:3px;padding:16px 20px;margin:20px 0;color:#DC2626;font-size:13px;line-height:1.7;">
                  <strong>Reason:</strong> {reason}
                </div>""" if reason else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#F5F0E8;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0E8;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:4px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <!-- Header -->
            <tr>
              <td style="background:#0D1B2A;padding:0;border-left:6px solid #DC2626;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding:28px 36px;">
                      <div style="font-size:18px;font-weight:800;color:#ffffff;letter-spacing:-0.3px;">Eximp &amp; Cloves Infrastructure Limited</div>
                      <div style="font-size:10px;color:#DC2626;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-top:4px;">Human Resources Division</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <!-- Body -->
            <tr>
              <td style="padding:40px 36px;">
                <div style="width:56px;height:56px;background:#FEE2E2;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:20px;font-size:26px;text-align:center;line-height:56px;">✕</div>
                <p style="font-size:13px;color:#DC2626;margin:0 0 8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;">Action Required</p>
                <h1 style="font-size:22px;font-weight:800;color:#0D1B2A;margin:0 0 20px;line-height:1.3;">Guarantor Form — Revision Needed</h1>
                <p style="font-size:14px;color:#374151;line-height:1.8;margin:0 0 12px;">Dear Employee,</p>
                <p style="font-size:14px;color:#374151;line-height:1.8;margin:0 0 16px;">
                  HR has reviewed your Guarantor Form and requires a revision for the following section:
                  <strong>{section_label}</strong>.
                </p>
                {reason_block}
                <p style="font-size:14px;color:#374151;line-height:1.8;margin:0 0 28px;">
                  Please use the button below to return to your form, correct the flagged section(s), and re-sign where required.
                </p>
                <!-- CTA -->
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center" style="padding:0 0 28px;">
                      <a href="{form_link}" style="display:inline-block;background:#B8860B;color:#ffffff;text-decoration:none;padding:16px 40px;border-radius:3px;font-size:14px;font-weight:700;letter-spacing:0.5px;">
                        Return to Form &amp; Re-sign &rarr;
                      </a>
                    </td>
                  </tr>
                </table>
                <!-- Link fallback -->
                <div style="background:#F8F9FB;border:1px solid #E8E2D9;border-radius:3px;padding:16px 18px;margin-bottom:24px;">
                  <p style="font-size:11px;color:#6B7280;margin:0 0 6px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">Or copy this link into your browser</p>
                  <p style="font-size:12px;color:#B8860B;margin:0;word-break:break-all;font-family:monospace;">{form_link}</p>
                </div>
                <div style="background:#FEF9EC;border:1px solid #B8860B;border-radius:3px;padding:14px 18px;">
                  <p style="font-size:13px;font-weight:800;color:#92640A;margin:0 0 4px;">⚠ Remember — Login Required</p>
                  <p style="font-size:13px;color:#78510A;line-height:1.7;margin:0;">
                    Ensure you are already logged into your staff account before opening the link.
                  </p>
                </div>
              </td>
            </tr>
            <!-- Footer -->
            <tr>
              <td style="background:#F8F9FB;border-top:1px solid #E8E2D9;padding:20px 36px;">
                <p style="font-size:11px;color:#9CA3AF;margin:0;line-height:1.6;">
                  <strong style="color:#6B7280;">Eximp &amp; Cloves Infrastructure Limited</strong><br>
                  RC 8311800 &nbsp;|&nbsp; 57B, Isaac John Street, Yaba, Lagos &nbsp;|&nbsp; +234 912 686 4383<br>
                  This is an automated HR system notification.
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: resend.Emails.send({{
        "from":     f"Eximp & Cloves HR <{{from_email}}>",
        "to":       [email_addr],
        "subject":  f"Action Required: Guarantor Form Revision — {{section_label}}",
        "html":     html,
        "reply_to": "hr@eximps-cloves.com",
    }}))


async def _send_guarantor_invite_email(email_addr: str, inviter_name: str, form_link: str):
    """Send a professional guarantor form invitation email via Resend."""
    import resend
    resend.api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "hr@eximps-cloves.com")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#F5F0E8;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0E8;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:4px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

            <!-- Header bar -->
            <tr>
              <td style="background:#0D1B2A;padding:0 0 0 0;border-left:6px solid #B8860B;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding:28px 36px;">
                      <div style="font-size:18px;font-weight:800;color:#ffffff;letter-spacing:-0.3px;">
                        Eximp &amp; Cloves Infrastructure Limited
                      </div>
                      <div style="font-size:10px;color:#B8860B;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-top:4px;">
                        Human Resources Division
                      </div>
                    </td>
                    <td align="right" style="padding:28px 36px;">
                      <div style="display:inline-block;border:1px solid #B8860B;color:#B8860B;font-size:9px;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:5px 12px;border-radius:2px;">
                        Confidential
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding:40px 36px;">
                <p style="font-size:13px;color:#6B7280;margin:0 0 8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;">
                  Official HR Communication
                </p>
                <h1 style="font-size:24px;font-weight:800;color:#0D1B2A;margin:0 0 24px;line-height:1.2;">
                  Guarantor Form Submission Required
                </h1>

                <p style="font-size:14px;color:#374151;line-height:1.8;margin:0 0 16px;">
                  Dear Employee,
                </p>
                <p style="font-size:14px;color:#374151;line-height:1.8;margin:0 0 16px;">
                  As part of your employment documentation process, you are required to complete the
                  <strong>Employee Guarantor's Form</strong>. This form must be filled out by you
                  and two independent guarantors before your file can be considered complete.
                </p>
                <p style="font-size:14px;color:#374151;line-height:1.8;margin:0 0 32px;">
                  Please click the button below to access your secure, personalised form. Once you
                  complete your section, a link will be generated for you to share with your guarantors.
                </p>

                <!-- CTA Button -->
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center" style="padding:0 0 32px;">
                      <a href="{form_link}"
                         style="display:inline-block;background:#0D1B2A;color:#ffffff;text-decoration:none;padding:16px 40px;border-radius:3px;font-size:14px;font-weight:700;letter-spacing:0.5px;">
                        Open Guarantor Form &rarr;
                      </a>
                    </td>
                  </tr>
                </table>

                <!-- Link fallback -->
                <div style="background:#F8F9FB;border:1px solid #E8E2D9;border-radius:3px;padding:16px 18px;margin-bottom:28px;">
                  <p style="font-size:11px;color:#6B7280;margin:0 0 6px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">
                    Or copy this link into your browser
                  </p>
                  <p style="font-size:12px;color:#B8860B;margin:0;word-break:break-all;font-family:monospace;">
                    {form_link}
                  </p>
                </div>

                <!-- Login Notice -->
                <div style="background:#FEF9EC;border:1px solid #B8860B;border-radius:3px;padding:16px 20px;margin-bottom:20px;">
                  <p style="font-size:13px;font-weight:800;color:#92640A;margin:0 0 6px;">⚠ Important — Login Required</p>
                  <p style="font-size:13px;color:#78510A;line-height:1.7;margin:0;">
                    This form requires you to be logged in to the company portal.
                    <strong>Before clicking the link or copying it into your browser, please ensure you are already
                    logged in to your staff account at
                    <a href="https://app.eximps-cloves.com/hr" style="color:#B8860B;">app.eximps-cloves.com/hr</a>.</strong>
                    Once logged in, then open or paste the form link in the same browser.
                  </p>
                </div>

                <!-- Instructions -->
                <div style="border-left:3px solid #B8860B;padding:16px 20px;background:#FDFBF7;margin-bottom:28px;">
                  <p style="font-size:13px;font-weight:700;color:#0D1B2A;margin:0 0 10px;">How to complete your form</p>
                  <ol style="font-size:13px;color:#374151;line-height:1.9;margin:0;padding-left:18px;">
                    <li>Log in to your staff account at <a href="https://app.eximps-cloves.com/hr" style="color:#B8860B;">app.eximps-cloves.com/hr</a> first.</li>
                    <li>Once logged in, click the button above <em>in the same browser</em>, or copy and paste the link below into that browser.</li>
                    <li>Verify your identity with your company email address on the form.</li>
                    <li>Complete <strong>Section A</strong> — your personal employment details and signature.</li>
                    <li>Share the generated link with your <strong>two guarantors</strong> to complete Sections B &amp; C.</li>
                  </ol>
                </div>

                <p style="font-size:13px;color:#9CA3AF;line-height:1.7;margin:0;">
                  This link is unique to your account and expires in <strong>7 days</strong>.
                  If you have any questions, please contact HR at
                  <a href="mailto:hr@eximps-cloves.com" style="color:#B8860B;">hr@eximps-cloves.com</a>.
                </p>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background:#F8F9FB;border-top:1px solid #E8E2D9;padding:20px 36px;">
                <p style="font-size:11px;color:#9CA3AF;margin:0;line-height:1.6;">
                  <strong style="color:#6B7280;">Eximp &amp; Cloves Infrastructure Limited</strong><br>
                  RC 8311800 &nbsp;|&nbsp; 57B, Isaac John Street, Yaba, Lagos &nbsp;|&nbsp; +234 912 686 4383<br>
                  This email was sent by {inviter_name} via the HR Management System.
                  It contains confidential employment information intended solely for the named recipient.
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: resend.Emails.send({
        "from":     f"Eximp & Cloves HR <{from_email}>",
        "to":       [email_addr],
        "subject":  "Action Required: Complete Your Employee Guarantor Form",
        "html":     html,
        "reply_to": "hr@eximps-cloves.com",
    }))


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

    # The Vite app is mounted at /hr/ so the public form URL is /hr/?guarantor_token=...
    link = f"{base_url}/?guarantor_token={settings['general_link_token']}"

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
            # Allow re-access if any section on their submission was rejected by HR
            sub_check_res = await db_execute(
                lambda: db.table("guarantor_submissions")
                .select("section_a_status,section_b_status,section_c_status")
                .eq("employee_email", email)
                .limit(1)
                .execute()
            )
            has_rejected_section = False
            if sub_check_res.data:
                s = sub_check_res.data[0]
                has_rejected_section = any(
                    s.get(f"section_{x}_status") == "rejected" for x in ("a", "b", "c")
                )
            if not has_rejected_section:
                raise HTTPException(
                    status_code=400,
                    detail="This invitation link has already been used.",
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

    # Build relay link — the Vite app is mounted at /hr/
    base_url   = _build_base_url(request)
    relay_link = f"{base_url}/?guarantor_token={token}&email={email}"

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