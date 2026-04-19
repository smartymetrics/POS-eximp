from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from database import get_db, db_execute, SUPABASE_URL
from models import (
    CompanySignatureUpload, ExtendSigningLink, WitnessSignatureSubmit, 
    ClientContractSignatureSubmit, WitnessRemovalRequest, CustomContractHTMLUpdate, 
    ExecuteContractRequest, SendSealedRequest
)
from routers.auth import verify_token, resolve_admin_token, has_any_role
from routers.analytics import log_activity
from datetime import datetime, timedelta, timezone
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

    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client_raw = invoice.get("clients", {})
    client = client_raw[0] if isinstance(client_raw, list) and client_raw else client_raw
    if not client: client = {}

    existing = await db_execute(lambda: db.table("contract_signing_sessions")\
        .select("id, token, status, expires_at")\
        .eq("invoice_id", invoice_id)\
        .neq("status", "expired")\
        .order("created_at", desc=True)\
        .execute())

    if existing.data:
        if any(s["status"] == "completed" for s in existing.data):
            raise HTTPException(status_code=400, detail="Contract for this invoice is already fully signed")
        return existing.data[0]

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=48)

    session = db.table("contract_signing_sessions").insert({
        "invoice_id": invoice_id,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "status": "pending",
        "created_by": current_admin["sub"]
    }).execute().data[0]

    from email_service import send_signing_link_email
    background_tasks.add_task(send_signing_link_email, invoice, client, token, expires_at)

    await log_activity(
        "contract_initiated",
        f"Contract signing initiated for {invoice['invoice_number']}. Signing link sent to client. Note: This link expires in 48 hours.",
        current_admin["sub"],
        client_id=invoice["client_id"],
        invoice_id=invoice_id
    )

    return session

@router.post("/{invoice_id}/initiate")
async def initiate_contract_signing(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Check role
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Check if company signatures are set
    sig_res = await db_execute(lambda: db.table("company_signatures").select("id, role").eq("is_active", True).execute())
    roles_set = [s["role"] for s in sig_res.data]
    if "director" not in roles_set or "secretary" not in roles_set:
        raise HTTPException(status_code=400, detail="Company signatures (Director/Secretary) must be uploaded before initiating contracts.")

    # 1. Fetch Invoice
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client_raw = invoice.get("clients", {})
    client = client_raw[0] if isinstance(client_raw, list) and client_raw else client_raw
    if not client: client = {}
    
    # 2. Prevent duplicate active sessions
    existing = await db_execute(lambda: db.table("contract_signing_sessions").select("id, status").eq("invoice_id", invoice_id).neq("status", "expired").execute())
    if existing.data:
        # If it's already completed, don't restart
        if any(s["status"] == "completed" for s in existing.data):
             raise HTTPException(status_code=400, detail="Contract for this invoice is already fully signed")
        # Else, we could expire the old one and start new, but for now let's just return it
        return {"message": "Session already exists", "token": existing.data[0].get("token")}

    # 3. Create Session
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=48)
    
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
    
    await log_activity(
        "contract_initiated",
        f"Contract signing initiated for {invoice['invoice_number']}. Signing link sent to client. Note: This link expires in 48 hours.",
        current_admin["sub"],
        client_id=invoice["client_id"],
        invoice_id=invoice_id
    )
    
    # Log to email_logs
    await db_execute(lambda: db.table("email_logs").insert({
        "client_id": invoice["client_id"],
        "invoice_id": invoice_id,
        "email_type": "contract",
        "recipient_email": client.get("email"),
        "subject": "Your Contract of Sale is Ready — Eximp & Cloves",
        "status": "sent",
        "sent_by": current_admin["sub"]
    }).execute())
    
    return {"message": "Contract signing initiated", "token": token, "expires_at": expires_at}

@router.get("/{invoice_id}/status")
async def get_contract_status(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute())
    
    if not res.data:
         return {"status": "not_started", "client_signed": False}

    session = res.data[0]
    
    # Check if client has signed (look at invoice)
    inv_res = await db_execute(lambda: db.table("invoices").select("contract_signature_url").eq("id", invoice_id).execute())
    client_signed = False
    if inv_res.data:
        inv = inv_res.data[0]
        client_signed = bool(inv.get("contract_signature_url"))


    return {
        "id": session["id"],
        "invoice_id": session["invoice_id"],
        "token": session["token"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        "created_at": session.get("created_at"),
        "witness_signatures": session.get("witness_signatures", []),
        "client_signed": client_signed,
        "is_executed": session["status"] == "completed"
    }

@router.post("/{invoice_id}/extend")
async def extend_signing_session(invoice_id: str, current_admin=Depends(verify_token)):
    """Extend an active session by 48 hours."""
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    res = await db_execute(lambda: db.table("contract_signing_sessions").select("id, expires_at").eq("invoice_id", invoice_id).neq("status", "expired").order("created_at", desc=True).limit(1).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="No active session found to extend")
    
    new_expiry = datetime.now(timezone.utc) + timedelta(hours=48)
    
    await db_execute(lambda: db.table("contract_signing_sessions").update({"expires_at": new_expiry.isoformat()}).eq("id", res.data[0]["id"]).execute())
    
    await log_activity(
        "contract_extended",
        f"Contract signing session extended by 48 hours for {invoice_id}",
        current_admin["sub"],
        invoice_id=invoice_id
    )
    return {"message": "Session extended", "new_expiry": new_expiry}

@router.get("/{invoice_id}/html-draft")
async def get_contract_html_draft(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    """Render a high-fidelity HTML draft of the contract, NOT an invoice."""
    from pdf_service import render_contract_html
    from fastapi.responses import HTMLResponse
    
    db = get_db()
    
    # 1. Fetch Invoice
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data: raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    
    # 2. Fetch Session & Witnesses
    session_res = await db_execute(lambda: db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", invoice_id).order("created_at", desc=True).limit(1).execute())
    witnesses = session_res.data[0].get("witness_signatures", []) if session_res.data else []
    
    # 3. Render full contract (Draft mode, Browser-friendly URLs)
    html_content = render_contract_html(
        invoice, 
        invoice["clients"], 
        witnesses=witnesses, 
        is_draft=True, 
        embed_images=False # Use URLs for faster browser preview
    )
    
    return HTMLResponse(content=html_content)

@router.post("/session/{invoice_id}")
async def create_contract_session(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    sig_res = await db_execute(lambda: get_db().table("company_signatures").select("id, role").eq("is_active", True).execute())
    roles_set = [s["role"] for s in sig_res.data]
    if "director" not in roles_set or "secretary" not in roles_set:
        raise HTTPException(status_code=400, detail="Company signatures (Director/Secretary) must be uploaded before initiating contracts.")

    session = await _create_contract_session(invoice_id, current_admin, background_tasks)
    return {"message": "Contract signing initiated", "token": session["token"], "expires_at": session["expires_at"]}

@router.post("/resend/{invoice_id}")
async def resend_contract_link(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    session_res = await db_execute(lambda: db.table("contract_signing_sessions")\
        .select("*, invoices(*, clients(*))")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute())

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

    # Log to email_logs
    await db_execute(lambda: db.table("email_logs").insert({
        "client_id": invoice["client_id"],
        "invoice_id": invoice_id,
        "email_type": "contract",
        "recipient_email": client["email"],
        "subject": "Your Contract of Sale — Eximp & Cloves",
        "status": "sent",
        "sent_by": current_admin["sub"]
    }).execute())

    return {"message": "Signing link resent"}

@router.post("/execute/{invoice_id}")
async def execute_final_contract(invoice_id: str, payload: ExecuteContractRequest, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
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
    if len(witnesses) < 1:
        raise HTTPException(status_code=400, detail="The external witness must sign before executing the contract")

    if session["status"] != "completed":
        await db_execute(lambda: db.table("contract_signing_sessions").update({"status": "completed"}).eq("id", session["id"]).execute())

    from pdf_service import generate_contract_pdf, generate_audit_certificate_pdf
    # 1. Generate Main Contract
    pdf_content = generate_contract_pdf(invoice, client, witnesses, is_draft=False)
    
    # 2. Generate Audit Certificate (Always generated for internal storage)
    cert_content = generate_audit_certificate_pdf(invoice, client, witnesses)

    # 3. Email Delivery (Optional Certificate)
    from email_service import send_executed_contract_email
    background_tasks.add_task(
        send_executed_contract_email, 
        invoice, 
        client, 
        pdf_content, 
        cert_content if payload.send_certificate else None
    )

    await db_execute(lambda: db.table("contract_documents").insert({
        "invoice_id": invoice_id,
        "session_id": session["id"],
        "document_type": "executed",
        "generated_by": current_admin["sub"],
        "emailed_to": client.get("email")
    }).execute())

    await log_activity(
        "contract_executed",
        f"Final executed contract generated for {invoice['invoice_number']}",
        current_admin["sub"],
        invoice_id=invoice_id,
        client_id=client.get("id")
    )

    # Log to email_logs
    await db_execute(lambda: db.table("email_logs").insert({
        "client_id": client.get("id"),
        "invoice_id": invoice_id,
        "email_type": "contract",
        "recipient_email": client.get("email"),
        "subject": f"Execution Complete: Your Contract of Sale {invoice['invoice_number']}",
        "status": "sent",
        "sent_by": current_admin["sub"]
    }).execute())

    return {"message": "Final contract executed and emailed"}

@router.get("/download-sealing/{invoice_id}")
async def download_sealing_contract(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
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

    witnesses = []
    if session_res.data:
        witnesses = session_res.data[0].get("witness_signatures", []) or []

    from pdf_service import generate_contract_pdf
    pdf_content = generate_contract_pdf(invoice, client, witnesses, is_draft=False)
    
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Contract_FOR_SEALING_{invoice['invoice_number']}.pdf"}
    )

@router.post("/upload-sealed/{invoice_id}")
async def upload_sealed_contract(invoice_id: str, file: UploadFile = File(...), current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    db = get_db()
    content = await file.read()
    
    file_path = f"sealed_contracts/{invoice_id}/sealed_contract.pdf"
    
    try:
        try:
            db.storage.from_("signatures").remove([file_path])
        except:
            pass
            
        db.storage.from_("signatures").upload(
            path=file_path,
            file=content,
            file_options={"content-type": "application/pdf"}
        )
        
        await db_execute(lambda: db.table("contract_documents").insert({
            "invoice_id": invoice_id,
            "document_type": "sealed_lawyer_copy",
            "generated_by": current_admin["sub"]
        }).execute())

        await log_activity(
            "sealed_contract_uploaded",
            f"Externally sealed contract uploaded for {invoice_id}",
            current_admin["sub"],
            invoice_id=invoice_id
        )

        return {"message": "Sealed contract uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/send-sealed/{invoice_id}")
async def send_sealed_contract(invoice_id: str, payload: SendSealedRequest, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    file_path = f"sealed_contracts/{invoice_id}/sealed_contract.pdf"
    try:
        sealed_pdf_res = db.storage.from_("signatures").download(file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="Sealed contract not found. Please upload it first.")

    session_res = db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    
    witnesses = []
    if session_res.data:
        witnesses = session_res.data[0].get("witness_signatures", []) or []
    
    from pdf_service import generate_audit_certificate_pdf
    cert_content = generate_audit_certificate_pdf(invoice, client, witnesses)

    from email_service import send_executed_contract_email
    background_tasks.add_task(
        send_executed_contract_email, 
        invoice, 
        client, 
        sealed_pdf_res, 
        cert_content if payload.send_certificate else None
    )

    await log_activity(
        "sealed_contract_sent",
        f"Externally sealed contract emailed to {client['email']}",
        current_admin["sub"],
        invoice_id=invoice_id,
        client_id=client.get("id")
    )

    await db_execute(lambda: db.table("email_logs").insert({
        "client_id": client.get("id"),
        "invoice_id": invoice_id,
        "email_type": "contract",
        "recipient_email": client.get("email"),
        "subject": f"Execution Complete: Your Contract of Sale {invoice['invoice_number']}",
        "status": "sent",
        "sent_by": current_admin["sub"]
    }).execute())

    return {"message": "Sealed contract emailed successfully"}

@router.post("/resend-final/{invoice_id}")
async def resend_executed_contract(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = await db_execute(lambda: db.table("contract_signing_sessions")\
        .select("*, witness_signatures(*)").eq("invoice_id", invoice_id).order("created_at", desc=True).limit(1).execute())

    if not session_res.data or session_res.data[0]["status"] != "completed":
        raise HTTPException(status_code=400, detail="The contract has not been executed yet")

    witnesses = session_res.data[0].get("witness_signatures", []) or []
    from pdf_service import generate_contract_pdf
    pdf_content = generate_contract_pdf(invoice, client, witnesses, is_draft=False)

    from email_service import send_executed_contract_email
    background_tasks.add_task(send_executed_contract_email, invoice, client, pdf_content)
    return {"message": "Final contract resent to client"}

@router.get("/{invoice_id}/contract")
async def get_executed_contract_pdf(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    """Download the final executed contract PDF."""
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data: raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = await db_execute(lambda: db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", invoice_id).order("created_at", desc=True).limit(1).execute())
    if not session_res.data or session_res.data[0]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Contract not yet executed")

    witnesses = session_res.data[0].get("witness_signatures", [])
    from pdf_service import generate_contract_pdf
    pdf_content = generate_contract_pdf(invoice, client, witnesses, is_draft=False)
    
    from fastapi.responses import Response
    return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Contract_{invoice['invoice_number']}.pdf"})

@router.get("/{invoice_id}/certificate")
async def get_audit_certificate_pdf(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    """Download the digital audit certificate for an executed contract."""
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data: raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    client = invoice["clients"]

    session_res = await db_execute(lambda: db.table("contract_signing_sessions").select("*, witness_signatures(*)").eq("invoice_id", invoice_id).order("created_at", desc=True).limit(1).execute())
    if not session_res.data or session_res.data[0]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Contract not yet executed")

    witnesses = session_res.data[0].get("witness_signatures", [])
    from pdf_service import generate_audit_certificate_pdf
    pdf_content = generate_audit_certificate_pdf(invoice, client, witnesses)
    
    from fastapi.responses import Response
    return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Audit_Certificate_{invoice['invoice_number']}.pdf"})

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
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
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
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
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
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
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
        expires_at = datetime.now() + timedelta(hours=48)
        res = await db_execute(lambda: db.table("contract_signing_sessions").insert({
            "invoice_id": invoice_id,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "status": "pending",
            "created_by": current_admin["sub"]
        }).execute())
        session = res.data[0]

    existing_res = await db_execute(lambda: db.table("witness_signatures").select("witness_number").eq("session_id", session["id"]).execute())
    signed_numbers = [r["witness_number"] for r in existing_res.data]
    if len(signed_numbers) >= 1:
        raise HTTPException(status_code=400, detail="The external witness has already been recorded for this session")
    if data.witness_number and data.witness_number in signed_numbers:
        raise HTTPException(status_code=400, detail="That witness number has already been recorded")

    witness_num = data.witness_number if data.witness_number in [1, 2] and data.witness_number not in signed_numbers else (1 if 1 not in signed_numbers else 2)
    stored_signature = _upload_signature_to_storage(db, invoice_id, witness_num, data.signature_base64)

    await db_execute(lambda: db.table("witness_signatures").insert({
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
    }).execute())

    # Do not auto-complete the session status; let the admin click the final 'Execute' button
    # new_status = "completed"
    # db.table("contract_signing_sessions").update({"status": new_status}).eq("id", session["id"]).execute()
    
    # Check if we have at least one witness (the goal is met for execution)
    witnesses_res = await db_execute(lambda: db.table("witness_signatures").select("*").eq("session_id", session["id"]).order("witness_number").execute())
    witnesses = witnesses_res.data
    from email_service import send_admin_signing_alert
    background_tasks.add_task(send_admin_signing_alert, invoice, client, witnesses)

    await log_activity(
        "witness_added",
        f"Manual witness recorded for invoice {invoice['invoice_number']} ({data.full_name})",
        current_admin["sub"],
        invoice_id=invoice_id,
        client_id=invoice.get("client_id")
    )

    return {"message": "Witness recorded successfully", "witness_number": witness_num}

@router.post("/{invoice_id}/manual-client")
async def add_manual_client_signature(invoice_id: str, data: ClientContractSignatureSubmit, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("id, invoice_number, client_id").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]

    try:
        stored_signature = _upload_client_signature(db, invoice_id, data.signature_base64)
        await db_execute(lambda: db.table("invoices").update({
            "contract_signature_url": stored_signature,
            "contract_signature_method": data.signature_method,
            "contract_signed_at": datetime.now().isoformat()
        }).eq("id", invoice_id).execute())

        await log_activity(
            "manual_client_contract_signed",
            f"Walk-in client contract signature recorded for {invoice['invoice_number']}. Security Notice: Both links expire in 48 hours.",
            current_admin["sub"],
            client_id=invoice.get("client_id"),
            invoice_id=invoice_id
        )

        return {"message": "Walk-in client contract signature recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record client signature: {str(e)}")

@router.post("/{invoice_id}/witness/{witness_id}/remove")
async def remove_witness_signature(invoice_id: str, witness_id: str, data: WitnessRemovalRequest, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    note = data.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="Removal note is required")

    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("id").eq("id", invoice_id).execute())
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
    await db_execute(lambda: db.table("witness_signatures").delete().eq("id", witness_id).execute())

    remaining_res = await db_execute(lambda: db.table("witness_signatures").select("id").eq("session_id", session["id"]).execute())
    new_status = "partial" if remaining_res.data else "pending"
    if session["status"] != new_status:
        await db_execute(lambda: db.table("contract_signing_sessions").update({"status": new_status}).eq("id", session["id"]).execute())

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
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    db = get_db()
    res = await db_execute(lambda: db.table("company_signatures").select("*").eq("is_active", True).execute())
    return res.data

@router.post("/signatures")
async def upload_company_signature(data: CompanySignatureUpload, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
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
    await db_execute(lambda: db.table("company_signatures").update({"is_active": False}).eq("role", data.role).execute())
    
    # 4. Insert new with URL
    insert_data = {
        "role": data.role,
        "full_name": name_to_use,
        "signature_base64": public_url,  # Storing URL in base64 column for UI compatibility
        "is_active": True,               # Corrected: Newest signature must be active
        "uploaded_by": current_admin["sub"]
    }
    if data.address: insert_data["address"] = data.address
    if data.occupation: insert_data["occupation"] = data.occupation

    res = await db_execute(lambda: db.table("company_signatures").insert(insert_data).execute())

    
    await log_activity(
        "signature_updated",
        f"Updated authority signature for {data.role} ({name_to_use}) and standardized to PNG.",
        current_admin["sub"]
    )
    
    return res.data[0]

@router.delete("/signatures/{role}")
async def delete_company_signature(role: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    if role not in ["director", "secretary", "lawyer", "lawyer_seal", "witness"]:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    db = get_db()
    
    # Actually we just deactivate them so they don't show in UI
    await db_execute(lambda: db.table("company_signatures").update({"is_active": False}).eq("role", role).execute())
    
    await log_activity(
        "signature_deleted",
        f"Deactivated authority signature for {role}",
        current_admin["sub"]
    )
    
    return {"message": f"{role} signature deactivated"}

@router.post("/{invoice_id}/generate")
async def generate_final_contract(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    if not has_any_role(current_admin, "admin", "lawyer"):
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

@router.post("/extend/{invoice_id}")
async def extend_contract_signing(invoice_id: str, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    db = get_db()

    # 1. Fetch invoice and client for the email
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = inv_res.data[0]
    
    # 2. Find active or recently expired session
    session_res = db.table("contract_signing_sessions")\
        .select("*")\
        .eq("invoice_id", invoice_id)\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
        
    if not session_res.data:
        raise HTTPException(status_code=404, detail="No signing session found")
        
    session = session_res.data[0]
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Contract is already fully signed")

    # 3. Extend by 48 hours
    new_expiry = datetime.now() + timedelta(hours=48)
    db.table("contract_signing_sessions").update({
        "expires_at": new_expiry.isoformat(),
        "status": "pending" 
    }).eq("id", session["id"]).execute()
    
    # 4. Notify Client via Email
    from email_service import send_signing_link_email
    background_tasks.add_task(send_signing_link_email, invoice, invoice["clients"], session["token"], new_expiry)
    
    await log_activity(
        "contract_extended",
        f"Contract signing link extended by 48 hours for {invoice['invoice_number']}. Notification email sent.",
        current_admin["sub"],
        client_id=invoice["client_id"],
        invoice_id=invoice_id
    )
    
    return {"message": "Link extended and client notified", "new_expiry": new_expiry}

@router.get("/{invoice_id}/default-html")
@router.get("/{invoice_id}/custom-html")
async def get_contract_html(invoice_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    db = get_db()
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    invoice = inv_res.data[0]
    
    from pdf_service import get_default_contract_html_fragment, get_default_cover_html_fragment, get_default_execution_html_fragment
    
    # Body
    if invoice.get("custom_contract_html") is not None:
        html_content = invoice["custom_contract_html"]
        is_custom = True
    else:
        html_content = get_default_contract_html_fragment(invoice, invoice["clients"])
        is_custom = False

    # Cover
    if invoice.get("custom_cover_html") is not None:
        cover_html = invoice["custom_cover_html"]
        is_custom_cover = True
    else:
        cover_html = get_default_cover_html_fragment(invoice, invoice["clients"])
        is_custom_cover = False

    # Execution
    if invoice.get("custom_execution_html") is not None:
        execution_html = invoice["custom_execution_html"]
        is_custom_execution = True
    else:
        execution_html = get_default_execution_html_fragment(invoice, invoice["clients"])
        is_custom_execution = False
        
    return {
        "html_content": html_content, 
        "is_custom": is_custom,
        "cover_html": cover_html,
        "is_custom_cover": is_custom_cover,
        "execution_html": execution_html,
        "is_custom_execution": is_custom_execution,
        "lawfirm_name": invoice.get("custom_lawfirm_name"),
        "lawfirm_address": invoice.get("custom_lawfirm_address")
    }

@router.put("/{invoice_id}/custom-html")
async def update_contract_html(invoice_id: str, payload: CustomContractHTMLUpdate, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    db = get_db()
    
    # 1. Check if invoice exists
    inv_res = await db_execute(lambda: db.table("invoices").select("id").eq("id", invoice_id).execute())
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # 2. Prevent editing if contract is already signed
    session_res = await db_execute(lambda: db.table("contract_signing_sessions").select("status").eq("invoice_id", invoice_id).neq("status", "expired").execute())
    if session_res.data and session_res.data[0]["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot edit contract wording after it has been fully executed")
        
    # 3. Save the custom HTML to Supabase
    update_data = {
        "custom_contract_html": payload.html_content,
        "updated_at": datetime.now().isoformat()
    }
    if payload.cover_html is not None:
        update_data["custom_cover_html"] = payload.cover_html
    if payload.execution_html is not None:
        update_data["custom_execution_html"] = payload.execution_html
    if payload.lawfirm_name is not None:
        update_data["custom_lawfirm_name"] = payload.lawfirm_name
    if payload.lawfirm_address is not None:
        update_data["custom_lawfirm_address"] = payload.lawfirm_address

    await db_execute(lambda: db.table("invoices").update(update_data).eq("id", invoice_id).execute())
    
    await log_activity(
        "contract_wording_updated",
        f"Contract wordings updated manually for invoice {invoice_id}",
        current_admin["sub"],
        invoice_id=invoice_id
    )
    
    return {"message": "Custom contract wordings saved successfully"}

# --- NEW LEGAL DASHBOARD ENDPOINTS ---

@router.get("/summary")
async def get_legal_summary(current_admin=Depends(verify_token)):
    """Fetch high-level KPIs for the Legal Dashboard."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    
    # Run all 3 DB queries in parallel using asyncio
    import asyncio
    
    def _count_invoices():
        res = db.table("invoices").select("id", count="exact").neq("status", "voided").execute()
        return res.count or 0

    def _count_sessions():
        res = db.table("contract_signing_sessions").select("status").execute()
        rows = res.data or []
        active = sum(1 for r in rows if r["status"] != "completed")
        completed = sum(1 for r in rows if r["status"] == "completed")
        pending = sum(1 for r in rows if r["status"] == "pending")
        return active, completed, pending

    loop = asyncio.get_event_loop()
    try:
        total_contracts, (active_sessions, executed_contracts, pending_execution) = await asyncio.gather(
            loop.run_in_executor(None, _count_invoices),
            loop.run_in_executor(None, _count_sessions)
        )
    except Exception as e:
        print(f"Summary query error: {e}")
        total_contracts = active_sessions = executed_contracts = pending_execution = 0

    return {
        "total_contracts": int(total_contracts),
        "active_sessions": int(active_sessions),
        "executed_contracts": int(executed_contracts),
        "pending_execution": int(pending_execution),
    }

@router.get("/execution-trends")
async def get_execution_trends(current_admin=Depends(verify_token)):
    """Fetch weekly execution velocity and pipeline health for the Legal dashboard."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    db = get_db()
    execution_docs_res = await db_execute(lambda: db.table("contract_documents")\
        .select("id, created_at, session_id, contract_signing_sessions(created_at)")\
        .eq("document_type", "executed")\
        .order("created_at", desc=True)\
        .limit(200)\
        .execute())
    execution_docs = execution_docs_res.data or []

    session_rows_res = await db_execute(lambda: db.table("contract_signing_sessions")\
        .select("id, created_at")\
        .order("created_at", desc=True)\
        .limit(300)\
        .execute())
    session_rows = session_rows_res.data or []

    session_start = {}
    for row in session_rows:
        dt = None
        if row.get("created_at"):
            try:
                dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            except ValueError:
                continue
        if dt:
            session_start[row["id"]] = dt

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(weeks=16)

    def week_key(dt):
        iso = dt.isocalendar()
        return (iso[0], iso[1])

    weekly = {}

    def ensure_bucket(key):
        if key not in weekly:
            weekly[key] = {
                "label": f"{key[0]}-W{key[1]:02d}",
                "initiated": 0,
                "executed": 0,
                "total_hours": 0.0,
                "execution_count": 0
            }
        return weekly[key]

    for row in session_rows:
        created_at = row.get("created_at")
        if not created_at:
            continue
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt < window_start:
            continue
        bucket = ensure_bucket(week_key(dt))
        bucket["initiated"] += 1

    for doc in execution_docs:
        exec_at_raw = doc.get("created_at")
        session_dt = None
        if doc.get("contract_signing_sessions"):
            nested = doc["contract_signing_sessions"]
            if isinstance(nested, list) and nested:
                session_created_at = nested[0].get("created_at")
                if session_created_at:
                    try:
                        session_dt = datetime.fromisoformat(session_created_at.replace("Z", "+00:00"))
                    except ValueError:
                        session_dt = None

        if not session_dt and doc.get("session_id"):
            session_dt = session_start.get(doc["session_id"])

        if not exec_at_raw or not session_dt:
            continue

        try:
            exec_dt = datetime.fromisoformat(exec_at_raw.replace("Z", "+00:00"))
        except ValueError:
            continue

        if exec_dt < window_start:
            continue

        bucket = ensure_bucket(week_key(exec_dt))
        bucket["executed"] += 1
        duration_hours = max((exec_dt - session_dt).total_seconds() / 3600, 0)
        bucket["total_hours"] += duration_hours
        bucket["execution_count"] += 1

    sorted_weeks = sorted(weekly.items(), key=lambda item: item[0])
    labels = [item[1]["label"] for item in sorted_weeks]
    initiated_counts = [item[1]["initiated"] for item in sorted_weeks]
    executed_counts = [item[1]["executed"] for item in sorted_weeks]
    avg_hours = [round(item[1]["total_hours"] / item[1]["execution_count"], 1) if item[1]["execution_count"] else 0 for item in sorted_weeks]

    return {
        "labels": labels,
        "initiated_counts": initiated_counts,
        "executed_counts": executed_counts,
        "avg_hours_to_execution": avg_hours
    }

@router.get("/archive")
async def list_archived_contracts(current_admin=Depends(verify_token)):
    """Fetch all fully executed contracts for the legal archive."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    # Slim select — only fields needed for the archive table display
    result = await db_execute(lambda: db.table("contract_signing_sessions")\
        .select("id, invoice_id, created_at, updated_at, invoices(id, invoice_number, clients(full_name))")\
        .eq("status", "completed")\
        .order("created_at", desc=True)\
        .limit(50)\
        .execute())
        
    return result.data

@router.get("/all-contracts")
async def list_all_contracts(include_voided: bool = Query(False), current_admin=Depends(verify_token)):
    """Fetch a comprehensive list of all contracts and their real-time signing status."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    db = get_db()
    
    query = db.table("invoices")\
        .select("id, invoice_number, property_name, property_location, amount, created_at, status, contract_signature_url, plot_size_sqm, clients(full_name, email), contract_signing_sessions(*, witness_signatures(*))") \
        .order("created_at", desc=True)\
        .limit(100)

    if not include_voided:
        query = query.neq("status", "voided")

    result = await db_execute(lambda: query.execute())
        
    contracts = result.data
    for c in contracts:
        # Summarize status for the dashboard
        sessions = c.get("contract_signing_sessions", [])
        if isinstance(sessions, list) and sessions:
             # Pick the latest session
             session = sorted(sessions, key=lambda s: s.get("created_at", ""), reverse=True)[0]
        else:
             session = sessions if isinstance(sessions, dict) else {}

        c["signing_status"] = session.get("status", "not_started")
        c["expires_at"] = session.get("expires_at")
        
        # Count signatures collected
        sigs = 0
        if c.get("contract_signature_url"): 
            sigs += 1
            
        # Count witnesses in the same latest session
        witnesses = session.get("witness_signatures", [])
        if witnesses:
            sigs += len(witnesses)
            
        c["signatures_collected"] = sigs

    return contracts

@router.post("/{invoice_id}/seal")
async def upload_custom_lawyer_seal(
    invoice_id: str, 
    payload: dict, # {seal_base64: "..."}
    current_admin=Depends(verify_token)
):
    """Upload a one-off lawyer seal for a specific contract."""
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    db = get_db()
    seal_b64 = payload.get("seal_base64")
    if not seal_b64:
        raise HTTPException(status_code=400, detail="Missing seal data")

    # Upload to storage
    try:
        if "," in seal_b64:
            _, encoded = seal_b64.split(",", 1)
        else:
            encoded = seal_b64
        
        img_data = base64.b64decode(encoded)
        file_path = f"custom_seals/{invoice_id}_seal.png"
        
        # Optional: Remove old one if exists
        try:
            db.storage.from_("signatures").remove([file_path])
        except: pass
        
        db.storage.from_("signatures").upload(
            path=file_path,
            file=img_data,
            file_options={"content-type": "image/png"}
        )
        seal_url = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
        
        # Update invoice
        await db_execute(lambda: db.table("invoices").update({"custom_lawyer_seal_url": seal_url}).eq("id", invoice_id).execute())
        
        return {"message": "Custom lawyer seal uploaded successfully", "seal_url": seal_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seal upload failed: {str(e)}")



from fastapi.responses import HTMLResponse

@router.get("/{invoice_id}/html-preview/invoice", response_class=HTMLResponse)
async def preview_invoice_html(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("invoices").select("*, clients(*), payments(*)").eq("id", invoice_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = res.data[0]
    
    from pdf_service import render_invoice_html
    html_content = render_invoice_html(invoice)
    return HTMLResponse(content=html_content)

@router.get("/{invoice_id}/html-preview/receipt", response_class=HTMLResponse)
async def preview_receipt_html(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("invoices").select("*, clients(*), payments(*)").eq("id", invoice_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = res.data[0]
    
    from pdf_service import render_receipt_html
    html_content = render_receipt_html(invoice)
    return HTMLResponse(content=html_content)

@router.get("/{invoice_id}/html-preview/statement", response_class=HTMLResponse)
async def preview_statement_html(invoice_id: str, current_admin=Depends(resolve_admin_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    client_id = res.data[0].get("client_id")
    if not client_id:
        raise HTTPException(status_code=404, detail="Client not found")
        
    client = res.data[0].get("clients")
    
    # Fetch all invoices for the client
    inv_res = await db_execute(lambda: db.table("invoices").select("*, payments(*)").eq("client_id", client_id).order("invoice_date").execute())
    invoices = inv_res.data
    
    from pdf_service import render_statement_html
    html_content = render_statement_html(invoices, client)
    return HTMLResponse(content=html_content)


# --- SIGNATURE VAULT ENDPOINTS ---

@router.get("/authorities")
async def list_authorities(current_admin=Depends(verify_token)):
    """List all company signatures (active and inactive)."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    res = await db_execute(lambda: db.table("company_signatures").select("*").order("created_at", desc=True).execute())
    return res.data

@router.post("/authorities")
async def upload_authority_signature(payload: CompanySignatureUpload, current_admin=Depends(verify_token)):
    """Upload a new authority signature (Director, Secretary, Lawyer)."""
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    
    # Upload to storage
    try:
        sig_b64 = payload.signature_base64
        if "," in sig_b64:
            _, encoded = sig_b64.split(",", 1)
        else:
            encoded = sig_b64
        
        img_data = base64.b64decode(encoded)
        filename = f"authorities/{payload.role}_{secrets.token_hex(4)}.png"
        
        db.storage.from_("signatures").upload(
            path=filename,
            file=img_data,
            file_options={"content-type": "image/png"}
        )
        sig_url = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{filename}"
        
        # Save to DB
        new_sig = {
            "role": payload.role,
            "full_name": payload.full_name,
            "address": payload.address,
            "occupation": payload.occupation,
            "signature_base64": sig_url, # We store the URL in this field for consistency
            "uploaded_by": current_admin["sub"],
            "is_active": True
        }
        
        # Deactivate old signatures of the same role
        await db_execute(lambda: db.table("company_signatures").update({"is_active": False}).eq("role", payload.role).execute())
        
        res = await db_execute(lambda: db.table("company_signatures").insert(new_sig).execute())
        
        await log_activity(
            "authority_signature_uploaded",
            f"New {payload.role} signature uploaded: {payload.full_name}",
            current_admin["sub"]
        )
        
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/authorities/{sig_id}")
async def deactivate_authority_signature(sig_id: str, current_admin=Depends(verify_token)):
    """Mark an authority signature as inactive."""
    if not has_any_role(current_admin, "admin", "lawyer"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    await db_execute(lambda: db.table("company_signatures").update({"is_active": False}).eq("id", sig_id).execute())
    
    await log_activity(
        "authority_signature_deactivated",
        f"Authority signature {sig_id} deactivated",
        current_admin["sub"]
    )
    return {"message": "Signature deactivated"}

@router.get("/activity")
async def get_legal_activity(limit: int = 15, current_admin=Depends(verify_token)):
    """Fetch recent contract-related activity logs for the dashboard."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    # Filter for contract-related events
    legal_events = [
        "contract_created", "contract_signed", "contract_executed", 
        "witness_signed", "witness_added", "contract_extended", 
        "lawyer_seal_uploaded", "authority_signature_uploaded",
        "client_signed_contract", "manual_client_contract_signed",
        "contract_initiated", "contract_wording_updated", "witness_removed",
        "signature_updated", "signature_deactivated", "authority_signature_deactivated"
    ]
    
    result = await db_execute(lambda: db.table("activity_log")\
        .select("*, admins(full_name)")\
        .in_("event_type", legal_events)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute())
        
    return result.data
    await db_execute(lambda: db.table("company_signatures").update({"is_active": False}).eq("id", sig_id).execute())
    
    await log_activity(
        "authority_signature_deactivated",
        f"Authority signature {sig_id} deactivated",
        current_admin["sub"]
    )
    return {"message": "Signature deactivated"}

@router.get("/activity")
async def get_legal_activity(limit: int = 15, current_admin=Depends(verify_token)):
    """Fetch recent contract-related activity logs for the dashboard."""
    if not has_any_role(current_admin, "admin", "lawyer", "legal"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db = get_db()
    # Filter for contract-related events
    legal_events = [
        "contract_created", "contract_signed", "contract_executed", 
        "witness_signed", "witness_added", "contract_extended", 
        "lawyer_seal_uploaded", "authority_signature_uploaded",
        "client_signed_contract", "manual_client_contract_signed",
        "contract_initiated", "contract_wording_updated", "witness_removed",
        "signature_updated", "signature_deactivated", "authority_signature_deactivated"
    ]
    
    result = await db_execute(lambda: db.table("activity_log")\
        .select("*, admins(full_name)")\
        .in_("event_type", legal_events)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute())
        
    return result.data
