# 1. Product Objective
Replicate the high-conversion ecosystem of tools like **HubSpot** and **Salesforce**. Create a unified loop where Marketing, Sales (CRM), and Support share real-time intelligence to maximize revenue and client satisfaction.

# 2. Key Modules & Features

## A. Floating Support Widget (Website - App B)
- **Feature**: A persistent, floating "Help" button appearing on all pages.
- **Functionality**:
  - One-click intake form for tickets.
  - Auto-identifies returning clients (if logged in).
  - High-speed delivery to the Admin CRM.

## B. Closed-Loop Revenue Attribution (Marketing - App A)
- **Feature**: Revenue tracking per campaign.
- **Functionality**:
  - Links Invoice payments to the specific marketing campaign or segment that acquired the lead.
  - Dashboard shows: **"Total Revenue per Campaign"** and **"CPA" (Cost Per Acquisition)**.

## C. Support Desk & CRM Hub (CRM - App A)
- **Feature**: Unified Management Hub.
- **Functionality**:
  - **Support Kanban**: Managing tickets from the Website widget.
  - **VIP Priority**: Tickets from high-LTV clients (₦10M+) are automatically flagged for 1-hour response.
  - **Intelligence Sync**: Support reps see the client's full financial history while replying.

## D. Advanced Pipeline & Sales Hub (CRM - App A)
- **Feature**: Visual Deal Management & Forecasting.
- **Functionality**:
  - **Kanban Deal Board**: A drag-and-drop interface where Sales Reps move leads through stages (Inspection → Offer → Contract → Paid).
  - **Weighted Pipeline**: Shows predicted revenue based on deal probability (e.g., Prospect=10%, Inspection=50%, Partial=90%).
  - **Meeting Scheduler**: Integrated calendar links (like Calendly) that allow site visitors to book inspections directly from emails.

## E. Advanced Marketing Workflows (Automation - App A)
- **Feature**: "If-This-Then-That" Revenue Automation.
- **Functionality**:
  - **ROI Engagement**: Automatically re-targets leads who opened an email but didn't buy.
  - **Segment Transitions**: Auto-moves a contact from "Warm Lead" to "VIP Client" based on purchase value.
  - **Appointment Reminders**: Trigger automated SMS/Mail reminders 2 hours before a scheduled inspection.

# 3. Technical Requirements
- **App A (Backend)**: FastAPI + Supabase. Must handle a new `/api/support` lifecycle.
- **App B (Frontend)**: React / Vite. Implementation of a global `<FloatingSupport />` component within the `App.jsx` layout.
- **Automation**: Activation of the `APScheduler` in `main.py` to power the marketing engine.

# 4. Roadmap & Phases
1. **Phase 1**: Enable Automation Engine & Revenue Attribution (Audit & Drill-down).
2. **Phase 2**: Implement Floating Support Widget (Website) and Support Hub (CRM).
3. **Phase 3**: Premium Dark Mode Redesign & Revenue Transparency Dashboard.
4. **Phase 4**: Sales Hub Expansion (Kanban Pipelines & Appointment Scheduler).
5. **Phase 5**: Cross-Hub Automated Workflows & Segment Transitions.
