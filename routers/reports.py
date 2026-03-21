from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional
from routers.auth import get_current_admin
from report_service import ReportService
from datetime import datetime
from models import ReportScheduleCreate
from database import supabase
from starlette.concurrency import run_in_threadpool
import io
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reports"])

@router.get("/download")
async def download_report(
    report_type: str,
    start_date: str = "",
    end_date: str = "",
    format: str = "pdf",
    admin: dict = Depends(get_current_admin)
):
    try:
        # 1. Fetch data (async)
        data = await ReportService.get_report_data(report_type, start_date, end_date)
        
        # 2. Generate file in a separate thread (prevents event loop blocking)
        # This is critical for CPU-intensive tasks like PDF or large Excel generation
        if format == "excel":
            file_obj = await run_in_threadpool(ReportService.generate_excel, data, data["type"])
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{report_type}_{datetime.now().strftime('%Y%m%d%H%M')}.xlsx"
        else:
            file_obj = await run_in_threadpool(ReportService.generate_pdf, data, data["type"])
            media_type = "application/pdf"
            filename = f"{report_type}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"

        return Response(
            content=file_obj.getvalue(),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"DOWNLOAD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedules")
async def get_report_schedules(admin: dict = Depends(get_current_admin)):
    try:
        res = supabase.table("report_schedules").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedules")
async def create_schedule(schedule: ReportScheduleCreate, admin: dict = Depends(get_current_admin)):
    try:
        data = schedule.dict()
        data["created_by"] = admin["id"]
        res = supabase.table("report_schedules").insert(data).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, admin: dict = Depends(get_current_admin)):
    try:
        res = supabase.table("report_schedules").delete().eq("id", schedule_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
