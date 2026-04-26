
import re
import os

file_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update DARK and LIGHT Tokens for Eximp Prestige palette
content = re.sub(
    r'const DARK = { bg: "[^"]+", surface: "[^"]+", card: "[^"]+", border: "[^"]+", input: "[^"]+", text: "[^"]+", sub: "[^"]+", muted: "[^"]+" };',
    r'const DARK = { bg: "#0B0C0F", surface: "#111317", card: "#1A1D24", border: "#2D2F36", input: "#161820", text: "#E5E7EB", sub: "#A0A0A0", muted: "#6B7280" };',
    content
)

# 2. Rename Mismanagement to Disciplinary
content = content.replace("Mismanagement", "Disciplinary")
content = content.replace("mismanagement", "disciplinary")
content = content.replace("mismanage", "disciplinary")

# 3. Update Sidebar rendering to support headers
old_sidebar_nav = r'''        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {items.map(n => (
            <button key={n.id} className={`nb ${page === n.id ? "on" : ""}`} onClick={() => setPage(n.id)}>
              {IC[n.icon]}{n.label}
            </button>
          ))}
        </nav>'''

new_sidebar_nav = r'''        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {items.map(n => (
            n.isHeader ? (
              <div key={n.label} style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800, padding: "16px 16px 6px", marginTop: 4 }}>{n.label}</div>
            ) : (
            <button key={n.id} className={`nb ${page === n.id ? "on" : ""}`} onClick={() => !n.disabled && setPage(n.id)} style={{ opacity: n.disabled ? 0.5 : 1, cursor: n.disabled ? 'not-allowed' : 'pointer' }}>
              {IC[n.icon]}{n.label} {n.disabled && <span style={{fontSize: 9, marginLeft: 'auto', background: '#333', padding: '2px 6px', borderRadius: 4}}>SOON</span>}
            </button>
            )
          ))}
        </nav>'''

content = content.replace(old_sidebar_nav, new_sidebar_nav)

# 4. Refactor Nav Items for HRAdminPortal
old_hr_nav = r'''  const nav = [
    { id: "dashboard", icon: "dashboard", label: "HR Overview" },
    { id: "staff", icon: "staff", label: "Staff Directory" },
    { id: "leave", icon: "presence", label: "Leave Management" },
    { id: "admin", icon: "dashboard", label: "Workforce Stats" },
    { id: "presence", icon: "presence", label: "Presence" },
    { id: "perf", icon: "perf", label: "Performance" },
    { id: "goals", icon: "goal", label: "Goal Management" },
    { id: "payroll", icon: "payroll", label: "Payroll" },
    { id: "tasks", icon: "tasks", label: "Task Manager" },
    { id: "disciplinary", icon: "mis", label: "Disciplinary" },
    { id: "legal_vault", icon: "tasks", label: "Legal Matters" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
  ];'''

new_hr_nav = r'''  const nav = [
    { isHeader: true, label: "Hub 1: Recruitment" },
    { id: "ats", icon: "staff", label: "ATS & Jobs", disabled: true },
    { isHeader: true, label: "Hub 2: People & Org" },
    { id: "dashboard", icon: "dashboard", label: "HR Overview" },
    { id: "staff", icon: "staff", label: "Staff Directory" },
    { isHeader: true, label: "Hub 3: Time & Attendance" },
    { id: "presence", icon: "presence", label: "Attendance Logs" },
    { isHeader: true, label: "Hub 4: Leave Management" },
    { id: "leave", icon: "presence", label: "Leave Requests" },
    { isHeader: true, label: "Hub 5: Performance" },
    { id: "perf", icon: "perf", label: "Scorecards" },
    { id: "goals", icon: "goal", label: "Goal Management" },
    { isHeader: true, label: "Hub 6: Compensation" },
    { id: "payroll", icon: "payroll", label: "Payroll Engine" },
    { isHeader: true, label: "Hub 8: Compliance" },
    { id: "disciplinary", icon: "mis", label: "Disciplinary" },
    { id: "legal_vault", icon: "tasks", label: "Legal Vault" },
    { isHeader: true, label: "Hub 9: Administration" },
    { id: "tasks", icon: "tasks", label: "Task Manager" },
    { id: "admin", icon: "dashboard", label: "Workforce Stats" },
    { isHeader: true, label: "Personal" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
  ];'''

content = content.replace(old_hr_nav, new_hr_nav)

# 5. Refactor Nav Items for ManagerPortal
old_mgr_nav = r'''  const nav = [
    { id: "dashboard", icon: "dashboard", label: "Team Dashboard" },
    { id: "team", icon: "staff", label: "My Team" },
    { id: "leave", icon: "presence", label: "Leave Approval" },
    { id: "presence", icon: "presence", label: "Presence" },
    { id: "perf", icon: "perf", label: "Team Performance" },
    { id: "goals", icon: "goal", label: "Team Goals" },
    { id: "tasks", icon: "tasks", label: "Task Manager" },
    { id: "disciplinary", icon: "mis", label: "Incidents" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
    { id: "myperformance", icon: "perf", label: "My Performance" },
  ];'''

new_mgr_nav = r'''  const nav = [
    { isHeader: true, label: "Hub 2: People & Org" },
    { id: "dashboard", icon: "dashboard", label: "Team Dashboard" },
    { id: "team", icon: "staff", label: "My Team" },
    { isHeader: true, label: "Hub 3: Time & Attendance" },
    { id: "presence", icon: "presence", label: "Team Presence" },
    { isHeader: true, label: "Hub 4: Leave Management" },
    { id: "leave", icon: "presence", label: "Leave Approvals" },
    { isHeader: true, label: "Hub 5: Performance" },
    { id: "perf", icon: "perf", label: "Team Scorecards" },
    { id: "goals", icon: "goal", label: "Team Goals" },
    { isHeader: true, label: "Hub 8: Compliance" },
    { id: "disciplinary", icon: "mis", label: "Incidents" },
    { isHeader: true, label: "Hub 9: Administration" },
    { id: "tasks", icon: "tasks", label: "Task Manager" },
    { isHeader: true, label: "Personal" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
    { id: "myperformance", icon: "perf", label: "My Performance" },
  ];'''

content = content.replace(old_mgr_nav, new_mgr_nav)

# 6. Refactor Nav Items for StaffPortal
old_staff_nav = r'''  const nav = [
    { id: "dashboard", icon: "dashboard", label: "My Dashboard" },
    { id: "profile", icon: "profile", label: "My Profile" },
    { id: "leave", icon: "presence", label: "My Leave" },
    { id: "perf", icon: "perf", label: "My Performance" },
    { id: "goals", icon: "goal", label: "My Goals" },
    { id: "tasks", icon: "tasks", label: "My Tasks" },
    { id: "presence", icon: "presence", label: "My Presence" },
    { id: "payroll", icon: "payslip", label: "My Payroll" },
    { id: "disciplinary", icon: "mis", label: "My Flags" },
    { id: "legal_vault", icon: "tasks", label: "Legal Vault" },
  ];'''

new_staff_nav = r'''  const nav = [
    { isHeader: true, label: "Hub 2: People & Org" },
    { id: "dashboard", icon: "dashboard", label: "My Dashboard" },
    { id: "profile", icon: "profile", label: "My Profile" },
    { isHeader: true, label: "Hub 3: Time & Attendance" },
    { id: "presence", icon: "presence", label: "My Presence" },
    { isHeader: true, label: "Hub 4: Leave Management" },
    { id: "leave", icon: "presence", label: "My Leave" },
    { isHeader: true, label: "Hub 5: Performance" },
    { id: "perf", icon: "perf", label: "My Scorecard" },
    { id: "goals", icon: "goal", label: "My Goals" },
    { isHeader: true, label: "Hub 6: Compensation" },
    { id: "payroll", icon: "payslip", label: "My Payroll" },
    { isHeader: true, label: "Hub 8: Compliance" },
    { id: "disciplinary", icon: "mis", label: "My Flags" },
    { id: "legal_vault", icon: "tasks", label: "Legal Vault" },
    { isHeader: true, label: "Hub 9: Administration" },
    { id: "tasks", icon: "tasks", label: "My Tasks" },
  ];'''

content = content.replace(old_staff_nav, new_staff_nav)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied Phase 1 refactoring.")
