from database import get_db
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Curated international marketing and awareness days
MARKETING_DAYS = [
    {"name": "Valentine's Day", "month": 2, "day": 14, "action": "Gift-giving and investment legacy campaigns."},
    {"name": "International Women's Day", "month": 3, "day": 8, "action": "Celebrate female property owners and independence."},
    {"name": "World Health Day", "month": 4, "day": 7, "action": "The link between wellness and serene living spaces."},
    {"name": "Mother's Day (Global)", "month": 5, "day": 10, "action": "Target the decision-makers; families and homes."},
    {"name": "Father's Day", "month": 6, "day": 21, "action": "Legacy building and wealth accumulation for dads."},
    {"name": "World Habitat Day", "month": 10, "day": 5, "action": "Discuss sustainable real estate and urban life."},
    {"name": "Black Friday", "month": 11, "day": 27, "action": "The only time for significant plot discounts."},
    {"name": "International Migrants Day", "month": 12, "day": 18, "action": "Diaspora investment opportunities and homecoming."}
]

def get_marketing_calendar(year: int = None) -> List[Dict[str, Any]]:
    """Fetches public holidays, marketing days, and custom business events."""
    import requests # Keep local to avoid global import overhead if possible, or move to top
    if not year:
        year = datetime.now().year
    
    events = []
    db = get_db()
    
    # 1. Fetch Nigerian Holidays via Nager.Date API
    try:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/NG"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            holidays = response.json()
            for h in holidays:
                events.append({
                    "name": h["name"],
                    "date": h["date"],
                    "type": "public_holiday",
                    "action": f"Warm seasonal greeting + {h['name']} promotion."
                })
        else:
            logger.error(f"Failed to fetch holidays from Nager.Date: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching holidays: {e}")

    # 2. Add Marketing Days
    for md in MARKETING_DAYS:
        dt = datetime(year, md["month"], md["day"])
        events.append({
            "name": md["name"],
            "date": dt.strftime("%Y-%m-%d"),
            "type": "marketing_day",
            "action": md["action"]
        })

    # 3. Add Recurring Company Touchpoints (System Defaults)
    events.append({
        "name": "First of Month Broadcast",
        "date": f"{year}-{datetime.now().month:02d}-01",
        "type": "recurring",
        "action": "New month inspiration and property updates."
    })

    # 4. Fetch Custom Business Events from DB
    try:
        custom_res = db.table("marketing_events").select("*").execute()
        for ce in custom_res.data:
            start_dt = datetime.strptime(ce["event_date"], "%Y-%m-%d")
            end_dt = datetime.strptime(ce["end_date"], "%Y-%m-%d") if ce.get("end_date") else datetime(year, 12, 31)
            
            if not ce.get("is_recurring"):
                # One-off
                if start_dt.year == year:
                    events.append({
                        "id": ce["id"],
                        "name": ce["name"],
                        "date": ce["event_date"],
                        "type": "business_event",
                        "action": ce["action"]
                    })
            else:
                # Project recurring instances for the current year
                freq = ce.get("frequency")
                curr = start_dt
                
                # Fast forward to the start of the requested year if needed
                # (but respect the original start_dt)
                while curr < datetime(year, 1, 1) and curr <= end_dt:
                    if freq == 'weekly': curr += timedelta(days=7)
                    elif freq == 'monthly':
                        month = curr.month + 1 if curr.month < 12 else 1
                        y = curr.year if curr.month < 12 else curr.year + 1
                        curr = curr.replace(year=y, month=month)
                    elif freq == 'yearly': curr = curr.replace(year=curr.year + 1)
                    else: break

                # Add instances within the year
                while curr.year == year and curr <= end_dt:
                    events.append({
                        "id": ce["id"],
                        "name": ce["name"] + (" (Recurring)" if freq else ""),
                        "date": curr.strftime("%Y-%m-%d"),
                        "type": "business_event",
                        "action": ce["action"],
                        "is_custom": True
                    })
                    if freq == 'weekly': curr += timedelta(days=7)
                    elif freq == 'monthly':
                        month = curr.month + 1 if curr.month < 12 else 1
                        y = curr.year if curr.month < 12 else curr.year + 1
                        curr = curr.replace(year=y, month=month)
                    elif freq == 'yearly': curr = curr.replace(year=curr.year + 1)
                    else: break
    except Exception as e:
        logger.error(f"Error fetching custom events: {e}")

    # 5. Financial Payment Reminders (Dynamic from Invoices)
    try:
        today_date = datetime.utcnow().date()
        # Look for invoices that are due soon, or are already overdue but not fully paid
        invoices_res = db.table("invoices").select("id, amount, amount_paid, due_date, status, clients(full_name)").neq("status", "voided").execute()
        invoices = invoices_res.data or []
        
        for inv in invoices:
            due_date_str = inv.get("due_date", "")
            if not due_date_str: continue
            
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            amount = float(inv.get("amount") or 0)
            paid = float(inv.get("amount_paid") or 0)
            
            if paid >= amount: continue # Fully paid
            
            client_name = inv.get("clients", {}).get("full_name", "Unknown Client")
            
            days_until_due = (due_date - today_date).days
            
            # If it's overdue, surface it as an urgent event for TODAY
            if days_until_due < 0:
                events.append({
                    "id": inv["id"],
                    "name": f"Payment Overdue: {client_name}",
                    "date": today_date.strftime("%Y-%m-%d"),
                    "type": "financial_reminder",
                    "action": f"Client is {-days_until_due} days overdue. Send Payment Reminder."
                })
            # If it's coming up in the next 14 days, surface it on its due date
            elif 0 <= days_until_due <= 14:
                events.append({
                    "id": inv["id"],
                    "name": f"Payment Due: {client_name}",
                    "date": due_date.strftime("%Y-%m-%d"),
                    "type": "financial_reminder",
                    "action": f"Invoice due today. Trigger Due Date sequence."
                })
    except Exception as e:
        logger.error(f"Error fetching financial reminders for calendar: {e}")

    # Sort by date
    events.sort(key=lambda x: x["date"])
    
    # Filter only future events (or recent past for context) - allow today as future
    now_str = today_date.strftime("%Y-%m-%d")
    final_events = [e for e in events if e["date"] >= now_str]
    
    return final_events
