**EXIMP & CLOVES**

**HR Management System**

Product Requirements Document (PRD)

  ------------- ---------------------------------------------------------
  **Document    Product Requirements Document
  type**        

  ------------- ---------------------------------------------------------

  ------------- ---------------------------------------------------------
  **Version**   1.0 --- Initial Release

  ------------- ---------------------------------------------------------

  ------------- ---------------------------------------------------------
  **Date**      April 2026

  ------------- ---------------------------------------------------------

  ------------- ---------------------------------------------------------
  **Prepared    Product & Technology Team
  by**          

  ------------- ---------------------------------------------------------

  ------------- ---------------------------------------------------------
  **Status**    Draft --- Pending Management Review

  ------------- ---------------------------------------------------------

  -------------- ---------------------------------------------------------
  **Audience**   Management, HR Team, Engineering Team

  -------------- ---------------------------------------------------------

**CONFIDENTIAL --- INTERNAL USE ONLY**

**1. Executive Summary**

Eximp & Cloves currently operates fully built dashboards across CRM,
Sales, Marketing, and Finance. As the organisation grows, a structured
Human Resources Management (HR) system is required to ensure staff
performance is evaluated objectively, personnel data is centralised, and
HR operations are tracked with the same rigour applied to sales and
marketing.

This document outlines the product requirements for a new HR Management
module to be built within the existing ERP system. The system will
introduce two core capabilities:

-   A Staff Profile Database --- a centralised registry of all staff
    bio-data, employment records, qualifications, and documents.

-   A Staff Performance Dashboard --- a data-driven scoring system
    pulling from existing database tables to evaluate every staff member
    objectively across four weighted metrics.

A key design principle of this system is that performance evaluation
must not be based on sentiment or manager opinion alone. The majority of
performance data will be computed automatically from activity already
recorded in the existing database, ensuring fairness and consistency
across all roles and seniority levels, including management.

+-----------------------+-----------------------+-----------------------+
| **8**                 | **1**                 | **5**                 |
|                       |                       |                       |
| Existing DB tables    | Table to extend       | New tables to build   |
| reused                |                       |                       |
+-----------------------+-----------------------+-----------------------+

**2. Background & Problem Statement**

**2.1 Current state**

The existing ERP system serves the business well across CRM, sales
pipeline management, marketing automation, and financial operations.
Staff accounts are managed via the admins table, which stores login
credentials and role assignments. However, no structured HR layer
currently exists.

As a result, the following gaps exist today:

-   Staff performance is evaluated informally, based on manager
    perception rather than data.

-   There is no single source of truth for staff bio-data, CVs, or
    employment records.

-   There is no mechanism for setting, tracking, or reviewing staff
    goals.

-   HR metrics such as headcount trends, leave, and attrition are not
    tracked.

-   Staff have no visibility into how their performance is measured.

**2.2 Business problem**

The absence of an objective performance framework creates several
organisational risks:

-   Evaluation bias --- without data, performance reviews default to
    sentiment, which can create real or perceived unfairness among
    staff.

-   Accountability gaps --- underperformance can go undetected or
    unchallenged without a clear evidentiary basis.

-   Staff disengagement --- staff who are not evaluated clearly cannot
    self-correct or understand where to improve.

-   Compliance and operational risk --- no central record of staff
    documents, contracts, or qualifications.

**2.3 Opportunity**

Because the existing ERP already records deal activity, payment
collections, marketing campaigns, support tickets, and audit logs, the
raw data required for objective performance measurement already exists.
The opportunity is to build a thin but structured HR layer on top of
this data, rather than starting from scratch.

**3. Objectives**

The HR Management System must achieve the following objectives:

  -------- --------------------------------- ---------------------------------
  **\#**   **Objective**                     **Success criterion**

  1        Centralise all staff data in one  Every active staff member has a
           profile database                  complete profile with bio-data,
                                             employment record, and uploaded
                                             documents

  2        Enable objective, data-driven     ≥60% of each staff member\'s
           performance scoring               performance score is computed
                                             automatically from existing
                                             database activity

  3        Give staff visibility into their  Each staff member can log in and
           own performance                   see their own scores, goals, and
                                             progress

  4        Enable role-specific goal setting HR can set and adjust individual
                                             monthly targets per staff member,
                                             per role

  5        Support HR team with operational  Leave requests, headcount, and
           metrics                           attrition tracked within the
                                             dashboard

  6        Maintain a single                 Role-based access ensures HR sees
           access-controlled platform        all data, managers see their
                                             team, staff see only their own
                                             record
  -------- --------------------------------- ---------------------------------

**4. Scope**

**4.1 In scope --- Phase 1**

-   Staff Profile Database: creation and management of individual staff
    records

-   Staff Performance Dashboard: automated scoring system for all staff
    roles

-   Role-based access control: HR admin, line manager, and staff-level
    views

-   Goal-setting module: HR-configurable monthly targets per staff
    member

-   Basic HR metrics: headcount, leave requests, staff status overview

**4.2 Out of scope --- Phase 1**

-   Payroll processing or salary management

-   Recruitment and applicant tracking system (ATS)

-   Learning management system (LMS) / training module

-   360-degree peer review system

-   Mobile application for staff self-service

Note: The above items are candidates for Phase 2 and beyond, as the
system matures.

**4.3 Integration with existing system**

The HR module reads from --- but does not write to --- the following
existing tables. All performance data is derived, not duplicated:

  --------------------- ---------------------------- -------------------------
  **Existing table**    **Data used**                **Feeds into**

  admins                name, email, role, is_active Staff identity & access
                                                     control

  invoices              pipeline_stage, status,      Sales rep goals: deals
                        sales_rep_id                 closed, conversion rate

  payments              amount, payment_type, linked Collection rate per rep
                        rep                          

  commission_earnings   final_amount,                Payout history per staff
                        commission_rate              

  support_tickets       priority, status, assigned   Service quality score
                        staff                        

  email_campaigns       is_ab_test, sent count,      Marketing staff goals
                        dates                        

  campaign_recipients   opens, clicks, engagement    Email performance metrics

  marketing_contacts    engagement_score,            Lead generation goals
                        contact_type                 

  activity_log          all system actions per user  Initiative & activity
                                                     tracking

  appointments          scheduled, confirmed         Operations staff goals
                        meetings                     

  assets                equipment assigned per staff HR asset inventory view
  --------------------- ---------------------------- -------------------------

**5. System Architecture**

**5.1 Module overview**

The HR Management System sits as a new module within the existing ERP
platform. It introduces the following components:

  ------------------ ----------------------------------------------------
  **Module**         **Description**

  **Staff Profile    Central identity and records store for all staff.
  DB**               Foundation for all other HR modules.

  **Performance      Automated scoring engine that pulls from existing
  Dashboard**        transaction data and blends with manager-entered
                     qualitative scores.

  **Goal             HR-configurable monthly targets per staff member.
  Management**       Compared against actual data to compute the Goals
                     Achieved (40%) score.

  **HR Metrics**     Operational HR data: headcount, leave tracking,
                     staff status, asset assignment. Expands iteratively.

  **Access Control** Role-based views: HR admin (full access), line
                     manager (own team), staff (own record only).
  ------------------ ----------------------------------------------------

**5.2 New database tables required**

The following five new tables must be created to support the HR module:

  ---------------------- -------------------------- --------------------------
  **Table**              **Purpose**                **Key fields**

  staff_profiles         Extended bio and           admin_id (FK), dob, phone,
                         employment data linked to  emergency_contact,
                         admins table               start_date,
                                                    employment_type,
                                                    line_manager_id,
                                                    department

  staff_documents        Uploaded files per staff   staff_id (FK), doc_type,
                         member                     file_url, upload_date,
                                                    uploaded_by

  staff_qualifications   Education, certifications, staff_id (FK), type
                         and skills                 (education/cert/skill),
                                                    title, institution, year

  staff_goals            Monthly targets set per    staff_id (FK), period,
                         staff, per role            goal_type, target_value,
                                                    actual_value (computed),
                                                    achieved (%)

  performance_reviews    Manager-entered            staff_id (FK),
                         qualitative scores per     reviewer_id, period,
                         review cycle               teamwork_score (1--5),
                                                    initiative_score (1--5),
                                                    notes
  ---------------------- -------------------------- --------------------------

Additionally, the admins table requires a one-time extension to support
HR management, adding the fields department and line_manager_id.

**6. Performance Scoring Framework**

**6.1 Scoring model**

Each staff member receives a single composite performance score (0--100)
calculated monthly. The score is built from four weighted metrics:

  ------------------------ ------------ ------------------ ---------------------
  **Metric**               **Weight**   **Scoring method** **Data source**

  Goals achieved           **40%**      Automated ---      invoices, payments,
                                        actual vs. target  campaigns,
                                        from staff_goals   appointments

  Work quality             **20%**      Semi-automated --- clients,
                                        KYC completion,    support_tickets
                                        ticket resolution  
                                        rates              

  Teamwork & communication **20%**      Manual --- line    performance_reviews
                                        manager scores     
                                        1--5 per cycle     

  Initiative & growth      **20%**      Manual --- line    performance_reviews
                                        manager scores     
                                        1--5 per cycle     
  ------------------------ ------------ ------------------ ---------------------

**6.2 Goals by role --- industry-standard KPIs**

Goals are role-specific. The following KPIs are grounded in real estate
industry best practice and are derived automatically from existing
database activity:

**Sales Executives / Reps**

  ------------------------ ------------------------------ ------------------
  **KPI / Goal**           **What it measures**           **DB source**

  Deals closed per month   Invoices reaching closed       invoices
                           pipeline stage                 

  Collection rate (target  Payments collected vs. total   payments
  ≥80%)                    invoiced                       

  Lead-to-inspection ratio Leads that converted to        clients +
                           property inspection            appointments
                           appointments                   

  Inspection-to-contract   Inspections that progressed to invoices
  rate (benchmark 25--40%) contract stage                 

  Average deal value       Total revenue closed ÷ number  invoices
                           of deals                       

  KYC completion rate      \% of assigned clients with    clients
                           complete KYC data              
  ------------------------ ------------------------------ ------------------

**Marketing Staff**

  ---------------------- ------------------------------ ---------------------
  **KPI / Goal**         **What it measures**           **DB source**

  Campaigns sent per     Number of email campaigns      email_campaigns
  month                  executed                       

  Email open rate        Opens as % of delivered emails campaign_recipients
  (benchmark 25--35%)                                   

  Average lead           Mean engagement score (0--100) marketing_contacts
  engagement score       across campaign contacts       

  New leads added per    Contacts added to marketing DB marketing_contacts
  month                  from their channel             

  Lead-to-client         Leads whose contact_type       marketing_contacts
  conversion rate        changed to client              

  A/B test adoption      \% of campaigns using          email_campaigns
                         is_ab_test flag                
  ---------------------- ------------------------------ ---------------------

**Operations Staff**

  ---------------------- ------------------------------ ----------------------
  **KPI / Goal**         **What it measures**           **DB source**

  Expenditure requests   Expense requests reviewed and  expenditure_requests
  processed              actioned per month             

  Appointments           Property inspections and       appointments
  coordinated            signing meetings confirmed     

  Vendor directory       Active, complete vendor        vendors
  maintenance            records in system              

  Asset tracking         Company equipment correctly    assets
  accuracy               logged with assigned staff     
  ---------------------- ------------------------------ ----------------------

**Admin / Management**

  ---------------------- ------------------------------ -----------------------
  **KPI / Goal**         **What it measures**           **DB source**

  Team target            \% of direct reports who hit   staff_goals (computed)
  achievement rate       their monthly goals            

  Support ticket         Cases escalated to chat rooms  support_tickets
  escalation rate        --- lower is better            

  Payment verification   Avg. time to action pending    pending_verifications
  turnaround             payment proofs                 

  System activity        Regular login and action       activity_log
  consistency            frequency in audit log         
  ---------------------- ------------------------------ -----------------------

**7. Access Control**

The HR module uses a single platform with role-based access. What a user
sees depends on their role. There is no separate staff-facing portal in
Phase 1 --- staff access is a restricted view within the same system.

  ----------------------- --------------- --------------- ---------------
  **Capability**          **HR Admin**    **Line          **Staff
                                          Manager**       Member**

  View all staff profiles **Yes**         No              No

  View own profile        **Yes**         **Yes**         Read only

  View all performance    **Yes**         Own team only   No
  scores                                                  

  View own performance    **Yes**         **Yes**         **Yes**
  score                                                   

  Set / edit staff goals  **Yes**         Own team only   No

  Enter qualitative       **Yes**         Own team only   No
  review scores                                           

  View HR metrics         **Yes**         No              No
  (headcount, leave)                                      

  Upload / manage staff   **Yes**         No              No
  documents                                               
  ----------------------- --------------- --------------- ---------------

**8. Functional Requirements**

**8.1 Staff Profile Database**

-   The system shall allow HR admins to create a staff profile for any
    user in the admins table.

-   Each profile shall contain five sections: personal bio-data,
    employment details, CV & qualifications, uploaded documents, and
    system access notes.

-   HR admins shall be able to upload documents (PDF, JPG, PNG) to a
    staff profile, categorised by document type (CV, contract, ID,
    etc.).

-   Staff records shall not be deleted when a staff member exits ---
    they must be archived with an exit date and reason.

-   The system shall display a summary card for each staff member
    showing name, role, department, status, and line manager.

**8.2 Staff Performance Dashboard**

-   The system shall compute a composite performance score (0--100) for
    each staff member on a monthly basis.

-   Goals Achieved (40%): the system shall compare actual output pulled
    from existing tables against targets set in staff_goals and express
    this as a percentage score.

-   Work Quality (20%): the system shall compute this score from
    quantitative signals such as KYC completion rate and support ticket
    resolution rate where applicable.

-   Teamwork & Communication (20%) and Initiative & Growth (20%): line
    managers shall enter a rating of 1--5 each review cycle; the system
    shall convert this to a percentage contribution.

-   The dashboard shall display individual trend lines showing
    performance score over the past 6 months.

-   The dashboard shall flag staff members whose score falls below a
    configurable threshold (default: 50/100).

**8.3 Goal Management**

-   HR admins and line managers shall be able to set monthly targets for
    each staff member.

-   Targets shall be role-specific: the system shall offer the
    appropriate KPI fields based on the staff member\'s role (sales,
    marketing, operations, admin).

-   The system shall support different targets for staff at the same
    role level --- targets are per person, not per role.

-   Actual performance data shall be automatically populated at month
    end from the relevant source tables.

-   Goals and actuals shall be visible to both HR admins and the staff
    member themselves.

**8.4 HR Metrics**

-   The HR dashboard shall display a headcount overview: total active
    staff, by department, by role.

-   The system shall support leave request submission and approval,
    recording leave type, dates, and status.

-   Staff status changes (active, on leave, exited) shall be tracked
    with timestamps.

-   Asset assignments from the existing assets table shall be surfaced
    in the staff profile view.

**9. Non-Functional Requirements**

  ---------------- ------------------------------------------------------
  **Category**     **Requirement**

  Performance      Performance scores must be refreshed at least daily.
                   Dashboard pages must load within 3 seconds.

  Security         All staff data is sensitive. Access must be enforced
                   at the API level, not just the UI. No staff member can
                   access another\'s profile data.

  Data integrity   The HR module must read from existing tables without
                   modifying them. No HR process should alter sales,
                   marketing, or finance records.

  Auditability     All changes to staff profiles, goal targets, and
                   review scores must be logged with the editor\'s
                   identity and timestamp.

  Scalability      The system must support up to 200 staff records
                   without architectural changes.

  Data retention   Exited staff profiles must be retained for a minimum
                   of 5 years for compliance purposes.
  ---------------- ------------------------------------------------------

**10. Build Plan & Phasing**

**Phase 1 --- Staff Profile Database (build first)**

Rationale: All other HR functionality depends on clean, centralised
staff identity data. This must exist before performance scoring can be
linked to individuals.

-   Create staff_profiles table linked to admins

-   Create staff_documents table and file upload interface

-   Create staff_qualifications table

-   Build HR admin interface: create, view, edit, and archive staff
    profiles

-   Implement role-based access control for HR module

**Phase 2 --- Staff Performance Dashboard**

Rationale: With profiles in place, the scoring engine can be built,
linking each staff member to their relevant KPI data sources.

-   Create staff_goals table and goal-setting interface

-   Create performance_reviews table and manager review form

-   Build automated scoring engine (Goals Achieved + Work Quality)

-   Build performance dashboard view for HR, manager, and self-view

-   Implement monthly trend charts and threshold alerting

**Phase 3 --- HR Metrics (expand iteratively)**

Rationale: Operational HR metrics are important but not urgent. These
can be added incrementally after the core modules are stable.

-   Leave request and approval workflow

-   Headcount and attrition reporting

-   Asset assignment view within staff profiles

-   HR dashboard overview: all metrics in one view

**11. Risks & Mitigations**

  ---------------------- ---------------- -------------------------------------
  **Risk**               **Likelihood**   **Mitigation**

  Staff resistance to    Medium           Involve staff early --- give them
  objective scoring                       visibility into their own scores from
                                          day one. Transparency reduces
                                          resistance.

  Incomplete data in     Low              Audit existing table completeness
  existing tables                         before launch. Flag staff whose
  reducing score                          scores cannot be fully computed due
  accuracy                                to missing source data.

  Goal targets set       Medium           Require HR admin sign-off on all goal
  unfairly or                             targets before a review period
  inconsistently                          begins. Log all target changes with
                                          timestamps.

  Role-based access      Low              Access rules must be enforced at the
  misconfiguration                        API and database level. QA must
  leaking sensitive data                  include access control test
                                          scenarios.

  Scope creep delaying   High             Strictly maintain Phase 1 scope.
  Phase 1 delivery                        Payroll, recruitment, LMS, and peer
                                          review are explicitly deferred to
                                          future phases.
  ---------------------- ---------------- -------------------------------------

**12. Glossary**

  ---------------- ------------------------------------------------------
  **Term**         **Definition**

  PRD              Product Requirements Document --- a formal
                   specification of what must be built, for whom, and
                   why.

  KPI              Key Performance Indicator --- a measurable value used
                   to evaluate success against a target.

  ERP              Enterprise Resource Planning --- the integrated
                   software system Eximp & Cloves uses for all
                   operations.

  KYC              Know Your Client --- the compliance process of
                   verifying a client\'s identity and documentation.

  DXA              Document eXtended Attributes --- unit of measurement
                   used in DOCX files (1440 DXA = 1 inch).

  FK               Foreign Key --- a database field that references the
                   primary key of another table.

  Phase 1          The initial build scope: Staff Profile Database + core
                   access control.

  Phase 2          Second build scope: Staff Performance Dashboard + Goal
                   Management.

  Phase 3          Third build scope: HR Metrics module --- expanded
                   iteratively over time.
  ---------------- ------------------------------------------------------

End of Document --- Eximp & Cloves HR Management System PRD v1.0

For questions contact the Product & Technology Team
