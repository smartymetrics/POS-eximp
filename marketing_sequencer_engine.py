import logging
from datetime import datetime, timedelta
from database import get_db
from marketing_service import send_marketing_email, resolve_target_recipients

logger = logging.getLogger(__name__)

async def process_active_sequences():
    """
    Industrial-Grade Background Engine for sequence automation.
    Supports: Behavioral Branching, Universal Exit, and Dynamic Delay.
    """
    db = get_db()
    today = datetime.utcnow().date().isoformat()
    
    logger.info(f"Starting automation engine for date: {today}")

    try:
        # 1. Find all active enrollments due today (or overdue)
        due_enrollments = db.table("contact_sequence_status")\
            .select("*, marketing_contacts(*), marketing_sequences(*)")\
            .eq("status", "active")\
            .lte("next_send_date", today)\
            .execute()
            
        if not due_enrollments.data:
            logger.info("No sequence emails due today.")
            return

        for enrollment in due_enrollments.data:
            contact = enrollment["marketing_contacts"]
            sequence = enrollment["marketing_sequences"]
            sequence_id = enrollment["sequence_id"]
            current_step_num = enrollment["current_step"]
            
            # --- 2. UNIVERSAL EXIT RULE (Professional Logic) ---
            # If the contact is now a 'client', immediately exit any 'Lead' sequences
            # to avoid unprofessional automated emails post-purchase.
            if contact.get("contact_type") == "client" and "Lead" in (sequence.get("name") or ""):
                logger.info(f"Auto-exiting contact {contact['email']} from Lead sequence (now a client).")
                db.table("contact_sequence_status").update({
                    "status": "exited",
                    "last_step_at": datetime.utcnow().isoformat()
                }).eq("id", enrollment["id"]).execute()
                continue

            # --- 3. FETCH STEP DETAILS ---
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
            campaign = step.get("email_campaigns")
            
            # --- 4. BEHAVIORAL BRANCHING (Smart Logic) ---
            # If the step requires interaction from a previous step
            if step.get("requires_interaction") and current_step_num > 1:
                prev_step_num = current_step_num - 1
                prev_step_res = db.table("sequence_steps").select("campaign_id").eq("sequence_id", sequence_id).eq("step_number", prev_step_num).execute()
                
                if prev_step_res.data:
                    prev_camp_id = prev_step_res.data[0]["campaign_id"]
                    # Check if the contact interacted with that campaign
                    rec_res = db.table("campaign_recipients").select("opened_at, clicked_at").eq("campaign_id", prev_camp_id).eq("contact_id", contact["id"]).execute()
                    
                    interacted = False
                    if rec_res.data:
                        rec = rec_res.data[0]
                        i_type = step.get("interaction_type") or "open"
                        # Check either opened_at or clicked_at depending on the rule
                        interacted = (rec.get("opened_at") if i_type == "open" else rec.get("clicked_at")) is not None
                    
                    # If skip_if_not_met is True, we skip this step and look for the next
                    if not interacted and step.get("skip_if_not_met"):
                        logger.info(f"Skipping step {current_step_num} for {contact['email']} (interaction not met).")
                        await move_to_next_step(db, enrollment["id"], sequence_id, current_step_num)
                        continue

            # --- 5. SEND EMAIL ---
            if campaign:
                logger.info(f"Sending sequence step {current_step_num} to {contact['email']}")
                success = await send_marketing_email(campaign, contact)
                
                if success:
                    await move_to_next_step(db, enrollment["id"], sequence_id, current_step_num)
                else:
                    logger.error(f"Failed to send sequence email to {contact['email']}")
            else:
                # No campaign for this step? Maybe it's a 'Wait Only' step. Just move on.
                await move_to_next_step(db, enrollment["id"], sequence_id, current_step_num)

    except Exception as e:
        logger.error(f"Automation Engine Error: {e}")

async def move_to_next_step(db, enrollment_id, sequence_id, current_step_num):
    """Helper to calculate the next step and schedule the next send_date."""
    next_step_num = current_step_num + 1
    next_step_res = db.table("sequence_steps")\
        .select("delay_days")\
        .eq("sequence_id", sequence_id)\
        .eq("step_number", next_step_num)\
        .execute()
    
    if next_step_res.data:
        # Calculate next send date
        delay = next_step_res.data[0].get("delay_days") or 1
        next_date = (datetime.utcnow() + timedelta(days=delay)).date().isoformat()
        
        db.table("contact_sequence_status").update({
            "current_step": next_step_num,
            "next_send_date": next_date,
            "last_step_at": datetime.utcnow().isoformat()
        }).eq("id", enrollment_id).execute()
        return True
    else:
        # No more steps - Mark as Completed
        db.table("contact_sequence_status").update({
            "status": "completed",
            "last_step_at": datetime.utcnow().isoformat()
        }).eq("id", enrollment_id).execute()
        return False

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

async def process_segment_triggers():
    """
    Scans for sequences triggered by segment entry and enrolls matching contacts.
    Runs periodically via scheduler.
    """
    db = get_db()
    try:
        # 1. Fetch active sequences that use segment triggers
        seq_res = db.table("marketing_sequences")\
            .select("id, trigger_segment_id")\
            .eq("trigger_event", "segment_entry")\
            .eq("is_active", True)\
            .not_.is_("trigger_segment_id", "null")\
            .execute()
            
        if not seq_res.data:
            logger.info("No active sequences found with segment triggers.")
            return

        logger.info(f"Checking {len(seq_res.data)} sequences for segment-based enrollment...")

        for seq in seq_res.data:
            seq_id = seq["id"]
            segment_id = seq["trigger_segment_id"]
            
            # 2. Resolve ALL current members of the segment
            contacts = await resolve_target_recipients(segment_ids=[segment_id])
            
            if not contacts:
                continue
                
            enrolled_count = 0
            for contact in contacts:
                contact_id = contact["id"]
                
                # Check if already enrolled (any status)
                existing = db.table("contact_sequence_status")\
                    .select("id")\
                    .eq("contact_id", contact_id)\
                    .eq("sequence_id", seq_id)\
                    .execute()
                    
                if not existing.data:
                    try:
                        db.table("contact_sequence_status").insert({
                            "contact_id": contact_id,
                            "sequence_id": seq_id,
                            "current_step": 1,
                            "status": "active",
                            "next_send_date": datetime.utcnow().date().isoformat()
                        }).execute()
                        enrolled_count += 1
                    except: pass
            
            if enrolled_count > 0:
                logger.info(f"Sequence {seq_id}: Auto-enrolled {enrolled_count} new members from segment {segment_id}")

    except Exception as e:
        logger.error(f"Segment Trigger Engine Error: {e}")
