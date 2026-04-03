import requests
import logging
from datetime import datetime
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
    """Fetches public holidays for Nigeria and merges with marketing days."""
    if not year:
        year = datetime.now().year
    
    events = []
    
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

    # 3. Add Recurring Company Touchpoints
    # (Monday Motivation, Monthly Update)
    events.append({
        "name": "First of Month Broadcast",
        "date": f"{year}-{datetime.now().month:02d}-01",
        "type": "recurring",
        "action": "New month inspiration and property updates."
    })

    # Sort by date
    events.sort(key=lambda x: x["date"])
    
    # Filter only future events (or recent past for context)
    now_str = datetime.now().strftime("%Y-%m-%d")
    final_events = [e for e in events if e["date"] >= now_str]
    
    return final_events
