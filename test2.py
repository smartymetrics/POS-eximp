import asyncio
import traceback
from datetime import date
from routers.analytics import get_kpis, get_revenue_trend, get_estates, get_payment_status, get_referral_sources, get_rep_leaderboard

admin = {'role': 'admin'}
start_date = date(2026, 2, 18)
end_date = date(2026, 3, 21)

async def test_endpoint(name, coro):
    try:
        await coro
        print(f"{name} OK")
    except Exception as e:
        print(f"{name} ERR:")
        traceback.print_exc()

async def run():
    await test_endpoint('kpis', get_kpis(start_date, end_date, admin))
    await test_endpoint('revenue_trend', get_revenue_trend(start_date, end_date, 'daily', admin))
    await test_endpoint('estates', get_estates(start_date, end_date, admin))
    await test_endpoint('payment_status', get_payment_status(start_date, end_date, admin))
    await test_endpoint('referral_sources', get_referral_sources(start_date, end_date, admin))
    await test_endpoint('rep_leaderboard', get_rep_leaderboard(start_date, end_date, 10, admin))

asyncio.run(run())
