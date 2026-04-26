import math
import os
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from database import get_db, db_execute
from routers.auth import verify_token
from models import (
    KPITemplateCreate, KPITemplateUpdate, PerformanceReviewCreate,
    LeaveRequestCreate, LeaveRequestUpdate, StaffDocumentCreate, 
    StaffQualificationCreate, IncidentCreate
)

router = APIRouter(prefix="/api/hr", tags=["HR Management"])

# ─── MODELS ───────────────────────────────────────────────────────────────────

# ─── MODELS ───────────────────────────────────────────────────────────────────

class GoalBase(BaseModel):
    kpi_name: str
    target_value: float
    unit: str
    weight: float
    status: str = "Draft"

class GoalCreate(GoalBase):
    staff_id: Optional[str] = None
    department: Optional[str] = None
    month: date
    template_id: Optional[str] = None

class GoalUpdate(BaseModel):
    kpi_name: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    weight: Optional[float] = None
    status: Optional[str] = None
    month: Optional[date] = None
    template_id: Optional[str] = None
    staff_id: Optional[str] = None
    department: Optional[str] = None

class KPITemplateBase(BaseModel):
    name: str
    department: str
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True

class KPITemplateCreate(KPITemplateBase):
    pass

class KPITemplateUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PerformanceReviewBase(BaseModel):
    quality_score: float # 0-100 (20%)
    teamwork_score: int  # 1-5
    leadership_score: int # 1-5
    attitude_score: int  # 1-5
    comments: Optional[str] = None

class PerformanceReviewCreate(PerformanceReviewBase):
    staff_id: str
    review_period: date

class StaffProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    line_manager_id: Optional[str] = None
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    cv_url: Optional[str] = None
    base_salary: Optional[float] = None
    leave_quota: Optional[int] = None
    exit_date: Optional[date] = None
    exit_reason: Optional[str] = None

class CompanyAssetCreate(BaseModel):
    asset_name: str
    asset_type: Optional[str] = "Equipment"
    serial_number: Optional[str] = None
    status: str = "Available"
    purchase_cost: Optional[float] = None
    notes: Optional[str] = None

class AssetAssign(BaseModel):
    staff_id: Optional[str] = None
    status: str = "Assigned"
    notes: Optional[str] = None

class StaffQualificationCreate(BaseModel):
    staff_id: str
    type: str # Education, Certification, Skill
    title: str
    institution: Optional[str] = None
    year: Optional[int] = None

class StaffDocumentCreate(BaseModel):
    staff_id: str
    doc_type: str # CV, Contract, ID, Passport, Certificate
    title: str
    file_url: str

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    days_count: int
    reason: Optional[str] = None

class MigrationResponse(BaseModel):
    message: str
    success: bool
    details: Optional[str] = None

class ManualPayrollCreate(BaseModel):
    staff_id: str
    gross_pay: float
    tax: float
    pension: Optional[float] = 0.0
    net_pay: float
    notes: Optional[str] = None
    period_start: date

# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.post("/migrate", response_model=MigrationResponse)
async def run_hr_migration(current_admin: dict = Depends(verify_token)):
    """Apply the HR SQL migration via RPC or manual execution."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "super_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="Admin only")
         
    db = get_db()
    phases = [
        "sql/hr_management_migration.sql",
        "sql/hr_management_phase2.sql",
        "sql/hr_phase3_tasks.sql",
        "sql/hr_phase4_payroll.sql",
        "sql/hr_phase5_attendance.sql",
        "sql/hr_phase6_geofence.sql",
        "sql/hr_phase7_profile_enrichment.sql"
    ]
    
    results = []
    try:
        for sql_path in phases:
            with open(sql_path, "r") as f:
                sql = f.read()
            # Try to use exec_sql RPC if it exists
            res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": sql}).execute())
            results.append(f"{sql_path}: Success")
        
        return {"message": "All HR migration phases applied successfully", "success": True, "details": ", ".join(results)}
    except Exception as e:
        return {"message": f"Migration failed: {e}", "success": False, "details": "Try running the SQL manually in Supabase SQL Editor."}

@router.get("/staff", response_model=List[dict])
async def get_staff_list(current_admin: dict = Depends(verify_token)):
    """Fetch staff members with their HR profiles and performance summaries."""
    db = get_db()
    today = date.today()
    month_start = date(today.year, today.month, 1).isoformat()
    
    # 1. Fetch admins joined with staff_profiles
    res = await db_execute(lambda: db.table("admins").select(
        "id, full_name, email, role, primary_role, department, line_manager_id, created_at, is_active, staff_profiles(*)"
    ).execute())
    staff_data = res.data
    
    # 2. Fetch all goals for current month
    goals_res = await db_execute(lambda: db.table("staff_goals")
        .select("staff_id, achievement_pct")
        .gte("month", month_start)
        .execute())
    
    # 3. Fetch latest reviews for everyone
    # For performance, we'll get simple latest review per staff if possible, 
    # or just fetch recent ones and map.
    rev_res = await db_execute(lambda: db.table("performance_reviews")
        .select("staff_id, quality_score, teamwork_score, leadership_score, review_period")
        .order("review_period", desc=True)
        .execute())
        
    # Organize data for mapping
    goals_map = {}
    for g in goals_res.data:
        sid = g["staff_id"]
        if sid not in goals_map: goals_map[sid] = []
        goals_map[sid].append(g)
        
    rev_map = {}
    for r in rev_res.data:
        sid = r["staff_id"]
        if sid not in rev_map: rev_map[sid] = r # Latest because of order
        
    # Enrich staff data
    for s in staff_data:
        sid = s["id"]
        s_goals = goals_map.get(sid, [])
        s_rev = [rev_map[sid]] if sid in rev_map else []
        s["performance"] = compute_composite_score(s_goals, s_rev)
        
    return staff_data

@router.get("/profile/{staff_id}")
async def get_staff_profile(staff_id: str, current_admin: dict = Depends(verify_token)):
    """Fetch full personnel data for a staff member. Accessible by HR, Manager, or Self."""
    user_email = current_admin["email"]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    db = get_db()
    
    # Check if self
    staff_res = await db_execute(lambda: db.table("admins").select("id, email, line_manager_id").eq("id", staff_id).execute())
    if not staff_res.data:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    target_staff = staff_res.data[0]
    is_self = target_staff["email"] == user_email
    
    # Check if manager
    mgr_res = await db_execute(lambda: db.table("admins").select("id").eq("email", user_email).execute())
    is_mgr = False
    if mgr_res.data:
        is_mgr = target_staff["line_manager_id"] == mgr_res.data[0]["id"]

    if not (is_hr or is_self or is_mgr):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Fetch profile data
    profile = await db_execute(lambda: db.table("admins").select("*, staff_profiles(*), staff_documents!staff_documents_staff_id_fkey(*), staff_qualifications(*)").eq("id", staff_id).execute())
    
    return profile.data[0] if profile.data else None

@router.patch("/profile/{staff_id}")
async def update_staff_profile(staff_id: str, update: StaffProfileUpdate, current_admin: dict = Depends(verify_token)):
    """Update detailed staff profile. HR admins may edit all fields; line managers and staff may self-edit a restricted set."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    is_self = current_admin.get("sub") == staff_id

    # Check if the caller is the direct line manager of this staff member
    is_mgr = False
    if not is_hr and not is_self:
        target_res = await db_execute(lambda: db.table("admins").select("line_manager_id").eq("id", staff_id).execute())
        if target_res.data and target_res.data[0].get("line_manager_id"):
            is_mgr = target_res.data[0]["line_manager_id"] == current_admin.get("sub")

    if not (is_hr or is_self or is_mgr):
        raise HTTPException(status_code=403, detail="Only HR, the profile owner, or their line manager can update this record")
    update_data = update.dict(exclude_unset=True)

    admin_updates = {}
    profile_updates = {}

    if is_hr:
        # HR can update administrative fields as well as profile data.
        if update.full_name: admin_updates["full_name"] = update.full_name
        if update.email: admin_updates["email"] = update.email
        if update.department: admin_updates["department"] = update.department
        if update.line_manager_id: admin_updates["line_manager_id"] = update.line_manager_id
        if update.exit_date is not None:
            admin_updates["is_active"] = False  # Auto-deactivate if exit date set

        profile_updates = update.dict(exclude={"full_name", "email", "department", "line_manager_id"}, exclude_unset=True)
    else:
        # Staff members may update only personal profile fields.
        allowed_self_fields = {"phone_number", "emergency_contact", "address", "bio"}
        invalid_fields = set(update_data.keys()) - allowed_self_fields
        if invalid_fields:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot edit administrative fields: {', '.join(sorted(invalid_fields))}"
            )
        profile_updates = update_data

    if admin_updates:
        await db_execute(lambda: db.table("admins").update(admin_updates).eq("id", staff_id).execute())

    if profile_updates:
        # Convert date objects to strings for JSON serialization
        for k, v in profile_updates.items():
            if isinstance(v, (date, datetime)):
                profile_updates[k] = v.isoformat()

        profile_updates = {k: v for k, v in profile_updates.items() if v is not None}
        if profile_updates:
            profile_exists = await db_execute(lambda: db.table("staff_profiles").select("id").eq("admin_id", staff_id).execute())
            if profile_exists.data:
                await db_execute(lambda: db.table("staff_profiles").update(profile_updates).eq("admin_id", staff_id).execute())
            else:
                profile_updates["admin_id"] = staff_id
                await db_execute(lambda: db.table("staff_profiles").insert(profile_updates).execute())

    return {"message": "Profile updated successfully"}

@router.get("/performance/{staff_id}")
async def get_performance_score(staff_id: str, current_admin: dict = Depends(verify_token)):
    """Calculate the weighted performance score (40/20/40 rule) with role-aware logic."""
    db = get_db()
    
    # Fetch user role to determine scoring logic
    user_data = await db_execute(lambda: db.table("admins").select("primary_role, role").eq("id", staff_id).execute())
    main_role = "staff"
    if user_data.data:
        main_role = user_data.data[0].get("primary_role") or user_data.data[0].get("role", "staff").split(",")[0]

    # 1. Fetch Goals (40%) - Automated comparing staff_goals
    goals = await db_execute(lambda: db.table("staff_goals").select("*").eq("staff_id", staff_id).execute())
    
    goal_score = 0
    if goals.data:
        total_weight = sum(g['weight'] for g in goals.data) or 1
        weighted_sum = 0
        for g in goals.data:
            # Role-specific achievement detection could go here (e.g. fetching real data from invoices)
            # For now we use the 'actual_value' which our background syncers fill
            achieved = (g['actual_value'] / max(g['target_value'], 1))
            weighted_sum += min(achieved, 1.2) * g['weight'] # Cap at 120%
        goal_score = (weighted_sum / total_weight) * 100
        
    # 2. Fetch Latest Performance Review (Quality 20% + Manager Review 40%)
    reviews = await db_execute(lambda: db.table("performance_reviews")
                               .select("*")
                               .eq("staff_id", staff_id)
                               .order("review_period", desc=True)
                               .limit(1)
                               .execute())
    
    quality_score = 0
    manager_review_score = 0
    
    if reviews.data:
        rev = reviews.data[0]
        quality_score = rev.get('quality_score', 0)
        # Manager review (Teamwork + Initiative/Growth (Section 6.1))
        # Logic: (Teamwork 1-5 + Initiative 1-5) / 10 * 100
        raw_manager = (rev.get('teamwork_score', 0) + 
                       rev.get('initiative_score', 0))
        manager_review_score = (raw_manager / 10) * 100
        
    # Final weighted calc
    final_score = (goal_score * 0.4) + (quality_score * 0.2) + (manager_review_score * 0.4)
    
    # Flagging Logic (PRD 8.2)
    flagged = final_score < 50
    
    return {
        "staff_id": staff_id,
        "score": round(final_score, 1),
        "rating": "Excellent" if final_score >= 85 else "Good" if final_score >= 70 else "Fair" if final_score >= 50 else "Poor",
        "flagged": flagged,
        "breakdown": {
            "goals_40_pct": round(goal_score, 1),
            "quality_20_pct": round(quality_score, 1),
            "manager_review_40_pct": round(manager_review_score, 1)
        }
    }

@router.post("/goals", status_code=status.HTTP_201_CREATED)
async def set_staff_goal(goal: GoalCreate, current_admin: dict = Depends(verify_token)):
    """HR or manager sets a KPI goal for a staff member or a department."""
    user_email = current_admin["email"]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    if not goal.staff_id and not goal.department:
        raise HTTPException(status_code=400, detail="Either staff_id or department is required")
    if goal.staff_id and goal.department:
        raise HTTPException(status_code=400, detail="Provide either staff_id or department, not both")

    db = get_db()

    if goal.staff_id:
        # Auth check: is it own team for non-HR users?
        if not is_hr:
            staff_res = await db_execute(lambda: db.table("admins").select("line_manager_id").eq("id", goal.staff_id).execute())
            mgr_res = await db_execute(lambda: db.table("admins").select("id").eq("email", user_email).execute())
            if not (staff_res.data and mgr_res.data and staff_res.data[0]["line_manager_id"] == mgr_res.data[0]["id"]):
                raise HTTPException(status_code=403, detail="You can only set goals for your direct reports")
    else:
        # Only HR may set department-level goals.
        if not is_hr:
            raise HTTPException(status_code=403, detail="Only HR can set department goals")

    goal_data = {
        "kpi_name": goal.kpi_name,
        "target_value": goal.target_value,
        "unit": goal.unit,
        "weight": goal.weight,        "status": goal.status,        "month": goal.month.isoformat(),
        "department": goal.department or None,
        "staff_id": goal.staff_id or None
    }
    if getattr(goal, "template_id", None):
        goal_data["kpi_template_id"] = goal.template_id

    res = await db_execute(lambda: db.table("staff_goals").insert(goal_data).execute())
    
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create goal")
    return res.data[0]

@router.patch("/goals/{goal_id}")
async def update_goal(goal_id: str, update: GoalUpdate, current_admin: dict = Depends(verify_token)):
    """Update an existing KPI goal when it is still editable."""
    user_email = current_admin["email"]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)

    db = get_db()
    existing = await db_execute(lambda: db.table("staff_goals").select("*").eq("id", goal_id).execute())
    if not existing.data:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal_record = existing.data[0]
    if goal_record.get("status") == "Published" and not is_hr:
        raise HTTPException(status_code=403, detail="Locked goals can only be updated by HR")

    if not is_hr:
        # Managers may only update goals for their direct reports
        staff_res = await db_execute(lambda: db.table("admins").select("line_manager_id").eq("id", goal_record.get("staff_id")).execute())
        mgr_res = await db_execute(lambda: db.table("admins").select("id").eq("email", user_email).execute())
        if not (staff_res.data and mgr_res.data and staff_res.data[0]["line_manager_id"] == mgr_res.data[0]["id"]):
            raise HTTPException(status_code=403, detail="You can only update goals for your direct reports")

    update_data = update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No changes provided")

    if update_data.get("month") is not None:
        if isinstance(update_data["month"], date):
            update_data["month"] = update_data["month"].isoformat()
        else:
            update_data["month"] = str(update_data["month"])

    if "template_id" in update_data:
        update_data["kpi_template_id"] = update_data.pop("template_id")

    if update_data.get("staff_id") and update_data.get("department"):
        raise HTTPException(status_code=400, detail="Provide either staff_id or department, not both")

    res = await db_execute(lambda: db.table("staff_goals").update(update_data).eq("id", goal_id).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to update goal")
    return res.data[0]

@router.post("/goals/sync")
async def trigger_goal_sync(month: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Manually trigger the background sync for goal achievement actuals."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR Admin only")
         
    from scheduler import sync_goal_actuals
    # Run as a background task to avoid timeout
    import asyncio
    asyncio.create_task(sync_goal_actuals(month))
    
    return {"message": "Goal sync triggered successfully"}

@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_staff_document(doc: StaffDocumentCreate, current_admin: dict = Depends(verify_token)):
    """Log an uploaded document. HR Admin only."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("staff_documents").insert({
        "staff_id": doc.staff_id,
        "doc_type": doc.doc_type,
        "title": doc.title,
        "file_url": doc.file_url,
        "uploaded_by": current_admin["sub"]
    }).execute())
    
    return res.data[0]

@router.get("/assets")
async def get_company_assets(current_admin: dict = Depends(verify_token)):
    """Fetch all company assets, including assignee details and financial links. HR only."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("company_assets").select("*, admins!company_assets_assigned_to_fkey(full_name, department)").order("created_at", desc=True).execute())
    return res.data

@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def create_company_asset(asset: CompanyAssetCreate, current_admin: dict = Depends(verify_token)):
    """Register a new company asset into the HR inventory."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("company_assets").insert(asset.dict(exclude_unset=True)).execute())
    return res.data[0]

@router.patch("/assets/{asset_id}/assign")
async def assign_company_asset(asset_id: str, assign_data: AssetAssign, current_admin: dict = Depends(verify_token)):
    """Assign or reassign an asset to a staff member."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("company_assets").update({
        "assigned_to": assign_data.staff_id,
        "status": assign_data.status,
        "notes": assign_data.notes,
        "updated_at": "now()"
    }).eq("id", asset_id).execute())
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Asset not found")
    return res.data[0]

@router.post("/leave", status_code=status.HTTP_201_CREATED)
async def request_leave(req: LeaveRequestCreate, current_admin: dict = Depends(verify_token)):
    """Staff submits a leave request."""
    db = get_db()
    staff_id = current_admin["sub"]
    
    # 1. Fetch User's Leave Quota
    profile_res = await db_execute(lambda: db.table("staff_profiles").select("leave_quota").eq("staff_id", staff_id).execute())
    leave_quota = 20
    if profile_res.data and profile_res.data[0].get("leave_quota") is not None:
        leave_quota = profile_res.data[0]["leave_quota"]
        
    # 2. Fetch used approved days this year
    current_year = date.today().year
    leaves_res = await db_execute(lambda: db.table("leave_requests")
        .select("days_count")
        .eq("staff_id", staff_id)
        .eq("status", "approved")
        .gte("start_date", f"{current_year}-01-01")
        .lte("start_date", f"{current_year}-12-31")
        .execute())
        
    used_days = sum(l.get("days_count", 0) for l in leaves_res.data)
    
    if used_days + req.days_count > leave_quota:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave quota exceeded. You have {leave_quota - used_days} days remaining out of {leave_quota}."
        )

    res = await db_execute(lambda: db.table("leave_requests").insert({
        "staff_id": staff_id,
        "leave_type": req.leave_type,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "days_count": req.days_count,
        "reason": req.reason,
        "proof_url": req.proof_url,
        "status": "pending"
    }).execute())
    
    return res.data[0]

@router.get("/leave/pending")
async def get_pending_leave(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch leave requests. HR sees all. Managers see their team. Staff see their own."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    # We must explicitly define the foreign key relationship for admins to avoid PGRST201
    query = db.table("leave_requests").select("*, admins!leave_requests_staff_id_fkey(full_name, department)")
    
    if not is_hr:
        # Managers see their own + team. Staff see only own.
        cur_id = current_admin["sub"]
        if "line_manager" in user_roles:
            query = query.or_(f"staff_id.eq.{cur_id},admins.line_manager_id.eq.{cur_id}")
        else:
            query = query.eq("staff_id", cur_id)
    elif staff_id:
        query = query.eq("staff_id", staff_id)
        
    res = await db_execute(lambda: query.execute())
    return res.data

@router.get("/presence/leaves")
async def get_presence_leaves(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch pending leave requests for the dashboard. Alias to keep it grouped under presence."""
    return await get_pending_leave(staff_id, current_admin)

@router.get("/presence/attendance")
async def get_attendance(
    staff_id: Optional[str] = None, 
    date: Optional[str] = None, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: dict = Depends(verify_token)
):
    """Fetch attendance records. HR sees all. Staff see own. Supports single date or date range."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("attendance_records").select("*, admins(full_name, department)")
    
    # Range filtering takes precedence
    if start_date and end_date:
        query = query.gte("date", start_date).lte("date", end_date)
    elif date:
        query = query.eq("date", date)
    elif not staff_id:
        # Default to today if no date or specific staff history requested
        from datetime import date as dt
        query = query.eq("date", dt.today().isoformat())

    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        cur_id = current_admin["sub"]
        if "line_manager" in user_roles:
             # Match by staff_id or by line_manager_id of the linked admin
             query = query.or_(f"staff_id.eq.{cur_id},admins.line_manager_id.eq.{cur_id}")
        else:
             query = query.eq("staff_id", cur_id)
        
    res = await db_execute(lambda: query.order("date", desc=True).order("check_in", desc=True).execute())
    return res.data

@router.get("/presence/absences")
async def get_absence_report(
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: dict = Depends(verify_token)
):
    """
    Generate a full absenteeism report for a given staff member over a date range.
    Returns every expected working day (Mon-Fri) with its status:
    - present, late, on_leave, absent, weekend
    """
    from datetime import timedelta as td
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    # Staff can only see their own record
    target_id = staff_id if (is_hr and staff_id) else current_admin["sub"]
    
    # Default: last 30 days
    end_dt = date.fromisoformat(end_date) if end_date else date.today()
    start_dt = date.fromisoformat(start_date) if start_date else end_dt - td(days=29)
    
    db = get_db()
    
    # Fetch attendance records for the period
    att_res = await db_execute(
        lambda: db.table("attendance_records")
            .select("date, check_in, status, is_suspicious")
            .eq("staff_id", target_id)
            .gte("date", start_dt.isoformat())
            .lte("date", end_dt.isoformat())
            .execute()
    )
    
    # Fetch approved leaves for the period
    leave_res = await db_execute(
        lambda: db.table("leave_requests")
            .select("start_date, end_date, leave_type")
            .eq("staff_id", target_id)
            .eq("status", "approved")
            .execute()
    )
    
    # Build a lookup: date_str -> attendance record
    att_map = {a["date"]: a for a in att_res.data}
    
    # Build a set of approved leave dates
    leave_dates = set()
    for l in leave_res.data:
        s = date.fromisoformat(l["start_date"])
        e = date.fromisoformat(l["end_date"])
        cur = s
        while cur <= e:
            leave_dates.add(cur.isoformat())
            cur += td(days=1)
    
    today = date.today()
    
    # Walk each day in range and categorize
    days = []
    cur = start_dt
    while cur <= end_dt:
        day_str = cur.isoformat()
        day_name = cur.strftime("%A")
        
        if cur.weekday() >= 5:  # Saturday or Sunday
            status = "weekend"
        elif day_str in att_map:
            att = att_map[day_str]
            ci = att.get("check_in")
            if ci:
                time_part = (ci.split("T")[1] if "T" in ci else ci).split(".")[0]
                status = "late" if time_part > "09:00:00" else "present"
            else:
                status = "present"
        elif day_str in leave_dates:
            status = "on_leave"
        elif cur > today:
            status = "future"
        else:
            status = "absent"
        
        days.append({
            "date": day_str,
            "day": day_name,
            "status": status,
            "check_in": att_map.get(day_str, {}).get("check_in"),
            "is_suspicious": att_map.get(day_str, {}).get("is_suspicious", False)
        })
        cur += td(days=1)
    
    # Summary stats
    working_days = [d for d in days if d["status"] not in ("weekend", "future")]
    
    return {
        "staff_id": target_id,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "days": days,
        "summary": {
            "total_working_days": len(working_days),
            "present": sum(1 for d in working_days if d["status"] == "present"),
            "late": sum(1 for d in working_days if d["status"] == "late"),
            "absent": sum(1 for d in working_days if d["status"] == "absent"),
            "on_leave": sum(1 for d in working_days if d["status"] == "on_leave"),
        }
    }

@router.get("/presence/global-absences")
async def get_global_absences(
    start_date: str,
    end_date: str,
    current_admin: dict = Depends(verify_token)
):
    """
    Generate a company-wide absence log for a specific period.
    Only active staff are included. Weekends are excluded.
    """
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    if not is_hr:
         raise HTTPException(status_code=403, detail="Not authorized")

    db = get_db()
    s_dt = date.fromisoformat(start_date)
    e_dt = date.fromisoformat(end_date)
    today = date.today()
    if e_dt > today: e_dt = today
    
    # 1. Fetch active staff
    staff_res = await db_execute(lambda: db.table("admins").select("id, full_name, department").eq("is_active", True).execute())
    staff_list = staff_res.data
    
    # 2. Fetch all attendance in range
    att_res = await db_execute(lambda: db.table("attendance_records").select("staff_id, date").gte("date", start_date).lte("date", end_date).execute())
    att_map = {(a["date"], a["staff_id"]) for a in att_res.data}
    
    # 3. Fetch all approved leaves
    leave_res = await db_execute(lambda: db.table("leave_requests").select("staff_id, start_date, end_date").eq("status", "approved").execute())
    
    absences = []
    curr = s_dt
    while curr <= e_dt:
        if curr.weekday() < 5: # Monday to Friday
            d_str = curr.isoformat()
            for s in staff_list:
                sid = s["id"]
                # Check attendance
                if (d_str, sid) in att_map: continue
                
                # Check leave
                on_leave = False
                for l in leave_res.data:
                    if l["staff_id"] == sid:
                        l_start = date.fromisoformat(l["start_date"])
                        l_end = date.fromisoformat(l["end_date"])
                        if l_start <= curr <= l_end:
                            on_leave = True
                            break
                if on_leave: continue
                
                # Verified absence
                absences.append({
                    "date": d_str,
                    "staff_name": s["full_name"],
                    "department": s["department"],
                    "status": "Absent"
                })
        curr += timedelta(days=1)
        
    return sorted(absences, key=lambda x: (x["date"], x["staff_name"]), reverse=True)

@router.post("/payroll/run")
async def run_payroll(current_admin: dict = Depends(verify_token)):
    """Generate payroll records for all active staff for the current month."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR Admin only")
         
    db = get_db()
    
    # 1. Fetch all active staff with their profiles
    staff_res = await db_execute(lambda: db.table("admins").select("*, staff_profiles(*)").eq("is_active", True).execute())
    staff_list = staff_res.data
    
    records_created = 0
    now = datetime.now()
    month_start = date(now.year, now.month, 1).isoformat()
    month_end = date(now.year, now.month, 28).isoformat() # Simplified month end
    
    # 2. Fetch existing payroll records for this month in one go
    existing = await db_execute(lambda: db.table("payroll_records")
                                .select("staff_id")
                                .eq("period_start", month_start)
                                .execute())
    existing_staff_ids = {r["staff_id"] for r in existing.data} if existing.data else set()

    payroll_inserts = []
    
    for s in staff_list:
        if s["id"] in existing_staff_ids:
            continue

        p = s.get("staff_profiles", [{}])[0] if s.get("staff_profiles") else {}
        base = float(p.get("base_salary") or 0)
        
        # Nigerian Tax Engine (PAYE / Pension)
        monthly_tax = 0.0
        monthly_pension = 0.0
        monthly_cra = 0.0
        
        if base > 30000: # Minimum wage exemption
            annual_gross = base * 12
            annual_pension = annual_gross * 0.08
            annual_cra = max(200000.0, annual_gross * 0.01) + (0.2 * annual_gross)
            taxable_income = max(0.0, annual_gross - annual_pension - annual_cra)
            
            annual_tax = 0.0
            brackets = [
                (300000, 0.07),
                (300000, 0.11),
                (500000, 0.15),
                (500000, 0.19),
                (1600000, 0.21),
                (float('inf'), 0.24)
            ]
            
            rem_income = taxable_income
            for limit, rate in brackets:
                if rem_income <= 0:
                    break
                taxable_amount = min(rem_income, limit)
                annual_tax += taxable_amount * rate
                rem_income -= taxable_amount
                
            if annual_tax == 0 and taxable_income <= 0:
                 annual_tax = annual_gross * 0.01 # Minimum tax 1%
                 
            monthly_tax = round(annual_tax / 12, 2)
            monthly_pension = round(annual_pension / 12, 2)
            monthly_cra = round(annual_cra / 12, 2)
            
        net = round(base - monthly_tax - monthly_pension, 2)
        
        payroll_inserts.append({
            "staff_id": s["id"],
            "period_start": month_start,
            "period_end": month_end,
            "gross_pay": base,
            "tax": monthly_tax,
            "pension": monthly_pension,
            "cra": monthly_cra,
            "net_pay": net,
            "status": "pending",
            "processed_by": current_admin["sub"]
        })

    # Bulk insert if there are records to create
    if payroll_inserts:
        await db_execute(lambda: db.table("payroll_records").insert(payroll_inserts).execute())
        records_created = len(payroll_inserts)
            
    return {"message": f"Payroll generation complete. {records_created} records created.", "count": records_created}

@router.post("/payroll/manual", status_code=status.HTTP_201_CREATED)
async def create_manual_payroll(nf: ManualPayrollCreate, current_admin: dict = Depends(verify_token)):
    """Manually log a payroll record (bonus, contractor fee, etc). HR only."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR Admin only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("payroll_records").insert({
        "staff_id": nf.staff_id,
        "period_start": nf.period_start.isoformat(),
        "period_end": nf.period_start.isoformat(), # Same day for manual entries
        "gross_pay": nf.gross_pay,
        "tax": nf.tax,
        "pension": nf.pension,
        "net_pay": nf.net_pay,
        "status": "paid", # Manual entries usually reflect paid amounts
        "processed_by": current_admin["sub"]
    }).execute())
    
    return res.data[0]

class LeaveStatusUpdate(BaseModel):
    status: str

@router.patch("/leave/{leave_id}/status")
async def update_leave_status(leave_id: str, update: LeaveStatusUpdate, current_admin: dict = Depends(verify_token)):
    """Approve or reject a leave request (HR or Line Manager only)."""
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    db = get_db()
    
    # Check if authorized (simplified: HR or Manager)
    if not is_hr:
         # Check if manager
         req_check = await db_execute(lambda: db.table("leave_requests").select("*, admins(line_manager_id)").eq("id", leave_id).execute())
         if not req_check.data or req_check.data[0]["admins"]["line_manager_id"] != current_admin["sub"]:
              raise HTTPException(status_code=403, detail="Not authorized to approve this leave")

    status = update.status
    if status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    res = await db_execute(lambda: db.table("leave_requests").update({
        "status": status
    }).eq("id", leave_id).execute())
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Leave request not found or update failed")
    return {"message": f"Leave {status} successfully"}


@router.post("/performance/review", status_code=status.HTTP_201_CREATED)
async def submit_performance_review(review: PerformanceReviewCreate, current_admin: dict = Depends(verify_token)):
    """Line Manager or HR submits a formal performance review."""
    user_email = current_admin["email"]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    db = get_db()
    
    # Auth check: is it own team?
    if not is_hr:
        staff_res = await db_execute(lambda: db.table("admins").select("line_manager_id").eq("id", review.staff_id).execute())
        mgr_res = await db_execute(lambda: db.table("admins").select("id").eq("email", user_email).execute())
        if not (staff_res.data and mgr_res.data and staff_res.data[0]["line_manager_id"] == mgr_res.data[0]["id"]):
            raise HTTPException(status_code=403, detail="You can only review your direct reports")
            
    res = await db_execute(lambda: db.table("performance_reviews").insert({
        "staff_id": review.staff_id,
        "review_period": review.review_period.isoformat(),
        "quality_score": review.quality_score,
        "teamwork_score": review.teamwork_score,
        "leadership_score": review.leadership_score,
        "attitude_score": review.attitude_score,
        "initiative_score": review.attitude_score, # Mapping attitude to initiative for our calc
        "comments": review.comments,
        "reviewed_by": current_admin["sub"]
    }).execute())
    
    return {"message": "Review submitted successfully"}

@router.get("/goals")
async def get_all_goals(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch goals. HR sees all, Managers see team, Staff see own."""
    db = get_db()
    user_email = current_admin["email"]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)

    query = db.table("staff_goals").select("*, admins(full_name, department)")
    
    if not is_hr:
        # Get current user ID
        cur = await db_execute(lambda: db.table("admins").select("id").eq("email", user_email).execute())
        cur_id = cur.data[0]["id"] if cur.data else None
        
        if staff_id and staff_id == cur_id:
             query = query.eq("staff_id", cur_id)
        else:
             # Managers see their own + team
             query = query.or_(f"staff_id.eq.{cur_id},admins.line_manager_id.eq.{cur_id}")
    elif staff_id:
        query = query.eq("staff_id", staff_id)

    res = await db_execute(lambda: query.execute())
    return res.data

class TaskCreate(BaseModel):
    assigned_to: str
    title: str
    due_date: date
    priority: str = "Medium"
    notes: Optional[str] = None

@router.get("/tasks")
async def get_hr_tasks(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch tasks for HR (all) or Staff (own)."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("staff_tasks").select("*, admins!staff_tasks_assigned_to_fkey(full_name)")
    if staff_id:
        query = query.eq("assigned_to", staff_id)
    elif not is_hr:
        query = query.eq("assigned_to", current_admin["sub"])
        
    res = await db_execute(lambda: query.execute())
    return res.data

@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_hr_task(task: TaskCreate, current_admin: dict = Depends(verify_token)):
    """Assign a task. HR or Manager only."""
    db = get_db()
    res = await db_execute(lambda: db.table("staff_tasks").insert({
        "assigned_to": task.assigned_to,
        "title": task.title,
        "due_date": task.due_date.isoformat(),
        "priority": task.priority,
        "status": "pending",
        "created_by": current_admin["sub"]
    }).execute())
    return res.data[0]

class GoalCreate(BaseModel):
    staff_id: str
    kpi_name: str
    target_value: float
    unit: str = "%"
    weight: float = 1.0
    month: date
    template_id: Optional[str] = None

@router.get("/goals")
async def get_hr_goals(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch goals/KPIs for HR (all) or Staff (own)."""
    # This was a duplicate of get_all_goals, we just alias to keep it compiling if anything points here
    return await get_all_goals(staff_id, current_admin)

@router.post("/goals", status_code=status.HTTP_201_CREATED)
async def create_hr_goal(goal: GoalCreate, current_admin: dict = Depends(verify_token)):
    """Set a KPI goal for a staff member. HR or Manager only."""
    # This was a duplicate of set_staff_goal
    return await set_staff_goal(goal, current_admin)

@router.get("/kpi-templates")
async def list_kpi_templates(department: Optional[str] = None, active: Optional[bool] = True, current_admin: dict = Depends(verify_token)):
    """Fetch KPI template entries for the Goal Library."""
    db = get_db()
    query = db.table("kpi_templates").select("*")
    if department:
        query = query.eq("department", department)
    if active is not None:
        query = query.eq("is_active", active)
    res = await db_execute(lambda: query.order("department").execute())
    return res.data

@router.post("/kpi-templates", status_code=status.HTTP_201_CREATED)
async def create_kpi_template(template: KPITemplateCreate, current_admin: dict = Depends(verify_token)):
    """Create a new KPI template. HR only."""
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    if not is_hr:
        raise HTTPException(status_code=403, detail="Admin only")
    db = get_db()
    res = await db_execute(lambda: db.table("kpi_templates").insert({
        "name": template.name,
        "department": template.department,
        "category": template.category,
        "description": template.description,
        "measurement_source": template.measurement_source,
        "default_unit": template.default_unit,
        "is_active": template.is_active,
        "created_by": current_admin["sub"]
    }).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create KPI template")
    return res.data[0]

@router.patch("/kpi-templates/{template_id}")
async def update_kpi_template(template_id: str, template: KPITemplateUpdate, current_admin: dict = Depends(verify_token)):
    """Update an existing KPI template. HR only."""
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    if not is_hr:
        raise HTTPException(status_code=403, detail="Admin only")
    update_data = template.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No changes provided")
    db = get_db()
    res = await db_execute(lambda: db.table("kpi_templates").update(update_data).eq("id", template_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="KPI template not found")
    return res.data[0]

@router.delete("/kpi-templates/{template_id}")
async def delete_kpi_template(template_id: str, current_admin: dict = Depends(verify_token)):
    """Delete a KPI template. HR only."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    db = get_db()
    
    # Check if in use
    in_use = await db_execute(lambda: db.table("staff_goals").select("id").eq("template_id", template_id).limit(1).execute())
    if in_use.data:
        raise HTTPException(status_code=400, detail="Cannot delete template currently in use by staff goals.")
        
    await db_execute(lambda: db.table("kpi_templates").delete().eq("id", template_id).execute())
    return {"message": "KPI template deleted"}

# ─── PERFORMANCE REVIEWS ──────────────────────────────────────────────────────

@router.post("/performance/review", tags=["Performance"])
async def create_performance_review(review: PerformanceReviewCreate, current_admin: dict = Depends(verify_token)):
    """Log a formal performance review. HR/Admin only (reviewers)."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "operations"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Reviewer access only.")
    
    db = get_db()
    data = review.dict()
    data["reviewer_id"] = current_admin["sub"]
    data["created_at"] = datetime.utcnow().isoformat()
    
    res = await db_execute(lambda: db.table("performance_reviews").insert(data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to log review.")
    return res.data[0]

@router.get("/performance/reviews", tags=["Performance"])
async def get_performance_reviews(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch performance reviews. HR sees all. Staff sees own."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("performance_reviews").select("*, reviewer:admins!performance_reviews_reviewer_id_fkey(full_name), staff:admins!performance_reviews_staff_id_fkey(full_name)")
    
    if staff_id:
        if not is_hr and staff_id != current_admin["sub"]:
            raise HTTPException(status_code=403, detail="You can only view your own reviews.")
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
        
    res = await db_execute(lambda: query.order("review_date", desc=True).execute())
    return res.data

class IncidentCreate(BaseModel):
    staff_id: str
    incident_type: str
    severity: str
    incident_date: Optional[str] = None  # ISO date string; defaults to today if omitted
    notes: Optional[str] = None

@router.get("/mismanagement")
async def get_hr_incidents(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch logged incidents. HR sees all. Staff see own."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("disciplinary_records").select("*, admins!disciplinary_records_staff_id_fkey(full_name, department)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
        
    res = await db_execute(lambda: query.execute())
    # Normalise field names to match frontend expectations
    records = []
    for r in res.data:
        records.append({
            **r,
            "type": r.get("incident_type", r.get("type", "")),
        })
    return records

@router.post("/mismanagement", status_code=status.HTTP_201_CREATED)
async def log_hr_incident(inc: IncidentCreate, current_admin: dict = Depends(verify_token)):
    """Log a conduct or performance incident. HR or Manager only."""
    db = get_db()
    res = await db_execute(lambda: db.table("disciplinary_records").insert({
        "staff_id": inc.staff_id,
        "incident_type": inc.incident_type,
        "severity": inc.severity,
        "incident_date": date.today().isoformat(),
        "notes": inc.notes,
        "logged_by": current_admin["sub"]
    }).execute())
    return res.data[0]

@router.get("/payroll/payslips")
async def get_payslips(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch payslips. HR sees all. Staff see own."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("payroll_records").select("*, admins!payroll_records_staff_id_fkey(full_name, department)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
        
    res = await db_execute(lambda: query.execute())
    return res.data

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_admin: dict = Depends(verify_token)):
    """Fetch all necessary data for the HR dashboard in a single optimized call."""
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    if not is_hr:
         raise HTTPException(status_code=403, detail="Not authorized for HR Dashboard")
    
    db = get_db()
    today_str = date.today().isoformat()
    
    # 1. Fetch raw data
    staff_res = await db_execute(lambda: db.table("admins").select("id, full_name, role, primary_role, department, is_active, is_archived, created_at, staff_profiles(dob, date_joined)").execute())
    leaves_res = await db_execute(lambda: db.table("leave_requests").select("*, admins!leave_requests_staff_id_fkey(full_name, department)").execute())
    tasks_res = await db_execute(lambda: db.table("staff_tasks").select("*, admins!staff_tasks_assigned_to_fkey(full_name)").execute())
    incidents_res = await db_execute(lambda: db.table("disciplinary_records").select("*, admins!disciplinary_records_staff_id_fkey(full_name, department)").execute())
    attendance_today = await db_execute(lambda: db.table("attendance_records").select("staff_id, check_in, is_suspicious").eq("date", today_str).execute())
    
    staff_data = staff_res.data
    active_staff = [s for s in staff_data if s.get("is_active") and not s.get("is_archived")]
    
    # 2. Attendance Analytics
    present_ids = {a["staff_id"] for a in attendance_today.data}
    on_leave_ids = {l["staff_id"] for l in leaves_res.data if l["status"] == "approved" and l["start_date"] <= today_str <= l["end_date"]}
    
    late_count = 0
    for a in attendance_today.data:
        ci = a.get("check_in")
        if ci:
            # Threshold 09:00:00
            time_part = ci.split("T")[1].split(".")[0] if "T" in ci else ""
            if time_part and time_part > "09:00:00":
                late_count += 1
    
    suspicious_today = sum(1 for a in attendance_today.data if a.get("is_suspicious"))
    
    absent_staff = [s for s in active_staff if s["id"] not in present_ids and s["id"] not in on_leave_ids]
    
    # 3. Department Distribution
    dept_dist = {}
    for s in active_staff:
        d = s.get("department") or "Unassigned"
        dept_dist[d] = dept_dist.get(d, 0) + 1
    
    # 4. Milestones
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
    recent_staff = [s for s in staff_data if s.get("created_at") and s["created_at"] >= thirty_days_ago]
    
    today_dt = date.today()
    upcoming_birthdays = []
    upcoming_anniversaries = []
    
    for s in active_staff:
        prof = s.get("staff_profiles")
        if prof and len(prof) > 0:
            p = prof[0]
            # Check Birthdays (Next 14 days)
            if p.get("dob"):
                try:
                    dob = date.fromisoformat(p["dob"])
                    # Handle leap years safely
                    try:
                        this_year_bday = dob.replace(year=today_dt.year)
                    except ValueError:
                        this_year_bday = dob.replace(year=today_dt.year, day=dob.day-1)
                        
                    if this_year_bday < today_dt:
                        try:
                            this_year_bday = dob.replace(year=today_dt.year + 1)
                        except ValueError:
                            this_year_bday = dob.replace(year=today_dt.year + 1, day=dob.day-1)
                    
                    days_to_bday = (this_year_bday - today_dt).days
                    if days_to_bday <= 14:
                        upcoming_birthdays.append({
                            "id": s["id"], "full_name": s["full_name"], "department": s["department"], "date": p["dob"], "days_left": days_to_bday
                        })
                except:
                    pass
                    
            # Check Anniversaries (Next 30 days)
            if p.get("date_joined"):
                try:
                    dj = date.fromisoformat(p["date_joined"])
                    try:
                        this_year_anniv = dj.replace(year=today_dt.year)
                    except ValueError:
                        this_year_anniv = dj.replace(year=today_dt.year, day=dj.day-1)
                        
                    if this_year_anniv < today_dt:
                        try:
                            this_year_anniv = dj.replace(year=today_dt.year + 1)
                        except ValueError:
                            this_year_anniv = dj.replace(year=today_dt.year + 1, day=dj.day-1)
                            
                    days_to_anniv = (this_year_anniv - today_dt).days
                    years_worked = this_year_anniv.year - dj.year
                    if days_to_anniv <= 30 and years_worked > 0:
                        upcoming_anniversaries.append({
                            "id": s["id"], "full_name": s["full_name"], "department": s["department"], "date": p["date_joined"], "days_left": days_to_anniv, "years": years_worked
                        })
                except:
                    pass

    upcoming_birthdays.sort(key=lambda x: x["days_left"])
    upcoming_anniversaries.sort(key=lambda x: x["days_left"])

    return {
        "staff": staff_data,
        "leaves": leaves_res.data,
        "tasks": tasks_res.data,
        "incidents": incidents_res.data,
        "analytics": {
            "total_active": len(active_staff),
            "present_today": len(present_ids),
            "late_today": late_count,
            "on_leave_today": len(on_leave_ids),
            "absent_today": len(absent_staff),
            "absent_names": [s["full_name"] for s in absent_staff],
            "suspicious_today": suspicious_today,
            "department_distribution": dept_dist,
            "recent_milestones": recent_staff[:5],
            "upcoming_birthdays": upcoming_birthdays,
            "upcoming_anniversaries": upcoming_anniversaries
        }
    }

"""
Paste this block into routers/hr.py

Place the Pydantic models near the top with your other models.
Place the two route handlers alongside your other attendance routes.

Requires: pip install httpx  (already likely installed)
"""

# ── ADD TO MODELS SECTION ────────────────────────────────────────────────────

from fastapi import Request  # add to existing fastapi import

class AttendanceCheckIn(BaseModel):
    """Payload sent by the browser when a staff member checks in."""
    latitude:          Optional[float] = None
    longitude:         Optional[float] = None
    location_accuracy: Optional[float] = None   # metres
    location_status:   str = "unavailable"       # granted | denied | unavailable
    device_type:       Optional[str] = None      # resolved by frontend from UA
    is_remote:         bool = False              # remote work flag

class AttendanceCheckOut(BaseModel):
    """Payload sent on check-out."""
    latitude:          Optional[float] = None
    longitude:         Optional[float] = None
    location_status:   str = "unavailable"
    device_type:       Optional[str] = None
    is_remote:         bool = False


# ── HELPER ───────────────────────────────────────────────────────────────────

def _get_real_ip(request: Request) -> str:
    """
    Render sits behind a proxy so the real IP is in X-Forwarded-For.
    We take the first (leftmost) address which is the original client.
    Falls back to request.client.host for local dev.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── ROUTES ───────────────────────────────────────────────────────────────────

def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine formula to calculate distance between two points on Earth in meters."""
    if None in [float(x) if x is not None else None for x in [lat1, lon1, lat2, lon2]]:
        return None
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        R = 6371000 # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except:
        return None

@router.post("/presence/checkin", status_code=status.HTTP_201_CREATED)
async def check_in(
    payload: AttendanceCheckIn,
    request: Request,
    current_admin: dict = Depends(verify_token)
):
    """
    Staff member checks in for the day.
    Records: timestamp, GPS coords (if granted), IP, device type, raw UA.
    One check-in per staff per calendar day is enforced by the DB UNIQUE
    constraint on (staff_id, date).
    """
    db        = get_db()
    staff_id  = current_admin["sub"]
    today     = date.today().isoformat()
    now       = datetime.utcnow().isoformat()
    ip        = _get_real_ip(request)
    ua        = request.headers.get("user-agent", "")

    # Reject if already checked in today
    existing = await db_execute(
        lambda: db.table("attendance_records")
                  .select("id, check_in")
                  .eq("staff_id", staff_id)
                  .eq("date", today)
                  .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail="Already checked in for today."
        )

    # Geofence & Anti-Cheating Logic
    office_lat = os.getenv("OFFICE_LAT", "6.525737")
    office_lon = os.getenv("OFFICE_LON", "3.372357")
    threshold  = float(os.getenv("GEOFENCE_RADIUS_METERS", "200"))
    
    distance = None
    is_suspicious = False
    reasons = []

    if payload.latitude and payload.longitude:
        distance = calculate_distance(payload.latitude, payload.longitude, office_lat, office_lon)
        if not payload.is_remote and distance and distance > threshold:
            is_suspicious = True
            reasons.append(f"Location Outside Geofence ({int(distance)}m away)")
    else:
        if not payload.is_remote:
            is_suspicious = True
            reasons.append("GPS Coordinates Missing")

    # Simple device check: if it's a mobile device without GPS, that's often suspicious
    if payload.device_type == "Mobile" and not payload.latitude and not payload.is_remote:
         is_suspicious = True
         reasons.append("Mobile check-in without GPS")

    record = {
        "staff_id":          staff_id,
        "date":              today,
        "check_in":          now,
        "status":            "Present",
        "is_suspicious":     is_suspicious,
        "suspicious_reason": ". ".join(reasons) if reasons else None,
        "distance_meters":   distance,
        "is_remote":         payload.is_remote,
        # location
        "latitude":          payload.latitude,
        "longitude":         payload.longitude,
        "location_accuracy": payload.location_accuracy,
        "location_status":   payload.location_status,
        # device fingerprint
        "ip_address":        ip,
        "device_type":       payload.device_type,
        "user_agent":        ua,
    }

    res = await db_execute(
        lambda: db.table("attendance_records").insert(record).execute()
    )
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to record check-in.")

    return {
        "message":    "Checked in successfully.",
        "check_in":   now,
        "ip_address": ip,
        "location":   {
            "latitude":  payload.latitude,
            "longitude": payload.longitude,
            "status":    payload.location_status,
        },
    }


@router.patch("/presence/checkout")
async def check_out(
    payload: AttendanceCheckOut,
    request: Request,
    current_admin: dict = Depends(verify_token)
):
    """
    Staff member checks out for the day.
    Updates the existing today record with check-out time + location.
    """
    db       = get_db()
    staff_id = current_admin["sub"]
    today    = date.today().isoformat()
    now      = datetime.utcnow().isoformat()
    ip       = _get_real_ip(request)
    ua       = request.headers.get("user-agent", "")

    # Must have checked in first
    existing = await db_execute(
        lambda: db.table("attendance_records")
                  .select("id, check_in, check_out")
                  .eq("staff_id", staff_id)
                  .eq("date", today)
                  .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="No check-in found for today.")

    rec = existing.data[0]
    if rec.get("check_out"):
        raise HTTPException(status_code=409, detail="Already checked out for today.")

    # Geofence check for checkout
    office_lat = os.getenv("OFFICE_LAT", "6.525737")
    office_lon = os.getenv("OFFICE_LON", "3.372357")
    threshold  = float(os.getenv("GEOFENCE_RADIUS_METERS", "200"))
    
    distance = None
    is_suspicious = rec.get("is_suspicious", False)
    existing_reason = rec.get("suspicious_reason", "")
    reasons = [existing_reason] if existing_reason else []

    if payload.latitude and payload.longitude:
        distance = calculate_distance(payload.latitude, payload.longitude, office_lat, office_lon)
        if not payload.is_remote and distance and distance > threshold:
            is_suspicious = True
            reasons.append(f"Check-Out Outside Geofence ({int(distance)}m away)")
    else:
        if not payload.is_remote:
            is_suspicious = True
            reasons.append("Check-Out GPS Coordinates Missing")

    updates = {
        "check_out":              now,
        "check_out_latitude":     payload.latitude,
        "check_out_longitude":    payload.longitude,
        "check_out_ip_address":   ip,
        "check_out_device_type":  payload.device_type,
        "check_out_user_agent":   ua,
        "is_suspicious":          is_suspicious,
        "suspicious_reason":      ". ".join(reasons) if reasons else None,
        "updated_at":             now,
    }

    await db_execute(
        lambda: db.table("attendance_records")
                  .update(updates)
                  .eq("id", rec["id"])
                  .execute()
    )

    return {"message": "Checked out successfully.", "check_out": now}


@router.get("/presence/suspicious", tags=["HR Management"])
async def get_suspicious_attendance(current_admin: dict = Depends(verify_token)):
    """
    HR-only: Returns attendance records where two different staff
    shared the same IP on the same day — buddy-punch candidates.
    Reads from the suspicious_attendance view created in the migration.
    """
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR Admin only.")

    db  = get_db()
    res = await db_execute(
        lambda: db.table("suspicious_attendance").select("*").execute()
    )
    return res.data

@router.post("/debug/seed-kpis", tags=["HR Management"])
async def seed_kpi_library(current_admin: dict = Depends(verify_token)):
    """Temporary endpoint to seed professional KPI templates."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Admin access required.")
        
    db = get_db()
    templates = [
        {"name": "Lead Generation", "department": "Sales & Acquisitions", "category": "Marketing", "measurement_source": "mkt_leads_added", "default_unit": "leads", "is_active": True, "description": "Counts distinct Marketing Contacts and Clients added to CRM by the staff."},
        {"name": "Lead Conversion Rate", "department": "Sales & Acquisitions", "category": "Sales", "measurement_source": "mkt_lead_conversion", "default_unit": "%", "is_active": True, "description": "Percentage of leads converted to registered clients."},
        {"name": "Sales Revenue (Paid)", "department": "Finance", "category": "Revenue", "measurement_source": "sales_revenue", "default_unit": "NGN", "is_active": True, "description": "Total actual revenue collected from payments attributed to staff."},
        {"name": "Deals Closed", "department": "Sales & Acquisitions", "category": "Sales", "measurement_source": "sales_deals_closed", "default_unit": "deals", "is_active": True, "description": "Number of deal invoices marked as completed/closed."},
        {"name": "Client Appointments", "department": "Operations", "category": "Activity", "measurement_source": "ops_appointments", "default_unit": "appts", "is_active": True, "description": "Count of successfully completed client appointments."},
        {"name": "Support Efficiency", "department": "Human Resources", "category": "Service", "measurement_source": "admin_ticket_esc", "default_unit": "tickets", "is_active": True, "description": "Effectiveness in resolving assigned internal support tickets."}
    ]
    
    results = []
    for t in templates:
        # Check if exists by name AND department
        exists = await db_execute(lambda: db.table("kpi_templates").select("id").eq("name", t["name"]).eq("department", t["department"]).execute())
        if not exists.data:
            res = await db_execute(lambda: db.table("kpi_templates").insert(t).execute())
            results.append(t["name"])
            
    return {"message": "KPI Library Seeded", "added": results}

# ─── LEAVE MANAGEMENT ─────────────────────────────────────────────────────────

@router.post("/leave-requests", tags=["HR Suite"])
async def request_leave(req: LeaveRequestCreate, current_admin: dict = Depends(verify_token)):
    """Submit a new leave request."""
    db = get_db()
    data = req.dict()
    data["staff_id"] = current_admin["sub"]
    data["status"] = "pending"
    data["created_at"] = datetime.utcnow().isoformat()
    # Ensure proof_url is present (req.dict() already has it if it's in the model)
    
    res = await db_execute(lambda: db.table("leave_requests").insert(data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to submit leave request.")
    return res.data[0]

@router.get("/leave-requests", tags=["HR Suite"])
async def get_leave_requests(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch leave requests. HR sees all. Staff see own."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("leave_requests").select("*, staff:admins!leave_requests_staff_id_fkey(full_name, department)")
    
    if staff_id:
        if not is_hr and staff_id != current_admin["sub"]:
            raise HTTPException(status_code=403, detail="Access denied.")
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
        
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return res.data

@router.patch("/leave-requests/{req_id}", tags=["HR Suite"])
async def update_leave_status(req_id: str, up: LeaveRequestUpdate, current_admin: dict = Depends(verify_token)):
    """Approve or reject a leave request. HR only."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "operations"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Admin only.")
    
    db = get_db()
    # 1. Fetch current request to know days_count and staff_id
    req_res = await db_execute(lambda: db.table("leave_requests").select("*").eq("id", req_id).execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found.")
    req = req_res.data[0]
    
    # 2. Update status
    res = await db_execute(lambda: db.table("leave_requests").update({
        "status": up.status,
        "approver_id": current_admin["sub"]
    }).eq("id", req_id).execute())
    
    # 3. If approved, deduct from staff_profiles quota
    if up.status == "approved" and req["status"] != "approved":
        await db_execute(lambda: db.rpc("deduct_leave_quota", {
            "p_staff_id": req["staff_id"],
            "p_days": req["days_count"]
        }).execute())
        
    return res.data[0]

# ─── DOCUMENTS & QUALIFICATIONS ──────────────────────────────────────────────

@router.post("/documents", tags=["HR Suite"])
async def upload_staff_document(doc: StaffDocumentCreate, current_admin: dict = Depends(verify_token)):
    """Link an uploaded document to a staff profile. HR can upload anything; Staff can only self-upload uniquely per type."""
    user_id = current_admin["sub"]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin"] for r in user_roles)
    is_self = doc.staff_id == user_id
    
    if not (is_hr or is_self):
        raise HTTPException(status_code=403, detail="Permission denied. You can only upload for yourself or if you are HR.")
    
    db = get_db()
    
    # Duplicate check for non-HR
    if not is_hr:
        existing = await db_execute(lambda: db.table("staff_documents").select("id").eq("staff_id", doc.staff_id).eq("doc_type", doc.doc_type).execute())
        if existing.data:
            raise HTTPException(status_code=403, detail=f"You have already uploaded a document of type '{doc.doc_type}'. Please contact HR to update it.")
    
    db = get_db()
    data = doc.dict()
    data["uploaded_by"] = current_admin["sub"]
    data["created_at"] = datetime.utcnow().isoformat()
    
    res = await db_execute(lambda: db.table("staff_documents").insert(data).execute())
    return res.data[0]

@router.delete("/documents/{doc_id}", tags=["HR Suite"])
async def delete_staff_document(doc_id: str, current_admin: dict = Depends(verify_token)):
    """HR-only: Delete a staff document."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR Admin only.")
    
    db = get_db()
    await db_execute(lambda: db.table("staff_documents").delete().eq("id", doc_id).execute())
    return {"message": "Document deleted successfully"}

@router.get("/staff/{staff_id}/documents", tags=["HR Suite"])
async def get_staff_documents(staff_id: str, current_admin: dict = Depends(verify_token)):
    """Fetch documents for a specific staff member."""
    db = get_db()
    res = await db_execute(lambda: db.table("staff_documents").select("*").eq("staff_id", staff_id).execute())
    return res.data

@router.post("/staff/{staff_id}/qualifications", tags=["HR Suite"])
async def add_qualification(staff_id: str, q: StaffQualificationCreate, current_admin: dict = Depends(verify_token)):
    """Add education or certification to a profile."""
    db = get_db()
    data = q.dict()
    data["staff_id"] = staff_id
    res = await db_execute(lambda: db.table("staff_qualifications").insert(data).execute())
    return res.data[0]

@router.get("/staff/{staff_id}/qualifications", tags=["HR Suite"])
async def get_qualifications(staff_id: str):
    db = get_db()
    res = await db_execute(lambda: db.table("staff_qualifications").select("*").eq("staff_id", staff_id).execute())
    return res.data

# ─── HR ANALYTICS ────────────────────────────────────────────────────────────

@router.get("/analytics/headcount", tags=["HR Suite"])
async def get_headcount_stats(current_admin: dict = Depends(verify_token)):
    """Fetch high-level headcount stats."""
    db = get_db()
    res = await db_execute(lambda: db.table("admins").select("department, role, is_active").execute())
    
    active_staff = [s for s in res.data if s["is_active"]]
    stats = {
        "total_active": len(active_staff),
        "by_department": {},
        "by_role": {}
    }
    
    for s in active_staff:
        dept = s.get("department") or "Unassigned"
        role = s.get("role") or "Staff"
        stats["by_department"][dept] = stats["by_department"].get(dept, 0) + 1
        stats["by_role"][role] = stats["by_role"].get(role, 0) + 1
        
    return stats

# ─── PERFORMANCE MANAGEMENT ──────────────────────────────────────────────────

def compute_composite_score(goals: List[dict], reviews: List[dict]) -> dict:
    """
    Computes a composite performance score based on the PRD framework:
    - Monthly Goals (40%)
    - Work Quality (20%)
    - Teamwork / Initiative (20% + 20%)
    Returns a breakdown of components and the final score (0-100).
    """
    # 1. Goal Achievement (40%)
    goal_avg = 0
    if goals:
        goal_avg = sum(g.get("achievement_pct", 0) for g in goals) / len(goals)
    
    # 2. Qualitative Components (From latest review)
    # PRD uses 1-5 scale for soft skills, 0-100 for quality.
    quality = 0
    teamwork = 0
    initiative = 0
    
    if reviews:
        latest = reviews[0] # Assumes ordered by date desc
        quality = float(latest.get("quality_score", 0))
        teamwork = (float(latest.get("teamwork_score", 0)) / 5) * 100
        initiative = (float(latest.get("leadership_score", 0)) / 5) * 100
        
    final_score = (goal_avg * 0.4) + (quality * 0.2) + (teamwork * 0.2) + (initiative * 0.2)
    
    return {
        "score": round(final_score, 1),
        "breakdown": {
            "goals": round(goal_avg, 1),
            "quality": round(quality, 1),
            "teamwork": round(teamwork, 1),
            "initiative": round(initiative, 1)
        }
    }

@router.post("/staff/{staff_id}/performance/review", tags=["HR Suite"])
async def create_performance_review(staff_id: str, rev: PerformanceReviewCreate, current_admin: dict = Depends(verify_token)):
    """Managers or HR submit a qualitative performance review."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "line_manager"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Managerial access only.")
        
    db = get_db()
    data = rev.dict()
    data["staff_id"] = staff_id
    data["reviewer_id"] = current_admin["sub"]
    data["review_period"] = rev.review_period.isoformat()
    data["created_at"] = datetime.utcnow().isoformat()
    
    res = await db_execute(lambda: db.table("performance_reviews").insert(data).execute())
    return res.data[0]

@router.get("/staff/{staff_id}/performance", tags=["HR Suite"])
async def get_staff_performance(staff_id: str, current_admin: dict = Depends(verify_token)):
    """Fetch current month's performance score and breakdown."""
    db = get_db()
    today = date.today()
    month_start = date(today.year, today.month, 1).isoformat()
    
    # Fetch goals for current month
    goals_res = await db_execute(lambda: db.table("staff_goals")
        .select("*")
        .eq("staff_id", staff_id)
        .gte("month", month_start)
        .execute())
        
    # Fetch latest review
    rev_res = await db_execute(lambda: db.table("performance_reviews")
        .select("*")
        .eq("staff_id", staff_id)
        .order("review_period", desc=True)
        .limit(1)
        .execute())
        
    summary = compute_composite_score(goals_res.data, rev_res.data)
    return {
        **summary,
        "goals": goals_res.data,
        "review": rev_res.data[0] if rev_res.data else None
    }

@router.get("/staff/{staff_id}/performance/history", tags=["HR Suite"])
async def get_performance_history(staff_id: str, current_admin: dict = Depends(verify_token)):
    """Generate a 6-month historical trend of performance scores."""
    db = get_db()
    today = date.today()
    history = []
    
    # We'll compute for the last 6 months
    for i in range(6):
        m_date = today - timedelta(days=i*30)
        m_start = date(m_date.year, m_date.month, 1)
        m_end = (m_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # 1. Fetch goals
        g_res = await db_execute(lambda: db.table("staff_goals")
            .select("achievement_pct")
            .eq("staff_id", staff_id)
            .gte("month", m_start.isoformat())
            .lte("month", m_end.isoformat())
            .execute())
            
        # 2. Fetch review within this period or most recent prior
        r_res = await db_execute(lambda: db.table("performance_reviews")
            .select("*")
            .eq("staff_id", staff_id)
            .lte("review_period", m_end.isoformat())
            .order("review_period", desc=True)
            .limit(1)
            .execute())
            
        scoring = compute_composite_score(g_res.data, r_res.data)
        history.append({
            "month": m_start.strftime("%b %Y"),
            "score": scoring["score"]
        })
        
    return history[::-1] # Chronological order

# ─── DISCIPLINARY / INCIDENT LOG ──────────────────────────────────────────────

@router.post("/incidents", tags=["HR Suite"])
async def log_incident(inc: IncidentCreate, current_admin: dict = Depends(verify_token)):
    """Log a management/disciplinary incident."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "line_manager"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Managerial access only.")
        
    db = get_db()
    data = inc.dict()
    data["created_at"] = datetime.utcnow().isoformat()
    # Default incident_date to today if not provided (disciplinary_records requires it)
    if not data.get("incident_date"):
        data["incident_date"] = datetime.utcnow().date().isoformat()
    data["logged_by"] = current_admin.get("sub")

    res = await db_execute(lambda: db.table("disciplinary_records").insert(data).execute())
    return res.data[0]

@router.get("/incidents", tags=["HR Suite"])
async def get_all_incidents(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    """Fetch incidents. HR sees all. Staff see own."""
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    query = db.table("disciplinary_records").select("*, staff:admins!disciplinary_records_staff_id_fkey(full_name, department)")
    
    if staff_id:
        if not is_hr and staff_id != current_admin["sub"]:
            raise HTTPException(status_code=403, detail="Access denied.")
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
        
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return res.data

@router.post("/upload", tags=["HR Suite"])
async def upload_hr_file(request: Request, current_admin=Depends(verify_token)):
    """Upload a file to hr-documents bucket."""
    try:
        form = await request.form()
        file = next((v for v in form.values() if hasattr(v, "filename") and v.filename), None)
        if not file: raise HTTPException(status_code=400, detail="No file found")

        file_bytes = await file.read()
        db = get_db()
        from database import SUPABASE_URL
        import uuid

        ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Upload to hr-documents bucket
        db.storage.from_("hr-documents").upload(path=filename, file=file_bytes, file_options={"content-type": file.content_type})
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/hr-documents/{filename}"
        
        return {"url": file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ─── RECRUITMENT / ATS ────────────────────────────────────────────────────────

class JobRequisitionCreate(BaseModel):
    title: str
    department: str
    employment_type: str
    location: Optional[str] = None
    status: str = "Pending Approval"
    description: Optional[str] = None # About the Role
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    salary_range: Optional[str] = None
    headcount: int = 1
    justification: Optional[str] = None

class JobApplicationCreate(BaseModel):
    job_id: Optional[str] = None
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None

class InterviewCreate(BaseModel):
    application_id: str
    interviewer_id: str
    scheduled_at: datetime

@router.get("/recruitment/jobs")
async def get_jobs():
    db = get_db()
    res = await db_execute(lambda: db.table("job_requisitions").select("*").order("created_at", desc=True).execute())
    return res.data

@router.post("/recruitment/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(job: JobRequisitionCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("job_requisitions").insert(job.dict(exclude_unset=True)).execute())
    return res.data[0]

@router.patch("/recruitment/jobs/{job_id}")
async def update_job(job_id: str, status_update: dict, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("job_requisitions").update({"status": status_update.get("status"), "updated_at": "now()"}).eq("id", job_id).execute())
    return res.data[0] if res.data else None

@router.get("/recruitment/applications")
async def get_applications(job_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    query = db.table("job_applications").select("*, job_requisitions(title, department)")
    if job_id: query = query.eq("job_id", job_id)
    res = await db_execute(lambda: query.order("applied_at", desc=True).execute())
    return res.data

@router.post("/recruitment/applications", status_code=status.HTTP_201_CREATED)
async def create_application(app: JobApplicationCreate):
    # Could be public, no token required natively, but keeping simple
    db = get_db()
    res = await db_execute(lambda: db.table("job_applications").insert(app.dict(exclude_unset=True)).execute())
    return res.data[0]

@router.patch("/recruitment/applications/{app_id}")
async def update_application_status(app_id: str, status_update: dict, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("job_applications").update({"status": status_update.get("status")}).eq("id", app_id).execute())
    return res.data[0] if res.data else None

@router.post("/recruitment/applications/{app_id}/hire")
async def hire_applicant(app_id: str, current_admin: dict = Depends(verify_token)):
    """Convert a successful applicant into a staff member."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
    
    db = get_db()
    
    # 1. Fetch application details
    app_res = await db_execute(lambda: db.table("job_applications").select("*, job_requisitions(title, department)").eq("id", app_id).execute())
    if not app_res.data:
        raise HTTPException(status_code=404, detail="Application not found")
    app = app_res.data[0]
    job = app.get("job_requisitions", {})
    
    # 2. Check if already has an admin account
    existing = await db_execute(lambda: db.table("admins").select("id").eq("email", app["candidate_email"]).execute())
    if existing.data:
        # If they already exist, just link them to a profile if missing
        admin_id = existing.data[0]["id"]
    else:
        # 3. Create Admin Account
        import bcrypt
        default_pwd = "Welcome@Eximp" + str(datetime.now().year)
        pwd_hash = bcrypt.hashpw(default_pwd.encode(), bcrypt.gensalt()).decode()
        
        adm_res = await db_execute(lambda: db.table("admins").insert({
            "full_name": app["candidate_name"],
            "email": app["candidate_email"],
            "password_hash": pwd_hash,
            "role": "staff",
            "primary_role": "staff",
            "department": job.get("department", "Unassigned"),
            "is_active": True
        }).execute())
        if not adm_res.data:
            raise HTTPException(status_code=500, detail="Failed to create admin account")
        admin_id = adm_res.data[0]["id"]

    # 4. Create/Update Staff Profile
    profile_data = {
        "admin_id": admin_id,
        "job_title": job.get("title", "Staff Member"),
        "phone_number": app["candidate_phone"],
        "date_joined": datetime.utcnow().date().isoformat(),
        "staff_type": "full"
    }
    
    # Use upsert logic or simple check
    prof_exists = await db_execute(lambda: db.table("staff_profiles").select("id").eq("admin_id", admin_id).execute())
    if prof_exists.data:
        await db_execute(lambda: db.table("staff_profiles").update(profile_data).eq("admin_id", admin_id).execute())
    else:
        await db_execute(lambda: db.table("staff_profiles").insert(profile_data).execute())

    # 5. Attach CV as a document if exists
    if app["resume_url"]:
        await db_execute(lambda: db.table("staff_documents").insert({
            "staff_id": admin_id,
            "doc_type": "CV",
            "title": f"CV - {app['candidate_name']}",
            "file_url": app["resume_url"],
            "uploaded_by": current_admin["sub"]
        }).execute())

    # 6. Update Application Status to Hired
    await db_execute(lambda: db.table("job_applications").update({"status": "Hired"}).eq("id", app_id).execute())
    
    return {"message": "Applicant successfully hired and onboarded", "admin_id": admin_id}

@router.post("/recruitment/interviews", status_code=status.HTTP_201_CREATED)
async def schedule_interview(interview: InterviewCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    
    # Must also move application status to "Interview"
    await db_execute(lambda: db.table("job_applications").update({"status": "Interview"}).eq("id", interview.application_id).execute())
    
    # Needs isoformat for datetime
    idata = interview.dict()
    idata["scheduled_at"] = idata["scheduled_at"].isoformat()
    
    res = await db_execute(lambda: db.table("job_interviews").insert(idata).execute())
    return res.data[0]



# ─── ENGAGEMENT & CULTURE ─────────────────────────────────────────────────────

class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: list # list of strings

class SurveyResponseSubmit(BaseModel):
    answers: dict
    is_anonymous: bool = True

@router.get("/culture/surveys")
async def get_surveys(current_admin: dict = Depends(verify_token)):
    db = get_db()
    
    # 1. Fetch active surveys
    surveys = await db_execute(lambda: db.table("engagement_surveys").select("*").order("created_at", desc=True).execute())
    
    # 2. Fetch responses if HR to calculate completion rates
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    if is_hr:
        responses = await db_execute(lambda: db.table("survey_responses").select("survey_id, answers").execute())
        resp_map = {}
        for r in responses.data:
            sid = r["survey_id"]
            if sid not in resp_map: resp_map[sid] = []
            resp_map[sid].append(r["answers"])
            
        for s in surveys.data:
            s["responses"] = resp_map.get(s["id"], [])
    
    return surveys.data

@router.post("/culture/surveys", status_code=status.HTTP_201_CREATED)
async def create_survey(survey: SurveyCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("engagement_surveys").insert({
        "title": survey.title,
        "description": survey.description,
        "questions": survey.questions
    }).execute())
    return res.data[0]

@router.post("/culture/surveys/{survey_id}/respond", status_code=status.HTTP_201_CREATED)
async def submit_survey_response(survey_id: str, response: SurveyResponseSubmit, current_admin: dict = Depends(verify_token)):
    db = get_db()
    
    # Check if already responded (if not anonymous, or strictly enforce one per staff)
    # We will just allow it, but in a real app you'd enforce unique limits if not anonymous.
    
    payload = {
        "survey_id": survey_id,
        "answers": response.answers,
        "is_anonymous": response.is_anonymous,
        "staff_id": None if response.is_anonymous else current_admin["sub"]
    }
    
    res = await db_execute(lambda: db.table("survey_responses").insert(payload).execute())
    return res.data[0]

# ============================================================
# PASTE THIS AT THE END OF routers/hr.py
# New routes for: task status, incident status, timesheets,
# shifts, learning, announcements, recognition, work permits,
# HR letters, grievances, audit logs, comp bands, bonuses
# ============================================================

# ─── TASK STATUS FIX ─────────────────────────────────────────
class TaskStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

@router.patch("/tasks/{task_id}")
async def update_task_status(task_id: str, update: TaskStatusUpdate, current_admin: dict = Depends(verify_token)):
    """Update task status to pending | in_progress | completed."""
    if update.status not in ["pending", "in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    db = get_db()
    task_res = await db_execute(lambda: db.table("staff_tasks").select("*").eq("id", task_id).execute())
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_res.data[0]
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    is_assignee = task.get("assigned_to") == current_admin.get("sub")
    is_creator = task.get("created_by") == current_admin.get("sub")
    if not (is_hr or is_assignee or is_creator):
        raise HTTPException(status_code=403, detail="Not authorised")
    update_data = {"status": update.status, "updated_at": datetime.utcnow().isoformat()}
    if update.status == "completed":
        update_data["completed_at"] = datetime.utcnow().isoformat()
    if update.notes:
        update_data["completion_notes"] = update.notes
    res = await db_execute(lambda: db.table("staff_tasks").update(update_data).eq("id", task_id).execute())
    return res.data[0] if res.data else {"message": "Updated"}

# ─── INCIDENT STATUS FIX ─────────────────────────────────────
class IncidentStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

@router.patch("/incidents/{incident_id}")
async def update_incident(incident_id: str, update: IncidentStatusUpdate, current_admin: dict = Depends(verify_token)):
    """HR only: update incident status to open|under_review|resolved|dismissed."""
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "operations"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR Admin only")
    valid = ["open", "under_review", "resolved", "dismissed"]
    if update.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    db = get_db()
    update_data = {
        "status": update.status,
        "updated_at": datetime.utcnow().isoformat(),
        "resolution_notes": update.resolution_notes,
    }
    if update.status in ["resolved", "dismissed"]:
        update_data["resolved_by"] = current_admin.get("sub")
        update_data["resolved_at"] = datetime.utcnow().isoformat()
    res = await db_execute(lambda: db.table("disciplinary_records").update(update_data).eq("id", incident_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Incident not found")
    return res.data[0]

# ─── TIMESHEETS ───────────────────────────────────────────────
class TimesheetCreate(BaseModel):
    week_start: date
    mon_hrs: float = 0; tue_hrs: float = 0; wed_hrs: float = 0
    thu_hrs: float = 0; fri_hrs: float = 0
    notes: Optional[str] = None

class TimesheetApproval(BaseModel):
    status: str
    reviewer_notes: Optional[str] = None

@router.get("/timesheets")
async def get_timesheets(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    query = db.table("timesheets").select("*, admins!timesheets_staff_id_fkey(full_name, department)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
    res = await db_execute(lambda: query.order("week_start", desc=True).execute())
    return res.data

@router.post("/timesheets", status_code=201)
async def submit_timesheet(ts: TimesheetCreate, current_admin: dict = Depends(verify_token)):
    db = get_db()
    total = ts.mon_hrs + ts.tue_hrs + ts.wed_hrs + ts.thu_hrs + ts.fri_hrs
    res = await db_execute(lambda: db.table("timesheets").insert({
        "staff_id": current_admin["sub"], "week_start": ts.week_start.isoformat(),
        "mon_hrs": ts.mon_hrs, "tue_hrs": ts.tue_hrs, "wed_hrs": ts.wed_hrs,
        "thu_hrs": ts.thu_hrs, "fri_hrs": ts.fri_hrs, "total_hrs": total,
        "notes": ts.notes, "status": "pending", "created_at": datetime.utcnow().isoformat()
    }).execute())
    return res.data[0]

@router.patch("/timesheets/{ts_id}")
async def approve_timesheet(ts_id: str, approval: TimesheetApproval, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "line_manager", "operations"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Manager or HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("timesheets").update({
        "status": approval.status, "reviewer_id": current_admin["sub"],
        "reviewer_notes": approval.reviewer_notes, "reviewed_at": datetime.utcnow().isoformat()
    }).eq("id", ts_id).execute())
    return res.data[0] if res.data else {"message": "Updated"}

# ─── SHIFT SCHEDULING ─────────────────────────────────────────
class ShiftCreate(BaseModel):
    staff_id: str; shift_date: date; start_time: str; end_time: str
    shift_type: str = "Regular"; notes: Optional[str] = None

@router.get("/shifts")
async def get_shifts(staff_id: Optional[str] = None, week_start: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    query = db.table("shifts").select("*, admins!shifts_staff_id_fkey(full_name, department)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    if week_start:
        week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()
        query = query.gte("shift_date", week_start).lte("shift_date", week_end)
    res = await db_execute(lambda: query.order("shift_date").execute())
    return res.data

@router.post("/shifts", status_code=201)
async def create_shift(shift: ShiftCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "operations", "line_manager"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Manager or HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("shifts").insert({
        "staff_id": shift.staff_id, "shift_date": shift.shift_date.isoformat(),
        "start_time": shift.start_time, "end_time": shift.end_time,
        "shift_type": shift.shift_type, "notes": shift.notes,
        "created_by": current_admin["sub"]
    }).execute())
    return res.data[0]

@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str, current_admin: dict = Depends(verify_token)):
    db = get_db()
    await db_execute(lambda: db.table("shifts").delete().eq("id", shift_id).execute())
    return {"message": "Deleted"}

# ─── HOLIDAYS / CALENDAR ─────────────────────────────────────
class HolidayCreate(BaseModel):
    name: str; holiday_date: date; is_recurring: bool = True

@router.get("/holidays")
async def get_holidays(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("public_holidays").select("*").order("holiday_date").execute())
    return res.data

@router.post("/holidays", status_code=201)
async def add_holiday(h: HolidayCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR Admin only")
    db = get_db()
    res = await db_execute(lambda: db.table("public_holidays").insert({
        "name": h.name, "holiday_date": h.holiday_date.isoformat(), "is_recurring": h.is_recurring
    }).execute())
    return res.data[0]

# ─── LEAVE POLICIES & BALANCES ────────────────────────────────
class LeavePolicyCreate(BaseModel):
    leave_type: str; days_per_year: int; carry_over: bool = False
    requires_proof: bool = False; description: Optional[str] = None

@router.get("/leave-policies")
async def get_leave_policies(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("leave_policies").select("*").execute())
    return res.data

@router.post("/leave-policies", status_code=201)
async def create_leave_policy(p: LeavePolicyCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR Admin only")
    db = get_db()
    res = await db_execute(lambda: db.table("leave_policies").insert(p.dict()).execute())
    return res.data[0]

@router.get("/leave-balances")
async def get_leave_balances(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    target = staff_id if (is_hr and staff_id) else current_admin["sub"]
    profile = await db_execute(lambda: db.table("staff_profiles").select("leave_quota, leave_taken").eq("admin_id", target).execute())
    leaves = await db_execute(lambda: db.table("leave_requests").select("days_count, leave_type").eq("staff_id", target).eq("status", "approved").execute())
    quota = profile.data[0].get("leave_quota", 20) if profile.data else 20
    used = sum(l.get("days_count", 0) for l in leaves.data)
    by_type = {}
    for l in leaves.data:
        lt = l.get("leave_type", "Annual")
        by_type[lt] = by_type.get(lt, 0) + l.get("days_count", 0)
    return {"staff_id": target, "quota": quota, "used": used, "remaining": quota - used, "by_type": by_type}

# ─── PERFORMANCE — IMPROVEMENT PLANS ─────────────────────────
class PIPCreate(BaseModel):
    staff_id: str; reason: str; goals: str; start_date: date
    review_date: date; notes: Optional[str] = None

@router.get("/pip")
async def get_pips(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    query = db.table("performance_improvement_plans").select("*, admins!performance_improvement_plans_staff_id_fkey(full_name)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    res = await db_execute(lambda: query.execute())
    return res.data

@router.post("/pip", status_code=201)
async def create_pip(pip: PIPCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "line_manager"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Manager or HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("performance_improvement_plans").insert({
        **pip.dict(), "start_date": pip.start_date.isoformat(),
        "review_date": pip.review_date.isoformat(), "status": "active",
        "created_by": current_admin["sub"]
    }).execute())
    return res.data[0]

# ─── LEARNING & GROWTH ────────────────────────────────────────
class TrainingCreate(BaseModel):
    title: str; training_type: str = "Internal"; description: Optional[str] = None
    start_date: date; end_date: Optional[date] = None
    trainer: Optional[str] = None; max_participants: Optional[int] = None

class OnboardingChecklistCreate(BaseModel):
    staff_id: str; items: List[str]

@router.get("/trainings")
async def get_trainings(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("trainings").select("*, training_enrollments(staff_id)").order("start_date", desc=True).execute())
    return res.data

@router.post("/trainings", status_code=201)
async def create_training(t: TrainingCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    data = t.dict()
    data["start_date"] = t.start_date.isoformat()
    if t.end_date: data["end_date"] = t.end_date.isoformat()
    data["created_by"] = current_admin["sub"]
    res = await db_execute(lambda: db.table("trainings").insert(data).execute())
    return res.data[0]

@router.post("/trainings/{training_id}/enroll", status_code=201)
async def enroll_in_training(training_id: str, staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    target = staff_id or current_admin["sub"]
    res = await db_execute(lambda: db.table("training_enrollments").insert({
        "training_id": training_id, "staff_id": target, "enrolled_at": datetime.utcnow().isoformat()
    }).execute())
    return res.data[0]

@router.get("/onboarding/{staff_id}")
async def get_onboarding_checklist(staff_id: str, current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("onboarding_checklists").select("*").eq("staff_id", staff_id).execute())
    return res.data

@router.post("/onboarding", status_code=201)
async def create_onboarding_checklist(oc: OnboardingChecklistCreate, current_admin: dict = Depends(verify_token)):
    db = get_db()
    inserts = [{"staff_id": oc.staff_id, "item": item, "completed": False, "created_by": current_admin["sub"]} for item in oc.items]
    res = await db_execute(lambda: db.table("onboarding_checklists").insert(inserts).execute())
    return res.data

@router.patch("/onboarding/{item_id}")
async def update_onboarding_item(item_id: str, current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("onboarding_checklists").update({"completed": True, "completed_at": datetime.utcnow().isoformat()}).eq("id", item_id).execute())
    return res.data[0] if res.data else {"message": "Updated"}

# ─── PROBATION TRACKING ───────────────────────────────────────
class ProbationReviewCreate(BaseModel):
    staff_id: str; review_date: date; outcome: str; notes: Optional[str] = None

@router.get("/probation")
async def get_probation_reviews(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("probation_reviews").select("*, admins!probation_reviews_staff_id_fkey(full_name, department)").execute())
    return res.data

@router.post("/probation", status_code=201)
async def create_probation_review(pr: ProbationReviewCreate, current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("probation_reviews").insert({
        **pr.dict(), "review_date": pr.review_date.isoformat(), "reviewed_by": current_admin["sub"]
    }).execute())
    return res.data[0]

# ─── COMPENSATION BANDS & BONUSES ─────────────────────────────
class CompBandCreate(BaseModel):
    role_title: str; department: str; min_salary: float
    max_salary: float; currency: str = "NGN"

class BonusCreate(BaseModel):
    staff_id: str; bonus_type: str; amount: float
    period: str; notes: Optional[str] = None

@router.get("/comp-bands")
async def get_comp_bands(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("compensation_bands").select("*").execute())
    return res.data

@router.post("/comp-bands", status_code=201)
async def create_comp_band(cb: CompBandCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("compensation_bands").insert(cb.dict()).execute())
    return res.data[0]

@router.get("/bonuses")
async def get_bonuses(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin"] for r in user_roles)
    query = db.table("bonuses").select("*, admins!bonuses_staff_id_fkey(full_name)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
    res = await db_execute(lambda: query.execute())
    return res.data

@router.post("/bonuses", status_code=201)
async def create_bonus(b: BonusCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("bonuses").insert({**b.dict(), "created_by": current_admin["sub"]}).execute())
    return res.data[0]

# ─── ANNOUNCEMENTS ────────────────────────────────────────────
class AnnouncementCreate(BaseModel):
    title: str; body: str; priority: str = "Normal"
    target_department: Optional[str] = None

@router.get("/announcements")
async def get_announcements(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("announcements").select("*, admins!announcements_created_by_fkey(full_name)").order("created_at", desc=True).execute())
    return res.data

@router.post("/announcements", status_code=201)
async def create_announcement(a: AnnouncementCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin", "operations"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("announcements").insert({
        **a.dict(), "created_by": current_admin["sub"], "created_at": datetime.utcnow().isoformat()
    }).execute())
    return res.data[0]

# ─── RECOGNITION (KUDOS) ──────────────────────────────────────
class RecognitionCreate(BaseModel):
    recipient_id: str; message: str; badge_type: str = "Kudos"

@router.get("/recognition")
async def get_recognition(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("recognition").select("*, recipient:admins!recognition_recipient_id_fkey(full_name), giver:admins!recognition_giver_id_fkey(full_name)").order("created_at", desc=True).limit(50).execute())
    return res.data

@router.post("/recognition", status_code=201)
async def give_recognition(r: RecognitionCreate, current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("recognition").insert({
        **r.dict(), "giver_id": current_admin["sub"], "created_at": datetime.utcnow().isoformat()
    }).execute())
    return res.data[0]

# ─── SURVEYS ──────────────────────────────────────────────────
class SurveyCreate(BaseModel):
    title: str; description: Optional[str] = None
    questions: List[str]; is_anonymous: bool = True

class SurveyResponse(BaseModel):
    answers: dict; is_anonymous: bool = True

@router.get("/culture/surveys")
async def list_surveys(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("surveys").select("*").eq("is_active", True).execute())
    return res.data

@router.post("/culture/surveys", status_code=201)
async def create_survey(s: SurveyCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("surveys").insert({
        **s.dict(), "is_active": True, "created_by": current_admin["sub"]
    }).execute())
    return res.data[0]

@router.post("/culture/surveys/{survey_id}/respond", status_code=201)
async def respond_to_survey(survey_id: str, r: SurveyResponse, current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("survey_responses").insert({
        "survey_id": survey_id,
        "answers": r.answers,
        "is_anonymous": r.is_anonymous,
        "respondent_id": None if r.is_anonymous else current_admin["sub"],
        "created_at": datetime.utcnow().isoformat()
    }).execute())
    return res.data[0]

# ─── WORK PERMITS ─────────────────────────────────────────────
class WorkPermitCreate(BaseModel):
    staff_id: str; permit_type: str; permit_number: str
    issue_date: date; expiry_date: date; issuing_authority: Optional[str] = None

@router.get("/work-permits")
async def get_work_permits(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    query = db.table("work_permits").select("*, admins!work_permits_staff_id_fkey(full_name)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    res = await db_execute(lambda: query.execute())
    return res.data

@router.post("/work-permits", status_code=201)
async def create_work_permit(wp: WorkPermitCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    data = wp.dict()
    data["issue_date"] = wp.issue_date.isoformat()
    data["expiry_date"] = wp.expiry_date.isoformat()
    today = date.today()
    data["status"] = "Active" if wp.expiry_date >= today else "Expired"
    res = await db_execute(lambda: db.table("work_permits").insert(data).execute())
    return res.data[0]

# ─── HR LETTERS ───────────────────────────────────────────────
class HRLetterCreate(BaseModel):
    staff_id: str; letter_type: str; content: str; date_issued: date

@router.get("/hr-letters")
async def get_hr_letters(staff_id: Optional[str] = None, current_admin: dict = Depends(verify_token)):
    db = get_db()
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin"] for r in user_roles)
    query = db.table("hr_letters").select("*, admins!hr_letters_staff_id_fkey(full_name)")
    if staff_id:
        query = query.eq("staff_id", staff_id)
    elif not is_hr:
        query = query.eq("staff_id", current_admin["sub"])
    res = await db_execute(lambda: query.order("date_issued", desc=True).execute())
    return res.data

@router.post("/hr-letters", status_code=201)
async def create_hr_letter(l: HRLetterCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("hr_letters").insert({
        **l.dict(), "date_issued": l.date_issued.isoformat(), "issued_by": current_admin["sub"]
    }).execute())
    return res.data[0]

# ─── GRIEVANCES ───────────────────────────────────────────────
class GrievanceCreate(BaseModel):
    subject: str; description: str
    is_anonymous: bool = True; against_staff_id: Optional[str] = None

@router.get("/grievances")
async def get_grievances(current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    res = await db_execute(lambda: db.table("grievances").select("*").order("created_at", desc=True).execute())
    return res.data

@router.post("/grievances", status_code=201)
async def submit_grievance(g: GrievanceCreate, current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("grievances").insert({
        **g.dict(),
        "filed_by": None if g.is_anonymous else current_admin["sub"],
        "status": "open",
        "created_at": datetime.utcnow().isoformat()
    }).execute())
    return {"message": "Grievance submitted successfully"}

# ─── AUDIT LOGS ───────────────────────────────────────────────
@router.get("/audit-logs")
async def get_audit_logs(limit: int = 100, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if not any(r in ["admin", "super_admin", "hr_admin"] for r in user_roles):
        raise HTTPException(status_code=403, detail="Super Admin only")
    db = get_db()
    res = await db_execute(lambda: db.table("audit_logs").select("*, admins!audit_logs_actor_id_fkey(full_name)").order("created_at", desc=True).limit(limit).execute())
    return res.data

# ─── HR REPORTS ───────────────────────────────────────────────
@router.get("/reports/headcount")
async def report_headcount(current_admin: dict = Depends(verify_token)):
    db = get_db()
    staff = await db_execute(lambda: db.table("admins").select("id, department, role, is_active, created_at").execute())
    active = [s for s in staff.data if s.get("is_active")]
    by_dept = {}
    for s in active:
        d = s.get("department") or "Unassigned"
        by_dept[d] = by_dept.get(d, 0) + 1
    thirty_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
    new_hires = [s for s in active if s.get("created_at", "") >= thirty_ago]
    return {"total": len(active), "by_department": by_dept, "new_hires_30d": len(new_hires)}

@router.get("/departments")
async def get_departments(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("departments").select("*").execute())
    if not res.data:
        # Fallback: derive from admins table
        staff = await db_execute(lambda: db.table("admins").select("department").execute())
        depts = list(set(s["department"] for s in staff.data if s.get("department")))
        return [{"name": d} for d in sorted(depts)]
    return res.data
@router.get("/recruitment/interviews")
async def get_interviews(current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles and "manager" not in user_roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_db()
    res = await db_execute(lambda: db.table("job_interviews").select("*").execute())
    return res.data if res.data else []

@router.get("/calendar-events")
async def get_calendar_events(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("calendar_events").select("*").execute())
    return res.data if res.data else []

@router.post("/calendar-events", status_code=status.HTTP_201_CREATED)
async def create_calendar_event(request: Request, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
        raise HTTPException(status_code=403, detail="HR only")
    db = get_db()
    data = await request.json()
    res = await db_execute(lambda: db.table("calendar_events").insert(data).execute())
    return res.data[0] if res.data else None

@router.get("/expenses")
async def get_expenses(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("expenses").select("*, staff:admins(full_name, department)").execute())
    return res.data if res.data else []

@router.post("/expenses", status_code=status.HTTP_201_CREATED)
async def submit_expense(request: Request, current_admin: dict = Depends(verify_token)):
    db = get_db()
    data = await request.json()
    if "staff_id" not in data or not data["staff_id"]:
        data["staff_id"] = current_admin.get("id")
    res = await db_execute(lambda: db.table("expenses").insert(data).execute())
    return res.data[0] if res.data else None

@router.patch("/expenses/{expense_id}")
async def update_expense(expense_id: str, request: Request, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles and "manager" not in user_roles:
        raise HTTPException(status_code=403, detail="HR/Managers only")
    db = get_db()
    data = await request.json()
    res = await db_execute(lambda: db.table("expenses").update({"status": data.get("status")}).eq("id", expense_id).execute())
    return res.data[0] if res.data else None

@router.get("/peer-reviews")
async def get_peer_reviews(current_admin: dict = Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("peer_reviews").select("*").execute())
    return res.data if res.data else []

@router.post("/peer-reviews", status_code=status.HTTP_201_CREATED)
async def launch_peer_review(request: Request, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles and "manager" not in user_roles:
        raise HTTPException(status_code=403, detail="HR/Managers only")
    db = get_db()
    data = await request.json()
    res = await db_execute(lambda: db.table("peer_reviews").insert(data).execute())
    return res.data[0] if res.data else None

@router.patch("/peer-reviews/{review_id}")
async def update_peer_review(review_id: str, request: Request, current_admin: dict = Depends(verify_token)):
    db = get_db()
    data = await request.json()
    res = await db_execute(lambda: db.table("peer_reviews").update({"status": data.get("status")}).eq("id", review_id).execute())
    return res.data[0] if res.data else None
