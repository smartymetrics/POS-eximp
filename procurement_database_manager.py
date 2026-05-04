"""
PROCUREMENT DATABASE INTEGRATION
Eximp & Cloves Infrastructure Limited - ERP System
====================================================

Integrates parsed procurement data with Supabase database.
Handles vendor management, expense tracking, and financial records.
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import sys
sys.path.insert(0, os.getcwd())

from database import supabase, db_execute
from procurement_parser import QuotationParser, ProcurementSection, ProcurementItem
from procurement_analytics import ProcurementAnalytics


class ProcurementDatabaseManager:
    """
    Manages procurement data insertion into Supabase.
    Handles vendors, expenses, and procurement project tracking.
    """
    
    def __init__(self):
        self.metadata = {}
        self.sections = []
        self.all_items = []
        self.project_id = None
        self.vendor_ids = {}
        self.inserted_expenses = []
    
    async def import_quotation(self, filepath: str, property_id: Optional[str] = None, 
                              estate_draft_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Import a complete quotation into the database.
        
        Args:
            filepath: Path to quotation Excel file
            property_id: Target property UUID (optional)
            estate_draft_id: Target estate draft UUID (optional)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Step 1: Parse the quotation
            print("📋 Step 1: Parsing quotation file...")
            parser = QuotationParser(filepath)
            self.sections, self.metadata = parser.parse()
            
            for section in self.sections:
                self.all_items.extend(section.items)
            
            print(f"✓ Parsed {len(self.all_items)} items across {len(self.sections)} sections")
            
            # Step 2: Create or get vendors
            print("\n🏢 Step 2: Setting up vendors...")
            await self._setup_vendors()
            
            # Step 3: Create procurement project record
            print("\n📊 Step 3: Creating procurement project record...")
            await self._create_procurement_project(property_id, estate_draft_id)
            
            # Step 4: Insert expenses
            print("\n💰 Step 4: Inserting procurement expenses...")
            await self._insert_expenses(property_id, estate_draft_id)
            
            # Step 5: Generate analytics summary
            print("\n📈 Step 5: Generating analytics summary...")
            await self._save_analytics_summary()
            
            message = f"✅ Successfully imported {len(self.inserted_expenses)} expense records from quotation"
            print(f"\n{message}")
            return True, message
            
        except Exception as e:
            error_msg = f"❌ Import failed: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    async def _setup_vendors(self):
        """Create or get vendor records for each category"""
        vendor_categories = set(item.category for item in self.all_items)
        
        for category in vendor_categories:
            # Check if vendor exists
            res = await db_execute(lambda: supabase.table("vendors")
                .select("id")
                .eq("name", category)
                .eq("type", "supplier")
                .execute()
            )
            
            if res.data:
                self.vendor_ids[category] = res.data[0]["id"]
                print(f"  ✓ Using existing vendor: {category}")
            else:
                # Create new vendor
                vendor_data = {
                    "name": category,
                    "type": "supplier",
                    "email": f"procurement@eximps-cloves.com",
                    "phone": "+234 912 686 4383",
                    "is_active": True
                }
                res = await db_execute(lambda: supabase.table("vendors")
                    .insert(vendor_data)
                    .execute()
                )
                
                if res.data:
                    self.vendor_ids[category] = res.data[0]["id"]
                    print(f"  ✓ Created vendor: {category}")
    
    async def _create_procurement_project(self, property_id: Optional[str], 
                                         estate_draft_id: Optional[str]):
        """Create a procurement project record"""
        project_data = {
            "name": f"Procurement - {self.metadata.get('location', 'Project')}",
            "description": f"Quotation dated {self.metadata.get('quotation_date')}",
            "property_id": property_id,
            "estate_draft_id": estate_draft_id,
            "total_budget": float(sum(s.total_amount for s in self.sections)),
            "total_items": len(self.all_items),
            "total_sections": len(self.sections),
            "quotation_date": self.metadata.get('quotation_date'),
            "location": self.metadata.get('location'),
            "company": self.metadata.get('company'),
            "status": "active"
        }
        
        # Try to insert into procurement_projects table if it exists
        try:
            res = await db_execute(lambda: supabase.table("procurement_projects")
                .insert(project_data)
                .execute()
            )
            if res.data:
                self.project_id = res.data[0]["id"]
                print(f"  ✓ Created procurement project: {self.project_id}")
        except:
            # Table might not exist, continue anyway
            print("  ℹ Procurement projects table not found (optional)")
    
    async def _insert_expenses(self, property_id: Optional[str], 
                              estate_draft_id: Optional[str]):
        """Insert procurement expenses into the database"""
        for section in self.sections:
            for item in section.items:
                expense_data = {
                    "title": item.description,
                    "description": f"From {section.name} - Quotation ({self.metadata.get('location')})",
                    "category": item.category,
                    "section": item.section,
                    "quantity": item.quantity,
                    "quantity_unit": item.quantity_unit,
                    "unit_price": float(item.unit_price),
                    "amount": float(item.amount),
                    "amount_paid": 0.0,  # Not yet paid
                    "status": "pending",
                    "vendor_id": self.vendor_ids.get(item.category),
                    "property_id": property_id,
                    "estate_draft_id": estate_draft_id,
                    "source": "quotation_import",
                    "quotation_date": self.metadata.get('quotation_date'),
                    "expense_date": self.metadata.get('quotation_date'),
                    "sn": item.sn,
                    "project_id": self.project_id,
                    "metadata": {
                        "quotation_location": self.metadata.get('location'),
                        "company": self.metadata.get('company')
                    }
                }
                
                try:
                    res = await db_execute(lambda: supabase.table("procurement_expenses")
                        .insert(expense_data)
                        .execute()
                    )
                    
                    if res.data:
                        self.inserted_expenses.append(res.data[0])
                        print(f"  ✓ {item.sn}. {item.description[:40]:40} - ₦{item.amount:>12,.0f}")
                except Exception as e:
                    print(f"  ⚠ Error inserting {item.description}: {e}")
    
    async def _save_analytics_summary(self):
        """Generate and save analytics summary"""
        try:
            analytics = ProcurementAnalytics(self.sections, self.metadata)
            summary = analytics.get_executive_summary()
            
            # Try to save to procurement_analytics table
            analytics_data = {
                "project_id": self.project_id,
                "total_budget": summary['metrics']['total_budget'],
                "total_items": summary['metrics']['total_items'],
                "cost_distribution": summary['cost_distribution'],
                "top_risks": summary['risks'],
                "opportunities": summary['opportunities'],
                "insights": summary['insights'],
                "recommendations": summary['recommendations'],
                "generated_at": datetime.now().isoformat()
            }
            
            await db_execute(lambda: supabase.table("procurement_analytics")
                .insert(analytics_data)
                .execute()
            )
            
            print(f"  ✓ Analytics summary saved")
            
            # Print key insights to console
            print(f"\n  📊 Key Insights:")
            for insight in summary['insights']:
                print(f"     • {insight}")
                
        except Exception as e:
            print(f"  ℹ Analytics save skipped: {e}")
    
    async def get_procurement_status(self, project_id: str) -> Dict:
        """Get status of a procurement project"""
        try:
            # Get project
            proj_res = await db_execute(lambda: supabase.table("procurement_projects")
                .select("*")
                .eq("id", project_id)
                .execute()
            )
            
            if not proj_res.data:
                return {"error": "Project not found"}
            
            project = proj_res.data[0]
            
            # Get expenses
            exp_res = await db_execute(lambda: supabase.table("procurement_expenses")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            )
            
            expenses = exp_res.data or []
            
            # Calculate stats
            total_budget = sum(float(e.get("amount", 0)) for e in expenses)
            total_paid = sum(float(e.get("amount_paid", 0)) for e in expenses)
            total_pending = total_budget - total_paid
            
            return {
                "project": project,
                "expenses": expenses,
                "total_budget": total_budget,
                "total_paid": total_paid,
                "total_pending": total_pending,
                "payment_percentage": (total_paid / total_budget * 100) if total_budget > 0 else 0,
                "item_count": len(expenses)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def update_expense_payment(self, expense_id: str, amount_paid: float) -> Tuple[bool, str]:
        """Update payment for an expense"""
        try:
            # Get current expense
            exp_res = await db_execute(lambda: supabase.table("procurement_expenses")
                .select("*")
                .eq("id", expense_id)
                .execute()
            )
            
            if not exp_res.data:
                return False, "Expense not found"
            
            expense = exp_res.data[0]
            total_amount = float(expense.get("amount", 0))
            new_total_paid = amount_paid
            
            # Determine status
            if new_total_paid >= total_amount:
                status = "paid"
                new_total_paid = total_amount
            elif new_total_paid > 0:
                status = "partial"
            else:
                status = "pending"
            
            # Update expense
            update_data = {
                "amount_paid": new_total_paid,
                "status": status,
                "last_payment_date": datetime.now().isoformat()
            }
            
            await db_execute(lambda: supabase.table("procurement_expenses")
                .update(update_data)
                .eq("id", expense_id)
                .execute()
            )
            
            return True, f"Updated expense to {status} (₦{new_total_paid:,.0f})"
        except Exception as e:
            return False, f"Error updating expense: {str(e)}"
    
    async def get_cost_summary(self, project_id: str) -> Dict:
        """Get comprehensive cost summary for project"""
        try:
            status = await self.get_procurement_status(project_id)
            if "error" in status:
                return status
            
            expenses = status['expenses']
            
            # Breakdown by category
            by_category = {}
            by_section = {}
            by_status = {}
            
            for exp in expenses:
                category = exp.get('category', 'Other')
                section = exp.get('section', 'Other')
                exp_status = exp.get('status', 'pending')
                amount = float(exp.get('amount', 0))
                
                by_category[category] = by_category.get(category, 0) + amount
                by_section[section] = by_section.get(section, 0) + amount
                by_status[exp_status] = by_status.get(exp_status, 0) + amount
            
            return {
                "total_budget": status['total_budget'],
                "total_paid": status['total_paid'],
                "total_pending": status['total_pending'],
                "payment_percentage": status['payment_percentage'],
                "by_category": by_category,
                "by_section": by_section,
                "by_status": by_status,
                "item_count": status['item_count']
            }
        except Exception as e:
            return {"error": str(e)}


# Example usage script
async def main():
    """Example: Import a quotation"""
    manager = ProcurementDatabaseManager()
    
    filepath = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\eximps-cloves quotation.xlsx'
    
    # Import quotation
    success, message = await manager.import_quotation(
        filepath,
        property_id=None,  # Optional: set property_id if needed
        estate_draft_id=None  # Optional: set estate_draft_id if needed
    )
    
    if success:
        print("\n" + "="*80)
        print("✅ IMPORT SUCCESSFUL")
        print("="*80)
        print(f"Total expenses inserted: {len(manager.inserted_expenses)}")
        print(f"Total budget: ₦{sum(s.total_amount for s in manager.sections):,.2f}")
    else:
        print(f"\n❌ IMPORT FAILED: {message}")


if __name__ == "__main__":
    asyncio.run(main())
