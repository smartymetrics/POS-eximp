from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db, SUPABASE_URL
from models import WitnessSignatureSubmit
from routers.analytics import log_activity
from datetime import datetime
import base64
import io
from PIL import Image

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _upload_witness_signature(db, invoice_id: str, witness_number: int, signature_base64: str) -> str:
    if not signature_base64:
        return signature_base64
    signature_value = signature_base64.strip()
    if signature_value.startswith("http://") or signature_value.startswith("https://"):
        return signature_value

    try:
        header, encoded = (signature_value.split(",", 1) + [signature_value])[:2]
        if "," in signature_value:
            encoded = signature_value.split(",", 1)[1]
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

@router.get("/sign/{token}", response_class=HTMLResponse)
async def get_signing_page(request: Request, token: str):
    return templates.TemplateResponse("sign.html", {"request": request})

@router.get("/api/signing/context/{token}")
async def get_signing_context(token: str):
    db = get_db()
    # 1. Validate session
    session_res = db.table("contract_signing_sessions")\
        .select("*, invoices(*, clients(*))")\
        .eq("token", token)\
        .execute()
    
    if not session_res.data:
        raise HTTPException(status_code=404, detail="Invalid signing link")
    
    session = session_res.data[0]
    
    # 2. Check expiry
    expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
    if expires_at < datetime.now().astimezone():
        raise HTTPException(status_code=400, detail="This signing link has expired")
    
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Signatures have already been collected for this contract")
    
    invoice = session["invoices"]
    client = invoice["clients"]
    
    return {
        "client_name": client["full_name"],
        "estate_name": invoice["property_name"],
        "plot_size_sqm": str(invoice["plot_size_sqm"]),
        "contract_date": invoice["invoice_date"]
    }

@router.post("/api/signing/sign/{token}")
async def submit_witness_signature(token: str, data: WitnessSignatureSubmit, request: Request):
    db = get_db()
    
    # 1. Validate session
    session_res = db.table("contract_signing_sessions")\
        .select("*, invoices(*)")\
        .eq("token", token)\
        .execute()
    
    if not session_res.data:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    session = session_res.data[0]
    invoice = session["invoices"]
    
    # 2. Check expiry & status
    expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
    if expires_at < datetime.now().astimezone():
        raise HTTPException(status_code=400, detail="Link expired")
    
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Already completed")
    
    # 3. Determine witness number (1 or 2)
    # Check what's already signed
    existing_res = db.table("witness_signatures").select("witness_number").eq("session_id", session["id"]).execute()
    signed_numbers = [r["witness_number"] for r in existing_res.data]
    
    if len(signed_numbers) >= 2:
         raise HTTPException(status_code=400, detail="Both witnesses have already signed")
    
    # Automatically assign the next number
    witness_num = 1 if 1 not in signed_numbers else 2
    
    # 4. Insert signature
    try:
        stored_signature = _upload_witness_signature(db, invoice["id"], witness_num, data.signature_base64)

        db.table("witness_signatures").insert({
            "session_id": session["id"],
            "witness_number": witness_num,
            "full_name": data.full_name,
            "address": data.address,
            "occupation": data.occupation,
            "signature_base64": stored_signature,
            "signature_method": data.signature_method,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }).execute()
        
        # 5. Update session status
        new_status = "partial" if witness_num == 1 and 2 not in signed_numbers else "completed"
        db.table("contract_signing_sessions").update({"status": new_status}).eq("id", session["id"]).execute()
        
        # 6. LOG ACTIVITY (Crucial requirement)
        await log_activity(
            "witness_signed",
            f"Witness {witness_num} ({data.full_name}) signed contract for {invoice['invoice_number']}",
            "system",
            client_id=invoice["client_id"],
            invoice_id=invoice["id"]
        )
        
        # 7. Check if we should notify admin
        if new_status == "completed":
            from email_service import send_admin_alert_email # We'll add a specialized one later or reuse
            # For now, let's just log it. PRD says notify admin.
            await log_activity(
                "contract_ready",
                f"Contract for {invoice['invoice_number']} is now fully witnessed and ready for execution.",
                "system",
                invoice_id=invoice["id"]
            )
            
        return {"message": "Signature recorded successfully", "witness_number": witness_num}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record signature: {str(e)}")
