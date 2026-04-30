import resend
import os
import base64
import time
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf, COMPANY
from database import get_db, db_execute
from utils import sanitize_client_address
from datetime import datetime, timedelta, timezone
import logging

async def async_resend(payload):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: resend.Emails.send(payload))


# Set up logging
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "sales@eximps-cloves.com")
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://app.eximps-cloves.com")

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
          <a href="https://www.eximps-cloves.com" style="color: #999; text-decoration: none;">www.eximps-cloves.com</a>
        </p>
        <p style="color: #888; font-size: 11px; text-align: center; margin-top: 16px;">
          Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a>
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
        res = await async_resend({
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
          <a href="https://www.eximps-cloves.com" style="color: #999; text-decoration: none;">www.eximps-cloves.com</a>
        </p>
        <p style="color: #888; font-size: 11px; text-align: center; margin-top: 16px;">
          Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a>
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
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color: #999; text-decoration: none;">www.eximps-cloves.com</a>
        </p>
        <p style="color: #C47D0A; font-size: 10px; font-weight: 600; text-align: center; margin-top: 16px; font-family: 'Outfit', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">
          Note: Tax would be deducted by the company and be paid to the Government.
        </p>
        <p style="color: #888; font-size: 11px; text-align: center; margin-top: 16px;">
          Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a>
        </p>
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
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color: #999; text-decoration: none;">www.eximps-cloves.com</a>
        </p>
        <p style="color: #888; font-size: 11px; text-align: center; margin-top: 16px;">
          Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a>
        </p>
      </div>
    </div>"""


async def send_invoice_email(invoice: dict, client: dict, sent_by: str):
    from routers.analytics import log_activity
    email_addr = client.get("email")
    client_name = client.get("full_name", "Client")
    invoice_no = invoice.get("invoice_number", "unknown")
    
    try:
        client_sanitized = sanitize_client_address(client.copy())
        pdf = await db_execute(lambda: generate_invoice_pdf(invoice))
        res = await async_resend({
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
        pdf = await db_execute(lambda: generate_receipt_pdf(invoice))
        res = await async_resend({
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
        pdf = await db_execute(lambda: generate_statement_pdf(invoices, client_sanitized))
        total_invoiced = sum(float(i["amount"]) for i in invoices if i.get("status") != "voided")
        total_paid = sum(float(p["amount"]) for inv in invoices for p in (inv.get("payments") or []) if not p.get("is_voided"))
        balance = total_invoiced - total_paid
    
        res = await async_resend({
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
        res = await async_resend({
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
        res = await async_resend({
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
        receipt_pdf = await db_execute(lambda: generate_receipt_pdf(invoice))
        statement_pdf = await db_execute(lambda: generate_statement_pdf(invoices, client_sanitized))
    
        # Combine receipt and statement content into a nice hybrid HTML or just use receipt HTML with a mention
        html = _receipt_html(invoice, client_sanitized).replace(
            "The full receipt PDF is attached to this email.",
            "Your payment receipt and latest statement of account are attached to this email."
        )
    
        res = await async_resend({
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
        res = await async_resend({
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
        res = await async_resend({
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
    # Handle triad with fallbacks
    rate = float(earning.get("commission_rate") or 0)
    gross_val = float(earning.get("gross_commission") or earning["commission_amount"])
    wht_val = float(earning.get("wht_amount") or 0)
    net_val = float(earning.get("net_commission") or (gross_val - wht_val))
    
    # Calculate effective WHT rate for display
    wht_rate_val = (wht_val / gross_val * 100) if gross_val > 0 else 5.0
    wht_rate_pct = "{:.1f}".format(wht_rate_val)
    
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
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #333; color: #777;">Payment Rec'd:</td><td style="padding: 8px 0; border-bottom: 1px solid #333; text-align: right; color: #333;"><strong>NGN {float(earning['payment_amount']):,.2f}</strong></td></tr>
        </table>
        
        <div style="background: #1A1A1A; padding: 24px; border-radius: 8px; margin: 24px 0;">
          <table style="width: 100%; color: #ccc; font-size: 13px;">
            <tr>
                <td style="text-align: left; padding: 4px 0;">Gross Commission ({rate}%)</td>
                <td style="text-align: right; color: #fff;">NGN {gross_val:,.2f}</td>
            </tr>
            <tr>
                <td style="text-align: left; padding: 4px 0;">WHT Withheld ({wht_rate_pct}%)</td>
                <td style="text-align: right; color: #e74c3c;">-NGN {wht_val:,.2f}</td>
            </tr>
            <tr style="border-top: 1px solid #333;">
                <td style="text-align: left; padding: 12px 0 0; font-weight: bold; color: #aaa; text-transform: uppercase;">Net Payable</td>
                <td style="text-align: right; padding: 12px 0 0; color: #27ae60; font-size: 24px; font-weight: bold;">NGN {net_val:,.2f}</td>
            </tr>
          </table>
          <p style="margin: 16px 0 0; font-size: 10px; color: #666; font-style: italic; text-align: center;">
            * Withholding Tax (WHT) deducted as per the Nigerian Finance Act.
          </p>
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
        res = await async_resend({
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
          <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee; color: #777;">Net Amount Reversed:</td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; color: #e74c3c;"><strong>-NGN {float(earning.get('net_commission') or earning['commission_amount']):,.2f}</strong></td></tr>
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
        res = await async_resend({
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
        pdf = await db_execute(lambda: generate_refund_receipt_pdf(payment, invoice, client_sanitized))
        res = await async_resend({
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


# ─── RECRUITMENT: INTERVIEW INVITATION ────────────────────────────────────────

def _interview_invite_html(candidate_name, job_title, interview_type, scheduled_at, location, interviewer_name, notes):
    notes_block = f'<div style="background:#fdf3e3;border-left:4px solid #F5A623;padding:16px;margin:20px 0;font-size:13px;color:#7d5a0a;"><strong>Preparation Notes:</strong><br>{notes}</div>' if notes else ""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1A1A1A;padding:24px;text-align:center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="max-height:48px;display:block;margin:0 auto;">
      </div>
      <div style="background:#F5A623;padding:12px 24px;">
        <h2 style="color:#1A1A1A;margin:0;font-size:16px;">&#128197; Interview Invitation &mdash; {job_title}</h2>
      </div>
      <div style="padding:32px 24px;background:#fff;border:1px solid #eee;">
        <p style="color:#333;">Dear <strong>{candidate_name}</strong>,</p>
        <p style="color:#555;">We are pleased to invite you to an interview for the position of <strong>{job_title}</strong> at Eximp &amp; Cloves Infrastructure Limited.</p>
        <div style="background:#1A1A1A;border-radius:8px;padding:24px;margin:24px 0;">
          <table style="width:100%;color:#ccc;font-size:14px;border-collapse:collapse;">
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Interview Type</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#F5A623;font-weight:bold;">{interview_type or "Interview"}</td></tr>
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Date &amp; Time</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#fff;font-weight:bold;">{scheduled_at}</td></tr>
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Format / Venue</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#fff;">{location or "To be confirmed"}</td></tr>
            <tr><td style="padding:8px 0;color:#aaa;">Interviewer</td><td style="padding:8px 0;text-align:right;color:#fff;">{interviewer_name or "HR Team"}</td></tr>
          </table>
        </div>
        {notes_block}
        <p style="color:#555;font-size:13px;">Please confirm your attendance by replying to this email. If you need to reschedule, contact us at least 24 hours in advance.</p>
        <p style="color:#555;margin-top:30px;">We look forward to speaking with you.<br>The Eximp &amp; Cloves HR Team</p>
        <hr style="border-color:#eee;margin:24px 0;">
        <p style="color:#999;font-size:12px;margin:0;">Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color:#999;text-decoration:none;">www.eximps-cloves.com</a></p>
      </div>
    </div>"""


async def send_interview_invitation_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    interview_type: str = "Technical",
    scheduled_at_str: str = "",
    location: str = "",
    interviewer_name: str = "",
    notes: str = ""
):
    """Send an interview invitation email to a candidate via Resend."""
    if not candidate_email:
        logger.warning("No candidate email — skipping interview invite.")
        return None
    try:
        res = await async_resend({
            "from": "Eximp & Cloves HR <hr@mail.eximps-cloves.com>",
            "to": [candidate_email],
            "reply_to": "hr@eximps-cloves.com",
            # "cc": ["operations@eximps-cloves.com"],
            "subject": f"Interview Invitation — {job_title} | Eximp & Cloves",
            "html": _interview_invite_html(candidate_name, job_title, interview_type, scheduled_at_str, location, interviewer_name, notes)
        })
        logger.info(f"Interview invite sent to {candidate_email}")
        return res
    except Exception as e:
        logger.error(f"Failed to send interview invite to {candidate_email}: {e}")
        return None


# ─── RECRUITMENT: INTERVIEW CANCELLATION ──────────────────────────────────────

def _interview_cancellation_html(candidate_name, job_title):
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1A1A1A;padding:24px;text-align:center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="max-height:48px;display:block;margin:0 auto;">
      </div>
      <div style="background:#F87171;padding:12px 24px;">
        <h2 style="color:#fff;margin:0;font-size:16px;">&#10006; Interview Cancellation &mdash; {job_title}</h2>
      </div>
      <div style="padding:32px 24px;background:#fff;border:1px solid #eee;">
        <p style="color:#333;">Dear <strong>{candidate_name}</strong>,</p>
        <p style="color:#555;">This is to inform you that your scheduled interview for the position of <strong>{job_title}</strong> has been cancelled.</p>
        <p style="color:#555;font-size:13px;">We apologize for any inconvenience this may cause. If you have any questions, please feel free to reach out to our recruitment team.</p>
        <p style="color:#555;margin-top:30px;">Best regards,<br>The Eximp &amp; Cloves HR Team</p>
        <hr style="border-color:#eee;margin:24px 0;">
        <p style="color:#999;font-size:12px;margin:0;">Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color:#999;text-decoration:none;">www.eximps-cloves.com</a></p>
      </div>
    </div>"""

async def send_interview_cancellation_email(candidate_email: str, candidate_name: str, job_title: str):
    if not candidate_email: return None
    try:
        res = await async_resend({
            "from": "Eximp & Cloves HR <hr@mail.eximps-cloves.com>",
            "to": [candidate_email],
            "reply_to": "hr@eximps-cloves.com",
            # "cc": ["operations@eximps-cloves.com"],
            "subject": f"Interview Cancellation — {job_title} | Eximp & Cloves",
            "html": _interview_cancellation_html(candidate_name, job_title)
        })
        logger.info(f"Cancellation email sent to {candidate_email}")
        return res
    except Exception as e:
        logger.error(f"Failed to send cancellation email to {candidate_email}: {e}")
        return None


# ─── RECRUITMENT: INTERVIEW RESCHEDULE ────────────────────────────────────────

def _interview_reschedule_html(candidate_name, job_title, interview_type, scheduled_at, location, interviewer_name, notes):
    notes_block = f'<div style="background:#fdf3e3;border-left:4px solid #F5A623;padding:16px;margin:20px 0;font-size:13px;color:#7d5a0a;"><strong>Updated Preparation Notes:</strong><br>{notes}</div>' if notes else ""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1A1A1A;padding:24px;text-align:center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="max-height:48px;display:block;margin:0 auto;">
      </div>
      <div style="background:#F5A623;padding:12px 24px;">
        <h2 style="color:#1A1A1A;margin:0;font-size:16px;">&#128197; Interview Rescheduled &mdash; {job_title}</h2>
      </div>
      <div style="padding:32px 24px;background:#fff;border:1px solid #eee;">
        <p style="color:#333;">Dear <strong>{candidate_name}</strong>,</p>
        <p style="color:#555;">Please be advised that your interview for the position of <strong>{job_title}</strong> has been rescheduled to the following new time:</p>
        <div style="background:#1A1A1A;border-radius:8px;padding:24px;margin:24px 0;">
          <table style="width:100%;color:#ccc;font-size:14px;border-collapse:collapse;">
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Interview Type</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#F5A623;font-weight:bold;">{interview_type or "Interview"}</td></tr>
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">NEW Date &amp; Time</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#fff;font-weight:bold;">{scheduled_at}</td></tr>
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Format / Venue</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#fff;">{location or "To be confirmed"}</td></tr>
            <tr><td style="padding:8px 0;color:#aaa;">Interviewer</td><td style="padding:8px 0;text-align:right;color:#fff;">{interviewer_name or "HR Team"}</td></tr>
          </table>
        </div>
        {notes_block}
        <p style="color:#555;font-size:13px;">Please confirm that you have received this update and are available for the new time.</p>
        <p style="color:#555;margin-top:30px;">Best regards,<br>The Eximp &amp; Cloves HR Team</p>
        <hr style="border-color:#eee;margin:24px 0;">
        <p style="color:#999;font-size:12px;margin:0;">Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color:#999;text-decoration:none;">www.eximps-cloves.com</a></p>
      </div>
    </div>"""

async def send_interview_reschedule_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    interview_type: str = "Technical",
    scheduled_at_str: str = "",
    location: str = "",
    interviewer_name: str = "",
    notes: str = ""
):
    if not candidate_email: return None
    try:
        res = await async_resend({
            "from": "Eximp & Cloves HR <hr@mail.eximps-cloves.com>",
            "to": [candidate_email],
            "reply_to": "hr@eximps-cloves.com",
            "subject": f"Interview Rescheduled — {job_title} | Eximp & Cloves",
            "html": _interview_reschedule_html(candidate_name, job_title, interview_type, scheduled_at_str, location, interviewer_name, notes)
        })
        logger.info(f"Reschedule email sent to {candidate_email}")
        return res
    except Exception as e:
        logger.error(f"Failed to send reschedule email to {candidate_email}: {e}")
        return None


# ─── RECRUITMENT: EMPLOYMENT OFFER ──────────────────────────────────────────

def _offer_email_html(candidate_name, job_title, salary, start_date, notes, app_id):
    notes_block = f'<div style="background:#f9f9f9;border-left:4px solid #4ADE80;padding:16px;margin:20px 0;font-size:13px;color:#333;"><strong>Offer Conditions & Notes:</strong><br>{notes}</div>' if notes else ""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1A1A1A;padding:24px;text-align:center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="max-height:48px;display:block;margin:0 auto;">
      </div>
      <div style="background:#4ADE80;padding:12px 24px;">
        <h2 style="color:#1A1A1A;margin:0;font-size:16px;">&#127881; Employment Offer &mdash; {job_title}</h2>
      </div>
      <div style="padding:32px 24px;background:#fff;border:1px solid #eee;">
        <p style="color:#333;">Dear <strong>{candidate_name}</strong>,</p>
        <p style="color:#555;">Congratulations! We are delighted to offer you the position of <strong>{job_title}</strong> at Eximp &amp; Cloves Infrastructure Limited.</p>
        <div style="background:#1A1A1A;border-radius:8px;padding:24px;margin:24px 0;">
          <table style="width:100%;color:#ccc;font-size:14px;border-collapse:collapse;">
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Offered Salary</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#4ADE80;font-weight:bold;">₦{float(salary):,.2f} / month</td></tr>
            <tr><td style="padding:8px 0;border-bottom:1px solid #333;color:#aaa;">Proposed Start Date</td><td style="padding:8px 0;border-bottom:1px solid #333;text-align:right;color:#fff;">{start_date or "To be agreed"}</td></tr>
          </table>
        </div>
        {notes_block}
        <p style="color:#555;font-size:13px;">We believe your skills and experience will be a fantastic addition to our team. This offer is subject to satisfactory references and standard onboarding procedures.</p>
        <div style="text-align:center;margin:32px 0;">
          <a href="https://app.eximps-cloves.com/hr/?offer={app_id}" style="display:inline-block;background:#4ADE80;color:#1A1A1A;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:bold;font-size:14px;">Review & Respond to Offer</a>
        </div>
        <p style="color:#555;font-size:13px;">Please let us know your decision by clicking the button above. We would love to have you on board!</p>
        <p style="color:#555;margin-top:30px;">Best regards,<br>The Eximp &amp; Cloves HR Team</p>
        <hr style="border-color:#eee;margin:24px 0;">
        <p style="color:#999;font-size:12px;margin:0;">Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color:#999;text-decoration:none;">www.eximps-cloves.com</a></p>
      </div>
    </div>"""


async def send_employment_offer_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    salary: str,
    start_date: str = "",
    notes: str = "",
    app_id: str = ""
):
    """Send an employment offer email to a candidate via Resend."""
    if not candidate_email:
        logger.warning("No candidate email — skipping offer email.")
        return None
    try:
        res = await async_resend({
            "from": "Eximp & Cloves HR <hr@mail.eximps-cloves.com>",
            "to": [candidate_email],
            "reply_to": "hr@eximps-cloves.com",
            "subject": f"Job Offer — {job_title} | Eximp & Cloves",
            "html": _offer_email_html(candidate_name, job_title, salary, start_date, notes, app_id)
        })
        logger.info(f"Offer email sent to {candidate_email}")
        return res
    except Exception as e:
        logger.error(f"Failed to send offer email to {candidate_email}: {e}")
        return None


# ─── RECRUITMENT: STAFF ONBOARDING ──────────────────────────────────────────

def _staff_onboarding_html(name, email, password, job_title, department):
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1A1A1A;padding:24px;text-align:center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="max-height:48px;display:block;margin:0 auto;">
      </div>
      <div style="background:#F5A623;padding:12px 24px;">
        <h2 style="color:#1A1A1A;margin:0;font-size:16px;">🎊 Welcome to the Team!</h2>
      </div>
      <div style="padding:32px 24px;background:#fff;border:1px solid #eee;">
        <p style="color:#333;">Dear <strong>{name}</strong>,</p>
        <p style="color:#555;">We are thrilled to officially welcome you to Eximp &amp; Cloves Infrastructure Limited as our new <strong>{job_title}</strong> in the <strong>{department}</strong> department.</p>
        <p style="color:#333;font-weight:bold;margin-top:24px;">Your Portal Access Credentials:</p>
        <div style="background:#f9f9f9;border-radius:8px;padding:20px;margin:12px 0;border:1px solid #eee;">
          <table style="width:100%;font-size:14px;border-collapse:collapse;">
            <tr><td style="padding:8px 0;color:#888;">Portal URL</td><td style="padding:8px 0;text-align:right;"><a href="https://app.eximps-cloves.com/hr" style="color:#F5A623;font-weight:bold;text-decoration:none;">app.eximps-cloves.com/hr</a></td></tr>
            <tr><td style="padding:8px 0;color:#888;">Email Address</td><td style="padding:8px 0;text-align:right;font-weight:bold;">{email}</td></tr>
            <tr><td style="padding:8px 0;color:#888;">Default Password</td><td style="padding:8px 0;text-align:right;font-family:monospace;background:#eee;padding:4px 8px;border-radius:4px;">{password}</td></tr>
          </table>
        </div>
        <p style="color:#E74C3C;font-size:12px;margin-top:8px;">⚠️ Please change your password immediately upon your first login.</p>
        <p style="color:#555;font-size:13px;margin-top:24px;">You can use the portal to manage your leave requests, view payslips, participate in performance reviews, and stay updated with company announcements.</p>
        <p style="color:#555;margin-top:30px;">Once again, welcome aboard! We look forward to achieving great things together.</p>
        <p style="color:#555;">Best regards,<br>The Eximp &amp; Cloves Team</p>
        <hr style="border-color:#eee;margin:24px 0;">
        <p style="color:#999;font-size:12px;margin:0;">Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color:#999;text-decoration:none;">www.eximps-cloves.com</a></p>
      </div>
    </div>"""


async def send_staff_onboarding_email(
    name: str,
    email: str,
    password: str,
    job_title: str,
    department: str
):
    """Send onboarding credentials to a new staff member via Resend."""
    if not email:
        return None
    try:
        res = await async_resend({
            "from": "Eximp & Cloves HR <hr@mail.eximps-cloves.com>",
            "to": [email],
            "reply_to": "hr@eximps-cloves.com",
            "subject": f"Welcome to Eximp & Cloves — Your Portal Access",
            "html": _staff_onboarding_html(name, email, password, job_title, department)
        })
        logger.info(f"Onboarding email sent to {email}")
        return res
    except Exception as e:
        logger.error(f"Failed to send onboarding email to {email}: {e}")
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
      <div style="background: #f4f4f4; padding: 20px; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee;">
        Eximp & Cloves Infrastructure Limited | RC 8311800
      </div>
    </div>"""

def _commission_paid_html(rep: dict, batch: dict) -> str:
    amount_val = float(batch.get("total_amount", 0))
    # Dynamic tax rate lookup (default to 5% if not set)
    wht_rate = float(rep.get("wht_rate") if rep.get("wht_rate") is not None else 5.0)
    
    # Derive gross/wht for display based on the actual rate
    # Net = Gross * (1 - Rate/100) => Gross = Net / (1 - Rate/100)
    divisor = 1 - (wht_rate / 100)
    gross_val = amount_val / divisor if divisor > 0 else amount_val
    wht_val = gross_val - amount_val
    
    amount_str = "{:,.2f}".format(amount_val)
    gross_str = "{:,.2f}".format(gross_val)
    wht_str = "{:,.2f}".format(wht_val)
    wht_pct_str = "{:.1f}".format(wht_rate)
    rep_name = str(rep.get("name", "Rep"))
    ref_val = str(batch.get("reference", "N/A"))
    date_val = str(batch.get("paid_at", "")[:10])
    
    html = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
      </div>
      <div style="background: #27ae60; padding: 12px 24px;">
        <h2 style="color: #fff; margin: 0; font-size: 16px;">Commission Payout Successful</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{{rep_name}}</strong>,</p>
        <p style="color: #555;">We are pleased to inform you that a commission payout has been successfully processed and remitted to your account.</p>
        
        <div style="background: #1A1A1A; padding: 24px; border-radius: 8px; margin: 24px 0;">
          <table style="width: 100%; color: #ccc; font-size: 13px; border-collapse: collapse;">
            <tr>
                <td style="text-align: left; padding: 6px 0;">Gross Commission Accrued</td>
                <td style="text-align: right; color: #fff;">NGN {{gross_str}}</td>
            </tr>
            <tr>
                <td style="text-align: left; padding: 6px 0;">Withholding Tax ({{wht_pct_str}}% WHT)</td>
                <td style="text-align: right; color: #e74c3c;">-NGN {{wht_str}}</td>
            </tr>
            <tr style="border-top: 1px solid #333;">
                <td style="text-align: left; padding: 15px 0 0; font-weight: bold; color: #aaa; text-transform: uppercase;">Amount Disbursed (Net)</td>
                <td style="text-align: right; padding: 15px 0 0; color: #27ae60; font-size: 28px; font-weight: bold;">NGN {{amount_str}}</td>
            </tr>
          </table>
          <p style="margin: 16px 0 0; font-size: 10px; color: #666; font-style: italic; text-align: center;">
            * Payout Reference: {{reference}} | Date: {{date_str}}
          </p>
        </div>
        
        <p style="color: #555; font-size: 13px;">The funds have been transferred as per your registered bank details. Please allow 24-48 hours for the transaction to reflect depending on your bank.</p>
        <p style="color: #555; font-size: 13px; font-weight: bold;">Thank you for your partnership and continued dedication!</p>
        
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          Block 57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""
    return html.replace("{{rep_name}}", rep_name).replace("{{amount_str}}", amount_str).replace("{{gross_str}}", gross_str).replace("{{wht_str}}", wht_str).replace("{{wht_pct_str}}", wht_pct_str).replace("{{reference}}", ref_val).replace("{{date_str}}", date_val)

async def send_commission_paid_email(rep: dict, batch: dict):
    from routers.analytics import log_activity
    if not rep.get("email"):
        return
        
    email_addr = rep["email"]
    rep_name = rep.get("name", "Rep")
    
    try:
        res = await async_resend({
            "from": "Eximp & Cloves Finance <" + FROM_EMAIL + ">",
            "to": [email_addr],
            "reply_to": "finance@eximps-cloves.com",
            "subject": "Commission Payout Processed | Eximp & Cloves",
            "html": _commission_paid_html(rep, batch)
        })
        
        # Avoid f-string formatting here too just in case
        amount_fmt = "{:,.2f}".format(float(batch.get("total_amount", 0)))
        log_msg = "Commission payout email for NGN " + amount_fmt + " sent to " + rep_name + " (" + email_addr + ")"
        
        await log_activity("email_sent", log_msg, "system")
        return res
    except Exception as e:
        logger.error("Error sending payout email to " + str(email_addr) + ": " + str(e))
        return None

# --- PRD 5: LEGAL & CONTRACT EMAILS ---

async def send_signing_link_email(invoice, client, token, expires_at):
    """Sent to the client with the witness signing link."""
    # Use LEGAL_EMAIL if set, else FROM_EMAIL
    sender = os.getenv("LEGAL_EMAIL", os.getenv("FROM_EMAIL"))
    email_addr = client.get("email")
    if not email_addr: return

    witness_signing_url = "https://app.eximps-cloves.com/sign/" + str(token)
    client_signing_url = "https://app.eximps-cloves.com/sign/client/" + str(token)
    expiry_str = expires_at.strftime("%B %d, %Y")

    html = """
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #F5A623;">Action Required: Contract of Sale Execution</h2>
        <p>Dear {CLIENT_NAME},</p>
        <p>Your Contract of Sale for <strong>{ESTATE_NAME}</strong> is ready for execution.</p>
        <p>There are two separate steps:</p>
        <ol>
            <li>Review and sign the contract yourself using the Client Signing Link below.</li>
            <li>Forward the Witness Signing Link to <strong>your witness</strong>. The witness must open the link and sign as a witness.</li>
        </ol>

        <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="font-size: 12px; color: #888; margin-bottom: 8px;">CLIENT SIGNING LINK</p>
            <a href="{CLIENT_SIGNING_URL}" style="color: #F5A623; font-weight: bold; text-decoration: none; font-size: 16px;">{CLIENT_SIGNING_URL}</a>
        </div>

        <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <p style="font-size: 12px; color: #888; margin-bottom: 8px;">WITNESS SIGNING LINK</p>
            <a href="{WITNESS_SIGNING_URL}" style="color: #F5A623; font-weight: bold; text-decoration: none; font-size: 16px;">{WITNESS_SIGNING_URL}</a>
            <p style="font-size: 11px; color: #e74c3c; margin-top: 10px;">Security Notice: Both links expire in 48 hours (on {EXPIRY_DATE}).</p>
        </div>

        <p><strong>Instructions for Client:</strong></p>
        <ul>
            <li>Open the Client Signing Link.</li>
            <li>Read the complete contract document.</li>
            <li>Sign and submit your contract signature.</li>
        </ul>
        
        <div style="background-color: #f9f9f9; border-left: 4px solid #F5A623; padding: 15px; margin-top: 30px; font-size: 13px; color: #666;">
            <strong>Data Compliance & Security:</strong><br>
            For legal and audit purposes, please be aware that we record your IP address, device type, browser user agent, and the precise timestamp of your signature. This information is stored securely as part of the digital audit trail for this transaction.
        </div>

        <p><strong>Instructions for Witness:</strong></p>
        <ol>
            <li>Open the witness link on a phone or computer.</li>
            <li>Review the contract document.</li>
            <li>Enter name, address, occupation, and sign.</li>
            <li>Click "Submit Witness Signature".</li>
        </ol>

        <p>Once your witness has signed, the system will notify our legal department to generate your final executed contract.</p>
        <p>Best regards,<br>Legal Department<br>Eximp & Cloves Infrastructure Limited</p>
    </div>
    """
    html = html.replace("{CLIENT_NAME}", client.get("full_name", "Valued Client"))
    html = html.replace("{ESTATE_NAME}", invoice.get("property_name", "the property"))
    html = html.replace("{CLIENT_SIGNING_URL}", client_signing_url)
    html = html.replace("{WITNESS_SIGNING_URL}", witness_signing_url)
    html = html.replace("{EXPIRY_DATE}", expiry_str)

    try:
        from main import app # dummy to avoid circular import if needed, but resend is global
        import resend 
        res = await async_resend({
            "from": "Eximp & Cloves Legal <" + str(sender) + ">",
            "to": email_addr,
            "cc": ["legal@eximps-cloves.com"],
            "reply_to": "admin@eximps-cloves.com",
            "subject": "Your Contract of Sale is Ready — Eximp & Cloves",
            "html": html
        })
        return res
    except Exception as e:
        logger.error("Error sending signing link email: " + str(e))
        return None

async def send_admin_signing_alert(invoice, client, witnesses):
    """Notifies admin when both witnesses have signed."""
    sender = os.getenv("FROM_EMAIL")
    admin_email = os.getenv("ADMIN_ALERT_EMAIL", os.getenv("FROM_EMAIL"))
    
    html = """
    <div style="font-family: sans-serif; padding: 20px;">
        <h3 style="color: #2e7d32;">✓ Contract Ready for Execution</h3>
        <p>The external witness has completed their signature for the following contract:</p>
        <ul>
            <li><strong>Client:</strong> {CLIENT_NAME}</li>
            <li><strong>Invoice:</strong> {INV_NO}</li>
            <li><strong>Property:</strong> {ESTATE_NAME}</li>
        </ul>
        <p><strong>Witness Detail:</strong><br>
        1. {W1_NAME} ({W1_OCC})</p>
        <p>A company representative will be automatically assigned to the second witness slot. You can now generate the final executed Contract of Sale from the dashboard.</p>
    </div>
    """
    html = html.replace("{CLIENT_NAME}", client.get("full_name"))
    html = html.replace("{INV_NO}", invoice.get("invoice_number"))
    html = html.replace("{ESTATE_NAME}", invoice.get("property_name"))
    html = html.replace("{W1_NAME}", witnesses[0].get("full_name"))
    html = html.replace("{W1_OCC}", witnesses[0].get("occupation"))
    html = html.replace("{W2_NAME}", witnesses[1].get("full_name"))
    html = html.replace("{W2_OCC}", witnesses[1].get("occupation"))

    try:
        import resend
        await async_resend({
            "from": "System Alert <" + str(sender) + ">",
            "to": admin_email,
            "subject": "Contract Ready: " + str(client.get("full_name")) + " (" + str(invoice.get("invoice_number")) + ")",
            "html": html
        })
    except Exception as e:
        logger.error("Error sending admin signing alert: " + str(e))

async def send_executed_contract_email(invoice, client, pdf_content, certificate_pdf=None):
    """Sends the final executed PDF to the client, optionally with an audit certificate."""
    sender = os.getenv("LEGAL_EMAIL", os.getenv("FROM_EMAIL"))
    email_addr = client.get("email")
    if not email_addr: return

    import base64
    attachments = [
        {
            "content": base64.b64encode(pdf_content).decode(),
            "filename": f"Executed_Contract_{invoice.get('invoice_number')}.pdf"
        }
    ]
    
    cert_note = ""
    if certificate_pdf:
        attachments.append({
            "content": base64.b64encode(certificate_pdf).decode(),
            "filename": f"Audit_Certificate_{invoice.get('invoice_number')}.pdf"
        })
        cert_note = "<p>Also attached is your <strong>Digital Audit Certificate</strong>, providing a secure log of all signing events, IP addresses, and document integrity checksums for your records.</p>"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 40px;">
        </div>
        <h2 style="color: #2e7d32; text-align: center;">Execution Complete</h2>
        <p>Dear {client.get('full_name', 'Valued Client')},</p>
        <p>Congratulations! Your Contract of Sale for <strong>{invoice.get('property_name')}</strong> has been fully executed by all parties.</p>
        <p>Please find the final signed document attached to this email. This is a legally binding document; please keep it in a safe place.</p>
        
        {cert_note}

        <p><strong>Property Details:</strong><br>
        Estate: {invoice.get('property_name')}<br>
        Plot Size: {invoice.get('plot_size_sqm')} SQM<br>
        Execution Date: {datetime.now(timezone(timedelta(hours=1))).strftime("%B %d, %Y")}</p>

        <p>Our documentation team will contact you shortly regarding the next steps (Survey and Allocation).</p>
        <p>Thank you for choosing Eximp & Cloves Infrastructure Limited.</p>
        <p>Best regards,<br>Legal Department</p>
        <hr style="border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #888; font-size: 11px; text-align: center;">Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a></p>
    </div>
    """

    try:
        import resend
        res = await async_resend({
            "from": f"Eximp & Cloves Legal <{sender}>",
            "to": [email_addr],
            "cc": ["legal@eximps-cloves.com"],
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Your Fully Executed Contract of Sale — {invoice.get('invoice_number')}",
            "html": html,
            "attachments": attachments
        })
        return res
    except Exception as e:
        logger.error(f"Error sending executed contract email: {e}")
        return None


def _witness_confirmation_html(witness_name, estate_name, client_name):
    return f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #2e7d32;">✓ Witness Signature Recorded</h2>
        <p>Dear {witness_name},</p>
        <p>Thank you for acting as a witness for the Contract of Sale between <strong>Eximp & Cloves Infrastructure Limited</strong> and <strong>{client_name}</strong> regarding the property: <strong>{estate_name}</strong>.</p>
        <p>Your signature has been securely recorded and linked to the official document. No further action is required from your side.</p>
        
        <p>For security reasons, please note that you will not receive a copy of the full contract. Only the contracting parties receive the executed document.</p>
        
        <p>Thank you for your cooperation.</p>
        <p>Best regards,<br>Legal Department<br>Eximp & Cloves Infrastructure Limited</p>
    </div>
    """

async def send_witness_confirmation_email(witness_name, witness_email, estate_name, client_name):
    """Sends a professional thank you email to the witness after signing."""
    sender = os.getenv("LEGAL_EMAIL", os.getenv("FROM_EMAIL"))
    if not witness_email: return
    
    html = _witness_confirmation_html(witness_name, estate_name, client_name)
    
    try:
        import resend
        res = await async_resend({
            "from": "Eximp & Cloves Legal <" + str(sender) + ">",
            "to": [witness_email],
            "cc": ["legal@eximps-cloves.com"],
            "reply_to": "admin@eximps-cloves.com",
            "subject": "Witness Signature Confirmation — Eximp & Cloves",
            "html": html
        })
        return res
    except Exception as e:
        logger.error("Error sending witness confirmation email: " + str(e))
        return None

def _marketing_wrapper(content_html: str, client_name: str) -> str:
    """Wraps campaign content in a professional, luxury Real Estate editorial layout."""
    # Placeholder for personalized greeting
    body_content = content_html.replace("{CLIENT_NAME}", client_name)
    
    # Social Media Links
    social_links = {
        "facebook": "https://facebook.com/eximp.cloves",
        "instagram": "https://instagram.com/eximp.cloves",
        "tiktok": "https://tiktok.com/@eximp.cloves",
        "x": "https://x.com/eximp_cloves",
        "linkedin": "https://www.linkedin.com/company/eximp-cloves"
    }

    # Social Icons (using reliable CDN images for email compatibility)
    icons = {
        "facebook": "https://img.icons8.com/ios-filled/50/ffffff/facebook-new.png",
        "instagram": "https://img.icons8.com/ios-filled/50/ffffff/instagram-new.png",
        "tiktok": "https://img.icons8.com/ios-filled/50/ffffff/tiktok.png",
        "x": "https://img.icons8.com/ios-filled/50/ffffff/twitterx--v2.png",
        "linkedin": "https://img.icons8.com/ios-filled/50/linkedin.png"
    }

    social_html = "".join([
        f'<a href="{url}" style="margin: 0 10px; display: inline-block;"><img src="{icons[name]}" width="24" height="24" alt="{name}" style="display: block; border: 0;"></a>'
        for name, url in social_links.items()
    ])

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
        <style>
            body {{ margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'DM Sans', Arial, sans-serif; -webkit-font-smoothing: antialiased; }}
            .container {{ max-width: 600px; margin: 40px auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }}
            .header {{ background-color: #1A1A1A; padding: 40px 20px; text-align: center; border-bottom: 4px solid #C47D0A; }}
            .logo {{ height: 50px; width: auto; }}
            .hero-strip {{ background-color: #C47D0A; height: 10px; }}
            .content {{ padding: 60px 50px; color: #333333; line-height: 1.8; font-size: 16px; background-image: linear-gradient(to bottom, #ffffff, #fafafa); }}
            .footer {{ background-color: #1A1A1A; padding: 60px 40px; text-align: center; color: #bbbbbb; font-size: 13px; border-top: 4px solid #C47D0A; }}
            h1, h2, h3 {{ font-family: 'Playfair Display', serif; color: #1A1A1A; line-height: 1.2; font-weight: 700; margin-bottom: 24px; }}
            .cta-button {{ display: inline-block; padding: 20px 40px; background-color: #C47D0A; color: #ffffff !important; text-decoration: none; border-radius: 2px; font-weight: 700; margin-top: 20px; text-transform: uppercase; letter-spacing: 2px; font-size: 14px; box-shadow: 0 4px 15px rgba(196, 125, 10, 0.3); }}
            .divider {{ height: 1px; background-color: #dddddd; margin: 40px 0; }}
            .social-bar {{ margin-top: 30px; padding: 20px 0; border-top: 1px solid #333333; }}
            .address {{ color: #888888; margin-top: 20px; font-style: normal; }}
            a {{ color: #C47D0A; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" class="logo">
            </div>
            <div class="hero-strip"></div>
            <div class="content">
                {body_content}
            </div>
            <div class="footer">
                <p style="color: #C47D0A; font-weight: 700; text-transform: uppercase; letter-spacing: 3px; font-size: 14px; margin-bottom: 15px;">Experience Luxury</p>
                <p style="font-size: 18px; color: #ffffff; margin-bottom: 20px; font-family: 'Playfair Display', serif;">Eximp & Cloves Infrastructure Limited</p>
                <div class="address">
                    57B, Isaac John Street, Yaba, Lagos<br>
                    <a href="tel:+2349126864383" style="color: #ffffff;">+234 912 686 4383</a> | <a href="https://www.eximps-cloves.com" style="color: #C47D0A;">www.eximps-cloves.com</a>
                </div>
                <div class="social-bar">
                    {social_html}
                </div>
                <div class="divider" style="background: #333; margin: 30px 0;"></div>
                <p style="font-size: 11px; color: #777; line-height: 1.6;">
                    RC 8311800. All rights reserved.<br>
                    You are receiving this email because you expressed interest in our luxury properties.<br>
                    <a href="#" style="color: #555;">Unsubscribe from our marketing list</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

async def broadcast_campaign_email(campaign: dict, recipients: list, admin_id: str):
    """Background task to send campaign emails to multiple recipients."""
    from database import get_db
    db = get_db()
    campaign_id = campaign["id"]
    
    delivered = 0
    total = len(recipients)
    
    for client in recipients:
        email_addr = client.get("email")
        if not email_addr: continue
        
        try:
            # We wrap the content for each recipient (enables future per-recipient personalization)
            html = _marketing_wrapper(campaign["content_html"], client.get("full_name", "Valued Client"))
            
            await async_resend({
                "from": f"Eximp & Cloves <{FROM_EMAIL}>",
                "to": [email_addr],
                "subject": campaign["subject"],
                "html": html,
                "reply_to": "sales@eximps-cloves.com"
            })
            delivered += 1
            
            # Update campaign progress every 5 emails (to prevent too many DB writes)
            if delivered % 5 == 0:
                db.table("marketing_campaigns").update({
                    "delivered_count": delivered,
                    "updated_at": datetime.now(timezone(timedelta(hours=1))).isoformat()
                }).eq("id", campaign_id).execute()
                
            # Optional: Add a small delay to respect rate limits if needed
            # time.sleep(0.1) 
            
        except Exception as e:
            logger.error(f"Error sending campaign {campaign_id} to {email_addr}: {e}")

    # Final Update
    db.table("marketing_campaigns").update({
        "status": "sent",
        "delivered_count": delivered,
        "sent_at": datetime.now(timezone(timedelta(hours=1))).isoformat()
    }).eq("id", campaign_id).execute()

    logger.info(f"Campaign {campaign_id} broadcast finished. Delivered: {delivered}/{total}")


def _payout_receipt_html(payout: dict, vendor: dict, payment_amount: float = None) -> str:
    # Use payment_amount if passed, else fallback to net_payout_amount (old behavior)
    amount_now = float(payment_amount or payout.get("net_payout_amount") or 0)
    total_paid = float(payout.get("amount_paid") or 0)
    total_due = float(payout.get("net_payout_amount") or 0)
    balance = max(0, total_due - total_paid)
    ref = payout.get("payout_reference") or "N/A"

    # BANK SNAPSHOT RESOLUTION:
    # Prefer the snapshot stored on the expenditure_request at submission time.
    # This means if a vendor changes their bank details for a future transaction,
    # receipts for THIS specific payout still show the bank that was used here.
    # Fall back to the current vendor record only if no snapshot exists (legacy rows).
    display_bank_name  = payout.get("bank_name_snapshot")    or vendor.get("bank_name")    or "N/A"
    display_acc_number = payout.get("account_number_snapshot") or vendor.get("account_number") or "N/A"
    
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
      </div>
      <div style="background: #C47D0A; padding: 12px 24px;">
        <h2 style="color: #fff; margin: 0; font-size: 16px;">✓ Payment Authorized & Processed</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Dear <strong>{vendor['name']}</strong>,</p>
        <p style="color: #555;">We are pleased to inform you that your payment has been authorized and processed via our expenditure cloud.</p>
        <div style="background: #1A1A1A; border-radius: 8px; padding: 24px; margin: 24px 0;">
          <p style="color: #aaa; margin: 0 0 8px; font-size: 13px; text-transform: uppercase;">Amount Remitted Now</p>
          <p style="color: #F5A623; font-size: 32px; font-weight: bold; margin: 0;">NGN {amount_now:,.2f}</p>
          <hr style="border-color: #333; margin: 16px 0;">
          <table style="width: 100%; color: #ccc; font-size: 13px;">
            <tr><td>Total Paid to Date</td><td style="text-align:right;color:#fff;">NGN {total_paid:,.2f}</td></tr>
            <tr><td>Balance Outstanding</td><td style="text-align:right;color:{'#27ae60' if balance == 0 else '#F5A623'};">NGN {balance:,.2f}</td></tr>
            <tr style="height: 10px;"><td></td><td></td></tr>
            <tr><td>Reference</td><td style="text-align:right;color:#fff;">{ref}</td></tr>
            <tr><td>Payee Bank</td><td style="text-align:right;color:#fff;">{display_bank_name}</td></tr>
            <tr><td>Account</td><td style="text-align:right;color:#fff;">{display_acc_number}</td></tr>
            <tr><td>Due Date</td><td style="text-align:right;color:#fff;">{payout.get('due_date','—')}</td></tr>
            <tr><td>Phone</td><td style="text-align:right;color:#fff;">{vendor.get('phone','—')}</td></tr>
          </table>
        </div>
        <p style="color: #555; text-align: center; font-size: 11px;">Note: Tax would be deducted by the company and be paid to the Government.</p>
        <p style="color: #555; font-size: 13px;">The official Payment Advice (PDF) with full tax breakdown is attached to this email.</p>
        <p style="color: #555; font-size: 13px;">Thank you for your partnership.</p>
        <hr style="border-color: #eee;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383<br>
          <a href="https://www.eximps-cloves.com" style="color: #999; text-decoration: none;">www.eximps-cloves.com</a>
        </p>
        <p style="color: #888; font-size: 11px; text-align: center; margin-top: 16px;">
          Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a>
        </p>
      </div>
    </div>"""


async def send_payout_claim_rejected_email(payout: dict, vendor: dict, rejection_reason: str, admin_id: str = "system"):
    """
    Sent to the claimant (vendor/staff) when their payout or expenditure claim
    is rejected at the audit/review stage. Includes the reason so they can resubmit.
    """
    from routers.analytics import log_activity

    email_addr = vendor.get("email")
    if not email_addr:
        logger.warning(f"Cannot send rejection email — no email on vendor {vendor.get('name')}")
        return None

    claimant_name = vendor.get("name") or vendor.get("full_name") or "Claimant"
    claim_title   = payout.get("title") or "Your claim"
    claim_amount  = payout.get("amount_gross") or 0
    ref           = payout.get("payout_reference") or payout.get("id", "")[:8].upper()
    reason_text   = rejection_reason or "No specific reason provided. Please contact Finance for details."

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;border-radius:10px;
     border:1px solid #e5e7eb;overflow:hidden;">
  <div style="background:#1A1A1A;padding:24px;text-align:center;">
    <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves"
         style="max-height:44px;display:block;margin:0 auto;">
  </div>
  <div style="background:#C0392B;padding:14px 24px;text-align:center;">
    <h2 style="color:#fff;margin:0;font-size:17px;letter-spacing:0.5px;">
      ⚠️ Claim Rejected — Action Required
    </h2>
  </div>
  <div style="padding:32px 28px;background:#fff;">
    <p style="color:#333;font-size:16px;margin:0 0 12px;">Dear <strong>{claimant_name}</strong>,</p>
    <p style="color:#555;line-height:1.7;margin:0 0 24px;">
      We have reviewed your expenditure/payout claim and unfortunately it has been
      <strong style="color:#C0392B;">rejected</strong> at this time.
    </p>

    <!-- Claim summary box -->
    <div style="background:#f9f9f9;border:1px solid #e5e7eb;border-radius:8px;
                padding:18px 20px;margin-bottom:24px;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
          <div style="font-size:10px;color:#9ca3af;text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:4px;">Claim Reference</div>
          <div style="font-weight:800;color:#1A1A1A;">{ref}</div>
        </div>
        <div>
          <div style="font-size:10px;color:#9ca3af;text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:4px;">Amount Claimed</div>
          <div style="font-weight:800;color:#1A1A1A;">₦{float(claim_amount):,.2f}</div>
        </div>
      </div>
      <div style="margin-top:14px;">
        <div style="font-size:10px;color:#9ca3af;text-transform:uppercase;
                    letter-spacing:1px;margin-bottom:4px;">Description</div>
        <div style="color:#555;font-size:13px;">{claim_title}</div>
      </div>
    </div>

    <!-- Rejection reason -->
    <div style="background:#fef2f2;border:1.5px solid #fca5a5;border-radius:8px;
                padding:16px 20px;margin-bottom:28px;">
      <div style="font-size:11px;font-weight:800;color:#C0392B;text-transform:uppercase;
                  letter-spacing:0.8px;margin-bottom:8px;">Reason for Rejection</div>
      <p style="color:#374151;font-size:13px;line-height:1.6;margin:0;
                white-space:pre-wrap;">{reason_text}</p>
    </div>

    <p style="color:#555;line-height:1.6;font-size:14px;margin:0 0 20px;">
      If you believe this decision is incorrect, or you have additional supporting documents,
      please resubmit your claim via the <strong>Claims &amp; Payouts Portal</strong> or
      contact the Finance team directly.
    </p>

    <div style="text-align:center;margin:30px 0;">
      <a href="https://app.eximps-cloves.com/payout/portal"
         style="background:#C47D0A;color:#fff;padding:13px 28px;text-decoration:none;
                border-radius:6px;font-weight:700;font-size:14px;display:inline-block;">
        Resubmit / Appeal Claim
      </a>
    </div>

    <hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0;">
    <p style="color:#9ca3af;font-size:11px;text-align:center;margin:0;">
      Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>
      57B, Isaac John Street, Yaba, Lagos<br>
      <a href="https://www.eximps-cloves.com" style="color:#9ca3af;text-decoration:none;">
        www.eximps-cloves.com
      </a>
    </p>
  </div>
</div>"""

    try:
        res = await async_resend({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Claim Rejected — {claim_title} | Eximp & Cloves",
            "html": html,
        })
        await log_activity(
            "email_sent",
            f"Claim rejection email sent to {claimant_name} ({email_addr}). Ref: {ref}",
            admin_id,
            metadata={"payout_id": payout.get("id"), "vendor_id": vendor.get("id"),
                      "reason": rejection_reason}
        )
        logger.info(f"Claim rejection email sent to {email_addr}")
        return res
    except Exception as e:
        logger.error(f"Failed to send claim rejection email to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send rejection email to {claimant_name} ({email_addr}): {str(e)}",
            admin_id,
            metadata={"error": str(e), "email_type": "claim_rejected"}
        )
        return None


async def send_payout_receipt_email(payout: dict, vendor: dict, admin_id: str = "system", payment_amount: float = None):
    from routers.analytics import log_activity
    from pdf_service import generate_payout_receipt_pdf
    
    email_addr = vendor.get("email")
    if not email_addr:
        logger.warning(f"No email found for vendor {vendor['name']}. Payout receipt PDF generated but not sent.")
        return None

    try:
        payout_ref = payout.get("payout_reference") or "Processed"
        pdf = generate_payout_receipt_pdf(payout, vendor)
        res = await async_resend({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
            "reply_to": "admin@eximps-cloves.com",
            "subject": f"Payment Remittance Advice [Ref: {payout_ref}] — Eximp & Cloves",
            "html": _payout_receipt_html(payout, vendor, payment_amount),
            "attachments": [{"filename": f"Payment_Advice_{payout_ref}.pdf", "content": list(pdf)}],
        })
        
        await log_activity(
            "email_sent",
            f"Payout receipt for {payout_ref} sent to {vendor['name']} ({email_addr})",
            admin_id,
            metadata={"payout_id": payout.get("id"), "vendor_id": vendor.get("id")}
        )
        return res
    except Exception as e:
        logger.error(f"Error sending payout receipt to {email_addr}: {e}")
        await log_activity(
            "email_failed",
            f"FAILED to send payout receipt to {vendor['name']} ({email_addr}): {str(e)}",
            admin_id,
            metadata={"error": str(e), "email_type": "payout_receipt"}
        )
        return None
            
async def send_ready_for_execution_email(invoice, client):
    """Notifies legal and admin that a contract is fully signed and ready for final execution."""
    from routers.analytics import log_activity
    legal_email = os.getenv("LEGAL_EMAIL", "legal@eximps-cloves.com")
    admin_email = os.getenv("ADMIN_ALERT_EMAIL", "admin@eximps-cloves.com")
    recipients = list(dict.fromkeys([legal_email, admin_email]))

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #C47D0A; border-radius: 10px;">
        <h2 style="color: #C47D0A;">⚖️ Contract Ready for Execution</h2>
        <p>The contract has now been signed by the client and witnessed, and is pending final legal sealing.</p>
        
        <table style="width: 100%; font-size: 14px; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Client</td><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">{client['full_name']}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Property</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{invoice.get('property_name', 'N/A')}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Invoice No</td><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; color: #C47D0A;">{invoice.get('invoice_number', 'N/A')}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Signed On</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{datetime.now(timezone(timedelta(hours=1))).strftime("%B %d, %Y at %I:%M %p")}</td></tr>
        </table>

        <div style="text-align: center; margin-top: 24px;">
            <a href="https://eximp-cloves.com/legal" style="background: #C47D0A; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">Open Legal Dashboard</a>
        </div>
        
        <p style="color: #888; font-size: 12px; margin-top: 24px; text-align: center;">This is an automated notification from the Eximp & Cloves Legal Suite.</p>
    </div>
    """

    try:
        import resend
        res = await async_resend({
            "from": f"Legal Suite <{FROM_EMAIL}>",
            "to": recipients,
            "cc": CLIENT_CC_RECIPIENTS,
            "subject": f"Ready for Execution: {invoice.get('invoice_number', 'N/A')} — {client.get('full_name', 'Client')}",
            "html": html
        })
        
        await log_activity(
            "execution_ready_alert_sent",
            f"Execution readiness alert for {invoice.get('invoice_number', 'N/A')} sent to legal/admin team",
            "system",
            invoice_id=invoice.get('id')
        )
        return res
    except Exception as e:
        logger.error(f"Error sending execution ready email: {e}")
        return None

async def send_portal_invite_email(email_addr: str, inviter_name: str, token: str = "OFFICIAL"):
    from routers.analytics import log_activity
    
    # Use the absolute URL via config or env
    portal_link = f"{APP_BASE_URL}/payout/portal/{token}"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden;">
      <div style="background: #1A1A1A; padding: 30px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 50px;">
      </div>
      <div style="padding: 40px 30px; background: #fff;">
        <h2 style="color: #1A1A1A; font-size: 20px; margin-bottom: 20px;">Onboarding & Payment Invitation</h2>
        <p style="color: #555; line-height: 1.6;">Dear Partner,</p>
        <p style="color: #555; line-height: 1.6;"><strong>{inviter_name}</strong> from Eximp & Cloves Infrastructure Limited has invited you to submit your details for payout processing.</p>
        <p style="color: #555; line-height: 1.6;">Our expenditure system is now fully automated. Please use the link below to provide your bank details and upload your quotation or receipt to initiate your payment request.</p>
        
        <div style="text-align: center; margin: 40px 0;">
          <a href="{portal_link}" style="background: #C47D0A; color: #fff; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block; box-shadow: 0 4px 15px rgba(196, 125, 10, 0.3);">Open Payout Portal</a>
        </div>
        
        <p style="color: #888; font-size: 12px; font-style: italic;">Note: This link is secure and redirects you to the Eximp & Cloves Financial Cloud.</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 11px;">Eximp & Cloves Infrastructure Limited | RC 8311800<br>
        57B, Isaac John Street, Yaba, Lagos</p>
      </div>
    </div>"""

    try:
        res = await async_resend({
            "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
            "to": [email_addr],
            "subject": "Invitation: Submit Payout Request | Eximp & Cloves",
            "html": html,
            "reply_to": "admin@eximps-cloves.com"
        })
        
        await log_activity(
            "email_sent",
            f"Portal invitation sent to {email_addr} by {inviter_name}",
            "system",
            metadata={"email_type": "portal_invite"}
        )
        return res
    except Exception as e:
        logger.error(f"Error sending portal invite to {email_addr}: {e}")
        return None

def _support_response_html(ticket: dict, message: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <h1 style="color: #C47D0A; margin: 0; font-size: 20px;">Support Hub Response</h1>
      </div>
      <div style="padding: 32px 24px; background: #fff;">
        <p style="color: #333;">Hello <strong>{ticket.get('contact_name', 'Visitor')}</strong>,</p>
        <p style="color: #555;">An admin has responded to your inquiry regarding <strong>"{ticket.get('subject')}"</strong>.</p>
        
        <div style="background: #fdfaf3; border-left: 4px solid #C47D0A; padding: 20px; margin: 24px 0; color: #444; font-size: 14px; line-height: 1.6;">
          {message}
          <div style="text-align: center; margin: 32px 0;">
            <a href="{APP_BASE_URL}/support/portal/{ticket.get('id')}" style="background-color: #C47D0A; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(196, 125, 10, 0.3);">View Discussion & Reply</a>
          </div>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #888; font-size: 12px;">This is a response to your support ticket #{ticket.get('id', '').split('-')[0]}. You can also reply to this email directly.</p>
        <p style="color: #999; font-size: 11px; margin-top: 12px;">Eximp & Cloves Infrastructure Limited | RC 8311800<br>
        57B, Isaac John Street, Yaba, Lagos</p>
      </div>
    </div>"""

def _support_followup_html(ticket: dict) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden;">
      <div style="background: #C47D0A; padding: 24px; text-align: center;">
        <h1 style="color: #FFFFFF; margin: 0; font-size: 20px;">Support Nudge</h1>
      </div>
      <div style="padding: 32px 24px; background: #fff;">
        <p style="color: #333;">Hello <strong>{ticket.get('contact_name', 'Visitor')}</strong>,</p>
        <p style="color: #555;">It's been an hour since we sent you a response regarding <strong>"{ticket.get('subject')}"</strong>, and we haven't heard back from you yet.</p>
        
        <p style="color: #555;">We just want to make sure your issue is fully resolved. Do you still need assistance?</p>
        
        <div style="text-align: center; margin: 32px 0;">
          <a href="{APP_BASE_URL}/support/portal/{ticket.get('id')}" style="background-color: #C47D0A; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(196, 125, 10, 0.3);">View Discussion & Reply</a>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #888; font-size: 12px;">This is a follow-up to your support ticket #{ticket.get('id', '').split('-')[0]}.</p>
        <p style="color: #999; font-size: 11px; margin-top: 12px;">Eximp & Cloves Infrastructure Limited | RC 8311800<br>
        57B, Isaac John Street, Yaba, Lagos</p>
      </div>
    </div>"""

async def send_support_response_email(ticket: dict, message: str):
    email_addr = ticket.get("contact_email")
    if not email_addr: return
    
    try:
        res = await async_resend({
            "from": f"Eximp & Cloves Support <{FROM_EMAIL}>",
            "to": [email_addr],
            "subject": f"Re: {ticket.get('subject')}",
            "html": _support_response_html(ticket, message),
            "reply_to": "admin@eximps-cloves.com"
        })
        return res
    except Exception as e:
        logger.error(f"Error sending support response email: {e}")

async def send_followup_nudge_email(ticket: dict):
    email_addr = ticket.get("contact_email")
    if not email_addr: return
    
    try:
        import resend
        await async_resend({
            "from": f"Eximp & Cloves Support <{FROM_EMAIL}>",
            "to": [email_addr],
            "subject": f"Checking in: {ticket.get('subject')}",
            "html": _support_followup_html(ticket)
        })
        logger.info(f"Follow-up nudge sent for ticket {ticket.get('id')}")
    except Exception as e:
        logger.error(f"Error sending support nudge: {e}")

def _appointment_reminder_html(appointment: dict) -> str:
    scheduled_at = datetime.fromisoformat(appointment["scheduled_at"])
    time_str = scheduled_at.strftime("%I:%M %p")
    date_str = scheduled_at.strftime("%A, %d %B %Y")
    
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden; background: #fff;">
      <div style="background: #1A1A1A; padding: 30px; text-align: center;">
        <h1 style="color: #C47D0A; margin: 0; font-size: 22px; letter-spacing: 1px;">Inspection Reminder</h1>
        <p style="color: #888; margin: 8px 0 0; font-size: 13px;">Eximp & Cloves Infrastructure Limited</p>
      </div>
      <div style="padding: 40px 30px;">
        <p style="color: #333; font-size: 16px;">Hello <strong>{appointment.get('contact_name')}</strong>,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.6;">This is a friendly reminder for your upcoming property inspection. We are looking forward to showing you the future of Nigerian real estate.</p>
        
        <div style="background: #f9f9f9; border-radius: 12px; padding: 24px; margin: 30px 0; border: 1px solid #eee;">
          <table style="width: 100%; border-collapse: collapse;">
            <tr>
              <td style="padding-bottom: 12px; color: #888; font-size: 12px; text-transform: uppercase;">When</td>
              <td style="padding-bottom: 12px; text-align: right; color: #1A1A1A; font-weight: bold; font-size: 14px;">{time_str}<br><span style="font-weight: normal; color: #666;">{date_str}</span></td>
            </tr>
            <tr>
              <td style="padding-top: 12px; border-top: 1px solid #eee; color: #888; font-size: 12px; text-transform: uppercase;">Location</td>
              <td style="padding-top: 12px; border-top: 1px solid #eee; text-align: right; color: #1A1A1A; font-weight: bold; font-size: 14px;">{appointment.get('location', 'To be provided by agent')}</td>
            </tr>
          </table>
        </div>
        
        <p style="color: #555; font-size: 14px; line-height: 1.6;">If you need to reschedule or have any questions, please reply to this email or call us at +234 912 686 4383.</p>
        
        <div style="margin-top: 40px; text-align: center;">
          <p style="color: #999; font-size: 12px;">Warm regards,<br>The Eximp & Cloves Team</p>
        </div>
      </div>
    </div>"""

async def send_appointment_reminder_email(appointment: dict):
    email_addr = appointment.get("contact_email")
    if not email_addr: return
    
    try:
        res = await async_resend({
            "from": f"Eximp & Cloves <{FROM_EMAIL}>",
            "to": [email_addr],
            "subject": "Reminder: Your Property Inspection",
            "html": _appointment_reminder_html(appointment),
            "reply_to": "sales@eximps-cloves.com"
        })
        return res
    except Exception as e:
        logger.error(f"Error sending appointment reminder to {email_addr}: {e}")
        return None

def _chat_invitation_html(name: str, inviter: str, join_url: str, ticket_subject: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden; background: #fff;">
      <div style="background: #1A1A1A; padding: 30px; text-align: center;">
        <h1 style="color: #F5A623; margin: 0; font-size: 22px; letter-spacing: 1px;">Group Chat Invitation</h1>
        <p style="color: #888; margin: 8px 0 0; font-size: 13px;">Secure Collaboration | Eximp & Cloves</p>
      </div>
      <div style="padding: 40px 30px;">
        <p style="color: #333; font-size: 16px;">Hello <strong>{name}</strong>,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.6;"><strong>{inviter}</strong> has invited you to join a secure group chat regarding the support ticket: <strong>"{ticket_subject}"</strong>.</p>
        
        <p style="color: #555; font-size: 14px; line-height: 1.6;">This chat is a private, secure back-channel for real-time collaboration with our team.</p>

        <div style="margin: 40px 0; text-align: center;">
          <a href="{join_url}" style="background: #F5A623; color: #1A1A1A; text-decoration: none; padding: 15px 30px; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">Accept & Join Chat</a>
        </div>
        
        <p style="color: #888; font-size: 12px; text-align: center;">If the button above doesn't work, copy and paste this link into your browser:<br>
        <a href="{join_url}" style="color: #C47D0A;">{join_url}</a></p>
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
          <p style="color: #999; font-size: 12px;">Warm regards,<br>The Eximp & Cloves Team</p>
        </div>
      </div>
    </div>"""

async def send_chat_invitation_email(email_addr: str, name: str, inviter: str, join_url: str, ticket_subject: str):
    try:
        res = await async_resend({
            "from": f"Eximp & Cloves <{FROM_EMAIL}>",
            "to": [email_addr],
            "subject": f"Invitation to Group Chat: {ticket_subject}",
            "html": _chat_invitation_html(name, inviter, join_url, ticket_subject),
            "reply_to": "sales@eximps-cloves.com"
        })
        return res
    except Exception as e:
        logger.error(f"Error sending chat invitation to {email_addr}: {e}")
        return None

def _staff_signing_html(staff_name: str, doc_title: str, signing_url: str, custom_message: str = None) -> str:
    message_html = ""
    if custom_message:
        message_html = f"""
        <div style="margin: 10px 0 25px 0; padding: 15px; background: #fffcf5; border: 1px dashed #F5A623; border-radius: 6px; font-style: italic; color: #555; font-size: 14px; line-height: 1.6;">
            "{custom_message}"
        </div>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border-radius: 8px; border: 1px solid #ddd; overflow: hidden;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height: 48px; display: block; margin: 0 auto;">
      </div>
      <div style="background: #F5A623; padding: 12px 24px; text-align: center;">
        <h2 style="color: #1A1A1A; margin: 0; font-size: 18px;">Action Required: Signature Requested</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff;">
        <p style="color: #333; font-size: 16px;">Dear <strong>{staff_name}</strong>,</p>
        
        {message_html}

        <p style="color: #555; line-height: 1.5;">You have been requested to review and digitally sign the following legal document:</p>
        
        <div style="margin: 20px 0; padding: 16px; background-color: #f9f9f9; border-left: 4px solid #F5A623; font-weight: bold; color: #1a1a1a;">
            {doc_title}
        </div>
        
        <div style="text-align: center; margin: 35px 0;">
          <a href="{signing_url}" style="background-color: #C47D0A; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Review & Sign Document</a>
        </div>
        
        <p style="color: #555; font-size: 13px; line-height: 1.5;">For security purposes, this unique link is generated specifically for you and is protected. Your digital signature, IP address, and an exact timestamp will be recorded for compliance.</p>
        
        <hr style="border-color: #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          57B, Isaac John Street, Yaba, Lagos<br>
          <a href="https://www.eximps-cloves.com" style="color: #999; text-decoration: none;">www.eximps-cloves.com</a>
        </p>
      </div>
    </div>"""

async def send_staff_signing_request_email(staff_name: str, email_addr: str, doc_title: str, signing_url: str, custom_message: str = None):
    logger.info(f"Attempting to send signing request to {email_addr} for '{doc_title}'")
    try:
        res = await async_resend({
            "from": f"Eximp & Cloves Personnel <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "admin@eximps-cloves.com",
            "cc": ["legal@eximps-cloves.com"],
            "subject": f"Action Required: Signature Requested - {doc_title}",
            "html": _staff_signing_html(staff_name, doc_title, signing_url, custom_message)
        })
        logger.info(f"Resend API Response for {email_addr}: {res}")
        return res
    except Exception as e:
        logger.error(f"FATAL: Error sending signing request email to {email_addr}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def send_personnel_executed_email(
    signer_name: str,
    signer_email: str,
    doc_title: str,
    matter_id: str,
    pdf_bytes: bytes,
    audit_entries: list,
    download_token: str
):
    """
    Sent to the signer immediately after they execute a personnel document.
    Attaches the signed PDF and includes a brief audit trail in the email body.
    """
    if not signer_email:
        return

    executed_date = datetime.now(timezone(timedelta(hours=1))).strftime("%d %B %Y at %H:%M")
    download_url = f"https://app.eximps-cloves.com/api/hr-legal/matters/{matter_id}/export?token={download_token}"

    # Build audit rows
    audit_rows = ""
    for entry in audit_entries[:10]:  # cap at 10 events
        action = entry.get("action", "—")
        desc = entry.get("description", "")
        ts = ""
        try:
            ts = datetime.fromisoformat(entry["created_at"]).strftime("%d %b %Y, %H:%M")
        except Exception:
            ts = entry.get("created_at", "")
        audit_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:12px;color:#555;">{ts}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:12px;font-weight:600;color:#333;">{action}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:12px;color:#888;">{desc}</td>
        </tr>"""

    html = f"""
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;max-width:640px;margin:auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
      <!-- Header -->
      <div style="background:#0F1115;padding:28px 36px;text-align:center;">
        <img src="https://app.eximps-cloves.com/static/img/logo_dark.svg" alt="Eximp &amp; Cloves" style="height:36px;">
        <p style="color:#C47D0A;font-size:11px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin:10px 0 0;">Legal Department</p>
      </div>

      <!-- Body -->
      <div style="padding:36px;">
        <div style="text-align:center;margin-bottom:28px;">
          <div style="font-size:48px;">✅</div>
          <h2 style="color:#16a34a;font-size:20px;font-weight:800;margin:8px 0;">Document Successfully Executed</h2>
          <p style="color:#6b7280;font-size:13px;margin:0;">{executed_date}</p>
        </div>

        <p style="color:#374151;font-size:14px;line-height:1.7;">Dear <strong>{signer_name}</strong>,</p>
        <p style="color:#374151;font-size:14px;line-height:1.7;">
          This is to confirm that you have successfully signed the following document:
        </p>

        <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px 20px;margin:20px 0;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#111;">📄 {doc_title}</p>
          <p style="margin:6px 0 0;font-size:12px;color:#6b7280;">Eximp &amp; Cloves Infrastructure Limited</p>
        </div>

        <p style="color:#374151;font-size:14px;line-height:1.7;">
          Your signed copy is attached to this email as a PDF. Please keep it in a safe place — it is a legally binding document.
        </p>

        <div style="text-align:center;margin:28px 0;">
          <a href="{download_url}" style="background:#C47D0A;color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:13px;display:inline-block;">
            ⬇ Download Your Copy
          </a>
        </div>

        <!-- Audit Trail -->
        <div style="margin-top:32px;">
          <p style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px;">Audit Trail</p>
          <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
            <thead>
              <tr style="background:#f9fafb;">
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#9ca3af;text-transform:uppercase;font-weight:700;border-bottom:1px solid #e5e7eb;">Time</th>
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#9ca3af;text-transform:uppercase;font-weight:700;border-bottom:1px solid #e5e7eb;">Action</th>
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#9ca3af;text-transform:uppercase;font-weight:700;border-bottom:1px solid #e5e7eb;">Details</th>
              </tr>
            </thead>
            <tbody>{audit_rows}</tbody>
          </table>
        </div>

        <p style="color:#9ca3af;font-size:12px;margin-top:32px;line-height:1.6;">
          If you did not sign this document or believe this is an error, please contact us immediately at
          <a href="mailto:legal@eximps-cloves.com" style="color:#C47D0A;text-decoration:none;">legal@eximps-cloves.com</a>
        </p>
      </div>

      <div style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:16px 36px;text-align:center;">
        <p style="color:#9ca3af;font-size:11px;margin:0;">Eximp &amp; Cloves Infrastructure Limited · <a href="https://eximps-cloves.com" style="color:#C47D0A;text-decoration:none;">eximps-cloves.com</a></p>
      </div>
    </div>"""

    try:
        attachments = []
        if pdf_bytes:
            attachments.append({
                "content": base64.b64encode(pdf_bytes).decode(),
                "filename": f"Executed_{doc_title.replace(' ', '_')}.pdf"
            })
        await async_resend({
            "from": f"Eximp & Cloves Legal <{FROM_EMAIL}>",
            "to": [signer_email],
            "reply_to": "admin@eximps-cloves.com",
            "cc": ["legal@eximps-cloves.com"],
            "subject": f"✅ Your Signed Document: {doc_title}",
            "html": html,
            "attachments": attachments
        })
        logger.info(f"Post-signing email sent to {signer_email} for matter {matter_id}")
    except Exception as e:
        logger.error(f"Error sending post-signing email to {signer_email}: {e}")

# ─── Talent Pool Chat — Follow-up email ──────────────────────────────────────

def _talent_chat_followup_html(name: str, chat_url: str) -> str:
    return f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;border-radius:8px;border:1px solid #ddd;overflow:hidden;">
  <div style="background:#1A1A1A;padding:24px;text-align:center;">
    <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height:48px;display:block;margin:0 auto;">
  </div>
  <div style="background:#C47D0A;padding:12px 24px;text-align:center;">
    <h2 style="color:#1A1A1A;margin:0;font-size:18px;">💬 Message Waiting for You</h2>
  </div>
  <div style="padding:32px 24px;background:#fff;">
    <p style="color:#333;font-size:16px;">Dear <strong>{name}</strong>,</p>
    <p style="color:#555;line-height:1.6;margin:16px 0;">
      Our HR team has sent you a message regarding your talent profile with 
      <strong>Eximp &amp; Cloves</strong>, and we haven't heard back from you yet.
    </p>
    <p style="color:#555;line-height:1.6;margin:16px 0;">
      It takes just a moment to reply — click below to open the private chat thread:
    </p>
    <div style="text-align:center;margin:35px 0;">
      <a href="{chat_url}" 
         style="background-color:#C47D0A;color:#ffffff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:bold;font-size:16px;display:inline-block;">
        Open Chat Conversation
      </a>
    </div>
    <p style="color:#999;font-size:12px;line-height:1.5;">
      This is a private, secure thread between you and our HR team. 
      You can share files and documents directly in the chat.
    </p>
    <hr style="border-color:#eee;margin:30px 0;">
    <p style="color:#999;font-size:12px;margin:0;text-align:center;">
      Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>
      57B, Isaac John Street, Yaba, Lagos<br>
      <a href="https://www.eximps-cloves.com" style="color:#999;text-decoration:none;">www.eximps-cloves.com</a>
    </p>
  </div>
</div>"""


async def send_talent_chat_followup_email(email_addr: str, name: str, chat_url: str):
    try:
        await async_resend({
            "from": f"Eximp & Cloves HR <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "hr@eximps-cloves.com",
            "subject": "💬 You have an unread message from Eximp & Cloves HR",
            "html": _talent_chat_followup_html(name, chat_url),
        })
        logger.info(f"Talent chat follow-up sent to {email_addr}")
    except Exception as e:
        logger.error(f"Failed to send talent chat follow-up to {email_addr}: {e}")


async def send_talent_chat_invite_email(email_addr: str, name: str, chat_url: str, hr_name: str = "Our HR Team"):
    """Sent when HR first opens a chat room and wants to invite the applicant."""
    html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;border-radius:8px;border:1px solid #ddd;overflow:hidden;">
  <div style="background:#1A1A1A;padding:24px;text-align:center;">
    <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style="max-height:48px;display:block;margin:0 auto;">
  </div>
  <div style="background:#C47D0A;padding:12px 24px;text-align:center;">
    <h2 style="color:#1A1A1A;margin:0;font-size:18px;">🎉 HR Would Like to Chat With You</h2>
  </div>
  <div style="padding:32px 24px;background:#fff;">
    <p style="color:#333;font-size:16px;">Dear <strong>{name}</strong>,</p>
    <p style="color:#555;line-height:1.6;margin:16px 0;">
      <strong>{hr_name}</strong> from <strong>Eximp &amp; Cloves</strong> has opened a private chat 
      thread with you. This is a great opportunity to discuss potential roles and opportunities.
    </p>
    <p style="color:#555;line-height:1.6;">
      You can send text messages and share files (CV, portfolio, certificates) directly in the chat.
    </p>
    <div style="text-align:center;margin:35px 0;">
      <a href="{chat_url}" 
         style="background-color:#C47D0A;color:#ffffff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:bold;font-size:16px;display:inline-block;">
        Open My Chat Thread
      </a>
    </div>
    <p style="color:#999;font-size:12px;text-align:center;">
      No account needed — your unique link is all you need to access this private conversation.
    </p>
    <hr style="border-color:#eee;margin:30px 0;">
    <p style="color:#999;font-size:12px;margin:0;text-align:center;">
      Eximp &amp; Cloves Infrastructure Limited | RC 8311800<br>
      57B, Isaac John Street, Yaba, Lagos
    </p>
  </div>
</div>"""
    try:
        await async_resend({
            "from": f"Eximp & Cloves HR <{FROM_EMAIL}>",
            "to": [email_addr],
            "reply_to": "hr@eximps-cloves.com",
            "subject": f"💬 {hr_name} has started a chat with you — Eximp & Cloves",
            "html": html,
        })
        logger.info(f"Talent chat invite sent to {email_addr}")
    except Exception as e:
        logger.error(f"Failed to send talent chat invite to {email_addr}: {e}")