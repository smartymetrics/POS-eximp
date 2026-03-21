from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional
from routers.auth import get_current_admin
from report_service import ReportService
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/download")
async def download_report(
    report_type: str,
    start_date: str,
    end_date: str,
    format: str = "pdf",
    admin: dict = Depends(get_current_admin)
):
    """Generate and return a report file (PDF or Excel)."""
    if admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can download reports")
        
    try:
        # 1. Fetch data
        data = await ReportService.get_report_data(report_type, start_date, end_date)
        
        # 2. Generate file
        title = f"{data['type']} ({start_date} to {end_date})"
        if format == "excel":
            file_obj = ReportService.generate_excel(data, title)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{report_type}_{start_date}.xlsx"
        else:
            file_obj = ReportService.generate_pdf(data, title)
            media_type = "application/pdf"
            filename = f"{report_type}_{start_date}.pdf"
            
        return Response(
            content=file_obj.getvalue(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedules")
async def get_report_schedules(admin: dict = Depends(get_current_admin)):
    """List all scheduled reports (To be implemented with db table in next phase)."""
    return []

@router.post("/schedules")
async def create_report_schedule(admin: dict = Depends(get_current_admin)):
    """Create a new report schedule."""
    if admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return {"message": "Schedule updated"}
