from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
import uuid
import os
import base64
from datetime import datetime, timedelta, timezone
from storage_service import upload_portal_file, generate_signed_url, PORTAL_CLAIMS_BUCKET
from typing import List, Optional

router = APIRouter()

# ── Admin Endpoints ──────────────────────────────────────────────────────────

@router.get("/submissions")
async def get_submissions(current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    # Fetch submissions and count guarantors
    res = await db_execute(lambda: db.table("guarantor_submissions").select("*, guarantors(count)").order("submitted_at", desc=True).execute())
    # Flatten count
    for item in res.data:
        item["guarantors_count"] = item["guarantors"][0]["count"] if item.get("guarantors") else 0
        # Cleanup internal count object
        if "guarantors" in item: del item["guarantors"]
    return res.data

@router.get("/submissions/{id}")
async def get_submission_detail(id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    sub_res = await db_execute(lambda: db.table("guarantor_submissions").select("*").eq("id", id).execute())
    if not sub_res.data:
        raise HTTPException(status_code=404, detail="Not found")
    
    sub = sub_res.data[0]
    g_res = await db_execute(lambda: db.table("guarantors").select("*").eq("submission_id", id).order("slot_number").execute())
    
    # Generate signed URLs and map to guarantor1, guarantor2 for frontend
    sub["guarantor1"] = None
    sub["guarantor2"] = None
    
    for g in g_res.data:
        g["passport_photo_url"] = generate_signed_url(PORTAL_CLAIMS_BUCKET, g["passport_photo_url"])
        g["id_document_url"] = generate_signed_url(PORTAL_CLAIMS_BUCKET, g["id_document_url"])
        g["signature_url"] = generate_signed_url(PORTAL_CLAIMS_BUCKET, g["signature_url"])
        
        slot = g.get("slot_number", 1)
        sub[f"guarantor{slot}"] = g
    
    # Employee sig
    sub["employee_signature_url"] = generate_signed_url(PORTAL_CLAIMS_BUCKET, sub["employee_signature_url"])
        
    return sub

@router.post("/submissions/{id}/review")
async def review_submission(id: str, data: dict, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    db = get_db()
    section = data.get("section") # "a", "b", "c"
    status = data.get("status")
    reason = data.get("reason", "")
    
    if status not in ["approved", "rejected", "pending"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    update_data = {
        "reviewed_at": datetime.utcnow().isoformat(),
        "reviewed_by": current_admin["sub"]
    }
    
    if section in ["a", "b", "c"]:
        update_data[f"section_{section}_status"] = status
        update_data[f"section_{section}_reason"] = reason
    else:
        update_data["status"] = status
        
    res = await db_execute(lambda: db.table("guarantor_submissions").update(update_data).eq("id", id).execute())
    
    # Notify employee
    sub_res = await db_execute(lambda: db.table("guarantor_submissions").select("employee_email").eq("id", id).execute())
    if sub_res.data:
        emp_email = sub_res.data[0]["employee_email"]
        admin_res = await db_execute(lambda: db.table("admins").select("id").eq("email", emp_email).execute())
        if admin_res.data:
            section_label = "Employee Details" if section == "a" else f"Guarantor {1 if section == 'b' else 2}"
            msg = f"Your Guarantor Form ({section_label}) has been {status}."
            if status == "rejected" and reason:
                msg += f" Reason: {reason}"
                
            await db_execute(lambda: db.table("notifications").insert({
                "staff_id": admin_res.data[0]["id"],
                "type": "guarantor_update",
                "message": msg
            }).execute())
            
    return res.data[0]

@router.get("/invites")
# ... (rest of admin endpoints)
async def get_invites(current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    res = await db_execute(lambda: db.table("guarantor_invites").select("*").order("created_at", desc=True).execute())
    return res.data

@router.post("/invites")
async def create_invite(data: dict, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    token = str(uuid.uuid4())
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    
    res = await db_execute(lambda: db.table("guarantor_invites").insert({
        "email": email,
        "token": token,
        "expires_at": expires_at,
        "created_by": current_admin["sub"]
    }).execute())
    
    return res.data[0]

@router.get("/general-link")
async def get_general_link(request: Request):
    db = get_db()
    settings_res = await db_execute(lambda: db.table("guarantor_settings").select("*").limit(1).execute())
    if not settings_res.data:
        return {"link": "", "is_collecting": False}
    
    settings = settings_res.data[0]
    base_url = os.getenv("APP_BASE_URL", str(request.base_url).rstrip("/"))
    if not base_url.endswith("/hr"):
        base_url = f"{base_url}/hr"
        
    link = f"{base_url}?guarantor_token={settings['general_link_token']}"
    
    return {
        "link": link,
        "is_collecting": settings["is_collecting"]
    }

@router.patch("/settings")
async def update_settings(data: dict, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin", "hr_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    update_data = {}
    if "is_collecting" in data:
        update_data["is_collecting"] = data["is_collecting"]
    
    settings_res = await db_execute(lambda: db.table("guarantor_settings").select("id").limit(1).execute())
    if not settings_res.data:
        raise HTTPException(status_code=404, detail="Settings record not found")
        
    res = await db_execute(lambda: db.table("guarantor_settings").update(update_data).eq("id", settings_res.data[0]["id"]).execute())
    return res.data[0]

# ── Public Endpoints ─────────────────────────────────────────────────────────

@router.get("/public/check")
async def check_public_token(token: str, email: str):
    db = get_db()
    settings_res = await db_execute(lambda: db.table("guarantor_settings").select("*").limit(1).execute())
    if not settings_res.data or not settings_res.data[0]["is_collecting"]:
        raise HTTPException(status_code=403, detail="Guarantor form collection is currently closed.")

    is_general = token == settings_res.data[0]["general_link_token"]
    if not is_general:
        invite_res = await db_execute(lambda: db.table("guarantor_invites").select("*").eq("token", token).eq("email", email).execute())
        if not invite_res.data:
            raise HTTPException(status_code=404, detail="Invalid invitation link or email.")
        if invite_res.data[0]["status"] != "pending":
            raise HTTPException(status_code=400, detail="This invitation link has already been used.")
        
        expires_at = datetime.fromisoformat(invite_res.data[0]["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="This invitation link has expired.")

    sub_res = await db_execute(lambda: db.table("guarantor_submissions").select("*, guarantors(*)").eq("employee_email", email).execute())
    
    submission = None
    if sub_res.data:
        submission = sub_res.data[0]
        if submission.get("employee_signature_url"):
            submission["employee_signature_url"] = generate_signed_url(PORTAL_CLAIMS_BUCKET, submission["employee_signature_url"])
        
        guarantors = submission.get("guarantors") or []
        submission["g1"] = next((g for g in guarantors if g["slot_number"] == 1), None)
        submission["g2"] = next((g for g in guarantors if g["slot_number"] == 2), None)
        
        for key in ["g1", "g2"]:
            if submission[key]:
                for field in ["passport_photo_url", "id_document_url", "signature_url"]:
                    if submission[key].get(field):
                        submission[key][field] = generate_signed_url(PORTAL_CLAIMS_BUCKET, submission[key][field])

    staff_info = None
    if not submission:
        staff_res = await db_execute(lambda: db.table("admins").select("id, full_name, role, department").eq("email", email).execute())
        staff_info = staff_res.data[0] if staff_res.data else None
        if staff_info:
            profile_res = await db_execute(lambda: db.table("staff_profiles").select("staff_id").eq("admin_id", staff_info["id"]).execute())
            staff_info["staff_id"] = profile_res.data[0]["staff_id"] if profile_res.data else ""
            staff_info["job_title"] = staff_info.get("role", "")

    return {
        "status": "ok", 
        "staff_info": staff_info,
        "submission": submission,
        "is_general": is_general
    }

@router.post("/public/save-partial")
async def save_partial_submission(
    token: str = Form(...),
    email: str = Form(...),
    section: str = Form(...), # employee, g1, g2
    data: str = Form(...) # JSON string of fields
):
    import json
    fields = json.loads(data)
    db = get_db()
    
    sub_res = await db_execute(lambda: db.table("guarantor_submissions").select("id").eq("employee_email", email).execute())
    submission_id = sub_res.data[0]["id"] if sub_res.data else str(uuid.uuid4())
    
    if section == "employee":
        payload = {
            "id": submission_id,
            "employee_name": fields.get("full_name"),
            "employee_email": email,
            "position": fields.get("position"),
            "staff_id": fields.get("staff_id"),
            "date_of_employment": fields.get("date_of_employment"),
            "employee_phone": fields.get("phone"),
            "employee_address": fields.get("address"),
            "section_a_status": "pending" # Reset status on update
        }
        
        sig_b64 = fields.get("signature")
        if sig_b64 and "," in sig_b64:
            img_data = base64.b64decode(sig_b64.split(",")[1])
            path = f"guarantors/{submission_id}/employee_sig.png"
            upload_portal_file(path, img_data, "image/png")
            payload["employee_signature_url"] = path
            
        await db_execute(lambda: db.table("guarantor_submissions").upsert(payload).execute())
        
    elif section in ["g1", "g2"]:
        slot = 1 if section == "g1" else 2
        g_payload = {
            "submission_id": submission_id,
            "slot_number": slot,
            "full_name": fields.get("full_name"),
            "relationship": fields.get("relationship"),
            "address": fields.get("address"),
            "occupation": fields.get("occupation"),
            "employer_name": fields.get("employer_name"),
            "position_held": fields.get("position_held"),
            "years_at_job": fields.get("years_at_job"),
            "phone": fields.get("phone"),
            "email": fields.get("email"),
            "id_type": fields.get("id_type"),
            "id_number": fields.get("id_number"),
            "witness_name": fields.get("witness_name"),
            "witness_occupation": fields.get("witness_occupation"),
            "witness_phone": fields.get("witness_phone"),
            "witness_address": fields.get("witness_address"),
            "witness_date": fields.get("witness_date")
        }
        
        sig_b64 = fields.get("signature")
        if sig_b64 and "," in sig_b64:
            img_data = base64.b64decode(sig_b64.split(",")[1])
            path = f"guarantors/{submission_id}/{section}_sig.png"
            upload_portal_file(path, img_data, "image/png")
            g_payload["signature_url"] = path
            
        await db_execute(lambda: db.table("guarantors").upsert(g_payload, on_conflict="submission_id, slot_number").execute())
        
        # Reset section status to pending
        await db_execute(lambda: db.table("guarantor_submissions").update({
            f"section_{'b' if section == 'g1' else 'c'}_status": "pending"
        }).eq("id", submission_id).execute())

        # Notify Employee
        admin_res = await db_execute(lambda: db.table("admins").select("id").eq("email", email).execute())
        if admin_res.data:
            g_name = fields.get("full_name") or ("Guarantor 1" if section == "g1" else "Guarantor 2")
            await db_execute(lambda: db.table("notifications").insert({
                "staff_id": admin_res.data[0]["id"],
                "type": "guarantor_submission",
                "message": f"{g_name} has completed their part of your Guarantor Form."
            }).execute())

    base_url = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com")
    relay_link = f"{base_url}/hr?guarantor_token={token}&email={email}"
    
    return {"status": "success", "submission_id": submission_id, "relay_link": relay_link}

@router.post("/public/submit")
async def submit_guarantor_form(
    token: str = Form(...),
    email: str = Form(...),
    # ... (remaining fields same as before)
    emp_full_name: str = Form(...),
    emp_position: str = Form(...),
    emp_address: str = Form(...),
    emp_phone: str = Form(...),
    emp_date_of_employment: str = Form(...),
    emp_staff_id: str = Form(None),
    emp_signature: str = Form(...), # Base64
    # Guarantor 1
    g1_full_name: str = Form(...),
    g1_relationship: str = Form(...),
    g1_address: str = Form(...),
    g1_occupation: str = Form(...),
    g1_employer_name: str = Form(...),
    g1_position_held: str = Form(...),
    g1_years_at_job: str = Form(...),
    g1_phone: str = Form(...),
    g1_email: str = Form(...),
    g1_id_type: str = Form(...),
    g1_id_number: str = Form(...),
    g1_signature: str = Form(...), # Base64
    g1_passport_photo: UploadFile = File(...),
    g1_id_document: UploadFile = File(None),
    # Guarantor 2
    g2_full_name: str = Form(...),
    g2_relationship: str = Form(...),
    g2_address: str = Form(...),
    g2_occupation: str = Form(...),
    g2_employer_name: str = Form(...),
    g2_position_held: str = Form(...),
    g2_years_at_job: str = Form(...),
    g2_phone: str = Form(...),
    g2_email: str = Form(...),
    g2_id_type: str = Form(...),
    g2_id_number: str = Form(...),
    g2_signature: str = Form(...), # Base64
    g2_passport_photo: UploadFile = File(...),
    g2_id_document: UploadFile = File(None)
):
    db = get_db()
    # 1. Upload Files
    submission_id = str(uuid.uuid4())
    
    def upload_sig(b64, name):
        if not b64 or "," not in b64: return None
        try:
            img_data = base64.b64decode(b64.split(",")[1])
            path = f"guarantors/{submission_id}/{name}.png"
            upload_portal_file(path, img_data, "image/png")
            return path
        except: return None

    emp_sig_path = upload_sig(emp_signature, "employee_sig")
    g1_sig_path = upload_sig(g1_signature, "g1_sig")
    g2_sig_path = upload_sig(g2_signature, "g2_sig")
    
    async def upload_file(file, name):
        if not file: return None
        try:
            content = await file.read()
            path = f"guarantors/{submission_id}/{name}_{file.filename}"
            upload_portal_file(path, content, file.content_type)
            return path
        except: return None

    g1_pass_path = await upload_file(g1_passport_photo, "g1_passport")
    g1_id_path = await upload_file(g1_id_document, "g1_id")
    g2_pass_path = await upload_file(g2_passport_photo, "g2_passport")
    g2_id_path = await upload_file(g2_id_document, "g2_id")

    # 2. Save Submission
    await db_execute(lambda: db.table("guarantor_submissions").insert({
        "id": submission_id,
        "employee_name": emp_full_name,
        "employee_email": email,
        "position": emp_position,
        "staff_id": emp_staff_id,
        "date_of_employment": emp_date_of_employment,
        "employee_phone": emp_phone,
        "employee_address": emp_address,
        "employee_signature_url": emp_sig_path
    }).execute())
    
    # 3. Save Guarantors
    await db_execute(lambda: db.table("guarantors").insert([
        {
            "submission_id": submission_id,
            "slot_number": 1,
            "full_name": g1_full_name,
            "relationship": g1_relationship,
            "address": g1_address,
            "occupation": g1_occupation,
            "employer_name": g1_employer_name,
            "position_held": g1_position_held,
            "years_at_job": g1_years_at_job,
            "phone": g1_phone,
            "email": g1_email,
            "id_type": g1_id_type,
            "id_number": g1_id_number,
            "passport_photo_url": g1_pass_path,
            "id_document_url": g1_id_path,
            "signature_url": g1_sig_path
        },
        {
            "submission_id": submission_id,
            "slot_number": 2,
            "full_name": g2_full_name,
            "relationship": g2_relationship,
            "address": g2_address,
            "occupation": g2_occupation,
            "employer_name": g2_employer_name,
            "position_held": g2_position_held,
            "years_at_job": g2_years_at_job,
            "phone": g2_phone,
            "email": g2_email,
            "id_type": g2_id_type,
            "id_number": g2_id_number,
            "passport_photo_url": g2_pass_path,
            "id_document_url": g2_id_path,
            "signature_url": g2_sig_path
        }
    ]).execute())

    # 4. Mark invite as used if not general
    invite_res = await db_execute(lambda: db.table("guarantor_invites").select("id").eq("token", token).execute())
    if invite_res.data:
        await db_execute(lambda: db.table("guarantor_invites").update({"status": "used"}).eq("id", invite_res.data[0]["id"]).execute())
    
    return {"status": "success", "submission_id": submission_id}

@router.get("/company-info")
async def get_company_info():
    return {
        "name": "Eximp & Cloves Infrastructure Limited",
        "address": "57B, Isaac John Street, Yaba, Lagos",
        "rc": "RC 8311800",
        "phone": "+234 912 686 4383",
        "email_addr": "hr@eximps-cloves.com"
    }
