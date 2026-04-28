import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '{apps.filter(a => ["Interview", "Screening"].includes(a.status)).map(a => (<option key={a.id} value={a.id}>{a.candidate_name} — {jobs.find(j => j.id === a.job_id)?.title || "—"}</option>))}'
new_str = '{apps.filter(a => ["Interview", "Screening", "Offered", "Offer Accepted", "Offer Declined", "Rejected"].includes(a.status) || a.id === form.application_id).map(a => (<option key={a.id} value={a.id}>{a.candidate_name} ({a.candidate_email || "N/A"}) — {jobs.find(j => j.id === a.job_id)?.title || "—"}</option>))}'

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed OffersManager dropdown.")
else:
    print("Could not find the exact old_str.")

