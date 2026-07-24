import os
import sys
import asyncio
sys.path.append(os.getcwd())

from report_service import ReportService

async def main():
    print("Fetching collection report data via ReportService...")
    try:
        report_data = await ReportService.get_report_data("collection_report", None, None)
        items = report_data.get("items", [])
        
        found = False
        print(f"\nReport loaded. Found {len(items)} item(s) in the Outstanding Payments report.")
        
        for item in items:
            inv_num = item.get("Invoice #")
            if inv_num == "EC-000033":
                found = True
                print("\n[SUCCESS] Invoice EC-000033 was successfully found in the Outstanding Payments report!")
                print(f"  Client: {item.get('Client')}")
                print(f"  Phone: {item.get('Phone')}")
                print(f"  Property: {item.get('Property')}")
                print(f"  Total: {item.get('Total (NGN)')}")
                print(f"  Paid: {item.get('Paid (NGN)')}")
                print(f"  Balance: {item.get('Balance (NGN)')}")
                print(f"  Due Date: {item.get('Due Date')}")
                print(f"  Status: {item.get('Status')}")
                print(f"  Days Overdue: {item.get('Days Overdue')}")
                break
                
        if not found:
            print("\n[FAILURE] Invoice EC-000033 is STILL missing from the Outstanding Payments report.")
            
    except Exception as e:
        print(f"Error during report validation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
