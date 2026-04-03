import logging
from datetime import datetime, timedelta
from database import get_db
from marketing_service import send_marketing_email

logger = logging.getLogger(__name__)

async def process_active_sequences():
    """
    Background job to find and send due sequence emails.
    Called daily/hourly by the scheduler.
    """
    db = get_db()
    today = datetime.utcnow().date().isoformat()
    
    logger.info(f"Starting automation engine for date: {today}")

    try:
        # 1. Find enrollments due today
        due_enrollments = db.table("contact_sequence_status")\
            .select("*, marketing_contacts(*), marketing_sequences(*)")\
            .eq("status", "active")\
            .lte("next_send_date", today)\
            .execute()
            
        if not due_enrollments.data:
            logger.info("No automated emails due for sending today.")
            return

        for enrollment in due_enrollments.data:
            contact = enrollment["marketing_contacts"]
            sequence_id = enrollment["sequence_id"]
            current_step_num = enrollment["current_step"]
            
            # 2. Fetch step details
            step_res = db.table("sequence_steps")\
                .select("*, email_campaigns(*)")\
                .eq("sequence_id", sequence_id)\
                .eq("step_number", current_step_num)\
                .execute()
                
            if not step_res.data:
                # No more steps? Mark sequence as completed
                db.table("contact_sequence_status").update({
                    "status": "completed",
                    "last_step_at": datetime.utcnow().isoformat()
                }).eq("id", enrollment["id"]).execute()
                continue
            
            step = step_res.data[0]
            campaign = step["email_campaigns"]
            
            # 3. Send Email
            logger.info(f"Sending sequence step {current_step_num} to {contact['email']}")
            success = await send_marketing_email(campaign, contact)
            
            if success:
                # 4. Schedule next step
                next_step_num = current_step_num + 1
                next_step_res = db.table("sequence_steps")\
                    .select("delay_days")\
                    .eq("sequence_id", sequence_id)\
                    .eq("step_number", next_step_num)\
                    .execute()
                
                if next_step_res.data:
                    # Calculate next send date
                    delay = next_step_res.data[0]["delay_days"]
                    next_date = (datetime.utcnow() + timedelta(days=delay)).date().isoformat()
                    
                    db.table("contact_sequence_status").update({
                        "current_step": next_step_num,
                        "next_send_date": next_date,
                        "last_step_at": datetime.utcnow().isoformat()
                    }).eq("id", enrollment["id"]).execute()
                else:
                    # Completed
                    db.table("contact_sequence_status").update({
                        "status": "completed",
                        "last_step_at": datetime.utcnow().isoformat()
                    }).eq("id", enrollment["id"]).execute()
            else:
                logger.error(f"Failed to send sequence email to {contact['email']}")

    except Exception as e:
        logger.error(f"Automation Engine Error: {e}")

async def auto_enroll_contact(contact_id: str, trigger_event: str):
    """Utility to enroll a contact based on an event (e.g. 'client_created')."""
    db = get_db()
    
    # Find active sequences for this trigger
    seq_res = db.table("marketing_sequences").select("id").eq("trigger_event", trigger_event).eq("is_active", True).execute()
    
    for seq in seq_res.data:
        # Check if already in it
        existing = db.table("contact_sequence_status").select("id").eq("contact_id", contact_id).eq("sequence_id", seq["id"]).execute()
        if not existing.data:
            # Enroll starting at Step 1 (delay 0 usually)
            db.table("contact_sequence_status").insert({
                "contact_id": contact_id,
                "sequence_id": seq["id"],
                "current_step": 1,
                "status": "active",
                "next_send_date": datetime.utcnow().date().isoformat()
            }).execute()
            logger.info(f"Auto-enrolled contact {contact_id} into sequence {seq['id']} via {trigger_event}")
