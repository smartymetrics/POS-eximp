"""
Seed / refresh the role_sop table from the Eximp & Cloves SOP Manual.

Usage:
    python scripts/seed_role_sop.py

Safe to re-run: upserts on the unique `department` column, so re-running
after editing ROLE_SOP_SEED below just refreshes the content HR sees.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402

ROLE_SOP_SEED = [
    {
        "department": "Executive Office",
        "aliases": ["Executive", "Exec", "Management"],
        "purpose": "Highest operational authority at Eximp & Cloves — sets corporate vision, secures strategic funding, acquires new land assets, and steers overall profitability.",
        "responsibilities": [
            "Own market positioning and brand trajectory",
            "Manage high-level investor and government relations",
            "Give final approval on new estate acquisitions and JV partnerships",
            "Set annual revenue targets and departmental budgets",
            "Directly supervise and appraise all Department Heads (HODs)",
            "Review corporate financial health monthly via the Market & Strategy Council",
        ],
        "slas": [
            "Holds ultimate authority on executive hiring/firing, capital expenditure, legal settlements, and corporate restructuring",
        ],
        "workflow_steps": [
            "Identify a potential land asset",
            "Approve marketing campaign budgets before launch",
            "Give final sign-off on expense requisitions after Finance checks the budget",
        ],
        "reporting_rhythm": "Reviews Weekly Departmental Flash Reports from every HOD (due Fridays, 6:00 PM) and the Monthly Board Pack (due 2nd working day of the new month).",
        "doc_reference": "SOP Section 5.0",
    },
    {
        "department": "Business Development and Sales",
        "aliases": ["Sales", "Sales & Acquisitions", "Acquisitions", "Sales and Acquisitions", "Business Development"],
        "purpose": "The lifeblood of the organization — solely responsible for driving corporate revenue through direct, B2B, and affiliate sales of the property portfolio.",
        "responsibilities": [
            "Sales Managers: strategize sales targets, coach associates, close high-ticket clients",
            "Sales Executives: handle daily lead follow-ups, conduct site inspections, negotiate closes",
            "Conduct outbound prospecting (LinkedIn, networking events, corporate pitches) in addition to inbound leads from Marketing",
            "Continuously recruit and train independent realtors (affiliates)",
            "Provide affiliates with updated product papers, FAQs, and pricing strictly through official channels",
        ],
        "slas": [
            "Contact every inbound lead within 2 hours of assignment",
            "Maintain a minimum 20% lead-to-inspection conversion rate and 30% inspection-to-close rate",
            "Submit End-of-Day (EOD) activity logs via the CRM by 5:30 PM",
            "Attend the mandatory Monday Sales Performance Review",
        ],
        "workflow_steps": [
            "Lead assigned via CRM — first contact within 2 hours",
            "Needs analysis: confirm budget, preferred location, investment goal",
            "Send the official Product Paper via WhatsApp/Email",
            "Book a site inspection, giving Operations 24 hours' notice",
            "Conduct a 24-hour post-inspection follow-up call",
            "On agreement, send Corporate Account Details and the digital Subscription Form",
            "On payment, fill out the Lead Handover Form",
            "Hand the file to Finance (receipting) and Legal (documentation); step back and let CX manage the post-sale relationship",
        ],
        "reporting_rhythm": "Daily EOD log by 5:30 PM. Weekly Monday Sales Performance Review. Monthly consolidated revenue and ROI report due 2nd working day of the new month.",
        "doc_reference": "SOP Section 6.0 / 28.0",
    },
    {
        "department": "Marketing and Communications",
        "aliases": ["Marketing"],
        "purpose": "Generate brand awareness, protect the corporate identity, and provide a steady, predictable stream of qualified leads to Sales.",
        "responsibilities": [
            "Act as gatekeeper of the brand — no flyer, video, or post goes out unless vetted and watermarked by Marketing",
            "Plan and run data-driven digital ad campaigns (Meta, Google) and offline campaigns (billboards, radio, print)",
            "Translate raw estate data into premium collateral: product papers, investment briefs, site layout maps, virtual tours",
            "Integrate every campaign with the corporate CRM and route leads fairly to Sales",
            "Monitor Cost Per Lead (CPL) and Cost Per Acquisition (CPA)",
        ],
        "slas": [
            "Deliver 100 qualified leads per week to Sales",
        ],
        "workflow_steps": [
            "Head of Marketing drafts a Campaign Brief (audience, budget, duration, expected ROI)",
            "Executive Office approves the budget",
            "Content team develops creatives",
            "Head of Marketing runs QA/QC for brand compliance and zero false claims",
            "Campaign goes live; monitor CPL daily",
            "Incoming leads captured in the CRM and distributed to Sales Executives round-robin",
        ],
        "reporting_rhythm": "Weekly Flash Report to the Executive Office (Fridays, 6:00 PM). Monthly consolidated revenue/ROI report with Sales, due 2nd working day of the new month.",
        "doc_reference": "SOP Section 7.0 / 29.0",
    },
    {
        "department": "Operations",
        "aliases": ["Ops"],
        "purpose": "Ensure the physical, logistical, and infrastructural smoothness of daily activities at the office and across all estate sites.",
        "responsibilities": [
            "Maintain 99% uptime for office internet, power, and HVAC systems",
            "Manage office security and access control",
            "Liaise with Sales to facilitate client site inspections",
            "Act as bridge between the office and site contractors — monitor fencing, road grading, and infrastructure delivery timelines and quality",
        ],
        "slas": [
            "Given 24 hours' notice by Sales, ensure the site vehicle is fueled, cleaned, and a driver assigned 30 minutes before departure",
        ],
        "workflow_steps": [
            "Receive site-inspection request from Sales (24-hour notice)",
            "Prepare vehicle and assign a professional driver",
            "Monitor contractor progress against delivery timelines at active estates",
        ],
        "reporting_rhythm": "Weekly Flash Report to the Executive Office (Fridays, 6:00 PM).",
        "doc_reference": "SOP Section 8.0",
    },
    {
        "department": "Human Resources and Administration",
        "aliases": ["HR", "H.R.", "Human Resources"],
        "purpose": "Recruit, retain, and develop talent; enforce corporate policy; manage all workplace administrative functions.",
        "responsibilities": [
            "Ensure job postings reflect the premium brand; run a minimum of two interview stages per candidate (Culture Fit + Technical Fit)",
            "Run the mandatory 2-day orientation for every new hire before desk deployment",
            "Track biometric attendance and enforce the lateness policy",
            "Administer the KPI appraisal process and calculate performance bonuses",
            "Act as impartial mediator in workplace disputes and run the disciplinary panel for major infractions",
            "Manage HMO enrollment, pension remittances, and staff bonding events",
        ],
        "slas": [],
        "workflow_steps": [
            "Post job and screen candidates",
            "Culture Fit interview (HR) then Technical Fit interview (HOD)",
            "2-day mandatory orientation before desk deployment",
            "Collect monthly/quarterly KPI scorecards from HODs and calculate bonuses",
        ],
        "reporting_rhythm": "Weekly Flash Report to the Executive Office. Monthly payroll, headcount, and disciplinary report due 2nd working day of the new month.",
        "doc_reference": "SOP Section 9.0",
    },
    {
        "department": "Finance and Accounts",
        "aliases": ["Finance", "Finance & Accounts", "Accounts"],
        "purpose": "Safeguard company assets, manage cash flow, ensure tax compliance, and provide accurate financial reporting to the Executive Office.",
        "responsibilities": [
            "Enforce the strict no-cash policy — all client payments go to official corporate accounts only",
            "Verify all inflows daily and issue Official Digital Receipts",
            "Act as final gatekeeper for expense requisitions against approved departmental budgets",
            "Process payroll and commissions",
            "Reconcile bank statements weekly and prepare Monthly P&L statements",
            "Prepare annual books for external tax auditors",
        ],
        "slas": [
            "Issue Official Digital Receipts within 24 hours of funds clearing",
            "Disburse payroll by the 25th of every month",
            "Process commissions bi-weekly, after verifying the Lead Handover Form and payment clearance",
        ],
        "workflow_steps": [
            "Client transfers funds to the corporate account",
            "Check the banking portal at 10:00 AM and 3:00 PM daily",
            "Match the inflow to the client's Subscription Form",
            "Generate the Official Electronic Receipt within 24 hours, copying CX and Legal",
            "For expenses: staff submits a Purchase Requisition, HOD signs off, Finance checks the budget, Executive Office gives final approval, Finance disburses to the vendor",
        ],
        "reporting_rhythm": "Weekly bank reconciliation. Monthly P&L for the Market & Strategy Council, due 2nd working day of the new month.",
        "doc_reference": "SOP Section 10.0 / 32.0",
    },
    {
        "department": "Legal and Compliance",
        "aliases": ["Legal", "Compliance"],
        "purpose": "Protect the company from legal liability, ensure regulatory compliance, and guarantee the authenticity of every land title sold to clients.",
        "responsibilities": [
            "Conduct due diligence at the State Land Registry before any land acquisition, confirming root of title and freedom from government acquisition or family disputes",
            "Draft, seal, and execute all Deeds of Assignment and Contracts of Sale",
            "Keep the company compliant with CAC, FIRS, and SCUML",
            "Handle escalated client disputes involving refunds or breach of contract; represent the company in arbitration or litigation",
        ],
        "slas": [
            "Return drafted contracts to Sales within 5 working days of a fully completed Subscription Form",
            "Ready client documents within 5 working days of full payment confirmation",
        ],
        "workflow_steps": [
            "Receive the cleared file (Subscription Form + Finance Receipt)",
            "Draft the Contract of Sale or Deed of Assignment",
            "Print, stamp, and route documents to Executive Directors for wet signature",
            "Hand signed documents to CX for dispatch",
            "For land acquisition: take coordinates from Executive Office, search the State Surveyor General's Office and Land Registry, issue a Clearance Report — no land is bought without it",
        ],
        "reporting_rhythm": "Weekly Flash Report to the Executive Office.",
        "doc_reference": "SOP Section 11.0 / 33.0",
    },
    {
        "department": "Customer Experience (CX)",
        "aliases": ["CX", "Customer Experience", "Customer Service"],
        "purpose": "Ensure absolute client satisfaction from point of sale through to final physical allocation — the post-sale face of the company.",
        "responsibilities": [
            "Acknowledge every inbound inquiry within 1 hour during business hours",
            "Log complaints as Tickets in the CRM, route to the right department, and resolve within SLA",
            "Contact the client 48 hours after a completed sale to formally welcome them",
            "Coordinate physical allocation with Operations/Surveyors",
            "Send milestone updates, birthday wishes, and end-of-year gifts to high-net-worth clients",
        ],
        "slas": [
            "Acknowledge inbound inquiries within 1 hour",
            "Resolve complaint tickets within a maximum of 72 hours",
            "Submit End-of-Day (EOD) activity logs via the CRM by 5:30 PM",
        ],
        "workflow_steps": [
            "Call the client 48 hours after payment to welcome them",
            "Dispatch physical legal documents via courier or schedule pickup",
            "When the estate is allocation-ready, schedule the date and liaise with Operations/Surveyors on plot beacons",
            "On complaint: log a CRM ticket, route to the responsible department, follow up internally every 24 hours until resolved, confirm satisfaction with the client, close the ticket",
        ],
        "reporting_rhythm": "Daily EOD log by 5:30 PM. Weekly Flash Report to the Executive Office.",
        "doc_reference": "SOP Section 12.0 / 34.0",
    },
    {
        "department": "Technology",
        "aliases": ["IT", "Information Technology", "Tech"],
        "purpose": "Manage the digital infrastructure, software tools, and data security protocols that keep the company running efficiently.",
        "responsibilities": [
            "Administer the corporate CRM so lead data flows seamlessly from Marketing to Sales",
            "Maintain the corporate website and property listings",
            "Enforce cybersecurity protocols to protect client data",
            "Create corporate email addresses for new hires and revoke access immediately on termination",
            "Automate repetitive tasks such as new-lead email sequences",
        ],
        "slas": [
            "Maintain 99.9% server uptime",
        ],
        "workflow_steps": [
            "New hire onboarding: create corporate email and system access",
            "Staff exit: revoke all system access immediately",
        ],
        "reporting_rhythm": "Weekly Flash Report to the Executive Office.",
        "doc_reference": "SOP Section 13.0",
    },
    {
        "department": "REBC",
        "aliases": ["Real Estate Bankers Club"],
        "purpose": "Build and manage an elite community of real estate ambassadors who drive indirect, high-trust sales through peer-to-peer networking — reducing corporate Customer Acquisition Cost.",
        "responsibilities": [
            "Recruit bankers, professionals, and high-net-worth individuals into the club",
            "Host bi-weekly virtual wealth-creation webinars on the Nigerian property market and the 'Build to Yield' strategy",
            "Organize exclusive quarterly site-tour events and networking galas for Premium members",
        ],
        "slas": [],
        "workflow_steps": [],
        "reporting_rhythm": "Weekly Flash Report to the Executive Office.",
        "doc_reference": "SOP Section 14.0",
    },
]


async def main():
    db = get_db()
    for row in ROLE_SOP_SEED:
        payload = dict(row)
        db.table("role_sop").upsert(payload, on_conflict="department").execute()
        print(f"  upserted: {row['department']}")
    print(f"Done. {len(ROLE_SOP_SEED)} department SOP briefs seeded.")


if __name__ == "__main__":
    asyncio.run(main())