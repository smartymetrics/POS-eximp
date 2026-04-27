import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix the specific broken lines
    broken_lines = [
        ('{ id: "manual", label:', '    { id: "manual", label: "✍️ Manual Entry", desc: "Manager must update the actual value manually." },'),
        ('{ id: "mkt_leads_added", label:', '    { id: "mkt_leads_added", label: "🤖 Leads Generated (CRM)", desc: "Counts distinct contacts added to CRM/Marketing by the staff." },'),
        ('{ id: "mkt_lead_conversion", label:', '    { id: "mkt_lead_conversion", label: "📈 Lead Conversion (%)", desc: "Percentage of leads converted to paying clients." },'),
        ('{ id: "sales_revenue", label:', '    { id: "sales_revenue", label: "💰 Sales Revenue (Paid)", desc: "Total sum of payments recorded by this staff." },'),
        ('{ id: "sales_deals_closed", label:', '    { id: "sales_deals_closed", label: "🤝 Deals Closed", desc: "Count of invoices marked as \'Closed\' by this staff." },'),
        ('{ id: "ops_appointments", label:', '    { id: "ops_appointments", label: "📅 Appts Completed", desc: "Count of appointments successfully completed." },'),
        ('{ id: "admin_ticket_esc", label:', '    { id: "admin_ticket_esc", label: "🎫 Support Efficiency", desc: "Count of pending vs resolved tickets." },'),
    ]

    lines = content.splitlines()
    new_lines = []
    for line in lines:
        fixed = False
        for start, replacement in broken_lines:
            if start in line:
                new_lines.append(replacement)
                fixed = True
                break
        if not fixed:
            new_lines.append(line)
            
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(new_lines))
    print("Repair successful")
except Exception as e:
    print(f"Error: {e}")
