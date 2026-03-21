import os
import io
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
import pandas as pd
from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader
from database import supabase

# Setup Jinja2 environment for HTML templates (reports)
# In a real app, you'd have a 'templates/reports' directory
# But for now I'll use a string template or look for one
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "reports")
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR, exist_ok=True)

class ReportService:
    @staticmethod
    async def get_report_data(report_type: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch and aggregate data for reports."""
        if report_type == "sales_summary":
            res = supabase.table("invoices").select("*, clients(full_name, email)").gte("invoice_date", start_date).lte("invoice_date", end_date).execute()
            data = res.data
            stats = {
                "total_invoiced": sum(float(i["amount"]) for i in data),
                "total_collected": sum(float(i["amount_paid"]) for i in data),
                "count": len(data)
            }
            return {"items": data, "stats": stats, "type": "Sales Summary"}
            
        elif report_type == "collection_report":
            res = supabase.table("invoices").select("*, clients(full_name, email)").gt("balance_due", 0).execute()
            data = res.data
            stats = {
                "total_outstanding": sum(float(i["balance_due"]) for i in data),
                "overdue_count": len([i for i in data if datetime.strptime(i["due_date"], "%Y-%m-%d").date() < datetime.now().date()])
            }
            return {"items": data, "stats": stats, "type": "Collection & Outstanding"}
            
        elif report_type == "rep_performance":
            res = supabase.table("invoices").select("sales_rep_name, amount, amount_paid").gte("invoice_date", start_date).lte("invoice_date", end_date).execute()
            df = pd.DataFrame(res.data)
            if df.empty:
                return {"items": [], "stats": {}, "type": "Sales Rep Performance"}
            
            summary = df.groupby("sales_rep_name").agg({
                "amount": "sum",
                "amount_paid": "sum",
                "sales_rep_name": "count"
            }).rename(columns={"sales_rep_name": "deals"}).reset_index()
            
            summary["collection_rate"] = (summary["amount_paid"] / summary["amount"]) * 100
            summary = summary.sort_values("amount", ascending=False)
            
            return {"items": summary.to_dict("records"), "stats": {}, "type": "Sales Rep Performance"}

        return {"items": [], "stats": {}, "type": "General Report"}

    @staticmethod
    def generate_pdf(data: Dict[str, Any], title: str) -> io.BytesIO:
        """Generate a professional PDF using HTML/CSS."""
        # Professional HTML Template (inline for reliability)
        html = f"""
        <html>
        <head>
            <style>
                @page {{ size: a4 portrait; margin: 2cm; }}
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #2d3436; line-height: 1.6; }}
                .header {{ border-bottom: 2px solid #C47D0A; padding-bottom: 20px; margin-bottom: 30px; }}
                .logo {{ color: #C47D0A; font-size: 24px; font-weight: bold; }}
                .title {{ font-size: 20px; font-weight: bold; margin-bottom: 5px; }}
                .meta {{ font-size: 11px; color: #636e72; }}
                .stats-grid {{ display: block; margin-bottom: 30px; }}
                .stat-box {{ display: inline-block; width: 30%; background: #f8f9fa; padding: 15px; border-radius: 8px; margin-right: 2%; }}
                .stat-label {{ font-size: 10px; text-transform: uppercase; color: #636e72; }}
                .stat-value {{ font-size: 16px; font-weight: bold; color: #2d3436; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #2d3436; color: white; text-align: left; padding: 10px; font-size: 11px; }}
                td {{ padding: 10px; border-bottom: 1px solid #dfe6e9; font-size: 11px; }}
                .footer {{ position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 9px; color: #b2bec3; border-top: 1px solid #dfe6e9; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">EXIMP & CLOVES</div>
                <div class="title">{title}</div>
                <div class="meta">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            </div>

            <div class="stats-grid">
                <!-- Add dynamic stats here if needed -->
            </div>

            <table>
                <thead>
                    <tr>
                        {"".join([f"<th>{k.replace('_', ' ').upper()}</th>" for k in data['items'][0].keys()]) if data['items'] else "<th>No Data</th>"}
                    </tr>
                </thead>
                <tbody>
                    {"".join([
                        "<tr>" + "".join([f"<td>{v}</td>" for v in item.values()]) + "</tr>"
                        for item in data['items']
                    ]) if data['items'] else "<tr><td>No data found for the selected criteria.</td></tr>"}
                </tbody>
            </table>

            <div class="footer">
                Confidential Document - Eximp & Cloves Infrastructure Limited
            </div>
        </body>
        </html>
        """
        result = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html), dest=result)
        result.seek(0)
        return result

    @staticmethod
    def generate_excel(data: Dict[str, Any], title: str) -> io.BytesIO:
        """Generate a professional Excel file with formatting."""
        df = pd.DataFrame(data['items'])
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
            
            # Formatting (Simple version)
            workbook = writer.book
            worksheet = writer.sheets['Report']
            
            # Set column widths
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except: pass
                worksheet.column_dimensions[column].width = max_length + 2

        output.seek(0)
        return output
