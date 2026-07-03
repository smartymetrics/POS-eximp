from fastapi import APIRouter, HTTPException, Depends, Form, Request, BackgroundTasks
from typing import Optional, List
from pydantic import EmailStr
from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
from datetime import datetime
import uuid
import logging
from models import ClientFeedbackReview
from storage_service import upload_portal_file, generate_signed_url, PORTAL_CLAIMS_BUCKET

logger = logging.getLogger(__name__)

router = APIRouter()

async def create_feedback_notifications(feedback_payload: dict):
    """Background task to notify all admins authorized to view feedback."""
    try:
        db = get_db()
        # Query all admins
        admins_res = await db_execute(lambda: db.table("admins").select("id, role").execute())
        if not admins_res.data:
            return
        
        target_admin_ids = []
        for adm in admins_res.data:
            roles = [r.strip().lower() for r in (adm.get("role") or "").split(",") if r.strip()]
            if any(r in {"admin", "super_admin", "operations", "customer_support"} for r in roles):
                target_admin_ids.append(adm["id"])
                
        if not target_admin_ids:
            return
            
        notifications = [
            {
                "admin_id": admin_id,
                "title": "New Client Feedback",
                "message": f"New feedback submitted by {feedback_payload.get('name') or 'Anonymous'} ({feedback_payload.get('feedback_type', 'general')}). NPS: {feedback_payload.get('nps_score')}/10.",
                "notification_type": "general",
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }
            for admin_id in target_admin_ids
        ]
        await db_execute(lambda: db.table("notifications").insert(notifications).execute())
    except Exception as ex:
        logger.error(f"Failed to create feedback notifications for admins: {ex}")

@router.post("/submit")
async def submit_client_feedback(
    request: Request,
    background_tasks: BackgroundTasks,
    user_type: str = Form(...),
    feedback_type: str = Form(...),
    experience_rating: int = Form(...),
    nps_score: int = Form(...),
    communication_rating: int = Form(...),
    comments: str = Form(...),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    property_interest_id: Optional[str] = Form(None),
    contact_consent: bool = Form(False)
):
    """
    Public endpoint for clients/leads to submit feedback from the marketing website.
    Handles matching existing clients/leads or creating new leads upon follow-up consent.
    Also handles optional file uploads (screenshots, receipts, documents).
    """
    db = get_db()
    now = datetime.utcnow().isoformat()

    # Normalize fields
    name = name.strip() if name else None
    email = email.strip().lower() if email else None
    phone = phone.strip() if phone else None
    property_interest_id = property_interest_id.strip() if property_interest_id else None

    # Server-side validation
    if experience_rating < 1 or experience_rating > 5:
        raise HTTPException(status_code=400, detail="Experience rating must be between 1 and 5")
    if nps_score < 0 or nps_score > 10:
        raise HTTPException(status_code=400, detail="NPS score must be between 0 and 10")
    if communication_rating < 1 or communication_rating > 5:
        raise HTTPException(status_code=400, detail="Communication rating must be between 1 and 5")
    if not comments or not comments.strip():
        raise HTTPException(status_code=400, detail="Comments/Remarks cannot be empty")
    
    if contact_consent and (not email or not name):
        raise HTTPException(status_code=400, detail="Name and Email are required if you consent to follow-up.")

    # 1. Handle File Uploads (Multiple files)
    stored_paths = []
    ALLOWED_MIME = {
        "application/pdf", 
        "image/png", 
        "image/jpeg", 
        "video/mp4", 
        "video/quicktime", 
        "video/webm",
        "video/x-msvideo", 
        "video/mpeg"
    }
    MAX_BYTES = 50 * 1024 * 1024  # 50 MB

    try:
        form = await request.form()
        form_files = form.getlist('files') if hasattr(form, 'getlist') else []
        
        for f in form_files:
            contents = await f.read()
            if not contents:
                continue
            if f.content_type not in ALLOWED_MIME:
                raise HTTPException(status_code=400, detail=f"Invalid file type: {f.filename}. Only PDFs and images are allowed.")
            if len(contents) > MAX_BYTES:
                raise HTTPException(status_code=400, detail=f"File too large: {f.filename}. Maximum size is 10MB.")
            
            unique_id = str(uuid.uuid4())[:8]
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in f.filename)
            stored_path = f"feedback_attachments/{unique_id}_{safe_name}"
            
            # Upload using the existing storage service
            success = upload_portal_file(stored_path, contents, f.content_type)
            if success:
                stored_paths.append(stored_path)
            else:
                logger.error(f"Failed to upload feedback attachment: {f.filename}")
                raise HTTPException(status_code=500, detail="Failed to upload attachment.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing feedback file attachments")
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

    # 2. Client & Contact Association
    client_id = None
    contact_id = None

    if email:
        # Check if they are an existing client
        client_res = await db_execute(lambda: db.table("clients").select("id").eq("email", email).execute())
        if client_res.data:
            client_id = client_res.data[0]["id"]
            user_type = "client"
            
        # Check if they are an existing marketing contact
        contact_res = await db_execute(lambda: db.table("marketing_contacts").select("id, contact_type").eq("email", email).execute())
        if contact_res.data:
            contact_id = contact_res.data[0]["id"]
            if not client_id and contact_res.data[0]["contact_type"] == "client":
                user_type = "client"
            elif not client_id:
                user_type = "lead"
        elif contact_consent:
            # If not in system, auto-create as a Lead in marketing_contacts on consent
            try:
                names = name.split(" ", 1)
                first_name = names[0]
                last_name = names[1] if len(names) > 1 else ""
                
                new_contact = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "source": "feedback_form",
                    "contact_type": "lead",
                    "tags": ["feedback-submitter"],
                    "is_subscribed": True
                }
                ins_res = await db_execute(lambda: db.table("marketing_contacts").insert(new_contact).execute())
                if ins_res.data:
                    contact_id = ins_res.data[0]["id"]
                    user_type = "lead"
            except Exception as ex:
                logger.error(f"Failed to auto-create marketing contact for feedback submitter: {ex}")

    # 2.5. Property name-to-UUID resolution
    resolved_property_id = None
    if property_interest_id:
        property_interest_id = property_interest_id.strip()
        is_uuid = False
        try:
            uuid.UUID(property_interest_id)
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            prop_res = await db_execute(lambda: db.table("properties").select("id").eq("id", property_interest_id).execute())
            if prop_res.data:
                resolved_property_id = prop_res.data[0]["id"]
        else:
            # Look up case-insensitively by name
            prop_res = await db_execute(lambda: db.table("properties").select("id").ilike("name", f"%{property_interest_id}%").execute())
            if prop_res.data:
                resolved_property_id = prop_res.data[0]["id"]
            else:
                # Try matching by estate name
                prop_res = await db_execute(lambda: db.table("properties").select("id").ilike("estate_name", f"%{property_interest_id}%").execute())
                if prop_res.data:
                    resolved_property_id = prop_res.data[0]["id"]

    # 3. Insert Feedback submission
    payload = {
        "client_id": client_id,
        "contact_id": contact_id,
        "name": name,
        "email": email,
        "phone": phone,
        "user_type": user_type,
        "feedback_type": feedback_type,
        "experience_rating": experience_rating,
        "nps_score": nps_score,
        "communication_rating": communication_rating,
        "comments": comments,
        "property_interest_id": resolved_property_id,
        "contact_consent": contact_consent,
        "attachment_urls": stored_paths,
        "status": "new",
        "created_at": now,
        "updated_at": now
    }

    res = await db_execute(lambda: db.table("client_feedback").insert(payload).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to save feedback submission")

    background_tasks.add_task(create_feedback_notifications, payload)

    return {"message": "Feedback submitted successfully", "id": res.data[0]["id"]}

@router.get("/")
async def list_feedback(
    limit: int = 100,
    offset: int = 0,
    user_type: Optional[str] = None,
    feedback_type: Optional[str] = None,
    status: Optional[str] = None,
    nps_group: Optional[str] = None,
    current_admin=Depends(verify_token)
):
    """Admin-only endpoint to list feedback submissions with filters."""
    if not has_any_role(current_admin, ["admin", "super_admin", "operations", "customer_support"]):
        raise HTTPException(status_code=403, detail="Access denied")

    db = get_db()
    query = db.table("client_feedback").select("*, properties(name)")

    if user_type:
        query = query.eq("user_type", user_type)
    if feedback_type:
        query = query.eq("feedback_type", feedback_type)
    if status:
        query = query.eq("status", status)
    
    if nps_group:
        if nps_group == "promoter":
            query = query.gte("nps_score", 9)
        elif nps_group == "passive":
            query = query.in_("nps_score", [7, 8])
        elif nps_group == "detractor":
            query = query.lte("nps_score", 6)

    res = await db_execute(lambda: query.order("created_at", desc=True).range(offset, offset + limit - 1).execute())
    return res.data

@router.get("/stats")
async def get_feedback_stats(current_admin=Depends(verify_token)):
    """Admin-only endpoint to fetch dynamic metrics for the feedback dashboard."""
    if not has_any_role(current_admin, ["admin", "super_admin", "operations", "customer_support"]):
        raise HTTPException(status_code=403, detail="Access denied")

    db = get_db()
    res = await db_execute(lambda: db.table("client_feedback").select("experience_rating, nps_score, communication_rating").execute())
    data = res.data or []

    total = len(data)
    if total == 0:
        return {
            "total_count": 0,
            "avg_experience": 0,
            "avg_communication": 0,
            "nps_score": 0,
            "promoters_count": 0,
            "passives_count": 0,
            "detractors_count": 0,
            "promoters_pct": 0,
            "passives_pct": 0,
            "detractors_pct": 0
        }

    avg_exp = sum(d["experience_rating"] for d in data) / total
    avg_comm = sum(d["communication_rating"] for d in data) / total

    promoters = sum(1 for d in data if d["nps_score"] >= 9)
    passives = sum(1 for d in data if d["nps_score"] in [7, 8])
    detractors = sum(1 for d in data if d["nps_score"] <= 6)

    promoters_pct = (promoters / total) * 100
    passives_pct = (passives / total) * 100
    detractors_pct = (detractors / total) * 100

    nps_score = promoters_pct - detractors_pct

    return {
        "total_count": total,
        "avg_experience": round(avg_exp, 1),
        "avg_communication": round(avg_comm, 1),
        "nps_score": round(nps_score, 0),
        "promoters_count": promoters,
        "passives_count": passives,
        "detractors_count": detractors,
        "promoters_pct": round(promoters_pct, 1),
        "passives_pct": round(passives_pct, 1),
        "detractors_pct": round(detractors_pct, 1)
    }

@router.get("/{feedback_id}")
async def get_feedback_details(feedback_id: str, current_admin=Depends(verify_token)):
    """Admin-only endpoint to get details of a specific feedback, including signed URLs for attachments."""
    if not has_any_role(current_admin, ["admin", "super_admin", "operations", "customer_support"]):
        raise HTTPException(status_code=403, detail="Access denied")

    db = get_db()
    res = await db_execute(lambda: db.table("client_feedback").select("*, properties(name)").eq("id", feedback_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback = res.data[0]
    attachments = feedback.get("attachment_urls") or []
    signed_attachments = []

    for path in attachments:
        try:
            signed_url = generate_signed_url(PORTAL_CLAIMS_BUCKET, path, 3600)
            filename = path.split("/")[-1].split("_", 1)[-1] if "_" in path else path.split("/")[-1]
            signed_attachments.append({
                "filename": filename,
                "path": path,
                "url": signed_url or path
            })
        except Exception:
            signed_attachments.append({
                "filename": path.split("/")[-1],
                "path": path,
                "url": path
            })

    feedback["attachments"] = signed_attachments
    return feedback

@router.put("/{feedback_id}/review")
async def review_feedback(
    feedback_id: str,
    data: ClientFeedbackReview,
    current_admin=Depends(verify_token)
):
    """Admin-only endpoint to update the review status and admin notes of a feedback."""
    if not has_any_role(current_admin, ["admin", "super_admin", "operations", "customer_support"]):
        raise HTTPException(status_code=403, detail="Access denied")

    db = get_db()
    admin_id = current_admin.get("sub") or current_admin.get("id")

    now_iso = datetime.utcnow().isoformat()
    update_payload = {
        "status": data.status,
        "admin_notes": data.admin_notes,
        "reviewed_by": admin_id,
        "reviewed_at": now_iso,
        "updated_at": now_iso
    }

    res = await db_execute(lambda: db.table("client_feedback").update(update_payload).eq("id", feedback_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return {"message": "Feedback successfully reviewed", "feedback": res.data[0]}
