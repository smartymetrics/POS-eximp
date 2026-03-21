import asyncio
import traceback
from datetime import date
from routers.analytics import get_kpis, get_rep_leaderboard

admin = {'role': 'admin'}

async def run():
    try:
        await get_kpis(date(2026, 2, 18), date(2026, 3, 21), admin)
        print("KPIS OK")
    except Exception as e:
        print("KPIS ERR:")
        traceback.print_exc()

    try:
        await get_rep_leaderboard(date(2026, 2, 18), date(2026, 3, 21), 10, admin)
        print("REP OK")
    except Exception as e:
        print("REP ERR:")
        traceback.print_exc()

asyncio.run(run())
