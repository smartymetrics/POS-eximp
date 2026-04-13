from weasyprint import HTML as WeasyprintHTML
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
    import os
    try:
        # Prioritize PNG as requested for white background documents
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode('utf-8')
        # Fallback to SVG if PNG doesn't exist
        elif os.path.exists("logo.svg"):
            with open("logo.svg", "rb") as f:
                return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode('utf-8')
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

def naira_in_words(amount):
    """Convert numerical amount to Naira words (e.g., Five Million Naira Only)."""
    if amount is None: return "Zero Naira Only"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    thousands = ["", "Thousand", "Million", "Billion"]

    def _convert_less_than_thousand(n):
        if n == 0: return ""
        if n < 10: return units[n]
        if n < 20: return teens[n-10]
        if n < 100: return tens[n//10] + (" " + units[n%10] if n%10 != 0 else "")
        return units[n//100] + " Hundred" + (" and " + _convert_less_than_thousand(n%100) if n%100 != 0 else "")

    num = int(amount)
    if num == 0: return "Zero Naira Only"
    
    res = ""
    group_idx = 0
    temp_num = num
    while temp_num > 0:
        if temp_num % 1000 != 0:
            part = _convert_less_than_thousand(temp_num % 1000)
            res = part + " " + thousands[group_idx] + " " + res
        temp_num //= 1000
        group_idx += 1
    
    return res.strip() + " Naira Only"



def _render_with_weasyprint(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint."""
    return WeasyprintHTML(string=html_content).write_pdf()


def _render_with_xhtml2pdf(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using xhtml2pdf."""
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=result)
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf generation failed with {pisa_status.err} errors")
    return result.getvalue()




def render_invoice_html(invoice: dict) -> str:
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
    if db_sig_url and db_sig_url.startswith("http"):
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
    comp_ctx = get_company_context()
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
    return html_content

def generate_invoice_pdf(invoice: dict) -> bytes:
    html_content = render_invoice_html(invoice)
    return _render_with_xhtml2pdf(html_content)



def render_receipt_html(invoice: dict) -> str:
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
    if db_sig_url and db_sig_url.startswith("http"):
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
    comp_ctx = get_company_context()
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
    return html_content

def generate_receipt_pdf(invoice: dict) -> bytes:
    html_content = render_receipt_html(invoice)
    return _render_with_xhtml2pdf(html_content)



def render_statement_html(invoices: list, client: dict) -> str:
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
    comp_ctx = get_company_context()
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
    return html_content

def generate_statement_pdf(invoices: list, client: dict) -> bytes:
    html_content = render_statement_html(invoices, client)
    return _render_with_xhtml2pdf(html_content)


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
    if db_sig_url and db_sig_url.startswith("http"):
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
    comp_ctx = get_company_context()
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
    return _render_with_xhtml2pdf(html_content)

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


def render_contract_html(invoice: dict, client: dict, witnesses: list = None, is_draft: bool = True, embed_images: bool = True) -> str:
    """
    Renders the Contract of Sale as an HTML string.
    - embed_images: If True, fetches images and converts them to base64 (required for PDF).
                   If False, uses original URLs (faster for web preview).
    """
    from database import get_db
    db = get_db()

    template = env.get_template("contract.html")
    client_sanitized = sanitize_client_address(client.copy())

    # 1. Fetch Company Signatures (Director, Secretary, Lawyer, etc.)
    sig_res = db.table("company_signatures").select("*").eq("is_active", True).execute()
    company_sigs = {s["role"]: s["signature_base64"] for s in sig_res.data}
    company_names = {s["role"]: s.get("full_name") for s in sig_res.data}
    company_addresses = {s["role"]: s.get("address") for s in sig_res.data}
    company_occupations = {s["role"]: s.get("occupation") for s in sig_res.data}

    # 2. Get Purchaser Signature
    purchaser_sig = invoice.get("contract_signature_url")

    # 3. Resolve signatures
    signatures = {
        "director":     None,
        "secretary":    None,
        "lawyer":       None,
        "lawyer_seal":  None,
        "purchaser":    None,
        "witness1":     None,
        "witness2":     None,
    }

    # Priority: Custom Lawyer Seal (per contract) -> Default Company Seal
    seal_to_use = invoice.get("custom_lawyer_seal_url") or company_sigs.get("lawyer_seal")

    if embed_images:
        signatures["director"]     = _resolve_sig_to_data_uri(company_sigs.get("director"),    max_width=180)
        signatures["secretary"]    = _resolve_sig_to_data_uri(company_sigs.get("secretary"),   max_width=180)
        signatures["lawyer"]       = _resolve_sig_to_data_uri(company_sigs.get("lawyer"),      max_width=180)
        signatures["lawyer_seal"]  = _resolve_sig_to_data_uri(seal_to_use,                   max_width=160)
        signatures["purchaser"]    = _resolve_sig_to_data_uri(purchaser_sig,                    max_width=160)
    else:
        # Use direct URLs for faster browser loading
        signatures["director"]     = company_sigs.get("director")
        signatures["secretary"]    = company_sigs.get("secretary")
        signatures["lawyer"]       = company_sigs.get("lawyer")
        signatures["lawyer_seal"]  = seal_to_use
        signatures["purchaser"]    = purchaser_sig


    # 4. Map witness signatures with Company Hierarchy for Witness 2
    witness_list = []
    witness_data = witnesses or []
    
    # Witness 1: The one provided via the link (Client's)
    if len(witness_data) > 0:
        w1 = witness_data[0]
        witness_list.append(w1)
        if embed_images:
            signatures["witness1"] = _resolve_sig_to_data_uri(w1.get("signature_base64"), max_width=160)
        else:
            signatures["witness1"] = w1.get("signature_base64")
    else:
        witness_list.append({"full_name": "PENDING", "address": "PENDING", "occupation": "PENDING"})

    # Witness 2: Priority (Manual Override -> Company Witness -> Lawyer)
    if len(witness_data) > 1:
        # User manually added a second witness or link was signed by two
        w2 = witness_data[1]
        witness_list.append(w2)
        if embed_images:
            signatures["witness2"] = _resolve_sig_to_data_uri(w2.get("signature_base64"), max_width=160)
        else:
            signatures["witness2"] = w2.get("signature_base64")
    else:
        # Automatic Company Witness from roles
        comp_wit_sig = company_sigs.get("company_witness") or company_sigs.get("lawyer")
        comp_wit_name = company_names.get("company_witness") or company_names.get("lawyer") or "COMPANY REPRESENTATIVE"
        comp_wit_addr = company_addresses.get("company_witness") or COMPANY["address"].upper()
        comp_wit_occ = company_occupations.get("company_witness") or ("Company Witness" if company_sigs.get("company_witness") else "Legal Officer")
        
        witness_list.append({
            "full_name": comp_wit_name.upper(),
            "address": comp_wit_addr.upper(),
            "occupation": comp_wit_occ.upper()
        })
        
        if comp_wit_sig:
            if embed_images:
                signatures["witness2"] = _resolve_sig_to_data_uri(comp_wit_sig, max_width=160)
            else:
                signatures["witness2"] = comp_wit_sig

    # 5. Build context

    company = get_company_context()
    if embed_images:
        company["stamp_b64"] = get_authorized_stamp_base64()
    else:
        # Use URL for faster preview
        supabase_url = os.getenv("SUPABASE_URL")
        if supabase_url:
            company["stamp_b64"] = f"{supabase_url}/storage/v1/object/public/signatures/authority/stamp.png"

    invoice_data = invoice.copy()
    if "amount_in_words" not in invoice_data:
        invoice_data["amount_in_words"] = naira_in_words(invoice_data.get("amount"))

    # Evaluate custom execution HTML if it exists, so Jinja logic for signatures is retained
    if invoice_data.get("custom_execution_html"):
        try:
            exec_tmpl = env.from_string(invoice_data["custom_execution_html"])
            invoice_data["custom_execution_html_rendered"] = exec_tmpl.render(
                company=company,
                invoice=invoice_data,
                client=client_sanitized,
                witnesses=witness_list,
                signatures=signatures
            )
        except Exception as e:
            print("Error rendering custom execution HTML:", e)

    return template.render(
        company=company,
        invoice=invoice_data,
        client=client_sanitized,
        witnesses=witness_list,
        signatures=signatures,
        lawyer_name=company_names.get("lawyer") or "GODSLOVE S. NNAJI, ESQ.",
        generated_at=datetime.now().strftime("%d %B %Y"),
        is_draft=is_draft,
        format_currency=format_currency,
        format_naira=format_naira,
        naira_in_words=naira_in_words
    )

def generate_contract_pdf(invoice: dict, client: dict, witnesses: list = None, is_draft: bool = True) -> bytes:
    """Generates the Contract of Sale PDF by first rendering the HTML."""
    html_content = render_contract_html(invoice, client, witnesses, is_draft=is_draft, embed_images=True)
    return _render_with_weasyprint(html_content)

def render_audit_certificate_html(invoice: dict, client: dict, witnesses: list = None) -> str:
    """Renders the Digital Audit Certificate as an HTML string."""
    template = env.get_template("certificate.html")
    
    # Calculate checksum/hash for the document (mock for now or simple hash of ID)
    import hashlib
    doc_hash = hashlib.sha256(f"{invoice['id']}-{invoice['contract_signed_at']}".encode()).hexdigest()
    if not invoice.get("contract_checksum"):
        invoice["contract_checksum"] = doc_hash

    return template.render(
        company=get_company_context(),
        invoice=invoice,
        client=client,
        witnesses=witnesses or [],
        signatures_count=1 + (len(witnesses) if witnesses else 0),
        current_year=datetime.now().year
    )

def generate_audit_certificate_pdf(invoice: dict, client: dict, witnesses: list = None) -> bytes:
    """Generates a standalone Audit Certificate PDF."""
    html_content = render_audit_certificate_html(invoice, client, witnesses)
    return _render_with_weasyprint(html_content)


def generate_payout_receipt_pdf(payout: dict, vendor: dict) -> bytes:
    """
    Generates a professional Payment Advice / Payout Receipt for Vendors or Staff.
    Includes WHT breakdown and digital authorization.
    """
    template = env.get_template("payout_receipt.html")
    
    # Get company context with fresh stamps
    comp_ctx = get_company_context()

    payout_data = payout.copy()
    payout_data["payout_reference"] = payout_data.get("payout_reference") or "Processed"

    html_content = template.render(
        company=comp_ctx,
        payout=payout_data,
        vendor=vendor,
        amount_in_words=naira_in_words(payout_data.get("net_payout_amount") or 0),
        format_currency=format_currency,
        generated_at=datetime.now().strftime("%d %b %Y")
    )
    return _render_with_weasyprint(html_content)


def get_default_contract_html_fragment(invoice: dict, client: dict) -> str:
    """
    Renders just the body (clauses) of the contract so it can be passed to the frontend for editing.
    """
    template = env.get_template("contract_body.html")
    client_sanitized = sanitize_client_address(client.copy())

    invoice_data = invoice.copy()
    if "amount_in_words" not in invoice_data:
        invoice_data["amount_in_words"] = naira_in_words(invoice_data.get("amount"))

    return template.render(
        company=get_company_context(),
        invoice=invoice_data,
        client=client_sanitized,
        format_currency=format_currency,
        format_naira=format_naira,
        generated_at=datetime.now().strftime("%d %B %Y")
    )

def get_default_cover_html_fragment(invoice: dict, client: dict) -> str:
    """
    Renders just the default cover page fragment for the frontend WYSIWYG editor.
    """
    template = env.get_template("cover_middle.html")
    client_sanitized = sanitize_client_address(client.copy())
    
    return template.render(
        company=get_company_context(),
        invoice=invoice,
        client=client_sanitized
    )

def get_default_execution_html_fragment(invoice: dict, client: dict) -> str:
    """
    Renders just the default execution page fragment for the frontend WYSIWYG editor.
    We return the raw file content so Jinja tags aren't wiped out before signatures are added.
    """
    import os
    path = os.path.join("pdf_templates", "execution_body.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<p>Execution placeholder</p>"