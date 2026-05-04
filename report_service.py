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
            res = supabase.table("clients").select("full_name, email, phone, address, title, middle_name, gender, dob, marital_status, occupation, nin, id_number, nationality, nok_name, nok_phone, nok_relationship, source_of_income, referral_source, created_at, invoices(invoice_number, property_name, purchase_purpose, purchase_for, status)").order("created_at", desc=True).execute()
            data = res.data or []
            rows = []
            for c in data:
                all_invoices = c.get("invoices") or []
                # Filter out voided invoices
                active_invoices = [inv for inv in all_invoices if inv.get("status") != "voided"]
                
                if not active_invoices: continue # Filter: Only include clients with at least one valid (non-voided) transaction
                
                # Create a list of "Invoice: Property Name (Purpose/Reason)" strings
                prop_list = []
                for i in active_invoices:
                    inv_no = i.get("invoice_number", "N/A")
                    p_name = i.get("property_name")
                    p_purpose = i.get("purchase_purpose")
                    p_for = i.get("purchase_for")
                    if p_name:
                        entry = f"{inv_no}: {p_name}"
                        details = []
                        if p_purpose: details.append(f"Purpose: {p_purpose}")
                        if p_for: details.append(f"Reason: {p_for}")
                        
                        if details:
                            entry += f" ({', '.join(details)})"
                        prop_list.append(entry)
                
                # Join with newlines for cleaner PDF display
                props_display = "\n".join(sorted(set(prop_list))) if prop_list else "None"
                
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
                
                sales_info = f"PROPERTIES: {props_display}\nREFERRAL: {c.get('referral_source', 'N/A')}\nINCOME: {c.get('source_of_income', 'N/A')}\nREG DATE: {c.get('created_at', '')[:10]}"

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
        
        elif report_type == "payout_audit":
            res = supabase.table("expenditure_requests").select("*, vendors(name, type), admins!requester_id(full_name)").gte("created_at", start_date).lte("created_at", end_date).neq("status", "voided").order("created_at", desc=True).execute()
            data = res.data or []
            rows = []
            for p in data:
                rows.append({
                    "Date": str(p.get("created_at"))[:10],
                    "Title": p.get("title", "—"),
                    "Requester": p.get("admins", {}).get("full_name", "—") if p.get("admins") else "—",
                    "Payee": p.get("vendors", {}).get("name", "—") if p.get("vendors") else "—",
                    "Category": p.get("vendors", {}).get("type", "—").capitalize() if p.get("vendors") else "—",
                    "Gross (NGN)": f"NGN {float(p.get('amount_gross', 0)):,.2f}",
                    "WHT (NGN)": f"NGN {float(p.get('wht_amount', 0)):,.2f}",
                    "Net Paid (NGN)": f"NGN {float(p.get('net_payout_amount', 0)):,.2f}",
                    "Status": p.get("status", "").capitalize()
                })
            stats = {
                "total_gross": sum(float(p.get("amount_gross") or 0) for p in data),
                "total_wht": sum(float(p.get("wht_amount") or 0) for p in data),
                "count": len(data)
            }
            return {"items": rows, "stats": stats, "type": "Expenditure & Payout Audit"}

        elif report_type == "tax_compliance":
            # Focused on FIRS / WHT obligations
            res = supabase.table("expenditure_requests").select("*, vendors(name, tin, type)").gte("created_at", start_date).lte("created_at", end_date).eq("status", "paid").execute()
            data = res.data or []
            rows = []
            for p in data:
                vendor = p.get("vendors") or {}
                rows.append({
                    "Vendor/Payee": vendor.get("name", "—"),
                    "TIN": vendor.get("tin", "NOT PROVIDED"),
                    "Category": vendor.get("type", "—").capitalize(),
                    "Transaction Date": str(p.get("created_at"))[:10],
                    "Gross Amount": f"NGN {float(p.get('amount_gross', 0)):,.2f}",
                    "WHT Rate": f"{float(p.get('wht_rate', 0)*100)}%",
                    "WHT Withheld": f"NGN {float(p.get('wht_amount', 0)):,.2f}",
                    "Payment Ref": p.get("payout_reference", "—")
                })
            stats = {
                "total_tax_liability": sum(float(p.get("wht_amount") or 0) for p in data),
                "count": len(data)
            }
            return {"items": rows, "stats": stats, "type": "Tax Compliance (WHT Duty) Report"}

        elif report_type == "accounts_payable":
            # Outstanding Liabilities (Owed but not Paid)
            res = supabase.table("expenditure_requests").select("*, vendors(*)").in_("status", ["approved", "partially_paid"]).execute()
            data = res.data or []
            rows = []
            for p in data:
                net = float(p.get("net_payout_amount", 0))
                paid = float(p.get("amount_paid", 0))
                balance = net - paid
                if balance <= 0: continue
                
                rows.append({
                    "Payee": p.get("vendors", {}).get("name", "—") if p.get("vendors") else "—",
                    "Description": p.get("title", "—"),
                    "Due Date": p.get("due_date", "NOT SET"),
                    "Total Approved": f"NGN {net:,.2f}",
                    "Paid to Date": f"NGN {paid:,.2f}",
                    "Balance Owed": f"NGN {balance:,.2f}",
                    "Status": p.get("status", "").replace("_", " ").capitalize()
                })
            stats = {
                "total_outstanding": sum(float(r["Balance Owed"].replace("NGN ", "").replace(",", "")) for r in rows),
                "creditor_count": len(rows)
            }
            return {"items": rows, "stats": stats, "type": "Accounts Payable Registry"}

        elif report_type == "asset_registry":
            res = supabase.table("company_assets").select("*, admins!assigned_to(full_name)").execute()
            data = res.data or []
            rows = []
            for a in data:
                rows.append({
                    "Asset ID": a.get("asset_id", "—"),
                    "Description": a.get("name", "—"),
                    "Category": a.get("category", "—"),
                    "Purchase Date": a.get("purchase_date", "—"),
                    "Cost": f"NGN {float(a.get('purchase_cost', 0)):,.2f}",
                    "Assigned To": a.get("admins", {}).get("full_name", "—") if a.get("admins") else "UNASSIGNED",
                    "Status": a.get("current_status", "").capitalize()
                })
            stats = {
                "inventory_count": len(data),
                "total_asset_value": sum(float(a.get("purchase_cost") or 0) for a in data)
            }
            return {"items": rows, "stats": stats, "type": "Company Asset Registry"}

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
            "Commission Earned Report": "standard_report.html",
            "Expenditure & Payout Audit": "standard_report.html",
            "Tax Compliance (WHT Duty) Report": "standard_report.html",
            "Company Asset Registry": "standard_report.html",
            "Accounts Payable Registry": "standard_report.html"
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

    @staticmethod
    @staticmethod
    async def get_procurement_analytics() -> List[Dict[str, Any]]:
        """
        Analyzes estate-level financial health: Acquisition + Development vs Revenue.
        Includes both live Properties and pre-launch Estate Drafts.
        """
        # 1. Fetch live properties
        prop_res = supabase.table("properties").select("*").eq("is_archived", False).execute()
        properties = prop_res.data or []
        
        # 2. Fetch estate drafts
        draft_res = supabase.table("estate_drafts").select("*").eq("is_public", False).execute()
        drafts = draft_res.data or []
        
        # 3. Fetch all procurement specific expenses
        exp_res = supabase.table("procurement_expenses").select("*").execute()
        expenditures = exp_res.data or []
        
        # 4. Fetch all revenue (invoices)
        inv_res = supabase.table("invoices").select("property_id, amount, amount_paid").neq("status", "voided").execute()
        invoices = inv_res.data or []
        
        estates_map = {}
        
        # Process Live Properties
        for p in properties:
            p_name = p["name"]
            p_desc = (p.get("description") or "").lower()
            
            # Use the dedicated estate_name column if available, otherwise fallback to name splitting
            estate_name = p.get("estate_name") or p_name.split(" - ")[0]
            
            # Extract base name and size (e.g. "Park View - 500SQM")
            # We strip common plan suffixes to get the unique variation name
            base_part = p_name
            for suffix in [" (Outright)", " (Installment)", " (Outright Payment)", " (Installment Payment)"]:
                if suffix in p_name:
                    base_part = p_name.split(suffix)[0]
                    break
            
            if estate_name not in estates_map:
                estates_map[estate_name] = {
                    "ids": [],
                    "location": p["location"],
                    "acquisition_cost": 0,
                    "total_plots": 0,
                    "variations": [],
                    "is_draft": False
                }
            
            # Add to IDs for expense matching
            estates_map[estate_name]["ids"].append(str(p["id"]))
            
            # Check if this size variation already exists in our map
            existing_var = next((v for v in estates_map[estate_name]["variations"] if v["base_name"] == base_part), None)
            
            if not existing_var:
                # Create new variation entry
                var_data = {
                    "base_name": base_part,
                    "size": float(p.get("plot_size_sqm") or 0),
                    "outright_id": None,
                    "installment_id": None,
                    "outright_price": 0,
                    "installment_price": 0,
                    "plots_total": int(p.get("total_plots") or 0),
                    "acquisition_cost": float(p.get("acquisition_cost") or 0)
                }
                estates_map[estate_name]["variations"].append(var_data)
                existing_var = var_data
                
                # Update estate totals once per variation
                estates_map[estate_name]["acquisition_cost"] += var_data["acquisition_cost"]
                estates_map[estate_name]["total_plots"] += var_data["plots_total"]

            # Map the specific plan to the variation
            # We check both the name suffix AND the description content
            is_installment = "(Installment)" in p_name or "installment" in p_desc
            
            if is_installment:
                existing_var["installment_id"] = str(p["id"])
                existing_var["installment_price"] = float(p.get("total_price") or 0)
            else:
                # Default to outright if not marked as installment
                existing_var["outright_id"] = str(p["id"])
                existing_var["outright_price"] = float(p.get("total_price") or 0)
                # Primary ID for internal mapping
                existing_var["id"] = str(p["id"]) 

        # Process Drafts
        for d in drafts:
            name = d["name"]
            if name not in estates_map:
                estates_map[name] = {
                    "ids": [],
                    "draft_id": str(d["id"]),
                    "location": d["location"],
                    "acquisition_cost": 0,
                    "total_plots": 0,
                    "variations": [],
                    "is_draft": True
                }
            
            vars_list = d.get("variations", [])
            for v in vars_list:
                acq = float(v.get('acquisition_cost') or 0)
                estates_map[name]["acquisition_cost"] += acq
                estates_map[name]["total_plots"] += int(v.get('total_plots') or 0)
                estates_map[name]["variations"].append({
                    "id": None,
                    "base_name": f"{name} - {v.get('size_sqm')}SQM",
                    "size": float(v.get('size_sqm') or 0),
                    "outright_price": float(v.get('outright_price') or 0),
                    "installment_price": float(v.get('installment_price') or 0),
                    "plots_total": int(v.get('total_plots') or 0),
                    "acquisition_cost": acq
                })

        analytics = []
        for name, data in estates_map.items():
            ids = data["ids"]
            draft_id = data.get("draft_id")
            
            # Costs
            acquisition = data["acquisition_cost"]
            p_exp = [e for e in expenditures if (str(e.get("property_id")) in ids) or (draft_id and str(e.get("estate_draft_id")) == draft_id)]
            
            clearing = sum(float(e["amount"]) for e in p_exp if e.get("category") == "Clearing")
            fencing = sum(float(e["amount"]) for e in p_exp if e.get("category") == "Fencing")
            other_dev = sum(float(e["amount"]) for e in p_exp if e.get("category") not in ["Clearing", "Fencing"])
            
            total_development = clearing + fencing + other_dev
            total_investment = acquisition + total_development
            
            # Revenue
            p_inv = [i for i in invoices if str(i.get("property_id")) in ids]
            revenue_invoiced = sum(float(i["amount"]) for i in p_inv)
            revenue_collected = sum(float(i["amount_paid"]) for i in p_inv)
            
            inventory_value = 0
            total_plots_sold = 0
            for v in data["variations"]:
                # Count sales for BOTH IDs in this variation
                relevant_ids = [v.get("outright_id"), v.get("installment_id")]
                sold_this_var = len([i for i in p_inv if str(i.get("property_id")) in relevant_ids and i.get("property_id")])
                total_plots_sold += sold_this_var
                
                avail_this_var = max(0, v["plots_total"] - sold_this_var)
                # Use Outright price for unsold inventory valuation (standard practice)
                inventory_value += (avail_this_var * (v.get("outright_price") or v.get("price") or 0))
            
            total_plots = data["total_plots"]
            plots_available = max(0, total_plots - total_plots_sold)
            
            projected_total_revenue = revenue_invoiced + inventory_value
            net_profit_actual = revenue_collected - total_investment
            net_profit_projected = projected_total_revenue - total_investment
            
            roi_actual = (net_profit_actual / total_investment * 100) if total_investment > 0 else 0
            roi_projected = (net_profit_projected / total_investment * 100) if total_investment > 0 else 0
            
            analytics.append({
                "name": name,
                "draft_id": draft_id,
                "location": data["location"],
                "total_plots": total_plots,
                "plots_sold": total_plots_sold,
                "plots_available": plots_available,
                "is_draft": data["is_draft"],
                "variations": data["variations"],
                "financials": {
                    "acquisition_cost": acquisition,
                    "clearing_cost": clearing,
                    "fencing_cost": fencing,
                    "other_development_cost": other_dev,
                    "total_development": total_development,
                    "total_investment": total_investment,
                    "revenue_invoiced": revenue_invoiced,
                    "revenue_collected": revenue_collected,
                    "inventory_value": inventory_value,
                    "projected_total_revenue": projected_total_revenue,
                    "net_profit_actual": net_profit_actual,
                    "net_profit_projected": net_profit_projected,
                    "roi_percent": round(roi_actual, 1),
                    "roi_projected": round(roi_projected, 1)
                }
            })
            
        return sorted(analytics, key=lambda x: x["is_draft"], reverse=True)
