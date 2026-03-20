import resend
import os
import base64
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf
from database import get_db

resend.api_key = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "finance@eximps-cloves.com")


def _b64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode()


def _invoice_html(invoice: dict, client: dict) -> str:
    amount = float(invoice["amount"])
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>
        <p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>
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
        <h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>
        <p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>
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
        <h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>
        <p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>
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
        "attachments": [{"filename": f"Invoice_{invoice['invoice_number']}.pdf", "content": list(pdf)}],
    })


async def send_receipt_email(invoice: dict, client: dict, sent_by: str):
    pdf = generate_receipt_pdf(invoice)
    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Payment Receipt — {invoice['invoice_number']}",
        "html": _receipt_html(invoice, client),
        "attachments": [{"filename": f"Receipt_{invoice['invoice_number']}.pdf", "content": list(pdf)}],
    })


async def send_statement_email(invoices: list, client: dict, sent_by: str):
    pdf = generate_statement_pdf(invoices, client)
    total_invoiced = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(float(p["amount"]) for i in invoices for p in (i.get("payments") or []))
    balance = total_invoiced - total_paid

    resend.Emails.send({
        "from": f"Eximp & Cloves Finance <{FROM_EMAIL}>",
        "to": [client["email"]],
        "subject": f"Statement of Account — {client['full_name']}",
        "html": _statement_html(client, total_invoiced, total_paid, balance),
        "attachments": [{"filename": f"Statement_{client['full_name'].replace(' ', '_')}.pdf", "content": list(pdf)}],
    })
