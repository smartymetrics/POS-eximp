from xhtml2pdf import pisa
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import io
import os
import requests
import base64
from urllib.parse import urlparse, parse_qs
from utils import sanitize_client_address

env = Environment(loader=FileSystemLoader("pdf_templates"))

def _get_google_drive_direct_link(url):
    """Converts a Google Drive viewer/sharing link to a direct download link."""
    if not url or "drive.google.com" not in url:
        return url
    try:
        file_id = None
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url:
            parsed = urlparse(url)
            file_id = parse_qs(parsed.query).get("id", [None])[0]
        elif "/open?" in url:
            parsed = urlparse(url)
            file_id = parse_qs(parsed.query).get("id", [None])[0]
        
        if file_id:
            # Bypass HTML interceptors on large/unscanned files using the thumbnail API
            return f"https://drive.google.com/thumbnail?sz=w800&id={file_id}"
    except Exception:
        pass
    return url


def _get_image_as_base64(url):
    """Fetches an image and returns (base64_string, content_type)."""
    try:
        direct_url = _get_google_drive_direct_link(url)
        res = requests.get(direct_url, timeout=10)
        
        content_type = res.headers.get("Content-Type", "image/jpeg")
        if res.ok and content_type.startswith("image/"):
            b64_str = base64.b64encode(res.content).decode("utf-8")
            return b64_str, content_type
        else:
            print(f"Skipping signature fetch: Expected image from {url} but got {content_type}")
    except Exception as e:
        print(f"Failed to fetch image from {url}: {e}")
    return None, None

def get_company_logo_base64():
    import base64
    try:
        with open("logo.png", "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        pass
    return ""

def get_authorized_stamp_base64():
    """Fetches the official authority stamp from Supabase storage."""
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        return ""
    # Constructed public URL for the stamp
    stamp_url = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"
    b64, _ = _get_image_as_base64(stamp_url)
    if b64:
        return f"data:image/png;base64,{b64}"
    return ""

def get_authorized_seal_base64():
    """Fetches the official company seal from Supabase."""
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        return ""
    url = f"{supabase_url}/storage/v1/object/public/signatures/authority/seal.png"
    b64, _ = _get_image_as_base64(url)
    if b64:
        return f"data:image/png;base64,{b64}"
    return ""

COMPANY = {
    "name": "Eximp & Cloves Infrastructure Limited",
    "rc": "8311800",
    "address": "57B, Isaac John Street, Yaba, Lagos, Nigeria",
    "phone": "+234 912 686 4383",
    "email": "admin@eximps-cloves.com",
    "website": "www.eximps-cloves.com",
    "primary_color": "#F5A623",
    "dark_color": "#1A1A1A",
    "logo_b64": get_company_logo_base64(),
    "stamp_b64": get_authorized_stamp_base64(),
    "seal_b64": get_authorized_seal_base64(),
    "logo_url": "https://eximpcloves.vercel.app/light%20theme%20logo.png",
}


def format_currency(amount):
    """Format as NGN currency"""
    if amount is None:
        return "NGN 0.00"
    return f"NGN {float(amount):,.2f}"


def _html_to_pdf(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using xhtml2pdf."""
    buffer = io.BytesIO()
    result = pisa.CreatePDF(
        src=html_content,
        dest=buffer,
        encoding="utf-8"
    )
    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} errors")
    return buffer.getvalue()




def generate_invoice_pdf(invoice: dict) -> bytes:
    template = env.get_template("invoice.html")
    client = sanitize_client_address(invoice.get("clients", {}).copy())
    
    # Handle Client Digital Signature
    signature_base64 = None
    signature_mime = "image/png"
    
    # 1. Try to fetch from Supabase first (as our system prioritize this now)
    invoice_no = invoice.get("invoice_number", "unknown")
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url and invoice_no != "unknown":
        stored_path = f"customer_signatures/sig_{invoice_no}.png"
        url = f"{supabase_url}/storage/v1/object/public/signatures/{stored_path}"
        b64, mime = _get_image_as_base64(url)
        if b64:
            signature_base64 = b64
            signature_mime = mime

    # 2. Fallback to signature_url in DB if Supabase fetch failed
    if not signature_base64 and invoice.get("signature_url"):
        url = invoice["signature_url"]
        if url.startswith("data:") and ";base64," in url:
            header, raw = url.split(";base64,", 1)
            signature_mime = header.split("data:")[-1]
            signature_base64 = raw
        elif url.startswith("data:image/"):
            signature_base64 = url.split(",")[-1]
            signature_mime = url.split(";")[0].split(":")[-1]
        else:
            b64, mime = _get_image_as_base64(url)
            if b64:
                signature_base64 = b64
                signature_mime = mime
        
    html_content = template.render(
        company=COMPANY,
        invoice=invoice,
        client=client,
        signature_img_base64=signature_base64,
        signature_mime=signature_mime,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _html_to_pdf(html_content)



def generate_receipt_pdf(invoice: dict) -> bytes:
    template = env.get_template("receipt.html")
    client = sanitize_client_address(invoice.get("clients", {}).copy())
    # Only include standard payments (not refunds) in the payment receipt
    raw_payments = invoice.get("payments", [])
    payments = [p for p in raw_payments if p.get("payment_type") != "refund"]
    
    # Handle Client Digital Signature
    signature_base64 = None
    signature_mime = "image/png"
    
    # 1. Try to fetch from Supabase first
    invoice_no = invoice.get("invoice_number", "unknown")
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url and invoice_no != "unknown":
        stored_path = f"customer_signatures/sig_{invoice_no}.png"
        url = f"{supabase_url}/storage/v1/object/public/signatures/{stored_path}"
        b64, mime = _get_image_as_base64(url)
        if b64:
            signature_base64 = b64
            signature_mime = mime

    # 2. Fallback to signature_url in DB
    if not signature_base64 and invoice.get("signature_url"):
        url = invoice["signature_url"]
        if url.startswith("data:") and ";base64," in url:
            header, raw = url.split(";base64,", 1)
            signature_mime = header.split("data:")[-1]
            signature_base64 = raw
        elif url.startswith("data:image/"):
            signature_base64 = url.split(",")[-1]
            signature_mime = url.split(";")[0].split(":")[-1]
        else:
            b64, mime = _get_image_as_base64(url)
            if b64:
                signature_base64 = b64
                signature_mime = mime
        
    html_content = template.render(
        company=COMPANY,
        invoice=invoice,
        client=client,
        payments=payments,
        signature_img_base64=signature_base64,
        signature_mime=signature_mime,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _html_to_pdf(html_content)



def generate_statement_pdf(invoices: list, client: dict) -> bytes:
    template = env.get_template("statement.html")
    client = sanitize_client_address(client.copy())

    # Build transaction timeline
    transactions = []
    running_balance = 0.0

    for inv in invoices:
        running_balance += float(inv["amount"])
        transactions.append({
            "date": inv["invoice_date"],
            "type": "Invoice",
            "ref": inv["invoice_number"],
            "amount": float(inv["amount"]),
            "payment": None,
            "balance": running_balance,
        })
        for pay in (inv.get("payments") or []):
            if pay.get("is_voided"):
                continue
            
            p_type = pay.get("payment_type", "payment")
            p_amount = float(pay["amount"])
            
            if p_type == "refund":
                running_balance += p_amount
                transactions.append({
                    "date": pay["payment_date"],
                    "type": "Refund",
                    "ref": pay["reference"],
                    "amount": p_amount,
                    "payment": None,
                    "balance": running_balance,
                })
            else:
                running_balance -= p_amount
                transactions.append({
                    "date": pay["payment_date"],
                    "type": "Payment",
                    "ref": pay["reference"],
                    "amount": None,
                    "payment": p_amount,
                    "balance": running_balance,
                })

    total_invoiced = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(
        float(p["amount"]) if p.get("payment_type", "payment") == "payment" else -float(p["amount"])
        for i in invoices
        for p in (i.get("payments") or []) if not p.get("is_voided")
    )

    html_content = template.render(
        company=COMPANY,
        client=client,
        transactions=transactions,
        total_invoiced=total_invoiced,
        total_paid=total_paid,
        balance_due=total_invoiced - total_paid,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y"),
        period_start=invoices[0]["invoice_date"] if invoices else "",
        period_end=invoices[-1]["invoice_date"] if invoices else "",
    )
    return _html_to_pdf(html_content)


def generate_refund_receipt_pdf(payment: dict, invoice: dict, client: dict = None) -> bytes:
    template = env.get_template("refund_receipt.html")
    # Use provided client or fetch from nested invoice data
    if not client:
        client = sanitize_client_address(invoice.get("clients", {}).copy())
    else:
        client = sanitize_client_address(client.copy())
    
    # Handle Client Digital Signature
    signature_base64 = None
    signature_mime = "image/png"
    
    # 1. Try to fetch from Supabase first
    invoice_no = invoice.get("invoice_number", "unknown")
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url and invoice_no != "unknown":
        stored_path = f"customer_signatures/sig_{invoice_no}.png"
        url = f"{supabase_url}/storage/v1/object/public/signatures/{stored_path}"
        b64, mime = _get_image_as_base64(url)
        if b64:
            signature_base64 = b64
            signature_mime = mime

    # 2. Fallback to signature_url in DB
    if not signature_base64 and invoice.get("signature_url"):
        url = invoice["signature_url"]
        if url.startswith("data:") and ";base64," in url:
            header, raw = url.split(";base64,", 1)
            signature_mime = header.split("data:")[-1]
            signature_base64 = raw
        elif url.startswith("data:image/"):
            signature_base64 = url.split(",")[-1]
            signature_mime = url.split(";")[0].split(":")[-1]
        else:
            b64, mime = _get_image_as_base64(url)
            if b64:
                signature_base64 = b64
                signature_mime = mime

    html_content = template.render(
        company=COMPANY,
        payment=payment,
        invoice=invoice,
        client=client,
        signature_img_base64=signature_base64,
        signature_mime=signature_mime,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _html_to_pdf(html_content)