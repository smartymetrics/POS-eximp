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
from pdf_service import COMPANY

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
            res = supabase.table("invoices").select("invoice_number, invoice_date, property_name, amount, amount_paid, status, sales_rep_name, clients(full_name, email)").gte("invoice_date", start_date).lte("invoice_date", end_date).neq("status", "voided").order("invoice_date", desc=True).execute()
            data = res.data or []
            rows = []
            for i in data:
                amt = float(i.get("amount") or 0)
                paid = float(i.get("amount_paid") or 0)
                rows.append({
                    "Invoice #": i.get("invoice_number", ""),
                    "Date": i.get("invoice_date", ""),
                    "Client": i.get("clients", {}).get("full_name", "") if i.get("clients") else "",
                    "Property": i.get("property_name", ""),
                    "Amount (NGN)": f"NGN {amt:,.2f}",
                    "Paid (NGN)": f"NGN {paid:,.2f}",
                    "Balance (NGN)": f"NGN {(amt - paid):,.2f}",
                    "Sales Rep": i.get("sales_rep_name", "—"),
                    "Status": i.get("status", "").capitalize()
                })
            stats = {
                "total_invoiced": sum(float(i.get("amount") or 0) for i in data),
                "total_collected": sum(float(i.get("amount_paid") or 0) for i in data),
                "count": len(data)
            }
            return {"items": rows, "stats": stats, "type": "Sales Summary"}

        elif report_type == "collection_report":
            # Optimization: Only fetch non-paid and non-voided invoices
            res = supabase.table("invoices").select("invoice_number, invoice_date, due_date, property_name, amount, amount_paid, balance_due, status, clients(full_name, email, phone)").neq("status", "paid").neq("status", "voided").execute()
            data = res.data or []

            today = datetime.now().date()
            rows = []
            for inv in data:
                amount = float(inv.get("amount") or 0)
                paid = float(inv.get("amount_paid") or 0)
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
                    "Total (NGN)": f"NGN {amount:,.2f}",
                    "Paid (NGN)": f"NGN {paid:,.2f}",
                    "Balance (NGN)": f"NGN {balance:,.2f}",
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
            active_reps_res = supabase.table("sales_reps").select("name").eq("is_active", True).execute()
            active_names = [r["name"] for r in (active_reps_res.data or [])]
            
            if not active_names:
                return {"items": [], "stats": {}, "type": "Sales Rep Performance"}
                
            res = supabase.table("invoices").select("sales_rep_name, amount, amount_paid").gte("invoice_date", start_date).lte("invoice_date", end_date).neq("status", "voided").in_("sales_rep_name", active_names).execute()
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
            summary["Revenue"] = summary["Revenue"].apply(lambda x: f"NGN {x:,.2f}")
            summary["Collected"] = summary["Collected"].apply(lambda x: f"NGN {x:,.2f}")
            summary = summary.rename(columns={"sales_rep_name": "Sales Rep"}).sort_values("Deals", ascending=False)
            return {"items": summary.to_dict("records"), "stats": {}, "type": "Sales Rep Performance"}

        elif report_type == "client_register":
            res = supabase.table("clients").select("full_name, email, phone, address, title, middle_name, gender, dob, marital_status, occupation, nin, id_number, nationality, nok_name, nok_phone, nok_relationship, source_of_income, referral_source, created_at, invoices(property_name, purchase_purpose)").order("created_at", desc=True).execute()
            data = res.data or []
            rows = []
            for c in data:
                invoices = c.get("invoices") or []
                # Create a list of "Property Name (Purpose)" strings
                prop_list = []
                for i in invoices:
                    p_name = i.get("property_name")
                    p_purpose = i.get("purchase_purpose")
                    if p_name:
                        entry = p_name
                        if p_purpose:
                            entry += f" ({p_purpose})"
                        prop_list.append(entry)
                
                # Deduplicate and join
                props_display = "; ".join(sorted(set(prop_list))) if prop_list else "None"
                
                name_parts = [p for p in [c.get("title"), c.get("full_name"), c.get("middle_name")] if p]
                full_name_str = " ".join(name_parts) or "Unknown Client"
                
                demographics = [d for d in [c.get("gender"), c.get("marital_status")] if d]
                demo_str = ", ".join(demographics)
                
                client_details = full_name_str.upper()
                if demo_str: client_details += f"\n{demo_str}"
                if c.get("dob"): client_details += f"\nDOB: {c.get('dob')}"
                
                contact_info = "\n".join([v for v in [c.get("phone"), c.get("email"), c.get("address")] if v])
                
                identification = f"Nat: {c.get('nationality', 'N/A')}\nID: {c.get('id_number', 'N/A')}\nOcc: {c.get('occupation', 'N/A')}\nNIN: {c.get('nin', 'N/A')}"
                
                nok_details = "\n".join([v for v in [c.get("nok_name"), c.get("nok_phone")] if v]) or "N/A"
                if c.get("nok_relationship"): nok_details += f" ({c.get('nok_relationship')})"
                if c.get("nok_occupation"): nok_details += f"\nOcc: {c.get('nok_occupation')}"
                
                sales_info = f"Props: {props_display}\nReferral: {c.get('referral_source', 'N/A')}\nIncome: {c.get('source_of_income', 'N/A')}\nReg: {c.get('created_at', '')[:10]}"

                rows.append({
                    "Client Details": client_details,
                    "Contact Info": contact_info,
                    "Identification": identification,
                    "Next of Kin": nok_details,
                    "Sales Info": sales_info
                })
            return {"items": rows, "stats": {"count": len(rows)}, "type": "Client Register & KYC Report"}

        elif report_type == "commission_report":
            end_timestamp = end_date + "T23:59:59"
            res = supabase.table("commission_earnings").select("*, sales_reps(name), clients(full_name), invoices(invoice_number, status)").gte("created_at", start_date).lte("created_at", end_timestamp).order("created_at", desc=True).execute()
            data = res.data or []
            rows = []
            for c in data:
                if c.get("invoices", {}).get("status") == "voided":
                    continue
                rows.append({
                    "Date": str(c.get("created_at"))[:10] if c.get("created_at") else "",
                    "Sales Rep": c.get("sales_reps", {}).get("name", "Unknown") if c.get("sales_reps") else "Unknown",
                    "Client": c.get("clients", {}).get("full_name", "") if c.get("clients") else "",
                    "Invoice": c.get("invoices", {}).get("invoice_number", "") if c.get("invoices") else "",
                    "Estate": c.get("estate_name", ""),
                    "Deposit": f"NGN {float(c.get('payment_amount') or 0):,.2f}",
                    "Rate": f"{float(c.get('commission_rate') or 0)}%",
                    "Earning": f"NGN {float(c.get('final_amount') or 0):,.2f}",
                    "Status": "Paid" if c.get("is_paid") else "Unpaid"
                })
            return {"items": rows, "stats": {"count": len(rows)}, "type": "Commission Earned Report"}

        elif report_type == "inventory_report":
            res = supabase.table("properties").select("name, location, description, plot_size_sqm, total_price, is_active").eq("is_archived", False).order("name").execute()
            data = res.data or []
            rows = []
            for p in data:
                rows.append({
                    "Estate Name": p.get("name", "—"),
                    "Location": p.get("location", "—"),
                    "Description": p.get("description", "—"),
                    "Size": f"{p.get('plot_size_sqm', 0)} SQM",
                    "Price": f"NGN {float(p.get('total_price') or 0):,.2f}",
                    "Status": "Active" if p.get("is_active") else "Inactive"
                })
            stats = {
                "total_estates": len(set(p.get("name") for p in data if p.get("name"))),
                "active": sum(1 for p in data if p.get("is_active")),
                "inactive": sum(1 for p in data if not p.get("is_active"))
            }
            return {"items": rows, "stats": stats, "type": "Property Inventory Status"}

        return {"items": [], "stats": {}, "type": "Report"}

    @staticmethod
    def generate_pdf(data: Dict[str, Any], title: str) -> io.BytesIO:
        """Constructs a professional PDF document using WeasyPrint for high-quality rendering."""
        from pdf_service import get_company_context, env, format_currency
        from weasyprint import HTML
        
        # Mapping report types to templates
        report_type = data.get("type", "")
        template_map = {
            "Property Inventory Status": "inventory_report.html",
            "Sales Summary": "standard_report.html",
            "Outstanding Payments": "standard_report.html",
            "Sales Rep Performance": "standard_report.html",
            "Client Register & KYC Report": "standard_report.html",
            "Commission Earned Report": "standard_report.html"
        }
        
        template_name = template_map.get(report_type, "standard_report.html")

        try:
            template = env.get_template(template_name)
        except Exception:
            # Absolute fallback
            template = env.get_template("standard_report.html")

        # Get the professional company branding (logo, stamp, seal)
        comp_ctx = get_company_context()
        
        # Render the professional HTML
        html_content = template.render(
            company=comp_ctx,
            title=title,
            items=data.get("items", []),
            stats=data.get("stats", {}),
            format_currency=format_currency,
            generated_at=datetime.now().strftime("%d %b %Y %H:%M")
        )
        
        # Generate the PDF using the modern WeasyPrint engine
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        result = io.BytesIO(pdf_bytes)
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
