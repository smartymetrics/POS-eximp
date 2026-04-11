import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import supabase, db_execute, try_claim_job
from report_service import ReportService
from email_service import send_report_email
from datetime import datetime, timedelta
import asyncio
import io
import base64
from marketing_scheduler import setup_marketing_scheduler
from marketing_sequencer_engine import process_active_sequences, process_segment_triggers
from marketing_ltv_engine import refresh_marketing_ltv_stats
from email_service import send_appointment_reminder_email, send_followup_nudge_email

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_scheduled_report(schedule_id: str):
    """Generate and email a scheduled report."""
    job_key = f"report_{schedule_id}_{datetime.now().strftime('%Y-%m-%d_%H')}"
    # Use a 50-minute threshold for hourly/daily reports to allow only one run per window
    if not await try_claim_job(job_key, threshold_mins=50):
        logger.info(f"Report {schedule_id} already claimed by another worker, skipping.")
        return

    try:
        # 1. Get schedule details
        res = await db_execute(lambda: supabase.table("report_schedules").select("*").eq("id", schedule_id).execute())
        if not res.data:
            logger.warning(f"Schedule {schedule_id} not found, skipping.")
            return

        schedule = res.data[0]
        if not schedule.get("is_active", False):
            logger.info(f"Schedule {schedule_id} is paused, skipping.")
            return

        report_type = schedule["report_type"]
        fmt = schedule.get("format", "pdf")
        recipients = schedule.get("recipients", [])

        if not recipients:
            logger.warning(f"Schedule {schedule_id} has no recipients, skipping.")
            return

        # 2. Determine date range based on frequency
        end_date = datetime.now().date()
        freq = schedule.get("frequency", "weekly")
        if freq == "daily":
            start_date = end_date - timedelta(days=1)
        elif freq == "weekly":
            start_date = end_date - timedelta(days=7)
        else:  # monthly
            first_day_current_month = end_date.replace(day=1)
            last_day_prev_month = first_day_current_month - timedelta(days=1)
            start_date = last_day_prev_month.replace(day=1)
            end_date = last_day_prev_month

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # 3. Generate report
        report_data = await ReportService.get_report_data(report_type, start_str, end_str)
        title = f"Scheduled {report_data['type']} ({start_str} to {end_str})"

        if fmt == "excel":
            # generate_excel and generate_pdf are usually CPU-bound and involve IO, wrapping for safety
            file_obj = await asyncio.get_event_loop().run_in_executor(None, lambda: ReportService.generate_excel(report_data, title))
            attachment_name = f"{report_data['type'].replace(' ', '_')}_{start_str}.xlsx"
        else:
            file_obj = await asyncio.get_event_loop().run_in_executor(None, lambda: ReportService.generate_pdf(report_data, title))
            attachment_name = f"{report_data['type'].replace(' ', '_')}_{start_str}.pdf"

        # 4. Send via Resend
        import resend
        import os
        resend.api_key = os.getenv("RESEND_API_KEY")
        from_email = os.getenv("FROM_EMAIL", "sales@mail.eximps-cloves.com")

        file_bytes = file_obj.getvalue()

        # Wrap Resend call in executor (Culprit 6 fix pattern)
        try:
            email_payload = {
                "from": f"Eximp & Cloves Reports <{from_email}>",
                "to": recipients,
                "subject": f"Scheduled Report: {report_data['type']} - {start_str} to {end_str}",
                "html": _report_email_html(report_data['type'], start_str, end_str, freq, len(report_data.get('items', []))),
                "attachments": [{
                    "filename": attachment_name,
                    "content": list(file_bytes),
                }],
            }
            await asyncio.get_event_loop().run_in_executor(None, lambda: resend.Emails.send(email_payload))
            logger.info(f"Scheduled report '{title}' emailed to {recipients}")
        except Exception as email_err:
            logger.error(f"Failed to email report: {email_err}")

        # 5. Update last_run timestamp
        await db_execute(lambda: supabase.table("report_schedules").update({
            "last_run": datetime.now().isoformat()
        }).eq("id", schedule_id).execute())

    except Exception as e:
        logger.error(f"Error running scheduled report {schedule_id}: {str(e)}")


async def process_appointment_reminders():
    """Find appointments due in 2-3 hours and send email reminders."""
    # Claim for this 30-min window
    job_key = f"appointment_reminders_{datetime.now().strftime('%Y-%m-%d_%H_%M')[:15]}0" # bucket to 30 mins
    if not await try_claim_job(job_key, threshold_mins=25):
        return

    try:
        now = datetime.now()
        two_hours_later = now + timedelta(hours=2)
        three_hours_later = now + timedelta(hours=3)
        
        # We look for appointments in the next 2-3 hour window that haven't had a reminder
        res = await db_execute(lambda: supabase.table("appointments")\
            .select("*")\
            .is_("reminder_sent_at", "null")\
            .eq("status", "scheduled")\
            .gte("scheduled_at", two_hours_later.isoformat())\
            .lte("scheduled_at", three_hours_later.isoformat())\
            .execute())
            
        appointments = res.data or []
        for appt in appointments:
            logger.info(f"Sending reminder for appointment {appt['id']} to {appt['contact_email']}")
            sent = await send_appointment_reminder_email(appt)
            if sent:
                await db_execute(lambda: supabase.table("appointments").update({
                    "reminder_sent_at": datetime.now().isoformat()
                }).eq("id", appt["id"]).execute())
                
    except Exception as e:
        logger.error(f"Error in appointment reminder job: {e}")


async def process_support_nudges():
    """Find tickets with no client response for 1 hour and send a nudge."""
    # Claim for this 30-min window
    job_key = f"support_nudges_{datetime.now().strftime('%Y-%m-%d_%H_%M')[:15]}0"
    if not await try_claim_job(job_key, threshold_mins=25):
        return

    try:
        # Find tickets where admin responded > 1hr ago and no nudge sent yet
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        res = await db_execute(lambda: supabase.table("support_tickets")\
            .select("*")\
            .eq("status", "pending")\
            .lt("last_admin_response_at", one_hour_ago)\
            .is_("followup_sent_at", "null")\
            .execute())
            
        if not res.data:
            return
            
        logger.info(f"Found {len(res.data)} tickets needing a follow-up nudge.")
        
        for ticket in res.data:
            await send_followup_nudge_email(ticket)
            
            # Mark as sent
            await db_execute(lambda: supabase.table("support_tickets").update({
                "followup_sent_at": datetime.utcnow().isoformat()
            }).eq("id", ticket["id"]).execute())
            
    except Exception as e:
        logger.error(f"Error processing support nudges: {e}")


def _report_email_html(report_type: str, start: str, end: str, freq: str, item_count: int) -> str:
    """Professional HTML email body for scheduled reports."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1A1A1A; padding: 24px; text-align: center;">
        <h1 style="color: #F5A623; margin: 0; font-size: 22px;">Eximp & Cloves</h1>
        <p style="color: #aaa; margin: 4px 0 0; font-size: 12px;">INFRASTRUCTURE LIMITED</p>
      </div>
      <div style="background: #F5A623; padding: 12px 24px;">
        <h2 style="color: #1A1A1A; margin: 0; font-size: 16px;">Scheduled Report: {report_type}</h2>
      </div>
      <div style="padding: 32px 24px; background: #fff; border: 1px solid #eee;">
        <p style="color: #333;">Hello Admin,</p>
        <p style="color: #555;">Your <strong>{freq}</strong> scheduled report has been automatically generated and is attached to this email.</p>
        <div style="background: #f9f9f9; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin: 24px 0;">
          <table style="width: 100%; font-size: 14px;">
            <tr><td style="padding:6px 0; color:#888;">Report Type</td><td style="text-align:right; font-weight:bold;">{report_type}</td></tr>
            <tr><td style="padding:6px 0; color:#888;">Period</td><td style="text-align:right;">{start} to {end}</td></tr>
            <tr><td style="padding:6px 0; color:#888;">Records</td><td style="text-align:right; font-weight:bold;">{item_count}</td></tr>
            <tr><td style="padding:6px 0; color:#888;">Frequency</td><td style="text-align:right; text-transform:capitalize;">{freq}</td></tr>
          </table>
        </div>
        <p style="color: #555; font-size: 13px;">The full report is attached as a file. You can manage your scheduled reports from the dashboard.</p>
        <hr style="border-color: #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; margin: 0;">
          Eximp & Cloves Infrastructure Limited | RC 8311800<br>
          This is an automated report - no action is required.
        </p>
      </div>
    </div>"""


async def sync_schedules_from_db():
    """Load all active schedules from DB and register them as APScheduler jobs."""
    try:
        # Using a fresh query to verify table presence
        res = await db_execute(lambda: supabase.table("report_schedules").select("*").eq("is_active", True).execute())
        schedules = res.data or []

        # Remove all existing report jobs first
        existing_jobs = scheduler.get_jobs()
        for job in existing_jobs:
            if job.id.startswith("report_"):
                job.remove()

        for s in schedules:
            _register_schedule_job(s)

        logger.info(f"Synced {len(schedules)} active report schedule(s) from database.")
    except Exception as e:
        logger.error(f"Failed to sync schedules from DB: {e}")


def _register_schedule_job(schedule: dict):
    """Register a single schedule as an APScheduler cron job."""
    schedule_id = schedule["id"]
    freq = schedule.get("frequency", "weekly")
    job_id = f"report_{schedule_id}"
    # Use custom scheduling if provided, else use defaults
    hour = schedule.get("hour", 8)
    minute = schedule.get("minute", 0)
    
    # Map UI day_of_week (1=Mon, 7=Sun) to APScheduler labels
    dow_map = {1: "mon", 2: "tue", 3: "wed", 4: "thu", 5: "fri", 6: "sat", 7: "sun"}
    dow_label = dow_map.get(schedule.get("day_of_week", 1), "mon")
    dom = schedule.get("day_of_month", 1)

    if freq == "daily":
        trigger = CronTrigger(hour=hour, minute=minute)
    elif freq == "weekly":
        trigger = CronTrigger(day_of_week=dow_label, hour=hour, minute=minute)
    elif freq == "monthly":
        trigger = CronTrigger(day=dom, hour=hour, minute=minute)
    else:
        trigger = CronTrigger(day_of_week=dow_label, hour=hour, minute=minute)

    try:
        scheduler.add_job(
            run_scheduled_report,
            trigger,
            args=[schedule_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(f"Registered job '{job_id}' for report type '{schedule.get('report_type')}'")
    except Exception as e:
        logger.error(f"Failed to register job '{job_id}': {e}")


async def start_scheduler():
    """Load schedules from DB and start the background scheduler."""
    if scheduler.running:
        return

    # Periodic sync job
    scheduler.add_job(
        sync_schedules_from_db,
        CronTrigger(minute="*/10"),
        id="sync_schedules",
        replace_existing=True,
    )
    
    # 2. Setup Marketing specific schedules
    setup_marketing_scheduler(scheduler)
    
    # 3. Automation Engine (Runs Hourly)
    scheduler.add_job(
        process_active_sequences,
        CronTrigger(hour="*"),
        id="marketing_automation",
        replace_existing=True,
    )
    
    # 4. Segment Trigger Monitor (Runs Hourly)
    scheduler.add_job(
        process_segment_triggers,
        CronTrigger(hour="*", minute="5"), # Offset by 5 mins to stagger DB load
        id="segment_trigger_monitor",
        replace_existing=True,
    )
    
    # 6. Appointment Reminders (Runs every 30 mins)
    scheduler.add_job(
        process_appointment_reminders,
        CronTrigger(minute="0,30"),
        id="appointment_reminders",
        replace_existing=True,
    )

    # 7. Support Nudges (Runs every 30 mins)
    scheduler.add_job(
        process_support_nudges,
        CronTrigger(minute="15,45"),
        id="support_nudges",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started")

    # Initial sync as a non-blocking task to speed up server boot
    asyncio.create_task(sync_schedules_from_db())


async def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
