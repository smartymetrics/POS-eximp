import sys
sys.path.insert(0, '.')
from email_service import _commission_html

def generate_preview():
    # 1. Mock Data representing the Beside Banq revamped transaction
    mock_rep = {
        "name": "Adewale Rep",
        "email": "adewale@eximps-reps.com"
    }
    
    mock_client = {
        "full_name": "Beside Banq"
    }
    
    mock_invoice = {
        "invoice_number": "EC-000090",
        "property_name": "Northstar Residence",
        "balance_due": 400000.0,
        "due_date": "2026-07-29",
        "land_cost": 360000.0 # Non-null to trigger the new revamped email layout
    }
    
    mock_earning = {
        "payment_amount": 100000.0,      # Final payment installment amount
        "commission_rate": 10.0,          # Rep's rate
        "gross_commission": 8000.0,       # Calculated on 80% (80,000 * 0.10)
        "wht_amount": 400.0,              # 5% WHT
        "net_commission": 7600.0          # Net payable
    }
    
    # 2. Generate the HTML template
    html_content = _commission_html(mock_rep, mock_client, mock_invoice, mock_earning)
    
    # 3. Write to preview file
    preview_path = "scratch/commission_email_preview.html"
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"[SUCCESS] Email preview generated at: {preview_path}")

if __name__ == "__main__":
    generate_preview()
