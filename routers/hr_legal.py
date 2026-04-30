from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import Response
import os
from database import get_db, db_execute, SUPABASE_URL
import os
from routers.auth import verify_token, verify_token_optional, resolve_admin_token
from datetime import datetime, timezone, timedelta
import json
import uuid
import pdf_service

router = APIRouter()
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com")

# ── HELPER: LEGAL BRANDING ──
async def get_branding_urls():
    """Fetches high-fidelity Seal and Stamp URLs from the Signature Vault (company_signatures table)."""
    db = get_db()
    res = await db_execute(lambda: db.table("company_signatures").select("*").eq("is_active", True).execute())
    
    branding = {
        "seal_url": None, 
        "stamp_url": None, 
        "auth_signature": None, 
        "auth_name": "Managing Director",
        "firm_logo": f"{APP_BASE_URL}/static/img/logo_firm.png"
    }

    if res.data:
        for sig in res.data:
            role = sig.get("role", "").lower()
            url = sig.get("signature_base64")
            if not url: continue
            
            # Company stamp/seal
            if role == "stamp" or role == "seal":
                branding["stamp_url" if role == "stamp" else "seal_url"] = url
            
            # Authorized Signatory
            if role == "director" or role == "md" or (role == "ceo" and not branding["auth_signature"]):
                branding["auth_signature"] = url
                branding["auth_name"] = "Managing Director"
            elif role == "lawyer" and not branding["auth_signature"]:
                branding["auth_signature"] = url
                branding["auth_name"] = "Legal Counsel"
    
    # ── SMART DISCOVERY FALLBACK ──
    # If URLs are missing but we have an authority signature, try to find seal/stamp in the same folder
    if branding["auth_signature"] and (not branding["seal_url"] or not branding["stamp_url"]):
        base_path = branding["auth_signature"].rsplit('/', 1)[0]
        if not branding["seal_url"]:
            branding["seal_url"] = f"{base_path}/seal.png"
        if not branding["stamp_url"]:
            branding["stamp_url"] = f"{base_path}/stamp.png"

    return branding

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

@router.get("/branding")
async def get_legal_branding_api(current_admin=Depends(verify_token_optional)):
    """Fetch official branding assets for the Personnel Editor. 
    Accessible to anyone with a valid token (including previewers)."""
    return await get_branding_urls()

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
    matter_res = await db_execute(lambda: db.table("legal_matters").select("*, staff:admins!legal_matters_staff_id_fkey(*)").eq("id", matter_id).execute())
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
    if "css" in data:
        update_data["content_css"] = data.get("css")
    
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
                lambda: db.table("admins").select("*").eq("id", data.get("staff_id")).execute()
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

@router.post("/matters/{matter_id}/prepare-signing")
async def prepare_signing(
    matter_id: str,
    data: dict,
    current_admin=Depends(verify_token)
):
    """Prepare document for digital signing (verify integrity, update settings, create signing request)."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, current_admin, required_level="Edit")
    
    title = data.get("title", "Untitled Document")
    hash = data.get("hash")
    requires_signing = data.get("requires_signing", True)
    
    db = get_db()
    
    # 1. Update the matter itself with the signing preference
    await db_execute(
        lambda: db.table("legal_matters").update({
            "requires_signing": requires_signing
        }).eq("id", matter_id).execute()
    )
    
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
    data: dict = {},
    current_admin=Depends(verify_token)
):
    """Sends the signing link to the recipient (Staff or External Party) and includes a custom message."""
    admin_id = current_admin["sub"]
    custom_message = data.get("message")
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
        staff_res = await db_execute(lambda: db.table("admins").select("full_name, email").eq("id", staff_id).execute())
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
        signing_url=signing_url,
        custom_message=custom_message
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
            .select("*, legal_matters(*)")\
            .eq("signing_token", signing_token)\
            .execute()
    )
    
    if not signing_res.data:
        raise HTTPException(status_code=404, detail="Signing request not found")
    
    signing_req = signing_res.data[0]
    
    # Check if expired
    expiry = signing_req.get("expiry_at")
    if expiry and datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
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
                "has_drawn_signature": bool(data.get("signature_image", "")),
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
        lagos_tz = timezone(timedelta(hours=1))
        signed_at = datetime.now(lagos_tz).strftime("%d %B %Y, %H:%M")

        # ── Resolve placeholders in existing content_html ──
        branding = await get_branding_urls()
        logo_url = branding.get("firm_logo")
        stamp_url = branding.get("stamp_url")
        auth_sig = branding.get("auth_signature")
        auth_name = branding.get("auth_name", "Authorized Signatory")

        # ── Update sig_block with actual Authority Signature ──
        sig_block = f"""
<div style="margin-top: 60px; border-top: 2px solid #C47D0A; padding-top: 20px; font-family: 'Times New Roman', serif;">
  <p style="font-size: 9pt; font-weight: 700; color: #C47D0A; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 16px;">
    ✓ Executed &amp; Digitally Signed
  </p>
  <table style="width: 100%; border-collapse: collapse;">
    <tr>
      <td style="width: 50%; padding-right: 40px; vertical-align: top;">
        <p style="font-size: 8pt; font-weight: 700; color: #333; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">Employee / Signatory</p>
        {"<img src='" + sig_image + "' width='200' height='80' style='max-width:200px;max-height:80px;width:auto;height:auto;border:1px solid #eee;padding:6px;display:block;margin-bottom:6px;background:#fff;'>" if sig_image else "<div style='height:60px;border-bottom:1px solid #333;margin-bottom:6px;'></div>"}
        <p style="font-size: 9pt; font-weight: 700; margin: 0;">{signer_name}</p>
        <p style="font-size: 8pt; color: #666; margin: 2px 0 0;">{signer_email}</p>
        <p style="font-size: 8pt; color: #888; margin: 4px 0 0;">Date: {signed_at}</p>
      </td>
      <td style="width: 50%; padding-left: 40px; vertical-align: top; border-left: 1px solid #eee;">
        <p style="font-size: 8pt; font-weight: 700; color: #333; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">Employer / Authorized Representative</p>
        <div style="height: 60px; border-bottom: 1px solid #333; margin-bottom: 6px;">
          {f"<img src='{auth_sig}' style='max-height: 60px; width: auto; opacity: 1;'>" if auth_sig else f"<img src='{logo_url}' style='height: 48px; width: auto; opacity: 0.7;'>"}
        </div>
        <p style="font-size: 9pt; font-weight: 700; margin: 0;">Eximp &amp; Cloves Infrastructure Limited</p>
        <p style="font-size: 8pt; color: #666; font-weight: 600; margin: 2px 0 0;">{auth_name}</p>
        <p style="font-size: 8pt; color: #888; margin: 4px 0 0;">Date: {signed_at}</p>
      </td>
    </tr>
  </table>
</div>"""

        # Seal is dynamic CSS (Elite badge)

        # Seal is dynamic CSS (Elite badge)
        seal_html = f"""<div class="legal-badge seal-badge" style="display:inline-flex;flex-direction:column;align-items:center;border:3px solid #C47D0A;border-radius:50%;width:110px;height:110px;justify-content:center;padding:8px;text-align:center;box-shadow:0 0 0 2px #C47D0A inset;line-height:1.1;background:rgba(196,125,10,0.05);color:#C47D0A;vertical-align:middle;margin:10px;"><img src="{logo_url}" style="height:40px;width:auto;margin-bottom:2px;opacity:0.9;"><span style="font-size:6.5pt;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;">OFFICIAL<br>CORPORATE SEAL</span></div>"""
        
        if stamp_url:
            stamp_html = f"""<div class="legal-badge stamp-badge" style="display:inline-block;border:2px solid #C47D0A;padding:10px 20px;text-align:center;transform:rotate(-3deg);opacity:0.9;background:rgba(196,125,10,0.05);color:#C47D0A;vertical-align:middle;margin:10px;"><img src="{stamp_url}" style="height:36px;width:auto;display:block;margin:0 auto 4px;"><div style="font-size:10pt;font-weight:900;letter-spacing:0.15em;text-transform:uppercase;">AUTHORIZED</div><div style="font-size:8pt;color:#888;">{signed_at}</div></div>"""
        else:
            stamp_html = f"""<div class="legal-badge stamp-badge" style="display:inline-block;border:2px solid #C47D0A;padding:10px 20px;text-align:center;transform:rotate(-3deg);opacity:0.9;background:rgba(196,125,10,0.05);color:#C47D0A;vertical-align:middle;margin:10px;"><div style="font-size:10pt;font-weight:900;letter-spacing:0.15em;text-transform:uppercase;">AUTHORIZED</div><div style="font-size:8pt;font-weight:700;color:#333;text-transform:uppercase;">Eximp &amp; Cloves Infrastructure Ltd.</div><div style="font-size:8pt;color:#888;">{signed_at}</div></div>"""

        raw_html = matter.get("content_html") or ""
        raw_html = raw_html.replace("{{ seal }}", seal_html).replace("{{ stamp }}", stamp_html)
        patched_html = raw_html + sig_block

        update_data = {
            "status": "Executed",
            "signed_at": datetime.now(timezone(timedelta(hours=1))).isoformat(),
            "executed_at": datetime.now(timezone(timedelta(hours=1))).isoformat(),
            "signed_by": signer_email,
            "staff_visible": True,
            "content_html": patched_html,
            "signature_metadata": {
                "signing_token": signing_token[:8],
                "signer_name": signer_name,
                "signer_email": signer_email,
                "timestamp": datetime.now(timezone(timedelta(hours=1))).isoformat()
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
                        "uploaded_at": datetime.now(timezone(timedelta(hours=1))).isoformat()
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

    # ── Fire post-execution confirmation email (non-blocking) ──
    await _send_matter_executed_email(
        matter_id=matter_id,
        signing_token=signing_token,
        signer_name=data.get("signer_name", "Signatory"),
        signer_email=data.get("signer_email", "")
    )

    return {
        "status": "success",
        "message": "Document signed successfully",
        "matter_id": matter_id,
        "redirect": f"/matters/{matter_id}"
    }

async def _send_matter_executed_email(matter_id: str, signing_token: str, signer_name: str, signer_email: str):
    """Refactored helper to send PDF confirmation after either signing or acknowledgment."""
    db = get_db()
    try:
        from email_service import send_personnel_executed_email
        from weasyprint import HTML as WeasyprintHTML

        # Fetch the final executed matter for email
        exec_matter = await db_execute(
            lambda: db.table("legal_matters").select("title, content_html, content_css").eq("id", matter_id).execute()
        )
        if not exec_matter.data: return
        
        exec_audit = await db_execute(
            lambda: db.table("legal_matter_history").select("*").eq("matter_id", matter_id).order("created_at", desc=False).execute()
        )

        matter_data = exec_matter.data[0]
        doc_title = matter_data.get("title", "Legal Document")
        body_html = matter_data.get("content_html", "")
        contact_html = matter_data.get("content_css")
        
        if not contact_html or contact_html.strip() == "":
            contact_html = """<div>phone: +234 912 6864 383</div>
        <div>web: <a href="https://eximps-cloves.com" class="text-brand-gold">https://eximps-cloves.com</a></div>
        <div>email: <a href="mailto:admin@eximps-cloves.com" class="text-brand-gold">admin@eximps-cloves.com</a></div>"""

        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, "static", "img", "logo_firm.png")
        logo_uri = "file:///" + logo_path.replace("\\", "/")
        
        # Ensure weasyprint can resolve logos
        body_html = body_html.replace(f"{APP_BASE_URL}/static/img/logo_firm.png", logo_uri)
        audit_entries = exec_audit.data or []

        # Build full PDF (Using the shared styles we established earlier)
        pdf_full_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Tinos:ital,wght@0,400;0,700;1,400;1,700&display=swap');
  @page {{ size: A4; margin: 0; }}
  body {{ font-family: 'Tinos', 'Times New Roman', serif; font-size: 11pt; color: #000; background: white; margin: 0; padding: 0; }}
  
  /* ── ABSOLUTE BARS (Pinned to Page Top) ── */
  .bar-black {{ position: absolute; top: 0; left: 0; width: 60%; height: 40px; background: #000; border-bottom-right-radius: 40px; z-index: 100; }}
  .bar-gold {{ position: absolute; top: 0; right: 0; width: 70%; height: 30px; background: #C47D0A; z-index: 90; }}
  
  /* ── MAIN CONTENT (Pushed down by padding) ── */
  .main-wrapper {{ position: relative; z-index: 200; width: 100%; }}
  
  .header-content {{ padding: 50px 60px 10px; width: 100%; box-sizing: border-box; }}
  .logo-box {{ float: left; width: 50%; }}
  .contact-box {{ float: right; width: 45%; border-left: 2px solid #000; padding: 4px 15px; font-size: 9pt; line-height: 1.4; color: #111; font-weight: 700; font-variant-caps: all-small-caps; letter-spacing: 0.05em; font-family: 'Inter', sans-serif; }}
  .contact-box a {{ color: #C47D0A; text-decoration: none; }}
  
  .clear {{ clear: both; height: 1px; }}
  .divider {{ height: 2px; background: #eee; margin: 10px 60px 0; }}
  
  .body {{ padding: 30px 72px; line-height: 1.6; text-align: justify; }}
  .body p {{ margin-bottom: 12pt; min-height: 1.2em; }}
  .body ol, .body ul {{ padding: 0 0 0 40px; margin: 12pt 0; list-style-position: outside; }}
  .body li {{ margin-bottom: 8pt; padding-left: 5px; }}
  /* Automatic Parent-Child Nesting */
  .body ol {{ list-style-type: decimal; }}
  .body ol ol {{ list-style-type: lower-alpha; margin: 6pt 0; }}
  .body ol ol ol {{ list-style-type: lower-roman; margin: 4pt 0; }}
  .body ul {{ list-style-type: disc; }}
  .body ul ul {{ list-style-type: circle; }}
  /* Force specific types if overridden by user */
  .body ol[type="a"] {{ list-style-type: lower-alpha !important; }}
  .body ol[type="A"] {{ list-style-type: upper-alpha !important; }}
  .body ol[type="i"] {{ list-style-type: lower-roman !important; }}
  .body ol[type="I"] {{ list-style-type: upper-roman !important; }}
  .body img {{ max-width: 100%; height: auto; display: block; }}
  
  .footer {{ position: absolute; bottom: 0; left: 0; width: 100%; }}
  .footer-bars {{ display: flex; height: 12px; }}
  .fb {{ flex: 1; background: #000; }}
  .fg {{ flex: 1; background: #C47D0A; }}
</style>
</head>
<body>
  <div class="bar-black"></div>
  <div class="bar-gold"></div>
  
  <div class="main-wrapper">
    <div class="header-content">
      <div class="logo-box">
        <img src="{logo_uri}" style="height:70px; width:auto;">
      </div>
      <div class="contact-box">
        {contact_html}
      </div>
      <div class="clear"></div>
    </div>
    <div class="divider"></div>
    <div class="body">{body_html}</div>
  </div>
  
  <div class="footer">
    <div class="footer-bars"><div class="fb"></div><div class="fg"></div></div>
  </div>
</body></html>"""

        pdf_bytes = WeasyprintHTML(string=pdf_full_html, base_url=APP_BASE_URL).write_pdf()

        await send_personnel_executed_email(
            signer_name=signer_name,
            signer_email=signer_email,
            doc_title=doc_title,
            matter_id=matter_id,
            pdf_bytes=pdf_bytes,
            audit_entries=audit_entries,
            download_token=signing_token
        )
    except Exception as email_err:
        import logging
        logging.getLogger(__name__).error(f"Execution email failed (non-fatal): {email_err}")

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
        
    # Fetch the matter record
    matter_res = await db_execute(lambda: db.table("legal_matters").select("*").eq("id", matter_id).execute())
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Matter not found")
    matter = matter_res.data[0]
    
    # ── Resolve Recipient for Confirmation Email ──
    signer_name = signing_req.get("signer_name")
    signer_email = signing_req.get("signer_email")
    
    if not signer_email:
        # Lookup from matter since it wasn't populated during dispatch
        staff_id = matter.get("staff_id")
        if staff_id:
            staff_res = await db_execute(lambda: db.table("admins").select("full_name, email").eq("id", staff_id).execute())
            if staff_res.data:
                signer_name = staff_res.data[0].get("full_name")
                signer_email = staff_res.data[0].get("email")
        
        if not signer_email:
            signer_name = matter.get("external_party_name")
            signer_email = matter.get("external_party_email")

    # Update signing request with the resolved details for the audit record
    await db_execute(
        lambda: db.table("legal_signing_requests").update({
            "status": "Acknowledged",
            "acknowledged_at": datetime.now(timezone(timedelta(hours=1))).isoformat(),
            "signer_name": signer_name,
            "signer_email": signer_email,
            "signature_metadata": {
                "type": "acknowledgment",
                "timestamp": data.get("timestamp"),
                "user_agent": data.get("user_agent", "")
            }
        }).eq("id", signing_req["id"]).execute()
    )

    # ── Update matter status to Executed ──
    branding = await get_branding_urls()
    logo_url = branding.get("firm_logo")
    stamp_url = branding.get("stamp_url")
    lagos_tz = timezone(timedelta(hours=1))
    signed_date_str = datetime.now(lagos_tz).strftime("%d %B %Y, %H:%M")
    
    seal_html = f"""<div class="legal-badge seal-badge" style="display:inline-flex;flex-direction:column;align-items:center;border:3px solid #C47D0A;border-radius:50%;width:110px;height:110px;justify-content:center;padding:8px;text-align:center;box-shadow:0 0 0 2px #C47D0A inset;line-height:1.1;background:rgba(196,125,10,0.05);color:#C47D0A;vertical-align:middle;margin:10px;"><img src="{logo_url}" style="height:40px;width:auto;margin-bottom:2px;opacity:0.9;"><span style="font-size:6.5pt;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;">OFFICIAL<br>CORPORATE SEAL</span></div>"""
    
    if stamp_url:
        stamp_html = f"""<div class="legal-badge stamp-badge" style="display:inline-block;border:2px solid #C47D0A;padding:10px 20px;text-align:center;transform:rotate(-3deg);opacity:0.9;background:rgba(196,125,10,0.05);color:#C47D0A;vertical-align:middle;margin:10px;"><img src="{stamp_url}" style="height:36px;width:auto;display:block;margin:0 auto 4px;"><div style="font-size:10pt;font-weight:900;letter-spacing:0.15em;text-transform:uppercase;">AUTHORIZED</div><div style="font-size:8pt;color:#888;">{signed_date_str}</div></div>"""
    else:
        stamp_html = f"""<div class="legal-badge stamp-badge" style="display:inline-block;border:2px solid #C47D0A;padding:10px 20px;text-align:center;transform:rotate(-3deg);opacity:0.9;background:rgba(196,125,10,0.05);color:#C47D0A;vertical-align:middle;margin:10px;"><div style="font-size:10pt;font-weight:900;letter-spacing:0.15em;text-transform:uppercase;">AUTHORIZED</div><div style="font-size:8pt;font-weight:700;color:#333;text-transform:uppercase;">Eximp &amp; Cloves Infrastructure Ltd.</div><div style="font-size:8pt;color:#888;">{signed_date_str}</div></div>"""

    raw_html = matter.get("content_html") or ""
    patched_html = raw_html.replace("{{ seal }}", seal_html).replace("{{ stamp }}", stamp_html)

    update_data = {
        "status": "Executed",
        "signed_at": datetime.now().isoformat(),
        "executed_at": datetime.now().isoformat(),
        "signed_by": "acknowledged",
        "content_html": patched_html,
        "staff_visible": True,
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
        "description": f"Contract acknowledged by {signer_name or 'staff member'} ({signer_email or 'unknown email'})"
    }).execute())
    
    # ── Fire post-acknowledgment confirmation email (non-blocking) ──
    if signer_email:
        await _send_matter_executed_email(
            matter_id=matter_id,
            signing_token=signing_token,
            signer_name=signer_name or "Staff Member",
            signer_email=signer_email
        )

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
    await check_matter_access(matter_id, current_admin)
    
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
        lambda: db.table("admins").select("id, full_name, position_title, department").eq("id", staff_id).execute()
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


@router.post("/matters/{matter_id}/duplicate")
async def duplicate_matter(matter_id: str, current_admin=Depends(verify_token)):
    """
    Creates a new matter by copying content from an existing one.
    Resets status to 'Draft' and clears signatures.
    """
    db = get_db()
    
    # Fetch source
    source_res = await db_execute(lambda: db.table("legal_matters").select("*").eq("id", matter_id).execute())
    if not source_res.data:
        raise HTTPException(status_code=404, detail="Source matter not found")
        
    source = source_res.data[0]
    
    # Build new matter (resetting execution fields)
    new_matter = {
        "title": f"Copy of {source.get('title', 'Untitled')}",
        "category": source.get("category"),
        "staff_id": source.get("staff_id"),
        "content_html": source.get("content_html"),
        "content_css": source.get("content_css"),
        "meta_data": source.get("meta_data") or {},
        "status": "Draft",
        "staff_visible": False,
        "executed_at": None,
        "signed_at": None,
        "signed_by": None,
        "signature_metadata": None,
        "drafter_id": current_admin["sub"]
    }
    
    # Insert
    res = await db_execute(lambda: db.table("legal_matters").insert(new_matter).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to duplicate matter")
        
    new_id = res.data[0]["id"]
    
    # Log history
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": new_id,
        "action": "Matter Created",
        "performed_by": current_admin["sub"],
        "description": f"Duplicated from matter {matter_id[:8]}"
    }).execute())
    
    return {"status": "success", "new_id": new_id}

@router.post("/matters/{matter_id}/preview-link")
async def generate_preview_link(matter_id: str, current_admin=Depends(verify_token)):
    """Generates a 48-hour valid JWT token for sharing a read-only preview."""
    import jwt as _jwt
    from routers.auth import SECRET_KEY, ALGORITHM
    from datetime import timedelta
    
    payload = {
        "sub": "preview",
        "matter_id": str(matter_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=48)
    }
    preview_token = _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Log the action
    db = get_db()
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Preview Link Generated",
        "performed_by": current_admin.get("sub"),
        "description": "Generated a 48-hour secure preview link."
    }).execute())
    
    return {"preview_token": preview_token, "preview_url": f"/preview/{preview_token}"}


@router.get("/preview/{token}")
async def get_preview_data(token: str):
    """Decodes the preview token and returns the matter payload if valid."""
    import jwt as _jwt
    from routers.auth import SECRET_KEY, ALGORITHM
    db = get_db()
    
    try:
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        matter_id = payload.get("matter_id")
        if not matter_id:
            raise HTTPException(status_code=400, detail="Invalid token payload")
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Preview link has expired. Please request a new one.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupt preview link.")
        
    matter_res = await db_execute(
        lambda: db.table("legal_matters").select("*, legal_matter_signatories(*)").eq("id", matter_id).execute()
    )
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Document cannot be found.")
        
    matter = matter_res.data[0]
    
    # Audit trail (Guest View)
    await db_execute(lambda: db.table("legal_matter_history").insert({
        "matter_id": matter_id,
        "action": "Preview Link Accessed",
        "performed_by": None,
        "description": "Guest accessed document via 48H Preview Link."
    }).execute())
    
    return matter


@router.get("/matters/{matter_id}/export")
async def export_matter_pdf(matter_id: str, token: str = None, request: Request = None):
    """
    Generate a full-page PDF of a legal matter.
    Accepts:
      1. Authorization: Bearer <JWT>  — normal staff/admin access
      2. ?token=<JWT>                 — JWT passed as query param (dashboard use)
      3. ?token=<signing_token>       — raw UUID signing token (external signer download)
    """
    db = get_db()
    matter_query = db.table("legal_matters").select("id, title, content_html, content_css, staff_id")

    # ── Strategy 1: JWT via header or query param ──
    current_admin = None
    try:
        from routers.auth import resolve_admin_token
        from fastapi.security import HTTPAuthorizationCredentials
        authorization = request.headers.get("authorization", "") if request else ""
        if authorization:
            scheme, creds = authorization.split()
            if scheme.lower() == "bearer":
                from routers.auth import verify_token
                current_admin = verify_token(HTTPAuthorizationCredentials(scheme=scheme, credentials=creds))
        if not current_admin and token:
            import jwt as _jwt
            import os as _os
            SECRET_KEY = _os.getenv("JWT_SECRET", "eximp-cloves-secret-key-change-in-production")
            try:
                current_admin = _jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            except Exception:
                pass  # Not a JWT — might be a signing token, handled below
    except Exception:
        pass

    if current_admin:
        admin_id = current_admin.get("sub")
        roles = current_admin.get("role", "").lower().split(",")
        is_privileged = any(r.strip() in ["hr", "lawyer", "legal", "admin", "super_admin"] for r in roles)
        query = matter_query.eq("id", matter_id)
        if not is_privileged:
            query = query.eq("staff_id", admin_id).eq("staff_visible", True)
        res = await db_execute(lambda: query.execute())
        if not res.data:
            raise HTTPException(status_code=403, detail="You do not have permission to access this document")

    # ── Strategy 2: Raw signing token (UUID) from external signer ──
    elif token:
        signing_res = await db_execute(
            lambda: db.table("legal_signing_requests")
            .select("matter_id, status")
            .eq("signing_token", token)
            .execute()
        )
        if not signing_res.data or signing_res.data[0].get("matter_id") != matter_id:
            raise HTTPException(status_code=403, detail="Invalid or expired download token")
        res = await db_execute(lambda: matter_query.eq("id", matter_id).execute())
        if not res.data:
            raise HTTPException(status_code=404, detail="Document not found")

    else:
        raise HTTPException(status_code=401, detail="Authentication required")

    matter = res.data[0]
    title = matter.get("title", "Legal Document")
    body_html = matter.get("content_html", "<p>No content.</p>") or "<p>No content.</p>"
    contact_html = matter.get("content_css")
    if not contact_html or contact_html.strip() == "":
        contact_html = """<div>phone: +234 912 6864 383</div>
        <div>web: <a href="https://eximps-cloves.com" class="text-brand-gold">https://eximps-cloves.com</a></div>
        <div>email: <a href="mailto:admin@eximps-cloves.com" class="text-brand-gold">admin@eximps-cloves.com</a></div>"""

    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "static", "img", "logo_firm.png")
    logo_uri = "file:///" + logo_path.replace("\\", "/")
    
    # Ensure weasyprint can resolve the signature block logos without failing due to CORS or local SSL limits
    body_html = body_html.replace(f"{APP_BASE_URL}/static/img/logo_firm.png", logo_uri)

    # ── Handle branding placeholders (for Preview/Draft PDFs) ──
    # If the document hasn't been executed yet, we show the "Elite" placeholders in the PDF export too.
    if "{{ seal }}" in body_html or "{{ stamp }}" in body_html:
        branding = await get_branding_urls()
        logo_url = logo_uri # Safe local URI for WeasyPrint
        stamp_url = branding.get("stamp_url")
        
        # Seal is dynamic CSS (Elite badge)
        seal_html = f"""<div style="display:inline-flex;flex-direction:column;align-items:center;border:3px solid #C47D0A;border-radius:50%;width:110px;height:110px;justify-content:center;padding:8px;text-align:center;box-shadow:0 0 0 2px #C47D0A inset;line-height:1.1;color:#C47D0A;background:rgba(196,125,10,0.02);vertical-align:middle;margin:10px;"><img src="{logo_url}" style="height:40px;width:auto;margin-bottom:2px;opacity:0.8;"><div style="font-size:6.5pt;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;">OFFICIAL SEAL<br>DRAFT</div></div>"""
        
        if stamp_url:
            stamp_html = f"""<div style="display:inline-block;border:2px solid #C47D0A;padding:10px 20px;text-align:center;transform:rotate(-3deg);color:#C47D0A;background:rgba(196,125,10,0.02);vertical-align:middle;margin:10px;"><img src="{stamp_url}" style="height:36px;width:auto;display:block;margin:0 auto 4px;opacity:0.8;"><div style="font-size:10pt;font-weight:900;letter-spacing:0.15em;text-transform:uppercase;">AUTHORIZED</div></div>"""
        else:
            stamp_html = f"""<div style="display:inline-block;border:2px solid #C47D0A;padding:10px 20px;text-align:center;transform:rotate(-3deg);color:#C47D0A;background:rgba(196,125,10,0.02);vertical-align:middle;margin:10px;"><div style="font-size:10pt;font-weight:900;letter-spacing:0.15em;text-transform:uppercase;">AUTHORIZED</div><div style="font-size:8pt;font-weight:700;color:#333;text-transform:uppercase;">Eximp &amp; Cloves Infrastructure Ltd.</div></div>"""
            
        body_html = body_html.replace("{{ seal }}", seal_html).replace("{{ stamp }}", stamp_html)

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
    padding: 0;
    overflow: hidden;
  }}

  /* ── LETTERHEAD ── */
  @page {{ size: A4; margin: 0; }}
  body {{ font-family: 'Tinos', 'Times New Roman', serif; font-size: 11pt; color: #000; background: white; margin: 0; padding: 0; }}
  
  .bar-black {{ position: absolute; top: 0; left: 0; width: 60%; height: 40px; background: #000; border-bottom-right-radius: 40px; z-index: 100; }}
  .bar-gold {{ position: absolute; top: 0; right: 0; width: 70%; height: 30px; background: #C47D0A; z-index: 90; }}
  
  .main-wrapper {{ position: relative; z-index: 200; width: 100%; }}
  .header-content {{ padding: 50px 60px 10px; width: 100%; box-sizing: border-box; }}
  .logo-box {{ float: left; width: 50%; }}
  .contact-box {{ float: right; width: 45%; border-left: 2px solid #000; padding: 4px 15px; font-size: 9pt; line-height: 1.4; color: #111; font-weight: 700; font-variant-caps: all-small-caps; letter-spacing: 0.05em; font-family: 'Inter', sans-serif; }}
  .contact-box a {{ color: #C47D0A; text-decoration: none; }}
  
  .clear {{ clear: both; height: 1px; }}
  .divider {{ height: 2px; background: #eee; margin: 10px 60px 0; }}
  
  .body-content {{ padding: 30px 72px; line-height: 1.6; text-align: justify; }}
  .body-content p {{ margin-bottom: 12pt; min-height: 1.2em; }}
  .body-content ol, .body-content ul {{ padding: 0 0 0 40px; margin: 12pt 0; list-style-position: outside; }}
  .body-content li {{ margin-bottom: 8pt; padding-left: 5px; }}
  /* Automatic Parent-Child Nesting */
  .body-content ol {{ list-style-type: decimal; }}
  .body-content ol ol {{ list-style-type: lower-alpha; margin: 6pt 0; }}
  .body-content ol ol ol {{ list-style-type: lower-roman; margin: 4pt 0; }}
  .body-content ul {{ list-style-type: disc; }}
  .body-content ul ul {{ list-style-type: circle; }}
  /* Force specific types if overridden by user */
  .body-content ol[type="a"] {{ list-style-type: lower-alpha !important; }}
  .body-content ol[type="A"] {{ list-style-type: upper-alpha !important; }}
  .body-content ol[type="i"] {{ list-style-type: lower-roman !important; }}
  .body-content ol[type="I"] {{ list-style-type: upper-roman !important; }}
  .body-content img {{ max-width: 100%; height: auto; display: block; }}
  
  .footer {{ position: absolute; bottom: 0; left: 0; width: 100%; }}
  .footer-bars {{ display: flex; height: 12px; }}
  .fb {{ flex: 1; background: #000; }}
  .fg {{ flex: 1; background: #C47D0A; }}
</style>
</head>
<body>
  <div class="bar-black"></div>
  <div class="bar-gold"></div>
  
  <div class="main-wrapper">
    <div class="header-content">
      <div class="logo-box">
        <img src="{logo_uri}" style="height:70px; width:auto;">
      </div>
      <div class="contact-box">
        {contact_html}
      </div>
      <div class="clear"></div>
    </div>
    <div class="divider"></div>
    <div class="body-content">{body_html}</div>
  </div>
  
  <div class="footer">
    <div class="footer-bars"><div class="fb"></div><div class="fg"></div></div>
  </div>
</body></html>"""

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
