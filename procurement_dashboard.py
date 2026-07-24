"""
Procurement Dashboard - Professional Analysis & Reporting
=============================================================
Analyzes estate procurement costs and generates executive-level insights
for management and CEO review.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass

# Set style for professional charts
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

@dataclass
class ProcurementMetrics:
    """Container for procurement KPIs"""
    total_budget: float
    total_spent: float
    budget_utilization: float
    total_items: int
    categories: Dict[str, float]
    pending_amount: float
    approved_amount: float
    completed_amount: float
    average_unit_cost: float
    cost_variance: float


class ProcurementAnalyzer:
    """Professional procurement analysis engine"""
    
    def __init__(self, data_path: str):
        """Initialize analyzer with procurement data"""
        self.file_path = Path(data_path)
        self.df = None
        self.load_data()
        
    def load_data(self):
        """Load and clean procurement data"""
        try:
            # Try to load from properly structured sheet first
            self.df = pd.read_excel(self.file_path, sheet_name="Procurement")
        except:
            try:
                # Fallback to raw import
                self.df = pd.read_excel(self.file_path, sheet_name="Sheet1")
                self._structure_raw_data()
            except Exception as e:
                print(f"❌ Error loading file: {e}")
                return False
        
        print(f"✅ Loaded {len(self.df)} procurement items")
        return True
    
    def _structure_raw_data(self):
        """Convert raw quotation data into structured format"""
        # This would extract data from rows 13-23 and 33-37 of the quotation sheet
        pass
    
    def calculate_metrics(self) -> ProcurementMetrics:
        """Calculate key procurement metrics"""
        df = self.df.copy()
        
        # Ensure numeric columns
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Unit Price'] = pd.to_numeric(df['Unit Price'], errors='coerce')
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        
        total_spent = df['Amount'].sum()
        total_budget = df.get('Budget', pd.Series([total_spent])).sum()
        
        # Status-based analysis
        pending = df[df['Status'] == 'Pending']['Amount'].sum()
        approved = df[df['Status'] == 'Approved']['Amount'].sum()
        completed = df[df['Status'] == 'Completed']['Amount'].sum()
        
        # Category breakdown
        category_spend = df.groupby('Category')['Amount'].sum().to_dict()
        
        # Average costs
        avg_unit_cost = df['Unit Price'].mean()
        
        # Budget variance
        cost_variance = ((total_spent - total_budget) / total_budget * 100) if total_budget > 0 else 0
        
        return ProcurementMetrics(
            total_budget=total_budget,
            total_spent=total_spent,
            budget_utilization=(total_spent / total_budget * 100) if total_budget > 0 else 0,
            total_items=len(df),
            categories=category_spend,
            pending_amount=pending if not pd.isna(pending) else 0,
            approved_amount=approved if not pd.isna(approved) else 0,
            completed_amount=completed if not pd.isna(completed) else 0,
            average_unit_cost=avg_unit_cost,
            cost_variance=cost_variance
        )
    
    def generate_executive_summary(self) -> Dict:
        """Generate executive summary for CEO/Management"""
        metrics = self.calculate_metrics()
        
        summary = {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project": "Estate Procurement - Agbowa Ikorodu",
            
            # Financial Summary
            "financial_summary": {
                "total_allocated_budget": f"₦{metrics.total_budget:,.0f}",
                "total_expended": f"₦{metrics.total_spent:,.0f}",
                "budget_utilization_percent": f"{metrics.budget_utilization:.1f}%",
                "remaining_budget": f"₦{metrics.total_budget - metrics.total_spent:,.0f}",
                "cost_variance_percent": f"{metrics.cost_variance:+.1f}%"
            },
            
            # Status Breakdown
            "status_breakdown": {
                "pending": f"₦{metrics.pending_amount:,.0f}",
                "approved": f"₦{metrics.approved_amount:,.0f}",
                "completed": f"₦{metrics.completed_amount:,.0f}",
                "total_items": metrics.total_items
            },
            
            # Category Breakdown
            "category_breakdown": {
                k: f"₦{v:,.0f}" for k, v in metrics.categories.items()
            },
            
            # Key Metrics
            "key_metrics": {
                "average_unit_cost": f"₦{metrics.average_unit_cost:,.0f}",
                "total_categories": len(metrics.categories),
                "items_pending_approval": len(self.df[self.df['Status'] == 'Pending'])
            }
        }
        
        return summary
    
    def generate_category_analysis(self) -> pd.DataFrame:
        """Detailed category-level analysis"""
        df = self.df.copy()
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        category_analysis = df.groupby('Category').agg({
            'Amount': ['sum', 'mean', 'count'],
            'Unit Price': 'mean',
            'Quantity': 'sum'
        }).round(0)
        
        category_analysis.columns = ['Total Cost', 'Avg Cost/Item', 'Item Count', 'Avg Unit Price', 'Total Quantity']
        category_analysis = category_analysis.reset_index()
        category_analysis['Percentage of Total'] = (
            category_analysis['Total Cost'] / category_analysis['Total Cost'].sum() * 100
        ).round(1)
        
        return category_analysis.sort_values('Total Cost', ascending=False)
    
    def generate_vendor_analysis(self) -> pd.DataFrame:
        """Analyze vendor performance and costs"""
        df = self.df.copy()
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        if 'Vendor' not in df.columns:
            return pd.DataFrame()
        
        vendor_analysis = df.groupby('Vendor').agg({
            'Amount': ['sum', 'count', 'mean'],
            'Status': lambda x: (x == 'Completed').sum()
        }).round(0)
        
        vendor_analysis.columns = ['Total Spend', 'Items Supplied', 'Avg Item Cost', 'Completed Items']
        vendor_analysis['On-Time Delivery %'] = (
            vendor_analysis['Completed Items'] / vendor_analysis['Items Supplied'] * 100
        ).round(1)
        
        return vendor_analysis.reset_index().sort_values('Total Spend', ascending=False)
    
    def generate_timeline_analysis(self) -> Dict:
        """Analyze procurement timeline and spending pace"""
        df = self.df.copy()
        
        if 'Date' not in df.columns:
            return {"note": "Date column not available for timeline analysis"}
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        daily_spend = df.groupby(df['Date'].dt.date)['Amount'].agg(['sum', 'count'])
        
        return {
            "daily_average_spend": f"₦{daily_spend['sum'].mean():,.0f}",
            "spending_pace": f"{daily_spend['count'].sum()} items over {len(daily_spend)} days",
            "peak_spend_day": f"₦{daily_spend['sum'].max():,.0f}",
            "low_spend_day": f"₦{daily_spend['sum'].min():,.0f}"
        }
    
    def generate_variance_analysis(self) -> pd.DataFrame:
        """Analyze cost variance by category"""
        df = self.df.copy()
        df['Unit Price'] = pd.to_numeric(df['Unit Price'], errors='coerce')
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        if 'Budgeted Amount' not in df.columns:
            return pd.DataFrame({"Note": ["Budget variance analysis requires 'Budgeted Amount' column"]})
        
        df['Budgeted Amount'] = pd.to_numeric(df['Budgeted Amount'], errors='coerce')
        df['Variance'] = df['Amount'] - df['Budgeted Amount']
        df['Variance %'] = (df['Variance'] / df['Budgeted Amount'] * 100).round(1)
        
        variance_summary = df.groupby('Category').agg({
            'Variance': 'sum',
            'Variance %': 'mean'
        }).round(1)
        
        return variance_summary.reset_index().sort_values('Variance', ascending=False)
    
    def create_visualizations(self, output_dir: str = "procurement_reports"):
        """Generate professional charts for presentation"""
        Path(output_dir).mkdir(exist_ok=True)
        
        metrics = self.calculate_metrics()
        df = self.df.copy()
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        # 1. Budget Utilization Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        spent = metrics.total_spent
        remaining = metrics.total_budget - metrics.total_spent
        
        categories = ['Expended', 'Remaining']
        values = [spent, remaining]
        colors = ['#2ecc71', '#3498db']
        
        ax.bar(categories, values, color=colors, edgecolor='black', linewidth=1.5)
        ax.set_ylabel('Amount (₦)', fontsize=12, fontweight='bold')
        ax.set_title('Budget Utilization - Procurement Dashboard', fontsize=14, fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₦{x/1e6:.1f}M'))
        
        for i, v in enumerate(values):
            ax.text(i, v + max(values)*0.02, f"₦{v:,.0f}\n({v/metrics.total_budget*100:.1f}%)", 
                   ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/01_budget_utilization.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Category Breakdown
        category_data = df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(category_data.index, category_data.values, color=sns.color_palette("husl", len(category_data)))
        ax.set_xlabel('Amount (₦)', fontsize=12, fontweight='bold')
        ax.set_title('Procurement by Category', fontsize=14, fontweight='bold')
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₦{x/1e6:.1f}M'))
        
        for i, (idx, v) in enumerate(category_data.items()):
            ax.text(v + max(category_data)*0.01, i, f'₦{v:,.0f}', va='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/02_category_breakdown.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Status Distribution (if Status column exists)
        if 'Status' in df.columns:
            status_data = df['Status'].value_counts()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            colors = ['#2ecc71', '#f39c12', '#e74c3c']
            wedges, texts, autotexts = ax.pie(status_data.values, labels=status_data.index, autopct='%1.1f%%',
                                               colors=colors[:len(status_data)], startangle=90)
            ax.set_title('Procurement Items by Status', fontsize=14, fontweight='bold')
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/03_status_distribution.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        print(f"✅ Visualizations saved to {output_dir}/")
    
    def export_comprehensive_report(self, output_path: str = "procurement_report.xlsx"):
        """Export comprehensive multi-sheet Excel report"""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Executive Summary
            summary = self.generate_executive_summary()
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            
            # Category Analysis
            category_analysis = self.generate_category_analysis()
            category_analysis.to_excel(writer, sheet_name='Category Analysis', index=False)
            
            # Raw Data
            self.df.to_excel(writer, sheet_name='Detailed Data', index=False)
            
            # Vendor Analysis (if applicable)
            vendor_analysis = self.generate_vendor_analysis()
            if not vendor_analysis.empty:
                vendor_analysis.to_excel(writer, sheet_name='Vendor Analysis', index=False)
            
            # Timeline Analysis
            timeline = self.generate_timeline_analysis()
            timeline_df = pd.DataFrame([timeline])
            timeline_df.to_excel(writer, sheet_name='Timeline Analysis', index=False)
        
        print(f"✅ Comprehensive report exported to {output_path}")


def run_dashboard_analysis(file_path: str):
    """Main execution function"""
    print("="*70)
    print("PROCUREMENT DASHBOARD - EXECUTIVE ANALYSIS REPORT")
    print("="*70)
    print()
    
    analyzer = ProcurementAnalyzer(file_path)
    
    # Generate and display executive summary
    print("\n📊 EXECUTIVE SUMMARY")
    print("-"*70)
    summary = analyzer.generate_executive_summary()
    
    print(f"\nReport Date: {summary['report_date']}")
    print(f"Project: {summary['project']}")
    
    print("\n💰 FINANCIAL SUMMARY:")
    for key, value in summary['financial_summary'].items():
        print(f"   • {key.replace('_', ' ').title()}: {value}")
    
    print("\n📋 STATUS BREAKDOWN:")
    for key, value in summary['status_breakdown'].items():
        print(f"   • {key.title()}: {value}")
    
    print("\n🏗️  CATEGORY BREAKDOWN:")
    for category, value in summary['category_breakdown'].items():
        print(f"   • {category}: {value}")
    
    print("\n📈 CATEGORY ANALYSIS:")
    print("-"*70)
    category_analysis = analyzer.generate_category_analysis()
    print(category_analysis.to_string(index=False))
    
    print("\n🚚 VENDOR ANALYSIS:")
    print("-"*70)
    vendor_analysis = analyzer.generate_vendor_analysis()
    if not vendor_analysis.empty:
        print(vendor_analysis.to_string(index=False))
    else:
        print("   (Vendor column not available)")
    
    print("\n📅 TIMELINE ANALYSIS:")
    print("-"*70)
    timeline = analyzer.generate_timeline_analysis()
    for key, value in timeline.items():
        print(f"   • {key.replace('_', ' ').title()}: {value}")
    
    # Generate visualizations
    print("\n📊 GENERATING VISUALIZATIONS...")
    analyzer.create_visualizations()
    
    # Export comprehensive report
    print("\n💾 EXPORTING COMPREHENSIVE REPORT...")
    analyzer.export_comprehensive_report()
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    # Change to your file path
    file_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\eximps-cloves quotation.xlsx"
    run_dashboard_analysis(file_path)
