from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date, timedelta
from database import get_db, db_execute
from routers.auth import verify_token
from models import (
    KPISummary, KPIDelta, RevenueTrend, EstateStat, 
    PaymentStatusStats, ReferralSourceStat, RepLeaderboardEntry, ActivityLogEntry
)
from utils import resolve_invoice_status

from routers.auth import verify_token, require_roles, has_any_role
from report_service import ReportService

router = APIRouter()

@router.get("/procurement")
async def get_procurement_analytics_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(require_roles(["super_admin"]))
):
    """JSON API for Procurement Analytics."""
    return await ReportService.get_procurement_analytics(start_date, end_date)

def get_previous_period(start: date, end: date):
    delta = end - start
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - delta
    return prev_start, prev_end

@router.get("/kpis", response_model=KPISummary)
async def get_kpis(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    db = get_db()
    is_admin = has_any_role(admin, "admin", "operations")
    
    # 1. Total Invoiced (Gross)
    invoiced_query = db.table("invoices").select("amount").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).neq("status", "voided")
    invoiced_data = (await db_execute(lambda: invoiced_query.execute())).data
    gross_revenue = sum(float(i["amount"]) for i in invoiced_data) if is_admin else 0
    plots_sold = len(invoiced_data)
    
    # 2. Amount Collected & Refunds
    collected_query = db.table("payments").select("amount, payment_type").filter("payment_date", "gte", start.isoformat()).filter("payment_date", "lte", end.isoformat()).eq("is_voided", False)
    collected_data = (await db_execute(lambda: collected_query.execute())).data
    
    total_refunds = sum(float(p["amount"]) for p in collected_data if p.get("payment_type") == "refund")
    amount_collected = sum(float(p["amount"]) for p in collected_data if p.get("payment_type") != "refund") - total_refunds
    
    # Net Revenue = Gross Invoiced - Total Refunded
    total_revenue = (gross_revenue - total_refunds) if is_admin else None
    
    # 3. New Clients (Paying customers only)
    clients_query = db.table("clients").select("id", count="exact")\
        .filter("created_at", "gte", start.isoformat())\
        .filter("created_at", "lte", end.isoformat() + "T23:59:59")\
        .eq("client_type", "client")
    new_clients = (await db_execute(lambda: clients_query.execute())).count
    
    # 4. Pending Verifications (Always live)
    pending_count = (await db_execute(lambda: db.table("pending_verifications").select("id", count="exact").eq("status", "pending").execute())).count
    
    # 5. Dynamic Status Counts (Overdue / Partial)
    # Fetch all relevant invoices to resolve status dynamically
    all_inv_query = db.table("invoices").select("amount, amount_paid, due_date, status").neq("status", "voided")
    if not is_admin:
         # Staff might only see limited data? PRD doesn't specify filter for staff here, 
         # but usually KPIs are restricted. Line 31 already handles is_admin for totals.
         pass
    
    all_inv_data = (await db_execute(lambda: all_inv_query.execute())).data
    overdue_count = 0
    partial_count = 0
    
    for inv in all_inv_data:
        status = resolve_invoice_status(inv)
        if status == "overdue":
            overdue_count += 1
        elif status == "partial":
            partial_count += 1

    # Outstanding & Rate
    outstanding = (total_revenue - amount_collected) if is_admin and total_revenue is not None else None
    collection_rate = (amount_collected / total_revenue * 100) if is_admin and total_revenue and total_revenue > 0 else 0
    avg_deal = (total_revenue / plots_sold) if is_admin and plots_sold > 0 else 0
    
    # Delta Logic (Simplified)
    delta = None
    if is_admin:
        prev_start, prev_end = get_previous_period(start, end)
        # Prev Revenue (Net)
        prev_rev_data = (await db_execute(lambda: db.table("invoices").select("amount").filter("invoice_date", "gte", prev_start.isoformat()).filter("invoice_date", "lte", prev_end.isoformat()).neq("status", "voided").execute())).data
        prev_refund_data = (await db_execute(lambda: db.table("payments").select("amount").filter("payment_date", "gte", prev_start.isoformat()).filter("payment_date", "lte", prev_end.isoformat()).eq("payment_type", "refund").eq("is_voided", False).execute())).data
        prev_revenue = sum(float(i["amount"]) for i in prev_rev_data) - sum(float(r["amount"]) for r in prev_refund_data)
        
        # Prev Collected
        prev_col_data = (await db_execute(lambda: db.table("payments").select("amount, payment_type").filter("payment_date", "gte", prev_start.isoformat()).filter("payment_date", "lte", prev_end.isoformat()).eq("is_voided", False).execute())).data
        prev_collected = sum(
            float(p["amount"]) if p.get("payment_type") != "refund" else -float(p["amount"])
            for p in prev_col_data
        )
        
        # Prev Clients
        prev_clients = (await db_execute(lambda: db.table("clients")\
            .select("id", count="exact")\
            .filter("created_at", "gte", prev_start.isoformat())\
            .filter("created_at", "lte", prev_end.isoformat() + "T23:59:59")\
            .eq("client_type", "client")\
            .execute())).count
        
        # Prev Refunds
        prev_refunds = sum(float(r["amount"]) for r in prev_refund_data)
        
        delta = KPIDelta(
            total_revenue=((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else None,
            amount_collected=((amount_collected - prev_collected) / prev_collected * 100) if prev_collected > 0 else None,
            new_clients=((new_clients - prev_clients) / prev_clients * 100) if prev_clients > 0 else None,
            total_refunds=((total_refunds - prev_refunds) / prev_refunds * 100) if prev_refunds > 0 else None
        )

    return KPISummary(
        total_revenue=total_revenue,
        amount_collected=amount_collected,
        total_refunds=total_refunds,
        outstanding_balance=outstanding,
        new_clients=new_clients,
        plots_sold=plots_sold,
        avg_deal_size=avg_deal,
        collection_rate=collection_rate,
        pending_verifications=pending_count,
        overdue_count=overdue_count,
        partial_count=partial_count,
        delta=delta
    )

@router.get("/revenue-trend", response_model=RevenueTrend)
async def get_revenue_trend(
    start: date = Query(...),
    end: date = Query(...),
    granularity: str = "daily",
    admin: dict = Depends(verify_token)
):
    if not has_any_role(admin, "admin", "operations"):
        raise HTTPException(status_code=403, detail="Financial data restricted to authorized roles")
        
    db = get_db()
    # Fetch all invoices and payments in period
    invoices = (await db_execute(lambda: db.table("invoices").select("amount", "invoice_date").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).neq("status", "voided").execute())).data
    payments = (await db_execute(lambda: db.table("payments").select("amount", "payment_date", "payment_type").filter("payment_date", "gte", start.isoformat()).filter("payment_date", "lte", end.isoformat()).eq("is_voided", False).execute())).data
    
    # Aggregate by date
    labels = []
    invoiced_vals = []
    collected_vals = []
    refund_vals = []
    
    curr = start
    while curr <= end:
        date_str = curr.isoformat()
        labels.append(curr.strftime("%b %d"))
        
        inv_sum = sum(float(i["amount"]) for i in invoices if i["invoice_date"] == date_str)
        col_sum = sum(float(p["amount"]) for p in payments if p["payment_date"] == date_str and p.get("payment_type") != "refund")
        ref_sum = sum(float(p["amount"]) for p in payments if p["payment_date"] == date_str and p.get("payment_type") == "refund")
        
        invoiced_vals.append(inv_sum)
        collected_vals.append(col_sum)
        refund_vals.append(ref_sum)
        curr += timedelta(days=1)
        
    return RevenueTrend(labels=labels, invoiced=invoiced_vals, collected=collected_vals, refunds=refund_vals)

@router.get("/estates", response_model=List[EstateStat])
async def get_estates(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    if not has_any_role(admin, "admin", "operations"):
        raise HTTPException(status_code=403, detail="Restricted")
        
    db = get_db()
    data = (await db_execute(lambda: db.table("invoices").select("property_name", "amount").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).neq("status", "voided").execute())).data
    
    stats = {}
    for item in data:
        name = item["property_name"] or "Unknown"
        if name not in stats:
            stats[name] = {"revenue": 0, "deals": 0}
        stats[name]["revenue"] += float(item["amount"])
        stats[name]["deals"] += 1
        
    return [EstateStat(name=k, revenue=v["revenue"], deals=v["deals"]) for k, v in stats.items()]

@router.get("/payment-status", response_model=PaymentStatusStats)
async def get_payment_status(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    db = get_db()
    data = (await db_execute(lambda: db.table("invoices").select("amount, amount_paid, due_date, status").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).neq("status", "voided").execute())).data
    
    stats = {"paid": 0, "partial": 0, "unpaid": 0, "overdue": 0}
    for inv in data:
        status = resolve_invoice_status(inv)
        if status in stats:
            stats[status] += 1
            
    return PaymentStatusStats(**stats)

@router.get("/referral-sources", response_model=List[ReferralSourceStat])
async def get_referral_sources(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    db = get_db()
    data = (await db_execute(lambda: db.table("clients")\
        .select("referral_source")\
        .filter("created_at", "gte", start.isoformat())\
        .filter("created_at", "lte", end.isoformat() + "T23:59:59")\
        .eq("client_type", "client")\
        .execute())).data
    
    sources = {}
    for item in data:
        s = item["referral_source"] or "Other"
        sources[s] = sources.get(s, 0) + 1
        
    return [ReferralSourceStat(source=k, count=v) for k, v in sources.items()]

@router.get("/activity", response_model=List[ActivityLogEntry])
async def get_activity(
    limit: int = 20,
    offset: int = 0,
    admin: dict = Depends(verify_token)
):
    db = get_db()
    role = admin.get("role", "")
    admin_id = admin["sub"]
    
    # Check if user is restricted
    # Privileged roles: admin, super_admin, operations
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])
    
    query = db.table("activity_log").select("*, admins(full_name), clients(assigned_rep_id)")

    if not is_privileged:
        # Restricted users (Sales, Marketing, Staff) see:
        # 1. Activities they performed
        # 2. Activities related to clients assigned to them
        #
        # NOTE: PostgREST or_() cannot filter on embedded/related table columns
        # (e.g. clients.assigned_rep_id). Instead, we pre-fetch the IDs of clients
        # assigned to this rep and use client_id.in.(...) in the or_ expression.
        assigned_res = await db_execute(
            lambda: db.table("clients").select("id").eq("assigned_rep_id", admin_id).execute()
        )
        assigned_client_ids = [c["id"] for c in (assigned_res.data or [])]

        if assigned_client_ids:
            ids_csv = ",".join(assigned_client_ids)
            query = query.or_(f"performed_by.eq.{admin_id},client_id.in.({ids_csv})")
        else:
            # No assigned clients — only show own activity
            query = query.eq("performed_by", admin_id)

    data = (await db_execute(lambda: query\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute())).data
        
    activity = []
    for item in data:
        activity.append(ActivityLogEntry(
            id=str(item["id"]),
            event_type=item["event_type"],
            description=item["description"],
            client_id=str(item["client_id"]) if item["client_id"] else None,
            invoice_id=str(item["invoice_id"]) if item["invoice_id"] else None,
            performed_by_name=item["admins"].get("full_name") if item.get("admins") else "System",
            created_at=item["created_at"]
        ))
        
    return activity
@router.get("/rep-leaderboard", response_model=List[RepLeaderboardEntry])
async def get_rep_leaderboard(
    start: date = Query(...),
    end: date = Query(...),
    limit: int = 10,
    admin: dict = Depends(verify_token)
):
    if not has_any_role(admin, "admin", "operations"):
        raise HTTPException(status_code=403, detail="Restricted")
        
    db = get_db()
    data = (await db_execute(lambda: db.table("invoices")\
        .select("sales_rep_name, amount, property_name, payments(amount, is_voided, payment_type)")\
        .filter("invoice_date", "gte", start.isoformat())\
        .filter("invoice_date", "lte", end.isoformat())\
        .neq("status", "voided")\
        .execute())).data
        
    reps = {}
    for item in data:
        name = item["sales_rep_name"] or "Unknown"
        if name not in reps:
            reps[name] = {"deals": 0, "total_value": 0, "collected": 0, "estates": {}}
        
        reps[name]["deals"] += 1
        reps[name]["total_value"] += float(item["amount"])
        
        # Calculate collected from related payments (filtering out voided and refunds)
        p_list = item.get("payments") or []
        inv_collected = sum(
            float(p["amount"]) 
            for p in p_list 
            if not p.get("is_voided") and p.get("payment_type") != "refund"
        )
        reps[name]["collected"] += inv_collected
        
        estate = item["property_name"] or "N/A"
        reps[name]["estates"][estate] = reps[name]["estates"].get(estate, 0) + 1
        
    results = []
    for name, stats in reps.items():
        # Find top estate
        top_estate = max(stats["estates"].items(), key=lambda x: x[1])[0] if stats["estates"] else "N/A"
        
        results.append(RepLeaderboardEntry(
            rep_name=name,
            deals=stats["deals"],
            total_value=stats["total_value"],
            avg_deal_size=stats["total_value"] / stats["deals"],
            top_estate=top_estate,
            collected=stats["collected"],
            collection_rate=(stats["collected"] / stats["total_value"] * 100) if stats["total_value"] > 0 else 0
        ))
        
    # Sort by total value
    results.sort(key=lambda x: x.total_value, reverse=True)
    return results[:limit]

async def log_activity(
    event_type: str,
    description: str,
    performed_by: str,
    client_id: Optional[str] = None,
    invoice_id: Optional[str] = None,
    metadata: Optional[dict] = None
):
    try:
        db = get_db()
        insert_data = {
            "event_type": event_type,
            "description": description,
            "client_id": client_id,
            "invoice_id": invoice_id,
            "metadata": metadata
        }
        # Only include performed_by if it's a valid UUID (not 'system')
        if performed_by and performed_by != "system":
            insert_data["performed_by"] = performed_by
            
        await db_execute(lambda: db.table("activity_log").insert(insert_data).execute())
    except Exception as e:
        print(f"Error logging activity: {e}")


# ── Internal Payouts Dashboard Endpoints ──

from pydantic import BaseModel

class SendReportRequest(BaseModel):
    emails: List[str]
    message: Optional[str] = None
    format: str = "csv"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class GrantAccessRequest(BaseModel):
    admin_id: str

async def has_internal_payouts_permission(admin: dict, db) -> bool:
    role = (admin.get("role") or "").lower()
    roles = [r.strip() for r in role.split(",") if r.strip()]
    if "super_admin" in roles:
        return True
    admin_id = admin.get("sub")
    if not admin_id:
        return False
    res = await db_execute(lambda: db.table("internal_payouts_access").select("admin_id").eq("admin_id", admin_id).execute())
    return len(res.data) > 0

@router.get("/internal-payouts/check-access")
async def check_internal_payouts_access(admin: dict = Depends(verify_token)):
    db = get_db()
    has_access = await has_internal_payouts_permission(admin, db)
    return {"has_access": has_access}

@router.get("/internal-payouts")
async def get_internal_payouts_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(verify_token)
):
    db = get_db()
    if not await has_internal_payouts_permission(admin, db):
        raise HTTPException(status_code=403, detail="Access denied to Internal Payouts Ledger")
        
    query = db.table("invoices").select("id, invoice_number, amount, land_cost, allocation_fee, documentation_fee, vat_amount, property_name, invoice_date, clients(full_name, email)").neq("status", "voided")
    if start_date:
        query = query.filter("invoice_date", "gte", start_date)
    if end_date:
        query = query.filter("invoice_date", "lte", end_date)
        
    res = await db_execute(lambda: query.order("invoice_date", desc=True).execute())
    invoices = res.data or []
    
    total_invoiced = 0.0
    total_land_cost = 0.0
    total_allocation = 0.0
    total_documentation = 0.0
    total_vat = 0.0
    
    estates = {}
    client_invoices = []
    
    for inv in invoices:
        amt = float(inv.get("amount") or 0.0)
        lc = float(inv.get("land_cost") or 0.0) if inv.get("land_cost") is not None else 0.0
        af = float(inv.get("allocation_fee") or 0.0) if inv.get("allocation_fee") is not None else 0.0
        df = float(inv.get("documentation_fee") or 0.0) if inv.get("documentation_fee") is not None else 0.0
        vat = float(inv.get("vat_amount") or 0.0) if inv.get("vat_amount") is not None else 0.0
        
        total_invoiced += amt
        total_land_cost += lc
        total_allocation += af
        total_documentation += df
        total_vat += vat
        
        est_name = inv.get("property_name") or "Unknown Estate"
        if est_name not in estates:
            estates[est_name] = {
                "property_name": est_name,
                "total_amount": 0.0,
                "land_cost": 0.0,
                "allocation_fee": 0.0,
                "documentation_fee": 0.0,
                "vat_amount": 0.0,
                "payment_count": 0
            }
        estates[est_name]["total_amount"] += amt
        estates[est_name]["land_cost"] += lc
        estates[est_name]["allocation_fee"] += af
        estates[est_name]["documentation_fee"] += df
        estates[est_name]["vat_amount"] += vat
        estates[est_name]["payment_count"] += 1
        
        client_info = inv.get("clients") or {}
        client_invoices.append({
            "id": inv["id"],
            "invoice_number": inv["invoice_number"],
            "client_name": client_info.get("full_name") or "—",
            "client_email": client_info.get("email") or "—",
            "property_name": est_name,
            "invoice_date": inv["invoice_date"],
            "amount": amt,
            "land_cost": lc,
            "allocation_fee": af,
            "documentation_fee": df,
            "vat_amount": vat,
            "has_splits": inv.get("land_cost") is not None
        })
        
    return {
        "company_totals": {
            "total_invoiced": total_invoiced,
            "total_land_cost": total_land_cost,
            "total_allocation": total_allocation,
            "total_documentation": total_documentation,
            "total_vat": total_vat
        },
        "estate_breakdown": list(estates.values()),
        "client_invoices": client_invoices
    }

@router.get("/internal-payouts/export")
async def export_internal_payouts_report(
    format: str = "csv",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(verify_token)
):
    db = get_db()
    if not await has_internal_payouts_permission(admin, db):
        raise HTTPException(status_code=403, detail="Access denied")
        
    query = db.table("invoices").select("invoice_number, amount, land_cost, allocation_fee, documentation_fee, vat_amount, property_name, invoice_date, clients(full_name)").neq("status", "voided")
    if start_date:
        query = query.filter("invoice_date", "gte", start_date)
    if end_date:
        query = query.filter("invoice_date", "lte", end_date)
        
    res = await db_execute(lambda: query.order("invoice_date", desc=True).execute())
    invoices = res.data or []
    
    if format == "csv":
        import io
        import csv
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Invoice Number", "Client Name", "Property Name", "Invoice Date", "Total Paid (NGN)", "Land Cost (90%)", "Allocation Fee (2.5%)", "Documentation Fee (7.5%)", "VAT Portion"])
        
        for inv in invoices:
            client_info = inv.get("clients") or {}
            writer.writerow([
                inv["invoice_number"],
                client_info.get("full_name") or "—",
                inv.get("property_name") or "—",
                inv["invoice_date"],
                inv["amount"],
                inv.get("land_cost") if inv.get("land_cost") is not None else 0.0,
                inv.get("allocation_fee") if inv.get("allocation_fee") is not None else 0.0,
                inv.get("documentation_fee") if inv.get("documentation_fee") is not None else 0.0,
                inv.get("vat_amount") if inv.get("vat_amount") is not None else 0.0
            ])
            
        stream = io.BytesIO(output.getvalue().encode("utf-8"))
        return StreamingResponse(
            stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=Internal_Payouts_Report_{start_date or 'all'}_to_{end_date or 'all'}.csv"}
        )
    elif format == "pdf":
        from fastapi.responses import Response
        from pdf_service import generate_internal_payouts_pdf
        pdf_bytes = await db_execute(lambda: generate_internal_payouts_pdf(invoices, start_date, end_date, admin.get("name") or "Super Admin"))
        return Response(
            pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Internal_Payouts_Report_{start_date or 'all'}_to_{end_date or 'all'}.pdf"}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format")

@router.post("/internal-payouts/send-report")
async def send_internal_payouts_report(
    req: SendReportRequest,
    admin: dict = Depends(verify_token)
):
    db = get_db()
    if not await has_internal_payouts_permission(admin, db):
        raise HTTPException(status_code=403, detail="Access denied")
        
    query = db.table("invoices").select("invoice_number, amount, land_cost, allocation_fee, documentation_fee, vat_amount, property_name, invoice_date, clients(full_name)").neq("status", "voided")
    if req.start_date:
        query = query.filter("invoice_date", "gte", req.start_date)
    if req.end_date:
        query = query.filter("invoice_date", "lte", req.end_date)
        
    res = await db_execute(lambda: query.order("invoice_date", desc=True).execute())
    invoices = res.data or []
    
    if req.format == "csv":
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Invoice Number", "Client Name", "Property Name", "Invoice Date", "Total Paid (NGN)", "Land Cost (90%)", "Allocation Fee (2.5%)", "Documentation Fee (7.5%)", "VAT Portion"])
        for inv in invoices:
            client_info = inv.get("clients") or {}
            writer.writerow([
                inv["invoice_number"],
                client_info.get("full_name") or "—",
                inv.get("property_name") or "—",
                inv["invoice_date"],
                inv["amount"],
                inv.get("land_cost") if inv.get("land_cost") is not None else 0.0,
                inv.get("allocation_fee") if inv.get("allocation_fee") is not None else 0.0,
                inv.get("documentation_fee") if inv.get("documentation_fee") is not None else 0.0,
                inv.get("vat_amount") if inv.get("vat_amount") is not None else 0.0
            ])
        file_bytes = output.getvalue().encode("utf-8")
        filename = f"Internal_Payouts_Report_{req.start_date or 'all'}_to_{req.end_date or 'all'}.csv"
        mime_type = "text/csv"
    elif req.format == "pdf":
        from pdf_service import generate_internal_payouts_pdf
        file_bytes = await db_execute(lambda: generate_internal_payouts_pdf(invoices, req.start_date, req.end_date, admin.get("name") or "Super Admin"))
        filename = f"Internal_Payouts_Report_{req.start_date or 'all'}_to_{req.end_date or 'all'}.pdf"
        mime_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
        
    from email_service import send_internal_payouts_report_email
    await send_internal_payouts_report_email(
        file_content=file_bytes,
        filename=filename,
        mime_type=mime_type,
        emails=req.emails,
        message_text=req.message,
        current_admin_name=admin.get("name") or "Super Admin"
    )
    
    await log_activity(
        "report_shared",
        f"Internal Payouts report ({req.format}) emailed to: {', '.join(req.emails)}",
        admin["sub"]
    )
    return {"message": "Report sent successfully"}

@router.get("/internal-payouts/access")
async def list_internal_payouts_access(admin: dict = Depends(verify_token)):
    db = get_db()
    role = (admin.get("role") or "").lower()
    roles = [r.strip() for r in role.split(",") if r.strip()]
    if "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Super Admin role required to view access controls")
        
    all_admins_res = await db_execute(lambda: db.table("admins").select("id, full_name, email, role").execute())
    all_admins = all_admins_res.data or []
    
    access_res = await db_execute(lambda: db.table("internal_payouts_access").select("admin_id, granted_by, granted_at").execute())
    access_list = access_res.data or []
    access_map = {row["admin_id"]: row for row in access_list}
    
    results = []
    for u in all_admins:
        u_id = u["id"]
        u_role = (u.get("role") or "").lower()
        u_roles = [r.strip() for r in u_role.split(",") if r.strip()]
        
        is_super = "super_admin" in u_roles
        has_custom = u_id in access_map
        
        if is_super or has_custom:
            granted_by = "System"
            granted_at = None
            if has_custom:
                g_rec = access_map[u_id]
                g_by_id = g_rec.get("granted_by")
                g_by_name = next((adm["full_name"] for adm in all_admins if adm["id"] == g_by_id), None)
                granted_by = g_by_name or "System"
                granted_at = g_rec.get("granted_at")
                
            results.append({
                "admin_id": u_id,
                "full_name": u["full_name"],
                "email": u["email"],
                "role": u["role"],
                "access_type": "Role-based (Automatic)" if is_super else "Custom Granted",
                "granted_by": granted_by,
                "granted_at": granted_at,
                "can_revoke": not is_super
            })
            
    return results

@router.post("/internal-payouts/access")
async def grant_internal_payouts_access(req: GrantAccessRequest, admin: dict = Depends(verify_token)):
    db = get_db()
    role = (admin.get("role") or "").lower()
    roles = [r.strip() for r in role.split(",") if r.strip()]
    if "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Super Admin role required")
        
    payload = {
        "admin_id": req.admin_id,
        "granted_by": admin["sub"]
    }
    await db_execute(lambda: db.table("internal_payouts_access").upsert(payload).execute())
    
    await log_activity(
        "access_granted",
        f"Custom access to Internal Payouts granted to admin ID {req.admin_id}",
        admin["sub"]
    )
    return {"message": "Access granted successfully"}

@router.delete("/internal-payouts/access/{admin_id}")
async def revoke_internal_payouts_access(admin_id: str, admin: dict = Depends(verify_token)):
    db = get_db()
    role = (admin.get("role") or "").lower()
    roles = [r.strip() for r in role.split(",") if r.strip()]
    if "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Super Admin role required")
        
    await db_execute(lambda: db.table("internal_payouts_access").delete().eq("admin_id", admin_id).execute())
    
    await log_activity(
        "access_revoked",
        f"Custom access to Internal Payouts revoked for admin ID {admin_id}",
        admin["sub"]
    )
    return {"message": "Access revoked successfully"}