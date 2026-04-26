import re

path = r'hrm-portal\src\App.jsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update form initial states
content = content.replace(
    'const [form, setForm] = useState({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", description: "", requirements: "" });',
    'const [form, setForm] = useState({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", description: "", responsibilities: "", requirements: "" });'
)
content = content.replace(
    'const [form, setForm] = useState({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", headcount: 1, justification: "", approved_by: "" });',
    'const [form, setForm] = useState({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", headcount: 1, justification: "", responsibilities: "", approved_by: "" });'
)

# 2. Update reset in create function (JobsBoard)
content = content.replace(
    'setShowNew(false); setForm({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", description: "", requirements: "" }); refresh();',
    'setShowNew(false); setForm({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", description: "", responsibilities: "", requirements: "" }); refresh();'
)

# 3. Update viewJob modal (JobsBoard)
content = content.replace(
    '{viewJob.description && <div style={{ marginBottom: 16 }}><Lbl>Job Description</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}18` }}>{viewJob.description}</div></div>}',
    '{viewJob.description && <div style={{ marginBottom: 16 }}><Lbl>Job Description</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}18` }}>{viewJob.description}</div></div>}\n        {viewJob.responsibilities && <div style={{ marginBottom: 16 }}><Lbl>Key Responsibilities</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}18` }}>{viewJob.responsibilities}</div></div>}'
)

# 4. Update showNew modal (JobsBoard)
content = content.replace(
    '<div><Lbl>Job Description</Lbl><textarea className="inp" rows={4} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>',
    '<div><Lbl>Job Description</Lbl><textarea className="inp" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>\n          <div><Lbl>Key Responsibilities</Lbl><textarea className="inp" rows={3} value={form.responsibilities} onChange={e => setForm(f => ({ ...f, responsibilities: e.target.value }))} /></div>'
)

# 5. Update JobRequisitions form
content = content.replace(
    '<div><Lbl>Business Justification *</Lbl><textarea className="inp" rows={4} value={form.justification} onChange={e => setForm(f => ({ ...f, justification: e.target.value }))} placeholder="Why is this role needed?" /></div>',
    '<div><Lbl>Business Justification *</Lbl><textarea className="inp" rows={3} value={form.justification} onChange={e => setForm(f => ({ ...f, justification: e.target.value }))} placeholder="Why is this role needed?" /></div>\n          <div><Lbl>Key Responsibilities</Lbl><textarea className="inp" rows={3} value={form.responsibilities} onChange={e => setForm(f => ({ ...f, responsibilities: e.target.value }))} /></div>'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
