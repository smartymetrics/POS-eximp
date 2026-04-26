
import os

file_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

recruitment_code = """
// ─── RECRUITMENT / ATS ───────────────────────────────────────────────────────
function RecruitmentHub() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("jobs"); // "jobs" | "pipeline"
  const [showJobModal, setShowJobModal] = useState(false);
  const [jobForm, setJobForm] = useState({ title: "", department: "General", employment_type: "Full-time", location: "Remote", salary_range: "" });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [j, a] = await Promise.all([
        apiFetch(`${API_BASE}/hr/recruitment/jobs`),
        apiFetch(`${API_BASE}/hr/recruitment/applications`)
      ]);
      setJobs(j || []);
      setApps(a || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const createJob = async () => {
    if (!jobForm.title) return alert("Job title required");
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/jobs`, {
        method: "POST",
        body: JSON.stringify(jobForm)
      });
      setShowJobModal(false);
      fetchData();
    } catch (e) { alert(e.message); }
  };

  const updateAppStatus = async (appId, newStatus) => {
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus })
      });
      fetchData();
    } catch (e) { alert(e.message); }
  };

  const statuses = ["Applied", "Screening", "Interview", "Offered", "Hired", "Rejected"];

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Recruitment & ATS</div>
          <div style={{ fontSize: 13, color: C.sub }}>Manage job requisitions and candidate pipelines.</div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <Tabs items={[["jobs", "Job Board"], ["pipeline", "ATS Pipeline"]]} active={view} setActive={setView} />
          {view === "jobs" && <button className="bp" onClick={() => setShowJobModal(true)} style={{ height: 38 }}>+ Post Job</button>}
        </div>
      </div>

      {view === "jobs" && (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw">
            <table className="ht">
              <thead><tr><th>Job Title & Dept</th><th>Type / Location</th><th>Status</th><th>Applicants</th></tr></thead>
              <tbody>
                {jobs.map(j => {
                  const applicantCount = apps.filter(a => a.job_id === j.id).length;
                  return (
                    <tr key={j.id}>
                      <td><div style={{ fontWeight: 800, color: C.text }}>{j.title}</div><div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{j.department}</div></td>
                      <td><div style={{ color: C.text }}>{j.employment_type}</div><div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{j.location || "Remote"}</div></td>
                      <td><span className="tg" style={{ background: j.status === 'Open' ? '#4ADE8022' : '#F8717122', color: j.status === 'Open' ? '#4ADE80' : '#F87171' }}>{j.status}</span></td>
                      <td><div style={{ fontWeight: 800, color: T.orange }}>{applicantCount}</div></td>
                    </tr>
                  )
                })}
                {jobs.length === 0 && !loading && <tr><td colSpan="4" style={{ textAlign: "center", padding: 30, color: C.muted }}>No active job requisitions.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {view === "pipeline" && (
        <div style={{ display: "flex", gap: 16, overflowX: "auto", paddingBottom: 20 }}>
          {statuses.map(status => {
            const colApps = apps.filter(a => a.status === status);
            return (
              <div key={status} style={{ minWidth: 280, width: 280, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 800, color: C.text, textTransform: "uppercase", fontSize: 11, letterSpacing: "1px" }}>{status}</div>
                  <span className="tg tm">{colApps.length}</span>
                </div>
                {colApps.map(a => (
                  <div key={a.id} className="gc" style={{ padding: 14, cursor: "pointer", borderLeft: `3px solid ${T.orange}` }}>
                    <div style={{ fontWeight: 800, color: C.text, fontSize: 13 }}>{a.candidate_name}</div>
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>Role: {a.job_requisitions?.title || "Unknown"}</div>
                    <select className="inp" style={{ marginTop: 10, padding: "6px 10px", fontSize: 11 }} value={a.status} onChange={e => updateAppStatus(a.id, e.target.value)}>
                      {statuses.map(s => <option key={s} value={s}>Move to {s}</option>)}
                    </select>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      )}

      {showJobModal && (
        <Modal title="Create Job Requisition" width={480} onClose={() => setShowJobModal(false)}>
           <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div><Lbl>Job Title *</Lbl><input className="inp" value={jobForm.title} onChange={e => setJobForm({...jobForm, title: e.target.value})} placeholder="e.g. Senior Backend Engineer" /></div>
            <div className="g2">
              <div><Lbl>Department</Lbl>
                <select className="inp" value={jobForm.department} onChange={e => setJobForm({...jobForm, department: e.target.value})}>
                  <option>General</option><option>Sales & Acquisitions</option><option>Engineering</option><option>HR</option><option>Finance</option>
                </select>
              </div>
              <div><Lbl>Employment Type</Lbl>
                <select className="inp" value={jobForm.employment_type} onChange={e => setJobForm({...jobForm, employment_type: e.target.value})}>
                  <option>Full-time</option><option>Part-time</option><option>Contract</option>
                </select>
              </div>
            </div>
            <div className="g2">
              <div><Lbl>Location</Lbl><input className="inp" value={jobForm.location} onChange={e => setJobForm({...jobForm, location: e.target.value})} placeholder="e.g. London, UK or Remote" /></div>
              <div><Lbl>Salary Range</Lbl><input className="inp" value={jobForm.salary_range} onChange={e => setJobForm({...jobForm, salary_range: e.target.value})} placeholder="e.g. £50k - £70k" /></div>
            </div>
            <button className="bp" onClick={createJob} style={{ marginTop: 10 }}>Post Job Requisition</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
"""

if "function RecruitmentHub()" not in content:
    content = content.replace("// ─── ROOT ────────────────────────────────────────────────────────────────────", recruitment_code + "\n// ─── ROOT ────────────────────────────────────────────────────────────────────")

# Activate the ATS nav item
content = content.replace('{ id: "ats", icon: "staff", label: "ATS & Jobs", disabled: true },', '{ id: "ats", icon: "staff", label: "ATS & Jobs" },')

# Add routing rendering
if 'if (p === "ats") return <RecruitmentHub />;' not in content:
    content = content.replace('if (p === "dashboard") return <HRDashboard />;', 'if (p === "dashboard") return <HRDashboard />;\n      if (p === "ats") return <RecruitmentHub />;')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected RecruitmentHub component")
