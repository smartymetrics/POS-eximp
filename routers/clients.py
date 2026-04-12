from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from database import get_db, db_execute
from routers.auth import verify_token
from routers.analytics import log_activity
from models import ClientCreate, ClientUpdate
from marketing_logic import sync_client_to_marketing

router = APIRouter()


@router.get("/")
async def list_clients(
    limit: int = 100,
    offset: int = 0,
    current_admin=Depends(verify_token)
):
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    
    # Privileged check
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])
    
    query = db.table("clients").select("*")
    
    if not is_privileged:
        # Restricted users see only their assigned clients
        query = query.eq("assigned_rep_id", admin_id)

    result = await db_execute(lambda: query.order("created_at", desc=True).range(offset, offset + limit - 1).execute())
    return result.data


@router.get("/{client_id}")
async def get_client(client_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
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
async def create_client(
    data: ClientCreate, 
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()
    client_data = jsonable_encoder(data)
    client_data["added_by"] = current_admin["sub"]
    
    result = await db_execute(lambda: db.table("clients").insert(client_data).execute())
    
    background_tasks.add_task(
        log_activity,
        "client_created",
        f"New client registered: {data.full_name}",
        current_admin["sub"],
        client_id=result.data[0]["id"]
    )

    # Sync to Marketing
    await sync_client_to_marketing(result.data[0])

    return {"message": "Client created", "client": result.data[0]}


@router.put("/{client_id}")
async def update_client(client_id: str, data: ClientUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    role = current_admin.get("role")
    update_data = jsonable_encoder(data, exclude_none=True)
    
    if not update_data:
        return {"message": "No changes applied"}

    # Admin-only fields
    admin_only_fields = ["email", "nin", "id_number", "passport_photo_url", "id_document_url"]
    
    if role != "admin":
        for field in admin_only_fields:
            if field in update_data:
                raise HTTPException(status_code=403, detail=f"Permission denied to edit {field}")

    result = await db_execute(lambda: db.table("clients").update(update_data).eq("id", client_id).execute())
    if not result.data:
         raise HTTPException(status_code=404, detail="Client not found")
         
    log_activity(
        "client_updated",
        f"Client {result.data[0]['full_name']} updated by {role}",
        current_admin["sub"],
        client_id=client_id
    )
    
    # Sync to Marketing
    await sync_client_to_marketing(result.data[0])

    return {"message": "Client updated", "client": result.data[0]}
