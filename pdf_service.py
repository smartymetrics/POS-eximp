from weasyprint import HTML as WeasyprintHTML
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


def format_naira(amount):
    """Format as N currency without decimals when possible."""
    if amount is None:
        return "N 0"
    value = float(amount)
    if value.is_integer():
        return f"N {value:,.0f}"
    return f"N {value:,.2f}"


def _html_to_pdf(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint."""
    return WeasyprintHTML(string=html_content).write_pdf()




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

def _resolve_sig_to_data_uri(value: str, max_width: int = 200) -> str | None:
    """
    Accepts a raw base64 string, a data: URI, or an https:// URL.
    Always returns a 'data:image/png;base64,...' URI suitable for xhtml2pdf,
    with the image resized so signatures aren't oversized on the page.
    Returns None if the value is empty or fetch fails.
    """
    if not value:
        return None
    value = str(value).strip()

    # Already a data URI
    if value.startswith("data:"):
        # Re-compress to ensure consistent size
        try:
            header, encoded = value.split(";base64,", 1)
            img_bytes = base64.b64decode(encoded)
            img_bytes, _ = _compress_image_bytes(img_bytes, max_width=max_width)
            return "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")
        except Exception:
            return value  # return original if recompression fails

    # A remote URL
    if value.startswith("http://") or value.startswith("https://"):
        b64, _ = _get_image_as_base64(value)  # already compresses to max_width=400
        if not b64:
            return None
        # Further resize to target width
        try:
            img_bytes = base64.b64decode(b64)
            img_bytes, _ = _compress_image_bytes(img_bytes, max_width=max_width)
            return "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")
        except Exception:
            return "data:image/png;base64," + b64

    # Raw base64 without prefix
    try:
        img_bytes = base64.b64decode(value)
        img_bytes, _ = _compress_image_bytes(img_bytes, max_width=max_width)
        return "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")
    except Exception:
        return None


def generate_contract_pdf(invoice: dict, client: dict, witnesses: list = None, is_draft: bool = True) -> bytes:
    """
    Generates the Contract of Sale PDF.
    - witnesses: List of dicts with full_name, address, occupation, signature_base64
    - is_draft: If True, adds a DRAFT notice.
    """
    from database import get_db
    db = get_db()

    template = env.get_template("contract.html")
    client_sanitized = sanitize_client_address(client.copy())

    # 1. Fetch Company Signatures (Director, Secretary, Lawyer)
    sig_res = db.table("company_signatures").select("*").eq("is_active", True).execute()
    company_sigs = {s["role"]: s["signature_base64"] for s in sig_res.data}
    company_names = {s["role"]: s.get("full_name") for s in sig_res.data}

    # 2. Get Purchaser Signature
    purchaser_sig = (
        invoice.get("contract_signature_url")
        or invoice.get("contract_signature_base64")
        or invoice.get("signature_url")
        or invoice.get("signature_base64")
    )

    # 3. Resolve ALL signatures to base64 data URIs before rendering.
    #    xhtml2pdf cannot fetch remote URLs reliably, so we must embed them.
    #    Authority signatures (director/secretary/lawyer) use max_width=180px —
    #    small enough to look clean in the signature line without distortion.
    #    Purchaser and witness signatures use 160px.
    signatures = {
        "director":  _resolve_sig_to_data_uri(company_sigs.get("director"), max_width=180),
        "secretary": _resolve_sig_to_data_uri(company_sigs.get("secretary"), max_width=180),
        "lawyer":    _resolve_sig_to_data_uri(company_sigs.get("lawyer"),    max_width=180),
        "purchaser": _resolve_sig_to_data_uri(purchaser_sig,                 max_width=160),
        "witness1":  None,
        "witness2":  None,
    }

    # 4. Map witness signatures
    witness_list = []
    if witnesses:
        for i, w in enumerate(witnesses[:2]):
            key = f"witness{i + 1}"
            signatures[key] = _resolve_sig_to_data_uri(w.get("signature_base64"), max_width=160)
            witness_list.append(w)

    # Pad witness list to exactly 2
    while len(witness_list) < 2:
        witness_list.append({"full_name": "PENDING", "address": "PENDING", "occupation": "PENDING"})

    # 5. Build company context
    company = COMPANY.copy()

    # 6. Render HTML
    html_content = template.render(
        company=company,
        invoice=invoice,
        client=client_sanitized,
        witnesses=witness_list,
        signatures=signatures,
        lawyer_name=company_names.get("lawyer") or "Legal Department",
        generated_at=datetime.now().strftime("%d %B %Y"),
        is_draft=is_draft,
        format_currency=format_currency,
        format_naira=format_naira,
    )

    return _html_to_pdf(html_content)