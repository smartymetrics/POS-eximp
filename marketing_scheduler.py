import logging
from datetime import datetime, timedelta
from database import get_db
from marketing_service import broadcast_campaign

logger = logging.getLogger(__name__)

async def run_engagement_decay():
    """
    Nightly job to decay engagement scores based on inactivity.
    1. 30 Days Inactive: -5 points
    2. 90 Days Inactive: Halve score
    3. 180 Days Inactive: Score = 0
    """
    db = get_db()
    now = datetime.utcnow()
    
    logger.info("Starting nightly marketing engagement decay job...")

    try:
        # Case 1: 180 Days Inactivity -> 0
        limit_180 = (now - timedelta(days=180)).isoformat()
        db.table("marketing_contacts").update({"engagement_score": 0})\
            .lt("last_opened_at", limit_180)\
            .lt("last_clicked_at", limit_180)\
            .gt("engagement_score", 0)\
            .execute()

        # Case 2: 90 Days Inactivity -> Halve (PostgREST doesn't support expressions like score/2, so we fetch and update)
        limit_90 = (now - timedelta(days=90)).isoformat()
        dormantres = db.table("marketing_contacts").select("id", "engagement_score")\
            .lt("last_opened_at", limit_90)\
            .lt("last_clicked_at", limit_90)\
            .gt("engagement_score", 0)\
            .execute()
        
        for contact in dormantres.data:
            new_score = contact["engagement_score"] // 2
            db.table("marketing_contacts").update({"engagement_score": new_score}).eq("id", contact["id"]).execute()

        # Case 3: 30 Days Inactivity -> -5
        limit_30 = (now - timedelta(days=30)).isoformat()
        stale_res = db.table("marketing_contacts").select("id", "engagement_score")\
            .lt("last_opened_at", limit_30)\
            .lt("last_clicked_at", limit_30)\
            .gt("engagement_score", 0)\
            .execute()
            
        for contact in stale_res.data:
            new_score = max(0, contact["engagement_score"] - 5)
            db.table("marketing_contacts").update({"engagement_score": new_score}).eq("id", contact["id"]).execute()

        logger.info("Nightly marketing engagement decay job complete.")
    except Exception as e:
        logger.error(f"Error during engagement decay job: {e}")

async def check_scheduled_campaigns():
    """
    Checks for campaigns due for broadcast.
    Runs every minute.
    """
    db = get_db()
    # Use explicit UTC indicator for robust Supabase comparison
    now = datetime.utcnow().isoformat() + "Z"
    
    try:
        res = db.table("email_campaigns").select("*").eq("status", "scheduled").lte("scheduled_for", now).execute()
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
