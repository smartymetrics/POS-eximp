import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
from storage_service import upload_portal_file, generate_signed_url

logger = logging.getLogger(__name__)

router = APIRouter()

REFUND_BUCKET = "refund-documents"


@router.post("/public/submit")
async def submit_refund_request(
    request: Request,
    background_tasks: BackgroundTasks,
    client_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    invoice_number: str = Form(...),
    estate_bought: str = Form(...),
    amount_paid: float = Form(...),
    refund_reason: str = Form(...),
    bank_name: str = Form(...),
    account_number: str = Form(...),
    account_name: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    """Public endpoint for clients to submit formal refund applications."""
    db = get_db()
    
    stored_paths = []
    for f in files:
        if f.filename:
            content = await f.read()
            if content:
                ext = f.filename.split(".")[-1].lower() if "." in f.filename else "pdf"
                path = f"refunds/{uuid.uuid4().hex[:12]}_{f.filename}"
                try:
                    await db_execute(lambda: db.storage.from_(REFUND_BUCKET).upload(path, content, {"content-type": f.content_type or "application/octet-stream"}))
                    stored_paths.append(path)
                except Exception as e:
                    logger.warning(f"Failed to store refund file {f.filename}: {e}")

    payload = {
        "client_name": client_name.strip(),
        "email": email.strip().lower(),
        "phone": phone.strip(),
        "invoice_number": invoice_number.strip(),
        "estate_bought": estate_bought.strip(),
        "amount_paid": float(amount_paid),
        "refund_reason": refund_reason.strip(),
        "bank_name": bank_name.strip(),
        "account_number": account_number.strip(),
        "account_name": account_name.strip(),
        "status": "pending",
        "file_paths": stored_paths,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    res = await db_execute(lambda: db.table("refund_requests").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to record refund request")

    return {
        "status": "success",
        "message": "Refund application submitted successfully. An administrator will review your submission.",
        "request_id": res.data[0]["id"]
    }


@router.get("/")
async def list_refund_requests(current_admin=Depends(verify_token)):
    """Admin endpoint to list all client refund applications."""
    if not has_any_role(current_admin, "admin", "super_admin", "finance", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    res = await db_execute(lambda: db.table("refund_requests").select("*").order("created_at", desc=True).execute())
    return res.data or []


@router.get("/{request_id}")
async def get_refund_request(request_id: str, current_admin=Depends(verify_token)):
    """Admin endpoint to retrieve a specific refund application."""
    if not has_any_role(current_admin, "admin", "super_admin", "finance", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    res = await db_execute(lambda: db.table("refund_requests").select("*").eq("id", request_id).limit(1).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Refund application not found")
    return res.data[0]


@router.get("/{request_id}/files")
async def get_refund_files(request_id: str, current_admin=Depends(verify_token)):
    """Generates signed URLs for files attached to a refund application."""
    if not has_any_role(current_admin, "admin", "super_admin", "finance", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    res = await db_execute(lambda: db.table("refund_requests").select("file_paths").eq("id", request_id).limit(1).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Refund application not found")

    paths = res.data[0].get("file_paths") or []
    signed_links = []
    for p in paths:
        try:
            url_res = await db_execute(lambda: db.storage.from_(REFUND_BUCKET).create_signed_url(p, 3600))
            if url_res and "signedURL" in url_res:
                signed_links.append({"path": p, "url": url_res["signedURL"]})
        except Exception:
            signed_links.append({"path": p, "url": f"https://scsdnstqtrqjsosbmxyf.supabase.co/storage/v1/object/public/{REFUND_BUCKET}/{p}"})

    return {"files": signed_links}


@router.patch("/{request_id}/status")
async def update_refund_status(
    request_id: str,
    payload: dict,
    current_admin=Depends(verify_token)
):
    """Admin endpoint to approve, reject, or mark a refund application as processing."""
    if not has_any_role(current_admin, "admin", "super_admin", "finance", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    new_status = payload.get("status", "").lower()
    reason = payload.get("reason", "").strip()

    if new_status not in ("pending", "processing", "approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid refund status")

    db = get_db()
    update_data = {
        "status": new_status,
        "status_reason": reason,
        "reviewed_by": current_admin.get("sub"),
        "updated_at": datetime.utcnow().isoformat()
    }

    res = await db_execute(lambda: db.table("refund_requests").update(update_data).eq("id", request_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Refund request not found")

    return {"status": "success", "message": f"Refund status updated to {new_status}"}

