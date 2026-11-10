import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from database import get_db, db_execute
from routers.auth import require_roles

logger = logging.getLogger(__name__)
router = APIRouter()

class BiodataSubmissionCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    date_of_birth: Optional[str] = None
    state_of_origin: Optional[str] = None
    lga: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    passport_photo_url: Optional[str] = None
    signature_url: Optional[str] = None
    notes: Optional[str] = None

class BiodataStatusUpdate(BaseModel):
    status: str
    review_notes: Optional[str] = None

@router.get("/")
async def list_biodata_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(require_roles(["super_admin", "admin", "hr", "operations"])),
    db=Depends(get_db)
):
    """List staff biodata submissions with optional status filter."""
    try:
        query = db.table("biodata_submissions").select("*").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        res = await db_execute(lambda: query.execute())
        return res.data or []
    except Exception as e:
        logger.error(f"Error listing biodata submissions: {e}")
        return []

@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_biodata(
    payload: BiodataSubmissionCreate,
    db=Depends(get_db)
):
    """Submit a biodata form."""
    try:
        data = payload.dict(exclude_none=True)
        data["status"] = "pending"
        res = await db_execute(lambda: db.table("biodata_submissions").insert(data).execute())
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to save biodata submission.")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating biodata submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{submission_id}")
async def get_biodata_submission(
    submission_id: str,
    current_user: dict = Depends(require_roles(["super_admin", "admin", "hr", "operations"])),
    db=Depends(get_db)
):
    """Retrieve details for a single biodata submission."""
    try:
        res = await db_execute(lambda: db.table("biodata_submissions").select("*").eq("id", submission_id).single().execute())
        if not res.data:
            raise HTTPException(status_code=404, detail="Biodata submission not found")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching biodata submission {submission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{submission_id}/status")
async def update_biodata_status(
    submission_id: str,
    payload: BiodataStatusUpdate,
    current_user: dict = Depends(require_roles(["super_admin", "admin", "hr"])),
    db=Depends(get_db)
):
    """Update review status of a biodata submission."""
    try:
        update_data = {
            "status": payload.status,
            "reviewed_by": current_user.get("sub"),
            "review_notes": payload.review_notes
        }
        res = await db_execute(lambda: db.table("biodata_submissions").update(update_data).eq("id", submission_id).execute())
        if not res.data:
            raise HTTPException(status_code=404, detail="Submission not found or update failed")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating biodata status for {submission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

