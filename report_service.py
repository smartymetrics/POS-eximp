import os
import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
import pandas as pd
from xhtml2pdf import pisa
from database import supabase
from utils import resolve_invoice_status

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportService:
    @staticmethod
    async def get_report_data(report_type: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch and aggregate data for reports."""
        # Provide defaults for empty dates
        if not start_date: start_date = "2000-01-01"
        if not end_date: end_date = datetime.now().strftime("%Y-%m-%d")

        if report_type == "sales_summary":
            res = supabase.table("invoices").select("invoice_number, invoice_date, property_name, amount, amount_paid, status, sales_rep_name, clients(full_name, email)").gte("invoice_date", start_date).lte("invoice_date", end_date).order("invoice_date", desc=True).execute()
            data = res.data or []
            rows = []
            for i in data:
                amt = float(i.get("amount", 0))
                paid = float(i.get("amount_paid", 0))
                rows.append({
                    "Invoice #": i.get("invoice_number", ""),
                    "Date": i.get("invoice_date", ""),
                    "Client": i.get("clients", {}).get("full_name", "") if i.get("clients") else "",
                    "Property": i.get("property_name", ""),
                    "Amount (NGN)": f"₦{amt:,.2f}",
                    "Paid (NGN)": f"₦{paid:,.2f}",
                    "Balance (NGN)": f"₦{(amt - paid):,.2f}",
                    "Sales Rep": i.get("sales_rep_name", "—"),
                    "Status": i.get("status", "").capitalize()
                })
            stats = {
                "total_invoiced": sum(float(i.get("amount", 0)) for i in data),
                "total_collected": sum(float(i.get("amount_paid", 0)) for i in data),
                "count": len(data)
            }
            return {"items": rows, "stats": stats, "type": "Sales Summary"}

        elif report_type == "collection_report":
            # Optimization: Only fetch non-paid invoices to save bandwidth/latency
            res = supabase.table("invoices").select("invoice_number, invoice_date, due_date, property_name, amount, amount_paid, status, clients(full_name, email, phone)").neq("status", "paid").execute()
            data = res.data or []

            today = datetime.now().date()
            rows = []
            for inv in data:
                amount = float(inv.get("amount", 0))
                paid = float(inv.get("amount_paid", 0))
                balance = amount - paid
                if balance <= 0: continue
                
                resolved_status = resolve_invoice_status(inv)
                days_overdue = "—"
                if resolved_status == "overdue" and inv.get("due_date"):
                    try:
                        due_date = datetime.strptime(inv["due_date"], "%Y-%m-%d").date()
                        days_overdue = (today - due_date).days
                    except: pass
                
                rows.append({
                    "Invoice #": inv.get("invoice_number", ""),
                    "Client": inv.get("clients", {}).get("full_name", "") if inv.get("clients") else "",
                    "Phone": inv.get("clients", {}).get("phone", "") if inv.get("clients") else "",
                    "Property": inv.get("property_name", ""),
                    "Total (NGN)": f"₦{amount:,.2f}",
                    "Paid (NGN)": f"₦{paid:,.2f}",
                    "Balance (NGN)": f"₦{balance:,.2f}",
                    "Due Date": inv.get("due_date", ""),
                    "Status": resolved_status.capitalize(),
                    "Days Overdue": days_overdue
                })

            def sort_key(x):
                s = x["Status"].lower()
                if s == "overdue": return 0
                if s == "partial": return 1
                return 2
            rows.sort(key=sort_key)
            return {"items": rows, "stats": {"count": len(rows)}, "type": "Outstanding Payments"}

        elif report_type == "rep_performance":
            res = supabase.table("invoices").select("sales_rep_name, amount, amount_paid").gte("invoice_date", start_date).lte("invoice_date", end_date).execute()
            df = pd.DataFrame(res.data or [])
            if df.empty: return {"items": [], "stats": {}, "type": "Sales Rep Performance"}

            df["amount"] = df["amount"].astype(float)
            df["amount_paid"] = df["amount_paid"].astype(float)
            summary = df.groupby("sales_rep_name").agg(
                Deals=("amount", "count"),
                Revenue=("amount", "sum"),
                Collected=("amount_paid", "sum")
            ).reset_index()
            summary["Collection Rate"] = (summary["Collected"] / summary["Revenue"] * 100).round(1).astype(str) + "%"
            summary["Revenue"] = summary["Revenue"].apply(lambda x: f"₦{x:,.2f}")
            summary["Collected"] = summary["Collected"].apply(lambda x: f"₦{x:,.2f}")
            summary = summary.rename(columns={"sales_rep_name": "Sales Rep"}).sort_values("Deals", ascending=False)
            return {"items": summary.to_dict("records"), "stats": {}, "type": "Sales Rep Performance"}

        elif report_type == "client_register":
            res = supabase.table("clients").select("full_name, email, phone, nationality, occupation, referral_source, created_at, invoices(property_name)").order("created_at", desc=True).execute()
            data = res.data or []
            rows = []
            for c in data:
                invoices = c.get("invoices") or []
                props = "; ".join(set(i.get("property_name", "") for i in invoices if i.get("property_name")))
                rows.append({
                    "Full Name": c.get("full_name", ""),
                    "Email": c.get("email", ""),
                    "Phone": c.get("phone", ""),
                    "Nationality": c.get("nationality", ""),
                    "Occupation": c.get("occupation", ""),
                    "Referral Source": c.get("referral_source", ""),
                    "Properties": props or "None",
                    "Date Registered": c.get("created_at", "")[:10] if c.get("created_at") else "",
                })
            return {"items": rows, "stats": {"count": len(rows)}, "type": "Client Register"}

        return {"items": [], "stats": {}, "type": "Report"}

    @staticmethod
    def generate_pdf(data: Dict[str, Any], title: str) -> io.BytesIO:
        """Constructs a professional PDF document."""
        items = data.get("items", [])
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: a4 landscape; margin: 1cm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; color: #2d3436; }}
                .header {{ border-bottom: 2px solid #F5A623; padding-bottom: 10px; margin-bottom: 20px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #1A1A1A; }}
                .title {{ font-size: 18px; color: #636e72; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #f1f2f6; color: #2f3542; text-align: left; padding: 8px; font-size: 10px; border-bottom: 1px solid #dfe4ea; }}
                td {{ padding: 8px; border-bottom: 1px solid #f1f2f6; font-size: 10px; }}
                .footer {{ position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 8px; color: #a4b0be; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">EXIMP & CLOVES</div>
                <div class="title">{title}</div>
                <div style="font-size: 10px; color: #747d8c;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            </div>
            <table>
                <thead>
                    <tr>
                        {"".join([f"<th>{str(k).upper()}</th>" for k in items[0].keys()]) if items else "<th>NO DATA</th>"}
                    </tr>
                </thead>
                <tbody>
                    {"".join([
                        "<tr>" + "".join([f"<td>{str(v)}</td>" for v in row.values()]) + "</tr>"
                        for row in items
                    ]) if items else "<tr><td>No records found.</td></tr>"}
                </tbody>
            </table>
            <div class="footer">Eximp & Cloves Infrastructure Limited - Confidential Report</div>
        </body>
        </html>
        """
        result = io.BytesIO()
        pisa.CreatePDF(html, dest=result)
        result.seek(0)
        return result

    @staticmethod
    def generate_excel(data: Dict[str, Any], title: str) -> io.BytesIO:
        """Builds a professional Excel spreadsheet."""
        df = pd.DataFrame(data.get("items", []))
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
            # Basic auto-width
            worksheet = writer.sheets['Data']
            for col in worksheet.columns:
                max_len = max([len(str(cell.value) or "") for cell in col])
                worksheet.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
        output.seek(0)
        return output
