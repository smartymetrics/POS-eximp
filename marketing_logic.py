import logging
from database import get_db, db_execute
from datetime import datetime
from marketing_sequencer_engine import auto_enroll_contact

logger = logging.getLogger(__name__)

async def sync_client_to_marketing(client_data: dict):
    """
    Ensures a client in the Finance system is correctly 
    mirrored and upgraded in the Marketing system.
    """
    db = get_db()
    email = client_data.get("email", "").strip().lower()
    if not email:
        return None

    try:
        client_id = client_data.get("id")
        
        # 1. Search by client_id first, then fallback to email (handles email changes safely)
        mc_res = None
        if client_id:
            mc_res = await db_execute(lambda: db.table("marketing_contacts").select("*").eq("client_id", client_id).execute())
            
        if not mc_res or not mc_res.data:
            mc_res = await db_execute(lambda: db.table("marketing_contacts").select("*").eq("email", email).execute())
        
        contact_id = None
        # 1b. Check for placeholder emails (Safety Filter)
        suppressed_domains = ["temp-eximps.com", "placeholder.com"]
        is_placeholder = any(domain in email for domain in suppressed_domains)
        
        marketing_data = {
            "email": email,
            "first_name": client_data.get("full_name", "").split(" ")[0] if client_data.get("full_name") else "",
            "last_name": " ".join(client_data.get("full_name", "").split(" ")[1:]) if client_data.get("full_name") else "",
            "phone": client_data.get("phone"),
            "contact_type": "client",
            "client_id": client_data.get("id"),
            "is_subscribed": False if is_placeholder else True, # Suppress placeholders
            "engagement_score": 100, # Client conversion = Max score
            "updated_at": datetime.utcnow().isoformat()
        }


        if mc_res.data:
            # Upgrade existing lead to client
            contact_id = mc_res.data[0]["id"]
            await db_execute(lambda: db.table("marketing_contacts").update(marketing_data).eq("id", contact_id).execute())
            logger.info(f"Upgraded marketing contact {email} to CLIENT status.")
            # Enroll if not already in some sequences
            await auto_enroll_contact(contact_id, "client_created")
        else:
            # Create new marketing contact for this client
            res = await db_execute(lambda: db.table("marketing_contacts").insert(marketing_data).execute())
            if res.data:
                contact_id = res.data[0]["id"]
                logger.info(f"Created new marketing contact for client {email}.")
                await auto_enroll_contact(contact_id, "client_created")

        return contact_id
    except Exception as e:
        logger.error(f"Error syncing client {email} to marketing: {e}")
        return None
