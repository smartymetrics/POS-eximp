# Technical Instructions for Future Refactor: 7-Stage Sales Pipeline

This document serves as a guide for any future AI assistant to correctly implement changes to the Sales Pipeline stages.

## Objective
Expand and rename the sales pipeline from the current 4 stages (`inspection`, `offer`, `contract`, `closed`) to 6 or 7 stages.

## Technical Scope of Work

### 1. Database Migration
*   **Identify and Drop Constraints**: Locate and `DROP` the `CHECK` constraints on the `pipeline_stage` column in the `invoices` and `clients` tables.
*   **Data Migration**: Run an `UPDATE` query to map existing data (e.g., `'inspection'`, `'offer'`) to the new expanded names.
*   **Update Schema**: 
    *   Change the `DEFAULT` value for the column to the new starting stage.
    *   Apply a new `CHECK` constraint that includes all 7 new stage names.

### 2. Frontend (CRM Kanban Optimization)
*   **Layout Refactor**: The `templates/professional_crm.html` Kanban board currently uses a layout optimized for 4 columns.
*   **Responsive Scrolling**: Refactor the Kanban container to support **horizontal scrolling** if more than 4 stages are present.
*   **Re-mapping**: Ensure that the drag-and-drop JavaScript logic handles the new IDs and titles of the expanded columns.

### 3. Backend Logic & Automation
*   **Routers Review**: Search for the old stage strings in `signing.py`, `payments.py`, `crm.py`, `invoices.py`, and `webhooks.py`.
*   **Automation Triggers**: 
    *   Update the logic that moves a deal to the "Contract" stage when a signing link is generated.
    *   Update the logic that moves a deal to the "Closed" stage when full payment is confirmed.
*   **Models**: Update any default values or validation in `models.py`.

### 4. Reporting & Analytics
*   **KPI Calculation**: Update `routers/analytics.py` and `routers/crm_professional.py` to ensure that aggregation of "Deals in Pipeline" correctly sums up figures across all 7 stages.
*   **Visualizations**: Ensure that chart legends or categories handle the increased number of stages without overlapping.

---
**Note to Assistant**: Do not perform a simple search-and-replace of strings. You must execute the SQL migration first and then update the backend logic to match the new schema exactly.
