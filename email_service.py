import resend
import os
import base64
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf, COMPANY
from database import get_db

resend.api_key = os.getenv("RESEND_API_KEY")
# Force onboarding test domain because eximps-cloves.com is unverified
FROM_EMAIL = "onboarding@resend.dev"

def _b64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode()

def _welcome_html(client: dict, property_name: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        {f'<img src="{COMPANY.get("logo_b64", "")}" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">' if COMPANY.get("logo_b64") else '<h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1><p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>'}
      </div>
      <div style="background: #F5A623; padding: 12px 24px;">
        <h2 style="color: #1A1A1A; margin: 0; font-size: 16px;">Welcome to Eximp & Cloves!</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{client['full_name']}</strong>,</p>
        <p style="color: #555;">Thank you for choosing Eximp & Cloves Infrastructure Limited! We are thrilled to welcome you to our community.</p>
        <p style="color: #555;">We have successfully received your subscription form for <strong>{property_name}</strong>.</p>
        <p style="color: #555;">Our team is currently reviewing your submission and verifying your payment details. Once confirmed, you will receive your official invoice and receipt via email.</p>
        <p style="color: #555;">If you have any questions in the meantime, please reply to this email or contact your Sales Representative.</p>
        <p style="color: #555; margin-top: 30px;">Warm regards,<br>The Eximp & Cloves Team</p>
        <hr style="border-color: #eee;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          www.eximps-cloves.com
        </p>
      </div>
    </div>"""

async def send_welcome_email(client: dict, property_name: str):
    resend.Emails.send({
        "from": f"Eximp & Cloves <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": "Welcome to Eximp & Cloves!",
        "html": _welcome_html(client, property_name)
    })

def _invoice_html(invoice: dict, client: dict) -> str:
    amount = float(invoice["amount"])
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        {f'<img src="{COMPANY.get("logo_b64", "")}" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">' if COMPANY.get("logo_b64") else '<h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1><p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>'}
      </div>
      <div style="background: #F5A623; padding: 12px 24px;">
        <h2 style="color: #1A1A1A; margin: 0; font-size: 16px;">Invoice #{invoice['invoice_number']}</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{client['full_name']}</strong>,</p>
        <p style="color: #555;">Thank you for your business. Please find attached your invoice for the property purchase.</p>
        <div style="background: #1A1A1A; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
          <p style="color: #aaa; margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Invoice Amount</p>
          <p style="color: #F5A623; font-size: 32px; font-weight: bold; margin: 0;">NGN {amount:,.2f}</p>
          <hr style="border-color: #333; margin: 16px 0;">
          <table style="width: 100%; color: #ccc; font-size: 13px;">
            <tr><td style="text-align: left;">Invoice No</td><td style="text-align: right; color: #fff;">{invoice['invoice_number']}</td></tr>
            <tr><td style="text-align: left;">Invoice Date</td><td style="text-align: right; color: #fff;">{invoice['invoice_date']}</td></tr>
            <tr><td style="text-align: left;">Due Date</td><td style="text-align: right; color: #fff;">{invoice['due_date']}</td></tr>
            <tr><td style="text-align: left;">Property</td><td style="text-align: right; color: #fff;">{invoice.get('property_name', 'N/A')}</td></tr>
            <tr><td style="text-align: left;">Terms</td><td style="text-align: right; color: #fff;">{invoice.get('payment_terms', 'Outright')}</td></tr>
          </table>
        </div>
        <p style="color: #555; font-size: 13px;">The full invoice PDF is attached to this email. You can also contact us for any inquiries.</p>
        <hr style="border-color: #eee;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          www.eximps-cloves.com
        </p>
      </div>
    </div>"""


def _receipt_html(invoice: dict, client: dict) -> str:
    paid = float(invoice.get("amount_paid", 0))
    balance = float(invoice.get("balance_due", 0))
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        {f'<img src="{COMPANY.get("logo_b64", "")}" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">' if COMPANY.get("logo_b64") else '<h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1><p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>'}
      </div>
      <div style="background: #27ae60; padding: 12px 24px;">
        <h2 style="color: #fff; margin: 0; font-size: 16px;">✓ Payment Receipt — {invoice['invoice_number']}</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{client['full_name']}</strong>,</p>
        <p style="color: #555;">We have received your payment. Thank you for your business!</p>
        <div style="background: #1A1A1A; border-radius: 8px; padding: 24px; margin: 24px 0;">
          <p style="color: #aaa; margin: 0 0 8px; font-size: 13px; text-transform: uppercase;">Amount Received</p>
          <p style="color: #27ae60; font-size: 32px; font-weight: bold; margin: 0;">NGN {paid:,.2f}</p>
          <hr style="border-color: #333; margin: 16px 0;">
          <table style="width: 100%; color: #ccc; font-size: 13px;">
            <tr><td>Invoice No</td><td style="text-align:right;color:#fff;">{invoice['invoice_number']}</td></tr>
            <tr><td>Property</td><td style="text-align:right;color:#fff;">{invoice.get('property_name','N/A')}</td></tr>
            <tr><td>Balance Due</td><td style="text-align:right;color:{'#27ae60' if balance == 0 else '#F5A623'};">NGN {balance:,.2f}</td></tr>
          </table>
        </div>
        <p style="color: #555; font-size: 13px;">The full receipt PDF is attached to this email.</p>
        <hr style="border-color: #eee;">
        <p style="color: #999; font-size: 12px;">Eximp & Cloves Infrastructure Limited | RC 8311800<br>
        57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383</p>
      </div>
    </div>"""


def _statement_html(client: dict, total_invoiced: float, total_paid: float, balance: float) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        {f'<img src="{COMPANY.get("logo_b64", "")}" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">' if COMPANY.get("logo_b64") else '<h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1><p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>'}
      </div>
      <div style="background: #F5A623; padding: 12px 24px;">
        <h2 style="color: #1A1A1A; margin: 0; font-size: 16px;">Statement of Account</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{client['full_name']}</strong>,</p>
        <p style="color: #555;">Please find your account statement attached as a PDF.</p>
        <div style="background: #f9f9f9; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin: 24px 0;">
          <table style="width: 100%; font-size: 14px;">
            <tr><td style="color:#555; padding: 6px 0;">Total Invoiced</td><td style="text-align:right; font-weight:bold;">NGN {total_invoiced:,.2f}</td></tr>
            <tr><td style="color:#555; padding: 6px 0;">Total Paid</td><td style="text-align:right; color: #27ae60; font-weight:bold;">NGN {total_paid:,.2f}</td></tr>
            <tr style="border-top: 1px solid #ddd;"><td style="color:#333; padding: 10px 0 0; font-weight:bold;">Balance Due</td>
            <td style="text-align:right; font-size:18px; font-weight:bold; color:{'#27ae60' if balance==0 else '#e74c3c'}; padding-top:10px;">NGN {balance:,.2f}</td></tr>
          </table>
        </div>
        <hr style="border-color: #eee;">
        <p style="color: #999; font-size: 12px;">Eximp & Cloves Infrastructure Limited | RC 8311800<br>
        57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383</p>
      </div>
    </div>"""


async def send_invoice_email(invoice: dict, client: dict, sent_by: str):
    pdf = generate_invoice_pdf(invoice)
    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Invoice {invoice['invoice_number']} — Eximp & Cloves",
        "html": _invoice_html(invoice, client),
        "attachments": [{"filename": f"Invoice_{invoice['invoice_number']}.pdf", "content": pdf}],
    })


async def send_receipt_email(invoice: dict, client: dict, sent_by: str):
    pdf = generate_receipt_pdf(invoice)
    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Payment Receipt — {invoice['invoice_number']}",
        "html": _receipt_html(invoice, client),
        "attachments": [{"filename": f"Receipt_{invoice['invoice_number']}.pdf", "content": pdf}],
    })


async def send_statement_email(invoices: list, client: dict, sent_by: str):
    pdf = generate_statement_pdf(invoices, client)
    total_invoiced = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(float(p["amount"]) for inv in invoices for p in (inv.get("payments") or []))
    balance = total_invoiced - total_paid

    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Statement of Account — {client['full_name']}",
        "html": _statement_html(client, total_invoiced, total_paid, balance),
        "attachments": [{"filename": f"Statement_{client['full_name'].replace(' ', '_')}.pdf", "content": pdf}],
    })


def _admin_alert_html(invoice: dict, client: dict) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <h1 style="color: #F5A623; margin: 0; font-size: 20px;">New Form Submission</h1>
      </div>
      <div style="padding: 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">A new subscription has been received via Google Forms.</p>
        <table style="width: 100%; font-size: 13px; border-collapse: collapse; margin: 20px 0;">
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Client</td><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">{client['full_name']}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Email</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{client['email']}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Property</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{invoice['property_name']}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Invoice No</td><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #F5A623;">{invoice['invoice_number']}</td></tr>
          <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Deposit Amount</td><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">NGN {float(invoice['amount_paid']):,.2f}</td></tr>
        </table>
        <div style="text-align: center; margin-top: 24px;">
          <a href="{invoice.get('payment_proof_url', '#')}" target="_blank" style="background: #F5A623; color: #1A1A1A; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">View Payment Proof</a>
        </div>
        <p style="color: #888; font-size: 12px; margin-top: 24px; text-align: center;">Review this submission in the <strong>Pending Verifications</strong> section of the dashboard.</p>
      </div>
    </div>"""


async def send_admin_alert_email(invoice: dict, client: dict):
    admin_email = os.getenv("ADMIN_ALERT_EMAIL", FROM_EMAIL)
    resend.Emails.send({
        "from": f"EC Systems <{FROM_EMAIL}>",
        "to": [admin_email],
        "subject": f"New Subscription — {client['full_name']} — {invoice['invoice_number']}",
        "html": _admin_alert_html(invoice, client)
    })


def _rejection_html(invoice: dict, client: dict, reason: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        {f'<img src="{COMPANY.get("logo_b64", "")}" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">' if COMPANY.get("logo_b64") else '<h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>'}
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{client['full_name']}</strong>,</p>
        <p style="color: #555;">Thank you for your subscription to {invoice.get('property_name', 'our property')}.</p>
        <p style="color: #e74c3c; font-weight: bold; margin: 20px 0;">Unfortunately, we were unable to verify your payment proof for Invoice {invoice['invoice_number']}.</p>
        <div style="background: #fff5f5; border-left: 4px solid #e74c3c; padding: 16px; margin: 20px 0; font-size: 14px; color: #c0392b;">
          <strong>Reason:</strong> {reason}
        </div>
        <p style="color: #555; font-size: 13px;">Please contact us or resubmit your payment evidence at your earliest convenience so we can process your subscription.</p>
        <p style="color: #555; font-size: 13px;">We apologise for any inconvenience.</p>
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""


async def send_rejection_email(invoice: dict, client: dict, reason: str):
    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Action Required — Payment Verification Issue | Eximp & Cloves",
        "html": _rejection_html(invoice, client, reason)
    })


async def send_receipt_and_statement_email(invoice: dict, client: dict, invoices: list):
    receipt_pdf = generate_receipt_pdf(invoice)
    statement_pdf = generate_statement_pdf(invoices, client)
    
    total_invoiced = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(float(p["amount"]) for inv in invoices for p in (inv.get("payments") or []))
    balance = total_invoiced - total_paid

    # Combine receipt and statement content into a nice hybrid HTML or just use receipt HTML with a mention
    html = _receipt_html(invoice, client).replace(
        "The full receipt PDF is attached to this email.",
        "Your payment receipt and latest statement of account are attached to this email."
    )

    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Payment Confirmed & Documents attached — {invoice['invoice_number']}",
        "html": html,
        "attachments": [
            {"filename": f"Receipt_{invoice['invoice_number']}.pdf", "content": list(receipt_pdf)},
            {"filename": f"Statement_{client['full_name'].replace(' ', '_')}.pdf", "content": list(statement_pdf)}
        ],
    })


def _void_html(invoice: dict, client: dict, reason: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        {f'<img src="{COMPANY.get("logo_b64", "")}" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">' if COMPANY.get("logo_b64") else '<h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>'}
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{client['full_name']}</strong>,</p>
        <p style="color: #555;">We are writing to inform you that Receipt for {invoice['invoice_number']}, issued on {invoice['invoice_date']}, has been voided due to an administrative correction.</p>
        <div style="background: #fdf3e3; border-left: 4px solid #f5a623; padding: 16px; margin: 20px 0; font-size: 14px; color: #7d5a0a;">
          <strong>Reason:</strong> {reason}
        </div>
        <p style="color: #555; font-size: 13px;">Please contact our office immediately so we can resolve this matter.</p>
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""


async def send_void_notification_email(invoice: dict, client: dict, reason: str):
    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Important Notice — Receipt Correction | Eximp & Cloves",
        "html": _void_html(invoice, client, reason)
    })

def _report_html(message: str) -> str:
    msg_html = f'<p style="color: #333; margin: 20px 0;">{message}</p>' if message else ''
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>
        <p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>
      </div>
      <div style="background: #F5A623; padding: 12px 24px;">
        <h2 style="color: #1A1A1A; margin: 0; font-size: 16px;">Financial Report Document</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #555;">Please find the requested financial report attached to this email.</p>
        {msg_html}
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""

async def send_report_email(emails: list, subject: str, message: str, attachment: dict, sent_by: str):
    resend.Emails.send({
        "from": f"Eximp & Cloves <{FROM_EMAIL}>",
        "to": emails,
        "subject": subject,
        "html": _report_html(message),
        "attachments": [attachment]
    })
