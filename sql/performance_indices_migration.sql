-- ============================================================
-- PERFORMANCE INDICES MIGRATION
-- Target: Resolve 502 Bad Gateway timeouts by eliminating slow table scans
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. SPEED UP CLIENT LOOKUPS BY REP
-- This is the most common filter used in the CRM
CREATE INDEX IF NOT EXISTS idx_clients_assigned_rep_id ON clients(assigned_rep_id);

-- 2. SPEED UP INVOICE LOOKUPS BY CLIENT AND REP
-- Used heavily in the Invoices and Payment dashboards
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_sales_rep_id ON invoices(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_invoices_sales_rep_name ON invoices(sales_rep_name);

-- 3. SPEED UP PAYMENT LOOKUPS
-- Ensures that payment histories load instantly
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_client_id ON payments(client_id);

-- 4. SPEED UP SUPPORT TICKET MANAGEMENT
-- Critical for team-based support ticketing
CREATE INDEX IF NOT EXISTS idx_support_tickets_client_id ON support_tickets(client_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned_admin_id ON support_tickets(assigned_admin_id);

-- 5. SPEED UP VERIFICATIONS
-- Used when finance audits new payment proofs
CREATE INDEX IF NOT EXISTS idx_pending_verifications_invoice_id ON pending_verifications(invoice_id);
CREATE INDEX IF NOT EXISTS idx_pending_verifications_client_id ON pending_verifications(client_id);

-- 6. SPEED UP MARKETING CONTACT SYNC
-- Prevents lag when leads are converted to clients
CREATE INDEX IF NOT EXISTS idx_marketing_contacts_client_id ON marketing_contacts(client_id);

-- 7. SPEED UP CAMPAIGN RECIPIENT TRACKING
-- Critical for large email blasts
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_contact_id ON campaign_recipients(contact_id);
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign_id ON campaign_recipients(campaign_id);

-- 8. SPEED UP CRM DASHBOARD & LEAD SCORING
-- The Lead Scoring Engine hits these for every calculation
CREATE INDEX IF NOT EXISTS idx_activity_log_client_id ON activity_log(client_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_commission_earnings_client_id ON commission_earnings(client_id);

-- 9. SPEED UP PAYOUTS & EXPENDITURE APPROVALS
-- Critical for the AP Ledger and Payout Dashboards
CREATE INDEX IF NOT EXISTS idx_expenditure_requests_requester_id ON expenditure_requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_expenditure_requests_vendor_id ON expenditure_requests(vendor_id);
CREATE INDEX IF NOT EXISTS idx_expenditure_requests_status ON expenditure_requests(status);

-- 10. SPEED UP LEGAL & CONTRACTS
-- Used every time a contract is initiated or checked
CREATE INDEX IF NOT EXISTS idx_contract_signing_sessions_invoice_id ON contract_signing_sessions(invoice_id);
CREATE INDEX IF NOT EXISTS idx_witness_signatures_session_id ON witness_signatures(session_id);

-- 11. SPEED UP CRM INTERACTION HISTORY
CREATE INDEX IF NOT EXISTS idx_email_logs_client_id ON email_logs(client_id);
