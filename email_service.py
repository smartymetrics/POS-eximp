import resend
import os
import base64
import time
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf, COMPANY
from database import get_db
from utils import sanitize_client_address
from datetime import datetime
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
        <p style="color: #555; font-size: 13px;">The full receipt PDF is attached to this email.</p>
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
      <div style="background: #f4f4f4; padding: 20px; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee;">
        Eximp & Cloves Infrastructure Limited | RC 8311800
      </div>
    </div>"""

def _commission_paid_html(rep: dict, batch: dict) -> str:
    amount_val = float(batch.get("total_amount", 0))
    amount_str = "{:,.2f}".format(amount_val)
    rep_name = str(rep.get("name", "Rep"))
    ref_val = str(batch.get("reference", "N/A"))
    date_val = str(batch.get("paid_at", "")[:10])
    
    # Use replacement to avoid ANY f-string/format parsing issues with braces in HTML or quotes
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
        <p style="color: #555;">We are pleased to inform you that a commission payout has been processed for you.</p>
        
        <div style="background: #f9f9f9; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
          <p style="color: #888; margin: 0 0 8px; font-size: 13px; text-transform: uppercase;">Amount Paid</p>
          <p style="color: #27ae60; font-size: 32px; font-weight: bold; margin: 0;">NGN {{amount_str}}</p>
          <hr style="border-color: #ddd; margin: 16px 0;">
          <p style="color: #555; font-size: 13px;">Reference: <strong>{{reference}}</strong></p>
          <p style="color: #555; font-size: 12px;">Date: {{date_str}}</p>
        </div>
        
        <p style="color: #555; font-size: 13px;">Please check your bank account or contact the Finance Department if you have any questions.</p>
        <p style="color: #555; font-size: 13px;">Keep up the great work!</p>
        
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          Block 57B, Isaac John Street, Yaba, Lagos | +234 912 686 4383
        </p>
      </div>
    </div>"""
    return html.replace("{{rep_name}}", rep_name).replace("{{amount_str}}", amount_str).replace("{{reference}}", ref_val).replace("{{date_str}}", date_val)

async def send_commission_paid_email(rep: dict, batch: dict):
    from routers.analytics import log_activity
    if not rep.get("email"):
        return
        
    email_addr = rep["email"]
    rep_name = rep.get("name", "Rep")
    
    try:
        res = resend.Emails.send({
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

def send_signing_link_email(invoice, client, token, expires_at):
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
        res = resend.Emails.send({
            "from": "Eximp & Cloves Legal <" + str(sender) + ">",
            "to": email_addr,
            "cc": CLIENT_CC_RECIPIENTS,
            "subject": "Your Contract of Sale is Ready — Eximp & Cloves",
            "html": html
        })
        return res
    except Exception as e:
        logger.error("Error sending signing link email: " + str(e))
        return None

def send_admin_signing_alert(invoice, client, witnesses):
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
        resend.Emails.send({
            "from": "System Alert <" + str(sender) + ">",
            "to": admin_email,
            "subject": "Contract Ready: " + str(client.get("full_name")) + " (" + str(invoice.get("invoice_number")) + ")",
            "html": html
        })
    except Exception as e:
        logger.error("Error sending admin signing alert: " + str(e))

def send_executed_contract_email(invoice, client, pdf_content, certificate_pdf=None):
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
        Execution Date: {datetime.now().strftime("%B %d, %Y")}</p>

        <p>Our documentation team will contact you shortly regarding the next steps (Survey and Allocation).</p>
        <p>Thank you for choosing Eximp & Cloves Infrastructure Limited.</p>
        <p>Best regards,<br>Legal Department</p>
        <hr style="border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #888; font-size: 11px; text-align: center;">Please review our official refund policy at <a href="https://www.eximps-cloves.com/refund" style="color: #C47D0A; text-decoration: none;">www.eximps-cloves.com/refund</a></p>
    </div>
    """

    try:
        import resend
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Legal <{sender}>",
            "to": [email_addr],
            "cc": CLIENT_CC_RECIPIENTS,
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
        res = resend.Emails.send({
            "from": "Eximp & Cloves Legal <" + str(sender) + ">",
            "to": [witness_email],
            "cc": CLIENT_CC_RECIPIENTS,
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
        "linkedin": "https://img.icons8.com/ios-filled/50/ffffff/linkedin.png"
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
            
            resend.Emails.send({
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
                    "updated_at": datetime.now().isoformat()
                }).eq("id", campaign_id).execute()
                
            # Optional: Add a small delay to respect rate limits if needed
            # time.sleep(0.1) 
            
        except Exception as e:
            logger.error(f"Error sending campaign {campaign_id} to {email_addr}: {e}")

    # Final Update
    db.table("marketing_campaigns").update({
        "status": "sent",
        "delivered_count": delivered,
        "sent_at": datetime.now().isoformat()
    }).eq("id", campaign_id).execute()

    logger.info(f"Campaign {campaign_id} broadcast finished. Delivered: {delivered}/{total}")


def _payout_receipt_html(payout: dict, vendor: dict, payment_amount: float = None) -> str:
    # Use payment_amount if passed, else fallback to net_payout_amount (old behavior)
    amount_now = float(payment_amount or payout.get("net_payout_amount") or 0)
    total_paid = float(payout.get("amount_paid") or 0)
    total_due = float(payout.get("net_payout_amount") or 0)
    balance = max(0, total_due - total_paid)
    ref = payout.get("payout_reference") or "N/A"
    
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
            <tr><td>Payee Bank</td><td style="text-align:right;color:#fff;">{vendor.get('bank_name','N/A')}</td></tr>
            <tr><td>Account</td><td style="text-align:right;color:#fff;">{vendor.get('account_number','N/A')}</td></tr>
          </table>
        </div>
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
        res = resend.Emails.send({
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
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; color: #888;">Signed On</td><td style="padding: 8px; border-bottom: 1px solid #eee;">{datetime.now().strftime("%B %d, %Y at %I:%M %p")}</td></tr>
        </table>

        <div style="text-align: center; margin-top: 24px;">
            <a href="https://eximp-cloves.com/legal" style="background: #C47D0A; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">Open Legal Dashboard</a>
        </div>
        
        <p style="color: #888; font-size: 12px; margin-top: 24px; text-align: center;">This is an automated notification from the Eximp & Cloves Legal Suite.</p>
    </div>
    """

    try:
        import resend
        res = resend.Emails.send({
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
    portal_link = f"https://app.eximps-cloves.com/payout/portal/{token}"
    
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
        res = resend.Emails.send({
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
        </div>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #888; font-size: 12px;">This is a response to your support ticket #{ticket.get('id', '').split('-')[0]}. You can reply to this email if you have further questions.</p>
        <p style="color: #999; font-size: 11px; margin-top: 12px;">Eximp & Cloves Infrastructure Limited | RC 8311800<br>
        57B, Isaac John Street, Yaba, Lagos</p>
      </div>
    </div>"""

async def send_support_response_email(ticket: dict, message: str):
    email_addr = ticket.get("contact_email")
    if not email_addr: return
    
    try:
        res = resend.Emails.send({
            "from": f"Eximp & Cloves Support <{FROM_EMAIL}>",
            "to": [email_addr],
            "subject": f"Re: {ticket.get('subject')}",
            "html": _support_response_html(ticket, message),
            "reply_to": "admin@eximps-cloves.com"
        })
        return res
    except Exception as e:
        logger.error(f"Error sending support response email to {email_addr}: {e}")
        return None
