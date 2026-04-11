import logging
from datetime import datetime, timedelta
from database import get_db, db_execute
from marketing_service import broadcast_campaign

logger = logging.getLogger(__name__)

async def run_engagement_decay():
    """
    Nightly job to decay engagement scores based on inactivity.
    """
    # Claim for this 24-hour window
    from database import try_claim_job
    job_key = f"engagement_decay_{datetime.utcnow().strftime('%Y-%m-%d')}"
    if not await try_claim_job(job_key, threshold_mins=60 * 20): # 20 hour lock
        return

    db = get_db()
    logger.info("Starting nightly marketing engagement decay job...")

    try:
        # Call the bulk SQL RPC to perform the halving and decrements efficiently
        await db_execute(lambda: db.rpc("bulk_decay_engagement").execute())

        logger.info("Nightly marketing engagement decay job complete.")
    except Exception as e:
        logger.error(f"Error during engagement decay job: {e}")

async def check_scheduled_campaigns():
    """
    Checks for campaigns due for broadcast.
    Runs every 5 mins.
    """
    # Claim for this specific 5-min window
    from database import try_claim_job
    job_key = f"campaign_check_{datetime.utcnow().strftime('%Y-%m-%d_%H_%M')[:15]}" # bucket to 5 mins
    if not await try_claim_job(job_key, threshold_mins=4):
        return

    db = get_db()
    # Use explicit UTC indicator for robust Supabase comparison
    now = datetime.utcnow().isoformat() + "Z"
    
    try:
        res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("status", "scheduled").lte("scheduled_for", now).execute())
        due = res.data or []
        
        if not due:
            # Silent check — no logs to avoid bloating output every 5 mins
            return
        
        for camp in due:
            if not camp.get("scheduled_for"): continue # Safety
            
            logger.info(f"Triggering scheduled broadcast for campaign: {camp['name']} ({camp['id']})")
            
            # Unpack target configuration
            config = camp.get("target_config") or {}
            segment_ids = config.get("segment_ids")
            manual_emails = config.get("manual_emails")
            
            # Trigger broadcast (this is an async function)
            await broadcast_campaign(camp["id"], segment_ids, manual_emails)
            
    except Exception as e:
        logger.error(f"Error checking scheduled campaigns: {e}")

def setup_marketing_scheduler(scheduler):
    """Integrates marketing tasks into the main APScheduler."""
    # Run at 2 AM every night
    scheduler.add_job(run_engagement_decay, 'cron', hour=2, minute=0)
    logger.info("Marketing engagement decay scheduled for 02:00 daily.")

    # Check for scheduled campaigns every 5 minutes
    scheduler.add_job(check_scheduled_campaigns, 'interval', minutes=5, id='check_scheduled_campaigns')
    logger.info("Campaign scheduler started (5-minute check).")
