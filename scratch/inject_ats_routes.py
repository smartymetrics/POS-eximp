
import os

file_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\routers\hr.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

ats_routes = """
# ─── RECRUITMENT / ATS ────────────────────────────────────────────────────────

class JobRequisitionCreate(BaseModel):
    title: str
    department: str
    employment_type: str
    location: Optional[str] = None
    status: str = "Open"
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_range: Optional[str] = None

class JobApplicationCreate(BaseModel):
    job_id: str
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
async def get_jobs(current_admin: dict = Depends(verify_token)):
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
"""

if "RECRUITMENT / ATS" not in content:
    content += "\n" + ats_routes + "\n"

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected ATS routes")
