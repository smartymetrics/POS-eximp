# 🏢 HRM Portal — Comprehensive Improvement Roadmap
**Eximp & Cloves Infrastructure Limited**
*Researched against: BambooHR, HiBob ("Bob"), Rippling, Workday HCM, Lattice, Culture Amp, SeamlessHR, PaidHR, SAP SuccessFactors, Gusto, Factoral HR, ADP*
*Document Date: April 2026 | Status: Planning*

---

## 1. Executive Summary — The "Gold Standard" Vision

Our goal is to transition the current HRM portal from a functional logging tool to an enterprise-grade "People & Performance" suite. This roadmap aligns our development with the industry-standard **9-Hub Architecture** seen in top-tier platforms like Deel and Zoho People.

### 🔑 Critical Principle: Tiered Access Permissions
Every hub listed below follows a strict **Org-Aware Access Level** (Role-Based Access Control):
*   **👤 Staff Level (Personalized)**: Users see only their own data (e.g., "My Payslip", "My Performance", "My Leave").
*   **👥 Manager Level (Team-Aware)**: Managers see their own data PLUS a consolidated dashboard for their direct reports (e.g., "Team Attendance", "Approval Requests").
*   **🛡️ HR / Admin Level (Global access)**: Full visibility across all 9 hubs for company-wide analytics, payroll processing, and legal compliance.

---

## 2. Global Inventory — Current Build ✅
These features are already functional in the codebase and will be migrated into the new Hub structure.

| Feature | Category | Built Status |
|---|---|---|
| **Staff Directory** | People & Org | ✅ CRUD functionality, role assignment |
| **Scorecard Engine** | Performance | ✅ 40/20/40 weighted logic (Goals/Quality/Manager) |
| **KPI Goal Library** | Performance | ✅ Auto-sync templates + Manual entry |
| **Attendance (Presence)**| Ops | ✅ Geofence support + suspicious log detection |
| **Leave Management** | Ops | ✅ Request/Approval workflow + Quota check |
| **Payroll Engine** | Finance | ✅ Monthly run generation + Payslip viewing |
| **Disciplinary Records**| Compliance | ✅ 4-tier severity flagging (Minor to Critical) |
| **Contract Center** | Compliance | ✅ Legal Vault + Personnel Studio signing |
| **Task Manager** | Ops | ✅ Cross-role task assignment & tracking |

---

## 3. The 9-Hub Standard (Roadmap Modules) 🚀
*Items below reflect the modules captured from the provided visual references.*

### 🏛️ HUB 1: Recruitment (ATS)
*Status: Roadmap*
*   **Modules**: Jobs, Job Requisitions, Applications, ATS Pipeline, Interviews, Offers, Talent Pool.
*   **Access**:
    *   *Managers*: View applications for their open roles, log interview feedback.
    *   *HR*: Manage job board, view full pipeline, issue offer letters.

### 👥 HUB 2: People & Org
*Status: 30% Complete*
*   **Modules**: Employees (Directory ✅), Org Chart (Visual), Departments, Diversity & Inclusion.
*   **Access**:
    *   *Global*: Searchable directory for all (phone/email only).
    *   *HR*: Full profile management including salary and private HR notes.

### ⏰ HUB 3: Time & Attendance
*Status: 70% Complete*
*   **Modules**: Attendance (Logs ✅), Timesheets, Timesheet Approvals, Shift Scheduling, Calendar, Holidays.
*   **Access**:
    *   *Staff*: Personal clock-in/out + timesheet submission.
    *   *Managers*: Approve team timesheets, view team shift calendar.

### 🌴 HUB 4: Leave Management
*Status: 80% Complete*
*   **Modules**: Leave Requests (Workflow ✅), Leave Balances, Leave Policies, Leave Accrual.
*   **Access**:
    *   *Staff*: See remaining balance + request time off.
    *   *HR*: Configure accrual rates (e.g., 1.6 days/month) and public holidays.

### 📈 HUB 5: Performance & Growth
*Status: 90% Complete*
*   **Modules**: Performance (Scorecards ✅), Goals & OKRs (Library ✅), Improvement Plans (PIPs), 360 Peer Reviews, Skills Matrix, Succession Planning.
*   **Access**:
    *   *Staff*: Interactive "My Score" dashboard.
    *   *Managers*: Launch PIPs for low-performing reports based on score alerts.

### 💰 HUB 6: Compensation & Benefits
*Status: 60% Complete*
*   **Modules**: Payroll (Runs ✅), Compensation Bands, Bonuses & Incentives, Benefits, Expenses (Payouts ✅), Tax Configuration.
*   **Access**:
    *   *Staff*: "My Payslips" and "My Benefits".
    *   *Finance/HR*: Full payroll run approval and tax remittance.

### 📣 HUB 7: Engagement & Culture
*Status: Roadmap*
*   **Modules**: Announcements, Recognition (Kudos), Surveys (eNPS), Remote Work, Policy Library, Internal Job Board.
*   **Access**:
    *   *Global*: Peer-to-peer recognition feed.
    *   *HR*: Launch anonymous surveys and publish company policies.

### ⚖️ HUB 8: Documents & Compliance
*Status: 80% Complete*
*   **Modules**: Documents, Contracts (Legal Vault ✅), HR Letters, Work Permits, Requests, Grievances, Disciplinary Records (Conduct ✅), Assets (Assign ✅).
*   **Access**:
    *   *Staff*: Personal e-signature wallet.
    *   *HR*: Manage disciplinary cases and track asset lifecycles.

### ⚙️ HUB 9: Administration
*Status: 40% Complete*
*   **Modules**: Reports, Exit & Offboarding, Users, Audit Logs, Settings.
*   **Access**:
    *   *HR/SuperAdmin*: Access to system-wide audit trails and configuration.

---

## 4. UI/UX Standard: The "Eximp Prestige" Palette
To align with the official brand identity, we are utilizing a **High-Fidelity "Black & Gold" Aesthetic** that conveys luxury, stability, and professional authority:
*   **Primary Background**: Deep Charcoal or Midnight Black (#000000 to #1A1A1A).
*   **Accents**: Lustrous Gold (#D4AF37 or #B8860B) for icons, progress rings, and active states.
*   **Typography**: Stark White (#FFFFFF) for headers and Muted Silver (#A0A0A0) for secondary text.
*   **Navigation**: Sleek Black Sidebar with gold-hued active highlights.
*   **Stat Cards**: Dark mode "Glassmorphism" effect with gold borders.

---

## 5. Implementation Priority Matrix (2026)

| Priority | Feature | Category | Notes |
|---|---|---|---|
| 🔴 **P0** | **Hub-Based Sidebar** | UX | Essential to house the new structure. |
| 🔴 **P0** | **Nigerian Tax Engine** | Finance | Automate PAYE/Pension for local compliance. |
| 🟡 **P1** | **Visual Org Chart** | People | Auto-generated from reporting lines. |
| 🟡 **P1** | **Offboarding Workflow**| Admin | Complete the lifecycle from Hire to Exit. |
| 🟢 **P2** | **Engagement Surveys** | Culture | Pulse checks for remote team wellbeing. |

---
*Document prepared for Eximp & Cloves Infrastructure Limited.*
*Next Action: Build Sidebar Shell (Hub Architecture).*
