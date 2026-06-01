import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Flowable

# ── Brand colours ──────────────────────────────────────────────────────────────
NAVY   = HexColor("#0D1B3E")
GREEN  = HexColor("#3CB449")
WHITE  = white
LGREY  = HexColor("#F4F6F9")
MGREY  = HexColor("#D0D5DD")
DGREY  = HexColor("#667085")
BLACK  = black

W, H = A4

# ── Styles ─────────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE   = S("Title2", fontName="Helvetica-Bold",  fontSize=22, textColor=WHITE,
            spaceAfter=4, leading=28)
H1      = S("H1",    fontName="Helvetica-Bold",  fontSize=15, textColor=NAVY,
            spaceBefore=14, spaceAfter=6, leading=20)
H2      = S("H2",    fontName="Helvetica-Bold",  fontSize=12, textColor=NAVY,
            spaceBefore=10, spaceAfter=4, leading=16)
H3      = S("H3",    fontName="Helvetica-Bold",  fontSize=10, textColor=GREEN,
            spaceBefore=8, spaceAfter=3, leading=14)
BODY    = S("Body2", fontName="Helvetica",        fontSize=9,  textColor=black,
            spaceAfter=5, leading=14, alignment=TA_JUSTIFY)
BODYSM  = S("BodySm",fontName="Helvetica",        fontSize=8,  textColor=black,
            spaceAfter=4, leading=12)
SMALL   = S("Small", fontName="Helvetica",        fontSize=7.5,textColor=DGREY,
            spaceAfter=3, leading=11)
CONF    = S("Conf",  fontName="Helvetica-Oblique",fontSize=7.5,textColor=DGREY,
            alignment=TA_CENTER, spaceAfter=2)
LABEL   = S("Label", fontName="Helvetica-Bold",   fontSize=8,  textColor=DGREY,
            spaceBefore=2, spaceAfter=1, leading=11)
PART    = S("Part",  fontName="Helvetica-Bold",   fontSize=18, textColor=WHITE,
            spaceAfter=4, leading=24, alignment=TA_CENTER)
PARTSUB = S("PartSub",fontName="Helvetica",       fontSize=10, textColor=LGREY,
            spaceAfter=0, leading=14, alignment=TA_CENTER)
CENTER  = S("Ctr",   fontName="Helvetica",        fontSize=9,  textColor=black,
            alignment=TA_CENTER, spaceAfter=4)
GREENB  = S("GreenB",fontName="Helvetica-Bold",   fontSize=9,  textColor=GREEN)

# ── Helpers ────────────────────────────────────────────────────────────────────

def confidential_header():
    return Paragraph("CONFIDENTIAL — INTERNAL USE ONLY", CONF)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=6, spaceBefore=4)

def navy_rule():
    return HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=8, spaceBefore=4)

def green_rule():
    return HRFlowable(width="100%", thickness=1.5, color=GREEN, spaceAfter=6, spaceBefore=4)

def kv_table(rows, col_widths=None):
    """Two-column label/value table."""
    if col_widths is None:
        col_widths = [5.5*cm, 10.5*cm]
    data = [[Paragraph(f"<b>{k}</b>", BODYSM), Paragraph(v, BODYSM)] for k, v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LGREY, WHITE]),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]))
    return t

def hub_table(rows):
    col_widths = [2*cm, 3.5*cm, 10.5*cm]
    header = [Paragraph("<b>Hub</b>", BODYSM), Paragraph("<b>Name</b>", BODYSM), Paragraph("<b>Core Capabilities</b>", BODYSM)]
    data = [header] + [[Paragraph(f"<b>{h}</b>", BODYSM), Paragraph(n, BODYSM), Paragraph(c, BODYSM)] for h, n, c in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGREY, WHITE]),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]))
    return t

def perm_table(rows):
    col_widths = [7*cm, 2.5*cm, 2.5*cm, 2.5*cm]
    header = [Paragraph("<b>Capability</b>", BODYSM),
              Paragraph("<b>HR Admin</b>", BODYSM),
              Paragraph("<b>Manager</b>", BODYSM),
              Paragraph("<b>Staff</b>", BODYSM)]
    data = [header]
    for cap, hr_a, mgr, stf in rows:
        row = [Paragraph(cap, BODYSM), Paragraph(hr_a, CENTER), Paragraph(mgr, CENTER), Paragraph(stf, CENTER)]
        data.append(row)
    t = Table(data, colWidths=col_widths)
    ts = [
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGREY, WHITE]),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]
    t.setStyle(TableStyle(ts))
    return t

def compliance_table(rows):
    col_widths = [2.8*cm, 3*cm, 3*cm, 7.2*cm]
    header = [Paragraph("<b>Obligation</b>", BODYSM),
              Paragraph("<b>Authority</b>", BODYSM),
              Paragraph("<b>Rate / Basis</b>", BODYSM),
              Paragraph("<b>How Everywin Handles It</b>", BODYSM)]
    data = [header] + [[Paragraph(a, BODYSM), Paragraph(b, BODYSM), Paragraph(c, BODYSM), Paragraph(d, BODYSM)] for a,b,c,d in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGREY, WHITE]),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]))
    return t

def tax_band_table(rows):
    col_widths = [9*cm, 5*cm]
    header = [Paragraph("<b>Annual Income Band</b>", BODYSM), Paragraph("<b>Tax Rate</b>", BODYSM)]
    data = [header] + [[Paragraph(a, BODYSM), Paragraph(b, BODYSM)] for a,b in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGREY, WHITE]),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]))
    return t

def glossary_table(rows):
    col_widths = [4.5*cm, 11.5*cm]
    data = [[Paragraph(f"<b>{k}</b>", BODYSM), Paragraph(v, BODYSM)] for k,v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LGREY, WHITE]),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]))
    return t

def part_divider(part_label, title, subtitle):
    """Full-width navy divider page-block."""
    inner = [
        Spacer(1, 1*cm),
        Paragraph(part_label, S("pl", fontName="Helvetica", fontSize=9, textColor=GREEN, alignment=TA_CENTER)),
        Paragraph(title, PART),
        Paragraph(subtitle, PARTSUB),
        Spacer(1, 1*cm),
    ]
    data = [[inner]]
    t = Table(data, colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("LEFTPADDING",(0,0),(-1,-1), 20),
        ("RIGHTPADDING",(0,0),(-1,-1), 20),
        ("TOPPADDING",(0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
    ]))
    return t

# ── Section builder helpers ────────────────────────────────────────────────────

def section(num_title, content_items):
    """Returns a list of flowables for a named section."""
    out = [Paragraph(num_title, H1), green_rule()]
    out += content_items
    return out

def subsection(title, items):
    out = [Paragraph(title, H2)]
    out += items
    return out

def field_rows(rows):
    """Small label/content table for portal field specs."""
    data = [[Paragraph(f"<b>{k}</b>", SMALL), Paragraph(v, SMALL)] for k, v in rows]
    t = Table(data, colWidths=[4.5*cm, 11.5*cm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LGREY, WHITE]),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("GRID",          (0,0), (-1,-1), 0.3, MGREY),
    ]))
    return t

# ── Cover page ─────────────────────────────────────────────────────────────────

def cover():
    elems = []

    # Navy header block
    header_data = [[
        [
            Paragraph("AFRICA PAYROLL INFRASTRUCTURE OS", S("badge", fontName="Helvetica", fontSize=8, textColor=GREEN, alignment=TA_CENTER)),
            Spacer(1, 8),
            Paragraph("EVERYWIN", S("logo", fontName="Helvetica-Bold", fontSize=36, textColor=WHITE, alignment=TA_CENTER)),
            Spacer(1, 4),
            Paragraph("Product Requirements Document", S("subt", fontName="Helvetica", fontSize=13, textColor=LGREY, alignment=TA_CENTER)),
            Spacer(1, 12),
            Paragraph("Version 2.0 · June 2026 · Confidential", S("meta", fontName="Helvetica-Oblique", fontSize=9, textColor=MGREY, alignment=TA_CENTER)),
        ]
    ]]
    ht = Table(header_data, colWidths=[16*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 30),
        ("BOTTOMPADDING", (0,0),(-1,-1), 30),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
    ]))
    elems.append(ht)
    elems.append(Spacer(1, 18))

    # Portal badges
    badges = [["Staff Portal", "Manager Portal", "HR Admin Portal", "Anchor Payroll", "Multi-Tenant Onboarding"]]
    bt = Table(badges, colWidths=[3.2*cm]*5)
    bt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GREEN),
        ("TEXTCOLOR",     (0,0),(-1,-1), WHITE),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 7.5),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), 3),
    ]))
    elems.append(bt)
    elems.append(Spacer(1, 20))

    meta = [
        ("DOCUMENT TYPE", "Product Requirements Document"),
        ("VERSION",       "2.0 — Full Platform Specification"),
        ("DATE",          "June 2026"),
        ("STATUS",        "Draft"),
        ("AUDIENCE",      "Product, Engineering, Design, Investors"),
    ]
    elems.append(kv_table(meta))
    elems.append(Spacer(1, 20))

    elems.append(Paragraph(
        "Powered by Anchor Disbursements · Built for Emerging Economies · for every organisation",
        S("footer_cover", fontName="Helvetica-Oblique", fontSize=8, textColor=DGREY, alignment=TA_CENTER)
    ))
    elems.append(PageBreak())
    return elems

# ── Table of Contents ──────────────────────────────────────────────────────────

def toc():
    elems = [confidential_header(), Spacer(1,6)]
    elems.append(Paragraph("Table of Contents", H1))
    elems.append(green_rule())
    toc_items = [
        "1  Executive Summary & Platform Overview",
        "2  Platform Architecture & Multi-Tenancy",
        "3  Organisation Onboarding Flow",
        "4  Role-Based Access Control (RBAC)",
        "PART A  STAFF PORTAL",
        "    A.1  Staff Dashboard",
        "    A.2  My Profile & Bio Data",
        "    A.3  Attendance & Timesheets",
        "    A.4  Leave Management",
        "    A.5  Performance & Goals",
        "    A.6  Learning & Growth",
        "    A.7  Compensation — My Payroll & Bonuses",
        "    A.8  Engagement, Culture & Messaging",
        "    A.9  Documents, Requests & Compliance",
        "PART B  MANAGER PORTAL",
        "    B.1  Team Dashboard",
        "    B.2  Team Attendance & Timesheets",
        "    B.3  Leave Approvals",
        "    B.4  Performance Management",
        "    B.5  Shift Scheduling & Calendar",
        "    B.6  Disciplinary & Incident Logging",
        "    B.7  Succession Planning & Skills Matrix",
        "    B.8  Messaging & Engagement",
        "    B.9  Task Management",
        "PART C  HR ADMIN PORTAL",
        "    C.1  HR Overview Dashboard",
        "    C.2  Recruitment — ATS & Talent Pool",
        "    C.3  People & Organisation",
        "    C.4  Time, Attendance & Shifts",
        "    C.5  Leave Administration",
        "    C.6  Performance Administration",
        "    C.7  Learning, Onboarding & Probation",
        "    C.8  Compensation, Payroll & Anchor Disbursement",
        "    C.9  Engagement, Surveys & Culture",
        "    C.10 Documents, Contracts & Compliance",
        "    C.11 Administration, Reports & Audit",
        "5  Payroll Disbursement — Detailed Flow",
        "6  Universal Messaging System",
        "7  Statutory Compliance Engine",
        "8  Non-Functional Requirements",
        "9  Glossary",
    ]
    for item in toc_items:
        bold = not item.startswith("    ")
        fn = "Helvetica-Bold" if bold else "Helvetica"
        col = NAVY if bold else black
        elems.append(Paragraph(item, S("toc"+item[:4], fontName=fn, fontSize=9, textColor=col, spaceAfter=3, leading=13)))
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Executive Summary
# ═══════════════════════════════════════════════════════════════════════════════

def sec1():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("1 · Executive Summary & Platform Overview", [
        Paragraph("What Everywin Is", H2),
        Paragraph(
            "Everywin is the modern HR infrastructure OS for organisations in emerging economies. "
            "It powers payroll, compliance, workforce management, and the entire people operations stack — "
            "from hiring and onboarding to salary payments, benefits, and employee management — "
            "seamlessly across multiple countries and regulatory environments.",
            BODY),
        Spacer(1, 8),
        Paragraph("The 9-Hub Architecture", H2),
        Paragraph("Everywin is structured around nine integrated hubs, each owning a distinct domain of people operations:", BODY),
        Spacer(1,4),
        hub_table([
            ("Hub 1",  "Recruitment",               "ATS, pipeline, talent pool, candidate chat, bulk email"),
            ("Hub 2",  "People & Org",               "Employee directory, bio-data, org chart, departments, D&I"),
            ("Hub 3",  "Time & Attendance",          "Check-in/out, timesheets, geofencing, shift scheduling"),
            ("Hub 4",  "Leave Management",           "Requests, approvals, accrual, balances, policies"),
            ("Hub 5",  "Performance & Growth",       "Scoring engine, OKRs, PIPs, 360° reviews, skills matrix, succession"),
            ("Hub 5B", "Learning & Growth",          "Training hub, onboarding checklists, probation tracker"),
            ("Hub 6",  "Compensation & Benefits",    "Payroll engine, Anchor disbursement, local tax & statutory deductions, bonuses, expenses"),
            ("Hub 7",  "Engagement & Culture",       "Announcements, kudos, surveys, policy library, internal job board"),
            ("Hub 7B", "Universal Messaging",        "Real-time DMs, group chats, voice notes, full media, role-based access"),
            ("Hub 8",  "Documents & Compliance",     "Contracts, HR letters, grievances, disciplinary, assets, documents vault"),
            ("Hub 9",  "Administration",             "Reports, offboarding, audit logs, system users, settings"),
        ]),
        Spacer(1, 10),
        Paragraph("Key Differentiators", H2),
        field_rows([
            ("Anchor-powered payroll disbursement",
             "Salaries disburse automatically to staff bank accounts. Zero manual transfers once configured."),
            ("Full statutory compliance — per country",
             "Income tax (PAYE/WHT equivalent), pension/provident fund, housing fund, health insurance, workplace insurance — computed automatically per the applicable jurisdiction on every payroll run."),
            ("Three-tier RBAC",
             "Staff, Manager, and HR Admin portals each surface only the data and actions their role is entitled to."),
            ("Universal Messaging System",
             "Full-featured internal communication layer — DMs, groups, voice notes, media — embedded across all portals."),
            ("Multi-tenant isolation",
             "Every registered organisation gets a fully isolated OS. No data cross-contamination between organisations."),
            ("Self-service onboarding",
             "Any HR team can configure their environment, invite staff, and run their first payroll in under 30 minutes."),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Platform Architecture
# ═══════════════════════════════════════════════════════════════════════════════

def sec2():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("2 · Platform Architecture & Multi-Tenancy", [
        Paragraph(
            "Everywin is a multi-tenant SaaS platform. Each registered organisation receives an isolated operating "
            "environment (referred to as the 'Everywin OS'). All tenant data is partitioned at the database level "
            "using an organisation_id foreign key on every record. No tenant can access, view, or infer data "
            "belonging to another tenant. Row-level security is enforced at the database level — not only in application code.",
            BODY),
        Spacer(1,6),
        Paragraph("Tenancy Model", H2),
        field_rows([
            ("Organisation Registration", "Any company registers via the public sign-up page. On approval, their OS is provisioned automatically."),
            ("Data Isolation",            "Every record is tagged with organisation_id. Queries are scoped to the authenticated org at the database level."),
            ("User Accounts",             "Each staff member gets a platform user account linked to their employing organisation. A user cannot log into another org's OS."),
            ("Anchor Integration",        "Each organisation connects their own Anchor funding account. Payroll funds are never commingled across tenants."),
            ("Subdomain / OS Identity",   "Each org OS is accessible via a unique URL or organisation identifier resolved at login."),
            ("Ads Platform",              "Everywin's Ads Platform operates cross-tenant — ads are served to all users, but advertiser targeting is aggregated and anonymised."),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Onboarding
# ═══════════════════════════════════════════════════════════════════════════════

def sec3():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("3 · Organisation Onboarding Flow", [
        Paragraph(
            "The onboarding flow is the first product experience for every HR Admin. It must be frictionless, "
            "fully self-service, and complete within 30 minutes for a typical organisation of 50–200 staff. "
            "It is structured in three phases: Organisation Setup, Team Population, and Payroll Configuration.",
            BODY),
        Spacer(1,6),
        Paragraph("Phase 1 — Organisation Registration & Setup", H2),
        field_rows([
            ("Step 1 · Registration",
             "HR Admin visits the Everywin sign-up page and enters: company name, industry, company size range, "
             "contact name, work email, phone number, and password. Email verification is required before access is granted."),
            ("Step 2 · Company Profile",
             "After verifying their email, the HR Admin completes the company profile: registered address (country, "
             "state/province), logo upload, company description, and default timezone. This data is used for "
             "compliance reporting and ad targeting."),
            ("Step 3 · Organisation Structure",
             "HR Admin creates departments (e.g. Sales, Operations, Finance, Marketing, HR). At least one department "
             "is required before staff can be added. Departments can be added, renamed, and deactivated at any time."),
            ("Step 4 · Leave & Policy Defaults",
             "The system pre-loads statutory leave defaults appropriate to the organisation's country. HR Admin "
             "reviews and adjusts entitlements per employment type and sets leave accrual rules in line with local law."),
            ("Step 5 · Payroll Configuration",
             "HR Admin sets payroll frequencies (monthly for full staff and contractors; weekly for "
             "onsite/labourers). Local statutory tax and deduction schedules are pre-configured per the selected "
             "jurisdiction. HR Admin reviews and adjusts income tax rates, pension/provident fund rates, housing "
             "fund eligibility, and withholding tax rates."),
            ("Step 6 · Anchor Connection",
             "HR Admin connects the company's Anchor account by entering API credentials and designating the "
             "funding account. The system validates the connection by performing a test lookup. Disbursement "
             "schedule and approval rules are set."),
        ]),
        Spacer(1,8),
        Paragraph("Phase 2 — Staff Population", H2),
        field_rows([
            ("Option A — Manual Add",
             "HR Admin adds staff individually from the 'Employees' section. Required fields: full name, work email, "
             "department, employment type (Full Staff / Contractor / Onsite), job title, base salary, employment "
             "start date, and line manager. The system creates a user account and sends a login invitation email automatically."),
            ("Option B — Bio Data Link",
             "HR Admin generates a tokenised bio-data collection link and sends it to each new hire. The staff "
             "member completes the form (personal details, guarantor details, bank account, government ID) from "
             "any device. HR reviews and approves each submitted section."),
            ("Option C — Bulk Import",
             "HR Admin uploads a CSV of staff records matching the Everywin template. The system validates each "
             "row and flags any errors before committing the import. Invitation emails are sent in bulk on "
             "successful import."),
            ("Staff Account Activation",
             "Every new staff member receives an email with their login credentials. On first login, they are "
             "prompted to: set a new password, review their profile, complete any outstanding bio-data, and "
             "review the company's onboarding checklist (if configured by HR)."),
            ("Guarantor Collection",
             "For each new hire, HR generates a tokenised guarantor link. Guarantors submit their details and "
             "supporting documents without creating a platform account. HR reviews and approves or rejects each "
             "guarantor submission independently."),
        ]),
        Spacer(1,8),
        Paragraph("Phase 3 — First Payroll Run", H2),
        field_rows([
            ("Salary Verification",
             "HR Admin reviews the salary attached to each staff member's profile before the first run. Any discrepancies are corrected from the staff profile screen."),
            ("Bank Account Verification",
             "Each staff member's bank details (bank name, account number) must be entered and verified via "
             "Anchor's account name lookup before they can receive a disbursement. Staff can enter their own "
             "details via their profile; HR can also enter them directly."),
            ("Draft Payroll Review",
             "HR Admin triggers the first payroll run. The system generates a full draft showing each staff "
             "member's gross pay, all statutory deductions, and net pay. HR reviews the draft before approving."),
            ("Approval & Disbursement",
             "HR Admin approves the payroll run. If a two-person authorisation rule was configured, a second "
             "Admin must also approve. On final approval, Anchor disburses net salaries to all staff bank accounts automatically."),
            ("Staff Notification",
             "Each staff member receives an in-app and optional email notification confirming their salary has "
             "been disbursed, including the amount and their registered bank account."),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — RBAC
# ═══════════════════════════════════════════════════════════════════════════════

def sec4():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("4 · Role-Based Access Control (RBAC)", [
        Paragraph(
            "Everywin enforces a strict three-tier RBAC model. Access is enforced at the API and database level "
            "— never UI-only. Role assignments are logged in the audit trail. A user can hold multiple roles "
            "(e.g. a line manager who is also an HR Admin), but each role's permissions are additive.",
            BODY),
        Spacer(1,6),
        Paragraph("Permission Matrix", H2),
        perm_table([
            ("View all staff profiles",          "✓ Yes", "✗ No",      "✗ No"),
            ("View own profile",                  "✓ Yes", "✓ Yes",    "Read-only"),
            ("Add / edit staff records",          "✓ Yes", "✗ No",      "✗ No"),
            ("View all performance scores",       "✓ Yes", "Team only", "✗ No"),
            ("View own performance score",        "✓ Yes", "✓ Yes",    "✓ Yes"),
            ("Set / edit staff goals",            "✓ Yes", "Team only", "✗ No"),
            ("Enter manager review scores",       "✓ Yes", "Team only", "✗ No"),
            ("Configure & run payroll",           "✓ Yes", "✗ No",      "✗ No"),
            ("View own payslips",                 "✓ Yes", "✓ Yes",    "✓ Yes"),
            ("View HR-level payroll reports",     "✓ Yes", "✗ No",      "✗ No"),
            ("Submit leave requests",             "✓ Yes", "✓ Yes",    "✓ Yes"),
            ("Approve leave requests",            "✓ Yes", "Team only", "✗ No"),
            ("Submit grievances",                 "✓ Yes", "✓ Yes",    "✓ Yes"),
            ("Manage contracts",                  "✓ Yes", "✗ No",      "View only (if granted)"),
            ("Manage disciplinary records",       "✓ Yes", "Flag for own team", "View own flags"),
            ("Access audit logs",                 "✓ Yes", "✗ No",      "✗ No"),
            ("Send / receive direct messages",    "✓ Yes", "✓ Yes",    "✓ Yes"),
            ("Create group chats",                "✓ Yes", "✓ Yes",    "✓ Yes"),
            ("View all org group chats",          "✓ Yes", "✗ No",      "✗ No"),
            ("View team group chats",             "✓ Yes", "Team only", "✗ No"),
            ("Moderate / delete any message",     "✓ Yes", "✗ No",      "✗ No"),
            ("Manage Ads Account",                "✓ Yes", "✗ No",      "✗ No"),
            ("Access system users panel",         "✓ Yes", "✗ No",      "✗ No"),
            ("Configure Anchor / payroll settings","✓ Yes","✗ No",      "✗ No"),
            ("View HR analytics reports",         "✓ Yes", "✗ No",      "✗ No"),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# PART A — STAFF PORTAL (abbreviated field tables)
# ═══════════════════════════════════════════════════════════════════════════════

def part_a():
    elems = []
    elems.append(part_divider("PART A", "STAFF PORTAL", "Self-service access for every team member"))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(
        "The Staff Portal is the self-service face of Everywin. Every employee — whether full-time, contractor, "
        "or onsite labourer — has a dedicated view showing exactly what they need without requiring HR intervention "
        "for routine queries. The portal is designed mobile-first and accessible from any device.",
        BODY))
    elems.append(Spacer(1,8))

    # A.1
    elems.append(Paragraph("A.1 — Staff Dashboard", H2))
    elems.append(Paragraph("The dashboard is the staff member's home screen. It surfaces their most important real-time data at a glance, reducing the need to navigate deep into sub-sections for routine checks.", BODY))
    elems.append(Paragraph("Dashboard Widgets", H3))
    elems.append(field_rows([
        ("Performance Score Card", "Live composite performance score (0–100) with colour coding: 80–100 Elite (green), 60–79 Stable (amber), below 60 Needs Improvement (red). Shows rank within department if applicable."),
        ("Leave Balance Summary",  "Remaining annual leave days, sick leave days, and any other leave types configured for the org. Tappable — links directly to the Leave section."),
        ("Attendance Check-In Widget", "One-tap check-in and check-out. Displays current attendance status (Present, On Leave, Absent). Shows today's check-in time after clocking in."),
        ("Pending Tasks Counter",  "Count of open tasks assigned to the staff member with a direct link to the Task Manager."),
        ("Upcoming Shifts",        "Next scheduled shift(s) for the week pulled from the shift schedule."),
        ("Latest Announcements",   "The two or three most recent company or department announcements, with a link to read more."),
        ("Pending Peer Reviews",   "Badge count of peer review requests awaiting the staff member's response."),
        ("Salary Disbursement Status", "Most recent payslip status: 'Salary of ■X disbursed on [date]' or 'Payroll for [month] pending'. Links to My Payroll."),
        ("Ads Banner (Dashboard)", "Ad unit served at the top of the dashboard. Maximum 3 unique ads per user per day. Marked as 'Sponsored'. Staff can hide or report any ad."),
    ]))

    # A.2
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.2 — My Profile & Bio Data", H2))
    elems.append(Paragraph("Profile Sections", H3))
    elems.append(field_rows([
        ("Personal Information",   "Full name, date of birth, gender, marital status, phone number, home address, state/province of origin, nationality, religion (optional). Staff can edit: phone, home address, next-of-kin details, emergency contact."),
        ("Employment Details",     "Start date, employment type, department, job title, line manager, base salary (visible but not editable by staff). Changes to sensitive fields go through an HR Request."),
        ("Bank Account Details",   "Bank name and account number linked for payroll disbursement. Staff can add or update their bank account. Changes require HR review before taking effect on the next payroll run."),
        ("Identification",         "Local tax identification number and bank/identity verification number — visible to staff, not self-editable. Changes via HR Request only."),
        ("CV & Qualifications",    "Educational history, certifications, and skills. Staff can add and update their own qualification records."),
        ("Documents",              "Staff can view documents shared with them by HR (e.g. signed contract, offer letter). Upload personal documents where HR has enabled this."),
        ("System Notes",           "HR-internal notes on the staff member. Not visible to the staff member."),
    ]))
    elems.append(Paragraph("Bio Data Collection Form", H3))
    elems.append(Paragraph(
        "HR sends each staff member a tokenised link to complete their bio-data form. The form is organised into "
        "three sections: Employee Details (personal and employment information), Guarantor 1, and Guarantor 2. "
        "Each section is submitted independently and reviewed by HR. Staff see the submission status of each "
        "section (Pending, Under Review, Approved, Returned for Correction) in their My Bio Data screen.", BODY))

    # A.3
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.3 — Attendance & Timesheets", H2))
    elems.append(field_rows([
        ("Check-In / Check-Out",  "One-tap check-in and check-out from the staff portal. The system records timestamp, IP address, and device type. Optional GPS capture for organisations using geofencing. Late arrivals are automatically flagged."),
        ("Attendance History",    "Staff can view their own attendance record for any date range: Present, Late, On Leave, Absent. Shows check-in and check-out times per day."),
        ("Timesheet Entry",       "Staff log daily or weekly work hours against tasks or projects. Timesheets are submitted to their line manager for approval. Status tracking: Draft, Submitted, Approved, Rejected."),
        ("Timesheet History",     "Full history of all submitted timesheets with approval status and any rejection notes from the manager."),
        ("Calendar View",         "Staff see their own calendar overlaid with attendance records, approved leave, scheduled shifts, and company-wide events."),
    ]))

    # A.4
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.4 — Leave Management", H2))
    elems.append(field_rows([
        ("Submit Leave Request",  "Staff select leave type (Annual, Sick, Study, Maternity, Paternity, Compassionate), start date, end date, and reason. The system auto-calculates working days, checks remaining balance, and flags any overlap with approved leave or public holidays before submission."),
        ("Leave Request Status",  "Real-time status of all leave requests: Pending, Approved, Rejected, Cancelled. Rejection includes the reason from the approving manager or HR."),
        ("Leave Balances",        "Real-time view of entitlement, days taken, and days remaining per leave type. Updated instantly when a leave request is approved."),
        ("Leave Policies",        "Read-only view of the organisation's configured leave policies: entitlement per type, accrual method, carry-over rules."),
        ("Leave Accrual",         "Monthly accrual credits are shown per leave type. Staff can see how their balance has accumulated month-by-month."),
        ("Public Holidays",       "Statutory public holidays for the organisation's country are pre-loaded and excluded from leave day counts. Staff can view the holiday calendar for the year."),
    ]))

    # A.5
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.5 — Performance & Goals", H2))
    elems.append(Paragraph("Staff have full transparency into how they are measured. The performance section surfaces their composite score, the breakdown behind it, their goals progress, and their trajectory over time.", BODY))
    elems.append(field_rows([
        ("Composite Score",        "Live composite performance score (0–100) broken into three pillars: KPI Goals Achievement (40%), Work Quality (20%), Manager Review (40%). Each pillar score is visible alongside the composite."),
        ("6-Month Trend Chart",    "A line chart showing the staff member's composite score over the past six months. Identifies trajectory: improving, stable, or declining."),
        ("Goals & OKRs",           "All goals set for the current period are listed with: the target, the current actual, the percentage achieved, and the deadline. Goals are role-specific and set by HR or the manager."),
        ("Manager Review Score",   "The manager's submitted review score for the current period is visible. Staff can see the total score but not individual sub-category notes (which remain HR-visible only)."),
        ("360° Peer Reviews",      "Staff can see peer review assignments: who they are asked to review, and the deadline. After submission, they can see anonymised aggregated feedback they have received. Individual reviewer identities are not revealed."),
        ("Improvement Plans (PIPs)","If a PIP has been initiated, the staff member can see: the concern area, improvement targets, milestones, support offered, and current status. PIPs are read-only for staff."),
        ("Skills Matrix",          "Staff can view their own skill ratings across the competencies defined for their role. Updated by their manager after review cycles."),
    ]))

    # A.6
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.6 — Learning & Growth", H2))
    elems.append(field_rows([
        ("Training Programmes",   "Staff see all training programmes assigned to them: title, format (internal, external, online), associated documents, and completion status. Staff mark individual modules complete."),
        ("Compliance Training",   "A dedicated tab for mandatory training (data protection, workplace safety, anti-bribery). Shows completion deadlines and overdue alerts."),
        ("Onboarding Checklist",  "New hires see their onboarding checklist on first login: document submission, IT setup, induction sessions, policy acknowledgements. Each item shows the responsible party, deadline, and completion status."),
        ("Probation Status",      "New hires on probation can see their probation start and end dates, remaining days, and current status (Active, Completed, Extended, Terminated)."),
        ("Internal Job Board",    "Staff can browse all internally posted open roles and submit applications. Application status is tracked: Submitted, Under Review, Shortlisted, Rejected, Hired."),
    ]))

    # A.7
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.7 — My Payroll & Bonuses", H2))
    elems.append(Paragraph("The payroll section gives staff complete visibility into their compensation without needing to contact HR. Every payslip is downloadable as a PDF and shows the full statutory deduction summary.", BODY))
    elems.append(field_rows([
        ("Payslip List",           "All payroll periods listed in reverse chronological order. Each entry shows: period, gross pay, total deductions, net pay, disbursement status (Pending / Disbursed), and Anchor reference number."),
        ("Payslip Detail",         "Full payslip breakdown: gross earnings, all deductions itemised (income tax, pension/provident fund, housing levy, withholding tax where applicable), total deductions, net payout, annual taxable income used in tax computation, relief allowance applied, and disbursement status."),
        ("Payslip Download",       "Each payslip is downloadable as a PDF from the payslip detail view."),
        ("Salary Disbursement Notification", "Staff receive an in-app notification when their salary is disbursed: 'Your salary of ■[amount] for [month] has been disbursed to your [Bank] account ending [last 4 digits].'"),
        ("My Bonuses",             "All logged bonuses and commissions: type (Performance, Annual, Spot Award, Commission), amount, period, and disbursement status. Shows whether each bonus has been disbursed via Anchor."),
        ("Expense Claims",         "Staff can submit expense claims: amount, category, description, and receipt upload. Status tracking: Submitted, Under Review, Approved, Rejected, Disbursed."),
        ("Benefits Summary",       "Staff can view their configured benefits package: health insurance plan and provider, vehicle allowance, data allowance, and any other benefits logged by HR."),
    ]))

    # A.8
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.8 — Engagement, Culture & Messaging", H2))
    elems.append(field_rows([
        ("Announcements",          "Company-wide and department-specific announcements from HR. Normal, Important, and Urgent priority levels. Pinned announcements stay at the top of the feed. Native ad posts are interspersed (max 1 per 5 organic posts), clearly labelled 'Sponsored'."),
        ("Recognition Wall (Kudos)","Any staff member can recognise a colleague publicly with a message and category (Teamwork, Innovation, Client Excellence, Going Above & Beyond). Posts appear on the company wall visible to all staff."),
        ("Surveys",                "HR-published pulse surveys and eNPS. Staff complete surveys directly from their portal. Anonymous surveys are flagged — staff are reminded their identity will not be linked to their response."),
        ("Remote Work Log",        "Staff log and track their remote work days. Can see their weekly usage against any manager-configured maximum."),
        ("Policy Library",         "Read-only access to all company policies uploaded by HR. Staff acknowledge each policy individually — HR tracks acknowledgement status."),
        ("Direct Messages (DMs)",  "Staff can start a private one-on-one conversation with any other platform user. Supported: text, images, videos, documents, voice notes, emoji reactions. Notification badge shows unread count."),
        ("Group Chats",            "Staff can create group chats and add multiple members. Can see only groups they are a member of. Supported: group name, group avatar, pin important messages, mute notifications per group."),
        ("Message History & Search","Staff can search their own message history by keyword, sender, or date range."),
    ]))

    # A.9
    elems.append(Spacer(1,8))
    elems.append(Paragraph("A.9 — Documents, Requests & Compliance", H2))
    elems.append(field_rows([
        ("Documents Vault",        "Staff see documents explicitly shared with them by HR: signed contracts, offer letters, certificates, policy documents. Download available for shared documents."),
        ("HR Letters",             "View issued HR letters: offer letter, employment confirmation, salary review letter, promotion letter. Downloadable as PDF."),
        ("HR Requests",            "Staff raise operational HR requests: payslip reissue, reference letter, employment confirmation, address update, department transfer, role clarification. Status tracking: Open, In Progress, Resolved."),
        ("Grievances",             "A confidential channel for formal complaints. Default is anonymous — the link between submitter and submission is severed on save (cryptographic anonymisation). Named submissions are also supported. Status updates are visible to the staff member."),
        ("My Flags (Disciplinary)","Staff can view their own disciplinary record: incident date, severity level (D through A), and current status. They cannot see HR's internal notes."),
        ("My Guarantors",          "Staff can access the tokenised guarantor form link and track guarantor submission status (Pending, Submitted, Under Review, Approved, Returned)."),
        ("My Tasks",               "View all tasks assigned to the staff member. Mark tasks as complete. Overdue tasks are highlighted."),
        ("Contracts (Shared)",     "Employment contracts and other documents that HR has made visible to the staff member. Read-only. Private documents (e.g. disciplinary notices) are not shown."),
    ]))

    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# PART B — MANAGER PORTAL
# ═══════════════════════════════════════════════════════════════════════════════

def part_b():
    elems = []
    elems.append(part_divider("PART B", "MANAGER PORTAL", "Team-level visibility and management for line managers & team leads"))
    elems.append(Spacer(1,12))
    elems.append(Paragraph(
        "The Manager Portal gives line managers everything they need to run their team efficiently — attendance "
        "oversight, leave approvals, performance reviews, goal-setting, and incident management — without "
        "exposing organisation-wide HR data. Managers see their direct reports only, unless explicitly granted "
        "broader access by HR.", BODY))
    elems.append(Spacer(1,8))

    for title, rows in [
        ("B.1 — Team Dashboard", [
            ("Team Summary",                     "Direct reports headcount, active vs. on-leave today, absent today. One-line status for each direct report."),
            ("Average Team Performance Score",   "The team's average composite performance score for the current month, with trend vs. previous month."),
            ("Pending Leave Requests",           "Count of leave requests awaiting manager approval, with a quick-approve workflow directly from the dashboard."),
            ("Pending Timesheet Approvals",      "Count of timesheet submissions awaiting approval."),
            ("Active PIPs",                      "Count of active Performance Improvement Plans in the manager's team."),
            ("Team Attendance Today",            "Breakdown of today's attendance across the team: Present, Late, Absent, On Leave."),
            ("Upcoming Shifts",                  "The next 7 days of shifts for the manager's team in a compact calendar strip."),
            ("Messages Unread",                  "Unread DM count and group chat badges for the manager."),
            ("Dashboard Ad Banner",              "Ad unit served at top of screen. Manager-tier ads are targeted to managerial and decision-maker segments."),
        ]),
        ("B.2 — My Team", [
            ("Team Directory",                   "Full list of direct reports with: name, role, department, employment type, performance score, current status (Active, On Leave, Probation). Searchable and filterable."),
            ("Individual Staff Profile (Read)",  "Managers can view the profiles of their direct reports: bio-data, employment details, performance history, goals, leave history, and disciplinary flags. Cannot edit salary, tax details, or HR-internal notes."),
            ("Org Chart",                        "Company-wide org chart accessible to managers. Useful for understanding cross-team reporting lines and headcount context."),
        ]),
        ("B.3 — Time & Attendance", [
            ("Team Attendance Overview",         "Daily attendance status for all direct reports. Filter by date range, status (Present, Late, Absent, On Leave). Export as CSV."),
            ("Late Arrival Alerts",              "Automatic flag when any direct report arrives late. Manager sees the flagged records in the attendance view."),
            ("Timesheet Review Queue",           "All timesheets submitted by direct reports awaiting approval. Approve or reject individually or in bulk. Rejection requires a note."),
            ("Shift Scheduling",                 "Create, assign, and publish shift schedules for direct reports. Support for rotating, fixed, day/night patterns. Published shifts appear in staff calendars immediately."),
            ("Team Calendar",                    "Shared calendar view for the manager's team: attendance records, approved leave, shifts, public holidays, and HR events."),
            ("Holiday Calendar",                 "View the annual public holiday calendar. Public holidays are automatically excluded from leave calculations."),
        ]),
        ("B.4 — Leave Approvals", [
            ("Leave Request Inbox",              "All pending leave requests from direct reports. Each request shows: staff name, leave type, date range, working days requested, remaining balance, and reason."),
            ("Approve / Reject with Note",       "Manager approves or rejects. Rejection requires a reason which is communicated to the staff member."),
            ("Team Leave Calendar",              "A calendar view showing all approved leave across the manager's team. Helps identify resource conflicts before approving new requests."),
            ("Leave Balances (Team)",            "View remaining leave balances for all direct reports across all leave types."),
            ("Leave Policies (Read)",            "Read-only access to the organisation's leave policies to ensure approval decisions are compliant."),
        ]),
        ("B.5 — Performance Management", [
            ("Team Performance Scorecard",       "Overview of all direct reports' current composite scores, colour-coded. Sortable by score, name, or department. Highlights staff below 60 who may need a PIP."),
            ("Manager Review Submission",        "For each direct report, the manager enters scores across defined review dimensions. The system weights the input and factors it into the composite score. Review periods are set by HR."),
            ("Goals & OKRs — Set & Adjust",      "Managers set monthly or quarterly goals per direct report, selecting the appropriate KPI template for their role. Actuals are auto-populated at period end from source data. Managers can adjust targets mid-period with a reason logged."),
            ("Performance Improvement Plans",    "Managers initiate PIPs for direct reports scoring below the threshold. Each PIP captures: concern area, improvement targets, support offered, review milestones, and expected outcome. HR is notified when a PIP is initiated."),
            ("360° Peer Reviews",                "Managers can initiate peer review cycles for their direct reports. Assign reviewers, set deadlines. See full reviewer breakdown. Participate in peer reviews themselves as a reviewer."),
            ("Skills Matrix Updates",            "Managers update skill ratings for direct reports after review cycles. The matrix maps each staff member against the competency framework for their role."),
            ("Succession Planning",              "Managers nominate direct reports as successors for key roles. Each nomination captures: target role, nominated staff, readiness rating, and estimated readiness timeline."),
        ]),
        ("B.6 — Disciplinary & Incident Logging", [
            ("Log Incident",                     "Managers can log disciplinary incidents for direct reports with: date, description, severity level (D–A), and supporting evidence. Incidents are stored against the staff record."),
            ("Severity Levels",                  "Grade D: Verbal counselling (noted on record). Grade C: Formal written warning. Grade B: Written warning + PIP initiation triggered. Grade A: Formal disciplinary action — HR is immediately notified."),
            ("Incident History",                 "View all incidents logged for each direct report. Accumulated incidents trigger automatic alerts to HR."),
            ("HR Escalation",                    "Grade A incidents auto-notify HR Admin. Managers cannot close Grade A incidents without HR sign-off."),
        ]),
        ("B.7 — Succession Planning & Skills Matrix", [
            ("Succession Nominations",           "Managers can nominate direct reports as potential successors for any role designated as critical by HR. Each nomination records: target role, nominee, readiness rating (1–4), estimated readiness timeline, and development notes."),
            ("Skills Matrix View",               "Managers see the skills matrix for their entire team — all staff mapped against the role competency framework. Cells are rated Novice / Developing / Proficient / Expert. Managers update ratings after each review cycle."),
            ("Skill Gap Identification",         "The matrix view highlights gaps: cells below 'Proficient' are flagged. Managers use this to identify training needs and inform succession decisions."),
        ]),
        ("B.8 — Messaging & Engagement", [
            ("Direct Messages",                  "All DM capabilities as described in the Staff Portal. Managers can message any platform user."),
            ("Group Chats",                      "Managers can see all group chats that include any member of their direct team — not just groups they personally belong to."),
            ("Message Search",                   "Managers can search within their team's conversations. Search scope: all chats involving any of their direct reports."),
            ("Announcements",                    "Read and receive company-wide and department announcements. Cannot publish announcements (HR-only capability)."),
            ("Recognition",                      "Give kudos to team members and across the organisation. See team recognition posts on the company wall."),
            ("Surveys",                          "Respond to HR-published surveys. See team survey completion rates (not individual responses) if HR grants this visibility."),
            ("Policy Library",                   "Read and acknowledge company policies. Same access as staff."),
        ]),
        ("B.9 — Task Management", [
            ("Task Assignment",                  "Managers can create tasks and assign them to direct reports: title, description, due date, priority (Low, Medium, High, Critical), and attached files."),
            ("Task Tracking",                    "View all tasks assigned to the team with status (Pending, In Progress, Completed, Overdue). Filter by assignee, status, and due date."),
            ("Task Completion",                  "When a staff member marks a task complete, the manager receives a notification. Managers can re-open tasks if the completion is insufficient."),
            ("Personal Tasks",                   "Managers also have access to their own task list and the same self-service features as staff members for their personal portal view."),
        ]),
    ]:
        elems.append(Paragraph(title, H2))
        elems.append(field_rows(rows))
        elems.append(Spacer(1,6))

    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# PART C — HR ADMIN PORTAL
# ═══════════════════════════════════════════════════════════════════════════════

def part_c():
    elems = []
    elems.append(part_divider("PART C", "HR ADMIN PORTAL", "Full platform control — organisation-wide visibility and configuration"))
    elems.append(Spacer(1,12))
    elems.append(Paragraph(
        "The HR Admin Portal is the operating system for the HR team. It provides full visibility across every "
        "staff member, every payroll run, every compliance record, and every platform action. HR Admins are "
        "the only users who can configure the platform, run payroll, access audit logs, and manage system users. "
        "Every action taken by an HR Admin is logged immutably in the audit trail.", BODY))
    elems.append(Spacer(1,8))

    for title, rows in [
        ("C.1 — HR Overview Dashboard", [
            ("Organisation Headcount",    "Total active staff by employment type (Full Staff, Contractors, Onsite). Active vs. inactive count. New hires this month."),
            ("Payroll Status",            "Current payroll run status: Not Started, Draft, Under Review, Approved, Disbursed. Quick-access to the payroll module. Last disbursement amount and date."),
            ("Compliance Alerts",         "Outstanding statutory reminders: income tax filing due, pension remittance due, any failed disbursements requiring retry."),
            ("Leave Overview",            "Staff currently on approved leave. Pending leave requests awaiting action. Absenteeism rate for the current period."),
            ("Performance Snapshot",      "Organisation-wide average performance score. Count of staff below 60 (flagged for PIP consideration). Active PIPs count."),
            ("Attendance Summary",        "Today's attendance: Present, Late, Absent, On Leave counts across the full organisation."),
            ("Recent Activity Feed",      "The five most recent significant actions in the platform: payroll runs, new staff additions, contract signings, grievance submissions, audit-relevant changes."),
            ("Quick Actions",             "One-click shortcuts: Run Payroll, Add Staff, Create Announcement, Generate Report, View Audit Log."),
            ("Dashboard Ad Banner",       "Ad unit for HR tier — restricted to financial services, HR tools, and compliance product categories."),
        ]),
        ("C.2 — Recruitment — ATS & Talent Pool", [
            ("Job Listings",              "Create job listings: title, department, salary band, responsibilities, requirements. Mark as internal-only or external. Published listings are visible on the Internal Job Board."),
            ("Job Requisitions",          "Review and approve department manager headcount requests. Each requisition shows: role, justification, proposed salary, target start date, and requester."),
            ("Application Tracker",       "Centralised view of all applications across all open roles. Filter by role, status, date, and source. Each record shows: applicant name, contact, resume, cover letter, role applied for, pipeline stage."),
            ("ATS Pipeline",              "Kanban-style candidate pipeline: Applied → Screening → Interview Scheduled → Interview Complete → Offer → Hired / Rejected. Drag-and-drop stage progression."),
            ("Interview Scheduler",       "Book, reschedule, and log interviews. Capture: date, interviewer(s), format, notes, and post-interview scores. Scheduling conflicts are flagged."),
            ("Offers Manager",            "Generate and track offer letters: salary, start date, role, department, offer expiry. Status: Sent, Accepted, Declined, Expired. Accepted offers trigger automatic staff account creation."),
            ("Talent Pool",               "Strong candidates not hired for the current role. Tag by skill, filter by skill set, add private notes. Candidate records retained indefinitely unless archived by HR."),
            ("Talent Pool — Candidate Chat","HR initiates real-time chat with Talent Pool candidates. Candidate receives a secure tokenised link — no account creation needed. Supports: text, file attachments, images."),
            ("Talent Pool — Bulk Email",  "Compose and send personalised emails to individual or bulk-selected candidates. Supports rich-text, templates with variable substitution. Delivery tracking: Sent, Delivered, Opened, Bounced."),
        ]),
        ("C.3 — People & Organisation", [
            ("Employee Directory",        "Full searchable, filterable registry of all active and archived staff. HR sees complete profile data. Can filter by department, employment type, status, and role."),
            ("Add Staff (Manual)",        "Create a new staff record: full name, work email, department, employment type, job title, base salary, start date, line manager. System creates a user account and sends a login invitation email."),
            ("Staff Profile Management",  "HR can view and edit all fields in any staff profile: personal bio-data, employment details, salary, tax identification, bank verification number, bank account details, qualifications, documents, and HR-internal notes."),
            ("Employment Types",          "Three classifications with distinct payroll rules: Full Staff (monthly, full benefits), Contractors (monthly, withholding tax applied), Onsite/Labourers (weekly, simplified payroll)."),
            ("Bio Data Collection",       "Generate and send tokenised bio-data collection links. Review and approve submitted sections (Employee Details, Guarantor 1, Guarantor 2). Return with correction requests if needed."),
            ("Guarantor Management",      "Review and approve or reject guarantor submissions. Each guarantor section reviewed independently. Approved submissions stored against the staff profile."),
            ("Staff Archiving",           "On exit, staff profiles are set to Inactive with exit date and reason. Records are retained for the minimum statutory period (never hard-deleted). Archived profiles are searchable and accessible to HR."),
            ("Org Chart",                 "Auto-generated from reporting lines in staff profiles. View the full hierarchy from CEO/MD downward. Supports search, expand/collapse. Updates in real time when reporting lines change."),
            ("Departments",               "Create, rename, deactivate departments. Each department shows headcount, active staff, and associated roles."),
            ("Diversity & Inclusion Dashboard","Workforce composition by gender, age group, department, and employment type. Aggregates only — no PII surfaced."),
        ]),
        ("C.4 — Time, Attendance & Shifts", [
            ("Organisation-Wide Attendance","Full attendance view for all staff across all departments. Filterable by department, date range, and status. Suspicious log flags (multiple check-ins from different locations) highlighted for review."),
            ("Geofencing Configuration",  "HR can define geofencing zones. Staff check-ins outside the defined radius are automatically flagged. Geofencing can be applied globally or per department."),
            ("Timesheet Approval Centre", "Consolidated view of all timesheet submissions across the organisation awaiting action. Approve or reject in bulk or individually. Rejection requires a note."),
            ("Shift Scheduling",          "Create and publish shifts for any department or team. Supports rotating, fixed, and day/night patterns. Shifts are visible to staff in their calendars immediately on publication."),
            ("HR Calendar",               "Organisation-wide calendar: attendance, approved leave, shifts, public holidays, and HR events (review cycles, payroll run dates). HR can add organisation-wide events."),
            ("Holiday Manager",           "Configure the annual public holiday calendar. Statutory holidays are pre-loaded per the organisation's country. HR can add, edit, or remove holidays. Holidays are automatically excluded from leave day calculations."),
        ]),
        ("C.5 — Leave Administration", [
            ("All Leave Requests",        "Organisation-wide view of all leave requests across all staff and departments. HR can approve or reject any request, overriding the manager's decision where required."),
            ("Leave Balances (All Staff)","Real-time view of every staff member's leave balance across all leave types. Filterable by department and employment type."),
            ("Leave Policies",            "Define and update leave policies per employment type: annual entitlement, accrual method, carry-over rules, blackout periods. Policy changes take effect from the next accrual cycle."),
            ("Leave Accrual Configuration","Define accrual rate (e.g. 1.6 days per month for annual leave). System updates balances automatically each month. HR can view the accrual run log."),
            ("Absenteeism Report",        "All unplanned absences (days with no approved leave and no attendance record) across any date range. Excludes weekends and public holidays. Exportable as CSV or PDF."),
            ("Global Absence Log",        "Chronological log of all absence records organisation-wide. Filter by staff member, department, date range, and status."),
        ]),
        ("C.6 — Performance Administration", [
            ("Organisation Performance Dashboard","Score distribution across the organisation: Elite (80–100), Stable (60–79), Needs Improvement (<60). Department-level breakdown. Count of staff on active PIPs."),
            ("Individual Performance Management","HR can view and manage any staff member's performance record: composite score, pillar breakdown, goals, manager reviews, trend chart, PIPs, peer review results, and skills matrix."),
            ("Goals & OKRs Administration","Set, edit, and view goals for any staff member. Assign role-appropriate KPI templates. Review actuals at period end. Mass-assign goals to a department or team."),
            ("Improvement Plans",         "Initiate PIPs for any staff member. Monitor milestone progress. Log outcomes (Completed, Extended, Escalated). PIPs are linked to disciplinary records where Grade B or A incidents are present."),
            ("360° Peer Reviews — Admin", "Create and manage review cycles: select reviewees, assign reviewers, set deadlines. View full results (individual reviewer breakdown) unlike managers and staff who see only aggregated data."),
            ("Skills Matrix Administration","Define and update the competency framework per role. View and update skill ratings for any staff member. Export the organisation-wide skills matrix as a report."),
            ("Succession Planning",       "Designate key roles as critical. View all succession nominations across the organisation. Dashboard shows coverage gaps: critical roles with no nominated successor."),
        ]),
        ("C.7 — Learning, Onboarding & Probation", [
            ("Training Hub",              "Create training programmes: title, description, format, documents, assigned staff. Track completion rates per programme and per staff member. Compliance training tab for mandatory programmes with deadlines and overdue alerts."),
            ("Onboarding Checklists",     "Create onboarding checklists for new hires: document submission, IT setup, induction sessions, policy acknowledgements. Assign responsible parties and deadlines. Monitor completion status across all active onboarding cohorts."),
            ("Probation Tracker",         "All staff on probation: start date, end date, remaining days, line manager, current review outcome. HR logs confirmation, extension, or termination decisions. Each decision is recorded against the staff profile."),
        ]),
        ("C.8 — Compensation, Payroll & Anchor Disbursement", [
            ("Payroll Run — Trigger",     "HR Admin triggers a payroll run for the current period. The system fetches all active staff, their base salaries, approved bonuses, approved commissions, and approved expense reimbursements. The statutory compliance engine computes all deductions per the applicable jurisdiction."),
            ("Draft Review",              "HR sees the full draft payroll: total headcount processed, total gross, total income tax, total pension/provident fund, total housing levy, total withholding tax, total net, and total disbursement amount. HR can drill into any individual payslip, edit values, add notes, or remove specific staff from the run."),
            ("Payroll Approval",          "HR Admin approves the payroll run. If a two-person authorisation rule is configured, a second HR Admin must also approve. Approval is logged with the approver's identity, IP address, and timestamp."),
            ("Anchor Disbursement — Automated","On approval, the system instructs Anchor to initiate individual bank transfers for each staff member. Each transfer includes a reference string ('Salary – [Name] – [Month]'). Transfers are executed individually and logged in real time."),
            ("Failed Disbursement Handling","Failed transfers are flagged in the HR dashboard within 60 seconds with the failure reason (invalid account number, insufficient funds, Anchor API error). HR can update bank details and retry failed transfers individually or in bulk without reprocessing the full run."),
            ("Payroll Runs History",      "All previous payroll runs grouped by period. Each entry shows: headcount, gross total, deduction breakdown, net total. Drill down to individual payslips per run. Full disbursement log per run."),
            ("Disbursement Log",          "Complete audit trail of every disbursement: staff name, amount, Anchor reference number, timestamp, status (Pending, Processing, Successful, Failed), and failure reason where applicable. Downloadable as CSV or PDF."),
            ("Tax Configuration",         "Configure all applicable statutory rates for each jurisdiction: progressive income tax bands, pension/provident fund (employee and employer rates), housing levy rate, withholding tax rate. Toggle social insurance and health insurance tracking on/off. All changes are logged with effective date."),
            ("Compensation Bands",        "Define salary bands per role and department (minimum and maximum). System flags any staff whose salary falls outside their role's defined band. Used for offer benchmarking and merit increase planning."),
            ("Bonuses & Incentives",      "Log bonuses per staff member: Performance, Annual, Spot Award, Commission. Each entry: staff, type, amount, period, notes. Approved bonuses are included in the next payroll run and disbursed via Anchor automatically."),
            ("Benefits Administration",   "Record the benefits package per employment type and per individual: health insurance plan, provider, vehicle allowance, data allowance. Staff see their own benefits in their portal."),
            ("Expenses Management",       "Review and approve or reject expense claims from staff and managers. Approved claims can be processed alongside the next payroll run or as a standalone Anchor disbursement."),
            ("Sales Commission Tracking", "Configure commission rates per staff or per role. Track commissionable events (deals closed, payments collected). Review, adjust, and approve commission payouts. Disbursed via Anchor."),
        ]),
        ("C.9 — Engagement, Surveys & Culture", [
            ("Announcements — Publish",   "Create and publish company-wide or department-specific announcements: title, body, priority (Normal, Important, Urgent), target audience. Announcements can be pinned. Supports scheduled publishing."),
            ("Recognition Wall — Moderation","HR can feature, pin, or remove any recognition post. Full moderation access to the company wall."),
            ("Surveys — Create & Analyse","Create eNPS surveys and custom pulse surveys (rating scales, multiple choice, open text). Set anonymity mode. Publish to all staff or targeted departments. View aggregated results: response rate, score breakdowns, open-text responses."),
            ("Remote Work Management",    "Organisation-wide view of remote work patterns. Configure maximum remote days per week per staff or per role. Flag exceptions."),
            ("Policy Library — Manage",   "Upload and publish company policies. Track which staff have read and acknowledged each policy. Send reminders to staff who have not acknowledged mandatory policies."),
            ("Internal Job Board — Manage","All internally posted roles. Manage internal applications through the ATS pipeline. Internal candidates are flagged for differentiated treatment."),
        ]),
        ("C.10 — Documents, Contracts & Compliance", [
            ("Documents Vault",           "Upload, categorise, and control access to all HR documents. Set visibility per staff member. HR sees all documents organisation-wide."),
            ("Contract Kitchen",          "Full contract lifecycle: create contracts from templates or scratch (Employment Contract, Offer Letter, NDA, Consultancy Agreement, Disciplinary Notice, Exit Settlement). Assign signatories, set visibility, invite legal collaborators. Track status: Draft → Review → Legal Signing → Executed → Voided. Download executed contracts as PDF."),
            ("HR Letters — Generate",     "Generate standard HR letters from built-in templates: Offer Letter, Employment Confirmation, Salary Review, Promotion, Warning, Termination. Auto-populated with staff details, editable before issuing."),
            ("Work Permits",              "Track work permit and visa status for non-citizen employees: permit type, issuing authority, issue and expiry dates, document upload. Alerts generated as expiry approaches."),
            ("HR Requests — Manage",      "Manage all staff-submitted HR requests. Assign to an HR team member, update status, and resolve. Search and filter by request type, status, and assignee."),
            ("Grievances — Manage",       "Full grievance management: view all submissions (anonymous and named), update status (Open → In Review → Resolved → Closed), add internal notes. Anonymous submissions have no submitter linkage at the database level."),
            ("Disciplinary Records",      "Log and manage incidents across four severity levels (D–A). View full disciplinary history per staff member and organisation-wide. Repeated incidents trigger automatic HR alerts. Grade A incidents require HR-level sign-off to close."),
            ("Asset Manager",             "Register and track all company assets: name, type, serial number, purchase date, value, current status, and assigned staff. Log assignment and recovery with timestamps. During offboarding, asset recovery checklist is auto-populated from assigned assets."),
        ]),
        ("C.11 — Administration, Reports & Audit", [
            ("HR Reports",                "Pre-built report library: Headcount by department and type, Payroll summary, Leave utilisation, Attendance rate, Performance score distribution, Disciplinary incidents, Recruitment funnel metrics, Bonus and commission totals, Attrition report. All filterable by date range. Downloadable as CSV or PDF."),
            ("Exit & Offboarding Manager","Initiate offboarding for a departing staff member: set exit date and reason, review and confirm asset recovery, deactivate the profile, trigger final payroll run if applicable. Archived profiles remain accessible for the minimum statutory retention period."),
            ("Exit Interviews",           "Conduct and log structured exit interviews after offboarding is initiated. Questions: reason for leaving, overall experience, improvement suggestions, likelihood to return, willingness to recommend. Responses aggregated into exit analytics."),
            ("System Users",              "Create new user accounts, assign roles (HR Admin, Manager, Staff), deactivate accounts, reset passwords. All role changes logged in the audit trail."),
            ("Audit Logs",                "Every action in the platform is logged: actor identity, module, action type (Create, Update, Delete, Approve, Reject), affected record, before/after values, IP address, timestamp. Read-only — cannot be modified or deleted."),
            ("Settings & Configuration",  "Company name and branding, org structure defaults, payroll frequency and schedule, Anchor disbursement settings and funding account, statutory tax configuration, leave policy defaults, notification preferences (in-app, email), theme (Light, Dark, Warm)."),
            ("Task Manager (HR)",         "HR Admins have their own task management view. Can create tasks and assign to any staff member, manager, or HR team member. Full task tracking across the organisation."),
        ]),
    ]:
        elems.append(Paragraph(title, H2))
        elems.append(field_rows(rows))
        elems.append(Spacer(1,6))

    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Payroll Disbursement Flow
# ═══════════════════════════════════════════════════════════════════════════════

def sec5():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("5 · Payroll Disbursement — Detailed Flow", [
        Paragraph(
            "The automated payroll disbursement flow via Anchor is the defining operational workflow of Everywin. "
            "It is fully automated once configured. Human checkpoints exist to prevent errors, not to slow the process. "
            "All steps are logged immutably.", BODY),
        Spacer(1,6),
        field_rows([
            ("Step 1 · Configuration (One-time)",
             "HR connects the company's Anchor account and funding account. Bank account details for each staff "
             "member are entered and verified via Anchor's account name lookup API. Payroll schedules are set per "
             "employment type (monthly for full staff and contractors; weekly for onsite/labourers). Disbursement "
             "approval rule configured: auto-disburse on approval, or require second HR authorisation."),
            ("Step 2 · Payroll Preparation",
             "On the configured schedule (or when HR triggers manually), the system generates a draft payroll run: "
             "fetches all active staff and their base salaries, applies approved bonuses, commissions, and expense "
             "reimbursements for the period. The statutory compliance engine computes income tax, pension/provident "
             "fund, housing levy, withholding tax, and net pay per staff member per the applicable jurisdiction. "
             "A draft payslip is generated for each."),
            ("Step 3 · HR Review",
             "HR sees the full payroll run: total headcount, total gross, deduction breakdown by type, total net, "
             "total disbursement amount. HR can drill into any individual payslip, edit values, add notes, add or "
             "remove specific staff. Editing is logged with the editor's identity."),
            ("Step 4 · Approval",
             "HR Admin approves the payroll run. If a two-person authorisation rule is configured, a second HR "
             "Admin must approve before disbursement proceeds. All approvals are logged with identity, IP address, and timestamp."),
            ("Step 5 · Anchor Disbursement (Automated)",
             "On approval, the system instructs Anchor to initiate individual bank transfers for each staff "
             "member's net pay from the company's Anchor funding account. Each transfer includes a reference "
             "string: 'Salary – [Name] – [Month/Week]'. All Anchor API calls are idempotent — duplicate transfer "
             "attempts are blocked automatically."),
            ("Step 6 · Staff Notification",
             "Each staff member receives an in-app notification (and optional email): 'Your salary of ■[amount] "
             "for [period] has been disbursed to your [Bank] account ending [last 4 digits].' Notification is "
             "triggered only on confirmed Successful status from Anchor."),
            ("Step 7 · Failed Disbursement Handling",
             "Any failed transfer is flagged in the HR dashboard within 60 seconds with the failure reason. HR "
             "can update the bank details if incorrect and retry failed transfers individually or in bulk, without "
             "reprocessing the full payroll run. No silent failures — all errors surface."),
            ("Step 8 · Reconciliation",
             "The disbursement log shows the Anchor reference number for every successful transfer. HR downloads "
             "the log as CSV or PDF for reconciliation against the company's bank statement. Log entries are immutable."),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Universal Messaging
# ═══════════════════════════════════════════════════════════════════════════════

def sec6():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("6 · Universal Messaging System", [
        Paragraph(
            "The Universal Messaging System is a full-featured, real-time communication layer embedded across "
            "all three portals. It eliminates the need for external messaging tools (WhatsApp, Telegram) for "
            "internal communication, keeping all workplace conversations within the platform where they are "
            "subject to HR oversight and data retention policies.", BODY),
        Spacer(1,6),
        field_rows([
            ("Direct Messages",            "Any user can start a one-on-one conversation with any other user. Real-time delivery. Persistent across sessions."),
            ("Supported Content Types",    "Plain text, images (JPG, PNG, GIF including animated), videos (MP4, configurable size limit), documents (PDF, DOCX, XLSX, common formats), voice notes (recorded in-browser/app), emoji reactions on any message."),
            ("Group Chats",                "Any user can create a group and add multiple members. Group features: name, optional avatar, add/remove members, group description, pin important messages, mute notifications per group."),
            ("Group Visibility by Role",   "HR Admin: all groups organisation-wide. Manager: all groups containing any direct report. Staff: only groups they are a member of."),
            ("Message Search",             "HR Admin: search all conversations org-wide. Manager: search within team conversations. Staff: search own threads only. Search by keyword, sender, or date range."),
            ("Message Status",             "Sent, Delivered, Read indicators on every message."),
            ("Notifications",              "In-platform notification badge. Optional email digest for offline messages. Notification preferences configurable per user."),
            ("Moderation",                 "HR Admins can view any thread for compliance. HR can delete any message or attachment. Moderation log records deletions with actor identity, message reference, and timestamp."),
            ("Privacy Disclosure",         "Platform policy (visible in Policy Library) discloses that internal communications are subject to HR oversight. Users are not notified in real time when HR reviews their messages."),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Statutory Compliance Engine (GLOBALISED)
# ═══════════════════════════════════════════════════════════════════════════════

def sec7():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("7 · Statutory Compliance Engine", [
        Paragraph(
            "The compliance engine computes all statutory employer and employee obligations automatically on "
            "every payroll run, per the jurisdiction configured for the organisation. Everywin ships with "
            "pre-built compliance packs for supported countries. New jurisdictions can be added via the tax "
            "configuration module. All computation changes are logged with an effective date — the system always "
            "applies the configuration that was active at the payroll run date.", BODY),
        Spacer(1,6),
        Paragraph("Standard Obligation Categories", H2),
        Paragraph(
            "The table below maps the universal obligation categories that Everywin models. The labels and "
            "rates shown reflect a reference implementation (e.g. Nigeria). Each organisation's HR Admin "
            "configures the applicable rates and authority names for their own jurisdiction via Settings.", BODY),
        Spacer(1,4),
        compliance_table([
            ("Income Tax (PAYE / WHT equivalent)",
             "National / State Revenue Authority",
             "Progressive bands or flat rate per jurisdiction",
             "Auto-computed with any applicable statutory relief allowance applied. Annual taxable income and monthly deduction shown on each payslip."),
            ("Pension / Provident Fund",
             "Pension Regulator (per country)",
             "Employee % + Employer % (configurable)",
             "Mandatory for applicable employment types. Configurable rates per organisation. Tracked per designated fund administrator."),
            ("Housing / Infrastructure Levy",
             "National Housing Authority (per country)",
             "% of basic salary (configurable)",
             "Applied to eligible staff based on configuration. Shown as a named deduction on payslip. Toggle on/off per org."),
            ("Withholding Tax",
             "Revenue Authority (per country)",
             "% on contractor payments (configurable)",
             "Auto-applied to contractors. Not applied to full staff by default. Rate configurable per organisation."),
            ("Health Insurance / HMO",
             "National Health Authority (per country)",
             "Per employee per benefits config",
             "Tracked per benefits configuration. Toggle on/off per org. Shown in benefits administration."),
            ("Social / Workplace Insurance",
             "Social Insurance Fund (per country)",
             "Workplace insurance contribution",
             "Included in compliance dashboard. Toggle on/off. Contribution logged per payroll run."),
        ]),
        Spacer(1,10),
        Paragraph("Income Tax Bands — Reference Implementation (configurable per org)", H2),
        Paragraph(
            "The bands below illustrate the progressive PAYE structure for a reference jurisdiction. "
            "All bands, rates, and relief allowances are fully configurable per organisation in the Tax Configuration module "
            "under C.8. The engine applies whichever rates are active at the time of each payroll run.",
            BODY),
        Spacer(1,4),
        tax_band_table([
            ("First threshold (e.g. first ₦300,000 or equivalent)", "Lowest rate (e.g. 7%)"),
            ("Second band",                                          "~11%"),
            ("Third band",                                           "~15%"),
            ("Fourth band",                                          "~19%"),
            ("Fifth band",                                           "~21%"),
            ("Above top threshold",                                  "Top rate (e.g. 24%)"),
        ]),
        Spacer(1,6),
        Paragraph(
            "A statutory Relief Allowance (equivalent to Consolidated Relief Allowance, or the local equivalent) "
            "is applied before computing taxable income. The engine displays the annual taxable income used, "
            "the relief applied, and the monthly income tax deducted on every payslip — giving staff and HR "
            "full transparency into the tax computation.", BODY),
        Spacer(1,8),
        Paragraph("Country Compliance Packs", H2),
        Paragraph(
            "Everywin ships with pre-configured compliance packs for supported markets. Each pack includes "
            "statutory income tax bands, pension/provident fund rates, applicable levies, and public holiday "
            "calendars. HR Admins select their country during onboarding and can customise rates within "
            "legal bounds. Additional country packs are added as Everywin expands into new markets.", BODY),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Non-Functional Requirements
# ═══════════════════════════════════════════════════════════════════════════════

def sec8():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("8 · Non-Functional Requirements", [
        field_rows([
            ("Performance",      "Dashboard pages load within 3 seconds. Performance scores refresh daily. Payroll draft generation completes within 30 seconds for up to 500 staff."),
            ("Security",         "Access enforced at API and database level — never UI-only. No staff member can access another staff member's data. No cross-tenant data access. All monetary data stored as fixed-precision decimal (never floating point)."),
            ("Data Integrity",   "All monetary values stored as Numeric(15,2). Soft deletes only — no hard deletions of staff, payroll, or compliance records. Foreign key integrity enforced at database level."),
            ("Auditability",     "Every change to staff profiles, goals, review scores, payroll, contracts, and system settings is logged with actor identity, timestamp, and before/after values. Audit logs are immutable."),
            ("Scalability",      "Must support up to 1,000 staff records per tenant across multiple departments and employment types without architectural changes."),
            ("Data Retention",   "Exited staff profiles and payroll records retained for the minimum statutory period per jurisdiction (minimum 5 years as a platform baseline). Audit logs retained indefinitely. Anonymous grievance submissions — submitter identity cryptographically severed on save."),
            ("Availability",     "Core payroll and disbursement workflows must maintain 99.9% uptime. Payroll runs must not be affected by UI downtime. Anchor disbursement runs as a background process isolated from UI service health."),
            ("Anchor Integration","All Anchor API calls must be idempotent. Failed transfers must never silently fail — all errors surface in the HR dashboard within 60 seconds. Retry logic with exponential backoff on transient failures."),
            ("Confidentiality",  "Anonymous grievances are cryptographically anonymised — no server-side linkage to the submitter. HR cannot re-identify anonymous submissions through any platform interface or admin tool."),
            ("Multi-Tenancy",    "All tenant data partitioned at database level using organisation_id. Row-level security enforced by the database engine. No shared mutable state between tenants."),
        ]),
    ])
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Glossary
# ═══════════════════════════════════════════════════════════════════════════════

def sec9():
    elems = [confidential_header(), Spacer(1,6)]
    elems += section("9 · Glossary", [
        glossary_table([
            ("Anchor",                   "Nigerian banking infrastructure platform used for programmatic bank transfers and automated payroll disbursement."),
            ("Income Tax (PAYE / WHT)",  "Pay As You Earn or equivalent — progressive or flat-rate personal income tax withheld by employers and remitted to the relevant national or regional revenue authority."),
            ("Revenue Authority",        "The national or state body responsible for collecting income tax and other statutory remittances (e.g. FIRS in Nigeria, KRA in Kenya, SARS in South Africa)."),
            ("Pension / Provident Fund", "Mandatory employer and employee contributions to a licensed pension or provident fund administrator, as required by the applicable jurisdiction's pension legislation."),
            ("Housing / Infrastructure Levy", "A statutory contribution to a national housing or infrastructure fund, deducted from employee basic salary (e.g. NHF in Nigeria). Configurable per jurisdiction."),
            ("Withholding Tax (WHT)",    "Tax deducted at source from contractor and professional service payments and remitted to the revenue authority."),
            ("Relief Allowance (CRA equivalent)", "A statutory deduction applied to gross income before computing taxable income. The label and formula vary by jurisdiction (e.g. Consolidated Relief Allowance in Nigeria)."),
            ("Fund Administrator (PFA equivalent)", "The licenced pension or provident fund custodian to which contributions are remitted. Varies by jurisdiction."),
            ("Compliance Pack",          "A pre-configured set of statutory tax bands, pension rates, applicable levies, and public holiday calendars for a specific country, loaded during org onboarding."),
            ("PIP",                      "Performance Improvement Plan — a formal structured plan to support and monitor an underperforming staff member."),
            ("eNPS",                     "Employee Net Promoter Score — a single-question survey measuring likelihood to recommend the company as an employer."),
            ("ATS",                      "Applicant Tracking System — the software pipeline managing candidates through the recruitment process."),
            ("OKR",                      "Objectives and Key Results — a goal-setting framework linking individual targets to organisational outcomes."),
            ("RBAC",                     "Role-Based Access Control — an access model where permissions are granted based on assigned role."),
            ("Bank / Identity Verification Number", "A unique biometric or identity identifier linked to a bank customer, used to verify account ownership before payroll disbursement (e.g. BVN in Nigeria)."),
            ("Tax Identification Number (TIN)", "A unique identifier assigned to a taxpayer by the relevant revenue authority."),
            ("Multi-Tenant",             "A software architecture where a single platform instance serves multiple organisations, each with fully isolated data."),
            ("Everywin OS",              "The organisation-specific operating environment each registered company accesses within Everywin."),
            ("Universal Messaging System","Everywin's built-in real-time communication layer: DMs, group chats, full media support, role-based access."),
            ("Soft Delete",              "A data approach where records are marked inactive but retained in the database — never permanently removed."),
            ("Idempotent",               "A property of an API call where making the same request multiple times produces the same result — preventing duplicate bank transfers."),
            ("CPM",                      "Cost Per Mille — advertising pricing where the advertiser pays per 1,000 impressions."),
            ("CPC",                      "Cost Per Click — advertising pricing where the advertiser pays each time a user clicks the ad."),
            ("Ads Wallet",               "A pre-funded balance within an advertiser's Everywin Ads Account used to pay for campaign spend in real time."),
        ]),
    ])

    # End of document
    elems.append(Spacer(1, 20))
    elems.append(HRFlowable(width="100%", thickness=1.5, color=GREEN, spaceAfter=8))
    elems.append(Paragraph(
        "End of Document — Everywin Platform PRD v2.0 · June 2026 · Confidential",
        S("eod", fontName="Helvetica-Bold", fontSize=9, textColor=NAVY, alignment=TA_CENTER)
    ))
    elems.append(Paragraph(
        "Product & Technology Team · Everywin Africa Payroll Infrastructure OS",
        S("eod2", fontName="Helvetica-Oblique", fontSize=8, textColor=DGREY, alignment=TA_CENTER)
    ))
    return elems

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

def on_page(canvas, doc):
    canvas.saveState()
    # footer line
    canvas.setStrokeColor(MGREY)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 22*mm, W - doc.rightMargin, 22*mm)
    # left footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(DGREY)
    canvas.drawString(doc.leftMargin, 17*mm, "CONFIDENTIAL — INTERNAL USE ONLY")
    # centre
    canvas.drawCentredString(W/2, 17*mm, "Everywin PRD v2.0 · June 2026")
    # right: page number
    canvas.drawRightString(W - doc.rightMargin, 17*mm, f"Page {doc.page}")
    # top green accent
    canvas.setStrokeColor(GREEN)
    canvas.setLineWidth(2)
    canvas.line(doc.leftMargin, H - 15*mm, W - doc.rightMargin, H - 15*mm)
    canvas.restoreState()

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD
# ═══════════════════════════════════════════════════════════════════════════════

out = os.path.join(os.path.dirname(__file__), "Everywin_Platform_PRD_v2_Global.pdf")

doc = SimpleDocTemplate(
    out,
    pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2.2*cm, bottomMargin=2.8*cm,
    title="Everywin PRD v2.0",
    author="Everywin Product & Technology Team",
)

story = []
story += cover()
story += toc()
story += sec1()
story += sec2()
story += sec3()
story += sec4()
story += part_a()
story += part_b()
story += part_c()
story += sec5()
story += sec6()
story += sec7()
story += sec8()
story += sec9()

doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("Built:", out)