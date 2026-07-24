import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """                    <div style={{ display: "flex", gap: 16, fontSize: 12, color: C.muted, flexWrap: "wrap" }}>
                      {a.offered_salary && <span>💰 Offered: <strong style={{ color: T.gold }}>₦{parseFloat(a.offered_salary).toLocaleString()}</strong></span>}
                      {a.start_date && <span>📅 Start: {a.start_date}</span>}
                    </div>
                  </div>"""

new_block = """                    <div style={{ display: "flex", gap: 16, fontSize: 12, color: C.muted, flexWrap: "wrap" }}>
                      {a.offered_salary && <span>💰 Offered: <strong style={{ color: T.gold }}>₦{parseFloat(a.offered_salary).toLocaleString()}</strong></span>}
                      {a.start_date && <span>📅 Start: {a.start_date}</span>}
                    </div>
                    {a.notes && (
                      <div style={{ marginTop: 12, fontSize: 12, color: C.sub, padding: "8px 12px", background: `${T.gold}11`, borderLeft: `3px solid ${T.gold}`, borderRadius: 4, whiteSpace: "pre-wrap" }}>
                        {a.notes}
                      </div>
                    )}
                  </div>"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added candidate notes rendering to OffersManager.")
else:
    print("Could not find the block to replace.")
