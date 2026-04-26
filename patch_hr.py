import os

content = """
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
"""

with open(r"routers\hr.py", "a", encoding="utf-8") as f:
    f.write(content)
