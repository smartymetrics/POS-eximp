import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import supabase
from report_service import ReportService
from datetime import datetime, timedelta
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def run_scheduled_report(schedule_id: str):
    """Generate and email a scheduled report."""
    try:
        # 1. Get schedule details
        res = supabase.table("report_schedules").select("*").eq("id", schedule_id).execute()
        if not res.data:
            return
        
        schedule = res.data[0]
        if not schedule["is_active"]:
            return
            
        report_type = schedule["report_type"]
        format = schedule["format"]
        recipients = schedule["recipients"]
        
        # 2. Determine date range (e.g. last 7 days for weekly)
        end_date = datetime.now().date()
        if schedule["frequency"] == "daily":
            start_date = end_date - timedelta(days=1)
        elif schedule["frequency"] == "weekly":
            start_date = end_date - timedelta(days=7)
        else: # monthly
            start_date = end_date - timedelta(days=30)
            
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # 3. Generate report
        report_data = await ReportService.get_report_data(report_type, start_str, end_str)
        title = f"Scheduled {report_data['type']} ({start_str} to {end_str})"
        
        if format == "excel":
            file_obj = ReportService.generate_excel(report_data, title)
            attachment_name = f"{report_type}_{start_str}.xlsx"
        else:
            file_obj = ReportService.generate_pdf(report_data, title)
            attachment_name = f"{report_type}_{start_str}.pdf"
            
        # 4. Email report (Stub for now, would integrate with an SMTP service)
        logger.info(f"EMAIL SENT: '{title}' to {recipients} with attachment {attachment_name}")
        
        # 5. Update last_run
        supabase.table("report_schedules").update({
            "last_run": datetime.now().isoformat()
        }).eq("id", schedule_id).execute()
        
    except Exception as e:
        logger.error(f"Error in scheduled report {schedule_id}: {str(e)}")

async def start_scheduler():
    """Load schedules from DB and start the background job."""
    if scheduler.running:
        return
        
    # Example: Daily revenue report at 8 AM
    # In a full impl, we'd loop through report_schedules table
    # For now, let's add a test job
    
    # scheduler.add_job(
    #     run_scheduled_report,
    #     CronTrigger(hour=8, minute=0),
    #     args=["some-id"],
    #     id="daily_revenue"
    # )
    
    scheduler.start()
    logger.info("Background scheduler started")

async def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
