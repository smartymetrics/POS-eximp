from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form, Request
from typing import List, Optional
from pydantic import EmailStr
from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
from datetime import datetime
import uuid
from email_service import async_resend, FROM_EMAIL, send_refund_request_admin_email, send_refund_request_confirmation_email, send_refund_status_update_email
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

REFUND_BUCKET = "refund_receipts"


async def _upload_file_to_bucket_bytes(file_bytes: bytes, filename: str, content_type: str, prefix: str) -> str:
    unique_id = str(uuid.uuid4())[:8]
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    stored_path = f"{prefix}/{unique_id}_{safe_name}"
    from database import supabase
    supabase.storage.from_(REFUND_BUCKET).upload(path=stored_path, file=file_bytes, file_options={"content-type": content_type})
    return stored_path


@router.post("/public/submit")
async def submit_refund_request(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: EmailStr = Form(...),
    phone: str = Form(...),
    estate_bought: str = Form(...),
    invoice_number: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    accept_policy: bool = Form(...),
    # files will be read from the raw form to avoid single/multiple validation issues
):
    """Public endpoint used by the marketing website to submit refund requests."""
    if not accept_policy:
        raise HTTPException(status_code=400, detail="You must accept the refund policy before submitting.")

    db = get_db()
    now = datetime.utcnow().isoformat()

    # Server-side validation
    if not phone or not phone.strip():
        raise HTTPException(status_code=400, detail="Phone number is required")
    digits = ''.join([c for c in phone if c.isdigit()])
    if len(digits) < 7 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg"}
    MAX_BYTES = 10 * 1024 * 1024

    stored_paths = []
    # Read files from form (works for single or multiple uploads)
    form = await request.form()
    form_files = form.getlist('files') if hasattr(form, 'getlist') else []
    for f in form_files:
        # f is UploadFile
        contents = await f.read()
        if not contents:
            continue
        if f.content_type not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {f.filename}")
        if len(contents) > MAX_BYTES:
            raise HTTPException(status_code=400, detail=f"File too large: {f.filename}")
        path = await _upload_file_to_bucket_bytes(contents, f.filename, f.content_type, "requests")
        stored_paths.append(path)
    # Enforce at least one uploaded receipt
    if not stored_paths:
        raise HTTPException(status_code=400, detail="At least one receipt must be uploaded")

    payload = {
        "name": name,
        "email": email,
        "phone": phone,
        "estate_bought": estate_bought,
        "invoice_number": invoice_number,
        "comment": comment,
        "files": stored_paths,
        "status": "submitted",
        "created_at": now,
        "updated_at": now
    }

    res = await db_execute(lambda: db.table("refund_requests").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to record refund request")

    request_id = res.data[0]["id"]

    # Prepare admin notification (background)
    async def _notify_admins():
        try:
            logger.info("Starting refund notification task for request %s", request_id)
            # Build simple HTML
            file_links = []
            from database import supabase
            for p in stored_paths:
                try:
                    url_res = supabase.storage.from_(REFUND_BUCKET).create_signed_url(p, 60 * 60)
                    file_links.append(url_res.get("signedURL") or url_res.get("signed_url") or p)
                except Exception:
                    file_links.append(p)

            # Use branded email service helpers
            try:
                await send_refund_request_admin_email({
                    "id": request_id,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "estate_bought": estate_bought,
                    "invoice_number": invoice_number,
                    "comment": comment
                }, file_links)
            except Exception:
                logger.exception("Failed sending refund admin notification for %s", request_id)
            # Send confirmation to requester
            try:
                await send_refund_request_confirmation_email({
                    "id": request_id,
                    "name": name,
                    "email": email,
                    "estate_bought": estate_bought,
                    "invoice_number": invoice_number,
                })
            except Exception:
                logger.exception("Failed sending refund confirmation to requester %s", email)
            logger.info("Completed refund notification task for request %s", request_id)
        except Exception as e:
            logger.exception("Error in refund notification task for request %s", request_id)
            # Persist failure to DB so admins can see failed email attempts
            try:
                await db_execute(lambda: db.table("refund_requests").update({
                    "status": "email_failed",
                    "email_error": str(e),
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", request_id).execute())
            except Exception as ee:
                logger.exception("Failed to update refund_requests with email failure for %s: %s", request_id, ee)

    # Schedule notifier in background so it runs after response without blocking.
    try:
        asyncio.create_task(_notify_admins())
    except Exception as e:
        logger.exception("Failed to schedule refund notification task: %s", e)

    return {"message": "Refund request submitted", "id": request_id}



@router.patch("/{request_id}/status")
async def update_refund_status(request_id: str, request: Request, current_admin=Depends(verify_token)):
    """Admin endpoint to update refund request status (approved/rejected/processing)."""
    if not has_any_role(current_admin, ["admin", "super_admin"]):
        raise HTTPException(status_code=403, detail="Admins only")
    # Accept either JSON body or form-encoded body
    body = {}
    try:
        body = await request.json()
    except Exception:
        form = await request.form()
        body = {k: v for k, v in form.items()}

    status = (body.get('status') or '').lower()
    reason = body.get('reason') or None
    if status not in ("approved", "rejected", "processing", "submitted"):
        raise HTTPException(status_code=400, detail="Invalid status")
    db = get_db()
    now = datetime.utcnow().isoformat()
    payload = {"status": status, "updated_at": now}
    if reason:
        payload["status_reason"] = reason
    try:
        res = await db_execute(lambda: db.table("refund_requests").update(payload).eq("id", request_id).execute())
    except Exception as e:
        logger.exception("Failed to update refund status for %s: %s", request_id, e)
        # Surface the exception message to aid debugging in local/dev environments
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")

    # Fetch updated row to send email
    try:
        row_res = await db_execute(lambda: db.table("refund_requests").select("*").eq("id", request_id).execute())
        row = row_res.data[0] if row_res.data else None
        if row:
            # Notify requester of status change
            try:
                await send_refund_status_update_email(row, status, reason)
            except Exception:
                logger.exception("Failed to send status update email for %s", request_id)
    except Exception:
        logger.exception("Failed to load refund row after status update %s", request_id)

    return {"message": "Status updated", "id": request_id, "status": status}


@router.get("/")
async def list_refund_requests(current_admin=Depends(verify_token)):
    # Only admin and super_admin
    if not has_any_role(current_admin, ["admin", "super_admin"]):
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    res = await db_execute(lambda: db.table("refund_requests").select("*").order("created_at", desc=True).execute())
    return res.data


@router.get("/{request_id}")
async def get_refund_request(request_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, ["admin", "super_admin"]):
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    res = await db_execute(lambda: db.table("refund_requests").select("*").eq("id", request_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    return res.data[0]


@router.get("/{request_id}/files")
async def get_refund_files(request_id: str, current_admin=Depends(verify_token)):
    """Return signed URLs for files attached to a refund request (admin-only)."""
    if not has_any_role(current_admin, ["admin", "super_admin"]):
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    res = await db_execute(lambda: db.table("refund_requests").select("files").eq("id", request_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    files = res.data[0].get("files") or []
    signed = []
    from database import supabase
    for p in files:
        try:
            url_res = supabase.storage.from_(REFUND_BUCKET).create_signed_url(p, 60 * 60)
            signed_url = url_res.get("signedURL") or url_res.get("signed_url") or None
            if signed_url:
                signed.append(signed_url)
            else:
                signed.append(p)
        except Exception:
            signed.append(p)
    return {"files": signed}
