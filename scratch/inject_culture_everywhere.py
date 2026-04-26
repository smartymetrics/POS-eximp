
import os

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Manager Portal Nav
old_mgr_nav = """    { id: "goals", icon: "goal", label: "Team Goals" },
    { isHeader: true, label: "Hub 8: Compliance" },"""
new_mgr_nav = """    { id: "goals", icon: "goal", label: "Team Goals" },
    { isHeader: true, label: "Hub 7: Engagement & Culture" },
    { id: "culture", icon: "profile", label: "Culture & Surveys" },
    { isHeader: true, label: "Hub 8: Compliance" },"""
content = content.replace(old_mgr_nav, new_mgr_nav)

# 2. Manager Portal Rendering
old_mgr_render = """      if (p === "disciplinary") return <Disciplinary isManager userId={user.id} />;"""
new_mgr_render = """      if (p === "disciplinary") return <Disciplinary isManager userId={user.id} />;
      if (p === "culture") return <CultureHub authRole="manager" />;"""
content = content.replace(old_mgr_render, new_mgr_render)

# 3. Staff Portal Nav
old_staff_nav = """    { id: "goals", icon: "goal", label: "My Goals" },
    { isHeader: true, label: "Hub 6: Compensation" },"""
new_staff_nav = """    { id: "goals", icon: "goal", label: "My Goals" },
    { isHeader: true, label: "Hub 7: Engagement & Culture" },
    { id: "culture", icon: "profile", label: "Culture & Surveys" },
    { isHeader: true, label: "Hub 6: Compensation" },"""
content = content.replace(old_staff_nav, new_staff_nav)

# 4. Staff Portal Rendering
old_staff_render_payroll = """      if (p === "payroll") return <Payroll />;"""
new_staff_render_payroll = """      if (p === "payroll") return <Payroll />;
      if (p === "culture") return <CultureHub authRole="staff" />;"""
content = content.replace(old_staff_render_payroll, new_staff_render_payroll)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected Culture Hub into Manager and Staff portals")
