with open('templates/payouts_dashboard.html', encoding='utf-8') as f:
    content = f.read()

# Find the tabs container and add the Verification tab
old_tabs = (
    "            <div class=\"tab active\" onclick=\"switchTab('requests', event)\">Audit Queue</div>\n"
    "            <div class=\"tab\" onclick=\"switchTab('vendors', event)\">Vendor Registry</div>\n"
)
new_tabs = (
    "            <div class=\"tab active\" onclick=\"switchTab('requests', event)\">Audit Queue</div>\n"
    "            <div class=\"tab\" onclick=\"switchTab('verification', event)\" id=\"verif-tab\">Bill Verification <span id=\"verif-badge\" style=\"display:none; background:var(--error); color:#fff; font-size:10px; border-radius:8px; padding:2px 6px; margin-left:4px;\">0</span></div>\n"
    "            <div class=\"tab\" onclick=\"switchTab('vendors', event)\">Vendor Registry</div>\n"
)

# Also update renderVerifications call inside fetchRequests
old_render = "            renderRequests(requestsData);"
new_render = "            renderRequests(requestsData);\n            renderVerifications(requestsData);\n            payableBills = requestsData.filter(r => r.status === 'approved' || r.status === 'partially_paid');"

# Also fix: new bill default status to pending_verification instead of pending
old_status = '"status": "pending"'
new_status = '"status": "pending_verification"'

changed = []
if old_tabs in content:
    content = content.replace(old_tabs, new_tabs, 1)
    changed.append("tabs")
else:
    print("WARNING: tabs target not found")

if old_render in content:
    content = content.replace(old_render, new_render, 1)
    changed.append("renderVerifications call")
else:
    print("WARNING: renderRequests call not found")

with open('templates/payouts_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done. Changed:", changed)
