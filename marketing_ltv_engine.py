import logging
from database import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

async def refresh_marketing_ltv_stats():
    """
    Scans paid invoices and updates total_revenue_attributed in marketing_contacts.
    Also handles 'VIP' tagging for high-value customers.
    """
    db = get_db()
    logger.info("Starting Marketing LTV Sync Engine...")

    try:
        # 1. Fetch total paid per email from invoices
        revenue_res = db.table("invoices")\
            .select("amount_paid, clients(email)")\
            .eq("status", "paid")\
            .execute()
        
        if not revenue_res.data:
            logger.info("No paid revenue found for LTV sync.")
            return

        # 2. Aggregate
        email_ltv = {}
        for inv in revenue_res.data:
            client = inv.get("clients")
            if not client or not client.get("email"):
                continue
            
            email = client["email"].lower().strip()
            email_ltv[email] = email_ltv.get(email, 0) + float(inv.get("amount_paid") or 0)

        # 3. Update Marketing Contacts
        for email, total_spent in email_ltv.items():
            # Apply VIP Tagging logic (Threshold: 10M)
            is_vip = total_spent >= 10000000
            
            # Fetch current contact to update tags
            contact_res = db.table("marketing_contacts").select("id, tags").eq("email", email).execute()
            if contact_res.data:
                contact = contact_res.data[0]
                tags = contact.get("tags") or []
                
                if is_vip and "VIP" not in tags:
                    tags.append("VIP")
                elif not is_vip and "VIP" in tags:
                    tags.remove("VIP")

                db.table("marketing_contacts").update({
                    "total_revenue_attributed": total_spent,
                    "tags": tags,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", contact["id"]).execute()

        logger.info(f"LTV Sync Complete. Processed {len(email_ltv)} contacts.")

    except Exception as e:
        logger.error(f"LTV Engine Error: {e}")

if __name__ == "__main__":
    # For manual testing
    import asyncio
    asyncio.run(refresh_marketing_ltv_stats())
