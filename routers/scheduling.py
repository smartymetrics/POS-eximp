from fastapi import APIRouter, HTTPException, Depends, Request
from database import get_db
from routers.auth import verify_token
from datetime import datetime, timedelta
import pytz

router = APIRouter()

# Lagos timezone
LAGOS_TZ = pytz.timezone("Africa/Lagos")

@router.get("/slots")
async def get_available_slots(date_str: str):
    """
    Get available 60-minute slots for a given date.
    date_str format: YYYY-MM-DD
    """
    db = get_db()
    
    try:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if query_date < datetime.now(LAGOS_TZ).date():
        return []

    # Operating hours: 09:00 to 17:00 (last slot at 16:00)
    slots = []
    for hour in range(9, 17):
        slot_time = datetime.combine(query_date, datetime.min.time().replace(hour=hour))
        slots.append(slot_time.isoformat())

    # Get existing appointments for this date
    existing = db.table("appointments")\
        .select("scheduled_at")\
        .gte("scheduled_at", f"{date_str}T00:00:00")\
        .lte("scheduled_at", f"{date_str}T23:59:59")\
        .neq("status", "cancelled")\
        .execute().data or []

    booked_times = [datetime.fromisoformat(a["scheduled_at"]).replace(tzinfo=None).isoformat() for a in existing]
    
    available_slots = [s for s in slots if s not in booked_times]
    
    return available_slots

@router.post("/book")
async def book_appointment(request: Request):
    """
    Public-facing booking endpoint.
    """
    db = get_db()
    data = await request.json()
    
    # Validation
    required = ["scheduled_at", "contact_name", "contact_email", "contact_phone"]
    for field in required:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # Check for conflicts
    scheduled_at = data.get("scheduled_at")
    conflict = db.table("appointments")\
        .select("id")\
        .eq("scheduled_at", scheduled_at)\
        .neq("status", "cancelled")\
        .execute().data
    
    if conflict:
        raise HTTPException(status_code=400, detail="This slot is no longer available.")

    appointment_payload = {
        "scheduled_at": scheduled_at,
        "contact_name": data.get("contact_name"),
        "contact_email": data.get("contact_email"),
        "contact_phone": data.get("contact_phone"),
        "property_id": data.get("property_id"),
        "appointment_type": data.get("appointment_type", "inspection"),
        "notes": data.get("notes"),
        "status": "scheduled",
        "created_at": datetime.now(LAGOS_TZ).isoformat()
    }

    res = await db_execute(lambda: db.table("appointments").insert(appointment_payload).execute())
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to book appointment")

    # TODO: Trigger Email Confirmation via background task
    
    return {"message": "Success", "appointment_id": res.data[0]["id"]}

@router.get("/my-appointments")
async def list_admin_appointments(current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("appointments")\
        .select("*, properties(name)")\
        .order("scheduled_at", desc=False)\
        .execute()
    return res.data
