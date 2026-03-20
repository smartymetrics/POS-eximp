from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from models import InvoiceCreate, SendDocumentRequest
from database import get_db
from routers.auth import verify_token
from email_service import send_invoice_email, send_receipt_email, send_statement_email
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf
import io

router = APIRouter()


@router.get("/")
async def list_invoices(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("invoices")\
        .select("*, clients(full_name, email)")\
        .order("created_at", desc=True)\
        .execute()
    return result.data


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("invoices")\
        .select("*, clients(*), payments(*)")\
        .eq("id", invoice_id)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result.data[0]


@router.post("/")
async def create_invoice(data: InvoiceCreate, current_admin=Depends(verify_token)):
    db = get_db()

    # Generate invoice number via DB function
    seq_result = db.rpc("generate_invoice_number").execute()
    invoice_number = seq_result.data

    # If property_id provided, snapshot the property details
    property_name = data.property_name
    property_location = data.property_location
    plot_size = data.plot_size_sqm

    if data.property_id:
        prop = db.table("properties").select("*").eq("id", data.property_id).execute()
        if prop.data:
            p = prop.data[0]
            property_name = property_name or p["name"]
            property_location = property_location or p["location"]
            plot_size = plot_size or p["plot_size_sqm"]

    result = db.table("invoices").insert({
        "invoice_number": invoice_number,
        "client_id": data.client_id,
        "property_id": data.property_id,
        "property_name": property_name,
        "property_location": property_location,
        "plot_size_sqm": float(plot_size) if plot_size else None,
        "amount": float(data.amount),
        "payment_terms": data.payment_terms,
        "invoice_date": str(data.invoice_date),
        "due_date": str(data.due_date),
        "notes": data.notes,
        "created_by": current_admin["sub"]
    }).execute()

    return {"message": "Invoice created", "invoice": result.data[0]}


@router.post("/send")
async def send_documents(
    data: SendDocumentRequest,
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()

    # Fetch full invoice data
    inv = db.table("invoices")\
        .select("*, clients(*), payments(*)")\
        .eq("id", data.invoice_id)\
        .execute()

    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv.data[0]
    client = invoice["clients"]

    sent = []

    for doc_type in data.document_types:
        if doc_type == "invoice":
            background_tasks.add_task(send_invoice_email, invoice, client, current_admin["sub"])
            sent.append("invoice")
        elif doc_type == "receipt" and invoice["amount_paid"] > 0:
            background_tasks.add_task(send_receipt_email, invoice, client, current_admin["sub"])
            sent.append("receipt")
        elif doc_type == "statement":
            # Fetch all invoices for this client
            all_inv = db.table("invoices")\
                .select("*, payments(*)")\
                .eq("client_id", invoice["client_id"])\
                .order("invoice_date")\
                .execute()
            background_tasks.add_task(send_statement_email, all_inv.data, client, current_admin["sub"])
            sent.append("statement")

    # Log emails
    for doc_type in sent:
        db.table("email_logs").insert({
            "client_id": invoice["client_id"],
            "invoice_id": data.invoice_id,
            "email_type": doc_type,
            "recipient_email": client["email"],
            "subject": f"Eximp & Cloves - {doc_type.title()} {invoice['invoice_number']}",
            "status": "sent",
            "sent_by": current_admin["sub"]
        }).execute()

    return {"message": f"Sent: {', '.join(sent)}", "sent": sent}


@router.get("/{invoice_id}/pdf/{doc_type}")
async def download_pdf(invoice_id: str, doc_type: str, current_admin=Depends(verify_token)):
    db = get_db()
    inv = db.table("invoices")\
        .select("*, clients(*), payments(*)")\
        .eq("id", invoice_id)\
        .execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv.data[0]

    if doc_type == "invoice":
        pdf_bytes = generate_invoice_pdf(invoice)
        filename = f"Invoice_{invoice['invoice_number']}.pdf"
    elif doc_type == "receipt":
        pdf_bytes = generate_receipt_pdf(invoice)
        filename = f"Receipt_{invoice['invoice_number']}.pdf"
    elif doc_type == "statement":
        all_inv = db.table("invoices")\
            .select("*, payments(*)")\
            .eq("client_id", invoice["client_id"])\
            .order("invoice_date")\
            .execute()
        pdf_bytes = generate_statement_pdf(all_inv.data, invoice["clients"])
        filename = f"Statement_{invoice['clients']['full_name'].replace(' ', '_')}.pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid document type")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
