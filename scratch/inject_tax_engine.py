
import os

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\routers\hr.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update ManualPayrollCreate
old_manual_payroll = """class ManualPayrollCreate(BaseModel):
    staff_id: str
    gross_pay: float
    tax: float
    net_pay: float
    notes: Optional[str] = None
    period_start: date"""

new_manual_payroll = """class ManualPayrollCreate(BaseModel):
    staff_id: str
    gross_pay: float
    tax: float
    pension: Optional[float] = 0.0
    net_pay: float
    notes: Optional[str] = None
    period_start: date"""

content = content.replace(old_manual_payroll, new_manual_payroll)

# 2. Update run_payroll calculation logic
old_calc = """        base = float(p.get("base_salary") or 0)
        
        # Calculate simple tax (e.g. 10%)
        tax = base * 0.1
        net = base - tax
        
        payroll_inserts.append({
            "staff_id": s["id"],
            "period_start": month_start,
            "period_end": month_end,
            "gross_pay": base,
            "tax": tax,
            "net_pay": net,
            "status": "pending",
            "processed_by": current_admin["sub"]
        })"""

new_calc = """        base = float(p.get("base_salary") or 0)
        
        # Nigerian Tax Engine (PAYE / Pension)
        monthly_tax = 0.0
        monthly_pension = 0.0
        monthly_cra = 0.0
        
        if base > 30000: # Minimum wage exemption
            annual_gross = base * 12
            annual_pension = annual_gross * 0.08
            annual_cra = max(200000.0, annual_gross * 0.01) + (0.2 * annual_gross)
            taxable_income = max(0.0, annual_gross - annual_pension - annual_cra)
            
            annual_tax = 0.0
            brackets = [
                (300000, 0.07),
                (300000, 0.11),
                (500000, 0.15),
                (500000, 0.19),
                (1600000, 0.21),
                (float('inf'), 0.24)
            ]
            
            rem_income = taxable_income
            for limit, rate in brackets:
                if rem_income <= 0:
                    break
                taxable_amount = min(rem_income, limit)
                annual_tax += taxable_amount * rate
                rem_income -= taxable_amount
                
            if annual_tax == 0 and taxable_income <= 0:
                 annual_tax = annual_gross * 0.01 # Minimum tax 1%
                 
            monthly_tax = round(annual_tax / 12, 2)
            monthly_pension = round(annual_pension / 12, 2)
            monthly_cra = round(annual_cra / 12, 2)
            
        net = round(base - monthly_tax - monthly_pension, 2)
        
        payroll_inserts.append({
            "staff_id": s["id"],
            "period_start": month_start,
            "period_end": month_end,
            "gross_pay": base,
            "tax": monthly_tax,
            "pension": monthly_pension,
            "cra": monthly_cra,
            "net_pay": net,
            "status": "pending",
            "processed_by": current_admin["sub"]
        })"""

content = content.replace(old_calc, new_calc)

# 3. Update manual payroll insert to include pension
old_manual_insert = """    res = await db_execute(lambda: db.table("payroll_records").insert({
        "staff_id": nf.staff_id,
        "period_start": nf.period_start.isoformat(),
        "period_end": nf.period_start.isoformat(), # Same day for manual entries
        "gross_pay": nf.gross_pay,
        "tax": nf.tax,
        "net_pay": nf.net_pay,
        "status": "paid", # Manual entries usually reflect paid amounts
        "processed_by": current_admin["sub"]
    }).execute())"""

new_manual_insert = """    res = await db_execute(lambda: db.table("payroll_records").insert({
        "staff_id": nf.staff_id,
        "period_start": nf.period_start.isoformat(),
        "period_end": nf.period_start.isoformat(), # Same day for manual entries
        "gross_pay": nf.gross_pay,
        "tax": nf.tax,
        "pension": nf.pension,
        "net_pay": nf.net_pay,
        "status": "paid", # Manual entries usually reflect paid amounts
        "processed_by": current_admin["sub"]
    }).execute())"""

content = content.replace(old_manual_insert, new_manual_insert)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected Nigerian Tax Engine logic")
