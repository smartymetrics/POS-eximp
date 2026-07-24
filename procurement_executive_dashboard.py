"""
PROCUREMENT EXECUTIVE DASHBOARD
Eximp & Cloves Infrastructure Limited - ERP System
====================================================

Professional dashboard for CEO/Management to monitor procurement spend,
risks, and financial health at a glance.
"""

import json
from datetime import datetime
from procurement_parser import QuotationParser
from procurement_analytics import ProcurementAnalytics


class ProcurementDashboard:
    """Generates executive dashboard HTML with KPIs and visualizations"""
    
    def __init__(self, sections, metadata):
        self.sections = sections
        self.metadata = metadata
        self.analytics = ProcurementAnalytics(sections, metadata)
    
    def generate_html(self, output_path: str = "procurement_dashboard_executive.html"):
        """Generate complete HTML dashboard"""
        summary = self.analytics.get_executive_summary()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Procurement Dashboard - Eximp & Cloves</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        
        .project-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
            font-size: 14px;
            color: #666;
        }}
        
        .project-info div {{
            padding: 10px;
            background: #f5f5f5;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        
        .project-info strong {{
            display: block;
            color: #333;
            margin-bottom: 5px;
            font-weight: 600;
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .kpi-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }}
        
        .kpi-card.warning {{
            border-left-color: #f59e0b;
        }}
        
        .kpi-card.success {{
            border-left-color: #10b981;
        }}
        
        .kpi-card.danger {{
            border-left-color: #ef4444;
        }}
        
        .kpi-label {{
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        .kpi-value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .kpi-subtext {{
            font-size: 13px;
            color: #666;
        }}
        
        .chart-section {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .chart-section h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        .risks-section {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .risks-section h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 20px;
            border-bottom: 2px solid #f59e0b;
            padding-bottom: 10px;
        }}
        
        .risk-item {{
            padding: 15px;
            margin-bottom: 15px;
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
        }}
        
        .risk-item.high {{
            background: #fee2e2;
            border-left-color: #ef4444;
        }}
        
        .risk-item.medium {{
            background: #fef3c7;
            border-left-color: #f59e0b;
        }}
        
        .risk-item.low {{
            background: #dbeafe;
            border-left-color: #3b82f6;
        }}
        
        .risk-type {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .risk-description {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        
        .risk-recommendation {{
            color: #555;
            font-size: 13px;
            font-style: italic;
            padding-top: 8px;
            border-top: 1px solid rgba(0,0,0,0.1);
        }}
        
        .top-items {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .top-items h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .item-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }}
        
        .item-row:last-child {{
            border-bottom: none;
        }}
        
        .item-name {{
            flex: 1;
            font-weight: 500;
            color: #333;
        }}
        
        .item-amount {{
            font-weight: bold;
            color: #667eea;
            min-width: 120px;
            text-align: right;
        }}
        
        .item-percentage {{
            color: #999;
            min-width: 70px;
            text-align: right;
        }}
        
        .recommendations {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .recommendations h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 20px;
            border-bottom: 2px solid #10b981;
            padding-bottom: 10px;
        }}
        
        .recommendation-item {{
            padding: 12px 0;
            padding-left: 30px;
            position: relative;
            color: #555;
            line-height: 1.6;
        }}
        
        .recommendation-item::before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #10b981;
            font-weight: bold;
            font-size: 18px;
        }}
        
        footer {{
            text-align: center;
            color: white;
            padding: 20px;
            font-size: 12px;
        }}
        
        @media (max-width: 768px) {{
            .kpi-grid {{
                grid-template-columns: 1fr;
            }}
            
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            h1 {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <h1>🏢 Procurement Dashboard</h1>
            <p style="color: #999; margin: 5px 0;">Eximp & Cloves Infrastructure Limited</p>
            
            <div class="project-info">
                <div>
                    <strong>Location</strong>
                    {self.metadata.get('location', 'N/A')}
                </div>
                <div>
                    <strong>Quotation Date</strong>
                    {self.metadata.get('quotation_date', 'N/A')}
                </div>
                <div>
                    <strong>Sections</strong>
                    {len(self.sections)} sections
                </div>
                <div>
                    <strong>Items</strong>
                    {len([i for s in self.sections for i in s.items])} line items
                </div>
                <div>
                    <strong>Generated</strong>
                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </header>
        
        <!-- KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Total Project Budget</div>
                <div class="kpi-value">₦{summary['metrics']['total_budget']:,.0f}</div>
                <div class="kpi-subtext">All procurement costs</div>
            </div>
            
            <div class="kpi-card warning">
                <div class="kpi-label">Average Item Cost</div>
                <div class="kpi-value">₦{summary['metrics']['avg_item_cost']:,.0f}</div>
                <div class="kpi-subtext">Across {summary['metrics']['total_items']} items</div>
            </div>
            
            <div class="kpi-card danger">
                <div class="kpi-label">High-Value Items</div>
                <div class="kpi-value">{len([i for i in summary['top_items'][:3]])}</div>
                <div class="kpi-subtext">Items >10% of budget</div>
            </div>
            
            <div class="kpi-card success">
                <div class="kpi-label">Cost Optimization</div>
                <div class="kpi-value">{len(summary['opportunities'])}</div>
                <div class="kpi-subtext">Savings opportunities identified</div>
            </div>
        </div>
        
        <!-- Charts Section -->
        <div class="charts-grid">
            <div class="chart-section">
                <h2>Cost Breakdown by Section</h2>
                <div class="chart-container">
                    <canvas id="sectionChart"></canvas>
                </div>
            </div>
            
            <div class="chart-section">
                <h2>Cost Breakdown by Category</h2>
                <div class="chart-container">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Top Expense Items -->
        <div class="top-items">
            <h2>Top 10 Expense Items</h2>
            {self._generate_top_items_html(summary['top_items'])}
        </div>
        
        <!-- Risks Section -->
        {self._generate_risks_html(summary['risks']) if summary['risks'] else ''}
        
        <!-- Recommendations -->
        <div class="recommendations">
            <h2>Management Recommendations</h2>
            {self._generate_recommendations_html(summary['recommendations'])}
        </div>
        
        <!-- Key Insights -->
        <div class="chart-section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin-bottom: 30px;">
            <h2 style="border-bottom-color: rgba(255,255,255,0.3); color: white;">Key Insights & Findings</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 15px;">
                {self._generate_insights_html(summary['insights'])}
            </div>
        </div>
        
        <footer>
            Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} | Eximp & Cloves Infrastructure Limited
        </footer>
    </div>
    
    <script>
        // Section Chart
        const sectionData = {json.dumps(summary['metrics']['cost_per_section'])};
        new Chart(document.getElementById('sectionChart'), {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(sectionData),
                datasets: [{{
                    data: Object.values(sectionData),
                    backgroundColor: [
                        '#667eea',
                        '#764ba2',
                        '#f093fb',
                        '#4facfe',
                        '#43e97b'
                    ],
                    borderColor: '#fff',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
        
        // Category Chart
        const categoryData = {json.dumps(summary['cost_distribution']['by_category'])};
        new Chart(document.getElementById('categoryChart'), {{
            type: 'bar',
            data: {{
                labels: Object.keys(categoryData),
                datasets: [{{
                    label: 'Cost Distribution (%)',
                    data: Object.values(categoryData),
                    backgroundColor: '#667eea',
                    borderColor: '#667eea',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ Dashboard saved to: {output_path}")
        return output_path
    
    def _generate_top_items_html(self, items):
        html = ""
        for item in items:
            html += f"""
            <div class="item-row">
                <div class="item-name">{item['rank']}. {item['description'][:50]}</div>
                <div class="item-amount">₦{item['amount']:,.0f}</div>
                <div class="item-percentage">{item['percentage_of_total']:.1f}%</div>
            </div>
            """
        return html
    
    def _generate_risks_html(self, risks):
        html = '<div class="risks-section"><h2>⚠️ Identified Risks & Concerns</h2>'
        for risk in risks:
            severity_class = risk['severity'].lower()
            html += f"""
            <div class="risk-item {severity_class}">
                <div class="risk-type">{risk['type']} - {risk['severity']}</div>
                <div class="risk-description">{risk['description']}</div>
                <div class="risk-recommendation">→ {risk['recommendation']}</div>
            </div>
            """
        html += '</div>'
        return html
    
    def _generate_insights_html(self, insights):
        html = ""
        icons = ['⚠️', '📊', '💰', '🎯', '📈']
        for i, insight in enumerate(insights):
            icon = icons[i % len(icons)]
            html += f"""
            <div style="padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; border-left: 4px solid white;">
                <div style="font-size: 18px; margin-bottom: 8px;">{icon}</div>
                <div style="font-size: 14px; line-height: 1.5;">{insight}</div>
            </div>
            """
        return html
    
    def _generate_recommendations_html(self, recommendations):
        html = ""
        for rec in recommendations:
            html += f'<div class="recommendation-item">{rec}</div>'
        return html


if __name__ == "__main__":
    # Generate dashboard
    filepath = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\eximps-cloves quotation.xlsx'
    
    parser = QuotationParser(filepath)
    sections, metadata = parser.parse()
    
    dashboard = ProcurementDashboard(sections, metadata)
    dashboard.generate_html()
    
    print("\n✅ Executive dashboard generated successfully!")
