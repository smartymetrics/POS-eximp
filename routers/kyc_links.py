from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from database import get_db, db_execute
from routers.auth import verify_token
import uuid, secrets, datetime

router = APIRouter()

@router.post("/api/kyc-links/generate")
async def generate_kyc_link(request: Request, current_admin=Depends(verify_token)):
    """
    Generate a secure KYC link token for the current rep (admin).
    Returns a unique URL-safe token and stores it in the kyc_links table.
    """
    db = get_db()
    rep_id = current_admin["sub"]
    label = (await request.json()).get("label")
    # Only one active link per rep for now
    token = secrets.token_urlsafe(16)
    await db_execute(lambda: db.table("kyc_links").upsert({
        "rep_id": rep_id,
        "token": token,
        "label": label,
        "is_active": True,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat()
    }, on_conflict=["rep_id"]).execute())
    return {"status": "success", "token": token, "url": f"/kyc?t={token}"}

@router.get("/api/kyc-links/my")
async def get_my_kyc_link(current_admin=Depends(verify_token)):
    db = get_db()
    rep_id = current_admin["sub"]
    res = await db_execute(lambda: db.table("kyc_links").select("token, label, is_active, created_at").eq("rep_id", rep_id).eq("is_active", True).limit(1).execute())
    if not res.data:
        raise HTTPException(404, "No active KYC link found")
    data = res.data[0]
    return {"status": "success", **data, "url": f"/kyc?t={data['token']}"}

@router.get("/api/kyc-links/resolve/{token}")
async def resolve_kyc_token(token: str):
    db = get_db()
    res = await db_execute(lambda: db.table("kyc_links").select("rep_id").eq("token", token).eq("is_active", True).limit(1).execute())
    if not res.data:
        raise HTTPException(404, "Invalid or expired KYC link")
    return {"status": "success", "rep_id": res.data[0]["rep_id"]}
