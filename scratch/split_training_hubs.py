import os
import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # 1. Define ComplianceHub
    compliance_hub_code = """
function ComplianceHub({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [trainings, setTrainings] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", start_date: "", end_date: "" });

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/trainings`).then(d => setTrainings((d || []).filter(t => t.training_type === "Compliance"))).catch(() => setTrainings([])).finally(() => setLoading(false));
  }, []);

  const add = async () => {
    if (!form.title || !form.start_date) return alert("Title and date required");
    try {
      await apiFetch(`${API_BASE}/hr/trainings`, { method: "POST", body: JSON.stringify({ ...form, training_type: "Compliance" }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/trainings`).then(d => setTrainings((d || []).filter(t => t.training_type === "Compliance")));
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Compliance & Certifications</div><div style={{ fontSize: 13, color: C.sub }}>Mandatory training and policy acknowledgements.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)} style={{ height: 38 }}>+ Add Compliance Item</button>}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading...</div> : (
        <div className="g3">
          {trainings.map(t => (
            <div key={t.id} className="gc" style={{ padding: 20, borderLeft: `4px solid #F87171` }}>
              <div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{t.title}</div>
              <div style={{ fontSize: 12, color: C.sub, marginTop: 8, lineHeight: 1.5 }}>{t.description}</div>
              <div style={{ fontSize: 11, color: "#F87171", fontWeight: 800, marginTop: 12, textTransform: "uppercase" }}>Due Date: {t.start_date}</div>
              <button className="bp" style={{ marginTop: 12, fontSize: 11, background: "#F8717122", color: "#F87171", border: "none" }}>Complete Training</button>
            </div>
          ))}
          {trainings.length === 0 && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: C.muted }}>No mandatory compliance items pending.</div>}
        </div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="New Compliance Requirement">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Requirement Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
          <div><Lbl>Description</Lbl><textarea className="inp" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
          <div><Lbl>Deadline *</Lbl><input type="date" className="inp" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} /></div>
          <button className="bp" style={{ background: "#F87171" }} onClick={add}>Launch Requirement</button>
        </div>
      </Modal>}
    </div>
  );
}
"""
    # Insert ComplianceHub before LearningHub
    content = content.replace('function LearningHub', compliance_hub_code + '\nfunction LearningHub')

    # 2. Refine LearningHub (remove compliance tab and filter)
    # We'll look for the return statement and simplify it
    # This is tricky with string replace, let's use regex to find the tab part
    content = content.replace('<Tabs items={[["trainings", "Trainings"], ["compliance", "Compliance"]]} active={tab} setActive={setTab} />', '')
    content = content.replace('{(trainings.filter(t => tab === "compliance" ? t.training_type === "Compliance" : t.training_type !== "Compliance")).map(t => {', '{trainings.filter(t => t.training_type !== "Compliance").map(t => {')
    content = content.replace('Learning & Training', 'Learning & Development')
    content = content.replace('Internal, external and compliance training programmes.', 'Internal and external training programmes to boost your career.')

    # 3. Update Routing
    # Admin side
    content = content.replace('if (p === "training" || p === "compliance_training") return <LearningHub isHR={true} defaultTab={p === "compliance_training" ? "compliance" : "trainings"} />;', 
                              'if (p === "training") return <LearningHub isHR={true} />;\n      if (p === "compliance_training") return <ComplianceHub isHR={true} />;')
    # Staff side
    content = content.replace('if (pg === "training" || pg === "compliance_training") return <LearningHub isHR={false} defaultTab={pg === "compliance_training" ? "compliance" : "trainings"} />;', 
                              'if (pg === "training") return <LearningHub isHR={false} />;\n      if (pg === "compliance_training") return <ComplianceHub isHR={false} />;')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Split successful")
except Exception as e:
    print(f"Error: {e}")
