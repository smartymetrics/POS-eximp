from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Optional

def calculate_due_date(payment_date_str: str, payment_duration: str) -> str:
    """
    Calculate final due date from deposit date + installment duration.
    payment_date_str: "3/18/2026" (Google Form format MM/DD/YYYY)
    payment_duration: "3 months", "6 months", "Outright", etc.
    Returns: ISO date string "YYYY-MM-DD"
    """
    if not payment_duration or payment_duration.strip().lower() == "outright":
        try:
            # Try MM/DD/YYYY first (Google Form)
            base = datetime.strptime(payment_date_str.strip(), "%m/%d/%Y")
            return base.strftime("%Y-%m-%d")
        except:
            try:
                # Try YYYY-MM-DD
                base = datetime.strptime(payment_date_str.strip(), "%Y-%m-%d")
                return base.strftime("%Y-%m-%d")
            except:
                return payment_date_str

    try:
        months = int(
            payment_duration.lower()
            .replace("months", "")
            .replace("month", "")
            .strip()
        )
        try:
            base = datetime.strptime(payment_date_str.strip(), "%m/%d/%Y")
        except:
            base = datetime.strptime(payment_date_str.strip(), "%Y-%m-%d")
        
        due = base + relativedelta(months=months)
        return due.strftime("%Y-%m-%d")
    except:
        # Fallback to 7 days if duration parsing fails
        try:
            base = datetime.strptime(payment_date_str.strip(), "%m/%d/%Y")
        except:
            base = datetime.strptime(payment_date_str.strip(), "%Y-%m-%d")
        return (base + relativedelta(days=7)).strftime("%Y-%m-%d")


def resolve_invoice_status(invoice: dict) -> str:
    """
    Dynamically calculate the correct status for an invoice.
    Overrides the stored status if the due date has passed.
    """
    balance = float(invoice.get("balance_due") or 0)
    amount_paid = float(invoice.get("amount_paid") or 0)
    due_date_str = invoice.get("due_date")

    if balance <= 0:
        return "paid"

    if due_date_str:
        try:
            due = date.fromisoformat(str(due_date_str))
            if date.today() > due:
                return "overdue"
        except:
            pass

    if amount_paid > 0:
        return "partial"

    return "unpaid"
    

def sanitize_client_address(client: dict) -> dict:
    """
    Returns the client record as is.
    (Address filtering for Yaba/Lagos is no longer required as form fields are now explicit).
    """
    return client
