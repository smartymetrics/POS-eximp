from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File
from database import get_db, db_execute
from routers.auth import verify_token
from datetime import datetime
import json
import uuid

router = APIRouter()

# ── HELPER: PERMISSION CHECK ──
async def check_matter_access(matter_id: str, admin_id: str, required_level: str = "View"):
    """
    Verifies if an admin has access to a legal matter.
    Levels: 'View', 'Edit', 'Full' (Drafter has 'Full')
    """
    db = get_db()
    
    # 1. Is the admin the drafter or a super-admin?
    matter_res = await db_execute(lambda: db.table("legal_matters").select("drafter_id").eq("id", matter_id).execute())
    if not matter_res.data:
        raise HTTPException(status_code=404, detail="Legal matter not found")
    
    matter = matter_res.data[0]
    
    # Check if admin is the drafter
    if str(matter.get("drafter_id")) == str(admin_id):
        return "Full"
        
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
    """Convenience endpoint for HR portal to fetch matters for a specific employee."""
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
    await check_matter_access(matter_id, admin_id)
    
    db = get_db()
    matter_res = await db_execute(lambda: db.table("legal_matters").select("*").eq("id", matter_id).execute())
    collabs_res = await db_execute(lambda: db.table("legal_matter_collaborators").select("*, public_admins(full_name)").eq("matter_id", matter_id).execute())
    history_res = await db_execute(lambda: db.table("legal_matter_history").select("*").eq("matter_id", matter_id).order("created_at", desc=True).execute())
    
    return {
        "matter": matter_res.data[0],
        "collaborators": collabs_res.data or [],
        "history": history_res.data or []
    }

@router.patch("/matters/{matter_id}/save")
async def save_matter_content(matter_id: str, data: dict, current_admin=Depends(verify_token)):
    """Save GrapesJS HTML and CSS."""
    admin_id = current_admin["sub"]
    await check_matter_access(matter_id, admin_id, required_level="Edit")
    
    db = get_db()
    update_data = {
        "content_html": data.get("html"),
        "content_css": data.get("css"),
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
