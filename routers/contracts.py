from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from database import get_db, SUPABASE_URL
from models import CompanySignatureUpload, ExtendSigningLink, WitnessSignatureSubmit, ClientContractSignatureSubmit, WitnessRemovalRequest
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime, timedelta
import secrets
import os
import base64
import io
from PIL import Image

router = APIRouter()


def _upload_signature_to_storage(db, invoice_id: str, witness_number: int, signature_base64: str) -> str:
    if not signature_base64:
        return signature_base64
    signature_value = signature_base64.strip()
    if signature_value.startswith("http://") or signature_value.startswith("https://"):
        return signature_value

    try:
        if "," in signature_value:
            _, encoded = signature_value.split(",", 1)
        else:
            encoded = signature_value

        img_data = base64.b64decode(encoded)
        with Image.open(io.BytesIO(img_data)) as img:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            out_buf = io.BytesIO()
            img.save(out_buf, format="PNG")
            img_data = out_buf.getvalue()

        file_path = f"witnesses/{invoice_id}/witness{witness_number}.png"
        try:
            db.storage.from_("signatures").remove([file_path])
        except Exception:
            pass
        db.storage.from_("signatures").upload(
            path=file_path,
            file=img_data,
            file_options={"content-type": "image/png"}
        )
        return f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
    except Exception as e:
        print(f"WARNING: Witness signature upload failed: {e}")
        return signature_base64


def _upload_client_signature(db, invoice_id: str, signature_base64: str) -> str:
    if not signature_base64:
        return signature_base64
    signature_value = signature_base64.strip()
    if signature_value.startswith("http://") or signature_value.startswith("https://"):
        return signature_value

    try:
        if "," in signature_value:
            _, encoded = signature_value.split(",", 1)
        else:
            encoded = signature_value

        img_data = base64.b64decode(encoded)
        with Image.open(io.BytesIO(img_data)) as img:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            out_buf = io.BytesIO()
            img.save(out_buf, format="PNG")
            img_data = out_buf.getvalue()

        file_path = f"contracts/{invoice_id}/client.png"
        try:
            db.storage.from_("signatures").remove([file_path])
        except Exception:
            pass
        db.storage.from_("signatures").upload(
            path=file_path,
            file=img_data,
            file_options={"content-type": "image/png"}
        )
        return f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
    except Exception as e:
        print(f"WARNING: Client signature upload failed: {e}")
        return signature_base64


def _delete_witness_signature_from_storage(db, signature_url: str):
    if not signature_url or not signature_url.startswith(f"{SUPABASE_URL}/storage/v1/object/public/"):
        return
    file_path = signature_url.replace(f"{SUPABASE_URL}/storage/v1/object/public/", "")
    try:
        db.storage.from_("signatures").remove([file_path])
    except Exception:
        pass


async def _create_contract_session(invoice_id: str, current_admin: dict, background_tasks: BackgroundTasks):
    db = get_db()

    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]

    existing = db.table("contract_signing_sessions")\
        .select("id, token, status, expires_at")\
        .eq("invoice_id", invoice_id)\
        .neq("status", "expired")\
        .order("created_at", desc=True)\
        .execute()

    if existing.data:
        if any(s["status"] == "completed" for s in existing.data):
            raise HTTPException(status_code=400, detail="Contract for this invoice is already fully signed")
        return existing.data[0]

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)

    session = db.table("contract_signing_sessions").insert({
        "invoice_id": invoice_id,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "status": "pending",
        "created_by": current_admin["sub"]
    }).execute().data[0]

    from email_service import send_signing_link_email
    background_tasks.add_task(send_signing_link_email, invoice, invoice["clients"], token, expires_at)

    await log_activity(
        "contract_initiated",
        f"Contract signing initiated for {invoice['invoice_number']}. Signing link sent to client.",
        current_admin["sub"],
        client_id=invoice["client_id"],
        invoice_id=invoice_id
    )

    return session

@router.post("/{invoice_id}/initiate")
async def initiate_contract_signing(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Check role
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Check if company signatures are set
    sig_res = db.table("company_signatures").select("id, role").eq("is_active", True).execute()
    roles_set = [s["role"] for s in sig_res.data]
    if "director" not in roles_set or "secretary" not in roles_set:
        raise HTTPException(status_code=400, detail="Company signatures (Director/Secretary) must be uploaded before initiating contracts.")

    # 1. Fetch Invoice
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    
    # 2. Prevent duplicate active sessions
    existing = db.table("contract_signing_sessions").select("id, status").eq("invoice_id", invoice_id).neq("status", "expired").execute()
    if existing.data:
        # If it's already completed, don't restart
        if any(s["status"] == "completed" for s in existing.data):
             raise HTTPException(status_code=400, detail="Contract for this invoice is already fully signed")
        # Else, we could expire the old one and start new, but for now let's just return it
        return {"message": "Session already exists", "token": existing.data[0].get("token")}

    # 3. Create Session
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)
    
    session = db.table("contract_signing_sessions").insert({
        "invoice_id": invoice_id,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "status": "pending",
        "created_by": current_admin["sub"]
    }).execute().data[0]
    
    # 4. Generate DRAFT PDF & Log it
    from pdf_service import generate_contract_pdf
    # draft_pdf = await generate_contract_pdf(invoice, invoice["clients"], is_draft=True)
    
    # 5. Email Client with link
    from email_service import send_signing_link_email
    background_tasks.add_task(send_signing_link_email, invoice, invoice["clients"], token, expires_at)
    
    # 6. LOG ACTIVITY
    await log_activity(
        "contract_initiated",
        f"Contract signing initiated for {invoice['invoice_number']}. Signing link sent to client.",
        current_admin["sub"],
        client_id=invoice["client_id"],
        invoice_id=invoice_id
    )
    
    return {"message": "Contract signing initiated", "token": token, "expires_at": expires_at}

@router.get("/{invoice_id}/status")
async def get_contract_status(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .execute()
    
    if not res.data:
         raise HTTPException(status_code=404, detail="No contract session found")

    session = res.data[0]
    return {
        "id": session["id"],
        "invoice_id": session["invoice_id"],
        "token": session["token"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        "created_at": session.get("created_at"),
        "witness_signatures": session.get("witness_signatures", []),
        "is_executed": session["status"] == "completed"
    }

@router.get("/session/{invoice_id}")
async def get_contract_session(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="No contract session found")

    session = res.data[0]
    return {
        "id": session["id"],
        "invoice_id": session["invoice_id"],
        "token": session["token"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        "created_at": session.get("created_at"),
        "witness_signatures": session.get("witness_signatures", []),
        "is_executed": session["status"] == "completed"
    }

@router.post("/session/{invoice_id}")
async def create_contract_session(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    sig_res = get_db().table("company_signatures").select("id, role").eq("is_active", True).execute()
    roles_set = [s["role"] for s in sig_res.data]
    if "director" not in roles_set or "secretary" not in roles_set:
        raise HTTPException(status_code=400, detail="Company signatures (Director/Secretary) must be uploaded before initiating contracts.")

    session = await _create_contract_session(invoice_id, current_admin, background_tasks)
    return {"message": "Contract signing initiated", "token": session["token"], "expires_at": session["expires_at"]}

@router.post("/resend/{invoice_id}")
async def resend_contract_link(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    session_res = db.table("contract_signing_sessions")\
        .select("*, invoices(*, clients(*))")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    if not session_res.data:
        raise HTTPException(status_code=404, detail="No active signing session found")

    session = session_res.data[0]
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="The contract is already fully signed")

    expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
    if expires_at < datetime.now().astimezone():
        raise HTTPException(status_code=400, detail="Signing session has expired; create a new one")

    invoice = session["invoices"]
    client = invoice["clients"]
    from email_service import send_signing_link_email
    background_tasks.add_task(send_signing_link_email, invoice, client, session["token"], expires_at)
    return {"message": "Signing link resent"}

@router.post("/execute/{invoice_id}")
async def execute_final_contract(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    if not session_res.data:
        raise HTTPException(status_code=404, detail="No signing session found")

    session = session_res.data[0]
    witnesses = session.get("witness_signatures", []) or []
    if len(witnesses) < 2:
        raise HTTPException(status_code=400, detail="At least two witnesses must sign before executing the contract")

    if session["status"] != "completed":
        db.table("contract_signing_sessions").update({"status": "completed"}).eq("id", session["id"]).execute()

    from pdf_service import generate_contract_pdf
    pdf_content = generate_contract_pdf(invoice, client, witnesses, is_draft=False)

    from email_service import send_executed_contract_email
    background_tasks.add_task(send_executed_contract_email, invoice, client, pdf_content)

    db.table("contract_documents").insert({
        "invoice_id": invoice_id,
        "session_id": session["id"],
        "document_type": "executed",
        "generated_by": current_admin["sub"],
        "emailed_to": client.get("email")
    }).execute()

    await log_activity(
        "contract_executed",
        f"Final executed contract generated for {invoice['invoice_number']}",
        current_admin["sub"],
        invoice_id=invoice_id,
        client_id=client.get("id")
    )

    return {"message": "Final contract executed and emailed"}

def _resolve_admin_token(token: str | None = None, authorization: str | None = Header(None)):
    if authorization:
        try:
            scheme, creds = authorization.split()
            if scheme.lower() == "bearer":
                return verify_token(HTTPAuthorizationCredentials(scheme=scheme, credentials=creds))
        except Exception:
            pass
    if token:
        return verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    raise HTTPException(status_code=401, detail="Not authenticated")

@router.get("/pdf/draft/{invoice_id}")
async def get_draft_contract_pdf(invoice_id: str, token: str | None = None, current_admin=Depends(_resolve_admin_token)):
    db = get_db()
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    witnesses = session_res.data[0].get("witness_signatures", []) if session_res.data else []

    from pdf_service import generate_contract_pdf
    pdf_bytes = generate_contract_pdf(invoice, client, witnesses, is_draft=True)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=contract-draft-{invoice_id}.pdf"})

@router.get("/pdf/final/{invoice_id}")
async def get_final_contract_pdf(invoice_id: str, token: str | None = None, current_admin=Depends(_resolve_admin_token)):
    db = get_db()
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    witnesses = session_res.data[0].get("witness_signatures", []) if session_res.data else []

    from pdf_service import generate_contract_pdf
    pdf_bytes = generate_contract_pdf(invoice, client, witnesses, is_draft=False)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=contract-final-{invoice_id}.pdf"})

@router.post("/{invoice_id}/manual-witness")
async def add_manual_witness(invoice_id: str, data: WitnessSignatureSubmit, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    if session_res.data and session_res.data[0]["status"] != "expired":
        session = session_res.data[0]
    else:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        session = db.table("contract_signing_sessions").insert({
            "invoice_id": invoice_id,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "status": "pending",
            "created_by": current_admin["sub"]
        }).execute().data[0]

    existing_res = db.table("witness_signatures").select("witness_number").eq("session_id", session["id"]).execute()
    signed_numbers = [r["witness_number"] for r in existing_res.data]
    if len(signed_numbers) >= 2:
        raise HTTPException(status_code=400, detail="Both witnesses have already been recorded for this session")
    if data.witness_number and data.witness_number in signed_numbers:
        raise HTTPException(status_code=400, detail="That witness number has already been recorded")

    witness_num = data.witness_number if data.witness_number in [1, 2] and data.witness_number not in signed_numbers else (1 if 1 not in signed_numbers else 2)
    stored_signature = _upload_signature_to_storage(db, invoice_id, witness_num, data.signature_base64)

    db.table("witness_signatures").insert({
        "session_id": session["id"],
        "witness_number": witness_num,
        "full_name": data.full_name,
        "witness_email": data.email,
        "address": data.address,
        "occupation": data.occupation,
        "signature_base64": stored_signature,
        "signature_method": data.signature_method,
        "ip_address": "office",
        "user_agent": "manual-entry"
    }).execute()

    new_status = "partial" if len(signed_numbers) == 0 else "completed"
    db.table("contract_signing_sessions").update({"status": new_status}).eq("id", session["id"]).execute()

    if new_status == "completed":
        witnesses = db.table("witness_signatures").select("*").eq("session_id", session["id"]).order("witness_number").execute().data
        from email_service import send_admin_signing_alert
        background_tasks.add_task(send_admin_signing_alert, invoice, client, witnesses)

    return {"message": "Witness recorded successfully", "witness_number": witness_num}

@router.post("/{invoice_id}/manual-client")
async def add_manual_client_signature(invoice_id: str, data: ClientContractSignatureSubmit, current_admin=Depends(verify_token)):
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = db.table("invoices").select("id, invoice_number, client_id").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]

    try:
        stored_signature = _upload_client_signature(db, invoice_id, data.signature_base64)
        db.table("invoices").update({
            "contract_signature_url": stored_signature,
            "contract_signature_method": data.signature_method,
            "contract_signed_at": datetime.now().isoformat()
        }).eq("id", invoice_id).execute()

        await log_activity(
            "manual_client_contract_signed",
            f"Walk-in client contract signature recorded for {invoice['invoice_number']}",
            current_admin["sub"],
            client_id=invoice.get("client_id"),
            invoice_id=invoice_id
        )

        return {"message": "Walk-in client contract signature recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record client signature: {str(e)}")

@router.post("/{invoice_id}/witness/{witness_id}/remove")
async def remove_witness_signature(invoice_id: str, witness_id: str, data: WitnessRemovalRequest, current_admin=Depends(verify_token)):
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    note = data.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="Removal note is required")

    db = get_db()
    inv_res = db.table("invoices").select("id").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    session_res = db.table("contract_signing_sessions")\
        .select("id, status")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    if not session_res.data:
        raise HTTPException(status_code=404, detail="No signing session found")

    session = session_res.data[0]
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot remove witness after contract execution")

    witness_res = db.table("witness_signatures")\
        .select("*")\
        .eq("id", witness_id)\
        .eq("session_id", session["id"])\
        .execute()

    if not witness_res.data:
        raise HTTPException(status_code=404, detail="Witness record not found")

    witness = witness_res.data[0]
    _delete_witness_signature_from_storage(db, witness.get("signature_base64", ""))
    db.table("witness_signatures").delete().eq("id", witness_id).execute()

    remaining_res = db.table("witness_signatures").select("id").eq("session_id", session["id"]).execute()
    new_status = "partial" if remaining_res.data else "pending"
    if session["status"] != new_status:
        db.table("contract_signing_sessions").update({"status": new_status}).eq("id", session["id"]).execute()

    await log_activity(
        "witness_removed",
        f"Witness {witness['witness_number']} removed from contract session {session['id']} - {note}",
        current_admin["sub"],
        invoice_id=invoice_id,
        metadata={"witness_id": witness_id, "note": note}
    )

    return {"message": "Witness removed", "session_status": new_status}

@router.get("/signatures")
async def list_company_signatures(current_admin=Depends(verify_token)):
    if current_admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    res = db.table("company_signatures").select("*").eq("is_active", True).execute()
    return res.data

@router.post("/signatures")
async def upload_company_signature(data: CompanySignatureUpload, current_admin=Depends(verify_token)):
    if current_admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    
    # 1. Process Signature (Standardize to PNG)
    try:
        if "," in data.signature_base64:
            header, encoded = data.signature_base64.split(",", 1)
        else:
            encoded = data.signature_base64
        
        raw_data = base64.b64decode(encoded)
        
        # --- PILLOW CONVERSION: Standardize to PNG ---
        with Image.open(io.BytesIO(raw_data)) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            out_buf = io.BytesIO()
            img.save(out_buf, format="PNG")
            img_data = out_buf.getvalue()
        
        file_path = f"authority/{data.role}.png"
        
        # Upload to signatures bucket
        try:
            db.storage.from_("signatures").remove([file_path])
        except Exception:
            pass
        db.storage.from_("signatures").upload(
            path=file_path,
            file=img_data,
            file_options={"content-type": "image/png"}
        )
        
        # Get public URL
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and upload signature: {str(e)}")

    # 2. Handle full_name (fetch existing if not provided)
    name_to_use = data.full_name
    old_sigs = db.table("company_signatures")\
       .select("full_name")\
       .eq("role", data.role)\
       .order("created_at", desc=True)\
       .limit(1)\
       .execute()
    if data.role == 'lawyer' and not name_to_use and not old_sigs.data:
        raise HTTPException(status_code=400, detail="Lawyer full name is required when uploading a lawyer signature.")
    if not name_to_use:
        if old_sigs.data:
            name_to_use = old_sigs.data[0]["full_name"]
        else:
            name_to_use = data.role.capitalize()

    # 3. Deactivate old ones of same role
    db.table("company_signatures").update({"is_active": False}).eq("role", data.role).execute()
    
    # 4. Insert new with URL
    res = db.table("company_signatures").insert({
        "role": data.role,
        "full_name": name_to_use,
        "signature_base64": public_url,  # Storing URL in base64 column for UI compatibility
        "uploaded_by": current_admin["sub"]
    }).execute()
    
    await log_activity(
        "signature_updated",
        f"Updated authority signature for {data.role} ({name_to_use}) and standardized to PNG.",
        current_admin["sub"]
    )
    
    return res.data[0]

@router.delete("/signatures/{role}")
async def delete_company_signature(role: str, current_admin=Depends(verify_token)):
    if current_admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    if role not in ["director", "secretary", "lawyer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    db = get_db()
    
    # Actually we just deactivate them so they don't show in UI
    db.table("company_signatures").update({"is_active": False}).eq("role", role).execute()
    
    await log_activity(
        "signature_deleted",
        f"Deactivated authority signature for {role}",
        current_admin["sub"]
    )
    
    return {"message": f"{role} signature deactivated"}

@router.post("/{invoice_id}/generate")
async def generate_final_contract(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    if current_admin["role"] not in ["admin", "lawyer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # 1. Fetch all signatures
    # (Implementation follows in pdf_service and email_service)
    
    await log_activity(
        "contract_executed",
        f"Final executed Contract of Sale generated and sent for invoice ID {invoice_id}",
        current_admin["sub"],
        invoice_id=invoice_id
    )
    
    return {"message": "Final contract execution triggered"}
