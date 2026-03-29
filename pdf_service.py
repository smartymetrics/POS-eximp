from xhtml2pdf import pisa
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import io
import os
import re
import requests
import base64
from urllib.parse import urlparse, parse_qs
from utils import sanitize_client_address

env = Environment(loader=FileSystemLoader("pdf_templates"))

from concurrent.futures import ThreadPoolExecutor, as_completed

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
            return f"https://drive.google.com/thumbnail?sz=w800&id={file_id}"
    except Exception:
        pass
    return url


def _compress_image_bytes(img_bytes, max_width=400, quality=75):
    """Compress and resize an image to reduce its size for PDF embedding."""
    try:
        from PIL import Image as PILImage
        with PILImage.open(io.BytesIO(img_bytes)) as img:
            # Convert to RGBA to support transparency
            if img.mode not in ('RGB', 'RGBA', 'L'):
                img = img.convert('RGBA')
            # Downscale if wider than max_width
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), PILImage.LANCZOS)
            # Save as PNG (lossless, good for signatures)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), "image/png"
    except Exception:
        return img_bytes, None  # Return original if compression fails


def _get_image_as_base64(url):
    """Fetches an image, compresses it, and returns (base64_string, content_type)."""
    try:
        direct_url = _get_google_drive_direct_link(url)
        res = requests.get(direct_url, timeout=10)  # Reduced from 10s to 5s
        
        content_type = res.headers.get("Content-Type", "image/jpeg")
        if res.ok and content_type.startswith("image/"):
            img_bytes, compressed_mime = _compress_image_bytes(res.content)
            mime = compressed_mime or content_type
            b64_str = base64.b64encode(img_bytes).decode("utf-8")
            return b64_str, mime
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

def _get_parallel_images(urls_map):
    """
    Fetches multiple images in parallel.
    urls_map: dict of {name: url}
    returns: dict of {name: (base64, mime)}
    """
    results = {}
    with ThreadPoolExecutor(max_workers=len(urls_map)) as executor:
        future_to_name = {executor.submit(_get_image_as_base64, url): name for name, url in urls_map.items()}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = (None, None)
    return results

def get_company_context():
    """Returns the company context with fresh stamp and seal fetched in each call."""
    supabase_url = os.getenv("SUPABASE_URL")
    urls = {}
    if supabase_url:
        urls["stamp"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"
        urls["seal"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/seal.png"
    
    fetched = _get_parallel_images(urls)
    
    stamp_b64, _ = fetched.get("stamp", (None, None))
    seal_b64, _ = fetched.get("seal", (None, None))
    
    return {
        "name": "Eximp & Cloves Infrastructure Limited",
        "rc": "8311800",
        "address": "57B, Isaac John Street, Yaba, Lagos, Nigeria",
        "phone": "+234 912 686 4383",
        "email": "admin@eximps-cloves.com",
        "website": "www.eximps-cloves.com",
        "primary_color": "#F5A623",
        "dark_color": "#1A1A1A",
        "logo_b64": get_company_logo_base64(),
        "stamp_b64": f"data:image/png;base64,{stamp_b64}" if stamp_b64 else "",
        "seal_b64": f"data:image/png;base64,{seal_b64}" if seal_b64 else "",
        "logo_url": "https://eximpcloves.vercel.app/light%20theme%20logo.png",
    }

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
    "stamp_b64": "", # Placeholder, will be updated in functions
    "seal_b64": "", # Placeholder, will be updated in functions
    "logo_url": "https://eximpcloves.vercel.app/light%20theme%20logo.png",
}

def format_currency(amount):
    """Format as NGN currency"""
    if amount is None:
        return "NGN 0.00"
    return f"NGN {float(amount):,.2f}"

def _sanitize_html_for_pdf(html_content: str) -> str:
    """Remove or rewrite unsupported CSS for xhtml2pdf."""
    # xhtml2pdf struggles with @page blocks and some modern CSS properties
    html_content = re.sub(r'@page\s*\{[^}]*\}', '', html_content, flags=re.S)
    html_content = re.sub(r'transform\s*:\s*[^;]+;', '', html_content, flags=re.I)
    html_content = re.sub(r'position\s*:\s*fixed\s*;?', 'position:absolute;', html_content, flags=re.I)
    html_content = re.sub(r'page-break-after\s*:\s*avoid\s*;?', '', html_content, flags=re.I)
    return html_content


def _html_to_pdf(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using xhtml2pdf."""
    html_content = _sanitize_html_for_pdf(html_content)
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
    
    # 1. Prepare all URLs for parallel fetching
    supabase_url = os.getenv("SUPABASE_URL")
    urls_to_fetch = {}
    
    if supabase_url:
        urls_to_fetch["stamp"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"
        urls_to_fetch["seal"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/seal.png"
        
        invoice_no = invoice.get("invoice_number", "unknown")
        if invoice_no != "unknown":
            urls_to_fetch["signature"] = f"{supabase_url}/storage/v1/object/public/signatures/customer_signatures/sig_{invoice_no}.png"
            
    # Also include the signature_url from DB if it's a remote URL and not a data URI
    db_sig_url = invoice.get("signature_url")
    if db_sig_url and db_sig_url.startswith("http") and "supabase" not in db_sig_url:
        urls_to_fetch["db_signature"] = db_sig_url

    # 2. Fetch all images in parallel
    fetched = _get_parallel_images(urls_to_fetch)
    
    # 3. Process results
    stamp_b64, _ = fetched.get("stamp", (None, None))
    seal_b64, _ = fetched.get("seal", (None, None))
    
    signature_base64 = None
    signature_mime = "image/png"
    
    # Try Supabase signature first
    sig_b64, sig_mime = fetched.get("signature", (None, None))
    if sig_b64:
        signature_base64 = sig_b64
        signature_mime = sig_mime
    # Fallback to DB signature if Supabase failed
    elif "db_signature" in fetched and fetched["db_signature"][0]:
        signature_base64, signature_mime = fetched["db_signature"]
    # Handle data URIs
    elif db_sig_url and db_sig_url.startswith("data:"):
        if ";base64," in db_sig_url:
            header, raw = db_sig_url.split(";base64,", 1)
            signature_mime = header.split("data:")[-1]
            signature_base64 = raw
        else:
            signature_base64 = db_sig_url.split(",")[-1]
            signature_mime = db_sig_url.split(";")[0].split(":")[-1]

    # 4. Build dynamic company context
    comp_ctx = COMPANY.copy()
    comp_ctx["stamp_b64"] = f"data:image/png;base64,{stamp_b64}" if stamp_b64 else ""
    comp_ctx["seal_b64"] = f"data:image/png;base64,{seal_b64}" if seal_b64 else ""

    html_content = template.render(
        company=comp_ctx,
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
    
    # 1. Prepare all URLs for parallel fetching
    supabase_url = os.getenv("SUPABASE_URL")
    urls_to_fetch = {}
    
    if supabase_url:
        urls_to_fetch["stamp"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"
        urls_to_fetch["seal"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/seal.png"
        
        invoice_no = invoice.get("invoice_number", "unknown")
        if invoice_no != "unknown":
            urls_to_fetch["signature"] = f"{supabase_url}/storage/v1/object/public/signatures/customer_signatures/sig_{invoice_no}.png"
            
    db_sig_url = invoice.get("signature_url")
    if db_sig_url and db_sig_url.startswith("http") and "supabase" not in db_sig_url:
        urls_to_fetch["db_signature"] = db_sig_url

    # 2. Fetch all images in parallel
    fetched = _get_parallel_images(urls_to_fetch)
    
    # 3. Process results
    stamp_b64, _ = fetched.get("stamp", (None, None))
    seal_b64, _ = fetched.get("seal", (None, None))
    
    signature_base64 = None
    signature_mime = "image/png"
    
    sig_b64, sig_mime = fetched.get("signature", (None, None))
    if sig_b64:
        signature_base64 = sig_b64
        signature_mime = sig_mime
    elif "db_signature" in fetched and fetched["db_signature"][0]:
        signature_base64, signature_mime = fetched["db_signature"]
    elif db_sig_url and db_sig_url.startswith("data:"):
        if ";base64," in db_sig_url:
            header, raw = db_sig_url.split(";base64,", 1)
            signature_mime = header.split("data:")[-1]
            signature_base64 = raw
        else:
            signature_base64 = db_sig_url.split(",")[-1]
            signature_mime = db_sig_url.split(";")[0].split(":")[-1]

    # 4. Build dynamic company context
    comp_ctx = COMPANY.copy()
    comp_ctx["stamp_b64"] = f"data:image/png;base64,{stamp_b64}" if stamp_b64 else ""
    comp_ctx["seal_b64"] = f"data:image/png;base64,{seal_b64}" if seal_b64 else ""

    html_content = template.render(
        company=comp_ctx,
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

    # 1. Prepare URLs (only stamp and seal for statement)
    supabase_url = os.getenv("SUPABASE_URL")
    urls_to_fetch = {}
    if supabase_url:
        urls_to_fetch["stamp"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"
        urls_to_fetch["seal"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/seal.png"
    
    fetched = _get_parallel_images(urls_to_fetch)
    stamp_b64, _ = fetched.get("stamp", (None, None))
    seal_b64, _ = fetched.get("seal", (None, None))

    # 2. Build dynamic company context
    comp_ctx = COMPANY.copy()
    comp_ctx["stamp_b64"] = f"data:image/png;base64,{stamp_b64}" if stamp_b64 else ""
    comp_ctx["seal_b64"] = f"data:image/png;base64,{seal_b64}" if seal_b64 else ""

    html_content = template.render(
        company=comp_ctx,
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
    if not client:
        client = sanitize_client_address(invoice.get("clients", {}).copy())
    else:
        client = sanitize_client_address(client.copy())
    
    # 1. Prepare all URLs for parallel fetching
    supabase_url = os.getenv("SUPABASE_URL")
    urls_to_fetch = {}
    
    if supabase_url:
        urls_to_fetch["stamp"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"
        urls_to_fetch["seal"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/seal.png"
        
        invoice_no = invoice.get("invoice_number", "unknown")
        if invoice_no != "unknown":
            urls_to_fetch["signature"] = f"{supabase_url}/storage/v1/object/public/signatures/customer_signatures/sig_{invoice_no}.png"
            
    db_sig_url = invoice.get("signature_url")
    if db_sig_url and db_sig_url.startswith("http") and "supabase" not in db_sig_url:
        urls_to_fetch["db_signature"] = db_sig_url

    # 2. Fetch all images in parallel
    fetched = _get_parallel_images(urls_to_fetch)
    
    # 3. Process results
    stamp_b64, _ = fetched.get("stamp", (None, None))
    seal_b64, _ = fetched.get("seal", (None, None))
    
    signature_base64 = None
    signature_mime = "image/png"
    
    sig_b64, sig_mime = fetched.get("signature", (None, None))
    if sig_b64:
        signature_base64 = sig_b64
        signature_mime = sig_mime
    elif "db_signature" in fetched and fetched["db_signature"][0]:
        signature_base64, signature_mime = fetched["db_signature"]
    elif db_sig_url and db_sig_url.startswith("data:"):
        if ";base64," in db_sig_url:
            header, raw = db_sig_url.split(";base64,", 1)
            signature_mime = header.split("data:")[-1]
            signature_base64 = raw
        else:
            signature_base64 = db_sig_url.split(",")[-1]
            signature_mime = db_sig_url.split(";")[0].split(":")[-1]

    # 4. Build dynamic company context
    comp_ctx = COMPANY.copy()
    comp_ctx["stamp_b64"] = f"data:image/png;base64,{stamp_b64}" if stamp_b64 else ""
    comp_ctx["seal_b64"] = f"data:image/png;base64,{seal_b64}" if seal_b64 else ""

    html_content = template.render(
        company=comp_ctx,
        payment=payment,
        invoice=invoice,
        client=client,
        signature_img_base64=signature_base64,
        signature_mime=signature_mime,
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _html_to_pdf(html_content)

def generate_contract_pdf(invoice: dict, client: dict, witnesses: list = None, is_draft: bool = True) -> bytes:
    """
    Generates the Contract of Sale PDF.
    - witnesses: List of dicts with full_name, address, occupation, signature_base64
    - is_draft: If True, adds a 'DRAFT' watermark.
    """
    from database import get_db
    db = get_db()
    
    template = env.get_template("contract.html")
    # Sanitize client address for legal document consistency
    client_sanitized = sanitize_client_address(client.copy())
    
    # 1. Fetch Company Signatures (Director & Secretary)
    sig_res = db.table("company_signatures").select("*").eq("is_active", True).execute()
    company_sigs = {s["role"]: s["signature_base64"] for s in sig_res.data}
    
    # 2. Get Purchaser Signature (Data URI from invoices table)
    purchaser_sig = invoice.get("signature_url") or invoice.get("signature_base64")
    
    # Ensure signatures are prefixed with data:image/ if they are raw base64
    def _ensure_prefix(b64):
        if not b64:
            return None
        b64_str = str(b64).strip()
        if b64_str.startswith("http://") or b64_str.startswith("https://"):
            return b64_str
        if b64_str.startswith("data:"):
            return b64_str
        return "data:image/png;base64," + b64_str

    # 3. Assemble all signatures for the template
    signatures = {
        "director": _ensure_prefix(company_sigs.get("director")),
        "secretary": _ensure_prefix(company_sigs.get("secretary")),
        "purchaser": _ensure_prefix(purchaser_sig),
        "witness1": None,
        "witness2": None
    }
    
    # 4. Map witness signatures if provided
    witness_list = []
    if witnesses:
        for i, w in enumerate(witnesses):
            w_num = i + 1
            if f"witness{w_num}" in signatures:
                signatures[f"witness{w_num}"] = _ensure_prefix(w.get("signature_base64"))
            witness_list.append(w)
    
    # Pad witness list to 2
    while len(witness_list) < 2:
        witness_list.append({"full_name": "PENDING", "address": "PENDING", "occupation": "PENDING"})

    # 5. Build company context for the contract page
    company = COMPANY.copy()

    # 6. Render
    html_content = template.render(
        company=company,
        invoice=invoice,
        client=client_sanitized,
        witnesses=witness_list,
        signatures=signatures,
        is_draft=is_draft,
        format_currency=format_currency
    )
    
    return _html_to_pdf(html_content)
