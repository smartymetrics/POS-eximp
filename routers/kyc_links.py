from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from database import get_db, db_execute
from routers.auth import verify_token
import secrets
from datetime import datetime

router = APIRouter(prefix="/api/kyc-links")

@router.get("/my")
async def get_my_kyc_link(request: Request, current_admin=Depends(verify_token)):
    """Returns the sales rep's active unique KYC link."""
    db = get_db()
    rep_id = current_admin.get("sub")
    res = await db_execute(lambda: db.table("kyc_links")
        .select("*")
        .eq("rep_id", rep_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute())
    
    if not res.data:
        # Auto-generate if not exists
        token = secrets.token_urlsafe(16)
        payload = {
            "rep_id": rep_id,
            "token": token,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        ins_res = await db_execute(lambda: db.table("kyc_links").insert(payload).execute())
        token_val = ins_res.data[0]["token"] if ins_res.data else token
    else:
        token_val = res.data[0]["token"]
        
    base_url = str(request.base_url).rstrip("/")
    return {
        "status": "success",
        "token": token_val,
        "url": f"{base_url}/kyc?rep={token_val}"
    }

@router.post("/generate")
async def generate_kyc_link(request: Request, current_admin=Depends(verify_token)):
    """Generates a new secure KYC link token for the rep."""
    db = get_db()
    rep_id = current_admin.get("sub")
    token = secrets.token_urlsafe(16)
    
    # Deactivate existing links
    await db_execute(lambda: db.table("kyc_links").update({"is_active": False}).eq("rep_id", rep_id).execute())
    
    payload = {
        "rep_id": rep_id,
        "token": token,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    res = await db_execute(lambda: db.table("kyc_links").insert(payload).execute())
    base_url = str(request.base_url).rstrip("/")
    return {
        "status": "success",
        "token": token,
        "url": f"{base_url}/kyc?rep={token}"
    }

@router.get("/resolve/{token}")
async def resolve_kyc_token(token: str):
    """Resolves a KYC link token to the originating sales rep."""
    db = get_db()
    res = await db_execute(lambda: db.table("kyc_links")
        .select("*, admins(id, full_name, email)")
        .eq("token", token)
        .eq("is_active", True)
        .limit(1)
        .execute())
        
    if not res.data:
        raise HTTPException(status_code=404, detail="Invalid or expired KYC link")
        
    return {
        "status": "success",
        "rep_id": res.data[0]["rep_id"],
        "rep": res.data[0].get("admins") or {}
    }

