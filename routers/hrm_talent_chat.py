import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from database import get_db, db_execute
from routers.auth import require_roles

logger = logging.getLogger(__name__)
router = APIRouter()

class TalentChatMessageCreate(BaseModel):
    talent_id: str
    message: str
    sender_type: Optional[str] = "staff"

@router.get("/conversations")
async def list_conversations(
    current_user: dict = Depends(require_roles(["super_admin", "admin", "hr"])),
    db=Depends(get_db)
):
    """List recent HRM talent chat conversations."""
    try:
        res = await db_execute(lambda: db.table("hrm_talent_messages").select("talent_id").execute())
        talent_ids = list(set(r["talent_id"] for r in (res.data or []) if "talent_id" in r))
        return {"conversations": talent_ids}
    except Exception as e:
        logger.error(f"Error listing talent conversations: {e}")
        return {"conversations": []}

@router.get("/messages/{talent_id}")
async def get_messages(
    talent_id: str,
    current_user: dict = Depends(require_roles(["super_admin", "admin", "hr"])),
    db=Depends(get_db)
):
    """Retrieve chat history for a specific talent record."""
    try:
        res = await db_execute(
            lambda: db.table("hrm_talent_messages")
            .select("*")
            .eq("talent_id", talent_id)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error(f"Error fetching talent messages for {talent_id}: {e}")
        return []

@router.post("/messages")
async def send_message(
    payload: TalentChatMessageCreate,
    current_user: dict = Depends(require_roles(["super_admin", "admin", "hr"])),
    db=Depends(get_db)
):
    """Send a message to a talent profile."""
    try:
        data = {
            "talent_id": payload.talent_id,
            "message": payload.message,
            "sender_type": payload.sender_type,
            "sender_id": current_user.get("sub")
        }
        res = await db_execute(lambda: db.table("hrm_talent_messages").insert(data).execute())
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to save message")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending talent message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

