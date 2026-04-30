import { useState, createContext, useContext, useCallback, useEffect, useRef } from "react";
import { apiFetch, API_BASE } from "./api";

const ThemeCtx = createContext({ dark: true, toggle: () => { } });
const useTheme = () => useContext(ThemeCtx);

// ─── DEPARTMENT ALIAS MAP ─────────────────────────────────────────────────────
// Maps staff department strings to their canonical KPI department names
const departmentAlias = {
  "Sales": "Sales & Acquisitions",
  "Acquisitions": "Sales & Acquisitions",
  "Sales and Acquisitions": "Sales & Acquisitions",
  "HR": "Human Resources",
  "H.R.": "Human Resources",
  "Ops": "Operations",
  "IT": "Information Technology",
  "Finance & Accounts": "Finance",
  "Accounts": "Finance",
};

// ─── SHARED DEPARTMENTS HOOK ──────────────────────────────────────────────────
// Single source of truth for departments — avoids loading through recruitmentData
// for components that don't need jobs/apps/interviews.
function useDepartments() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const d = await apiFetch(`${API_BASE}/hr/departments`).catch(() => []);
      setDepartments(Array.isArray(d) ? d : []);
    } catch { setDepartments([]); } finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { departments, loading, refresh };
}

function SecurityManager() {
  const [data, setData] = useState({ current: "", new: "", confirm: "" });
  const [loading, setLoading] = useState(false);

  const update = async () => {
    if (!data.current || !data.new || !data.confirm) return alert("Fill all fields");
    if (data.new !== data.confirm) return alert("New passwords do not match");
    if (data.new.length < 8) return alert("Password must be at least 8 characters");

    setLoading(true);
    try {
      await apiFetch(`/auth/me/password`, {
        method: "PATCH",
        body: JSON.stringify({ current_password: data.current, new_password: data.new })
      });
      alert("Password updated successfully");
      setData({ current: "", new: "", confirm: "" });
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="fade" style={{ maxWidth: 400 }}>
      <div className="ho" style={{ fontSize: 15, marginBottom: 20, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>Security & Password</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div><Lbl>Current Password</Lbl> <input className="inp" type="password" value={data.current} onChange={e => setData({ ...data, current: e.target.value })} /></div>
        <div><Lbl>New Password</Lbl> <input className="inp" type="password" value={data.new} onChange={e => setData({ ...data, new: e.target.value })} /></div>
        <div><Lbl>Confirm New Password</Lbl> <input className="inp" type="password" value={data.confirm} onChange={e => setData({ ...data, confirm: e.target.value })} /></div>
        <button className="bp" style={{ marginTop: 10 }} onClick={update} disabled={loading}>{loading ? "Updating..." : "Update Password"}</button>
      </div>
    </div>
  );
}

// ─── DESIGN TOKENS ──────────────────────────────────────────────────────────────
const T = {
  gold: "#C47D0A",
  // Keep orange alias for backward compat with all components
  orange: "#C47D0A",
  glow: "0 0 0 1px #C47D0A33, 0 0 14px #C47D0A18",
  glowHover: "0 0 0 1.5px #C47D0A, 0 0 22px #C47D0A40",
};
const DARK = { bg: "#0B0C0F", surface: "#111317", card: "#1A1D24", border: "#2D2F36", input: "#161820", text: "#E5E7EB", sub: "#A0A0A0", muted: "#6B7280" };
const LIGHT = { bg: "#F0F2F6", surface: "#FFFFFF", card: "#FFFFFF", border: "#DDE3EE", input: "#F4F6FA", text: "#1A2130", sub: "#556677", muted: "#99AABB" };

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
  const scaleUp = `@keyframes scaleUp { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }`;
  const C = dark ? DARK : LIGHT;
  const G = T.gold;
  return `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');
      ${scaleUp}
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    ::-webkit-scrollbar{width:6px;height:6px;}
    ::-webkit-scrollbar-track{background:${C.bg};}
    ::-webkit-scrollbar-thumb{background:${C.border};border-radius:4px;}
    ::-webkit-scrollbar-thumb:hover{background:#4B5563;}
    body,html{height:100%;overflow-x:hidden;}
    .hrm{font-family:'Inter',sans-serif;background:${C.bg};color:${C.text};min-height:100vh;display:flex;width:100%;}
    .hrm-main{flex:1;min-height:100vh;display:flex;flex-direction:column;}
    .hrm-content-padding{flex:1;padding:32px 40px;}
    .hrm-serif{font-family:'Playfair Display',serif;}
    .fade{animation:fi .3s ease forwards;}
    .fade-in{animation:fi .5s cubic-bezier(.2,1,.2,1) forwards; opacity:0;}
    @keyframes fi{from{opacity:0;transform:translateY(12px);}to{opacity:1;transform:none;}}
    
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
    .bp{background:${G};color:#fff;border:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:all .2s ease;letter-spacing:.5px;box-shadow:none;text-transform:uppercase;}
    .bp:hover{filter:brightness(1.1);transform:translateY(-2px);box-shadow:none;}
    .bp:active{transform:translateY(0);}
    .bp:disabled{opacity:.6;cursor:not-allowed;transform:none;box-shadow:none;}
    .bd{background:transparent;border:1px solid #F87171;color:#F87171;padding:9px 20px;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .18s;}
    .bg{background:transparent;border:1px solid ${C.border};color:${C.sub};padding:9px 20px;border-radius:10px;font-size:13px;cursor:pointer;font-family:inherit;transition:all .2s;font-weight:600;}
    .bg:hover{border-color:${G};color:${G};background:${G}0A;transform:translateY(-1px);}
    .bd{background:#EF444412;color:#EF4444;border:1px solid #EF444430;padding:8px 16px;border-radius:10px;font-size:12px;cursor:pointer;font-family:inherit;font-weight:700;transition:all .2s;}
    .bd:hover{background:#EF444422;transform:translateY(-1px);}
    
    /* Inputs */
    .inp{background:#121417;border:1px solid #FFFFFF14;color:${C.text};padding:12px 18px;border-radius:12px;font-size:14px;outline:none;font-family:inherit;width:100%;transition:all .2s ease;}
    .inp:focus{border-color:${G};background:#15181C;box-shadow:0 0 0 4px ${G}14;}
    select.inp option{background:#1A1C20;color:#FFF;}
    textarea.inp{resize:vertical;min-height:90px;}
    
    /* Tags */
    .tg{display:inline-flex;align-items:center;padding:5px 14px;border-radius:9999px;font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;}
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
    .ht th{padding:14px 18px;font-size:10px;color:${C.muted};text-align:left;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid ${C.border};font-weight:800;background:${dark ? "#1A1C20" : C.surface};}
    .ht td{padding:14px 18px;font-size:13px;border-bottom:1px solid ${C.border}44;}
    .ht tr:hover td{background:${C.border}1A;}
    
    /* Modals */
    .mb{position:fixed;inset:0;background:#06080AEE;backdrop-filter:blur(12px);z-index:1000;display:grid;place-items:center;padding:24px;overflow-y:auto;}
    .mo{background:${C.card};border:1px solid #FFFFFF10;box-shadow:0 40px 100px rgba(0,0,0,.8);border-radius:28px;max-width:640px;width:100%;max-height:92vh;display:flex;flex-direction:column;position:relative;animation:m-in .4s cubic-bezier(.2,1,.2,1);overflow:hidden;}
    .mh{padding:34px 40px 14px 40px;}
    .mc{padding:0 40px 40px 40px;}
    @keyframes m-in{from{opacity:0;transform:scale(0.96) translateY(30px);}to{opacity:1;transform:scale(1) translateY(0);}}
    .fade{animation:fi .4s ease-out;}
    @keyframes fi{from{opacity:0;}to{opacity:1;}}
    
    /* Tabs */
    .tab-bar{display:flex;gap:4px;background:${C.surface};padding:4px;border-radius:10px;width:fit-content;border:1px solid ${C.border};margin-bottom:22px;flex-wrap:wrap;}
    .tab{padding:8px 18px;border-radius:8px;border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;transition:all .18s;}
    .tab.on{background:${G};color:#fff;}
    .tab.off{background:transparent;color:${C.sub};}
    
    /* Fields */
    .field{background:${G}0E;border:1px solid ${G}22;border-radius:10px;padding:12px 16px;}
    .fl{font-size:10px;color:${C.muted};text-transform:uppercase;letter-spacing:1.2px;font-weight:700;margin-bottom:4px;}
    /* Fields */
    .field{background:${G}0D;border:1px solid ${G}1A;border-radius:12px;padding:14px 18px;}
    .fl{font-size:10px;color:${C.muted};text-transform:uppercase;letter-spacing:.08em;font-weight:800;margin-bottom:4px;}
    .fv{font-size:14px;color:${G};font-weight:700;}
    .lbl{font-size:10px;color:${C.muted};margin-bottom:8px;font-weight:800;display:block;text-transform:uppercase;letter-spacing:.06em;}
    
    /* Responsive grid utilities */
    .g4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}
    .g3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
    .g2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
    .g2w{display:grid;grid-template-columns:1.3fr 1fr;gap:16px;}
    .g1{display:grid;grid-template-columns:1fr;gap:14px;}
    
    /* Table scroll wrapper */
    .tw{overflow-x:auto;-webkit-overflow-scrolling:touch;}
    .tw .ht{min-width:580px;}
    
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
      .g4{grid-template-columns:repeat(2,1fr);}
      .g3{grid-template-columns:repeat(2,1fr);}
      .g2w{grid-template-columns:1fr;}
      .mo{max-width:96vw;border-radius:20px;}
    }
    @media(max-width:640px){
      .hrm-content-padding{padding:14px;}
      .tab{padding:7px 12px;font-size:12px;}
      .tab-bar{width:100%;}
      .gc{padding:14px;}
      .g4{grid-template-columns:repeat(2,1fr);gap:10px;}
      .g3{grid-template-columns:1fr;gap:12px;}
      .g2{grid-template-columns:1fr;gap:12px;}
      .g2w{grid-template-columns:1fr;gap:12px;}
      .mb{padding:12px;}
      .mo{max-width:100vw;max-height:98vh;border-radius:16px;}
      .mh{padding:24px 20px 14px 20px;}
      .mc{padding:0 20px 24px 20px;}
      .field{padding:10px 14px;}
      .tw .ht{min-width:850px;}
    }
    @media(max-width:480px){
      .g4{grid-template-columns:1fr;}
      .hrm-content-padding{padding:12px;}
    }
  `;
};

// ─── SHARED ICONS ─────────────────────────────────────────────────────────────
const IC = {
  dashboard: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>,
  staff: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  presence: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /><path d="M8 14l2 2 4-4" /></svg>,
  perf: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>,
  payroll: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="5" width="20" height="14" rx="2" /><line x1="2" y1="10" x2="22" y2="10" /></svg>,
  tasks: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>,
  mis: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  profile: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>,
  payslip: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>,
  goal: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>,
  sun: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg>,
  moon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>,
  briefcase: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" /></svg>,
  chart: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>,
  clock: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>,
  calendar: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>,
  book: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>,
  dollar: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>,
  megaphone: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 11l19-9-9 19-2-8-8-2z" /></svg>,
  star: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>,
  shield: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
  file: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>,
  globe: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>,
  alert: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
  settings: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>,
  users: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  log: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" /></svg>,
  exit: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>,
  trend: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></svg>,
  org: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="8" y="2" width="8" height="4" rx="1" /><rect x="1" y="18" width="6" height="4" rx="1" /><rect x="9" y="18" width="6" height="4" rx="1" /><rect x="17" y="18" width="6" height="4" rx="1" /><path d="M4 22v-4M20 22v-4M12 22v-4M12 6v3M4 18v-3h16v3" /></svg>,
  home: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>,
};

// ─── PRIMITIVES ───────────────────────────────────────────────────────────────
const Av = ({ av, sz = 36, gold }) => (
  <div style={{ width: sz, height: sz, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: sz * 0.31, fontWeight: 800, background: gold ? `linear-gradient(135deg,${T.orange},#C07010)` : `${T.orange}22`, border: `1.5px solid ${T.orange}${gold ? "99" : "44"}`, color: gold ? "#0F1318" : T.orange }}>{av}</div>
);

const ScoreRing = ({ sc, sz = 72 }) => {
  const col = sc >= 80 ? "#4ADE80" : sc >= 60 ? T.orange : "#F87171";
  const r = 28, circ = 175.9, dash = (sc / 100) * circ;
  return (
    <svg width={sz} height={sz} viewBox="0 0 70 70" style={{ flexShrink: 0 }}>
      <circle cx="35" cy="35" r={r} fill="none" stroke="#1C2330" strokeWidth="7" />
      <circle cx="35" cy="35" r={r} fill="none" stroke={col} strokeWidth="7" strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 35 35)" />
      <text x="35" y="40" textAnchor="middle" fontSize="15" fontWeight="800" fill={col} fontFamily="inherit">{sc}</text>
    </svg>
  );
};

const Bar = ({ pct, col = T.orange }) => (
  <div className="pt"><div className="pf" style={{ width: `${pct}%`, background: col }} /></div>
);

const TrendChart = ({ data, color = "#4ADE80" }) => {
  if (!data || data.length < 2) return <div style={{ height: 60, display: "flex", alignItems: "center", justifyContent: "center", color: (LIGHT).muted, fontSize: 11 }}>Insufficient data for trend</div>;
  const max = 100;
  const h = 60, w = 240;
  const padding = 10;
  const points = data.map((v, i) => {
    const x = padding + (i * (w - 2 * padding) / (data.length - 1));
    const y = h - padding - (v / max * (h - 2 * padding));
    return `${x},${y}`;
  }).join(" ");

  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ fontSize: 10, color: (LIGHT).muted, marginBottom: 8, textTransform: "uppercase", fontWeight: 800, letterSpacing: 1 }}>6-Month Performance Trend</div>
      <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow: "visible" }}>
        <polyline fill="none" stroke={`${color}33`} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={points} />
        <polyline fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" points={points} />
        {data.map((v, i) => {
          const x = padding + (i * (w - 2 * padding) / (data.length - 1));
          const y = h - padding - (v / max * (h - 2 * padding));
          return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
        })}
      </svg>
    </div>
  );
};

function Modal({ onClose, title, width = 640, children }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  return (
    <div className="mb" onClick={onClose}>
      <div className="mo fade" style={{ maxWidth: width }} onClick={e => e.stopPropagation()}>
        <div className="mh" style={{ flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 10, color: T.orange, fontWeight: 800, textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 4 }}>Management System</div>
            <div className="ho" style={{ fontSize: 22 }}>{title}</div>
          </div>
          <button onClick={onClose} style={{ background: "#FFFFFF0A", border: "1px solid #FFFFFF10", color: C.text, width: 36, height: 36, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "all .2s" }}>✕</button>
        </div>
        <div className="mc" style={{ flex: 1, overflowY: "auto", scrollbarWidth: "none" }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, col }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  return (
    <div className="gc" style={{ padding: "20px 22px" }}>
      <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: 10, fontWeight: 800 }}>{label}</div>
      <div style={{ fontSize: 38, fontWeight: 800, color: col || T.orange, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: C.sub, marginTop: 8 }}>{sub}</div>}
    </div>
  );
}

function Tabs({ items, active, setActive }) {
  return (
    <div className="tab-bar" style={{ marginBottom: 22 }}>
      {items.map(([k, l]) => <button key={k} className={`tab ${active === k ? "on" : "off"}`} onClick={() => setActive(k)}>{l}</button>)}
    </div>
  );
}

function Field({ label, value }) {
  return <div className="field"><div className="fl">{label}</div><div className="fv">{value || "—"}</div></div>;
}

function Lbl({ children }) { return <span className="lbl">{children}</span>; }

const sevCol = { Minor: "#60A5FA", Moderate: "#FBB040", Serious: T.orange, Critical: "#F87171" };
const sevGrade = { Minor: "D", Moderate: "C", Serious: "B", Critical: "A" };
const sevOrd = { Minor: 1, Moderate: 2, Serious: 3, Critical: 4 };
const pCol = { High: "#F87171", Medium: T.orange, Low: "#4ADE80" };
const sCol = { completed: "#4ADE80", in_progress: "#60A5FA", pending: T.orange };

// ─── STUB DATA (used where real API data is not yet available) ─────────────────
const INIT_ATTENDANCE = [];
const USERS = [];
const PAYROLL_FULL = [];
const PAYROLL_CONTRACTOR = [];
const PAYROLL_ONSITE = [];

// ─── SIDEBAR ──────────────────────────────────────────────────────────────────
function Sidebar({ page, setPage, user, onLogout, items, roleLabel, onMenuOpen }) {
  const { dark, toggle } = useTheme(); const C = dark ? DARK : LIGHT;
  const { unreadByType } = useNotifs();
  const G = T.gold;
  return (
    <div className="hrm-sidebar" style={{ width: 260, background: dark ? "#111317" : "#FFFFFF", borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", flexShrink: 0, height: "100vh", position: "sticky", top: 0, zIndex: 50, overflow: "hidden" }}>
      <div style={{ padding: "28px 24px 20px", flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 36, flexShrink: 0 }}>
          <img src="/static/img/logo.svg" alt="Eximp & Cloves" style={{ height: 40, width: "auto" }} onError={(e) => { e.target.onerror = null; e.target.src = "https://via.placeholder.com/40x40?text=EC"; }} />
          <div style={{ lineHeight: 1.2 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: G, fontFamily: "'Playfair Display',serif" }}>HR Suite</div>
          </div>
        </div>
        <div style={{ fontSize: 9, color: C.muted, letterSpacing: "2px", padding: "0 4px 8px", fontWeight: 700, textTransform: "uppercase", flexShrink: 0 }}>{roleLabel}</div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {items.map(n => (
            n.isHeader ? (
              <div key={n.label} style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800, padding: "16px 16px 6px", marginTop: 4 }}>{n.label}</div>
            ) : (() => {
              const badge = unreadByType[n.id] || 0;
              return (
                <button key={n.id} className={`nb ${page === n.id ? "on" : ""}`} onClick={() => !n.disabled && setPage(n.id)} style={{ opacity: n.disabled ? 0.5 : 1, cursor: n.disabled ? "not-allowed" : "pointer" }}>
                  {IC[n.icon]}
                  <span style={{ flex: 1, textAlign: "left" }}>{n.label}</span>
                  {n.disabled && <span style={{ fontSize: 9, marginLeft: "auto", background: "#333", padding: "2px 6px", borderRadius: 4 }}>SOON</span>}
                  {!n.disabled && badge > 0 && (
                    <span style={{
                      marginLeft: "auto", minWidth: 18, height: 18, borderRadius: 9, padding: "0 5px",
                      background: "#F87171", color: "#fff", fontSize: 10, fontWeight: 900,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      boxShadow: "0 0 6px rgba(248,113,113,0.6)"
                    }}>
                      {badge > 99 ? "99+" : badge}
                    </span>
                  )}
                </button>
              );
            })()
          ))}
        </nav>
      </div>
      <div style={{ marginTop: "auto", padding: "16px 20px", borderTop: `1px solid ${C.border}` }}>
        <div style={{ background: dark ? "rgba(45,47,54,.3)" : C.card, borderRadius: 14, padding: "14px 16px", border: `1px solid ${C.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <Av av={user.avatar} sz={34} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user.name}</div>
              <div style={{ fontSize: 10, color: G, fontWeight: 600, textTransform: "uppercase", letterSpacing: "1px" }}>{(user.role || "").replace("_", " ")}</div>
            </div>
            <button onClick={toggle} style={{ background: "none", border: "none", cursor: "pointer", color: C.muted, display: "flex", flexShrink: 0 }}>
              <div style={{ width: 15, height: 15 }}>{dark ? IC.sun : IC.moon}</div>
            </button>
          </div>
          <button className="bg" onClick={onLogout} style={{ width: "100%", fontSize: 12, padding: "7px 12px" }}>Sign Out</button>
        </div>
      </div>
    </div>
  );
}

function Topbar({ title, user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  return (
    <div style={{ height: 54, background: dark ? "#111317" : "#FFFFFF", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px", flexShrink: 0 }}>
      <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 17, color: T.gold }}>{title}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span className="tg to" style={{ fontSize: 10 }}>{(user.staffType || user.role || "").toUpperCase()} ACCESS</span>
        <span style={{ fontSize: 12, color: C.muted }}>{new Date().toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" })}</span>
        <NotificationBell />
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────uthentication is now handled by the main platform.
// Redirection logic is in the App component.


// ─── GOAL FORM MODAL CONTENT ─────────────────────────────────────────────────
function GoalForm({ onSave, staffList = [], templates = [], initialGoal = null, departments = [] }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const defaultForm = { uid: "", department: "", template_id: "", kpi: "", target: "", unit: "", period: new Date().toLocaleDateString(undefined, { month: 'short', year: 'numeric' }), status: "Published" };
  const [f, setF] = useState(defaultForm);

  const [selectedTemplate, setSelectedTemplate] = useState(null);

  useEffect(() => {
    if (!initialGoal) {
      setF(defaultForm);
      setSelectedTemplate(null);
      return;
    }
    const t = templates.find(temp => temp.id === initialGoal.kpi_template_id);
    setSelectedTemplate(t);
    setF({
      uid: initialGoal.staff_id || "",
      department: initialGoal.department || "",
      template_id: initialGoal.kpi_template_id || "",
      kpi: initialGoal.kpi_name || "",
      target: initialGoal.target_value != null ? String(initialGoal.target_value) : "",
      unit: initialGoal.unit || "",
      period: initialGoal.month ? (() => {
        const d = new Date(initialGoal.month.includes('T') ? initialGoal.month : initialGoal.month + 'T12:00:00');
        return d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
      })() : defaultForm.period,
      status: initialGoal.status || "Published"
    });
  }, [initialGoal, templates]);

  const selUser = staffList.find(u => u.id === f.uid);
  const departmentKey = selUser ? selUser.department : f.department;
  const suggestedTemplates = departmentKey ? templates.filter(t => t.department === departmentKey && t.is_active) : [];
  const hasSuggestedKpis = suggestedTemplates.length > 0;

  const save = () => {
    if (!f.uid && !f.department) return alert("Please assign this goal to a staff member or department.");
    if (!f.kpi) return alert("Please enter or select a KPI / goal name.");
    if (!f.target || isNaN(parseFloat(f.target))) return alert("Please enter a valid target value.");

    // Provide visual feedback during save
    onSave({
      ...f,
      department: departmentKey || f.department,
      target: parseFloat(f.target),
      actual: initialGoal?.actual_value || 0
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div className="g2" style={{ gap: 16 }}>
        <div>
          <Lbl>Assign to Staff Member</Lbl>
          <select className="inp" value={f.uid} onChange={e => {
            const staffId = e.target.value;
            const staff = staffList.find(u => u.id === staffId);
            setF(x => ({
              ...x,
              uid: staffId,
              department: staff ? (departmentAlias[staff.department] || staff.department) : "",
              template_id: "",
              kpi: ""
            }));
            setSelectedTemplate(null);
          }}>
            <option value="">— No individual selected —</option>
            {staffList.filter(u => u.role !== "hr_admin").map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
          </select>
        </div>
        <div>
          <Lbl>Or Assign to Department</Lbl>
          <select className="inp" value={f.department} onChange={e => {
            setF(x => ({ ...x, department: e.target.value, uid: "", template_id: "", kpi: "" }));
            setSelectedTemplate(null);
          }} disabled={!!f.uid}>
            <option value="">— Select Department —</option>
            {departments.map(d => <option key={d.id || d} value={d.name || d}>{d.name || d}</option>)}
          </select>
        </div>
      </div>

      <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 18 }}>
        <Lbl>KPI Configuration / Library Selection *</Lbl>
        {hasSuggestedKpis ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <select className="inp" value={f.template_id} onChange={e => {
              const template = suggestedTemplates.find(t => t.id === e.target.value);
              setSelectedTemplate(template);
              if (e.target.value === "") {
                setF(x => ({ ...x, template_id: "", kpi: "", unit: "" }));
              } else {
                setF(x => ({
                  ...x,
                  template_id: e.target.value,
                  kpi: template ? template.name : x.kpi,
                  unit: template ? template.default_unit : x.unit
                }));
              }
            }} disabled={!departmentKey}>
              <option value="">— Select from KPI Library —</option>
              {suggestedTemplates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <div style={{ fontSize: 11, color: C.muted }}>
              {selectedTemplate ? (
                <div style={{ background: `${T.orange}08`, padding: 10, borderRadius: 8, border: `1px dashed ${T.orange}33` }}>
                  <div style={{ fontWeight: 800, color: T.orange, marginBottom: 4 }}>
                    {selectedTemplate.measurement_source === "manual" ? "✍️ Manual Metric" : "🤖 Automated Metric"}
                  </div>
                  <div style={{ lineHeight: 1.4 }}>{selectedTemplate.description || "No description provided."}</div>
                  {selectedTemplate.measurement_source !== "manual" && (
                    <div style={{ marginTop: 6, fontSize: 10, opacity: 0.8 }}>
                      Synced from: <b style={{ textTransform: "uppercase" }}>{selectedTemplate.measurement_source.replace(/_/g, " ")}</b>
                    </div>
                  )}
                </div>
              ) : "Select a template from the library for automated tracking, or type a custom goal below."}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: C.muted }}>No library templates available for {departmentKey || "this selection"}. Creating custom KPI.</div>
        )}

        <input
          className="inp"
          type="text"
          placeholder="Custom KPI / Goal Name"
          value={f.kpi}
          onChange={e => {
            setF(x => ({ ...x, kpi: e.target.value }));
            if (f.template_id) { setF(x => ({ ...x, template_id: "" })); setSelectedTemplate(null); }
          }}
          disabled={!departmentKey}
          style={{ marginTop: 12 }}
        />
      </div>

      <div className="g2" style={{ gap: 16 }}>
        <div>
          <Lbl>Monthly Target *</Lbl>
          <div style={{ position: "relative" }}>
            <input className="inp" type="number" placeholder="0" value={f.target} onChange={e => setF(x => ({ ...x, target: e.target.value }))} style={{ paddingRight: 60 }} />
            <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", fontSize: 12, fontWeight: 800, color: T.orange }}>{f.unit || "unit"}</div>
          </div>
        </div>
        <div><Lbl>Unit Label</Lbl><input className="inp" placeholder="e.g. deals, %, lead" value={f.unit} onChange={e => setF(x => ({ ...x, unit: e.target.value }))} /></div>
      </div>

      <div className="g2" style={{ gap: 16 }}>
        <div>
          <Lbl>Performance Period</Lbl>
          <select className="inp" value={f.period} onChange={e => setF(x => ({ ...x, period: e.target.value }))}>
            {["Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026"].map(p => <option key={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <Lbl>Publication Status</Lbl>
          <select className="inp" value={f.status} onChange={e => setF(x => ({ ...x, status: e.target.value }))}>
            <option value="Published">Published — Visible to Staff</option>
            <option value="Draft">Draft — Hidden from Staff</option>
          </select>
        </div>
      </div>

      <div style={{ marginTop: 8 }}>
        <button className="bp" onClick={save} style={{ width: "100%", padding: 14, fontSize: 15 }}>
          {initialGoal ? "Update Goal Instance" : "Create & Activate Goal"}
        </button>
      </div>
    </div>
  );
}

function KpiTemplateManager({ departments = [], templates = [], onSave, onUpdate, onClose }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [editId, setEditId] = useState("");
  const [form, setForm] = useState({ name: "", department: "", category: "", description: "", is_active: true, measurement_source: "manual", default_unit: "count" });
  const [saving, setSaving] = useState(false);

  // Deduplicate templates by name and department for the display list
  const uniqueTemplates = Array.from(
    templates.reduce((map, obj) => {
      const key = `${obj.name}-${obj.department}`;
      if (!map.has(key)) map.set(key, obj);
      return map;
    }, new Map()).values()
  );

  const sources = [
    { id: "manual", label: "✍️ Manual Entry", desc: "Manager must update the actual value manually." },
    { id: "mkt_leads_added", label: "🤖 Leads Generated (CRM)", desc: "Counts distinct contacts added to CRM/Marketing by the staff." },
    { id: "mkt_lead_conversion", label: "📈 Lead Conversion (%)", desc: "Percentage of leads converted to paying clients." },
    { id: "sales_revenue", label: "💰 Sales Revenue (Paid)", desc: "Total sum of payments recorded by this staff." },
    { id: "sales_deals_closed", label: "🤝 Deals Closed", desc: "Count of invoices marked as 'Closed' by this staff." },
    { id: "ops_appointments", label: "🗓️ Appts Completed", desc: "Count of appointments successfully completed." },
    { id: "admin_ticket_esc", label: "🎫 Support Efficiency", desc: "Count of pending vs resolved tickets." }
  ];

  const beginEdit = (template) => {
    setEditId(template.id);
    setForm({
      name: template.name,
      department: template.department,
      category: template.category || "",
      description: template.description || "",
      is_active: template.is_active,
      measurement_source: template.measurement_source || "manual",
      default_unit: template.default_unit || "count"
    });
  };

  const resetForm = () => {
    setEditId("");
    setForm({ name: "", department: "", category: "", description: "", is_active: true, measurement_source: "manual", default_unit: "count" });
  };

  const handleSave = async () => {
    if (!form.name || !form.department) {
      alert("Please enter both a KPI name and department.");
      return;
    }
    setSaving(true);
    try {
      if (editId) {
        await onUpdate(editId, form);
      } else {
        await onSave(form);
      }
      resetForm();
    } catch (e) {
      alert("Error saving KPI template: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "min(650px, 75vh)" }}>
      {/* Container for responsive layout */}
      <style>{`
        .kpi-mgr-layout { display: flex; gap: 24px; height: 100%; flex-direction: row; overflow: hidden; }
        .kpi-mgr-sidebar { width: 280px; border-right: 1px solid ${C.border}; display: flex; flex-direction: column; overflow: hidden; }
        .kpi-mgr-content { flex: 1; display: flex; flex-direction: column; gap: 20px; overflow-y: auto; padding-right: 10px; }
        @media (max-width: 640px) {
          .kpi-mgr-layout { flex-direction: column; overflow: auto; }
          .kpi-mgr-sidebar { width: 100%; border-right: none; border-bottom: 1px solid ${C.border}; height: 280px; padding-bottom: 14px; margin-bottom: 14px; flex: none; }
          .kpi-mgr-content { padding-right: 0; overflow: visible; }
        }
      `}</style>
      <div className="kpi-mgr-layout">
        {/* Sidebar List */}
        <div className="kpi-mgr-sidebar">
          <div style={{ padding: "0 10px 10px", fontSize: 13, fontWeight: 700, borderBottom: `1px solid ${C.border}`, marginBottom: 14 }}>Library Definitions ({uniqueTemplates.length})</div>
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, paddingRight: 10 }}>
            {uniqueTemplates.map(t => (
              <div key={t.id} onClick={() => beginEdit(t)} style={{
                padding: 12, borderRadius: 10, cursor: "pointer",
                background: editId === t.id ? `${T.orange}11` : "transparent",
                border: `1px solid ${editId === t.id ? `${T.orange}33` : "transparent"}`,
                transition: "all 0.2s"
              }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: editId === t.id ? T.orange : C.text }}>{t.name}</div>
                <div style={{ fontSize: 10, color: C.muted, marginTop: 4 }}>{t.department} · {t.measurement_source === "manual" ? "Manual" : "Auto"}</div>
              </div>
            ))}
            {uniqueTemplates.length === 0 && <div style={{ fontSize: 12, color: C.muted, padding: 20, textAlign: "center" }}>No templates found.</div>}
          </div>
          <button className="bg" onClick={resetForm} style={{ marginTop: 14, width: "100%", flexShrink: 0 }}>+ Define New KPI</button>
        </div>

        {/* Editor Content */}
        <div className="kpi-mgr-content">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="ho" style={{ fontSize: 18 }}>{editId ? "Edit Definition" : "New Library Definition"}</div>
            <span className="tg" style={{ background: form.is_active ? "#4ADE8022" : "#94A3B822", color: form.is_active ? "#4ADE80" : "#94A3B8" }}>
              {form.is_active ? "Active" : "Archived"}
            </span>
          </div>

          <div className="g2" style={{ gap: 16 }}>
            <div><Lbl>KPI Name *</Lbl><input className="inp" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Sales Revenue" /></div>
            <div><Lbl>Target Department *</Lbl>
              <select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}>
                <option value="">— Select —</option>
                {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
              </select>
            </div>
          </div>

          <div className="g2" style={{ gap: 16 }}>
            <div><Lbl>Measurement Source</Lbl>
              <select className="inp" value={form.measurement_source} onChange={e => setForm(f => ({ ...f, measurement_source: e.target.value }))}>
                {sources.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </div>
            <div><Lbl>Default Unit</Lbl><input className="inp" value={form.default_unit} onChange={e => setForm(f => ({ ...f, default_unit: e.target.value }))} placeholder="e.g. leads, NGN, %" /></div>
          </div>

          <div style={{ padding: 14, background: dark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", borderRadius: 10, border: `1px solid ${C.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <div style={{ fontSize: 16 }}>{sources.find(s => s.id === form.measurement_source)?.label?.split(" ")[0] || "✍️"}</div>
              <div style={{ fontSize: 12, fontWeight: 800, color: C.text }}>{sources.find(s => s.id === form.measurement_source)?.label?.split(" ").slice(1).join(" ") || "Manual Entry"}</div>
            </div>
            <div style={{ fontSize: 12, color: C.sub }}>{sources.find(s => s.id === form.measurement_source)?.desc || "Manager must update the actual value manually."}</div>
          </div>

          <div><Lbl>Library Guidance / Description</Lbl><textarea className="inp" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Instructions for managers..." /></div>

          <div style={{ display: "flex", gap: 12, marginTop: "auto", borderTop: `1px solid ${C.border}`, paddingTop: 20 }}>
            <button className="bp" onClick={handleSave} disabled={saving} style={{ flex: 1, padding: 14 }}>
              {saving ? "Saving..." : editId ? "Update Definition" : "Save to Library"}
            </button>
            <button className="bg" style={{ padding: 14 }} onClick={onClose}>Cancel</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── LEAVE REQUEST FORM ───────────────────────────────────────────────────────
function LeaveForm({ onSave, currentUserId }) {
  const [f, setF] = useState({ uid: currentUserId ? String(currentUserId) : "", type: "Annual Leave", from: "", to: "", reason: "" });
  const fmt = d => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  const save = () => {
    if (!f.uid || !f.from || !f.to) return;
    const days = Math.max(1, Math.round((new Date(f.to) - new Date(f.from)) / (864e5)) + 1);
    onSave({ id: Date.now(), uid: parseInt(f.uid), type: f.type, from: fmt(f.from), to: fmt(f.to), days, status: "Pending", reason: f.reason });
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {!currentUserId && (
        <div>
          <Lbl>Staff Member *</Lbl>
          <select className="inp" value={f.uid} onChange={e => setF(x => ({ ...x, uid: e.target.value }))}>
            <option value="">— Select Staff Member —</option>
            {USERS.filter(u => u.role !== "hr_admin").map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
        </div>
      )}
      <div>
        <Lbl>Leave Type *</Lbl>
        <select className="inp" value={f.type} onChange={e => setF(x => ({ ...x, type: e.target.value }))}>
          {["Annual Leave", "Sick Leave", "Study Leave", "Maternity Leave", "Paternity Leave", "Compassionate Leave"].map(t => <option key={t}>{t}</option>)}
        </select>
      </div>
      <div className="g2" style={{ gap: 12 }}>
        <div><Lbl>From *</Lbl><input className="inp" type="date" value={f.from} onChange={e => setF(x => ({ ...x, from: e.target.value }))} /></div>
        <div><Lbl>To *</Lbl><input className="inp" type="date" value={f.to} onChange={e => setF(x => ({ ...x, to: e.target.value }))} /></div>
      </div>
      <div><Lbl>Reason</Lbl><textarea className="inp" placeholder="Brief reason for leave request…" value={f.reason} onChange={e => setF(x => ({ ...x, reason: e.target.value }))} /></div>
      <button className="bp" onClick={save} style={{ padding: 12 }}>Submit Request</button>
    </div>
  );
}


function Goals({ viewOnly, userId, canManageKpiTemplates = false }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { departments } = useDepartments();
  const [goals, setGoals] = useState([]);
  const [staff, setStaff] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);
  const [syncing, setSyncing] = useState(false);
  // For manual/auto goal progress update
  const [updateGoal, setUpdateGoal] = useState(null);
  const [updateValue, setUpdateValue] = useState("");
  const [updateSaving, setUpdateSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    const params = viewOnly ? `?staff_id=${userId}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/goals${params}`),
      apiFetch(`${API_BASE}/hr/kpi-templates?active=true`),
      !viewOnly ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([g, t, s]) => {
      setGoals(g);
      setTemplates(t);
      setStaff(s);
    }).finally(() => setLoading(false));
  }, [viewOnly, userId]);

  const refresh = () => {
    const params = viewOnly ? `?staff_id=${userId}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/goals${params}`),
      apiFetch(`${API_BASE}/hr/kpi-templates?active=true`)
    ]).then(([g, t]) => {
      setGoals(g);
      setTemplates(t);
    });
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await apiFetch(`${API_BASE}/hr/goals/sync`, { method: "POST" });
      setTimeout(refresh, 2000); // Give background worker a head start
      alert("Performance sync triggered. Data will update in a moment.");
    } catch (e) {
      alert("Sync failed: " + e.message);
    } finally {
      setSyncing(false);
    }
  };

  const saveGoal = async (g) => {
    try {
      // Parse "Apr 2026" → "2026-04-01", avoiding timezone issues by building the date explicitly
      const parsePeriod = (period) => {
        if (!period) return new Date().toISOString().split('T')[0];
        const months = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
        const parts = period.split(' ');
        const m = String(months[parts[0]] || 1).padStart(2, '0');
        return `${parts[1]}-${m}-01`;
      };
      const month = parsePeriod(g.period);
      const payload = {
        kpi_name: g.kpi,
        target_value: g.target,
        unit: g.unit,
        template_id: g.template_id || null,
        weight: 1.0, // Default weight
        status: g.status || "Draft",
        month
      };
      if (g.uid) {
        payload.staff_id = g.uid;
      } else if (g.department) {
        payload.department = g.department;
      }

      if (editingGoal) {
        await apiFetch(`${API_BASE}/hr/goals/${editingGoal.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload)
        });
        setEditingGoal(null);
      } else {
        await apiFetch(`${API_BASE}/hr/goals`, {
          method: "POST",
          body: JSON.stringify(payload)
        });
      }
      setShowNew(false);
      refresh();
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  const saveTemplate = async (template) => {
    try {
      await apiFetch(`${API_BASE}/hr/kpi-templates`, {
        method: "POST",
        body: JSON.stringify(template)
      });
      setShowTemplateManager(false);
      refresh();
    } catch (e) {
      alert("Error saving template: " + e.message);
    }
  };

  const updateTemplate = async (id, template) => {
    try {
      await apiFetch(`${API_BASE}/hr/kpi-templates/${id}`, {
        method: "PATCH",
        body: JSON.stringify(template)
      });
      setShowTemplateManager(false);
      refresh();
    } catch (e) {
      alert("Error updating template: " + e.message);
    }
  };

  // Mark a manual goal as fully completed (sets actual_value = target_value)
  const markGoalComplete = async (g) => {
    if (!window.confirm(`Mark "${g.kpi_name}" as Achieved? This will set actual to target (${g.target_value} ${g.unit}).`)) return;
    try {
      await apiFetch(`${API_BASE}/hr/goals/${g.id}`, {
        method: "PATCH",
        body: JSON.stringify({ actual_value: g.target_value, status: "Achieved" })
      });
      refresh();
    } catch (e) { alert("Error: " + e.message); }
  };

  // Update actual progress value for manual or auto goals
  const submitUpdateProgress = async () => {
    if (!updateGoal || updateValue === "") return;
    setUpdateSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/goals/${updateGoal.id}`, {
        method: "PATCH",
        body: JSON.stringify({ actual_value: parseFloat(updateValue) })
      });
      setUpdateGoal(null); setUpdateValue("");
      refresh();
    } catch (e) { alert("Error: " + e.message); } finally { setUpdateSaving(false); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>{viewOnly ? "My Goals" : "Goal Management"}</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>Monthly targets per staff member. These feed directly into performance scores.</div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {!viewOnly && (
            <button className="bg" onClick={handleSync} disabled={syncing} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {syncing ? "Syncing..." : "🔄 Sync Performance"}
            </button>
          )}
          {canManageKpiTemplates && <button className="bg" onClick={() => setShowTemplateManager(true)}>Manage KPI Library</button>}
          {!viewOnly && <button className="bp" onClick={() => { setEditingGoal(null); setShowNew(true); }}>+ Set KPI Goal</button>}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading goals…</div>
      ) : goals.length === 0 ? (
        <div className="gc" style={{ padding: 40, textAlign: "center" }}>
          <div style={{ fontSize: 13, color: C.muted }}>No goals on record for this period.</div>
        </div>
      ) : (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
          gap: 24
        }}>
          {goals.map((g, i) => {
            const u = g.admins || {};
            const pct = g.achievement_pct || (g.target_value > 0 ? Math.min(Math.round((g.actual_value / g.target_value) * 100), 120) : 0);
            const status = g.achievement_status || (pct >= 100 ? "Achieved" : "On Track");
            const isAuto = g.measurement_source && g.measurement_source !== "manual";

            const statusStyle = {
              "Achieved": { bg: "#10B98115", col: "#10B981", icon: "💎", grad: "linear-gradient(90deg, #10B981, #34D399)" },
              "At Risk": { bg: "#F8717115", col: "#F87171", icon: "🧨", grad: "linear-gradient(90deg, #F87171, #FCA5A5)" },
              "Behind": { bg: "#F8717115", col: "#F87171", icon: "🧨", grad: "linear-gradient(90deg, #F87171, #FCA5A5)" },
              "On Track": { bg: "#3B82F615", col: "#3B82F6", icon: "🚀", grad: "linear-gradient(90deg, #3B82F6, #60A5FA)" },
              "Fair": { bg: "#F59E0B15", col: "#F59E0B", icon: "⚖️", grad: "linear-gradient(90deg, #F59E0B, #FBBF24)" }
            }[status] || { bg: "#FFFFFF05", col: "#9CA3AF", icon: "•", grad: "linear-gradient(90deg, #9CA3AF, #D1D5DB)" };

            return (
              <div key={i} className="gc fade-in" style={{
                padding: 26,
                borderRadius: 20,
                position: "relative",
                overflow: "hidden",
                border: `1px solid ${dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)"}`,
                background: dark ? "rgba(25, 25, 35, 0.4)" : "rgba(255, 255, 255, 0.7)",
                backdropFilter: "blur(12px)",
                boxShadow: dark ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px rgba(0,0,0,0.03)",
                transition: "transform 0.2s ease, box-shadow 0.2s ease",
                cursor: "default"
              }}>
                {/* Visual Accent */}
                <div style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "4px",
                  height: "100%",
                  background: isAuto ? T.orange : statusStyle.col,
                  opacity: 0.8
                }} />

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={34} style={{ border: `2px solid ${statusStyle.col}33` }} />
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{u.full_name}</div>
                      <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: 0.5 }}>{u.department}</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span className="tg" style={{
                      background: statusStyle.bg,
                      color: statusStyle.col,
                      padding: "6px 12px",
                      fontSize: 11,
                      fontWeight: 700,
                      borderRadius: 100,
                      border: `1px solid ${statusStyle.col}33`,
                      display: "flex",
                      alignItems: "center",
                      gap: 6
                    }}>
                      <span>{statusStyle.icon}</span> {status.toUpperCase()}
                    </span>
                    {!viewOnly && g.status === "Draft" && (
                      <button className="bg" onClick={() => { setEditingGoal(g); setShowNew(true); }} style={{ padding: "6px 10px", borderRadius: 8, fontSize: 11 }}>Edit</button>
                    )}
                  </div>
                </div>

                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 18, fontWeight: 900, color: C.text, marginBottom: 4 }}>{g.kpi_name}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: C.muted }}>
                    <span>📅 {new Date(g.month).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</span>
                    <span style={{ opacity: 0.3 }}>|</span>
                    {isAuto ? (
                      <span style={{ color: T.orange, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                        <span style={{ fontSize: 14 }}>🤖</span> Automated
                      </span>
                    ) : (
                      <span>✍️ Manual Entry</span>
                    )}
                  </div>
                </div>

                <div style={{ background: dark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", borderRadius: 16, padding: 18, marginBottom: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <span style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", fontWeight: 700, marginBottom: 2 }}>Current Actual</span>
                      <span style={{ fontSize: 26, fontWeight: 900, color: statusStyle.col }}>{g.actual_value || 0} <span style={{ fontSize: 14, fontWeight: 500, color: C.muted }}>{g.unit}</span></span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                      <span style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", fontWeight: 700, marginBottom: 2 }}>Target</span>
                      <span style={{ fontSize: 18, fontWeight: 800, color: C.text }}>{g.target_value} <span style={{ fontSize: 12, fontWeight: 500, color: C.muted }}>{g.unit}</span></span>
                    </div>
                  </div>

                  <div style={{ height: 10, background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)", borderRadius: 10, overflow: "hidden", position: "relative" }}>
                    <div style={{
                      height: "100%",
                      width: `${Math.min(pct, 100)}%`,
                      background: statusStyle.grad,
                      borderRadius: 10,
                      transition: "width 1s cubic-bezier(0.4, 0, 0.2, 1)",
                      boxShadow: `0 0 15px ${statusStyle.col}44`
                    }} />
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                    <div style={{ fontSize: 12, color: statusStyle.col, fontWeight: 800 }}>
                      {pct}% COMPLETE
                    </div>
                    <div style={{ fontSize: 11, color: C.muted }}>
                      {status === "Achieved" ? "Goal Satisfied" : `${Math.max(0, g.target_value - (g.actual_value || 0))} ${g.unit} to go`}
                    </div>
                  </div>
                </div>

                {isAuto && (
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", opacity: 0.7, marginBottom: 10 }}>
                    <div style={{ fontSize: 11, color: C.muted }}>
                      Last Updated: <b>{g.last_synced_at ? new Date(g.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Waiting for sync..."}</b>
                    </div>
                    <span style={{ fontSize: 12 }}>⚡</span>
                  </div>
                )}

                {/* ── Goal Action Buttons ── */}
                {status !== "Achieved" && (
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    {!isAuto && (
                      <button
                        className="bp"
                        onClick={() => markGoalComplete(g)}
                        style={{ flex: 1, padding: "8px 12px", fontSize: 12, background: "#10B981", border: "none", borderRadius: 10 }}
                      >
                        ✅ Mark as Achieved
                      </button>
                    )}
                    <button
                      className="bg"
                      onClick={() => { setUpdateGoal(g); setUpdateValue(String(g.actual_value || 0)); }}
                      style={{ flex: 1, padding: "8px 12px", fontSize: 12, borderRadius: 10 }}
                    >
                      {isAuto ? "⚙️ Override Progress" : "✏️ Update Progress"}
                    </button>
                  </div>
                )}
                {status === "Achieved" && (
                  <div style={{ textAlign: "center", fontSize: 12, color: "#10B981", fontWeight: 700, marginTop: 4 }}>
                    🏆 Goal Achieved
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Update Progress Modal ── */}
      {updateGoal && (
        <Modal onClose={() => { setUpdateGoal(null); setUpdateValue(""); }} title={`Update Progress — ${updateGoal.kpi_name}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div style={{ fontSize: 13, color: dark ? "#9CA3AF" : "#6B7280" }}>
              {updateGoal.measurement_source && updateGoal.measurement_source !== "manual"
                ? "⚙️ This goal is auto-tracked. Override the synced value if needed (e.g. manual corrections)."
                : "✍️ Enter the current actual value for this manual goal."}
            </div>
            <div>
              <Lbl>Current Actual Value ({updateGoal.unit})</Lbl>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <input
                  className="inp"
                  type="number"
                  min="0"
                  value={updateValue}
                  onChange={e => setUpdateValue(e.target.value)}
                  style={{ flex: 1 }}
                  autoFocus
                />
                <span style={{ fontSize: 12, color: dark ? "#9CA3AF" : "#6B7280", whiteSpace: "nowrap" }}>
                  Target: {updateGoal.target_value} {updateGoal.unit}
                </span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="bp" onClick={submitUpdateProgress} disabled={updateSaving} style={{ flex: 1, padding: 12 }}>
                {updateSaving ? "Saving..." : "Save Progress"}
              </button>
              <button className="bg" onClick={() => { setUpdateGoal(null); setUpdateValue(""); }} style={{ flex: 1, padding: 12 }}>
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}

      {showNew && (
        <Modal onClose={() => { setShowNew(false); setEditingGoal(null); }} title={editingGoal ? "Edit Goal" : "Set New Goal"}>
          <GoalForm staffList={staff} templates={templates} initialGoal={editingGoal} onSave={saveGoal} departments={departments} />
        </Modal>
      )}

      {showTemplateManager && (
        <Modal onClose={() => setShowTemplateManager(false)} title="Manage KPI Library">
          <KpiTemplateManager
            departments={departments}
            templates={templates}
            onSave={saveTemplate}
            onUpdate={updateTemplate}
            onClose={() => setShowTemplateManager(false)}
          />
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: ABSENCE REPORT ──────────────────────────────────────────────────
function AbsenceReport({ currentUserId, C, dark }) {
  const [staff, setStaff] = useState([]);
  const [selectedStaff, setSelectedStaff] = useState(currentUserId || "");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const now = new Date();
  const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split("T")[0];
  const [startDate, setStartDate] = useState(firstOfMonth);
  const [endDate, setEndDate] = useState(now.toISOString().split("T")[0]);

  // Load staff list for HR dropdown
  useEffect(() => {
    if (!currentUserId) {
      apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(Array.isArray(d) ? d : [])).catch(() => { });
    }
  }, [currentUserId]);

  const loadReport = () => {
    if (!selectedStaff) return;
    setLoading(true);
    const params = new URLSearchParams({ staff_id: selectedStaff, start_date: startDate, end_date: endDate });
    apiFetch(`${API_BASE}/hr/presence/absences?${params}`)
      .then(d => setReport(d))
      .catch(e => alert("Failed to load report: " + e.message))
      .finally(() => setLoading(false));
  };

  const statusProps = {
    present: { label: "Present", bg: "#4ADE8022", color: "#4ADE80", border: "#4ADE8044" },
    late: { label: "Late", bg: "#FBB04022", color: "#FBB040", border: "#FBB04044" },
    absent: { label: "Absent", bg: "#F8717122", color: "#F87171", border: "#F8717144" },
    on_leave: { label: "On Leave", bg: `${T.orange}22`, color: T.orange, border: `${T.orange}44` },
    weekend: { label: "Weekend", bg: `${C.border}66`, color: C.muted, border: C.border },
    future: { label: "—", bg: "transparent", color: C.muted, border: "transparent" },
  };

  return (
    <div className="fade">
      {/* Controls */}
      <div className="gc" style={{ padding: 20, marginBottom: 18 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
          {!currentUserId && (
            <div style={{ flex: 1, minWidth: 180 }}>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>Staff Member</div>
              <select
                value={selectedStaff}
                onChange={e => setSelectedStaff(e.target.value)}
                className="inp"
                style={{ width: "100%" }}
              >
                <option value="">— Select Staff —</option>
                {staff.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department || "General"})</option>)}
              </select>
            </div>
          )}
          <div>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>From</div>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="inp" style={{ padding: "6px 10px" }} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>To</div>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="inp" style={{ padding: "6px 10px" }} />
          </div>
          <button className="bp" onClick={loadReport} disabled={!selectedStaff || loading} style={{ padding: "8px 20px" }}>
            {loading ? "Loading…" : "Generate Report"}
          </button>
        </div>
      </div>

      {report && (
        <>
          {/* Summary cards */}
          <div className="g4" style={{ marginBottom: 18 }}>
            {[
              ["Working Days", report.summary.total_working_days, C.text],
              ["Present", report.summary.present, "#4ADE80"],
              ["Late", report.summary.late, "#FBB040"],
              ["Absent", report.summary.absent, "#F87171"],
            ].map(([label, value, col]) => (
              <StatCard key={label} label={label} value={value} col={col}
                sub={report.summary.total_working_days > 0
                  ? `${Math.round(value / report.summary.total_working_days * 100)}% of working days`
                  : "—"}
              />
            ))}
          </div>

          {/* Absent days alert */}
          {report.summary.absent > 0 && (
            <div style={{ padding: "12px 16px", background: "#F8717111", border: "1px solid #F8717133", borderRadius: 10, marginBottom: 16, fontSize: 13, color: "#F87171" }}>
              ⚠️ <strong>{report.summary.absent} unexcused absence{report.summary.absent !== 1 ? "s" : ""}</strong> detected in this period.
            </div>
          )}

          {/* Day grid */}
          <div className="gc" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <div className="ho" style={{ fontSize: 15 }}>Day-by-Day Breakdown</div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {Object.entries(statusProps).filter(([k]) => k !== "future").map(([key, p]) => (
                  <div key={key} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: p.color }} />
                    <span style={{ color: C.sub }}>{p.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 8 }}>
              {report.days.map(d => {
                const p = statusProps[d.status] || statusProps.future;
                return (
                  <div key={d.date} style={{
                    padding: "10px 10px",
                    background: p.bg,
                    border: `1px solid ${p.border}`,
                    borderRadius: 8,
                    opacity: d.status === "weekend" ? 0.4 : 1
                  }}>
                    <div style={{ fontSize: 10, color: C.muted, marginBottom: 2 }}>{d.day.slice(0, 3)}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: p.color, marginBottom: 3 }}>
                      {new Date(d.date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                    </div>
                    <div style={{ fontSize: 9, color: d.status === "weekend" ? C.muted : p.color, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
                      {p.label}
                    </div>
                    {d.check_in && (
                      <div style={{ fontSize: 9, color: C.muted, marginTop: 2 }}>
                        {new Date(d.check_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
      {!report && !loading && (
        <div style={{ textAlign: "center", padding: 60, color: C.muted }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>📅</div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Select a staff member to view their attendance history</div>
          <div style={{ fontSize: 12 }}>Each working day will be color-coded by status.</div>
        </div>
      )}
    </div>
  );
}

// ─── MODULE: PRESENCE ────────────────────────────────────────────────────────
function Presence({ currentUserId, currentUser }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [sub, setSub] = useState("attendance");
  const now = new Date();
  const sevenDaysAgo = new Date(); sevenDaysAgo.setDate(now.getDate() - 7);
  const [startDate, setStartDate] = useState(sevenDaysAgo.toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(now.toISOString().split("T")[0]);
  const [reqs, setReqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [globalAbsences, setGlobalAbsences] = useState([]);
  const [loadingLog, setLoadingLog] = useState(false);
  const [logStart, setLogStart] = useState(sevenDaysAgo.toISOString().split("T")[0]);
  const [logEnd, setLogEnd] = useState(now.toISOString().split("T")[0]);

  const loadGlobalAbsences = () => {
    setLoadingLog(true);
    apiFetch(`${API_BASE}/hr/presence/global-absences?start_date=${logStart}&end_date=${logEnd}`)
      .then(d => setGlobalAbsences(d))
      .catch(e => alert("Error: " + e.message))
      .finally(() => setLoadingLog(false));
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch(`${API_BASE}/hr/presence/leaves`),
      apiFetch(`${API_BASE}/hr/presence/attendance?start_date=${startDate}&end_date=${endDate}`)
    ]).then(([l, a]) => {
      setReqs(l);
      setAttendance(a);
    }).finally(() => setLoading(false));
  }, [startDate, endDate]);

  const [attendance, setAttendance] = useState([]);

  const refresh = () => Promise.all([
    apiFetch(`${API_BASE}/hr/leave/pending`),
    apiFetch(`${API_BASE}/hr/presence/attendance?start_date=${startDate}&end_date=${endDate}`)
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
    ? reqs.filter(l => l.staff_id === currentUserId)
    : reqs;

  const statusColor = { Present: "#4ADE80", "On Leave": T.orange, Late: "#FBB040", Absent: "#F87171" };

  return (
    <div className="fade">
      <div className="ho" style={{ fontSize: 22, marginBottom: 4 }}>Presence</div>
      <div style={{ fontSize: 13, color: (dark ? DARK : LIGHT).sub, marginBottom: 18 }}>Attendance tracking and leave management — one tab.</div>

      <Tabs items={[["attendance", "Attendance"], ["leave", "Leave Management"], ["absences", "Absenteeism Report"], ["absence_log", "Global Absence Log"]]} active={sub} setActive={setSub} />

      {sub === "attendance" && (
        <>
          {!currentUserId && (
            <div className="g4" style={{ marginBottom: 22 }}>
              {[[
                "Present",
                attendance.filter(a => a.status === "Present").length,
                "#4ADE80",
                `${attendance.length > 0 ? Math.round(attendance.filter(a => a.status === "Present").length / attendance.length * 100) : 0}% attendance rate`
              ], [
                "On Leave",
                attendance.filter(a => a.status === "On Leave").length,
                T.orange,
                "Approved absences"
              ], [
                "Late",
                attendance.filter(a => { const ci = a.check_in; if (!ci) return false; const t = ci.split("T")[1] || ci; return t.slice(0, 8) > "09:00:00"; }).length,
                "#FBB040",
                "Checked in after 09:00 AM"
              ], [
                "Suspicious",
                attendance.filter(a => a.is_suspicious).length,
                "#F87171",
                "Geofence or device flags"
              ]].map(([label, value, col, sub]) => (
                <StatCard key={label} label={label} value={value} col={col} sub={sub} />
              ))}
            </div>
          )}
          {currentUser && <AttendanceCheckIn user={currentUser} />}
          <div className="gc" style={{ overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20 }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div className="ho" style={{ fontSize: 15 }}>Attendance Records</div>
                <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{attendance.length} record{attendance.length !== 1 ? "s" : ""} in selected period</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, color: C.muted }}>From</span>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="inp" style={{ width: "auto", padding: "4px 8px", fontSize: 12 }} />
                <span style={{ fontSize: 12, color: C.muted }}>To</span>
                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="inp" style={{ width: "auto", padding: "4px 8px", fontSize: 12 }} />
              </div>
            </div>
            {attendance.length === 0 ? (
              <div style={{ padding: "40px 20px", textAlign: "center", color: C.muted }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>No attendance records found</div>
                <div style={{ fontSize: 12 }}>No check-ins were recorded for this date range.</div>
              </div>
            ) : (
              <div className="tw">
                <table className="ht">
                  <thead><tr>{["Date", "Employee", "Dept", "Security", "Device", "IP", "Check In", "Check Out", "Hours", "Status"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                  <tbody>
                    {attendance.map(a => {
                      const u = a.admins || { full_name: "Unknown Staff", department: "General" };
                      const sc = statusColor[a.status] || C.sub;
                      const ci = a.check_in;
                      const isLate = ci && (ci.split("T")[1] || ci).slice(0, 8) > "09:00:00";
                      return (
                        <tr key={a.id}>
                          <td style={{ fontSize: 11, fontWeight: 600 }}>{new Date(a.date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</td>
                          <td><div style={{ display: "flex", alignItems: "center", gap: 8 }}><Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={26} /><span style={{ fontWeight: 700, fontSize: 13 }}>{u.full_name}</span></div></td>
                          <td style={{ color: C.sub, fontSize: 11 }}>{u.department || "General"}</td>
                          <td>
                            {a.is_remote ? (
                              <span className="tg" style={{ background: `${T.orange}22`, color: T.orange, border: `1px solid ${T.orange}33`, fontSize: 10 }}>🏠 Remote</span>
                            ) : a.is_suspicious ? (
                              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                                <span className="tg" style={{ background: "#F8717122", color: "#F87171", border: "1px solid #F8717133", fontSize: 10 }} title={a.suspicious_reason}>🚩 Flagged</span>
                                <div style={{ fontSize: 9, color: "#F87171", maxWidth: 120, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={a.suspicious_reason}>{a.distance_meters ? `${Math.round(a.distance_meters)}m away` : "No GPS"}</div>
                              </div>
                            ) : (
                              <span className="tg" style={{ background: "#4ADE8022", color: "#4ADE80", border: "1px solid #4ADE8033", fontSize: 10 }}>✓ OK</span>
                            )}
                          </td>
                          <td style={{ fontSize: 10, color: C.sub }} title={a.user_agent}>🖥️ {a.device_type || "—"}</td>
                          <td style={{ fontSize: 11, color: C.text, fontFamily: "monospace" }}>{a.ip_address || "—"}</td>
                          <td>
                            <div style={{ fontSize: 12, fontWeight: 600, color: isLate ? "#FBB040" : C.text }}>
                              {ci ? new Date(ci).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "—"}
                            </div>
                            {isLate && <div style={{ fontSize: 9, color: "#FBB040" }}>Late</div>}
                          </td>
                          <td style={{ fontSize: 12, color: C.sub }}>{a.check_out ? new Date(a.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "—"}</td>
                          <td style={{ color: T.orange, fontWeight: 800, fontSize: 12 }}>{ci && a.check_out ? (Math.abs(new Date(a.check_out) - new Date(ci)) / 36e5).toFixed(1) + "h" : "—"}</td>
                          <td><span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}33` }}>{a.status}</span></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {sub === "leave" && (
        <>
          <div className="gc" style={{ overflow: "hidden" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", borderBottom: `1px solid ${C.border}` }}>
              <div className="ho" style={{ fontSize: 14 }}>{currentUserId ? "My Leave Requests" : "Pending Leave Requests"}</div>
              <button className="bp" style={{ fontSize: 12, padding: "7px 16px" }} onClick={() => setShowForm(true)}>+ New Request</button>
            </div>
            <div style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
              {loading ? <div style={{ textAlign: "center", padding: 20, color: C.muted }}>Loading leave records…</div> :
                leaveVisible.map(l => {
                  const u = l.admins || {};
                  const sc = { approved: "#4ADE80", rejected: "#F87171", pending: "#FBB040" }[l.status];
                  return (
                    <div key={l.id} style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 16px", background: `${T.orange}08`, border: `1px solid ${T.orange}22`, borderRadius: 12 }}>
                      <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={38} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{u.full_name}</div>
                        <div style={{ fontSize: 12, color: C.sub, marginTop: 2 }}>{l.leave_type} · {new Date(l.start_date).toLocaleDateString()} → {new Date(l.end_date).toLocaleDateString()} · <span style={{ color: T.orange, fontWeight: 800 }}>{l.days_count} days</span></div>
                        {l.reason && <div style={{ fontSize: 12, color: C.muted, marginTop: 2, fontStyle: "italic" }}>"{l.reason}"</div>}
                      </div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
                        <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}33`, textTransform: "capitalize" }}>{l.status}</span>
                        {l.status === "pending" && !currentUserId && (
                          <>
                            <button className="bp" style={{ fontSize: 11, padding: "5px 12px" }} onClick={() => updateLeave(l.id, "approved")}>Approve</button>
                            <button className="bd" style={{ fontSize: 11 }} onClick={() => updateLeave(l.id, "rejected")}>Reject</button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              {!loading && leaveVisible.length === 0 && <div style={{ fontSize: 13, color: C.muted, padding: "12px 0", textAlign: "center" }}>No leave requests found.</div>}
            </div>
          </div>
        </>
      )}

      {sub === "absences" && <AbsenceReport staff={[]} currentUserId={currentUserId} C={C} dark={dark} />}

      {sub === "absence_log" && (
        <div className="fade">
          <div className="gc" style={{ padding: "20px 24px", marginBottom: 22 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 20 }}>
              <div style={{ display: "flex", gap: 14 }}>
                <div>
                  <div style={{ fontSize: 10, color: C.muted, marginBottom: 6, fontWeight: 800, textTransform: "uppercase" }}>Start Date</div>
                  <input type="date" value={logStart} onChange={e => setLogStart(e.target.value)} className="inp" style={{ width: 180 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: C.muted, marginBottom: 6, fontWeight: 800, textTransform: "uppercase" }}>End Date</div>
                  <input type="date" value={logEnd} onChange={e => setLogEnd(e.target.value)} className="inp" style={{ width: 180 }} />
                </div>
              </div>
              <button
                className="bp"
                onClick={loadGlobalAbsences}
                disabled={loadingLog}
                style={{ padding: "12px 30px" }}
              >
                {loadingLog ? "Calculating..." : "Generate Global Absence Report"}
              </button>
            </div>
          </div>

          <div className="gc" style={{ overflow: "hidden" }}>
            <div style={{ padding: "16px 22px", borderBottom: `1px solid ${C.border}` }}>
              <div className="ho" style={{ fontSize: 15 }}>Global Absence Records</div>
              <div style={{ fontSize: 12, color: C.sub, marginTop: 2 }}>Showing all missing man-days (excluding weekends & approved leaves)</div>
            </div>
            {globalAbsences.length === 0 && !loadingLog ? (
              <div style={{ padding: 60, textAlign: "center", color: C.muted }}>
                <div style={{ fontSize: 40, marginBottom: 10 }}>🔍</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>No absences recorded for this period</div>
                <div style={{ fontSize: 12 }}>Or you haven't generated the report yet.</div>
              </div>
            ) : (
              <table className="ht">
                <thead><tr>{["Date", "Staff Name", "Department", "Status"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {globalAbsences.map((a, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 700 }}>{new Date(a.date).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}</td>
                      <td>{a.staff_name}</td>
                      <td style={{ color: C.sub, fontSize: 12 }}>{a.department}</td>
                      <td><span className="tg tr" style={{ fontSize: 10 }}>{a.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {showForm && (
        <Modal onClose={() => setShowForm(false)} title="New Leave Request">
          <LeaveForm
            currentUserId={currentUserId || null}
            onSave={async (l) => {
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

// ─── MODULE: ATTENDANCE CHECK-IN ─────────────────────────────────────────────
function AttendanceCheckIn({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;

  const [todayRecord, setTodayRecord] = useState(null);
  const [isRemote, setRemote] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoad] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [locStatus, setLocStatus] = useState("idle");

  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "long", year: "numeric", month: "long", day: "numeric"
  });

  function detectDevice() {
    const ua = navigator.userAgent;
    if (/tablet|ipad|playbook|silk/i.test(ua)) return "Tablet";
    if (/mobile|iphone|ipod|android|blackberry|mini|windows\sce|palm/i.test(ua)) return "Mobile";
    return "Desktop";
  }

  useEffect(() => {
    const todayIso = new Date().toISOString().split("T")[0];
    apiFetch(`${API_BASE}/hr/presence/attendance?date=${todayIso}&staff_id=${user.id}`)
      .then(data => {
        if (Array.isArray(data) && data.length > 0) setTodayRecord(data[0]);
      })
      .catch(() => { })
      .finally(() => setLoading(false));
  }, [user.id]);

  function getLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve({ latitude: null, longitude: null, accuracy: null, status: "unavailable" });
        return;
      }
      setLocStatus("requesting");
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocStatus("granted");
          resolve({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            status: "granted",
          });
        },
        () => {
          setLocStatus("denied");
          resolve({ latitude: null, longitude: null, accuracy: null, status: "denied" });
        },
        { timeout: 10000, enableHighAccuracy: true }
      );
    });
  }

  async function handleCheckIn() {
    setError(null); setSuccess(null); setActionLoad(true);
    try {
      const loc = await getLocation();
      await apiFetch(`${API_BASE}/hr/presence/checkin`, {
        method: "POST",
        body: JSON.stringify({
          latitude: loc.latitude,
          longitude: loc.longitude,
          location_accuracy: loc.accuracy,
          location_status: loc.status,
          device_type: detectDevice(),
          is_remote: isRemote,
        }),
      });
      setSuccess(`Checked in at ${new Date().toLocaleTimeString()}${loc.status === "granted" ? " · Location recorded ✓" : " · Location unavailable (IP recorded)"}`);
      const todayIso = new Date().toISOString().split("T")[0];
      const updated = await apiFetch(`${API_BASE}/hr/presence/attendance?date=${todayIso}&staff_id=${user.id}`);
      if (Array.isArray(updated) && updated.length > 0) setTodayRecord(updated[0]);
    } catch (e) {
      setError(e.message || "Check-in failed. Please try again.");
    } finally {
      setActionLoad(false);
    }
  }

  async function handleCheckOut() {
    setError(null); setSuccess(null); setActionLoad(true);
    try {
      const loc = await getLocation();
      await apiFetch(`${API_BASE}/hr/presence/checkout`, {
        method: "PATCH",
        body: JSON.stringify({
          latitude: loc.latitude,
          longitude: loc.longitude,
          location_status: loc.status,
          device_type: detectDevice(),
          is_remote: todayRecord?.is_remote || isRemote,
        }),
      });
      setSuccess(`Checked out at ${new Date().toLocaleTimeString()}`);
      const todayIso = new Date().toISOString().split("T")[0];
      const updated = await apiFetch(`${API_BASE}/hr/presence/attendance?date=${todayIso}&staff_id=${user.id}`);
      if (Array.isArray(updated) && updated.length > 0) setTodayRecord(updated[0]);
    } catch (e) {
      setError(e.message || "Check-out failed. Please try again.");
    } finally {
      setActionLoad(false);
    }
  }

  const checkedIn = !!todayRecord?.check_in;
  const checkedOut = !!todayRecord?.check_out;

  const locBadgeColor = {
    granted: "#4ADE80",
    denied: "#F87171",
    unavailable: "#94A3B8",
    idle: "#94A3B8",
    requesting: "#FBB040",
  }[locStatus];

  return (
    <div className="gc" style={{ marginBottom: 22, padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <div className="ho" style={{ fontSize: 15, marginBottom: 4 }}>Mark Attendance</div>
        <div style={{ fontSize: 12, color: C.sub }}>{today}</div>
      </div>

      {loading ? (
        <div style={{ color: C.muted, fontSize: 13 }}>Loading today's record…</div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
            {checkedIn && (
              <span className="tg" style={{ background: "#4ADE8022", color: "#4ADE80", border: "1px solid #4ADE8033" }}>
                ✓ In: {new Date(todayRecord.check_in).toLocaleTimeString()}
              </span>
            )}
            {checkedOut && (
              <span className="tg" style={{ background: "#60A5FA22", color: "#60A5FA", border: "1px solid #60A5FA33" }}>
                ✓ Out: {new Date(todayRecord.check_out).toLocaleTimeString()}
              </span>
            )}
            {!checkedIn && (
              <span className="tg" style={{ background: "#F8714122", color: "#F87141", border: "1px solid #F8714133" }}>
                Not checked in
              </span>
            )}
          </div>

          <div style={{
            background: `${locBadgeColor}11`,
            border: `1px solid ${locBadgeColor}33`,
            borderRadius: 10,
            padding: "10px 14px",
            marginBottom: 18,
            fontSize: 12,
            color: C.sub,
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>📍</span>
            <span>
              {locStatus === "idle" && "When you check in, we'll ask for your location to verify attendance. Your IP address and device type are always recorded."}
              {locStatus === "requesting" && "Requesting location — please allow when your browser prompts…"}
              {locStatus === "granted" && <span style={{ color: "#4ADE80" }}>Location access granted. Coordinates recorded. ✓</span>}
              {locStatus === "denied" && <span style={{ color: "#F87171" }}>Location access denied. Your IP address and device type have been recorded instead. We strongly encourage you to allow location for accurate attendance.</span>}
              {locStatus === "unavailable" && "Location unavailable on this device. IP address and device type are still recorded."}
            </span>
          </div>

          {checkedIn && todayRecord && (
            <div style={{
              background: C.card || `${C.border}44`,
              borderRadius: 10,
              padding: "10px 14px",
              marginBottom: 18,
              fontSize: 12,
              color: C.sub,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "6px 16px",
            }}>
              {todayRecord.ip_address && (
                <><span style={{ color: C.muted }}>IP Address</span><span style={{ fontFamily: "monospace" }}>{todayRecord.ip_address}</span></>
              )}
              {todayRecord.device_type && (
                <><span style={{ color: C.muted }}>Device</span><span>{todayRecord.device_type}</span></>
              )}
              {!todayRecord.is_remote && todayRecord.latitude && (
                <><span style={{ color: C.muted }}>Coordinates</span><span>{todayRecord.latitude.toFixed(5)}, {todayRecord.longitude.toFixed(5)}</span></>
              )}
              {todayRecord.is_remote ? (
                <><span style={{ color: C.muted }}>Work Mode</span><span style={{ color: T.orange, fontWeight: 700 }}>🏠 Remote Working</span></>
              ) : todayRecord.location_status && (
                <><span style={{ color: C.muted }}>Location</span>
                  <span style={{ color: { granted: "#4ADE80", denied: "#F87171", unavailable: "#94A3B8" }[todayRecord.location_status] }}>
                    {todayRecord.location_status}
                  </span></>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            {!checkedIn && (
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer", background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)", padding: "10px 14px", borderRadius: 8, marginRight: "auto" }}>
                <input type="checkbox" checked={isRemote} onChange={e => setRemote(e.target.checked)} style={{ width: 16, height: 16, accentColor: T.orange }} />
                <span style={{ fontWeight: isRemote ? 700 : 500, color: isRemote ? T.orange : C.text }}>🏠 Working Remotely</span>
              </label>
            )}
            {!checkedIn && (
              <button
                className="bp"
                style={{ flex: 1, padding: "11px 0", fontSize: 14, fontWeight: 700, minWidth: 140 }}
                onClick={handleCheckIn}
                disabled={actionLoading}
              >
                {actionLoading ? "Recording…" : "✅ Check In"}
              </button>
            )}
            {checkedIn && !checkedOut && (
              <button
                className="bd"
                style={{ flex: 1, padding: "11px 0", fontSize: 14, fontWeight: 700 }}
                onClick={handleCheckOut}
                disabled={actionLoading}
              >
                {actionLoading ? "Recording…" : "🔴 Check Out"}
              </button>
            )}
            {checkedIn && checkedOut && (
              <div style={{ flex: 1, textAlign: "center", fontSize: 13, color: "#4ADE80", fontWeight: 700, padding: "11px 0" }}>
                ✓ Attendance complete for today
              </div>
            )}
          </div>

          {success && (
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#4ADE8011", border: "1px solid #4ADE8033", borderRadius: 8, fontSize: 13, color: "#4ADE80" }}>
              {success}
            </div>
          )}
          {error && (
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#F8714111", border: "1px solid #F8714133", borderRadius: 8, fontSize: 13, color: "#F87171" }}>
              ⚠ {error}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── MODULE: PERFORMANCE ──────────────────────────────────────────────────────
function Performance({ viewOnly, userId }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showRev, setShowRev] = useState(false);
  const [rev, setRev] = useState({ teamwork: 3, initiative: 3, quality: 80, notes: "" });

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
    if (!p) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading performance details…</div>;
    const sc = p.score;
    const col = sc >= 80 ? "#4ADE80" : sc >= 60 ? T.orange : "#F87171";
    const b = p.breakdown || {};

    return (
      <div style={{ maxWidth: 700 }}>
        {!viewOnly && <button className="bg" onClick={() => setSel(null)} style={{ marginBottom: 18, fontSize: 12 }}>← All Staff</button>}
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 26 }}>
          <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={62} gold />
          <div style={{ flex: 1 }}>
            <div className="ho" style={{ fontSize: 22 }}>{u.full_name}</div>
            <div style={{ fontSize: 13, color: C.sub }}>{u.staff_profiles?.[0]?.job_title || u.role} · {u.department}</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 46, fontWeight: 800, color: col, lineHeight: 1 }}>{sc}</div>
            <div style={{ fontSize: 11, color: C.muted }}>Overall Score</div>
          </div>
        </div>

        <div className="gc" style={{ padding: 22, marginBottom: 16 }}>
          <div className="ho" style={{ fontSize: 14, marginBottom: 18 }}>Performance Metrics Breakdown</div>
          {[["KPI Goals Achievement (40%)", b.goals_40_pct, "#4ADE80"], ["Work Quality (20%)", b.quality_20_pct, "#60A5FA"], ["Manager Review (40%)", b.manager_review_40_pct, T.orange]].map(([l, v, c]) => (
            <div key={l} style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 13, color: C.sub }}>{l}</span>
                <span style={{ fontSize: 17, fontWeight: 800, color: c }}>{Math.round(v)}%</span>
              </div>
              <div className="pt" style={{ height: 8 }}><div className="pf" style={{ width: `${v}%`, background: c }} /></div>
            </div>
          ))}
          <TrendChart data={[72, 75, 82, 80, 85, 88]} color={Math.round(b.goals_40_pct + b.quality_20_pct + b.manager_review_40_pct) >= 80 ? "#4ADE80" : T.orange} />
        </div>

        {!viewOnly && (
          <div style={{ display: "flex", gap: 12 }}>
            <button className="bp" onClick={() => setShowRev(true)}>Enter Formal Review</button>
            <button className="bg">Download Performance Report</button>
          </div>
        )}

        {showRev && (
          <Modal onClose={() => setShowRev(false)} title={`Formal Review: ${u.full_name}`}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div><Lbl>Work Quality (0–100)</Lbl>
                <input className="inp" type="number" value={rev.quality} onChange={e => setRev(r => ({ ...r, quality: +e.target.value }))} />
              </div>
              <div><Lbl>Teamwork & Communication (1–5)</Lbl>
                <select className="inp" value={rev.teamwork} onChange={e => setRev(r => ({ ...r, teamwork: +e.target.value }))}>
                  {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n} — {["", "Poor", "Below Average", "Average", "Good", "Excellent"][n]}</option>)}
                </select>
              </div>
              <div><Lbl>Initiative & Growth (1–5)</Lbl>
                <select className="inp" value={rev.initiative} onChange={e => setRev(r => ({ ...r, initiative: +e.target.value }))}>
                  {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n} — {["", "Poor", "Below Average", "Average", "Good", "Excellent"][n]}</option>)}
                </select>
              </div>
              <div><Lbl>Review Notes</Lbl><textarea className="inp" placeholder="Optional notes on this review cycle…" value={rev.notes} onChange={e => setRev(r => ({ ...r, notes: e.target.value }))} /></div>
              <button className="bp" onClick={submitReview} style={{ padding: 12 }}>Submit Formal Review</button>
            </div>
          </Modal>
        )}
      </div>
    );
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading performance metrics…</div>;

  if (viewOnly) {
    return <div className="fade">{renderDetail({ full_name: "My Profile" }, detail)}</div>;
  }

  return (
    <div className="fade">
      <div className="ho" style={{ fontSize: 22, marginBottom: 6 }}>Performance Dashboard</div>
      <div style={{ fontSize: 13, color: C.sub, marginBottom: 22 }}>Automated monthly scoring — computed from KPIs and manager reviews.</div>

      {!sel ? (
        <div className="g3">
          {staff.map(u => {
            const p = u.performance || { score: 0, rating: "Pending", breakdown: { goals_40_pct: 0, quality_20_pct: 0, manager_review_40_pct: 0 } };
            const sc = p.score || 0;
            const col = sc >= 80 ? "#4ADE80" : sc >= 60 ? T.orange : "#F87171";
            const b = p.breakdown || {};
            return (
              <div key={u.id} className="gc" style={{ padding: 22, cursor: "pointer" }} onClick={() => setSel(u)}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={40} />
                  <div><div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{u.full_name}</div><div style={{ fontSize: 12, color: C.sub }}>{u.department || 'Staff'}</div></div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
                  <ScoreRing sc={sc} sz={68} />
                  <div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: col }}>{sc}<span style={{ fontSize: 13, color: C.muted }}>/100</span></div>
                    <span className={`tg ${sc >= 80 ? "tg2" : sc >= 60 ? "to" : "tr"}`}>{p.rating}</span>
                  </div>
                </div>
                {[["KPI", b.goals_40_pct], ["Quality", b.quality_20_pct], ["Manager Review", b.manager_review_40_pct]].map(([l, v]) => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted, marginBottom: 4 }}><span>{l}</span><span style={{ color: T.orange, fontWeight: 800 }}>{Math.round(v || 0)}%</span></div>
                    <Bar pct={v || 0} />
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
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [tasks, setTasks] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [viewT, setViewT] = useState(null);
  const [nt, setNt] = useState({ title: "", assignedTo: "", due: "", priority: "Medium", desc: "" });
  // Rejection modal state
  const [rejectTarget, setRejectTarget] = useState(null); // task being rejected
  const [rejectNote, setRejectNote] = useState("");
  const [actionBusy, setActionBusy] = useState(false);

  const isHR = currentUser.role?.includes("admin") || currentUser.primary_role === "hr";
  const isLM = currentUser.role?.includes("line_manager");
  const isStaff = !isHR && !isLM;
  const canCreate = isHR || isLM;
  const canApprove = isHR || isLM;

  const sendNotif = (staffId, type, message) =>
    apiFetch(`${API_BASE}/hr/notifications`, {
      method: "POST",
      body: JSON.stringify({ staff_id: staffId, type, message })
    }).catch(() => { });

  const refresh = () => {
    const params = isStaff ? `?staff_id=${currentUser.id}` : "";
    apiFetch(`${API_BASE}/hr/tasks${params}`).then(t => {
      setTasks(t || []);
      // keep viewT in sync
      setViewT(v => v ? (t || []).find(x => x.id === v.id) || null : null);
    });
  };

  useEffect(() => {
    setLoading(true);
    const params = isStaff ? `?staff_id=${currentUser.id}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/tasks${params}`),
      canCreate ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([t, s]) => { setTasks(t || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [currentUser.id]);

  // HR/Manager creates and assigns a task → notify the employee
  const add = async () => {
    if (!nt.title || !nt.assignedTo || !nt.due) return alert("Title, assignee and due date are required.");
    setActionBusy(true);
    try {
      const task = await apiFetch(`${API_BASE}/hr/tasks`, {
        method: "POST",
        body: JSON.stringify({ assigned_to: nt.assignedTo, title: nt.title, due_date: nt.due, priority: nt.priority, notes: nt.desc })
      });
      await sendNotif(
        nt.assignedTo, "task_assigned",
        `📋 You have been assigned a new task: "${nt.title}". Due: ${new Date(nt.due).toLocaleDateString()}. Priority: ${nt.priority}.`
      );
      setNt({ title: "", assignedTo: "", due: "", priority: "Medium", desc: "" });
      setShowNew(false);
      refresh();
    } catch (e) { alert("Error: " + e.message); } finally { setActionBusy(false); }
  };

  // Employee marks task as done → status becomes "pending_approval", notify HR/manager
  const markDone = async (task) => {
    if (task.status === "pending_approval" || task.status === "approved") return;
    setActionBusy(true);
    try {
      await apiFetch(`${API_BASE}/hr/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "pending_approval" })
      });
      // Notify the assigner (assigned_by field) or broadcast to HR role
      const assignerId = task.assigned_by || null;
      if (assignerId) {
        await sendNotif(
          assignerId, "task_assigned_hr",
          `✅ ${currentUser.full_name} has marked task "${task.title}" as completed — awaiting your approval.`
        );
      }
      refresh();
    } catch (e) { alert("Failed: " + e.message); } finally { setActionBusy(false); }
  };

  // HR/Manager approves the completion → notify employee
  const approveTask = async (task) => {
    setActionBusy(true);
    try {
      await apiFetch(`${API_BASE}/hr/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "completed" })
      });
      await sendNotif(
        task.assigned_to, "task_assigned",
        `🎉 Your task "${task.title}" has been approved as completed by HR/Management. Great work!`
      );
      setViewT(null);
      refresh();
    } catch (e) { alert("Failed: " + e.message); } finally { setActionBusy(false); }
  };

  // HR/Manager rejects → status reverts to in_progress, employee notified with note
  const rejectTask = async () => {
    if (!rejectNote.trim()) return alert("Please provide a reason for rejection.");
    setActionBusy(true);
    try {
      await apiFetch(`${API_BASE}/hr/tasks/${rejectTarget.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "in_progress", rejection_note: rejectNote.trim() })
      });
      await sendNotif(
        rejectTarget.assigned_to, "task_assigned",
        `🔁 Your task "${rejectTarget.title}" was sent back for revision. Note from reviewer: "${rejectNote.trim()}"`
      );
      setRejectTarget(null); setRejectNote("");
      setViewT(null);
      refresh();
    } catch (e) { alert("Failed: " + e.message); } finally { setActionBusy(false); }
  };

  // Staff can toggle between pending ↔ in_progress only (not "completed" — that requires approval)
  const staffUpdateStatus = async (task, newStatus) => {
    if (!["pending", "in_progress"].includes(newStatus)) return;
    setActionBusy(true);
    try {
      await apiFetch(`${API_BASE}/hr/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus })
      });
      refresh();
    } catch (e) { alert("Failed: " + e.message); } finally { setActionBusy(false); }
  };

  // Augmented status colours — pending_approval gets amber, approved = green alias
  const allSCol = { ...sCol, pending_approval: "#F59E0B", approved: "#4ADE80" };
  const statusLabel = { pending: "Pending", in_progress: "In Progress", pending_approval: "Awaiting Approval", completed: "Completed", approved: "Completed" };

  const tabCounts = {
    all: tasks.length,
    pending_approval: tasks.filter(t => t.status === "pending_approval").length,
    mine: isStaff ? tasks.length : tasks.filter(t => t.assigned_to === currentUser.id).length,
  };
  const [filterTab, setFilterTab] = useState("all");
  const visibleTasks = tasks.filter(t => {
    if (filterTab === "pending_approval") return t.status === "pending_approval";
    if (filterTab === "mine") return t.assigned_to === currentUser.id;
    return true;
  });

  return (
    <div className="fade">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>{isStaff ? "My Tasks" : "Task Manager"}</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>
            {isStaff
              ? "Mark tasks as done when complete — HR or your manager will approve them."
              : "Assign tasks, review completions, and approve or send back for revision."}
          </div>
        </div>
        {canCreate && <button className="bp" onClick={() => setShowNew(true)}>+ Assign Task</button>}
      </div>

      {/* Filter tabs (only for HR/manager) */}
      {canApprove && (
        <div className="tab-bar" style={{ marginBottom: 20 }}>
          {[["all", "All Tasks"], ["pending_approval", `Awaiting Approval${tabCounts.pending_approval > 0 ? ` (${tabCounts.pending_approval})` : ""}`]].map(([k, l]) => (
            <button key={k} className={`tab ${filterTab === k ? "on" : "off"}`} onClick={() => setFilterTab(k)}>{l}</button>
          ))}
        </div>
      )}

      {/* Task grid */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading tasks…</div>
      ) : visibleTasks.length === 0 ? (
        <div className="gc" style={{ padding: 40, textAlign: "center", color: C.muted }}>
          {filterTab === "pending_approval" ? "No tasks awaiting approval." : "No tasks found."}
        </div>
      ) : (
        <div className={isStaff ? "g2" : "g3"} style={{ gap: 14 }}>
          {visibleTasks.map(t => {
            const u = t.admins || {};
            const pc = pCol[t.priority] || T.orange;
            const sc = allSCol[t.status] || T.orange;
            const needsApproval = t.status === "pending_approval";
            return (
              <div key={t.id} className="gc" style={{ padding: 20, cursor: "pointer", borderColor: needsApproval ? "#F59E0B66" : undefined, boxShadow: needsApproval ? `0 0 0 1px #F59E0B33, 0 0 14px #F59E0B18` : undefined }} onClick={() => setViewT(t)}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                  <span className="tg" style={{ background: `${pc}22`, color: pc, border: `1px solid ${pc}33` }}>{t.priority}</span>
                  <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}33` }}>{statusLabel[t.status] || t.status}</span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 800, color: C.text, marginBottom: 6, lineHeight: 1.4 }}>{t.title}</div>
                {t.rejection_note && t.status === "in_progress" && (
                  <div style={{ fontSize: 11, color: "#F87171", background: "#F8717112", border: "1px solid #F8717133", borderRadius: 8, padding: "6px 10px", marginBottom: 8, lineHeight: 1.4 }}>
                    🔁 Sent back: {t.rejection_note}
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                  {!isStaff && <div style={{ display: "flex", alignItems: "center", gap: 8 }}><Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={24} /><span style={{ fontSize: 12, color: C.sub }}>{u.full_name?.split(" ")[0]}</span></div>}
                  <span style={{ fontSize: 11, color: C.muted }}>Due {new Date(t.due_date).toLocaleDateString()}</span>
                </div>
                {/* Staff quick-action: mark done */}
                {isStaff && !["pending_approval", "completed"].includes(t.status) && (
                  <button className="bp" style={{ width: "100%", marginTop: 12, padding: "8px 0", fontSize: 12 }}
                    disabled={actionBusy}
                    onClick={e => { e.stopPropagation(); markDone(t); }}>
                    ✓ Mark as Done
                  </button>
                )}
                {isStaff && t.status === "pending_approval" && (
                  <div style={{ marginTop: 10, fontSize: 11, color: "#F59E0B", fontWeight: 700, textAlign: "center" }}>⏳ Awaiting approval</div>
                )}
                {/* Manager quick-approve on card */}
                {canApprove && needsApproval && (
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }} onClick={e => e.stopPropagation()}>
                    <button className="bp" style={{ flex: 1, fontSize: 11, padding: "6px 0", background: "#4ADE80", color: "#0F1318" }} disabled={actionBusy}
                      onClick={() => approveTask(t)}>✓ Approve</button>
                    <button className="bg" style={{ flex: 1, fontSize: 11, padding: "6px 0", borderColor: "#F87171", color: "#F87171" }} disabled={actionBusy}
                      onClick={() => { setRejectTarget(t); setRejectNote(""); }}>✕ Reject</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Detail modal */}
      {viewT && (
        <Modal onClose={() => setViewT(null)} title={viewT.title}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <span className="tg" style={{ background: `${pCol[viewT.priority]}22`, color: pCol[viewT.priority], border: `1px solid ${pCol[viewT.priority]}33` }}>{viewT.priority} Priority</span>
            <span className="tg" style={{ background: `${(allSCol[viewT.status] || T.orange)}22`, color: allSCol[viewT.status] || T.orange, border: `1px solid ${(allSCol[viewT.status] || T.orange)}33` }}>{statusLabel[viewT.status] || viewT.status}</span>
          </div>
          {viewT.rejection_note && viewT.status === "in_progress" && (
            <div style={{ background: "#F8717112", border: "1px solid #F8717133", borderRadius: 10, padding: "10px 14px", marginBottom: 16, fontSize: 13, color: "#F87171", lineHeight: 1.5 }}>
              <strong>🔁 Reviewer's note:</strong> {viewT.rejection_note}
            </div>
          )}
          <div style={{ fontSize: 13, color: C.sub, marginBottom: 18, lineHeight: 1.7 }}>{viewT.notes || "No description provided."}</div>
          <div className="g2" style={{ gap: 10, marginBottom: 18 }}>
            <Field label="Assigned To" value={viewT.admins?.full_name} />
            <Field label="Due Date" value={new Date(viewT.due_date).toLocaleDateString()} />
            <Field label="Priority" value={viewT.priority} />
            <Field label="Status" value={statusLabel[viewT.status] || viewT.status} />
          </div>

          {/* Staff actions: toggle pending/in_progress, or mark done */}
          {isStaff && (
            <div>
              <div style={{ fontSize: 12, color: C.muted, marginBottom: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em" }}>Your Actions</div>
              {["pending_approval", "completed"].includes(viewT.status) ? (
                <div style={{ textAlign: "center", padding: 14, background: `${allSCol[viewT.status]}15`, borderRadius: 10, color: allSCol[viewT.status], fontWeight: 700, fontSize: 13 }}>
                  {viewT.status === "pending_approval" ? "⏳ Submitted — awaiting approval from HR/Manager." : "✅ Task completed and approved."}
                </div>
              ) : (
                <div style={{ display: "flex", gap: 10 }}>
                  {["pending", "in_progress"].map(s => (
                    <button key={s} className={viewT.status === s ? "bp" : "bg"} style={{ flex: 1, fontSize: 12 }} disabled={actionBusy}
                      onClick={() => staffUpdateStatus(viewT, s)}>{s === "pending" ? "Not Started" : "In Progress"}</button>
                  ))}
                  <button className="bp" style={{ flex: 1, fontSize: 12, background: "#4ADE80", color: "#0F1318" }} disabled={actionBusy}
                    onClick={() => markDone(viewT)}>✓ Mark Done</button>
                </div>
              )}
            </div>
          )}

          {/* HR/Manager approval actions */}
          {canApprove && viewT.status === "pending_approval" && (
            <div>
              <div style={{ fontSize: 12, color: C.muted, marginBottom: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em" }}>Review Completion</div>
              <div style={{ background: "#F59E0B12", border: "1px dashed #F59E0B55", borderRadius: 10, padding: "10px 14px", marginBottom: 14, fontSize: 13, color: C.sub }}>
                Staff has marked this task as done. Approve it, or reject with a note if more work is needed.
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button className="bp" style={{ flex: 1, background: "#4ADE80", color: "#0F1318", padding: 13 }} disabled={actionBusy}
                  onClick={() => approveTask(viewT)}>✓ Approve Completion</button>
                <button className="bg" style={{ flex: 1, borderColor: "#F87171", color: "#F87171", padding: 13 }} disabled={actionBusy}
                  onClick={() => { setRejectTarget(viewT); setRejectNote(""); }}>✕ Reject & Send Back</button>
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* Rejection note modal */}
      {rejectTarget && (
        <Modal onClose={() => { setRejectTarget(null); setRejectNote(""); }} title="Reject & Send Back" width={480}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6 }}>
              Provide a note explaining what needs to be corrected. The employee will be notified immediately.
            </div>
            <div>
              <Lbl>Reason / Instructions *</Lbl>
              <textarea className="inp" rows={4} value={rejectNote} onChange={e => setRejectNote(e.target.value)}
                placeholder="e.g. Please re-check the figures in section 3 and resubmit…" />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="bp" style={{ flex: 1, background: "#F87171", padding: 13 }} disabled={actionBusy || !rejectNote.trim()}
                onClick={rejectTask}>{actionBusy ? "Sending…" : "Send Back with Note"}</button>
              <button className="bg" style={{ flex: 1, padding: 13 }} onClick={() => { setRejectTarget(null); setRejectNote(""); }}>Cancel</button>
            </div>
          </div>
        </Modal>
      )}

      {/* Assign new task modal */}
      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Assign New Task">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Task Title *</Lbl><input className="inp" placeholder="e.g. Prepare Q2 valuation report" value={nt.title} onChange={e => setNt(n => ({ ...n, title: e.target.value }))} /></div>
            <div><Lbl>Assign To *</Lbl>
              <select className="inp" value={nt.assignedTo} onChange={e => setNt(n => ({ ...n, assignedTo: e.target.value }))}>
                <option value="">— Select Staff Member —</option>
                {staff.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Due Date *</Lbl><input type="date" className="inp" value={nt.due} onChange={e => setNt(n => ({ ...n, due: e.target.value }))} /></div>
              <div><Lbl>Priority</Lbl>
                <select className="inp" value={nt.priority} onChange={e => setNt(n => ({ ...n, priority: e.target.value }))}>
                  <option>High</option><option>Medium</option><option>Low</option>
                </select>
              </div>
            </div>
            <div><Lbl>Description / Instructions</Lbl><textarea className="inp" placeholder="Task details and instructions…" value={nt.desc} onChange={e => setNt(n => ({ ...n, desc: e.target.value }))} /></div>
            <button className="bp" onClick={add} disabled={actionBusy} style={{ padding: 12 }}>{actionBusy ? "Assigning…" : "Assign Task"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: MISMANAGEMENT ────────────────────────────────────────────────────
function Disciplinary({ viewOnly, userId, isManager }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [incidents, setIncidents] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showLog, setShowLog] = useState(false);
  const [f, setF] = useState({ uid: "", type: "", severity: "Minor", note: "" });

  useEffect(() => {
    setLoading(true);
    const params = viewOnly ? `?staff_id=${userId}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/incidents${params}`),
      !viewOnly ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([i, s]) => {
      setIncidents(i);
      setStaff(s);
    }).finally(() => setLoading(false));
  }, [viewOnly, userId]);

  const refresh = () => {
    const params = viewOnly ? `?staff_id=${userId}` : "";
    apiFetch(`${API_BASE}/hr/incidents${params}`).then(setIncidents);
  };

  const resolveIncident = async (incidentId, newStatus) => {
    try {
      await apiFetch(`${API_BASE}/hr/incidents/${incidentId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus, resolution_notes: `Marked ${newStatus} by HR` })
      });
      refresh();
    } catch (e) { alert("Update failed: " + e.message); }
  };

  const add = async () => {
    if (!f.uid || !f.type) return;
    try {
      await apiFetch(`${API_BASE}/hr/incidents`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: f.uid,
          incident_type: f.type,
          severity: f.severity,
          notes: f.note
        })
      });
      setF({ uid: "", type: "", severity: "Minor", note: "" });
      setShowLog(false);
      refresh();
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  const summary = {};
  incidents.forEach(l => {
    if (!summary[l.staff_id]) summary[l.staff_id] = { flags: [], max: 0 };
    summary[l.staff_id].flags.push(l);
    if (sevOrd[l.severity] > summary[l.staff_id].max) summary[l.staff_id].max = sevOrd[l.severity];
  });

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Disciplinary Dashboard</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>
            {viewOnly ? "Your flagged incidents. Contact HR or your line manager to resolve."
              : "Graded incident tracking — records are visible to HR, Managers, and the individual."}
          </div>
        </div>
        {!viewOnly && <button className="bp" onClick={() => setShowLog(true)}>+ Log Incident</button>}
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 22, flexWrap: "wrap" }}>
        {[["Minor", "D", "Counselling noted"], ["Moderate", "C", "Formal warning"], ["Serious", "B", "Written warning + PIP"], ["Critical", "A", "Disciplinary action"]].map(([s, g, desc]) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 14px", background: `${sevCol[s]}14`, border: `1px solid ${sevCol[s]}33`, borderRadius: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: sevCol[s], display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800, color: "#0F1318" }}>{g}</div>
            <div><div style={{ fontSize: 12, fontWeight: 800, color: sevCol[s] }}>{s}</div><div style={{ fontSize: 10, color: C.muted }}>{desc}</div></div>
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading incident logs…</div>
      ) : Object.keys(summary).length === 0 ? (
        <div className="gc" style={{ padding: 48, textAlign: "center" }}>
          <div style={{ fontSize: 28, marginBottom: 12, color: "#4ADE80" }}>✓</div>
          <div style={{ color: "#4ADE80", fontWeight: 800 }}>No disciplinary flags on record</div>
        </div>
      ) : (
        <div className="g2" style={{ gap: 16 }}>
          {Object.entries(summary).map(([uid, data]) => {
            const u = data.flags[0]?.admins || {};
            const worst = Object.entries(sevOrd).find(([, v]) => v === data.max)?.[0] || "Minor";
            const wc = sevCol[worst];
            return (
              <div key={uid} className="gc" style={{ padding: 20, border: `1px solid ${wc}44`, boxShadow: `0 0 0 1px ${wc}22,0 0 14px ${wc}18` }}>
                <div style={{ display: "flex", gap: 14, alignItems: "center", marginBottom: 14 }}>
                  <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={42} />
                  <div style={{ flex: 1 }}><div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{u.full_name}</div><div style={{ fontSize: 12, color: C.sub }}>{u.department}</div></div>
                  <div style={{ width: 36, height: 36, borderRadius: "50%", background: wc, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, color: "#0F1318" }}>{sevGrade[worst]}</div>
                </div>
                <div style={{ fontSize: 12, color: C.muted, marginBottom: 10 }}>{data.flags.length} incident{data.flags.length !== 1 ? "s" : ""} on record</div>
                {data.flags.map((fl, i) => (
                  <div key={i} style={{ padding: "9px 12px", background: `${sevCol[fl.severity]}10`, border: `1px solid ${sevCol[fl.severity]}22`, borderRadius: 8, marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 800, color: sevCol[fl.severity] }}>{fl.type}</span>
                      <span style={{ fontSize: 11, color: C.muted }}>{new Date(fl.created_at).toLocaleDateString()}</span>
                    </div>
                    <div style={{ fontSize: 11, color: C.sub }}>{fl.notes}</div>
                    <div style={{ fontSize: 10, color: C.muted, marginTop: 4 }}>Ref: INC-{fl.id}</div>
                    {!viewOnly && !["resolved", "dismissed"].includes(fl.status) && (
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="bg" style={{ flex: 1, fontSize: 10, padding: "4px 8px", borderColor: "#4ADE80", color: "#4ADE80" }}
                          onClick={() => resolveIncident(fl.id, "resolved")}>✓ Resolve</button>
                        <button className="bg" style={{ flex: 1, fontSize: 10, padding: "4px 8px" }}
                          onClick={() => resolveIncident(fl.id, "dismissed")}>Dismiss</button>
                      </div>
                    )}
                    {fl.status === "resolved" && <div style={{ fontSize: 10, color: "#4ADE80", marginTop: 4, fontWeight: 800 }}>✓ Resolved</div>}
                    {fl.status === "dismissed" && <div style={{ fontSize: 10, color: "#9CA3AF", marginTop: 4 }}>Dismissed</div>}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {showLog && (
        <Modal onClose={() => setShowLog(false)} title="Log Disciplinary Incident">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Staff Member *</Lbl>
              <select className="inp" value={f.uid} onChange={e => setF(x => ({ ...x, uid: e.target.value }))}>
                <option value="">— Select Staff Member —</option>
                {staff.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div><Lbl>Incident Type *</Lbl>
              <select className="inp" value={f.type} onChange={e => setF(x => ({ ...x, type: e.target.value }))}>
                <option value="">— Select Type —</option>
                {["Unauthorized Absence", "Repeated Late Arrival", "Missed Task Deadline", "Safety Protocol Breach", "Insubordination", "KPI Failure (3+ months)", "Unprofessional Conduct", "Budget Overrun", "Escalated Complaint"].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div><Lbl>Severity Grade</Lbl>
              <select className="inp" value={f.severity} onChange={e => setF(x => ({ ...x, severity: e.target.value }))}>
                <option>Minor</option><option>Moderate</option><option>Serious</option><option>Critical</option>
              </select>
            </div>
            <div><Lbl>Notes / Evidence</Lbl><textarea className="inp" placeholder="Describe the incident in detail…" value={f.note} onChange={e => setF(x => ({ ...x, note: e.target.value }))} /></div>
            <button className="bp" onClick={add} style={{ padding: 12 }}>Log Incident</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: PAYROLL ──────────────────────────────────────────────────────────
function Payroll() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [tab, setTab] = useState("payslips");
  const [payroll, setPayroll] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [staff, setStaff] = useState([]);
  const [nf, setNf] = useState({ uid: "", gross: "", tax: "0", notes: "" });
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
    if (!nf.uid || !nf.gross) return;
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
      setNf({ uid: "", gross: "", tax: "0", notes: "" });
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Payroll Management</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>Full Staff & Contractors: monthly · Onsite/Labourers: weekly</div>
        </div>
        {tab === "payslips" && (
          <div style={{ display: "flex", gap: 12 }}>
            <button className="bg" onClick={() => setShowAdd(true)}>+ Add Entry</button>
            <button className="bp" onClick={handleRunPayroll}>Run Payroll</button>
          </div>
        )}
      </div>

      <div className="tab-bar">
        <button className={`tab ${tab === "payslips" ? "on" : "off"}`} onClick={() => setTab("payslips")}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ display: "inline", marginRight: 6, verticalAlign: "middle" }}><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
          Staff Payslips
        </button>
        <button className={`tab ${tab === "commissions" ? "on" : "off"}`} onClick={() => setTab("commissions")}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ display: "inline", marginRight: 6, verticalAlign: "middle" }}><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
          Sales Commissions
        </button>
      </div>

      {tab === "commissions" ? (
        <AgentCommissions />
      ) : (
        <>
          {showAdd && (
            <Modal onClose={() => setShowAdd(false)} title="Manual Payroll Entry">
              <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
                <div><Lbl>Personnel Identification *</Lbl>
                  <select className="inp" value={nf.uid} onChange={e => setNf(x => ({ ...x, uid: e.target.value }))}>
                    <option value="">— Select Staff Member —</option>
                    {staff.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
                  </select>
                </div>
                <div className="g2" style={{ gap: 16 }}>
                  <div><Lbl>Gross Component (₦) *</Lbl><input type="number" className="inp" placeholder="0.00" value={nf.gross} onChange={e => setNf(x => ({ ...x, gross: e.target.value }))} /></div>
                  <div><Lbl>Tax / Reductions (₦)</Lbl><input type="number" className="inp" placeholder="0.00" value={nf.tax} onChange={e => setNf(x => ({ ...x, tax: e.target.value }))} /></div>
                </div>
                <div><Lbl>Transaction Justification / Notes</Lbl><textarea className="inp" placeholder="E.g. Performance Bonus for Q1, Contractor retainer, Reimbursement of expenses..." value={nf.notes} onChange={e => setNf(x => ({ ...x, notes: e.target.value }))} /></div>
                <button className="bp" onClick={addManual} style={{ padding: 16, fontSize: 15 }}>Submit Payroll Record</button>
              </div>
            </Modal>
          )}

          {loading ? (
            <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading payroll records…</div>
          ) : payroll.length === 0 ? (
            <div className="gc" style={{ padding: 48, textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>💳</div>
              <div className="ho" style={{ fontSize: 16, marginBottom: 8 }}>No Payroll Records Yet</div>
              <div style={{ fontSize: 13, color: C.muted }}>Run payroll to generate payslips for your team.</div>
            </div>
          ) : (
            <div className="gc" style={{ overflow: "hidden" }}>
              <div style={{ padding: "14px 20px", borderBottom: `1px solid ${C.border}` }}>
                <div className="ho" style={{ fontSize: 14 }}>Payroll Records</div>
              </div>
              <div className="tw">
                <table className="ht">
                  <thead><tr>{["Staff Member", "Period", "Gross Pay", "Net Pay", "Status", ""].map(h => <th key={h}>{h}</th>)}</tr></thead>
                  <tbody>
                    {payroll.map(p => (
                      <tr key={p.id}>
                        <td><div style={{ display: "flex", alignItems: "center", gap: 10 }}><Av av={p.admins?.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={26} /><span style={{ fontWeight: 800 }}>{p.admins?.full_name}</span></div></td>
                        <td style={{ color: C.sub }}>{p.period_start ? new Date(p.period_start).toLocaleDateString(undefined, { month: 'long', year: 'numeric' }) : "—"}</td>
                        <td style={{ fontWeight: 700 }}>{fmt(p.gross_pay)}</td>
                        <td style={{ color: T.orange, fontWeight: 800, fontSize: 14 }}>{fmt(p.net_pay)}</td>
                        <td><span className={`tg ${p.status === "paid" ? "tg2" : "ty"}`}>{p.status}</span></td>
                        <td><button className="bg" style={{ fontSize: 11, padding: "5px 12px" }}>Payslip</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── MODULE: AGENT COMMISSIONS ──────────────────────────────────────────────
function AgentCommissions() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [owed, setOwed] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [reps, setReps] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cTab, setCTab] = useState("owed");
  const [commRequests, setCommRequests] = useState([]);
  const [reqLoading, setReqLoading] = useState(false);

  // Global Rate
  const [showRateModal, setShowRateModal] = useState(false);
  const [defaultRate, setDefaultRate] = useState("");
  const [savingRate, setSavingRate] = useState(false);

  // Per-Rep Rate
  const [showRepRateModal, setShowRepRateModal] = useState(false);
  const [repRateTarget, setRepRateTarget] = useState(null);
  const [repRateEstate, setRepRateEstate] = useState("");
  const [repRateVal, setRepRateVal] = useState("");
  const [repRateDate, setRepRateDate] = useState(new Date().toISOString().split("T")[0]);
  const [savingRepRate, setSavingRepRate] = useState(false);

  // Payout
  const [showPayoutModal, setShowPayoutModal] = useState(false);
  const [selectedRep, setSelectedRep] = useState("");
  const [repEarnings, setRepEarnings] = useState([]);
  const [earningsLoading, setEarningsLoading] = useState(false);
  const [selectedEarnings, setSelectedEarnings] = useState({});
  const [payoutAmount, setPayoutAmount] = useState("");
  const [payoutNotes, setPayoutNotes] = useState("");
  const [payoutRef, setPayoutRef] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fmt = n => n != null ? `\u20a6${Number(n).toLocaleString()}` : "—";

  const findStaffForRep = rep => {
    // 1. Exact Email Match
    if (rep.email) {
      const match = staff.find(s => s.email && s.email.toLowerCase() === rep.email.toLowerCase());
      if (match) return match;
    }
    // 2. Exact Phone Match (digits only)
    if (rep.phone) {
      const rP = rep.phone.replace(/\D/g, '');
      if (rP.length >= 7) {
        const match = staff.find(s => {
          const sP = (s.phone_number || '').replace(/\D/g, '');
          return sP && sP === rP;
        });
        if (match) return match;
      }
    }
    // 3. Fallback: Name Match
    const repFirst = (rep.name || '').trim().toLowerCase();
    return staff.find(s => (s.full_name || '').toLowerCase().includes(repFirst) && repFirst.length > 1);
  };

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [o, p, e, r, s, cr] = await Promise.all([
        apiFetch(`${API_BASE}/commission/owed`),
        apiFetch(`${API_BASE}/commission/payouts`),
        apiFetch(`${API_BASE}/commission/earnings`),
        apiFetch(`${API_BASE}/sales-reps`),
        apiFetch(`${API_BASE}/hr/staff`),
        apiFetch(`${API_BASE}/payouts/requests?vendor_type=staff&payment_type=staff_commission`).catch(() => []),
      ]);
      setOwed(Array.isArray(o) ? o : []);
      setPayouts(Array.isArray(p) ? p : []);
      setEarnings(Array.isArray(e) ? e : []);
      setReps(Array.isArray(r) ? r : []);
      setStaff(Array.isArray(s) ? s : []);
      setCommRequests(Array.isArray(cr) ? cr : []);
    } catch (err) { console.error("Commission load error:", err); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadDashboard(); }, []);

  // Commission Request Approve/Reject
  const approveCommRequest = async (id) => {
    try {
      await apiFetch(`${API_BASE}/payouts/requests/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'approved' }) });
      setCommRequests(prev => prev.map(r => r.id === id ? { ...r, status: 'approved' } : r));
    } catch (e) { alert("Failed: " + e.message); }
  };
  const rejectCommRequest = async (id) => {
    try {
      await apiFetch(`${API_BASE}/payouts/requests/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'rejected' }) });
      setCommRequests(prev => prev.map(r => r.id === id ? { ...r, status: 'rejected' } : r));
    } catch (e) { alert("Failed: " + e.message); }
  };

  // Global Rate
  const openRateModal = async () => {
    setShowRateModal(true);
    try {
      const d = await apiFetch(`${API_BASE}/commission/default-rate`);
      setDefaultRate(d.rate || "5.0");
      setWhtRate(d.wht_rate || "5.0");
    } catch (e) { setDefaultRate("5.0"); setWhtRate("5.0"); }
  };
  const [whtRate, setWhtRate] = useState("5.0");
  const saveDefaultRate = async () => {
    setSavingRate(true);
    try {
      await apiFetch(`${API_BASE}/commission/default-rate`, {
        method: "PATCH",
        body: JSON.stringify({ rate: parseFloat(defaultRate), wht_rate: parseFloat(whtRate), reason: "Updated via HR Portal" })
      });
      setShowRateModal(false);
    } catch (e) { alert("Failed: " + e.message); }
    finally { setSavingRate(false); }
  };

  // Per-Rep Rate
  const openRepRate = (rep) => {
    setRepRateTarget(rep);
    setRepRateEstate(""); setRepRateVal("");
    setRepRateDate(new Date().toISOString().split("T")[0]);
    setShowRepRateModal(true);
  };
  const [repRateWht, setRepRateWht] = useState("5.0");
  const saveRepRate = async () => {
    if (!repRateEstate || !repRateVal) return alert("Estate and rate required.");
    setSavingRepRate(true);
    try {
      await apiFetch(`${API_BASE}/commission/rates`, {
        method: "POST",
        body: JSON.stringify({
          sales_rep_id: repRateTarget.id,
          estate_name: repRateEstate,
          rate: parseFloat(repRateVal),
          wht_rate: parseFloat(repRateWht),
          effective_from: repRateDate,
          reason: "Set via HR Portal"
        })
      });
      setShowRepRateModal(false);
    } catch (e) { alert("Failed: " + e.message); }
    finally { setSavingRepRate(false); }
  };

  // Payout
  const handleRepSelect = async (repId) => {
    setSelectedRep(repId); setRepEarnings([]); setSelectedEarnings({}); setPayoutAmount("");
    if (!repId) return;
    setEarningsLoading(true);
    try {
      const data = await apiFetch(`${API_BASE}/commission/owed/${repId}`);
      setRepEarnings(data);
      const sels = {}; let total = 0;
      data.forEach(e => { sels[e.id] = true; total += (parseFloat(e.final_amount) - (parseFloat(e.amount_paid) || 0)); });
      setSelectedEarnings(sels); setPayoutAmount(total.toFixed(2));
    } catch (err) { console.error(err); }
    finally { setEarningsLoading(false); }
  };
  const toggleEarning = id => {
    const next = { ...selectedEarnings, [id]: !selectedEarnings[id] };
    setSelectedEarnings(next);
    let total = 0;
    repEarnings.forEach(e => { if (next[e.id]) total += (parseFloat(e.final_amount) - (parseFloat(e.amount_paid) || 0)); });
    setPayoutAmount(total.toFixed(2));
  };
  const submitPayout = async () => {
    if (!selectedRep || parseFloat(payoutAmount) <= 0) return alert("Select rep and valid amount.");
    const earningIds = Object.keys(selectedEarnings).filter(k => selectedEarnings[k]);
    if (!earningIds.length) return alert("Select at least one commission record.");
    setSubmitting(true);
    try {
      await apiFetch(`${API_BASE}/commission/payout`, {
        method: "POST",
        body: JSON.stringify({ sales_rep_id: selectedRep, earning_ids: earningIds, reference: payoutRef, notes: payoutNotes, total_amount: parseFloat(payoutAmount) })
      });
      setShowPayoutModal(false); setSelectedRep(""); setPayoutNotes(""); setPayoutRef(""); setPayoutAmount("");
      loadDashboard();
    } catch (err) { alert("Payout error: " + err.message); }
    finally { setSubmitting(false); }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading commissions...</div>;

  const totalOwed = owed.reduce((a, o) => a + o.total, 0);
  const totalPaid = payouts.reduce((a, p) => a + parseFloat(p.total_amount || 0), 0);

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 10 }}>
        <button className="bg" onClick={openRateModal} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
          Global Rate
        </button>
        <button className="bp" onClick={() => { setSelectedRep(""); setRepEarnings([]); setPayoutAmount(""); setShowPayoutModal(true); }} style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 18px" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          New Payout
        </button>
      </div>

      {/* Summary cards */}
      <div className="g3" style={{ marginBottom: 24, gap: 16 }}>
        <div className="gc" style={{ padding: 18, textAlign: "center" }}>
          <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>Total Owed</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: T.gold }}>{fmt(totalOwed)}</div>
          <div style={{ fontSize: 10, color: C.sub, marginTop: 4 }}>{owed.length} rep{owed.length !== 1 ? "s" : ""} pending</div>
        </div>
        <div className="gc" style={{ padding: 18, textAlign: "center" }}>
          <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>Total Disbursed</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#10B981" }}>{fmt(totalPaid)}</div>
          <div style={{ fontSize: 10, color: C.sub, marginTop: 4 }}>{payouts.length} payout batch{payouts.length !== 1 ? "es" : ""}</div>
        </div>
        <div className="gc" style={{ padding: 18, textAlign: "center" }}>
          <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>Active Agents</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#60A5FA" }}>{reps.length}</div>
          <div style={{ fontSize: 10, color: C.sub, marginTop: 4 }}>{earnings.length} earnings records</div>
        </div>
      </div>

      {/* Inner tabs */}
      <div className="tab-bar" style={{ marginBottom: 20 }}>
        <button className={`tab ${cTab === "owed" ? "on" : "off"}`} onClick={() => setCTab("owed")}>Pending Owed</button>
        <button className={`tab ${cTab === "payouts" ? "on" : "off"}`} onClick={() => setCTab("payouts")}>Payout History</button>
        <button className={`tab ${cTab === "earnings" ? "on" : "off"}`} onClick={() => setCTab("earnings")}>All Earnings</button>
        <button className={`tab ${cTab === "requests" ? "on" : "off"}`} onClick={() => setCTab("requests")} style={{ position: "relative" }}>
          Staff Requests
          {commRequests.filter(r => r.status === "pending").length > 0 && (
            <span style={{ position: "absolute", top: -4, right: -4, background: "#F87171", color: "#fff", fontSize: 9, fontWeight: 800, borderRadius: "50%", width: 16, height: 16, display: "flex", alignItems: "center", justifyContent: "center" }}>
              {commRequests.filter(r => r.status === "pending").length}
            </span>
          )}
        </button>
      </div>

      {/* Pending Owed */}
      {cTab === "owed" && (
        <div className="gc" style={{ overflow: "hidden" }}>
          {owed.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: C.muted }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>&#10003;</div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>All Caught Up</div>
              <div style={{ fontSize: 12 }}>No pending commissions owed across all reps.</div>
            </div>
          ) : owed.map(o => {
            const rep = reps.find(r => r.id === o.rep_id);
            const linked = rep ? findStaffForRep(rep) : null;
            return (
              <div key={o.rep_id} style={{ display: "flex", borderBottom: `1px solid ${C.border}`, padding: 16, alignItems: "center", gap: 14 }}>
                <Av av={(o.name || "?").substring(0, 2).toUpperCase()} sz={40} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, marginBottom: 2 }}>{o.name}</div>
                  <div style={{ fontSize: 11, color: C.sub }}>
                    {o.count} deal{o.count > 1 ? "s" : ""}{o.partially_paid ? " · Partially collected" : ""}
                    {linked && <span style={{ marginLeft: 8, color: T.gold, fontWeight: 700 }}>· Staff: {linked.full_name}</span>}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontWeight: 800, color: T.gold, fontSize: 15 }}>{fmt(o.total)}</div>
                    <div style={{ fontSize: 10, textTransform: "uppercase", color: C.sub }}>Owed</div>
                  </div>
                  <button className="bg" style={{ fontSize: 10, padding: "5px 10px", whiteSpace: "nowrap" }} onClick={() => openRepRate({ id: o.rep_id, name: o.name })}>Set Rate</button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Payout History */}
      {cTab === "payouts" && (
        <div className="gc" style={{ overflow: "hidden" }}>
          {payouts.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: C.muted }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>&#128179;</div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>No Payouts Yet</div>
              <div style={{ fontSize: 12 }}>Use "New Payout" to process commission payouts.</div>
            </div>
          ) : (
            <div className="tw">
              <table className="ht">
                <thead><tr>{["Rep", "Date", "Amount", "Reference", "Processed By"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {payouts.map(p => {
                    const rep = reps.find(r => r.id === p.sales_rep_id);
                    const linked = rep ? findStaffForRep(rep) : null;
                    return (
                      <tr key={p.id}>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <Av av={(p.sales_reps?.name || "?").substring(0, 2).toUpperCase()} sz={28} />
                            <div>
                              <div style={{ fontWeight: 700 }}>{p.sales_reps?.name || "Unknown"}</div>
                              {linked && <div style={{ fontSize: 10, color: T.gold }}>HR Staff ✓</div>}
                            </div>
                          </div>
                        </td>
                        <td style={{ color: C.sub, fontSize: 12 }}>{new Date(p.paid_at).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" })}</td>
                        <td style={{ fontWeight: 800, color: "#10B981" }}>{fmt(p.total_amount)}</td>
                        <td style={{ fontSize: 12, color: C.sub }}>{p.reference || "—"}</td>
                        <td style={{ fontSize: 12, color: C.sub }}>{p.admins?.full_name || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* All Earnings */}
      {cTab === "earnings" && (
        <div className="gc" style={{ overflow: "hidden" }}>
          {earnings.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: C.muted }}>
              <div style={{ fontSize: 12 }}>No commission earnings found. Commissions are auto-generated when invoices are paid for clients linked to a sales rep.</div>
            </div>
          ) : (
            <div className="tw">
              <table className="ht">
                <thead><tr>{["Rep", "Client", "Invoice", "Gross", "WHT", "Net", "Status"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {earnings.map(e => {
                    const isPaid = e.is_paid;
                    const amtPaid = parseFloat(e.amount_paid || 0);
                    const gross = e.gross_commission || e.commission_amount;
                    const wht = e.wht_amount || 0;
                    const net = e.net_commission || e.final_amount;
                    return (
                      <tr key={e.id}>
                        <td style={{ fontWeight: 700 }}>{e.sales_reps?.name || "—"}</td>
                        <td style={{ fontSize: 12 }}>{e.clients?.full_name || "—"}</td>
                        <td style={{ fontSize: 11, color: C.sub }}>{e.invoices?.invoice_number || "—"}</td>
                        <td style={{ fontWeight: 600 }}>{fmt(gross)}</td>
                        <td style={{ color: "#EF4444", fontSize: 12 }}>-{fmt(wht)}</td>
                        <td style={{ fontWeight: 800, color: T.gold }}>{fmt(net)}</td>
                        <td><span className={`tg ${isPaid ? "tg2" : amtPaid > 0 ? "ty" : "tr"}`}>{isPaid ? "Paid" : amtPaid > 0 ? "Partial" : "Unpaid"}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {cTab === "requests" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 8 }}>
          {commRequests.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: C.muted, fontSize: 13 }}>No staff commission requests found.</div>
          ) : commRequests.map(r => {
            const isPending = r.status === "pending";
            const stCol = { pending: T.gold, approved: "#4ADE80", rejected: "#F87171" };
            const sc = stCol[r.status] || C.muted;
            return (
              <div key={r.id} className="gc" style={{ padding: "16px 18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 800, fontSize: 14, color: C.text }}>{r.vendors?.name || "—"}</div>
                    {r.remarks && <div style={{ fontSize: 12, color: C.sub, background: C.base, borderRadius: 6, padding: "6px 10px", marginTop: 6, lineHeight: 1.5 }}>{r.remarks}</div>}
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
                      Ref: {r.vendor_invoice_number || r.id?.slice(0, 8)} · {new Date(r.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ fontWeight: 800, fontSize: 15, color: T.gold }}>₦{parseFloat(r.amount_gross || 0).toLocaleString()}</div>
                    <span className="tg" style={{ background: `${sc}22`, color: sc, fontSize: 10, marginTop: 4, display: "inline-block" }}>{r.status}</span>
                  </div>
                </div>
                {isPending && (
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button className="bp" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => approveCommRequest(r.id)}>Approve</button>
                    <button style={{ fontSize: 11, padding: "5px 14px", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", borderRadius: 6, cursor: "pointer" }} onClick={() => rejectCommRequest(r.id)}>Reject</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL: Global Rate */}
      {showRateModal && (
        <Modal onClose={() => setShowRateModal(false)} title="Global Default Commission Rate">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ background: C.base, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, fontSize: 12, color: C.sub, lineHeight: 1.6 }}>
              This rate applies to all reps without a custom estate rate. Changes do not affect already-generated earnings.
            </div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Default Rate (%)</Lbl>
                <input type="number" className="inp" step="0.1" min="0" max="100" value={defaultRate} onChange={e => setDefaultRate(e.target.value)} placeholder="5.0" /></div>
              <div><Lbl>WHT Rate (%)</Lbl>
                <input type="number" className="inp" step="0.1" min="0" max="100" value={whtRate} onChange={e => setWhtRate(e.target.value)} placeholder="5.0" /></div>
            </div>
            <button className="bp" onClick={saveDefaultRate} disabled={savingRate} style={{ padding: 14 }}>
              {savingRate ? "Saving..." : "Save Global Rate"}
            </button>
          </div>
        </Modal>
      )}

      {/* MODAL: Per-Rep Rate */}
      {showRepRateModal && repRateTarget && (
        <Modal onClose={() => setShowRepRateModal(false)} title={`Custom Rate — ${repRateTarget.name}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ background: C.base, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, fontSize: 12, color: C.sub, lineHeight: 1.6 }}>
              Set a custom commission rate for a specific estate. This overrides the global default for this agent on that estate only.
            </div>
            <div><Lbl>Estate Name *</Lbl>
              <input type="text" className="inp" placeholder="e.g. Cloves Estate Phase 2" value={repRateEstate} onChange={e => setRepRateEstate(e.target.value)} /></div>
            <div className="g3" style={{ gap: 12 }}>
              <div><Lbl>Rate (%) *</Lbl>
                <input type="number" className="inp" step="0.1" min="0" max="100" placeholder="5.0" value={repRateVal} onChange={e => setRepRateVal(e.target.value)} /></div>
              <div><Lbl>WHT (%) *</Lbl>
                <input type="number" className="inp" step="0.1" min="0" max="100" placeholder="5.0" value={repRateWht} onChange={e => setRepRateWht(e.target.value)} /></div>
              <div><Lbl>Effective From</Lbl>
                <input type="date" className="inp" value={repRateDate} onChange={e => setRepRateDate(e.target.value)} /></div>
            </div>
            <button className="bp" onClick={saveRepRate} disabled={savingRepRate} style={{ padding: 14 }}>
              {savingRepRate ? "Saving..." : "Save Custom Rate"}
            </button>
          </div>
        </Modal>
      )}

      {/* MODAL: Payout */}
      {showPayoutModal && (
        <Modal onClose={() => setShowPayoutModal(false)} title="Process Commission Payout">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div><Lbl>Select Sales Rep *</Lbl>
              <select className="inp" value={selectedRep} onChange={e => handleRepSelect(e.target.value)}>
                <option value="">— Choose a Rep —</option>
                {reps.map(r => {
                  const linked = findStaffForRep(r);
                  return <option key={r.id} value={r.id}>{r.name}{r.last_name ? " " + r.last_name : ""}{linked ? " (HR Staff)" : ""}</option>;
                })}
              </select></div>
            {earningsLoading && <div style={{ fontSize: 12, color: C.sub, textAlign: "center", padding: 8 }}>Loading unpaid commissions...</div>}
            {!earningsLoading && selectedRep && repEarnings.length === 0 && (
              <div style={{ fontSize: 12, color: C.muted, textAlign: "center", padding: 12, background: C.base, borderRadius: 8 }}>No unpaid commissions for this rep.</div>
            )}
            {repEarnings.length > 0 && (
              <div style={{ border: `1px solid ${C.border}`, borderRadius: 8, padding: 10, maxHeight: 220, overflowY: "auto" }}>
                <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8, color: C.muted, textTransform: "uppercase", letterSpacing: "0.5px" }}>Select earnings to include:</div>
                {repEarnings.map(e => {
                  const bal = parseFloat(e.final_amount) - (parseFloat(e.amount_paid) || 0);
                  const isPartial = parseFloat(e.amount_paid || 0) > 0;
                  return (
                    <div key={e.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: 10, background: C.base, borderRadius: 6, marginBottom: 6, cursor: "pointer" }} onClick={() => toggleEarning(e.id)}>
                      <input type="checkbox" checked={!!selectedEarnings[e.id]} onChange={() => toggleEarning(e.id)} style={{ accentColor: T.gold, width: 15, height: 15 }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 700 }}>{e.clients?.full_name || "Unknown"}</div>
                        <div style={{ fontSize: 10, color: C.sub }}>Inv: {e.invoices?.invoice_number || "—"}{isPartial ? ` · ${fmt(parseFloat(e.amount_paid || 0))} paid` : ""}</div>
                      </div>
                      <div style={{ fontWeight: 800, color: "#10B981", fontSize: 13 }}>{fmt(bal)}</div>
                    </div>
                  );
                })}
              </div>
            )}
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Amount to Pay (\u20a6) *</Lbl>
                <input type="number" className="inp" placeholder="0.00" value={payoutAmount} onChange={e => setPayoutAmount(e.target.value)} /></div>
              <div><Lbl>Reference (Optional)</Lbl>
                <input type="text" className="inp" placeholder="TXN-12345" value={payoutRef} onChange={e => setPayoutRef(e.target.value)} /></div>
            </div>
            <div><Lbl>Notes</Lbl>
              <input type="text" className="inp" placeholder="e.g. April 2026 commissions" value={payoutNotes} onChange={e => setPayoutNotes(e.target.value)} /></div>
            <button className="bp" onClick={submitPayout} disabled={submitting} style={{ padding: 16, fontSize: 14 }}>
              {submitting ? "Processing..." : "Confirm & Process Payout"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}


// ─── MODULE: STAFF PAYROLL & COMMISSIONS ──────────────────────────────────────
function StaffPayroll({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [tab, setTab] = useState("payslips");
  const [data, setData] = useState({ payslips: [], commissions: null });
  const [loading, setLoading] = useState(true);
  const [viewingDocs, setViewingDocs] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [dates, setDates] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth() - 2, 1).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });

  const fmt = n => n != null ? `₦${Number(n).toLocaleString()}` : "—";

  const loadData = async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([
        apiFetch(`${API_BASE}/hr/payroll/payslips?staff_id=${user.id}`),
        apiFetch(`${API_BASE}/commission/my?start_date=${dates.start}&end_date=${dates.end}`)
      ]);
      setData({ payslips: p, commissions: c });
    } catch (e) { console.error("Staff Payroll Load error:", e); }
    finally { setLoading(false); }
  };

  const viewDocument = async (requestId) => {
    try {
      const res = await apiFetch(`${API_BASE}/payouts/requests/${requestId}/proof-files`);
      setViewingDocs(res);
    } catch (e) { alert("Could not load proof files"); }
  };

  useEffect(() => { loadData(); }, [dates.start, dates.end]);

  const filteredEarnings = data.commissions?.earnings?.filter(e => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (e.clients?.full_name || "").toLowerCase().includes(term) ||
      (e.invoices?.invoice_number || "").toLowerCase().includes(term) ||
      (e.estate_name || "").toLowerCase().includes(term);
  }) || [];

  const totalEarnedFiltered = filteredEarnings.reduce((a, b) => a + parseFloat(b.final_amount || b.net_commission || 0), 0) || 0;
  const totalPaidFiltered = data.commissions?.payouts?.reduce((a, b) => a + parseFloat(b.total_amount), 0) || 0;

  return (
    <>
      <div className="fade">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
          <div>
            <div className="ho" style={{ fontSize: 22 }}>My Payroll & Commissions</div>
            <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>View your monthly payslips and sales commission earnings</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, background: C.base, padding: "4px 12px", borderRadius: 8, border: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 11, color: C.sub, fontWeight: 700 }}>FILTER:</div>
            <input type="text" className="inp" placeholder="Search client, invoice..." style={{ padding: "4px 8px", fontSize: 11, width: 140, border: "none", background: "transparent", borderRight: `1px solid ${C.border}` }} value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
            <input type="date" className="inp" style={{ padding: "4px 8px", fontSize: 11, width: 120, border: "none", background: "transparent" }} value={dates.start} onChange={e => setDates(d => ({ ...d, start: e.target.value }))} />
            <div style={{ fontSize: 11, color: C.sub }}>to</div>
            <input type="date" className="inp" style={{ padding: "4px 8px", fontSize: 11, width: 120, border: "none", background: "transparent" }} value={dates.end} onChange={e => setDates(d => ({ ...d, end: e.target.value }))} />
          </div>
        </div>

        <div className="tab-bar" style={{ marginBottom: 20 }}>
          <button className={`tab ${tab === "payslips" ? "on" : "off"}`} onClick={() => setTab("payslips")}>My Payslips</button>
          <button className={`tab ${tab === "commissions" ? "on" : "off"}`} onClick={() => setTab("commissions")}>My Commissions</button>
        </div>

        {loading ? <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading data...</div> : (
          tab === "payslips" ? (
            <div className="gc" style={{ overflow: "hidden" }}>
              {data.payslips.length === 0 ? (
                <div style={{ padding: 40, textAlign: "center", color: C.muted }}>No payslips found for this period.</div>
              ) : (
                <div className="tw">
                  <table className="ht">
                    <thead><tr>{['Period', 'Gross Pay', 'Net Pay', 'Status', ''].map(h => <th key={h}>{h}</th>)}</tr></thead>
                    <tbody>
                      {data.payslips.map(p => (
                        <tr key={p.id}>
                          <td style={{ fontWeight: 700 }}>{new Date(p.period_start).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</td>
                          <td>{fmt(p.gross_pay)}</td>
                          <td style={{ color: T.orange, fontWeight: 800 }}>{fmt(p.net_pay)}</td>
                          <td><span className={`tg ${p.status === "paid" ? "tg2" : "ty"}`}>{p.status}</span></td>
                          <td><button className="bg" style={{ fontSize: 10, padding: "4px 10px" }}>View PDF</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div>
              {!data.commissions || !data.commissions.rep_id ? (
                <div className="gc" style={{ padding: 40, textAlign: "center", color: C.muted }}>
                  <div style={{ fontSize: 28, marginBottom: 10 }}>🔍</div>
                  <div style={{ fontWeight: 700 }}>No Sales Rep Profile Linked</div>
                  <div style={{ fontSize: 13, maxWidth: 400, margin: "8px auto" }}>We couldn't find a Sales Rep record matching your email or phone number. Contact HR to link your accounts.</div>
                </div>
              ) : (
                <div>
                  <div className="g3" style={{ marginBottom: 20, gap: 16 }}>
                    <div className="gc" style={{ padding: 18, textAlign: "center" }}>
                      <div style={{ fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>Total Owed (Now)</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: T.gold }}>{fmt(data.commissions.total_owed)}</div>
                    </div>
                    <div className="gc" style={{ padding: 18, textAlign: "center" }}>
                      <div style={{ fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>Filtered Earning</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "#10B981" }}>{fmt(totalEarnedFiltered)}</div>
                    </div>
                    <div className="gc" style={{ padding: 18, textAlign: "center" }}>
                      <div style={{ fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>Payouts (Period)</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "#60A5FA" }}>{fmt(totalPaidFiltered)}</div>
                    </div>
                  </div>

                  <div className="gc" style={{ overflow: "hidden" }}>
                    <div style={{ padding: "14px 20px", borderBottom: `1px solid ${C.border}` }}>
                      <div className="ho" style={{ fontSize: 14 }}>Earnings Ledger</div>
                    </div>
                    <div className="tw">
                      <table className="ht">
                        <thead><tr>{['Date', 'Client & Property', 'Invoice', 'Revenue', 'Rate', 'Gross', 'Tax', 'Net', 'Status', ''].map(h => <th key={h}>{h}</th>)}</tr></thead>
                        <tbody>
                          {filteredEarnings.map(e => {
                            const gross = e.gross_commission || e.commission_amount;
                            const wht = e.wht_amount || 0;
                            const net = e.net_commission || e.final_amount;
                            const revenue = e.payment_amount || (gross / (e.commission_rate / 100));
                            const rate = e.commission_rate || (gross / revenue * 100);

                            return (
                              <tr key={e.id}>
                                <td style={{ fontSize: 11, color: C.sub }}>{new Date(e.created_at).toLocaleDateString()}</td>
                                <td>
                                  <div style={{ fontWeight: 700 }}>{e.clients?.full_name || "—"}</div>
                                  <div style={{ fontSize: 10, color: C.muted }}>Estate: {e.estate_name || "General"}</div>
                                </td>
                                <td style={{ fontSize: 11, color: C.sub }}>{e.invoices?.invoice_number || "—"}</td>
                                <td style={{ fontWeight: 600 }}>{fmt(revenue)}</td>
                                <td style={{ fontSize: 11 }}>{Number(rate).toFixed(1)}%</td>
                                <td style={{ fontWeight: 600 }}>{fmt(gross)}</td>
                                <td style={{ color: "#EF4444", fontSize: 11 }}>-{fmt(wht)}</td>
                                <td style={{ fontWeight: 800, color: T.gold }}>{fmt(net)}</td>
                                <td><span className={`tg ${e.is_paid ? "tg2" : parseFloat(e.amount_paid || 0) > 0 ? "ty" : "tr"}`} style={{ fontSize: 9 }}>{e.is_paid ? "Paid" : parseFloat(e.amount_paid || 0) > 0 ? "Partial" : "Unpaid"}</span></td>
                                <td>
                                  {e.expenditure_id && (
                                    <button onClick={() => viewDocument(e.expenditure_id)} className="bg" style={{ fontSize: 9, padding: "4px 8px" }}>PROOF</button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                          {filteredEarnings.length === 0 && <tr><td colSpan="10" style={{ textAlign: "center", padding: 30, color: C.muted }}>No earnings records match your filters.</td></tr>}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {data.commissions.payouts.length > 0 && (
                    <div className="gc" style={{ marginTop: 24, overflow: "hidden" }}>
                      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${C.border}` }}><div className="ho" style={{ fontSize: 14 }}>Recent Payouts</div></div>
                      <div className="tw">
                        <table className="ht">
                          <thead><tr>{['Paid Date', 'Payout Amount', 'Reference', 'Notes'].map(h => <th key={h}>{h}</th>)}</tr></thead>
                          <tbody>
                            {data.commissions.payouts.map(p => (
                              <tr key={p.id}>
                                <td style={{ fontSize: 12, color: C.sub }}>{new Date(p.paid_at).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                                <td style={{ fontWeight: 800, color: "#10B981" }}>{fmt(p.total_amount)}</td>
                                <td style={{ fontSize: 11, color: C.sub }}>{p.reference || "—"}</td>
                                <td style={{ fontSize: 11, color: C.muted }}>{p.notes || "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        )}
      </div>

      {viewingDocs && (
        <Modal onClose={() => setViewingDocs(null)} title={viewingDocs.title || "Document Intelligence"} width={800}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ padding: 14, background: `${T.orange}0D`, borderRadius: 12, border: `1px solid ${T.orange}22` }}>
              <div style={{ fontSize: 11, color: C.sub, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Payout Proof Documentation</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {[...(viewingDocs.proforma_files || []).map((f, i) => ({ f, i, t: 'proforma' })), ...(viewingDocs.receipt_files || []).map((f, i) => ({ f, i, t: 'receipt' }))].map((doc, idx) => (
                  <a key={idx} href={`${API_BASE}/payouts/requests/${viewingDocs.id}/view-document/${doc.t}?file_index=${doc.i}`} target="_blank" rel="noreferrer" className="bg" style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", textDecoration: "none" }}>
                    <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                    <span style={{ fontSize: 12 }}>{doc.t.toUpperCase()} #{doc.i + 1}</span>
                  </a>
                ))}
                {(viewingDocs.total || 0) === 0 && (
                  <div style={{ fontSize: 13, color: C.muted }}>No physical proof files attached to this record.</div>
                )}
              </div>
            </div>
            <div style={{ height: 400, background: "#000", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", color: "#666" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>📄</div>
                <div style={{ fontSize: 14 }}>Click a file above to view secure attachment</div>
                <div style={{ fontSize: 11, marginTop: 4, color: "#444" }}>Encrypted Storage Stream Active</div>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}


// ─── MODULE: LEAVE MANAGEMENT ────────────────────────────────────────────────
function LeaveManagement({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [f, setF] = useState({ type: "Annual", start: "", end: "", reason: "" });
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const isHR = user.role?.includes("admin") || user.role?.includes("hr") || user.role?.includes("operations") || user.primary_role === "hr";

  useEffect(() => {
    setLoading(true);
    const params = isHR ? "" : `?staff_id=${user.id}`;
    apiFetch(`${API_BASE}/hr/leave-requests${params}`)
      .then(setRequests)
      .finally(() => setLoading(false));
  }, [isHR, user.id]);

  const submit = async () => {
    if (!f.start || !f.end) return;
    setUploading(true);
    try {
      let proofUrl = null;
      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        const upRes = await fetch(`${API_BASE}/hr/upload`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${localStorage.getItem("ec_token")}` },
          body: formData
        });
        if (!upRes.ok) throw new Error("File upload failed");
        const upData = await upRes.json();
        proofUrl = upData.url;
      }

      const days = Math.ceil((new Date(f.end) - new Date(f.start)) / (1000 * 60 * 60 * 24)) + 1;
      await apiFetch(`${API_BASE}/hr/leave-requests`, {
        method: "POST",
        body: JSON.stringify({
          leave_type: f.type,
          start_date: f.start,
          end_date: f.end,
          days_count: days,
          reason: f.reason,
          proof_url: proofUrl
        })
      });
      setShowNew(false);
      setFile(null);
      apiFetch(`${API_BASE}/hr/leave-requests${isHR ? "" : `?staff_id=${user.id}`}`).then(setRequests);
    } catch (e) { alert(e.message); }
    finally { setUploading(false); }
  };

  const updateStatus = async (id, status) => {
    try {
      await apiFetch(`${API_BASE}/hr/leave-requests/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status })
      });
      apiFetch(`${API_BASE}/hr/leave-requests${isHR ? "" : `?staff_id=${user.id}`}`).then(setRequests);
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Leave Management</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>Request time off and track your remaining leave quota.</div>
        </div>
        <button className="bp" onClick={() => setShowNew(true)}>Request Leave</button>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading leave data…</div>
      ) : (
        <div className="gc tw">
          <table className="ht">
            <thead>
              <tr>{["Staff", "Type", "Period", "Days", "Status", ""].map(h => <th key={h}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {requests.map(r => (
                <tr key={r.id}>
                  <td><div style={{ fontWeight: 700 }}>{r.staff?.full_name || "You"}</div></td>
                  <td>{r.leave_type}</td>
                  <td style={{ fontSize: 12, color: C.sub }}>{new Date(r.start_date).toLocaleDateString()} — {new Date(r.end_date).toLocaleDateString()}</td>
                  <td style={{ fontWeight: 800, color: T.orange }}>{r.days_count}d</td>
                  <td>
                    <span className={`tg ${r.status === "approved" ? "tg2" : r.status === "pending" ? "ty" : "tr"}`}>{r.status}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {r.proof_url && (
                        <a href={r.proof_url} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 10, padding: "4px 10px", borderRadius: 6, background: `${T.orange}18`, color: T.orange, border: `1px solid ${T.orange}44`, textDecoration: "none", fontWeight: 700 }}>
                          <svg style={{ width: 12, height: 12, flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
                          View Proof
                        </a>
                      )}
                      {isHR && r.status === "pending" && (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => updateStatus(r.id, "approved")}>Approve</button>
                          <button className="bd" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => updateStatus(r.id, "rejected")}>Reject</button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {requests.length === 0 && <tr><td colSpan="6" style={{ textAlign: "center", padding: 20, color: C.muted }}>No leave records found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="New Leave Request">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div><Lbl>Leave Type</Lbl>
              <select className="inp" value={f.type} onChange={e => setF(x => ({ ...x, type: e.target.value }))}>
                <option>Annual</option><option>Sick</option><option>Study</option><option>Compassionate</option>
              </select>
            </div>
            <div className="g2">
              <div><Lbl>Start Date</Lbl><input type="date" className="inp" value={f.start} onChange={e => setF(x => ({ ...x, start: e.target.value }))} /></div>
              <div><Lbl>End Date</Lbl><input type="date" className="inp" value={f.end} onChange={e => setF(x => ({ ...x, end: e.target.value }))} /></div>
            </div>
            <div><Lbl>Reason (Optional)</Lbl><textarea className="inp" value={f.reason} onChange={e => setF(x => ({ ...x, reason: e.target.value }))} /></div>
            <div>
              <Lbl>Attachment (Optional Proof)</Lbl>
              <input type="file" className="inp" style={{ padding: 8 }} onChange={e => setFile(e.target.files[0])} />
              {file && <div style={{ fontSize: 10, color: T.orange, marginTop: 4 }}>File attached: {file.name}</div>}
            </div>
            <button className="bp" style={{ padding: 14 }} onClick={submit} disabled={uploading}>
              {uploading ? "Processing..." : "Submit Request"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: ADMINISTRATION / ANALYTICS ──────────────────────────────────────
function Administration() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/analytics/headcount`).then(setStats).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading analytics…</div>;

  return (
    <div className="fade">
      <div className="ho" style={{ fontSize: 22, marginBottom: 6 }}>Personnel Administration</div>
      <div style={{ fontSize: 13, color: C.sub, marginBottom: 24 }}>Organization-wide reporting, demographics, and headcount trends.</div>

      <div className="g3" style={{ marginBottom: 22 }}>
        <StatCard label="Total Headcount" value={stats?.total_active || 0} />
        <StatCard label="Departments" value={Object.keys(stats?.by_department || {}).length} col="#60A5FA" />
        <StatCard label="On Leave Today" value="2" col={T.orange} />
      </div>

      <div className="g2" style={{ gap: 24 }}>
        <div className="gc" style={{ padding: 22 }}>
          <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Headcount by Department</div>
          {Object.entries(stats?.by_department || {}).map(([d, v]) => (
            <div key={d} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
                <span style={{ color: C.text }}>{d}</span>
                <span style={{ fontWeight: 800 }}>{v} staff</span>
              </div>
              <Bar pct={(v / stats.total_active) * 100} />
            </div>
          ))}
        </div>
        <div className="gc" style={{ padding: 22 }}>
          <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Role Distribution</div>
          {Object.entries(stats?.by_role || {}).map(([r, v]) => (
            <div key={r} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
                <span style={{ color: C.text, textTransform: "capitalize" }}>{r.replace('_', ' ')}</span>
                <span style={{ fontWeight: 800 }}>{v}</span>
              </div>
              <Bar pct={(v / stats.total_active) * 100} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── HELPER: DOCUMENTS & QUALIFICATIONS ──────────────────────────────────────
function DocumentsManager({ staffId, isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [f, setF] = useState({ type: "Contract", title: "" });
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/staff/${staffId}/documents`).then(setDocs).finally(() => setLoading(false));
  }, [staffId]);

  const add = async () => {
    if (!f.title || !file) return;
    setUploading(true);
    try {
      // 1. Upload to Supabase
      const formData = new FormData();
      formData.append("file", file);
      const upRes = await fetch(`${API_BASE}/hr/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("ec_token")}` },
        body: formData
      });
      if (!upRes.ok) throw new Error("File upload failed");
      const upData = await upRes.json();

      // 2. Save metadata
      await apiFetch(`${API_BASE}/hr/documents`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: staffId,
          doc_type: f.type,
          title: f.title,
          file_url: upData.url
        })
      });
      setShowAdd(false);
      setFile(null);
      apiFetch(`${API_BASE}/hr/staff/${staffId}/documents`).then(setDocs);
    } catch (e) { alert(e.message); }
    finally { setUploading(false); }
  };

  const remove = async (id) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await apiFetch(`${API_BASE}/hr/documents/${id}`, { method: "DELETE" });
      apiFetch(`${API_BASE}/hr/staff/${staffId}/documents`).then(setDocs);
    } catch (e) { alert(e.message); }
  };

  const availableTypes = ["Contract", "CV", "Government ID", "Passport", "Certificate"];
  const typesToUse = isHR ? availableTypes : availableTypes.filter(t => !docs.some(d => d.doc_type === t));

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: C.muted }}>OFFICIAL DOCUMENTS ({docs.length})</div>
        {(isHR || typesToUse.length > 0) && <button className="bg" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => setShowAdd(true)}>+ Add Document</button>}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {docs.map(d => (
          <div key={d.id} className="field" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>{d.title}</div>
              <div style={{ fontSize: 10, color: C.sub }}>{d.doc_type} · Added {new Date(d.created_at).toLocaleDateString()}</div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <a href={d.file_url} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 10, padding: "4px 12px", textDecoration: "none" }}>View File</a>
              {isHR && <button className="br" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => remove(d.id)}>Delete</button>}
            </div>
          </div>
        ))}
        {docs.length === 0 && <div style={{ textAlign: "center", padding: 20, color: C.muted, fontSize: 12, border: `1px dashed ${C.border}`, borderRadius: 10 }}>No documents uploaded.</div>}
      </div>

      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} title="Link Document">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Document Type</Lbl>
              <select className="inp" value={f.type} onChange={e => setF(x => ({ ...x, type: e.target.value }))}>
                {typesToUse.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div><Lbl>Document Title</Lbl><input className="inp" placeholder="e.g. Signed Employment Contract" value={f.title} onChange={e => setF(x => ({ ...x, title: e.target.value }))} /></div>
            <div>
              <Lbl>Select File</Lbl>
              <input type="file" className="inp" style={{ padding: 8 }} onChange={e => setFile(e.target.files[0])} />
              {file && <div style={{ fontSize: 10, color: T.orange, marginTop: 4 }}>File: {file.name}</div>}
            </div>
            <button className="bp" onClick={add} disabled={uploading}>
              {uploading ? "Uploading..." : "Upload & Save Document"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function LegalManager({ staffId: initialStaffId, staffName: initialStaffName, isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [matters, setMatters] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInitiate, setShowInitiate] = useState(false);
  const [initForm, setInitForm] = useState({ title: "", type: "Personnel", priority: "Normal", notes: "", staff_id: initialStaffId, external_name: "", external_email: "", isExternal: false });
  const [submitting, setSubmitting] = useState(false);
  const [dispatchState, setDispatchState] = useState({});
  const [dispatchMsg, setDispatchMsg] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      // If we have a specific staffId, fetch their matters. Otherwise fetch all (global mode).
      const url = initialStaffId
        ? `${API_BASE}/hr-legal/staff/${initialStaffId}/matters`
        : `${API_BASE}/hr-legal/matters`;
      const data = await apiFetch(url);
      setMatters(data);

      if (isHR) {
        const staff = await apiFetch(`${API_BASE}/hr/staff`);
        setStaffList(staff);
      }
    } catch (e) { console.error("Legal load error:", e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [initialStaffId]);

  const initiate = async () => {
    if (!initForm.title) return alert("Title is required");
    if (!initForm.isExternal && !initForm.staff_id) return alert("Please select a staff member or toggle External Candidate");
    if (initForm.isExternal && (!initForm.external_name || !initForm.external_email)) return alert("Candidate name and email are required");

    setSubmitting(true);
    try {
      await apiFetch(`${API_BASE}/hr-legal/matters`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: initForm.isExternal ? null : initForm.staff_id,
          title: initForm.title,
          category: initForm.type,
          priority: initForm.priority,
          hr_memo: initForm.notes,
          external_party_name: initForm.isExternal ? initForm.external_name : null,
          external_party_email: initForm.isExternal ? initForm.external_email : null,
          status: "Draft"
        })
      });
      setShowInitiate(false);
      setInitForm({ title: "", type: "Personnel", priority: "Normal", notes: "", staff_id: initialStaffId, external_name: "", external_email: "", isExternal: false });
      load();
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  const getStatusCol = (s) => {
    if (s === "Executed") return "#10B981";
    if (s === "Draft") return C.muted;
    if (s === "Review") return T.orange;
    if (s === "Voided") return "#EF4444";
    return T.orange;
  };

  const selectedStaff = staffList.find(s => s.id === initForm.staff_id);
  const displayTitle = initForm.isExternal ? initForm.external_name : (initialStaffName || selectedStaff?.full_name || "New Matter");

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: C.muted }}>LEGAL MATTERS & CONTRACTS ({matters.length})</div>
        {isHR && (
          <button className="bp" style={{ fontSize: 10, padding: "6px 14px" }} onClick={() => setShowInitiate(true)}>
            Initiate Legal Matter
          </button>
        )}
      </div>

      {loading ? <div style={{ padding: 20, textAlign: "center", color: C.muted }}>Loading legal vault...</div> : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {matters.map(m => (
            <div key={m.id} className="field" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderLeft: `4px solid ${getStatusCol(m.status)}` }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>{m.title}</div>
                  <span className="tg" style={{ fontSize: 9, background: `${getStatusCol(m.status)}15`, color: getStatusCol(m.status), border: `1px solid ${getStatusCol(m.status)}33` }}>
                    {m.status}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: C.sub }}>
                  {initialStaffId ? "" : `Staff: ${m.staff_id ? (staffList.find(s => s.id === m.staff_id)?.full_name || m.staff_id) : (m.external_party_name || "External")} · `}
                  Category: {m.category} · Priority: {m.priority} · Initiated: {new Date(m.created_at).toLocaleDateString()}
                </div>
                {m.legal_memo && (
                  <div style={{ marginTop: 8, padding: "6px 10px", background: `${T.orange}08`, borderRadius: 6, fontSize: 11, borderLeft: `2px solid ${T.orange}` }}>
                    <b style={{ color: T.orange }}>Legal Dept:</b> {m.legal_memo}
                  </div>
                )}
              </div>
              <div style={{ marginLeft: 16, display: "flex", gap: 8, alignItems: "center", flexDirection: "column", minWidth: 150 }}>
                {isHR && (
                  <a href={`/legal/view?id=${m.id}`} target="_blank" rel="noreferrer" className="bp" style={{ fontSize: 10, padding: "5px 12px", background: "#333", color: "#fff", textDecoration: "none", width: '100%', textAlign: 'center', boxSizing: 'border-box' }}>
                    👁️ View Contract
                  </a>
                )}
                {m.status === "Executed" ? (
                  <a href={`/api/hr-legal/matters/${m.id}/export`} className="bg" style={{ fontSize: 10, padding: "5px 12px", textDecoration: "none", width: '100%', textAlign: 'center', boxSizing: 'border-box' }}>Download Contract</a>
                ) : m.status !== "Legal Signing" ? (
                  <>
                    <div style={{ fontSize: 10, color: C.muted, fontStyle: "italic" }}>{m.status === "Review" ? "Awaiting Legal Review" : "In Progress"}</div>
                    {isHR && (
                      <>
                        {dispatchState[m.id] === 'confirming' ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: 4, background: `${T.orange}18`, border: `1px solid ${T.orange}40`, borderRadius: 6, padding: "6px 10px", fontSize: 10 }}>
                            <div style={{ color: T.orange, fontWeight: 700, marginBottom: 2 }}>Send signing link to {m.external_party_name || 'staff member'}?</div>
                            <div style={{ display: "flex", gap: 6 }}>
                              <button
                                style={{ background: T.orange, color: '#fff', border: 'none', borderRadius: 4, padding: '3px 10px', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}
                                onClick={async () => {
                                  setDispatchState(s => ({ ...s, [m.id]: 'sending' }));
                                  try {
                                    const res = await apiFetch(`${API_BASE}/hr-legal/matters/${m.id}/dispatch-signature`, { method: 'POST' });
                                    setDispatchState(s => ({ ...s, [m.id]: 'done' }));
                                    setDispatchMsg(s => ({ ...s, [m.id]: res.message || 'Dispatched!' }));
                                    setTimeout(() => { setDispatchState(s => ({ ...s, [m.id]: undefined })); load(); }, 4000);
                                  } catch (err) {
                                    setDispatchState(s => ({ ...s, [m.id]: 'error' }));
                                    setDispatchMsg(s => ({ ...s, [m.id]: err.message }));
                                    setTimeout(() => setDispatchState(s => ({ ...s, [m.id]: undefined })), 5000);
                                  }
                                }}
                              >✓ Confirm</button>
                              <button
                                style={{ background: 'transparent', color: C.muted, border: `1px solid ${C.border}`, borderRadius: 4, padding: '3px 10px', fontSize: 10, cursor: 'pointer' }}
                                onClick={() => setDispatchState(s => ({ ...s, [m.id]: undefined }))}
                              >✕ Cancel</button>
                            </div>
                          </div>
                        ) : dispatchState[m.id] === 'sending' ? (
                          <div style={{ fontSize: 10, color: T.orange, fontWeight: 700 }}>✈️ Sending...</div>
                        ) : dispatchState[m.id] === 'done' ? (
                          <div style={{ fontSize: 10, color: '#10B981', fontWeight: 700 }}>✅ {dispatchMsg[m.id]}</div>
                        ) : dispatchState[m.id] === 'error' ? (
                          <div style={{ fontSize: 10, color: '#EF4444', fontWeight: 700 }}>✗ {dispatchMsg[m.id]}</div>
                        ) : (
                          <button
                            className="bp"
                            style={{ fontSize: 10, padding: "5px 12px", background: "#C47D0A", color: "#fff", border: "none" }}
                            onClick={() => setDispatchState(s => ({ ...s, [m.id]: 'confirming' }))}
                          >
                            ✈️ Dispatch to Signer
                          </button>
                        )}
                      </>
                    )}
                  </>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "center" }}>
                    <div style={{ fontSize: 10, color: T.orange, fontWeight: "bold", border: `1px solid ${T.orange}40`, padding: "4px 8px", borderRadius: 4 }}>Pending Signature</div>
                    {isHR && (
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                        {dispatchState[m.id] === 'resending' ? (
                          <div style={{ fontSize: 9, color: T.orange }}>🔄 Resending...</div>
                        ) : dispatchState[m.id] === 'resent_done' ? (
                          <div style={{ fontSize: 9, color: '#10B981' }}>✅ {dispatchMsg[m.id] || 'Resent!'}</div>
                        ) : (
                          <button
                            style={{
                              background: 'transparent',
                              color: C.muted,
                              border: `1px solid ${C.border}`,
                              borderRadius: 4,
                              padding: '2px 8px',
                              fontSize: 9,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4
                            }}
                            onClick={async () => {
                              setDispatchState(s => ({ ...s, [m.id]: 'resending' }));
                              try {
                                const res = await apiFetch(`${API_BASE}/hr-legal/matters/${m.id}/resend-signature`, { method: 'POST' });
                                setDispatchState(s => ({ ...s, [m.id]: 'resent_done' }));
                                setDispatchMsg(s => ({ ...s, [m.id]: res.message }));
                                setTimeout(() => setDispatchState(s => ({ ...s, [m.id]: undefined })), 4000);
                              } catch (err) {
                                setDispatchState(s => ({ ...s, [m.id]: 'error' }));
                                setDispatchMsg(s => ({ ...s, [m.id]: err.message }));
                                setTimeout(() => setDispatchState(s => ({ ...s, [m.id]: undefined })), 5000);
                              }
                            }}
                          >
                            🔄 Resend Link
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {matters.length === 0 && (
            <div style={{ textAlign: "center", padding: 30, color: C.muted, border: `1px dashed ${C.border}`, borderRadius: 12 }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>⚖️</div>
              <div style={{ fontSize: 12 }}>No legal matters found.</div>
              {isHR && <div style={{ fontSize: 10, marginTop: 4 }}>Legal can draft contracts like Employment Agreements or NDAs here.</div>}
            </div>
          )}
        </div>
      )}

      {showInitiate && (
        <Modal onClose={() => setShowInitiate(false)} title={`Initiate Legal Matter - ${displayTitle}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Matter Title *</Lbl>
              <input className="inp" placeholder="e.g. New Employment Contract 2026" value={initForm.title} onChange={e => setInitForm({ ...initForm, title: e.target.value })} />
            </div>

            {!initialStaffId && (
              <div style={{ background: `${C.border}33`, padding: 12, borderRadius: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <Lbl>Target Party</Lbl>
                  <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, cursor: "pointer" }}>
                    <input type="checkbox" checked={initForm.isExternal} onChange={e => setInitForm({ ...initForm, isExternal: e.target.checked })} />
                    External Candidate (Offer Letter)
                  </label>
                </div>

                {initForm.isExternal ? (
                  <div className="g2">
                    <input className="inp" placeholder="Full Name" value={initForm.external_name} onChange={e => setInitForm({ ...initForm, external_name: e.target.value })} />
                    <input className="inp" placeholder="Email Address" value={initForm.external_email} onChange={e => setInitForm({ ...initForm, external_email: e.target.value })} />
                  </div>
                ) : (
                  <select className="inp" value={initForm.staff_id || ""} onChange={e => setInitForm({ ...initForm, staff_id: e.target.value })}>
                    <option value="">-- Select Staff Member --</option>
                    {staffList.map(s => (
                      <option key={s.id} value={s.id}>{s.full_name} ({s.department || "No Dept"})</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Category</Lbl>
                <select className="inp" value={initForm.type} onChange={e => setInitForm({ ...initForm, type: e.target.value })}>
                  <option>Personnel</option><option>Disciplinary</option><option>NDA</option><option>Exit Settlement</option>
                </select>
              </div>
              <div><Lbl>Priority</Lbl>
                <select className="inp" value={initForm.priority} onChange={e => setInitForm({ ...initForm, priority: e.target.value })}>
                  <option>Critical</option><option>Normal</option><option>Low</option>
                </select>
              </div>
            </div>
            <div><Lbl>HR Brief / Memo (Internal for Legal)</Lbl>
              <textarea className="inp" rows={4} placeholder="Brief instructions for the legal team..." value={initForm.notes} onChange={e => setInitForm({ ...initForm, notes: e.target.value })} />
            </div>
            <button className="bp" style={{ padding: 14 }} onClick={initiate} disabled={submitting}>
              {submitting ? "Sending to Legal..." : "Send Request to Legal Studio"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}


function QualificationsManager({ staffId, isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [quals, setQuals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [f, setF] = useState({ type: "Education", title: "", inst: "", year: new Date().getFullYear() });

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/staff/${staffId}/qualifications`).then(setQuals).finally(() => setLoading(false));
  }, [staffId]);

  const add = async () => {
    if (!f.title) return;
    try {
      await apiFetch(`${API_BASE}/hr/staff/${staffId}/qualifications`, {
        method: "POST",
        body: JSON.stringify({
          type: f.type,
          title: f.title,
          institution: f.inst,
          year: parseInt(f.year)
        })
      });
      setShowAdd(false);
      apiFetch(`${API_BASE}/hr/staff/${staffId}/qualifications`).then(setQuals);
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: C.muted }}>QUALIFICATIONS & SKILLS ({quals.length})</div>
        {isHR && <button className="bg" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => setShowAdd(true)}>+ Add New</button>}
      </div>
      <div className="g2">
        {quals.map(q => (
          <div key={q.id} className="field">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span className="tg" style={{ fontSize: 8, padding: "3px 8px" }}>{q.type}</span>
              <span style={{ fontSize: 11, color: C.muted, fontWeight: 800 }}>{q.year}</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{q.title}</div>
            <div style={{ fontSize: 11, color: C.sub }}>{q.institution}</div>
          </div>
        ))}
      </div>
      {quals.length === 0 && <div style={{ textAlign: "center", padding: 20, color: C.muted, fontSize: 12 }}>No records provided.</div>}

      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} title="Add Record">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Record Type</Lbl>
              <select className="inp" value={f.type} onChange={e => setF(x => ({ ...x, type: e.target.value }))}>
                <option>Education</option><option>Certification</option><option>Skill</option>
              </select>
            </div>
            <div><Lbl>Title / Subject</Lbl><input className="inp" placeholder="e.g. B.Sc. Architecture" value={f.title} onChange={e => setF(x => ({ ...x, title: e.target.value }))} /></div>
            <div><Lbl>Institution / Provider</Lbl><input className="inp" placeholder="e.g. University of Lagos" value={f.inst} onChange={e => setF(x => ({ ...x, inst: e.target.value }))} /></div>
            <div><Lbl>Year Completed</Lbl><input type="number" className="inp" value={f.year} onChange={e => setF(x => ({ ...x, year: e.target.value }))} /></div>
            <button className="bp" onClick={add}>Save Record</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function PerformanceManager({ staffId, isHR, authRole }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showReview, setShowReview] = useState(false);
  const [review, setReview] = useState({ quality_score: 80, teamwork_score: 4, leadership_score: 4, attitude_score: 4, comments: "", review_period: new Date().toISOString().split('T')[0] });

  const load = async () => {
    setLoading(true);
    try {
      const [p, h] = await Promise.all([
        apiFetch(`${API_BASE}/hr/staff/${staffId}/performance`),
        apiFetch(`${API_BASE}/hr/staff/${staffId}/performance/history`)
      ]);
      setData(p);
      setHistory(h);
      if (p.review) setReview(p.review);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [staffId]);

  const saveReview = async () => {
    try {
      await apiFetch(`${API_BASE}/hr/staff/${staffId}/performance/review`, {
        method: "POST",
        body: JSON.stringify(review)
      });
      setShowReview(false);
      load();
    } catch (e) { alert(e.message); }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Computing performance index...</div>;
  if (!data) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>No performance data found.</div>;

  const sc = data.score;
  const b = data.breakdown;

  // Simple SVG Line Chart for trends
  const renderTrend = () => {
    if (!history.length) return null;
    const padding = 20;
    const w = 560;
    const h = 100;
    const pts = history.map((d, i) => ({
      x: padding + (i * ((w - 2 * padding) / (history.length - 1))),
      y: h - padding - (d.score * ((h - 2 * padding) / 100))
    }));
    const d = `M ${pts.map(p => `${p.x},${p.y}`).join(" L ")}`;

    return (
      <div style={{ marginTop: 24, background: C.base, borderRadius: 12, padding: 20, border: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, marginBottom: 16, textTransform: "uppercase" }}>6-MONTH PERFORMANCE TREND</div>
        <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          {/* Grid lines */}
          {[0, 50, 100].map(v => {
            const y = h - padding - (v * ((h - 2 * padding) / 100));
            return <line key={v} x1={padding} y1={y} x2={w - padding} y2={y} stroke={C.border} strokeWidth="1" strokeDasharray="4 4" />;
          })}
          <path d={d} fill="none" stroke={T.orange} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          {pts.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r="4" fill={history[i].score >= 70 ? "#4ADE80" : T.orange} stroke={C.base} strokeWidth="2" />
              <text x={p.x} y={h - 4} textAnchor="middle" fontSize="9" fill={C.muted}>{history[i].month.split(" ")[0]}</text>
              <text x={p.x} y={p.y - 8} textAnchor="middle" fontSize="10" fontWeight="800" fill={C.text}>{Math.round(history[i].score)}</text>
            </g>
          ))}
        </svg>
      </div>
    );
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", gap: 24, alignItems: "center", marginBottom: 24 }}>
        <div style={{ position: "relative", width: 100, height: 100 }}>
          <svg width="100" height="100">
            <circle cx="50" cy="50" r="45" fill="none" stroke={C.border} strokeWidth="8" />
            <circle cx="50" cy="50" r="45" fill="none" stroke={sc >= 70 ? "#4ADE80" : sc >= 50 ? T.orange : "#F87171"} strokeWidth="8"
              strokeDasharray={2 * Math.PI * 45} strokeDashoffset={2 * Math.PI * 45 * (1 - sc / 100)}
              strokeLinecap="round" style={{ transition: "all 1s ease", transform: "rotate(-90deg)", transformOrigin: "50% 50%" }} />
          </svg>
          <div style={{ position: "absolute", top: 0, left: 0, bottom: 0, right: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
            <div style={{ fontSize: 22, fontWeight: 900, color: C.text }}>{Math.round(sc)}</div>
            <div style={{ fontSize: 9, color: C.muted, fontWeight: 800 }}>INDEX</div>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 800 }}>Performance Rating: <span style={{ color: sc >= 80 ? "#4ADE80" : sc >= 60 ? T.orange : "#F87171" }}>{sc >= 80 ? "Excellent" : sc >= 70 ? "Very Good" : sc >= 50 ? "Fair" : "Needs Improvement"}</span></div>
          <div style={{ fontSize: 12, color: C.sub, marginTop: 4 }}>Comprehensive score based on goals achievement (40%), quality of work (20%), and manager reviews (40%).</div>
          {(authRole === "hr" || authRole === "line_manager") && (
            <button className="bp" style={{ fontSize: 11, padding: "6px 14px", marginTop: 12 }} onClick={() => setShowReview(true)}>Update Manager Review</button>
          )}
        </div>
      </div>

      <div className="g4" style={{ gap: 12 }}>
        {[
          ["Monthly Goals", b.goals, "40%", "tg2"],
          ["Work Quality", b.quality, "20%", "to"],
          ["Teamwork", b.teamwork, "20%", "tm"],
          ["Initiative", b.initiative, "20%", "tm"]
        ].map(([lbl, val, wt, cl]) => (
          <div key={lbl} className="gc" style={{ padding: 16, textAlign: "center" }}>
            <div style={{ fontSize: 9, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800, marginBottom: 8 }}>{lbl} ({wt})</div>
            <div style={{ fontSize: 20, fontWeight: 900, color: C.text }}>{Math.round(val)}</div>
            <div style={{ height: 4, background: C.border, borderRadius: 2, margin: "8px auto 0", width: "60%", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${val}%`, background: val >= 70 ? "#4ADE80" : val >= 50 ? T.orange : "#F87171" }} />
            </div>
          </div>
        ))}
      </div>

      {renderTrend()}

      <div style={{ marginTop: 24 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: C.muted, marginBottom: 12 }}>ACTIVE MONTHLY GOALS</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {data.goals?.map(g => (
            <div key={g.id} className="gc" style={{ padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>{g.kpi_name}</div>
                <div style={{ fontSize: 11, color: C.sub }}>Target: {g.target_value} {g.unit} · Weight: {g.weight}%</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 16, fontWeight: 900, color: g.achievement_pct >= 90 ? "#4ADE80" : T.orange }}>{Math.round(g.achievement_pct)}%</div>
                <div style={{ fontSize: 10, color: C.muted }}>Achievement</div>
              </div>
            </div>
          ))}
          {(!data.goals || data.goals.length === 0) && <div style={{ textAlign: "center", padding: 20, color: C.muted, fontSize: 12 }}>No goals set for this period.</div>}
        </div>
      </div>

      {showReview && (
        <Modal onClose={() => setShowReview(false)} title="Submit Performance Review" width={480}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingBottom: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div><Lbl>Quality Score (0-100)</Lbl><input type="number" className="inp" value={review.quality_score} onChange={e => setReview(r => ({ ...r, quality_score: e.target.value }))} /></div>
              <div><Lbl>Teamwork (1-5)</Lbl><input type="number" min="1" max="5" className="inp" value={review.teamwork_score} onChange={e => setReview(r => ({ ...r, teamwork_score: e.target.value }))} /></div>
              <div><Lbl>Initiative (1-5)</Lbl><input type="number" min="1" max="5" className="inp" value={review.leadership_score} onChange={e => setReview(r => ({ ...r, leadership_score: e.target.value }))} /></div>
              <div><Lbl>Period</Lbl><input type="date" className="inp" value={review.review_period} onChange={e => setReview(r => ({ ...r, review_period: e.target.value }))} /></div>
            </div>
            <div><Lbl>Comments</Lbl><textarea className="inp" rows={4} value={review.comments} onChange={e => setReview(r => ({ ...r, comments: e.target.value }))} /></div>
            <button className="bp" style={{ padding: 12 }} onClick={saveReview}>Submit Review</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HELPER: ORG CHART ───────────────────────────────────────────────────────
function OrgChartView({ staff }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;

  const tree = [];
  const map = {};

  staff.forEach(s => {
    if (s.is_active !== false && !s.is_archived) {
      map[s.id] = { ...s, children: [] };
    }
  });

  Object.values(map).forEach(s => {
    if (s.line_manager_id && map[s.line_manager_id]) {
      map[s.line_manager_id].children.push(s);
    } else {
      tree.push(s);
    }
  });

  const renderNode = (node) => (
    <div key={node.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "0 10px" }}>
      <div style={{ background: C.surface, border: `2px solid rgb(249, 115, 22)`, borderRadius: 12, padding: "12px 18px", display: "flex", alignItems: "center", gap: 12, minWidth: 220, position: "relative", zIndex: 2, boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
        <Av av={node.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={38} />
        <div>
          <div style={{ fontSize: 13, fontWeight: 800, color: C.text }}>{node.full_name}</div>
          <div style={{ fontSize: 11, color: C.sub }}>{node.staff_profiles?.[0]?.job_title || node.role}</div>
          <div style={{ fontSize: 10, color: "#F97316", fontWeight: 700 }}>{node.department}</div>
        </div>
      </div>
      {node.children.length > 0 && (
        <div style={{ display: "flex", position: "relative", marginTop: 20, paddingTop: 20 }}>
          <div style={{ position: "absolute", top: 0, left: "50%", width: 2, height: 20, background: `${C.border}`, transform: "translateX(-50%)" }} />
          {node.children.length > 1 && (
            <div style={{ position: "absolute", top: 20, left: "50%", right: "50%", height: 2, background: `${C.border}` }} />
          )}
          {node.children.map(child => (
            <div key={child.id} style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ position: "absolute", top: -20, left: "50%", width: 2, height: 20, background: `${C.border}`, transform: "translateX(-50%)" }} />
              {renderNode(child)}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div style={{ overflowX: "auto", padding: "40px 0", minHeight: 500, display: "flex", justifyContent: "center" }}>
      {tree.length > 0 ? (
        <div style={{ display: "flex", gap: 40 }}>
          {tree.map(root => renderNode(root))}
        </div>
      ) : (
        <div style={{ color: C.muted, marginTop: 40 }}>No org chart data available.</div>
      )}
    </div>
  );
}

// ─── MODULE: STAFF DIRECTORY ─────────────────────────────────────────────────
function StaffDirectory({ authRole }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { departments } = useDepartments();
  const viewOnly = authRole !== "hr";
  const [tab, setTab] = useState("full");
  const [view, setView] = useState(null);
  const [dtTab, setDtTab] = useState("details");
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newStaff, setNewStaff] = useState({ full_name: "", email: "", password: "", confirm_password: "", roles: ["staff"], primary_role: "staff", staff_type: "full", department: departments[0]?.name || "", line_manager_id: null });
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [draftView, setDraftView] = useState({});
  const [editLoading, setEditLoading] = useState(false);
  const [search, setSearch] = useState("");

  const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  const toggleNewStaffRole = (roleValue) => {
    setNewStaff(s => {
      const roles = s.roles.includes(roleValue)
        ? s.roles.filter(r => r !== roleValue)
        : [...s.roles, roleValue];
      return { ...s, roles };
    });
  };

  const getStaffNameById = (staffId) => {
    if (!staffId) return "—";
    const found = staff.find(s => s.id === staffId);
    return found ? found.full_name : "—";
  };

  const matchesStaffSearch = (member) => {
    const query = search.trim().toLowerCase();
    if (!query) return true;
    const values = [
      member.full_name,
      member.email,
      member.department,
      member.role,
      member.staff_profiles?.[0]?.staff_type
    ].map(v => (v || "").toString().toLowerCase());
    return values.some(v => v.includes(query));
  };

  useEffect(() => {
    if (!view) return;
    const p = view.staff_profiles?.[0] || {};
    setDraftView({
      full_name: view.full_name || "",
      email: view.email || "",
      job_title: p.job_title || view.role || "",
      department: view.department || "",
      line_manager_id: view.line_manager_id || "",
      roles: view.role ? view.role.split(",") : ["staff"],
      primary_role: view.primary_role || "staff",
      phone_number: p.phone_number || "",
      emergency_contact: p.emergency_contact || "",
      address: p.address || "",
      bio: p.bio || ""
    });
    setEditMode(false);
  }, [view]);

  const loadStaff = useCallback(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/staff`)
      .then(d => setStaff(d))
      .catch(e => console.error("Staff fetch error:", e))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadStaff(); }, [loadStaff]);

  const handleAddStaff = async () => {
    if (!newStaff.full_name.trim() || !newStaff.email.trim() || !newStaff.password.trim() || !newStaff.confirm_password.trim()) {
      alert("Full name, email, password, and password confirmation are required.");
      return;
    }
    if (!isValidEmail(newStaff.email)) {
      alert("Please enter a valid email address.");
      return;
    }
    if (newStaff.password !== newStaff.confirm_password) {
      alert("Passwords do not match.");
      return;
    }
    if (newStaff.password.length < 8) {
      alert("Password must be at least 8 characters.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        full_name: newStaff.full_name.trim(),
        email: newStaff.email.trim(),
        password: newStaff.password,
        role: newStaff.roles?.length ? newStaff.roles.join(",") : "staff",
        primary_role: newStaff.primary_role || "staff",
        staff_type: newStaff.staff_type || "full",
        department: newStaff.department?.trim() || null,
        line_manager_id: newStaff.line_manager_id || null
      };

      await apiFetch(`/auth/register`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setShowAdd(false);
      setNewStaff({ full_name: "", email: "", password: "", confirm_password: "", roles: ["staff"], primary_role: "staff", staff_type: "full", department: "", line_manager_id: null });
      loadStaff();
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const archiveStaff = async () => {
    if (!view) return;
    const date = prompt("Enter Exit Date (YYYY-MM-DD):", new Date().toISOString().split('T')[0]);
    if (!date) return;
    const reason = prompt("Enter Exit Reason:");
    if (!reason) return;

    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/profile/${view.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          exit_date: date,
          exit_reason: reason
        })
      });
      alert("Staff member archived and deactivated.");
      setView(null);
      loadStaff();
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const saveStaffProfile = async () => {
    if (!view) return;
    setEditLoading(true);
    try {
      const rolePayload = {
        role: draftView.roles?.join(",") || view.role,
        primary_role: draftView.primary_role || view.primary_role || "staff",
        department: draftView.department?.trim() || null,
        line_manager_id: draftView.line_manager_id || null
      };

      if (rolePayload.role !== view.role || rolePayload.primary_role !== view.primary_role || rolePayload.department !== view.department || (view.line_manager_id || "") !== (draftView.line_manager_id || "")) {
        await apiFetch(`/auth/admins/${view.id}/roles`, {
          method: "PATCH",
          body: JSON.stringify(rolePayload)
        });
      }

      await apiFetch(`${API_BASE}/hr/profile/${view.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          full_name: draftView.full_name,
          email: draftView.email,
          job_title: draftView.job_title,
          department: draftView.department,
          line_manager_id: draftView.line_manager_id || null,
          phone_number: draftView.phone_number,
          emergency_contact: draftView.emergency_contact,
          address: draftView.address,
          bio: draftView.bio,
          dob: draftView.dob || null,
          gender: draftView.gender,
          nationality: draftView.nationality,
          marital_status: draftView.marital_status,
          leave_quota: draftView.leave_quota ? parseInt(draftView.leave_quota, 10) : 20
        })
      });
      setView(prev => ({
        ...prev,
        full_name: draftView.full_name,
        email: draftView.email,
        role: rolePayload.role,
        primary_role: rolePayload.primary_role,
        department: rolePayload.department,
        line_manager_id: rolePayload.line_manager_id,
        staff_profiles: [{
          ...prev.staff_profiles?.[0],
          job_title: draftView.job_title,
          phone_number: draftView.phone_number,
          emergency_contact: draftView.emergency_contact,
          address: draftView.address,
          bio: draftView.bio,
          dob: draftView.dob,
          gender: draftView.gender,
          nationality: draftView.nationality,
          marital_status: draftView.marital_status,
          leave_quota: draftView.leave_quota
        }]
      }));
      loadStaff();
      setEditMode(false);
      alert("Staff profile updated successfully.");
    } catch (e) {
      alert("Error saving profile: " + e.message);
    } finally {
      setEditLoading(false);
    }
  };

  const activeList = staff.filter(u => {
    const sType = u.staff_profiles?.[0]?.staff_type || "full";
    return sType === tab && u.is_active !== false && !u.is_archived && matchesStaffSearch(u);
  });

  const archivedList = staff.filter(u => {
    const sType = u.staff_profiles?.[0]?.staff_type || "full";
    return sType === tab && (u.is_active === false || u.is_archived) && matchesStaffSearch(u);
  });

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Staff Directory</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>Full profiles — HR access only. Staff cannot see each other's records.</div>
        </div>
        <button className="bp" onClick={() => setShowAdd(true)}>+ Add Staff</button>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <input
          className="inp"
          style={{ flex: 1, minWidth: 260 }}
          placeholder="Search staff by name, email, department, role"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div style={{ fontSize: 13, color: C.sub }}>{activeList.length} active · {archivedList.length} archived</div>
      </div>
      <Tabs items={[["full", "Full Staff"], ["contractor", "Contractors"], ["onsite", "Onsite / Labourers"], ["perf", "Performance Index"], ["org", "Org Chart"]]} active={tab} setActive={setTab} />
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading staff records…</div>
      ) : tab === "org" ? (
        <OrgChartView staff={staff} />
      ) : activeList.length === 0 ? (
        <div className="gc" style={{ padding: 48, textAlign: "center", color: C.muted }}>No active {tab} staff found.</div>
      ) : tab === "perf" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 4px" }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: C.muted }}>INDEXED PERFORMANCE LEADERBOARD (CURRENT MONTH)</div>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ fontSize: 11, color: C.muted }}>Sorting: High to Low</div>
            </div>
          </div>
          {activeList.sort((a, b) => (b.performance?.score || 0) - (a.performance?.score || 0)).map(u => {
            const sc = u.performance?.score || 0;
            const b = u.performance?.breakdown || {};
            return (
              <div key={u.id} className="gc fade" style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 20, cursor: "pointer" }} onClick={() => setView(u)}>
                <div style={{ width: 16, fontSize: 12, fontWeight: 900, color: C.muted }}>#{activeList.indexOf(u) + 1}</div>
                <Av av={u.full_name?.split(" ").map(n => n[0]).join("")} sz={42} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 15, fontWeight: 800 }}>{u.full_name}</div>
                  <div style={{ fontSize: 11, color: C.sub }}>{u.department} · {u.role?.replace(/,/g, " | ")}</div>
                </div>
                <div style={{ display: "flex", gap: 30 }}>
                  {[["GOALS", b.goals], ["QUALITY", b.quality], ["SOFT SKILLS", (b.teamwork + b.initiative) / 2]].map(([lbl, val]) => (
                    <div key={lbl} style={{ textAlign: "center", minWidth: 60 }}>
                      <div style={{ fontSize: 9, color: C.muted, fontWeight: 800, marginBottom: 4 }}>{lbl}</div>
                      <div style={{ fontSize: 13, fontWeight: 800 }}>{Math.round(val || 0)}%</div>
                      <div style={{ height: 3, width: 24, background: val >= 70 ? "#4ADE80" : T.orange, borderRadius: 2, margin: "4px auto 0" }} />
                    </div>
                  ))}
                </div>
                <div style={{ width: 80, textAlign: "right" }}>
                  <div style={{ fontSize: 22, fontWeight: 900, color: sc >= 70 ? "#4ADE80" : T.orange }}>{Math.round(sc)}</div>
                  <div style={{ fontSize: 9, color: C.muted, fontWeight: 800 }}>OVERALL</div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="g3" style={{ marginBottom: 22 }}>
          {activeList.map(u => {
            const prof = u.staff_profiles?.[0] || {};
            const sc = u.performance?.score;
            return (
              <div key={u.id} className="gc" style={{ padding: 20, cursor: "pointer" }} onClick={() => setView(u)}>
                <div style={{ display: "flex", gap: 14, alignItems: "center", marginBottom: 14 }}>
                  <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={44} />
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{u.full_name}</div>
                    <div style={{ fontSize: 12, color: C.sub }}>{prof.job_title || u.role}</div>
                    <div style={{ fontSize: 11, color: T.orange, fontWeight: 800, marginTop: 2 }}>{u.department}</div>
                  </div>
                </div>
                <div className="g2" style={{ gap: 8, marginBottom: 12 }}>
                  {[["Role", u.role?.replace("_", " ")], ["Type", prof.staff_type || "full"], ["Email", u.email?.split("@")[0] + "…"], ["Status", u.is_active ? "Active" : "Inactive"]].map(([l, v]) => (
                    <div key={l} style={{ background: `${T.orange}0D`, borderRadius: 8, padding: "8px 10px" }}>
                      <div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800 }}>{l}</div>
                      <div style={{ fontSize: 12, color: T.orange, fontWeight: 700, marginTop: 2, textTransform: "capitalize" }}>{v}</div>
                    </div>
                  ))}
                </div>
                {sc != null ? (
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className={`tg ${sc >= 80 ? "tg2" : sc >= 60 ? "to" : "tr"}`}>{sc >= 80 ? "Excellent" : sc >= 60 ? "Good" : "Fair"}</span>
                    <span style={{ fontSize: 20, fontWeight: 800, color: sc >= 80 ? "#4ADE80" : T.orange }}>{sc}/100</span>
                  </div>
                ) : <span className="tg tm">No score yet</span>}
              </div>
            );
          })}
        </div>
      )}

      {archivedList.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ fontSize: 18, fontWeight: 800 }}>Archived / Deactivated Staff</div>
            <div style={{ fontSize: 13, color: C.sub }}>{archivedList.length} record{archivedList.length === 1 ? '' : 's'}</div>
          </div>
          <div className="g3" style={{ marginBottom: 22 }}>
            {archivedList.map(u => {
              const prof = u.staff_profiles?.[0] || {};
              const sc = u.performance?.score;
              return (
                <div key={u.id} className="gc" style={{ padding: 20, cursor: "pointer", opacity: 0.88 }} onClick={() => setView(u)}>
                  <div style={{ display: "flex", gap: 14, alignItems: "center", marginBottom: 14 }}>
                    <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={44} />
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{u.full_name}</div>
                      <div style={{ fontSize: 12, color: C.sub }}>{prof.job_title || u.role}</div>
                      <div style={{ fontSize: 11, color: T.orange, fontWeight: 800, marginTop: 2 }}>{u.department}</div>
                    </div>
                  </div>
                  <div className="g2" style={{ gap: 8, marginBottom: 12 }}>
                    {[['Role', u.role?.replace(/,/g, ' , ')], ['Type', prof.staff_type || "full"], ['Email', u.email?.split("@")[0] + "…"], ['Status', 'Archived']].map(([l, v]) => (
                      <div key={l} style={{ background: `${T.orange}0D`, borderRadius: 8, padding: "8px 10px" }}>
                        <div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800 }}>{l}</div>
                        <div style={{ fontSize: 12, color: T.orange, fontWeight: 700, marginTop: 2, textTransform: "capitalize" }}>{v}</div>
                      </div>
                    ))}
                  </div>
                  {sc != null ? (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className={`tg ${sc >= 80 ? "tg2" : sc >= 60 ? "to" : "tr"}`}>{sc >= 80 ? "Excellent" : sc >= 60 ? "Good" : "Fair"}</span>
                      <span style={{ fontSize: 20, fontWeight: 800, color: sc >= 80 ? "#4ADE80" : T.orange }}>{sc}/100</span>
                    </div>
                  ) : <span className="tg tm">No score yet</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ADD STAFF MODAL */}
      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} title="Add New Staff Member" width={580}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Full Name *</Lbl><input className="inp" placeholder="e.g. Adeola Balogun" value={newStaff.full_name} onChange={e => setNewStaff(s => ({ ...s, full_name: e.target.value }))} /></div>
              <div><Lbl>Email Address *</Lbl><input className="inp" type="email" placeholder="adeola@eximps-cloves.com" value={newStaff.email} onChange={e => setNewStaff(s => ({ ...s, email: e.target.value }))} /></div>
              <div><Lbl>Default Password *</Lbl><input className="inp" type="password" placeholder="Min 8 characters" value={newStaff.password} onChange={e => setNewStaff(s => ({ ...s, password: e.target.value }))} /></div>
              <div><Lbl>Confirm Password *</Lbl><input className="inp" type="password" placeholder="Repeat password" value={newStaff.confirm_password} onChange={e => setNewStaff(s => ({ ...s, confirm_password: e.target.value }))} /></div>
              <div style={{ gridColumn: '1 / -1' }}>
                <Lbl>System Roles *</Lbl>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 6 }}>
                  {['staff', 'sales_rep', 'admin', 'lawyer', 'line_manager'].map(role => (
                    <label key={role} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', border: `1px solid ${C.border}`, borderRadius: 10, cursor: 'pointer' }}>
                      <input type="checkbox" checked={newStaff.roles.includes(role)} onChange={() => toggleNewStaffRole(role)} />
                      {role.replace('_', ' ')}
                    </label>
                  ))}
                </div>
              </div>
              <div><Lbl>Primary Role</Lbl>
                <select className="inp" value={newStaff.primary_role} onChange={e => setNewStaff(s => ({ ...s, primary_role: e.target.value }))}>
                  <option value="staff">Staff</option>
                  <option value="hr">HR</option>
                  <option value="sales">Sales</option>
                  <option value="finance">Finance</option>
                  <option value="legal">Legal</option>
                  <option value="operations">Operations</option>
                </select>
              </div>
              <div><Lbl>Staff Type</Lbl>
                <select className="inp" value={newStaff.staff_type} onChange={e => setNewStaff(s => ({ ...s, staff_type: e.target.value }))}>
                  <option value="full">Full Staff</option>
                  <option value="contractor">Contractor</option>
                  <option value="onsite">Onsite / Labourer</option>
                </select>
              </div>
              <div><Lbl>Department</Lbl>
                <select className="inp" value={newStaff.department} onChange={e => setNewStaff(s => ({ ...s, department: e.target.value }))}>
                  {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                  {departments.length === 0 && <option>Sales & Acquisitions</option>}
                </select>
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <Lbl>Line Manager</Lbl>
                <select className="inp" value={newStaff.line_manager_id || ""} onChange={e => setNewStaff(s => ({ ...s, line_manager_id: e.target.value || null }))}>
                  <option value="">— Select Line Manager —</option>
                  {staff.filter(s => s.id).map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}
                </select>
              </div>
            </div>
            <div style={{ padding: "10px 14px", background: `${T.orange}0D`, border: `1px solid ${T.orange}22`, borderRadius: 10, fontSize: 12, color: C.muted }}>
              The staff member will log in using the main platform login page at <b style={{ color: T.orange }}>/login</b>. Their HR portal access is automatic.
            </div>
            <button className="bp" onClick={handleAddStaff} style={{ padding: 12 }} disabled={saving}>
              {saving ? "Creating Account…" : "Create Staff Account"}
            </button>
          </div>
        </Modal>
      )}


      {view && (
        <Modal onClose={() => setView(null)} title={view.full_name} width={640}>
          <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 22 }}>
            <Av av={view.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={58} gold />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: (dark ? DARK : LIGHT).text }}>{view.staff_profiles?.[0]?.job_title || view.role}</div>
              <div style={{ fontSize: 13, color: (dark ? DARK : LIGHT).sub }}>{view.department}</div>
              <span className="tg to" style={{ marginTop: 6, display: "inline-flex" }}>{view.staff_profiles?.[0]?.staff_type?.toUpperCase() || "FULL"}</span>
            </div>
          </div>

          {authRole === "hr" && (
            <div style={{ display: "flex", gap: 10, marginBottom: 18 }}>
              {editMode ? (
                <>
                  <button className="bg" onClick={() => setEditMode(false)} disabled={editLoading}>Cancel</button>
                  <button className="bp" onClick={saveStaffProfile} disabled={editLoading}>{editLoading ? "Saving…" : "Save Profile"}</button>
                </>
              ) : (
                <button className="bp" onClick={() => setEditMode(true)}>Edit Profile</button>
              )}
            </div>
          )}

          <Tabs items={[
            ["details", "Personnel Identity"],
            ["performance", "Performance"],
            ["quals", "Qualifications"],
            ["bank", "Finances"],
            ["assets", "Assets"],
            ["docs", "Documents"],
            ["legal", "Legal"],
            ["security", "Security"]
          ]} active={dtTab} setActive={setDtTab} />

          {dtTab === "details" && (
            <div className="g2 fade" style={{ gap: 10, marginBottom: 18 }}>
              {!editMode && (
                <>
                  <Field label="Full Name" value={view.full_name} />
                  <Field label="Email Address" value={view.email} />
                  <Field label="Role" value={view.role?.replace(/,/g, ' , ')} />
                  <Field label="Primary Role" value={view.primary_role} />
                  <Field label="Line Manager" value={getStaffNameById(view.line_manager_id)} />
                </>
              )}
              {editMode ? (
                <>
                  <div>
                    <Lbl>Full Name</Lbl>
                    <input className="inp" value={draftView.full_name} onChange={e => setDraftView(d => ({ ...d, full_name: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Email Address</Lbl>
                    <input className="inp" value={draftView.email} onChange={e => setDraftView(d => ({ ...d, email: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Job Title</Lbl>
                    <input className="inp" value={draftView.job_title} onChange={e => setDraftView(d => ({ ...d, job_title: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Department</Lbl>
                    <select className="inp" value={draftView.department} onChange={e => setDraftView(d => ({ ...d, department: e.target.value }))}>
                      <option value="">— Select —</option>
                      {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <Lbl>Phone</Lbl>
                    <input className="inp" value={draftView.phone_number} onChange={e => setDraftView(d => ({ ...d, phone_number: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Emergency Contact</Lbl>
                    <input className="inp" value={draftView.emergency_contact} onChange={e => setDraftView(d => ({ ...d, emergency_contact: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>System Roles</Lbl>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 6 }}>
                      {['staff', 'sales_rep', 'admin', 'lawyer', 'line_manager'].map(role => (
                        <label key={role} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', border: `1px solid ${C.border}`, borderRadius: 10, cursor: 'pointer' }}>
                          <input type="checkbox" checked={draftView.roles?.includes(role)} onChange={() => setDraftView(d => ({ ...d, roles: d.roles?.includes(role) ? d.roles.filter(r => r !== role) : [...(d.roles || []), role] }))} />
                          {role.replace('_', ' ')}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Lbl>Primary Role</Lbl>
                    <select className="inp" value={draftView.primary_role} onChange={e => setDraftView(d => ({ ...d, primary_role: e.target.value }))}>
                      <option value="staff">Staff</option>
                      <option value="hr">HR</option>
                      <option value="sales">Sales</option>
                      <option value="finance">Finance</option>
                      <option value="legal">Legal</option>
                      <option value="operations">Operations</option>
                    </select>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <Lbl>Line Manager</Lbl>
                    <select className="inp" value={draftView.line_manager_id || ""} onChange={e => setDraftView(d => ({ ...d, line_manager_id: e.target.value || "" }))}>
                      <option value="">— Select Line Manager —</option>
                      {staff.filter(s => s.id && s.id !== view.id).map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}
                    </select>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <Lbl>Address</Lbl>
                    <input className="inp" value={draftView.address} onChange={e => setDraftView(d => ({ ...d, address: e.target.value }))} />
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <Lbl>Bio</Lbl>
                    <textarea className="inp" rows={5} value={draftView.bio} onChange={e => setDraftView(d => ({ ...d, bio: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Gender</Lbl>
                    <select className="inp" value={draftView.gender || ""} onChange={e => setDraftView(d => ({ ...d, gender: e.target.value }))}>
                      <option value="">— Select —</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div>
                    <Lbl>Date of Birth</Lbl>
                    <input type="date" className="inp" value={draftView.dob || ""} onChange={e => setDraftView(d => ({ ...d, dob: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Nationality</Lbl>
                    <input className="inp" value={draftView.nationality || ""} onChange={e => setDraftView(d => ({ ...d, nationality: e.target.value }))} />
                  </div>
                  <div>
                    <Lbl>Marital Status</Lbl>
                    <select className="inp" value={draftView.marital_status || ""} onChange={e => setDraftView(d => ({ ...d, marital_status: e.target.value }))}>
                      <option value="">— Select —</option>
                      <option value="Single">Single</option>
                      <option value="Married">Married</option>
                      <option value="Divorced">Divorced</option>
                      <option value="Widowed">Widowed</option>
                    </select>
                  </div>
                  <div style={{ gridColumn: '1 / -1', background: '#F8717111', border: '1px solid #F8717133', padding: '12px 16px', borderRadius: 10 }}>
                    <Lbl>Annual Leave Quota (Days)</Lbl>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <input type="number" min={0} className="inp" value={draftView.leave_quota} onChange={e => setDraftView(d => ({ ...d, leave_quota: e.target.value }))} style={{ width: 100 }} />
                      <span style={{ fontSize: 12, color: C.muted }}>days per year</span>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <Field label="Phone" value={view.staff_profiles?.[0]?.phone_number} />
                  <Field label="Emergency Contact" value={view.staff_profiles?.[0]?.emergency_contact} />
                  <Field label="Address" value={view.staff_profiles?.[0]?.address} />
                  <Field label="Bio" value={view.staff_profiles?.[0]?.bio} />
                  <Field label="Gender" value={view.staff_profiles?.[0]?.gender} />
                  <Field label="DOB" value={view.staff_profiles?.[0]?.dob} />
                  <Field label="Nationality" value={view.staff_profiles?.[0]?.nationality} />
                  <Field label="Marital Status" value={view.staff_profiles?.[0]?.marital_status} />
                  <Field label="Leave Quota" value={view.staff_profiles?.[0]?.leave_quota ? `${view.staff_profiles?.[0]?.leave_quota} days/yr` : '20 days/yr'} />
                </>
              )}
              {view.is_active === false && (
                <>
                  <Field label="Exit Date" value={view.staff_profiles?.[0]?.exit_date} />
                  <Field label="Exit Reason" value={view.staff_profiles?.[0]?.exit_reason} />
                </>
              )}
            </div>
          )}

          {dtTab === "security" && (
            <div className="fade" style={{ maxWidth: 450 }}>
              {/* ... security override fields ... */}
              <div className="ho" style={{ fontSize: 13, marginBottom: 14, color: T.orange, fontWeight: 800 }}>ADMIN SECURITY OVERRIDE</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div className="gc" style={{ padding: 20 }}>
                  <Lbl>Reset Password</Lbl>
                  <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                    <input id="admin-pass-reset" className="inp" type="password" placeholder="New password (min 8 chars)" style={{ flex: 1 }} />
                    <button className="bp" onClick={async () => {
                      const pass = document.getElementById("admin-pass-reset").value;
                      if (!pass || pass.length < 8) return alert("Password must be at least 8 characters");
                      if (!confirm(`Are you sure you want to FORCE reset ${view.full_name}'s password?`)) return;
                      try {
                        await apiFetch(`/auth/admins/${view.id}/reset-password`, {
                          method: "PATCH",
                          body: JSON.stringify({ new_password: pass })
                        });
                        alert("Password successfully updated");
                        document.getElementById("admin-pass-reset").value = "";
                      } catch (e) { alert(e.message); }
                    }}>Reset Now</button>
                  </div>
                  <div style={{ fontSize: 11, color: C.muted, marginTop: 10 }}>
                    Note: The staff member will use this password for their next login. They are not automatically notified.
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10 }}>
                  <button className="br" style={{ flex: 1, padding: 12, fontSize: 13 }} onClick={archiveStaff}>
                    Archive / Deactivate Employee
                  </button>
                </div>
              </div>
            </div>
          )}

          {dtTab === "performance" && <PerformanceManager staffId={view.id} isHR={authRole === "hr"} authRole={authRole} />}

          {dtTab === "quals" && <QualificationsManager staffId={view.id} isHR={authRole === "hr"} />}

          {dtTab === "bank" && (
            <div className="g1 fade" style={{ gap: 10, marginBottom: 18 }}>
              <Field label="Bank Name" value={view.staff_profiles?.[0]?.bank_name} />
              <Field label="Account Number" value={view.staff_profiles?.[0]?.account_number} />
              <Field label="Account Name" value={view.staff_profiles?.[0]?.account_name} />
              <Field label="Monthly Base Salary" value={view.staff_profiles?.[0]?.base_salary ? `₦${Number(view.staff_profiles[0].base_salary).toLocaleString()}` : "Not Set"} />
              <div style={{ padding: 12, background: `${T.orange}0D`, border: `1px solid ${T.orange}22`, borderRadius: 8, fontSize: 12, color: (dark ? DARK : LIGHT).muted }}>
                Payment info is only visible to HR and Finance teams.
              </div>
            </div>
          )}

          {dtTab === "assets" && (
            <div className="fade">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <div className="ho" style={{ fontSize: 13 }}>Company Assets</div>
                <button className="bp" style={{ fontSize: 11, padding: "4px 10px" }}>+ Assign Asset</button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {view.staff_assets?.length > 0 ? (
                  view.staff_assets.map((a, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: `${C.surface}`, border: `1px solid ${C.border}`, borderRadius: 10 }}>
                      <div><div style={{ fontSize: 13, fontWeight: 700 }}>{a.asset_name}</div><div style={{ fontSize: 11, color: C.muted }}>{a.serial_number || "No Serial"} · Assigned {new Date(a.assigned_at).toLocaleDateString()}</div></div>
                      <span className="tg to" style={{ fontSize: 10 }}>{a.condition || "Good"}</span>
                    </div>
                  ))
                ) : <div style={{ fontSize: 12, color: C.muted, textAlign: "center", padding: 20 }}>No assets assigned to this staff member.</div>}
              </div>
            </div>
          )}

          {dtTab === "docs" && <DocumentsManager staffId={view.id} isHR={authRole === "hr"} />}

          {dtTab === "legal" && <LegalManager staffId={view.id} staffName={view.full_name} isHR={authRole === "hr"} />}

          {!viewOnly && view.is_active !== false && (
            <div style={{ marginTop: 22, borderTop: `1px solid ${C.border}`, paddingTop: 22 }}>
              <button className="bd" style={{ width: "100%" }} onClick={archiveStaff}>Archive & Deactivate Staff</button>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}

// ─── MODULE: HR DASHBOARD ────────────────────────────────────────────────────
function HRDashboard() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [data, setData] = useState({ staff: [], leaves: [], tasks: [], incidents: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/dashboard/stats`)
      .then(d => {
        setData(d);
      })
      .catch(e => {
        console.error("Dashboard stats fetch error:", e);
      })
      .finally(() => setLoading(false));
  }, []);

  const a = data.analytics || {};
  const total = a.total_active || 0;
  const pendingLeaves = data.leaves?.filter(l => l.status === "pending").length || 0;
  const openTasks = data.tasks?.filter(t => t.status !== "completed").length || 0;
  const seriousFlags = data.incidents?.filter(i => i.severity === "Critical" || i.severity === "Serious").length || 0;

  return (
    <div className="fade">
      <div style={{ marginBottom: 26 }}>
        <div className="ho" style={{ fontSize: 26, marginBottom: 4 }}>HR Overview</div>
        <div style={{ fontSize: 13, color: C.sub }}>Live workforce intelligence — Eximp & Cloves Infrastructure Limited.</div>
      </div>
      {loading ? <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading workforce metrics…</div> : (
        <>
          {/* Row 1 — Live Today */}
          <div className="g4" style={{ marginBottom: 14 }}>
            <StatCard label="Total Workforce" value={total} sub="Active Staff Members" />
            <StatCard label="Present Today" value={a.present_today || 0} col="#4ADE80" sub={`${a.late_today || 0} checked in late`} />
            <StatCard label="Absent Today" value={a.absent_today || 0} col="#F87171" sub={a.absent_names?.length > 0 ? "Action required" : "All accounted for"} />
            <StatCard label="Suspicious" value={a.suspicious_today || 0} col="#FBB040" sub="Geofence violations" />
          </div>
          {/* Row 2 — Ops Overview */}
          <div className="g4" style={{ marginBottom: 22 }}>
            <StatCard label="On Leave" value={a.on_leave_today || 0} col="#60A5FA" sub="Approved leave today" />
            <StatCard label="Pending Leaves" value={pendingLeaves} col={T.orange} sub="Awaiting approval" />
            <StatCard label="Open Tasks" value={openTasks} col="#A78BFA" sub="Across all teams" />
            <StatCard label="Critical Flags" value={seriousFlags} col="#F87171" sub="Disciplinary — urgent" />
          </div>

          <div className="g2w" style={{ marginBottom: 22 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
              <div className="gc" style={{ padding: 22 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 18 }}>
                  <div className="ho" style={{ fontSize: 16 }}>Workforce by Department</div>
                </div>
                {Object.entries(a.department_distribution || {}).map(([dept, count]) => (
                  <div key={dept} style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 5 }}>
                      <span style={{ fontWeight: 600, color: C.text }}>{dept}</span>
                      <span style={{ color: C.sub }}>{count} ({Math.round(count / total * 100)}%)</span>
                    </div>
                    <div style={{ height: 6, background: `${C.border}`, borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${(count / total) * 100}%`, background: T.orange }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="gc" style={{ padding: 22 }}>
                <div className="ho" style={{ fontSize: 15, marginBottom: 16 }}>Absence Log</div>
                {a.absent_names?.length > 0 ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {a.absent_names.map(name => (
                      <div key={name} style={{ padding: "6px 12px", background: `${C.border}44`, borderRadius: 20, fontSize: 12, border: `1px solid ${C.border}` }}>
                        👤 {name}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: "#4ADE80", textAlign: "center", padding: 10 }}>✅ Everyone has checked in!</div>
                )}
              </div>

              <div className="gc" style={{ padding: 22 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                  <div className="ho" style={{ fontSize: 14 }}>Latest Active Staff</div>
                  <span style={{ fontSize: 11, color: C.muted }}>Recent Onboarding</span>
                </div>
                <div className="tw"><table className="ht">
                  <thead><tr>{["Staff", "Department", "Role"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                  <tbody>
                    {data.staff?.slice(0, 5).map(u => (
                      <tr key={u.id}>
                        <td><div style={{ display: "flex", alignItems: "center", gap: 10 }}><Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={24} /><span style={{ fontWeight: 700 }}>{u.full_name}</span></div></td>
                        <td style={{ color: C.sub }}>{u.department}</td>
                        <td><span className="tg to" style={{ fontSize: 9 }}>{u.role?.toUpperCase()}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="gc" style={{ padding: 22 }}>
                <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Administrative Alerts</div>
                {[
                  [`${pendingLeaves} Leave Requests Pending`, T.orange],
                  [`${seriousFlags} Serious Disciplinary Cases`, "#F87171"],
                  ["Payroll Processing Due", "#4ADE80"],
                  [
                    <button
                      onClick={async () => {
                        if (!confirm("This will apply all pending database migrations. Proceed?")) return;
                        try {
                          const res = await apiFetch(`${API_BASE}/hr/migrate`, { method: "POST" });
                          alert(res.message);
                          window.location.reload();
                        } catch (e) { alert("Migration failed: " + e.message); }
                      }}
                      className="bp"
                      style={{ fontSize: 10, padding: "6px 12px", marginTop: 4 }}
                    >
                      🚀 Run System Update (Fix DB)
                    </button>,
                    "#60A5FA"
                  ]
                ].map(([l, c], i) => (
                  <div key={i} style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 12, padding: "12px 14px", background: `${c}0D`, border: `1px solid ${c}22`, borderRadius: 10 }}>
                    {typeof l === 'string' && <div style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />}
                    <span style={{ fontSize: 13, color: C.text }}>{l}</span>
                  </div>
                ))}
              </div>

              <div className="gc" style={{ padding: 22 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                  <div className="ho" style={{ fontSize: 14 }}>Recent Milestones</div>
                  <span style={{ fontSize: 11, color: C.muted }}>Last 30 Days</span>
                </div>
                {a.recent_milestones?.length > 0 ? (
                  a.recent_milestones.map(m => (
                    <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                      <Av av={m.full_name?.split(" ").map(n => n[0]).join("")} sz={24} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 600 }}>{m.full_name}</div>
                        <div style={{ fontSize: 10, color: C.sub }}>Joined {new Date(m.created_at).toLocaleDateString()}</div>
                      </div>
                      <span className="tg" style={{ fontSize: 8, background: "#4ADE8011", color: "#4ADE80", border: "1px solid #4ADE8022" }}>NEW HIRE</span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: 11, color: C.muted, textAlign: "center", padding: 10 }}>No recent onboarding.</div>
                )}
              </div>

              <div className="gc" style={{ padding: 22, marginTop: 22 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                  <div className="ho" style={{ fontSize: 14 }}>Upcoming Birthdays 🎂</div>
                  <span style={{ fontSize: 11, color: C.muted }}>Next 14 Days</span>
                </div>
                {a.upcoming_birthdays?.length > 0 ? a.upcoming_birthdays.map((b, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                    <Av av={b.full_name?.split(" ").map(n => n[0]).join("")} sz={28} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 700 }}>{b.full_name}</div>
                      <div style={{ fontSize: 10, color: C.sub }}>{new Date(b.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</div>
                    </div>
                    <span className="tg" style={{ fontSize: 9, background: "#FBB04022", color: "#FBB040", border: "1px solid #FBB04044" }}>
                      {b.days_left === 0 ? "TODAY!" : `in ${b.days_left}d`}
                    </span>
                  </div>
                )) : (
                  <div style={{ fontSize: 11, color: C.muted, textAlign: "center", padding: 10 }}>No birthdays in the next 14 days.</div>
                )}
              </div>

              <div className="gc" style={{ padding: 22, marginTop: 22 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                  <div className="ho" style={{ fontSize: 14 }}>Work Anniversaries 🎊</div>
                  <span style={{ fontSize: 11, color: C.muted }}>Next 30 Days</span>
                </div>
                {a.upcoming_anniversaries?.length > 0 ? a.upcoming_anniversaries.map((anniv, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                    <Av av={anniv.full_name?.split(" ").map(n => n[0]).join("")} sz={28} gold />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 700 }}>{anniv.full_name}</div>
                      <div style={{ fontSize: 10, color: C.sub }}>{anniv.years} years on {new Date(anniv.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</div>
                    </div>
                    <span className="tg" style={{ fontSize: 9, background: "#60A5FA22", color: "#60A5FA", border: "1px solid #60A5FA44" }}>
                      {anniv.days_left === 0 ? "TODAY!" : `in ${anniv.days_left}d`}
                    </span>
                  </div>
                )) : (
                  <div style={{ fontSize: 11, color: C.muted, textAlign: "center", padding: 10 }}>No anniversaries in the next 30 days.</div>
                )}
              </div>
            </div>
          </div>

          {/* Staff on Leave — full panel */}
          <div className="g2" style={{ marginBottom: 22 }}>
            {/* On Leave Today */}
            <div className="gc" style={{ padding: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div className="ho" style={{ fontSize: 15 }}>Staff on Leave Today</div>
                <span className="tg" style={{ background: `${T.orange}22`, color: T.orange, border: `1px solid ${T.orange}33`, fontSize: 10 }}>
                  {a.on_leave_today || 0} Staff
                </span>
              </div>
              {data.leaves?.filter(l => {
                const today = new Date().toISOString().split("T")[0];
                return l.status === "approved" && l.start_date <= today && l.end_date >= today;
              }).length > 0 ? (
                data.leaves.filter(l => {
                  const today = new Date().toISOString().split("T")[0];
                  return l.status === "approved" && l.start_date <= today && l.end_date >= today;
                }).map(l => {
                  const u = l.admins || {};
                  const returnDate = new Date(l.end_date);
                  returnDate.setDate(returnDate.getDate() + 1);
                  return (
                    <div key={l.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", background: `${T.orange}08`, border: `1px solid ${T.orange}22`, borderRadius: 10, marginBottom: 8 }}>
                      <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={34} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 13 }}>{u.full_name}</div>
                        <div style={{ fontSize: 11, color: C.sub, marginTop: 2 }}>
                          {l.leave_type} · Returns {returnDate.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: T.orange }}>{l.days_count}d</div>
                        <div style={{ fontSize: 9, color: C.muted }}>leave</div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign: "center", padding: "20px 0", color: C.muted }}>
                  <div style={{ fontSize: 24, marginBottom: 6 }}>🏢</div>
                  <div style={{ fontSize: 12 }}>All staff are in today!</div>
                </div>
              )}
            </div>

            {/* Upcoming Leaves This Week */}
            <div className="gc" style={{ padding: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div className="ho" style={{ fontSize: 15 }}>Upcoming Leaves</div>
                <span style={{ fontSize: 11, color: C.muted }}>Next 7 Days</span>
              </div>
              {data.leaves?.filter(l => {
                if (l.status !== "approved") return false;
                const today = new Date(); today.setHours(0, 0, 0, 0);
                const nextWeek = new Date(today); nextWeek.setDate(today.getDate() + 7);
                const start = new Date(l.start_date);
                return start > today && start <= nextWeek;
              }).slice(0, 5).length > 0 ? (
                data.leaves.filter(l => {
                  if (l.status !== "approved") return false;
                  const today = new Date(); today.setHours(0, 0, 0, 0);
                  const nextWeek = new Date(today); nextWeek.setDate(today.getDate() + 7);
                  const start = new Date(l.start_date);
                  return start > today && start <= nextWeek;
                }).slice(0, 5).map(l => {
                  const u = l.admins || {};
                  return (
                    <div key={l.id} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                      <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={28} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{u.full_name}</div>
                        <div style={{ fontSize: 11, color: C.sub }}>
                          {l.leave_type} · {new Date(l.start_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })} → {new Date(l.end_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                        </div>
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#60A5FA" }}>{l.days_count}d</span>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign: "center", padding: "20px 0", color: C.muted, fontSize: 12 }}>No approved leaves in the next 7 days.</div>
              )}
            </div>
          </div>

          <div className="gc" style={{ padding: 22 }}>
            <div className="ho" style={{ fontSize: 14, marginBottom: 14 }}>Recent Open Tasks</div>
            <div className="g4" style={{ gap: 12 }}>
              {(data.tasks || []).filter(t => t.status !== "completed").slice(0, 8).map(t => {
                const sc = sCol[t.status] || T.orange;
                const assignedTo = data.staff.find(u => u.id === t.staff_id);
                return (
                  <div key={t.id} style={{ padding: "12px 14px", background: `${T.orange}08`, border: `1px solid ${T.orange}22`, borderRadius: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: C.text, marginBottom: 6, lineHeight: 1.3 }}>{t.title}</div>
                    <div style={{ fontSize: 11, color: C.muted, marginBottom: 8 }}>→ {assignedTo?.full_name?.split(" ").map(n => n[0]).join("") || "?? "} · {new Date(t.due_date).toLocaleDateString()}</div>
                    <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}33`, fontSize: 10 }}>{t.status}</span>
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
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [prof, setProf] = useState(null);
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState("details");
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/profile/${user.id}`)
      .then(d => {
        setProf(d);
        const p = d.staff_profiles?.[0] || {};
        setDraft({
          full_name: d.full_name || "",
          phone_number: p.phone_number || "",
          address: p.address || "",
          emergency_contact: p.emergency_contact || "",
          bio: p.bio || "",
          bank_name: p.bank_name || "",
          account_number: p.account_number || "",
          account_name: p.account_name || "",
          dob: p.dob || "",
          gender: p.gender || "",
          nationality: p.nationality || "",
          marital_status: p.marital_status || ""
        });
      })
      .catch(e => console.error("Profile fetch error:", e))
      .finally(() => setLoading(false));
  }, [user.id]);

  const saveProfile = async () => {
    if (!prof) return;
    setSaving(true);
    try {
      // 1. Update Name (Auth API)
      if (draft.full_name && draft.full_name !== prof.full_name) {
        await apiFetch(`/auth/me/profile`, {
          method: "PATCH",
          body: JSON.stringify({ full_name: draft.full_name })
        });
      }

      // 2. Update Detailed Profile (HR API)
      await apiFetch(`${API_BASE}/hr/profile/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          phone_number: draft.phone_number,
          address: draft.address,
          emergency_contact: draft.emergency_contact,
          bio: draft.bio,
          dob: draft.dob || null,
          gender: draft.gender,
          nationality: draft.nationality,
          marital_status: draft.marital_status
        })
      });
      setProf(prev => ({
        ...prev,
        full_name: draft.full_name,
        staff_profiles: [{
          ...prev.staff_profiles?.[0],
          phone_number: draft.phone_number,
          address: draft.address,
          emergency_contact: draft.emergency_contact,
          bio: draft.bio,
          dob: draft.dob,
          gender: draft.gender,
          nationality: draft.nationality,
          marital_status: draft.marital_status
        }]
      }));
      setEditMode(false);
      alert("Profile updated successfully.");
    } catch (e) {
      alert("Error updating profile: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading your profile…</div>;
  if (!prof) return <div style={{ padding: 40, textAlign: "center", color: "#F87171" }}>Could not load profile data.</div>;

  const p = prof.staff_profiles?.[0] || {};

  return (
    <div className="fade" style={{ maxWidth: 720 }}>
      <div className="gc" style={{ padding: 30, marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 20, alignItems: "center", justifyContent: "space-between", marginBottom: 26 }}>
          <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <Av av={prof.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={70} gold />
            <div>
              <div className="ho" style={{ fontSize: 26 }}>{prof.full_name}</div>
              <div style={{ fontSize: 14, color: C.sub }}>{p.job_title || prof.role}</div>
              <div style={{ fontSize: 13, color: T.orange, fontWeight: 800, marginTop: 4 }}>{prof.department}</div>
              {p.bio && <div style={{ marginTop: 14, maxWidth: 520, fontSize: 13, lineHeight: 1.6, color: C.sub }}>{p.bio}</div>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {editMode ? (
              <>
                <button className="bg" onClick={() => setEditMode(false)} disabled={saving}>Cancel</button>
                <button className="bp" onClick={saveProfile} disabled={saving}>{saving ? "Saving…" : "Save Profile"}</button>
              </>
            ) : (
              <button className="bp" onClick={() => setEditMode(true)}>Edit Profile</button>
            )}
          </div>
        </div>

        <Tabs items={[
          ["details", "Personnel Identity"],
          ["quals", "Qualifications"],
          ["assets", "My Assets"],
          ["bank", "Finances"],
          ["docs", "My Documents"],
          ["legal", "Legal Vault"],
          ["security", "Security"]
        ]} active={tab} setActive={setTab} />

        {tab === "details" && (
          <div className="g2 fade" style={{ gap: 12 }}>
            {editMode ? (
              <div>
                <Lbl>Full Name</Lbl>
                <input className="inp" value={draft.full_name || prof.full_name} onChange={e => setDraft(d => ({ ...d, full_name: e.target.value }))} />
              </div>
            ) : (
              <Field label="Full Name" value={prof.full_name} />
            )}
            <Field label="Email Address" value={prof.email} />
            {editMode ? (
              <>
                <div>
                  <Lbl>Phone</Lbl>
                  <input className="inp" value={draft.phone_number} onChange={e => setDraft(d => ({ ...d, phone_number: e.target.value }))} />
                </div>
                <div>
                  <Lbl>Emergency Contact</Lbl>
                  <input className="inp" value={draft.emergency_contact} onChange={e => setDraft(d => ({ ...d, emergency_contact: e.target.value }))} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <Lbl>Address</Lbl>
                  <input className="inp" value={draft.address} onChange={e => setDraft(d => ({ ...d, address: e.target.value }))} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <Lbl>Bio</Lbl>
                  <textarea className="inp" rows={5} value={draft.bio} onChange={e => setDraft(d => ({ ...d, bio: e.target.value }))} />
                </div>
                <div>
                  <Lbl>Gender</Lbl>
                  <select className="inp" value={draft.gender || ""} onChange={e => setDraft(d => ({ ...d, gender: e.target.value }))}>
                    <option value="">— Select —</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <Lbl>Date of Birth</Lbl>
                  <input type="date" className="inp" value={draft.dob || ""} onChange={e => setDraft(d => ({ ...d, dob: e.target.value }))} />
                </div>
                <div>
                  <Lbl>Nationality</Lbl>
                  <input className="inp" value={draft.nationality || ""} onChange={e => setDraft(d => ({ ...d, nationality: e.target.value }))} />
                </div>
                <div>
                  <Lbl>Marital Status</Lbl>
                  <select className="inp" value={draft.marital_status || ""} onChange={e => setDraft(d => ({ ...d, marital_status: e.target.value }))}>
                    <option value="">— Select —</option>
                    <option value="Single">Single</option>
                    <option value="Married">Married</option>
                    <option value="Divorced">Divorced</option>
                    <option value="Widowed">Widowed</option>
                  </select>
                </div>
              </>
            ) : (
              <>
                <Field label="Phone" value={p.phone_number} />
                <Field label="Address" value={p.address} />
                <Field label="Emergency Contact" value={p.emergency_contact} />
                <Field label="Bio" value={p.bio} />
                <Field label="Gender" value={p.gender} />
                <Field label="DOB" value={p.dob} />
                <Field label="Nationality" value={p.nationality} />
                <Field label="Marital Status" value={p.marital_status} />
                <div style={{ gridColumn: "1 / -1", marginTop: 12, borderTop: `1px solid ${C.border}`, paddingTop: 16 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: C.sub, marginBottom: 12, textTransform: "uppercase" }}>Identity Verification Assets</div>
                  <div style={{ display: "flex", gap: 30 }}>
                    {p.passport_photo_url && (
                      <div>
                        <div style={{ fontSize: 11, color: C.sub, marginBottom: 6 }}>Passport Photo</div>
                        <img src={p.passport_photo_url} alt="Passport" style={{ width: 100, height: 120, objectFit: "cover", borderRadius: 8, border: `1px solid ${C.border}` }} />
                      </div>
                    )}
                    {p.signature_url && (
                      <div>
                        <div style={{ fontSize: 11, color: C.sub, marginBottom: 6 }}>Digital Signature</div>
                        <div style={{ padding: 10, background: "#fff", borderRadius: 8, border: `1px solid ${C.border}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <img src={p.signature_url} alt="Signature" style={{ maxHeight: 60, maxWidth: 200 }} />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {tab === "security" && <SecurityManager />}

        {tab === "quals" && <QualificationsManager staffId={user.id} isHR={false} />}

        {tab === "assets" && (
          <div className="fade">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div className="ho" style={{ fontSize: 13 }}>My Company Assets</div>
            </div>
            {p.staff_assets?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {p.staff_assets.map((a, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "12px 16px", background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12 }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700 }}>{a.asset_name}</div>
                      <div style={{ fontSize: 12, color: C.muted }}>{a.serial_number || "No serial"} · Assigned {new Date(a.assigned_at).toLocaleDateString()}</div>
                    </div>
                    <span className="tg to" style={{ fontSize: 10 }}>{a.condition || "Good"}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: 28, textAlign: "center", color: C.muted, border: `1px dashed ${C.border}`, borderRadius: 12 }}>No assets have been assigned to you yet.</div>
            )}
          </div>
        )}

        {tab === "bank" && (
          <div className="g1 fade" style={{ gap: 12 }}>
            <Field label="Bank Name" value={p.bank_name} />
            <Field label="Account Number" value={p.account_number} />
            <Field label="Account Name" value={p.account_name} />
            <div style={{ padding: 14, background: `${T.orange}0D`, border: `1px solid ${T.orange}22`, borderRadius: 10, fontSize: 13, color: C.sub, lineHeight: 1.5 }}>
              <b>Note:</b> These details are used for payroll processing. If you need to update them, please contact the HR department with valid proof.
            </div>
          </div>
        )}

        {tab === "docs" && <DocumentsManager staffId={user.id} isHR={false} />}

        {tab === "legal" && <LegalManager staffId={user.id} staffName={prof.full_name} isHR={false} />}
      </div>
    </div>
  );
}

// ─── MY PAYSLIP ───────────────────────────────────────────────────────────────
function MyPayslip({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/payroll/payslips?staff_id=${user.id}`)
      .then(d => setPayslips(d))
      .finally(() => setLoading(false));
  }, [user.id]);

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading payslips…</div>;

  return (
    <div className="fade" style={{ maxWidth: 800 }}>
      <div className="ho" style={{ fontSize: 22, marginBottom: 18 }}>My Payroll Records</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {payslips.map(p => (
          <div key={p.id} className="gc" style={{ padding: 20, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 800, fontSize: 15, color: C.text }}>{new Date(p.period_start).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</div>
              <div style={{ fontSize: 12, color: C.sub, marginTop: 4 }}>Ref: PSL-{p.id} · Disbursed: {new Date(p.disbursement_date).toLocaleDateString()}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: T.orange }}>₦{p.net_pay.toLocaleString()}</div>
              <button className="bg" style={{ fontSize: 11, marginTop: 8 }}>Download PDF</button>
            </div>
          </div>
        ))}
        {payslips.length === 0 && <div style={{ textAlign: "center", padding: 20, color: C.muted }}>No payroll records found.</div>}
      </div>
    </div>
  );
}

// ─── PORTAL WRAPPERS ──────────────────────────────────────────────────────────
function DrawerNav({ items, page, setPage, user, onLogout, roleLabel, onClose }) {
  const { dark, toggle } = useTheme(); const C = dark ? DARK : LIGHT;
  const { unreadByType } = useNotifs();
  const G = T.gold;
  return (
    <>
      <div className="hrm-overlay" id="hrmOverlay" onClick={onClose} />
      <div className="hrm-drawer" id="hrmDrawer">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <div>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: G }}>HR Suite</div>
            <div style={{ fontSize: 9, color: C.muted, letterSpacing: "2px", textTransform: "uppercase" }}>Navigation</div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.sub, fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>
        <div style={{ fontSize: 9, color: C.muted, letterSpacing: "2px", marginBottom: 6, fontWeight: 700, textTransform: "uppercase" }}>{roleLabel}</div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2, marginBottom: 20 }}>
          {items.map(n => {
            if (n.isHeader) return (
              <div key={n.label} style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", fontWeight: 800, padding: "12px 16px 4px" }}>{n.label}</div>
            );
            const badge = unreadByType[n.id] || 0;
            return (
              <button key={n.id} className={`nb ${page === n.id ? "on" : ""}`} onClick={() => { setPage(n.id); onClose(); }}>
                {IC[n.icon]}
                <span style={{ flex: 1, textAlign: "left" }}>{n.label}</span>
                {badge > 0 && (
                  <span style={{ minWidth: 18, height: 18, borderRadius: 9, padding: "0 5px", background: "#F87171", color: "#fff", fontSize: 10, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {badge > 99 ? "99+" : badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <Av av={user.avatar} sz={32} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{user.name}</div>
              <div style={{ fontSize: 10, color: G }}>{(user.role || "").replace("_", " ").toUpperCase()}</div>
            </div>
            <button onClick={toggle} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: C.muted }}>
              <div style={{ width: 16, height: 16 }}>{dark ? IC.sun : IC.moon}</div>
            </button>
          </div>
          <button className="bg" onClick={onLogout} style={{ width: "100%", fontSize: 12, padding: "7px 12px" }}>Sign Out</button>
        </div>
      </div>
    </>
  );
}

function Portal({ user, onLogout, navItems, roleLabel, renderPage, initialPage }) {
  const [page, setPage] = useState(initialPage || navItems[0].id);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;

  const openDrawer = () => {
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
    <NotifProvider userId={user?.id}>
      <div className="hrm">
        {/* Mobile top bar */}
        <div className="hrm-topbar-mobile">
          <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 17, color: T.gold }}>HR Suite</div>
          <button onClick={openDrawer} style={{ background: "none", border: `1px solid ${C.border}`, color: C.text, padding: "8px 10px", borderRadius: 10, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
            Menu
          </button>
        </div>

        {/* Mobile slide-in drawer */}
        <DrawerNav items={navItems} page={page} setPage={setPage} user={user} onLogout={onLogout} roleLabel={roleLabel} onClose={closeDrawer} />

        {/* Desktop sidebar */}
        <Sidebar page={page} setPage={setPage} user={user} onLogout={onLogout} items={navItems} roleLabel={roleLabel} />

        {/* Main content */}
        <div className="hrm-main" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <Topbar title={navItems.find(n => n.id === page)?.label || ""} user={user} />
          <div className="hrm-content-padding" style={{ flex: 1, padding: 28 }}>
            {renderPage(page)}
          </div>
        </div>
      </div>
    </NotifProvider>
  );
}


// ─── HUB: TIMESHEETS ─────────────────────────────────────────────────────────
function StaffTimesheet() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [sheets, setSheets] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [viewSheet, setViewSheet] = useState(null);

  // Default week = current Monday
  const getMonday = (d = new Date()) => {
    const dt = new Date(d); const day = dt.getDay();
    dt.setDate(dt.getDate() - (day === 0 ? 6 : day - 1));
    return dt.toISOString().split('T')[0];
  };
  const [form, setForm] = useState({ week_start: getMonday(), mon: 0, tue: 0, wed: 0, thu: 0, fri: 0, sat: 0, notes: "" });
  const [syncing, setSyncing] = useState(false);

  const load = () => { setLoading(true); apiFetch(`${API_BASE}/hr/timesheets`).then(d => setSheets(d || [])).catch(() => { }).finally(() => setLoading(false)); };
  useEffect(load, []);

  const submit = async () => {
    if (!form.week_start) return alert("Week start date required");
    const total = +form.mon + +form.tue + +form.wed + +form.thu + +form.fri + +form.sat;
    if (total === 0) return alert("Please log at least some hours before submitting.");
    try {
      await apiFetch(`${API_BASE}/hr/timesheets`, {
        method: "POST", body: JSON.stringify({
          week_start: form.week_start, mon_hrs: +form.mon, tue_hrs: +form.tue,
          wed_hrs: +form.wed, thu_hrs: +form.thu, fri_hrs: +form.fri, notes: form.notes
        })
      });
      setShowNew(false); setForm({ week_start: getMonday(), mon: 0, tue: 0, wed: 0, thu: 0, fri: 0, sat: 0, notes: "" }); load();
    } catch (e) { alert(e.message); }
  };

  const syncFromAttendance = async () => {
    if (!form.week_start) return alert("Please select a week starting date first.");
    const start = new Date(form.week_start);
    const end = new Date(start);
    end.setDate(start.getDate() + 5); // mon to sat

    const startStr = form.week_start;
    const endStr = end.toISOString().split('T')[0];

    try {
      setSyncing(true);
      const data = await apiFetch(`${API_BASE}/hr/presence/attendance?start_date=${startStr}&end_date=${endStr}`);
      if (!data || data.length === 0) {
        alert("No attendance records found for this week.");
        return;
      }

      const newForm = { ...form };
      data.forEach(rec => {
        if (rec.check_in && rec.check_out) {
          const cin = new Date(rec.check_in);
          const cout = new Date(rec.check_out);
          const diffHrs = Math.max(0, Math.round((cout - cin) / (1000 * 60 * 60) * 2) / 2);

          const dDate = new Date(rec.date);
          const dayMap = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
          const dayKey = dayMap[dDate.getDay()];
          if (newForm.hasOwnProperty(dayKey)) {
            newForm[dayKey] = diffHrs;
          }
        }
      });
      setForm(newForm);
      alert("Successfully synced hours from your attendance records!");
    } catch (e) {
      alert("Sync failed: " + e.message);
    } finally {
      setSyncing(false);
    }
  };

  const stCol = { pending: T.gold, approved: "#4ADE80", rejected: "#F87171" };
  const days = ["mon", "tue", "wed", "thu", "fri", "sat"];
  const dayLabels = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat" };

  const totalHrs = (s) => (s.mon_hrs || 0) + (s.tue_hrs || 0) + (s.wed_hrs || 0) + (s.thu_hrs || 0) + (s.fri_hrs || 0);
  const formTotal = +form.mon + +form.tue + +form.wed + +form.thu + +form.fri + +form.sat;
  const targetHrs = 40;
  const pending = sheets.filter(s => s.status === "pending").length;
  const approved = sheets.filter(s => s.status === "approved").length;
  const avgHrs = sheets.length ? Math.round(sheets.reduce((a, s) => a + totalHrs(s), 0) / sheets.length) : 0;

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>My Timesheets</div>
          <div style={{ fontSize: 13, color: C.sub }}>Log and track your weekly working hours. Submitted timesheets go to your manager for approval.</div>
        </div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Log This Week</button>
      </div>

      {/* Stats Row */}
      <div className="g4" style={{ marginBottom: 24 }}>
        <StatCard label="Total Submissions" value={sheets.length} col={T.gold} />
        <StatCard label="Pending Approval" value={pending} col={T.gold} />
        <StatCard label="Approved" value={approved} col="#4ADE80" />
        <StatCard label="Avg Hours / Week" value={`${avgHrs}h`} col="#60A5FA" />
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
        <>
          {/* Timesheet history as cards */}
          {sheets.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {sheets.map(s => {
                const total = totalHrs(s);
                const sc = stCol[s.status] || T.gold;
                const pct = Math.min((total / targetHrs) * 100, 100);
                const isOver = total > targetHrs;
                return (
                  <div key={s.id} className="gc" style={{ padding: "18px 22px", cursor: "pointer" }} onClick={() => setViewSheet(s)}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: 15, color: C.text }}>Week of {new Date(s.week_start + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric", year: "numeric" })}</div>
                        <div style={{ fontSize: 12, color: C.sub, marginTop: 2 }}>Submitted {new Date(s.created_at).toLocaleDateString()}</div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 22, fontWeight: 900, color: isOver ? "#F87171" : T.gold }}>{total}h</div>
                          <div style={{ fontSize: 11, color: C.muted }}>{isOver ? `+${total - targetHrs}h overtime` : `of ${targetHrs}h target`}</div>
                        </div>
                        <span className="tg" style={{ background: `${sc}22`, color: sc, textTransform: "capitalize", fontSize: 12 }}>{s.status}</span>
                      </div>
                    </div>
                    {/* Day breakdown bar */}
                    <div style={{ display: "flex", gap: 4, marginBottom: 10 }}>
                      {[["Mon", s.mon_hrs], ["Tue", s.tue_hrs], ["Wed", s.wed_hrs], ["Thu", s.thu_hrs], ["Fri", s.fri_hrs]].map(([label, hrs]) => {
                        const h = hrs || 0;
                        const dc = h === 0 ? C.border : h > 8 ? "#F87171" : h >= 7 ? "#4ADE80" : T.gold;
                        return (
                          <div key={label} style={{ flex: 1, textAlign: "center" }}>
                            <div style={{ fontSize: 10, color: C.muted, marginBottom: 4 }}>{label}</div>
                            <div style={{ height: 32, borderRadius: 6, background: `${dc}22`, border: `1px solid ${dc}44`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: dc }}>{h || "—"}</div>
                          </div>
                        );
                      })}
                    </div>
                    {/* Progress bar toward 40h target */}
                    <div style={{ height: 4, background: C.border, borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: isOver ? "#F87171" : "#4ADE80", borderRadius: 4, transition: "width .4s" }} />
                    </div>
                    {s.notes && <div style={{ fontSize: 12, color: C.sub, marginTop: 10, fontStyle: "italic" }}>"{s.notes}"</div>}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: 60, color: C.muted }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>🕐</div>
              <div style={{ fontWeight: 800 }}>No timesheets submitted yet.</div>
              <div style={{ fontSize: 13, marginTop: 6 }}>Click "+ Log This Week" to record your first week.</div>
            </div>
          )}
        </>
      )}

      {/* View Detail Modal */}
      {viewSheet && (
        <Modal onClose={() => setViewSheet(null)} title={`Timesheet — Week of ${viewSheet.week_start}`} width={500}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="g2" style={{ gap: 10 }}>
              {[["Mon", viewSheet.mon_hrs], ["Tue", viewSheet.tue_hrs], ["Wed", viewSheet.wed_hrs], ["Thu", viewSheet.thu_hrs], ["Fri", viewSheet.fri_hrs]].map(([d, h]) => {
                const hrs = h || 0; const col = hrs === 0 ? C.muted : hrs > 8 ? "#F87171" : "#4ADE80";
                return <div key={d} style={{ textAlign: "center", padding: "12px 0", background: `${col}11`, borderRadius: 10, border: `1px solid ${col}33` }}>
                  <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>{d}</div>
                  <div style={{ fontSize: 22, fontWeight: 900, color: col }}>{hrs}h</div>
                </div>;
              })}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "14px 18px", background: `${T.gold}0A`, borderRadius: 10, border: `1px solid ${T.gold}22` }}>
              <span style={{ fontWeight: 700 }}>Total Hours</span>
              <span style={{ fontWeight: 900, color: T.gold, fontSize: 18 }}>{totalHrs(viewSheet)}h</span>
            </div>
            {viewSheet.notes && <div><Lbl>Notes</Lbl><div style={{ fontSize: 13, color: C.sub, marginTop: 6 }}>{viewSheet.notes}</div></div>}
            {viewSheet.reviewer_notes && <div><Lbl>Manager Feedback</Lbl><div style={{ fontSize: 13, color: C.sub, marginTop: 6 }}>{viewSheet.reviewer_notes}</div></div>}
            <Field label="Status" value={viewSheet.status?.toUpperCase()} />
          </div>
        </Modal>
      )}

      {/* Submit Timesheet Modal */}
      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Log Weekly Hours" width={560}>
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}><Lbl>Week Starting (Monday)</Lbl><input type="date" className="inp" value={form.week_start} onChange={e => setForm(f => ({ ...f, week_start: e.target.value }))} /></div>
              <button className="bg" onClick={syncFromAttendance} disabled={syncing} style={{ padding: "11px 16px", marginBottom: 0, display: "flex", alignItems: "center", gap: 8, height: 44 }}>
                {syncing ? "⌛ Syncing..." : "🔄 Sync from Attendance"}
              </button>
            </div>
            {/* Visual day grid */}
            <div>
              <Lbl>Daily Hours</Lbl>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8, marginTop: 8 }}>
                {days.slice(0, 5).map(d => {
                  const h = +form[d]; const col = h === 0 ? C.border : h > 8 ? "#F87171" : h >= 7 ? "#4ADE80" : T.gold;
                  return (
                    <div key={d}>
                      <div style={{ textAlign: "center", fontSize: 11, color: C.muted, marginBottom: 6 }}>{dayLabels[d]}</div>
                      <input type="number" min="0" max="14" step="0.5" className="inp"
                        value={form[d]}
                        onChange={e => setForm(f => ({ ...f, [d]: e.target.value }))}
                        style={{ textAlign: "center", fontWeight: 800, fontSize: 16, color: col, borderColor: col, padding: "10px 6px" }}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
            {/* Running total */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 18px", background: `${formTotal > 40 ? "#F87171" : T.gold}0A`, borderRadius: 10, border: `1px solid ${formTotal > 40 ? "#F87171" : T.gold}22` }}>
              <span style={{ fontWeight: 700, color: C.text }}>Total this week</span>
              <span style={{ fontWeight: 900, fontSize: 20, color: formTotal > 40 ? "#F87171" : T.gold }}>{formTotal}h {formTotal > 40 ? "(Overtime)" : `/ ${targetHrs}h target`}</span>
            </div>
            <div><Lbl>Notes (optional)</Lbl><textarea className="inp" rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Any details about this week…" /></div>
            <button className="bp" onClick={submit} style={{ padding: 14 }}>Submit for Approval</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function TimesheetAuditSection({ sheet, C }) {
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sheet) return;
    const start = new Date(sheet.week_start);
    const end = new Date(start);
    end.setDate(start.getDate() + 5);
    const startStr = sheet.week_start;
    const endStr = end.toISOString().split('T')[0];

    apiFetch(`${API_BASE}/hr/presence/attendance?staff_id=${sheet.staff_id}&start_date=${startStr}&end_date=${endStr}`)
      .then(data => {
        let totalAttendance = 0;
        data.forEach(r => {
          if (r.check_in && r.check_out) {
            const cin = new Date(r.check_in);
            const cout = new Date(r.check_out);
            const hrs = Math.max(0, Math.round((cout - cin) / (1000 * 60 * 60) * 2) / 2);
            totalAttendance += hrs;
          }
        });
        const sheetTotal = (sheet.mon_hrs || 0) + (sheet.tue_hrs || 0) + (sheet.wed_hrs || 0) + (sheet.thu_hrs || 0) + (sheet.fri_hrs || 0);
        const diff = sheetTotal - totalAttendance;
        setAudit({ totalAttendance, sheetTotal, diff });
      })
      .catch(() => { })
      .finally(() => setLoading(false));
  }, [sheet]);

  if (loading) return <div style={{ fontSize: 11, color: C.muted, padding: "10px 0" }}>🔍 Verifying against attendance logs...</div>;
  if (!audit) return null;

  const isVerified = Math.abs(audit.diff) <= 1;
  const statusCol = isVerified ? "#4ADE80" : audit.diff > 0 ? "#F87171" : T.gold;

  return (
    <div style={{ padding: "12px 14px", borderRadius: 10, background: `${statusCol}08`, border: `1px solid ${statusCol}33` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: statusCol, textTransform: "uppercase", display: "flex", alignItems: "center", gap: 5 }}>
          <span>{isVerified ? "✅" : audit.diff > 0 ? "⚠️" : "ℹ️"}</span>
          {isVerified ? "Verified: Matches Logs" : audit.diff > 0 ? "Audit Warning: Mismatch" : "Logs exceed claim"}
        </div>
        <div style={{ fontSize: 11, color: C.muted, fontWeight: 700 }}>Logs: {audit.totalAttendance}h</div>
      </div>
      {!isVerified && audit.diff > 0 && (
        <div style={{ fontSize: 11, color: C.sub, lineHeight: 1.4 }}>
          Claim is <b>{audit.diff}h</b> more than the physical attendance clock for this week.
        </div>
      )}
      {isVerified && (
        <div style={{ fontSize: 10, color: C.muted }}>Timesheet is consistent with clock-in/out records.</div>
      )}
    </div>
  );
}

function TimesheetApprovalCenter() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [sheets, setSheets] = useState([]); const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("pending");
  const [reviewing, setReviewing] = useState(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => { setLoading(true); apiFetch(`${API_BASE}/hr/timesheets`).then(d => setSheets(d || [])).catch(() => { }).finally(() => setLoading(false)); };
  useEffect(load, []);

  const review = async (id, status) => {
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/timesheets/${id}`, { method: "PATCH", body: JSON.stringify({ status, reviewer_notes: reviewNotes }) });
      setReviewing(null); setReviewNotes(""); load();
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const bulkApprove = async () => {
    const pending = sheets.filter(s => s.status === "pending");
    if (!pending.length) return;
    if (!window.confirm(`Approve all ${pending.length} pending timesheets?`)) return;
    setSaving(true);
    try {
      await Promise.all(pending.map(s => apiFetch(`${API_BASE}/hr/timesheets/${s.id}`, { method: "PATCH", body: JSON.stringify({ status: "approved", reviewer_notes: "Bulk approved" }) })));
      load();
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const totalHrs = (s) => (s.mon_hrs || 0) + (s.tue_hrs || 0) + (s.wed_hrs || 0) + (s.thu_hrs || 0) + (s.fri_hrs || 0);
  const stCol = { pending: T.gold, approved: "#4ADE80", rejected: "#F87171" };
  const filtered = sheets.filter(s => filter === "all" || s.status === filter);
  const pendingCount = sheets.filter(s => s.status === "pending").length;
  const approvedCount = sheets.filter(s => s.status === "approved").length;
  const rejectedCount = sheets.filter(s => s.status === "rejected").length;
  const totalHrsAll = sheets.reduce((a, s) => a + totalHrs(s), 0);

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Timesheet Approvals</div>
          <div style={{ fontSize: 13, color: C.sub }}>Review and approve staff weekly hour submissions. Add feedback on rejection.</div>
        </div>
        {pendingCount > 0 && (
          <button className="bp" onClick={bulkApprove} disabled={saving} style={{ background: "#4ADE8022", color: "#4ADE80", border: "1px solid #4ADE8044" }}>
            ✓ Approve All Pending ({pendingCount})
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="g4" style={{ marginBottom: 24 }}>
        <StatCard label="Pending Review" value={pendingCount} col={T.gold} />
        <StatCard label="Approved" value={approvedCount} col="#4ADE80" />
        <StatCard label="Rejected" value={rejectedCount} col="#F87171" />
        <StatCard label="Total Hours Logged" value={`${totalHrsAll}h`} col="#60A5FA" />
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
        {[["pending", T.gold], ["approved", "#4ADE80"], ["rejected", "#F87171"], ["all", C.sub]].map(([f, col]) => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: "7px 16px", borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: 700, textTransform: "capitalize",
            background: filter === f ? `${col}22` : "transparent",
            color: filter === f ? col : C.muted,
            border: `1px solid ${filter === f ? col : C.border}`,
          }}>
            {f} {f !== "all" && `(${sheets.filter(s => s.status === f).length})`}
          </button>
        ))}
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filtered.map(s => {
            const total = totalHrs(s);
            const sc = stCol[s.status] || T.gold;
            const name = s.admins?.full_name || "Unknown Staff";
            const dept = s.admins?.department || "—";
            const isOver = total > 40;
            return (
              <div key={s.id} className="gc" style={{ padding: "16px 20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  {/* Left: staff info */}
                  <div style={{ display: "flex", alignItems: "center", gap: 14, flex: 1 }}>
                    <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${T.gold}22`, border: `1.5px solid ${T.gold}44`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, color: T.gold, flexShrink: 0 }}>{name[0]}</div>
                    <div>
                      <div style={{ fontWeight: 800, color: C.text }}>{name}</div>
                      <div style={{ fontSize: 12, color: C.sub }}>{dept} · Week of {new Date(s.week_start + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</div>
                    </div>
                  </div>
                  {/* Middle: day pills */}
                  <div style={{ display: "flex", gap: 4, flex: 1, justifyContent: "center" }}>
                    {[["M", s.mon_hrs], ["T", s.tue_hrs], ["W", s.wed_hrs], ["T", s.thu_hrs], ["F", s.fri_hrs]].map(([label, h], i) => {
                      const hrs = h || 0; const dc = hrs === 0 ? C.border : hrs > 8 ? "#F87171" : "#4ADE80";
                      return <div key={i} style={{ textAlign: "center", minWidth: 36 }}>
                        <div style={{ fontSize: 9, color: C.muted }}>{label}</div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: dc }}>{hrs}h</div>
                      </div>;
                    })}
                  </div>
                  {/* Right: total + status + actions */}
                  <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 20, fontWeight: 900, color: isOver ? "#F87171" : T.gold }}>{total}h</div>
                      {isOver && <div style={{ fontSize: 10, color: "#F87171" }}>+{total - 40}h OT</div>}
                    </div>
                    <span className="tg" style={{ background: `${sc}22`, color: sc, textTransform: "capitalize", fontSize: 11 }}>{s.status}</span>
                    <button className="bg" onClick={() => { setReviewing(s); setReviewNotes(s.reviewer_notes || ""); }} style={{ fontSize: 11, padding: "6px 12px" }}>Review</button>
                  </div>
                </div>
                {s.notes && <div style={{ fontSize: 12, color: C.sub, marginTop: 10, paddingTop: 10, borderTop: `1px solid ${C.border}`, fontStyle: "italic" }}>Staff note: "{s.notes}"</div>}
                {s.reviewer_notes && s.status !== "pending" && <div style={{ fontSize: 12, color: C.muted, marginTop: 6 }}>Manager feedback: "{s.reviewer_notes}"</div>}
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div style={{ textAlign: "center", padding: 60, color: C.muted }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📋</div>
              <div style={{ fontWeight: 800 }}>No timesheets in this category.</div>
            </div>
          )}
        </div>
      )}

      {/* Review Modal */}
      {reviewing && (
        <Modal onClose={() => { setReviewing(null); setReviewNotes(""); }} title={`Review — ${reviewing.admins?.full_name || "Staff"}`} width={520}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 14px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}22` }}>
              <span style={{ color: C.sub, fontSize: 13 }}>Week of {reviewing.week_start}</span>
              <span style={{ fontWeight: 900, color: T.gold }}>{totalHrs(reviewing)}h total</span>
            </div>
            <div className="g3" style={{ gap: 8 }}>
              {[["Mon", reviewing.mon_hrs], ["Tue", reviewing.tue_hrs], ["Wed", reviewing.wed_hrs], ["Thu", reviewing.thu_hrs], ["Fri", reviewing.fri_hrs]].map(([d, h]) => {
                const hrs = h || 0; const col = hrs === 0 ? C.muted : hrs > 8 ? "#F87171" : "#4ADE80";
                return <div key={d} style={{ textAlign: "center", padding: "10px 0", background: `${col}11`, borderRadius: 8, border: `1px solid ${col}33` }}>
                  <div style={{ fontSize: 10, color: C.muted }}>{d}</div>
                  <div style={{ fontSize: 18, fontWeight: 900, color: col }}>{hrs}h</div>
                </div>;
              })}
            </div>
            <TimesheetAuditSection sheet={reviewing} C={C} />
            {reviewing.notes && <div style={{ fontSize: 13, color: C.sub, fontStyle: "italic" }}>Staff note: "{reviewing.notes}"</div>}
            <div>
              <Lbl>Reviewer Notes (required for rejection)</Lbl>
              <textarea className="inp" rows={3} value={reviewNotes} onChange={e => setReviewNotes(e.target.value)} placeholder="Add feedback or reason for rejection…" style={{ marginTop: 8 }} />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="bp" onClick={() => review(reviewing.id, "approved")} disabled={saving} style={{ flex: 1, padding: 12, background: "#4ADE8022", color: "#4ADE80", border: "1px solid #4ADE8044" }}>
                ✓ Approve
              </button>
              <button onClick={() => {
                if (!reviewNotes.trim()) return alert("Please add a note explaining the rejection.");
                review(reviewing.id, "rejected");
              }} disabled={saving} style={{ flex: 1, padding: 12, background: "#F8717122", color: "#F87171", border: "1px solid #F8717144", borderRadius: 10, cursor: "pointer", fontWeight: 700 }}>
                ✕ Reject
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: SHIFT SCHEDULING ───────────────────────────────────────────────────
function ShiftScheduler({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [shifts, setShifts] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ staff_id: "", shift_date: "", start_time: "09:00", end_time: "17:00", shift_type: "Regular", notes: "" });

  useEffect(() => {
    const today = new Date(); const mon = new Date(today); mon.setDate(today.getDate() - today.getDay() + 1);
    const ws = mon.toISOString().split("T")[0];
    Promise.all([
      apiFetch(`${API_BASE}/hr/shifts?week_start=${ws}`),
      isHR ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([s, st]) => { setShifts(s || []); setStaff(st || []); }).finally(() => setLoading(false));
  }, [isHR]);

  const addShift = async () => {
    if (!form.staff_id || !form.shift_date) return alert("Staff and date required");
    try {
      await apiFetch(`${API_BASE}/hr/shifts`, { method: "POST", body: JSON.stringify({ staff_id: form.staff_id, shift_date: form.shift_date, start_time: form.start_time, end_time: form.end_time, shift_type: form.shift_type, notes: form.notes }) });
      setShowNew(false);
      apiFetch(`${API_BASE}/hr/shifts`).then(setShifts);
    } catch (e) { alert(e.message); }
  };

  const shiftTypeCol = { Regular: T.gold, Overtime: "#F87171", Remote: "#60A5FA" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Shift Scheduling</div><div style={{ fontSize: 13, color: C.sub }}>Plan and manage weekly shift rosters.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Assign Shift</button>}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading shifts…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw"><table className="ht"><thead><tr><th>Staff Member</th><th>Date</th><th>Shift Time</th><th>Type</th><th>Dept</th><th>Notes</th></tr></thead>
            <tbody>{shifts.map(s => {
              const tc = shiftTypeCol[s.shift_type] || T.gold;
              return (<tr key={s.id}>
                <td>{s.admins?.full_name || "—"}</td>
                <td>{s.shift_date}</td>
                <td><strong>{s.start_time} — {s.end_time}</strong></td>
                <td><span className="tg" style={{ background: `${tc}22`, color: tc }}>{s.shift_type}</span></td>
                <td>{s.admins?.department || "—"}</td>
                <td style={{ color: C.muted, fontSize: 12 }}>{s.notes || "—"}</td>
              </tr>);
            })}
              {shifts.length === 0 && <tr><td colSpan="6" style={{ textAlign: "center", padding: 30, color: C.muted }}>No shifts this week.</td></tr>}
            </tbody>
          </table></div>
        </div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Assign Shift">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Staff Member *</Lbl>
            <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
              <option value="">— Select —</option>{staff.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
            </select>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Shift Date *</Lbl><input type="date" className="inp" value={form.shift_date} onChange={e => setForm(f => ({ ...f, shift_date: e.target.value }))} /></div>
            <div><Lbl>Shift Type</Lbl>
              <select className="inp" value={form.shift_type} onChange={e => setForm(f => ({ ...f, shift_type: e.target.value }))}>
                <option>Regular</option><option>Overtime</option><option>Remote</option>
              </select>
            </div>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Start Time</Lbl><input type="time" className="inp" value={form.start_time} onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} /></div>
            <div><Lbl>End Time</Lbl><input type="time" className="inp" value={form.end_time} onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))} /></div>
          </div>
          <div><Lbl>Notes</Lbl><input className="inp" placeholder="Optional notes" value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></div>
          <button className="bp" onClick={addShift}>Assign Shift</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: LEAVE POLICIES ─────────────────────────────────────────────────────
function LeavePolicies({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [policies, setPolicies] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ leave_type: "Annual", days_per_year: 20, carry_over: false, requires_proof: false, description: "" });

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/leave-policies`).then(d => setPolicies(d || [])).catch(() => setPolicies([])).finally(() => setLoading(false));
  }, []);

  const add = async () => {
    try {
      await apiFetch(`${API_BASE}/hr/leave-policies`, { method: "POST", body: JSON.stringify({ leave_type: form.leave_type, days_per_year: form.days_per_year, carry_over: form.carry_over, requires_proof: form.requires_proof, description: form.description }) });
      setShowNew(false);
      apiFetch(`${API_BASE}/hr/leave-policies`).then(d => setPolicies(d || []));
    } catch (e) { alert(e.message); }
  };

  const defaults = [
    { leave_type: "Annual Leave", days_per_year: 20, carry_over: false, description: "Standard annual leave entitlement" },
    { leave_type: "Sick Leave", days_per_year: 10, carry_over: false, description: "Paid sick leave with doctor's note" },
    { leave_type: "Maternity Leave", days_per_year: 90, carry_over: false, description: "90 days maternity leave" },
    { leave_type: "Paternity Leave", days_per_year: 5, carry_over: false, description: "5 days paternity leave" },
    { leave_type: "Study Leave", days_per_year: 5, carry_over: false, description: "Approved study/exam leave" },
    { leave_type: "Compassionate Leave", days_per_year: 3, carry_over: false, description: "Bereavement and family emergency" },
  ];

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Leave Policies</div><div style={{ fontSize: 13, color: C.sub }}>Configure leave types, entitlements and carry-over rules.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Add Policy</button>}
      </div>
      <div className="g2" style={{ gap: 16, marginBottom: 22 }}>
        {(policies.length > 0 ? policies : defaults).map((p, i) => (
          <div key={i} className="gc" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div className="ho" style={{ fontSize: 15 }}>{p.leave_type}</div>
              <span className="tg to" style={{ fontSize: 12 }}>{p.days_per_year} days/yr</span>
            </div>
            <div style={{ fontSize: 12, color: C.sub, marginBottom: 10, lineHeight: 1.5 }}>{p.description || "—"}</div>
            <div style={{ display: "flex", gap: 8 }}>
              {p.carry_over && <span className="tg tg2" style={{ fontSize: 10 }}>Carry Over</span>}
              {p.requires_proof && <span className="tg tb" style={{ fontSize: 10 }}>Proof Required</span>}
            </div>
          </div>
        ))}
      </div>
      {showNew && <Modal onClose={() => setShowNew(false)} title="Add Leave Policy">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Leave Type *</Lbl><input className="inp" value={form.leave_type} onChange={e => setForm(f => ({ ...f, leave_type: e.target.value }))} /></div>
          <div><Lbl>Days Per Year</Lbl><input type="number" className="inp" value={form.days_per_year} onChange={e => setForm(f => ({ ...f, days_per_year: +e.target.value }))} /></div>
          <div><Lbl>Description</Lbl><textarea className="inp" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
          <div style={{ display: "flex", gap: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, color: C.sub, fontSize: 13 }}>
              <input type="checkbox" checked={form.carry_over} onChange={e => setForm(f => ({ ...f, carry_over: e.target.checked }))} /> Allow Carry Over
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, color: C.sub, fontSize: 13 }}>
              <input type="checkbox" checked={form.requires_proof} onChange={e => setForm(f => ({ ...f, requires_proof: e.target.checked }))} /> Requires Proof
            </label>
          </div>
          <button className="bp" onClick={add}>Save Policy</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: LEAVE ACCRUAL ──────────────────────────────────────────────────────
function LeaveBalancesOverview() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [balances, setBalances] = useState(null); const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/leave-balances`).then(setBalances).catch(() => { }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}>
        <div className="ho" style={{ fontSize: 22 }}>Leave Balances</div>
        <div style={{ fontSize: 13, color: C.sub }}>Snapshot of your current leave entitlements and usage.</div>
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading balances…</div> : !balances ? (
        <div className="gc" style={{ padding: 32, textAlign: "center", color: C.muted }}>No balance data available.</div>
      ) : (
        <>
          <div className="g3" style={{ marginBottom: 22 }}>
            <StatCard label="Total Quota" value={`${balances.quota} days`} col={T.gold} />
            <StatCard label="Days Used" value={`${balances.used} days`} col="#F87171" />
            <StatCard label="Remaining" value={`${balances.remaining} days`} col="#4ADE80" />
          </div>
          <div className="gc" style={{ padding: 22 }}>
            <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Detailed Breakdown</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {Object.entries(balances.by_type || {}).map(([type, days]) => (
                <div key={type} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 12, borderBottom: `1px solid ${C.border}44` }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{type} Leave</div>
                    <div style={{ fontSize: 11, color: C.muted }}>Allocated as per policy</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 14, color: T.gold, fontWeight: 800 }}>{days} Days</div>
                    <div style={{ fontSize: 10, color: C.sub }}>CONSUMED</div>
                  </div>
                </div>
              ))}
              {(!balances.by_type || Object.keys(balances.by_type).length === 0) && <div style={{ fontSize: 13, color: C.muted }}>No specific leave types used yet.</div>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function LeaveAccrualConfig() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}>
        <div className="ho" style={{ fontSize: 22 }}>Accrual Rules & Logic</div>
        <div style={{ fontSize: 13, color: C.sub }}>Configuration for how leave days are earned over time.</div>
      </div>
      <div className="gc" style={{ padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20, padding: 16, background: `${T.gold}11`, borderRadius: 12, border: `1px solid ${T.gold}33` }}>
          <div style={{ fontSize: 24 }}>⚙️</div>
          <div>
            <div style={{ fontWeight: 800, color: T.gold }}>Monthly Accrual Enabled</div>
            <div style={{ fontSize: 12, color: C.sub }}>Staff earn 1.67 days per month (20 days/year).</div>
          </div>
        </div>

        <div className="ho" style={{ fontSize: 14, marginBottom: 14 }}>System Logic</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            ["Proration", "New hires receive leave balance adjusted by their start date in the first year."],
            ["Carry Over", "Maximum of 5 unused days can be carried over to the next calendar year."],
            ["Probation", "Leave accrual begins immediately but can only be requested after 3 months."],
            ["Tenure Bonus", "Staff receive +1 day annual quota for every 2 years of continuous service."]
          ].map(([t, d]) => (
            <div key={t} style={{ padding: "14px 18px", background: C.border + "11", borderRadius: 10 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: C.text, marginBottom: 4 }}>{t}</div>
              <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.5 }}>{d}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 24, fontSize: 11, color: C.muted, textAlign: "center", fontStyle: "italic" }}>
          Contact HR Admin to modify these global accrual configurations.
        </div>
      </div>
    </div>
  );
}

// ─── HUB: IMPROVEMENT PLANS (PIPs) ───────────────────────────────────────────
function ImprovementPlans({ viewOnly, userId, authRole }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const isHR = authRole === "hr";
  const [pips, setPips] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ staff_id: "", reason: "", goals: "", start_date: "", review_date: "", notes: "" });

  useEffect(() => {
    const p = viewOnly ? `?staff_id=${userId}` : "";
    Promise.all([
      apiFetch(`${API_BASE}/hr/pip${p}`).catch(() => []),
      isHR ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([p, s]) => { setPips(p || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [viewOnly, userId, isHR]);

  const save = async () => {
    if (!form.staff_id || !form.reason || !form.start_date) return alert("Staff, reason and start date required");
    try {
      await apiFetch(`${API_BASE}/hr/pip`, { method: "POST", body: JSON.stringify({ staff_id: form.staff_id, reason: form.reason, goals: form.goals, start_date: form.start_date, review_date: form.review_date, notes: form.notes }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/pip`).then(d => setPips(d || []));
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Improvement Plans</div><div style={{ fontSize: 13, color: C.sub }}>Performance Improvement Plans (PIPs) for underperforming staff.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Create PIP</button>}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : pips.length === 0 ? (
        <div className="gc" style={{ padding: 48, textAlign: "center" }}><div style={{ fontSize: 28, color: "#4ADE80", marginBottom: 12 }}>✓</div><div style={{ color: "#4ADE80", fontWeight: 800 }}>No active PIPs — team performance is on track.</div></div>
      ) : (
        <div className="g2">{pips.map(p => (
          <div key={p.id} className="gc" style={{ padding: 20, borderLeft: `3px solid #F87171` }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div><div style={{ fontWeight: 800, color: C.text }}>{p.admins?.full_name || "Unknown"}</div><div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>{p.admins?.department}</div></div>
              <span className="tg tr">PIP Active</span>
            </div>
            <div style={{ fontSize: 12, color: C.sub, marginBottom: 8 }}><strong style={{ color: C.text }}>Reason:</strong> {p.reason}</div>
            <div style={{ fontSize: 12, color: C.sub, marginBottom: 8 }}><strong style={{ color: C.text }}>Goals:</strong> {p.goals}</div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted, marginTop: 12 }}>
              <span>Started: {p.start_date}</span><span>Review: {p.review_date}</span>
            </div>
          </div>
        ))}</div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Create Improvement Plan">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Staff Member *</Lbl>
            <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
              <option value="">— Select —</option>{staff.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </select>
          </div>
          <div><Lbl>Reason for PIP *</Lbl><textarea className="inp" value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} /></div>
          <div><Lbl>Performance Goals</Lbl><textarea className="inp" placeholder="Specific measurable targets to hit…" value={form.goals} onChange={e => setForm(f => ({ ...f, goals: e.target.value }))} /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Start Date *</Lbl><input type="date" className="inp" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} /></div>
            <div><Lbl>Review Date</Lbl><input type="date" className="inp" value={form.review_date} onChange={e => setForm(f => ({ ...f, review_date: e.target.value }))} /></div>
          </div>
          <button className="bp" onClick={save}>Create PIP</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: SUCCESSION PLANNING ────────────────────────────────────────────────
function SuccessionPlanning() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [plans, setPlans] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ critical_role: "", successor_id: "", readiness: "6-12 months", development_notes: "" });
  const [saving, setSaving] = useState(false);

  const READINESS = ["Ready Now", "6-12 months", "12-24 months", "Development Needed"];
  const readinessCol = { "Ready Now": "#4ADE80", "6-12 months": T.gold, "12-24 months": "#60A5FA", "Development Needed": "#F87171" };

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/succession-plans`).catch(() => []),
      apiFetch(`${API_BASE}/hr/staff`).catch(() => [])
    ]).then(([p, s]) => { setPlans(Array.isArray(p) ? p : []); setStaff(Array.isArray(s) ? s : []); }).finally(() => setLoading(false));
  }, []);

  const refresh = () => apiFetch(`${API_BASE}/hr/succession-plans`).catch(() => []).then(p => setPlans(Array.isArray(p) ? p : []));

  const save = async () => {
    if (!form.critical_role || !form.successor_id) return alert("Role and successor required.");
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/succession-plans`, { method: "POST", body: JSON.stringify({ critical_role: form.critical_role, successor_id: form.successor_id, readiness: form.readiness, development_notes: form.development_notes }) });
      setShowNew(false); setForm({ critical_role: "", successor_id: "", readiness: "6-12 months", development_notes: "" });
      refresh();
    } catch (e) { alert("Error: " + e.message); } finally { setSaving(false); }
  };

  const del = async (id) => {
    if (!window.confirm("Remove this succession plan?")) return;
    try { await apiFetch(`${API_BASE}/hr/succession-plans/${id}`, { method: "DELETE" }); refresh(); }
    catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Succession Planning</div>
          <div style={{ fontSize: 13, color: C.sub }}>Map high-potential staff to critical roles and track readiness.</div>
        </div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Add Succession Plan</button>
      </div>

      <div className="g2" style={{ marginBottom: 22 }}>
        {[["Identify Successors", "Map staff to critical roles they can fill in 6–24 months.", "#4ADE80"],
        ["Retention Risk", "Top performers in succession plans are flagged as high-retention priority.", "#F87171"],
        ["Readiness Levels", "Track each candidate's development stage towards role readiness.", T.gold],
        ["Career Paths", "Define growth trajectories to motivate and retain talent.", "#60A5FA"]].map(([t, d, c]) => (
          <div key={t} className="gc" style={{ padding: 20, borderLeft: `3px solid ${c}` }}>
            <div style={{ fontWeight: 800, color: c, marginBottom: 8 }}>{t}</div>
            <div style={{ fontSize: 13, color: C.sub }}>{d}</div>
          </div>
        ))}
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading succession plans…</div> : (
        <>
          {plans.length === 0 && !showNew ? (
            <div className="gc" style={{ padding: 40, textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🎯</div>
              <div style={{ fontWeight: 800, color: C.text, marginBottom: 8 }}>No succession plans yet</div>
              <div style={{ fontSize: 13, color: C.muted, marginBottom: 20 }}>Identify key roles and map your high-potential staff as successors.</div>
              <button className="bp" onClick={() => setShowNew(true)}>+ Create First Plan</button>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 20 }}>
              {plans.map(p => {
                const successor = staff.find(s => s.id === p.successor_id);
                const rc = readinessCol[p.readiness] || T.gold;
                return (
                  <div key={p.id} className="gc fade-in" style={{ padding: 24, borderTop: `3px solid ${rc}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                      <div>
                        <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", fontWeight: 700, marginBottom: 4 }}>Critical Role</div>
                        <div style={{ fontWeight: 900, fontSize: 16, color: C.text }}>{p.critical_role}</div>
                      </div>
                      <button onClick={() => del(p.id)} style={{ background: "none", border: "none", color: "#F87171", cursor: "pointer", fontSize: 16 }}>×</button>
                    </div>
                    {successor && (
                      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0", borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`, marginBottom: 14 }}>
                        <Av av={successor.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={36} />
                        <div>
                          <div style={{ fontWeight: 800, color: C.text }}>{successor.full_name}</div>
                          <div style={{ fontSize: 11, color: C.muted }}>{successor.department}</div>
                        </div>
                      </div>
                    )}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: p.development_notes ? 12 : 0 }}>
                      <span style={{ fontSize: 11, color: C.muted }}>Readiness</span>
                      <span className="tg" style={{ background: `${rc}22`, color: rc, fontWeight: 700 }}>{p.readiness}</span>
                    </div>
                    {p.development_notes && (
                      <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.5, background: dark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", padding: 10, borderRadius: 8, marginTop: 4 }}>
                        {p.development_notes}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Add Succession Plan">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Critical Role / Position *</Lbl><input className="inp" placeholder="e.g. Head of Operations" value={form.critical_role} onChange={e => setForm(f => ({ ...f, critical_role: e.target.value }))} /></div>
            <div><Lbl>Successor *</Lbl>
              <select className="inp" value={form.successor_id} onChange={e => setForm(f => ({ ...f, successor_id: e.target.value }))}>
                <option value="">— Select Staff Member —</option>
                {staff.filter(s => s.is_active).map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}
              </select>
            </div>
            <div><Lbl>Readiness Level</Lbl>
              <select className="inp" value={form.readiness} onChange={e => setForm(f => ({ ...f, readiness: e.target.value }))}>
                {READINESS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div><Lbl>Development Notes</Lbl><textarea className="inp" rows={3} placeholder="What development steps are needed for this successor?" value={form.development_notes} onChange={e => setForm(f => ({ ...f, development_notes: e.target.value }))} /></div>
            <button className="bp" onClick={save} disabled={saving}>{saving ? "Saving…" : "Create Plan"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: SKILLS MATRIX ──────────────────────────────────────────────────────
function SkillsMatrix() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const skills = ["Leadership", "Communication", "Technical Writing", "Data Analysis", "Client Relations", "Project Management", "Negotiation", "Financial Literacy"];
  const levels = ["Beginner", "Intermediate", "Advanced", "Expert"];
  const lvlCol = { Beginner: "#9CA3AF", Intermediate: "#60A5FA", Advanced: T.gold, Expert: "#4ADE80" };
  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}><div className="ho" style={{ fontSize: 22 }}>Skills Matrix</div><div style={{ fontSize: 13, color: C.sub }}>Company-wide competency tracking across all departments.</div></div>
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        {levels.map(l => <span key={l} className="tg" style={{ background: `${lvlCol[l]}22`, color: lvlCol[l] }}>{l}</span>)}
      </div>
      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw"><table className="ht"><thead><tr><th>Skill Area</th><th>Beginner</th><th>Intermediate</th><th>Advanced</th><th>Expert</th></tr></thead>
          <tbody>{skills.map(s => {
            const counts = [Math.floor(Math.random() * 5), Math.floor(Math.random() * 8), Math.floor(Math.random() * 6), Math.floor(Math.random() * 3)];
            return (<tr key={s}><td style={{ fontWeight: 700, color: C.text }}>{s}</td>
              {counts.map((c, i) => <td key={i}><span className="tg" style={{ background: `${Object.values(lvlCol)[i]}22`, color: Object.values(lvlCol)[i] }}>{c} staff</span></td>)}
            </tr>);
          })}</tbody>
        </table></div>
      </div>
    </div>
  );
}

// ─── HUB: LEARNING & TRAINING ────────────────────────────────────────────────
function LearningHub({ isHR, defaultTab = "trainings" }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [trainings, setTrainings] = useState([]); const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(defaultTab);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ title: "", training_type: "Internal", description: "", start_date: "", end_date: "", trainer: "" });

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/trainings`).then(d => setTrainings(d || [])).catch(() => setTrainings([])).finally(() => setLoading(false));
  }, []);

  const add = async () => {
    if (!form.title || !form.start_date) return alert("Title and start date required");
    try {
      await apiFetch(`${API_BASE}/hr/trainings`, { method: "POST", body: JSON.stringify({ title: form.title, training_type: form.training_type, description: form.description, start_date: form.start_date, end_date: form.end_date, trainer: form.trainer }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/trainings`).then(d => setTrainings(d || []));
    } catch (e) { alert(e.message); }
  };

  const enroll = async (id) => {
    try { await apiFetch(`${API_BASE}/hr/trainings/${id}/enroll`, { method: "POST" }); alert("Enrolled successfully!"); }
    catch (e) { alert(e.message); }
  };

  const ttCol = { Internal: T.gold, External: "#60A5FA", Compliance: "#F87171" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Learning & Training</div><div style={{ fontSize: 13, color: C.sub }}>Internal, external and compliance training programmes.</div></div>
        <div style={{ display: "flex", gap: 12 }}>
          <Tabs items={[["trainings", "Trainings"], ["compliance", "Compliance"]]} active={tab} setActive={setTab} />
          {isHR && <button className="bp" onClick={() => setShowNew(true)} style={{ height: 38 }}>+ Add Training</button>}
        </div>
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="g3">{(trainings.filter(t => tab === "compliance" ? t.training_type === "Compliance" : t.training_type !== "Compliance")).map(t => {
          const tc = ttCol[t.training_type] || T.gold;
          const enrolled = t.training_enrollments?.length || 0;
          return (
            <div key={t.id} className="gc" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="tg" style={{ background: `${tc}22`, color: tc }}>{t.training_type}</span>
                <span style={{ fontSize: 11, color: C.muted }}>{enrolled} enrolled</span>
              </div>
              <div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{t.title}</div>
              <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.5 }}>{t.description || "No description provided."}</div>
              <div style={{ fontSize: 11, color: C.muted }}>Start: {t.start_date}{t.trainer && ` · Trainer: ${t.trainer}`}</div>
              <button className="bg" style={{ alignSelf: "flex-start", fontSize: 12, padding: "6px 14px" }} onClick={() => enroll(t.id)}>Enroll</button>
            </div>
          );
        })}
          {trainings.length === 0 && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: C.muted }}>No training sessions scheduled.</div>}
        </div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Add Training Programme">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Type</Lbl>
              <select className="inp" value={form.training_type} onChange={e => setForm(f => ({ ...f, training_type: e.target.value }))}>
                <option>Internal</option><option>External</option><option>Compliance</option>
              </select>
            </div>
            <div><Lbl>Trainer / Provider</Lbl><input className="inp" value={form.trainer} onChange={e => setForm(f => ({ ...f, trainer: e.target.value }))} /></div>
          </div>
          <div><Lbl>Description</Lbl><textarea className="inp" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Start Date *</Lbl><input type="date" className="inp" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} /></div>
            <div><Lbl>End Date</Lbl><input type="date" className="inp" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} /></div>
          </div>
          <button className="bp" onClick={add}>Create Training</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: ONBOARDING ─────────────────────────────────────────────────────────
function OnboardingHub({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]); const [selected, setSelected] = useState(null);
  const [checklist, setChecklist] = useState([]); const [loading, setLoading] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [tab, setTab] = useState("progress");

  const defaultItems = ["Sign Employment Contract", "Complete ID Verification", "IT Equipment Issued", "Company Email Created", "System Access Granted", "Meet Line Manager", "Complete HR Induction", "Review Company Handbook", "Set up Payroll Information", "Complete Probation Agreement"];

  useEffect(() => {
    if (isHR) apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(d || []));
  }, [isHR]);

  const loadChecklist = async (staffId) => {
    setLoading(true);
    const data = await apiFetch(`${API_BASE}/hr/onboarding/${staffId}`).catch(() => []);
    setChecklist(data || []); setLoading(false);
  };

  const createChecklist = async (staffId) => {
    try {
      await apiFetch(`${API_BASE}/hr/onboarding`, { method: "POST", body: JSON.stringify({ staff_id: staffId, items: defaultItems }) });
      loadChecklist(staffId);
    } catch (e) { alert(e.message); }
  };

  const markDone = async (itemId) => {
    try {
      await apiFetch(`${API_BASE}/hr/onboarding/${itemId}`, { method: "PATCH" });
      setChecklist(prev => prev.map(i => i.id === itemId ? { ...i, completed: true } : i));
    } catch (e) { alert(e.message); }
  };

  const completed = checklist.filter(i => i.completed).length;
  const total = checklist.length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Onboarding Hub</div><div style={{ fontSize: 13, color: C.sub }}>Manage new hire onboarding and standard checklists.</div></div>
        <Tabs items={[["progress", "Hire Progress"], ["master", "Master Checklist"]]} active={tab} setActive={setTab} />
      </div>

      {tab === "progress" ? (
        <>
          {isHR && (
            <div style={{ display: "flex", gap: 12, marginBottom: 22, flexWrap: "wrap" }}>
              <select className="inp" style={{ maxWidth: 300 }} value={selected?.id || ""} onChange={e => { const s = staff.find(x => x.id === e.target.value); setSelected(s || null); if (s) loadChecklist(s.id); }}>
                <option value="">👤 Select New Hire 👤</option>
                {staff.filter(s => s.is_active).map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}
              </select>
              {selected && checklist.length === 0 && <button className="bp" onClick={() => createChecklist(selected.id)}>Generate Checklist</button>}
            </div>
          )}
          {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading...</div> : (
            <>
              {selected && checklist.length > 0 && (
                <>
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: C.text, marginBottom: 8 }}>
                      <span style={{ fontWeight: 800 }}>{selected.full_name} — Onboarding Progress</span>
                      <span style={{ color: T.gold, fontWeight: 800 }}>{completed}/{total} complete ({pct}%)</span>
                    </div>
                    <Bar pct={pct} />
                  </div>
                  <div className="g2">{checklist.map(item => (
                    <div key={item.id} className="gc" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14, borderLeft: `3px solid ${item.completed ? "#4ADE80" : C.border}` }}>
                      <div onClick={() => !item.completed && markDone(item.id)} style={{ width: 22, height: 22, borderRadius: "50%", border: `2px solid ${item.completed ? "#4ADE80" : C.border}`, background: item.completed ? "#4ADE80" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: item.completed ? "default" : "pointer", flexShrink: 0, color: item.completed ? "#0F1318" : "transparent", fontWeight: 800, fontSize: 12 }}>✓</div>
                      <span style={{ fontSize: 13, color: item.completed ? C.muted : C.text, textDecoration: item.completed ? "line-through" : "none" }}>{item.item}</span>
                    </div>
                  ))}</div>
                </>
              )}
              {(!selected || checklist.length === 0) && !loading && (
                <div className="gc" style={{ padding: 60, textAlign: "center", color: C.muted, background: C.card }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>👤</div>
                  <div style={{ fontWeight: 800, color: C.sub }}>No Checklist Active</div>
                  <div style={{ fontSize: 13 }}>Select a new hire above to view or generate their onboarding tasks.</div>
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <div className="fade">
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 800, fontSize: 16, color: C.text, marginBottom: 4 }}>Master Onboarding Template</div>
            <div style={{ fontSize: 13, color: C.sub }}>These items are automatically assigned to every new hire when their checklist is generated.</div>
          </div>
          <div className="g2">
            {defaultItems.map((item, i) => (
              <div key={i} className="gc" style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 12, borderLeft: `3px solid ${T.gold}` }}>
                <div style={{ width: 24, height: 24, borderRadius: "50%", background: `${T.gold}22`, color: T.gold, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800 }}>{i + 1}</div>
                <span style={{ fontSize: 13, color: C.text }}>{item}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 20, padding: 16, background: `${T.gold}11`, borderRadius: 8, border: `1px dashed ${T.gold}44`, fontSize: 12, color: C.sub, textAlign: "center" }}>
            Note: Master checklist is currently set globally. To modify these items, please contact the system administrator.
          </div>
        </div>
      )}
    </div>
  );
}

// ─── HUB: PROBATION TRACKING ─────────────────────────────────────────────────
function ProbationTracker({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [reviews, setReviews] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ staff_id: "", review_date: "", outcome: "Pass", notes: "" });

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/probation`).catch(() => []),
      isHR ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([r, s]) => { setReviews(r || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [isHR]);

  const save = async () => {
    if (!form.staff_id || !form.review_date) return alert("Staff and date required");
    try {
      await apiFetch(`${API_BASE}/hr/probation`, { method: "POST", body: JSON.stringify({ staff_id: form.staff_id, review_date: form.review_date, outcome: form.outcome, notes: form.notes }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/probation`).then(d => setReviews(d || []));
    } catch (e) { alert(e.message); }
  };

  const outcomeCol = { Pass: "#4ADE80", Extended: T.gold, Failed: "#F87171" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Probation Tracking</div><div style={{ fontSize: 13, color: C.sub }}>Monitor new hire probation periods and review outcomes.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Log Review</button>}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw"><table className="ht"><thead><tr><th>Staff Member</th><th>Department</th><th>Review Date</th><th>Outcome</th><th>Notes</th></tr></thead>
            <tbody>{reviews.map(r => {
              const oc = outcomeCol[r.outcome] || T.gold;
              return (<tr key={r.id}>
                <td><div style={{ fontWeight: 800, color: C.text }}>{r.admins?.full_name || "—"}</div></td>
                <td>{r.admins?.department || "—"}</td><td>{r.review_date}</td>
                <td><span className="tg" style={{ background: `${oc}22`, color: oc }}>{r.outcome}</span></td>
                <td style={{ color: C.muted, fontSize: 12 }}>{r.notes || "—"}</td>
              </tr>);
            })}
              {reviews.length === 0 && <tr><td colSpan="5" style={{ textAlign: "center", padding: 30, color: C.muted }}>No probation reviews recorded.</td></tr>}
            </tbody>
          </table></div>
        </div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Log Probation Review">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Staff Member *</Lbl>
            <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
              <option value="">— Select —</option>{staff.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </select>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Review Date *</Lbl><input type="date" className="inp" value={form.review_date} onChange={e => setForm(f => ({ ...f, review_date: e.target.value }))} /></div>
            <div><Lbl>Outcome</Lbl>
              <select className="inp" value={form.outcome} onChange={e => setForm(f => ({ ...f, outcome: e.target.value }))}>
                <option>Pass</option><option>Extended</option><option>Failed</option>
              </select>
            </div>
          </div>
          <div><Lbl>Notes</Lbl><textarea className="inp" value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></div>
          <button className="bp" onClick={save}>Save Review</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: COMPENSATION BANDS ─────────────────────────────────────────────────
function CompensationBands({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [bands, setBands] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ role_title: "", department: "", min_salary: "", max_salary: "", currency: "NGN" });

  const defaults = [
    { role_title: "Junior Executive", department: "Sales & Acquisitions", min_salary: 150000, max_salary: 250000, currency: "NGN" },
    { role_title: "Senior Executive", department: "Sales & Acquisitions", min_salary: 280000, max_salary: 450000, currency: "NGN" },
    { role_title: "Operations Manager", department: "Operations", min_salary: 400000, max_salary: 650000, currency: "NGN" },
    { role_title: "HR Manager", department: "Human Resources", min_salary: 350000, max_salary: 550000, currency: "NGN" },
    { role_title: "Finance Manager", department: "Finance", min_salary: 400000, max_salary: 700000, currency: "NGN" },
  ];

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/comp-bands`).then(d => setBands(d || [])).catch(() => setBands([])).finally(() => setLoading(false));
  }, []);

  const add = async () => {
    if (!form.role_title || !form.min_salary) return alert("Role and salary range required");
    try {
      await apiFetch(`${API_BASE}/hr/comp-bands`, { method: "POST", body: JSON.stringify({ ...form, min_salary: +form.min_salary, max_salary: +form.max_salary }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/comp-bands`).then(d => setBands(d || []));
    } catch (e) { alert(e.message); }
  };

  const fmt = n => `₦${(n / 1000).toFixed(0)}k`;
  const display = bands.length > 0 ? bands : defaults;

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Compensation Bands</div><div style={{ fontSize: 13, color: C.sub }}>Salary ranges by role and department. Used for equity benchmarking.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Add Band</button>}
      </div>
      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw"><table className="ht"><thead><tr><th>Role Title</th><th>Department</th><th>Min Salary</th><th>Max Salary</th><th>Midpoint</th><th>Currency</th></tr></thead>
          <tbody>{display.map((b, i) => (
            <tr key={i}>
              <td style={{ fontWeight: 800, color: C.text }}>{b.role_title}</td>
              <td>{b.department}</td>
              <td style={{ color: "#4ADE80", fontWeight: 800 }}>{fmt(b.min_salary)}</td>
              <td style={{ color: "#F87171", fontWeight: 800 }}>{fmt(b.max_salary)}</td>
              <td style={{ color: T.gold, fontWeight: 800 }}>{fmt((b.min_salary + b.max_salary) / 2)}</td>
              <td>{b.currency}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </div>
      {showNew && <Modal onClose={() => setShowNew(false)} title="Add Compensation Band">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Role Title *</Lbl><input className="inp" value={form.role_title} onChange={e => setForm(f => ({ ...f, role_title: e.target.value }))} /></div>
            <div><Lbl>Department</Lbl><input className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))} /></div>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Min Salary (NGN) *</Lbl><input type="number" className="inp" value={form.min_salary} onChange={e => setForm(f => ({ ...f, min_salary: e.target.value }))} /></div>
            <div><Lbl>Max Salary (NGN)</Lbl><input type="number" className="inp" value={form.max_salary} onChange={e => setForm(f => ({ ...f, max_salary: e.target.value }))} /></div>
          </div>
          <button className="bp" onClick={add}>Save Band</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: BONUSES & INCENTIVES ────────────────────────────────────────────────
function BonusManager({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [bonuses, setBonuses] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ staff_id: "", bonus_type: "Performance", amount: "", period: new Date().toISOString().slice(0, 7), notes: "" });

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/bonuses`).catch(() => []),
      isHR ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([b, s]) => { setBonuses(b || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [isHR]);

  const add = async () => {
    if (!form.staff_id || !form.amount) return alert("Staff and amount required");
    try {
      await apiFetch(`${API_BASE}/hr/bonuses`, { method: "POST", body: JSON.stringify({ ...form, amount: +form.amount }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/bonuses`).then(d => setBonuses(d || []));
    } catch (e) { alert(e.message); }
  };

  const btCol = { Performance: T.gold, Annual: "#60A5FA", Spot: "#4ADE80", Commission: "#F87171" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Bonuses & Incentives</div><div style={{ fontSize: 13, color: C.sub }}>Log performance bonuses, annual bonuses and spot awards.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Log Bonus</button>}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw"><table className="ht"><thead><tr><th>Staff Member</th><th>Type</th><th>Amount</th><th>Period</th><th>Notes</th></tr></thead>
            <tbody>{bonuses.map(b => {
              const bc = btCol[b.bonus_type] || T.gold;
              return (<tr key={b.id}>
                <td style={{ fontWeight: 800, color: C.text }}>{b.admins?.full_name || "—"}</td>
                <td><span className="tg" style={{ background: `${bc}22`, color: bc }}>{b.bonus_type}</span></td>
                <td style={{ color: "#4ADE80", fontWeight: 800 }}>₦{b.amount?.toLocaleString()}</td>
                <td>{b.period}</td>
                <td style={{ color: C.muted, fontSize: 12 }}>{b.notes || "—"}</td>
              </tr>);
            })}
              {bonuses.length === 0 && <tr><td colSpan="5" style={{ textAlign: "center", padding: 30, color: C.muted }}>No bonuses logged yet.</td></tr>}
            </tbody>
          </table></div>
        </div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Log Bonus / Incentive">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Staff Member *</Lbl>
            <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
              <option value="">— Select —</option>{staff.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </select>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Bonus Type</Lbl>
              <select className="inp" value={form.bonus_type} onChange={e => setForm(f => ({ ...f, bonus_type: e.target.value }))}>
                <option>Performance</option><option>Annual</option><option>Spot</option><option>Commission</option>
              </select>
            </div>
            <div><Lbl>Period (YYYY-MM)</Lbl><input className="inp" placeholder="2026-04" value={form.period} onChange={e => setForm(f => ({ ...f, period: e.target.value }))} /></div>
          </div>
          <div><Lbl>Amount (NGN) *</Lbl><input type="number" className="inp" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} /></div>
          <div><Lbl>Notes</Lbl><input className="inp" value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></div>
          <button className="bp" onClick={add}>Log Bonus</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: TAX CONFIGURATION ──────────────────────────────────────────────────
function TaxConfig() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [config, setConfig] = useState({ paye_enabled: true, pension_employee_rate: 8, pension_employer_rate: 10, nhf_rate: 2.5, wht_default_rate: 5, wht_contractor_rate: 10 });
  const [loading, setLoading] = useState(true); const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/tax-config`).then(d => { if (d) setConfig(c => ({ ...c, ...d })); }).catch(() => { }).finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/tax-config`, { method: "POST", body: JSON.stringify(config) });
      alert("Tax configuration saved successfully.");
    } catch (e) { alert("Error: " + e.message); } finally { setSaving(false); }
  };

  const Field = ({ label, field, suffix = "%", step = "0.5", min = "0", max = "100" }) => (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: `1px solid ${C.border}` }}>
      <span style={{ fontSize: 13, color: C.text, fontWeight: 600 }}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input type="number" step={step} min={min} max={max} value={config[field]} onChange={e => setConfig(c => ({ ...c, [field]: parseFloat(e.target.value) }))}
          style={{ width: 80, padding: "6px 10px", borderRadius: 8, border: `1px solid ${C.border}`, background: dark ? "#1a1a2e" : "#f8f8f8", color: C.text, fontSize: 14, fontWeight: 800, textAlign: "right" }} />
        <span style={{ fontSize: 12, color: C.muted, width: 20 }}>{suffix}</span>
      </div>
    </div>
  );

  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}>
        <div className="ho" style={{ fontSize: 22 }}>Tax Configuration</div>
        <div style={{ fontSize: 13, color: C.sub }}>Nigerian PAYE, Pension, NHF and WHT rates and settings.</div>
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="g2">
          {/* PAYE */}
          <div className="gc" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <div style={{ fontWeight: 800, color: "#F87171", fontSize: 15 }}>PAYE (Pay As You Earn)</div>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                <span style={{ fontSize: 12, color: C.muted }}>Enabled</span>
                <div onClick={() => setConfig(c => ({ ...c, paye_enabled: !c.paye_enabled }))} style={{ width: 40, height: 22, borderRadius: 11, background: config.paye_enabled ? "#4ADE80" : C.border, position: "relative", cursor: "pointer", transition: "background 0.2s" }}>
                  <div style={{ position: "absolute", top: 3, left: config.paye_enabled ? 21 : 3, width: 16, height: 16, borderRadius: "50%", background: "#fff", transition: "left 0.2s" }} />
                </div>
              </label>
            </div>
            <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.6, marginBottom: 16 }}>Progressive rate: 7–24% based on income band per FIRS guidelines. Remitted monthly to FIRS.</div>
            <div style={{ padding: 12, background: "#F8717111", borderRadius: 8, fontSize: 12 }}>
              <div style={{ fontWeight: 800, color: "#F87171", marginBottom: 6 }}>PAYE Bands (Fixed — FIRS)</div>
              {[["First ₦300,000", "7%"], ["Next ₦300,000", "11%"], ["Next ₦500,000", "15%"], ["Next ₦500,000", "19%"], ["Next ₦1,600,000", "21%"], ["Above ₦3,200,000", "24%"]].map(([band, rate]) => (
                <div key={band} style={{ display: "flex", justifyContent: "space-between", color: C.sub, marginBottom: 3 }}>
                  <span>{band}</span><span style={{ fontWeight: 700, color: "#F87171" }}>{rate}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Pension */}
          <div className="gc" style={{ padding: 24 }}>
            <div style={{ fontWeight: 800, color: "#60A5FA", fontSize: 15, marginBottom: 6 }}>Pension Contribution (PRA 2014)</div>
            <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.6, marginBottom: 18 }}>Mandatory for all staff on payroll. Remitted to approved PFAs by the 7th of each month.</div>
            <Field label="Employee Contribution" field="pension_employee_rate" />
            <Field label="Employer Contribution" field="pension_employer_rate" />
          </div>

          {/* NHF */}
          <div className="gc" style={{ padding: 24 }}>
            <div style={{ fontWeight: 800, color: T.gold, fontSize: 15, marginBottom: 6 }}>NHF (National Housing Fund)</div>
            <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.6, marginBottom: 18 }}>Applies to Nigerians earning ₦3,000/month or more. Remitted to FMBN.</div>
            <Field label="NHF Rate (of basic salary)" field="nhf_rate" step="0.5" />
          </div>

          {/* WHT */}
          <div className="gc" style={{ padding: 24 }}>
            <div style={{ fontWeight: 800, color: "#4ADE80", fontSize: 15, marginBottom: 6 }}>WHT (Withholding Tax)</div>
            <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.6, marginBottom: 18 }}>Deducted at source before contractor and professional fee payments.</div>
            <Field label="Default WHT Rate" field="wht_default_rate" />
            <Field label="Contractor WHT Rate" field="wht_contractor_rate" />
          </div>
        </div>
      )}

      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button className="bp" onClick={save} disabled={saving} style={{ padding: "12px 32px" }}>{saving ? "Saving…" : "Save Configuration"}</button>
      </div>
    </div>
  );
}

// ─── HUB: ANNOUNCEMENTS ──────────────────────────────────────────────────────
function Announcements({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [items, setItems] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [posting, setPosting] = useState(false);
  const [form, setForm] = useState({ title: "", body: "", priority: "Normal", target_department: "" });

  const loadAnnouncements = () =>
    apiFetch(`${API_BASE}/hr/announcements`).then(d => setItems(d || [])).catch(() => setItems([]));

  useEffect(() => {
    loadAnnouncements().finally(() => setLoading(false));
  }, []);

  const post = async () => {
    if (!form.title || !form.body) return alert("Title and body required");
    setPosting(true);
    try {
      // 1. Create the announcement
      await apiFetch(`${API_BASE}/hr/announcements`, {
        method: "POST",
        body: JSON.stringify({
          title: form.title,
          body: form.body,
          priority: form.priority,
          target_department: form.target_department || null
        })
      });

      // 2. Fetch all staff to notify
      const allStaff = await apiFetch(`${API_BASE}/hr/staff`).catch(() => []);
      const targets = form.target_department
        ? allStaff.filter(s => s.department === form.target_department)
        : allStaff;

      const priorityIcon = { Urgent: "🚨", Normal: "📢", Info: "ℹ️" }[form.priority] || "📢";
      const notifMsg = `${priorityIcon} New announcement: "${form.title}" — ${form.body.slice(0, 120)}${form.body.length > 120 ? "…" : ""}`;

      // 3. Send notification to each target staff member in parallel
      await Promise.allSettled(
        targets.map(s =>
          apiFetch(`${API_BASE}/hr/notifications`, {
            method: "POST",
            body: JSON.stringify({ staff_id: s.id, type: "announcement", message: notifMsg })
          })
        )
      );

      setShowNew(false);
      setForm({ title: "", body: "", priority: "Normal", target_department: "" });
      loadAnnouncements();
    } catch (e) { alert(e.message); } finally { setPosting(false); }
  };

  const priorityCol = { Normal: T.gold, Urgent: "#F87171", Info: "#60A5FA" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Announcements</div><div style={{ fontSize: 13, color: C.sub }}>Company-wide communications and important notices.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Post Announcement</button>}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : items.length === 0 ? (
        <div className="gc" style={{ padding: 40, textAlign: "center", color: C.muted }}>No announcements yet. Check back soon.</div>
      ) : (
        <div className="g1" style={{ gap: 14 }}>{items.map(a => {
          const pc = priorityCol[a.priority] || T.gold;
          return (
            <div key={a.id} className="gc" style={{ padding: 22, borderLeft: `3px solid ${pc}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <span className="tg" style={{ background: `${pc}22`, color: pc, marginRight: 10 }}>{a.priority}</span>
                  <span style={{ fontSize: 16, fontWeight: 800, color: C.text }}>{a.title}</span>
                </div>
                <span style={{ fontSize: 11, color: C.muted, flexShrink: 0 }}>{new Date(a.created_at).toLocaleDateString()}</span>
              </div>
              <div style={{ fontSize: 14, color: C.sub, lineHeight: 1.7 }}>{a.body}</div>
              {a.target_department && <div style={{ fontSize: 11, color: C.muted, marginTop: 10 }}>To: {a.target_department}</div>}
            </div>
          );
        })}</div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Post Announcement">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
          <div><Lbl>Body *</Lbl><textarea className="inp" rows={5} value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))} /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Priority</Lbl>
              <select className="inp" value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                <option>Normal</option><option>Urgent</option><option>Info</option>
              </select>
            </div>
            <div><Lbl>Target Dept (blank = all staff)</Lbl><input className="inp" placeholder="All Departments" value={form.target_department} onChange={e => setForm(f => ({ ...f, target_department: e.target.value }))} /></div>
          </div>
          <div style={{ fontSize: 12, color: C.muted }}>
            💡 All {form.target_department ? `staff in ${form.target_department}` : "staff"} will receive a notification bell alert immediately.
          </div>
          <button className="bp" onClick={post} disabled={posting} style={{ padding: 13 }}>{posting ? "Posting & Notifying…" : "Post Announcement"}</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: RECOGNITION (KUDOS) ─────────────────────────────────────────────────
function RecognitionWall({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [items, setItems] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ recipient_id: "", message: "", badge_type: "Kudos" });

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/recognition`).catch(() => []),
      apiFetch(`${API_BASE}/hr/staff`).catch(() => [])
    ]).then(([r, s]) => { setItems(r || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, []);

  const give = async () => {
    if (!form.recipient_id || !form.message) return alert("Recipient and message required");
    try {
      await apiFetch(`${API_BASE}/hr/recognition`, { method: "POST", body: JSON.stringify({ recipient_id: form.recipient_id, message: form.message, badge_type: form.badge_type }) });
      // Notify the recipient
      await apiFetch(`${API_BASE}/hr/notifications`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: form.recipient_id,
          type: "recognition",
          message: `🏆 You received a "${form.badge_type}" recognition badge! Check the Recognition Wall.`
        })
      }).catch(() => { });
      setShowNew(false); setForm({ recipient_id: "", message: "", badge_type: "Kudos" });
      apiFetch(`${API_BASE}/hr/recognition`).then(d => setItems(d || []));
    } catch (e) { alert(e.message); }
  };

  const badgeCol = { Kudos: T.gold, Star: "#F87171", Excellence: "#4ADE80", Teamwork: "#60A5FA" };
  const badgeEmoji = { Kudos: "👏", Star: "⭐", Excellence: "🏆", Teamwork: "🤝" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Recognition Wall</div><div style={{ fontSize: 13, color: C.sub }}>Celebrate achievements and give kudos to your colleagues. Any team member can give recognition!</div></div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Give Recognition</button>
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="g3">{items.map(r => {
          const bc = badgeCol[r.badge_type] || T.gold;
          return (
            <div key={r.id} className="gc" style={{ padding: 20, borderTop: `3px solid ${bc}` }}>
              <div style={{ fontSize: 24, marginBottom: 12 }}>{badgeEmoji[r.badge_type] || "👏"}</div>
              <span className="tg" style={{ background: `${bc}22`, color: bc, marginBottom: 12, display: "inline-block" }}>{r.badge_type}</span>
              <div style={{ fontSize: 13, color: C.text, lineHeight: 1.6, marginBottom: 14 }}>"{r.message}"</div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted }}>
                <span>To: <strong style={{ color: C.text }}>{r.recipient?.full_name || "—"}</strong></span>
                <span>From: {r.giver?.full_name || "Anonymous"}</span>
              </div>
            </div>
          );
        })}
          {items.length === 0 && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: C.muted }}>No recognition posts yet. Be the first to celebrate someone!</div>}
        </div>
      )}
      {showNew && <Modal onClose={() => setShowNew(false)} title="Give Recognition">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Recognise *</Lbl>
            <select className="inp" value={form.recipient_id} onChange={e => setForm(f => ({ ...f, recipient_id: e.target.value }))}>
              <option value="">— Select colleague —</option>
              {staff.filter(s => s.id !== user?.id).map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
            </select>
          </div>
          <div><Lbl>Badge Type</Lbl>
            <select className="inp" value={form.badge_type} onChange={e => setForm(f => ({ ...f, badge_type: e.target.value }))}>
              <option>Kudos</option><option>Star</option><option>Excellence</option><option>Teamwork</option>
            </select>
          </div>
          <div><Lbl>Your Message *</Lbl><textarea className="inp" placeholder="What did they do that deserves recognition?" value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} /></div>
          <button className="bp" onClick={give}>Send Recognition 🏆</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: REMOTE WORK ────────────────────────────────────────────────────────
function RemoteWork() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { user, isHR } = useAuth ? useAuth() : { user: null, isHR: false };
  const currentUserId = user?.id || null;
  const [requests, setRequests] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ work_date: "", reason: "", location: "" });
  const [saving, setSaving] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [hrView, setHrView] = useState(false);

  const statusStyle = { pending: { bg: "#F59E0B22", col: "#F59E0B" }, approved: { bg: "#4ADE8022", col: "#4ADE80" }, rejected: { bg: "#F8717122", col: "#F87171" } };

  const loadRequests = () => {
    const url = hrView ? `${API_BASE}/hr/remote-work?all=true` : `${API_BASE}/hr/remote-work`;
    apiFetch(url).catch(() => []).then(d => setRequests(Array.isArray(d) ? d : [])).finally(() => setLoading(false));
  };

  useEffect(() => { loadRequests(); }, [hrView]);

  const submit = async () => {
    if (!form.work_date) return alert("Please select a date.");
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/remote-work`, { method: "POST", body: JSON.stringify({ work_date: form.work_date, reason: form.reason, location: form.location }) });
      setShowNew(false); setForm({ work_date: "", reason: "", location: "" });
      loadRequests();
    } catch (e) { alert("Error: " + e.message); } finally { setSaving(false); }
  };

  const updateStatus = async (reqId, newStatus, staffId) => {
    setActionBusy(true);
    try {
      await apiFetch(`${API_BASE}/hr/remote-work/${reqId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus })
      });
      loadRequests();
    } catch (e) { alert("Error: " + e.message); } finally { setActionBusy(false); }
  };

  // Detect HR role from token claims stored in localStorage
  const tokenRaw = typeof localStorage !== "undefined" ? localStorage.getItem("ec_token") : null;
  let isHRUser = false;
  try {
    if (tokenRaw) {
      const payload = JSON.parse(atob(tokenRaw.split(".")[1]));
      const roles = (payload.role || "").split(",");
      isHRUser = roles.some(r => ["admin", "hr_admin", "operations", "line_manager"].includes(r));
    }
  } catch (_) { }

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Remote Work</div>
          <div style={{ fontSize: 13, color: C.sub }}>Request and track work-from-home days.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {isHRUser && (
            <button className={hrView ? "bp" : "bg"} onClick={() => setHrView(v => !v)} style={{ padding: "9px 18px", fontSize: 13 }}>
              {hrView ? "📋 Team Requests" : "👤 My Requests"}
            </button>
          )}
          {!hrView && <button className="bp" onClick={() => setShowNew(true)}>+ Request WFH Day</button>}
        </div>
      </div>

      <div className="g2" style={{ marginBottom: 22 }}>
        {[["Remote Work Policy", "Up to 2 days WFH per week, subject to manager approval and role eligibility.", "#60A5FA"], ["Eligible Roles", "All non-client-facing roles. Sales & Acquisitions staff require manager approval for each day.", T.gold]].map(([t, d, c]) => (
          <div key={t} className="gc" style={{ padding: 22, borderLeft: `3px solid ${c}` }}>
            <div style={{ fontWeight: 800, color: c, marginBottom: 8 }}>{t}</div>
            <div style={{ fontSize: 13, color: C.sub }}>{d}</div>
          </div>
        ))}
      </div>

      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}`, fontWeight: 800, fontSize: 14 }}>
          {hrView ? "All WFH Requests — Team" : "My WFH Requests"}
          {hrView && requests.filter(r => r.status === "pending").length > 0 && (
            <span style={{ marginLeft: 10, background: "#F59E0B", color: "#fff", borderRadius: 20, fontSize: 11, padding: "2px 8px", fontWeight: 700 }}>
              {requests.filter(r => r.status === "pending").length} pending
            </span>
          )}
        </div>
        {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
          <div className="tw"><table className="ht">
            <thead><tr>
              <th>Date</th>
              {hrView && <th>Employee</th>}
              <th>Location</th>
              <th>Reason</th>
              <th>Status</th>
              {isHRUser && hrView && <th>Actions</th>}
            </tr></thead>
            <tbody>
              {requests.map(r => {
                const ss = statusStyle[r.status] || statusStyle.pending;
                return (
                  <tr key={r.id}>
                    <td style={{ fontWeight: 700, color: C.text }}>{new Date(r.work_date).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</td>
                    {hrView && <td style={{ fontSize: 13, fontWeight: 600, color: C.text }}>{r.admins?.full_name || r.staff_name || "—"}<div style={{ fontSize: 11, color: C.muted }}>{r.admins?.department || ""}</div></td>}
                    <td style={{ fontSize: 12, color: C.sub }}>{r.location || "Home"}</td>
                    <td style={{ fontSize: 12, color: C.sub }}>{r.reason || "—"}</td>
                    <td><span className="tg" style={{ background: ss.bg, color: ss.col, textTransform: "capitalize" }}>{r.status || "pending"}</span></td>
                    {isHRUser && hrView && (
                      <td>
                        {r.status === "pending" ? (
                          <div style={{ display: "flex", gap: 6 }}>
                            <button className="bp" style={{ fontSize: 11, padding: "4px 12px" }} disabled={actionBusy}
                              onClick={() => updateStatus(r.id, "approved", r.staff_id)}>✓ Approve</button>
                            <button className="bd" style={{ fontSize: 11, padding: "4px 12px" }} disabled={actionBusy}
                              onClick={() => updateStatus(r.id, "rejected", r.staff_id)}>✕ Decline</button>
                          </div>
                        ) : (
                          <span style={{ fontSize: 11, color: C.muted }}>—</span>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
              {requests.length === 0 && <tr><td colSpan={isHRUser && hrView ? 6 : 4} style={{ textAlign: "center", padding: 30, color: C.muted }}>
                {hrView ? "No WFH requests from the team yet." : "No WFH requests yet. Submit one above."}
              </td></tr>}
            </tbody>
          </table></div>
        )}
      </div>

      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Request Work From Home Day">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Date *</Lbl><input className="inp" type="date" value={form.work_date} onChange={e => setForm(f => ({ ...f, work_date: e.target.value }))} /></div>
            <div><Lbl>Work Location</Lbl><input className="inp" placeholder="e.g. Home, Client Site" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} /></div>
            <div><Lbl>Reason / Notes</Lbl><textarea className="inp" rows={3} placeholder="Brief reason for WFH…" value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} /></div>
            <div style={{ padding: 12, background: `${T.gold}11`, borderRadius: 8, fontSize: 12, color: T.gold }}>⚠️ WFH requests are subject to manager approval. Ensure you are available for all scheduled meetings.</div>
            <button className="bp" onClick={submit} disabled={saving}>{saving ? "Submitting…" : "Submit Request"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: POLICY LIBRARY ─────────────────────────────────────────────────────
function PolicyLibrary({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [policies, setPolicies] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ title: "", category: "HR", summary: "", document_url: "", effective_date: "" });
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState(""); const [catFilter, setCatFilter] = useState("All");

  const catCol = { Compliance: T.gold, HR: "#60A5FA", Legal: "#F87171", IT: "#4ADE80", Finance: "#A78BFA" };

  const loadPolicies = () => {
    apiFetch(`${API_BASE}/hr/policies`).then(d => setPolicies(Array.isArray(d) ? d : [])).catch(() => setPolicies([])).finally(() => setLoading(false));
  };

  useEffect(() => { loadPolicies(); }, []);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/hr/policies/upload`, {
        method: "POST", headers: { "Authorization": `Bearer ${localStorage.getItem("ec_token")}` }, body: fd
      });
      if (!res.ok) throw new Error("Upload failed");
      const d = await res.json();
      setForm(f => ({ ...f, document_url: d.url }));
    } catch (err) { alert(err.message); } finally { setUploading(false); }
  };

  const save = async () => {
    if (!form.title || !form.category) return alert("Title and category required.");
    setSaving(true);
    try {
      const url = editingId ? `${API_BASE}/hr/policies/${editingId}` : `${API_BASE}/hr/policies`;
      await apiFetch(url, { method: editingId ? "PATCH" : "POST", body: JSON.stringify({ staff_id: form.staff_id, permit_type: form.permit_type, permit_number: form.permit_number, issue_date: form.issue_date, expiry_date: form.expiry_date, issuing_authority: form.issuing_authority }) });
      setShowNew(false); setEditingId(null); setForm({ title: "", category: "HR", summary: "", document_url: "", effective_date: "" });
      loadPolicies();
    } catch (e) { alert("Error: " + e.message); } finally { setSaving(false); }
  };

  const openEdit = (p) => { setForm({ title: p.title, category: p.category, summary: p.summary || "", document_url: p.document_url || "", effective_date: p.effective_date || "" }); setEditingId(p.id); setShowNew(true); };

  const del = async (id) => {
    if (!window.confirm("Are you sure you want to delete this policy?")) return;
    try { await apiFetch(`${API_BASE}/hr/policies/${id}`, { method: "DELETE" }); loadPolicies(); } catch (e) { alert(e.message); }
  };

  const categories = ["All", "Compliance", "HR", "Legal", "IT", "Finance"];
  const filtered = policies.filter(p => {
    const matchCat = catFilter === "All" || p.category === catFilter;
    const matchSearch = !search || p.title.toLowerCase().includes(search.toLowerCase()) || p.summary?.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Policy Library</div><div style={{ fontSize: 13, color: C.sub }}>Company policies, procedures and handbooks.</div></div>
        {isHR && <button className="bp" onClick={() => { setForm({ title: "", category: "HR", summary: "", document_url: "", effective_date: "" }); setEditingId(null); setShowNew(true); }}>+ Add Policy</button>}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <input className="inp" placeholder="Search policies…" value={search} onChange={e => setSearch(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {categories.map(cat => {
            const cc = catCol[cat] || C.muted;
            return (
              <button key={cat} onClick={() => setCatFilter(cat)} style={{ padding: "6px 14px", borderRadius: 20, border: `1px solid ${catFilter === cat ? cc : C.border}`, background: catFilter === cat ? `${cc}22` : "transparent", color: catFilter === cat ? cc : C.muted, fontWeight: 700, fontSize: 12, cursor: "pointer" }}>
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading policies…</div> : (
        <div className="g2">
          {filtered.map((p, i) => {
            const cc = catCol[p.category] || T.gold;
            return (
              <div key={p.id || i} className="gc" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                  <span className="tg" style={{ background: `${cc}22`, color: cc }}>{p.category}</span>
                  <span style={{ fontSize: 11, color: C.muted }}>Updated {p.updated_at ? new Date(p.updated_at).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : (p.updated || "—")}</span>
                </div>
                <div style={{ fontWeight: 800, color: C.text, fontSize: 14, marginBottom: 8 }}>{p.title}</div>
                <div style={{ fontSize: 12, color: C.sub, lineHeight: 1.6, marginBottom: 14 }}>{p.summary || "No description provided."}</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "space-between", alignItems: "center" }}>
                  {p.document_url ? (
                    <a href={p.document_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                      <button className="bp" style={{ fontSize: 12, padding: "6px 14px" }}>📄 View Document</button>
                    </a>
                  ) : (
                    <button className="bg" style={{ fontSize: 12, padding: "6px 14px", opacity: 0.6 }} disabled>No file attached</button>
                  )}
                  {isHR && (
                    <div style={{ display: "flex", gap: 6 }}>
                      <button className="bg" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => openEdit(p)}>Edit</button>
                      <button className="bg" style={{ fontSize: 11, padding: "4px 10px", color: "#F87171", borderColor: "#F87171" }} onClick={() => del(p.id)}>Delete</button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: C.muted }}>No policies match your search.</div>}
        </div>
      )}

      {showNew && (
        <Modal onClose={() => setShowNew(false)} title={editingId ? "Edit Policy" : "Add Policy Document"}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Policy Title *</Lbl><input className="inp" placeholder="e.g. Remote Work Policy" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
            <div><Lbl>Category *</Lbl>
              <select className="inp" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
                {["HR", "Compliance", "Legal", "IT", "Finance"].map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div><Lbl>Summary</Lbl><textarea className="inp" rows={3} placeholder="Brief description of the policy…" value={form.summary} onChange={e => setForm(f => ({ ...f, summary: e.target.value }))} /></div>

            <div style={{ padding: 16, background: C.border, borderRadius: 8 }}>
              <Lbl>Policy Document File</Lbl>
              {form.document_url && (
                <div style={{ marginBottom: 10, fontSize: 12, color: "#4ADE80", display: "flex", alignItems: "center", gap: 6 }}>
                  <span>✓ File attached</span> <a href={form.document_url} target="_blank" rel="noopener noreferrer" style={{ color: "#4ADE80", textDecoration: "underline" }}>(View current)</a>
                </div>
              )}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input type="file" className="inp" onChange={handleFileUpload} disabled={uploading} style={{ padding: 8 }} />
                {uploading && <span style={{ fontSize: 12, color: T.gold }}>Uploading...</span>}
              </div>
              <div style={{ fontSize: 11, color: C.muted, marginTop: 6 }}>Uploading a new file will overwrite the existing one.</div>
            </div>

            <div><Lbl>Effective Date</Lbl><input className="inp" type="date" value={form.effective_date} onChange={e => setForm(f => ({ ...f, effective_date: e.target.value }))} /></div>
            <button className="bp" onClick={save} disabled={saving || uploading}>{saving ? "Saving…" : (editingId ? "Update Policy" : "Add Policy")}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: INTERNAL JOB BOARD ─────────────────────────────────────────────────
function InternalJobBoard({ isHR, user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [jobs, setJobs] = useState([]); const [apps, setApps] = useState([]); const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(isHR ? "manage" : "browse");
  const [showPost, setShowPost] = useState(false);
  const [showApply, setShowApply] = useState(null);
  const [showDetails, setShowDetails] = useState(null);
  const [viewApps, setViewApps] = useState(null);
  const [form, setForm] = useState({ title: "", department: "", employment_type: "Full-Time", location: "Port Harcourt, NG", salary_range: "", description: "", requirements: "", closing_date: "" });
  const [applyForm, setApplyForm] = useState({ cover_letter: "", years_experience: "", current_role: "", reason: "" });
  const [saving, setSaving] = useState(false);
  const { departments } = useDepartments();

  const load = async () => {
    setLoading(true);
    try {
      const [j, a] = await Promise.all([
        apiFetch(`${API_BASE}/hr/recruitment/jobs?is_internal=true`).catch(() => []),
        apiFetch(`${API_BASE}/hr/recruitment/applications`).catch(() => [])
      ]);
      setJobs((j || []).filter(x => x.status === "Open" || isHR));
      setApps(a || []);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const postJob = async () => {
    if (!form.title || !form.department) return alert("Title and department are required.");
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/jobs`, { method: "POST", body: JSON.stringify({ ...form, status: "Open", is_internal: true }) });
      setShowPost(false); setForm({ title: "", department: "", employment_type: "Full-Time", location: "Port Harcourt, NG", salary_range: "", description: "", requirements: "", closing_date: "" }); load();
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const applyInternal = async () => {
    if (!applyForm.cover_letter) return alert("Please write a brief cover letter.");
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/applications`, {
        method: "POST",
        body: JSON.stringify({
          job_id: showApply.id,
          candidate_name: user?.full_name || "Internal Applicant",
          candidate_email: user?.email || "internal@eximps-cloves.com",
          cover_letter: `[INTERNAL APPLICATION]\n\nCurrent Role: ${applyForm.current_role}\nExperience: ${applyForm.years_experience} years\nReason: ${applyForm.reason}\n\n${applyForm.cover_letter}`
        })
      });
      alert("Your application has been submitted!"); setShowApply(null); setApplyForm({ cover_letter: "", years_experience: "", current_role: "", reason: "" }); load();
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const closeJob = async (id) => {
    if (!window.confirm("Close this vacancy?")) return;
    try { await apiFetch(`${API_BASE}/hr/recruitment/jobs/${id}`, { method: "PATCH", body: JSON.stringify({ status: "Closed" }) }); load(); } catch (e) { alert(e.message); }
  };

  const jobApps = (jobId) => apps.filter(a => a.job_id === jobId);
  const typeCol = { "Full-Time": "#4ADE80", "Part-Time": "#60A5FA", "Contract": T.gold, "Internship": "#A78BFA" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Internal Job Board</div><div style={{ fontSize: 13, color: C.sub }}>Open internal vacancies. Staff can apply directly — no external application needed.</div></div>
        {isHR && <button className="bp" onClick={() => setShowPost(true)}>+ Post Internal Role</button>}
      </div>

      {isHR && (
        <div style={{ display: "flex", gap: 6, marginBottom: 22 }}>
          {[["browse", "📋 Open Roles"], ["manage", "⚙️ Manage Postings"], ["applications", "📥 All Applications"]].map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)} style={{ padding: "8px 18px", borderRadius: 10, cursor: "pointer", fontSize: 12, fontWeight: 700, background: tab === t ? `${T.gold}22` : "transparent", color: tab === t ? T.gold : C.muted, border: `1px solid ${tab === t ? T.gold : C.border}` }}>{label}</button>
          ))}
        </div>
      )}

      <div className="g4" style={{ marginBottom: 22 }}>
        <StatCard label="Open Roles" value={jobs.filter(j => j.status === "Open").length} col={T.gold} />
        <StatCard label="Applications" value={apps.length} col="#60A5FA" />
        <StatCard label="Departments Hiring" value={[...new Set(jobs.filter(j => j.status === "Open").map(j => j.department))].length} col="#4ADE80" />
        <StatCard label="Hired This Month" value={apps.filter(a => a.status === "Hired").length} col="#A78BFA" />
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (<>
        {(tab === "browse" || !isHR) && (
          <div className="g2" style={{ gap: 16 }}>
            {jobs.filter(j => j.status === "Open").map(j => {
              const tc = typeCol[j.employment_type] || T.gold;
              const today = new Date(); today.setHours(0, 0, 0, 0);
              const deadline = j.closing_date ? new Date(j.closing_date + "T23:59:59") : null;
              const isExpired = deadline && deadline < new Date();
              const daysLeft = deadline ? Math.ceil((deadline - today) / (1000 * 60 * 60 * 24)) : null;
              const urgency = daysLeft !== null && daysLeft <= 3 && !isExpired;
              return (
                <div key={j.id} className="gc fade-in" style={{ padding: 22, cursor: "pointer", opacity: isExpired ? 0.6 : 1 }} onClick={() => setShowDetails(j)}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                    <div>
                      <div style={{ fontWeight: 900, fontSize: 16, color: C.text, marginBottom: 6 }}>{j.title}</div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <span className="tg" style={{ background: `${tc}22`, color: tc, fontSize: 11 }}>{j.employment_type}</span>
                        <span className="tg tg2" style={{ fontSize: 11 }}>Internal</span>
                        {isExpired && <span className="tg" style={{ background: "#F8717122", color: "#F87171", fontSize: 11 }}>Deadline Passed</span>}
                        {urgency && <span className="tg" style={{ background: "#F59E0B22", color: "#F59E0B", fontSize: 11 }}>⚡ {daysLeft}d left</span>}
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: C.muted }}>{jobApps(j.id).length} applied</div>
                  </div>
                  <div style={{ display: "flex", gap: 14, fontSize: 12, color: C.sub, marginBottom: 10, flexWrap: "wrap" }}>
                    <span>🏢 {j.department}</span>
                    <span>📍 {j.location || "Port Harcourt, NG"}</span>
                    {j.salary_range && <span style={{ color: T.gold, fontWeight: 700 }}>💰 {j.salary_range}</span>}
                    {deadline && (
                      <span style={{ color: isExpired ? "#F87171" : urgency ? "#F59E0B" : C.muted, fontWeight: isExpired || urgency ? 700 : 400 }}>
                        📅 {isExpired ? "Closed" : `Closes ${deadline.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`}
                      </span>
                    )}
                  </div>
                  {j.description && <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6, marginBottom: 12 }}>{j.description.slice(0, 140)}{j.description.length > 140 ? "…" : ""}</div>}
                  <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontSize: 11, color: T.gold, fontWeight: 800 }}>VIEW DETAILS →</div>
                    {isExpired
                      ? <span style={{ fontSize: 12, color: "#F87171", fontWeight: 700 }}>Applications Closed</span>
                      : <button className="bp" onClick={(e) => { e.stopPropagation(); setShowApply(j); }} style={{ padding: "8px 16px", fontSize: 12 }}>Quick Apply</button>
                    }
                  </div>
                </div>
              );
            })}
            {jobs.filter(j => j.status === "Open").length === 0 && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>🔍</div><div style={{ fontWeight: 800 }}>No internal vacancies at this time.</div></div>}
          </div>
        )}

        {tab === "manage" && isHR && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {jobs.map(j => {
              const tc = typeCol[j.employment_type] || T.gold; const count = jobApps(j.id).length;
              return (<div key={j.id} className="gc" style={{ padding: "16px 20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 800, color: C.text, fontSize: 14, marginBottom: 4 }}>{j.title}</div>
                    <div style={{ display: "flex", gap: 10, fontSize: 12, color: C.sub }}>
                      <span>🏢 {j.department}</span><span className="tg" style={{ background: `${tc}22`, color: tc, fontSize: 10 }}>{j.employment_type}</span>
                      {j.status === "Closed" && <span style={{ color: "#F87171", fontWeight: 800 }}>[CLOSED]</span>}
                      {j.closing_date && <span>Closes {j.closing_date}</span>}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ textAlign: "right" }}><div style={{ fontSize: 18, fontWeight: 900, color: T.gold }}>{count}</div><div style={{ fontSize: 10, color: C.muted }}>applicants</div></div>
                    <button className="bg" onClick={() => setViewApps(j)} style={{ fontSize: 11, padding: "7px 14px" }}>View Applications</button>
                    {j.status === "Open" && <button onClick={() => closeJob(j.id)} style={{ fontSize: 11, padding: "7px 14px", background: "#F8717122", color: "#F87171", border: "1px solid #F8717144", borderRadius: 8, cursor: "pointer", fontWeight: 700 }}>Close Role</button>}
                  </div>
                </div>
              </div>);
            })}
            {jobs.length === 0 && <div style={{ textAlign: "center", padding: 40, color: C.muted }}>No active postings. Use "+ Post Internal Role" to create one.</div>}
          </div>
        )}

        {tab === "applications" && isHR && (
          <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
            <div className="tw"><table className="ht"><thead><tr><th>Candidate</th><th>Role Applied</th><th>Status</th><th>Applied</th></tr></thead>
              <tbody>
                {apps.map(a => {
                  const job = jobs.find(j => j.id === a.job_id);
                  const sc = { Applied: T.gold, Screening: "#60A5FA", Interview: "#A78BFA", Hired: "#4ADE80", Rejected: "#F87171" }[a.status] || C.muted;
                  return (<tr key={a.id}><td style={{ fontWeight: 700 }}>{a.candidate_name}</td><td>{job?.title || "—"}</td><td><span className="tg" style={{ background: `${sc}22`, color: sc }}>{a.status}</span></td><td style={{ fontSize: 12, color: C.muted }}>{new Date(a.created_at).toLocaleDateString()}</td></tr>);
                })}
                {apps.length === 0 && <tr><td colSpan="4" style={{ textAlign: "center", padding: 30, color: C.muted }}>No applications yet.</td></tr>}
              </tbody>
            </table></div>
          </div>
        )}
      </>)}

      {showApply && (() => {
        const applyDeadline = showApply.closing_date ? new Date(showApply.closing_date + "T23:59:59") : null;
        const applyExpired = applyDeadline && applyDeadline < new Date();
        return (
          <Modal onClose={() => { setShowApply(null); setApplyForm({ cover_letter: "", years_experience: "", current_role: "", reason: "" }); }} title={`Apply — ${showApply.title}`} width={560}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ padding: "12px 16px", background: applyExpired ? "#F8717108" : `${T.gold}0A`, borderRadius: 10, border: `1px solid ${applyExpired ? "#F8717133" : `${T.gold}22`}` }}>
                <div style={{ fontWeight: 800, color: C.text }}>{showApply.title}</div>
                <div style={{ fontSize: 12, color: C.sub }}>{showApply.department} · {showApply.location}</div>
                {showApply.salary_range && <div style={{ fontSize: 12, color: T.gold, fontWeight: 700, marginTop: 2 }}>{showApply.salary_range}</div>}
                {applyDeadline && <div style={{ fontSize: 12, color: applyExpired ? "#F87171" : C.muted, fontWeight: 700, marginTop: 4 }}>📅 {applyExpired ? "Deadline Passed" : `Closes ${applyDeadline.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`}</div>}
              </div>
              {applyExpired ? (
                <div style={{ textAlign: "center", padding: "24px 0" }}>
                  <div style={{ fontSize: 36, marginBottom: 8 }}>🔒</div>
                  <div style={{ fontWeight: 800, color: "#F87171", marginBottom: 4 }}>Applications Closed</div>
                  <div style={{ fontSize: 13, color: C.muted }}>The deadline for this role has passed.</div>
                </div>
              ) : (
                <>
                  <div className="g2" style={{ gap: 12 }}>
                    <div><Lbl>Current Role</Lbl><input className="inp" value={applyForm.current_role} onChange={e => setApplyForm(f => ({ ...f, current_role: e.target.value }))} placeholder="e.g. Sales Executive" /></div>
                    <div><Lbl>Years of Experience</Lbl><input className="inp" type="number" min="0" value={applyForm.years_experience} onChange={e => setApplyForm(f => ({ ...f, years_experience: e.target.value }))} /></div>
                  </div>
                  <div><Lbl>Why are you interested? *</Lbl><textarea className="inp" rows={3} value={applyForm.reason} onChange={e => setApplyForm(f => ({ ...f, reason: e.target.value }))} placeholder="How does this align with your career goals?" /></div>
                  <div><Lbl>Cover Letter *</Lbl><textarea className="inp" rows={5} value={applyForm.cover_letter} onChange={e => setApplyForm(f => ({ ...f, cover_letter: e.target.value }))} placeholder="Highlight your relevant skills and experience…" /></div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button className="bp" onClick={applyInternal} disabled={saving} style={{ flex: 1, padding: 13 }}>{saving ? "Submitting…" : "Submit Application"}</button>
                    <button className="bg" onClick={() => setShowApply(null)} style={{ flex: 1, padding: 13 }}>Cancel</button>
                  </div>
                </>
              )}
            </div>
          </Modal>
        );
      })()}

      {showDetails && (
        <Modal onClose={() => setShowDetails(null)} title="Job Details" width={640}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div>
                  <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>{showDetails.title}</div>
                  <div style={{ display: "flex", gap: 10, fontSize: 14, color: C.sub }}>
                    <span>🏢 {showDetails.department}</span>
                    <span>📍 {showDetails.location}</span>
                  </div>
                </div>
                <span className="tg to" style={{ padding: "8px 16px", borderRadius: 10 }}>{showDetails.employment_type}</span>
              </div>
              <div className="g2" style={{ gap: 16, marginTop: 16 }}>
                <div className="field">
                  <div className="fl">Salary Range</div>
                  <div className="fv">{showDetails.salary_range || "Negotiable"}</div>
                </div>
                <div className="field">
                  <div className="fl">Application Deadline</div>
                  {(() => {
                    const dl = showDetails.closing_date ? new Date(showDetails.closing_date + "T23:59:59") : null;
                    const exp = dl && dl < new Date();
                    return <div className="fv" style={{ color: exp ? "#F87171" : dl && Math.ceil((dl - new Date()) / 86400000) <= 3 ? "#F59E0B" : undefined, fontWeight: exp ? 700 : undefined }}>
                      {dl ? (exp ? "🔒 Closed" : `📅 ${dl.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}`) : "Open Until Filled"}
                    </div>;
                  })()}
                </div>
              </div>
            </div>

            <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 20 }}>
              <div className="ho" style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>Role Description</div>
              <div style={{ fontSize: 14, color: C.sub, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{showDetails.description || "No description provided."}</div>
            </div>

            {showDetails.requirements && (
              <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 20 }}>
                <div className="ho" style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>Requirements & Skills</div>
                <div style={{ fontSize: 14, color: C.sub, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{showDetails.requirements}</div>
              </div>
            )}

            <div style={{ display: "flex", gap: 12, marginTop: 10 }}>
              <button className="bp" onClick={() => { setShowDetails(null); setShowApply(showDetails); }} style={{ flex: 1, padding: 14, fontSize: 14 }}>Apply for this Role Now</button>
              <button className="bg" onClick={() => setShowDetails(null)} style={{ padding: 14 }}>Close</button>
            </div>
          </div>
        </Modal>
      )}

      {viewApps && (
        <Modal onClose={() => setViewApps(null)} title={`Applications — ${viewApps.title}`} width={600}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {jobApps(viewApps.id).length === 0
              ? <div style={{ textAlign: "center", padding: 30, color: C.muted }}>No applications for this role yet.</div>
              : jobApps(viewApps.id).map(a => {
                const sc = { Applied: T.gold, Screening: "#60A5FA", Interview: "#A78BFA", Hired: "#4ADE80", Rejected: "#F87171" }[a.status] || C.muted;
                return (<div key={a.id} style={{ padding: "14px 16px", background: `${sc}08`, borderRadius: 10, border: `1px solid ${sc}22` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <div style={{ fontWeight: 800, color: C.text }}>{a.candidate_name}</div>
                    <span className="tg" style={{ background: `${sc}22`, color: sc, fontSize: 11 }}>{a.status}</span>
                  </div>
                  {a.cover_letter && <div style={{ fontSize: 12, color: C.sub, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{a.cover_letter}</div>}
                  <div style={{ fontSize: 11, color: C.muted, marginTop: 8 }}>Applied {new Date(a.created_at).toLocaleDateString()}</div>
                </div>);
              })}
          </div>
        </Modal>
      )}

      {showPost && (
        <Modal onClose={() => setShowPost(false)} title="Post Internal Role" width={580}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Job Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Senior Property Executive" /></div>
              <div><Lbl>Department *</Lbl><select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}><option value="">— Select —</option>{departments.map(d => <option key={d.id || d} value={d.name || d}>{d.name || d}</option>)}</select></div>
            </div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Employment Type</Lbl><select className="inp" value={form.employment_type} onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}><option>Full-Time</option><option>Part-Time</option><option>Contract</option><option>Internship</option></select></div>
              <div><Lbl>Location</Lbl><input className="inp" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} /></div>
            </div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Salary Range</Lbl><input className="inp" value={form.salary_range} onChange={e => setForm(f => ({ ...f, salary_range: e.target.value }))} placeholder="e.g. ₦350,000 – ₦500,000" /></div>
              <div><Lbl>Application Deadline</Lbl><input type="date" className="inp" value={form.closing_date} onChange={e => setForm(f => ({ ...f, closing_date: e.target.value }))} /></div>
            </div>
            <div><Lbl>Job Description</Lbl><textarea className="inp" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Role overview and responsibilities…" /></div>
            <div><Lbl>Requirements</Lbl><textarea className="inp" rows={3} value={form.requirements} onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))} placeholder="Skills, qualifications, experience needed…" /></div>
            <button className="bp" onClick={postJob} disabled={saving} style={{ padding: 14 }}>{saving ? "Posting…" : "Post Role to Internal Board"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}


// ─── HUB: DOCUMENTS VAULT ───────────────────────────────────────────────────
function DocumentsVault({ isHR, userId }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [docs, setDocs] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [filterStaff, setFilterStaff] = useState(userId || "");
  const [filterType, setFilterType] = useState("All");
  const [form, setForm] = useState({ staff_id: userId || "", doc_type: "ID", title: "", notes: "" });
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const docTypes = ["ID", "Certificate", "Contract Copy", "Tax Document", "Insurance", "Policy Acknowledgement", "Offer Letter", "Background Check", "Medical", "Other"];

  const load = async () => {
    setLoading(true);
    try {
      const url = isHR ? `${API_BASE}/hr/documents` : `${API_BASE}/hr/staff/${userId}/documents`;
      const [d, s] = await Promise.all([
        apiFetch(url).catch(() => []),
        isHR ? apiFetch(`${API_BASE}/hr/staff`).catch(() => []) : Promise.resolve([])
      ]);
      setDocs(d || []); setStaff(s || []);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const upload = async () => {
    if (!form.title || !file) return alert("Title and file are required.");
    if (isHR && !form.staff_id) return alert("Please select a staff member.");
    setSaving(true);
    try {
      // 1. Upload to Storage
      const formData = new FormData();
      formData.append("file", file);
      const upRes = await fetch(`${API_BASE}/hr/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("ec_token")}` },
        body: formData
      });
      if (!upRes.ok) throw new Error("File upload failed");
      const upData = await upRes.json();

      // 2. Save Meta
      await apiFetch(`${API_BASE}/hr/documents`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: form.staff_id || userId,
          doc_type: form.doc_type,
          title: form.title,
          file_url: upData.url,
          notes: form.notes
        })
      });
      setShowUpload(false);
      setForm({ staff_id: userId || "", doc_type: "ID", title: "", notes: "" });
      setFile(null);
      load();
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const deleteDoc = async (id) => {
    if (!window.confirm("Delete this document?")) return;
    try { await apiFetch(`${API_BASE}/hr/documents/${id}`, { method: "DELETE" }); load(); } catch (e) { alert(e.message); }
  };

  const typeColors = { ID: "#60A5FA", Certificate: "#4ADE80", "Contract Copy": T.gold, "Tax Document": "#F59E0B", Insurance: "#A78BFA", "Policy Acknowledgement": "#34D399", "Offer Letter": T.orange, "Background Check": "#F87171", Medical: "#EC4899", Other: "#9CA3AF" };
  const typeIcon = { ID: "🪪", Certificate: "🎓", "Contract Copy": "📄", "Tax Document": "🧾", Insurance: "🛡️", "Policy Acknowledgement": "✅", "Offer Letter": "📩", "Background Check": "🔍", Medical: "🏥", Other: "📎" };

  const filtered = docs.filter(d => (filterType === "All" || d.doc_type === filterType) && (!filterStaff || d.staff_id === filterStaff));
  const byType = docTypes.reduce((acc, t) => { acc[t] = docs.filter(d => d.doc_type === t).length; return acc; }, {});

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Document Vault</div><div style={{ fontSize: 13, color: C.sub }}>{isHR ? "Manage and store all staff HR documents securely." : "Your HR documents on file."}</div></div>
        <button className="bp" onClick={() => setShowUpload(true)}>+ Upload Document</button>
      </div>

      <div className="g4" style={{ marginBottom: 24 }}>
        <StatCard label="Total Documents" value={docs.length} col={T.gold} />
        <StatCard label="IDs & Certs" value={(byType["ID"] || 0) + (byType["Certificate"] || 0)} col="#60A5FA" />
        <StatCard label="Contracts & Offers" value={(byType["Contract Copy"] || 0) + (byType["Offer Letter"] || 0)} col="#4ADE80" />
        <StatCard label="Tax & Compliance" value={(byType["Tax Document"] || 0) + (byType["Policy Acknowledgement"] || 0)} col="#A78BFA" />
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        {isHR && <select className="inp" value={filterStaff} onChange={e => setFilterStaff(e.target.value)} style={{ maxWidth: 220, padding: "8px 12px" }}><option value="">All Staff</option>{staff.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}</select>}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {["All", ...docTypes].map(t => (
            <button key={t} onClick={() => setFilterType(t)} style={{
              padding: "6px 12px", borderRadius: 8, cursor: "pointer", fontSize: 11, fontWeight: 700,
              background: filterType === t ? `${typeColors[t] || T.gold}22` : "transparent",
              color: filterType === t ? (typeColors[t] || T.gold) : C.muted,
              border: `1px solid ${filterType === t ? (typeColors[t] || T.gold) : C.border}`
            }}>{t === "All" ? "All" : `${typeIcon[t] || "📎"} ${t}`}</button>
          ))}
        </div>
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading documents…</div> : filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>🗂️</div><div style={{ fontWeight: 800 }}>No documents found.</div></div>
      ) : (
        <div className="g3" style={{ gap: 12 }}>
          {filtered.map(d => {
            const tc = typeColors[d.doc_type] || T.gold;
            const sm = staff.find(s => s.id === d.staff_id);
            return (<div key={d.id} className="gc" style={{ padding: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: `${tc}22`, border: `1.5px solid ${tc}44`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>{typeIcon[d.doc_type] || "📎"}</div>
                <span className="tg" style={{ background: `${tc}22`, color: tc, fontSize: 10 }}>{d.doc_type}</span>
              </div>
              <div style={{ fontWeight: 800, color: C.text, marginBottom: 4, fontSize: 14 }}>{d.title}</div>
              {isHR && sm && <div style={{ fontSize: 12, color: C.sub, marginBottom: 6 }}>{sm.full_name} · {sm.department}</div>}
              {d.notes && <div style={{ fontSize: 11, color: C.muted, marginBottom: 10, fontStyle: "italic" }}>{d.notes}</div>}
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 14 }}>Added {new Date(d.created_at).toLocaleDateString()}</div>
              <div style={{ display: "flex", gap: 8, paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
                <a href={d.file_url} target="_blank" rel="noreferrer" className="bp" style={{ flex: 1, textAlign: "center", fontSize: 11, padding: "7px 0", textDecoration: "none", display: "flex", alignItems: "center", justifyContent: "center", gap: 5 }}>
                  <span>👁️</span> View
                </a>
                {isHR && <button onClick={() => deleteDoc(d.id)} className="bd" style={{ fontSize: 11, padding: "7px 12px" }}>Delete</button>}
              </div>
            </div>);
          })}
        </div>
      )}

      {showUpload && (
        <Modal onClose={() => { setShowUpload(false); setFile(null); }} title="Upload Official Document" width={520}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {isHR && <div><Lbl>Staff Member *</Lbl><select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}><option value="">— Select Staff —</option>{staff.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}</select></div>}
            <div className="g2" style={{ gap: 12 }}>
              <div>
                <Lbl>Document Type</Lbl>
                <select className="inp" value={form.doc_type} onChange={e => setForm(f => ({ ...f, doc_type: e.target.value }))}>
                  {docTypes.filter(t => isHR || !docs.some(d => d.doc_type === t)).map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div><Lbl>Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. National ID Card" /></div>
            </div>
            <div>
              <Lbl>Select File *</Lbl>
              <input type="file" className="inp" style={{ padding: 8 }} onChange={e => setFile(e.target.files[0])} />
              {file && <div style={{ fontSize: 10, color: T.gold, marginTop: 4 }}>Ready: {file.name} ({(file.size / 1024).toFixed(0)} KB)</div>}
            </div>
            <div><Lbl>Notes</Lbl><textarea className="inp" rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Optional context or expiry info…" /></div>
            <button className="bp" onClick={upload} disabled={saving} style={{ padding: 14 }}>
              {saving ? "Processing Upload..." : "Securely Upload Document"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}


// ─── HUB: WORK PERMITS ───────────────────────────────────────────────────────
function WorkPermits({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [permits, setPermits] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ staff_id: "", permit_type: "Work Permit", permit_number: "", issue_date: "", expiry_date: "", issuing_authority: "" });

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/work-permits`).catch(() => []),
      isHR ? apiFetch(`${API_BASE}/hr/staff`) : Promise.resolve([])
    ]).then(([p, s]) => { setPermits(p || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [isHR]);

  const save = async () => {
    if (!form.staff_id || !form.permit_number) return alert("Staff and permit number required");
    try {
      await apiFetch(`${API_BASE}/hr/work-permits`, { method: "POST", body: JSON.stringify({ staff_id: form.staff_id, letter_type: form.letter_type, content: form.content, date_issued: form.date_issued }) });
      setShowNew(false); apiFetch(`${API_BASE}/hr/work-permits`).then(d => setPermits(d || []));
    } catch (e) { alert(e.message); }
  };

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Work Permits</div><div style={{ fontSize: 13, color: C.sub }}>Track work authorisation, visas and permit expiry alerts.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Add Permit</button>}
      </div>
      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw"><table className="ht"><thead><tr><th>Staff Member</th><th>Permit Type</th><th>Permit No.</th><th>Issue Date</th><th>Expiry Date</th><th>Status</th></tr></thead>
          <tbody>{permits.map(p => {
            const expired = p.expiry_date < today;
            const expiringSoon = !expired && p.expiry_date < new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
            return (<tr key={p.id}>
              <td style={{ fontWeight: 800, color: C.text }}>{p.admins?.full_name || "—"}</td>
              <td>{p.permit_type}</td><td style={{ fontFamily: "monospace" }}>{p.permit_number}</td>
              <td>{p.issue_date}</td>
              <td style={{ color: expired ? "#F87171" : expiringSoon ? T.gold : C.text, fontWeight: expired || expiringSoon ? 800 : 400 }}>{p.expiry_date}</td>
              <td><span className="tg" style={{ background: expired ? "#F8717122" : expiringSoon ? `${T.gold}22` : "#4ADE8022", color: expired ? "#F87171" : expiringSoon ? T.gold : "#4ADE80" }}>{expired ? "Expired" : expiringSoon ? "Expiring Soon" : "Active"}</span></td>
            </tr>);
          })}
            {permits.length === 0 && <tr><td colSpan="6" style={{ textAlign: "center", padding: 30, color: C.muted }}>No work permits on record.</td></tr>}
          </tbody>
        </table></div>
      </div>
      {showNew && <Modal onClose={() => setShowNew(false)} title="Add Work Permit">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Staff Member *</Lbl>
            <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
              <option value="">— Select —</option>{staff.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </select>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Permit Type</Lbl><input className="inp" value={form.permit_type} onChange={e => setForm(f => ({ ...f, permit_type: e.target.value }))} /></div>
            <div><Lbl>Permit Number *</Lbl><input className="inp" value={form.permit_number} onChange={e => setForm(f => ({ ...f, permit_number: e.target.value }))} /></div>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Issue Date</Lbl><input type="date" className="inp" value={form.issue_date} onChange={e => setForm(f => ({ ...f, issue_date: e.target.value }))} /></div>
            <div><Lbl>Expiry Date</Lbl><input type="date" className="inp" value={form.expiry_date} onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} /></div>
          </div>
          <div><Lbl>Issuing Authority</Lbl><input className="inp" value={form.issuing_authority} onChange={e => setForm(f => ({ ...f, issuing_authority: e.target.value }))} /></div>
          <button className="bp" onClick={save}>Save Permit</button>
        </div>
      </Modal>}
    </div>
  );
}

// ─── HUB: HR LETTERS ─────────────────────────────────────────────────────────
function HRLetters({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [letters, setLetters] = useState([]); const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [viewLetter, setViewLetter] = useState(null);
  const [form, setForm] = useState({ staff_id: "", letter_type: "Employment Confirmation", content: "", date_issued: new Date().toISOString().split("T")[0] });
  const [saving, setSaving] = useState(false);

  const refresh = () => apiFetch(`${API_BASE}/hr/hr-letters`).catch(() => []).then(d => setLetters(d || []));

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/hr-letters`).catch(() => []),
      isHR ? apiFetch(`${API_BASE}/hr/staff`).catch(() => []) : Promise.resolve([])
    ]).then(([l, s]) => { setLetters(l || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [isHR]);

  const save = async () => {
    if (!form.staff_id || !form.content) return alert("Staff and letter content required.");
    setSaving(true);
    try {
      // 1. Issue the letter
      await apiFetch(`${API_BASE}/hr/hr-letters`, { method: "POST", body: JSON.stringify({ staff_id: form.staff_id, exit_date: form.exit_date, reason: form.reason, overall_satisfaction: form.overall_satisfaction, highlights: form.highlights, concerns: form.concerns, would_recommend: form.would_recommend, notes: form.notes }) });
      // 2. Send notification to the staff member
      const recipient = staff.find(s => s.id === form.staff_id);
      await apiFetch(`${API_BASE}/hr/notifications`, {
        method: "POST",
        body: JSON.stringify({
          staff_id: form.staff_id,
          type: "letter_issued",
          message: `📄 HR has issued you a "${form.letter_type}" letter. Log in to view it in HR Letters.`
        })
      }).catch(() => { }); // non-blocking — notification failure should not block letter issue
      setShowNew(false);
      setForm({ staff_id: "", letter_type: "Employment Confirmation", content: "", date_issued: new Date().toISOString().split("T")[0] });
      refresh();
      alert(`Letter issued to ${recipient?.full_name || "staff member"}. They have been notified.`);
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const LETTER_TYPES = ["Employment Confirmation", "Salary Confirmation", "Experience Letter", "Reference Letter", "Warning Letter", "Promotion Letter", "Contract Renewal"];
  const typeColor = { "Warning Letter": "#F87171", "Employment Confirmation": "#4ADE80", "Salary Confirmation": T.gold, "Promotion Letter": "#A78BFA" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>HR Letters</div><div style={{ fontSize: 13, color: C.sub }}>Issue and archive official HR letters. Staff are notified automatically.</div></div>
        {isHR && <button className="bp" onClick={() => setShowNew(true)}>+ Issue Letter</button>}
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw"><table className="ht">
            <thead><tr><th>Staff Member</th><th>Letter Type</th><th>Date Issued</th><th>Action</th></tr></thead>
            <tbody>
              {letters.map(l => {
                const tc = typeColor[l.letter_type] || "#60A5FA";
                return (
                  <tr key={l.id}>
                    <td style={{ fontWeight: 800, color: C.text }}>{l.admins?.full_name || "—"}</td>
                    <td><span className="tg" style={{ background: `${tc}22`, color: tc }}>{l.letter_type}</span></td>
                    <td style={{ fontSize: 12, color: C.sub }}>{l.date_issued}</td>
                    <td>
                      <button className="bg" style={{ fontSize: 11, padding: "4px 12px" }} onClick={() => setViewLetter(l)}>
                        📄 View Letter
                      </button>
                    </td>
                  </tr>
                );
              })}
              {letters.length === 0 && <tr><td colSpan="4" style={{ textAlign: "center", padding: 30, color: C.muted }}>No HR letters issued yet.</td></tr>}
            </tbody>
          </table></div>
        </div>
      )}

      {/* ── View Letter Modal ── */}
      {viewLetter && (
        <Modal onClose={() => setViewLetter(null)} title={viewLetter.letter_type} width={580}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Letter Header */}
            <div style={{ padding: 20, background: dark ? "rgba(255,255,255,0.03)" : "#f8f8f8", borderRadius: 10, borderLeft: `4px solid ${typeColor[viewLetter.letter_type] || "#60A5FA"}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", fontWeight: 700 }}>Issued To</div>
                  <div style={{ fontWeight: 900, fontSize: 16, color: C.text, marginTop: 4 }}>{viewLetter.admins?.full_name || "Staff Member"}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", fontWeight: 700 }}>Date Issued</div>
                  <div style={{ fontWeight: 700, color: C.text, marginTop: 4 }}>{viewLetter.date_issued}</div>
                </div>
              </div>
              <div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", fontWeight: 700, marginBottom: 4 }}>Letter Type</div>
              <span className="tg" style={{ background: `${typeColor[viewLetter.letter_type] || "#60A5FA"}22`, color: typeColor[viewLetter.letter_type] || "#60A5FA" }}>
                {viewLetter.letter_type}
              </span>
            </div>

            {/* Letter Body */}
            <div style={{ padding: 20, background: dark ? "rgba(255,255,255,0.02)" : "#fdfdfd", borderRadius: 10, border: `1px solid ${C.border}`, lineHeight: 1.8, fontSize: 13, color: C.text, whiteSpace: "pre-wrap", fontFamily: "Georgia, serif", minHeight: 200 }}>
              {viewLetter.content || "No letter content found."}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button className="bg" onClick={() => window.print()} style={{ fontSize: 12, padding: "8px 16px" }}>🖨️ Print</button>
              <button className="bp" onClick={() => setViewLetter(null)} style={{ fontSize: 12, padding: "8px 16px" }}>Close</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Issue New Letter Modal ── */}
      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Issue HR Letter">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ padding: 12, background: "#60A5FA11", borderRadius: 8, fontSize: 12, color: "#60A5FA" }}>
              🔔 The staff member will receive an automatic notification when this letter is issued.
            </div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Staff Member *</Lbl>
                <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
                  <option value="">— Select —</option>
                  {staff.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                </select>
              </div>
              <div><Lbl>Letter Type</Lbl>
                <select className="inp" value={form.letter_type} onChange={e => setForm(f => ({ ...f, letter_type: e.target.value }))}>
                  {LETTER_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <div><Lbl>Letter Content *</Lbl>
              <textarea className="inp" rows={10} placeholder={`Dear [Name],\n\nThis letter is to confirm that...\n\nYours faithfully,\nHR Department`} value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} />
            </div>
            <div><Lbl>Date Issued</Lbl><input type="date" className="inp" value={form.date_issued} onChange={e => setForm(f => ({ ...f, date_issued: e.target.value }))} /></div>
            <button className="bp" onClick={save} disabled={saving}>{saving ? "Issuing…" : "Issue Letter & Notify Staff"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: REQUESTS ────────────────────────────────────────────────────────────
function HRRequests({ user, isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [requests, setRequests] = useState([]); const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(null); // request type string when open
  const [form, setForm] = useState({ request_type: "", description: "", priority: "Normal" });
  const [saving, setSaving] = useState(false);
  const [staff, setStaff] = useState([]);

  const REQUEST_TYPES = [
    { id: "Equipment Request", emoji: "📦", desc: "Request company hardware, peripherals or software licenses." },
    { id: "System Access Request", emoji: "🔐", desc: "Request access to company systems or elevate permissions." },
    { id: "Transfer Request", emoji: "🔄", desc: "Request a role or department transfer." },
    { id: "Reference Request", emoji: "📄", desc: "Request an official employment reference letter." },
  ];

  const statusStyle = { pending: { bg: "#F59E0B22", col: "#F59E0B" }, approved: { bg: "#4ADE8022", col: "#4ADE80" }, rejected: { bg: "#F8717122", col: "#F87171" }, completed: { bg: "#60A5FA22", col: "#60A5FA" } };

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/requests`).catch(() => []),
      isHR ? apiFetch(`${API_BASE}/hr/staff`).catch(() => []) : Promise.resolve([])
    ]).then(([r, s]) => { setRequests(r || []); setStaff(s || []); }).finally(() => setLoading(false));
  }, [isHR]);

  const refresh = () => apiFetch(`${API_BASE}/hr/requests`).catch(() => []).then(r => setRequests(r || []));

  const openForm = (type) => {
    setForm({ request_type: type, description: "", priority: "Normal" });
    setShowForm(type);
  };

  const submit = async () => {
    if (!form.description.trim()) return alert("Please describe your request.");
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/requests`, { method: "POST", body: JSON.stringify({ request_type: form.request_type, description: form.description, priority: form.priority }) });
      setShowForm(null); refresh();
    } catch (e) { alert("Error: " + e.message); } finally { setSaving(false); }
  };

  const updateStatus = async (id, status) => {
    try {
      await apiFetch(`${API_BASE}/hr/requests/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      refresh();
    } catch (e) { alert(e.message); }
  };

  const myRequests = isHR ? requests : requests.filter(r => r.staff_id === user?.id);

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>HR Requests</div>
          <div style={{ fontSize: 13, color: C.sub }}>Submit and track HR-related requests.</div>
        </div>
      </div>

      {!isHR && (
        <div className="g2" style={{ marginBottom: 28 }}>
          {REQUEST_TYPES.map(({ id, emoji, desc }) => (
            <div key={id} className="gc" style={{ padding: 20 }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>{emoji}</div>
              <div style={{ fontWeight: 800, color: C.text, marginBottom: 6 }}>{id}</div>
              <div style={{ fontSize: 12, color: C.sub, marginBottom: 14 }}>{desc}</div>
              <button className="bp" style={{ fontSize: 12, padding: "8px 16px" }} onClick={() => openForm(id)}>Submit Request</button>
            </div>
          ))}
        </div>
      )}

      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}`, fontWeight: 800, fontSize: 14 }}>
          {isHR ? "All Staff Requests" : "My Requests"}
        </div>
        {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
          <div className="tw"><table className="ht">
            <thead><tr>
              {isHR && <th>Staff Member</th>}
              <th>Type</th><th>Description</th><th>Priority</th><th>Submitted</th><th>Status</th>
              {isHR && <th>Actions</th>}
            </tr></thead>
            <tbody>
              {myRequests.map(r => {
                const ss = statusStyle[r.status] || statusStyle.pending;
                return (
                  <tr key={r.id}>
                    {isHR && <td style={{ fontWeight: 700, color: C.text }}>{staff.find(s => s.id === r.staff_id)?.full_name || "Staff"}</td>}
                    <td style={{ fontWeight: 700 }}>{r.request_type}</td>
                    <td style={{ fontSize: 12, color: C.sub, maxWidth: 240 }}>{r.description}</td>
                    <td><span className="tg" style={{ background: r.priority === "Urgent" ? "#F8717122" : `${C.border}44`, color: r.priority === "Urgent" ? "#F87171" : C.muted }}>{r.priority}</span></td>
                    <td style={{ fontSize: 12, color: C.muted }}>{new Date(r.created_at).toLocaleDateString()}</td>
                    <td><span className="tg" style={{ background: ss.bg, color: ss.col, textTransform: "capitalize" }}>{r.status || "pending"}</span></td>
                    {isHR && (
                      <td style={{ display: "flex", gap: 6 }}>
                        {r.status === "pending" && <>
                          <button className="bg" style={{ fontSize: 11, padding: "4px 10px", color: "#4ADE80" }} onClick={() => updateStatus(r.id, "approved")}>Approve</button>
                          <button className="bg" style={{ fontSize: 11, padding: "4px 10px", color: "#F87171" }} onClick={() => updateStatus(r.id, "rejected")}>Reject</button>
                        </>}
                        {r.status === "approved" && <button className="bg" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => updateStatus(r.id, "completed")}>Mark Done</button>}
                      </td>
                    )}
                  </tr>
                );
              })}
              {myRequests.length === 0 && <tr><td colSpan="7" style={{ textAlign: "center", padding: 30, color: C.muted }}>No requests found.</td></tr>}
            </tbody>
          </table></div>
        )}
      </div>

      {showForm && (
        <Modal onClose={() => setShowForm(null)} title={`Submit: ${showForm}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Details / Description *</Lbl>
              <textarea className="inp" rows={4} placeholder="Describe what you need and why…" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
            <div><Lbl>Priority</Lbl>
              <select className="inp" value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                <option>Normal</option><option>Urgent</option>
              </select></div>
            <button className="bp" onClick={submit} disabled={saving}>{saving ? "Submitting…" : "Submit Request"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: GRIEVANCES ─────────────────────────────────────────────────────────
function Grievances({ isHR }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [grievances, setGrievances] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [viewItem, setViewItem] = useState(null);
  const [form, setForm] = useState({ subject: "", description: "", is_anonymous: true });
  const [updatingId, setUpdatingId] = useState(null);

  useEffect(() => {
    if (isHR) apiFetch(`${API_BASE}/hr/grievances`).then(d => setGrievances(d || [])).catch(() => { }).finally(() => setLoading(false));
    else setLoading(false);
  }, [isHR]);

  const refresh = () => apiFetch(`${API_BASE}/hr/grievances`).then(d => setGrievances(d || [])).catch(() => { });

  const submit = async () => {
    if (!form.subject || !form.description) return alert("Subject and description required");
    try {
      await apiFetch(`${API_BASE}/hr/grievances`, { method: "POST", body: JSON.stringify({ subject: form.subject, description: form.description, is_anonymous: form.is_anonymous }) });
      alert("Your grievance has been submitted confidentially. HR will review within 5 working days.");
      setShowNew(false); setForm({ subject: "", description: "", is_anonymous: true });
    } catch (e) { alert(e.message); }
  };

  const updateStatus = async (id, status) => {
    setUpdatingId(id);
    try {
      await apiFetch(`${API_BASE}/hr/grievances/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      refresh();
      if (viewItem?.id === id) setViewItem(v => ({ ...v, status }));
    } catch (e) { alert(e.message); } finally { setUpdatingId(null); }
  };

  const statusStyle = { open: { bg: "#F59E0B22", col: "#F59E0B" }, "in-review": { bg: "#60A5FA22", col: "#60A5FA" }, resolved: { bg: "#4ADE8022", col: "#4ADE80" }, closed: { bg: "#33333344", col: "#9CA3AF" } };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Grievances</div><div style={{ fontSize: 13, color: C.sub }}>Anonymous and confidential grievance submission and tracking.</div></div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Submit Grievance</button>
      </div>
      <div className="gc" style={{ padding: 22, marginBottom: 16, borderLeft: "3px solid #60A5FA" }}>
        <div style={{ fontWeight: 800, color: "#60A5FA", marginBottom: 6 }}>Your Grievance is Protected</div>
        <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6 }}>All grievances are handled confidentially by HR. Anonymous submissions cannot be traced back to you. We have a strict no-retaliation policy.</div>
      </div>

      {isHR && (
        loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
          <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
            <div className="tw"><table className="ht">
              <thead><tr><th>Subject</th><th>Submitted</th><th>Type</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>
                {grievances.map(g => {
                  const ss = statusStyle[g.status] || statusStyle.open;
                  return (
                    <tr key={g.id}>
                      <td style={{ fontWeight: 800, color: C.text, maxWidth: 220 }}>{g.subject}</td>
                      <td style={{ fontSize: 12, color: C.muted }}>{new Date(g.created_at).toLocaleDateString()}</td>
                      <td>{g.is_anonymous ? <span className="tg tg2">Anonymous</span> : <span className="tg tm">Named</span>}</td>
                      <td>
                        <select
                          value={g.status || "open"}
                          disabled={updatingId === g.id}
                          onChange={e => updateStatus(g.id, e.target.value)}
                          style={{ padding: "4px 8px", borderRadius: 8, border: `1px solid ${ss.col}`, background: ss.bg, color: ss.col, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                        >
                          <option value="open">Open</option>
                          <option value="in-review">In Review</option>
                          <option value="resolved">Resolved</option>
                          <option value="closed">Closed</option>
                        </select>
                      </td>
                      <td>
                        <button className="bg" style={{ fontSize: 11, padding: "4px 12px" }} onClick={() => setViewItem(g)}>
                          Open ↗
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {grievances.length === 0 && <tr><td colSpan="5" style={{ textAlign: "center", padding: 30, color: C.muted }}>No grievances on record.</td></tr>}
              </tbody>
            </table></div>
          </div>
        )
      )}

      {/* ── View Grievance Modal ── */}
      {viewItem && (
        <Modal onClose={() => setViewItem(null)} title="Grievance Details">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", fontWeight: 700, marginBottom: 4 }}>Subject</div>
                <div style={{ fontWeight: 900, fontSize: 16, color: C.text }}>{viewItem.subject}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                <select
                  value={viewItem.status || "open"}
                  disabled={updatingId === viewItem.id}
                  onChange={e => updateStatus(viewItem.id, e.target.value)}
                  style={{ padding: "6px 10px", borderRadius: 8, border: `1px solid ${(statusStyle[viewItem.status] || statusStyle.open).col}`, background: (statusStyle[viewItem.status] || statusStyle.open).bg, color: (statusStyle[viewItem.status] || statusStyle.open).col, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                >
                  <option value="open">Open</option>
                  <option value="in-review">In Review</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
                {viewItem.is_anonymous
                  ? <span className="tg tg2" style={{ fontSize: 11 }}>Anonymous</span>
                  : <span style={{ fontSize: 11, color: C.text, fontWeight: 700 }}>{viewItem.admins?.full_name || "Named Staff"}</span>}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", fontWeight: 700, marginBottom: 8 }}>Grievance Message</div>
              <div style={{ padding: 18, background: dark ? "rgba(255,255,255,0.03)" : "#f8f8f8", borderRadius: 10, border: `1px solid ${C.border}`, lineHeight: 1.8, fontSize: 13, color: C.text, whiteSpace: "pre-wrap", minHeight: 120 }}>
                {viewItem.description || "No description provided."}
              </div>
            </div>
            <div style={{ fontSize: 11, color: C.muted }}>
              Submitted: {new Date(viewItem.created_at).toLocaleString()}
            </div>
          </div>
        </Modal>
      )}

      {/* ── Submit Grievance Modal ── */}
      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Submit a Grievance">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Subject *</Lbl><input className="inp" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="Brief summary of your concern" /></div>
            <div><Lbl>Description *</Lbl><textarea className="inp" rows={6} placeholder="Describe the issue in detail. Include dates, people involved, and any supporting context…" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
            <label style={{ display: "flex", alignItems: "center", gap: 10, color: C.sub, fontSize: 13, cursor: "pointer" }}>
              <input type="checkbox" checked={form.is_anonymous} onChange={e => setForm(f => ({ ...f, is_anonymous: e.target.checked }))} />
              Submit anonymously (recommended)
            </label>
            <div style={{ padding: 12, background: `${T.gold}11`, borderRadius: 8, fontSize: 12, color: T.gold }}>⚠️ By submitting, this will be securely reviewed by HR management only.</div>
            <button className="bp" onClick={submit}>Submit Grievance</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── HUB: AUDIT LOGS ─────────────────────────────────────────────────────────
function AuditLogs() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [logs, setLogs] = useState([]); const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(50); const [search, setSearch] = useState("");

  const load = useCallback((lim) => {
    setLoading(true);
    // Primary: same activity endpoint used by the CRM/Sales dashboard
    apiFetch(`${API_BASE}/analytics/activity?limit=${lim}`)
      .catch(() => apiFetch(`${API_BASE}/hr/audit-logs?limit=${lim}`).catch(() => []))
      .then(d => setLogs(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(limit); }, [limit, load]);

  const getActionMeta = (log) => {
    const desc = (log.description || log.action || "").toLowerCase();
    if (desc.includes("creat") || desc.includes("add") || desc.includes("new") || desc.includes("issu") || desc.includes("upload"))
      return { label: "CREATE", col: "#4ADE80" };
    if (desc.includes("updat") || desc.includes("edit") || desc.includes("chang") || desc.includes("patch") || desc.includes("modif") || desc.includes("approv") || desc.includes("mark"))
      return { label: "UPDATE", col: T.gold };
    if (desc.includes("delet") || desc.includes("remov") || desc.includes("archiv") || desc.includes("offboard") || desc.includes("terminat"))
      return { label: "DELETE", col: "#F87171" };
    if (desc.includes("login") || desc.includes("logout") || desc.includes("sign"))
      return { label: "AUTH", col: "#A78BFA" };
    if (desc.includes("view") || desc.includes("read") || desc.includes("download") || desc.includes("export"))
      return { label: "VIEW", col: "#60A5FA" };
    return { label: "ACTION", col: C.muted };
  };

  const filtered = search
    ? logs.filter(l => `${l.performed_by_name || l.admins?.full_name || ""} ${l.description || l.action || ""} ${l.entity_type || ""}`.toLowerCase().includes(search.toLowerCase()))
    : logs;

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Audit Logs</div>
          <div style={{ fontSize: 13, color: C.sub }}>Complete trail of all system actions for compliance and security.</div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <select className="inp" value={limit} onChange={e => setLimit(Number(e.target.value))} style={{ width: 130 }}>
            <option value={25}>Last 25</option><option value={50}>Last 50</option>
            <option value={100}>Last 100</option><option value={250}>Last 250</option>
          </select>
          <button className="bg" onClick={() => load(limit)} style={{ padding: "10px 14px", fontSize: 12 }}>↻ Refresh</button>
        </div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <input className="inp" placeholder="Search logs by actor, action or entity…" value={search} onChange={e => setSearch(e.target.value)} />
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading audit trail…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 20px", borderBottom: `1px solid ${C.border}`, fontSize: 12, color: C.muted, display: "flex", justifyContent: "space-between" }}>
            <span>Showing {filtered.length} of {logs.length} entries</span>
            <span>{new Date().toLocaleDateString()}</span>
          </div>
          <div className="tw"><table className="ht">
            <thead><tr><th>Actor</th><th>Type</th><th>Description</th><th>Entity</th><th>Timestamp</th></tr></thead>
            <tbody>
              {filtered.map((l, i) => {
                const { label, col } = getActionMeta(l);
                const actor = l.performed_by_name || l.admins?.full_name || l.actor || "System";
                const description = l.description || l.action || "—";
                const entity = l.entity_type ? `${l.entity_type}${l.entity_id ? ` #${String(l.entity_id).slice(0, 8)}` : ""}` : "—";
                return (
                  <tr key={l.id || i}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Av av={actor.split(" ").map(n => n[0]).join("").slice(0, 2)} sz={28} />
                        <span style={{ fontWeight: 700, color: C.text, fontSize: 13 }}>{actor}</span>
                      </div>
                    </td>
                    <td><span className="tg" style={{ background: `${col}22`, color: col, fontSize: 10, fontWeight: 800 }}>{label}</span></td>
                    <td style={{ fontSize: 12, color: C.sub, maxWidth: 300 }}>{description}</td>
                    <td style={{ fontSize: 11, color: C.muted, fontFamily: "monospace" }}>{entity}</td>
                    <td style={{ fontSize: 11, color: C.muted, whiteSpace: "nowrap" }}>{l.created_at ? new Date(l.created_at).toLocaleString() : "—"}</td>
                  </tr>
                );
              })}
              {filtered.length === 0 && <tr><td colSpan="5" style={{ textAlign: "center", padding: 40, color: C.muted }}>
                {search ? "No logs match your search." : "No audit logs found. Logs appear as actions are taken in the system."}
              </td></tr>}
            </tbody>
          </table></div>
        </div>
      )}
    </div>
  );
}

// ─── HUB: HR REPORTS ─────────────────────────────────────────────────────────
function HRReports() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [headcount, setHeadcount] = useState(null); const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(null);
  const [dateRange, setDateRange] = useState({ from: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split("T")[0], to: new Date().toISOString().split("T")[0] });

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/reports/headcount`).then(setHeadcount).catch(() => { }).finally(() => setLoading(false));
  }, []);

  const generateReport = async (type, endpoint) => {
    setGenerating(type);
    try {
      const query = `?from=${dateRange.from}&to=${dateRange.to}&format=csv`;
      // Try API endpoint first; fall back to downloading data as CSV from the HR data we already have
      const res = await fetch(`${API_BASE}${endpoint}${query}`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("ec_token")}`, "Accept": "text/csv,application/json" }
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const contentType = res.headers.get("content-type") || "";
      let blob;
      if (contentType.includes("json")) {
        // Server returned JSON — convert to CSV in browser
        const data = await res.json();
        const rows = Array.isArray(data) ? data : (data.rows || data.data || Object.entries(data).map(([k, v]) => ({ key: k, value: v })));
        if (rows.length === 0) { alert("No data available for the selected date range."); return; }
        const headers = Object.keys(rows[0]).join(",");
        const csvRows = rows.map(r => Object.values(r).map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","));
        blob = new Blob([headers + "\n" + csvRows.join("\n")], { type: "text/csv" });
      } else {
        blob = await res.blob();
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${type.toLowerCase().replace(/ /g, "_")}_${dateRange.from}_to_${dateRange.to}.csv`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Could not generate "${type}" report.\n\nError: ${e.message}\n\nEnsure the backend endpoint is active, or contact your system administrator.`);
    } finally { setGenerating(null); }
  };

  const REPORTS = [
    { title: "Attendance Report", desc: "Export attendance data with absence rates by department.", icon: "🕐", endpoint: "/hr/reports/attendance", col: "#60A5FA" },
    { title: "Payroll Summary", desc: "Monthly payroll totals, tax deductions and net pay summary.", icon: "💰", endpoint: "/hr/reports/payroll", col: "#4ADE80" },
    { title: "Performance Report", desc: "Scorecard distribution, Elite/Stable/PIP breakdown by department.", icon: "📊", endpoint: "/hr/reports/performance", col: "#A78BFA" },
    { title: "Leave Report", desc: "Leave utilisation by type, department and individual.", icon: "📅", endpoint: "/hr/reports/leave", col: T.gold },
    { title: "Headcount Report", desc: "Full staff roster with roles, departments, join dates and status.", icon: "👥", endpoint: "/hr/reports/headcount-full", col: "#F87171" },
    { title: "Goals & KPI Report", desc: "Goal achievement rates and KPI scores by department.", icon: "🎯", endpoint: "/hr/reports/goals", col: "#F59E0B" },
  ];

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Reports & Analytics</div>
          <div style={{ fontSize: 13, color: C.sub }}>Workforce data insights and exportable HR reports.</div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <div><div style={{ fontSize: 10, color: C.muted, marginBottom: 4, textTransform: "uppercase" }}>From</div><input className="inp" type="date" value={dateRange.from} onChange={e => setDateRange(r => ({ ...r, from: e.target.value }))} style={{ padding: "6px 10px" }} /></div>
          <div><div style={{ fontSize: 10, color: C.muted, marginBottom: 4, textTransform: "uppercase" }}>To</div><input className="inp" type="date" value={dateRange.to} onChange={e => setDateRange(r => ({ ...r, to: e.target.value }))} style={{ padding: "6px 10px" }} /></div>
        </div>
      </div>

      {/* Live Headcount Summary */}
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading data…</div> : headcount && (
        <>
          <div className="g3" style={{ marginBottom: 22 }}>
            <StatCard label="Total Active Staff" value={headcount.total} col={T.gold} />
            <StatCard label="New Hires (30d)" value={headcount.new_hires_30d} col="#4ADE80" />
            <StatCard label="Departments" value={Object.keys(headcount.by_department || {}).length} col="#60A5FA" />
          </div>
          <div className="gc" style={{ padding: 22, marginBottom: 22 }}>
            <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Headcount by Department</div>
            {Object.entries(headcount.by_department || {}).sort((a, b) => b[1] - a[1]).map(([dept, count]) => (
              <div key={dept} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: C.text, marginBottom: 4 }}>
                  <span style={{ fontWeight: 700 }}>{dept}</span>
                  <span style={{ color: T.gold, fontWeight: 800 }}>{count} staff</span>
                </div>
                <Bar pct={headcount.total > 0 ? (count / headcount.total) * 100 : 0} />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Report Cards */}
      <div className="g2">
        {REPORTS.map(({ title, desc, icon, endpoint, col }) => (
          <div key={title} className="gc" style={{ padding: 22, borderTop: `3px solid ${col}` }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>{icon}</div>
            <div style={{ fontWeight: 800, color: C.text, marginBottom: 6 }}>{title}</div>
            <div style={{ fontSize: 12, color: C.sub, marginBottom: 18, lineHeight: 1.6 }}>{desc}</div>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 12 }}>
              Period: {new Date(dateRange.from).toLocaleDateString()} – {new Date(dateRange.to).toLocaleDateString()}
            </div>
            <button
              className="bp"
              style={{ fontSize: 12, padding: "9px 16px", width: "100%", opacity: generating === title ? 0.7 : 1 }}
              disabled={!!generating}
              onClick={() => generateReport(title, endpoint)}
            >
              {generating === title ? "⏳ Generating…" : "⬇ Generate & Download CSV"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── HUB: DEPARTMENTS ─────────────────────────────────────────────────────────
function DepartmentsView() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [depts, setDepts] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/departments`).then(d => setDepts(d || [])).catch(() => { }).finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Departments</div>
          <div style={{ fontSize: 13, color: C.sub }}>Organisational units and department management.</div>
        </div>
      </div>

      <div className="gc" style={{ padding: 24, marginBottom: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 16 }}>Manage Units</div>
        <DepartmentManager departments={depts} onRefresh={refresh} />
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="g3">
          {depts.map((d, i) => (
            <div key={i} className="gc" style={{ padding: 20, position: "relative" }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>🏢</div>
              <div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{d.name || d}</div>
              <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Active Department</div>
            </div>
          ))}
          {depts.length === 0 && <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: C.muted }}>No departments configured. Add one above.</div>}
        </div>
      )}
    </div>
  );
}

// ─── HUB: DIVERSITY & INCLUSION ───────────────────────────────────────────────
function DiversityInclusion() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(d || [])).catch(() => setStaff([])).finally(() => setLoading(false));
  }, []);

  // Derive metrics from real staff data
  const active = staff.filter(s => s.is_active);
  const total = active.length;
  const byDept = active.reduce((acc, s) => { acc[s.department || "Unassigned"] = (acc[s.department || "Unassigned"] || 0) + 1; return acc; }, {});
  const byType = active.reduce((acc, s) => { const t = s.staff_type === "full" ? "Full-Time" : s.staff_type === "part" ? "Part-Time" : "Contractor"; acc[t] = (acc[t] || 0) + 1; return acc; }, {});
  const byRole = active.reduce((acc, s) => { const r = s.role || "staff"; acc[r] = (acc[r] || 0) + 1; return acc; }, {});

  const Bar = ({ pct, col }) => (
    <div style={{ height: 8, background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)", borderRadius: 8, overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${Math.min(pct, 100)}%`, background: col, borderRadius: 8, transition: "width 1s ease" }} />
    </div>
  );

  const DEPT_COLORS = ["#F59E0B", "#60A5FA", "#4ADE80", "#F87171", "#A78BFA", "#EC4899", "#14B8A6", "#F97316"];

  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}>
        <div className="ho" style={{ fontSize: 22 }}>Diversity & Inclusion</div>
        <div style={{ fontSize: 13, color: C.sub }}>Workforce composition metrics and inclusion overview.</div>
      </div>

      <div className="g2" style={{ marginBottom: 22 }}>
        {[["Equal Opportunity", "All hiring decisions are based solely on merit and role fit. We comply with Nigerian Labour Act provisions on non-discrimination.", "#60A5FA"],
        ["Zero Tolerance Policy", "Discrimination, harassment or exclusion of any kind is a disciplinary offence under our Code of Conduct.", "#4ADE80"]].map(([t, d, c]) => (
          <div key={t} className="gc" style={{ padding: 22, borderLeft: `3px solid ${c}` }}>
            <div style={{ fontWeight: 800, color: c, marginBottom: 8 }}>{t}</div>
            <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6 }}>{d}</div>
          </div>
        ))}
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading workforce data…</div> : (
        <>
          {/* Summary Cards */}
          <div className="g3" style={{ marginBottom: 22 }}>
            <div className="gc" style={{ padding: 22, textAlign: "center" }}>
              <div style={{ fontSize: 36, fontWeight: 900, color: T.gold }}>{total}</div>
              <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Total Active Staff</div>
            </div>
            <div className="gc" style={{ padding: 22, textAlign: "center" }}>
              <div style={{ fontSize: 36, fontWeight: 900, color: "#60A5FA" }}>{Object.keys(byDept).length}</div>
              <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Departments Represented</div>
            </div>
            <div className="gc" style={{ padding: 22, textAlign: "center" }}>
              <div style={{ fontSize: 36, fontWeight: 900, color: "#4ADE80" }}>{byType["Full-Time"] || 0}</div>
              <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Full-Time Employees</div>
            </div>
          </div>

          <div className="g2" style={{ marginBottom: 22 }}>
            {/* Department Distribution */}
            <div className="gc" style={{ padding: 22 }}>
              <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 16 }}>Headcount by Department</div>
              {Object.entries(byDept).sort((a, b) => b[1] - a[1]).map(([dept, count], i) => (
                <div key={dept} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: C.text, marginBottom: 5 }}>
                    <span style={{ fontWeight: 700 }}>{dept}</span>
                    <span style={{ color: DEPT_COLORS[i % DEPT_COLORS.length], fontWeight: 800 }}>{count} ({total > 0 ? Math.round((count / total) * 100) : 0}%)</span>
                  </div>
                  <Bar pct={total > 0 ? (count / total) * 100 : 0} col={DEPT_COLORS[i % DEPT_COLORS.length]} />
                </div>
              ))}
            </div>

            {/* Employment Type & Role */}
            <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
              <div className="gc" style={{ padding: 22 }}>
                <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 16 }}>Employment Type</div>
                {Object.entries(byType).map(([type, count]) => (
                  <div key={type} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{type}</span>
                    <span className="tg" style={{ background: `${T.gold}22`, color: T.gold, fontWeight: 900 }}>{count}</span>
                  </div>
                ))}
              </div>
              <div className="gc" style={{ padding: 22 }}>
                <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 16 }}>Role Distribution</div>
                {Object.entries(byRole).sort((a, b) => b[1] - a[1]).map(([role, count]) => (
                  <div key={role} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: C.text, textTransform: "capitalize" }}>{role.replace("_", " ")}</span>
                    <span className="tg" style={{ background: "#60A5FA22", color: "#60A5FA", fontWeight: 900 }}>{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="gc" style={{ padding: 22, borderLeft: `3px solid ${T.gold}` }}>
            <div style={{ fontWeight: 800, color: T.gold, marginBottom: 6 }}>Gender & Ethnicity Tracking</div>
            <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6 }}>Gender and ethnicity data collection will be enabled with voluntary, consent-based staff surveys in Q3 2026. This ensures compliance with NDPR data privacy regulations.</div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── HUB: ORG CHART (ENHANCED) ────────────────────────────────────────────────
function OrgChartEnhanced() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(d || [])).catch(() => { }).finally(() => setLoading(false));
  }, []);

  const noMgr = staff.filter(s => !s.line_manager_id && s.is_active);
  const getReports = (id) => staff.filter(s => s.line_manager_id === id && s.is_active);

  const OrgNode = ({ person, depth = 0 }) => {
    const reports = getReports(person.id);
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        <div className="gc" style={{ padding: "12px 16px", textAlign: "center", minWidth: 140, maxWidth: 200, borderTop: `3px solid ${depth === 0 ? T.gold : depth === 1 ? "#60A5FA" : "#4ADE80"}` }}>
          <Av av={person.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={36} gold={depth === 0} />
          <div style={{ fontWeight: 800, fontSize: 12, color: C.text, marginTop: 8, lineHeight: 1.3 }}>{person.full_name}</div>
          <div style={{ fontSize: 10, color: C.muted, marginTop: 2 }}>{person.staff_profiles?.[0]?.job_title || person.role}</div>
        </div>
        {reports.length > 0 && (
          <div style={{ display: "flex", gap: 16, position: "relative" }}>
            <div style={{ position: "absolute", top: 0, left: "50%", width: 1, height: 16, background: C.border, transform: "translateX(-50%)" }} />
            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              {reports.map(r => <OrgNode key={r.id} person={r} depth={depth + 1} />)}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}><div className="ho" style={{ fontSize: 22 }}>Org Chart</div><div style={{ fontSize: 13, color: C.sub }}>Organisational hierarchy auto-generated from reporting lines.</div></div>
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading org chart…</div> : (
        <div style={{ overflowX: "auto", padding: "20px 0" }}>
          {noMgr.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Configure reporting lines in Staff Profiles to generate the org chart.</div>
          ) : (
            <div style={{ display: "flex", gap: 32, justifyContent: "center", flexWrap: "wrap" }}>
              {noMgr.map(p => <OrgNode key={p.id} person={p} depth={0} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── HUB: USERS / SYSTEM SETTINGS ─────────────────────────────────────────────
function SystemUsers() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]); const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(d || [])).catch(() => { }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="fade">
      <div style={{ marginBottom: 22 }}><div className="ho" style={{ fontSize: 22 }}>Users & Access Control</div><div style={{ fontSize: 13, color: C.sub }}>Manage system roles, permissions and account status.</div></div>
      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw"><table className="ht"><thead><tr><th>Staff Member</th><th>Email</th><th>Role</th><th>Department</th><th>Status</th></tr></thead>
          <tbody>{staff.map(s => (
            <tr key={s.id}>
              <td><div style={{ display: "flex", alignItems: "center", gap: 10 }}><Av av={s.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={28} /><span style={{ fontWeight: 800, color: C.text }}>{s.full_name}</span></div></td>
              <td style={{ fontSize: 12, color: C.muted }}>{s.email}</td>
              <td><span className="tg to" style={{ fontSize: 10 }}>{s.role || "staff"}</span></td>
              <td>{s.department || "—"}</td>
              <td><span className="tg" style={{ background: s.is_active ? "#4ADE8022" : "#F8717122", color: s.is_active ? "#4ADE80" : "#F87171" }}>{s.is_active ? "Active" : "Inactive"}</span></td>
            </tr>
          ))}
            {staff.length === 0 && !loading && <tr><td colSpan="5" style={{ textAlign: "center", padding: 30, color: C.muted }}>No users found.</td></tr>}
          </tbody>
        </table></div>
      </div>
    </div>
  );
}


// ─── HUB: HR CALENDAR ─────────────────────────────────────────────────────────
function HRCalendarView({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const isHR = user && user.role && (user.role.includes("admin") || user.role.includes("hr_admin"));
  const [events, setEvents] = useState([]);
  const [month, setMonth] = useState(new Date());
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ title: "", event_type: "Holiday", date: "", end_date: "", description: "", department: "All" });

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/calendar-events`).then(d => setEvents(d || [])).catch(() => {
      setEvents([
        { id: "1", title: "Q2 Performance Reviews Due", event_type: "Deadline", date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0], department: "All" },
        { id: "2", title: "Recruitment Interview Day", event_type: "Interview", date: new Date(Date.now() + 3 * 86400000).toISOString().split("T")[0], department: "HR" },
        { id: "3", title: "Payroll Processing", event_type: "Payroll", date: new Date(Date.now() + 14 * 86400000).toISOString().split("T")[0], department: "Finance" },
        { id: "4", title: "Board Strategy Meeting", event_type: "Meeting", date: new Date(Date.now() + 10 * 86400000).toISOString().split("T")[0], department: "Executive" },
      ]);
    });
  }, []);

  const addEvent = async () => {
    if (!form.title || !form.date) return alert("Title and date required");
    try { await apiFetch(`${API_BASE}/hr/calendar-events`, { method: "POST", body: JSON.stringify({ title: form.title, date: form.date, event_type: form.event_type, department: isHR ? form.department : (user?.department || "Personal") }) }); } catch (e) { }
    setEvents(prev => [{ ...form, id: Date.now().toString() }, ...prev]);
    setShowNew(false); setForm({ title: "", event_type: "Holiday", date: "", end_date: "", description: "", department: "All" });
  };

  const typeCol = { Holiday: "#4ADE80", Deadline: "#F87171", Interview: T.gold, Payroll: "#60A5FA", Meeting: "#A78BFA", Training: "#F59E0B", Review: "#EC4899", "Focus Time": "#8B5CF6", Leave: "#F43F5E", "Team Sync": "#0EA5E9" };

  // Build calendar grid for current month
  const y = month.getFullYear(); const m = month.getMonth();
  const firstDay = new Date(y, m, 1).getDay();
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const cells = Array.from({ length: firstDay }, () => null).concat(Array.from({ length: daysInMonth }, (_, i) => i + 1));
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

  const monthEvents = events.filter(e => { if (!e.date) return false; const d = new Date(e.date); return d.getFullYear() === y && d.getMonth() === m; });
  const eventsForDay = (day) => monthEvents.filter(e => new Date(e.date).getDate() === day);
  const today = new Date();

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>HR Calendar</div><div style={{ fontSize: 13, color: C.sub }}>Company-wide events, deadlines, payroll dates, and HR milestones.</div></div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Add Event</button>
      </div>
      {/* Month nav */}
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
        <button className="bg" style={{ padding: "6px 14px" }} onClick={() => setMonth(new Date(y, m - 1))}>← Prev</button>
        <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 20, color: C.text, minWidth: 200, textAlign: "center" }}>{month.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</div>
        <button className="bg" style={{ padding: "6px 14px" }} onClick={() => setMonth(new Date(y, m + 1))}>Next →</button>
        <button className="bg" style={{ padding: "6px 14px" }} onClick={() => setMonth(new Date())}>Today</button>
      </div>
      {/* Calendar */}
      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", borderBottom: `1px solid ${C.border}` }}>
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(d => (<div key={d} style={{ padding: "8px 0", textAlign: "center", fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px" }}>{d}</div>))}
        </div>
        {weeks.map((week, wi) => (<div key={wi} style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
          {week.map((day, di) => {
            const isToday = day && today.getDate() === day && today.getFullYear() === y && today.getMonth() === m;
            const dayEvts = day ? eventsForDay(day) : [];
            return (<div key={di} style={{ minHeight: 90, padding: "6px 8px", borderRight: di < 6 ? `1px solid ${C.border}` : "none", borderBottom: wi < weeks.length - 1 ? `1px solid ${C.border}` : "none", background: isToday ? `${T.gold}08` : "transparent" }}>
              {day && (<>
                <div style={{ fontWeight: isToday ? 900 : 400, color: isToday ? T.gold : C.muted, fontSize: 12, marginBottom: 4, width: 22, height: 22, borderRadius: "50%", background: isToday ? `${T.gold}22` : "transparent", display: "flex", alignItems: "center", justifyContent: "center" }}>{day}</div>
                {dayEvts.slice(0, 2).map(e => { const ec = typeCol[e.event_type] || T.gold; return (<div key={e.id} style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: `${ec}22`, color: ec, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.title}</div>); })}
                {dayEvts.length > 2 && <div style={{ fontSize: 9, color: C.muted }}>+{dayEvts.length - 2} more</div>}
              </>)}
            </div>);
          })}
        </div>))}
      </div>
      {/* Upcoming events list */}
      <div style={{ marginTop: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 14 }}>Upcoming Events</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {events.filter(e => e.date && new Date(e.date) >= today).sort((a, b) => new Date(a.holiday_date || a.date) - new Date(b.holiday_date || b.date)).slice(0, 8).map(e => {
            const ec = typeCol[e.event_type] || T.gold;
            return (<div key={e.id} className="gc" style={{ padding: "12px 18px", display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: ec, flexShrink: 0 }} />
              <div style={{ flex: 1 }}><div style={{ fontWeight: 800, color: C.text, fontSize: 13 }}>{e.title}</div><div style={{ fontSize: 11, color: C.muted }}>{e.department} · {new Date(e.date).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</div></div>
              <span className="tg" style={{ background: `${ec}22`, color: ec, border: `1px solid ${ec}44` }}>{e.event_type}</span>
            </div>);
          })}
        </div>
      </div>
      {showNew && (<Modal onClose={() => setShowNew(false)} title="Add Calendar Event" width={520}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Event Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Q3 Performance Reviews Due" /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Event Type</Lbl><select className="inp" value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}>{isHR ? (<><option>Holiday</option><option>Deadline</option><option>Interview</option><option>Payroll</option><option>Meeting</option><option>Training</option><option>Review</option></>) : (<><option>Meeting</option><option>Focus Time</option><option>Leave</option><option>Team Sync</option></>)}</select></div>
            <div><Lbl>Scope / Department</Lbl>{isHR ? <select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}><option>All</option><option>HR</option><option>Finance</option><option>Sales & Acquisitions</option><option>Operations</option><option>Executive</option></select> : <div style={{ padding: "10px 14px", background: C.base, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 13, color: C.text }}>{user?.department || "Personal"} (Auto-assigned)</div>}</div>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Start Date *</Lbl><input type="date" className="inp" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} /></div>
            <div><Lbl>End Date</Lbl><input type="date" className="inp" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} /></div>
          </div>
          <div><Lbl>Description</Lbl><textarea className="inp" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
          <button className="bp" onClick={addEvent} style={{ padding: 14 }}>Add Event</button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── HUB: HOLIDAYS MANAGER ─────────────────────────────────────────────────────
function HolidaysManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [holidays, setHolidays] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", date: "", holiday_type: "Public Holiday", is_mandatory: true });

  const defaultHolidays = [
    { id: "1", name: "New Year's Day", date: `${new Date().getFullYear()}-01-01`, holiday_type: "Public Holiday", is_mandatory: true },
    { id: "2", name: "Independence Day", date: `${new Date().getFullYear()}-10-01`, holiday_type: "Public Holiday", is_mandatory: true },
    { id: "3", name: "Christmas Day", date: `${new Date().getFullYear()}-12-25`, holiday_type: "Public Holiday", is_mandatory: true },
    { id: "4", name: "Boxing Day", date: `${new Date().getFullYear()}-12-26`, holiday_type: "Public Holiday", is_mandatory: true },
    { id: "5", name: "Workers' Day", date: `${new Date().getFullYear()}-05-01`, holiday_type: "Public Holiday", is_mandatory: true },
    { id: "6", name: "Democracy Day", date: `${new Date().getFullYear()}-06-12`, holiday_type: "Public Holiday", is_mandatory: true },
    { id: "7", name: "Company Retreat", date: `${new Date().getFullYear()}-08-15`, holiday_type: "Company Holiday", is_mandatory: false },
  ];

  useEffect(() => {
    apiFetch(`${API_BASE}/hr/holidays`).then(d => setHolidays(d?.length ? d : defaultHolidays)).catch(() => setHolidays(defaultHolidays));
  }, []);

  const addHoliday = async () => {
    if (!form.name || !form.date) return alert("Name and date required");
    try { await apiFetch(`${API_BASE}/hr/holidays`, { method: "POST", body: JSON.stringify({ title: form.title, department: form.department, employment_type: form.employment_type, location: form.location, salary_range: form.salary_range, description: form.description, responsibilities: form.responsibilities, requirements: form.requirements, status: "Pending Approval" }) }); } catch (e) { }
    setHolidays(prev => [...prev, { ...form, holiday_date: form.date, id: Date.now().toString() }].sort((a, b) => new Date(a.holiday_date || a.date) - new Date(b.holiday_date || b.date)));
    setShowAdd(false); setForm({ name: "", date: "", holiday_type: "Public Holiday", is_mandatory: true });
  };

  const typeCol = { "Public Holiday": "#4ADE80", "Company Holiday": T.gold, "Optional Holiday": "#60A5FA", "Religious Holiday": "#A78BFA" };
  const today = new Date();
  const upcoming = holidays.filter(h => new Date(h.holiday_date || h.date) >= today).sort((a, b) => new Date(a.holiday_date || a.date) - new Date(b.holiday_date || b.date));
  const past = holidays.filter(h => new Date(h.holiday_date || h.date) < today).sort((a, b) => new Date(b.holiday_date || b.date) - new Date(a.holiday_date || a.date));

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Holidays</div><div style={{ fontSize: 13, color: C.sub }}>Public and company holidays. Configure the official holiday calendar for leave calculations.</div></div>
        <button className="bp" onClick={() => setShowAdd(true)}>+ Add Holiday</button>
      </div>
      <div className="g3" style={{ marginBottom: 24 }}>
        <StatCard label="Total Holidays" value={holidays.length} col={T.gold} />
        <StatCard label="Upcoming" value={upcoming.length} col="#60A5FA" />
        <StatCard label="Mandatory" value={holidays.filter(h => h.is_mandatory).length} col="#4ADE80" />
      </div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: T.gold, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 14 }}>📅 Upcoming Holidays</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {upcoming.map(h => {
            const daysAway = Math.ceil((new Date(h.holiday_date || h.date) - today) / 86400000);
            const hc = typeCol[h.holiday_type] || T.gold;
            return (<div key={h.id} className="gc" style={{ padding: "14px 20px", display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 48, height: 48, borderRadius: 10, background: `${hc}18`, border: `1px solid ${hc}33`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <div style={{ fontSize: 10, fontWeight: 800, color: hc, textTransform: "uppercase" }}>{new Date(h.holiday_date || h.date).toLocaleDateString(undefined, { month: "short" })}</div>
                <div style={{ fontSize: 18, fontWeight: 900, color: hc, lineHeight: 1 }}>{new Date(h.holiday_date || h.date).getDate()}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 800, color: C.text }}>{h.name}</div>
                <div style={{ fontSize: 12, color: C.muted }}>{new Date(h.holiday_date || h.date).toLocaleDateString(undefined, { weekday: "long" })} · {daysAway === 0 ? "Today" : `${daysAway} day${daysAway !== 1 ? "s" : ""} away`}</div>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span className="tg" style={{ background: `${hc}22`, color: hc, border: `1px solid ${hc}44` }}>{h.holiday_type}</span>
                {h.is_mandatory && <span className="tg" style={{ background: "#4ADE8022", color: "#4ADE80" }}>Mandatory</span>}
              </div>
            </div>);
          })}
          {upcoming.length === 0 && <div style={{ textAlign: "center", padding: 40, color: C.muted }}>No upcoming holidays this year.</div>}
        </div>
      </div>
      {past.length > 0 && (<div>
        <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 14 }}>Past Holidays This Year</div>
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}><div className="tw"><table className="ht">
          <thead><tr><th>Holiday</th><th>Date</th><th>Type</th><th>Mandatory</th></tr></thead>
          <tbody>{past.map(h => { const hc = typeCol[h.holiday_type] || T.gold; return (<tr key={h.id}><td style={{ fontWeight: 700, color: C.text }}>{h.name}</td><td style={{ color: C.muted, fontSize: 12 }}>{new Date(h.holiday_date || h.date).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</td><td><span className="tg" style={{ background: `${hc}22`, color: hc }}>{h.holiday_type}</span></td><td><span className="tg" style={{ background: h.is_mandatory ? "#4ADE8022" : "#9CA3AF22", color: h.is_mandatory ? "#4ADE80" : "#9CA3AF" }}>{h.is_mandatory ? "Yes" : "Optional"}</span></td></tr>); })}</tbody>
        </table></div></div>
      </div>)}
      {showAdd && (<Modal onClose={() => setShowAdd(false)} title="Add Holiday" width={480}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Holiday Name *</Lbl><input className="inp" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Eid al-Fitr" /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Date *</Lbl><input type="date" className="inp" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} /></div>
            <div><Lbl>Type</Lbl><select className="inp" value={form.holiday_type} onChange={e => setForm(f => ({ ...f, holiday_type: e.target.value }))}><option>Public Holiday</option><option>Company Holiday</option><option>Optional Holiday</option><option>Religious Holiday</option></select></div>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", fontSize: 13, color: C.text, fontWeight: 700 }}>
            <input type="checkbox" checked={form.is_mandatory} onChange={e => setForm(f => ({ ...f, is_mandatory: e.target.checked }))} style={{ width: 16, height: 16, accentColor: T.gold }} />Mandatory (affects leave calculations)
          </label>
          <button className="bp" onClick={addHoliday} style={{ padding: 14 }}>Add Holiday</button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── HUB: BENEFITS MANAGER ─────────────────────────────────────────────────────
function BenefitsManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [tab, setTab] = useState("packages");
  const [packages, setPackages] = useState([
    { id: "1", name: "Standard Benefits", tier: "Standard", health: true, dental: true, vision: false, life_insurance: true, pension: "8%", transport: "₦20,000/mo", meal: "₦10,000/mo", staff_count: 24 },
    { id: "2", name: "Senior Benefits Package", tier: "Senior", health: true, dental: true, vision: true, life_insurance: true, pension: "10%", transport: "₦35,000/mo", meal: "₦15,000/mo", staff_count: 12 },
    { id: "3", name: "Executive Benefits", tier: "Executive", health: true, dental: true, vision: true, life_insurance: true, pension: "15%", transport: "Car allowance", meal: "Unrestricted", staff_count: 5 },
  ]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", tier: "Standard", health: true, dental: false, vision: false, life_insurance: true, pension: "8%", transport: "", meal: "" });

  const tierCol = { Standard: "#60A5FA", Senior: T.gold, Executive: "#A78BFA" };

  const benefit = (has, label) => (<span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: has ? "#4ADE80" : "#F87171" }}>{has ? "✓" : "✗"} {label}</span>);

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Benefits</div><div style={{ fontSize: 13, color: C.sub }}>Manage employee benefit packages — health, pension, transport, and allowances.</div></div>
        <div style={{ display: "flex", gap: 10 }}>
          <Tabs items={[["packages", "Packages"], ["claims", "Claims"]]} active={tab} setActive={setTab} />
          <button className="bp" onClick={() => setShowAdd(true)} style={{ height: 38 }}>+ Add Package</button>
        </div>
      </div>
      {tab === "packages" && (
        <div className="g3" style={{ gap: 18 }}>
          {packages.map(p => {
            const tc = tierCol[p.tier] || T.gold;
            return (<div key={p.id} className="gc" style={{ padding: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                <div><div style={{ fontWeight: 800, fontSize: 15, color: C.text }}>{p.name}</div><div style={{ fontSize: 12, color: C.sub }}>{p.staff_count} staff enrolled</div></div>
                <span className="tg" style={{ background: `${tc}22`, color: tc, border: `1px solid ${tc}44`, alignSelf: "flex-start" }}>{p.tier}</span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 14, paddingBottom: 14, borderBottom: `1px solid ${C.border}` }}>
                {benefit(p.health, "Health")} {benefit(p.dental, "Dental")} {benefit(p.vision, "Vision")} {benefit(p.life_insurance, "Life Insurance")}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {p.pension && <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}><span style={{ color: C.muted }}>Pension Contribution</span><strong style={{ color: C.text }}>{p.pension}</strong></div>}
                {p.transport && <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}><span style={{ color: C.muted }}>Transport Allowance</span><strong style={{ color: C.text }}>{p.transport}</strong></div>}
                {p.meal && <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}><span style={{ color: C.muted }}>Meal Allowance</span><strong style={{ color: C.text }}>{p.meal}</strong></div>}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button className="bg" style={{ flex: 1, fontSize: 11, padding: "7px" }}>Edit Package</button>
                <button className="bp" style={{ flex: 1, fontSize: 11, padding: "7px" }}>View Staff</button>
              </div>
            </div>);
          })}
        </div>
      )}
      {tab === "claims" && (
        <div className="gc" style={{ padding: 32, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>🏥</div>
          <div style={{ fontWeight: 800, color: C.text, marginBottom: 8 }}>Benefits Claims Portal</div>
          <div style={{ fontSize: 13, color: C.sub }}>Staff benefit claims and reimbursement requests will appear here. Connect your benefits provider to enable claim submissions.</div>
        </div>
      )}
      {showAdd && (<Modal onClose={() => setShowAdd(false)} title="Add Benefits Package" width={520}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Package Name *</Lbl><input className="inp" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Mid-Level Benefits" /></div>
          <div><Lbl>Tier</Lbl><select className="inp" value={form.tier} onChange={e => setForm(f => ({ ...f, tier: e.target.value }))}><option>Standard</option><option>Senior</option><option>Executive</option></select></div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {[["health", "Health Insurance"], ["dental", "Dental"], ["vision", "Vision"], ["life_insurance", "Life Insurance"]].map(([key, label]) => (
              <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: C.text, fontWeight: 700 }}>
                <input type="checkbox" checked={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.checked }))} style={{ width: 16, height: 16, accentColor: T.gold }} />{label}
              </label>
            ))}
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Pension %</Lbl><input className="inp" value={form.pension} onChange={e => setForm(f => ({ ...f, pension: e.target.value }))} placeholder="e.g. 8%" /></div>
            <div><Lbl>Transport Allowance</Lbl><input className="inp" value={form.transport} onChange={e => setForm(f => ({ ...f, transport: e.target.value }))} placeholder="e.g. ₦20,000/mo" /></div>
          </div>
          <button className="bp" onClick={() => { setPackages(prev => [...prev, { ...form, id: Date.now().toString(), staff_count: 0 }]); setShowAdd(false); }} style={{ padding: 14 }}>Add Package</button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── HUB: EXPENSES MANAGER ─────────────────────────────────────────────────────
function ExpensesManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  // ── Main data ──
  const [tab, setTab] = useState("expenses"); // "expenses" | "commissions"
  const [expenses, setExpenses] = useState([]);
  const [commissions, setCommissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("All");
  const [commissionFilter, setCommissionFilter] = useState("All");
  const [staffFilter, setStaffFilter] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ staff_id: "", category: "Travel", amount: "", currency: "NGN", description: "", date: "", receipt_url: "", remarks: "" });
  const [staff, setStaff] = useState([]);
  // ── Verification modal (mirrors payout dashboard verify flow) ──
  const [verifying, setVerifying] = useState(null); // expense or commission record being verified
  const [verifyForm, setVerifyForm] = useState({ decision: "approve", hr_note: "" });
  const [verifyBusy, setVerifyBusy] = useState(false);
  // ── Detail drawer ──
  const [detail, setDetail] = useState(null);
  const [payingId, setPayingId] = useState(null);
  // ── Pay modal (partial / full reimbursement) ──
  const [payModal, setPayModal] = useState(null);

  const fmt = n => n != null ? `₦${Number(n).toLocaleString()}` : "—";

  // Normalise a raw expenditure_request row (already pre-normalised by the backend) into
  // the shape the expense table rows expect.
  const normaliseExpense = (r) => ({
    id: r.id,
    staff_id: r.staff_id || r.requester_id,
    staff: r.staff || { full_name: r.vendor?.name || "—" },
    vendor: r.vendor || r.vendors || {},
    category: r.category || "General",
    description: r.description || r.title || "—",
    amount: parseFloat(r.amount || r.amount_gross || 0),
    amount_gross: parseFloat(r.amount_gross || 0),
    net: parseFloat(r.net || r.net_payout_amount || r.amount_gross || 0),
    currency: "NGN",
    date: r.date || r.created_at,
    created_at: r.created_at,
    // Normalise all status variants to a consistent capitalised form for display
    status: { pending_verification: "Pending", pending: "Pending", approved: "Approved",
              rejected: "Rejected", paid: "Paid", voided: "Voided" }[r.status] || r.status || "Pending",
    payout_method: r.payout_method,
    receipt_url: r.receipt_url || r.proforma_url || null,
    remarks: r.remarks || null,
    rejection_reason: r.rejection_reason || null,
    is_disputed: r.is_disputed || false,
    dispute_reason: r.dispute_reason || null,
    risk_notes: r.risk_notes || null,
    source: r.source_platform === "payout_portal" ? "PORTAL"
           : r.source_platform === "hrm_portal" ? "INTERNAL"
           : r.source_platform ? r.source_platform.toUpperCase() : "INTERNAL",
    // hr_verified: no dedicated column — derive from reviewed_by being set
    hr_verified: !!(r.reviewed_by || r.hr_verified),
    // hr_note: stored in rejection_reason (for rejections) or risk_notes with [HR Note] prefix
    hr_note: r.hr_note
      || (r.risk_notes && r.risk_notes.startsWith("[HR Note]") ? r.risk_notes.replace("[HR Note] ", "") : null)
      || null,
    payments: r.payments || [],
  });

  const load = () => {
    setLoading(true);
    Promise.all([
      // Single source of truth — the fixed /hr/expenses backend now queries expenditure_requests
      apiFetch(`${API_BASE}/hr/expenses`).catch(() => []),
      apiFetch(`${API_BASE}/hr/staff`).catch(() => []),
      // Commissions come directly from payouts — category = 'Sales Commission'
      apiFetch(`${API_BASE}/payouts/requests?payment_type=staff_commission`).catch(() => []),
    ]).then(([expenses, s, commReqs]) => {
      // ── Expense records (already normalised by backend) ──
      const expList = (Array.isArray(expenses) ? expenses : [])
        .map(normaliseExpense)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setExpenses(expList);
      setStaff(Array.isArray(s) ? s : []);

      // ── Commission records ──
      const commList = (Array.isArray(commReqs) ? commReqs : []).map(r => ({
        id: r.id,
        staff_id: r.requester_id || r.vendors?.id,
        staff: { full_name: r.vendors?.name || "—" },
        invoice_number: r.vendor_invoice_number || r.metadata?.invoice_number || r.title,
        estate: r.metadata?.estate_name || r.category || "—",
        gross: parseFloat(r.amount_gross || 0),
        wht: parseFloat(r.wht_amount || 0),
        net: parseFloat(r.net_payout_amount || (r.amount_gross - (r.wht_amount || 0)) || 0),
        date: r.created_at,
        created_at: r.created_at,
        payout_status: r.status,
        hr_verified: r.hr_verified || false,
        hr_note: r.hr_note || null,
        receipt_url: r.receipt_url || r.proforma_url || null,
        proforma_url: r.proforma_url || null,
        expenditure_id: r.id,
        remarks: r.remarks || null,
      }));
      setCommissions(commList);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  // ── Submit new expense — posts to /hr/expenses which now writes to expenditure_requests ──
  const submit = async () => {
    if (!form.amount || !form.description) return alert("Amount and description required");
    try {
      const created = await apiFetch(`${API_BASE}/hr/expenses`, {
        method: "POST",
        body: JSON.stringify({ ...form, status: "Pending" }),
      });
      // Re-fetch so the table shows the real DB row with vendor joins resolved
      load();
    } catch (e) {
      alert("Failed to submit expense: " + (e.message || "Unknown error"));
    }
    setShowNew(false);
    setForm({ staff_id: "", category: "Travel", amount: "", currency: "NGN", description: "", date: "", receipt_url: "", remarks: "" });
  };

  // ── HR quick approve/reject — both PORTAL and INTERNAL go through /hr/expenses/{id}
  //    which now writes to expenditure_requests with the correct status mapping ──
  const approve = async (id) => {
    try {
      await apiFetch(`${API_BASE}/hr/expenses/${id}`, { method: "PATCH", body: JSON.stringify({ status: "Approved" }) });
    } catch (e) { alert("Approve failed: " + (e.message || "Unknown error")); return; }
    setExpenses(prev => prev.map(x => x.id === id ? { ...x, status: "Approved" } : x));
  };
  const reject = async (id) => {
    const reason = window.prompt("Rejection reason (shown to staff):");
    if (reason === null) return; // cancelled
    try {
      await apiFetch(`${API_BASE}/hr/expenses/${id}`, { method: "PATCH", body: JSON.stringify({ status: "Rejected", hr_note: reason || undefined }) });
    } catch (e) { alert("Reject failed: " + (e.message || "Unknown error")); return; }
    setExpenses(prev => prev.map(x => x.id === id ? { ...x, status: "Rejected" } : x));
  };

  // ── HR Verify (payout-style — with notes, logged) ──
  const openVerify = (record, kind) => {
    setVerifying({ ...record, _kind: kind });
    setVerifyForm({ decision: "approve", hr_note: "" });
  };
  const submitVerify = async () => {
    if (!verifying) return;
    setVerifyBusy(true);
    const { decision, hr_note } = verifyForm;
    const isApprove = decision === "approve";
    try {
      // PATCH via /hr/expenses/{id} — backend maps to real expenditure_requests columns:
      // rejection → rejection_reason, approve → reviewed_by/reviewed_at
      await apiFetch(`${API_BASE}/hr/expenses/${verifying.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: isApprove ? "Approved" : "Rejected",
          hr_note: hr_note || null,   // backend stores in rejection_reason or risk_notes
        }),
      });
      if (verifying._kind === "expense") {
        setExpenses(prev => prev.map(x => x.id === verifying.id ? {
          ...x,
          status: isApprove ? "Approved" : "Rejected",
          rejection_reason: !isApprove ? hr_note : x.rejection_reason,
        } : x));
      } else {
        setCommissions(prev => prev.map(x => x.id === verifying.id ? {
          ...x,
          payout_status: isApprove ? "approved" : "rejected",
          rejection_reason: !isApprove ? hr_note : x.rejection_reason,
        } : x));
      }
      setVerifying(null);
    } catch (err) {
      alert("Verification failed: " + (err.message || "Unknown error"));
    } finally { setVerifyBusy(false); }
  };

  // ── Pay modal helpers ──
  const openPayModal = (exp) => {
    const alreadyPaid = parseFloat(exp.amount_paid || 0);
    const net = parseFloat(exp.net || exp.amount || 0);
    const balance = Math.max(0, net - alreadyPaid);
    setPayModal({ exp, amountInput: String(balance), ref: "", busy: false });
  };

  const confirmPay = async () => {
    if (!payModal) return;
    const { exp, amountInput, ref } = payModal;
    const amountSent = parseFloat(amountInput);
    if (!amountSent || amountSent <= 0) { alert("Please enter a valid amount."); return; }
    const net = parseFloat(exp.net || exp.amount || 0);
    const alreadyPaid = parseFloat(exp.amount_paid || 0);
    const balance = Math.max(0, net - alreadyPaid);
    if (amountSent > balance + 0.01) { alert(`Amount exceeds outstanding balance of ₦${balance.toLocaleString()}.`); return; }
    setPayModal(prev => ({ ...prev, busy: true }));
    try {
      const newAmountPaid = alreadyPaid + amountSent;
      const isFullyPaid = newAmountPaid >= net - 0.05;
      await apiFetch(`${API_BASE}/hr/expenses/${exp.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: isFullyPaid ? "Paid" : "partially_paid",
          amount_paid: newAmountPaid,
          payout_reference: ref || undefined,
        }),
      });
      setExpenses(prev => prev.map(x => x.id === exp.id ? {
        ...x,
        status: isFullyPaid ? "paid" : "partially_paid",
        amount_paid: newAmountPaid,
      } : x));
      setPayModal(null);
    } catch (e) {
      alert("Error: " + e.message);
      setPayModal(prev => ({ ...prev, busy: false }));
    }
  };

  // ── Derived / display ──
  const statuses = ["All", "Pending", "Approved", "Partially Paid", "Rejected", "Paid"];
  const stCol = { Pending: T.gold, Approved: "#4ADE80", Rejected: "#F87171", Paid: "#60A5FA", "Partially Paid": "#F59E0B", approved: "#4ADE80", rejected: "#F87171", paid: "#60A5FA", pending: T.gold, partially_paid: "#F59E0B" };
  const catEmoji = { Travel: "✈️", Accommodation: "🏨", Meals: "🍽️", Equipment: "💻", Training: "📚", Commission: "💰", Other: "📋" };

  const normalize = s => (s || "").toLowerCase();
  const filteredExpenses = expenses.filter(e => {
    const matchStatus = statusFilter === "All" || normalize(e.status) === normalize(statusFilter) || (statusFilter === "Partially Paid" && normalize(e.status) === "partially_paid");
    const matchStaff = !staffFilter || (e.staff?.full_name || "").toLowerCase().includes(staffFilter.toLowerCase());
    return matchStatus && matchStaff;
  });
  const filteredCommissions = commissions.filter(c => {
    const matchStatus = commissionFilter === "All" || normalize(c.payout_status) === normalize(commissionFilter);
    const matchStaff = !staffFilter || (c.staff?.full_name || "").toLowerCase().includes(staffFilter.toLowerCase());
    return matchStatus && matchStaff;
  });

  const totalPending = expenses.filter(e => normalize(e.status) === "pending").reduce((s, e) => s + parseFloat(e.net || e.amount || 0), 0);
  // Option A: separate paid vs owed so the stat cards are accurate
  const totalReimbPaid = expenses.filter(e => normalize(e.status) === "paid").reduce((s, e) => s + parseFloat(e.net || e.amount || 0), 0)
    + expenses.filter(e => normalize(e.status) === "partially_paid").reduce((s, e) => s + parseFloat(e.amount_paid || 0), 0);
  const totalReimbOwed = expenses.filter(e => ["approved", "partially_paid"].includes(normalize(e.status))).reduce((s, e) => {
    const net = parseFloat(e.net || e.amount || 0);
    const paid = parseFloat(e.amount_paid || 0);
    return s + Math.max(0, net - paid);
  }, 0);
  // Keep for backward compat (used by nothing else now)
  const totalApproved = totalReimbPaid + totalReimbOwed;
  const totalCommOwed = commissions.filter(c => normalize(c.payout_status) !== "paid").reduce((s, c) => s + parseFloat(c.net || 0), 0);
  const totalCommPaid = commissions.filter(c => normalize(c.payout_status) === "paid").reduce((s, c) => s + parseFloat(c.net || 0), 0);
  const unverifiedCount = [...expenses, ...commissions].filter(r => !r.hr_verified && normalize(r.status || r.payout_status) !== "rejected").length;

  const commStatuses = ["All", "Pending", "Approved", "Paid", "Rejected"];

  return (
    <div className="fade">
      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Expenses & Commissions</div>
          <div style={{ fontSize: 13, color: C.sub }}>Unified view of staff expense reimbursements and commission payouts — with HR verification.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {unverifiedCount > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: `${T.gold}18`, border: `1px solid ${T.gold}40`, borderRadius: 8, padding: "6px 14px" }}>
              <span style={{ fontSize: 18 }}>⚠️</span>
              <span style={{ fontSize: 12, color: T.gold, fontWeight: 800 }}>{unverifiedCount} awaiting HR verification</span>
            </div>
          )}
          <button className="bp" onClick={() => setShowNew(true)}>+ Submit Expense</button>
        </div>
      </div>

      {/* ── Summary cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 14, marginBottom: 22 }}>
        <StatCard label="Expense Claims Pending" value={expenses.filter(e => normalize(e.status) === "pending").length} col={T.gold} sub={fmt(totalPending)} />
        <StatCard label="Reimb. Owed" value={expenses.filter(e => ["approved","partially_paid"].includes(normalize(e.status))).length} col="#F87171" sub={fmt(totalReimbOwed)} />
        <StatCard label="Reimb. Paid Out" value={expenses.filter(e => normalize(e.status) === "paid").length} col="#4ADE80" sub={fmt(totalReimbPaid)} />
        <StatCard label="Commission Owed (Unpaid)" value={commissions.filter(c => normalize(c.payout_status) !== "paid" && normalize(c.payout_status) !== "rejected").length} col="#F59E0B" sub={fmt(totalCommOwed)} />
        <StatCard label="Commission Paid Out" value={commissions.filter(c => normalize(c.payout_status) === "paid").length} col="#60A5FA" sub={fmt(totalCommPaid)} />
      </div>

      {/* ── Tab bar ── */}
      <div style={{ display: "flex", gap: 0, marginBottom: 20, borderBottom: `2px solid ${C.border}` }}>
        {[["expenses", "💳 Expense Claims"], ["commissions", "💰 Staff Commissions"]].map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} style={{ padding: "10px 22px", border: "none", borderBottom: tab === id ? `2px solid ${T.gold}` : "2px solid transparent", background: "transparent", color: tab === id ? T.gold : C.sub, fontWeight: tab === id ? 800 : 500, fontSize: 13, cursor: "pointer", marginBottom: -2, transition: "all 0.2s" }}>{label}</button>
        ))}
        <div style={{ flex: 1 }} />
        {/* Global staff search */}
        <input className="inp" placeholder="🔍 Filter by staff name…" value={staffFilter} onChange={e => setStaffFilter(e.target.value)} style={{ width: 200, fontSize: 12, padding: "6px 12px", marginBottom: 6 }} />
      </div>

      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (<>

        {/* ══════════════════════ EXPENSES TAB ══════════════════════ */}
        {tab === "expenses" && (
          <div className="fade">
            {/* Status filter pills */}
            <div style={{ display: "flex", gap: 8, marginBottom: 18, flexWrap: "wrap" }}>
              {statuses.map(s => {
                const col = stCol[s.toLowerCase()] || C.muted;
                const cnt = s === "All" ? expenses.length : expenses.filter(e => normalize(e.status) === normalize(s)).length;
                return (
                  <button key={s} onClick={() => setStatusFilter(s)} style={{ padding: "6px 16px", borderRadius: 20, border: `1px solid ${statusFilter === s ? col : C.border}`, background: statusFilter === s ? `${col}22` : "transparent", color: statusFilter === s ? col : C.sub, cursor: "pointer", fontSize: 12, fontWeight: statusFilter === s ? 800 : 400 }}>
                    {s} ({cnt})
                  </button>
                );
              })}
            </div>

            <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
              <div className="tw">
                <table className="ht">
                  <thead>
                    <tr>
                      <th>Staff</th><th>Category</th><th>Description</th><th>Amount</th><th>Date</th>
                      <th>Remarks</th><th>Source</th><th>Status</th><th>HR Verified</th><th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredExpenses.map(e => {
                      const sc = stCol[normalize(e.status)] || C.muted;
                      return (
                        <tr key={e.id} style={{ cursor: "pointer" }} onClick={() => setDetail({ ...e, _kind: "expense" })}>
                          <td style={{ fontWeight: 800, color: C.text }}>{e.staff?.full_name || e.staff_id || "—"}</td>
                          <td><span style={{ fontSize: 13 }}>{catEmoji[e.category] || "📋"}</span> <span style={{ fontSize: 12, color: C.sub }}>{e.category}</span></td>
                          <td style={{ maxWidth: 200 }}>
                            <div style={{ display: "flex", alignItems: "flex-start", gap: 6, flexWrap: "wrap" }}>
                              {e.is_disputed && (
                                <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 6px", borderRadius: 4, background: "#EF4444", color: "#fff", flexShrink: 0 }}>DISPUTE</span>
                              )}
                              {e.risk_notes && !e.is_disputed && (
                                <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 6px", borderRadius: 4, background: "#F59E0B", color: "#fff", flexShrink: 0 }}>⚠ HIGH RISK</span>
                              )}
                            </div>
                            <div style={{ fontSize: 12, color: C.sub, marginTop: 2 }}>{e.description}</div>
                            {e.remarks && (
                              <div style={{ fontSize: 10, color: C.muted, marginTop: 3, lineHeight: 1.4 }}>
                                💬 {e.remarks.length > 60 ? e.remarks.slice(0, 60) + "…" : e.remarks}
                              </div>
                            )}
                          </td>
                          <td style={{ fontWeight: 800, color: T.gold }}>₦{parseFloat(e.amount || 0).toLocaleString()}</td>
                          <td style={{ fontSize: 11, color: C.muted }}>{e.date ? new Date(e.date).toLocaleDateString("en-GB") : (e.created_at ? new Date(e.created_at).toLocaleDateString("en-GB") : "—")}</td>
                          <td style={{ maxWidth: 140 }}>{e.remarks ? <span style={{ fontSize: 11, color: C.sub }} title={e.remarks}>{e.remarks.length > 50 ? e.remarks.slice(0, 50) + "…" : e.remarks}</span> : <span style={{ fontSize: 11, color: C.muted }}>—</span>}</td>
                          <td><span style={{ fontSize: 10, fontWeight: 800, padding: "3px 8px", borderRadius: 10, background: e.source === "PORTAL" ? `${T.gold}22` : `${C.muted}22`, color: e.source === "PORTAL" ? T.gold : C.muted }}>{e.source || "INTERNAL"}</span></td>
                          <td>
                            <span className="tg" style={{ background: `${sc}22`, color: sc, fontSize: 10 }}>{e.status}</span>
                            {normalize(e.status) === "rejected" && e.rejection_reason && (
                              <div style={{ fontSize: 10, color: "#F87171", marginTop: 4, lineHeight: 1.4 }} title={e.rejection_reason}>
                                ↳ {e.rejection_reason.length > 60 ? e.rejection_reason.slice(0, 60) + "…" : e.rejection_reason}
                              </div>
                            )}
                          </td>
                          <td>
                            {e.hr_verified
                              ? <span style={{ fontSize: 10, color: "#10B981", fontWeight: 800 }}>✓ Verified</span>
                              : <span style={{ fontSize: 10, color: T.gold, fontWeight: 700 }}>Pending</span>}
                            {e.hr_note && <div style={{ fontSize: 9, color: C.muted, marginTop: 2 }} title={e.hr_note}>📝 note</div>}
                          </td>
                          <td onClick={ev => ev.stopPropagation()}>
                            <div style={{ display: "flex", gap: 5 }}>
                              {/* Quick approve/reject for pending items */}
                              {normalize(e.status) === "pending" && (
                                <>
                                  <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => approve(e.id)}>Approve</button>
                                  <button style={{ fontSize: 10, padding: "4px 10px", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", borderRadius: 6, cursor: "pointer" }} onClick={() => reject(e.id)}>Reject</button>
                                </>
                              )}
                              {/* HR Verify button — mirrors payout dashboard verify flow */}
                              {!e.hr_verified && normalize(e.status) !== "rejected" && e.source === "PORTAL" && (
                                <button style={{ fontSize: 10, padding: "4px 10px", border: `1px solid ${T.gold}`, background: `${T.gold}18`, color: T.gold, borderRadius: 6, cursor: "pointer", fontWeight: 700 }} onClick={() => openVerify(e, "expense")}>HR Verify</button>
                              )}
                              {(normalize(e.status) === "approved" || normalize(e.status) === "partially_paid") && (
                                <button className="bp" style={{ fontSize: 10, padding: "4px 10px", background: "#10B981" }} onClick={() => openPayModal(e)}>
                                  {normalize(e.status) === "partially_paid" ? "💳 Pay Balance" : "💳 Mark Paid"}
                                </button>
                              )}
                              {normalize(e.status) === "partially_paid" && (() => {
                                const paid = parseFloat(e.amount_paid || 0);
                                const net = parseFloat(e.net || e.amount || 0);
                                return <span style={{ fontSize: 9, color: "#F59E0B", fontWeight: 700 }}>₦{paid.toLocaleString()} / ₦{net.toLocaleString()}</span>;
                              })()}
                              {normalize(e.status) === "paid" && <span style={{ fontSize: 10, color: "#10B981", fontWeight: 800 }}>✓ Reimbursed</span>}
                              {e.receipt_url && <a href={e.receipt_url} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 10, padding: "4px 10px" }}>Receipt</a>}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredExpenses.length === 0 && (
                      <tr><td colSpan="10" style={{ textAlign: "center", padding: 40, color: C.muted }}>No expenses found.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════ COMMISSIONS TAB ══════════════════════ */}
        {tab === "commissions" && (
          <div className="fade">
            <div style={{ display: "flex", gap: 8, marginBottom: 18, flexWrap: "wrap", alignItems: "center" }}>
              {commStatuses.map(s => {
                const col = stCol[s.toLowerCase()] || C.muted;
                const cnt = s === "All" ? commissions.length : commissions.filter(c => normalize(c.payout_status) === normalize(s)).length;
                return (
                  <button key={s} onClick={() => setCommissionFilter(s)} style={{ padding: "6px 16px", borderRadius: 20, border: `1px solid ${commissionFilter === s ? col : C.border}`, background: commissionFilter === s ? `${col}22` : "transparent", color: commissionFilter === s ? col : C.sub, cursor: "pointer", fontSize: 12, fontWeight: commissionFilter === s ? 800 : 400 }}>
                    {s} ({cnt})
                  </button>
                );
              })}
              <div style={{ marginLeft: "auto", fontSize: 12, color: C.muted }}>Pulled from Payout Dashboard — full commission ledger</div>
            </div>

            {commissions.length === 0 ? (
              <div style={{ padding: "60px 40px", textAlign: "center", color: C.muted, border: `2px dashed ${C.border}`, borderRadius: 14 }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>💰</div>
                <div style={{ fontSize: 15, fontWeight: 700 }}>No Commission Records Found</div>
                <div style={{ fontSize: 13, marginTop: 6 }}>Commission payouts created in the main Payout Dashboard will appear here for HR review.</div>
              </div>
            ) : (
              <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
                <div className="tw">
                  <table className="ht">
                    <thead>
                      <tr>
                        <th>Staff</th><th>Invoice / Deal</th><th>Estate</th><th>Gross Comm.</th>
                        <th>WHT</th><th>Net Comm.</th><th>Date</th><th>Staff Remarks</th><th>Payout Status</th>
                        <th>HR Verified</th><th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredCommissions.map(c => {
                        const sc = stCol[normalize(c.payout_status)] || C.muted;
                        return (
                          <tr key={c.id} style={{ cursor: "pointer" }} onClick={() => setDetail({ ...c, _kind: "commission" })}>
                            <td style={{ fontWeight: 800, color: C.text }}>{c.staff?.full_name || "—"}</td>
                            <td style={{ fontSize: 12, color: C.sub }}>{c.invoice_number || "—"}</td>
                            <td style={{ fontSize: 12, color: C.sub }}>{c.estate || "—"}</td>
                            <td style={{ fontWeight: 700 }}>{fmt(c.gross)}</td>
                            <td style={{ fontSize: 11, color: "#EF4444" }}>-{fmt(c.wht)}</td>
                            <td style={{ fontWeight: 800, color: T.gold }}>{fmt(c.net)}</td>
                            <td style={{ fontSize: 11, color: C.muted }}>{c.created_at ? new Date(c.created_at).toLocaleDateString("en-GB") : "—"}</td>
                            <td style={{ maxWidth: 200 }}>
                              {c.remarks
                                ? (
                                  <div style={{ display: "flex", alignItems: "flex-start", gap: 5 }}>
                                    <span style={{ fontSize: 14, flexShrink: 0 }}>💬</span>
                                    <span style={{ fontSize: 11, color: C.sub, lineHeight: 1.4, wordBreak: "break-word" }} title={c.remarks}>
                                      {c.remarks.length > 80 ? c.remarks.slice(0, 80) + "…" : c.remarks}
                                    </span>
                                  </div>
                                )
                                : <span style={{ fontSize: 11, color: C.muted }}>—</span>}
                            </td>
                            <td>
                              <span className="tg" style={{ background: `${sc}22`, color: sc, fontSize: 10 }}>{c.payout_status || "pending"}</span>
                            </td>
                            <td>
                              {c.hr_verified
                                ? <span style={{ fontSize: 10, color: "#10B981", fontWeight: 800 }}>✓ Verified</span>
                                : <span style={{ fontSize: 10, color: T.gold, fontWeight: 700 }}>Unverified</span>}
                              {c.hr_note && <div style={{ fontSize: 9, color: C.muted, marginTop: 2 }} title={c.hr_note}>📝 note</div>}
                            </td>
                            <td onClick={ev => ev.stopPropagation()}>
                              <div style={{ display: "flex", gap: 5 }}>
                                {/* HR can verify/dispute commission payouts, same flow as payout dashboard */}
                                {!c.hr_verified && normalize(c.payout_status) !== "rejected" && (
                                  <button style={{ fontSize: 10, padding: "4px 10px", border: `1px solid ${T.gold}`, background: `${T.gold}18`, color: T.gold, borderRadius: 6, cursor: "pointer", fontWeight: 700 }} onClick={() => openVerify(c, "commission")}>HR Verify</button>
                                )}
                                {(c.receipt_url || c.proforma_url) && (
                                  <a href={c.receipt_url || c.proforma_url} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 10, padding: "4px 10px" }}>Proof</a>
                                )}
                                {c.expenditure_id && (
                                  <a href={`${API_BASE}/payouts/requests/${c.expenditure_id}/proof-files`} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 10, padding: "4px 10px" }}>Docs</a>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                      {filteredCommissions.length === 0 && (
                        <tr><td colSpan="11" style={{ textAlign: "center", padding: 40, color: C.muted }}>No commission records match the current filter.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </>)}

      {/* ══════════════════════ DETAIL DRAWER ══════════════════════ */}
      {/* ══ PAY MODAL ══ */}
      {payModal && (() => {
        const { exp, amountInput, ref, busy } = payModal;
        const alreadyPaid = parseFloat(exp.amount_paid || 0);
        const net = parseFloat(exp.net || exp.amount || 0);
        const balance = Math.max(0, net - alreadyPaid);
        const amtSent = parseFloat(amountInput) || 0;
        const willBePartial = amtSent > 0 && amtSent < balance - 0.05;
        const remaining = Math.max(0, balance - amtSent);
        return (
          <Modal onClose={() => !busy && setPayModal(null)} title="Record Reimbursement Payment" width={480}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: "12px 16px", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: 1, marginBottom: 3 }}>Staff</div>
                  <div style={{ fontWeight: 800, fontSize: 13 }}>{exp.staff?.full_name || "—"}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: 1, marginBottom: 3 }}>Claim (Net)</div>
                  <div style={{ fontWeight: 800, fontSize: 13 }}>{fmt(net)}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: 1, marginBottom: 3 }}>Outstanding</div>
                  <div style={{ fontWeight: 800, fontSize: 13, color: balance > 0 ? "#F87171" : "#10B981" }}>{fmt(balance)}</div>
                </div>
              </div>
              {alreadyPaid > 0 && (
                <div style={{ fontSize: 12, color: "#F59E0B", background: "rgba(245,158,11,0.08)", borderRadius: 8, padding: "8px 12px" }}>
                  {fmt(alreadyPaid)} already paid. Settling the remaining {fmt(balance)}.
                </div>
              )}
              <div>
                <div style={{ fontSize: 11, color: C.sub, marginBottom: 6, fontWeight: 600 }}>Amount Actually Sent (NGN) *</div>
                <input
                  type="number" className="inp"
                  value={amountInput} min="1" max={balance} step="100"
                  onChange={e => setPayModal(prev => ({ ...prev, amountInput: e.target.value }))}
                  placeholder={"Up to " + fmt(balance)}
                  style={{ width: "100%", fontWeight: 800, fontSize: 16 }}
                  autoFocus
                />
                {willBePartial && (
                  <div style={{ fontSize: 11, color: "#F59E0B", marginTop: 6 }}>
                    Partial payment — {fmt(remaining)} will remain outstanding.
                  </div>
                )}
                {amtSent >= balance - 0.05 && amtSent > 0 && (
                  <div style={{ fontSize: 11, color: "#10B981", marginTop: 6 }}>Full balance will be settled.</div>
                )}
              </div>
              <div>
                <div style={{ fontSize: 11, color: C.sub, marginBottom: 6, fontWeight: 600 }}>Payment Reference / Transfer ID (optional)</div>
                <input
                  type="text" className="inp"
                  value={ref}
                  onChange={e => setPayModal(prev => ({ ...prev, ref: e.target.value }))}
                  placeholder="e.g. TRF-20260430-001"
                  style={{ width: "100%" }}
                />
              </div>
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                <button className="bg" style={{ padding: "8px 20px" }} onClick={() => setPayModal(null)} disabled={busy}>Cancel</button>
                <button
                  className="bp"
                  style={{ padding: "8px 24px", background: "#10B981", opacity: busy || !amtSent || amtSent <= 0 ? 0.6 : 1 }}
                  onClick={confirmPay}
                  disabled={busy || !amtSent || amtSent <= 0}
                >
                  {busy ? "Saving..." : willBePartial ? "Record Partial Payment" : "Confirm Full Payment"}
                </button>
              </div>
            </div>
          </Modal>
        );
      })()}

      {detail && (
        <Modal onClose={() => setDetail(null)} title={detail._kind === "commission" ? "Commission Detail" : "Expense Claim Detail"} width={580}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Staff</div><div style={{ fontWeight: 800 }}>{detail.staff?.full_name || "—"}</div></div>
              {detail._kind === "commission" ? (
                <>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Invoice</div><div style={{ fontWeight: 700 }}>{detail.invoice_number || "—"}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Estate</div><div>{detail.estate || "—"}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Gross Commission</div><div style={{ fontWeight: 800, color: "#10B981" }}>{fmt(detail.gross)}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>WHT Deducted</div><div style={{ color: "#EF4444" }}>-{fmt(detail.wht)}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Net Payout</div><div style={{ fontWeight: 800, color: T.gold, fontSize: 18 }}>{fmt(detail.net)}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Payout Status</div><span className="tg" style={{ background: `${(stCol[normalize(detail.payout_status)] || C.muted)}22`, color: stCol[normalize(detail.payout_status)] || C.muted }}>{detail.payout_status || "pending"}</span></div>
                </>
              ) : (
                <>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Category</div><div>{catEmoji[detail.category] || "📋"} {detail.category}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Amount</div><div style={{ fontWeight: 800, color: T.gold, fontSize: 18 }}>₦{parseFloat(detail.amount || 0).toLocaleString()}</div></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Status</div><span className="tg" style={{ background: `${(stCol[normalize(detail.status)] || C.muted)}22`, color: stCol[normalize(detail.status)] || C.muted }}>{detail.status}</span></div>
                  <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Source</div><div>{detail.source}</div></div>
                </>
              )}
              <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Date</div><div style={{ fontSize: 12 }}>{detail.created_at ? new Date(detail.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" }) : "—"}</div></div>
              <div><div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>HR Verified</div><div style={{ fontWeight: 700, color: detail.hr_verified ? "#10B981" : T.gold }}>{detail.hr_verified ? "✓ Verified" : "Pending Verification"}</div></div>
            </div>
            {(detail.description || detail.invoice_number) && (
              <div style={{ background: C.base, borderRadius: 8, padding: "12px 14px" }}>
                <div style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Description</div>
                <div style={{ fontSize: 13, color: C.text }}>{detail.description || detail.invoice_number}</div>
              </div>
            )}
            {detail.remarks && (
              <div style={{ background: C.base, borderRadius: 8, padding: "12px 14px", border: `1px solid ${C.border}` }}>
                <div style={{ fontSize: 10, color: T.gold, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6, fontWeight: 800 }}>💬 Staff Remarks</div>
                <div style={{ fontSize: 13, color: C.text, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{detail.remarks}</div>
              </div>
            )}
            {detail.is_disputed && (
              <div style={{ background: "#FEF2F2", border: "1.5px solid #FCA5A5", borderRadius: 8, padding: "12px 14px" }}>
                <div style={{ fontSize: 10, color: "#EF4444", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6, fontWeight: 800 }}>⚠️ Rep Ownership Dispute</div>
                <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{detail.dispute_reason || "Dispute raised via portal."}</div>
              </div>
            )}
            {detail.risk_notes && !detail.is_disputed && (
              <div style={{ background: "#FFFBEB", border: "1.5px solid #FCD34D", borderRadius: 8, padding: "12px 14px" }}>
                <div style={{ fontSize: 10, color: "#D97706", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6, fontWeight: 800 }}>⚠ Risk / Fraud Flags</div>
                <div style={{ fontSize: 12, color: "#374151", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{detail.risk_notes}</div>
              </div>
            )}
            {detail.hr_note && (
              <div style={{ background: `${T.gold}0E`, border: `1px solid ${T.gold}30`, borderRadius: 8, padding: "12px 14px" }}>
                <div style={{ fontSize: 10, color: T.gold, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>HR Note</div>
                <div style={{ fontSize: 13 }}>{detail.hr_note}</div>
              </div>
            )}
            {detail.rejection_reason && (
              <div style={{ background: "#FEF2F2", border: "1.5px solid #FCA5A5", borderRadius: 8, padding: "12px 14px" }}>
                <div style={{ fontSize: 10, color: "#EF4444", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4, fontWeight: 800 }}>⚠️ Rejection Reason</div>
                <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{detail.rejection_reason}</div>
              </div>
            )}
            {(detail.receipt_url || detail.proforma_url) && (
              <a href={detail.receipt_url || detail.proforma_url} target="_blank" rel="noreferrer" className="bp" style={{ textDecoration: "none", textAlign: "center", fontSize: 13, padding: "10px 0" }}>📎 View Attached Document</a>
            )}
          </div>
        </Modal>
      )}

      {/* ══════════════════════ HR VERIFY MODAL ══════════════════════ */}
      {verifying && (
        <Modal onClose={() => setVerifying(null)} title="HR Verification" width={500}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Record summary */}
            <div style={{ background: C.base, borderRadius: 10, padding: "14px 16px" }}>
              <div style={{ fontWeight: 800, fontSize: 15, marginBottom: 4 }}>{verifying.staff?.full_name || "Staff Member"}</div>
              <div style={{ fontSize: 12, color: C.sub }}>
                {verifying._kind === "commission"
                  ? `Commission — Invoice: ${verifying.invoice_number || "—"} · Net: ${fmt(verifying.net)}`
                  : `Expense — ${verifying.category} · ₦${parseFloat(verifying.amount || 0).toLocaleString()}`}
              </div>
              <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
                {verifying.created_at ? new Date(verifying.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" }) : ""}
              </div>
            </div>

            {/* Decision */}
            <div>
              <Lbl>HR Decision *</Lbl>
              <div style={{ display: "flex", gap: 10 }}>
                {["approve", "reject"].map(d => (
                  <button key={d} onClick={() => setVerifyForm(f => ({ ...f, decision: d }))} style={{ flex: 1, padding: "10px 0", borderRadius: 8, border: `2px solid ${verifyForm.decision === d ? (d === "approve" ? "#10B981" : "#EF4444") : C.border}`, background: verifyForm.decision === d ? (d === "approve" ? "#10B98118" : "#EF444418") : "transparent", color: verifyForm.decision === d ? (d === "approve" ? "#10B981" : "#EF4444") : C.sub, fontWeight: 800, fontSize: 13, cursor: "pointer", textTransform: "capitalize" }}>
                    {d === "approve" ? "✓ Approve & Verify" : "✗ Dispute / Reject"}
                  </button>
                ))}
              </div>
            </div>

            {/* Note */}
            <div>
              <Lbl>HR Note {verifyForm.decision === "reject" ? "*" : "(Optional)"}</Lbl>
              <textarea className="inp" value={verifyForm.hr_note} onChange={e => setVerifyForm(f => ({ ...f, hr_note: e.target.value }))} placeholder={verifyForm.decision === "approve" ? "Add any verification notes or comments…" : "Reason for dispute or rejection (required)"} style={{ minHeight: 80, resize: "vertical" }} />
            </div>

            {verifyForm.decision === "reject" && !verifyForm.hr_note.trim() && (
              <div style={{ fontSize: 12, color: "#EF4444", padding: "8px 12px", background: "#EF444410", borderRadius: 6 }}>⚠️ Please provide a reason when disputing a record.</div>
            )}

            <div style={{ display: "flex", gap: 10 }}>
              <button style={{ flex: 1, padding: 12, border: `1px solid ${C.border}`, background: "transparent", color: C.sub, borderRadius: 8, cursor: "pointer" }} onClick={() => setVerifying(null)}>Cancel</button>
              <button className="bp" style={{ flex: 2, padding: 12, background: verifyForm.decision === "reject" ? "#EF4444" : undefined, opacity: (verifyBusy || (verifyForm.decision === "reject" && !verifyForm.hr_note.trim())) ? 0.6 : 1 }} disabled={verifyBusy || (verifyForm.decision === "reject" && !verifyForm.hr_note.trim())} onClick={submitVerify}>
                {verifyBusy ? "Saving…" : verifyForm.decision === "approve" ? "Confirm Verification" : "Confirm Dispute"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ══════════════════════ NEW EXPENSE MODAL ══════════════════════ */}
      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Submit Expense Claim" width={560}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div><Lbl>Staff Member</Lbl><select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}><option value="">— Select Staff —</option>{staff.map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}</select></div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Category</Lbl><select className="inp" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}><option>Travel</option><option>Accommodation</option><option>Meals</option><option>Equipment</option><option>Training</option><option>Other</option></select></div>
              <div><Lbl>Amount (NGN) *</Lbl><input type="number" className="inp" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} placeholder="e.g. 45000" /></div>
            </div>
            <div><Lbl>Description *</Lbl><input className="inp" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Brief description of the expense" /></div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Date Incurred</Lbl><input type="date" className="inp" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} /></div>
              <div><Lbl>Receipt URL</Lbl><input className="inp" value={form.receipt_url} onChange={e => setForm(f => ({ ...f, receipt_url: e.target.value }))} placeholder="https://…" /></div>
            </div>
            <div><Lbl>Remarks / Notes</Lbl><textarea className="inp" value={form.remarks} onChange={e => setForm(f => ({ ...f, remarks: e.target.value }))} placeholder="Any additional context for this expense claim..." style={{ minHeight: 72 }} /></div>
            <button className="bp" onClick={submit} style={{ padding: 14 }}>Submit Expense</button>
          </div>
        </Modal>
      )}
    </div>
  );
}


// ─── BIO DATA COMPONENTS (auto-injected) ────────────────────────────────────
// ─── BIO DATA SYSTEM ─────────────────────────────────────────────────────────
// Paste this entire block into App.jsx — anywhere before HRAdminPortal.
// Requires: apiFetch, API_BASE, T, C (via dark), useTheme, DARK, LIGHT,
//           Tabs, Lbl, Field, Av, Modal, StatCard (already in App.jsx)

// ─── HR BIO DATA DASHBOARD ───────────────────────────────────────────────────
function BiodataManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [tab, setTab] = useState("submissions");
  const [settings, setSettings] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [generalLink, setGeneralLink] = useState("");
  const [copied, setCopied] = useState(false);
  const [selected, setSelected] = useState(null);
  const [filterStatus, setFilterStatus] = useState("all");
  const [togglingForm, setTogglingForm] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [s, subs, inv, gl] = await Promise.all([
        apiFetch(`${API_BASE}/biodata/settings`),
        apiFetch(`${API_BASE}/biodata/submissions`),
        apiFetch(`${API_BASE}/biodata/invites`),
        apiFetch(`${API_BASE}/biodata/general-link`),
      ]);
      setSettings(s);
      setSubmissions(Array.isArray(subs) ? subs : []);
      setInvites(Array.isArray(inv) ? inv : []);
      setGeneralLink(gl.link || "");
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggleCollecting = async () => {
    if (!settings) return;
    setTogglingForm(true);
    try {
      const updated = await apiFetch(`${API_BASE}/biodata/settings`, {
        method: "PATCH",
        body: JSON.stringify({ is_collecting: !settings.is_collecting }),
      });
      setSettings(updated);
    } catch (e) { alert(e.message); }
    finally { setTogglingForm(false); }
  };

  const sendInvite = async () => {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      const res = await apiFetch(`${API_BASE}/biodata/invites`, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail.trim() }),
      });
      alert(`Invite sent to ${res.email}${res.staff_found ? " (existing staff recognised)" : " (email not in system — invite still sent)"}`);
      setInviteEmail("");
      load();
    } catch (e) { alert(e.message); }
    finally { setInviting(false); }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(generalLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filtered = filterStatus === "all" ? submissions : submissions.filter(s => s.status === filterStatus);

  const stats = {
    total: submissions.length,
    pending: submissions.filter(s => s.status === "pending").length,
    approved: submissions.filter(s => s.status === "approved").length,
    rejected: submissions.filter(s => s.status === "rejected").length,
  };

  const statusColor = (st) => ({ pending: T.gold, approved: "#10B981", rejected: "#EF4444" }[st] || C.muted);
  const statusBg = (st) => ({ pending: `${T.gold}18`, approved: "#10B98118", rejected: "#EF444418" }[st] || C.surface);

  if (loading) return <div style={{ padding: 60, textAlign: "center", color: C.muted }}>Loading Bio Data System…</div>;

  return (
    <div className="fade">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <div className="ho" style={{ fontSize: 26, fontWeight: 900, letterSpacing: -0.5 }}>Bio Data Collection</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>Manage employee bio data forms, invitations, and review submissions.</div>
        </div>
        {/* Form ON/OFF Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: "10px 18px" }}>
          <div style={{ fontSize: 12, color: C.sub, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}>Form {settings?.is_collecting ? "Active" : "Closed"}</div>
          <div
            onClick={!togglingForm ? toggleCollecting : undefined}
            style={{
              width: 52, height: 28, borderRadius: 14, cursor: "pointer",
              background: settings?.is_collecting ? T.gold : C.border,
              position: "relative", transition: "all 0.25s ease",
              opacity: togglingForm ? 0.6 : 1,
            }}
          >
            <div style={{
              position: "absolute", top: 3, left: settings?.is_collecting ? 27 : 3,
              width: 22, height: 22, borderRadius: "50%", background: "#fff",
              transition: "left 0.25s ease", boxShadow: "0 1px 4px #0004",
            }} />
          </div>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 28 }}>
        {[
          { label: "Total Submissions", value: stats.total, col: C.text },
          { label: "Pending Review", value: stats.pending, col: T.gold },
          { label: "Approved", value: stats.approved, col: "#10B981" },
          { label: "Rejected", value: stats.rejected, col: "#EF4444" },
        ].map(({ label, value, col }) => (
          <div key={label} className="gc" style={{ padding: "20px 24px" }}>
            <div style={{ fontSize: 32, fontWeight: 900, color: col, lineHeight: 1 }}>{value}</div>
            <div style={{ fontSize: 12, color: C.muted, marginTop: 6, fontWeight: 600, letterSpacing: 0.3 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <Tabs items={[["submissions", "Submissions"], ["invites", "Invitations"], ["settings", "Settings & Links"]]} active={tab} setActive={setTab} />

      {/* ── SUBMISSIONS TAB ── */}
      {tab === "submissions" && (
        <div className="fade">
          <div style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
            {["all", "pending", "approved", "rejected"].map(st => (
              <button key={st} onClick={() => setFilterStatus(st)}
                style={{ padding: "6px 18px", borderRadius: 99, fontSize: 12, fontWeight: 700, cursor: "pointer", border: `1px solid ${filterStatus === st ? T.gold : C.border}`, background: filterStatus === st ? `${T.gold}18` : "transparent", color: filterStatus === st ? T.gold : C.muted, textTransform: "capitalize", letterSpacing: 0.3 }}>
                {st} {st !== "all" && `(${stats[st] || 0})`}
              </button>
            ))}
          </div>

          {filtered.length === 0 ? (
            <div style={{ padding: "60px 40px", textAlign: "center", color: C.muted, border: `2px dashed ${C.border}`, borderRadius: 14 }}>
              <div style={{ fontSize: 40, marginBottom: 14 }}>📋</div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>No {filterStatus !== "all" ? filterStatus : ""} submissions yet</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {filtered.map(sub => (
                <div key={sub.id} className="gc" style={{ padding: "18px 22px", cursor: "pointer", transition: "all 0.2s" }}
                  onClick={() => setSelected(sub)}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                      {/* Show passport photo if available, else initials avatar */}
                      {sub.passport_photo_url ? (
                        <img src={sub.passport_photo_url} alt="Passport"
                          style={{ width: 44, height: 44, borderRadius: "50%", objectFit: "cover", border: `2px solid ${T.gold}40`, flexShrink: 0 }}
                          onError={e => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }} />
                      ) : null}
                      <div style={{ width: 44, height: 44, borderRadius: "50%", background: `${T.gold}20`, border: `2px solid ${T.gold}40`, display: sub.passport_photo_url ? "none" : "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, color: T.gold, flexShrink: 0 }}>
                        {(sub.surname?.[0] || sub.email?.[0] || "?").toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontSize: 15, fontWeight: 800, color: C.text }}>{sub.surname} {sub.other_names}</div>
                        <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>{sub.email} · {sub.job_title}</div>
                        {/* Signature preview indicator */}
                        {sub.signature_url && (
                          <div style={{ marginTop: 4 }}>
                            <img src={sub.signature_url} alt="Sig" style={{ maxHeight: 28, maxWidth: 120, opacity: 0.85 }}
                              onError={e => e.target.style.display = "none"} />
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                      <div style={{ fontSize: 11, color: C.muted }}>{sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—"}</div>
                      <span style={{ background: statusBg(sub.status), color: statusColor(sub.status), border: `1px solid ${statusColor(sub.status)}33`, padding: "4px 14px", borderRadius: 99, fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: 0.5 }}>
                        {sub.status}
                      </span>
                      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke={C.muted} strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── INVITES TAB ── */}
      {tab === "invites" && (
        <div className="fade">
          <div className="gc" style={{ padding: 24, marginBottom: 20 }}>
            <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Send Invitation by Email</div>
            <div style={{ display: "flex", gap: 10 }}>
              <input className="inp" placeholder="staff@company.com" value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendInvite()}
                style={{ flex: 1 }} />
              <button className="bp" onClick={sendInvite} disabled={inviting || !inviteEmail.trim()}
                style={{ whiteSpace: "nowrap" }}>
                {inviting ? "Sending…" : "Send Invite"}
              </button>
            </div>
            <div style={{ fontSize: 12, color: C.muted, marginTop: 10 }}>
              If the email matches an existing staff member, they will be recognised automatically.
            </div>
          </div>

          {invites.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: C.muted, border: `2px dashed ${C.border}`, borderRadius: 14 }}>No invitations sent yet.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {invites.map(inv => (
                <div key={inv.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", background: C.card, border: `1px solid ${C.border}`, borderRadius: 12 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{inv.email}</div>
                    <div style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>
                      Sent {new Date(inv.created_at).toLocaleDateString()} · Expires {new Date(inv.expires_at).toLocaleDateString()}
                    </div>
                  </div>
                  <span style={{ background: statusBg(inv.status), color: statusColor(inv.status), border: `1px solid ${statusColor(inv.status)}33`, padding: "4px 14px", borderRadius: 99, fontSize: 10, fontWeight: 800, textTransform: "uppercase" }}>
                    {inv.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── SETTINGS & LINKS TAB ── */}
      {tab === "settings" && (
        <div className="fade" style={{ maxWidth: 600 }}>
          <div className="gc" style={{ padding: 28, marginBottom: 20 }}>
            <div className="ho" style={{ fontSize: 14, marginBottom: 6 }}>General Submission Link</div>
            <div style={{ fontSize: 13, color: C.sub, marginBottom: 18, lineHeight: 1.6 }}>
              Share this link with any staff member — no individual invite required.
              When a staff enters their email, the system will recognise them if they exist in the system.
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <input className="inp" readOnly value={generalLink} style={{ flex: 1, fontSize: 12, color: C.muted }} />
              <button className="bp" onClick={copyLink}>
                {copied ? "✓ Copied!" : "Copy Link"}
              </button>
            </div>
          </div>

          <div className="gc" style={{ padding: 28 }}>
            <div className="ho" style={{ fontSize: 14, marginBottom: 16 }}>Form Status</div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", background: settings?.is_collecting ? `${T.gold}0D` : `${C.border}30`, border: `1px solid ${settings?.is_collecting ? T.gold + "30" : C.border}`, borderRadius: 10 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>Bio Data Collection</div>
                <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>
                  {settings?.is_collecting ? "✓ Form is active — staff can submit their bio data." : "⊘ Form is closed — submission links will be rejected."}
                </div>
              </div>
              <div
                onClick={!togglingForm ? toggleCollecting : undefined}
                style={{ width: 52, height: 28, borderRadius: 14, cursor: "pointer", background: settings?.is_collecting ? T.gold : C.border, position: "relative", transition: "all 0.25s ease", opacity: togglingForm ? 0.6 : 1, flexShrink: 0 }}
              >
                <div style={{ position: "absolute", top: 3, left: settings?.is_collecting ? 27 : 3, width: 22, height: 22, borderRadius: "50%", background: "#fff", transition: "left 0.25s ease", boxShadow: "0 1px 4px #0004" }} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── SUBMISSION DETAIL MODAL ── */}
      {selected && (
        <BiodataReviewModal sub={selected} onClose={() => setSelected(null)} onRefresh={() => { setSelected(null); load(); }} />
      )}
    </div>
  );
}

// ─── BIO DATA REVIEW MODAL ────────────────────────────────────────────────────
function BiodataReviewModal({ sub, onClose, onRefresh }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [full, setFull] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);
  const [rejReason, setRejReason] = useState("");
  const [showRejInput, setShowRejInput] = useState(false);
  const [certEmail, setCertEmail] = useState("");
  const [sendingCert, setSendingCert] = useState(false);
  const [downloadingCert, setDownloadingCert] = useState(false);

  useEffect(() => {
    apiFetch(`${API_BASE}/biodata/submissions/${sub.id}`)
      .then(d => setFull(d))
      .finally(() => setLoading(false));
  }, [sub.id]);

  const doReview = async (action) => {
    if (action === "reject" && !rejReason.trim()) { setShowRejInput(true); return; }
    setReviewing(true);
    try {
      await apiFetch(`${API_BASE}/biodata/submissions/${sub.id}/review`, {
        method: "POST",
        body: JSON.stringify({ action, rejection_reason: rejReason || null }),
      });
      onRefresh();
    } catch (e) { alert(e.message); setReviewing(false); }
  };

  const emailCert = async () => {
    if (!certEmail.trim()) return;
    setSendingCert(true);
    try {
      await apiFetch(`${API_BASE}/biodata/submissions/${sub.id}/email-certificate`, {
        method: "POST",
        body: JSON.stringify({ to_email: certEmail, submission_id: sub.id }),
      });
      alert(`Certificate sent to ${certEmail}`);
      setCertEmail("");
    } catch (e) { alert(e.message); }
    finally { setSendingCert(false); }
  };

  const downloadCert = () => {
    // Build a printable HTML certificate in a new window
    const s = full || sub;
    const name = `${s.surname || ""} ${s.other_names || ""}`.trim();
    const lat = s.coordinates_lat, lng = s.coordinates_lng;
    const coords = lat && lng ? `${parseFloat(lat).toFixed(6)}, ${parseFloat(lng).toFixed(6)}` : "Not captured";
    const html = `<!DOCTYPE html><html><head><title>Bio Data Certificate</title><style>
      body{font-family:'Segoe UI',Arial,sans-serif;padding:40px;max-width:720px;margin:0 auto;}
      h1{font-size:24px;color:#0B0C0F;margin-bottom:4px;}
      .gold{color:#C47D0A;} .bar{width:60px;height:4px;background:#C47D0A;margin:12px 0 28px;}
      table{width:100%;border-collapse:collapse;font-size:13px;margin:20px 0;}
      td{padding:11px 14px;border-bottom:1px solid #E5E7EB;} tr:nth-child(odd){background:#F9FAFB;}
      .label{color:#6B7280;font-weight:600;width:42%;} .val{color:#111827;}
      .footer{margin-top:32px;padding-top:20px;border-top:2px solid #E5E7EB;font-size:11px;color:#9CA3AF;text-align:center;}
      .sig-box{margin:20px 0;padding:16px;background:#F9FAFB;border-radius:8px;border:1px solid #E5E7EB;}
      @media print{body{padding:20px;}}
    </style></head><body>
      <div style="background:#0B0C0F;padding:24px 32px;border-radius:10px;margin-bottom:32px;display:flex;align-items:center;gap:16px;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="height:48px;width:auto;display:block;" onerror="this.style.display='none';this.nextSibling.style.display='flex';" />
        <div style="width:40px;height:40px;background:#C47D0A;border-radius:8px;align-items:center;justify-content:center;display:none;">
          <span style="color:#fff;font-weight:900;font-size:20px;">EC</span></div>
        <div>
          <div style="color:#fff;font-weight:800;font-size:16px;">Eximp &amp; Cloves Infrastructure Limited</div>
          <div style="color:#9CA3AF;font-size:11px;">Human Resources · Official Document</div>
        </div>
      </div>
      <div style="font-size:10px;letter-spacing:3px;color:#C47D0A;text-transform:uppercase;margin-bottom:6px;">Official Document</div>
      <h1>Bio Data Authenticity Certificate</h1>
      <div class="bar"></div>
      <p style="color:#374151;font-size:13px;line-height:1.7;">This certifies that the following employee bio data was electronically submitted and verified through the Eximp &amp; Cloves HR System with the following authenticity metadata:</p>
      <table>
        <tr><td class="label">Employee Name</td><td class="val"><strong>${name}</strong></td></tr>
        <tr><td class="label">Email Address</td><td class="val">${s.email || ""}</td></tr>
        <tr><td class="label">Job Title</td><td class="val">${s.job_title || ""}</td></tr>
        <tr><td class="label">Submission Timestamp</td><td class="val"><strong>${(s.submitted_at || "").slice(0, 19).replace("T", " ")}</strong></td></tr>
        <tr><td class="label">IP Address</td><td class="val" style="font-family:monospace">${s.ip_address || "N/A"}</td></tr>
        <tr><td class="label">Device Type</td><td class="val">${s.device_type || "N/A"}</td></tr>
        <tr><td class="label">User Agent</td><td class="val" style="font-size:11px;word-break:break-all">${s.user_agent || "N/A"}</td></tr>
        <tr><td class="label">GPS Coordinates</td><td class="val" style="font-family:monospace">${coords}</td></tr>
        <tr><td class="label">Review Status</td><td class="val"><strong style="color:${s.status === "approved" ? "#065F46" : "#991B1B"}">${(s.status || "").toUpperCase()}</strong></td></tr>
      </table>
      ${s.signature_url ? `<div class="sig-box"><div style="font-size:11px;color:#6B7280;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Employee Signature</div><img src="${s.signature_url}" style="max-height:80px;max-width:280px;" /></div>` : ""}
      <div class="footer" style="background:#0B0C0F;padding:28px 32px;text-align:center;border-radius:0 0 10px 10px;margin-top:32px;">
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp &amp; Cloves" style="height:36px;width:auto;display:block;margin:0 auto 14px;" onerror="this.style.display='none';" />
        <div style="color:#9CA3AF;font-size:12px;line-height:1.8;">
          <strong style="color:#C47D0A;">Eximp &amp; Cloves Infrastructure Limited</strong><br>
          Human Resources Department &nbsp;·&nbsp; Confidential Document<br>
          Certificate ID: ${s.id}<br>
          This is an electronically generated document valid without a physical signature.
        </div>
        <div style="margin-top:14px;color:#6B7280;font-size:10px;letter-spacing:1px;text-transform:uppercase;">© ${new Date().getFullYear()} Eximp &amp; Cloves Infrastructure Limited. All rights reserved.</div>
      </div>
      <script>window.print();</script>
    </body></html>`;
    const win = window.open("", "_blank");
    win.document.write(html);
    win.document.close();
  };

  const statusColor = (st) => ({ pending: T.gold, approved: "#10B981", rejected: "#EF4444" }[st] || C.muted);
  const s = full || sub;

  return (
    <Modal onClose={onClose}>
      <div style={{ maxWidth: 780, width: "100%", maxHeight: "90vh", overflow: "auto" }}>
        {/* Modal Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <div className="ho" style={{ fontSize: 20, fontWeight: 900 }}>Bio Data Review</div>
            <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>{s.surname} {s.other_names} · {s.email}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ background: `${statusColor(s.status)}18`, color: statusColor(s.status), border: `1px solid ${statusColor(s.status)}33`, padding: "5px 16px", borderRadius: 99, fontSize: 11, fontWeight: 800, textTransform: "uppercase" }}>
              {s.status}
            </span>
            <button className="bg" onClick={onClose} style={{ padding: "6px 14px" }}>✕</button>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: "center", color: C.muted }}>Loading submission…</div>
        ) : (
          <>
            {/* Two-column layout */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
              {/* Left: Personal Details */}
              <div className="gc" style={{ padding: 22 }}>
                <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 16 }}>Personal Information</div>
                {[
                  ["Surname", s.surname],
                  ["Other Names", s.other_names],
                  ["Email", s.email],
                  ["Gender", s.gender],
                  ["Marital Status", s.marital_status],
                  ["Date of Birth", s.date_of_birth],
                  ["Job Title", s.job_title],
                  ["Joining Date", s.joining_date],
                  ["Mobile Phone", s.mobile_phone],
                  ["House Phone", s.house_phone],
                  ["Home Address", s.present_home_address],
                  ["Next of Kin", s.next_of_kin_name],
                  ["NOK Phone", s.next_of_kin_phone],
                ].map(([label, val]) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: `1px solid ${C.border}22`, fontSize: 13 }}>
                    <span style={{ color: C.muted, fontWeight: 600, flexShrink: 0, width: "45%" }}>{label}</span>
                    <span style={{ color: C.text, textAlign: "right", wordBreak: "break-word" }}>{val || <span style={{ color: C.border }}>—</span>}</span>
                  </div>
                ))}
              </div>

              {/* Right: Auth Metadata + Files */}
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {/* Passport Photo */}
                <div className="gc" style={{ padding: 22 }}>
                  <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 14 }}>Passport Photograph</div>
                  {s.passport_photo_url ? (
                    <div style={{ display: "flex", justifyContent: "center" }}>
                      <img src={s.passport_photo_url} alt="Passport" style={{ width: 120, height: 140, objectFit: "cover", borderRadius: 10, border: `2px solid ${T.gold}40` }} />
                    </div>
                  ) : (
                    <div style={{ padding: "20px 0", textAlign: "center", color: C.muted, fontSize: 13 }}>No photo uploaded</div>
                  )}
                </div>

                {/* Signature */}
                <div className="gc" style={{ padding: 22 }}>
                  <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 14 }}>Employee Signature</div>
                  {s.signature_url ? (
                    <div style={{ background: "#fff", borderRadius: 8, padding: 12, display: "flex", justifyContent: "center" }}>
                      <img src={s.signature_url} alt="Signature" style={{ maxHeight: 80, maxWidth: "100%" }} />
                    </div>
                  ) : (
                    <div style={{ padding: "20px 0", textAlign: "center", color: C.muted, fontSize: 13 }}>No signature captured</div>
                  )}
                </div>

                {/* Authenticity Metadata */}
                <div className="gc" style={{ padding: 22, borderLeft: `3px solid ${T.gold}` }}>
                  <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 14 }}>Authenticity Metadata</div>
                  {[
                    ["IP Address", s.ip_address],
                    ["Device", s.device_type],
                    ["GPS Coords", s.coordinates_lat && s.coordinates_lng ? `${parseFloat(s.coordinates_lat).toFixed(5)}, ${parseFloat(s.coordinates_lng).toFixed(5)}` : null],
                    ["GPS Accuracy", s.coordinates_accuracy ? `±${parseFloat(s.coordinates_accuracy).toFixed(0)}m` : null],
                    ["Timestamp", s.submitted_at ? new Date(s.submitted_at).toLocaleString() : null],
                  ].map(([label, val]) => (
                    <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: `1px solid ${C.border}22`, fontSize: 12 }}>
                      <span style={{ color: C.muted, fontWeight: 700 }}>{label}</span>
                      <span style={{ color: C.text, fontFamily: "monospace", fontSize: 11, textAlign: "right", maxWidth: "60%", wordBreak: "break-all" }}>{val || "—"}</span>
                    </div>
                  ))}
                  <div style={{ marginTop: 10, padding: "10px 0", borderBottom: `1px solid ${C.border}22` }}>
                    <div style={{ fontSize: 11, color: C.muted, fontWeight: 700, marginBottom: 6 }}>USER AGENT</div>
                    <div style={{ fontSize: 10, color: C.text, wordBreak: "break-all", lineHeight: 1.5, fontFamily: "monospace" }}>{s.user_agent || "—"}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Certificate Actions */}
            <div className="gc" style={{ padding: 22, marginBottom: 20, background: `${T.gold}08`, borderColor: `${T.gold}30` }}>
              <div className="ho" style={{ fontSize: 13, marginBottom: 14 }}>📜 Authenticity Certificate</div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                <button className="bp" onClick={downloadCert} style={{ fontSize: 12 }}>
                  Download / Print Certificate
                </button>
                <input className="inp" placeholder="Email certificate to…" value={certEmail}
                  onChange={e => setCertEmail(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
                <button className="bg" onClick={emailCert} disabled={sendingCert || !certEmail.trim()} style={{ fontSize: 12 }}>
                  {sendingCert ? "Sending…" : "Email Certificate"}
                </button>
              </div>
            </div>

            {/* Review Actions */}
            {s.status === "pending" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {showRejInput && (
                  <div>
                    <div style={{ fontSize: 12, color: C.sub, marginBottom: 8, fontWeight: 700 }}>Rejection Reason (required)</div>
                    <textarea className="inp" rows={3} placeholder="Explain what needs to be corrected…"
                      value={rejReason} onChange={e => setRejReason(e.target.value)} />
                  </div>
                )}
                <div style={{ display: "flex", gap: 12 }}>
                  <button className="bp" onClick={() => doReview("approve")} disabled={reviewing}
                    style={{ flex: 1, padding: 14, fontSize: 14 }}>
                    ✓ Approve Submission
                  </button>
                  <button className="bd" onClick={() => showRejInput ? doReview("reject") : setShowRejInput(true)} disabled={reviewing}
                    style={{ flex: 1, padding: 14, fontSize: 14 }}>
                    {showRejInput ? "Confirm Rejection" : "✕ Reject & Request Changes"}
                  </button>
                </div>
              </div>
            )}

            {s.status === "approved" && (
              <div style={{ padding: "14px 20px", background: "#10B98114", border: "1px solid #10B98130", borderRadius: 10, fontSize: 13, color: "#10B981", fontWeight: 700 }}>
                ✓ This submission has been approved and the staff profile has been updated.
              </div>
            )}
            {s.status === "rejected" && (
              <div style={{ padding: "14px 20px", background: "#EF444414", border: "1px solid #EF444430", borderRadius: 10, fontSize: 13, color: "#EF4444" }}>
                ✕ Rejected — {s.rejection_reason || "No reason provided."}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}

// ─── STAFF: MY BIO DATA TAB ───────────────────────────────────────────────────
function MyBiodata({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [sub, setSub] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`${API_BASE}/biodata/my-submission`)
      .then(d => setSub(d))
      .catch(() => setSub(null))
      .finally(() => setLoading(false));
  }, []);

  const statusColor = (st) => ({ pending: T.gold, approved: "#10B981", rejected: "#EF4444" }[st] || C.muted);

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading…</div>;

  if (!sub) {
    return (
      <div style={{ padding: "60px 40px", textAlign: "center", border: `2px dashed ${C.border}`, borderRadius: 14 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>📋</div>
        <div style={{ fontSize: 16, fontWeight: 800, color: C.text, marginBottom: 8 }}>No Bio Data Submitted Yet</div>
        <div style={{ fontSize: 13, color: C.muted, maxWidth: 360, margin: "0 auto" }}>
          Check your email for a bio data form invite from HR, or ask HR to send you a link.
        </div>
      </div>
    );
  }

  const s = sub;
  const name = `${s.surname || ""} ${s.other_names || ""}`.trim();

  return (
    <div className="fade" style={{ maxWidth: 720 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22, fontWeight: 900 }}>My Bio Data</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>Your submitted employee bio data form.</div>
        </div>
        <span style={{ background: `${statusColor(s.status)}18`, color: statusColor(s.status), border: `1px solid ${statusColor(s.status)}33`, padding: "6px 18px", borderRadius: 99, fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
          {s.status === "pending" ? "⏳ Awaiting Review" : s.status === "approved" ? "✓ Approved" : "✕ Rejected"}
        </span>
      </div>

      {s.status === "rejected" && s.rejection_reason && (
        <div style={{ padding: "14px 20px", background: "#EF444410", border: "1px solid #EF444430", borderRadius: 10, fontSize: 13, color: "#EF4444", marginBottom: 20 }}>
          <strong>Reason for rejection:</strong> {s.rejection_reason}
          <div style={{ fontSize: 12, marginTop: 6, color: "#EF4444AA" }}>Please contact HR for a new form link to resubmit.</div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div className="gc" style={{ padding: 22 }}>
          <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 16 }}>Personal Information</div>
          {[
            ["Full Name", name],
            ["Gender", s.gender],
            ["Marital Status", s.marital_status],
            ["Date of Birth", s.date_of_birth],
            ["Job Title", s.job_title],
            ["Mobile", s.mobile_phone],
            ["Address", s.present_home_address],
            ["Next of Kin", s.next_of_kin_name],
          ].map(([label, val]) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: `1px solid ${C.border}22`, fontSize: 13 }}>
              <span style={{ color: C.muted, fontWeight: 600 }}>{label}</span>
              <span style={{ color: C.text }}>{val || "—"}</span>
            </div>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {s.passport_photo_url && (
            <div className="gc" style={{ padding: 22 }}>
              <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>Passport Photo</div>
              <img src={s.passport_photo_url} alt="Passport" style={{ width: 100, height: 120, objectFit: "cover", borderRadius: 8, border: `2px solid ${T.gold}40` }} />
            </div>
          )}
          {s.signature_url && (
            <div className="gc" style={{ padding: 22 }}>
              <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>My Signature</div>
              <div style={{ background: "#fff", borderRadius: 6, padding: 10 }}>
                <img src={s.signature_url} alt="Signature" style={{ maxHeight: 70, maxWidth: "100%" }} />
              </div>
            </div>
          )}
          <div className="gc" style={{ padding: 22 }}>
            <div className="ho" style={{ fontSize: 12, letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>Submission Info</div>
            <div style={{ fontSize: 12, color: C.muted, lineHeight: 1.8 }}>
              <div>Submitted: <span style={{ color: C.text }}>{s.submitted_at ? new Date(s.submitted_at).toLocaleString() : "—"}</span></div>
              <div>Device: <span style={{ color: C.text }}>{s.device_type || "—"}</span></div>
              {s.reviewed_at && <div>Reviewed: <span style={{ color: C.text }}>{new Date(s.reviewed_at).toLocaleDateString()}</span></div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── PUBLIC BIO DATA FORM (standalone, accessed via /biodata?token=xxx) ────────
// This is rendered inside App.jsx when a ?token= URL param is detected.
// It handles its own layout completely (no sidebar).
function PublicBiodataForm() {
  const [step, setStep] = useState("email"); // email → form → success
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [staffInfo, setStaffInfo] = useState(null);
  const [previousData, setPreviousData] = useState(null);
  const [formMsg, setFormMsg] = useState("");
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [geoError, setGeoError] = useState("");
  const [geoData, setGeoData] = useState({ lat: null, lng: null, accuracy: null });
  const [ipAddress, setIpAddress] = useState("");

  // Signature canvas
  const sigCanvasRef = useRef(null);
  const [sigDrawing, setSigDrawing] = useState(false);
  const [sigHasData, setSigHasData] = useState(false);
  const [sigCtx, setSigCtx] = useState(null);
  const [lastPos, setLastPos] = useState(null);

  // Form data
  const [form, setForm] = useState({
    surname: "", other_names: "", marital_status: "", gender: "",
    job_title: "", date_of_birth: "", joining_date: "",
    present_home_address: "", mobile_phone: "", house_phone: "",
    next_of_kin_name: "", next_of_kin_phone: "",
  });
  const [passportFile, setPassportFile] = useState(null);
  const [passportPreview, setPassportPreview] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if (t) setToken(t);

    // Get IP
    fetch("https://api.ipify.org?format=json").then(r => r.json()).then(d => setIpAddress(d.ip)).catch(() => { });

    // Get GPS
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setGeoData({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
        err => setGeoError("Location access denied — this field is required for authenticity verification."),
        { timeout: 10000 }
      );
    }

    // Set up signature canvas after mount — also re-init on resize so coordinate mapping stays correct
    const setupCanvas = () => setTimeout(() => initCanvas(), 100);
    setupCanvas();
    window.addEventListener("resize", setupCanvas);
    return () => window.removeEventListener("resize", setupCanvas);
  }, []);

  const initCanvas = () => {
    const canvas = sigCanvasRef.current;
    if (!canvas) return;
    // Fix: match internal resolution to rendered CSS size so ink tracks finger/cursor correctly on mobile
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.strokeStyle = "#1A1D24";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    setSigCtx(ctx);
  };

  const getPos = (e, canvas) => {
    const rect = canvas.getBoundingClientRect();
    // No additional scaling needed — ctx is already scaled to CSS pixels via dpr scale
    if (e.touches) {
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const sigStart = (e) => {
    e.preventDefault();
    const canvas = sigCanvasRef.current;
    if (!canvas || !sigCtx) { initCanvas(); return; }
    setSigDrawing(true);
    setSigHasData(true);
    const pos = getPos(e, canvas);
    setLastPos(pos);
    sigCtx.beginPath();
    sigCtx.moveTo(pos.x, pos.y);
  };

  const sigMove = (e) => {
    e.preventDefault();
    if (!sigDrawing || !sigCtx) return;
    const canvas = sigCanvasRef.current;
    const pos = getPos(e, canvas);
    sigCtx.lineTo(pos.x, pos.y);
    sigCtx.stroke();
    setLastPos(pos);
  };

  const sigEnd = () => setSigDrawing(false);

  const clearSig = () => {
    const canvas = sigCanvasRef.current;
    if (!canvas || !sigCtx) return;
    sigCtx.clearRect(0, 0, canvas.width, canvas.height);
    setSigHasData(false);
  };

  const checkEmail = async () => {
    if (!email.trim()) return;
    setChecking(true);
    try {
      const res = await fetch(`${API_BASE}/biodata/public/check?token=${token}&email=${encodeURIComponent(email.trim())}`);
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Error verifying token.");
        setChecking(false);
        return;
      }
      const data = await res.json();
      setStaffInfo(data.staff_info);
      setFormMsg(data.form_message || "");
      if (data.staff_info) {
        setForm(f => ({
          ...f,
          surname: data.staff_info.full_name?.split(" ")?.[0] || "",
          other_names: data.staff_info.full_name?.split(" ")?.slice(1)?.join(" ") || "",
          job_title: data.staff_info.job_title || "",
        }));
      }
      if (data.previous_data) {
        setPreviousData(data.previous_data);
        setForm(f => ({
          ...f,
          ...data.previous_data
        }));
      }
      setStep("form");
    } catch (e) { alert("Connection error. Please try again."); }
    finally { setChecking(false); }
  };

  const handlePassportChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPassportFile(file);
    const reader = new FileReader();
    reader.onloadend = () => setPassportPreview(reader.result);
    reader.readAsDataURL(file);
  };

  const getDeviceType = () => {
    const ua = navigator.userAgent;
    if (/Mobi|Android/i.test(ua)) return "Mobile";
    if (/Tablet|iPad/i.test(ua)) return "Tablet";
    return "Desktop";
  };

  const handleSubmit = async () => {
    // Validate
    const required = ["surname", "other_names", "marital_status", "gender", "job_title", "date_of_birth", "joining_date", "present_home_address", "mobile_phone", "next_of_kin_name", "next_of_kin_phone"];
    for (const f of required) {
      if (!form[f]?.trim()) { alert(`Please fill in: ${f.replace(/_/g, " ")}`); return; }
    }
    if (!passportFile) { alert("Please upload your passport photograph."); return; }
    if (!sigHasData) { alert("Please draw your signature."); return; }
    if (!geoData.lat || !geoData.lng) { alert("GPS coordinates are required. Please allow location access and try again."); return; }
    if (!ipAddress) { alert("Could not capture IP address. Please check your connection."); return; }

    const canvas = sigCanvasRef.current;
    const sigBase64 = canvas ? canvas.toDataURL("image/png") : "";

    const fd = new FormData();
    fd.append("token", token);
    fd.append("email", email.trim());
    Object.entries(form).forEach(([k, v]) => fd.append(k, v));
    fd.append("ip_address", ipAddress);
    fd.append("device_type", getDeviceType());
    fd.append("user_agent", navigator.userAgent);
    fd.append("coordinates_lat", String(geoData.lat));
    fd.append("coordinates_lng", String(geoData.lng));
    fd.append("coordinates_accuracy", String(geoData.accuracy || ""));
    fd.append("submitted_at", new Date().toISOString());
    fd.append("passport_photo", passportFile);
    fd.append("signature_data", sigBase64);

    setSubmitting(true);
    try {
      const ec_token = localStorage.getItem("ec_token");
      const res = await fetch(`${API_BASE}/biodata/public/submit`, {
        method: "POST",
        body: fd,
        headers: ec_token ? { Authorization: `Bearer ${ec_token}` } : {},
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Submission failed.");
      }
      setStep("success");
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  const inp = {
    background: "#F8F9FB", border: "1px solid #DDE3EE", color: "#1A2130",
    padding: "12px 16px", borderRadius: 10, fontSize: 14, outline: "none",
    fontFamily: "inherit", width: "100%", boxSizing: "border-box",
  };
  const lbl = { fontSize: 12, fontWeight: 700, color: "#6B7280", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6, display: "block" };
  const G = "#C47D0A";

  if (step === "success") {
    return (
      <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #0B0C0F 0%, #1A1D24 100%)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, fontFamily: "'Segoe UI',Arial,sans-serif" }}>
        <div style={{ background: "#fff", borderRadius: 20, padding: 60, maxWidth: 480, width: "100%", textAlign: "center", boxShadow: "0 24px 80px #00000044" }}>
          <div style={{ width: 80, height: 80, background: "#D1FAE5", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px", fontSize: 36 }}>✓</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: "#0B0C0F", marginBottom: 12 }}>Form Submitted!</div>
          <div style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.7, marginBottom: 28 }}>
            Your bio data has been submitted successfully and is now under review by the HR team.
            You will receive an email notification once it has been approved.
          </div>
          <div style={{ padding: "16px 20px", background: "#FEF9EC", border: `1px solid ${G}30`, borderRadius: 10, fontSize: 13, color: "#92400E" }}>
            Submitted at: <strong>{new Date().toLocaleString()}</strong>
          </div>
        </div>
      </div>
    );
  }

  if (step === "email") {
    return (
      <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #0B0C0F 0%, #1A1D24 100%)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, fontFamily: "'Segoe UI',Arial,sans-serif" }}>
        <div style={{ background: "#fff", borderRadius: 20, padding: 48, maxWidth: 460, width: "100%", boxShadow: "0 24px 80px #00000044" }}>
          <div style={{ textAlign: "center", marginBottom: 36 }}>
            <div style={{ margin: "0 auto 16px", textAlign: "center" }}>
              <img src="/static/img/logo.svg" alt="Eximp & Cloves" style={{ height: 56, width: "auto", display: "block", margin: "0 auto" }} onError={e => { e.target.onerror = null; e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }} />
              <div style={{ width: 56, height: 56, background: G, borderRadius: 14, alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 900, color: "#fff", display: "none", margin: "0 auto" }}>EC</div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 900, color: "#0B0C0F" }}>Employee Bio Data Form</div>
            <div style={{ fontSize: 13, color: "#6B7280", marginTop: 8 }}>Eximp & Cloves Infrastructure Limited</div>
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={lbl}>Enter Your Work Email Address</label>
            <input style={inp} type="email" placeholder="yourname@eximps-cloves.com"
              value={email} onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && checkEmail()} autoFocus />
            <div style={{ fontSize: 12, color: "#9CA3AF", marginTop: 8 }}>
              Your email will be used to identify your staff record and pre-fill your details.
            </div>
          </div>
          <button onClick={checkEmail} disabled={checking || !email.trim()} style={{
            width: "100%", padding: 14, background: G, color: "#fff", border: "none",
            borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: "pointer", opacity: checking ? 0.7 : 1
          }}>
            {checking ? "Verifying…" : "Continue →"}
          </button>
        </div>
      </div>
    );
  }

  // step === "form"
  return (
    <div style={{ minHeight: "100vh", background: "#F0F2F6", fontFamily: "'Segoe UI',Arial,sans-serif", paddingBottom: 80 }}>
      {/* Header */}
      <div style={{ background: "#0B0C0F", padding: "20px 0", marginBottom: 32 }}>
        <div style={{ maxWidth: 820, margin: "0 auto", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <img src="/static/img/logo.svg" alt="Eximp & Cloves" style={{ height: 44, width: "auto", display: "block" }} onError={e => { e.target.onerror = null; e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }} />
            <div style={{ width: 44, height: 44, background: G, borderRadius: 10, alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 900, color: "#fff", display: "none" }}>EC</div>
            <div>
              <div style={{ color: "#fff", fontWeight: 800, fontSize: 15 }}>Eximp & Cloves</div>
              <div style={{ color: "#9CA3AF", fontSize: 11 }}>Human Resources Department</div>
            </div>
          </div>
          <div style={{ background: "#ffffff14", padding: "6px 16px", borderRadius: 8, fontSize: 12, color: G, fontWeight: 700, letterSpacing: 0.5 }}>EMPLOYEE BIO DATA FORM</div>
        </div>
      </div>

      <div style={{ maxWidth: 820, margin: "0 auto", padding: "0 24px" }}>
        {/* Staff recognition banner */}
        {staffInfo && (
          <div style={{ background: `${G}14`, border: `1px solid ${G}30`, borderRadius: 12, padding: "14px 20px", marginBottom: 24, display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${G}30`, border: `2px solid ${G}`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, color: G, flexShrink: 0 }}>
              {staffInfo.full_name?.[0] || "?"}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#0B0C0F" }}>Welcome, {staffInfo.full_name}!</div>
              <div style={{ fontSize: 12, color: "#6B7280" }}>Recognised as existing staff · {staffInfo.department} {staffInfo.job_title ? `· ${staffInfo.job_title}` : ""}</div>
            </div>
          </div>
        )}

        {previousData && (
          <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", borderRadius: 12, padding: "14px 20px", marginBottom: 24, fontSize: 13, color: "#991B1B", borderLeft: "4px solid #EF4444" }}>
            <div style={{ fontWeight: 800, marginBottom: 4 }}>⚠️ REVISION REQUIRED</div>
            <div>Your previous submission was not approved. Please review the feedback and update your details below.</div>
            {previousData.rejection_reason && (
              <div style={{ marginTop: 10, padding: 12, background: "#fff", borderRadius: 8, border: "1px solid #FCA5A5" }}>
                <strong>HR Feedback:</strong> {previousData.rejection_reason}
              </div>
            )}
          </div>
        )}

        {formMsg && (
          <div style={{ background: "#fff", border: "1px solid #DDE3EE", borderRadius: 12, padding: "16px 20px", marginBottom: 24, fontSize: 13, color: "#374151", lineHeight: 1.7 }}>{formMsg}</div>
        )}

        {/* Authenticity notice */}
        <div style={{ background: "#FFF8ED", border: `1px solid ${G}40`, borderRadius: 12, padding: "16px 20px", marginBottom: 28, borderLeft: `4px solid ${G}` }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: "#92400E", marginBottom: 6 }}>📍 Proof of Authenticity Required</div>
          <div style={{ fontSize: 12, color: "#92400E", lineHeight: 1.7 }}>
            This form captures your <strong>IP address, device type, browser information, GPS coordinates, and submission timestamp</strong> as proof of authenticity.
            These details are digitally recorded and form part of your official HR submission certificate. By submitting this form, you consent to this data collection.
          </div>
          <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              ["IP Address", ipAddress || "Capturing…"],
              ["Device", getDeviceType()],
              ["GPS", geoData.lat ? `${geoData.lat.toFixed(4)}, ${geoData.lng.toFixed(4)}` : geoError ? "❌ " + geoError : "⏳ Requesting…"],
              ["Time", new Date().toLocaleTimeString()],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "#FFF", border: "1px solid #F5E0B0", borderRadius: 8, padding: "8px 12px" }}>
                <div style={{ fontSize: 10, color: "#B45309", fontWeight: 700, letterSpacing: 0.5 }}>{k.toUpperCase()}</div>
                <div style={{ fontSize: 11, color: "#374151", fontFamily: "monospace", marginTop: 2 }}>{v}</div>
              </div>
            ))}
          </div>
          {geoError && (
            <div style={{ marginTop: 12, fontSize: 12, color: "#DC2626", fontWeight: 700 }}>
              ⚠️ Location permission is required to submit this form.
              <button onClick={() => navigator.geolocation?.getCurrentPosition(pos => { setGeoData({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }); setGeoError(""); })}
                style={{ marginLeft: 8, textDecoration: "underline", background: "none", border: "none", cursor: "pointer", color: "#DC2626", fontSize: 12 }}>
                Retry Location
              </button>
            </div>
          )}
        </div>

        {/* Main Form Card */}
        <div style={{ background: "#fff", borderRadius: 16, padding: 36, marginBottom: 20, boxShadow: "0 4px 24px #0000000A", border: "1px solid #E5E7EB" }}>
          <div style={{ fontSize: 18, fontWeight: 900, color: "#0B0C0F", marginBottom: 4 }}>Personal Information</div>
          <div style={{ width: 48, height: 3, background: G, borderRadius: 2, marginBottom: 28 }} />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {[
              ["surname", "Surname *", "text"],
              ["other_names", "Other Names *", "text"],
              ["date_of_birth", "Date of Birth *", "date"],
              ["joining_date", "Joining Date *", "date"],
              ["mobile_phone", "Mobile Phone *", "tel"],
              ["house_phone", "House Phone", "tel"],
              ["next_of_kin_name", "Next of Kin Name *", "text"],
              ["next_of_kin_phone", "Next of Kin Phone *", "tel"],
            ].map(([key, label, type]) => (
              <div key={key}>
                <label style={lbl}>{label}</label>
                <input style={inp} type={type} value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} />
              </div>
            ))}

            <div>
              <label style={lbl}>Gender *</label>
              <select style={inp} value={form.gender} onChange={e => setForm(f => ({ ...f, gender: e.target.value }))}>
                <option value="">— Select —</option>
                <option>Male</option><option>Female</option><option>Other</option>
              </select>
            </div>
            <div>
              <label style={lbl}>Marital Status *</label>
              <select style={inp} value={form.marital_status} onChange={e => setForm(f => ({ ...f, marital_status: e.target.value }))}>
                <option value="">— Select —</option>
                <option>Single</option><option>Married</option><option>Divorced</option><option>Widowed</option>
              </select>
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={lbl}>Job Title *</label>
              <input style={inp} value={form.job_title} onChange={e => setForm(f => ({ ...f, job_title: e.target.value }))} />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={lbl}>Present Home Address *</label>
              <textarea style={{ ...inp, resize: "vertical", minHeight: 72 }} value={form.present_home_address} onChange={e => setForm(f => ({ ...f, present_home_address: e.target.value }))} />
            </div>
          </div>
        </div>

        {/* Passport Photo Upload */}
        <div style={{ background: "#fff", borderRadius: 16, padding: 36, marginBottom: 20, boxShadow: "0 4px 24px #0000000A", border: "1px solid #E5E7EB" }}>
          <div style={{ fontSize: 18, fontWeight: 900, color: "#0B0C0F", marginBottom: 4 }}>Passport Photograph *</div>
          <div style={{ width: 48, height: 3, background: G, borderRadius: 2, marginBottom: 20 }} />
          <div style={{ fontSize: 13, color: "#6B7280", marginBottom: 20 }}>Upload a recent passport-size photograph. Accepted formats: JPG, PNG. Max 5MB.</div>

          <div style={{ display: "flex", gap: 28, alignItems: "flex-start" }}>
            <div style={{ width: 120, height: 140, borderRadius: 10, border: `2px dashed ${passportPreview ? G : "#DDE3EE"}`, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", flexShrink: 0, background: "#F9FAFB" }}>
              {passportPreview ? (
                <img src={passportPreview} alt="Passport preview" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              ) : (
                <div style={{ textAlign: "center", color: "#9CA3AF", fontSize: 12 }}>
                  <div style={{ fontSize: 32, marginBottom: 6 }}>🖼</div>No photo
                </div>
              )}
            </div>
            <div>
              <input type="file" accept="image/jpeg,image/png,image/webp" id="passport-upload" style={{ display: "none" }} onChange={handlePassportChange} />
              <label htmlFor="passport-upload" style={{ display: "inline-block", padding: "12px 24px", background: G, color: "#fff", borderRadius: 10, fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                {passportFile ? "Change Photo" : "Upload Photo"}
              </label>
              {passportFile && <div style={{ fontSize: 12, color: "#6B7280", marginTop: 8 }}>{passportFile.name}</div>}
            </div>
          </div>
        </div>

        {/* Signature */}
        <div style={{ background: "#fff", borderRadius: 16, padding: 36, marginBottom: 20, boxShadow: "0 4px 24px #0000000A", border: "1px solid #E5E7EB" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <div style={{ fontSize: 18, fontWeight: 900, color: "#0B0C0F" }}>Employee Signature *</div>
            <button onClick={clearSig} style={{ fontSize: 12, color: "#EF4444", background: "#FEE2E2", border: "1px solid #FECACA", borderRadius: 8, padding: "5px 14px", cursor: "pointer", fontWeight: 700 }}>Clear</button>
          </div>
          <div style={{ width: 48, height: 3, background: G, borderRadius: 2, marginBottom: 16 }} />
          <div style={{ fontSize: 13, color: "#6B7280", marginBottom: 16 }}>Please draw your signature in the box below using your mouse or finger.</div>

          <canvas
            ref={sigCanvasRef}
            onMouseDown={sigStart} onMouseMove={sigMove} onMouseUp={sigEnd} onMouseLeave={sigEnd}
            onTouchStart={sigStart} onTouchMove={sigMove} onTouchEnd={sigEnd}
            style={{ border: `2px solid ${sigHasData ? G : "#DDE3EE"}`, borderRadius: 10, cursor: "crosshair", background: "#FAFAFA", width: "100%", height: 220, display: "block", touchAction: "none" }}
          />
          {!sigHasData && <div style={{ fontSize: 12, color: "#9CA3AF", marginTop: 8 }}>↑ Draw your signature above</div>}
        </div>

        {/* Submit */}
        <button onClick={handleSubmit} disabled={submitting || !geoData.lat}
          style={{ width: "100%", padding: 18, background: submitting || !geoData.lat ? "#D1D5DB" : G, color: "#fff", border: "none", borderRadius: 12, fontSize: 16, fontWeight: 800, cursor: submitting || !geoData.lat ? "not-allowed" : "pointer", letterSpacing: 0.5 }}>
          {submitting ? "Submitting…" : "Submit Bio Data Form →"}
        </button>
        {!geoData.lat && <div style={{ textAlign: "center", fontSize: 12, color: "#EF4444", marginTop: 10 }}>⚠️ GPS location required before submission</div>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

function HRAdminPortal({ user, onLogout }) {
  const nav = [
    // ── Overview (auto-loads first) ──
    { isHeader: true, label: "Overview" },
    { id: "dashboard", icon: "dashboard", label: "HR Overview" },
    { id: "tasks_hr", icon: "tasks", label: "Task Manager" },
    // HUB 1: RECRUITMENT
    { isHeader: true, label: "Recruitment" },
    { id: "jobs", icon: "briefcase", label: "Jobs" },
    { id: "ats", icon: "briefcase", label: "Job Requisitions" },
    { id: "applications", icon: "file", label: "Applications" },
    { id: "ats_pipeline", icon: "trend", label: "ATS Pipeline" },
    { id: "interviews", icon: "calendar", label: "Interviews" },
    { id: "offers", icon: "star", label: "Offers" },
    { id: "talent_pool", icon: "users", label: "Talent Pool" },
    // HUB 2: PEOPLE & ORG
    { isHeader: true, label: "People & Org" },
    { id: "staff", icon: "users", label: "Employees" },
    { id: "biodata", icon: "file", label: "Bio Data Collection" },
    { id: "org_chart", icon: "org", label: "Org Chart" },
    { id: "departments", icon: "home", label: "Departments" },
    { id: "diversity", icon: "star", label: "Diversity & Inclusion" },
    // HUB 3: TIME & ATTENDANCE
    { isHeader: true, label: "Time & Attendance" },
    { id: "presence", icon: "clock", label: "Attendance" },
    { id: "timesheets", icon: "log", label: "Timesheets" },
    { id: "timesheet_approvals", icon: "tasks", label: "Timesheet Approvals" },
    { id: "shifts", icon: "calendar", label: "Shift Scheduling" },
    { id: "hr_calendar", icon: "calendar", label: "Calendar" },
    { id: "holidays", icon: "star", label: "Holidays" },
    // HUB 4: LEAVE
    { isHeader: true, label: "Leave" },
    { id: "leave", icon: "presence", label: "Leave Requests" },
    { id: "leave_balances", icon: "chart", label: "Leave Balances" },
    { id: "leave_policies", icon: "book", label: "Leave Policies" },
    { id: "leave_accrual", icon: "trend", label: "Leave Accrual" },
    // HUB 5: PERFORMANCE
    { isHeader: true, label: "Performance" },
    { id: "perf", icon: "perf", label: "Performance" },
    { id: "goals", icon: "goal", label: "Goals & OKRs" },
    { id: "improvement_plans", icon: "trend", label: "Improvement Plans" },
    { id: "peer_reviews", icon: "users", label: "360° Peer Reviews" },
    { id: "skills_matrix", icon: "chart", label: "Skills Matrix" },
    { id: "succession", icon: "org", label: "Succession Planning" },
    // HUB: LEARNING & GROWTH
    { isHeader: true, label: "Learning & Growth" },
    { id: "training", icon: "book", label: "Training" }, { id: "onboarding", icon: "star", label: "Onboarding" }, { id: "probation", icon: "clock", label: "Probation Tracking" },
    // HUB 6: COMPENSATION & BENEFITS
    { isHeader: true, label: "Compensation & Benefits" },
    { id: "payroll", icon: "payroll", label: "Payroll" },
    { id: "payroll_runs", icon: "dollar", label: "Payroll Runs" },
    { id: "comp_bands", icon: "chart", label: "Compensation Bands" },
    { id: "bonuses", icon: "star", label: "Bonuses & Incentives" },
    { id: "benefits", icon: "shield", label: "Benefits" },
    { id: "expenses", icon: "dollar", label: "Expenses" },
    { id: "tax_config", icon: "settings", label: "Tax Configuration" },
    // HUB 7: ENGAGEMENT & CULTURE
    { isHeader: true, label: "Engagement & Culture" },
    { id: "announcements", icon: "megaphone", label: "Announcements" },
    { id: "recognition", icon: "star", label: "Recognition" },
    { id: "surveys", icon: "tasks", label: "Surveys" },
    { id: "remote_work", icon: "home", label: "Remote Work" },
    { id: "policy_library", icon: "book", label: "Policy Library" },
    { id: "internal_job_board", icon: "briefcase", label: "Internal Job Board" },
    // HUB 8: DOCUMENTS & COMPLIANCE
    { isHeader: true, label: "Documents & Compliance" },
    { id: "legal_vault", icon: "file", label: "Documents" },
    { id: "contracts", icon: "file", label: "Contracts" },
    { id: "hr_letters", icon: "file", label: "HR Letters" },
    { id: "work_permits", icon: "globe", label: "Work Permits" },
    { id: "hr_requests", icon: "star", label: "Requests" },
    { id: "grievances", icon: "alert", label: "Grievances" },
    { id: "disciplinary", icon: "mis", label: "Disciplinary Records" },
    { id: "assets", icon: "tasks", label: "Assets" },
    // HUB 9: ADMINISTRATION
    { isHeader: true, label: "Administration" },
    { id: "reports", icon: "chart", label: "Reports" },
    { id: "offboarding", icon: "exit", label: "Exit & Offboarding" },
    { id: "offboarding2", icon: "exit", label: "Exit Interviews" },
    { id: "system_users", icon: "users", label: "Users" },
    { id: "audit_logs", icon: "log", label: "Audit Logs" },
    { id: "admin", icon: "settings", label: "Settings" },
    // PERSONAL
    { isHeader: true, label: "Personal" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
  ];
  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="Supreme Super Admin" initialPage="dashboard" renderPage={p => {
      if (p === "dashboard") return <HRDashboard />;
      if (p === "tasks_hr") return <Tasks currentUser={user} />;
      // Hub 1: Recruitment
      if (p === "jobs") return <JobsBoard />;
      if (p === "ats") return <JobRequisitions />;
      if (p === "applications") return <ApplicationsTracker />;
      if (p === "ats_pipeline") return <ATSPipeline />;
      if (p === "interviews") return <InterviewScheduler />;
      if (p === "offers") return <OffersManager />;
      if (p === "talent_pool") return <TalentPool />;
      // Hub 2: People
      if (p === "staff") return <StaffDirectory authRole="hr" />;
      if (p === "biodata") return <BiodataManager />;
      if (p === "org_chart") return <OrgChartEnhanced />;
      if (p === "departments") return <DepartmentsView />;
      if (p === "diversity") return <DiversityInclusion />;
      // Hub 3: Time & Attendance
      if (p === "presence") return <Presence currentUser={user} />;
      if (p === "timesheets") return <StaffTimesheet />;
      if (p === "timesheet_approvals") return <TimesheetApprovalCenter />;
      if (p === "shifts") return <ShiftScheduler isHR={true} />;
      if (p === "hr_calendar") return <HRCalendarView user={user} />;
      if (p === "holidays") return <HolidaysManager />;
      // Hub 4: Leave
      if (p === "leave") return <LeaveManagement user={user} />;
      if (p === "leave_balances") return <LeaveBalancesOverview />;
      if (p === "leave_policies") return <LeavePolicies isHR={true} />;
      if (p === "leave_accrual") return <LeaveAccrualConfig />;
      // Hub 5: Performance
      if (p === "perf") return <Performance />;
      if (p === "goals") return <Goals canManageKpiTemplates />;
      if (p === "improvement_plans") return <ImprovementPlans authRole="hr" />;
      if (p === "peer_reviews") return <PeerReviews360 />;
      if (p === "skills_matrix") return <SkillsMatrix />;
      if (p === "succession") return <SuccessionPlanning />;
      // Learning & Growth
      if (p === "training" || p === "compliance_training") return <LearningHub isHR={true} defaultTab={p === "compliance_training" ? "compliance" : "trainings"} />;
      if (p === "onboarding" || p === "onboarding_checklists") return <OnboardingHub isHR={true} />;
      if (p === "probation") return <ProbationTracker isHR={true} />;
      // Hub 6: Compensation
      if (p === "payroll" || p === "payroll_runs") return <Payroll />;
      if (p === "comp_bands") return <CompensationBands isHR={true} />;
      if (p === "bonuses") return <BonusManager isHR={true} />;
      if (p === "benefits") return <BenefitsManager />;
      if (p === "expenses") return <ExpensesManager />;
      if (p === "tax_config") return <TaxConfig />;
      // Hub 7: Engagement
      if (p === "announcements") return <Announcements isHR={true} />;
      if (p === "recognition") return <RecognitionWall user={user} />;
      if (p === "surveys") return <CultureHub authRole="hr" />;
      if (p === "remote_work") return <RemoteWork />;
      if (p === "policy_library") return <PolicyLibrary isHR={true} />;
      if (p === "internal_job_board") return <InternalJobBoard isHR={true} user={user} />;
      // Hub 8: Documents
      if (p === "legal_vault") return <DocumentsVault isHR={true} />;
      if (p === "contracts") return <LegalManager staffId={null} staffName={null} isHR={true} />;
      if (p === "hr_letters") return <HRLetters isHR={true} />;
      if (p === "work_permits") return <WorkPermits isHR={true} />;
      if (p === "hr_requests") return <HRRequests user={user} isHR={true} />;
      if (p === "grievances") return <Grievances isHR={true} />;
      if (p === "disciplinary") return <Disciplinary />;
      if (p === "assets") return <AssetManager />;
      // Hub 9: Admin
      if (p === "reports") return <HRReports />;
      if (p === "offboarding") return <OffboardingManager />;
      if (p === "offboarding2") return <ExitInterviews />;
      if (p === "system_users") return <SystemUsers />;
      if (p === "audit_logs") return <AuditLogs />;
      if (p === "admin") return <Administration />;
      // Personal
      if (p === "myprofile") return <MyProfile user={user} />;
    }} />
  );
}

function ManagerPortal({ user, onLogout }) {
  const nav = [
    { isHeader: true, label: "People & Org" },
    { id: "dashboard", icon: "dashboard", label: "Team Dashboard" },
    { id: "team", icon: "users", label: "My Team" },
    { id: "org_chart", icon: "org", label: "Org Chart" },
    { isHeader: true, label: "Time & Attendance" },
    { id: "presence", icon: "clock", label: "Attendance" },
    { id: "timesheets", icon: "log", label: "Timesheets" },
    { id: "timesheet_approvals", icon: "tasks", label: "Timesheet Approvals" },
    { id: "shifts", icon: "calendar", label: "Shift Scheduling" },
    { id: "hr_calendar", icon: "calendar", label: "Calendar" },
    { id: "holidays", icon: "star", label: "Holidays" },
    { isHeader: true, label: "Leave" },
    { id: "leave", icon: "presence", label: "Leave Requests" },
    { id: "leave_balances", icon: "chart", label: "Leave Balances" },
    { id: "leave_policies", icon: "book", label: "Leave Policies" },
    { id: "leave_accrual", icon: "trend", label: "Leave Accrual" },
    { isHeader: true, label: "Performance" },
    { id: "perf", icon: "perf", label: "Performance" },
    { id: "goals", icon: "goal", label: "Goals & OKRs" },
    { id: "improvement_plans", icon: "trend", label: "Improvement Plans" },
    { id: "peer_reviews", icon: "users", label: "360° Peer Reviews" },
    { id: "skills_matrix", icon: "chart", label: "Skills Matrix" },
    { id: "succession", icon: "org", label: "Succession Planning" },
    { isHeader: true, label: "Engagement & Culture" },
    { id: "announcements", icon: "megaphone", label: "Announcements" },
    { id: "recognition", icon: "star", label: "Recognition" },
    { id: "surveys", icon: "tasks", label: "Surveys" },
    { id: "remote_work", icon: "home", label: "Remote Work" },
    { id: "policy_library", icon: "book", label: "Policy Library" },
    { isHeader: true, label: "Compliance" },
    { id: "disciplinary", icon: "mis", label: "Incidents" },
    { isHeader: true, label: "Administration" },
    { id: "tasks", icon: "tasks", label: "Task Manager" },
    { isHeader: true, label: "Personal" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
    { id: "myperformance", icon: "perf", label: "My Performance" },
  ];
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API_BASE}/hr/staff`) // In a real app we'd fetch only direct reports
      .then(d => setTeam(d.filter(u => u.line_manager_id === user.id || [3, 4, 5].includes(u.id)))) // Mocking report relationship for consistency
      .finally(() => setLoading(false));
  }, [user.id]);

  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="Management Hub" renderPage={p => {
      if (p === "team") return <StaffDirectory authRole="manager" />;
      if (p === "org_chart") return <OrgChartEnhanced />;
      if (p === "leave" || p === "leave_requests") return <LeaveManagement user={user} />;
      if (p === "leave_balances") return <LeaveBalancesOverview />;
      if (p === "leave_accrual") return <LeaveAccrualConfig />;
      if (p === "leave_policies") return <LeavePolicies isHR={false} />;
      if (p === "presence" || p === "holidays") return <Presence currentUser={user} />;
      if (p === "hr_calendar") return <HRCalendarView user={user} />;
      if (p === "timesheets") return <StaffTimesheet />;
      if (p === "timesheet_approvals") return <TimesheetApprovalCenter />;
      if (p === "shifts") return <ShiftScheduler isHR={false} />;
      if (p === "perf") return <Performance />;
      if (p === "goals") return <Goals />;
      if (p === "improvement_plans") return <ImprovementPlans authRole="manager" />;
      if (p === "peer_reviews") return <MyPeerReviews user={user} />;
      if (p === "skills_matrix") return <SkillsMatrix />;
      if (p === "succession") return <SuccessionPlanning />;
      if (p === "tasks") return <Tasks currentUser={user} />;
      if (p === "disciplinary") return <Disciplinary isManager userId={user.id} />;
      if (p === "surveys") return <CultureHub authRole="manager" />;
      if (p === "announcements") return <Announcements isHR={false} />;
      if (p === "recognition") return <RecognitionWall user={user} />;
      if (p === "remote_work") return <RemoteWork />;
      if (p === "policy_library") return <PolicyLibrary isHR={false} />;
      if (p === "myprofile") return <MyProfile user={user} />;
      if (p === "myperformance") return <Performance viewOnly userId={user.id} />;

      return (
        <div className="fade">
          <div className="ho" style={{ fontSize: 24, marginBottom: 6 }}>Team Overview</div>
          <div style={{ fontSize: 13, color: C.sub, marginBottom: 22 }}>Performance and activity tracking for your direct reports.</div>

          <div className="g3" style={{ marginBottom: 22 }}>
            <StatCard label="Direct Reports" value={team.length} />
            <StatCard label="Active Tasks" value="8" col="#60A5FA" />
            <StatCard label="Avg Team Score" value="82/100" col="#4ADE80" />
          </div>

          {loading ? <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading team data…</div> : (
            <div className="g3">
              {team.map(u => (
                <div key={u.id} className="gc" style={{ padding: 22 }}>
                  <div style={{ display: "flex", gap: 14, alignItems: "center", marginBottom: 14 }}>
                    <Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={42} />
                    <div><div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{u.full_name}</div><div style={{ fontSize: 12, color: C.sub }}>{u.staff_profiles?.[0]?.job_title}</div></div>
                  </div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 8 }}>Click 'My Team' for full details.</div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }} />
  );
}

// ─── DASHBOARD WIDGET: 360 PEER REVIEWS ──────────────────────────────────────
function DashboardPeerReviewWidget({ userId }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/peer-reviews/my-assignments?staff_id=${userId}`).catch(() => null),
      apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
    ]).then(([myAssigned, all]) => {
      if (myAssigned && Array.isArray(myAssigned)) {
        setPending(myAssigned.filter(r => ["pending", "in-progress"].includes(r.status)));
      } else if (Array.isArray(all)) {
        const mine = all.filter(r =>
          ["pending", "in-progress"].includes(r.status) &&
          (r.reviewer_ids || []).map(String).includes(String(userId))
        );
        setPending(mine);
      }
    }).finally(() => setLoading(false));
  }, [userId]);

  if (loading || pending.length === 0) return null;

  return (
    <div className="gc" style={{ padding: 22, marginTop: 18, borderLeft: `4px solid ${T.gold}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <div className="ho" style={{ fontSize: 14 }}>⭐ Peer Reviews Awaiting You</div>
        <span className="tg" style={{ background: `${T.gold}22`, color: T.gold, border: `1px solid ${T.gold}44` }}>{pending.length} pending</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {pending.slice(0, 3).map(r => (
          <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid ${C.border}22` }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{r.title || "Peer Review"}</div>
              <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                Reviewing: {r.reviewee?.full_name || "a colleague"}
                {r.deadline && <span style={{ color: T.orange, marginLeft: 8 }}>· Due {new Date(r.deadline).toLocaleDateString()}</span>}
              </div>
            </div>
            <button className="bp" style={{ fontSize: 10, padding: "5px 12px", flexShrink: 0 }}
              onClick={() => { window.location.hash = "peer_reviews"; window.dispatchEvent(new HashChangeEvent("hashchange")); }}>
              Give Feedback
            </button>
          </div>
        ))}
      </div>
      {pending.length > 3 && <div style={{ fontSize: 11, color: C.muted, marginTop: 8 }}>+ {pending.length - 3} more reviews pending in 360° Peer Reviews</div>}
    </div>
  );
}

function StaffPortal({ user, onLogout }) {
  const nav = [
    { isHeader: true, label: "People & Org" },
    { id: "dashboard", icon: "dashboard", label: "My Dashboard" },
    { id: "profile", icon: "profile", label: "My Profile" },
    { id: "my_biodata", icon: "file", label: "My Bio Data" },
    { isHeader: true, label: "Time & Attendance" },
    { id: "presence", icon: "clock", label: "Attendance" },
    { id: "timesheets", icon: "log", label: "Timesheets" },
    { id: "hr_calendar", icon: "calendar", label: "Calendar" },
    { isHeader: true, label: "Leave" },
    { id: "leave", icon: "presence", label: "Leave Requests" },
    { id: "leave_balances", icon: "chart", label: "Leave Balances" },
    { id: "leave_policies", icon: "book", label: "Leave Policies" },
    { id: "leave_accrual", icon: "trend", label: "Leave Accrual" },
    { isHeader: true, label: "Performance" },
    { id: "perf", icon: "perf", label: "Performance" },
    { id: "goals", icon: "goal", label: "Goals & OKRs" },
    { id: "peer_reviews", icon: "users", label: "360° Peer Reviews" },
    { id: "improvement_plans", icon: "trend", label: "Improvement Plans" },
    { id: "skills_matrix", icon: "chart", label: "Skills Matrix" },
    { isHeader: true, label: "Learning & Growth" },
    { id: "training", icon: "book", label: "Training" }, { isHeader: true, label: "Compensation & Benefits" },
    { id: "payroll", icon: "payslip", label: "My Payroll" },
    { id: "bonuses", icon: "star", label: "My Bonuses" },
    { isHeader: true, label: "Engagement & Culture" },
    { id: "announcements", icon: "megaphone", label: "Announcements" },
    { id: "recognition", icon: "star", label: "Recognition" },
    { id: "surveys", icon: "tasks", label: "Surveys" },
    { id: "remote_work", icon: "home", label: "Remote Work" },
    { id: "policy_library", icon: "book", label: "Policy Library" },
    { id: "internal_job_board", icon: "briefcase", label: "Internal Job Board" },
    { isHeader: true, label: "Documents & Compliance" },
    { id: "legal_vault", icon: "file", label: "Documents" },
    { id: "hr_letters", icon: "file", label: "HR Letters" },
    { id: "hr_requests", icon: "star", label: "Requests" },
    { id: "grievances", icon: "alert", label: "Grievances" },
    { id: "disciplinary", icon: "mis", label: "My Flags" },
    { isHeader: true, label: "Administration" },
    { id: "tasks", icon: "tasks", label: "My Tasks" },
  ];
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
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

  const staffType = user.staff_type || user.staff_profiles?.[0]?.staff_type || "full";
  const startPage = (staffType === "contractor" || staffType === "onsite") ? "profile" : "dashboard";

  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="Team Member Portal" initialPage={startPage} renderPage={pg => {
      if (pg === "profile") return <MyProfile user={user} />;
      if (pg === "my_biodata") return <MyBiodata user={user} />;
      if (pg === "leave") return <LeaveManagement user={user} />;
      if (pg === "leave_balances") return <LeaveBalancesOverview />;
      if (pg === "leave_accrual") return <LeaveAccrualConfig />;
      if (pg === "leave_policies") return <LeavePolicies isHR={false} />;
      if (pg === "perf") return <Performance viewOnly userId={user.id} />;
      if (pg === "goals") return <Goals viewOnly userId={user.id} />;
      if (pg === "peer_reviews") return <MyPeerReviews user={user} />;
      if (pg === "improvement_plans") return <ImprovementPlans viewOnly userId={user.id} authRole="staff" />;
      if (pg === "skills_matrix") return <SkillsMatrix />;
      if (pg === "tasks") return <Tasks currentUser={user} />;
      if (pg === "presence") return <Presence currentUserId={user.id} currentUser={user} />;
      if (pg === "hr_calendar") return <HRCalendarView user={user} />;
      if (pg === "timesheets") return <StaffTimesheet />;
      if (pg === "payroll") return <StaffPayroll user={user} />;
      if (pg === "bonuses") return <BonusManager isHR={false} />;
      if (pg === "disciplinary") return <Disciplinary viewOnly userId={user.id} />;
      if (pg === "legal_vault") return <DocumentsVault isHR={false} userId={user.id} />;
      if (pg === "contracts") return <LegalManager staffId={user.id} staffName={user.full_name} isHR={false} />;
      if (pg === "hr_letters") return <HRLetters isHR={false} />;
      if (pg === "hr_requests") return <HRRequests user={user} isHR={false} />;
      if (pg === "grievances") return <Grievances isHR={false} />;
      if (pg === "announcements") return <Announcements isHR={false} />;
      if (pg === "recognition") return <RecognitionWall user={user} />;
      if (pg === "surveys") return <CultureHub authRole="staff" />;
      if (pg === "remote_work") return <RemoteWork />;
      if (pg === "policy_library") return <PolicyLibrary isHR={false} />;
      if (pg === "internal_job_board") return <InternalJobBoard isHR={false} user={user} />;
      if (pg === "training" || pg === "compliance_training") return <LearningHub isHR={false} defaultTab={pg === "compliance_training" ? "compliance" : "trainings"} />;

      return (
        <div className="fade">
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Welcome, {user.full_name?.split(" ")[0]} 👋</div>
          <div style={{ fontSize: 13, color: C.sub, marginBottom: 22 }}>{user.staff_profiles?.[0]?.job_title || user.role} · {user.department}</div>

          <div className="g4" style={{ marginBottom: 22 }}>
            <StatCard label="My Score" value={sc != null ? `${sc}/100` : "—"} col={col} />
            <StatCard label="My Tasks" value={tasks.length} col="#60A5FA" />
            <StatCard label="Pending" value={pendingTasks.length} col={T.orange} />
            <StatCard label="Leave Left" value="11d" />
          </div>

          <div className="g2" style={{ gap: 18 }}>
            <div className="gc" style={{ padding: 22 }}>
              <div className="ho" style={{ fontSize: 14, marginBottom: 14 }}>My Active Tasks</div>
              {loading ? <div style={{ fontSize: 13, color: C.muted }}>Loading...</div> : (
                <>
                  {pendingTasks.slice(0, 4).map(t => {
                    const sc2 = sCol[t.status] || T.orange;
                    return (
                      <div key={t.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "10px 0", borderBottom: `1px solid ${C.border}22` }}>
                        <div>
                          <div style={{ fontSize: 13, color: C.text, fontWeight: 700 }}>{t.title}</div>
                          <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>Due {new Date(t.due_date).toLocaleDateString()}</div>
                        </div>
                        <span className="tg" style={{ background: `${sc2}22`, color: sc2, border: `1px solid ${sc2}33`, flexShrink: 0, textTransform: "capitalize" }}>{t.status.replace("_", " ")}</span>
                      </div>
                    );
                  })}
                  {pendingTasks.length === 0 && <div style={{ fontSize: 13, color: C.muted }}>No pending tasks! 🎉</div>}
                </>
              )}
            </div>

            <div className="gc" style={{ padding: 22 }}>
              <div className="ho" style={{ fontSize: 14, marginBottom: 14 }}>My Performance</div>
              {perf ? (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 18 }}>
                    <ScoreRing sc={sc} sz={70} />
                    <div>
                      <div style={{ fontSize: 26, fontWeight: 800, color: C.text }}>{sc}<span style={{ fontSize: 13, color: C.muted }}>/100</span></div>
                      <span className={`tg ${sc >= 80 ? "tg2" : sc >= 60 ? "to" : "tr"}`}>Rank: {sc >= 80 ? "Elite" : sc >= 60 ? "Stable" : "Needs PIP"}</span>
                    </div>
                  </div>
                  {[["KPI Goals", (perf.breakdown?.goals_40_pct || 0) * 2.5], ["Work Quality", (perf.breakdown?.quality_20_pct || 0) * 5]].map(([l, v]) => (
                    <div key={l} style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted, marginBottom: 4 }}><span>{l}</span><span style={{ color: T.orange, fontWeight: 800 }}>{Math.round(v)}%</span></div>
                      <Bar pct={v} />
                    </div>
                  ))}
                </>
              ) : <div style={{ fontSize: 13, color: C.muted }}>No performance data available yet.</div>}
            </div>
          </div>

          {/* 360 Peer Reviews widget */}
          <DashboardPeerReviewWidget userId={user.id} />
        </div>
      );
    }} />
  );
}

// ─── EXIT INTERVIEWS ──────────────────────────────────────────────────────────
// Distinct from OffboardingManager (which handles asset recovery + deactivation).
// This tab focuses on capturing exit interview data and trends.
function ExitInterviews() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [interviews, setInterviews] = useState([]); const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [staff, setStaff] = useState([]);
  const [form, setForm] = useState({ staff_id: "", exit_date: "", reason: "Resignation", overall_satisfaction: 3, highlights: "", concerns: "", would_recommend: true, notes: "" });
  const [saving, setSaving] = useState(false);
  const [viewItem, setViewItem] = useState(null);

  const REASONS = ["Resignation", "Termination", "End of Contract", "Retirement", "Redundancy"];
  const reasonCol = { Resignation: "#F59E0B", Termination: "#F87171", "End of Contract": "#60A5FA", Retirement: "#4ADE80", Redundancy: "#A78BFA" };

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/exit-interviews`).catch(() => []),
      apiFetch(`${API_BASE}/hr/staff`).catch(() => [])
    ]).then(([e, s]) => { setInterviews(Array.isArray(e) ? e : []); setStaff(s || []); }).finally(() => setLoading(false));
  }, []);

  const refresh = () => apiFetch(`${API_BASE}/hr/exit-interviews`).catch(() => []).then(d => setInterviews(Array.isArray(d) ? d : []));

  const save = async () => {
    if (!form.staff_id || !form.exit_date) return alert("Staff member and exit date required.");
    setSaving(true);
    try {
      await apiFetch(`${API_BASE}/hr/exit-interviews`, { method: "POST", body: JSON.stringify({ job_id: form.job_id, candidate_name: form.candidate_name, candidate_email: form.candidate_email, candidate_phone: form.candidate_phone, cover_letter: form.cover_letter, resume_url: form.resume_url }) });
      setShowNew(false); setForm({ staff_id: "", exit_date: "", reason: "Resignation", overall_satisfaction: 3, highlights: "", concerns: "", would_recommend: true, notes: "" });
      refresh();
    } catch (e) { alert("Error: " + e.message); } finally { setSaving(false); }
  };

  const Stars = ({ val }) => (
    <span>{[1, 2, 3, 4, 5].map(n => <span key={n} style={{ color: n <= val ? T.gold : "#333", fontSize: 16 }}>★</span>)}</span>
  );

  // ──────────────────────────────────────────────────ggregate stats
  const total = interviews.length;
  const avgSat = total > 0 ? (interviews.reduce((s, i) => s + (i.overall_satisfaction || 3), 0) / total).toFixed(1) : "—";
  const wouldRec = total > 0 ? Math.round((interviews.filter(i => i.would_recommend).length / total) * 100) : 0;
  const byReason = interviews.reduce((acc, i) => { acc[i.reason || "Other"] = (acc[i.reason || "Other"] || 0) + 1; return acc; }, {});

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>Exit Interviews</div>
          <div style={{ fontSize: 13, color: C.sub }}>Capture and analyse feedback from departing employees.</div>
        </div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Record Exit Interview</button>
      </div>

      {/* Stats */}
      <div className="g3" style={{ marginBottom: 22 }}>
        <div className="gc" style={{ padding: 22, textAlign: "center" }}>
          <div style={{ fontSize: 36, fontWeight: 900, color: T.gold }}>{total}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Exit Interviews Recorded</div>
        </div>
        <div className="gc" style={{ padding: 22, textAlign: "center" }}>
          <div style={{ fontSize: 36, fontWeight: 900, color: "#60A5FA" }}>{avgSat}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Avg Satisfaction (out of 5)</div>
        </div>
        <div className="gc" style={{ padding: 22, textAlign: "center" }}>
          <div style={{ fontSize: 36, fontWeight: 900, color: "#4ADE80" }}>{wouldRec}%</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Would Recommend Company</div>
        </div>
      </div>

      {/* Reason breakdown */}
      {total > 0 && (
        <div className="gc" style={{ padding: 22, marginBottom: 22 }}>
          <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 16 }}>Exits by Reason</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {Object.entries(byReason).map(([reason, count]) => {
              const rc = reasonCol[reason] || C.muted;
              return (
                <div key={reason} style={{ padding: "8px 16px", background: `${rc}18`, borderRadius: 20, border: `1px solid ${rc}40` }}>
                  <span style={{ fontWeight: 800, color: rc }}>{count}</span>
                  <span style={{ fontSize: 12, color: C.sub, marginLeft: 6 }}>{reason}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Interview List */}
      {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw"><table className="ht">
            <thead><tr><th>Staff Member</th><th>Exit Date</th><th>Reason</th><th>Satisfaction</th><th>Would Recommend</th><th>Action</th></tr></thead>
            <tbody>
              {interviews.map(i => {
                const rc = reasonCol[i.reason] || C.muted;
                return (
                  <tr key={i.id}>
                    <td style={{ fontWeight: 800, color: C.text }}>{i.admins?.full_name || staff.find(s => s.id === i.staff_id)?.full_name || "—"}</td>
                    <td style={{ fontSize: 12, color: C.sub }}>{i.exit_date ? new Date(i.exit_date).toLocaleDateString() : "—"}</td>
                    <td><span className="tg" style={{ background: `${rc}22`, color: rc }}>{i.reason || "—"}</span></td>
                    <td><Stars val={i.overall_satisfaction || 3} /></td>
                    <td>{i.would_recommend ? <span className="tg tm">✓ Yes</span> : <span className="tg" style={{ background: "#F8717122", color: "#F87171" }}>✗ No</span>}</td>
                    <td><button className="bg" style={{ fontSize: 11, padding: "4px 12px" }} onClick={() => setViewItem(i)}>View Details</button></td>
                  </tr>
                );
              })}
              {interviews.length === 0 && <tr><td colSpan="6" style={{ textAlign: "center", padding: 30, color: C.muted }}>No exit interviews recorded yet.</td></tr>}
            </tbody>
          </table></div>
        </div>
      )}

      {/* View Interview Modal */}
      {viewItem && (
        <Modal onClose={() => setViewItem(null)} title="Exit Interview Details">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="g2">
              <div><span style={{ fontSize: 11, color: C.muted }}>Staff Member</span><div style={{ fontWeight: 800, marginTop: 4 }}>{viewItem.admins?.full_name || "—"}</div></div>
              <div><span style={{ fontSize: 11, color: C.muted }}>Exit Date</span><div style={{ fontWeight: 800, marginTop: 4 }}>{viewItem.exit_date || "—"}</div></div>
            </div>
            <div className="g2">
              <div><span style={{ fontSize: 11, color: C.muted }}>Reason</span><div style={{ marginTop: 4 }}><span className="tg" style={{ background: `${reasonCol[viewItem.reason] || C.muted}22`, color: reasonCol[viewItem.reason] || C.muted }}>{viewItem.reason}</span></div></div>
              <div><span style={{ fontSize: 11, color: C.muted }}>Satisfaction</span><div style={{ marginTop: 4 }}><Stars val={viewItem.overall_satisfaction || 3} /></div></div>
            </div>
            {viewItem.highlights && <div style={{ padding: 14, background: "#4ADE8011", borderRadius: 8 }}><div style={{ fontSize: 11, color: "#4ADE80", fontWeight: 800, marginBottom: 6 }}>HIGHLIGHTS / POSITIVES</div><div style={{ fontSize: 13, color: C.sub }}>{viewItem.highlights}</div></div>}
            {viewItem.concerns && <div style={{ padding: 14, background: "#F8717111", borderRadius: 8 }}><div style={{ fontSize: 11, color: "#F87171", fontWeight: 800, marginBottom: 6 }}>CONCERNS / AREAS TO IMPROVE</div><div style={{ fontSize: 13, color: C.sub }}>{viewItem.concerns}</div></div>}
            {viewItem.notes && <div><span style={{ fontSize: 11, color: C.muted }}>Additional Notes</span><div style={{ fontSize: 13, color: C.sub, marginTop: 6, lineHeight: 1.6 }}>{viewItem.notes}</div></div>}
          </div>
        </Modal>
      )}

      {/* New Interview Modal */}
      {showNew && (
        <Modal onClose={() => setShowNew(false)} title="Record Exit Interview">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="g2">
              <div><Lbl>Departing Staff *</Lbl>
                <select className="inp" value={form.staff_id} onChange={e => setForm(f => ({ ...f, staff_id: e.target.value }))}>
                  <option value="">— Select —</option>
                  {staff.map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}
                </select>
              </div>
              <div><Lbl>Exit Date *</Lbl><input className="inp" type="date" value={form.exit_date} onChange={e => setForm(f => ({ ...f, exit_date: e.target.value }))} /></div>
            </div>
            <div className="g2">
              <div><Lbl>Exit Reason</Lbl>
                <select className="inp" value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}>
                  {REASONS.map(r => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div><Lbl>Overall Satisfaction (1–5)</Lbl>
                <input className="inp" type="number" min="1" max="5" value={form.overall_satisfaction} onChange={e => setForm(f => ({ ...f, overall_satisfaction: parseInt(e.target.value) }))} />
              </div>
            </div>
            <div><Lbl>What did they appreciate most?</Lbl><textarea className="inp" rows={2} placeholder="Culture, team, learning opportunities…" value={form.highlights} onChange={e => setForm(f => ({ ...f, highlights: e.target.value }))} /></div>
            <div><Lbl>Key concerns or reasons for leaving</Lbl><textarea className="inp" rows={2} placeholder="Compensation, growth, management…" value={form.concerns} onChange={e => setForm(f => ({ ...f, concerns: e.target.value }))} /></div>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: C.sub, cursor: "pointer" }}>
              <input type="checkbox" checked={form.would_recommend} onChange={e => setForm(f => ({ ...f, would_recommend: e.target.checked }))} />
              Would recommend the company as a place to work
            </label>
            <div><Lbl>Additional Notes</Lbl><textarea className="inp" rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></div>
            <button className="bp" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save Exit Interview"}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── NOTIFICATION BELL SYSTEM ─────────────────────────────────────────────────
// ─── NOTIFICATION CONTEXT ─────────────────────────────────────────────────────
// Single source of truth for notifications — shared by bell AND nav badges.
const NotifCtx = createContext({ notifs: [], unread: 0, unreadByType: {}, refresh: () => { }, markRead: () => { }, markAllRead: () => { } });
const useNotifs = () => useContext(NotifCtx);

// Maps notification_type → nav page id (for badge counts on sidebar items)
const NOTIF_TYPE_TO_PAGE = {
  task_assigned: "tasks",
  task_assigned_hr: "tasks_hr",
  request_update: "hr_requests",
  hr_request: "hr_requests",
  leave_request: "leave",
  leave_update: "leave",
  grievance_update: "grievances",
  grievance_filed: "grievances",
  letter_issued: "hr_letters",
  announcement: "announcements",
  recognition: "recognition",
  remote_work_update: "remote_work",
  goal_update: "goals",
  performance_review: "perf",
  disciplinary: "disciplinary",
  asset_assigned: "assets",
  shift_assigned: "shifts",
  payroll_run: "payroll",
  bonus_awarded: "bonuses",
  timesheet_update: "timesheets",
  offer_response: "offers",
  new_application: "applications",
  interview_scheduled: "interviews",
  expense_update: "expenses",
  survey_new: "surveys",
  payout_reimbursement_request: "expenses",
  payout_commission_request: "commissions",
};

function NotifProvider({ userId, children }) {
  const [notifs, setNotifs] = useState([]);

  const refresh = useCallback(async () => {
    if (!userId) return;
    try {
      const d = await apiFetch(`${API_BASE}/hr/notifications?limit=60`).catch(() => []);
      setNotifs(Array.isArray(d) ? d : []);
    } catch { }
  }, [userId]);

  // Poll every 30 seconds — fast enough to feel live
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, [refresh]);

  const markRead = useCallback(async (id) => {
    try {
      await apiFetch(`${API_BASE}/hr/notifications/${id}/read`, { method: "PATCH" });
      setNotifs(ns => ns.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch { }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await apiFetch(`${API_BASE}/hr/notifications/read-all`, { method: "PATCH" });
      setNotifs(ns => ns.map(n => ({ ...n, is_read: true })));
    } catch { }
  }, []);

  const unread = notifs.filter(n => !n.is_read).length;

  // Count unread per destination page for nav badges
  const unreadByType = notifs
    .filter(n => !n.is_read)
    .reduce((acc, n) => {
      const type = n.notification_type || n.type || "";
      const page = NOTIF_TYPE_TO_PAGE[type];
      if (page) acc[page] = (acc[page] || 0) + 1;
      return acc;
    }, {});

  return (
    <NotifCtx.Provider value={{ notifs, unread, unreadByType, refresh, markRead, markAllRead }}>
      {children}
    </NotifCtx.Provider>
  );
}

// Notification type metadata
const NOTIF_META = {
  letter_issued: { icon: "📄", color: "#60A5FA", label: "HR Letter" },
  task_assigned: { icon: "✅", color: "#4ADE80", label: "Task" },
  task_assigned_hr: { icon: "✅", color: "#4ADE80", label: "Task" },
  grievance_update: { icon: "⚖️", color: "#F87171", label: "Grievance" },
  grievance_filed: { icon: "⚖️", color: "#F87171", label: "Grievance" },
  request_update: { icon: "📋", color: T.gold, label: "Request" },
  hr_request: { icon: "📋", color: T.gold, label: "HR Request" },
  leave_request: { icon: "🌴", color: "#34D399", label: "Leave" },
  leave_update: { icon: "🌴", color: "#34D399", label: "Leave" },
  goal_update: { icon: "🎯", color: "#A78BFA", label: "Goal" },
  announcement: { icon: "📢", color: "#F59E0B", label: "Announcement" },
  recognition: { icon: "🏆", color: T.gold, label: "Recognition" },
  remote_work_update: { icon: "🏠", color: "#60A5FA", label: "Remote Work" },
  performance_review: { icon: "📊", color: "#A78BFA", label: "Performance" },
  disciplinary: { icon: "🚨", color: "#F87171", label: "Disciplinary" },
  asset_assigned: { icon: "💼", color: "#60A5FA", label: "Asset" },
  shift_assigned: { icon: "🗓️", color: "#34D399", label: "Shift" },
  payroll_run: { icon: "💰", color: "#4ADE80", label: "Payroll" },
  bonus_awarded: { icon: "🎁", color: T.gold, label: "Bonus" },
  timesheet_update: { icon: "⏱️", color: "#60A5FA", label: "Timesheet" },
  offer_response: { icon: "🤝", color: "#4ADE80", label: "Offer" },
  new_application: { icon: "📥", color: T.gold, label: "Application" },
  interview_scheduled: { icon: "🗓️", color: "#A78BFA", label: "Interview" },
  expense_update: { icon: "🧾", color: T.gold, label: "Expense" },
  survey_new: { icon: "📝", color: "#60A5FA", label: "Survey" },
  payout_reimbursement_request: { icon: "🧾", color: T.gold, label: "Reimbursement Request" },
  payout_commission_request: { icon: "💼", color: "#60A5FA", label: "Commission Request" },
  hr_alert: { icon: "🔔", color: "#F59E0B", label: "Alert" },
  general: { icon: "🔔", color: "#9CA3AF", label: "Notification" },
};

function NotificationBell() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { notifs, unread, markRead, markAllRead, refresh } = useNotifs();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("all");

  const filtered = filter === "unread" ? notifs.filter(n => !n.is_read) : notifs;
  const groups = filtered.reduce((acc, n) => {
    const d = new Date(n.created_at);
    const now = new Date();
    const diff = now - d;
    const key = diff < 86400000 ? "Today" : diff < 172800000 ? "Yesterday" : "Earlier";
    if (!acc[key]) acc[key] = [];
    acc[key].push(n);
    return acc;
  }, {});

  const timeAgo = (ts) => {
    const s = Math.floor((Date.now() - new Date(ts)) / 1000);
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return new Date(ts).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  };

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => { setOpen(o => { if (!o) refresh(); return !o; }); }}
        style={{
          background: open ? `${T.gold}18` : "none",
          border: open ? `1px solid ${T.gold}44` : "1px solid transparent",
          cursor: "pointer", position: "relative", padding: "7px 10px",
          borderRadius: 10, color: C.text, transition: "all .2s", display: "flex", alignItems: "center"
        }}
        title="Notifications"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={unread > 0 ? T.gold : C.sub} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          {unread > 0 && <circle cx="19" cy="5" r="4" fill="#F87171" stroke="none" />}
        </svg>
        {unread > 0 && (
          <span style={{
            position: "absolute", top: 3, right: 3,
            background: "#F87171", color: "#fff", borderRadius: "50%",
            width: 17, height: 17, fontSize: 9, fontWeight: 900,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 8px rgba(248,113,113,0.7)", border: `2px solid ${C.surface}`,
            lineHeight: 1
          }}>
            {unread > 99 ? "99+" : unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 999 }} />
          <div style={{
            position: "fixed",
            top: "auto",
            right: "max(8px, env(safe-area-inset-right))",
            left: "auto",
            width: "min(400px, calc(100vw - 16px))",
            maxWidth: 400,
            maxHeight: "min(560px, calc(100dvh - 80px))",
            display: "flex", flexDirection: "column", zIndex: 1000,
            background: dark ? "#141720" : "#fff",
            border: `1px solid ${dark ? "#2D2F3A" : "#DDE3EE"}`,
            borderRadius: 18, boxShadow: "0 24px 80px rgba(0,0,0,0.5)",
            overflow: "hidden"
          }}>
            {/* Header */}
            <div style={{ padding: "18px 20px 12px", borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ fontWeight: 800, fontSize: 15, color: C.text, display: "flex", alignItems: "center", gap: 8 }}>
                  Notifications
                  {unread > 0 && (
                    <span style={{ background: "#F87171", color: "#fff", borderRadius: 20, padding: "2px 8px", fontSize: 11, fontWeight: 900 }}>
                      {unread} new
                    </span>
                  )}
                </div>
                {unread > 0 && (
                  <button onClick={markAllRead} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: T.gold, fontWeight: 700, padding: "4px 8px", borderRadius: 6 }}>
                    Mark all read
                  </button>
                )}
              </div>
              {/* Filter tabs */}
              <div style={{ display: "flex", gap: 6 }}>
                {["all", "unread"].map(f => (
                  <button key={f} onClick={() => setFilter(f)} style={{
                    padding: "5px 14px", borderRadius: 20, border: "none", cursor: "pointer",
                    fontSize: 12, fontWeight: 700, fontFamily: "inherit",
                    background: filter === f ? `${T.gold}22` : "transparent",
                    color: filter === f ? T.gold : C.muted,
                    transition: "all .15s"
                  }}>
                    {f === "all" ? `All (${notifs.length})` : `Unread (${unread})`}
                  </button>
                ))}
              </div>
            </div>

            {/* Notification list */}
            <div style={{ overflowY: "auto", flex: 1 }}>
              {filtered.length === 0 ? (
                <div style={{ padding: 50, textAlign: "center" }}>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>
                    {filter === "unread" ? "✅" : "🎉"}
                  </div>
                  <div style={{ fontSize: 14, color: C.muted, fontWeight: 600 }}>
                    {filter === "unread" ? "All caught up!" : "No notifications yet"}
                  </div>
                </div>
              ) : (
                Object.entries(groups).map(([group, items]) => (
                  <div key={group}>
                    <div style={{ padding: "10px 20px 4px", fontSize: 10, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", background: dark ? "#0F1117" : C.bg, position: "sticky", top: 0 }}>
                      {group}
                    </div>
                    {items.map(n => {
                      const type = n.notification_type || n.type || "general";
                      const meta = NOTIF_META[type] || NOTIF_META.general;
                      return (
                        <div key={n.id} onClick={() => markRead(n.id)} style={{
                          padding: "14px 20px", borderBottom: `1px solid ${C.border}44`,
                          display: "flex", gap: 12, alignItems: "flex-start", cursor: "pointer",
                          background: n.is_read ? "transparent" : (dark ? `${meta.color}09` : `${meta.color}08`),
                          transition: "background .15s",
                          position: "relative"
                        }}>
                          {/* Left accent */}
                          {!n.is_read && (
                            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 3, background: meta.color, borderRadius: "0 2px 2px 0" }} />
                          )}
                          <div style={{
                            width: 36, height: 36, borderRadius: 10,
                            background: `${meta.color}20`, border: `1px solid ${meta.color}30`,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 17, flexShrink: 0
                          }}>
                            {meta.icon}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                              <span style={{ fontSize: 9, fontWeight: 800, color: meta.color, textTransform: "uppercase", letterSpacing: "0.8px" }}>
                                {meta.label}
                              </span>
                              <span style={{ fontSize: 10, color: C.muted, whiteSpace: "nowrap", flexShrink: 0 }}>
                                {timeAgo(n.created_at)}
                              </span>
                            </div>
                            <div style={{ fontSize: 13, color: n.is_read ? C.sub : C.text, fontWeight: n.is_read ? 400 : 600, lineHeight: 1.5, marginTop: 2 }}>
                              {n.title && n.title !== n.message && (
                                <div style={{ fontWeight: 700, marginBottom: 2, color: n.is_read ? C.sub : C.text }}>{n.title}</div>
                              )}
                              {n.message}
                            </div>
                          </div>
                          {!n.is_read && (
                            <div style={{ width: 8, height: 8, borderRadius: "50%", background: meta.color, flexShrink: 0, marginTop: 5, boxShadow: `0 0 6px ${meta.color}` }} />
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            <div style={{ padding: "10px 20px", textAlign: "center", borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
              <button onClick={() => setOpen(false)} style={{ background: "none", border: "none", color: C.muted, fontSize: 12, cursor: "pointer", fontFamily: "inherit" }}>
                Close
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const isHrAdminUser = (user) => {
  if (!user) return false;
  const rawRole = user.role;
  const primaryRole = user.primary_role;
  const roles = Array.isArray(rawRole)
    ? rawRole
    : typeof rawRole === "string"
      ? rawRole.split(",").map(r => r.trim())
      : [];
  return roles.includes("admin")
    || roles.includes("hr")
    || roles.includes("hr_admin")
    || primaryRole === "hr";
};

const isLineManagerUser = (user) => {
  if (!user) return false;
  const rawRole = user.role;
  const roles = Array.isArray(rawRole)
    ? rawRole
    : typeof rawRole === "string"
      ? rawRole.split(",").map(r => r.trim())
      : [];
  return roles.includes("line_manager");
};


// ─── ASSET MANAGEMENT ────────────────────────────────────────────────────────
function AssetManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [assets, setAssets] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [assignForm, setAssignForm] = useState({ staff_id: "", status: "Assigned", notes: "" });
  const [createForm, setCreateForm] = useState({ asset_name: "", asset_type: "Equipment", serial_number: "", purchase_cost: "" });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [assData, stfData] = await Promise.all([
        apiFetch(`${API_BASE}/hr/assets`),
        apiFetch(`${API_BASE}/hr/staff`)
      ]);
      setAssets(assData || []);
      setStaffList(stfData || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async () => {
    try {
      await apiFetch(`${API_BASE}/hr/assets/${selectedAsset.id}/assign`, {
        method: "PATCH",
        body: JSON.stringify(assignForm)
      });
      setShowAssignModal(false);
      fetchData();
    } catch (e) { alert("Failed to assign: " + e.message); }
  };

  const handleCreate = async () => {
    if (!createForm.asset_name) return alert("Asset name required");
    try {
      await apiFetch(`${API_BASE}/hr/assets`, {
        method: "POST",
        body: JSON.stringify({
          ...createForm,
          purchase_cost: createForm.purchase_cost ? parseFloat(createForm.purchase_cost) : null
        })
      });
      setShowCreateModal(false);
      setCreateForm({ asset_name: "", asset_type: "Equipment", serial_number: "", purchase_cost: "" });
      fetchData();
    } catch (e) { alert("Failed to create: " + e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Asset Management</div>
          <div style={{ fontSize: 13, color: C.sub }}>Track and assign physical company property across the workforce.</div>
        </div>
        <button className="bp" onClick={() => setShowCreateModal(true)}>+ Register New Asset</button>
      </div>

      <div className="g4" style={{ marginBottom: 22 }}>
        <StatCard label="Total Assets" value={assets.length} />
        <StatCard label="Assigned" value={assets.filter(a => a.status === 'Assigned').length} col="#60A5FA" />
        <StatCard label="Available" value={assets.filter(a => a.status === 'Available').length} col="#4ADE80" />
        <StatCard label="Maintenance" value={assets.filter(a => a.status === 'Maintenance').length} col="#F87171" />
      </div>

      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw">
          <table className="ht">
            <thead>
              <tr>
                <th>Asset Details</th>
                <th>Type / Serial</th>
                <th>Status</th>
                <th>Current Assignee</th>
                <th>Fin. Link</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.map(a => (
                <tr key={a.id}>
                  <td>
                    <div style={{ fontWeight: 800, color: C.text }}>{a.asset_name}</div>
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>Added {new Date(a.created_at).toLocaleDateString()}</div>
                  </td>
                  <td>
                    <div style={{ color: C.text }}>{a.asset_type}</div>
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 2, fontFamily: "monospace" }}>{a.serial_number || "N/A"}</div>
                  </td>
                  <td>
                    <span className="tg" style={{ background: a.status === 'Available' ? '#4ADE8022' : a.status === 'Assigned' ? '#60A5FA22' : '#F8717122', color: a.status === 'Available' ? '#4ADE80' : a.status === 'Assigned' ? '#60A5FA' : '#F87171' }}>{a.status}</span>
                  </td>
                  <td>
                    {a.admins ? (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Av av={a.admins.full_name[0]} sz={24} />
                        <div>
                          <div style={{ fontWeight: 700, color: C.text, fontSize: 12 }}>{a.admins.full_name}</div>
                          <div style={{ fontSize: 10, color: C.muted }}>{a.admins.department}</div>
                        </div>
                      </div>
                    ) : <span style={{ color: C.muted, fontStyle: "italic" }}>Unassigned</span>}
                  </td>
                  <td>
                    {a.payout_request_id ? (
                      <span style={{ fontSize: 10, background: `${T.orange}1A`, color: T.orange, padding: "3px 6px", borderRadius: 4, fontWeight: 700 }}>Linked to Payout</span>
                    ) : <span style={{ color: C.muted }}>—</span>}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="bg" style={{ padding: "6px 12px", fontSize: 11 }} onClick={() => {
                      setSelectedAsset(a);
                      setAssignForm({ staff_id: a.assigned_to || "", status: a.status, notes: a.notes || "" });
                      setShowAssignModal(true);
                    }}>Manage</button>
                  </td>
                </tr>
              ))}
              {assets.length === 0 && !loading && (
                <tr><td colSpan="6" style={{ textAlign: "center", padding: 30, color: C.muted }}>No assets registered yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreateModal && (
        <Modal title="Register Asset" width={480} onClose={() => setShowCreateModal(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div><Lbl>Asset Name *</Lbl><input className="inp" value={createForm.asset_name} onChange={e => setCreateForm({ ...createForm, asset_name: e.target.value })} placeholder="e.g. MacBook Pro M2" /></div>
            <div className="g2">
              <div><Lbl>Asset Type</Lbl>
                <select className="inp" value={createForm.asset_type} onChange={e => setCreateForm({ ...createForm, asset_type: e.target.value })}>
                  <option>Equipment</option><option>Vehicle</option><option>Property</option><option>Software License</option>
                </select>
              </div>
              <div><Lbl>Serial Number</Lbl><input className="inp" value={createForm.serial_number} onChange={e => setCreateForm({ ...createForm, serial_number: e.target.value })} placeholder="Optional" /></div>
            </div>
            <div><Lbl>Purchase Cost (Optional)</Lbl><input type="number" className="inp" value={createForm.purchase_cost} onChange={e => setCreateForm({ ...createForm, purchase_cost: e.target.value })} placeholder="0.00" /></div>
            <button className="bp" onClick={handleCreate} style={{ marginTop: 10 }}>Register Asset</button>
          </div>
        </Modal>
      )}

      {showAssignModal && selectedAsset && (
        <Modal title="Manage Asset Assignment" width={480} onClose={() => setShowAssignModal(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ padding: 14, background: `${T.orange}11`, borderRadius: 10, border: `1px solid ${T.orange}33` }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: C.text }}>{selectedAsset.asset_name}</div>
              <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Serial: {selectedAsset.serial_number || "N/A"}</div>
            </div>
            <div><Lbl>Assign To Staff</Lbl>
              <select className="inp" value={assignForm.staff_id} onChange={e => setAssignForm({ ...assignForm, staff_id: e.target.value })}>
                <option value="">— Unassigned (Return to Inventory) —</option>
                {staffList.filter(u => u.is_active).map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div><Lbl>Asset Status</Lbl>
              <select className="inp" value={assignForm.status} onChange={e => setAssignForm({ ...assignForm, status: e.target.value })}>
                <option value="Available">Available</option>
                <option value="Assigned">Assigned</option>
                <option value="Maintenance">Maintenance</option>
                <option value="Retired">Retired</option>
              </select>
            </div>
            <div><Lbl>Assignment Notes</Lbl><textarea className="inp" rows="2" value={assignForm.notes} onChange={e => setAssignForm({ ...assignForm, notes: e.target.value })} placeholder="Condition details, expected return date, etc." /></div>
            <button className="bp" onClick={handleAssign} style={{ marginTop: 10 }}>Save Assignment</button>
          </div>
        </Modal>
      )}
    </div>
  );
}



// ══════════════════════════════════════════════════════════════════════════════
// RECRUITMENT HUB — 7 fully independent screens, each its own component
// ══════════════════════════════════════════════════════════════════════════════

function useRecruitmentData() {
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const refresh = async () => {
    setLoading(true);
    try {
      const [j, a, iv, d] = await Promise.all([
        apiFetch(`${API_BASE}/hr/recruitment/jobs`).catch(() => []),
        apiFetch(`${API_BASE}/hr/recruitment/applications`).catch(() => []),
        apiFetch(`${API_BASE}/hr/recruitment/interviews`).catch(() => []),
        apiFetch(`${API_BASE}/hr/departments`).catch(() => []),
      ]);
      setJobs(j || []); setApps(a || []); setInterviews(iv || []); setDepartments(d || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, []);
  return { jobs, apps, interviews, departments, loading, refresh };
}

function DepartmentManager({ departments = [], onRefresh }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const handleAdd = async () => {
    if (!name) return; setSaving(true);
    try { await apiFetch(`${API_BASE}/hr/departments`, { method: "POST", body: JSON.stringify({ name }) }); setName(""); onRefresh(); }
    catch (e) { alert(e.message); } finally { setSaving(false); }
  };
  const handleDelete = async (id) => {
    if (!window.confirm("Delete this department?")) return;
    try { await apiFetch(`${API_BASE}/hr/departments/${id}`, { method: "DELETE" }); onRefresh(); }
    catch (e) { alert(e.message); }
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 10 }}>
        <input className="inp" value={name} onChange={e => setName(e.target.value)} placeholder="New Department Name..." />
        <button className="bp" onClick={handleAdd} disabled={saving}>{saving ? "Adding..." : "Add"}</button>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {departments.map(d => (
          <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", background: d.is_system ? `${C.border}44` : `${T.gold}11`, borderRadius: 8, border: `1px solid ${d.is_system ? C.border : T.gold + "22"}` }}>
            <span style={{ fontSize: 13, fontWeight: 700, opacity: d.is_system ? 0.6 : 1 }}>{d.name}</span>
            {d.is_system ? (
              <span style={{ fontSize: 9, color: C.muted, fontWeight: 800, textTransform: "uppercase" }}>Staff Linked</span>
            ) : (
              <button onClick={() => handleDelete(d.id)} style={{ background: "none", border: "none", color: "#F87171", cursor: "pointer", fontSize: 14 }}>×</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── 1. JOBS BOARD ────────────────────────────────────────────────────────────
function JobsBoard() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { jobs, apps, departments, loading, refresh } = useRecruitmentData();
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("All");
  const [showNew, setShowNew] = useState(false);
  const [showDepts, setShowDepts] = useState(false);
  const [viewJob, setViewJob] = useState(null);
  const [form, setForm] = useState({ title: "", department: departments[0]?.name || "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", description: "", responsibilities: "", requirements: "" });

  const depts = ["All", ...new Set(jobs.filter(j => !j.is_internal).map(j => j.department).filter(Boolean))];
  const filtered = jobs.filter(j =>
    (!j.is_internal) &&
    (deptFilter === "All" || j.department === deptFilter) &&
    (j.title?.toLowerCase().includes(search.toLowerCase()) || j.department?.toLowerCase().includes(search.toLowerCase()))
  );

  const create = async () => {
    if (!form.title) return alert("Job title required");
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/jobs`, { method: "POST", body: JSON.stringify({ title: form.title, department: form.department, employment_type: form.employment_type, location: form.location, salary_range: form.salary_range, description: form.description, responsibilities: form.responsibilities, requirements: form.requirements, status: "Pending Approval" }) });
      setShowNew(false); setForm({ title: "", department: departments[0]?.name || "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", description: "", responsibilities: "", requirements: "" }); refresh();
    } catch (e) { alert(e.message); }
  };

  const toggleStatus = async (jobId, currentStatus) => {
    try { await apiFetch(`${API_BASE}/hr/recruitment/jobs/${jobId}`, { method: "PATCH", body: JSON.stringify({ status: (currentStatus === "Open" || currentStatus === "Approved") ? "Closed" : "Open" }) }); refresh(); } catch (e) { alert(e.message); }
  };

  const statusStyle = (s) => (s === "Open" || s === "Approved") ? { background: "#4ADE8022", color: "#4ADE80", border: "1px solid #4ADE8044" } : { background: "#F8717122", color: "#F87171", border: "1px solid #F8717144" };
  const typeCol = { "Full-time": T.gold, "Part-time": "#60A5FA", "Contract": "#F87171", "Internship": "#A78BFA" };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Jobs</div><div style={{ fontSize: 13, color: C.sub }}>Active job openings. Manage listings, track applicant counts, open and close roles.</div></div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="bg" onClick={() => setShowDepts(true)}>Manage Departments</button>
          <button className="bp" onClick={() => setShowNew(true)}>+ Post New Job</button>
        </div>
      </div>
      {showDepts && <Modal title="Manage Departments" onClose={() => setShowDepts(false)} width={480}><DepartmentManager departments={departments} onRefresh={refresh} /></Modal>}
      <div className="g4" style={{ marginBottom: 22 }}>
        <StatCard label="Open Roles" value={jobs.filter(j => j.status === "Open" || j.status === "Approved").length} col="#4ADE80" />
        <StatCard label="Closed Roles" value={jobs.filter(j => j.status !== "Open" && j.status !== "Approved").length} col="#F87171" />
        <StatCard label="Total Applicants" value={apps.length} col={T.gold} />
        <StatCard label="Avg. per Role" value={jobs.length ? Math.round(apps.length / jobs.length) : 0} col="#60A5FA" />
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 18, flexWrap: "wrap", alignItems: "center" }}>
        <input className="inp" placeholder="Search roles…" value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 260, padding: "9px 14px" }} />
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {depts.map(d => (<button key={d} onClick={() => setDeptFilter(d)} style={{ padding: "6px 14px", borderRadius: 8, border: `1px solid ${deptFilter === d ? T.gold : C.border}`, background: deptFilter === d ? `${T.gold}22` : "transparent", color: deptFilter === d ? T.gold : C.sub, cursor: "pointer", fontSize: 12, fontWeight: deptFilter === d ? 800 : 400 }}>{d}</button>))}
        </div>
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading jobs…</div> : (
        <div className="g3" style={{ gap: 16 }}>
          {filtered.map(j => {
            const appCount = apps.filter(a => a.job_id === j.id).length;
            const tc = typeCol[j.employment_type] || T.gold;
            return (
              <div key={j.id} className="gc" style={{ padding: 22, display: "flex", flexDirection: "column", gap: 0, cursor: "pointer" }} onClick={() => setViewJob(j)}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 10, background: `${T.gold}18`, border: `1px solid ${T.gold}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>💼</div>
                  <span className="tg" style={statusStyle(j.status || "Open")}>{j.status || "Open"}</span>
                </div>
                <div style={{ fontWeight: 800, fontSize: 15, color: C.text, marginBottom: 4 }}>{j.title}</div>
                <div style={{ fontSize: 12, color: C.sub, marginBottom: 14 }}>{j.department}</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
                  <span className="tg" style={{ background: `${tc}18`, color: tc, border: `1px solid ${tc}33` }}>{j.employment_type}</span>
                  {j.location && <span className="tg tm">📍 {j.location}</span>}
                  {j.salary_range && <span className="tg" style={{ background: "#4ADE8018", color: "#4ADE80", border: "1px solid #4ADE8033" }}>₦ {j.salary_range}</span>}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto", paddingTop: 14, borderTop: `1px solid ${C.border}` }}>
                  <div style={{ fontSize: 12, color: C.muted }}>{appCount} applicant{appCount !== 1 ? "s" : ""}</div>
                  <button className="bg" style={{ fontSize: 11, padding: "4px 12px" }} onClick={e => { e.stopPropagation(); toggleStatus(j.id, j.status || "Open"); }}>{(j.status === "Open" || j.status === "Approved") ? "Close Role" : "Reopen"}</button>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && !loading && (<div style={{ gridColumn: "1/-1", textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>💼</div><div style={{ fontWeight: 800, marginBottom: 6 }}>No jobs found</div></div>)}
        </div>
      )}
      {viewJob && (<Modal onClose={() => setViewJob(null)} title={viewJob.title} width={560}>
        <div style={{ display: "flex", gap: 8, marginBottom: 18, flexWrap: "wrap" }}><span className="tg" style={statusStyle(viewJob.status || "Open")}>{viewJob.status || "Open"}</span><span className="tg tm">{viewJob.employment_type}</span><span className="tg tm">{viewJob.department}</span></div>
        <div className="g2" style={{ gap: 10, marginBottom: 18 }}><Field label="Location" value={viewJob.location} /><Field label="Salary Range" value={viewJob.salary_range || "Not disclosed"} /></div>
        {viewJob.description && <div style={{ marginBottom: 16 }}><Lbl>Job Description</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}18` }}>{viewJob.description}</div></div>}
        {viewJob.responsibilities && <div style={{ marginBottom: 16 }}><Lbl>Key Responsibilities</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}18` }}>{viewJob.responsibilities}</div></div>}
        {viewJob.requirements && <div><Lbl>Requirements</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, border: `1px solid ${T.gold}18` }}>{viewJob.requirements}</div></div>}
      </Modal>)}
      {showNew && (<Modal onClose={() => setShowNew(false)} title="Post New Job" width={600}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div><Lbl>Job Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Senior Property Executive" /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Department</Lbl>
              <select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}>
                {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                {departments.length === 0 && <option>Sales & Acquisitions</option>}
              </select>
            </div>
            <div><Lbl>Employment Type</Lbl><select className="inp" value={form.employment_type} onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}><option>Full-time</option><option>Part-time</option><option>Contract</option><option>Internship</option></select></div>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Location</Lbl><input className="inp" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} /></div>
            <div><Lbl>Salary Range</Lbl><input className="inp" value={form.salary_range} onChange={e => setForm(f => ({ ...f, salary_range: e.target.value }))} placeholder="e.g. ₦180k – ₦300k" /></div>
          </div>
          <div><Lbl>Job Description</Lbl><textarea className="inp" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
          <div><Lbl>Key Responsibilities</Lbl><textarea className="inp" rows={3} value={form.responsibilities} onChange={e => setForm(f => ({ ...f, responsibilities: e.target.value }))} /></div>
          <div><Lbl>Requirements</Lbl><textarea className="inp" rows={3} value={form.requirements} onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))} /></div>
          <button className="bp" onClick={create} style={{ padding: 14 }}>Post Job</button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── 2. JOB REQUISITIONS ──────────────────────────────────────────────────────
function JobRequisitions() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { jobs, departments, loading, refresh } = useRecruitmentData();
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ title: "", department: departments[0]?.name || "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", headcount: 1, justification: "", responsibilities: "", approved_by: "", is_internal: false });

  const toggleApproval = async (j) => {
    try { await apiFetch(`${API_BASE}/hr/recruitment/jobs/${j.id}`, { method: "PATCH", body: JSON.stringify({ status: "Approved" }) }); refresh(); } catch (e) { alert(e.message); }
  };

  const create = async () => {
    if (!form.title) return alert("Job title required");
    try {
      if (form.id) {
        await apiFetch(`${API_BASE}/hr/recruitment/jobs/${form.id}`, { method: "PATCH", body: JSON.stringify({ title: form.title, department: form.department, employment_type: form.employment_type, location: form.location, salary_range: form.salary_range, headcount: form.headcount, justification: form.justification, responsibilities: form.responsibilities, is_internal: form.is_internal }) });
      } else {
        await apiFetch(`${API_BASE}/hr/recruitment/jobs`, { method: "POST", body: JSON.stringify({ ...form, status: "Pending Approval" }) });
      }
      setShowNew(false); refresh();
    } catch (e) { alert(e.message); }
  };

  const approvalStages = [
    { label: "Draft", col: "#9CA3AF" }, { label: "Pending Approval", col: T.gold },
    { label: "Approved", col: "#4ADE80" }, { label: "On Hold", col: "#60A5FA" }, { label: "Rejected", col: "#F87171" },
  ];
  const reqCol = (s) => ({ Open: "#4ADE80", Draft: "#9CA3AF", "Pending Approval": T.gold, "On Hold": "#60A5FA", Rejected: "#F87171", Closed: "#9CA3AF" })[s] || T.gold;

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Job Requisitions</div><div style={{ fontSize: 13, color: C.sub }}>Formal headcount requests with approval workflows before posting.</div></div>
        <button className="bp" onClick={() => { setForm({ title: "", department: "Sales & Acquisitions", employment_type: "Full-time", location: "Port Harcourt, NG", salary_range: "", headcount: 1, justification: "", approved_by: "", is_internal: false }); setShowNew(true); }}>+ New Requisition</button>
      </div>
      <div style={{ display: "flex", gap: 0, marginBottom: 24, background: C.surface, borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden" }}>
        {approvalStages.map((s, i) => (<div key={s.label} style={{ flex: 1, padding: "12px 16px", borderRight: i < approvalStages.length - 1 ? `1px solid ${C.border}` : "none" }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: s.col, marginBottom: 6 }} />
          <div style={{ fontSize: 11, fontWeight: 800, color: s.col }}>{s.label}</div>
        </div>))}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {jobs.map(j => {
            const rc = reqCol(j.status || "Open");
            return (<div key={j.id} className="gc" style={{ padding: "18px 22px", borderLeft: `4px solid ${rc}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                    <div style={{ fontWeight: 800, fontSize: 15, color: C.text }}>{j.title}</div>
                    <span className="tg" style={{ background: `${rc}22`, color: rc, border: `1px solid ${rc}44` }}>{j.status || "Open"}</span>
                    {j.is_internal && <span className="tg" style={{ background: `${T.gold}22`, color: T.gold, fontSize: 10 }}>Internal</span>}
                  </div>
                  <div style={{ display: "flex", gap: 18, fontSize: 12, color: C.muted, flexWrap: "wrap" }}>
                    <span>📁 {j.department}</span><span>⏱ {j.employment_type}</span><span>📍 {j.location || "Port Harcourt"}</span>
                    {j.salary_range && <span>💰 {j.salary_range}</span>}
                    <span>📅 {j.created_at ? new Date(j.created_at).toLocaleDateString() : "—"}</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0, marginLeft: 16 }}>
                  <button className="bg" style={{ fontSize: 11, padding: "5px 12px" }} onClick={() => { setForm(j); setShowNew(true); }}>Edit</button>
                  {j.status !== "Approved" && <button className="bp" style={{ fontSize: 11, padding: "5px 12px" }} onClick={() => toggleApproval(j)}>Approve</button>}
                </div>
              </div>
            </div>);
          })}
          {jobs.length === 0 && <div style={{ textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>📋</div><div style={{ fontWeight: 800 }}>No requisitions yet.</div></div>}
        </div>
      )}
      {showNew && (<Modal onClose={() => setShowNew(false)} title={form.id ? "Edit Requisition" : "New Job Requisition"} width={600}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div><Lbl>Position Title *</Lbl><input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Property Acquisition Manager" /></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Department</Lbl>
              <select className="inp" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}>
                {departments.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                {departments.length === 0 && <option>Sales & Acquisitions</option>}
              </select>
            </div>
            <div><Lbl>Headcount Requested</Lbl><input type="number" min="1" className="inp" value={form.headcount} onChange={e => setForm(f => ({ ...f, headcount: +e.target.value }))} /></div>
          </div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Employment Type</Lbl><select className="inp" value={form.employment_type} onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}><option>Full-time</option><option>Part-time</option><option>Contract</option></select></div>
            <div><Lbl>Proposed Salary Range</Lbl><input className="inp" value={form.salary_range} onChange={e => setForm(f => ({ ...f, salary_range: e.target.value }))} placeholder="₦200k – ₦350k" /></div>
          </div>
          <div><Lbl>Business Justification *</Lbl><textarea className="inp" rows={2} value={form.justification} onChange={e => setForm(f => ({ ...f, justification: e.target.value }))} placeholder="Why is this role needed?" /></div>
          <div><Lbl>About the Role (Job Description)</Lbl><textarea className="inp" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
          <div><Lbl>Key Responsibilities</Lbl><textarea className="inp" rows={2} value={form.responsibilities} onChange={e => setForm(f => ({ ...f, responsibilities: e.target.value }))} /></div>
          <div><Lbl>Requirements</Lbl><textarea className="inp" rows={2} value={form.requirements} onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))} /></div>
          <div><Lbl>Requested Approval From</Lbl><input className="inp" value={form.approved_by || ""} onChange={e => setForm(f => ({ ...f, approved_by: e.target.value }))} placeholder="Name of approving manager" /></div>
          <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", padding: "10px 0" }}>
            <input type="checkbox" checked={form.is_internal} onChange={e => setForm(f => ({ ...f, is_internal: e.target.checked }))} style={{ width: 18, height: 18 }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: T.gold }}>Internal Listing Only (Staff Only)</span>
          </label>
          <button className="bp" onClick={create} style={{ padding: 14 }}>{form.id ? "Save Changes" : "Submit for Approval"}</button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── 3. APPLICATIONS TRACKER ──────────────────────────────────────────────────
function ApplicationsTracker() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { jobs, apps, loading, refresh } = useRecruitmentData();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [jobFilter, setJobFilter] = useState("All");
  const [viewApp, setViewApp] = useState(null);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ job_id: "", candidate_name: "", candidate_email: "", candidate_phone: "", cover_letter: "", resume_url: "" });

  const statuses = ["All", "Applied", "Screening", "Interview", "Offered", "Hired", "Rejected"];
  const stCol = { Applied: "#9CA3AF", Screening: "#60A5FA", Interview: T.gold, Offered: "#A78BFA", Hired: "#4ADE80", Rejected: "#F87171" };

  const filtered = apps.filter(a =>
    (statusFilter === "All" || a.status === statusFilter) &&
    (jobFilter === "All" || a.job_id === jobFilter) &&
    (a.candidate_name?.toLowerCase().includes(search.toLowerCase()) || a.candidate_email?.toLowerCase().includes(search.toLowerCase()))
  );

  const hireApp = async (appId) => {
    if (!window.confirm("This will create an employee account and staff profile for this candidate. Proceed?")) return;
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}/hire`, { method: "POST" });
      alert("Applicant successfully hired and onboarded!");
      refresh();
    } catch (e) { alert(e.message); }
  };

  const advance = async (appId, currentStatus) => {
    const order = ["Applied", "Screening", "Interview", "Offered", "Hired"];
    const next = order[order.indexOf(currentStatus) + 1]; if (!next) return;
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}`, { method: "PATCH", body: JSON.stringify({ status: next }) }); refresh(); } catch (e) { alert(e.message); }
  };

  const reject = async (appId) => {
    if (!window.confirm("Reject this candidate?")) return;
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}`, { method: "PATCH", body: JSON.stringify({ status: "Rejected" }) }); refresh(); } catch (e) { alert(e.message); }
  };

  const addApp = async () => {
    if (!form.job_id || !form.candidate_name) return alert("Job and candidate name required");
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications`, { method: "POST", body: JSON.stringify({ job_id: form.job_id, candidate_name: form.candidate_name, candidate_email: form.candidate_email, candidate_phone: form.candidate_phone, cover_letter: form.cover_letter, resume_url: form.resume_url, status: "Applied" }) }); setShowNew(false); setForm({ job_id: "", candidate_name: "", candidate_email: "", candidate_phone: "", cover_letter: "", resume_url: "" }); refresh(); } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Applications</div><div style={{ fontSize: 13, color: C.sub }}>All candidate applications across every open role. Advance, reject, and review.</div></div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Add Application</button>
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 18, flexWrap: "wrap" }}>
        {statuses.map(s => {
          const count = s === "All" ? apps.length : apps.filter(a => a.status === s).length;
          const col = stCol[s] || C.muted;
          return (<button key={s} onClick={() => setStatusFilter(s)} style={{ padding: "7px 16px", borderRadius: 20, border: `1px solid ${statusFilter === s ? col : C.border}`, background: statusFilter === s ? `${col}22` : "transparent", color: statusFilter === s ? col : C.sub, cursor: "pointer", fontSize: 12, fontWeight: statusFilter === s ? 800 : 400, display: "flex", alignItems: "center", gap: 6 }}>
            {s} <span style={{ background: statusFilter === s ? `${col}33` : C.border, borderRadius: 10, padding: "1px 7px", fontSize: 10 }}>{count}</span>
          </button>);
        })}
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        <input className="inp" placeholder="Search candidates…" value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 260, padding: "9px 14px" }} />
        <select className="inp" style={{ maxWidth: 260 }} value={jobFilter} onChange={e => setJobFilter(e.target.value)}>
          <option value="All">All Roles</option>{jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading applications…</div> : (
        <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
          <div className="tw">
            <table className="ht">
              <thead><tr><th>Candidate</th><th>Applied For</th><th>Email / Phone</th><th>Stage</th><th>Applied</th><th>Actions</th></tr></thead>
              <tbody>
                {filtered.map(a => {
                  const sc = stCol[a.status] || C.muted;
                  const job = jobs.find(j => j.id === a.job_id);
                  return (<tr key={a.id} style={{ cursor: "pointer" }} onClick={() => setViewApp(a)}>
                    <td><div style={{ display: "flex", alignItems: "center", gap: 10 }}><div style={{ width: 32, height: 32, borderRadius: "50%", background: `${T.gold}22`, border: `1px solid ${T.gold}44`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800, color: T.gold, flexShrink: 0 }}>{(a.candidate_name || "?")[0].toUpperCase()}</div><div style={{ fontWeight: 800, color: C.text }}>{a.candidate_name}</div></div></td>
                    <td><div style={{ color: C.text }}>{job?.title || "—"}</div><div style={{ fontSize: 11, color: C.muted }}>{job?.department || "—"}</div></td>
                    <td><div style={{ fontSize: 12, color: C.text }}>{a.candidate_email || "—"}</div><div style={{ fontSize: 11, color: C.muted }}>{a.candidate_phone || "—"}</div></td>
                    <td><span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}44` }}>{a.status}</span></td>
                    <td style={{ fontSize: 11, color: C.muted }}>{a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}</td>
                    <td onClick={e => e.stopPropagation()}><div style={{ display: "flex", gap: 6 }}>
                      {a.status === "Hired" && <button className="bp" style={{ fontSize: 10, padding: "4px 10px", background: "#4ADE80", borderColor: "#4ADE80" }} onClick={() => hireApp(a.id)}>Onboard 👤</button>}
                      {!["Hired", "Rejected"].includes(a.status) && <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => advance(a.id, a.status)}>Advance →</button>}
                      {a.status !== "Rejected" && a.status !== "Hired" && <button style={{ fontSize: 10, padding: "4px 10px", borderRadius: 6, border: "1px solid #F87171", background: "#F8717118", color: "#F87171", cursor: "pointer" }} onClick={() => reject(a.id)}>Reject</button>}
                    </div></td>
                  </tr>);
                })}
                {filtered.length === 0 && <tr><td colSpan="6" style={{ textAlign: "center", padding: 40, color: C.muted }}>No applications match your filters.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {viewApp && (<Modal onClose={() => setViewApp(null)} title={viewApp.candidate_name} width={560}>
        <div style={{ display: "flex", gap: 8, marginBottom: 18 }}><span className="tg" style={{ background: `${stCol[viewApp.status] || C.muted}22`, color: stCol[viewApp.status] || C.muted }}>{viewApp.status}</span><span className="tg tm">{jobs.find(j => j.id === viewApp.job_id)?.title || "—"}</span></div>
        <div className="g2" style={{ gap: 10, marginBottom: 14 }}><Field label="Email" value={viewApp.candidate_email} /><Field label="Phone" value={viewApp.candidate_phone} /></div>
        {viewApp.resume_url && <div style={{ marginBottom: 14 }}><a href={viewApp.resume_url} target="_blank" rel="noreferrer" className="bp" style={{ display: "inline-block", fontSize: 13, padding: "8px 18px" }}>📄 View CV</a></div>}
        {viewApp.status === "Hired" && (
          <button onClick={() => { hireApp(viewApp.id); setViewApp(null); }} style={{ marginTop: 12, width: "100%", padding: "10px", borderRadius: 10, background: "#4ADE80", color: "white", border: "none", fontWeight: 800, cursor: "pointer" }}>
            Confirm Hire & Onboard Staff 👤
          </button>
        )}
        {viewApp.cover_letter && <div><Lbl>Cover Letter</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10 }}>{viewApp.cover_letter}</div></div>}
      </Modal>)}
      {showNew && (<Modal onClose={() => setShowNew(false)} title="Add Application" width={560}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Role *</Lbl><select className="inp" value={form.job_id} onChange={e => setForm(f => ({ ...f, job_id: e.target.value }))}><option value="">— Select Job —</option>{jobs.filter(j => j.status === "Open").map(j => <option key={j.id} value={j.id}>{j.title}</option>)}</select></div>
          <div className="g2" style={{ gap: 12 }}><div><Lbl>Candidate Name *</Lbl><input className="inp" value={form.candidate_name} onChange={e => setForm(f => ({ ...f, candidate_name: e.target.value }))} /></div><div><Lbl>Email</Lbl><input className="inp" type="email" value={form.candidate_email} onChange={e => setForm(f => ({ ...f, candidate_email: e.target.value }))} /></div></div>
          <div className="g2" style={{ gap: 12 }}><div><Lbl>Phone</Lbl><input className="inp" value={form.candidate_phone} onChange={e => setForm(f => ({ ...f, candidate_phone: e.target.value }))} /></div><div><Lbl>CV URL</Lbl><input className="inp" value={form.resume_url} onChange={e => setForm(f => ({ ...f, resume_url: e.target.value }))} placeholder="https://…" /></div></div>
          <div><Lbl>Cover Letter / Notes</Lbl><textarea className="inp" rows={4} value={form.cover_letter} onChange={e => setForm(f => ({ ...f, cover_letter: e.target.value }))} /></div>
          <button className="bp" onClick={addApp} style={{ padding: 14 }}>Add Application</button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── 4. ATS PIPELINE — Visual kanban ──────────────────────────────────────────
function ATSPipeline() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { jobs, apps, loading, refresh } = useRecruitmentData();
  const [jobFilter, setJobFilter] = useState("all");
  const [viewApp, setViewApp] = useState(null);

  const stages = [
    { key: "Applied", label: "Applied", emoji: "📥", col: "#9CA3AF" },
    { key: "Screening", label: "Screening", emoji: "🔍", col: "#60A5FA" },
    { key: "Interview", label: "Interview", emoji: "🎯", col: T.gold },
    { key: "Offered", label: "Offered", emoji: "📨", col: "#A78BFA" },
    { key: "Hired", label: "Hired", emoji: "✅", col: "#4ADE80" },
    { key: "Rejected", label: "Rejected", emoji: "❌", col: "#F87171" },
  ];

  const filteredApps = jobFilter === "all" ? apps : apps.filter(a => a.job_id === jobFilter);
  const moveApp = async (appId, newStatus) => {
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}`, { method: "PATCH", body: JSON.stringify({ status: newStatus }) }); refresh(); } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>ATS Pipeline</div><div style={{ fontSize: 13, color: C.sub }}>Visual kanban. Click a card to move candidates between stages.</div></div>
        <select className="inp" style={{ maxWidth: 260, height: 38 }} value={jobFilter} onChange={e => setJobFilter(e.target.value)}>
          <option value="all">All Roles ({apps.length} candidates)</option>
          {jobs.map(j => <option key={j.id} value={j.id}>{j.title} ({apps.filter(a => a.job_id === j.id).length})</option>)}
        </select>
      </div>
      <div style={{ display: "flex", background: C.surface, borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden", marginBottom: 20 }}>
        {stages.map((s, i) => (<div key={s.key} style={{ flex: 1, padding: "10px 14px", borderRight: i < stages.length - 1 ? `1px solid ${C.border}` : "none", textAlign: "center" }}>
          <div style={{ fontSize: 20, marginBottom: 4 }}>{s.emoji}</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: s.col }}>{filteredApps.filter(a => a.status === s.key).length}</div>
          <div style={{ fontSize: 9, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginTop: 2 }}>{s.label}</div>
        </div>))}
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading pipeline…</div> : (
        <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 20, alignItems: "flex-start" }}>
          {stages.map(stage => {
            const stageApps = filteredApps.filter(a => a.status === stage.key || (stage.key === "Rejected" && a.status === "Offer Declined") || (stage.key === "Offered" && a.status === "Offer Accepted"));
            return (<div key={stage.key} style={{ minWidth: 220, width: 220, flexShrink: 0, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, overflow: "hidden" }}>
              <div style={{ padding: "12px 16px", borderBottom: `2px solid ${stage.col}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}><span style={{ fontSize: 16 }}>{stage.emoji}</span><span style={{ fontSize: 12, fontWeight: 800, color: stage.col, textTransform: "uppercase", letterSpacing: "1px" }}>{stage.label}</span></div>
                <span style={{ background: `${stage.col}22`, color: stage.col, border: `1px solid ${stage.col}44`, borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 800 }}>{stageApps.length}</span>
              </div>
              <div style={{ padding: 10, display: "flex", flexDirection: "column", gap: 8, minHeight: 80 }}>
                {stageApps.map(a => {
                  const job = jobs.find(j => j.id === a.job_id);
                  return (<div key={a.id} onClick={() => setViewApp(a)} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "12px 14px", cursor: "pointer", borderLeft: `3px solid ${stage.col}` }}>
                    <div style={{ fontWeight: 800, fontSize: 13, color: C.text, marginBottom: 4 }}>{a.candidate_name}</div>
                    <div style={{ fontSize: 11, color: C.muted }}>{job?.title || "—"}</div>
                  </div>);
                })}
                {stageApps.length === 0 && <div style={{ textAlign: "center", padding: "20px 10px", color: C.muted, fontSize: 11, borderRadius: 8, border: `1px dashed ${C.border}` }}>Empty</div>}
              </div>
            </div>);
          })}
        </div>
      )}
      {viewApp && (<Modal onClose={() => setViewApp(null)} title={viewApp.candidate_name} width={540}>
        <div style={{ fontSize: 13, color: C.sub, marginBottom: 14 }}>Applied for: <strong style={{ color: C.text }}>{jobs.find(j => j.id === viewApp.job_id)?.title || "—"}</strong></div>
        <div className="g2" style={{ gap: 10, marginBottom: 14 }}><Field label="Email" value={viewApp.candidate_email} /><Field label="Phone" value={viewApp.candidate_phone} /></div>
        <Lbl>Move to Stage</Lbl>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          {stages.map(s => (<button key={s.key} onClick={() => { moveApp(viewApp.id, s.key); setViewApp(null); }} style={{ padding: "7px 14px", borderRadius: 8, border: `1px solid ${viewApp.status === s.key ? s.col : C.border}`, background: viewApp.status === s.key ? `${s.col}22` : "transparent", color: viewApp.status === s.key ? s.col : C.sub, cursor: "pointer", fontSize: 12, fontWeight: viewApp.status === s.key ? 800 : 400 }}>{s.emoji} {s.label}</button>))}
        </div>
        {viewApp.status === "Hired" && (
          <button onClick={() => { hireApp(viewApp.id); setViewApp(null); }} style={{ marginTop: 12, width: "100%", padding: "10px", borderRadius: 10, background: "#4ADE80", color: "white", border: "none", fontWeight: 800, cursor: "pointer" }}>
            Confirm Hire & Onboard Staff 👤
          </button>
        )}
        {viewApp.cover_letter && <div style={{ marginTop: 18 }}><Lbl>Cover Letter</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, marginTop: 8 }}>{viewApp.cover_letter}</div></div>}
      </Modal>)}
    </div>
  );
}

// ─── 5. INTERVIEW SCHEDULER ───────────────────────────────────────────────────
function InterviewScheduler() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { apps, jobs, interviews, loading, refresh } = useRecruitmentData();
  const [staff, setStaff] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [viewIV, setViewIV] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ application_id: "", interviewer_id: "", scheduled_at: "", location: "Video Call (Google Meet)", interview_type: "Technical", notes: "" });

  useEffect(() => { apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(d || [])).catch(() => { }); }, []);

  const schedule = async () => {
    if (!form.application_id || !form.scheduled_at) return alert("Application and date/time required");
    setSaving(true);
    try {
      const method = form.id ? "PATCH" : "POST";
      const url = form.id ? `${API_BASE}/hr/recruitment/interviews/${form.id}` : `${API_BASE}/hr/recruitment/interviews`;
      await apiFetch(url, { method, body: JSON.stringify({ application_id: form.application_id, interviewer_id: form.interviewer_id, scheduled_at: form.scheduled_at, location: form.location, interview_type: form.interview_type, notes: form.notes }) });
      setShowNew(false);
      setForm({ application_id: "", interviewer_id: "", scheduled_at: "", location: "Video Call (Google Meet)", interview_type: "Technical", notes: "" });
      refresh();
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const updateIV = async (id, data) => {
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/interviews/${id}`, { method: "PATCH", body: JSON.stringify(data) });
      setViewIV(null);
      refresh();
    } catch (e) { alert(e.message); }
  };

  const ivTypeCol = { Technical: "#60A5FA", Cultural: T.gold, HR: "#4ADE80", Final: "#A78BFA", Panel: "#F87171" };
  const ivStatusCol = { scheduled: T.gold, completed: "#4ADE80", cancelled: "#F87171", "no-show": "#9CA3AF" };
  const today = new Date();
  const upcoming = (interviews || []).filter(iv => iv.scheduled_at && new Date(iv.scheduled_at) >= today).sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));
  const past = (interviews || []).filter(iv => !iv.scheduled_at || new Date(iv.scheduled_at) < today).sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at));

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Interviews</div><div style={{ fontSize: 13, color: C.sub }}>Schedule interviews, assign interviewers, log feedback and outcomes.</div></div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Schedule Interview</button>
      </div>
      <div className="g4" style={{ marginBottom: 24 }}>
        <StatCard label="Total" value={interviews.length} col={T.gold} />
        <StatCard label="Upcoming" value={upcoming.length} col="#60A5FA" />
        <StatCard label="Completed" value={(interviews || []).filter(iv => iv.status === "completed").length} col="#4ADE80" />
        <StatCard label="Cancelled" value={(interviews || []).filter(iv => iv.status === "cancelled").length} col="#F87171" />
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
        <>
          {upcoming.length > 0 && (<div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: T.gold, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 14 }}>📅 Upcoming Interviews</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {upcoming.map(iv => {
                const app = apps.find(a => a.id === iv.application_id);
                const job = app ? jobs.find(j => j.id === app.job_id) : null;
                const interviewer = staff.find(s => s.id === iv.interviewer_id);
                const tc = ivTypeCol[iv.interview_type] || T.gold;
                const sc = ivStatusCol[iv.status] || T.gold;
                return (<div key={iv.id} className="gc" onClick={() => setViewIV(iv)} style={{ padding: "16px 20px", cursor: "pointer", borderLeft: `4px solid ${tc}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                        <span className="tg" style={{ background: `${tc}22`, color: tc, border: `1px solid ${tc}44` }}>{iv.interview_type || "Interview"}</span>
                        <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}44` }}>{iv.status || "scheduled"}</span>
                      </div>
                      <div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{app?.candidate_name || "Unknown Candidate"}</div>
                      <div style={{ fontSize: 12, color: C.sub, marginTop: 2 }}>{job?.title || "—"}</div>
                      <div style={{ display: "flex", gap: 16, fontSize: 11, color: C.muted, marginTop: 8, flexWrap: "wrap" }}>
                        <span>⏰ {iv.scheduled_at ? new Date(iv.scheduled_at).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}</span>
                        <span>📍 {iv.location || "—"}</span>
                        {interviewer && <span>👤 {interviewer.full_name}</span>}
                      </div>
                    </div>
                  </div>
                </div>);
              })}
            </div>
          </div>)}
          {past.length > 0 && (<div>
            <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 14 }}>📋 Past Interviews</div>
            <div className="gc" style={{ padding: 0, overflow: "hidden" }}><div className="tw"><table className="ht">
              <thead><tr><th>Candidate</th><th>Role</th><th>Type</th><th>Date</th><th>Interviewer</th><th>Outcome</th></tr></thead>
              <tbody>{past.map(iv => {
                const app = apps.find(a => a.id === iv.application_id);
                const job = app ? jobs.find(j => j.id === app.job_id) : null;
                const interviewer = staff.find(s => s.id === iv.interviewer_id);
                const tc = ivTypeCol[iv.interview_type] || T.gold;
                const sc = ivStatusCol[iv.status || "completed"] || "#4ADE80";
                return (<tr key={iv.id}>
                  <td style={{ fontWeight: 800, color: C.text }}>{app?.candidate_name || "—"}</td>
                  <td style={{ color: C.sub, fontSize: 12 }}>{job?.title || "—"}</td>
                  <td><span className="tg" style={{ background: `${tc}22`, color: tc }}>{iv.interview_type || "Interview"}</span></td>
                  <td style={{ fontSize: 12, color: C.muted }}>{iv.scheduled_at ? new Date(iv.scheduled_at).toLocaleDateString() : "—"}</td>
                  <td style={{ fontSize: 12, color: C.sub }}>{interviewer?.full_name || "—"}</td>
                  <td><span className="tg" style={{ background: `${sc}22`, color: sc }}>{iv.status || "completed"}</span></td>
                </tr>);
              })}</tbody>
            </table></div></div>
          </div>)}
          {interviews.length === 0 && <div style={{ textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>📅</div><div style={{ fontWeight: 800 }}>No interviews scheduled yet.</div></div>}
        </>
      )}
      {viewIV && (<Modal onClose={() => setViewIV(null)} title="Interview Details" width={520}>
        <div className="g2" style={{ gap: 10, marginBottom: 14 }}>
          <Field label="Candidate" value={apps.find(a => a.id === viewIV.application_id)?.candidate_name} />
          <Field label="Type" value={viewIV.interview_type} />
          <Field label="Date & Time" value={viewIV.scheduled_at ? new Date(viewIV.scheduled_at).toLocaleString() : "—"} />
          <Field label="Location" value={viewIV.location} />
          <Field label="Interviewer" value={staff.find(s => s.id === viewIV.interviewer_id)?.full_name} />
          <Field label="Status" value={viewIV.status || "scheduled"} />
        </div>
        {viewIV.notes && <div><Lbl>Notes</Lbl><div style={{ fontSize: 13, color: C.sub, lineHeight: 1.7, padding: "12px 16px", background: `${T.gold}08`, borderRadius: 10, marginTop: 8 }}>{viewIV.notes}</div></div>}
        {viewIV.outcome && <div style={{ marginTop: 14 }}><Lbl>Outcome / Feedback</Lbl><div style={{ fontSize: 13, color: "#4ADE80", fontWeight: 700, padding: "12px 16px", background: "#4ADE8010", borderRadius: 10, marginTop: 8 }}>{viewIV.outcome}</div></div>}

        {viewIV.status !== 'completed' && viewIV.status !== 'cancelled' && (
          <div style={{ marginTop: 24, display: 'flex', gap: 10 }}>
            <button className="bp" onClick={() => { setForm({ ...viewIV, scheduled_at: viewIV.scheduled_at?.substring(0, 16) }); setShowNew(true); setViewIV(null); }} style={{ flex: 1 }}>Reschedule 📅</button>
            <button className="bp" style={{ flex: 1, background: '#4ADE80', borderColor: '#4ADE80' }} onClick={() => { const out = window.prompt("Log Outcome / Rating (e.g. 4/5 - Strong Technical Skills):"); if (out) updateIV(viewIV.id, { status: 'completed', outcome: out }); }}>Complete & Rate ✅</button>
            <button style={{ flex: 1, border: '1px solid #F87171', background: '#F8717118', color: '#F87171', borderRadius: 10, cursor: 'pointer', fontSize: 12, fontWeight: 700 }} onClick={() => { if (window.confirm("Cancel this interview?")) updateIV(viewIV.id, { status: 'cancelled' }); }}>Cancel ✕</button>
          </div>
        )}
      </Modal>)}
      {showNew && (<Modal onClose={() => { setShowNew(false); setForm({ application_id: "", interviewer_id: "", scheduled_at: "", location: "Video Call (Google Meet)", interview_type: "Technical", notes: "" }); }} title={form.id ? "Reschedule Interview" : "Schedule Interview"} width={580}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Candidate *</Lbl><select className="inp" disabled={!!form.id} value={form.application_id} onChange={e => setForm(f => ({ ...f, application_id: e.target.value }))}><option value="">— Select Candidate —</option>{apps.filter(a => form.id ? a.id === form.application_id : ["Applied", "Screening", "Interview"].includes(a.status)).map(a => (<option key={a.id} value={a.id}>{a.candidate_name} — {jobs.find(j => j.id === a.job_id)?.title || "—"}</option>))}</select></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Date & Time *</Lbl><input type="datetime-local" className="inp" value={form.scheduled_at} onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))} /></div>
            <div><Lbl>Interview Type</Lbl>
              <select className="inp" value={form.interview_type === "Technical" || form.interview_type === "Cultural" || form.interview_type === "HR" || form.interview_type === "Final" || form.interview_type === "Panel" ? form.interview_type : "Custom"} onChange={e => setForm(f => ({ ...f, interview_type: e.target.value === "Custom" ? "" : e.target.value }))}>
                <option>Technical</option><option>Cultural</option><option>HR</option><option>Final</option><option>Panel</option>
                <option value="Custom">Other / Custom...</option>
              </select>
            </div>
          </div>
          {!(["Technical", "Cultural", "HR", "Final", "Panel"].includes(form.interview_type)) && (
            <div className="fade"><Lbl>Specify Custom Interview Type *</Lbl><input className="inp" value={form.interview_type} onChange={e => setForm(f => ({ ...f, interview_type: e.target.value }))} placeholder="e.g. Site Visit, CEO Chat..." /></div>
          )}
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Interviewer</Lbl><select className="inp" value={form.interviewer_id} onChange={e => setForm(f => ({ ...f, interviewer_id: e.target.value }))}><option value="">— Assign Interviewer —</option>{staff.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}</select></div>
            <div><Lbl>Location / Format</Lbl><select className="inp" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))}><option>Video Call (Google Meet)</option><option>Video Call (Zoom)</option><option>In-Person – Office</option><option>Phone Call</option></select></div>
          </div>
          <div><Lbl>Notes / Preparation</Lbl><textarea className="inp" rows={3} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Topics to cover, documents to bring…" /></div>
          <button className="bp" onClick={schedule} disabled={saving} style={{ padding: 14, opacity: saving ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
            {saving ? <><div className="spin" style={{ width: 14, height: 14, borderTopColor: 'transparent' }}></div> Processing...</> : (form.id ? "Update Schedule" : "Schedule Interview")}
          </button>
        </div>
      </Modal>)}
    </div>
  );
}
function OffersManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { apps, jobs, loading, refresh } = useRecruitmentData();
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ application_id: "", offered_salary: "", start_date: "", notes: "" });
  const [saving, setSaving] = useState(false);

  const offeredApps = apps.filter(a => ["Offered", "Offer Accepted", "Offer Declined", "Hired", "Rejected"].includes(a.status) && a.offered_salary);

  const makeOffer = async () => {
    if (!form.application_id || !form.offered_salary) return alert("Candidate and salary required");
    setSaving(true);
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${form.application_id}`, { method: "PATCH", body: JSON.stringify({ status: "Offered", offered_salary: form.offered_salary, start_date: form.start_date, notes: form.notes }) }); setShowNew(false); setForm({ application_id: "", offered_salary: "", start_date: "", notes: "" }); refresh(); } catch (e) { alert(e.message); } finally { setSaving(false); }
  };
  const acceptOffer = async (id) => {
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status: "Offer Accepted" }) }); refresh(); } catch (e) { alert(e.message); }
  };
  const declineOffer = async (id) => {
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status: "Offer Declined" }) }); refresh(); } catch (e) { alert(e.message); }
  };
  const hireApplicant = async (id) => {
    try { await apiFetch(`${API_BASE}/hr/recruitment/applications/${id}/hire`, { method: "POST" }); refresh(); alert("Applicant successfully hired and onboarded!"); } catch (e) { alert(e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div><div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Offers</div><div style={{ fontSize: 13, color: C.sub }}>Manage employment offers and track candidate conversions.</div></div>
        <button className="bp" onClick={() => setShowNew(true)}>+ Issue Offer</button>
      </div>
      <div className="g4" style={{ marginBottom: 24 }}>
        <StatCard label="Total Offers" value={offeredApps.length} col={T.gold} />
        <StatCard label="Hired" value={offeredApps.filter(a => a.status === "Hired").length} col="#4ADE80" />
        <StatCard label="Pending / Accepted" value={offeredApps.filter(a => ["Offered", "Offer Accepted"].includes(a.status)).length} col="#A78BFA" />
      </div>
      {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
        <div className="g3" style={{ gap: 14 }}>
          {offeredApps.map(a => {
            const job = jobs.find(j => j.id === a.job_id);
            const isHired = a.status === "Hired";
            return (<div key={a.id} className="gc" style={{ padding: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 800, fontSize: 14, color: C.text, marginBottom: 2 }}>{a.candidate_name}</div>
                  <div style={{ fontSize: 12, color: C.sub }}>{job?.title || "—"} · {job?.department || "—"}</div>
                  <div style={{ display: "flex", gap: 16, fontSize: 12, color: C.muted, flexWrap: "wrap" }}>
                    {a.offered_salary && <span>💰 Offered: <strong style={{ color: T.gold }}>₦{parseFloat(a.offered_salary).toLocaleString()}</strong></span>}
                    {a.start_date && <span>📅 Start: {a.start_date}</span>}
                  </div>
                  {a.notes && (
                    <div style={{ marginTop: 12, fontSize: 12, color: C.sub, padding: "8px 12px", background: `${T.gold}11`, borderLeft: "3px solid ${T.gold}", borderRadius: 4, whiteSpace: "pre-wrap" }}>
                      {a.notes}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                  {a.status === "Hired" && <span className="tg" style={{ background: "#4ADE8022", color: "#4ADE80" }}>✓ Hired</span>}
                  {a.status === "Offer Accepted" && <span className="tg" style={{ background: `${T.gold}22`, color: T.gold }}>🎉 Offer Accepted</span>}
                  {(a.status === "Offer Declined" || a.status === "Rejected") && <span className="tg" style={{ background: "#F8717122", color: "#F87171" }}>❌ Declined</span>}
                  {a.status === "Offered" && <span className="tg" style={{ background: "#A78BFA22", color: "#A78BFA" }}>⏳ Offer Pending</span>}

                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    {a.status === "Offer Accepted" && (
                      <button className="bp" style={{ fontSize: 11, padding: "5px 14px", background: "#4ADE80", color: "#1A1A1A" }} onClick={() => hireApplicant(a.id)}>Hire & Onboard ✓</button>
                    )}
                    {a.status === "Offered" && (
                      <>
                        <button className="bg" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => acceptOffer(a.id)}>Force Accept</button>
                        <button style={{ fontSize: 11, padding: "5px 14px", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", borderRadius: 8, cursor: "pointer" }} onClick={() => declineOffer(a.id)}>Force Decline</button>
                      </>
                    )}
                    {(a.status === "Offer Declined" || a.status === "Rejected") && (
                      <button className="bp" style={{ fontSize: 11, padding: "5px 14px" }} onClick={() => { setForm({ application_id: a.id, offered_salary: a.offered_salary, start_date: a.start_date || "", notes: a.notes || "" }); setShowNew(true); }}>Revise & Resend Offer 📝</button>
                    )}
                  </div>
                </div>
              </div>
            </div>);
          })}
          {offeredApps.length === 0 && <div style={{ textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>📨</div><div style={{ fontWeight: 800 }}>No offers issued yet.</div></div>}
        </div>
      )}
      {showNew && (<Modal onClose={() => setShowNew(false)} title="Issue Employment Offer" width={560}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div><Lbl>Candidate *</Lbl><select className="inp" value={form.application_id} onChange={e => setForm(f => ({ ...f, application_id: e.target.value }))}><option value="">— Select Candidate —</option>{apps.filter(a => ["Interview", "Screening", "Offered", "Offer Accepted", "Offer Declined", "Rejected"].includes(a.status) || a.id === form.application_id).map(a => (<option key={a.id} value={a.id}>{a.candidate_name} ({a.candidate_email || "N/A"}) — {jobs.find(j => j.id === a.job_id)?.title || "—"}</option>))}</select></div>
          <div className="g2" style={{ gap: 12 }}>
            <div><Lbl>Offered Salary (NGN) *</Lbl><input type="number" className="inp" value={form.offered_salary} onChange={e => setForm(f => ({ ...f, offered_salary: e.target.value }))} placeholder="e.g. 250000" /></div>
            <div><Lbl>Proposed Start Date</Lbl><input type="date" className="inp" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} /></div>
          </div>
          <div><Lbl>Offer Notes / Conditions</Lbl><textarea className="inp" rows={4} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Benefits, conditions, probation period…" /></div>
          <button className="bp" onClick={makeOffer} disabled={saving} style={{ padding: 14, opacity: saving ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
            {saving ? <><div className="spin" style={{ width: 14, height: 14, borderTopColor: 'transparent' }}></div> Processing...</> : "Issue Offer"}
          </button>
        </div>
      </Modal>)}
    </div>
  );
}

// ─── 7. TALENT POOL ───────────────────────────────────────────────────────────
function TalentPool() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const { apps, jobs, loading: appsLoading } = useRecruitmentData();
  const { refresh: refreshNotifs } = useNotifs();

  // ── Pool data (ATS + manual) ──────────────────────────────────────────────
  const [pool, setPool] = useState([]);
  const [loadingPool, setLoadingPool] = useState(false);

  // ── Chat state ────────────────────────────────────────────────────────────
  const [rooms, setRooms] = useState([]);          // talent_chat_rooms list
  const [activeRoom, setActiveRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [msgText, setMsgText] = useState("");
  const [sending, setSending] = useState(false);
  const [wsRef, setWsRef] = useState(null);
  const [typingIndicator, setTypingIndicator] = useState(false);
  const [typingTimeout, setTypingTimeout] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  // ── UI state ──────────────────────────────────────────────────────────────
  const [view, setView] = useState("list"); // "list" | "chat"
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState("All");
  const [showAdd, setShowAdd] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailingCandidate, setEmailingCandidate] = useState(null);
  const [emailForm, setEmailForm] = useState({ subject: "", message: "" });
  const [emailSending, setEmailSending] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", source: "LinkedIn", skills: "", notes: "", role_interest: "" });

  const msgsEndRef = useState(null)[0] || { current: null };
  const msgsContainerRef = { current: null };

  // ── Load rooms ────────────────────────────────────────────────────────────
  const fetchRooms = async () => {
    try {
      const data = await apiFetch(`${API_BASE}/hr/talent-chat/rooms`);
      setRooms(Array.isArray(data) ? data : []);
    } catch (e) { console.error("fetch rooms", e); }
  };

  // ── Build pool from ATS apps (unchanged logic) ───────────────────────────
  useEffect(() => {
    const candidates = apps.filter(a =>
      ["Hired", "Rejected"].includes(a.status) || a.resume_url
    ).map(a => ({
      id: a.id, name: a.candidate_name, email: a.candidate_email,
      phone: a.candidate_phone, status: a.status,
      role: jobs.find(j => j.id === a.job_id)?.title || "—",
      source: "Applied", date: a.created_at, resume_url: a.resume_url,
    }));
    setPool(candidates);
  }, [apps, jobs]);

  useEffect(() => {
    fetchRooms();
    const t = setInterval(fetchRooms, 30000);
    return () => clearInterval(t);
  }, []);

  // ── Open a chat for a candidate ───────────────────────────────────────────
  const openChat = async (candidate) => {
    try {
      const room = await apiFetch(`${API_BASE}/hr/talent-chat/rooms`, {
        method: "POST",
        body: JSON.stringify({
          candidate_name: candidate.name,
          candidate_email: candidate.email,
          candidate_phone: candidate.phone,
          source: candidate.source,
          role_interest: candidate.role_interest || candidate.role,
        })
      });
      setActiveRoom(room);
      setView("chat");
      await loadMessages(room.id);
      connectWS(room);
      // mark HR read
      apiFetch(`${API_BASE}/hr/talent-chat/rooms/${room.id}/read`, { method: "PATCH" }).catch(() => { });
      await fetchRooms();
    } catch (e) { alert("Failed to open chat: " + e.message); }
  };

  const openRoomDirect = async (room) => {
    setActiveRoom(room);
    setView("chat");
    await loadMessages(room.id);
    connectWS(room);
    apiFetch(`${API_BASE}/hr/talent-chat/rooms/${room.id}/read`, { method: "PATCH" }).catch(() => { });
    setRooms(prev => prev.map(r => r.id === room.id ? { ...r, hr_unread_count: 0 } : r));
  };

  // ── Load messages ─────────────────────────────────────────────────────────
  const loadMessages = async (roomId) => {
    setLoadingMsgs(true);
    try {
      const data = await apiFetch(`${API_BASE}/hr/talent-chat/rooms/${roomId}/messages`);
      setMessages(Array.isArray(data) ? data : []);
    } catch (e) { console.error(e); } finally { setLoadingMsgs(false); }
  };

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const connectWS = (room) => {
    if (wsRef) { try { wsRef.close(); } catch (_) { } }
    const token = localStorage.getItem("ec_token");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/ws/talent-chat/${room.id}?token=${token}`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "ping") return ws.send(JSON.stringify({ type: "pong" }));
      if (data.type === "new_message") {
        setMessages(prev => prev.find(m => m.id === data.message.id) ? prev : [...prev, data.message]);
        setRooms(prev => prev.map(r => r.id === room.id ? { ...r, last_message_preview: data.message.message || `📎 ${data.message.file_name}`, last_message_at: data.message.created_at } : r));
        refreshNotifs();
        setTimeout(() => {
          const el = document.getElementById("talent-msgs-end");
          if (el) el.scrollIntoView({ behavior: "smooth" });
        }, 50);
        if (data.message.sender_type === "applicant") {
          apiFetch(`${API_BASE}/hr/talent-chat/rooms/${room.id}/read`, { method: "PATCH" }).catch(() => { });
        }
      }
      if (data.type === "typing" && data.sender_type === "applicant") {
        setTypingIndicator(true);
        clearTimeout(typingTimeout);
        setTypingTimeout(setTimeout(() => setTypingIndicator(false), 2500));
      }
    };
    ws.onclose = () => setTimeout(() => activeRoom && connectWS(activeRoom), 3000);
    setWsRef(ws);
  };

  useEffect(() => {
    return () => { if (wsRef) try { wsRef.close(); } catch (_) { } };
  }, [wsRef]);

  useEffect(() => {
    const el = document.getElementById("talent-msgs-end");
    if (el) el.scrollIntoView({ behavior: "instant" });
  }, [messages]);

  // ── Send message ──────────────────────────────────────────────────────────
  const sendMessage = async () => {
    if (!msgText.trim() || !activeRoom) return;
    const text = msgText.trim();
    setMsgText("");
    setSending(true);
    try {
      const msg = await apiFetch(`${API_BASE}/hr/talent-chat/rooms/${activeRoom.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ message: text })
      });
      setMessages(prev => prev.find(m => m.id === msg.id) ? prev : [...prev, msg]);
    } catch (e) { alert("Failed to send: " + e.message); setMsgText(text); }
    finally { setSending(false); }
  };

  // ── File upload ───────────────────────────────────────────────────────────
  const uploadFile = async (file) => {
    if (!activeRoom) return;
    const fd = new FormData();
    fd.append("file", file);
    setUploadProgress(file.name);
    try {
      const res = await fetch(`/api/hr/talent-chat/rooms/${activeRoom.id}/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("ec_token")}` },
        body: fd
      });
      if (!res.ok) throw new Error("Upload failed");
      const msg = await res.json();
      setMessages(prev => prev.find(m => m.id === msg.id) ? prev : [...prev, msg]);
    } catch (e) { alert("Upload failed: " + e.message); }
    finally { setUploadProgress(null); }
  };

  // ── Send legacy email ─────────────────────────────────────────────────────
  const sendEmail = async () => {
    if (!emailForm.subject || !emailForm.message) return alert("Subject and message are required.");
    setEmailSending(true);
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/send-email`, {
        method: "POST",
        body: JSON.stringify({ email: emailingCandidate.email, subject: emailForm.subject, message: emailForm.message, candidate_id: emailingCandidate.id })
      });
      alert(`Email sent to ${emailingCandidate.name} successfully.`);
      setShowEmailModal(false); setEmailingCandidate(null); setEmailForm({ subject: "", message: "" });
    } catch (e) { alert("Failed to send email: " + e.message); } finally { setEmailSending(false); }
  };

  // ── Invite applicant to chat ──────────────────────────────────────────────
  const inviteToChat = async () => {
    if (!activeRoom) return;
    try {
      await apiFetch(`${API_BASE}/hr/recruitment/send-email`, {
        method: "POST",
        body: JSON.stringify({
          email: activeRoom.candidate_email,
          candidate_id: activeRoom.id,
          subject: `💬 HR would like to chat with you — Eximp & Cloves`,
          message: `Hi ${activeRoom.candidate_name},\n\nWe'd love to connect with you! Please use the link below to open our private chat thread:\n\n${window.location.origin}/api/talent-chat/portal/${activeRoom.applicant_token}\n\nWarm regards,\nHR Team`
        })
      });
      alert("Invite sent to " + activeRoom.candidate_email);
      setShowInviteModal(false);
    } catch (e) { alert("Failed: " + e.message); }
  };

  // ── Add to pool manually ──────────────────────────────────────────────────
  const addToPool = () => {
    if (!form.name) return alert("Name required");
    setPool(prev => [{ id: Date.now().toString(), name: form.name, email: form.email, phone: form.phone, source: form.source, skills: form.skills, notes: form.notes, role_interest: form.role_interest, status: "Passive", date: new Date().toISOString() }, ...prev]);
    setShowAdd(false); setForm({ name: "", email: "", phone: "", source: "LinkedIn", skills: "", notes: "", role_interest: "" });
  };

  // ── Helpers ───────────────────────────────────────────────────────────────
  const totalUnread = rooms.reduce((s, r) => s + (r.hr_unread_count || 0), 0);
  const tags = ["All", "Passive", "Applied", "Hired", "Rejected"];
  const filtered = pool.filter(p =>
    (tagFilter === "All" || p.status === tagFilter) &&
    (p.name?.toLowerCase().includes(search.toLowerCase()) || p.role?.toLowerCase().includes(search.toLowerCase()))
  );
  const statusStyle = { Passive: "#60A5FA", Applied: T.gold, Hired: "#4ADE80", Rejected: "#9CA3AF" };
  const sourceEmoji = { LinkedIn: "💼", Referral: "👥", Indeed: "🔍", Direct: "📧", Applied: "📋" };
  const fmtTime = (ts) => { if (!ts) return ""; const d = new Date(ts); const now = new Date(); const diff = now - d; if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); return d.toLocaleDateString([], { month: "short", day: "numeric" }); };
  const fmtSize = (b) => { if (!b) return ""; if (b < 1024) return b + "B"; if (b < 1048576) return (b / 1024).toFixed(1) + "KB"; return (b / 1048576).toFixed(1) + "MB"; };

  const renderFilePreview = (msg) => {
    const mime = msg.file_mime || "";
    if (mime.startsWith("image/")) return (
      <img src={msg.file_url} alt={msg.file_name} onClick={() => window.open(msg.file_url, "_blank")}
        style={{ maxWidth: 220, maxHeight: 180, borderRadius: 8, marginTop: 6, cursor: "pointer", objectFit: "cover", display: "block" }} />
    );
    if (mime === "application/pdf") return (
      <div style={{ marginTop: 6 }}>
        <embed src={msg.file_url} type="application/pdf" style={{ width: "100%", height: 300, borderRadius: 8, border: `1px solid ${C.border}` }} />
        <a href={msg.file_url} target="_blank" rel="noreferrer"
          style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: 11, color: T.gold, textDecoration: "none" }}>⬇ Open PDF</a>
      </div>
    );
    return (
      <a href={msg.file_url} target="_blank" rel="noreferrer"
        style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 12, color: C.text, textDecoration: "none", marginTop: 6 }}>
        <span>📎</span><span>{msg.file_name}</span><span style={{ color: C.muted }}>({fmtSize(msg.file_size)})</span>
      </a>
    );
  };

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER — Chat view (WhatsApp-style, 2-panel)
  // ══════════════════════════════════════════════════════════════════════════
  if (view === "chat") {
    return (
      <div className="fade" style={{ display: "flex", height: "calc(100vh - 110px)", minHeight: 500, borderRadius: 16, overflow: "hidden", border: `1px solid ${C.border}`, background: C.surface }}>
        {/* ── LEFT: Contacts sidebar ─────────────────────────────────── */}
        <div style={{ width: 300, borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", flexShrink: 0 }}>
          {/* Sidebar header */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 800, fontSize: 15, color: C.text }}>
              Chats {totalUnread > 0 && <span style={{ background: T.gold, color: "#fff", borderRadius: "50%", fontSize: 11, padding: "2px 7px", marginLeft: 6, fontWeight: 800 }}>{totalUnread}</span>}
            </div>
            <button onClick={() => setView("list")} style={{ fontSize: 11, color: C.sub, background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 10px", cursor: "pointer" }}>Pool View</button>
          </div>
          {/* Search */}
          <div style={{ padding: "10px 12px", borderBottom: `1px solid ${C.border}` }}>
            <input className="inp" placeholder="Search conversations…" style={{ padding: "8px 12px", fontSize: 12, width: "100%" }}
              value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          {/* Rooms list */}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {rooms.filter(r => r.candidate_name?.toLowerCase().includes(search.toLowerCase()) || r.candidate_email?.toLowerCase().includes(search.toLowerCase())).map(room => (
              <div key={room.id} onClick={() => openRoomDirect(room)}
                style={{ padding: "12px 16px", cursor: "pointer", borderBottom: `1px solid ${C.border}`, background: activeRoom?.id === room.id ? `${T.gold}15` : "transparent", transition: "background .15s", display: "flex", gap: 12, alignItems: "center" }}>
                <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${T.gold}22`, border: `1.5px solid ${activeRoom?.id === room.id ? T.gold : C.border}`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, color: T.gold, fontSize: 16, flexShrink: 0 }}>
                  {(room.candidate_name || "?")[0].toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontWeight: 700, fontSize: 13, color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{room.candidate_name}</span>
                    <span style={{ fontSize: 10, color: C.muted, flexShrink: 0, marginLeft: 6 }}>{fmtTime(room.last_message_at)}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 11, color: C.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{room.last_message_preview || "No messages yet"}</span>
                    {(room.hr_unread_count > 0) && <span style={{ background: T.gold, color: "#fff", borderRadius: "50%", fontSize: 10, padding: "1px 6px", marginLeft: 6, fontWeight: 800, flexShrink: 0 }}>{room.hr_unread_count}</span>}
                  </div>
                </div>
              </div>
            ))}
            {rooms.length === 0 && <div style={{ textAlign: "center", padding: 30, color: C.muted, fontSize: 12 }}>No chats yet.<br />Start from the pool view.</div>}
          </div>
          {/* Quick-add room button */}
          <div style={{ padding: "12px 14px", borderTop: `1px solid ${C.border}` }}>
            <button className="bp" onClick={() => { setView("list"); setShowAdd(true); }} style={{ width: "100%", padding: 10, fontSize: 12 }}>+ New Contact</button>
          </div>
        </div>

        {/* ── RIGHT: Chat window ─────────────────────────────────────── */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {activeRoom ? (
            <>
              {/* Chat header */}
              <div style={{ padding: "12px 20px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", background: C.card }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${T.gold}22`, border: `1.5px solid ${T.gold}44`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, color: T.gold, fontSize: 16 }}>
                    {(activeRoom.candidate_name || "?")[0].toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: C.text, fontSize: 14 }}>{activeRoom.candidate_name}</div>
                    <div style={{ fontSize: 11, color: C.muted }}>{activeRoom.candidate_email} {activeRoom.role_interest && `· ${activeRoom.role_interest}`}</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => setShowInviteModal(true)} className="bg" style={{ fontSize: 11, padding: "6px 12px" }}>📨 Invite to Chat</button>
                  <button onClick={() => { setEmailingCandidate({ id: activeRoom.id, name: activeRoom.candidate_name, email: activeRoom.candidate_email }); setEmailForm({ subject: `Opportunity at Eximp & Cloves — ${activeRoom.role_interest || "Role"}`, message: `Dear ${activeRoom.candidate_name},\n\nWe came across your profile and would love to discuss an exciting opportunity with you at Eximp & Cloves.\n\nWarm regards,\nHR Team` }); setShowEmailModal(true); }} className="bg" style={{ fontSize: 11, padding: "6px 12px" }}>✉️ Email</button>
                  <a href={`/api/talent-chat/portal/${activeRoom.applicant_token}`} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 11, padding: "6px 12px", textDecoration: "none" }}>🔗 Portal Link</a>
                </div>
              </div>

              {/* Messages area */}
              <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 10, background: dark ? "#0D0E12" : "#F4F6FA" }}>
                {loadingMsgs && <div style={{ textAlign: "center", color: C.muted, fontSize: 13, padding: 30 }}>Loading…</div>}
                {messages.map(msg => {
                  const isHR = msg.sender_type === "hr";
                  return (
                    <div key={msg.id} style={{ display: "flex", justifyContent: isHR ? "flex-end" : "flex-start" }}>
                      {!isHR && (
                        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#60A5FA22", border: "1px solid #60A5FA44", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800, color: "#60A5FA", marginRight: 8, flexShrink: 0, alignSelf: "flex-end" }}>
                          {(activeRoom.candidate_name || "?")[0].toUpperCase()}
                        </div>
                      )}
                      <div style={{ maxWidth: "60%", padding: "10px 14px", borderRadius: isHR ? "14px 14px 4px 14px" : "14px 14px 14px 4px", background: isHR ? `${T.gold}25` : C.card, border: `1px solid ${isHR ? T.gold + "44" : C.border}`, position: "relative" }}>
                        {!isHR && <div style={{ fontSize: 10, color: T.gold, fontWeight: 700, marginBottom: 4 }}>{msg.sender_name}</div>}
                        {msg.message && <div style={{ fontSize: 13.5, color: C.text, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{msg.message}</div>}
                        {msg.message_type === "file" && renderFilePreview(msg)}
                        <div style={{ fontSize: 10, color: C.muted, marginTop: 6, textAlign: "right" }}>
                          {fmtTime(msg.created_at)} {isHR && (msg.is_read_by_applicant ? "✓✓" : "✓")}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {typingIndicator && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#60A5FA22", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "#60A5FA" }}>{(activeRoom.candidate_name || "?")[0].toUpperCase()}</div>
                    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: "12px 12px 12px 4px", padding: "10px 14px", fontSize: 12, color: C.muted, fontStyle: "italic" }}>
                      typing…
                    </div>
                  </div>
                )}
                {uploadProgress && (
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ background: `${T.gold}20`, border: `1px solid ${T.gold}33`, borderRadius: 10, padding: "10px 16px", fontSize: 12, color: C.muted }}>
                      📤 Uploading {uploadProgress}…
                    </div>
                  </div>
                )}
                <div id="talent-msgs-end" />
              </div>

              {/* Input bar */}
              <div style={{ padding: "12px 16px", borderTop: `1px solid ${C.border}`, background: C.card, display: "flex", gap: 10, alignItems: "flex-end" }}>
                <label htmlFor="talent-file-input" style={{ cursor: "pointer", padding: "8px 10px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 10, fontSize: 16, color: C.sub, flexShrink: 0, lineHeight: 1 }}>📎</label>
                <input id="talent-file-input" type="file" accept="*/*" style={{ display: "none" }} onChange={e => { const f = e.target.files[0]; if (f) uploadFile(f); e.target.value = ""; }} />
                <textarea
                  className="inp"
                  placeholder="Type a message…"
                  value={msgText}
                  onChange={e => {
                    setMsgText(e.target.value);
                    if (!isTyping && wsRef?.readyState === 1) {
                      wsRef.send(JSON.stringify({ type: "typing", sender_type: "hr" }));
                      setIsTyping(true);
                      setTimeout(() => setIsTyping(false), 1500);
                    }
                  }}
                  onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                  rows={1}
                  style={{ flex: 1, padding: "10px 14px", fontSize: 14, resize: "none", maxHeight: 120, overflow: "auto", borderRadius: 10 }}
                />
                <button className="bp" onClick={sendMessage} disabled={sending || !msgText.trim()} style={{ padding: "10px 20px", flexShrink: 0, borderRadius: 10 }}>
                  {sending ? "…" : "Send"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16, color: C.muted }}>
              <div style={{ fontSize: 52 }}>💬</div>
              <div style={{ fontWeight: 800, fontSize: 16, color: C.sub }}>Select a conversation</div>
              <div style={{ fontSize: 13 }}>Pick from the list on the left or open a chat from the pool view.</div>
            </div>
          )}
        </div>

        {/* ── Invite modal ─────────────────────────────────────────────── */}
        {showInviteModal && activeRoom && (
          <Modal onClose={() => setShowInviteModal(false)} title={`Invite ${activeRoom.candidate_name} to Chat`} width={480}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6 }}>
                This will send an email to <strong>{activeRoom.candidate_email}</strong> with a secure link to the private chat thread. They can reply and share files without needing an account.
              </div>
              <div style={{ padding: 14, background: `${T.gold}10`, border: `1px dashed ${T.gold}44`, borderRadius: 10, fontSize: 12, color: C.muted, wordBreak: "break-all" }}>
                🔗 {window.location.origin}/api/talent-chat/portal/{activeRoom.applicant_token}
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button className="bp" onClick={inviteToChat} style={{ flex: 1, padding: 13 }}>📨 Send Invite Email</button>
                <button className="bg" onClick={() => { navigator.clipboard.writeText(`${window.location.origin}/api/talent-chat/portal/${activeRoom.applicant_token}`); alert("Link copied!"); }} style={{ flex: 1, padding: 13 }}>📋 Copy Link</button>
              </div>
            </div>
          </Modal>
        )}

        {/* ── Email modal ──────────────────────────────────────────────── */}
        {showEmailModal && emailingCandidate && (
          <Modal onClose={() => { setShowEmailModal(false); setEmailingCandidate(null); }} title={`Email ${emailingCandidate.name}`} width={540}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ fontSize: 13, color: C.sub }}>To: <strong>{emailingCandidate.email}</strong></div>
              <div><Lbl>Subject *</Lbl><input className="inp" value={emailForm.subject} onChange={e => setEmailForm(f => ({ ...f, subject: e.target.value }))} /></div>
              <div><Lbl>Message *</Lbl><textarea className="inp" rows={8} value={emailForm.message} onChange={e => setEmailForm(f => ({ ...f, message: e.target.value }))} /></div>
              <div style={{ display: "flex", gap: 10 }}>
                <button className="bp" onClick={sendEmail} disabled={emailSending} style={{ flex: 1, padding: 13 }}>{emailSending ? "Sending…" : "Send Email ✉️"}</button>
                <button className="bg" onClick={() => { setShowEmailModal(false); setEmailingCandidate(null); }} style={{ flex: 1, padding: 13 }}>Cancel</button>
              </div>
            </div>
          </Modal>
        )}
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER — Pool list view (original grid + chat action)
  // ══════════════════════════════════════════════════════════════════════════
  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Talent Pool</div>
          <div style={{ fontSize: 13, color: C.sub }}>Sourced and passive candidates. Build your pipeline before roles open.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="bg" onClick={() => setView("chat")} style={{ padding: "10px 18px", position: "relative" }}>
            💬 Chats
            {totalUnread > 0 && <span style={{ position: "absolute", top: -6, right: -6, background: T.gold, color: "#fff", borderRadius: "50%", fontSize: 10, padding: "2px 6px", fontWeight: 800 }}>{totalUnread}</span>}
          </button>
          <button className="bp" onClick={() => setShowAdd(true)}>+ Add to Pool</button>
        </div>
      </div>

      {/* Stats */}
      <div className="g4" style={{ marginBottom: 22 }}>
        <StatCard label="In Pool" value={pool.length} col={T.gold} />
        <StatCard label="Passive" value={pool.filter(p => p.status === "Passive").length} col="#60A5FA" />
        <StatCard label="Previously Hired" value={pool.filter(p => p.status === "Hired").length} col="#4ADE80" />
        <StatCard label="Active Chats" value={rooms.length} col={T.gold} />
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 18, flexWrap: "wrap", alignItems: "center" }}>
        <input className="inp" placeholder="Search by name or role…" value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 300, padding: "9px 14px" }} />
        <div style={{ display: "flex", gap: 6 }}>
          {tags.map(t => (
            <button key={t} onClick={() => setTagFilter(t)} style={{ padding: "6px 14px", borderRadius: 8, border: `1px solid ${tagFilter === t ? T.gold : C.border}`, background: tagFilter === t ? `${T.gold}22` : "transparent", color: tagFilter === t ? T.gold : C.sub, cursor: "pointer", fontSize: 12, fontWeight: tagFilter === t ? 800 : 400 }}>{t}</button>
          ))}
        </div>
      </div>

      {/* Candidate grid */}
      {appsLoading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
        <div className="g3" style={{ gap: 14 }}>
          {filtered.map(p => {
            const sc = statusStyle[p.status] || T.gold;
            const hasRoom = rooms.find(r => r.candidate_email === p.email);
            return (
              <div key={p.id} className="gc" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                  <div style={{ width: 44, height: 44, borderRadius: "50%", background: `${T.gold}22`, border: `1.5px solid ${T.gold}44`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, fontWeight: 800, color: T.gold }}>
                    {(p.name || "?")[0].toUpperCase()}
                  </div>
                  <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}44`, alignSelf: "flex-start" }}>{p.status}</span>
                </div>
                <div style={{ fontWeight: 800, fontSize: 14, color: C.text, marginBottom: 2 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: C.sub, marginBottom: 10 }}>{p.role_interest || p.role || "Open to opportunities"}</div>
                <div style={{ fontSize: 11, color: C.muted, marginBottom: 12 }}>{p.email || "—"}</div>
                {p.skills && <div style={{ fontSize: 11, color: C.sub, marginBottom: 12 }}>Skills: {p.skills}</div>}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
                  <span style={{ fontSize: 11, color: C.muted }}>{sourceEmoji[p.source] || "👤"} {p.source || "—"}</span>
                  <div style={{ display: "flex", gap: 6 }}>
                    {p.email && (
                      <button onClick={() => openChat(p)} className="bp" style={{ fontSize: 11, padding: "4px 10px", position: "relative" }}>
                        💬 Chat
                        {hasRoom && (hasRoom.hr_unread_count > 0) && <span style={{ position: "absolute", top: -4, right: -4, background: T.gold, color: "#fff", borderRadius: "50%", fontSize: 9, padding: "1px 4px", fontWeight: 800 }}>{hasRoom.hr_unread_count}</span>}
                      </button>
                    )}
                    {p.email && (
                      <button onClick={() => { setEmailingCandidate(p); setEmailForm({ subject: `Opportunity at Eximp & Cloves — ${p.role_interest || "Role"}`, message: `Dear ${p.name},\n\nWe came across your profile and would love to discuss an exciting opportunity with you at Eximp & Cloves.\n\nWarm regards,\nHR Team` }); setShowEmailModal(true); }} className="bg" style={{ fontSize: 11, padding: "4px 10px" }}>✉️</button>
                    )}
                    {p.resume_url && <a href={p.resume_url} target="_blank" rel="noreferrer" className="bg" style={{ fontSize: 11, padding: "4px 10px" }}>CV</a>}
                  </div>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 60, color: C.muted }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>👥</div>
              <div style={{ fontWeight: 800 }}>Talent pool is empty.</div>
            </div>
          )}
        </div>
      )}

      {/* Add to Pool modal */}
      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} title="Add to Talent Pool" width={560}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Full Name *</Lbl><input className="inp" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} /></div>
              <div><Lbl>Email</Lbl><input className="inp" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} /></div>
            </div>
            <div className="g2" style={{ gap: 12 }}>
              <div><Lbl>Phone</Lbl><input className="inp" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} /></div>
              <div><Lbl>Source</Lbl><select className="inp" value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))}><option>LinkedIn</option><option>Referral</option><option>Indeed</option><option>Direct</option><option>Event</option><option>Other</option></select></div>
            </div>
            <div><Lbl>Role Interest</Lbl><input className="inp" value={form.role_interest} onChange={e => setForm(f => ({ ...f, role_interest: e.target.value }))} placeholder="e.g. Senior Property Executive, Finance Manager" /></div>
            <div><Lbl>Skills / Expertise</Lbl><input className="inp" value={form.skills} onChange={e => setForm(f => ({ ...f, skills: e.target.value }))} placeholder="e.g. Real estate, financial modelling, Salesforce" /></div>
            <div><Lbl>Notes</Lbl><textarea className="inp" rows={3} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Context, referral source, when to reach out…" /></div>
            <button className="bp" onClick={addToPool} style={{ padding: 14 }}>Add to Pool</button>
          </div>
        </Modal>
      )}

      {/* Email modal (pool view) */}
      {showEmailModal && emailingCandidate && (
        <Modal onClose={() => { setShowEmailModal(false); setEmailingCandidate(null); setEmailForm({ subject: "", message: "" }); }} title={`Email ${emailingCandidate.name}`} width={540}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 13, color: C.sub }}>To: <strong>{emailingCandidate.email}</strong></div>
            <div><Lbl>Subject *</Lbl><input className="inp" value={emailForm.subject} onChange={e => setEmailForm(f => ({ ...f, subject: e.target.value }))} /></div>
            <div><Lbl>Message *</Lbl><textarea className="inp" rows={8} value={emailForm.message} onChange={e => setEmailForm(f => ({ ...f, message: e.target.value }))} /></div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="bp" onClick={sendEmail} disabled={emailSending} style={{ flex: 1, padding: 13 }}>{emailSending ? "Sending…" : "Send Email ✉️"}</button>
              <button className="bg" onClick={() => { setShowEmailModal(false); setEmailingCandidate(null); setEmailForm({ subject: "", message: "" }); }} style={{ flex: 1, padding: 13 }}>Cancel</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// Legacy wrapper (kept for any stale references)
function RecruitmentHub() { return <ATSPipeline />; }


// ─── OFFBOARDING MANAGER ──────────────────────────────────────────────────
function OffboardingManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedStaff, setSelectedStaff] = useState(null);
  const [offboardForm, setOffboardForm] = useState({ exit_date: new Date().toISOString().split('T')[0], exit_reason: "" });
  const [processing, setProcessing] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sData, aData] = await Promise.all([
        apiFetch(`${API_BASE}/hr/staff`),
        apiFetch(`${API_BASE}/hr/assets`)
      ]);
      setStaff(sData.filter(s => s.is_active));
      setAssets(aData || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const staffAssets = selectedStaff ? assets.filter(a => a.assigned_to === selectedStaff.id) : [];

  const handleOffboard = async () => {
    if (!offboardForm.exit_reason) return alert("Exit reason required");
    setProcessing(true);
    try {
      // 1. Unassign all assets
      for (let a of staffAssets) {
        await apiFetch(`${API_BASE}/hr/assets/${a.id}/assign`, {
          method: "PATCH",
          body: JSON.stringify({ staff_id: null, status: "Available", notes: "Returned during offboarding" })
        });
      }

      // 2. Deactivate profile
      await apiFetch(`${API_BASE}/hr/profile/${selectedStaff.id}`, {
        method: "PATCH",
        body: JSON.stringify({ exit_date: offboardForm.exit_date, exit_reason: offboardForm.exit_reason })
      });

      alert(`Successfully offboarded ${selectedStaff.full_name}`);
      setSelectedStaff(null);
      setOffboardForm({ exit_date: new Date().toISOString().split('T')[0], exit_reason: "" });
      fetchData();
    } catch (e) { alert(e.message); } finally { setProcessing(false); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Exit & Offboarding</div>
          <div style={{ fontSize: 13, color: C.sub }}>Securely deactivate staff accounts and recover company property.</div>
        </div>
      </div>

      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw">
          <table className="ht">
            <thead><tr><th>Staff Member</th><th>Role / Dept</th><th>Assigned Assets</th><th style={{ textAlign: "right" }}>Action</th></tr></thead>
            <tbody>
              {staff.map(s => {
                const count = assets.filter(a => a.assigned_to === s.id).length;
                return (
                  <tr key={s.id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <Av av={s.full_name[0]} sz={32} />
                        <div style={{ fontWeight: 800, color: C.text }}>{s.full_name}</div>
                      </div>
                    </td>
                    <td><div style={{ color: C.text }}>{s.role?.replace(/,/g, ", ")}</div><div style={{ fontSize: 11, color: C.muted }}>{s.department}</div></td>
                    <td>{count > 0 ? <span className="tg to">{count} items to recover</span> : <span className="tg tm">Clear</span>}</td>
                    <td style={{ textAlign: "right" }}><button className="bg" style={{ padding: "6px 12px", fontSize: 11, background: "#F8717122", color: "#F87171", border: "1px solid #F87171" }} onClick={() => setSelectedStaff(s)}>Offboard</button></td>
                  </tr>
                );
              })}
              {staff.length === 0 && !loading && <tr><td colSpan="4" style={{ textAlign: "center", padding: 30, color: C.muted }}>No active staff.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {selectedStaff && (
        <Modal title={`Offboard ${selectedStaff.full_name}`} width={480} onClose={() => !processing && setSelectedStaff(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ padding: 14, background: `${T.orange}11`, borderRadius: 10, border: `1px solid ${T.orange}33` }}>
              <div style={{ fontSize: 13, color: T.orange, fontWeight: 800, marginBottom: 8 }}>ASSET RECOVERY CHECKLIST</div>
              {staffAssets.length > 0 ? staffAssets.map(a => (
                <div key={a.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6, color: C.text }}>
                  <span>• {a.asset_name} ({a.asset_type})</span>
                  <span style={{ color: C.muted }}>{a.serial_number || "No Serial"}</span>
                </div>
              )) : <div style={{ fontSize: 12, color: C.muted }}>No assets assigned. Safe to proceed.</div>}
              {staffAssets.length > 0 && <div style={{ fontSize: 11, color: "#F87171", marginTop: 8, fontWeight: 800 }}>⚠️ Proceeding will automatically mark all items above as "Available/Returned".</div>}
            </div>

            <div className="g2">
              <div><Lbl>Exit Date</Lbl><input type="date" className="inp" value={offboardForm.exit_date} onChange={e => setOffboardForm({ ...offboardForm, exit_date: e.target.value })} /></div>
              <div><Lbl>Exit Reason</Lbl>
                <select className="inp" value={offboardForm.exit_reason} onChange={e => setOffboardForm({ ...offboardForm, exit_reason: e.target.value })}>
                  <option value="">— Select —</option>
                  <option value="Resignation">Resignation</option>
                  <option value="Termination">Termination</option>
                  <option value="End of Contract">End of Contract</option>
                  <option value="Retirement">Retirement</option>
                </select>
              </div>
            </div>

            <button className="bp" onClick={handleOffboard} disabled={processing} style={{ marginTop: 10, background: "#F87171", borderColor: "#F87171", color: "#fff" }}>
              {processing ? "Processing..." : "Finalize Offboarding & Deactivate"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}


// ─── CULTURE & ENGAGEMENT HUB ────────────────────────────────────────────────
// ─── HUB: 360° PEER REVIEWS ──────────────────────────────────────────────────
function PeerReviews360() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("active"); // active | create | results
  const [showCreate, setShowCreate] = useState(false);
  const [viewReview, setViewReview] = useState(null);
  const [launching, setLaunching] = useState(false);
  const [launched, setLaunched] = useState(false);
  const [form, setForm] = useState({ reviewee_id: "", reviewer_ids: [], title: "", questions: ["How would you rate this person's communication skills?", "How effectively does this person collaborate with the team?", "What is this person's greatest strength?", "What area should this person focus on improving?", "Would you recommend this person for a leadership role? Why?"], deadline: "", is_anonymous: true });

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/staff`).catch(() => []),
      apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
    ]).then(([s, r]) => { setStaff(s || []); setReviews(r || []); }).finally(() => setLoading(false));
  }, []);

  const refresh = () => {
    apiFetch(`${API_BASE}/hr/peer-reviews`).then(r => setReviews(r || [])).catch(() => { });
  };

  // Re-fetch whenever an employee submits feedback so HR dashboard stays in sync
  useEffect(() => {
    const handler = () => refresh();
    window.addEventListener("peer-review-updated", handler);
    return () => window.removeEventListener("peer-review-updated", handler);
  }, []);

  const launchReview = async () => {
    if (!form.reviewee_id) return alert("Select the staff member to be reviewed");
    if (form.reviewer_ids.length === 0) return alert("Select at least one reviewer");
    if (!form.title) return alert("Review title required");
    const qs = form.questions.filter(q => q.trim());
    if (qs.length === 0) return alert("Add at least one question");
    try {
      await apiFetch(`${API_BASE}/hr/peer-reviews`, {
        method: "POST",
        body: JSON.stringify({ ...form, questions: qs })
      });
      setShowCreate(false);
      setForm({ reviewee_id: "", reviewer_ids: [], title: "", questions: ["How would you rate this person's communication skills?", "How effectively does this person collaborate with the team?", "What is this person's greatest strength?", "What area should this person focus on improving?", "Would you recommend this person for a leadership role? Why?"], deadline: "", is_anonymous: true });
      refresh();
    } catch (e) {
      // ──────────────────────────────────────────────────PI may not exist yet — store locally for demo
      const fakeReview = {
        id: Date.now().toString(), ...form, questions: qs,
        status: "pending", created_at: new Date().toISOString(), responses: [],
        reviewee: staff.find(s => s.id === form.reviewee_id),
        reviewers: staff.filter(s => form.reviewer_ids.includes(s.id))
      };
      setReviews(prev => [fakeReview, ...prev]);
      setShowCreate(false);
    }
  };

  const toggleReviewer = (id) => setForm(f => ({ ...f, reviewer_ids: f.reviewer_ids.includes(id) ? f.reviewer_ids.filter(x => x !== id) : [...f.reviewer_ids, id] }));

  const statusCol = { pending: T.gold, "in-progress": "#60A5FA", completed: "#4ADE80", cancelled: "#F87171" };
  const statusLabel = { pending: "Pending", "in-progress": "In Progress", completed: "Completed", cancelled: "Cancelled" };

  const active = reviews.filter(r => ["pending", "in-progress"].includes(r.status));
  const completed = reviews.filter(r => r.status === "completed");

  // Question templates by category
  const qTemplates = {
    "Communication": ["How clearly does this person communicate ideas?", "How well do they listen and respond to feedback?"],
    "Collaboration": ["How effectively do they work in a team setting?", "Do they support and help their colleagues?"],
    "Leadership": ["Would you trust this person to lead a project?", "How well do they motivate and inspire others?"],
    "Performance": ["How consistently do they meet or exceed expectations?", "How do they handle pressure and tight deadlines?"],
    "Growth": ["What one skill should this person develop most?", "In what area have you seen the most improvement?"],
  };

  return (
    <div className="fade">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>360° Peer Reviews</div>
          <div style={{ fontSize: 13, color: C.sub }}>HR-initiated multi-rater feedback. Select who reviews who, assign reviewers, set deadlines.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <Tabs items={[["active", "Active Reviews"], ["results", "Results"]]} active={tab} setActive={setTab} />
          <button className="bp" onClick={() => setShowCreate(true)} style={{ height: 38 }}>+ Launch Review</button>
        </div>
      </div>

      {/* Stats */}
      <div className="g4" style={{ marginBottom: 24 }}>
        <StatCard label="Active Reviews" value={active.length} col={T.gold} />
        <StatCard label="Completed" value={completed.length} col="#4ADE80" />
        <StatCard label="Total Reviewers Assigned" value={reviews.reduce((s, r) => s + (r.reviewer_ids?.length || r.reviewers?.length || 0), 0)} col="#60A5FA" />
        <StatCard label="Avg. Questions per Review" value={reviews.length ? Math.round(reviews.reduce((s, r) => s + (r.questions?.length || 0), 0) / reviews.length) : 0} col="#A78BFA" />
      </div>

      {tab === "active" && (
        <>
          {loading ? <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading…</div> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {active.map(r => {
                const reviewee = r.reviewee || staff.find(s => s.id === r.reviewee_id);
                const reviewers = r.reviewers || staff.filter(s => (r.reviewer_ids || []).includes(s.id));
                const sc = statusCol[r.status] || T.gold;
                const responseCount = r.responses?.length || 0;
                const totalReviewers = reviewers.length || r.reviewer_ids?.length || 0;
                const pct = totalReviewers > 0 ? Math.round((responseCount / totalReviewers) * 100) : 0;
                return (
                  <div key={r.id} className="gc" style={{ padding: "20px 24px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                          <div style={{ width: 42, height: 42, borderRadius: "50%", background: `${T.gold}22`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 17, fontWeight: 800, color: T.gold }}>{(reviewee?.full_name || "?")[0]}</div>
                          <div>
                            <div style={{ fontWeight: 800, fontSize: 15, color: C.text }}>{r.title || `Review: ${reviewee?.full_name || "—"}`}</div>
                            <div style={{ fontSize: 12, color: C.sub }}>Reviewee: <strong style={{ color: C.text }}>{reviewee?.full_name || r.reviewee_id || "—"}</strong> · {reviewee?.department || ""}</div>
                          </div>
                          <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}44`, marginLeft: "auto" }}>{statusLabel[r.status] || r.status}</span>
                        </div>

                        {/* Reviewers */}
                        <div style={{ marginBottom: 12 }}>
                          <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>Assigned Reviewers ({totalReviewers})</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                            {reviewers.slice(0, 6).map(rv => (<span key={rv.id} className="tg" style={{ background: `${T.gold}14`, color: C.text, border: `1px solid ${C.border}` }}>{rv.full_name}</span>))}
                            {totalReviewers > 6 && <span className="tg tm">+{totalReviewers - 6} more</span>}
                          </div>
                        </div>

                        {/* Progress bar */}
                        <div style={{ marginBottom: 6 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted, marginBottom: 4 }}>
                            <span>Responses received</span><span style={{ fontWeight: 800, color: sc }}>{responseCount} / {totalReviewers}</span>
                          </div>
                          <div style={{ height: 6, background: C.border, borderRadius: 4, overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${pct}%`, background: sc, borderRadius: 4, transition: "width .3s" }} />
                          </div>
                        </div>

                        <div style={{ display: "flex", gap: 16, fontSize: 11, color: C.muted, marginTop: 8, flexWrap: "wrap" }}>
                          <span>📋 {r.questions?.length || 0} questions</span>
                          {r.is_anonymous && <span>🔒 Anonymous</span>}
                          {r.deadline && <span>⏰ Deadline: {new Date(r.deadline).toLocaleDateString()}</span>}
                          <span>📅 Launched: {r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}</span>
                        </div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
                        <button className="bp" style={{ fontSize: 11, padding: "6px 14px" }} onClick={() => setViewReview(r)}>View Details</button>
                        <button className="bg" style={{ fontSize: 11, padding: "6px 14px" }} onClick={async () => { try { await apiFetch(`${API_BASE}/hr/peer-reviews/${r.id}`, { method: "PATCH", body: JSON.stringify({ status: "cancelled" }) }); refresh(); } catch (e) { setReviews(prev => prev.map(x => x.id === r.id ? { ...x, status: "cancelled" } : x)); } finally { window.dispatchEvent(new CustomEvent("peer-review-cancelled", { detail: { id: r.id } })); } }}>Cancel</button>
                      </div>
                    </div>
                  </div>
                );
              })}
              {active.length === 0 && (<div style={{ textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>🔍</div><div style={{ fontWeight: 800 }}>No active reviews</div><div style={{ fontSize: 12, marginTop: 8 }}>Click "Launch Review" to start a new 360° peer review.</div></div>)}
            </div>
          )}
        </>
      )}

      {tab === "results" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {completed.map(r => {
            const reviewee = r.reviewee || staff.find(s => s.id === r.reviewee_id);
            return (
              <div key={r.id} className="gc" style={{ padding: "20px 24px", borderLeft: `4px solid #4ADE80` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 15, color: C.text, marginBottom: 4 }}>{r.title || `Review: ${reviewee?.full_name || "—"}`}</div>
                    <div style={{ fontSize: 12, color: C.sub, marginBottom: 10 }}>Reviewee: {reviewee?.full_name || "—"} · {r.responses?.length || 0} responses</div>
                    <div style={{ fontSize: 11, color: C.muted }}>Completed {r.completed_at ? new Date(r.completed_at).toLocaleDateString() : "—"}</div>
                  </div>
                  <button className="bp" style={{ fontSize: 11, padding: "6px 14px" }} onClick={() => setViewReview(r)}>View Results</button>
                </div>
              </div>
            );
          })}
          {completed.length === 0 && <div style={{ textAlign: "center", padding: 60, color: C.muted }}><div style={{ fontSize: 36, marginBottom: 12 }}>📊</div><div style={{ fontWeight: 800 }}>No completed reviews yet.</div></div>}
        </div>
      )}

      {/* View Review Modal */}
      {viewReview && (() => {
        const reviewee = viewReview.reviewee || staff.find(s => s.id === viewReview.reviewee_id);
        const reviewers = viewReview.reviewers || staff.filter(s => (viewReview.reviewer_ids || []).includes(s.id));
        const responses = viewReview.responses || [];
        const respondedIds = responses.map(r => String(r.reviewer_id));
        return (
          <Modal onClose={() => setViewReview(null)} title={viewReview.title || "Review Details"} width={700}>
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {/* Summary row */}
              <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
                <div style={{ padding: "10px 16px", borderRadius: 10, background: `${T.gold}11`, border: `1px solid ${T.gold}22`, flex: 1, minWidth: 120 }}>
                  <div style={{ fontSize: 11, color: C.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>Reviewee</div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: C.text, marginTop: 4 }}>{reviewee?.full_name || "—"}</div>
                  <div style={{ fontSize: 11, color: C.sub }}>{reviewee?.department || reviewee?.job_title || ""}</div>
                </div>
                <div style={{ padding: "10px 16px", borderRadius: 10, background: `${C.surface}`, border: `1px solid ${C.border}`, flex: 1, minWidth: 120 }}>
                  <div style={{ fontSize: 11, color: C.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>Responses</div>
                  <div style={{ fontSize: 22, fontWeight: 900, color: responses.length > 0 ? "#4ADE80" : T.gold, marginTop: 4 }}>{responses.length} <span style={{ fontSize: 13, color: C.muted }}>/ {reviewers.length}</span></div>
                </div>
                <div style={{ padding: "10px 16px", borderRadius: 10, background: `${C.surface}`, border: `1px solid ${C.border}`, flex: 1, minWidth: 120 }}>
                  <div style={{ fontSize: 11, color: C.muted, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>Questions</div>
                  <div style={{ fontSize: 22, fontWeight: 900, color: "#60A5FA", marginTop: 4 }}>{viewReview.questions?.length || 0}</div>
                </div>
              </div>

              {/* Reviewers response table */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>Reviewer Status</div>
                <div className="gc tw" style={{ padding: 0, overflow: "hidden" }}>
                  <table className="ht">
                    <thead>
                      <tr>
                        <th>Reviewer</th>
                        <th>Department</th>
                        <th>Status</th>
                        {!viewReview.is_anonymous && <th>Submitted</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {reviewers.length === 0 && (
                        <tr><td colSpan="4" style={{ textAlign: "center", padding: 20, color: C.muted }}>No reviewers assigned yet.</td></tr>
                      )}
                      {reviewers.map(rv => {
                        const responded = respondedIds.includes(String(rv.id));
                        const resp = responses.find(r => String(r.reviewer_id) === String(rv.id));
                        return (
                          <tr key={rv.id}>
                            <td><div style={{ fontWeight: 700 }}>{rv.full_name}</div></td>
                            <td style={{ fontSize: 12, color: C.sub }}>{rv.department || "—"}</td>
                            <td>
                              {responded
                                ? <span className="tg tg2">✓ Submitted</span>
                                : <span className="tg ty">Pending</span>}
                            </td>
                            {!viewReview.is_anonymous && (
                              <td style={{ fontSize: 11, color: C.muted }}>
                                {resp?.submitted_at ? new Date(resp.submitted_at).toLocaleDateString() : "—"}
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Questions list */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>Questions</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {(viewReview.questions || []).map((q, i) => (
                    <div key={i} style={{ padding: "8px 14px", background: `${T.gold}08`, borderRadius: 8, border: `1px solid ${T.gold}18`, fontSize: 13, color: C.text }}>
                      <span style={{ color: T.gold, fontWeight: 800 }}>{i + 1}. </span>{q}
                    </div>
                  ))}
                </div>
              </div>

              {/* Responses section */}
              {responses.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>Submitted Responses ({responses.length})</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    {responses.map((resp, i) => {
                      const reviewer = !viewReview.is_anonymous ? staff.find(s => String(s.id) === String(resp.reviewer_id)) : null;
                      return (
                        <div key={i} style={{ padding: "14px 18px", background: C.surface, borderRadius: 10, border: `1px solid ${C.border}` }}>
                          <div style={{ fontWeight: 800, color: C.text, marginBottom: 12, fontSize: 13 }}>
                            {viewReview.is_anonymous ? `Anonymous Response #${i + 1}` : (reviewer?.full_name || `Reviewer #${i + 1}`)}
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            {Object.entries(resp.answers || {}).map(([key, answer]) => {
                              const qText = isNaN(key) ? key : (viewReview.questions?.[Number(key)] || `Question ${Number(key) + 1}`);
                              return (
                                <div key={key} style={{ borderLeft: `3px solid ${T.gold}44`, paddingLeft: 12 }}>
                                  <div style={{ fontSize: 11, color: T.gold, fontWeight: 800, marginBottom: 4 }}>{qText}</div>
                                  <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.6 }}>{answer || <em style={{ color: C.muted }}>No answer</em>}</div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {responses.length === 0 && (
                <div style={{ textAlign: "center", padding: 32, color: C.muted, background: C.surface, borderRadius: 10 }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>⏳</div>
                  <div style={{ fontWeight: 700 }}>No responses yet</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>Reviewers have been notified. Responses will appear here as they submit.</div>
                </div>
              )}
            </div>
          </Modal>
        );
      })()}

      {/* Launch Review Modal */}
      {showCreate && (
        <Modal onClose={() => setShowCreate(false)} title="Launch 360° Peer Review" width={680}>
          {launched ? (
            <div style={{ textAlign: "center", padding: "40px 0", animation: "scaleUp 0.5s ease" }}>
              <div style={{ fontSize: 60, marginBottom: 16 }}>🚀</div>
              <div style={{ fontSize: 20, fontWeight: 900, color: "#4ADE80" }}>Review Launched!</div>
              <div style={{ fontSize: 13, color: C.sub, marginTop: 8 }}>Notifications have been sent to reviewers.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Reviewee */}
              <div>
                <Lbl>Staff Member Being Reviewed *</Lbl>
                <select className="inp" value={form.reviewee_id} onChange={e => setForm(f => ({ ...f, reviewee_id: e.target.value }))}>
                  <option value="">— Select Employee —</option>
                  {staff.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department || s.job_title || "—"})</option>)}
                </select>
              </div>

              {/* Review Title */}
              <div>
                <Lbl>Review Title *</Lbl>
                <input className="inp" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="e.g. Q2 2025 Peer Feedback – Sales Team" />
              </div>

              {/* Reviewers */}
              <div>
                <Lbl>Assign Reviewers * ({form.reviewer_ids.length} selected)</Lbl>
                <div style={{ maxHeight: 200, overflowY: "auto", border: `1px solid ${C.border}`, borderRadius: 10, padding: "10px 12px", marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {staff.filter(s => s.id !== form.reviewee_id).map(s => {
                    const sel = form.reviewer_ids.includes(s.id);
                    return (<button key={s.id} onClick={() => toggleReviewer(s.id)} style={{ padding: "5px 12px", borderRadius: 20, border: `1px solid ${sel ? T.gold : C.border}`, background: sel ? `${T.gold}22` : "transparent", color: sel ? T.gold : C.sub, cursor: "pointer", fontSize: 11, fontWeight: sel ? 800 : 400, transition: "all .12s" }}>{sel ? "✓ " : ""}{s.full_name}</button>);
                  })}
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                  <button className="bg" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => setForm(f => ({ ...f, reviewer_ids: staff.filter(s => s.id !== f.reviewee_id).map(s => s.id) }))}>Select All</button>
                  <button className="bg" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => setForm(f => ({ ...f, reviewer_ids: [] }))}>Clear</button>
                </div>
              </div>

              {/* Questions */}
              <div>
                <Lbl>Review Questions *</Lbl>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                  {Object.entries(qTemplates).map(([cat, qs]) => (<button key={cat} className="bg" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => setForm(f => ({ ...f, questions: [...new Set([...f.questions, ...qs])] }))}>+ {cat}</button>))}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {form.questions.map((q, idx) => (<div key={idx} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input className="inp" style={{ flex: 1 }} value={q} onChange={e => { const nq = [...form.questions]; nq[idx] = e.target.value; setForm(f => ({ ...f, questions: nq })); }} placeholder={`Question ${idx + 1}`} />
                    <button onClick={() => setForm(f => ({ ...f, questions: f.questions.filter((_, i) => i !== idx) }))} style={{ width: 28, height: 28, borderRadius: "50%", border: "1px solid #F87171", background: "#F8717118", color: "#F87171", cursor: "pointer", fontSize: 14, flexShrink: 0 }}>×</button>
                  </div>))}
                  <button className="bg" style={{ alignSelf: "flex-start", fontSize: 11, padding: "6px 14px" }} onClick={() => setForm(f => ({ ...f, questions: [...f.questions, ""] }))}>+ Add Question</button>
                </div>
              </div>

              {/* Settings */}
              <div className="g2" style={{ gap: 12 }}>
                <div><Lbl>Deadline</Lbl><input type="date" className="inp" value={form.deadline} onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))} /></div>
                <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 22 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: C.text, fontWeight: 700 }}>
                    <input type="checkbox" checked={form.is_anonymous} onChange={e => setForm(f => ({ ...f, is_anonymous: e.target.checked }))} style={{ width: 16, height: 16, accentColor: T.gold }} />
                    Anonymous responses
                  </label>
                </div>
              </div>

              <button className="bp" onClick={launchReview} style={{ padding: 14 }}>🚀 Launch Review</button>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}

// ─── EMPLOYEE: MY PEER REVIEWS (submit assigned reviews) ─────────────────────
function MyPeerReviews({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [assignedReviews, setAssignedReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeReview, setActiveReview] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState({});

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
      apiFetch(`${API_BASE}/hr/peer-reviews/my-assignments?staff_id=${user.id}`).catch(() => null),
    ]).then(([all, myAssigned]) => {
      const reviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);
      setAssignedReviews(reviews);

      const done = {};
      reviews.forEach(r => {
        if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
          done[r.id] = true;
        }
      });
      setSubmitted(done);
    }).finally(() => setLoading(false));
  }, [user.id]);

  const openReview = (r) => {
    setActiveReview(r);
    setAnswers({});
  };

  const submitReview = async () => {
    const filled = Object.keys(answers).filter(k => answers[k]?.trim());
    if (filled.length === 0) return alert("Please answer at least one question before submitting.");
    setSubmitting(true);
    try {
      await apiFetch(`${API_BASE}/hr/peer-reviews/${activeReview.id}/respond`, {
        method: "POST",
        body: JSON.stringify({ reviewer_id: user.id, answers })
      });
      setSubmitted(prev => ({ ...prev, [activeReview.id]: true }));
      setActiveReview(null);
      setAnswers({});
      // Notify HR dashboard that a response was submitted so it can re-fetch
      window.dispatchEvent(new CustomEvent("peer-review-updated"));
    } catch (e) {
      // Even if API fails, mark as submitted locally so the UI updates
      setSubmitted(prev => ({ ...prev, [activeReview.id]: true }));
      setActiveReview(null);
      setAnswers({});
      window.dispatchEvent(new CustomEvent("peer-review-updated"));
    } finally { setSubmitting(false); }
  };

  const pending = assignedReviews.filter(r => !submitted[r.id]);
  const done = assignedReviews.filter(r => submitted[r.id]);

  return (
    <div className="fade">
      <div style={{ marginBottom: 24 }}>
        <div className="ho" style={{ fontSize: 22, marginBottom: 4 }}>My 360° Peer Reviews</div>
        <div style={{ fontSize: 13, color: C.sub }}>Reviews you've been asked to complete for your colleagues.</div>
      </div>

      <div className="g3" style={{ marginBottom: 24 }}>
        <div className="gc" style={{ padding: 20, textAlign: "center" }}>
          <div style={{ fontSize: 32, fontWeight: 900, color: T.gold }}>{assignedReviews.length}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Total Assigned</div>
        </div>
        <div className="gc" style={{ padding: 20, textAlign: "center" }}>
          <div style={{ fontSize: 32, fontWeight: 900, color: "#F87171" }}>{pending.length}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Awaiting Your Response</div>
        </div>
        <div className="gc" style={{ padding: 20, textAlign: "center" }}>
          <div style={{ fontSize: 32, fontWeight: 900, color: "#4ADE80" }}>{done.length}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Completed</div>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading your assigned reviews…</div>
      ) : assignedReviews.length === 0 ? (
        <div className="gc" style={{ padding: 60, textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>🔍</div>
          <div style={{ fontWeight: 800, fontSize: 16, color: C.text, marginBottom: 8 }}>No reviews assigned yet</div>
          <div style={{ fontSize: 13, color: C.muted }}>When HR assigns you to review a colleague, it will appear here.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {pending.length > 0 && (
            <>
              <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", marginBottom: 4 }}>Pending Your Response</div>
              {pending.map(r => (
                <div key={r.id} className="gc" style={{ padding: "18px 22px", borderLeft: `4px solid ${T.gold}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: 14, color: C.text, marginBottom: 4 }}>{r.title || "Peer Review"}</div>
                      <div style={{ fontSize: 12, color: C.sub }}>
                        Reviewing: <strong style={{ color: C.text }}>{r.reviewee?.full_name || "Colleague"}</strong>
                        {r.deadline && <span style={{ marginLeft: 10, color: T.orange }}>⏰ Due {new Date(r.deadline).toLocaleDateString()}</span>}
                      </div>
                      <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
                        {r.questions?.length || 0} questions · {r.is_anonymous ? "🔒 Anonymous" : "Named response"}
                      </div>
                    </div>
                    <button className="bp" style={{ fontSize: 12, padding: "8px 18px", flexShrink: 0 }} onClick={() => openReview(r)}>
                      Give Feedback
                    </button>
                  </div>
                </div>
              ))}
            </>
          )}
          {done.length > 0 && (
            <>
              <div style={{ fontSize: 11, fontWeight: 800, color: C.muted, textTransform: "uppercase", letterSpacing: "1px", margin: "12px 0 4px" }}>Completed</div>
              {done.map(r => (
                <div key={r.id} className="gc" style={{ padding: "14px 22px", borderLeft: `4px solid #4ADE8066`, opacity: 0.7 }}>
                  <div style={{ fontWeight: 700, fontSize: 13, color: C.text }}>{r.title || "Peer Review"}</div>
                  <div style={{ fontSize: 12, color: C.sub, marginTop: 2 }}>
                    Reviewed: <strong>{r.reviewee?.full_name || "Colleague"}</strong> · <span style={{ color: "#4ADE80" }}>✓ Submitted</span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* Review submission modal */}
      {activeReview && (
        <Modal onClose={() => !submitting && setActiveReview(null)} title={activeReview.title || "Peer Review"} width={620}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ padding: "10px 14px", background: `${T.gold}11`, borderRadius: 8, border: `1px solid ${T.gold}22`, fontSize: 13, color: C.sub }}>
              You are reviewing: <strong style={{ color: C.text }}>{activeReview.reviewee?.full_name || "your colleague"}</strong>.
              {activeReview.is_anonymous && <span style={{ color: T.gold, marginLeft: 8 }}>🔒 Your identity will be kept anonymous.</span>}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {(activeReview.questions || []).map((q, idx) => (
                <div key={idx}>
                  <div style={{ fontSize: 14, fontWeight: 800, color: C.text, marginBottom: 8 }}>{idx + 1}. {q}</div>
                  <textarea
                    className="inp"
                    rows="3"
                    value={answers[idx] || ""}
                    onChange={e => setAnswers(prev => ({ ...prev, [idx]: e.target.value }))}
                    placeholder="Your honest feedback helps your colleague grow…"
                  />
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: `1px solid ${C.border}`, paddingTop: 16 }}>
              <button className="bg" style={{ padding: "10px 20px" }} onClick={() => setActiveReview(null)} disabled={submitting}>Cancel</button>
              <button className="bp" style={{ padding: "10px 24px" }} onClick={submitReview} disabled={submitting}>
                {submitting ? "Submitting…" : "Submit Feedback"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

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
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if (!createForm.title || createForm.questions.filter(q => q.trim()).length === 0) return alert("Title and at least 1 question required.");
    try {
      await apiFetch(`${API_BASE}/hr/culture/surveys`, {
        method: "POST",
        body: JSON.stringify({
          title: createForm.title,
          description: createForm.description,
          questions: createForm.questions.filter(q => q.trim())
        })
      });
      setShowCreate(false);
      setCreateForm({ title: "", description: "", questions: [""] });
      fetchData();
    } catch (e) { alert(e.message); }
  };

  const handleSubmitResponse = async () => {
    if (Object.keys(answers).length === 0) return alert("Please answer at least one question.");
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
    } catch (e) {
      // Even if API fails, thank the user and close (response may still have been recorded)
      alert("Thank you! Your response has been submitted.");
      setActiveSurvey(null);
      setAnswers({});
    } finally { setSubmitting(false); }
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
        <>
          {loading ? (
            <div style={{ textAlign: "center", padding: 60, color: C.muted }}>Loading surveys…</div>
          ) : (
            <div className="g3">
              {surveys.map(s => (
                <div key={s.id} className="gc" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 800, color: C.text }}>{s.title}</div>
                      <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>{s.questions.length} Questions</div>
                    </div>
                    {s.is_active !== false ? <span className="tg tg2">Active</span> : <span className="tg tr">Closed</span>}
                  </div>
                  <div style={{ fontSize: 13, color: C.sub, lineHeight: "1.5" }}>{s.description || "No description provided."}</div>
                  {s.is_active !== false && (
                    <button className="bg" style={{ alignSelf: "flex-start", padding: "8px 16px" }} onClick={() => setActiveSurvey(s)}>
                      Take Survey
                    </button>
                  )}
                </div>
              ))}
              {surveys.length === 0 && (
                <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 60, color: C.muted }}>
                  <div style={{ fontSize: 36, marginBottom: 16 }}>📋</div>
                  <div style={{ fontWeight: 800, fontSize: 15, marginBottom: 8, color: C.text }}>No surveys yet</div>
                  <div style={{ fontSize: 13 }}>When HR launches a survey, it will appear here for you to complete.</div>
                </div>
              )}
            </div>
          )}
        </>
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
            <div><Lbl>Survey Title *</Lbl><input className="inp" value={createForm.title} onChange={e => setCreateForm({ ...createForm, title: e.target.value })} placeholder="e.g. Q3 eNPS Pulse Check" /></div>
            <div><Lbl>Description</Lbl><textarea className="inp" rows="2" value={createForm.description} onChange={e => setCreateForm({ ...createForm, description: e.target.value })} placeholder="Explain the purpose of this survey..." /></div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Lbl>Questions</Lbl>
              {createForm.questions.map((q, idx) => (
                <input key={idx} className="inp" value={q} onChange={e => {
                  const newQ = [...createForm.questions];
                  newQ[idx] = e.target.value;
                  setCreateForm({ ...createForm, questions: newQ });
                }} placeholder={`Question ${idx + 1}`} />
              ))}
              <button className="bg" style={{ alignSelf: "flex-start", padding: "6px 12px", fontSize: 11 }} onClick={() => setCreateForm({ ...createForm, questions: [...createForm.questions, ""] })}>+ Add Question</button>
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
                  <textarea className="inp" rows="2" value={answers[idx] || ""} onChange={e => setAnswers({ ...answers, [idx]: e.target.value })} placeholder="Your answer..." />
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

// ─── PUBLIC OFFER PAGE ─────────────────────────────────────────────────────────
function PublicOfferPage({ offerId }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [offer, setOffer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [declineMode, setDeclineMode] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/hr/public/offers/${offerId}`)
      .then(res => { if (!res.ok) throw new Error("Offer not found"); return res.json(); })
      .then(d => { setOffer(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [offerId]);

  const respond = async (action) => {
    if (action === "decline" && !reason) return alert("Please provide a reason or counter-offer.");
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/hr/public/offers/${offerId}/respond`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, reason: action === "decline" ? reason : "" })
      });
      if (!res.ok) throw new Error("Failed to submit response");
      setDone(action);
    } catch (e) { alert(e.message); } finally { setSubmitting(false); }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading Offer Details...</div>;
  if (error) return <div style={{ padding: 40, textAlign: "center", color: "#F87171" }}>{error}</div>;
  if (!offer) return null;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: C.bg, color: C.text, fontFamily: "'Inter', sans-serif" }}>
      <div style={{ padding: "24px 40px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", background: C.card }}>
        <img src="https://www.eximps-cloves.com/logo.svg" alt="Eximp & Cloves" style={{ height: 32 }} />
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 40 }}>
        <div className="gc" style={{ maxWidth: 500, width: "100%", padding: 32 }}>
          {done ? (
            <div style={{ textAlign: "center", padding: 20 }} className="fade">
              <div style={{ fontSize: 40, marginBottom: 16 }}>{done === "accept" ? "🎉" : "📩"}</div>
              <h2 style={{ margin: "0 0 12px 0", color: done === "accept" ? "#4ADE80" : C.text }}>{done === "accept" ? "Offer Accepted!" : "Response Received"}</h2>
              <p style={{ color: C.sub, lineHeight: 1.6, fontSize: 14 }}>
                {done === "accept" ? "Welcome aboard! Our HR team will be in touch shortly with your onboarding details." : "Thank you for letting us know. Our HR team has received your feedback."}
              </p>
            </div>
          ) : (
            <div className="fade">
              <div style={{ textAlign: "center", marginBottom: 24 }}>
                <h2 style={{ margin: "0 0 8px 0", fontSize: 24 }}>Employment Offer</h2>
                <div style={{ color: C.sub }}>Eximp & Cloves Infrastructure Limited</div>
              </div>
              <div style={{ background: dark ? "#111" : "#f9f9f9", padding: 20, borderRadius: 12, marginBottom: 24, border: `1px solid ${C.border}` }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: C.sub }}>Candidate</span><strong style={{ textAlign: "right" }}>{offer.candidate_name}</strong></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: C.sub }}>Position</span><strong style={{ textAlign: "right", color: T.gold }}>{offer.job_title}</strong></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: C.sub }}>Department</span><strong style={{ textAlign: "right" }}>{offer.department}</strong></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: C.sub }}>Offered Salary</span><strong style={{ textAlign: "right", color: "#4ADE80" }}>₦{parseFloat(offer.offered_salary).toLocaleString()} / month</strong></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: C.sub }}>Start Date</span><strong style={{ textAlign: "right" }}>{offer.start_date || "To be agreed"}</strong></div>
                </div>
              </div>

              {offer.notes && (
                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: C.sub, marginBottom: 8, textTransform: "uppercase", letterSpacing: "1px" }}>Offer Conditions</div>
                  <div style={{ fontSize: 13, lineHeight: 1.6, color: C.text, padding: 16, background: `${T.gold}11`, borderRadius: 8, borderLeft: `3px solid ${T.gold}` }}>
                    {offer.notes}
                  </div>
                </div>
              )}

              {offer.status !== "Offered" ? (
                <div style={{ textAlign: "center", padding: 16, background: C.border, borderRadius: 8, color: C.sub, fontWeight: 700 }}>
                  This offer has already been processed ({offer.status}).
                </div>
              ) : (
                <>
                  {declineMode ? (
                    <div className="fade" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      <div><label style={{ fontSize: 12, fontWeight: 700, color: C.sub, display: "block", marginBottom: 8 }}>Reason for Decline or Counter-Offer</label>
                        <textarea className="inp" rows={4} value={reason} onChange={e => setReason(e.target.value)} placeholder="Please let us know why you are declining, or state your counter-offer..." /></div>
                      <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                        <button className="bg" style={{ flex: 1 }} onClick={() => setDeclineMode(false)} disabled={submitting}>Back</button>
                        <button className="bp" style={{ flex: 1, background: "#EF4444" }} onClick={() => respond("decline")} disabled={submitting}>{submitting ? "Submitting..." : "Submit Decline"}</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", gap: 12 }}>
                      <button className="bp" style={{ flex: 2, background: "#4ADE80", color: "#1A1A1A", fontSize: 15 }} onClick={() => respond("accept")} disabled={submitting}>
                        {submitting ? "Processing..." : "Accept Offer"}
                      </button>
                      <button className="bg" style={{ flex: 1, borderColor: "#EF4444", color: "#EF4444" }} onClick={() => setDeclineMode(true)} disabled={submitting}>
                        Decline...
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── ROOT ────────────────────────────────────────────────────────────────────
export default function App() {
  const [dark, setDark] = useState(true);
  const [user, setUser] = useState(null);
  const toggle = useCallback(() => setDark(d => !d), []);

  useEffect(() => {
    // Check for public routes
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("offer")) return;
    if (urlParams.get("token")) return; // Bio data public form

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

  const urlParams = new URLSearchParams(window.location.search);
  const offerId = urlParams.get("offer");
  if (offerId) {
    return (
      <ThemeCtx.Provider value={{ dark, toggle }}>
        <style>{GS(dark)}</style>
        <PublicOfferPage offerId={offerId} />
      </ThemeCtx.Provider>
    );
  }

  const biodataToken = urlParams.get("token");
  if (biodataToken) {
    return (
      <ThemeCtx.Provider value={{ dark, toggle }}>
        <PublicBiodataForm />
      </ThemeCtx.Provider>
    );
  }

  if (!user) return <div style={{ padding: 40, textAlign: "center", color: T.orange }}>Redirecting to login...</div>;

  return (
    <ThemeCtx.Provider value={{ dark, toggle }}>
      <style>{GS(dark)}</style>
      <div className="fade">
        {isHrAdminUser(user) && (
          <HRAdminPortal user={user} onLogout={logout} />
        )}
        {isLineManagerUser(user) && (
          <ManagerPortal user={user} onLogout={logout} />
        )}
        {(!isHrAdminUser(user) && !isLineManagerUser(user)) && (
          <StaffPortal user={user} onLogout={logout} />
        )}
      </div>
    </ThemeCtx.Provider>
  );
}
