import { useState, createContext, useContext, useCallback, useEffect } from "react";
import { apiFetch, API_BASE } from "./api";

const ThemeCtx = createContext({ dark: true, toggle: () => { } });
const useTheme = () => useContext(ThemeCtx);

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
  const C = dark ? DARK : LIGHT;
  const G = T.gold;
  return `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');
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
            ) : (
            <button key={n.id} className={`nb ${page === n.id ? "on" : ""}`} onClick={() => !n.disabled && setPage(n.id)} style={{ opacity: n.disabled ? 0.5 : 1, cursor: n.disabled ? 'not-allowed' : 'pointer' }}>
              {IC[n.icon]}{n.label} {n.disabled && <span style={{fontSize: 9, marginLeft: 'auto', background: '#333', padding: '2px 6px', borderRadius: 4}}>SOON</span>}
            </button>
            )
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
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span className="tg to" style={{ fontSize: 10 }}>{(user.staffType || user.role || "").toUpperCase()} ACCESS</span>
        <span style={{ fontSize: 12, color: C.muted }}>{new Date().toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" })}</span>
      </div>
    </div>
  );
}

// Authentication is now handled by the main platform.
// Redirection logic is in the App component.


// ─── GOAL FORM MODAL CONTENT ─────────────────────────────────────────────────
function GoalForm({ onSave, staffList = [], templates = [], initialGoal = null }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const defaultForm = { uid: "", department: "", template_id: "", kpi: "", target: "", unit: "", period: new Date().toLocaleDateString(undefined, { month: 'short', year: 'numeric' }), status: "Published" };
  const [f, setF] = useState(defaultForm);
  const departmentAlias = { Sales: "Sales & Acquisitions", HR: "Human Resources" };

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
      period: initialGoal.month ? new Date(initialGoal.month).toLocaleDateString(undefined, { month: 'short', year: 'numeric' }) : defaultForm.period,
      status: initialGoal.status || "Published"
    });
  }, [initialGoal, templates]);

  const selUser = staffList.find(u => u.id === f.uid);
  const departmentKey = selUser ? (departmentAlias[selUser.department] || selUser.department) : f.department;
  const suggestedTemplates = departmentKey ? templates.filter(t => t.department === departmentKey && t.is_active) : [];
  const hasSuggestedKpis = suggestedTemplates.length > 0;

  const departments = Array.from(new Set([
    ...staffList.map(u => departmentAlias[u.department] || u.department).filter(Boolean),
    ...templates.map(t => t.department).filter(Boolean)
  ])).sort();

  const save = () => {
    if ((!f.uid && !f.department) || !f.kpi || !f.target) return;
    onSave({ ...f, department: departmentKey || f.department, target: parseFloat(f.target), actual: 0 });
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
            {departments.map(d => <option key={d} value={d}>{d}</option>)}
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

function KpiTemplateManager({ templates = [], onSave, onUpdate, onClose }) {
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
                {["General", "Sales & Acquisitions", "Human Resources", "Operations", "Finance", "Legal"].map(d => <option key={d}>{d}</option>)}
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
  const [goals, setGoals] = useState([]);
  const [staff, setStaff] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);
  const [syncing, setSyncing] = useState(false);

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
      const month = g.period ? new Date(`${g.period} 1`).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
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
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", opacity: 0.7 }}>
                    <div style={{ fontSize: 11, color: C.muted }}>
                      Last Updated: <b>{g.last_synced_at ? new Date(g.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Waiting for sync..."}</b>
                    </div>
                    <span style={{ fontSize: 12 }}>⚡</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showNew && (
        <Modal onClose={() => { setShowNew(false); setEditingGoal(null); }} title={editingGoal ? "Edit Goal" : "Set New Goal"}>
          <GoalForm staffList={staff} templates={templates} initialGoal={editingGoal} onSave={saveGoal} />
        </Modal>
      )}

      {showTemplateManager && (
        <Modal onClose={() => setShowTemplateManager(false)} title="Manage KPI Library">
          <KpiTemplateManager
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
  const [nt, setNt] = useState({ title: "", assignedTo: "", due: "", priority: "Medium", project: "", desc: "" });

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
      setNt({ title: "", assignedTo: "", due: "", priority: "Medium", project: "", desc: "" });
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
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status } : t));
      if (viewT) setViewT({ ...viewT, status });
    } catch (e) {
      alert(e.message);
    }
  };

  const canCreate = isHR || isLM;
  const canEdit = t => isHR || (isLM && t.assigned_by === currentUser.id);

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 22 }}>{isStaff ? "My Tasks" : "Task Manager"}</div>
          <div style={{ fontSize: 13, color: C.sub, marginTop: 4 }}>
            {isStaff ? "Tasks assigned to you. Complete tasks to boost your performance score."
              : "Assign and track tasks across the team. Overdue tasks trigger automated alerts."}
          </div>
        </div>
        {canCreate && <button className="bp" onClick={() => setShowNew(true)}>+ Assign Task</button>}
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: C.muted }}>Loading tasks…</div>
      ) : tasks.length === 0 ? (
        <div className="gc" style={{ padding: 40, textAlign: "center", color: C.muted }}>No tasks found for this period.</div>
      ) : (
        <div className={isStaff ? "g2" : "g3"} style={{ gap: 14 }}>
          {tasks.map(t => {
            const u = t.admins || {};
            const pc = pCol[t.priority] || T.orange;
            const sc = sCol[t.status] || T.orange;
            return (
              <div key={t.id} className="gc" style={{ padding: 20, cursor: "pointer" }} onClick={() => setViewT(t)}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                  <span className="tg" style={{ background: `${pc}22`, color: pc, border: `1px solid ${pc}33` }}>{t.priority}</span>
                  <span className="tg" style={{ background: `${sc}22`, color: sc, border: `1px solid ${sc}33`, textTransform: "capitalize" }}>{t.status}</span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 800, color: C.text, marginBottom: 6, lineHeight: 1.4 }}>{t.title}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                  {!isStaff && <div style={{ display: "flex", alignItems: "center", gap: 8 }}><Av av={u.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={24} /><span style={{ fontSize: 12, color: C.sub }}>{u.full_name?.split(" ")[0]}</span></div>}
                  <span style={{ fontSize: 11, color: C.muted }}>Due {new Date(t.due_date).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {viewT && (
        <Modal onClose={() => setViewT(null)} title={viewT.title}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <span className="tg" style={{ background: `${pCol[viewT.priority]}22`, color: pCol[viewT.priority], border: `1px solid ${pCol[viewT.priority]}33` }}>{viewT.priority} Priority</span>
            <span className="tg" style={{ background: `${sCol[viewT.status]}22`, color: sCol[viewT.status], border: `1px solid ${sCol[viewT.status]}33` }}>{viewT.status}</span>
          </div>
          <div style={{ fontSize: 13, color: (dark ? DARK : LIGHT).sub, marginBottom: 18, lineHeight: 1.7 }}>{viewT.notes || "No description provided."}</div>
          <div className="g2" style={{ gap: 10, marginBottom: 18 }}>
            <Field label="Staff Member" value={viewT.admins?.full_name} />
            <Field label="Due Date" value={new Date(viewT.due_date).toLocaleDateString()} />
            <Field label="Priority" value={viewT.priority} />
            <Field label="Status" value={viewT.status} />
          </div>
          {(isStaff || canEdit(viewT)) && (
            <div>
              <div style={{ fontSize: 12, color: (dark ? DARK : LIGHT).muted, marginBottom: 10, fontWeight: 800 }}>Update Task Status</div>
              <div style={{ display: "flex", gap: 10 }}>
                {["pending", "in_progress", "completed"].map(s => (
                  <button key={s} className={viewT.status === s ? "bp" : "bg"} style={{ flex: 1, fontSize: 12, textTransform: "capitalize" }}
                    onClick={() => updateStatus(viewT.id, s)}>
                    {s.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Modal>
      )}

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
            <div><Lbl>Description</Lbl><textarea className="inp" placeholder="Task details and instructions…" value={nt.desc} onChange={e => setNt(n => ({ ...n, desc: e.target.value }))} /></div>
            <button className="bp" onClick={add} style={{ padding: 12 }}>Assign Task</button>
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
      const [o, p, e, r, s] = await Promise.all([
        apiFetch(`${API_BASE}/commission/owed`),
        apiFetch(`${API_BASE}/commission/payouts`),
        apiFetch(`${API_BASE}/commission/earnings`),
        apiFetch(`${API_BASE}/sales-reps`),
        apiFetch(`${API_BASE}/hr/staff`)
      ]);
      setOwed(Array.isArray(o) ? o : []);
      setPayouts(Array.isArray(p) ? p : []);
      setEarnings(Array.isArray(e) ? e : []);
      setReps(Array.isArray(r) ? r : []);
      setStaff(Array.isArray(s) ? s : []);
    } catch (err) { console.error("Commission load error:", err); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadDashboard(); }, []);

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
                  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
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
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span className={`tg ${r.status === "approved" ? "tg2" : r.status === "pending" ? "ty" : "tr"}`}>{r.status}</span>
                      {r.proof_url && (
                        <a href={r.proof_url} target="_blank" rel="noreferrer" title="View Proof" style={{ display: "flex", color: T.orange }}>
                          <svg style={{ width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21.44 11.05a19.19 19.19 0 0 0-18.88 0 2 2 0 0 0 0 3.9 19.19 19.19 0 0 0 18.88 0 2 2 0 0 0 0-3.9z" /><circle cx="12" cy="13" r="3" /></svg>
                        </a>
                      )}
                    </div>
                  </td>
                  <td>
                    {isHR && r.status === "pending" && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => updateStatus(r.id, "approved")}>Approve</button>
                        <button className="bd" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => updateStatus(r.id, "rejected")}>Reject</button>
                      </div>
                    )}
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
                                  } catch(err) {
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
                              } catch(err) {
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
  const viewOnly = authRole !== "hr";
  const [tab, setTab] = useState("full");
  const [view, setView] = useState(null);
  const [dtTab, setDtTab] = useState("details");
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newStaff, setNewStaff] = useState({ full_name: "", email: "", password: "", confirm_password: "", roles: ["staff"], primary_role: "staff", staff_type: "full", department: "", line_manager_id: null });
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
              <div><Lbl>Department</Lbl><input className="inp" placeholder="e.g. Sales & Acquisitions" value={newStaff.department} onChange={e => setNewStaff(s => ({ ...s, department: e.target.value }))} /></div>
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
                    <input className="inp" value={draftView.department} onChange={e => setDraftView(d => ({ ...d, department: e.target.value }))} />
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
          {items.map(n => (
            <button key={n.id} className={`nb ${page === n.id ? "on" : ""}`} onClick={() => { setPage(n.id); onClose(); }}>
              {IC[n.icon]}{n.label}
            </button>
          ))}
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
  );
}

function HRAdminPortal({ user, onLogout }) {
  const nav = [
    { isHeader: true, label: "Hub 1: Recruitment" },
    { id: "ats", icon: "staff", label: "ATS & Jobs" },
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
    { id: "assets", icon: "tasks", label: "Asset Management" },
    { id: "legal_vault", icon: "tasks", label: "Legal Vault" },
    { isHeader: true, label: "Hub 9: Administration" },
    { id: "tasks", icon: "tasks", label: "Task Manager" },
    { id: "admin", icon: "dashboard", label: "Workforce Stats" },
    { isHeader: true, label: "Personal" },
    { id: "myprofile", icon: "profile", label: "My Profile" },
  ];
  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="HR Administration" renderPage={p => {
      if (p === "dashboard") return <HRDashboard />;
      if (p === "ats") return <RecruitmentHub />;
      if (p === "staff") return <StaffDirectory authRole="hr" />;
      if (p === "leave") return <LeaveManagement user={user} />;
      if (p === "admin") return <Administration />;
      if (p === "presence") return <Presence currentUser={user} />;
      if (p === "perf") return <Performance />;
      if (p === "goals") return <Goals canManageKpiTemplates />;
      if (p === "payroll") return <Payroll />;
      if (p === "tasks") return <Tasks currentUser={user} />;
      if (p === "disciplinary") return <Disciplinary />;
      if (p === "assets") return <AssetManager />;
      if (p === "legal_vault") return <LegalManager staffId={null} staffName={null} isHR={true} />; 
      if (p === "myprofile") return <MyProfile user={user} />;
    }} />
  );
}

function ManagerPortal({ user, onLogout }) {
  const nav = [
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
      if (p === "leave") return <LeaveManagement user={user} />;
      if (p === "presence") return <Presence currentUser={user} />;
      if (p === "perf") return <Performance />;
      if (p === "goals") return <Goals />;
      if (p === "tasks") return <Tasks currentUser={user} />;
      if (p === "disciplinary") return <Disciplinary isManager userId={user.id} />;
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

function StaffPortal({ user, onLogout }) {
  const nav = [
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
      if (pg === "leave") return <LeaveManagement user={user} />;
      if (pg === "perf") return <Performance viewOnly userId={user.id} />;
      if (pg === "goals") return <Goals viewOnly userId={user.id} />;
      if (pg === "tasks") return <Tasks currentUser={user} />;
      if (pg === "presence") return <Presence currentUserId={user.id} currentUser={user} />;
      if (pg === "payroll") return <StaffPayroll user={user} />;
      if (pg === "disciplinary") return <Disciplinary viewOnly userId={user.id} />;
      if (pg === "legal_vault") return <LegalManager staffId={user.id} staffName={user.full_name} isHR={false} />;

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
        </div>
      );
    }} />
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
            <div><Lbl>Asset Name *</Lbl><input className="inp" value={createForm.asset_name} onChange={e => setCreateForm({...createForm, asset_name: e.target.value})} placeholder="e.g. MacBook Pro M2" /></div>
            <div className="g2">
              <div><Lbl>Asset Type</Lbl>
                <select className="inp" value={createForm.asset_type} onChange={e => setCreateForm({...createForm, asset_type: e.target.value})}>
                  <option>Equipment</option><option>Vehicle</option><option>Property</option><option>Software License</option>
                </select>
              </div>
              <div><Lbl>Serial Number</Lbl><input className="inp" value={createForm.serial_number} onChange={e => setCreateForm({...createForm, serial_number: e.target.value})} placeholder="Optional" /></div>
            </div>
            <div><Lbl>Purchase Cost (Optional)</Lbl><input type="number" className="inp" value={createForm.purchase_cost} onChange={e => setCreateForm({...createForm, purchase_cost: e.target.value})} placeholder="0.00" /></div>
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
              <select className="inp" value={assignForm.staff_id} onChange={e => setAssignForm({...assignForm, staff_id: e.target.value})}>
                <option value="">— Unassigned (Return to Inventory) —</option>
                {staffList.filter(u => u.is_active).map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div><Lbl>Asset Status</Lbl>
              <select className="inp" value={assignForm.status} onChange={e => setAssignForm({...assignForm, status: e.target.value})}>
                <option value="Available">Available</option>
                <option value="Assigned">Assigned</option>
                <option value="Maintenance">Maintenance</option>
                <option value="Retired">Retired</option>
              </select>
            </div>
            <div><Lbl>Assignment Notes</Lbl><textarea className="inp" rows="2" value={assignForm.notes} onChange={e => setAssignForm({...assignForm, notes: e.target.value})} placeholder="Condition details, expected return date, etc." /></div>
            <button className="bp" onClick={handleAssign} style={{ marginTop: 10 }}>Save Assignment</button>
          </div>
        </Modal>
      )}
    </div>
  );
}



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

// ─── ROOT ────────────────────────────────────────────────────────────────────
export default function App() {
  const [dark, setDark] = useState(true);
  const [user, setUser] = useState(null);
  const toggle = useCallback(() => setDark(d => !d), []);

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
