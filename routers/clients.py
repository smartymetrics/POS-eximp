from fastapi import APIRouter, HTTPException, Depends
from models import ClientCreate, ClientUpdate
from database import get_db
from routers.auth import verify_token

router = APIRouter()


@router.get("/")
async def list_clients(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("clients").select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/{client_id}")
async def get_client(client_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("clients").select("*").eq("id", client_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")
    return result.data[0]


@router.get("/{client_id}/invoices")
async def get_client_invoices(client_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("invoices")\
        .select("*, payments(*)")\
        .eq("client_id", client_id)\
        .order("invoice_date", desc=True)\
        .execute()
    return result.data


@router.post("/")
async def create_client(data: ClientCreate, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("clients").insert({
        **data.dict(),
        "added_by": current_admin["sub"]
    }).execute()
    return {"message": "Client created", "client": result.data[0]}


@router.put("/{client_id}")
async def update_client(client_id: str, data: ClientUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    result = db.table("clients").update(update_data).eq("id", client_id).execute()
    return {"message": "Client updated", "client": result.data[0]}
