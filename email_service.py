import resend
import os
import base64
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf, COMPANY
from database import get_db
from utils import sanitize_client_address
import logging

# Set up logging
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "sales@eximps-cloves.com")

# CLIENT CC RECIPIENTS
CC_LEGAL = os.getenv("CC_LEGAL")
CC_CEO = os.getenv("CC_CEO")
CC_OPERATIONS = os.getenv("CC_OPERATIONS")
CLIENT_CC_RECIPIENTS = [email for email in [CC_LEGAL, CC_CEO, CC_OPERATIONS] if email]

def _b64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode()

def _welcome_html(client: dict, property_name: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
    from routers.analytics import log_activity
    client_id = client.get("id")
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        res = resend.Emails.send({
            "from": f"Eximp & Cloves <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "sales@eximps-cloves.com",
            "subject": "Welcome to Eximp & Cloves!",
            "html": _welcome_html(client_sanitized, property_name)
        })
        
        await log_activity(
            "email_sent",
            f"Welcome email successfully sent to {client_name} ({email_addr})",
            "system",
            client_id=client_id
        )
        return res
    except Exception as e:
        logger.error(f"Error sending welcome email to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send welcome email to {client_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client_id,
            metadata={"error": str(e), "email_type": "welcome"}
        )
        return None

def _invoice_html(invoice: dict, client: dict) -> str:
    amount = float(invoice["amount"])
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        pdf = generate_invoice_pdf(invoice)
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Invoice {invoice_no} — Eximp & Cloves",
            "html": _invoice_html(invoice, client_sanitized),
            "attachments": [{"filename": f"Invoice_{invoice_no}.pdf", "content": list(pdf)}],
        })
        
        await log_activity(
            "email_sent",
            f"Invoice {invoice_no} successfully sent to {client_name} ({email_addr})",
            sent_by,
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending invoice {invoice_no} to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send invoice {invoice_no} to {client_name} ({email_addr}): {str(e)}",
            sent_by,
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "invoice"}
        )
        return None


async def send_receipt_email(invoice: dict, client: dict, sent_by: str):
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        pdf = generate_receipt_pdf(invoice)
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Payment Receipt — {invoice_no}",
            "html": _receipt_html(invoice, client_sanitized),
            "attachments": [{"filename": f"Receipt_{invoice_no}.pdf", "content": list(pdf)}],
        })
        
        await log_activity(
            "email_sent",
            f"Receipt for {invoice_no} successfully sent to {client_name} ({email_addr})",
            sent_by,
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending receipt for {invoice_no} to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send receipt for {invoice_no} to {client_name} ({email_addr}): {str(e)}",
            sent_by,
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "receipt"}
        )
        return None


async def send_statement_email(invoices: list, client: dict, sent_by: str):
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        pdf = generate_statement_pdf(invoices, client_sanitized)
        total_invoiced = sum(float(i["amount"]) for i in invoices)
        total_paid = sum(float(p["amount"]) for inv in invoices for p in (inv.get("payments") or []) if not p.get("is_voided"))
        balance = total_invoiced - total_paid
    
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Statement of Account — {client_name}",
            "html": _statement_html(client_sanitized, total_invoiced, total_paid, balance),
            "attachments": [{"filename": f"Statement_{client_name.replace(' ', '_')}.pdf", "content": list(pdf)}],
        })
        
        await log_activity(
            "email_sent",
            f"Statement of Account successfully sent to {client_name} ({email_addr})",
            sent_by,
            client_id=client.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending statement to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send statement to {client_name} ({email_addr}): {str(e)}",
            sent_by,
            client_id=client.get("id"),
            metadata={"error": str(e), "email_type": "statement"}
        )
        return None


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
    from routers.analytics import log_activity
    admin_email = os.getenv("ADMIN_ALERT_EMAIL", FROM_EMAIL)
    client_name = client.get("full_name", "New Client")
    invoice_no = invoice.get("invoice_number", "Unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        res = resend.Emails.send({
            "from": f"EC Systems <{FROM_EMAIL}>",
            "to": [admin_email],
            "subject": f"New Subscription — {client_name} — {invoice_no}",
            "html": _admin_alert_html(invoice, client_sanitized)
        })
        
        await log_activity(
            "admin_alert_sent",
            f"Admin alert for {client_name} sent to {admin_email}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending admin alert for {invoice_no}: {e}")
        await log_activity(
            "admin_alert_failed",
            f"FAILED to send admin alert to {admin_email} for {client_name}: {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e)}
        )
        return None


def _rejection_html(invoice: dict, client: dict, reason: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "Unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "sales@eximps-cloves.com",
            "subject": f"Action Required — Payment Verification Issue | Eximp & Cloves",
            "html": _rejection_html(invoice, client_sanitized, reason)
        })
        
        await log_activity(
            "email_sent",
            f"Rejection email for {invoice_no} sent to {client_name} ({email_addr})",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending rejection email for {invoice_no} to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send rejection email for {invoice_no} to {client_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "rejection"}
        )
        return None


async def send_receipt_and_statement_email(invoice: dict, client: dict, invoices: list):
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "Unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        receipt_pdf = generate_receipt_pdf(invoice)
        statement_pdf = generate_statement_pdf(invoices, client_sanitized)
    
        # Combine receipt and statement content into a nice hybrid HTML or just use receipt HTML with a mention
        html = _receipt_html(invoice, client_sanitized).replace(
            "The full receipt PDF is attached to this email.",
            "Your payment receipt and latest statement of account are attached to this email."
        )
    
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Payment Confirmed & Documents attached — {invoice_no}",
            "html": html,
            "attachments": [
                {"filename": f"Receipt_{invoice_no}.pdf", "content": list(receipt_pdf)},
                {"filename": f"Statement_{client_name.replace(' ', '_')}.pdf", "content": list(statement_pdf)}
            ],
        })
        
        await log_activity(
            "email_sent",
            f"Receipt & Statement for {invoice_no} successfully sent to {client_name} ({email_addr})",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending receipt/statement for {invoice_no} to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send receipt/statement for {invoice_no} to {client_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "receipt_statement"}
        )
        return None


def _void_html(invoice: dict, client: dict, reason: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "Unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Important Notice — Receipt Correction | Eximp & Cloves",
            "html": _void_html(invoice, client_sanitized, reason)
        })
        
        await log_activity(
            "email_sent",
            f"Void notification for {invoice_no} successfully sent to {client_name} ({email_addr})",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending void notification for {invoice_no} to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send void notification for {invoice_no} to {client_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "void"}
        )
        return None

def _report_html(message: str) -> str:
    msg_html = f'<p style="color: #333; margin: 20px 0;">{message}</p>' if message else ''
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
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
    from routers.analytics import log_activity
    try:
        res = resend.Emails.send({
            "from": f"Eximp & Cloves <{FROM_EMAIL}>",
            "to": emails,
            "subject": subject,
            "html": _report_html(message),
            "attachments": [attachment]
        })
        
        await log_activity(
            "email_sent",
            f"Financial report '{subject}' successfully sent to {len(emails)} recipients",
            sent_by,
            metadata={"recipients": emails}
        )
        return res
    except Exception as e:
        logger.error(f"Error sending report email '{subject}': {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send financial report '{subject}': {str(e)}",
            sent_by,
            metadata={"error": str(e), "email_type": "report", "recipients": emails}
        )
        return None


def _commission_html(rep: dict, client: dict, invoice: dict, earning: dict) -> str:
    amount = float(earning["payment_amount"])
    rate = float(earning["commission_rate"])
    comm = float(earning["commission_amount"])
    
    balance = float(invoice.get("balance_due", 0))
    balance_note = ""
    if balance > 0:
        balance_note = f"""
        <div style="background: #f9f9f9; padding: 12px; margin-top: 20px; font-size: 13px; color: #555; border-left: 3px solid #F5A623;">
          <strong>Note:</strong> This client has a remaining balance of NGN {balance:,.2f} due by {invoice.get('due_date', 'N/A')}. 
          Additional commission will be earned when further payments are verified.
        </div>"""
        
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{rep.get('name', 'Rep')}</strong>,</p>
        <p style="color: #555;">Great news! A payment has been verified for one of your clients, and your commission has been recorded.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee; color: #777;">Client:</td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; color: #333;"><strong>{client.get('full_name')}</strong></td></tr>
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee; color: #777;">Property:</td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; color: #333;">{invoice.get('property_name')}</td></tr>
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee; color: #777;">Invoice:</td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; color: #333;">{invoice.get('invoice_number')}</td></tr>
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #333; color: #777;">Payment:</td><td style="padding: 8px 0; border-bottom: 1px solid #333; text-align: right; color: #333;"><strong>NGN {amount:,.2f}</strong></td></tr>
        </table>
        
        <div style="background: #1A1A1A; padding: 20px; text-align: center; color: #fff; border-radius: 6px;">
          <p style="margin: 0; font-size: 12px; color: #aaa; text-transform: uppercase;">Your Commission</p>
          <p style="margin: 8px 0 0; font-size: 28px; color: #27ae60; font-weight: bold;">NGN {comm:,.2f}</p>
          <p style="margin: 4px 0 0; font-size: 13px; color: #888;">Rate applied: {rate}%</p>
        </div>
        
        {balance_note}
        
        <p style="color: #555; font-size: 13px; margin-top: 24px;">Your commission will be processed in the next payout cycle. Contact finance@eximps-cloves.com for any enquiries.</p>
        
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""

async def send_commission_earned_email(rep: dict, client: dict, invoice: dict, earning: dict):
    from routers.analytics import log_activity
    if not rep.get("email"):
        return
        
    email_addr = rep["email"]
    rep_name = rep.get("name", "Rep")
    client_name = client.get("full_name", "Client")
    
    try:
        res = resend.Emails.send({
            "from": f"Eximp & Cloves <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "finance@eximps-cloves.com",
            "subject": f"Commission Earned — {client_name} | Eximp & Cloves",
            "html": _commission_html(rep, client, invoice, earning)
        })
        
        await log_activity(
            "email_sent",
            f"Commission earned email for {client_name} sent to {rep_name} ({email_addr})",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending commission email to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send commission email to {rep_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "commission"}
        )
        return None

def _commission_void_html(rep: dict, client: dict, invoice: dict, earning: dict, reason: str) -> str:
    amount = float(earning["commission_amount"])
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{rep.get('name', 'Rep')}</strong>,</p>
        <p style="color: #555;">This is to inform you that a previously recorded commission for <strong>{client.get('full_name')}</strong> (Invoice {invoice.get('invoice_number')}) has been <strong>voided</strong>.</p>
        
        <div style="background: #fff5f5; border-left: 4px solid #e74c3c; padding: 16px; margin: 20px 0; font-size: 14px; color: #c0392b;">
          <strong>Void Reason:</strong> {reason}
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee; color: #777;">Amount Reversed:</td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; color: #e74c3c;"><strong>-NGN {amount:,.2f}</strong></td></tr>
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee; color: #777;">Property:</td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; color: #333;">{invoice.get('property_name')}</td></tr>
        </table>
        
        <p style="color: #555; font-size: 13px; margin-top: 24px;">If you have any questions regarding this adjustment, please contact the Finance Department at finance@eximps-cloves.com.</p>
        
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""

async def send_commission_void_email(rep: dict, client: dict, invoice: dict, earning: dict, reason: str):
    from routers.analytics import log_activity
    if not rep.get("email"):
        return
        
    email_addr = rep["email"]
    rep_name = rep.get("name", "Rep")
    client_name = client.get("full_name", "Client")
    
    try:
        res = resend.Emails.send({
            "from": f"Eximp & Cloves <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "finance@eximps-cloves.com",
            "subject": f"Notice: Commission Record Adjusted (Voided) | Eximp & Cloves",
            "html": _commission_void_html(rep, client, invoice, earning, reason)
        })
        
        await log_activity(
            "email_sent",
            f"Commission void notice for {client_name} sent to {rep_name} ({email_addr})",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending commission void email to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send commission void email to {rep_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "commission_void"}
        )
        return None

async def send_refund_receipt_email(invoice: dict, payment: dict, client: dict):
    from routers.analytics import log_activity
    from pdf_service import generate_refund_receipt_pdf
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "Unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        pdf = generate_refund_receipt_pdf(payment, invoice, client_sanitized)
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Refund Receipt — {invoice_no}",
            "html": _refund_receipt_html(invoice, payment, client_sanitized),
            "attachments": [{"filename": f"Refund_Receipt_{invoice_no}.pdf", "content": list(pdf)}],
        })
        
        await log_activity(
            "email_sent",
            f"Refund receipt for {invoice_no} sent to {client_name} ({email_addr})",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id")
        )
        return res
    except Exception as e:
        logger.error(f"Error sending refund receipt for {invoice_no} to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send refund receipt for {invoice_no} to {client_name} ({email_addr}): {str(e)}",
            "system",
            client_id=client.get("id"),
            invoice_id=invoice.get("id"),
            metadata={"error": str(e), "email_type": "refund_receipt"}
        )
        return None

def _refund_receipt_html(invoice: dict, payment: dict, client: dict) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee;">
      <div style="background: #1A1A1A; padding: 30px; text-align: center;">
        <h1 style="color: #E74C3C; margin: 0; font-size: 24px;">Refund Receipt</h1>
        <p style="color: #aaa; margin: 10px 0 0;">Transaction: {payment['reference']}</p>
      </div>
      <div style="padding: 30px; background: #fff;">
        <p style="color: #333; font-size: 16px;">Dear {client['full_name']},</p>
        <p style="color: #555; line-height: 1.6;">This is to confirm that a refund of <strong>NGN {float(payment['amount']):,.2f}</strong> has been processed for your account regarding Invoice <strong>{invoice['invoice_number']}</strong>.</p>
        
        <div style="background: #f9f9f9; border-radius: 8px; padding: 20px; margin: 25px 0; border: 1px solid #eee;">
          <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
            <tr><td style="padding: 8px 0; color: #888;">Refund Amount</td><td style="padding: 8px 0; text-align: right; font-weight: bold; color: #E74C3C;">NGN {float(payment['amount']):,.2f}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">Refund Date</td><td style="padding: 8px 0; text-align: right;">{payment['payment_date']}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">Reference</td><td style="padding: 8px 0; text-align: right; font-weight: bold;">{payment['reference']}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">Method</td><td style="padding: 8px 0; text-align: right;">{payment['payment_method']}</td></tr>
          </table>
        </div>
        
        <p style="color: #555; line-height: 1.6;">If you have any questions, please contact our finance department.</p>
        <p style="color: #333; margin-top: 30px;">Best regards,<br><strong>The Eximp & Cloves Team</strong></p>
      </div>
      <div style="background: #f4f4f4; padding: 20px; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee;">
        Eximp & Cloves Infrastructure Limited | RC 8311800
      </div>

def _commission_paid_html(rep: dict, batch: dict) -> str:
    amount = float(batch["total_amount"])
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
      </div>
      <div style="background: #27ae60; padding: 12px 24px;">
        <h2 style="color: #fff; margin: 0; font-size: 16px;">Commission Payout Successful</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{rep.get('name', 'Rep')}</strong>,</p>
        <p style="color: #555;">We are pleased to inform you that a commission payout has been processed for you.</p>
        
        <div style="background: #f9f9f9; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
          <p style="color: #888; margin: 0 0 8px; font-size: 13px; text-transform: uppercase;">Amount Paid</p>
          <p style="color: #27ae60; font-size: 32px; font-weight: bold; margin: 0;">NGN {amount:,.2f}</p>
          <hr style="border-color: #ddd; margin: 16px 0;">
          <p style="color: #555; font-size: 13px;">Reference: <strong>{batch.get('reference', 'N/A')}</strong></p>
          <p style="color: #555; font-size: 12px;">Date: {batch.get('paid_at', '')[:10]}</p>
        </div>
        
        <p style="color: #555; font-size: 13px;">Please check your bank account or contact the Finance Department if you have any questions.</p>
        <p style="color: #555; font-size: 13px;">Keep up the great work!</p>
        
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""

async def send_commission_paid_email(rep: dict, batch: dict):
    from routers.analytics import log_activity
    if not rep.get("email"):
        return
        
    email_addr = rep["email"]
    rep_name = rep.get("name", "Rep")
    
    try:
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "finance@eximps-cloves.com",
            "subject": f"Commission Payout Processed | Eximp & Cloves",
            "html": _commission_paid_html(rep, batch)
        })
        
        await log_activity(
            "email_sent",
            f"Commission payout email for NGN {batch['total_amount']:,.2f} sent to {rep_name} ({email_addr})",
            "system"
        )
        return res
    except Exception as e:
        logger.error(f"Error sending payout email to {email_addr}: {e}")
        return None
