import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

templates = [
    {
        "name": "Lead Generation",
        "department": "Sales & Acquisitions",
        "category": "Marketing",
        "measurement_source": "mkt_leads_added",
        "default_unit": "leads",
        "description": "Total number of unique leads added to the CRM. Automatically counts Marketing Contacts and Clients added by the assignee.",
        "is_active": True
    },
    {
        "name": "Lead Conversion Rate",
        "department": "Sales & Acquisitions",
        "category": "Sales",
        "measurement_source": "mkt_lead_conversion",
        "default_unit": "%",
        "description": "Percentage of marketing contacts that were converted into clients.",
        "is_active": True
    },
    {
        "name": "Sales Revenue (Paid)",
        "department": "Finance",
        "category": "Revenue",
        "measurement_source": "sales_revenue",
        "default_unit": "NGN",
        "description": "Total actual revenue collected (Paid payments) attributed to the staff.",
        "is_active": True
    },
    {
        "name": "Deals Closed",
        "department": "Sales & Acquisitions",
        "category": "Sales",
        "measurement_source": "sales_deals_closed",
        "default_unit": "deals",
        "description": "Count of invoices/deals marked as 'Closed' in the pipeline.",
        "is_active": True
    },
    {
        "name": "Client Appointments",
        "department": "Operations",
        "category": "Activity",
        "measurement_source": "ops_appointments",
        "default_unit": "appts",
        "description": "Number of field or office appointments successfully completed.",
        "is_active": True
    },
    {
        "name": "Support Ticket Resolution",
        "department": "General",
        "category": "Service",
        "measurement_source": "admin_ticket_esc",
        "default_unit": "tickets",
        "description": "Efficiency in handling and resolving support/admin tickets.",
        "is_active": True
    }
]

async def seed():
    print("Seeding Professional KPI Library...")
    for t in templates:
        # Check if exists
        res = supabase.table("kpi_templates").select("id").eq("name", t["name"]).execute()
        if res.data:
            print(f"Skipping {t['name']} (already exists)")
            continue
        
        supabase.table("kpi_templates").insert(t).execute()
        print(f"Added: {t['name']}")

if __name__ == "__main__":
    asyncio.run(seed())
