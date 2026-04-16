import math
import os
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from database import get_db, db_execute
from routers.auth import verify_token

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

class StaffAssetCreate(BaseModel):
    staff_id: str
    asset_name: str
    serial_number: Optional[str] = None
    condition: str = "Good"
    assigned_at: date = date.today()

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
    
    # Query admins joined with staff_profiles
    res = await db_execute(lambda: db.table("admins").select(
        "id, full_name, email, role, primary_role, department, line_manager_id, created_at, is_active, staff_profiles(*)"
    ).execute())
    
    return res.data

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
    profile = await db_execute(lambda: db.table("admins").select("*, staff_profiles(*), staff_documents(*), staff_qualifications(*), staff_assets(*)").eq("id", staff_id).execute())
    
    return profile.data[0] if profile.data else None

@router.patch("/profile/{staff_id}")
async def update_staff_profile(staff_id: str, update: StaffProfileUpdate, current_admin: dict = Depends(verify_token)):
    """Update detailed staff profile. HR admins may edit all fields; staff may self-edit a restricted set."""
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    is_self = current_admin.get("sub") == staff_id
    if not (is_hr or is_self):
         raise HTTPException(status_code=403, detail="Only HR or the profile owner can update this record")

    db = get_db()
    update_data = update.dict(exclude_unset=True)

    admin_updates = {}
    profile_updates = {}

    if is_hr:
        # HR can update administrative fields as well as profile data.
        if update.department: admin_updates["department"] = update.department
        if update.line_manager_id: admin_updates["line_manager_id"] = update.line_manager_id
        if update.job_title: admin_updates["job_title"] = update.job_title
        if update.exit_date is not None:
            admin_updates["is_active"] = False  # Auto-deactivate if exit date set

        profile_updates = update.dict(exclude={"department", "line_manager_id", "job_title"}, exclude_unset=True)
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

    if update_data.get("template_id") is not None:
        update_data["kpi_template_id"] = update_data.pop("template_id")

    if update_data.get("staff_id") and update_data.get("department"):
        raise HTTPException(status_code=400, detail="Provide either staff_id or department, not both")

    res = await db_execute(lambda: db.table("staff_goals").update(update_data).eq("id", goal_id).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to update goal")
    return res.data[0]

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

@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def assign_staff_asset(asset: StaffAssetCreate, current_admin: dict = Depends(verify_token)):
    """Assign a company asset to a staff member. HR only."""
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("staff_assets").insert({
        "staff_id": asset.staff_id,
        "asset_name": asset.asset_name,
        "serial_number": asset.serial_number,
        "condition": asset.condition,
        "assigned_at": asset.assigned_at.isoformat()
    }).execute())
    
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
        
        # Calculate simple tax (e.g. 10%)
        tax = base * 0.1
        net = base - tax
        
        payroll_inserts.append({
            "staff_id": s["id"],
            "period_start": month_start,
            "period_end": month_end,
            "gross_pay": base,
            "tax": tax,
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

class IncidentCreate(BaseModel):
    staff_id: str
    incident_type: str
    severity: str
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
                    
            # Check Anniversaries (Next 30 days)
            if p.get("date_joined"):
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

class AttendanceCheckOut(BaseModel):
    """Payload sent on check-out."""
    latitude:          Optional[float] = None
    longitude:         Optional[float] = None
    location_status:   str = "unavailable"
    device_type:       Optional[str] = None


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
        if distance and distance > threshold:
            is_suspicious = True
            reasons.append(f"Location Outside Geofence ({int(distance)}m away)")
    else:
        is_suspicious = True
        reasons.append("GPS Coordinates Missing")

    # Simple device check: if it's a mobile device without GPS, that's often suspicious
    if payload.device_type == "Mobile" and not payload.latitude:
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

    updates = {
        "check_out":              now,
        "check_out_latitude":     payload.latitude,
        "check_out_longitude":    payload.longitude,
        "check_out_ip_address":   ip,
        "check_out_device_type":  payload.device_type,
        "check_out_user_agent":   ua,
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

