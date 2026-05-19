import os
import sys
import asyncio
sys.path.append(os.getcwd())

from report_service import ReportService

async def main():
    print("Testing ReportService collection_report with new 'Sales Rep' column (ASCII mode)...")
    try:
        report_data = await ReportService.get_report_data("collection_report", None, None)
        items = report_data.get("items", [])
        
        if not items:
            print("\n[WARNING] No outstanding invoices found. Cannot verify columns.")
            sys.exit(0)
            
        first_item = items[0]
        keys = list(first_item.keys())
        print(f"\nReport columns generated: {keys}")
        
        # Assert that 'Sales Rep' is in the columns
        if "Sales Rep" in keys:
            print("\n[SUCCESS] 'Sales Rep' is now a valid column in the outstanding payments dataset!")
            # Assert correct column ordering (it should be right after 'Phone')
            phone_idx = keys.index("Phone")
            rep_idx = keys.index("Sales Rep")
            if rep_idx == phone_idx + 1:
                print("  [OK] Column placement verified: 'Sales Rep' is directly after the 'Phone' column.")
            else:
                print(f"  [WARNING] Column placement is not as expected. 'Phone' index: {phone_idx}, 'Sales Rep' index: {rep_idx}")
        else:
            print("\n[FAILURE] 'Sales Rep' column is missing from the outstanding payments report!")
            sys.exit(1)
            
        print("\nDisplaying all outstanding payments items with their Sales Rep:")
        print("-" * 120)
        print(f"{'Invoice #':<12} | {'Client':<25} | {'Sales Rep':<25} | {'Property':<30} | {'Balance':<15}")
        print("-" * 120)
        for item in items:
            inv = item.get("Invoice #", "")
            client = item.get("Client", "")
            rep = item.get("Sales Rep", "")
            prop = item.get("Property", "")
            balance = item.get("Balance (NGN)", "")
            
            # Highlight EC-000033
            marker = " *" if inv == "EC-000033" else ""
            print(f"{inv + marker:<12} | {client[:25]:<25} | {rep[:25]:<25} | {prop[:30]:<30} | {balance:<15}")
            
        print("-" * 120)
        print("Note: * marks target invoice EC-000033.")
        
    except Exception as e:
        print(f"Error during report validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
