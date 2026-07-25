import asyncio
import os
import sys
from datetime import datetime

# Add the workspace root to sys.path so we can import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, db_execute
from pdf_service import get_company_context, format_currency
from weasyprint import HTML

async def main():
    # 1. Fetch Company Context (for logo, stamp, seal, addresses)
    company = get_company_context()
    
    # 2. Set up Forecast Parameters
    # Monthly salary constraint: ₦1.2 Million
    salary_monthly = 1200000.0
    
    # Baseline discretionary office operations: ₦300,000
    baseline_office_ops = 300000.0
    
    # Average monthly unit sold: 3.5 plots (based on 3-4 plots/month)
    avg_plots_sold_monthly = 3.5
    
    # Product catalog
    products = [
        {
            "name": "Baclay Estate",
            "size": "500 SQM",
            "price": 3500000.0,
            "doc_fee": 750000.0,
            "monthly_units": 1.5  # Assumed mix for forecast
        },
        {
            "name": "Northway (Mokoloki Ofada)",
            "size": "300 SQM",
            "price": 4000000.0,
            "doc_fee": 750000.0,
            "monthly_units": 1.0
        },
        {
            "name": "Northway (Mokoloki Ofada)",
            "size": "500 SQM",
            "price": 7000000.0,
            "doc_fee": 750000.0,  # ₦750,000
            "monthly_units": 1.0
        }
    ]
    
    # 3. Calculate Projected Monthly Revenue
    monthly_land_revenue = sum(p["price"] * p["monthly_units"] for p in products)
    monthly_doc_revenue = sum(p["doc_fee"] * p["monthly_units"] for p in products)
    total_projected_revenue = monthly_land_revenue + monthly_doc_revenue
    
    # 4. Calculate Projected Expenses
    # Total monthly operational expenses are fixed: Salary + Baseline Office Ops
    total_projected_expense = salary_monthly + baseline_office_ops
    expense_ratio = (total_projected_expense / total_projected_revenue) * 100
    
    # Low scenario: 1 plot of Baclay Estate
    low_revenue = 3500000.0 + 750000.0
    low_expense = total_projected_expense
    low_expense_ratio = (low_expense / low_revenue) * 100
    
    # High scenario (6 plots)
    high_units_factor = 6.0 / 3.5
    high_revenue = total_projected_revenue * high_units_factor
    high_expense = total_projected_expense
    high_expense_ratio = (high_expense / high_revenue) * 100
    
    # Legal documents list
    legal_docs = [
        "Deed of Assignment",
        "Contract of Sales",
        "Provisional Survey",
        "Payment Receipt",
        "Acknowledgement Certificate",
        "Allocation Letter"
    ]
    
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
      body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1A1A1A; font-size: 8pt; line-height: 1.45; background-color: #fff; }}
      
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
      .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; page-break-inside: avoid; }}
      .data-table tr {{ page-break-inside: avoid; page-break-after: auto; }}
      .data-table th {{ background: #1A1A1A; color: #F5A623; padding: 6px 7px; text-align: left; font-size: 7.2pt; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700; border-bottom: 1px solid #F5A623; }}
      .data-table td {{ padding: 6px 7px; border-bottom: 1px solid #eee; font-size: 7.2pt; vertical-align: middle; }}
      .data-table tr:nth-child(even) td {{ background-color: #fcfcfc; }}
      .data-table .total-row td {{ background: #fbfbf9; border-top: 1.5px solid #1A1A1A; font-weight: 800; font-size: 7.5pt; color: #1A1A1A; }}
      
      /* Checkbox/Deliverables style */
      .doc-grid {{ width: 100%; margin-bottom: 15px; border-spacing: 10px; margin-left: -10px; margin-right: -10px; }}
      .doc-item {{ background: #fbfbf9; border: 1px solid #e8e8e6; border-left: 3.5px solid #F5A623; padding: 7px 10px; font-size: 7.5pt; font-weight: 700; border-radius: 3px; }}
      .doc-icon {{ display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: middle; color: #F5A623; font-weight: 900; }}
      
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
    
      <!-- Header / Letterhead -->
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
      <div class="report-title">Product and operation forecast</div>
      <table class="report-meta-table" width="100%" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td style="font-size: 7.5pt; color: #555; line-height: 1.5;">
            Operational Run-Rate &amp; Product Sales Projections<br>
            <strong>Document Class:</strong> Strategic Management Forecast
          </td>
          <td align="right" valign="bottom" style="font-size: 7.5pt; color: #888;">Generated: {datetime.now().strftime("%d %b %Y %H:%M")}</td>
        </tr>
      </table>
    
      <!-- KPI Grid -->
      <table class="kpi-table" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td width="33.3%">
            <div class="kpi-card gold">
              <div class="kpi-label">Projected Monthly Revenue</div>
              <div class="kpi-value">{format_currency(total_projected_revenue)}</div>
              <div class="kpi-sub">Assuming 3.5 plots/month mix</div>
            </div>
          </td>
          <td width="33.3%">
            <div class="kpi-card">
              <div class="kpi-label">Projected Monthly Expenses</div>
              <div class="kpi-value">{format_currency(total_projected_expense)}</div>
              <div class="kpi-sub">Salaries &amp; Office overhead</div>
            </div>
          </td>
          <td width="33.3%">
            <div class="kpi-card green">
              <div class="kpi-label">Operating Profit Margin</div>
              <div class="kpi-value">{100.0 - expense_ratio:.1f}%</div>
              <div class="kpi-sub">Net surplus margin</div>
            </div>
          </td>
        </tr>
      </table>
    
      <!-- Section 1: Product Catalog & Revenue Forecast -->
      <div class="section-heading">I. Product Catalog &amp; Revenue Projections</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Product Name</th>
            <th>Plot Size</th>
            <th align="right">Unit Land Price</th>
            <th align="right">Documentation Fee</th>
            <th align="right">Projected Monthly Volume</th>
            <th align="right">Projected Monthly Revenue</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f'''
          <tr>
            <td>{p["name"]}</td>
            <td>{p["size"]}</td>
            <td align="right">{format_currency(p["price"])}</td>
            <td align="right">{format_currency(p["doc_fee"])}</td>
            <td align="right">{p["monthly_units"]} plots</td>
            <td align="right">{format_currency((p["price"] + p["doc_fee"]) * p["monthly_units"])}</td>
          </tr>
          ''' for p in products)}
          <tr class="total-row">
            <td colspan="4">Total Monthly Projections (Expected Run-Rate)</td>
            <td align="right">{avg_plots_sold_monthly} plots</td>
            <td align="right">{format_currency(total_projected_revenue)}</td>
          </tr>
        </tbody>
      </table>
      
      <!-- Section 2: Legal Documentation Package -->
      <div class="section-heading">II. Client Legal Documentation Package</div>
      <p style="font-size: 7.2pt; color: #555; margin-bottom: 8px;">
        Every client purchase is secured with the following legally binding deliverables, included as part of the minimum ₦750,000 documentation fee:
      </p>
      
      <table class="doc-grid" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td width="50%"><div class="doc-item"><span class="doc-icon">&#10003;</span> Deed of Assignment</div></td>
          <td width="50%"><div class="doc-item"><span class="doc-icon">&#10003;</span> Contract of Sales</div></td>
        </tr>
        <tr>
          <td><div class="doc-item"><span class="doc-icon">&#10003;</span> Provisional Survey</div></td>
          <td><div class="doc-item"><span class="doc-icon">&#10003;</span> Payment Receipt</div></td>
        </tr>
        <tr>
          <td><div class="doc-item"><span class="doc-icon">&#10003;</span> Acknowledgement Certificate</div></td>
          <td><div class="doc-item"><span class="doc-icon">&#10003;</span> Allocation Letter</div></td>
        </tr>
      </table>
      
      <!-- Section 3: Monthly Operational Expenses (Outflows) -->
      <div class="section-heading">III. Monthly Operational Expenses Breakdown</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Expense Category</th>
            <th>Description / Resource Allocation</th>
            <th align="right">Monthly Amount (NGN)</th>
            <th>% of Projected Revenue</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Staff Salaries</strong></td>
            <td>Monthly personnel and payroll costs</td>
            <td align="right">{format_currency(salary_monthly)}</td>
            <td>{(salary_monthly / total_projected_revenue) * 100:.2f}%</td>
          </tr>
          <tr>
            <td><strong>Office Operations</strong></td>
            <td>Office administrative, internet, utilities, and general overhead</td>
            <td align="right">{format_currency(baseline_office_ops)}</td>
            <td>{(baseline_office_ops / total_projected_revenue) * 100:.2f}%</td>
          </tr>
          <tr class="total-row">
            <td>Total Monthly Expenses</td>
            <td>Total projected operational overhead</td>
            <td align="right">{format_currency(total_projected_expense)}</td>
            <td>{expense_ratio:.2f}%</td>
          </tr>
        </tbody>
      </table>
      
      <!-- Section 4: Projections & Scenario Sensitivity Analysis -->
      <div class="section-heading">IV. Sales Scenario Sensitivity Analysis</div>
      <p style="font-size: 7.2pt; color: #555; margin-bottom: 8px;">
        Analysis of projected expenses and operating margins across different monthly sales volumes (Low, Expected, and High run-rates):
      </p>
      <table class="data-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Monthly Volume</th>
            <th align="right">Projected Revenue</th>
            <th align="right">Salaries (Fixed)</th>
            <th align="right">Office Ops (Discretionary)</th>
            <th align="right">Total Expense</th>
            <th>Operating Profit Margin</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Low Sales</strong></td>
            <td>1.0 plot/month (Baclay)</td>
            <td align="right">{format_currency(low_revenue)}</td>
            <td align="right">{format_currency(salary_monthly)}</td>
            <td align="right">{format_currency(baseline_office_ops)}</td>
            <td align="right">{format_currency(low_expense)}</td>
            <td style="color:#27AE60; font-weight:800;">{100.0 - low_expense_ratio:.1f}%</td>
          </tr>
          <tr>
            <td><strong>Expected Sales</strong></td>
            <td>3.5 plots/month</td>
            <td align="right">{format_currency(total_projected_revenue)}</td>
            <td align="right">{format_currency(salary_monthly)}</td>
            <td align="right">{format_currency(baseline_office_ops)}</td>
            <td align="right">{format_currency(total_projected_expense)}</td>
            <td style="color:#27AE60; font-weight:800;">{100.0 - expense_ratio:.1f}%</td>
          </tr>
          <tr>
            <td><strong>High Sales</strong></td>
            <td>6.0 plots/month</td>
            <td align="right">{format_currency(high_revenue)}</td>
            <td align="right">{format_currency(salary_monthly)}</td>
            <td align="right">{format_currency(baseline_office_ops)}</td>
            <td align="right">{format_currency(high_expense)}</td>
            <td style="color:#27AE60; font-weight:800;">{100.0 - high_expense_ratio:.1f}%</td>
          </tr>
        </tbody>
      </table>
    
      <!-- Sign-off & Stamps -->
      <table class="sign-table" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td width="60%" valign="bottom">
            <div class="sign-details">
              This document outlines the strategic operational and sales projections for Eximp &amp; Cloves Infrastructure Limited. Figures are based on current project listings and estimated monthly sales velocity.
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
            <td>Confidential Management Report - Eximp &amp; Cloves Infrastructure Limited</td>
            <td align="right">Page <span class="page-num"></span> of <span class="page-total"></span></td>
          </tr>
        </table>
      </div>
    
    </div>
    </body>
    </html>
    """
    
    # We must add CSS rules for page-num and page-total:
    css_insert = """
      .page-num::after { content: counter(page); }
      .page-total::after { content: counter(pages); }
    """
    html_content = html_content.replace("</style>", css_insert + "\n    </style>")
    
    # Save PDF directly to workspace root
    artifacts_dir = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh"
    pdf_path = os.path.join(artifacts_dir, "product_and_operation_forecast.pdf")
    
    print(f"Generating PDF at: {pdf_path}")
    HTML(string=html_content).write_pdf(pdf_path)
    print("PDF generation complete successfully!")

if __name__ == "__main__":
    asyncio.run(main())
