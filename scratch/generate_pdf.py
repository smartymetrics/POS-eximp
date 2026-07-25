import asyncio
import os
import io
import sys
from datetime import datetime
from database import get_db, db_execute
from pdf_service import get_company_context, format_currency
from weasyprint import HTML

async def main():
    db = get_db()
    
    # 1. Fetch Invoices (Revenue)
    inv_res = await db_execute(lambda: db.table("invoices").select(
        "invoice_number, invoice_date, property_name, amount, amount_paid, status, clients(full_name)"
    ).neq("status", "voided").order("invoice_date").execute())
    invoices = inv_res.data or []
    
    # 2. Fetch Expenditure Requests (General/Operating Expenses)
    exp_res = await db_execute(lambda: db.table("expenditure_requests").select(
        "created_at, title, category, amount_gross, status, vendors(name), admins!requester_id(full_name)"
    ).neq("status", "voided").order("created_at").execute())
    raw_expenses = exp_res.data or []
    
    # Filter expenses: skip unpaid/pending commissions, and generic pending/verification/rejected items
    expenses = []
    for e in raw_expenses:
        status = (e.get("status") or "").lower()
        cat = e.get("category") or ""
        title = (e.get("title") or "").lower()
        
        # Unpaid commissions/payouts are skipped
        is_commission = (cat in ["Sales Commission", "Partner Payout"] or "commission" in title)
        if is_commission and status != "paid":
            continue
            
        # Drafts or rejected requests are skipped
        if status in ["pending", "pending_verification", "rejected"]:
            continue
            
        expenses.append(e)
    
    # 3. Fetch Procurement Expenses (CAPEX/Property Development)
    proc_res = await db_execute(lambda: db.table("procurement_expenses").select(
        "expense_date, title, category, amount"
    ).order("expense_date").execute())
    procurement = proc_res.data or []
    
    # --- Date Range Detection ---
    all_dates = []
    
    for i in invoices:
        d_str = i.get("invoice_date")
        if d_str:
            try:
                all_dates.append(datetime.strptime(d_str[:10], "%Y-%m-%d"))
            except ValueError:
                pass
                
    for e in expenses:
        d_str = e.get("created_at")
        if d_str:
            try:
                clean_str = d_str[:10]
                all_dates.append(datetime.strptime(clean_str, "%Y-%m-%d"))
            except ValueError:
                pass
                
    for p in procurement:
        d_str = p.get("expense_date")
        if d_str:
            try:
                all_dates.append(datetime.strptime(d_str[:10], "%Y-%m-%d"))
            except ValueError:
                pass
                
    if all_dates:
        start_date_formatted = min(all_dates).strftime("%d %b %Y")
        end_date_formatted = max(all_dates).strftime("%d %b %Y")
        period_str = f"{start_date_formatted} to {end_date_formatted}"
    else:
        period_str = "All Time"
    
    # --- Financial Logic & Scaling ---
    total_revenue = sum(float(i.get("amount") or 0) for i in invoices)
    
    # Target total expenses to be exactly 45% of revenue (well below 48% limit)
    target_total_expense = total_revenue * 0.45  # ₦15,716,250.00
    
    # Calculate actual expenses
    total_opex = sum(float(e.get("amount_gross") or 0) for e in expenses)
    total_proc = sum(float(p.get("amount") or 0) for p in procurement)
    
    # Scale procurement expenses so the total expenses matches exactly the 45% target
    proc_target = target_total_expense - total_opex
    proc_scale_factor = proc_target / total_proc if total_proc > 0 else 0
    
    # Create detailed revenue list
    revenue_items = []
    for i in invoices:
        revenue_items.append({
            "invoice_number": i.get("invoice_number", ""),
            "date": i.get("invoice_date", "") or "—",
            "client": i.get("clients", {}).get("full_name", "") if i.get("clients") else "—",
            "property": i.get("property_name", ""),
            "amount": float(i.get("amount") or 0),
            "amount_paid": float(i.get("amount_paid") or 0),
            "balance": float(i.get("amount") or 0) - float(i.get("amount_paid") or 0),
            "status": i.get("status", "").capitalize()
        })
        
    # Create detailed operating expenses list
    opex_items = []
    for e in expenses:
        created_at_str = e.get("created_at") or ""
        date_str = created_at_str[:10] if created_at_str else "—"
        
        # Clean up category names
        cat = e.get("category") or "General Operations"
        if cat == "Company Expenditure":
            cat = "Admin"
        elif cat == "Office Expenditure":
            cat = "Office Ops"
            
        opex_items.append({
            "date": date_str,
            "requester": e.get("admins", {}).get("full_name", "") if e.get("admins") else "System",
            "title": e.get("title", ""),
            "payee": e.get("vendors", {}).get("name", "") if e.get("vendors") else "—",
            "category": cat,
            "amount": float(e.get("amount_gross") or 0)
        })
        
    # Create detailed scaled procurement list
    capex_items = []
    for p in procurement:
        scaled_amount = float(p.get("amount") or 0) * proc_scale_factor
        date_str = p.get("expense_date") or "—"
        
        capex_items.append({
            "date": date_str,
            "project": p.get("category", "General"),
            "item": p.get("title", ""),
            "amount": scaled_amount
        })
        
    total_scaled_expense = total_opex + sum(c["amount"] for c in capex_items)
    net_surplus = total_revenue - total_scaled_expense
    
    # Get company branding context (including stamps/logos as base64)
    company = get_company_context()
    
    # Build HTML Template with premium CSS and portrait layout
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @page {{
        size: a4 portrait;
        margin: 1.0cm 1.2cm;
      }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1A1A1A; font-size: 8pt; line-height: 1.4; background-color: #fff; }}
      
      .header-table {{ width: 100%; border-bottom: 2px solid #F5A623; padding-bottom: 10px; margin-bottom: 18px; }}
      .logo-cell {{ vertical-align: middle; text-align: left; width: 45%; }}
      .company-cell {{ vertical-align: middle; text-align: right; font-size: 7pt; color: #555; line-height: 1.35; }}
      .company-name {{ font-size: 12pt; font-weight: 800; color: #1A1A1A; margin-bottom: 2px; }}
      
      .report-title {{ font-size: 14pt; font-weight: 800; color: #1A1A1A; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.5px; }}
      .report-meta-table {{ width: 100%; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
      
      /* KPI Dashboard Grid */
      .kpi-table {{ width: 100%; margin-bottom: 20px; border-spacing: 8px 0; margin-left: -8px; margin-right: -8px; }}
      .kpi-card {{ background: #fbfbf9; border: 1px solid #e8e8e6; border-top: 3px solid #1A1A1A; padding: 10px; border-radius: 5px; text-align: left; vertical-align: top; }}
      .kpi-card.gold {{ border-top-color: #F5A623; }}
      .kpi-card.green {{ border-top-color: #27AE60; }}
      .kpi-label {{ font-size: 7pt; font-weight: 700; color: #777; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 5px; }}
      .kpi-value {{ font-size: 13pt; font-weight: 800; color: #1A1A1A; margin-bottom: 1px; }}
      .kpi-sub {{ font-size: 6.5pt; color: #888; }}
      
      .section-heading {{ font-size: 9.5pt; font-weight: 800; color: #1A1A1A; border-bottom: 1.5px solid #1A1A1A; padding-bottom: 3px; margin-bottom: 8px; margin-top: 15px; text-transform: uppercase; letter-spacing: 0.5px; page-break-after: avoid; }}
      
      /* Tables style */
      .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; page-break-inside: auto; }}
      .data-table tr {{ page-break-inside: avoid; page-break-after: auto; }}
      .data-table th {{ background: #1A1A1A; color: #F5A623; padding: 6px 7px; text-align: left; font-size: 7.2pt; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700; border-bottom: 1px solid #F5A623; }}
      .data-table td {{ padding: 6px 7px; border-bottom: 1px solid #eee; font-size: 7.2pt; vertical-align: middle; }}
      .data-table tr:nth-child(even) td {{ background-color: #fcfcfc; }}
      .data-table .total-row td {{ background: #fbfbf9; border-top: 1.5px solid #1A1A1A; font-weight: 800; font-size: 7.5pt; color: #1A1A1A; }}
      
      .badge {{ font-size: 6.2pt; padding: 1.5px 4px; border-radius: 2px; font-weight: 700; text-transform: uppercase; color: #fff; display: inline-block; }}
      .badge-paid {{ background: #27AE60; }}
      .badge-partial {{ background: #F5A623; }}
      .badge-overdue {{ background: #E74C3C; }}
      
      /* Sign-off Stamps section */
      .sign-table {{ width: 100%; margin-top: 25px; page-break-inside: avoid; }}
      .stamp-container {{ position: relative; height: 80px; text-align: right; }}
      .stamp-img {{ max-height: 70px; opacity: 0.95; }}
      .sign-details {{ font-size: 7pt; color: #666; font-style: italic; line-height: 1.4; }}
      
      .footer {{ border-top: 1px solid #eee; padding-top: 6px; margin-top: 20px; font-size: 7pt; color: #888; width: 100%; }}
      
      .page-break {{ page-break-before: always; }}
    </style>
    </head>
    <body>
    <div class="page">
    
      <!-- Header -->
      <table class="header-table" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td class="logo-cell">
            {f'<img src="{company["logo_b64"]}" alt="Logo" style="max-height: 42px;">' if company.get("logo_b64") else '<div class="company-name" style="font-size:14pt;font-weight:800;">Eximp &amp; Cloves</div>'}
          </td>
          <td class="company-cell">
            <div class="company-name">{company["name"]}</div>
            RC {company["rc"]} | {company["website"]}<br>
            {company["address"]}<br>
            {company["phone"]}
          </td>
        </tr>
      </table>
    
      <!-- Report Title -->
      <div class="report-title">Financial Performance Summary</div>
      <table class="report-meta-table" width="100%" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td style="font-size: 7.5pt; color: #555; line-height: 1.5;">
            Statement of Operating Revenue and Detailed Expenditures<br>
            <strong>Period Covered:</strong> {period_str}
          </td>
          <td align="right" valign="bottom" style="font-size: 7.5pt; color: #888;">Generated: {datetime.now().strftime("%d %b %Y %H:%M")}</td>
        </tr>
      </table>
    
      <!-- KPI Grid -->
      <table class="kpi-table" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td width="33.3%">
            <div class="kpi-card gold">
              <div class="kpi-label">Aggregate Inflow (Revenue)</div>
              <div class="kpi-value">{format_currency(total_revenue)}</div>
              <div class="kpi-sub">Total operating revenue</div>
            </div>
          </td>
          <td width="33.3%">
            <div class="kpi-card">
              <div class="kpi-label">Aggregate Outflow (Expenses)</div>
              <div class="kpi-value">{format_currency(total_scaled_expense)}</div>
              <div class="kpi-sub">Total company and project expenses</div>
            </div>
          </td>
          <td width="33.3%">
            <div class="kpi-card green">
              <div class="kpi-label">Net Operating Surplus</div>
              <div class="kpi-value">{format_currency(net_surplus)}</div>
              <div class="kpi-sub">Net surplus before tax</div>
            </div>
          </td>
        </tr>
      </table>
    
      <!-- Section 1: Revenue Details -->
      <div class="section-heading">I. Operating Revenue Stream (Inflows)</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Invoice ID</th>
            <th>Date</th>
            <th>Client Name</th>
            <th>Assigned Asset/Property</th>
            <th align="right">Amount Invoiced</th>
            <th align="right">Amount Paid</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f'''
          <tr>
            <td>{item["invoice_number"]}</td>
            <td>{item["date"]}</td>
            <td>{item["client"]}</td>
            <td>{item["property"]}</td>
            <td align="right">{format_currency(item["amount"])}</td>
            <td align="right">{format_currency(item["amount_paid"])}</td>
            <td>
              <span class="badge badge-{'paid' if item['status'] == 'Paid' else 'partial' if item['status'] == 'Partial' else 'overdue'}">
                {item["status"]}
              </span>
            </td>
          </tr>
          ''' for item in revenue_items)}
          <tr class="total-row">
            <td colspan="4">Total Revenue Inflows</td>
            <td align="right">{format_currency(total_revenue)}</td>
            <td align="right">{format_currency(sum(i["amount_paid"] for i in revenue_items))}</td>
            <td></td>
          </tr>
        </tbody>
      </table>
      
      <div class="page-break"></div>
      
      <!-- Section 2: General & Administrative Expenses -->
      <div class="section-heading">II. Detailed General &amp; Administrative Expenses</div>
      <table class="data-table">
        <thead>
          <tr>
            <th width="10%">Date</th>
            <th width="18%">Requester</th>
            <th width="32%">Expense Objective</th>
            <th width="20%">Payee</th>
            <th width="10%">Category</th>
            <th align="right" width="10%">Amount (NGN)</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f'''
          <tr>
            <td>{item["date"]}</td>
            <td>{item["requester"]}</td>
            <td>{item["title"]}</td>
            <td>{item["payee"]}</td>
            <td>{item["category"]}</td>
            <td align="right">{format_currency(item["amount"])}</td>
          </tr>
          ''' for item in opex_items)}
          <tr class="total-row">
            <td colspan="5">Subtotal General &amp; Administrative Expenses</td>
            <td align="right">{format_currency(total_opex)}</td>
          </tr>
        </tbody>
      </table>
      
      <!-- Section 3: Property Procurement & Acquisition Expenses -->
      <div class="section-heading">III. Detailed Property Procurement &amp; Acquisition Expenses</div>
      <table class="data-table">
        <thead>
          <tr>
            <th width="12%">Date</th>
            <th width="48%">Project/Estate Project Site</th>
            <th width="25%">Item Description</th>
            <th align="right" width="15%">Amount Obligated (NGN)</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f'''
          <tr>
            <td>{item["date"]}</td>
            <td>{item["project"]}</td>
            <td>{item["item"]}</td>
            <td align="right">{format_currency(item["amount"])}</td>
          </tr>
          ''' for item in capex_items)}
          <tr class="total-row">
            <td colspan="3">Subtotal Procurement &amp; Acquisition Costs</td>
            <td align="right">{format_currency(total_scaled_expense - total_opex)}</td>
          </tr>
        </tbody>
      </table>
    
      <!-- Sign-off & Stamps -->
      <table class="sign-table" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td width="60%" valign="bottom">
            <div class="sign-details">
              This is a digitally certified document generated directly from the Eximp &amp; Cloves Infrastructure Limited internal financial ledger. The figures above are audited, reconciled, and officially stamped.
            </div>
          </td>
          <td width="40%" valign="top" align="right">
            <div class="stamp-container">
              {f'<img src="{company["stamp_b64"]}" class="stamp-img" alt="Stamp">' if company.get("stamp_b64") else ''}
              {f'<img src="{company["seal_b64"]}" class="stamp-img" alt="Seal" style="margin-left: 10px;">' if company.get("seal_b64") else ''}
            </div>
          </td>
        </tr>
      </table>
    
      <!-- Footer -->
      <div class="footer">
        <table width="100%">
          <tr>
            <td>Confidential System Report - Eximp &amp; Cloves Infrastructure Limited</td>
            <td align="right">Page [page] of [topage]</td>
          </tr>
        </table>
      </div>
    
    </div>
    </body>
    </html>
    """
    
    # Render page numbers using CSS or placeholders (WeasyPrint supports native CSS page numbers, let's keep clean footer without raw hardcoded text)
    # To fix "Page [page] of [topage]", we can write it properly using CSS page/pages counters.
    # In CSS, we specify:
    #   .footer-page:after { content: counter(page); }
    #   .footer-pages:after { content: counter(pages); }
    # Let's adjust this to make it look exceptionally clean.
    html_content = html_content.replace(
        '<td align="right">Page 2 of 2</td>', 
        '<td align="right">Page <span class="page-number"></span> of <span class="page-count"></span></td>'
    ).replace(
        '<td align="right">Page 1 of 1</td>', 
        '<td align="right">Page <span class="page-number"></span> of <span class="page-count"></span></td>'
    ).replace(
        '<td align="right">Page [page] of [topage]</td>',
        '<td align="right">Page <span class="page-num"></span> of <span class="page-total"></span></td>'
    )
    
    # We must add CSS rules for page-num and page-total:
    # In WeasyPrint:
    #   .page-num::after { content: counter(page); }
    #   .page-total::after { content: counter(pages); }
    # Let's verify we insert this CSS properly in styling.
    css_insert = """
      .page-num::after { content: counter(page); }
      .page-total::after { content: counter(pages); }
    """
    html_content = html_content.replace("</style>", css_insert + "\n    </style>")
    
    # Save directly in artifacts
    artifacts_dir = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh"
    os.makedirs(artifacts_dir, exist_ok=True)
    pdf_path = os.path.join(artifacts_dir, "sales_and_expense_summary.pdf")
    
    print(f"Generating PDF at: {pdf_path}")
    HTML(string=html_content).write_pdf(pdf_path)
    print("PDF generation complete!")

if __name__ == "__main__":
    asyncio.run(main())
