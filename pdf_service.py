from xhtml2pdf import pisa
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import io
import os
import requests
import base64
from urllib.parse import urlparse, parse_qs

env = Environment(loader=FileSystemLoader("pdf_templates"))

COMPANY = {
    "name": "Eximp & Cloves Infrastructure Limited",
    "rc": "RC 8311800",
    "address": "57B, Isaac John Street, Yaba, Lagos, Nigeria",
    "phone": "+234 912 686 4383",
    "email": "admin@eximps-cloves.com",
    "website": "www.eximps-cloves.com",
    "primary_color": "#F5A623",
    "dark_color": "#1A1A1A",
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


def _get_google_drive_direct_link(url):
    """Converts a Google Drive viewer/sharing link to a direct download link."""
    if not url or "drive.google.com" not in url:
        return url
    try:
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
        else:
            parsed = urlparse(url)
            file_id = parse_qs(parsed.query).get("id", [None])[0]
        
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    except Exception:
        pass
    return url


def _get_image_as_base64(url):
    """Fetches an image and returns as base64 string."""
    try:
        direct_url = _get_google_drive_direct_link(url)
        res = requests.get(direct_url, timeout=10)
        if res.ok:
            return base64.b64encode(res.content).decode("utf-8")
    except Exception as e:
        print(f"Failed to fetch image: {e}")
    return None


def generate_invoice_pdf(invoice: dict) -> bytes:
    template = env.get_template("invoice.html")
    client = invoice.get("clients", {})
    
    signature_base64 = None
    if invoice.get("signature_url"):
        signature_base64 = _get_image_as_base64(invoice["signature_url"])
        
    html_content = template.render(
        company=COMPANY,
        invoice=invoice,
        client=client,
        signature_img_base64=signature_base64,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _html_to_pdf(html_content)


def generate_receipt_pdf(invoice: dict) -> bytes:
    template = env.get_template("receipt.html")
    client = invoice.get("clients", {})
    payments = invoice.get("payments", [])
    html_content = template.render(
        company=COMPANY,
        invoice=invoice,
        client=client,
        payments=payments,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _html_to_pdf(html_content)


def generate_statement_pdf(invoices: list, client: dict) -> bytes:
    template = env.get_template("statement.html")

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
            running_balance -= float(pay["amount"])
            transactions.append({
                "date": pay["payment_date"],
                "type": "Payment",
                "ref": pay["reference"],
                "amount": None,
                "payment": float(pay["amount"]),
                "balance": running_balance,
            })

    total_invoiced = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(
        float(p["amount"])
        for i in invoices
        for p in (i.get("payments") or [])
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