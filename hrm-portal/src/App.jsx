import { useState, createContext, useContext, useCallback, useEffect } from "react";
import { apiFetch, API_BASE } from "./api";

const ThemeCtx = createContext({ dark: true, toggle: () => {} });
const useTheme = () => useContext(ThemeCtx);

// ─── DESIGN TOKENS ──────────────────────────────────────────────────────────────
const T = {
  gold:     "#C47D0A",
  // Keep orange alias for backward compat with all components
  orange:   "#C47D0A",
  glow:     "0 0 0 1px #C47D0A33, 0 0 14px #C47D0A18",
  glowHover:"0 0 0 1.5px #C47D0A, 0 0 22px #C47D0A40",
};
const DARK  = { bg:"#0F1115", surface:"#111317", card:"#1E2128", border:"#2D2F36", input:"#161820", text:"#E5E7EB", sub:"#9CA3AF", muted:"#6B7280" };
const LIGHT = { bg:"#F0F2F6", surface:"#FFFFFF",  card:"#FFFFFF",  border:"#DDE3EE", input:"#F4F6FA", text:"#1A2130", sub:"#556677", muted:"#99AABB" };

// Data will be fetched from API
const calcScore = p => {
  if (!p || typeof p !== 'object') return 0;
  // If we have a calculated score from the backend, use it
  if (p.score !== undefined) return p.score;
  
  // Fallback for manual calc
  const goals = p.goals_40_pct || 0;
  const quality = p.quality_20_pct || 0;
  const manager = p.manager_review_40_pct || 0;
  return Math.round(goals * 0.4 + quality * 0.2 + manager * 0.4);
};


// ─── GLOBAL STYLES ──────────────────────────────────────────────────────────────
const GS = dark => {
  const C = dark ? DARK : LIGHT;
  const G = T.gold;
  return `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    ::-webkit-scrollbar{width:6px;height:6px;}
    ::-webkit-scrollbar-track{background:${C.bg};}
    ::-webkit-scrollbar-thumb{background:${C.border};border-radius:4px;}
    ::-webkit-scrollbar-thumb:hover{background:#4B5563;}
    body,html{height:100%;}
    .hrm{font-family:'Inter',sans-serif;background:${C.bg};color:${C.text};height:100vh;overflow:hidden;display:flex;width:100%;}
    .hrm-serif{font-family:'Playfair Display',serif;}
    .fade{animation:fi .3s ease forwards;}
    @keyframes fi{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
    
    /* Cards */
    .gc{background:${C.card};border:1px solid ${C.border};border-radius:12px;padding:16px;transition:all .3s ease;}
    .gc:hover{border-color:${G};box-shadow:0 0 20px ${G}1A;}
    .ho{color:${G};font-weight:700;letter-spacing:.3px;}
    
    /* Nav buttons */
    .nb{display:flex;align-items:center;gap:14px;padding:12px 16px;border-radius:10px;font-size:14px;font-weight:500;color:#9CA3AF;cursor:pointer;border-left:3px solid transparent;border-top:none;border-right:none;border-bottom:none;background:transparent;width:100%;text-align:left;transition:all .25s cubic-bezier(.4,0,.2,1);font-family:inherit;margin-bottom:2px;}
    .nb:hover{background:rgba(255,255,255,.03);color:#E5E7EB;}
    .nb.on{background:${G}14;color:${G};border-left-color:${G};font-weight:600;}
    .nb svg{width:18px;height:18px;flex-shrink:0;opacity:.7;transition:opacity .25s;}
    .nb:hover svg,.nb.on svg{opacity:1;}
    
    /* Buttons */
    .bp{background:linear-gradient(135deg, ${G} 0%, #A66A08 100%);color:#fff;border:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:all .2s ease;letter-spacing:.5px;box-shadow:0 4px 12px ${G}33;text-transform:uppercase;}
    .bp:hover{filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 6px 18px ${G}44;}
    .bp:active{transform:translateY(0);}
    .bp:disabled{opacity:.6;cursor:not-allowed;transform:none;box-shadow:none;}
    .bg{background:transparent;border:1px solid ${C.border};color:${C.sub};padding:9px 20px;border-radius:10px;font-size:13px;cursor:pointer;font-family:inherit;transition:all .2s;font-weight:600;}
    .bg:hover{border-color:${G};color:${G};background:${G}0A;transform:translateY(-1px);}
    .bd{background:#EF444412;color:#EF4444;border:1px solid #EF444430;padding:8px 16px;border-radius:10px;font-size:12px;cursor:pointer;font-family:inherit;font-weight:700;transition:all .2s;}
    .bd:hover{background:#EF444422;transform:translateY(-1px);}
    
    /* Inputs */
    .inp{background:${C.input};border:1px solid ${C.border};color:${C.text};padding:11px 16px;border-radius:10px;font-size:14px;outline:none;font-family:inherit;width:100%;transition:border-color .2s;}
    .inp:focus{border-color:${G};box-shadow:0 0 0 3px ${G}20;}
    select.inp option{background:${C.card};}
    textarea.inp{resize:vertical;min-height:80px;}
    
    /* Tags */
    .tg{display:inline-flex;align-items:center;padding:4px 12px;border-radius:9999px;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;}
    .to{background:${G}1A;color:${G};}
    .tg2{background:#10B98120;color:#10B981;}
    .tr{background:#EF444420;color:#EF4444;}
    .tb{background:#3B82F620;color:#3B82F6;}
    .ty{background:#F59E0B20;color:#F59E0B;}
    .tm{background:${C.border}44;color:${C.sub};}
    
    /* Progress bars */
    .pt{height:6px;background:${C.border};border-radius:6px;overflow:hidden;}
    .pf{height:100%;border-radius:6px;background:${G};transition:width .7s ease;}
    
    /* Tables */
    .ht{width:100%;border-collapse:collapse;}
    .ht th{padding:12px 16px;font-size:11px;color:${C.muted};text-align:left;text-transform:uppercase;letter-spacing:1.2px;border-bottom:1px solid ${C.border};font-weight:700;background:${dark?"#1A1C20":C.surface};}
    .ht td{padding:13px 16px;font-size:13px;border-bottom:1px solid ${C.border}44;}
    .ht tr:hover td{background:${C.border}28;}
    
    /* Modals */
    .mb{position:fixed;inset:0;background:#000000AA;backdrop-filter:blur(8px);z-index:1000;display:flex;flex-direction:column;align-items:center;padding:20px;overflow-y:auto;}
    .mo{background:${C.card};border:1px solid ${C.border};box-shadow:0 30px 90px rgba(0,0,0,.7);border-radius:24px;max-width:600px;width:100%;margin:auto;display:flex;flex-direction:column;max-height:calc(100vh - 40px);position:relative;animation:m-in .35s cubic-bezier(.2,1,.2,1);overflow:hidden;}
    @keyframes m-in{from{opacity:0;transform:scale(0.95) translateY(20px);}to{opacity:1;transform:scale(1) translateY(0);}}
    
    /* Tabs */
    .tab-bar{display:flex;gap:4px;background:${C.surface};padding:4px;border-radius:10px;width:fit-content;border:1px solid ${C.border};margin-bottom:22px;flex-wrap:wrap;}
    .tab{padding:8px 18px;border-radius:8px;border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;transition:all .18s;}
    .tab.on{background:${G};color:#fff;}
    .tab.off{background:transparent;color:${C.sub};}
    
    /* Fields */
    .field{background:${G}0E;border:1px solid ${G}22;border-radius:10px;padding:12px 16px;}
    .fl{font-size:10px;color:${C.muted};text-transform:uppercase;letter-spacing:1.2px;font-weight:700;margin-bottom:4px;}
    .fv{font-size:13px;color:${G};font-weight:700;}
    .lbl{font-size:12px;color:${C.sub};margin-bottom:8px;font-weight:600;display:block;}
    
    /* Mobile top bar - hidden on desktop */
    .hrm-topbar-mobile{display:none;}
    
    /* Mobile drawer */
    .hrm-drawer{display:none;position:fixed;top:0;left:0;width:min(300px,88vw);height:100vh;background:${C.surface};border-right:1px solid ${C.border};z-index:600;transform:translateX(-110%);transition:transform .28s cubic-bezier(.4,0,.2,1);padding:28px 20px;overflow-y:auto;box-shadow:24px 0 60px rgba(0,0,0,.5);}
    .hrm-drawer.open{transform:translateX(0);}
    .hrm-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);backdrop-filter:blur(3px);z-index:590;opacity:0;transition:opacity .28s ease;pointer-events:none;}
    .hrm-overlay.open{display:block;opacity:1;pointer-events:auto;}
    
    @media(max-width:1024px){
      .hrm{overflow:auto !important;flex-direction:column;height:auto;min-height:100vh;}
      .hrm-sidebar{display:none !important;}
      .hrm-main{margin-left:0 !important;padding-top:64px;width:100% !important;overflow:visible !important;height:auto !important;}
      .hrm-topbar-mobile{display:flex;position:fixed;top:0;left:0;right:0;height:64px;background:${C.surface};border-bottom:1px solid ${C.border};z-index:500;padding:0 20px;align-items:center;justify-content:space-between;box-shadow:0 4px 20px rgba(0,0,0,.3);}
      .hrm-drawer{display:block;}
      .hrm-content-padding{padding:20px 16px;overflow:visible !important;}
    }
    @media(max-width:640px){
      .hrm-content-padding{padding:14px;}
      .tab{padding:7px 12px;font-size:12px;}
      .gc{padding:14px;}
    }
  `;
};

// ─── SHARED ICONS ─────────────────────────────────────────────────────────────
const IC = {
  dashboard:<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  staff:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  presence: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14l2 2 4-4"/></svg>,
  perf:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  payroll:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>,
  tasks:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>,
  mis:      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  profile:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
  payslip:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
  goal:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>,
  sun:      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  moon:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>,
};

// ─── PRIMITIVES ───────────────────────────────────────────────────────────────
const Av = ({ av, sz=36, gold }) => (
  <div style={{ width:sz, height:sz, borderRadius:"50%", flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center", fontSize:sz*0.31, fontWeight:800, background: gold ? `linear-gradient(135deg,${T.orange},#C07010)` : `${T.orange}22`, border:`1.5px solid ${T.orange}${gold?"99":"44"}`, color: gold?"#0F1318":T.orange }}>{av}</div>
);

const ScoreRing = ({ sc, sz=72 }) => {
  const col = sc>=80?"#4ADE80":sc>=60?T.orange:"#F87171";
  const r=28, circ=175.9, dash=(sc/100)*circ;
  return (
    <svg width={sz} height={sz} viewBox="0 0 70 70" style={{ flexShrink:0 }}>
      <circle cx="35" cy="35" r={r} fill="none" stroke="#1C2330" strokeWidth="7"/>
      <circle cx="35" cy="35" r={r} fill="none" stroke={col} strokeWidth="7" strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 35 35)"/>
      <text x="35" y="40" textAnchor="middle" fontSize="15" fontWeight="800" fill={col} fontFamily="inherit">{sc}</text>
    </svg>
  );
};

const Bar = ({ pct, col=T.orange }) => (
  <div className="pt"><div className="pf" style={{ width:`${pct}%`, background:col }}/></div>
);

function Modal({ onClose, title, width=560, children }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  return (
    <div className="mb" onClick={onClose}>
      <div className="mo fade" style={{ maxWidth:width }} onClick={e=>e.stopPropagation()}>
        <div style={{ flexShrink:0, display:"flex", justifyContent:"space-between", alignItems:"center", padding:"28px 32px 12px 32px" }}>
          <div className="ho" style={{ fontSize:19 }}>{title}</div>
          <button onClick={onClose} style={{ background:"none", border:"none", color:C.sub, fontSize:22, cursor:"pointer", padding:4 }}>✕</button>
        </div>
        <div style={{ flex:1, overflowY:"auto", padding:"0 32px 32px 32px" }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, col }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  return (
    <div className="gc" style={{ padding:"20px 22px" }}>
      <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:"1.2px", marginBottom:10, fontWeight:800 }}>{label}</div>
      <div style={{ fontSize:38, fontWeight:800, color:col||T.orange, lineHeight:1 }}>{value}</div>
      {sub && <div style={{ fontSize:12, color:C.sub, marginTop:8 }}>{sub}</div>}
    </div>
  );
}

function Tabs({ items, active, setActive }) {
  return (
    <div className="tab-bar" style={{ marginBottom:22 }}>
      {items.map(([k,l]) => <button key={k} className={`tab ${active===k?"on":"off"}`} onClick={()=>setActive(k)}>{l}</button>)}
    </div>
  );
}

function Field({ label, value }) {
  return <div className="field"><div className="fl">{label}</div><div className="fv">{value||"—"}</div></div>;
}

function Lbl({ children }) { return <span className="lbl">{children}</span>; }

const sevCol = { Minor:"#60A5FA", Moderate:"#FBB040", Serious:T.orange, Critical:"#F87171" };
const sevGrade = { Minor:"D", Moderate:"C", Serious:"B", Critical:"A" };
const sevOrd  = { Minor:1, Moderate:2, Serious:3, Critical:4 };
const pCol = { High:"#F87171", Medium:T.orange, Low:"#4ADE80" };
const sCol = { completed:"#4ADE80", in_progress:"#60A5FA", pending:T.orange };

// ─── STUB DATA (used where real API data is not yet available) ─────────────────
const INIT_ATTENDANCE = [];
const USERS = [];
const PAYROLL_FULL = [];
const PAYROLL_CONTRACTOR = [];
const PAYROLL_ONSITE = [];

// ─── SIDEBAR ──────────────────────────────────────────────────────────────────
function Sidebar({ page, setPage, user, onLogout, items, roleLabel, onMenuOpen }) {
  const { dark, toggle } = useTheme(); const C = dark?DARK:LIGHT;
  const G = T.gold;
  return (
    <div className="hrm-sidebar" style={{ width:260, background:dark?"#111317":"#FFFFFF", borderRight:`1px solid ${C.border}`, display:"flex", flexDirection:"column", flexShrink:0, height:"100vh", position:"relative", zIndex:50 }}>
      <div style={{ padding:"28px 24px 20px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:36 }}>
          <div style={{ width:38, height:38, background:`linear-gradient(135deg,${G},#8B5500)`, borderRadius:10, display:"flex", alignItems:"center", justifyContent:"center", fontSize:17, fontWeight:700, color:"#fff", flexShrink:0 }}>E</div>
          <div style={{ lineHeight:1.2 }}>
            <div style={{ fontSize:16, fontWeight:700, color:G, fontFamily:"'Playfair Display',serif" }}>HR Suite</div>
            <div style={{ fontSize:10, color:C.muted, letterSpacing:"1.8px", fontWeight:700, textTransform:"uppercase" }}>Eximp & Cloves</div>
          </div>
        </div>
        <div style={{ fontSize:9, color:C.muted, letterSpacing:"2px", padding:"0 4px 8px", fontWeight:700, textTransform:"uppercase" }}>{roleLabel}</div>
        <nav style={{ display:"flex", flexDirection:"column", gap:2 }}>
          {items.map(n => (
            <button key={n.id} className={`nb ${page===n.id?"on":""}`} onClick={()=>setPage(n.id)}>
              {IC[n.icon]}{n.label}
            </button>
          ))}
        </nav>
      </div>
      <div style={{ marginTop:"auto", padding:"16px 20px", borderTop:`1px solid ${C.border}` }}>
        <div style={{ background:dark?"rgba(45,47,54,.3)":C.card, borderRadius:14, padding:"14px 16px", border:`1px solid ${C.border}` }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
            <Av av={user.avatar} sz={34}/>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontSize:13, fontWeight:700, color:C.text, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{user.name}</div>
              <div style={{ fontSize:10, color:G, fontWeight:600, textTransform:"uppercase", letterSpacing:"1px" }}>{(user.role||"").replace("_"," ")}</div>
            </div>
            <button onClick={toggle} style={{ background:"none", border:"none", cursor:"pointer", color:C.muted, display:"flex", flexShrink:0 }}>
              <div style={{ width:15, height:15 }}>{dark?IC.sun:IC.moon}</div>
            </button>
          </div>
          <button className="bg" onClick={onLogout} style={{ width:"100%", fontSize:12, padding:"7px 12px" }}>Sign Out</button>
        </div>
      </div>
    </div>
  );
}

function Topbar({ title, user }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  return (
    <div style={{ height:54, background:dark?"#111317":"#FFFFFF", borderBottom:`1px solid ${C.border}`, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 28px", flexShrink:0 }}>
      <div style={{ fontFamily:"'Playfair Display',serif", fontSize:17, color:T.gold }}>{title}</div>
      <div style={{ display:"flex", alignItems:"center", gap:12 }}>
        <span className="tg to" style={{ fontSize:10 }}>{(user.staffType||user.role||"").toUpperCase()} ACCESS</span>
        <span style={{ fontSize:12, color:C.muted }}>{new Date().toLocaleDateString(undefined,{weekday:"short",day:"numeric",month:"short",year:"numeric"})}</span>
      </div>
    </div>
  );
}

// Authentication is now handled by the main platform.
// Redirection logic is in the App component.


// ─── GOAL FORM MODAL CONTENT ─────────────────────────────────────────────────
function GoalForm({ onSave, staffList=[] }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [f, setF] = useState({ uid:"", kpi:"", target:"", unit:"", period:"Apr 2026", status:"Draft" });
  const kpiMap = {
    "Sales & Acquisitions":["Deals Closed","Collection Rate (%)","Lead Follow-ups","KYC Completion Rate (%)","Inspection-to-Contract Rate (%)"],
    "Property Management": ["Client Satisfaction Score","Listing Turnaround (days)","Lease Renewals","Property Valuations Completed"],
    "Construction":        ["Site Inspections Done","Safety Compliance Score (%)","Tasks Completed On Time","Defect Rate (%)"],
    "Marketing":           ["Campaigns Sent","Email Open Rate (%)","New Leads Added","Lead Engagement Score","A/B Test Adoption (%)"],
    "Legal & Compliance":  ["Contracts Drafted","Compliance Audits Passed","Escalated Disputes Resolved"],
    "Human Resources":     ["Team Target Achievement (%)","Onboarding Completed","Policy Reviews Done"],
  };
  const selUser = staffList.find(u => u.id === f.uid);
  const kpis = selUser ? (kpiMap[selUser.department]||["Custom KPI 1","Custom KPI 2"]) : [];

  const save = () => {
    if (!f.uid||!f.kpi||!f.target) return;
    onSave({ ...f, target:parseFloat(f.target), actual:0 });
  };

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
      <div>
        <Lbl>Staff Member *</Lbl>
        <select className="inp" value={f.uid} onChange={e=>setF(x=>({...x,uid:e.target.value,kpi:""}))}>
          <option value="">— Select Staff Member —</option>
          {staffList.filter(u=>u.role!=="hr_admin").map(u=><option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
        </select>
      </div>
      <div>
        <Lbl>KPI / Goal Type *</Lbl>
        <select className="inp" value={f.kpi} onChange={e=>setF(x=>({...x,kpi:e.target.value}))} disabled={!f.uid}>
          <option value="">— Select KPI for this role —</option>
          {kpis.map(k=><option key={k}>{k}</option>)}
        </select>
        {!f.uid && <div style={{ fontSize:11, color:(dark?DARK:LIGHT).muted, marginTop:4 }}>Select a staff member first to see role-relevant KPIs.</div>}
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
        <div><Lbl>Target Value *</Lbl><input className="inp" type="number" placeholder="e.g. 8" value={f.target} onChange={e=>setF(x=>({...x,target:e.target.value}))}/></div>
        <div><Lbl>Unit</Lbl><input className="inp" placeholder="e.g. deals, %, sites" value={f.unit} onChange={e=>setF(x=>({...x,unit:e.target.value}))}/></div>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
        <div>
          <Lbl>Period</Lbl>
          <select className="inp" value={f.period} onChange={e=>setF(x=>({...x,period:e.target.value}))}>
            {["Apr 2026","May 2026","Jun 2026","Jul 2026","Aug 2026"].map(p=><option key={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <Lbl>Status</Lbl>
          <select className="inp" value={f.status} onChange={e=>setF(x=>({...x,status:e.target.value}))}>
            <option value="Draft">Draft — editable</option>
            <option value="Published">Published — locked</option>
          </select>
        </div>
      </div>
      <button className="bp" onClick={save} style={{ padding:12 }}>Save Goal</button>
    </div>
  );
}

// ─── LEAVE REQUEST FORM ───────────────────────────────────────────────────────
function LeaveForm({ onSave, currentUserId }) {
  const [f, setF] = useState({ uid: currentUserId ? String(currentUserId) : "", type:"Annual Leave", from:"", to:"", reason:"" });
  const fmt = d => new Date(d).toLocaleDateString("en-GB",{day:"numeric",month:"short"});
  const save = () => {
    if (!f.uid||!f.from||!f.to) return;
    const days = Math.max(1, Math.round((new Date(f.to)-new Date(f.from))/(864e5))+1);
    onSave({ id:Date.now(), uid:parseInt(f.uid), type:f.type, from:fmt(f.from), to:fmt(f.to), days, status:"Pending", reason:f.reason });
  };
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
      {!currentUserId && (
        <div>
          <Lbl>Staff Member *</Lbl>
          <select className="inp" value={f.uid} onChange={e=>setF(x=>({...x,uid:e.target.value}))}>
            <option value="">— Select Staff Member —</option>
            {USERS.filter(u=>u.role!=="hr_admin").map(u=><option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
        </div>
      )}
      <div>
        <Lbl>Leave Type *</Lbl>
        <select className="inp" value={f.type} onChange={e=>setF(x=>({...x,type:e.target.value}))}>
          {["Annual Leave","Sick Leave","Study Leave","Maternity Leave","Paternity Leave","Compassionate Leave"].map(t=><option key={t}>{t}</option>)}
        </select>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
        <div><Lbl>From *</Lbl><input className="inp" type="date" value={f.from} onChange={e=>setF(x=>({...x,from:e.target.value}))}/></div>
        <div><Lbl>To *</Lbl><input className="inp" type="date" value={f.to} onChange={e=>setF(x=>({...x,to:e.target.value}))}/></div>
      </div>
      <div><Lbl>Reason</Lbl><textarea className="inp" placeholder="Brief reason for leave request…" value={f.reason} onChange={e=>setF(x=>({...x,reason:e.target.value}))}/></div>
      <button className="bp" onClick={save} style={{ padding:12 }}>Submit Request</button>
    </div>
  );
}


function Goals({ viewOnly, userId }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [goals, setGoals] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    setLoading(true);
    const params = viewOnly ? `?staff_id=${userId}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/goals${params}`),
      !viewOnly ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([g, s]) => {
      setGoals(g);
      setStaff(s);
    }).finally(() => setLoading(false));
  }, [viewOnly, userId]);

  const refresh = () => {
    const params = viewOnly ? `?staff_id=${userId}` : "";
    apiFetch(`${API_BASE}/hr/goals${params}`).then(setGoals);
  };

  const saveGoal = async (g) => {
    try {
      await apiFetch(`${API_BASE}/hr/goals`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: g.uid,
          kpi_name: g.kpi,
          target_value: g.target,
          unit: g.unit,
          weight: 1.0, // Default weight
          month: new Date().toISOString().split('T')[0]
        })
      });
      setShowNew(false);
      refresh();
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  return (
    <div className="fade">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>{viewOnly?"My Goals":"Goal Management"}</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>Monthly targets per staff member. These feed directly into performance scores.</div>
        </div>
        {!viewOnly && <button className="bp" onClick={()=>setShowNew(true)}>+ Set KPI Goal</button>}
      </div>

      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading goals…</div>
      ) : goals.length === 0 ? (
        <div className="gc" style={{ padding:40, textAlign:"center" }}>
          <div style={{ fontSize:13, color:C.muted }}>No goals on record for this period.</div>
        </div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:14 }}>
          {goals.map((g, i) => {
            const u = g.admins || {};
            const pct = g.target_value > 0 ? Math.min(Math.round((g.actual_value / g.target_value) * 100), 100) : 0;
            const hit = g.actual_value >= g.target_value;
            return (
              <div key={i} className="gc" style={{ padding:22 }}>
                {!viewOnly && (
                  <div style={{ display:"flex", gap:10, alignItems:"center", marginBottom:14 }}>
                    <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={26}/>
                    <div style={{ fontSize:13, fontWeight:800, color:C.text }}>{u.full_name}</div>
                    <div style={{ fontSize:11, color:C.muted, marginLeft:4 }}>{u.department}</div>
                  </div>
                )}
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
                  <div>
                    <div style={{ fontSize:15, fontWeight:800, color:T.orange }}>{g.kpi_name}</div>
                    <div style={{ fontSize:12, color:C.muted }}>{new Date(g.month).toLocaleDateString(undefined, {month:'long', year:'numeric'})}</div>
                  </div>
                  <span className={`tg tg2`}>Active</span>
                </div>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:8 }}>
                  <span style={{ fontSize:13, color:C.sub }}>Target: <b style={{ color:C.text }}>{g.target_value} {g.unit}</b></span>
                  <span style={{ fontSize:18, fontWeight:800, color:hit?"#4ADE80":"#F87171" }}>{g.actual_value || 0} {g.unit}</span>
                </div>
                <Bar pct={pct} col={hit?"#4ADE80":T.orange}/>
                <div style={{ fontSize:11, color:hit?"#4ADE80":"#F87171", marginTop:6, fontWeight:700 }}>
                  {hit?`✓ Target met (${pct}%)`:`${pct}% achieved — ${g.target_value-(g.actual_value||0)} ${g.unit} remaining`}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showNew && (
        <Modal onClose={()=>setShowNew(false)} title="Set New Goal">
          <GoalForm staffList={staff} onSave={saveGoal}/>
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: PRESENCE ────────────────────────────────────────────────────────
function Presence({ currentUserId }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [sub, setSub]   = useState("attendance");
  const [reqs, setReqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API_BASE}/hr/presence/leaves`),
      apiFetch(`${API_BASE}/hr/presence/attendance`)
    ]).then(([l, a]) => {
      setReqs(l);
      setAttendance(a);
    }).finally(() => setLoading(false));
  }, []);

  const [attendance, setAttendance] = useState([]);

  const refresh = () => Promise.all([
    apiFetch(`${API_BASE}/hr/leave/pending`),
    apiFetch(`${API_BASE}/hr/presence/attendance`)
  ]).then(([l, a]) => { setReqs(l); setAttendance(a); });

  const updateLeave = async (id, status) => {
    try {
       // I'll add this endpoint to the backend in the next step
       await apiFetch(`${API_BASE}/hr/leave/${id}/status`, {
         method: "PATCH",
         body: JSON.stringify({ status })
       });
       refresh();
    } catch (e) {
       alert("Error: " + e.message);
    }
  };


  const leaveVisible = currentUserId
    ? reqs.filter(l=>l.staff_id===currentUserId)
    : reqs;

  const statusColor = { Present:"#4ADE80", "On Leave":T.orange, Late:"#FBB040", Absent:"#F87171" };

  return (
    <div className="fade">
      <div className="ho" style={{ fontSize:22, marginBottom:4 }}>Presence</div>
      <div style={{ fontSize:13, color:(dark?DARK:LIGHT).sub, marginBottom:18 }}>Attendance tracking and leave management — one tab.</div>

      <Tabs items={[["attendance","Attendance"],["leave","Leave Management"]]} active={sub} setActive={setSub}/>

      {sub==="attendance" && (
        <>
          {!currentUserId && (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, marginBottom:22 }}>
              <StatCard label="Present"  value="5" col="#4ADE80"/>
              <StatCard label="On Leave" value="1" col={T.orange}/>
              <StatCard label="Late"     value="1" col="#FBB040"/>
              <StatCard label="Absent"   value="0" col="#F87171"/>
            </div>
          )}
          <div className="gc" style={{ overflow:"hidden" }}>
            <div style={{ padding:"14px 20px", borderBottom:`1px solid ${C.border}` }}>
              <div className="ho" style={{ fontSize:14 }}>Monday, April 13, 2026</div>
            </div>
            <table className="ht">
              <thead><tr>{["Employee","Department","Check In","Check Out","Hours","Status"].map(h=><th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {attendance.map(a=>{
                  const u = { name: "Staff Member", avatar: "??" }; // Placeholder for mockup
                  const sc=statusColor[a.status]||C.sub;
                  return (
                    <tr key={a.uid}>
                      <td><div style={{ display:"flex", alignItems:"center", gap:10 }}><Av av={u?.avatar} sz={28}/><span style={{ fontWeight:700 }}>{u?.name}</span></div></td>
                      <td style={{ color:C.sub }}>Property Mgmt</td>
                      <td>{a.checkIn}</td>
                      <td>{a.checkOut}</td>
                      <td style={{ color:T.orange, fontWeight:800 }}>{a.hours}</td>
                      <td><span className="tg" style={{ background:`${sc}22`, color:sc, border:`1px solid ${sc}33` }}>{a.status}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {sub==="leave" && (
        <>
          <div className="gc" style={{ overflow:"hidden" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"14px 20px", borderBottom:`1px solid ${C.border}` }}>
              <div className="ho" style={{ fontSize:14 }}>{currentUserId ? "My Leave Requests" : "Pending Leave Requests"}</div>
              <button className="bp" style={{ fontSize:12, padding:"7px 16px" }} onClick={()=>setShowForm(true)}>+ New Request</button>
            </div>
            <div style={{ padding:18, display:"flex", flexDirection:"column", gap:12 }}>
              {loading ? <div style={{ textAlign:"center", padding:20, color:C.muted }}>Loading leave records…</div> : 
               leaveVisible.map(l=>{
                const u = l.admins || {};
                const sc={approved:"#4ADE80",rejected:"#F87171",pending:"#FBB040"}[l.status];
                return (
                  <div key={l.id} style={{ display:"flex", alignItems:"center", gap:16, padding:"14px 16px", background:`${T.orange}08`, border:`1px solid ${T.orange}22`, borderRadius:12 }}>
                    <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={38}/>
                    <div style={{ flex:1 }}>
                      <div style={{ fontWeight:800, color:C.text, fontSize:14 }}>{u.full_name}</div>
                      <div style={{ fontSize:12, color:C.sub, marginTop:2 }}>{l.leave_type} · {new Date(l.start_date).toLocaleDateString()} → {new Date(l.end_date).toLocaleDateString()} · <span style={{ color:T.orange, fontWeight:800 }}>{l.days_count} days</span></div>
                      {l.reason && <div style={{ fontSize:12, color:C.muted, marginTop:2, fontStyle:"italic" }}>"{l.reason}"</div>}
                    </div>
                    <div style={{ display:"flex", gap:8, alignItems:"center", flexShrink:0 }}>
                      <span className="tg" style={{ background:`${sc}22`, color:sc, border:`1px solid ${sc}33`, textTransform:"capitalize" }}>{l.status}</span>
                      {l.status==="pending" && !currentUserId && (
                        <>
                          <button className="bp" style={{ fontSize:11, padding:"5px 12px" }} onClick={()=>updateLeave(l.id,"approved")}>Approve</button>
                          <button className="bd" style={{ fontSize:11 }} onClick={()=>updateLeave(l.id,"rejected")}>Reject</button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
              {!loading && leaveVisible.length===0 && <div style={{ fontSize:13, color:C.muted, padding:"12px 0", textAlign:"center" }}>No leave requests found.</div>}
            </div>
          </div>
        </>
      )}

      {showForm && (
        <Modal onClose={()=>setShowForm(false)} title="New Leave Request">
          <LeaveForm
            currentUserId={currentUserId||null}
            onSave={async (l)=>{ 
               try {
                  await apiFetch(`${API_BASE}/hr/leave`, {
                    method: "POST",
                    body: JSON.stringify({
                       leave_type: l.type,
                       start_date: l.from_raw,
                       end_date: l.to_raw,
                       days_count: l.days,
                       reason: l.reason
                    })
                  });
                  refresh();
                  setShowForm(false);
               } catch (e) {
                  alert(e.message);
               }
            }}
          />
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: PERFORMANCE ──────────────────────────────────────────────────────
function Performance({ viewOnly, userId }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showRev, setShowRev] = useState(false);
  const [rev, setRev] = useState({ teamwork:3, initiative:3, quality:80, notes:"" });

  useEffect(() => {
    setLoading(true);
    if (viewOnly) {
       apiFetch(`${API_BASE}/hr/performance/${userId}`)
         .then(d => setDetail(d))
         .finally(() => setLoading(false));
    } else {
       apiFetch(`${API_BASE}/hr/staff`)
         .then(d => setStaff(d))
         .finally(() => setLoading(false));
    }
  }, [viewOnly, userId]);

  useEffect(() => {
    if (sel) {
      setDetail(null);
      apiFetch(`${API_BASE}/hr/performance/${sel.id}`).then(d => setDetail(d));
    }
  }, [sel]);

  const submitReview = async () => {
    try {
      await apiFetch(`${API_BASE}/hr/performance/review`, {
        method: "POST",
        body: JSON.stringify({
           staff_id: sel.id,
           quality_score: rev.quality,
           teamwork_score: rev.teamwork,
           leadership_score: rev.initiative,
           attitude_score: rev.initiative,
           review_period: new Date().toISOString().split('T')[0],
           comments: rev.notes
        })
      });
      setShowRev(false);
      alert("Review submitted successfully!");
      // Refresh
      apiFetch(`${API_BASE}/hr/performance/${sel.id}`).then(d => setDetail(d));
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  const renderDetail = (u, p) => {
    if (!p) return <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading performance details…</div>;
    const sc = p.score;
    const col = sc>=80?"#4ADE80":sc>=60?T.orange:"#F87171";
    const b = p.breakdown || {};
    
    return (
      <div style={{ maxWidth:700 }}>
        {!viewOnly && <button className="bg" onClick={()=>setSel(null)} style={{ marginBottom:18, fontSize:12 }}>← All Staff</button>}
        <div style={{ display:"flex", alignItems:"center", gap:20, marginBottom:26 }}>
          <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={62} gold/>
          <div style={{ flex:1 }}>
            <div className="ho" style={{ fontSize:22 }}>{u.full_name}</div>
            <div style={{ fontSize:13, color:C.sub }}>{u.staff_profiles?.[0]?.job_title || u.role} · {u.department}</div>
          </div>
          <div style={{ textAlign:"center" }}>
            <div style={{ fontSize:46, fontWeight:800, color:col, lineHeight:1 }}>{sc}</div>
            <div style={{ fontSize:11, color:C.muted }}>Overall Score</div>
          </div>
        </div>

        <div className="gc" style={{ padding:22, marginBottom:16 }}>
          <div className="ho" style={{ fontSize:14, marginBottom:18 }}>Performance Metrics Breakdown</div>
          {[["KPI Goals Achievement (40%)", b.goals_40_pct,"#4ADE80"],["Work Quality (20%)", b.quality_20_pct,"#60A5FA"],["Manager Review (40%)", b.manager_review_40_pct,T.orange]].map(([l,v,c])=>(
            <div key={l} style={{ marginBottom:16 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
                <span style={{ fontSize:13, color:C.sub }}>{l}</span>
                <span style={{ fontSize:17, fontWeight:800, color:c }}>{Math.round(v)}%</span>
              </div>
              <div className="pt" style={{ height:8 }}><div className="pf" style={{ width:`${v}%`, background:c }}/></div>
            </div>
          ))}
        </div>

        {!viewOnly && (
          <div style={{ display:"flex", gap:12 }}>
            <button className="bp" onClick={()=>setShowRev(true)}>Enter Formal Review</button>
            <button className="bg">Download Performance Report</button>
          </div>
        )}

        {showRev && (
          <Modal onClose={()=>setShowRev(false)} title={`Formal Review: ${u.full_name}`}>
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <div><Lbl>Work Quality (0–100)</Lbl>
                <input className="inp" type="number" value={rev.quality} onChange={e=>setRev(r=>({...r,quality:+e.target.value}))}/>
              </div>
              <div><Lbl>Teamwork & Communication (1–5)</Lbl>
                <select className="inp" value={rev.teamwork} onChange={e=>setRev(r=>({...r,teamwork:+e.target.value}))}>
                  {[1,2,3,4,5].map(n=><option key={n} value={n}>{n} — {["","Poor","Below Average","Average","Good","Excellent"][n]}</option>)}
                </select>
              </div>
              <div><Lbl>Initiative & Growth (1–5)</Lbl>
                <select className="inp" value={rev.initiative} onChange={e=>setRev(r=>({...r,initiative:+e.target.value}))}>
                  {[1,2,3,4,5].map(n=><option key={n} value={n}>{n} — {["","Poor","Below Average","Average","Good","Excellent"][n]}</option>)}
                </select>
              </div>
              <div><Lbl>Review Notes</Lbl><textarea className="inp" placeholder="Optional notes on this review cycle…" value={rev.notes} onChange={e=>setRev(r=>({...r,notes:e.target.value}))}/></div>
              <button className="bp" onClick={submitReview} style={{ padding:12 }}>Submit Formal Review</button>
            </div>
          </Modal>
        )}
      </div>
    );
  };

  if (loading) return <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading performance metrics…</div>;

  if (viewOnly) {
    return <div className="fade">{renderDetail({ full_name: "My Profile" }, detail)}</div>;
  }

  return (
    <div className="fade">
      <div className="ho" style={{ fontSize:22, marginBottom:6 }}>Performance Dashboard</div>
      <div style={{ fontSize:13, color:C.sub, marginBottom:22 }}>Automated monthly scoring — computed from KPIs and manager reviews.</div>

      {!sel ? (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:16 }}>
          {staff.map(u=>{
            const p = u.performance || { score:0, rating:"Pending", breakdown: { goals_40_pct:0, quality_20_pct:0, manager_review_40_pct:0 } };
            const sc = p.score || 0; 
            const col = sc>=80?"#4ADE80":sc>=60?T.orange:"#F87171";
            const b = p.breakdown || {};
            return (
              <div key={u.id} className="gc" style={{ padding:22, cursor:"pointer" }} onClick={()=>setSel(u)}>
                  <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:16 }}>
                    <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={40}/>
                    <div><div style={{ fontSize:14, fontWeight:800, color:C.text }}>{u.full_name}</div><div style={{ fontSize:12, color:C.sub }}>{u.department || 'Staff'}</div></div>
                  </div>
                  <div style={{ display:"flex", alignItems:"center", gap:14, marginBottom:16 }}>
                    <ScoreRing sc={sc} sz={68}/>
                    <div>
                      <div style={{ fontSize:22, fontWeight:800, color:col }}>{sc}<span style={{ fontSize:13, color:C.muted }}>/100</span></div>
                      <span className={`tg ${sc>=80?"tg2":sc>=60?"to":"tr"}`}>{p.rating}</span>
                    </div>
                  </div>
                {[["KPI",b.goals_40_pct],["Quality",b.quality_20_pct],["Manager Review",b.manager_review_40_pct]].map(([l,v])=>(
                  <div key={l} style={{ marginBottom:8 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:C.muted, marginBottom:4 }}><span>{l}</span><span style={{ color:T.orange, fontWeight:800 }}>{Math.round(v||0)}%</span></div>
                    <Bar pct={v||0}/>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      ) : renderDetail(sel, detail)}
    </div>
  );
}

// ─── MODULE: TASKS ────────────────────────────────────────────────────────────
function Tasks({ currentUser }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [tasks, setTasks] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [viewT, setViewT] = useState(null);
  const [nt, setNt] = useState({ title:"", assignedTo:"", due:"", priority:"Medium", project:"", desc:"" });

  const isHR = currentUser.role?.includes("admin") || currentUser.primary_role === "hr";
  const isLM = currentUser.role?.includes("line_manager");
  const isStaff = !isHR && !isLM;

  useEffect(() => {
    setLoading(true);
    const params = isStaff ? `?staff_id=${currentUser.id}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/tasks${params}`),
      (isHR || isLM) ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([t, s]) => {
      setTasks(t);
      setStaff(s);
    }).finally(() => setLoading(false));
  }, [currentUser.id]);

  const refresh = () => {
    const params = isStaff ? `?staff_id=${currentUser.id}` : "";
    apiFetch(`${API_BASE}/hr/tasks${params}`).then(setTasks);
  };

  const add = async () => {
    if (!nt.title || !nt.assignedTo || !nt.due) return;
    try {
      await apiFetch(`${API_BASE}/hr/tasks`, {
        method: "POST",
        body: JSON.stringify({
          assigned_to: nt.assignedTo,
          title: nt.title,
          due_date: nt.due,
          priority: nt.priority,
          notes: nt.desc
        })
      });
      setNt({title:"",assignedTo:"",due:"",priority:"Medium",project:"",desc:""});
      setShowNew(false);
      refresh();
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  const updateStatus = async (taskId, status) => {
    try {
       // I'll add a generic PATCH for tasks later or just use individual updates
       // For now, let's assume we have it or use what's available
       setTasks(prev => prev.map(t => t.id === taskId ? {...t, status} : t));
       if (viewT) setViewT({...viewT, status});
    } catch (e) {
       alert(e.message);
    }
  };

  const canCreate = isHR || isLM;
  const canEdit = t => isHR || (isLM && t.assigned_by === currentUser.id);

  return (
    <div className="fade">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>{isStaff ? "My Tasks" : "Task Manager"}</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>
            {isStaff ? "Tasks assigned to you. Complete tasks to boost your performance score."
             : "Assign and track tasks across the team. Overdue tasks trigger automated alerts."}
          </div>
        </div>
        {canCreate && <button className="bp" onClick={()=>setShowNew(true)}>+ Assign Task</button>}
      </div>

      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading tasks…</div>
      ) : tasks.length === 0 ? (
        <div className="gc" style={{ padding:40, textAlign:"center", color:C.muted }}>No tasks found for this period.</div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:isStaff?"repeat(2,1fr)":"repeat(3,1fr)", gap:14 }}>
          {tasks.map(t=>{
            const u = t.admins || {};
            const pc = pCol[t.priority] || T.orange;
            const sc = sCol[t.status] || T.orange;
            return (
              <div key={t.id} className="gc" style={{ padding:20, cursor:"pointer" }} onClick={()=>setViewT(t)}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:10 }}>
                  <span className="tg" style={{ background:`${pc}22`, color:pc, border:`1px solid ${pc}33` }}>{t.priority}</span>
                  <span className="tg" style={{ background:`${sc}22`, color:sc, border:`1px solid ${sc}33`, textTransform:"capitalize" }}>{t.status}</span>
                </div>
                <div style={{ fontSize:14, fontWeight:800, color:C.text, marginBottom:6, lineHeight:1.4 }}>{t.title}</div>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginTop:12 }}>
                  {!isStaff && <div style={{ display:"flex", alignItems:"center", gap:8 }}><Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={24}/><span style={{ fontSize:12, color:C.sub }}>{u.full_name?.split(" ")[0]}</span></div>}
                  <span style={{ fontSize:11, color:C.muted }}>Due {new Date(t.due_date).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {viewT && (
        <Modal onClose={()=>setViewT(null)} title={viewT.title}>
          <div style={{ display:"flex", gap:8, marginBottom:16 }}>
            <span className="tg" style={{ background:`${pCol[viewT.priority]}22`, color:pCol[viewT.priority], border:`1px solid ${pCol[viewT.priority]}33` }}>{viewT.priority} Priority</span>
            <span className="tg" style={{ background:`${sCol[viewT.status]}22`, color:sCol[viewT.status], border:`1px solid ${sCol[viewT.status]}33` }}>{viewT.status}</span>
          </div>
          <div style={{ fontSize:13, color:(dark?DARK:LIGHT).sub, marginBottom:18, lineHeight:1.7 }}>{viewT.notes||"No description provided."}</div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:18 }}>
            <Field label="Staff Member" value={viewT.admins?.full_name}/>
            <Field label="Due Date" value={new Date(viewT.due_date).toLocaleDateString()}/>
            <Field label="Priority" value={viewT.priority}/>
            <Field label="Status" value={viewT.status}/>
          </div>
          {(isStaff || canEdit(viewT)) && (
            <div>
              <div style={{ fontSize:12, color:(dark?DARK:LIGHT).muted, marginBottom:10, fontWeight:800 }}>Update Task Status</div>
              <div style={{ display:"flex", gap:10 }}>
                {["pending","in_progress","completed"].map(s=>(
                  <button key={s} className={viewT.status===s?"bp":"bg"} style={{ flex:1, fontSize:12, textTransform:"capitalize" }}
                    onClick={()=>updateStatus(viewT.id, s)}>
                    {s.replace("_"," ")}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Modal>
      )}

      {showNew && (
        <Modal onClose={()=>setShowNew(false)} title="Assign New Task">
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <div><Lbl>Task Title *</Lbl><input className="inp" placeholder="e.g. Prepare Q2 valuation report" value={nt.title} onChange={e=>setNt(n=>({...n,title:e.target.value}))}/></div>
            <div><Lbl>Assign To *</Lbl>
              <select className="inp" value={nt.assignedTo} onChange={e=>setNt(n=>({...n,assignedTo:e.target.value}))}>
                <option value="">— Select Staff Member —</option>
                {staff.map(u=><option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <div><Lbl>Due Date *</Lbl><input type="date" className="inp" value={nt.due} onChange={e=>setNt(n=>({...n,due:e.target.value}))}/></div>
              <div><Lbl>Priority</Lbl>
                <select className="inp" value={nt.priority} onChange={e=>setNt(n=>({...n,priority:e.target.value}))}>
                  <option>High</option><option>Medium</option><option>Low</option>
                </select>
              </div>
            </div>
            <div><Lbl>Description</Lbl><textarea className="inp" placeholder="Task details and instructions…" value={nt.desc} onChange={e=>setNt(n=>({...n,desc:e.target.value}))}/></div>
            <button className="bp" onClick={add} style={{ padding:12 }}>Assign Task</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: MISMANAGEMENT ────────────────────────────────────────────────────
function Mismanagement({ viewOnly, userId, isManager }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [incidents, setIncidents] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showLog, setShowLog] = useState(false);
  const [f, setF] = useState({ uid:"", type:"", severity:"Minor", note:"" });

  useEffect(() => {
    setLoading(true);
    const params = viewOnly ? `?staff_id=${userId}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/mismanagement${params}`),
      !viewOnly ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([i, s]) => {
      setIncidents(i);
      setStaff(s);
    }).finally(() => setLoading(false));
  }, [viewOnly, userId]);

  const refresh = () => {
    const params = viewOnly ? `?staff_id=${userId}` : "";
    apiFetch(`${API_BASE}/hr/mismanagement${params}`).then(setIncidents);
  };

  const add = async () => {
    if(!f.uid || !f.type) return;
    try {
      await apiFetch(`${API_BASE}/hr/mismanagement`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: f.uid,
          incident_type: f.type,
          severity: f.severity,
          notes: f.note
        })
      });
      setF({uid:"",type:"",severity:"Minor",note:""});
      setShowLog(false);
      refresh();
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  const summary = {};
  incidents.forEach(l => {
    if(!summary[l.staff_id]) summary[l.staff_id] = { flags:[], max:0 };
    summary[l.staff_id].flags.push(l);
    if(sevOrd[l.severity] > summary[l.staff_id].max) summary[l.staff_id].max = sevOrd[l.severity];
  });

  return (
    <div className="fade">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>Mismanagement Dashboard</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>
            {viewOnly?"Your flagged incidents. Contact HR or your line manager to resolve."
             :"Graded incident tracking — records are visible to HR, Managers, and the individual."}
          </div>
        </div>
        {!viewOnly && <button className="bp" onClick={()=>setShowLog(true)}>+ Log Incident</button>}
      </div>

      <div style={{ display:"flex", gap:10, marginBottom:22, flexWrap:"wrap" }}>
        {[["Minor","D","Counselling noted"],["Moderate","C","Formal warning"],["Serious","B","Written warning + PIP"],["Critical","A","Disciplinary action"]].map(([s,g,desc])=>(
          <div key={s} style={{ display:"flex", alignItems:"center", gap:10, padding:"9px 14px", background:`${sevCol[s]}14`, border:`1px solid ${sevCol[s]}33`, borderRadius:10 }}>
            <div style={{ width:28, height:28, borderRadius:"50%", background:sevCol[s], display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, fontWeight:800, color:"#0F1318" }}>{g}</div>
            <div><div style={{ fontSize:12, fontWeight:800, color:sevCol[s] }}>{s}</div><div style={{ fontSize:10, color:C.muted }}>{desc}</div></div>
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading incident logs…</div>
      ) : Object.keys(summary).length === 0 ? (
        <div className="gc" style={{ padding:48, textAlign:"center" }}>
          <div style={{ fontSize:28, marginBottom:12, color:"#4ADE80" }}>✓</div>
          <div style={{ color:"#4ADE80", fontWeight:800 }}>No mismanagement flags on record</div>
        </div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:16 }}>
          {Object.entries(summary).map(([uid,data])=>{
            const u = data.flags[0]?.admins || {};
            const worst = Object.entries(sevOrd).find(([,v])=>v===data.max)?.[0] || "Minor";
            const wc = sevCol[worst];
            return (
              <div key={uid} className="gc" style={{ padding:20, border:`1px solid ${wc}44`, boxShadow:`0 0 0 1px ${wc}22,0 0 14px ${wc}18` }}>
                <div style={{ display:"flex", gap:14, alignItems:"center", marginBottom:14 }}>
                  <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={42}/>
                  <div style={{ flex:1 }}><div style={{ fontWeight:800, color:C.text, fontSize:14 }}>{u.full_name}</div><div style={{ fontSize:12, color:C.sub }}>{u.department}</div></div>
                  <div style={{ width:36, height:36, borderRadius:"50%", background:wc, display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, fontWeight:800, color:"#0F1318" }}>{sevGrade[worst]}</div>
                </div>
                <div style={{ fontSize:12, color:C.muted, marginBottom:10 }}>{data.flags.length} incident{data.flags.length!==1?"s":""} on record</div>
                {data.flags.map((fl,i)=>(
                  <div key={i} style={{ padding:"9px 12px", background:`${sevCol[fl.severity]}10`, border:`1px solid ${sevCol[fl.severity]}22`, borderRadius:8, marginBottom:8 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                      <span style={{ fontSize:12, fontWeight:800, color:sevCol[fl.severity] }}>{fl.type}</span>
                      <span style={{ fontSize:11, color:C.muted }}>{new Date(fl.created_at).toLocaleDateString()}</span>
                    </div>
                    <div style={{ fontSize:11, color:C.sub }}>{fl.notes}</div>
                    <div style={{ fontSize:10, color:C.muted, marginTop:4 }}>Ref: INC-{fl.id}</div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {showLog && (
        <Modal onClose={()=>setShowLog(false)} title="Log Mismanagement Incident">
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <div><Lbl>Staff Member *</Lbl>
              <select className="inp" value={f.uid} onChange={e=>setF(x=>({...x,uid:e.target.value}))}>
                <option value="">— Select Staff Member —</option>
                {staff.map(u=><option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div><Lbl>Incident Type *</Lbl>
              <select className="inp" value={f.type} onChange={e=>setF(x=>({...x,type:e.target.value}))}>
                <option value="">— Select Type —</option>
                {["Unauthorized Absence","Repeated Late Arrival","Missed Task Deadline","Safety Protocol Breach","Insubordination","KPI Failure (3+ months)","Unprofessional Conduct","Budget Overrun","Escalated Complaint"].map(t=><option key={t}>{t}</option>)}
              </select>
            </div>
            <div><Lbl>Severity Grade</Lbl>
              <select className="inp" value={f.severity} onChange={e=>setF(x=>({...x,severity:e.target.value}))}>
                <option>Minor</option><option>Moderate</option><option>Serious</option><option>Critical</option>
              </select>
            </div>
            <div><Lbl>Notes / Evidence</Lbl><textarea className="inp" placeholder="Describe the incident in detail…" value={f.note} onChange={e=>setF(x=>({...x,note:e.target.value}))}/></div>
            <button className="bp" onClick={add} style={{ padding:12 }}>Log Incident</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: PAYROLL ──────────────────────────────────────────────────────────
function Payroll() {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [tab, setTab] = useState("full");
  const [payroll, setPayroll] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [staff, setStaff] = useState([]);
  const [nf, setNf] = useState({ uid:"", gross:"", tax:"0", notes:"" });
  const fmt = n => n != null ? `₦${Number(n).toLocaleString()}` : "—";

  const handleRunPayroll = async () => {
    if (!confirm("Are you sure you want to run payroll for the current month? This will generate records for all active staff.")) return;
    setLoading(true);
    try {
      const res = await apiFetch(`${API_BASE}/hr/payroll/run`, { method: "POST" });
      alert(res.message);
      const updated = await apiFetch(`${API_BASE}/hr/payroll/payslips`);
      setPayroll(updated);
    } catch (e) {
      alert("Payroll error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API_BASE}/hr/payroll/payslips`),
      apiFetch(`${API_BASE}/hr/staff`)
    ]).then(([p, s]) => {
      setPayroll(p);
      setStaff(s);
    }).catch(() => setPayroll([]))
      .finally(() => setLoading(false));
  }, []);

  const addManual = async () => {
    if(!nf.uid || !nf.gross) return;
    setLoading(true);
    try {
      await apiFetch(`${API_BASE}/hr/payroll/manual`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: nf.uid,
          gross_pay: parseFloat(nf.gross),
          tax: parseFloat(nf.tax),
          net_pay: parseFloat(nf.gross) - parseFloat(nf.tax),
          notes: nf.notes,
          period_start: new Date().toISOString().split('T')[0]
        })
      });
      setShowAdd(false);
      setNf({ uid:"", gross:"", tax:"0", notes:"" });
      const updated = await apiFetch(`${API_BASE}/hr/payroll/payslips`);
      setPayroll(updated);
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>Payroll Management</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>Full Staff & Contractors: monthly · Onsite/Labourers: weekly</div>
        </div>
        <div style={{ display:"flex", gap:12 }}>
          <button className="bg" onClick={()=>setShowAdd(true)}>+ Add Entry</button>
          <button className="bp" onClick={handleRunPayroll}>Run Payroll</button>
        </div>
      </div>

      {showAdd && (
        <Modal onClose={()=>setShowAdd(false)} title="Manual Payroll Entry">
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div><Lbl>Staff Member *</Lbl>
              <select className="inp" value={nf.uid} onChange={e=>setNf(x=>({...x,uid:e.target.value}))}>
                <option value="">— Select Staff —</option>
                {staff.map(u=><option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <div><Lbl>Gross Pay (₦) *</Lbl><input type="number" className="inp" value={nf.gross} onChange={e=>setNf(x=>({...x,gross:e.target.value}))}/></div>
              <div><Lbl>Deductions / Tax (₦)</Lbl><input type="number" className="inp" value={nf.tax} onChange={e=>setNf(x=>({...x,tax:e.target.value}))}/></div>
            </div>
            <div><Lbl>Description / Notes</Lbl><textarea className="inp" placeholder="Bonus, Contractor fee, Reimbursement..." value={nf.notes} onChange={e=>setNf(x=>({...x,notes:e.target.value}))}/></div>
            <button className="bp" onClick={addManual} style={{ padding:14 }}>Create Record</button>
          </div>
        </Modal>
      )}

      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading payroll records…</div>
      ) : payroll.length === 0 ? (
        <div className="gc" style={{ padding:48, textAlign:"center" }}>
          <div style={{ fontSize:32, marginBottom:12 }}>💳</div>
          <div className="ho" style={{ fontSize:16, marginBottom:8 }}>No Payroll Records Yet</div>
          <div style={{ fontSize:13, color:C.muted }}>Run payroll to generate payslips for your team.</div>
        </div>
      ) : (
        <div className="gc" style={{ overflow:"hidden" }}>
          <div style={{ padding:"14px 20px", borderBottom:`1px solid ${C.border}` }}>
            <div className="ho" style={{ fontSize:14 }}>Payroll Records</div>
          </div>
          <table className="ht">
            <thead><tr>{["Staff Member","Period","Gross Pay","Net Pay","Status",""].map(h=><th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {payroll.map(p => (
                <tr key={p.id}>
                  <td><div style={{ display:"flex", alignItems:"center", gap:10 }}><Av av={p.admins?.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={26}/><span style={{ fontWeight:800 }}>{p.admins?.full_name}</span></div></td>
                  <td style={{ color:C.sub }}>{p.period_start ? new Date(p.period_start).toLocaleDateString(undefined, {month:'long',year:'numeric'}) : "—"}</td>
                  <td style={{ fontWeight:700 }}>{fmt(p.gross_pay)}</td>
                  <td style={{ color:T.orange, fontWeight:800, fontSize:14 }}>{fmt(p.net_pay)}</td>
                  <td><span className={`tg ${p.status==="paid"?"tg2":"ty"}`}>{p.status}</span></td>
                  <td><button className="bg" style={{ fontSize:11, padding:"5px 12px" }}>Payslip</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── MODULE: STAFF DIRECTORY ─────────────────────────────────────────────────
function StaffDirectory() {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [tab, setTab] = useState("full");
  const [view, setView] = useState(null);
  const [dtTab, setDtTab] = useState("details");
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newStaff, setNewStaff] = useState({ full_name:"", email:"", role:"staff", primary_role:"staff", department:"", password:"" });
  const [saving, setSaving] = useState(false);

  const loadStaff = useCallback(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/staff`)
      .then(d => setStaff(d))
      .catch(e => console.error("Staff fetch error:", e))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadStaff(); }, [loadStaff]);

  const handleAddStaff = async () => {
    if (!newStaff.full_name || !newStaff.email || !newStaff.password) {
      alert("Full name, email, and password are required.");
      return;
    }
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/register`, {
        method: "POST",
        body: JSON.stringify(newStaff)
      });
      setShowAdd(false);
      setNewStaff({ full_name:"", email:"", role:"staff", primary_role:"staff", department:"", password:"" });
      loadStaff();
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const list = staff.filter(u => {
    const sType = u.staff_profiles?.[0]?.staff_type || "full";
    return sType === tab;
  });

  return (
    <div className="fade">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>Staff Directory</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>Full profiles — HR access only. Staff cannot see each other's records.</div>
        </div>
        <button className="bp" onClick={() => setShowAdd(true)}>+ Add Staff</button>
      </div>
      <Tabs items={[["full","Full Staff"],["contractor","Contractors"],["onsite","Onsite / Labourers"]]} active={tab} setActive={setTab}/>
      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading staff records…</div>
      ) : list.length === 0 ? (
        <div className="gc" style={{ padding:48, textAlign:"center", color:C.muted }}>No {tab} staff found. Click + Add Staff to create one.</div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:16, marginBottom:22 }}>
          {list.map(u => {
            const prof = u.staff_profiles?.[0] || {};
            const sc = u.performance?.score; 
            return (
              <div key={u.id} className="gc" style={{ padding:20, cursor:"pointer" }} onClick={()=>setView(u)}>
                <div style={{ display:"flex", gap:14, alignItems:"center", marginBottom:14 }}>
                  <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={44}/>
                  <div>
                    <div style={{ fontSize:14, fontWeight:800, color:C.text }}>{u.full_name}</div>
                    <div style={{ fontSize:12, color:C.sub }}>{prof.job_title || u.role}</div>
                    <div style={{ fontSize:11, color:T.orange, fontWeight:800, marginTop:2 }}>{u.department}</div>
                  </div>
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:12 }}>
                  {[["Role",u.role?.replace("_"," ")],["Type",prof.staff_type||"full"],["Email",u.email?.split("@")[0]+"…"],["Status",u.is_active?"Active":"Inactive"]].map(([l,v])=>(
                    <div key={l} style={{ background:`${T.orange}0D`, borderRadius:8, padding:"8px 10px" }}>
                      <div style={{ fontSize:10, color:C.muted, textTransform:"uppercase", letterSpacing:"1px", fontWeight:800 }}>{l}</div>
                      <div style={{ fontSize:12, color:T.orange, fontWeight:700, marginTop:2, textTransform:"capitalize" }}>{v}</div>
                    </div>
                  ))}
                </div>
                {sc != null ? (
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <span className={`tg ${sc>=80?"tg2":sc>=60?"to":"tr"}`}>{sc>=80?"Excellent":sc>=60?"Good":"Fair"}</span>
                    <span style={{ fontSize:20, fontWeight:800, color:sc>=80?"#4ADE80":T.orange }}>{sc}/100</span>
                  </div>
                ) : <span className="tg tm">No score yet</span>}
              </div>
            );
          })}
        </div>
      )}

      {/* ADD STAFF MODAL */}
      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} title="Add New Staff Member" width={580}>
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <div><Lbl>Full Name *</Lbl><input className="inp" placeholder="e.g. Adeola Balogun" value={newStaff.full_name} onChange={e=>setNewStaff(s=>({...s,full_name:e.target.value}))}/></div>
              <div><Lbl>Email Address *</Lbl><input className="inp" type="email" placeholder="adeola@eximps-cloves.com" value={newStaff.email} onChange={e=>setNewStaff(s=>({...s,email:e.target.value}))}/></div>
              <div><Lbl>Default Password *</Lbl><input className="inp" type="password" placeholder="Min 8 characters" value={newStaff.password} onChange={e=>setNewStaff(s=>({...s,password:e.target.value}))}/></div>
              <div><Lbl>Department</Lbl><input className="inp" placeholder="e.g. Sales & Acquisitions" value={newStaff.department} onChange={e=>setNewStaff(s=>({...s,department:e.target.value}))}/></div>
              <div><Lbl>System Role</Lbl>
                <select className="inp" value={newStaff.role} onChange={e=>setNewStaff(s=>({...s,role:e.target.value}))}>
                  <option value="staff">Staff</option>
                  <option value="sales_rep">Sales Rep</option>
                  <option value="admin">Admin</option>
                  <option value="lawyer">Lawyer</option>
                  <option value="line_manager">Line Manager</option>
                </select>
              </div>
              <div><Lbl>Primary Role</Lbl>
                <select className="inp" value={newStaff.primary_role} onChange={e=>setNewStaff(s=>({...s,primary_role:e.target.value}))}>
                  <option value="staff">Staff</option>
                  <option value="hr">HR</option>
                  <option value="sales">Sales</option>
                  <option value="finance">Finance</option>
                  <option value="legal">Legal</option>
                  <option value="operations">Operations</option>
                </select>
              </div>
            </div>
            <div style={{ padding:"10px 14px", background:`${T.orange}0D`, border:`1px solid ${T.orange}22`, borderRadius:10, fontSize:12, color:C.muted }}>
              The staff member will log in using the main platform login page at <b style={{color:T.orange}}>/login</b>. Their HR portal access is automatic.
            </div>
            <button className="bp" onClick={handleAddStaff} style={{ padding:12 }} disabled={saving}>
              {saving ? "Creating Account…" : "Create Staff Account"}
            </button>
          </div>
        </Modal>
      )}


      {view && (
        <Modal onClose={()=>setView(null)} title={view.full_name} width={640}>
          <div style={{ display:"flex", gap:16, alignItems:"center", marginBottom:22 }}>
            <Av av={view.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={58} gold/>
            <div style={{ flex:1 }}>
              <div style={{ fontSize:18, fontWeight:800, color:(dark?DARK:LIGHT).text }}>{view.staff_profiles?.[0]?.job_title || view.role}</div>
              <div style={{ fontSize:13, color:(dark?DARK:LIGHT).sub }}>{view.department}</div>
              <span className="tg to" style={{ marginTop:6, display:"inline-flex" }}>{view.staff_profiles?.[0]?.staff_type?.toUpperCase() || "FULL"}</span>
            </div>
          </div>
          
          <Tabs items={[["details","Personnel Identity"],["bank","Finances"],["docs","Documents"]]} active={dtTab} setActive={setDtTab}/>

          {dtTab === "details" && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:18 }} className="fade">
              <Field label="Full Name" value={view.full_name}/>
              <Field label="Email Address" value={view.email}/>
              <Field label="Phone" value={view.staff_profiles?.[0]?.phone_number}/>
              <Field label="Address" value={view.staff_profiles?.[0]?.address}/>
              <Field label="Gender" value={view.staff_profiles?.[0]?.gender}/>
              <Field label="DOB" value={view.staff_profiles?.[0]?.dob}/>
              <Field label="Nationality" value={view.staff_profiles?.[0]?.nationality}/>
              <Field label="Marital Status" value={view.staff_profiles?.[0]?.marital_status}/>
            </div>
          )}

          {dtTab === "bank" && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr", gap:10, marginBottom:18 }} className="fade">
              <Field label="Bank Name" value={view.staff_profiles?.[0]?.bank_name}/>
              <Field label="Account Number" value={view.staff_profiles?.[0]?.account_number}/>
              <Field label="Account Name" value={view.staff_profiles?.[0]?.account_name}/>
              <Field label="Monthly Base Salary" value={view.staff_profiles?.[0]?.base_salary ? `₦${Number(view.staff_profiles[0].base_salary).toLocaleString()}` : "Not Set"}/>
              <div style={{ padding:12, background:`${T.orange}0D`, border:`1px solid ${T.orange}22`, borderRadius:8, fontSize:12, color:(dark?DARK:LIGHT).muted }}>
                Payment info is only visible to HR and Finance teams.
              </div>
            </div>
          )}

          {dtTab === "docs" && (
            <div className="fade">
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:12 }}>
                <div className="ho" style={{ fontSize:13 }}>Staff Documents</div>
                <button className="bp" style={{ fontSize:11, padding:"4px 10px" }}>+ Upload</button>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {view.staff_documents?.length > 0 ? (
                  view.staff_documents.map((d,i) => (
                    <div key={i} style={{ display:"flex", justifyContent:"space-between", padding:"10px 14px", background:`${C.surface}`, border:`1px solid ${C.border}`, borderRadius:10 }}>
                      <div><div style={{ fontSize:13, fontWeight:700 }}>{d.title}</div><div style={{ fontSize:11, color:C.muted }}>{d.doc_type}</div></div>
                      <a href={d.file_url} target="_blank" className="bg" style={{ fontSize:11, textDecoration:"none" }}>View</a>
                    </div>
                  ))
                ) : <div style={{ fontSize:12, color:C.muted, textAlign:"center", padding:20 }}>No documents uploaded.</div>}
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: HR DASHBOARD ────────────────────────────────────────────────────
function HRDashboard() {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [data, setData] = useState({ staff:[], leaves:[], tasks:[], incidents:[] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API_BASE}/hr/staff`),
      apiFetch(`${API_BASE}/hr/presence/leaves`),
      apiFetch(`${API_BASE}/hr/tasks`),
      apiFetch(`${API_BASE}/hr/mismanagement`)
    ]).then(([s, l, t, i]) => {
      setData({ staff:s, leaves:l, tasks:t, incidents:i });
    }).finally(() => setLoading(false));
  }, []);

  const total = data.staff.length;
  const pendingLeaves = data.leaves.filter(l => l.status === "pending").length;
  const openTasks = data.tasks.filter(t => t.status !== "completed").length;
  const seriousFlags = data.incidents.filter(i => i.severity === "Critical" || i.severity === "Serious").length;

  return (
    <div className="fade">
      <div style={{ marginBottom:26 }}>
        <div className="ho" style={{ fontSize:26, marginBottom:4 }}>HR Overview</div>
        <div style={{ fontSize:13, color:C.sub }}>Live workforce intelligence — Eximp & Cloves Infrastructure Limited.</div>
      </div>
      {loading ? <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading workforce metrics…</div> : (
        <>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, marginBottom:22 }}>
            <StatCard label="Total Workforce" value={total} sub={`${total} Active Members`}/>
            <StatCard label="Pending Leaves" value={pendingLeaves} col={T.orange} sub="Awaiting approval"/>
            <StatCard label="Open Tasks" value={openTasks} col="#60A5FA" sub="Across all teams"/>
            <StatCard label="Critical Flags" value={seriousFlags} col="#F87171" sub="Urgent action needed"/>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1.3fr 1fr", gap:16, marginBottom:22 }}>
            <div className="gc" style={{ padding:22 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
                <div className="ho" style={{ fontSize:14 }}>Latest Active Staff</div>
                <span style={{ fontSize:11, color:C.muted }}>Recent Onboarding</span>
              </div>
              <table className="ht">
                <thead><tr>{["Staff","Department","Role"].map(h=><th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {data.staff.slice(0,6).map(u => (
                    <tr key={u.id}>
                      <td><div style={{ display:"flex", alignItems:"center", gap:10 }}><Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={24}/><span style={{ fontWeight:700 }}>{u.full_name}</span></div></td>
                      <td style={{ color:C.sub }}>{u.department}</td>
                      <td><span className="tg to" style={{ fontSize:9 }}>{u.role?.toUpperCase()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <div className="gc" style={{ padding:22 }}>
                <div className="ho" style={{ fontSize:14, marginBottom:16 }}>Administrative Alerts</div>
                {[
                  [`${pendingLeaves} Leave Requests Pending`, T.orange],
                  [`${seriousFlags} Serious Disciplinary Cases`, "#F87171"],
                  ["Payroll Processing Due", "#4ADE80"]
                ].map(([l,c],i)=>(
                  <div key={i} style={{ display:"flex", gap:12, alignItems:"center", marginBottom:12, padding:"12px 14px", background:`${c}0D`, border:`1px solid ${c}22`, borderRadius:10 }}>
                    <div style={{ width:8, height:8, borderRadius:"50%", background:c }}/>
                    <span style={{ fontSize:13, color:C.text }}>{l}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="gc" style={{ padding:22 }}>
            <div className="ho" style={{ fontSize:14, marginBottom:14 }}>Recent Open Tasks</div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
              {data.tasks.filter(t => t.status !== "completed").slice(0, 8).map(t => {
                const sc = sCol[t.status] || T.orange;
                const assignedTo = data.staff.find(u => u.id === t.staff_id);
                return (
                  <div key={t.id} style={{ padding:"12px 14px", background:`${T.orange}08`, border:`1px solid ${T.orange}22`, borderRadius:10 }}>
                    <div style={{ fontSize:13, fontWeight:700, color:C.text, marginBottom:6, lineHeight:1.3 }}>{t.title}</div>
                    <div style={{ fontSize:11, color:C.muted, marginBottom:8 }}>→ {assignedTo?.full_name?.split(" ").map(n=>n[0]).join("") || "?? "} · {new Date(t.due_date).toLocaleDateString()}</div>
                    <span className="tg" style={{ background:`${sc}22`, color:sc, border:`1px solid ${sc}33`, fontSize:10 }}>{t.status}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── MY PROFILE PAGE (shared component for any user) ─────────────────────────
function MyProfile({ user }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [prof, setProf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("details");

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/profile/${user.id}`)
      .then(d => setProf(d))
      .catch(e => console.error("Profile fetch error:", e))
      .finally(() => setLoading(false));
  }, [user.id]);

  if (loading) return <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading your profile…</div>;
  if (!prof)   return <div style={{ padding:40, textAlign:"center", color:"#F87171" }}>Could not load profile data.</div>;

  const p = prof.staff_profiles?.[0] || {};

  return (
    <div className="fade" style={{ maxWidth:720 }}>
      <div className="gc" style={{ padding:30, marginBottom:18 }}>
        <div style={{ display:"flex", gap:20, alignItems:"center", marginBottom:26 }}>
          <Av av={prof.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={70} gold/>
          <div>
            <div className="ho" style={{ fontSize:26 }}>{prof.full_name}</div>
            <div style={{ fontSize:14, color:C.sub }}>{p.job_title || prof.role}</div>
            <div style={{ fontSize:13, color:T.orange, fontWeight:800, marginTop:4 }}>{prof.department}</div>
          </div>
        </div>
        
        <Tabs items={[["details","Personnel Identity"],["bank","Finances"],["docs","My Documents"]]} active={tab} setActive={setTab}/>

        {tab === "details" && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }} className="fade">
            <Field label="Full Name" value={prof.full_name}/>
            <Field label="Email Address" value={prof.email}/>
            <Field label="Phone" value={p.phone_number}/>
            <Field label="Address" value={p.address}/>
            <Field label="Gender" value={p.gender}/>
            <Field label="DOB" value={p.dob}/>
            <Field label="Nationality" value={p.nationality}/>
            <Field label="Marital Status" value={p.marital_status}/>
          </div>
        )}

        {tab === "bank" && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr", gap:12 }} className="fade">
            <Field label="Bank Name" value={p.bank_name}/>
            <Field label="Account Number" value={p.account_number}/>
            <Field label="Account Name" value={p.account_name}/>
            <div style={{ padding:14, background:`${T.orange}0D`, border:`1px solid ${T.orange}22`, borderRadius:10, fontSize:13, color:C.sub, lineHeight:1.5 }}>
              <b>Note:</b> These details are used for payroll processing. If you need to update them, please contact the HR department with valid proof.
            </div>
          </div>
        )}

        {tab === "docs" && (
          <div className="fade">
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
              <div className="ho" style={{ fontSize:14 }}>My Uploaded Documents</div>
              <button className="bp" style={{ fontSize:12, padding:"6px 14px" }}>+ Upload Document</button>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              {prof.staff_documents?.length > 0 ? prof.staff_documents.map((d,i)=>(
                <div key={i} style={{ display:"flex", justifyContent:"space-between", padding:"12px 16px", background:C.surface, border:`1px solid ${C.border}`, borderRadius:12 }}>
                   <div><div style={{ fontSize:14, fontWeight:700 }}>{d.title}</div><div style={{ fontSize:12, color:C.muted }}>{d.doc_type} · Uploaded {new Date(d.created_at).toLocaleDateString()}</div></div>
                   <a href={d.file_url} target="_blank" className="bg" style={{ alignSelf:"center", textDecoration:"none" }}>View</a>
                </div>
              )) : <div style={{ padding:30, textAlign:"center", color:C.muted, border:`1px dashed ${C.border}`, borderRadius:12 }}>No documents found. Please upload your CV and ID.</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── MY PAYSLIP ───────────────────────────────────────────────────────────────
function MyPayslip({ user }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/payroll/payslips?staff_id=${user.id}`)
      .then(d => setPayslips(d))
      .finally(() => setLoading(false));
  }, [user.id]);

  if (loading) return <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading payslips…</div>;

  return (
    <div className="fade" style={{ maxWidth:800 }}>
      <div className="ho" style={{ fontSize:22, marginBottom:18 }}>My Payroll Records</div>
      <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
        {payslips.map(p=>(
          <div key={p.id} className="gc" style={{ padding:20, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <div>
              <div style={{ fontWeight:800, fontSize:15, color:C.text }}>{new Date(p.period_start).toLocaleDateString(undefined, {month:'long', year:'numeric'})}</div>
              <div style={{ fontSize:12, color:C.sub, marginTop:4 }}>Ref: PSL-{p.id} · Disbursed: {new Date(p.disbursement_date).toLocaleDateString()}</div>
            </div>
            <div style={{ textAlign:"right" }}>
              <div style={{ fontSize:18, fontWeight:800, color:T.orange }}>₦{p.net_pay.toLocaleString()}</div>
              <button className="bg" style={{ fontSize:11, marginTop:8 }}>Download PDF</button>
            </div>
          </div>
        ))}
        {payslips.length === 0 && <div style={{ textAlign:"center", padding:20, color:C.muted }}>No payroll records found.</div>}
      </div>
    </div>
  );
}

// ─── PORTAL WRAPPERS ──────────────────────────────────────────────────────────
function DrawerNav({ items, page, setPage, user, onLogout, roleLabel, onClose }) {
  const { dark, toggle } = useTheme(); const C = dark?DARK:LIGHT;
  const G = T.gold;
  return (
    <>
      <div className="hrm-overlay" id="hrmOverlay" onClick={onClose}/>
      <div className="hrm-drawer" id="hrmDrawer">
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:28 }}>
          <div>
            <div style={{ fontFamily:"'Playfair Display',serif", fontSize:18, color:G }}>HR Suite</div>
            <div style={{ fontSize:9, color:C.muted, letterSpacing:"2px", textTransform:"uppercase" }}>Navigation</div>
          </div>
          <button onClick={onClose} style={{ background:"none", border:"none", color:C.sub, fontSize:20, cursor:"pointer" }}>✕</button>
        </div>
        <div style={{ fontSize:9, color:C.muted, letterSpacing:"2px", marginBottom:6, fontWeight:700, textTransform:"uppercase" }}>{roleLabel}</div>
        <nav style={{ display:"flex", flexDirection:"column", gap:2, marginBottom:20 }}>
          {items.map(n => (
            <button key={n.id} className={`nb ${page===n.id?"on":""}`} onClick={()=>{ setPage(n.id); onClose(); }}>
              {IC[n.icon]}{n.label}
            </button>
          ))}
        </nav>
        <div style={{ borderTop:`1px solid ${C.border}`, paddingTop:16 }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
            <Av av={user.avatar} sz={32}/>
            <div>
              <div style={{ fontSize:13, fontWeight:700, color:C.text }}>{user.name}</div>
              <div style={{ fontSize:10, color:G }}>{(user.role||"").replace("_"," ").toUpperCase()}</div>
            </div>
            <button onClick={toggle} style={{ marginLeft:"auto", background:"none", border:"none", cursor:"pointer", color:C.muted }}>
              <div style={{ width:16, height:16 }}>{dark?IC.sun:IC.moon}</div>
            </button>
          </div>
          <button className="bg" onClick={onLogout} style={{ width:"100%", fontSize:12, padding:"7px 12px" }}>Sign Out</button>
        </div>
      </div>
    </>
  );
}

function Portal({ user, onLogout, navItems, roleLabel, renderPage }) {
  const [page, setPage] = useState(navItems[0].id);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;

  const openDrawer  = () => {
    document.getElementById("hrmDrawer")?.classList.add("open");
    document.getElementById("hrmOverlay")?.classList.add("open");
    setDrawerOpen(true);
  };
  const closeDrawer = () => {
    document.getElementById("hrmDrawer")?.classList.remove("open");
    document.getElementById("hrmOverlay")?.classList.remove("open");
    setDrawerOpen(false);
  };

  return (
    <div className="hrm">
      {/* Mobile top bar */}
      <div className="hrm-topbar-mobile">
        <div style={{ fontFamily:"'Playfair Display',serif", fontSize:17, color:T.gold }}>HR Suite</div>
        <button onClick={openDrawer} style={{ background:"none", border:`1px solid ${C.border}`, color:C.text, padding:"8px 10px", borderRadius:10, cursor:"pointer", display:"flex", alignItems:"center", gap:6, fontSize:13 }}>
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          Menu
        </button>
      </div>

      {/* Mobile slide-in drawer */}
      <DrawerNav items={navItems} page={page} setPage={setPage} user={user} onLogout={onLogout} roleLabel={roleLabel} onClose={closeDrawer}/>

      {/* Desktop sidebar */}
      <Sidebar page={page} setPage={setPage} user={user} onLogout={onLogout} items={navItems} roleLabel={roleLabel}/>

      {/* Main content */}
      <div className="hrm-main" style={{ flex:1, overflow:"auto", display:"flex", flexDirection:"column", minWidth:0 }}>
        <Topbar title={navItems.find(n=>n.id===page)?.label||""} user={user}/>
        <div className="hrm-content-padding" style={{ flex:1, padding:28, overflow:"auto" }}>
          {renderPage(page)}
        </div>
      </div>
    </div>
  );
}

function HRAdminPortal({ user, onLogout }) {
  const nav = [
    { id:"dashboard", icon:"dashboard", label:"HR Overview"        },
    { id:"staff",     icon:"staff",     label:"Staff Directory"  },
    { id:"presence",  icon:"presence",  label:"Presence"         },
    { id:"perf",      icon:"perf",      label:"Performance"      },
    { id:"goals",     icon:"goal",      label:"Goal Management"  },
    { id:"payroll",   icon:"payroll",   label:"Payroll"          },
    { id:"tasks",     icon:"tasks",     label:"Task Manager"     },
    { id:"mismanage", icon:"mis",       label:"Mismanagement"    },
  ];
  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="HR Administration" renderPage={p=>{
      if (p==="dashboard") return <HRDashboard/>;
      if (p==="staff")     return <StaffDirectory/>;
      if (p==="presence")  return <Presence/>;
      if (p==="perf")      return <Performance/>;
      if (p==="goals")     return <Goals/>;
      if (p==="payroll")   return <Payroll/>;
      if (p==="tasks")     return <Tasks currentUser={user}/>;
      if (p==="mismanage") return <Mismanagement/>;
    }}/>
  );
}

function ManagerPortal({ user, onLogout }) {
  const nav = [
    { id:"dashboard", icon:"dashboard", label:"Team Dashboard"  },
    { id:"team",      icon:"staff",     label:"My Team"         },
    { id:"presence",  icon:"presence",  label:"Presence"        },
    { id:"perf",      icon:"perf",      label:"Team Performance"},
    { id:"goals",     icon:"goal",      label:"Team Goals"      },
    { id:"tasks",     icon:"tasks",     label:"Task Manager"    },
    { id:"mismanage", icon:"mis",       label:"Incidents"       },
    { id:"myprofile", icon:"profile",   label:"My Profile"      },
    { id:"myperformance", icon:"perf",  label:"My Performance"  },
  ];
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/staff`) // In a real app we'd fetch only direct reports
      .then(d => setTeam(d.filter(u => u.line_manager_id === user.id || [3,4,5].includes(u.id)))) // Mocking report relationship for consistency
      .finally(() => setLoading(false));
  }, [user.id]);

  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="Management Hub" renderPage={p=>{
      if (p==="team")      return <StaffDirectory/>;
      if (p==="presence")  return <Presence/>;
      if (p==="perf")      return <Performance/>;
      if (p==="goals")     return <Goals/>;
      if (p==="tasks")     return <Tasks currentUser={user}/>;
      if (p==="mismanage") return <Mismanagement isManager userId={user.id}/>;
      if (p==="myprofile") return <MyProfile user={user}/>;
      if (p==="myperformance") return <Performance viewOnly userId={user.id}/>;

      return (
        <div className="fade">
          <div className="ho" style={{ fontSize:24, marginBottom:6 }}>Team Overview</div>
          <div style={{ fontSize:13, color:C.sub, marginBottom:22 }}>Performance and activity tracking for your direct reports.</div>
          
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14, marginBottom:22 }}>
            <StatCard label="Direct Reports" value={team.length}/>
            <StatCard label="Active Tasks" value="8" col="#60A5FA"/>
            <StatCard label="Avg Team Score" value="82/100" col="#4ADE80"/>
          </div>

          {loading ? <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading team data…</div> : (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:16 }}>
              {team.map(u => (
                <div key={u.id} className="gc" style={{ padding:22 }}>
                  <div style={{ display:"flex", gap:14, alignItems:"center", marginBottom:14 }}>
                    <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={42}/>
                    <div><div style={{ fontSize:14, fontWeight:800, color:C.text }}>{u.full_name}</div><div style={{ fontSize:12, color:C.sub }}>{u.staff_profiles?.[0]?.job_title}</div></div>
                  </div>
                  <div style={{ fontSize:12, color:C.muted, marginTop:8 }}>Click 'My Team' for full details.</div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }}/>
  );
}

function StaffPortal({ user, onLogout }) {
  const nav = [
    { id:"dashboard",  icon:"dashboard", label:"My Dashboard"   },
    { id:"profile",    icon:"profile",   label:"My Profile"     },
    { id:"perf",       icon:"perf",      label:"My Performance" },
    { id:"goals",      icon:"goal",      label:"My Goals"       },
    { id:"tasks",      icon:"tasks",     label:"My Tasks"       },
    { id:"presence",   icon:"presence",  label:"My Presence"    },
    { id:"payslip",    icon:"payslip",   label:"My Payslip"     },
    { id:"mismanage",  icon:"mis",       label:"My Flags"       },
  ];
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [tasks, setTasks] = useState([]);
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
     setLoading(true);
     Promise.all([
       apiFetch(`${API_BASE}/hr/tasks?staff_id=${user.id}`),
       apiFetch(`${API_BASE}/hr/performance/${user.id}`)
     ]).then(([t, p]) => {
       setTasks(t);
       setPerf(p);
     }).finally(() => setLoading(false));
  }, [user.id]);

  const sc = perf?.score;
  const col = sc != null ? (sc >= 80 ? "#4ADE80" : sc >= 60 ? T.orange : "#F87171") : T.orange;
  const pendingTasks = tasks.filter(t => t.status !== "completed");

  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="Team Member Portal" renderPage={pg=>{
      if (pg==="profile")   return <MyProfile user={user}/>;
      if (pg==="perf")      return <Performance viewOnly userId={user.id}/>;
      if (pg==="goals")     return <Goals viewOnly userId={user.id}/>;
      if (pg==="tasks")     return <Tasks currentUser={user}/>;
      if (pg==="presence")  return <Presence currentUserId={user.id}/>;
      if (pg==="payslip")   return <MyPayslip user={user}/>;
      if (pg==="mismanage") return <Mismanagement viewOnly userId={user.id}/>;
      
      return (
        <div className="fade">
          <div className="ho" style={{ fontSize:24, marginBottom:4 }}>Welcome, {user.full_name?.split(" ")[0]} 👋</div>
          <div style={{ fontSize:13, color:C.sub, marginBottom:22 }}>{user.staff_profiles?.[0]?.job_title || user.role} · {user.department}</div>
          
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, marginBottom:22 }}>
            <StatCard label="My Score" value={sc != null ? `${sc}/100` : "—"} col={col}/>
            <StatCard label="My Tasks" value={tasks.length} col="#60A5FA"/>
            <StatCard label="Pending" value={pendingTasks.length} col={T.orange}/>
            <StatCard label="Leave Left" value="11d"/>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:18 }}>
            <div className="gc" style={{ padding:22 }}>
              <div className="ho" style={{ fontSize:14, marginBottom:14 }}>My Active Tasks</div>
              {loading ? <div style={{ fontSize:13, color:C.muted }}>Loading...</div> : (
                <>
                  {pendingTasks.slice(0,4).map(t => {
                    const sc2 = sCol[t.status] || T.orange;
                    return (
                      <div key={t.id} style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", padding:"10px 0", borderBottom:`1px solid ${C.border}22` }}>
                        <div>
                          <div style={{ fontSize:13, color:C.text, fontWeight:700 }}>{t.title}</div>
                          <div style={{ fontSize:11, color:C.muted, marginTop:2 }}>Due {new Date(t.due_date).toLocaleDateString()}</div>
                        </div>
                        <span className="tg" style={{ background:`${sc2}22`, color:sc2, border:`1px solid ${sc2}33`, flexShrink:0, textTransform:"capitalize" }}>{t.status.replace("_"," ")}</span>
                      </div>
                    );
                  })}
                  {pendingTasks.length === 0 && <div style={{ fontSize:13, color:C.muted }}>No pending tasks! 🎉</div>}
                </>
              )}
            </div>

            <div className="gc" style={{ padding:22 }}>
              <div className="ho" style={{ fontSize:14, marginBottom:14 }}>My Performance</div>
              {perf ? (
                <>
                  <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:18 }}>
                    <ScoreRing sc={sc} sz={70}/>
                    <div>
                      <div style={{ fontSize:26, fontWeight:800, color:C.text }}>{sc}<span style={{ fontSize:13, color:C.muted }}>/100</span></div>
                      <span className={`tg ${sc>=80?"tg2":sc>=60?"to":"tr"}`}>Rank: {sc>=80?"Elite":sc>=60?"Stable":"Needs PIP"}</span>
                    </div>
                  </div>
                  {[["KPI Goals", (perf.breakdown?.goals_40_pct||0)*2.5], ["Work Quality", (perf.breakdown?.quality_20_pct||0)*5]].map(([l,v])=>(
                    <div key={l} style={{ marginBottom:10 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:C.muted, marginBottom:4 }}><span>{l}</span><span style={{ color:T.orange, fontWeight:800 }}>{Math.round(v)}%</span></div>
                      <Bar pct={v}/>
                    </div>
                  ))}
                </>
              ) : <div style={{ fontSize:13, color:C.muted }}>No performance data available yet.</div>}
            </div>
          </div>
        </div>
      );
    }}/>
  );
}

// ─── ROOT ────────────────────────────────────────────────────────────────────
export default function App() {
  const [dark, setDark] = useState(true);
  const [user, setUser] = useState(null);
  const toggle = useCallback(()=>setDark(d=>!d),[]);

  useEffect(() => {
    const savedToken = localStorage.getItem("ec_token");
    const savedUser = localStorage.getItem("admin"); // Main system stores user info in 'admin' key
    
    if (savedToken && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem("ec_token");
        localStorage.removeItem("admin");
        window.location.href = "/login";
      }
    } else {
      // Redirect to main login page if not authenticated
      window.location.href = "/login";
    }
  }, []);

  const logout = () => {
    localStorage.removeItem("ec_token");
    localStorage.removeItem("admin");
    window.location.href = "/login";
  };

  if (!user) return <div style={{ padding:40, textAlign:"center", color:T.orange }}>Redirecting to login...</div>;

  return (
    <ThemeCtx.Provider value={{ dark, toggle }}>
      <style>{GS(dark)}</style>
      <div className="fade">
        {(user.role === "admin" || user.primary_role === "hr" || user.role?.includes("hr_admin")) && (
          <HRAdminPortal user={user} onLogout={logout} />
        )}
        {user.role?.includes("line_manager") && (
          <ManagerPortal user={user} onLogout={logout} />
        )}
        {!(user.role === "admin" || user.primary_role === "hr" || user.role?.includes("hr_admin") || user.role?.includes("line_manager")) && (
          <StaffPortal user={user} onLogout={logout} />
        )}
      </div>
    </ThemeCtx.Provider>
  );
}
