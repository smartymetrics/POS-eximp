import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix ATS Pipeline filtering
old_stage_apps = 'const stageApps = filteredApps.filter(a => a.status === stage.key);'
new_stage_apps = 'const stageApps = filteredApps.filter(a => a.status === stage.key || (stage.key === "Rejected" && a.status === "Offer Declined") || (stage.key === "Offered" && a.status === "Offer Accepted"));'
content = content.replace(old_stage_apps, new_stage_apps)

# 2. Add Revise Offer button
# The block looks like this:
"""
                    {a.status === "Offer Accepted" && (
                      <button className="bp" style={{ fontSize: 11, padding: "5px 14px", background: "#4ADE80", color: "#1A1A1A" }} onClick={() => hireApplicant(a.id)}>Hire & Onboard ✓</button>
                    )}
                    {a.status === "Offered" && (
                      <>
                        <button className="bg" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => acceptOffer(a.id)}>Force Accept</button>
                        <button style={{ fontSize: 11, padding: "5px 14px", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", borderRadius: 8, cursor: "pointer" }} onClick={() => declineOffer(a.id)}>Force Decline</button>
                      </>
                    )}
                  </div>
"""

# I will replace the end of the offered buttons to include the revise button.
# Let's target the `{a.status === "Offered" && (` block and add the new button after it.

old_offered_buttons = """                    {a.status === "Offered" && (
                      <>
                        <button className="bg" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => acceptOffer(a.id)}>Force Accept</button>
                        <button style={{ fontSize: 11, padding: "5px 14px", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", borderRadius: 8, cursor: "pointer" }} onClick={() => declineOffer(a.id)}>Force Decline</button>
                      </>
                    )}
                  </div>"""

new_offered_buttons = """                    {a.status === "Offered" && (
                      <>
                        <button className="bg" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => acceptOffer(a.id)}>Force Accept</button>
                        <button style={{ fontSize: 11, padding: "5px 14px", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", borderRadius: 8, cursor: "pointer" }} onClick={() => declineOffer(a.id)}>Force Decline</button>
                      </>
                    )}
                    {(a.status === "Offer Declined" || a.status === "Rejected") && (
                      <button className="bp" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => { setForm({ application_id: a.id, offered_salary: a.offered_salary, start_date: a.start_date || "", notes: a.notes || "" }); setShowNew(true); }}>Revise & Resend Offer 📝</button>
                    )}
                  </div>"""

content = content.replace(old_offered_buttons, new_offered_buttons)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("ATS fix applied.")
