
import os

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

culture_code = """
// ─── CULTURE & ENGAGEMENT HUB ────────────────────────────────────────────────
function CultureHub({ authRole }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const isHR = authRole === "hr";
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("surveys"); // surveys | analytics
  
  // Create State
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ title: "", description: "", questions: [""] });
  
  // Respond State
  const [activeSurvey, setActiveSurvey] = useState(null);
  const [answers, setAnswers] = useState({});
  const [isAnon, setIsAnon] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await apiFetch(`${API_BASE}/hr/culture/surveys`);
      setSurveys(data || []);
    } catch(e) { console.error(e); } finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if(!createForm.title || createForm.questions.filter(q=>q.trim()).length === 0) return alert("Title and at least 1 question required.");
    try {
      await apiFetch(`${API_BASE}/hr/culture/surveys`, {
        method: "POST",
        body: JSON.stringify({
          title: createForm.title,
          description: createForm.description,
          questions: createForm.questions.filter(q=>q.trim())
        })
      });
      setShowCreate(false);
      setCreateForm({ title: "", description: "", questions: [""] });
      fetchData();
    } catch(e) { alert(e.message); }
  };

  const handleSubmitResponse = async () => {
    if(Object.keys(answers).length === 0) return alert("Please answer at least one question.");
    setSubmitting(true);
    try {
      await apiFetch(`${API_BASE}/hr/culture/surveys/${activeSurvey.id}/respond`, {
        method: "POST",
        body: JSON.stringify({ answers, is_anonymous: isAnon })
      });
      alert("Thank you! Your response has been securely submitted.");
      setActiveSurvey(null);
      setAnswers({});
      fetchData();
    } catch(e) { alert(e.message); } finally { setSubmitting(false); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Engagement & Culture</div>
          <div style={{ fontSize: 13, color: C.sub }}>Company pulse checks, eNPS, and anonymous surveys.</div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          {isHR && <Tabs items={[["surveys", "Active Surveys"], ["analytics", "Analytics"]]} active={view} setActive={setView} />}
          {isHR && view === "surveys" && <button className="bp" onClick={() => setShowCreate(true)} style={{ height: 38 }}>+ Launch Survey</button>}
        </div>
      </div>

      {view === "surveys" && (
        <div className="g3">
          {surveys.map(s => (
            <div key={s.id} className="gc" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: C.text }}>{s.title}</div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>{s.questions.length} Questions</div>
                </div>
                {s.is_active ? <span className="tg tg2">Active</span> : <span className="tg tr">Closed</span>}
              </div>
              <div style={{ fontSize: 13, color: C.sub, lineHeight: "1.5" }}>{s.description || "No description provided."}</div>
              {s.is_active && (
                <button className="bg" style={{ alignSelf: "flex-start", padding: "8px 16px" }} onClick={() => setActiveSurvey(s)}>
                  Take Survey
                </button>
              )}
            </div>
          ))}
          {surveys.length === 0 && !loading && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: C.muted }}>No surveys available.</div>}
        </div>
      )}

      {view === "analytics" && isHR && (
         <div className="g2">
            {surveys.map(s => {
              const resCount = s.responses ? s.responses.length : 0;
              return (
                <div key={s.id} className="gc" style={{ padding: 20 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: C.text, marginBottom: 12 }}>{s.title}</div>
                  <div style={{ fontSize: 24, fontWeight: 900, color: T.gold }}>{resCount}</div>
                  <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800 }}>Total Responses</div>
                  {resCount > 0 && (
                    <div style={{ marginTop: 16, borderTop: `1px solid ${C.border}`, paddingTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                      {s.questions.map((q, i) => {
                        const answersForQ = s.responses.map(r => r[i]).filter(Boolean);
                        return (
                          <div key={i} style={{ background: C.bg, padding: 12, borderRadius: 8 }}>
                            <div style={{ fontSize: 12, fontWeight: 800, color: C.text, marginBottom: 8 }}>Q: {q}</div>
                            {answersForQ.slice(0, 3).map((a, j) => (
                               <div key={j} style={{ fontSize: 12, color: C.sub, padding: "4px 8px", background: `${C.border}55`, borderRadius: 4, marginBottom: 4 }}>"{a}"</div>
                            ))}
                            {answersForQ.length > 3 && <div style={{ fontSize: 10, color: T.orange, marginTop: 4 }}>+ {answersForQ.length - 3} more responses</div>}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
         </div>
      )}

      {showCreate && (
        <Modal title="Launch New Survey" width={540} onClose={() => setShowCreate(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div><Lbl>Survey Title *</Lbl><input className="inp" value={createForm.title} onChange={e => setCreateForm({...createForm, title: e.target.value})} placeholder="e.g. Q3 eNPS Pulse Check" /></div>
            <div><Lbl>Description</Lbl><textarea className="inp" rows="2" value={createForm.description} onChange={e => setCreateForm({...createForm, description: e.target.value})} placeholder="Explain the purpose of this survey..." /></div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Lbl>Questions</Lbl>
              {createForm.questions.map((q, idx) => (
                <input key={idx} className="inp" value={q} onChange={e => {
                  const newQ = [...createForm.questions];
                  newQ[idx] = e.target.value;
                  setCreateForm({...createForm, questions: newQ});
                }} placeholder={`Question ${idx + 1}`} />
              ))}
              <button className="bg" style={{ alignSelf: "flex-start", padding: "6px 12px", fontSize: 11 }} onClick={() => setCreateForm({...createForm, questions: [...createForm.questions, ""]})}>+ Add Question</button>
            </div>
            
            <button className="bp" onClick={handleCreate} style={{ marginTop: 10 }}>Publish Survey</button>
          </div>
        </Modal>
      )}

      {activeSurvey && (
        <Modal title={activeSurvey.title} width={600} onClose={() => !submitting && setActiveSurvey(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {activeSurvey.description && <div style={{ fontSize: 13, color: C.sub, background: `${T.gold}11`, padding: 12, borderRadius: 8, border: `1px solid ${T.gold}33` }}>{activeSurvey.description}</div>}
            
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {activeSurvey.questions.map((q, idx) => (
                <div key={idx}>
                  <div style={{ fontSize: 14, fontWeight: 800, color: C.text, marginBottom: 8 }}>{idx + 1}. {q}</div>
                  <textarea className="inp" rows="2" value={answers[idx] || ""} onChange={e => setAnswers({...answers, [idx]: e.target.value})} placeholder="Your answer..." />
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${C.border}`, paddingTop: 16 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: C.text, fontWeight: 800 }}>
                <input type="checkbox" checked={isAnon} onChange={e => setIsAnon(e.target.checked)} style={{ width: 16, height: 16, accentColor: T.gold }} />
                Submit Anonymously (Hide my identity)
              </label>
              <button className="bp" onClick={handleSubmitResponse} disabled={submitting}>
                {submitting ? "Submitting..." : "Submit Responses"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

"""

if "function CultureHub(" not in content:
    content = content.replace("// ─── ROOT ────────────────────────────────────────────────────────────────────", culture_code + "\n// ─── ROOT ────────────────────────────────────────────────────────────────────")

# Add to navigation
if '{ id: "culture", icon: "profile", label: "Culture & Surveys" }' not in content:
    content = content.replace('{ isHeader: true, label: "Hub 7: Engagement & Culture" },', '{ isHeader: true, label: "Hub 7: Engagement & Culture" },\n    { id: "culture", icon: "profile", label: "Culture & Surveys" },')

# Add routing rendering
if 'if (p === "culture") return <CultureHub authRole="hr" />;' not in content:
    content = content.replace('if (p === "admin") return <Administration />;', 'if (p === "admin") return <Administration />;\n      if (p === "culture") return <CultureHub authRole="hr" />;')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected CultureHub component")
