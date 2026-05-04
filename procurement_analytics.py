"""
PROCUREMENT ANALYTICS & INSIGHTS ENGINE
Eximp & Cloves Infrastructure Limited - ERP System
====================================================

Advanced analytics for procurement data.
Generates professional reports with executive insights and KPIs.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
from procurement_parser import QuotationParser, ProcurementSection, ProcurementItem


class ProcurementAnalytics:
    """Professional analytics engine for procurement data"""
    
    def __init__(self, sections: List[ProcurementSection], metadata: Dict):
        self.sections = sections
        self.metadata = metadata
        self.all_items = []
        for section in sections:
            self.all_items.extend(section.items)
    
    # ══════════════════════════════════════════════════════════════════════════
    # CORE METRICS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_total_project_cost(self) -> Decimal:
        """Total procurement budget"""
        return sum(s.total_amount for s in self.sections)
    
    def get_cost_by_section(self) -> Dict[str, float]:
        """Cost breakdown by section"""
        return {s.name: float(s.total_amount) for s in self.sections}
    
    def get_cost_by_category(self) -> Dict[str, float]:
        """Cost breakdown by category"""
        breakdown = {}
        for item in self.all_items:
            if item.category not in breakdown:
                breakdown[item.category] = Decimal(0)
            breakdown[item.category] += item.amount
        return {cat: float(amt) for cat, amt in breakdown.items()}
    
    def get_cost_by_quantity_unit(self) -> Dict[str, float]:
        """Cost breakdown by quantity unit (units, tons, days, etc.)"""
        breakdown = {}
        for item in self.all_items:
            key = item.quantity_unit.title()
            if key not in breakdown:
                breakdown[key] = Decimal(0)
            breakdown[key] += item.amount
        return {unit: float(amt) for unit, amt in breakdown.items()}
    
    # ══════════════════════════════════════════════════════════════════════════
    # LINE ITEM ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_top_expense_items(self, top_n: int = 10) -> List[Dict]:
        """Get top N expense items by amount"""
        sorted_items = sorted(self.all_items, key=lambda x: x.amount, reverse=True)
        return [
            {
                'rank': idx + 1,
                'description': item.description,
                'quantity': item.quantity,
                'quantity_unit': item.quantity_unit,
                'unit_price': float(item.unit_price),
                'amount': float(item.amount),
                'percentage_of_total': (float(item.amount) / float(self.get_total_project_cost()) * 100),
                'category': item.category,
                'section': item.section
            }
            for idx, item in enumerate(sorted_items[:top_n])
        ]
    
    def get_lowest_expense_items(self, bottom_n: int = 5) -> List[Dict]:
        """Get lowest N expense items"""
        sorted_items = sorted(self.all_items, key=lambda x: x.amount)
        return [
            {
                'description': item.description,
                'amount': float(item.amount),
                'percentage_of_total': (float(item.amount) / float(self.get_total_project_cost()) * 100),
                'category': item.category
            }
            for item in sorted_items[:bottom_n]
        ]
    
    # ══════════════════════════════════════════════════════════════════════════
    # COST DISTRIBUTION ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_cost_distribution(self) -> Dict:
        """Comprehensive cost distribution analysis"""
        total = float(self.get_total_project_cost())
        
        by_section = {k: (v/total*100) for k, v in self.get_cost_by_section().items()}
        by_category = {k: (v/total*100) for k, v in self.get_cost_by_category().items()}
        
        return {
            'by_section': by_section,
            'by_category': by_category,
            'largest_section': max(self.get_cost_by_section().items(), key=lambda x: x[1])[0],
            'largest_category': max(self.get_cost_by_category().items(), key=lambda x: x[1])[0]
        }
    
    def get_concentration_analysis(self) -> Dict:
        """Analyze spending concentration (Pareto analysis)"""
        total = float(self.get_total_project_cost())
        sorted_items = sorted(self.all_items, key=lambda x: x.amount, reverse=True)
        
        cumulative = 0
        pareto_items = []
        for item in sorted_items:
            cumulative += float(item.amount)
            percentage = (cumulative / total) * 100
            pareto_items.append({
                'description': item.description,
                'amount': float(item.amount),
                'cumulative_percentage': percentage
            })
            if percentage >= 80:  # Pareto principle - 80/20
                break
        
        items_for_80_percent = len(pareto_items)
        item_count_percent = (items_for_80_percent / len(self.all_items)) * 100
        
        return {
            'pareto_items': pareto_items,
            'items_for_80_percent': items_for_80_percent,
            'total_items': len(self.all_items),
            'item_concentration_percent': item_count_percent,
            'insight': f"{item_count_percent:.1f}% of items drive 80% of costs"
        }
    
    # ══════════════════════════════════════════════════════════════════════════
    # PROCUREMENT RISK & OPPORTUNITY ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_unit_price_analysis(self) -> Dict:
        """Analyze unit prices for anomalies"""
        by_category = {}
        for item in self.all_items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(float(item.unit_price))
        
        analysis = {}
        for category, prices in by_category.items():
            prices_arr = np.array(prices)
            analysis[category] = {
                'avg_unit_price': float(np.mean(prices_arr)),
                'min_unit_price': float(np.min(prices_arr)),
                'max_unit_price': float(np.max(prices_arr)),
                'std_dev': float(np.std(prices_arr)),
                'price_range': float(np.max(prices_arr) - np.min(prices_arr))
            }
        
        return analysis
    
    def get_cost_risks(self) -> List[Dict]:
        """Identify potential cost risks"""
        risks = []
        total = float(self.get_total_project_cost())
        
        # High-value items risk
        high_value_items = [item for item in self.all_items if float(item.amount) > total * 0.10]
        if high_value_items:
            risks.append({
                'type': 'HIGH-VALUE CONCENTRATION',
                'severity': 'MEDIUM',
                'description': f"{len(high_value_items)} items represent >10% of budget each",
                'items': [
                    {'description': item.description, 'amount': float(item.amount), 'percentage': float(item.amount)/total*100}
                    for item in high_value_items
                ],
                'recommendation': 'Request multiple quotes for high-value items'
            })
        
        # Labour cost concentration
        labour_items = [item for item in self.all_items if 'labour' in item.description.lower()]
        labour_total = sum(float(item.amount) for item in labour_items)
        labour_percent = labour_total / total * 100 if total > 0 else 0
        
        if labour_percent > 20:
            risks.append({
                'type': 'HIGH LABOUR COST',
                'severity': 'MEDIUM',
                'description': f"Labour represents {labour_percent:.1f}% of total budget",
                'amount': labour_total,
                'percentage': labour_percent,
                'recommendation': 'Consider mechanization or bulk labour contracts'
            })
        
        # Equipment rental concentration
        equipment_items = [item for item in self.all_items if any(w in item.description.lower() for w in ['excavator', 'loader', 'truck', 'crane'])]
        equipment_total = sum(float(item.amount) for item in equipment_items)
        equipment_percent = equipment_total / total * 100 if total > 0 else 0
        
        if equipment_percent > 15:
            risks.append({
                'type': 'EQUIPMENT RENTAL DEPENDENCY',
                'severity': 'LOW',
                'description': f"Equipment rental represents {equipment_percent:.1f}% of budget",
                'amount': equipment_total,
                'recommendation': 'Negotiate long-term rates or consider purchase'
            })
        
        return risks
    
    def get_cost_optimization_opportunities(self) -> List[Dict]:
        """Identify potential cost savings opportunities"""
        opportunities = []
        
        # Bulk material optimization
        materials = {
            'Cement': [item for item in self.all_items if 'cement' in item.description.lower()],
            'Blocks': [item for item in self.all_items if 'blocks' in item.description.lower()],
            'Sand': [item for item in self.all_items if 'sand' in item.description.lower()],
        }
        
        for material, items in materials.items():
            if len(items) > 1:
                total_qty = sum(item.quantity for item in items)
                avg_unit_price = np.mean([float(item.unit_price) for item in items])
                bulk_discount_potential = avg_unit_price * total_qty * 0.05  # 5% potential saving
                
                opportunities.append({
                    'type': 'BULK PURCHASING',
                    'material': material,
                    'description': f"Consolidate {len(items)} separate {material} purchases",
                    'total_quantity': total_qty,
                    'items_count': len(items),
                    'current_avg_unit_price': float(avg_unit_price),
                    'estimated_savings_5_percent': float(bulk_discount_potential),
                    'recommendation': f"Consolidate {len(items)} separate {material} purchases for bulk discount"
                })
        
        # Accommodation consolidation
        accommodation = [item for item in self.all_items if 'accommodation' in item.description.lower()]
        if accommodation:
            accom_total = sum(float(item.amount) for item in accommodation)
            opportunities.append({
                'type': 'ACCOMMODATION NEGOTIATION',
                'description': 'Negotiate bulk accommodation rates',
                'current_cost': float(accom_total),
                'estimated_savings_10_percent': float(accom_total * 0.10),
                'recommendation': 'Negotiate bulk accommodation rates with local hotels'
            })
        
        # Transportation efficiency
        transport_items = [item for item in self.all_items if 'truck' in item.description.lower()]
        if transport_items:
            transport_total = sum(float(item.amount) for item in transport_items)
            opportunities.append({
                'type': 'TRANSPORT CONSOLIDATION',
                'description': 'Schedule transportation efficiently',
                'current_cost': float(transport_total),
                'estimated_savings_10_percent': float(transport_total * 0.10),
                'recommendation': 'Schedule transportation efficiently to minimize trips'
            })
        
        return opportunities
    
    # ══════════════════════════════════════════════════════════════════════════
    # EXECUTIVE INSIGHTS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_executive_summary(self) -> Dict:
        """Generate executive-level summary"""
        total_cost = float(self.get_total_project_cost())
        
        # Key metrics
        metrics = {
            'total_budget': total_cost,
            'total_items': len(self.all_items),
            'total_sections': len(self.sections),
            'avg_item_cost': total_cost / len(self.all_items) if self.all_items else 0,
            'cost_per_section': {s.name: float(s.total_amount) for s in self.sections}
        }
        
        # Top risks
        risks = self.get_cost_risks()
        
        # Opportunities
        opportunities = self.get_cost_optimization_opportunities()
        
        # Pareto analysis
        pareto = self.get_concentration_analysis()
        
        # Insights
        insights = []
        
        # Insight 1: Cost concentration
        largest_section = self.get_cost_distribution()['largest_section']
        largest_section_cost = self.get_cost_by_section()[largest_section]
        largest_section_pct = (largest_section_cost / total_cost) * 100
        insights.append(f"⚠ {largest_section} accounts for {largest_section_pct:.1f}% of total project cost (₦{largest_section_cost:,.0f})")
        
        # Insight 2: Item concentration
        top_10_items = self.get_top_expense_items(10)
        top_10_total = sum(item['amount'] for item in top_10_items)
        top_10_pct = (top_10_total / total_cost) * 100
        insights.append(f"📊 Top 10 items represent {top_10_pct:.1f}% of budget (₦{top_10_total:,.0f}) - high spending concentration")
        
        # Insight 3: Potential savings
        total_opportunity = sum(
            opp.get('estimated_savings_5_percent', 0) + opp.get('estimated_savings_10_percent', 0)
            for opp in opportunities
        )
        if total_opportunity > 0:
            savings_pct = (total_opportunity / total_cost) * 100
            insights.append(f"💰 Identified ₦{total_opportunity:,.0f} in cost optimization opportunities ({savings_pct:.1f}% of budget)")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'metadata': self.metadata,
            'metrics': metrics,
            'cost_distribution': self.get_cost_distribution(),
            'top_items': top_10_items,
            'risks': risks,
            'opportunities': opportunities,
            'pareto_analysis': pareto,
            'insights': insights,
            'recommendations': self._generate_recommendations(risks, opportunities)
        }
    
    def _generate_recommendations(self, risks: List[Dict], opportunities: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if risks:
            recommendations.append(f"ADDRESS IDENTIFIED RISKS: {len(risks)} risk areas identified requiring management attention")
        
        if opportunities:
            recommendations.append(f"PURSUE COST SAVINGS: {len(opportunities)} optimization opportunities identified")
        
        # Specific recommendations
        if any('HIGH-VALUE CONCENTRATION' in r.get('type', '') for r in risks):
            recommendations.append("REQUEST MULTIPLE QUOTES for high-value items to ensure competitive pricing")
        
        if any('BULK PURCHASING' in o.get('type', '') for o in opportunities):
            recommendations.append("CONSOLIDATE MATERIAL PURCHASES to negotiate bulk discounts")
        
        recommendations.append("ESTABLISH VENDOR MANAGEMENT POLICY to ensure ongoing cost control")
        recommendations.append("IMPLEMENT CONTINGENCY RESERVE: Current budget should include 10-15% contingency")
        
        return recommendations
    
    # ══════════════════════════════════════════════════════════════════════════
    # REPORTING
    # ══════════════════════════════════════════════════════════════════════════
    
    def generate_json_report(self, output_path: str = None) -> str:
        """Generate comprehensive JSON report"""
        report = self.get_executive_summary()
        
        json_str = json.dumps(report, indent=2, default=str)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def generate_text_report(self) -> str:
        """Generate human-readable text report"""
        summary = self.get_executive_summary()
        
        lines = []
        lines.append("="*80)
        lines.append("PROCUREMENT ANALYSIS REPORT")
        lines.append("EXIMP & CLOVES INFRASTRUCTURE LIMITED")
        lines.append("="*80)
        lines.append("")
        
        # Header
        lines.append("PROJECT INFORMATION")
        lines.append("-" * 80)
        lines.append(f"Location: {summary['metadata'].get('location', 'N/A')}")
        lines.append(f"Date: {summary['metadata'].get('quotation_date', 'N/A')}")
        lines.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        metrics = summary['metrics']
        lines.append(f"Total Project Budget:        ₦{metrics['total_budget']:>15,.2f}")
        lines.append(f"Total Line Items:            {metrics['total_items']:>15,}")
        lines.append(f"Total Sections:              {metrics['total_sections']:>15,}")
        lines.append(f"Average Item Cost:           ₦{metrics['avg_item_cost']:>15,.2f}")
        lines.append("")
        
        # Key Insights
        lines.append("KEY INSIGHTS")
        lines.append("-" * 80)
        for i, insight in enumerate(summary['insights'], 1):
            lines.append(f"{i}. {insight}")
        lines.append("")
        
        # Cost Breakdown
        lines.append("COST BREAKDOWN BY SECTION")
        lines.append("-" * 80)
        for section, cost in metrics['cost_per_section'].items():
            pct = (cost / metrics['total_budget']) * 100
            lines.append(f"{section:<40} ₦{cost:>15,.2f}  ({pct:>5.1f}%)")
        lines.append("")
        
        # Top Expense Items
        lines.append("TOP 10 EXPENSE ITEMS")
        lines.append("-" * 80)
        for item in summary['top_items']:
            lines.append(f"{item['rank']:>2}. {item['description']:<45} ₦{item['amount']:>12,.2f} ({item['percentage_of_total']:>5.1f}%)")
        lines.append("")
        
        # Risks
        if summary['risks']:
            lines.append("IDENTIFIED RISKS & CONCERNS")
            lines.append("-" * 80)
            for risk in summary['risks']:
                lines.append(f"⚠  {risk['type']} ({risk['severity']})")
                lines.append(f"   {risk['description']}")
                lines.append(f"   ➜ {risk['recommendation']}")
                lines.append("")
        
        # Opportunities
        if summary['opportunities']:
            lines.append("COST OPTIMIZATION OPPORTUNITIES")
            lines.append("-" * 80)
            for opp in summary['opportunities']:
                lines.append(f"💡 {opp['type']}")
                lines.append(f"   {opp['description']}")
                lines.append(f"   ➜ {opp['recommendation']}")
                lines.append("")
        
        # Recommendations
        lines.append("MANAGEMENT RECOMMENDATIONS")
        lines.append("-" * 80)
        for i, rec in enumerate(summary['recommendations'], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        lines.append("="*80)
        
        return "\n".join(lines)


if __name__ == "__main__":
    # Test the analytics engine
    filepath = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\eximps-cloves quotation.xlsx'
    
    parser = QuotationParser(filepath)
    sections, metadata = parser.parse()
    
    analytics = ProcurementAnalytics(sections, metadata)
    
    # Generate and print report
    report_text = analytics.generate_text_report()
    print(report_text)
    
    # Save JSON report
    analytics.generate_json_report('procurement_analysis_report.json')
    print("\n✓ JSON report saved to: procurement_analysis_report.json")
