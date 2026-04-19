from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import Response
import os
from database import get_db, db_execute
from routers.auth import verify_token, resolve_admin_token
from datetime import datetime
import json
import uuid
import pdf_service

router = APIRouter()
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com")

# ── HELPER: PERMISSION CHECK ──
async def check_matter_access(matter_id: str, current_admin: dict, required_level: str = "View"):
    """
    Verifies if an admin has access to a legal matter.
    Levels: 'View', 'Edit', 'Full' (Drafter has 'Full')
    """
    db = get_db()
    admin_id = current_admin["sub"]
    user_roles = {r.strip() for r in (current_admin.get("role") or "").split(",") if r.strip()}
    
    # 1. Is the admin the drafter or a super-admin?
    matter_res = await db_execute(lambda: db.table("legal_matters").select("drafter_id, category").eq("id", matter_id).execute())
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Legal matter not found")
    
    matter = matter_res.data[0]
    
    # Check if admin is the drafter
    if str(matter.get("drafter_id")) == str(admin_id):
        return "Full"
        
    # Global 'View' bypass for HR and Legal on Personnel matters
    if required_level == "View" and matter.get("category") == "Personnel":
        if any(r in ["admin", "super_admin", "legal", "hr_admin", "hr"] for r in user_roles):
            return "View"
        
    # Check roles for Super Admin
    # (Simplified for now - assuming we can fetch role if needed, but for now we check collaborators)
    
    # 2. Check collaborators table
    collab_res = await db_execute(lambda: db.table("legal_matter_collaborators")\
        .select("permission_level")\
        .eq("matter_id", matter_id)\
        .eq("admin_id", admin_id).execute())
    
    if collab_res.data:
        level = collab_res.data[0]["permission_level"]
        # Basic check: Edit requires 'Edit' or 'Full'. View requires anything.
        if required_level == "Edit" and level not in ["Edit", "Full"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to edit this matter")
        return level

    raise HTTPException(status_code=403, detail="You do not have permission to access this legal matter")

# ── ENDPOINTS ──

@router.get("/collaborator-candidates")
async def get_collaborator_candidates(current_admin=Depends(verify_token)):
    """Fetch potential collaborators (admins/lawyers)."""
    db = get_db()
    res = await db_execute(lambda: db.table("admins")\
        .select("id, full_name, email, role")\
        .eq("is_active", True)\
        .execute())
    return [
       d for d in (res.data or []) 
       if str(d.get("id")) != str(current_admin["sub"])
    ]

@router.get("/matters")
async def get_legal_matters(category: str = None, staff_id: str = None, current_admin=Depends(verify_token)):
    """Fetch all legal matters accessible to the current admin."""
    db = get_db()
    admin_id = current_admin["sub"]
    user_roles = {r.strip() for r in (current_admin.get("role") or "").split(",") if r.strip()}
    
    # If the user is a lawyer, super_admin, or HR, they can see everything.
    # Otherwise, they only see matters where they are the drafter or collaborator.
    is_privileged = any(r in ["admin", "super_admin", "legal", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("legal_matters").select("*")
    if category:
        query = query.eq("category", category)
    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_privileged:
        # Restricted view: Only drafted or collaborated
        # This is slightly tricky for PostgREST 'or' logic, so we'll fetch drafted mostly
        query = query.eq("drafter_id", admin_id)
        
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return res.data or []

@router.get("/staff/{staff_id}/matters")
async def get_staff_matters(staff_id: str, current_admin=Depends(verify_token)):
    """HR Portal: Fetch all matters for a specific employee (HR/Legal only)."""
    user_roles = {r.strip() for r in (current_admin.get("role") or "").split(",") if r.strip()}
    if not any(r in ["admin", "super_admin", "hr_admin", "hr", "legal"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Only HR and Legal staff can view staff matters")
    
    db = get_db()
    res = await db_execute(lambda: db.table("legal_matters")\
        .select("*")\
        .eq("staff_id", staff_id)\
        .order("created_at", desc=True).execute())
    return res.data or []

@router.post("/matters")
async def initiate_matter(data: dict, current_admin=Depends(verify_token)):
    """Create a new legal matter."""
    db = get_db()
    admin_id = current_admin["sub"]
    
    matter_data = {
        "title": data.get("title", "Untitled Case"),
        "category": data.get("category", "General"),
        "drafter_id": admin_id,
        "staff_id": data.get("staff_id"),
        "external_party_name": data.get("external_party_name"),
        "external_party_email": data.get("external_party_email"),
        "priority": data.get("priority", "Normal"),
        "hr_memo": data.get("hr_memo"),
        "status": data.get("status", "Draft")
    }
    
    res = await db_execute(lambda: db.table("legal_matters").insert(matter_data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to initiate legal matter")
    
    matter = res.data[0]
    
    # Log audit
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter["id"],
        "action": "Matter Initiated",
        "performed_by": admin_id,
        "description": f"New {matter['category']} matter created via { 'HR' if data.get('hr_memo') else 'Legal'} Portal"
    }).execute())
    
    return matter

@router.get("/matters/{matter_id}")
async def get_matter_details(matter_id: str, current_admin=Depends(verify_token)):
    """Get full details including content and collaborators."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin)
    
    db = get_db()
    matter_res = await db_execute(lambda: db.table("legal_matters").select("*").eq("id", matter_id).execute())
    collabs_res = await db_execute(lambda: db.table("legal_matter_collaborators").select("*, admins(full_name)").eq("matter_id", matter_id).execute())
    history_res = await db_execute(lambda: db.table("legal_matter_history").select("*").eq("matter_id", matter_id).order("created_at", desc=True).execute())
    
    return {
        "matter": matter_res.data[0],
        "collaborators": collabs_res.data or [],
        "history": history_res.data or []
    }

@router.post("/matters/{matter_id}/collaborators")
async def add_collaborator(matter_id: str, data: dict, current_admin=Depends(verify_token)):
    """Add a new collaborator to a matter."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    db = get_db()
    collab_data = {
        "matter_id": matter_id,
        "admin_id": data.get("admin_id"),
        "permission_level": data.get("permission_level", "Edit")
    }
    
    res = await db_execute(lambda: db.table("legal_matter_collaborators").insert(collab_data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to add collaborator")
        
    # Audit
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Permission Granted",
        "performed_by": admin_id,
        "description": f"Granted {collab_data['permission_level']} access to admin {data.get('admin_id')}"
    }).execute())
    
    return res.data[0]

@router.delete("/matters/{matter_id}/collaborators/{target_admin_id}")
async def remove_collaborator(matter_id: str, target_admin_id: str, current_admin=Depends(verify_token)):
    """Remove a collaborator from a matter."""
    admin_id = current_admin["sub"]
    # Only drafter or admin should remove collaborators? Let's check access
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    db = get_db()
    await db_execute(lambda: db.table("legal_matter_collaborators")\
        .delete()\
        .eq("matter_id", matter_id)\
        .eq("admin_id", target_admin_id).execute())
        
    # Audit
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Permission Revoked",
        "performed_by": admin_id,
        "description": f"Revoked access for admin {target_admin_id}"
    }).execute())
    
    return {"status": "removed"}

@router.patch("/matters/{matter_id}/save")
async def save_matter_content(matter_id: str, data: dict, current_admin=Depends(verify_token)):
    """Save Tiptap editor content as HTML."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    db = get_db()
    update_data = {
        "content_html": data.get("html"),
        "updated_at": datetime.now().isoformat()
    }
    
    await db_execute(lambda: db.table("legal_matters").update(update_data).eq("id", matter_id).execute())
    
    # Audit trail
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Edit",
        "performed_by": admin_id,
        "description": "Updated document draft content"
    }).execute())
    
    return {"status": "saved"}

@router.patch("/matters/{matter_id}/settings")
async def update_matter_settings(matter_id: str, data: dict, current_admin=Depends(verify_token)):
    """Update matter-specific settings like 'requires_signing'."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    db = get_db()
    update_data = {}
    if "requires_signing" in data:
        update_data["requires_signing"] = data["requires_signing"]
    
    if not update_data:
        return {"status": "no-change"}
        
    await db_execute(lambda: db.table("legal_matters").update(update_data).eq("id", matter_id).execute())
    
    # Audit logic
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Settings Updated",
        "performed_by": admin_id,
        "description": f"Updated settings: {json.dumps(update_data)}"
    }).execute())
    
    return {"status": "updated"}

@router.post("/matters/{matter_id}/export")
async def export_matter_pdf(matter_id: str, current_admin=Depends(verify_token)):
    """Generate and return the PDF version of the document (Tiptap HTML)."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin)
    
    db = get_db()
    # Get the latest content
    matter_res = await db_execute(lambda: db.table("legal_matters").select("*").eq("id", matter_id).execute())
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Matter not found")
        
    matter = matter_res.data[0]
    html = matter.get("content_html")
    
    # Generate PDF from Tiptap HTML
    pdf_bytes = pdf_service.generate_matter_pdf(matter_id, html)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Personnel_Matter_{matter_id}.pdf"
        }
    )

@router.get("/clauses")
async def get_clause_library(current_admin=Depends(verify_token)):
    """Fetch all reusable legal clauses."""
    db = get_db()
    res = await db_execute(lambda: db.table("legal_clause_library").select("*").execute())
    return res.data or []

@router.post("/clauses")
async def add_to_library(data: dict, current_admin=Depends(verify_token)):
    """Save a new clause to the shared library."""
    db = get_db()
    clause_data = {
        "title": data.get("title"),
        "clause_category": data.get("category", "General"),
        "content_html": data.get("content_html"),
        "created_by": current_admin["sub"]
    }
    res = await db_execute(lambda: db.table("legal_clause_library").insert(clause_data).execute())
    return res.data[0]

# ──────────────────────────────────────────────────────────────────
# PHASE 1: TEMPLATE SYSTEM
# ──────────────────────────────────────────────────────────────────

@router.get("/templates")
async def get_template_library(category: str = None, current_admin=Depends(verify_token)):
    """Fetch all available legal templates (filtered by category if provided)."""
    db = get_db()
    query = db.table("legal_templates").select("id, name, category, description, preview_html").eq("is_active", True)
    if category:
        query = query.eq("category", category)
    res = await db_execute(lambda: query.execute())
    return res.data or []

@router.get("/templates/{template_id}")
async def get_template_details(template_id: str, current_admin=Depends(verify_token)):
    """Fetch template with all variables and content."""
    db = get_db()
    template_res = await db_execute(
        lambda: db.table("legal_templates").select("*").eq("id", template_id).execute()
    )
    if not template_res.data:
        raise HTTPException(status_code=404, detail="Template not found")
    
    vars_res = await db_execute(
        lambda: db.table("legal_template_variables").select("*").eq("template_id", template_id).execute()
    )
    
    return {
        "template": template_res.data[0],
        "variables": vars_res.data or []
    }

@router.post("/templates")
async def create_template(data: dict, current_admin=Depends(verify_token)):
    """Create a new template (admin only)."""
    user_roles = {r.strip() for r in (current_admin.get("role") or "").split(",") if r.strip()}
    if not any(r in ["admin", "super_admin", "legal"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Only admins can create templates")
    
    db = get_db()
    template_data = {
        "name": data.get("name"),
        "category": data.get("category"),
        "description": data.get("description"),
        "default_content_html": data.get("content_html"),
        "preview_html": data.get("preview_html"),
        "created_by": current_admin["sub"]
    }
    
    template_res = await db_execute(
        lambda: db.table("legal_templates").insert(template_data).execute()
    )
    if not template_res.data:
        raise HTTPException(status_code=500, detail="Failed to create template")
    
    template_id = template_res.data[0]["id"]
    
    # Insert variables if provided
    if data.get("variables"):
        variables_data = []
        for var in data.get("variables", []):
            variables_data.append({
                "template_id": template_id,
                "var_name": var.get("name"),
                "var_label": var.get("label"),
                "var_type": var.get("type", "text"),
                "required": var.get("required", False),
                "enum_values": var.get("enum_values"),
                "placeholder": var.get("placeholder")
            })
        await db_execute(
            lambda: db.table("legal_template_variables").insert(variables_data).execute()
        )
    
    return template_res.data[0]

@router.post("/matters/from-template/{template_id}")
async def create_matter_from_template(template_id: str, data: dict, current_admin=Depends(verify_token)):
    """Generate a new legal matter pre-populated from a template."""
    db = get_db()
    admin_id = current_admin["sub"]
    
    # Get template
    template_res = await db_execute(
        lambda: db.table("legal_templates").select("*").eq("id", template_id).execute()
    )
    if not template_res.data:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = template_res.data[0]
    
    # Fetch staff data if staff_id provided (for variable substitution)
    staff_data = {}
    if data.get("staff_id"):
        try:
            staff_res = await db_execute(
                lambda: db.table("staff").select("*").eq("id", data.get("staff_id")).execute()
            )
            if staff_res.data:
                staff_data = staff_res.data[0]
        except:
            pass
    
    # Replace variables in template
    content_html = template.get("default_content_html", "")
    variables_used = {}
    
    if content_html and staff_data:
        replacements = {
            "{{STAFF_NAME}}": staff_data.get("full_name", ""),
            "{{ROLE}}": staff_data.get("position_title", ""),
            "{{DEPARTMENT}}": staff_data.get("department", ""),
            "{{SALARY}}": str(staff_data.get("salary", "")),
            "{{COMMENCEMENT_DATE}}": staff_data.get("start_date", ""),
            "{{MANAGER_NAME}}": staff_data.get("manager_name", ""),
        }
        
        for placeholder, value in replacements.items():
            if placeholder in content_html:
                content_html = content_html.replace(placeholder, value)
                variables_used[placeholder.strip("{}")] = value
    
    # Create new matter from template
    matter_data = {
        "title": data.get("title") or f"{template['name']} - {staff_data.get('full_name', 'New')}",
        "category": data.get("category", template.get("category")),
        "drafter_id": admin_id,
        "staff_id": data.get("staff_id"),
        "content_html": content_html,
        "template_used_id": template_id,
        "variables_used": variables_used,
        "status": data.get("status", "Draft"),
        "requires_signing": data.get("requires_signing", True)
    }
    
    res = await db_execute(lambda: db.table("legal_matters").insert(matter_data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create matter from template")
    
    matter = res.data[0]
    
    # Log audit
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter["id"],
        "action": "Created from Template",
        "performed_by": admin_id,
        "description": f"Matter created using template '{template['name']}'"
    }).execute())
    
    return matter

# ──────────────────────────────────────────────────────────────────
# PHASE 3: MEMO THREAD SYSTEM
# ──────────────────────────────────────────────────────────────────

@router.get("/matters/{matter_id}/memos")
async def get_matter_memos(matter_id: str, current_admin=Depends(verify_token)):
    """Fetch all memos for a legal matter."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin)
    
    db = get_db()
    memos_res = await db_execute(
        lambda: db.table("legal_matter_memos")\
            .select("*")\
            .eq("matter_id", matter_id)\
            .order("created_at", desc=False)\
            .execute()
    )
    return memos_res.data or []

@router.post("/matters/{matter_id}/memos")
async def add_matter_memo(matter_id: str, data: dict, current_admin=Depends(verify_token)):
    """Add a memo/note to a legal matter."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    db = get_db()
    
    # Get admin info
    admin_res = await db_execute(
        lambda: db.table("admins").select("full_name, role").eq("id", admin_id).execute()
    )
    admin_info = admin_res.data[0] if admin_res.data else {"full_name": "Unknown", "role": ""}
    
    memo_data = {
        "matter_id": matter_id,
        "author_id": admin_id,
        "author_name": admin_info.get("full_name", "Unknown"),
        "author_role": admin_info.get("role", ""),
        "message_content": data.get("message"),
        "message_type": data.get("type", "note"),
        "is_internal": data.get("is_internal", True),
        "metadata": data.get("metadata", {})
    }
    
    res = await db_execute(lambda: db.table("legal_matter_memos").insert(memo_data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to add memo")
    
    # Audit trail
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Memo Added",
        "performed_by": admin_id,
        "description": f"{admin_info.get('full_name')} added internal note"
    }).execute())
    
    return res.data[0]

@router.patch("/matters/{matter_id}/memos/{memo_id}")
async def update_memo(matter_id: str, memo_id: str, data: dict, current_admin=Depends(verify_token)):
    """Update a memo (author only)."""
    admin_id = current_admin["sub"]
    db = get_db()
    
    # Verify ownership
    memo_res = await db_execute(
        lambda: db.table("legal_matter_memos").select("author_id").eq("id", memo_id).execute()
    )
    if not memo_res.data or memo_res.data[0]["author_id"] != admin_id:
        raise HTTPException(status_code=403, detail="Can only edit your own memos")
    
    update_data = {
        "message_content": data.get("message"),
        "updated_at": datetime.now().isoformat()
    }
    
    await db_execute(
        lambda: db.table("legal_matter_memos").update(update_data).eq("id", memo_id).execute()
    )
    
    return {"status": "updated"}

# ──────────────────────────────────────────────────────────────────
# PHASE 4: DIGITAL SIGNING WORKFLOW
# ──────────────────────────────────────────────────────────────────

def compute_document_hash(html_content: str) -> str:
    """Generate a simple hash of document content for integrity verification."""
    import hashlib
    return hashlib.sha256(html_content.encode()).hexdigest()

def generate_signing_token() -> str:
    """Generate a unique signing token."""
    import secrets
    return secrets.token_urlsafe(32)

@router.get("/matters/{matter_id}/prepare-signing")
async def prepare_signing(
    matter_id: str,
    hash: str,
    title: str,
    current_admin=Depends(verify_token)
):
    """Prepare document for digital signing (verify integrity, create signing request)."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    db = get_db()
    
    # Get the latest document
    matter_res = await db_execute(
        lambda: db.table("legal_matters").select("*").eq("id", matter_id).execute()
    )
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    matter = matter_res.data[0]
    html_content = matter.get("content_html", "")
    
    # Verify document hash (first 16 chars for comparison)
    current_hash = compute_document_hash(html_content)[:16]
    if current_hash != hash[:16]:
        raise HTTPException(status_code=400, detail="Document has been modified since draft save")
    
    # Generate signing token
    signing_token = generate_signing_token()
    
    # Create signing request
    signing_data = {
        "matter_id": matter_id,
        "signing_token": signing_token,
        "status": "Pending",
        "document_hash": current_hash,
        "document_title": title,
        "initiated_by": admin_id
    }
    
    signing_res = await db_execute(
        lambda: db.table("legal_signing_requests").insert(signing_data).execute()
    )
    if not signing_res.data:
        raise HTTPException(status_code=500, detail="Failed to create signing request")
    
    # Update matter status
    await db_execute(
        lambda: db.table("legal_matters").update({
            "status": "Legal Signing"
        }).eq("id", matter_id).execute()
    )
    
    # Audit log
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Signing Initiated",
        "performed_by": admin_id,
        "description": f"Document '{title}' prepared for e-signature (token: {signing_token[:8]}...)"
    }).execute())
    
    return {
        "signing_token": signing_token,
        "signing_url": f"/signing/{signing_token}",
        "matter_id": matter_id,
        "title": title,
        "status": "Pending"
    }

@router.post("/matters/{matter_id}/dispatch-signature")
async def dispatch_signature(
    matter_id: str,
    current_admin=Depends(verify_token)
):
    """Sends the signing link to the recipient (Staff or External Party) associated with the matter."""
    admin_id = current_admin["sub"]
    db = get_db()
    
    # 1. Fetch Matter & Signing Request
    matter_res = await db_execute(
        lambda: db.table("legal_matters")\
            .select("*, legal_signing_requests(*)")\
            .eq("id", matter_id)\
            .execute()
    )
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    matter = matter_res.data[0]
    signing_reqs = [r for r in matter.get("legal_signing_requests", []) if r["status"] == "Pending"]
    if not signing_reqs:
        raise HTTPException(status_code=400, detail="No pending signing request found for this matter. Please 'Seal & Prepare' first.")
    
    signing_req = signing_reqs[0]
    signing_token = signing_req["signing_token"]
    
    # 2. Identify Recipient (Staff lookup or External Party fields)
    staff_id = matter.get("staff_id")
    signer_name = None
    signer_email = None
    recipient_type = "Internal Staff"

    if staff_id:
        staff_res = await db_execute(lambda: db.table("staff").select("full_name, email").eq("id", staff_id).execute())
        if staff_res.data:
            staff = staff_res.data[0]
            signer_name = staff.get("full_name")
            signer_email = staff.get("email")
    
    if not signer_email:
        # Fallback to external party details if staff lookup fails or staff_id is null
        signer_name = matter.get("external_party_name")
        signer_email = matter.get("external_party_email")
        recipient_type = "External Party"

    if not signer_email:
        raise HTTPException(status_code=400, detail="No valid recipient found. Please update the matter with a staff member or external party email.")
    
    # 3. Dispatch Email
    from email_service import send_staff_signing_request_email
    signing_url = f"{APP_BASE_URL}/signing/{signing_token}"
    
    await send_staff_signing_request_email(
        staff_name=signer_name or "Valued Partner",
        email_addr=signer_email,
        doc_title=matter.get("title", "Legal Document"),
        signing_url=signing_url
    )
    
    # 4. Audit Log
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Signer Notification Sent",
        "performed_by": admin_id,
        "description": f"Signing link dispatched to {recipient_type}: {signer_email}"
    }).execute())
    
    return {"status": "dispatched", "message": f"Signature link sent to {recipient_type}"}

@router.get("/signing/{signing_token}/details")
async def get_signing_details(signing_token: str):
    """Fetch signing request details (no auth required for signing page)."""
    db = get_db()
    
    signing_res = await db_execute(
        lambda: db.table("legal_signing_requests")\
            .select("*, legal_matters(id, title, content_html, category, drafter_id, requires_signing)")\
            .eq("signing_token", signing_token)\
            .execute()
    )
    
    if not signing_res.data:
        raise HTTPException(status_code=404, detail="Signing request not found")
    
    signing_req = signing_res.data[0]
    
    # Check if expired
    expiry = signing_req.get("expiry_at")
    if expiry and datetime.fromisoformat(expiry) < datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=410, detail="Signing link has expired")
    
    # Extract requires_signing from nested matter object
    matter = signing_req.get("legal_matters", {}) or {}
    requires_signing = matter.get("requires_signing", True) if isinstance(matter, dict) else True
    
    # Add to response
    signing_req["requires_signing"] = requires_signing
    
    return signing_req

@router.post("/signing/{signing_token}/submit")
async def submit_signature(signing_token: str, data: dict):
    """Submit signature data (completes signing workflow)."""
    db = get_db()
    
    # Get signing request
    signing_res = await db_execute(
        lambda: db.table("legal_signing_requests").select("*").eq("signing_token", signing_token).execute()
    )
    
    if not signing_res.data:
        raise HTTPException(status_code=404, detail="Signing request not found")
    
    signing_req = signing_res.data[0]
    matter_id = signing_req["matter_id"]
    
    # Check if already signed
    if signing_req["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Signing request already processed")
    
    # Update signing request
    await db_execute(
        lambda: db.table("legal_signing_requests").update({
            "status": "Signed",
            "signed_at": datetime.now().isoformat(),
            "signer_email": data.get("signer_email"),
            "signer_name": data.get("signer_name"),
            "signature_metadata": {
                "signature_image": data.get("signature_image", ""),
                "timestamp": datetime.now().isoformat(),
                "ip_address": data.get("ip_address", ""),
                "user_agent": data.get("user_agent", "")
            }
        }).eq("id", signing_req["id"]).execute()
    )
    
    # Update matter status + patch content_html with signature
    matter_res = await db_execute(
        lambda: db.table("legal_matters").select("staff_id, content_html").eq("id", matter_id).execute()
    )
    
    if matter_res.data:
        matter = matter_res.data[0]
        signer_name  = data.get("signer_name", "Signatory")
        signer_email = data.get("signer_email", "")
        sig_image    = data.get("signature_image", "")
        signed_at    = datetime.now().strftime("%d %B %Y, %H:%M")

        # ── Build the executed signature block ──
        sig_block = f"""
<div style="margin-top: 60px; border-top: 2px solid #C47D0A; padding-top: 20px; font-family: 'Times New Roman', serif;">
  <p style="font-size: 9pt; font-weight: 700; color: #C47D0A; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 16px;">
    ✓ Executed &amp; Digitally Signed
  </p>
  <table style="width: 100%; border-collapse: collapse;">
    <tr>
      <td style="width: 50%; padding-right: 40px; vertical-align: top;">
        <p style="font-size: 8pt; font-weight: 700; color: #333; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">Employee / Signatory</p>
        {"<img src='" + sig_image + "' style='max-width: 200px; max-height: 80px; border: 1px solid #eee; padding: 4px; display: block; margin-bottom: 6px;'>" if sig_image else "<div style='height: 60px; border-bottom: 1px solid #333; margin-bottom: 6px;'></div>"}
        <p style="font-size: 9pt; font-weight: 700; margin: 0;">{signer_name}</p>
        <p style="font-size: 8pt; color: #666; margin: 2px 0 0;">{signer_email}</p>
        <p style="font-size: 8pt; color: #888; margin: 4px 0 0;">Date: {signed_at}</p>
      </td>
      <td style="width: 50%; padding-left: 40px; vertical-align: top; border-left: 1px solid #eee;">
        <p style="font-size: 8pt; font-weight: 700; color: #333; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">Employer / Authorized Representative</p>
        <div style="height: 60px; border-bottom: 1px solid #333; margin-bottom: 6px;">
          <img src="{APP_BASE_URL}/static/img/logo_firm.png" style="height: 48px; width: auto; opacity: 0.7;" onerror="">
        </div>
        <p style="font-size: 9pt; font-weight: 700; margin: 0;">Eximp &amp; Cloves Infrastructure Limited</p>
        <p style="font-size: 8pt; color: #888; margin: 4px 0 0;">Date: {signed_at}</p>
      </td>
    </tr>
  </table>
</div>"""

        # ── Resolve placeholders in existing content_html ──
        seal_html = """<div style="display:inline-flex;flex-direction:column;align-items:center;border:3px solid #C47D0A;border-radius:50%;width:110px;height:110px;justify-content:center;padding:8px;text-align:center;box-shadow:0 0 0 2px #C47D0A inset;"><img src="{base}/static/img/logo_firm.png" style="height:44px;width:auto;"><span style="font-size:6pt;font-weight:900;letter-spacing:0.1em;color:#C47D0A;text-transform:uppercase;line-height:1.2;">EXIMP &amp; CLOVES<br>SEAL</span></div>""".format(base=APP_BASE_URL)
        stamp_html = f"""<div style="display:inline-block;border:2px solid #C47D0A;padding:8px 18px;text-align:center;transform:rotate(-8deg);opacity:0.85;"><div style="font-size:8pt;font-weight:900;letter-spacing:0.15em;color:#C47D0A;text-transform:uppercase;">AUTHORIZED</div><div style="font-size:7pt;font-weight:700;color:#333;text-transform:uppercase;">Eximp &amp; Cloves Infrastructure Ltd.</div><div style="font-size:7pt;color:#888;">{signed_at}</div></div>"""

        raw_html = matter.get("content_html") or ""
        raw_html = raw_html.replace("{{ seal }}", seal_html).replace("{{ stamp }}", stamp_html)
        patched_html = raw_html + sig_block

        update_data = {
            "status": "Executed",
            "signed_at": datetime.now().isoformat(),
            "signed_by": signer_email,
            "staff_visible": True,
            "content_html": patched_html,
            "signature_metadata": {
                "signing_token": signing_token[:8],
                "signer_name": signer_name,
                "signer_email": signer_email,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await db_execute(
            lambda: db.table("legal_matters").update(update_data).eq("id", matter_id).execute()
        )
        
        # Auto-link to HR Staff Profile if staff_id exists
        if matter.get("staff_id"):
            try:
                await db_execute(
                    lambda: db.table("staff_documents").insert({
                        "staff_id": matter["staff_id"],
                        "document_type": "Legal Contract - Executed",
                        "document_link": f"/api/hr-legal/matters/{matter_id}/export",
                        "uploaded_at": datetime.now().isoformat()
                    }).execute()
                )
            except:
                pass  # Document link may already exist
    
    # Audit trail
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Document Executed",
        "performed_by": None,
        "description": f"Contract signed by {data.get('signer_name')} ({data.get('signer_email')})"
    }).execute())
    
    return {
        "status": "success",
        "message": "Document signed successfully",
        "matter_id": matter_id,
        "redirect": f"/matters/{matter_id}"
    }

@router.post("/signing/{signing_token}/acknowledge")
async def acknowledge_document(signing_token: str, data: dict):
    """Acknowledge document receipt (for non-signing contracts)."""
    db = get_db()
    
    # Get signing request
    signing_res = await db_execute(
        lambda: db.table("legal_signing_requests").select("*").eq("signing_token", signing_token).execute()
    )
    
    if not signing_res.data:
        raise HTTPException(status_code=404, detail="Signing request not found")
    
    signing_req = signing_res.data[0]
    matter_id = signing_req["matter_id"]
    
    # Check if already processed
    if signing_req["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Document already processed")
    
    # Update signing request to "Acknowledged" status
    await db_execute(
        lambda: db.table("legal_signing_requests").update({
            "status": "Acknowledged",
            "acknowledged_at": datetime.now().isoformat(),
            "signature_metadata": {
                "type": "acknowledgment",
                "timestamp": data.get("timestamp"),
                "user_agent": data.get("user_agent", "")
            }
        }).eq("id", signing_req["id"]).execute()
    )
    
    # Update matter status to Executed
    matter_res = await db_execute(
        lambda: db.table("legal_matters").select("staff_id").eq("id", matter_id).execute()
    )
    
    if matter_res.data:
        matter = matter_res.data[0]
        update_data = {
            "status": "Executed",
            "signed_at": datetime.now().isoformat(),
            "signed_by": "acknowledged",
            "signature_metadata": {
                "type": "acknowledgment",
                "acknowledged_at": datetime.now().isoformat()
            }
        }
        
        await db_execute(
            lambda: db.table("legal_matters").update(update_data).eq("id", matter_id).execute()
        )
        
        # Auto-link to HR Staff Profile if staff_id exists
        if matter.get("staff_id"):
            try:
                await db_execute(
                    lambda: db.table("staff_documents").insert({
                        "staff_id": matter["staff_id"],
                        "document_type": "Legal Contract - Acknowledged",
                        "document_link": f"/api/hr-legal/matters/{matter_id}/export",
                        "uploaded_at": datetime.now().isoformat()
                    }).execute()
                )
            except:
                pass  # Document link may already exist
    
    # Audit trail
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Document Acknowledged",
        "performed_by": None,
        "description": "Contract acknowledged by recipient (no signature required)"
    }).execute())
    
    return {
        "status": "success",
        "message": "Document acknowledged successfully",
        "matter_id": matter_id,
        "redirect": f"/matters/{matter_id}"
    }

@router.get("/matters/{matter_id}/signing-status")
async def get_signing_status(matter_id: str, current_admin=Depends(verify_token)):
    """Check current signing status of a matter."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, admin_id)
    
    db = get_db()
    signing_res = await db_execute(
        lambda: db.table("legal_signing_requests")\
            .select("*")\
            .eq("matter_id", matter_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
    )
    
    if not signing_res.data:
        return {"status": "No signing request", "message": "Document has not been prepared for signing yet"}
    
    return signing_res.data[0]

# ──────────────────────────────────────────────────────────────────
# PHASE 5: HR PORTAL INTEGRATION
# ──────────────────────────────────────────────────────────────────

@router.post("/staff/{staff_id}/create-legal-case")
async def create_legal_case_from_staff(staff_id: str, data: dict, current_admin=Depends(verify_token)):
    """
    HR Portal: Quick case creation for a staff member.
    Creates a new legal matter with staff context pre-filled.
    """
    user_roles = {r.strip() for r in (current_admin.get("role") or "").split(",") if r.strip()}
    if not any(r in ["admin", "super_admin", "hr_admin", "hr"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Only HR admins can create legal cases")
    
    db = get_db()
    admin_id = current_admin["sub"]
    
    # Verify staff exists
    staff_res = await db_execute(
        lambda: db.table("staff").select("id, full_name, position_title, department").eq("id", staff_id).execute()
    )
    if not staff_res.data:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    staff = staff_res.data[0]
    
    # Create legal matter
    matter_data = {
        "title": data.get("title", f"Legal Case - {staff['full_name']}"),
        "category": data.get("category", "Contract Request"),
        "drafter_id": admin_id,
        "staff_id": staff_id,
        "hr_memo": data.get("hr_memo", ""),
        "status": "Draft",
        "requires_signing": data.get("requires_signing", True)
    }
    
    matter_res = await db_execute(
        lambda: db.table("legal_matters").insert(matter_data).execute()
    )
    if not matter_res.data:
        raise HTTPException(status_code=500, detail="Failed to create legal case")
    
    matter = matter_res.data[0]
    
    # Log audit
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter["id"],
        "action": "Case Created from HR Portal",
        "performed_by": admin_id,
        "description": f"Legal case created for staff member {staff['full_name']} from HR Portal"
    }).execute())
    
    return {
        "matter_id": matter["id"],
        "staff_id": staff_id,
        "staff_name": staff["full_name"],
        "editor_url": f"/legal/advanced-editor?id={matter['id']}"
    }

@router.get("/case-categories")
async def get_case_categories(current_admin=Depends(verify_token)):
    """Fetch available legal case categories for HR portal."""
    return {
        "categories": [
            {
                "id": "Contract Request",
                "name": "📄 Contract Request",
                "description": "Employment offer or contract generation"
            },
            {
                "id": "Disciplinary Review",
                "name": "⚠️ Disciplinary Review",
                "description": "Performance issues or conduct violations"
            },
            {
                "id": "Legal Clearance",
                "name": "✓ Legal Clearance",
                "description": "Background check or compliance review"
            },
            {
                "id": "Termination",
                "name": "📋 Termination",
                "description": "Separation agreement or exit documentation"
            },
            {
                "id": "Other",
                "name": "📝 Other",
                "description": "Other legal matter"
            }
        ]
    }

# ──────────────────────────────────────────────────────────────────
# PHASE 6: STAFF VISIBILITY & PERSONNEL-FACING ACCESS
# ──────────────────────────────────────────────────────────────────

@router.patch("/matters/{matter_id}/visibility")
async def toggle_matter_visibility(matter_id: str, data: dict, current_admin=Depends(verify_token)):
    """
    HR/Legal only: Toggle whether staff member can see this matter.
    Only matters marked staff_visible=true are shown to the personnel.
    """
    user_roles = {r.strip() for r in (current_admin.get("role") or "").split(",") if r.strip()}
    if not any(r in ["admin", "super_admin", "hr_admin", "hr", "legal"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Only HR and Legal can control visibility")
    
    admin_id = current_admin["sub"]
    db = get_db()
    
    # Verify matter exists
    matter_res = await db_execute(lambda: db.table("legal_matters").select("id").eq("id", matter_id).execute())
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    # Update visibility
    staff_visible = data.get("staff_visible", False)
    await db_execute(lambda: db.table("legal_matters").update({
        "staff_visible": staff_visible,
        "updated_at": datetime.now().isoformat()
    }).eq("id", matter_id).execute())
    
    # Audit trail
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Visibility Changed",
        "performed_by": admin_id,
        "description": f"Matter marked as {'visible' if staff_visible else 'confidential'} to staff member"
    }).execute())
    
    return {"status": "updated", "staff_visible": staff_visible}

@router.get("/staff/self/visible-matters")
async def get_staff_visible_matters(current_admin=Depends(verify_token)):
    """
    Staff Portal: Fetch only the legal matters marked as visible to this staff member.
    Staff can ONLY see matters where staff_visible=true AND staff_id matches their ID.
    """
    admin_id = current_admin["sub"]
    db = get_db()
    
    # Get matters visible to this specific staff member
    res = await db_execute(lambda: db.table("legal_matters")\
        .select("id, title, category, status, created_at, content_html")\
        .eq("staff_id", admin_id)\
        .eq("staff_visible", True)\
        .order("created_at", desc=True).execute())
    
    return {"matters": res.data or [], "count": len(res.data) if res.data else 0}

@router.get("/staff/self/visible-matters/{matter_id}")
async def get_staff_visible_matter(matter_id: str, current_admin=Depends(verify_token)):
    """
    Staff Portal: Read-only access to a specific visible matter.
    Staff can ONLY view if staff_visible=true AND staff_id matches their ID.
    """
    admin_id = current_admin["sub"]
    roles = current_admin.get("role", "").lower().split(",")
    is_privileged = any(r.strip() in ["hr", "lawyer", "legal", "admin", "super_admin"] for r in roles)
    
    db = get_db()
    
    # Fetch matter
    query = db.table("legal_matters").select("id, title, category, status, created_at, content_html").eq("id", matter_id)
    
    if not is_privileged:
        # Standard staff can only view if it's explicitly assigned to them and marked visible
        query = query.eq("staff_id", admin_id).eq("staff_visible", True)
        
    matter_res = await db_execute(lambda: query.execute())
    
    if not matter_res.data:
        raise HTTPException(status_code=403, detail="You do not have permission to view this matter")
    
    matter = matter_res.data[0]
    
    # Audit trail (staff viewed document)
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Staff Viewed",
        "performed_by": admin_id,
        "description": "Staff member accessed visible matter"
    }).execute())
    
    return matter


@router.get("/matters/{matter_id}/export")
async def export_matter_pdf(matter_id: str, token: str = None, current_admin=Depends(resolve_admin_token)):
    """
    Generate a full-page PDF of a legal matter, including the company letterhead,
    body content (with seals/stamps/signatures embedded), and branded footer.
    Accepts a ?token= query param for direct browser download links.
    """
    admin_id = current_admin["sub"]
    roles = current_admin.get("role", "").lower().split(",")
    is_privileged = any(r.strip() in ["hr", "lawyer", "legal", "admin", "super_admin"] for r in roles)

    db = get_db()
    query = db.table("legal_matters").select("id, title, content_html, staff_id").eq("id", matter_id)
    if not is_privileged:
        query = query.eq("staff_id", admin_id).eq("staff_visible", True)

    res = await db_execute(lambda: query.execute())
    if not res.data:
        raise HTTPException(status_code=403, detail="You do not have permission to access this document")

    matter = res.data[0]
    title = matter.get("title", "Legal Document")
    body_html = matter.get("content_html", "<p>No content.</p>") or "<p>No content.</p>"

    # Build full branded HTML document for WeasyPrint
    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Tinos:ital,wght@0,400;0,700;1,400;1,700&display=swap');
  :root {{ --brand-gold: #C47D0A; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  @page {{
    size: A4;
    margin: 0;
  }}
  body {{
    font-family: 'Tinos', 'Times New Roman', serif;
    font-size: 11pt;
    color: #000;
    background: white;
  }}
  .page {{
    width: 210mm;
    min-height: 297mm;
    display: flex;
    flex-direction: column;
    position: relative;
  }}

  /* ── LETTERHEAD ── */
  .letterhead {{ position: relative; padding: 0; }}
  .header-bar-black {{
    position: absolute; top: 0; left: 0;
    width: 60%; height: 40px;
    background: #000;
    border-bottom-right-radius: 40px;
  }}
  .header-bar-gold {{
    position: absolute; top: 0; right: 0;
    width: 40%; height: 30px;
    background: var(--brand-gold);
  }}
  .letterhead-inner {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 50px 60px 20px;
    position: relative;
    z-index: 2;
  }}
  .logo-img {{ height: 70px; width: auto; }}
  .letterhead-contact {{
    border-left: 2px solid #000;
    padding: 4px 15px;
    font-size: 9pt;
    line-height: 1.7;
    color: #111;
    font-weight: 700;
    font-variant: small-caps;
    letter-spacing: 0.05em;
    font-family: 'Inter', sans-serif;
  }}
  .letterhead-contact a {{ color: var(--brand-gold); text-decoration: none; }}
  .letterhead-divider {{ height: 2px; background: #eee; margin: 0 60px; }}

  /* ── BODY ── */
  .document-body {{
    padding: 28px 72px;
    flex: 1;
    line-height: 1.6;
  }}
  .document-body h1 {{ font-size: 18pt; font-weight: 800; margin: 20pt 0 10pt; }}
  .document-body h2 {{ font-size: 14pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; margin: 16pt 0 8pt; }}
  .document-body h3 {{ font-size: 12pt; font-weight: 600; margin: 14pt 0 6pt; }}
  .document-body p {{ margin-bottom: 8pt; }}
  .document-body ul {{ margin: 8pt 0 8pt 24pt; list-style: disc; }}
  .document-body ol {{ margin: 8pt 0 8pt 24pt; }}
  .document-body table {{ width: 100%; border-collapse: collapse; margin: 12pt 0; }}
  .document-body td, .document-body th {{ border: 1px solid #ccc; padding: 6pt 8pt; font-size: 10pt; }}
  .document-body th {{ background: #f5f5f5; font-weight: 700; }}
  .document-body hr {{ border: none; border-top: 1px solid #ccc; margin: 20pt 0; }}
  .document-body img {{ max-width: 100%; height: auto; }}

  /* ── FOOTER ── */
  .page-footer {{ margin-top: auto; }}
  .footer-bar-container {{ display: flex; height: 12px; }}
  .footer-black {{ flex: 1; background: #000; }}
  .footer-gold {{ flex: 1; background: var(--brand-gold); }}
</style>
</head>
<body>
<div class="page">
  <div class="letterhead">
    <div class="header-bar-black"></div>
    <div class="header-bar-gold"></div>
    <div class="letterhead-inner">
      <img class="logo-img" src="{APP_BASE_URL}/static/img/logo_firm.png" alt="Eximp &amp; Cloves">
      <div class="letterhead-contact">
        <div>Phone: +234 912 6864 383</div>
        <div>Web: <a href="https://eximps-cloves.com">https://eximps-cloves.com</a></div>
        <div>Email: <a href="mailto:admin@eximps-cloves.com">admin@eximps-cloves.com</a></div>
      </div>
    </div>
    <div class="letterhead-divider"></div>
  </div>

  <div class="document-body">
    {body_html}
  </div>

  <div class="page-footer">
    <div class="footer-bar-container">
      <div class="footer-black"></div>
      <div class="footer-gold"></div>
    </div>
  </div>
</div>
</body>
</html>"""

    try:
        from weasyprint import HTML as WeasyprintHTML
        import io
        pdf_bytes = WeasyprintHTML(string=full_html, base_url=APP_BASE_URL).write_pdf()
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "document"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
