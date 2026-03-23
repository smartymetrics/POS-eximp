-- 1. Add payment_type column to payments table
ALTER TABLE payments 
ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) DEFAULT 'payment';

-- 2. Update existing payments to be 'payment' (already default, but safe to run)
UPDATE payments SET payment_type = 'payment' WHERE payment_type IS NULL;

-- 3. Update the trigger function to handle refunds correctly
-- A refund should REDUCE the amount_paid on the invoice.
CREATE OR REPLACE FUNCTION update_invoice_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE invoices
    SET 
        amount_paid = (
            SELECT COALESCE(SUM(
                CASE WHEN payment_type = 'refund' THEN -amount ELSE amount END
            ), 0)
            FROM payments
            WHERE invoice_id = COALESCE(NEW.invoice_id, OLD.invoice_id) AND is_voided = false
        ),
        status = CASE
            WHEN (
                SELECT COALESCE(SUM(
                    CASE WHEN payment_type = 'refund' THEN -amount ELSE amount END
                ), 0) FROM payments WHERE invoice_id = COALESCE(NEW.invoice_id, OLD.invoice_id) AND is_voided = false
            ) >= amount THEN 'paid'
            WHEN (
                SELECT COALESCE(SUM(
                    CASE WHEN payment_type = 'refund' THEN -amount ELSE amount END
                ), 0) FROM payments WHERE invoice_id = COALESCE(NEW.invoice_id, OLD.invoice_id) AND is_voided = false
            ) > 0 THEN 'partial'
            ELSE 'unpaid'
        END,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.invoice_id, OLD.invoice_id);
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 4. Add voiding columns to commission_earnings
ALTER TABLE commission_earnings
ADD COLUMN IF NOT EXISTS is_voided BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS voided_by UUID REFERENCES admins(id),
ADD COLUMN IF NOT EXISTS void_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_commission_earnings_not_voided 
ON commission_earnings(sales_rep_id, is_voided) 
WHERE is_voided = false;

-- 5. Re-sync all invoice totals to account for refunds correctly
UPDATE invoices SET amount_paid = (
    SELECT COALESCE(SUM(CASE WHEN payment_type = 'refund' THEN -amount ELSE amount END), 0)
    FROM payments WHERE invoice_id = invoices.id AND is_voided = false
);
