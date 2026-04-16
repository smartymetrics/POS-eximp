
import os
import sys
import asyncio
from datetime import date, datetime, timedelta

# Add root to sys.path
sys.path.append(os.getcwd())

from database import get_db, db_execute

async def test_stats():
    db = get_db()
    staff_res = await db_execute(lambda: db.table("admins").select("id, full_name, role, primary_role, department, is_active, is_archived, created_at, staff_profiles(dob, date_joined)").execute())
    staff_data = staff_res.data
    active_staff = [s for s in staff_data if s.get("is_active") and not s.get("is_archived")]
    
    today_dt = date.today()
    upcoming_birthdays = []
    upcoming_anniversaries = []
    
    print(f"Total Active Staff: {len(active_staff)}")
    
    for s in active_staff:
        prof = s.get("staff_profiles")
        if prof and len(prof) > 0:
            p = prof[0]
            print(f"Checking staff {s['full_name']}: dob={p.get('dob')}, date_joined={p.get('date_joined')}")
            # Check Birthdays (Next 14 days)
            if p.get("dob"):
                try:
                    dob = date.fromisoformat(p["dob"])
                    # Handle leap years safely
                    try:
                        this_year_bday = dob.replace(year=today_dt.year)
                    except ValueError:
                        this_year_bday = dob.replace(year=today_dt.year, day=dob.day-1)
                        
                    if this_year_bday < today_dt:
                        try:
                            this_year_bday = dob.replace(year=today_dt.year + 1)
                        except ValueError:
                            this_year_bday = dob.replace(year=today_dt.year + 1, day=dob.day-1)
                    
                    days_to_bday = (this_year_bday - today_dt).days
                    print(f"  Bday in {days_to_bday} days")
                    if days_to_bday <= 14:
                        upcoming_birthdays.append({
                            "id": s["id"], "full_name": s["full_name"], "days_left": days_to_bday
                        })
                except Exception as e:
                    print(f"  Bday Error: {e}")
                    
            # Check Anniversaries (Next 30 days)
            if p.get("date_joined"):
                try:
                    dj = date.fromisoformat(p["date_joined"])
                    try:
                        this_year_anniv = dj.replace(year=today_dt.year)
                    except ValueError:
                        this_year_anniv = dj.replace(year=today_dt.year, day=dj.day-1)
                        
                    if this_year_anniv < today_dt:
                        try:
                            this_year_anniv = dj.replace(year=today_dt.year + 1)
                        except ValueError:
                            this_year_anniv = dj.replace(year=today_dt.year + 1, day=dj.day-1)
                            
                    days_to_anniv = (this_year_anniv - today_dt).days
                    years_worked = this_year_anniv.year - dj.year
                    print(f"  Anniv in {days_to_anniv} days ({years_worked} years)")
                    if days_to_anniv <= 30 and years_worked > 0:
                        upcoming_anniversaries.append({
                            "id": s["id"], "full_name": s["full_name"], "days_left": days_to_anniv, "years": years_worked
                        })
                except Exception as e:
                    print(f"  Anniv Error: {e}")

    print("\nRESULTS:")
    print(f"Upcoming Birthdays: {upcoming_birthdays}")
    print(f"Upcoming Anniversaries: {upcoming_anniversaries}")

if __name__ == "__main__":
    asyncio.run(test_stats())
