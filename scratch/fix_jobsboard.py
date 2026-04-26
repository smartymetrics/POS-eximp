import re

with open(r'hrm-portal\src\App.jsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    'status: currentStatus === "Open" ? "Closed" : "Open"',
    'status: (currentStatus === "Open" || currentStatus === "Approved") ? "Closed" : "Open"'
)
c = c.replace(
    's === "Open" ? { background:',
    '(s === "Open" || s === "Approved") ? { background:'
)
c = c.replace(
    'jobs.filter(j => j.status === "Open").length',
    'jobs.filter(j => j.status === "Open" || j.status === "Approved").length'
)
c = c.replace(
    'jobs.filter(j => j.status !== "Open").length',
    'jobs.filter(j => j.status !== "Open" && j.status !== "Approved").length'
)
c = c.replace(
    'j.status === "Open" ? "Close Role" : "Reopen"',
    '(j.status === "Open" || j.status === "Approved") ? "Close Role" : "Reopen"'
)

with open(r'hrm-portal\src\App.jsx', 'w', encoding='utf-8') as f:
    f.write(c)
