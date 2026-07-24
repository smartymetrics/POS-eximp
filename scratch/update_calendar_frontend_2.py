import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Locate HRCalendarView bounds
start = content.find('function HRCalendarView')
if start == -1:
    print("HRCalendarView not found")
    exit()

end = content.find('function ', start + 10)
if end == -1: end = len(content)

component_code = content[start:end]

# 1. Update signature
component_code = component_code.replace('function HRCalendarView() {', 'function HRCalendarView({ user }) {')

# 2. Add isHR after useTheme
c_line = 'const { dark } = useTheme(); const C = dark ? DARK : LIGHT;'
is_hr_line = 'const isHR = user && user.role && (user.role.includes("admin") || user.role.includes("hr_admin"));'
component_code = component_code.replace(c_line, c_line + '\n    ' + is_hr_line)

# 3. Update addEvent
old_add = 'JSON.stringify({ name: form.name, holiday_date: form.date, is_recurring: form.is_mandatory })'
new_add = 'JSON.stringify({ title: form.title, date: form.date, event_type: form.event_type, department: isHR ? form.department : (user?.department || "Personal") })'
component_code = component_code.replace(old_add, new_add)

# 4. Update typeCol
old_type_col = 'const typeCol = { Holiday: "#4ADE80", Deadline: "#F87171", Interview: T.gold, Payroll: "#60A5FA", Meeting: "#A78BFA", Training: "#F59E0B", Review: "#EC4899" };'
new_type_col = 'const typeCol = { Holiday: "#4ADE80", Deadline: "#F87171", Interview: T.gold, Payroll: "#60A5FA", Meeting: "#A78BFA", Training: "#F59E0B", Review: "#EC4899", "Focus Time": "#8B5CF6", Leave: "#F43F5E", "Team Sync": "#0EA5E9" };'
component_code = component_code.replace(old_type_col, new_type_col)

# 5. Update form inputs
old_event_type = '<div><Lbl>Event Type</Lbl><select className="inp" value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}><option>Holiday</option><option>Deadline</option><option>Interview</option><option>Payroll</option><option>Meeting</option><option>Training</option><option>Review</option></select></div>'
new_event_type = '<div><Lbl>Event Type</Lbl><select className="inp" value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}>{isHR ? (<><option>Holiday</option><option>Deadline</option><option>Interview</option><option>Payroll</option><option>Meeting</option><option>Training</option><option>Review</option></>) : (<><option>Meeting</option><option>Focus Time</option><option>Leave</option><option>Team Sync</option></>)}</select></div>'
component_code = component_code.replace(old_event_type, new_event_type)

old_department = '<div><Lbl>Department</Lbl><select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}><option>All</option><option>HR</option><option>Finance</option><option>Sales & Acquisitions</option><option>Operations</option><option>Executive</option></select></div>'
new_department = '<div><Lbl>Scope / Department</Lbl>{isHR ? <select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}><option>All</option><option>HR</option><option>Finance</option><option>Sales & Acquisitions</option><option>Operations</option><option>Executive</option></select> : <div style={{ padding: "10px 14px", background: C.base, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 13, color: C.text }}>{user?.department || "Personal"} (Auto-assigned)</div>}</div>'
component_code = component_code.replace(old_department, new_department)

# Reassemble
new_content = content[:start] + component_code + content[end:]

# Update the call site: <HRCalendarView /> to <HRCalendarView user={user} />
# This is safe to do globally because there shouldn't be other components called <HRCalendarView />
new_content = new_content.replace('<HRCalendarView />', '<HRCalendarView user={user} />')

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Safely updated App.jsx")
