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
    body,html{height:100%;overflow-x:hidden;}
    .hrm{font-family:'Inter',sans-serif;background:${C.bg};color:${C.text};min-height:100vh;display:flex;width:100%;}
    .hrm-main{flex:1;min-height:100vh;display:flex;flex-direction:column;}
    .hrm-content-padding{flex:1;padding:32px 40px;}
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
    .ht th{padding:14px 18px;font-size:10px;color:${C.muted};text-align:left;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid ${C.border};font-weight:800;background:${dark?"#1A1C20":C.surface};}
    .ht td{padding:14px 18px;font-size:13px;border-bottom:1px solid ${C.border}44;}
    .ht tr:hover td{background:${C.border}1A;}
    
    /* Modals */
    .mb{position:fixed;inset:0;background:#06080AEE;backdrop-filter:blur(12px);z-index:1000;display:grid;place-items:center;padding:24px;overflow-y:auto;}
    .mo{background:${C.card};border:1px solid #FFFFFF10;box-shadow:0 40px 100px rgba(0,0,0,.8);border-radius:28px;max-width:640px;width:100%;max-height:92vh;display:flex;flex-direction:column;position:relative;animation:m-in .4s cubic-bezier(.2,1,.2,1);overflow:hidden;}
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
      .mo{max-width:100vw;margin:8px;border-radius:16px;max-height:96vh;}
      .field{padding:10px 14px;}
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

const TrendChart = ({ data, color="#4ADE80" }) => {
  if(!data || data.length < 2) return <div style={{ height:60, display:"flex", alignItems:"center", justifyContent:"center", color:(LIGHT).muted, fontSize:11 }}>Insufficient data for trend</div>;
  const max = 100;
  const h = 60, w = 240;
  const padding = 10;
  const points = data.map((v, i) => {
    const x = padding + (i * (w - 2 * padding) / (data.length - 1));
    const y = h - padding - (v / max * (h - 2 * padding));
    return `${x},${y}`;
  }).join(" ");
  
  return (
    <div style={{ marginTop:14 }}>
      <div style={{ fontSize:10, color:(LIGHT).muted, marginBottom:8, textTransform:"uppercase", fontWeight:800, letterSpacing:1 }}>6-Month Performance Trend</div>
      <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow:"visible" }}>
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

function Modal({ onClose, title, width=640, children }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  return (
    <div className="mb" onClick={onClose}>
      <div className="mo fade" style={{ maxWidth:width }} onClick={e=>e.stopPropagation()}>
        <div style={{ flexShrink:0, display:"flex", justifyContent:"space-between", alignItems:"center", padding:"34px 40px 14px 40px" }}>
          <div>
            <div style={{ fontSize:10, color:T.orange, fontWeight:800, textTransform:"uppercase", letterSpacing:".1em", marginBottom:4 }}>Management System</div>
            <div className="ho" style={{ fontSize:22 }}>{title}</div>
          </div>
          <button onClick={onClose} style={{ background:"#FFFFFF0A", border:"1px solid #FFFFFF10", color:C.text, width:36, height:36, borderRadius:10, display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", transition:"all .2s" }}>✕</button>
        </div>
        <div style={{ flex:1, overflowY:"auto", padding:"0 40px 40px 40px", scrollbarWidth:"none" }}>
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
          <img src="/static/img/logo.svg" alt="Eximp & Cloves" style={{ height: 40, width: "auto" }} onError={(e) => { e.target.onerror = null; e.target.src = "https://via.placeholder.com/40x40?text=EC"; }} />
          <div style={{ lineHeight:1.2 }}>
            <div style={{ fontSize:16, fontWeight:700, color:G, fontFamily:"'Playfair Display',serif" }}>HR Suite</div>
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
function GoalForm({ onSave, staffList=[], templates=[], initialGoal=null }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const defaultForm = { uid:"", department:"", template_id:"", kpi:"", target:"", unit:"", period:"Apr 2026", status:"Draft" };
  const [f, setF] = useState(defaultForm);
  const departmentAlias = { Sales: "Sales & Acquisitions", HR: "Human Resources" };

  useEffect(() => {
    if (!initialGoal) {
      setF(defaultForm);
      return;
    }
    setF({
      uid: initialGoal.staff_id || "",
      department: initialGoal.department || "",
      template_id: initialGoal.kpi_template_id || "",
      kpi: initialGoal.kpi_name || "",
      target: initialGoal.target_value != null ? String(initialGoal.target_value) : "",
      unit: initialGoal.unit || "",
      period: initialGoal.month ? new Date(initialGoal.month).toLocaleDateString(undefined, { month:'short', year:'numeric' }) : "Apr 2026",
      status: initialGoal.status || "Draft"
    });
  }, [initialGoal]);

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
    onSave({ ...f, department: departmentKey || f.department, target:parseFloat(f.target), actual:0 });
  };

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
        <div>
          <Lbl>Staff Member</Lbl>
          <select className="inp" value={f.uid} onChange={e=>{
            const staffId = e.target.value;
            const staff = staffList.find(u => u.id === staffId);
            setF(x => ({
              ...x,
              uid: staffId,
              department: staff ? (departmentAlias[staff.department] || staff.department) : "",
              template_id:"",
              kpi:""
            }));
          }}>
            <option value="">— No staff selected —</option>
            {staffList.filter(u=>u.role!=="hr_admin").map(u=><option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
          </select>
        </div>
        <div>
          <Lbl>Department</Lbl>
          <select className="inp" value={f.department} onChange={e=>{
            setF(x => ({ ...x, department: e.target.value, uid:"", template_id:"", kpi:"" }));
          }} disabled={!!f.uid}>
            <option value="">— Select Department —</option>
            {departments.map(d=><option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>
      <div>
        <Lbl>KPI / Goal Type *</Lbl>
        {hasSuggestedKpis ? (
          <>
            <select className="inp" value={f.template_id} onChange={e=>{
              const template = suggestedTemplates.find(t => t.id === e.target.value);
              if (e.target.value === "") {
                setF(x => ({ ...x, template_id:"", kpi:"" }));
              } else {
                setF(x => ({ ...x, template_id: e.target.value, kpi: template ? template.name : x.kpi }));
              }
            }} disabled={!departmentKey}>
              <option value="">— Select KPI for this department —</option>
              {suggestedTemplates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <input
              className="inp"
              type="text"
              placeholder={departmentKey ? "KPI name (select a template or type a custom name)" : "Select staff or department first"}
              value={f.kpi}
              onChange={e=>setF(x=>({...x,kpi:e.target.value, template_id: ""}))}
              disabled={!departmentKey}
              style={{ marginTop:12 }}
            />
          </>
        ) : (
          <input
            className="inp"
            type="text"
            placeholder={departmentKey ? "Enter a custom KPI goal name" : "Select staff or department first"}
            value={f.kpi}
            onChange={e=>setF(x=>({...x,kpi:e.target.value}))}
            disabled={!departmentKey}
          />
        )}
        {!departmentKey && <div style={{ fontSize:11, color:(dark?DARK:LIGHT).muted, marginTop:4 }}>Select a staff member or department first to see relevant KPIs.</div>}
        {departmentKey && !hasSuggestedKpis && <div style={{ fontSize:11, color:(dark?DARK:LIGHT).muted, marginTop:4 }}>This department has no active KPI templates. Enter a custom KPI name.</div>}
      </div>
      <div className="g2" style={{ gap:12 }}>
        <div><Lbl>Target Value *</Lbl><input className="inp" type="number" placeholder="e.g. 8" value={f.target} onChange={e=>setF(x=>({...x,target:e.target.value}))}/></div>
        <div><Lbl>Unit</Lbl><input className="inp" placeholder="e.g. deals, %, sites" value={f.unit} onChange={e=>setF(x=>({...x,unit:e.target.value}))}/></div>
      </div>
      <div className="g2" style={{ gap:12 }}>
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
      <button className="bp" onClick={save} style={{ padding:12 }}>{initialGoal ? "Update Goal" : "Save Goal"}</button>
    </div>
  );
}

function KpiTemplateManager({ templates=[], onSave, onUpdate, onClose }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [editId, setEditId] = useState("");
  const [form, setForm] = useState({ name:"", department:"", category:"", description:"", is_active:true });
  const [saving, setSaving] = useState(false);

  const beginEdit = (template) => {
    setEditId(template.id);
    setForm({
      name: template.name,
      department: template.department,
      category: template.category || "",
      description: template.description || "",
      is_active: template.is_active
    });
  };

  const resetForm = () => {
    setEditId("");
    setForm({ name:"", department:"", category:"", description:"", is_active:true });
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
    <div style={{ display:"flex", flexDirection:"column", gap:18 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", gap:10 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>KPI Library</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>Create and manage reusable KPI templates for the goal form.</div>
        </div>
        <button className="bg" onClick={onClose}>Close</button>
      </div>

      <div className="gc" style={{ padding:20 }}>
        <div className="g2" style={{ gap:14, marginBottom:14 }}>
          <div>
            <Lbl>Name *</Lbl>
            <input className="inp" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} placeholder="e.g. Deals Closed" />
          </div>
          <div>
            <Lbl>Department *</Lbl>
            <input className="inp" value={form.department} onChange={e=>setForm(f=>({...f,department:e.target.value}))} placeholder="e.g. Sales & Acquisitions" />
          </div>
        </div>
        <div className="g2" style={{ gap:14, marginBottom:14 }}>
          <div>
            <Lbl>Category</Lbl>
            <input className="inp" value={form.category} onChange={e=>setForm(f=>({...f,category:e.target.value}))} placeholder="e.g. Sales" />
          </div>
          <div>
            <Lbl>Status</Lbl>
            <select className="inp" value={String(form.is_active)} onChange={e=>setForm(f=>({...f,is_active:e.target.value === "true"}))}>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>
        </div>
        <div>
          <Lbl>Description</Lbl>
          <textarea className="inp" value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))} placeholder="Optional description for the KPI template." />
        </div>
        <div style={{ display:"flex", gap:10, marginTop:14 }}>
          <button className="bp" onClick={handleSave} disabled={saving} style={{ padding:12 }}>{editId ? "Save Changes" : "Create Template"}</button>
          {editId && <button className="bg" onClick={resetForm} style={{ padding:12 }}>New Template</button>}
        </div>
      </div>

      <div className="gc" style={{ padding:20 }}>
        <div style={{ fontSize:14, fontWeight:700, marginBottom:12 }}>Existing KPI Templates</div>
        <div className="tw">
          <table className="ht">
            <thead><tr><th>Name</th><th>Department</th><th>Category</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id}>
                  <td>{t.name}</td>
                  <td>{t.department}</td>
                  <td>{t.category || "—"}</td>
                  <td>{t.is_active ? "Active" : "Inactive"}</td>
                  <td><button className="bg" onClick={()=>beginEdit(t)}>Edit</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
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
      <div className="g2" style={{ gap:12 }}>
        <div><Lbl>From *</Lbl><input className="inp" type="date" value={f.from} onChange={e=>setF(x=>({...x,from:e.target.value}))}/></div>
        <div><Lbl>To *</Lbl><input className="inp" type="date" value={f.to} onChange={e=>setF(x=>({...x,to:e.target.value}))}/></div>
      </div>
      <div><Lbl>Reason</Lbl><textarea className="inp" placeholder="Brief reason for leave request…" value={f.reason} onChange={e=>setF(x=>({...x,reason:e.target.value}))}/></div>
      <button className="bp" onClick={save} style={{ padding:12 }}>Submit Request</button>
    </div>
  );
}


function Goals({ viewOnly, userId, canManageKpiTemplates = false }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [goals, setGoals] = useState([]);
  const [staff, setStaff] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);

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
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>{viewOnly?"My Goals":"Goal Management"}</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>Monthly targets per staff member. These feed directly into performance scores.</div>
        </div>
        <div style={{ display:"flex", gap:10, alignItems:"center" }}>
          {canManageKpiTemplates && <button className="bg" onClick={()=>setShowTemplateManager(true)}>Manage KPI Library</button>}
          {!viewOnly && <button className="bp" onClick={() => { setEditingGoal(null); setShowNew(true); }}>+ Set KPI Goal</button>}
        </div>
      </div>

      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading goals…</div>
      ) : goals.length === 0 ? (
        <div className="gc" style={{ padding:40, textAlign:"center" }}>
          <div style={{ fontSize:13, color:C.muted }}>No goals on record for this period.</div>
        </div>
      ) : (
        <div className="g2">
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
                  <div style={{ display:"flex", gap:10, alignItems:"center" }}>
                    {!viewOnly && g.status === "Draft" && (
                      <button className="bg" onClick={() => { setEditingGoal(g); setShowNew(true); }}>Edit</button>
                    )}
                    <span className={`tg tg2`} style={{ background: g.status === "Published" ? "#4ADE80" : g.status === "In Review" ? "#FBBF24" : "#93C5FD" }}>
                      {g.status || "Draft"}
                    </span>
                  </div>
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
        <Modal onClose={() => { setShowNew(false); setEditingGoal(null); }} title={editingGoal ? "Edit Goal" : "Set New Goal"}>
          <GoalForm staffList={staff} templates={templates} initialGoal={editingGoal} onSave={saveGoal}/>
        </Modal>
      )}

      {showTemplateManager && (
        <Modal onClose={()=>setShowTemplateManager(false)} title="Manage KPI Library">
          <KpiTemplateManager
            templates={templates}
            onSave={saveTemplate}
            onUpdate={updateTemplate}
            onClose={()=>setShowTemplateManager(false)}
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
      apiFetch(`${API_BASE}/hr/staff`).then(d => setStaff(Array.isArray(d) ? d : [])).catch(()=>{});
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
    present:  { label: "Present",  bg: "#4ADE8022", color: "#4ADE80", border: "#4ADE8044" },
    late:     { label: "Late",     bg: "#FBB04022", color: "#FBB040", border: "#FBB04044" },
    absent:   { label: "Absent",   bg: "#F8717122", color: "#F87171", border: "#F8717144" },
    on_leave: { label: "On Leave", bg: `${T.orange}22`, color: T.orange, border: `${T.orange}44` },
    weekend:  { label: "Weekend",  bg: `${C.border}66`, color: C.muted, border: C.border },
    future:   { label: "—",        bg: "transparent", color: C.muted, border: "transparent" },
  };

  return (
    <div className="fade">
      {/* Controls */}
      <div className="gc" style={{ padding:20, marginBottom:18 }}>
        <div style={{ display:"flex", flexWrap:"wrap", gap:12, alignItems:"flex-end" }}>
          {!currentUserId && (
            <div style={{ flex:1, minWidth:180 }}>
              <div style={{ fontSize:11, color:C.muted, marginBottom:4 }}>Staff Member</div>
              <select
                value={selectedStaff}
                onChange={e => setSelectedStaff(e.target.value)}
                className="inp"
                style={{ width:"100%" }}
              >
                <option value="">— Select Staff —</option>
                {staff.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department || "General"})</option>)}
              </select>
            </div>
          )}
          <div>
            <div style={{ fontSize:11, color:C.muted, marginBottom:4 }}>From</div>
            <input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)} className="inp" style={{ padding:"6px 10px" }}/>
          </div>
          <div>
            <div style={{ fontSize:11, color:C.muted, marginBottom:4 }}>To</div>
            <input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)} className="inp" style={{ padding:"6px 10px" }}/>
          </div>
          <button className="bp" onClick={loadReport} disabled={!selectedStaff || loading} style={{ padding:"8px 20px" }}>
            {loading ? "Loading…" : "Generate Report"}
          </button>
        </div>
      </div>

      {report && (
        <>
          {/* Summary cards */}
          <div className="g4" style={{ marginBottom:18 }}>
            {[
              ["Working Days", report.summary.total_working_days, C.text],
              ["Present",      report.summary.present,            "#4ADE80"],
              ["Late",         report.summary.late,               "#FBB040"],
              ["Absent",       report.summary.absent,             "#F87171"],
            ].map(([label, value, col]) => (
              <StatCard key={label} label={label} value={value} col={col}
                sub={report.summary.total_working_days > 0
                  ? `${Math.round(value/report.summary.total_working_days*100)}% of working days`
                  : "—"}
              />
            ))}
          </div>

          {/* Absent days alert */}
          {report.summary.absent > 0 && (
            <div style={{ padding:"12px 16px", background:"#F8717111", border:"1px solid #F8717133", borderRadius:10, marginBottom:16, fontSize:13, color:"#F87171" }}>
              ⚠️ <strong>{report.summary.absent} unexcused absence{report.summary.absent!==1?"s":""}</strong> detected in this period.
            </div>
          )}

          {/* Day grid */}
          <div className="gc" style={{ padding:20 }}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:16 }}>
              <div className="ho" style={{ fontSize:15 }}>Day-by-Day Breakdown</div>
              <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
                {Object.entries(statusProps).filter(([k])=>k!=="future").map(([key, p]) => (
                  <div key={key} style={{ display:"flex", alignItems:"center", gap:5, fontSize:11 }}>
                    <div style={{ width:10, height:10, borderRadius:2, background:p.color }}/>
                    <span style={{ color:C.sub }}>{p.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(110px, 1fr))", gap:8 }}>
              {report.days.map(d => {
                const p = statusProps[d.status] || statusProps.future;
                return (
                  <div key={d.date} style={{
                    padding:"10px 10px",
                    background: p.bg,
                    border: `1px solid ${p.border}`,
                    borderRadius: 8,
                    opacity: d.status === "weekend" ? 0.4 : 1
                  }}>
                    <div style={{ fontSize:10, color:C.muted, marginBottom:2 }}>{d.day.slice(0,3)}</div>
                    <div style={{ fontSize:13, fontWeight:700, color:p.color, marginBottom:3 }}>
                      {new Date(d.date).toLocaleDateString("en-GB", { day:"numeric", month:"short" })}
                    </div>
                    <div style={{ fontSize:9, color:d.status==="weekend"?C.muted:p.color, fontWeight:600, textTransform:"uppercase", letterSpacing:0.5 }}>
                      {p.label}
                    </div>
                    {d.check_in && (
                      <div style={{ fontSize:9, color:C.muted, marginTop:2 }}>
                        {new Date(d.check_in).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}
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
        <div style={{ textAlign:"center", padding:60, color:C.muted }}>
          <div style={{ fontSize:40, marginBottom:10 }}>📅</div>
          <div style={{ fontSize:14, fontWeight:600, marginBottom:4 }}>Select a staff member to view their attendance history</div>
          <div style={{ fontSize:12 }}>Each working day will be color-coded by status.</div>
        </div>
      )}
    </div>
  );
}

// ─── MODULE: PRESENCE ────────────────────────────────────────────────────────
function Presence({ currentUserId, currentUser }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [sub, setSub]   = useState("attendance");
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
    ? reqs.filter(l=>l.staff_id===currentUserId)
    : reqs;

  const statusColor = { Present:"#4ADE80", "On Leave":T.orange, Late:"#FBB040", Absent:"#F87171" };

  return (
    <div className="fade">
      <div className="ho" style={{ fontSize:22, marginBottom:4 }}>Presence</div>
      <div style={{ fontSize:13, color:(dark?DARK:LIGHT).sub, marginBottom:18 }}>Attendance tracking and leave management — one tab.</div>

      <Tabs items={[["attendance","Attendance"],["leave","Leave Management"],["absences","Absenteeism Report"],["absence_log","Global Absence Log"]]} active={sub} setActive={setSub}/>

      {sub==="attendance" && (
        <>
          {!currentUserId && (
            <div className="g4" style={{ marginBottom:22 }}>
            {[[
              "Present",
              attendance.filter(a=>a.status==="Present").length,
              "#4ADE80",
              `${attendance.length > 0 ? Math.round(attendance.filter(a=>a.status==="Present").length/attendance.length*100) : 0}% attendance rate`
            ],[
              "On Leave",
              attendance.filter(a=>a.status==="On Leave").length,
              T.orange,
              "Approved absences"
            ],[
              "Late",
              attendance.filter(a=>{ const ci=a.check_in; if(!ci) return false; const t=ci.split("T")[1]||ci; return t.slice(0,8)>"09:00:00"; }).length,
              "#FBB040",
              "Checked in after 09:00 AM"
            ],[
              "Suspicious",
              attendance.filter(a=>a.is_suspicious).length,
              "#F87171",
              "Geofence or device flags"
            ]].map(([label,value,col,sub])=>(
              <StatCard key={label} label={label} value={value} col={col} sub={sub}/>
            ))}
          </div>
          )}
          {currentUser && <AttendanceCheckIn user={currentUser} />}
          <div className="gc" style={{ overflow:"hidden" }}>
            <div style={{ padding:"14px 20px", borderBottom:`1px solid ${C.border}`, display:"flex", justifyContent:"space-between", alignItems:"center", gap:20 }}>
              <div style={{ display:"flex", flexDirection:"column" }}>
                <div className="ho" style={{ fontSize:15 }}>Attendance Records</div>
                <div style={{ fontSize:11, color:C.muted, marginTop:2 }}>{attendance.length} record{attendance.length!==1?"s":""} in selected period</div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ fontSize:12, color:C.muted }}>From</span>
                <input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)} className="inp" style={{ width:"auto", padding:"4px 8px", fontSize:12 }}/>
                <span style={{ fontSize:12, color:C.muted }}>To</span>
                <input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)} className="inp" style={{ width:"auto", padding:"4px 8px", fontSize:12 }}/>
              </div>
            </div>
            {attendance.length === 0 ? (
              <div style={{ padding:"40px 20px", textAlign:"center", color:C.muted }}>
                <div style={{ fontSize:32, marginBottom:8 }}>📋</div>
                <div style={{ fontSize:14, fontWeight:600, marginBottom:4 }}>No attendance records found</div>
                <div style={{ fontSize:12 }}>No check-ins were recorded for this date range.</div>
              </div>
            ) : (
            <table className="ht">
              <thead><tr>{["Date","Employee","Dept","Security","Device","IP","Check In","Check Out","Hours","Status"].map(h=><th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {attendance.map(a=>{
                  const u = a.admins || { full_name: "Unknown Staff", department: "General" };
                  const sc=statusColor[a.status]||C.sub;
                  const ci = a.check_in;
                  const isLate = ci && (ci.split("T")[1]||ci).slice(0,8) > "09:00:00";
                  return (
                    <tr key={a.id}>
                      <td style={{ fontSize:11, fontWeight:600 }}>{new Date(a.date).toLocaleDateString("en-GB", { day:"numeric", month:"short" })}</td>
                      <td><div style={{ display:"flex", alignItems:"center", gap:8 }}><Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={26}/><span style={{ fontWeight:700, fontSize:13 }}>{u.full_name}</span></div></td>
                      <td style={{ color:C.sub, fontSize:11 }}>{u.department || "General"}</td>
                      <td>
                        {a.is_suspicious ? (
                          <div style={{ display:"flex", flexDirection:"column", gap:2 }}>
                            <span className="tg" style={{ background:"#F8717122", color:"#F87171", border:"1px solid #F8717133", fontSize:10 }} title={a.suspicious_reason}>🚩 Flagged</span>
                            <div style={{ fontSize:9, color:"#F87171" }}>{a.distance_meters ? `${Math.round(a.distance_meters)}m away` : "No GPS"}</div>
                          </div>
                        ) : (
                          <span className="tg" style={{ background:"#4ADE8022", color:"#4ADE80", border:"1px solid #4ADE8033", fontSize:10 }}>✓ OK</span>
                        )}
                      </td>
                      <td style={{ fontSize:10, color:C.sub }} title={a.user_agent}>🖥️ {a.device_type || "—"}</td>
                      <td style={{ fontSize:11, color:C.text, fontFamily:"monospace" }}>{a.ip_address || "—"}</td>
                      <td>
                        <div style={{ fontSize:12, fontWeight:600, color: isLate ? "#FBB040" : C.text }}>
                          {ci ? new Date(ci).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : "—"}
                        </div>
                        {isLate && <div style={{ fontSize:9, color:"#FBB040" }}>Late</div>}
                      </td>
                      <td style={{ fontSize:12, color:C.sub }}>{a.check_out ? new Date(a.check_out).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : "—"}</td>
                      <td style={{ color:T.orange, fontWeight:800, fontSize:12 }}>{ci && a.check_out ? (Math.abs(new Date(a.check_out) - new Date(ci)) / 36e5).toFixed(1) + "h" : "—"}</td>
                      <td><span className="tg" style={{ background:`${sc}22`, color:sc, border:`1px solid ${sc}33` }}>{a.status}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            )}
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

      {sub==="absences" && <AbsenceReport staff={[]} currentUserId={currentUserId} C={C} dark={dark}/>}

      {sub==="absence_log" && (
        <div className="fade">
          <div className="gc" style={{ padding:"20px 24px", marginBottom:22 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", flexWrap:"wrap", gap:20 }}>
              <div style={{ display:"flex", gap:14 }}>
                <div>
                  <div style={{ fontSize:10, color:C.muted, marginBottom:6, fontWeight:800, textTransform:"uppercase" }}>Start Date</div>
                  <input type="date" value={logStart} onChange={e=>setLogStart(e.target.value)} className="inp" style={{ width:180 }}/>
                </div>
                <div>
                  <div style={{ fontSize:10, color:C.muted, marginBottom:6, fontWeight:800, textTransform:"uppercase" }}>End Date</div>
                  <input type="date" value={logEnd} onChange={e=>setLogEnd(e.target.value)} className="inp" style={{ width:180 }}/>
                </div>
              </div>
              <button 
                className="bp" 
                onClick={loadGlobalAbsences} 
                disabled={loadingLog}
                style={{ padding:"12px 30px" }}
              >
                {loadingLog ? "Calculating..." : "Generate Global Absence Report"}
              </button>
            </div>
          </div>

          <div className="gc" style={{ overflow:"hidden" }}>
             <div style={{ padding:"16px 22px", borderBottom:`1px solid ${C.border}` }}>
                <div className="ho" style={{ fontSize:15 }}>Global Absence Records</div>
                <div style={{ fontSize:12, color:C.sub, marginTop:2 }}>Showing all missing man-days (excluding weekends & approved leaves)</div>
             </div>
             {globalAbsences.length === 0 && !loadingLog ? (
               <div style={{ padding:60, textAlign:"center", color:C.muted }}>
                  <div style={{ fontSize:40, marginBottom:10 }}>🔍</div>
                  <div style={{ fontSize:14, fontWeight:600 }}>No absences recorded for this period</div>
                  <div style={{ fontSize:12 }}>Or you haven't generated the report yet.</div>
               </div>
             ) : (
               <table className="ht">
                 <thead><tr>{["Date","Staff Name","Department","Status"].map(h=><th key={h}>{h}</th>)}</tr></thead>
                 <tbody>
                   {globalAbsences.map((a,i) => (
                     <tr key={i}>
                       <td style={{ fontWeight:700 }}>{new Date(a.date).toLocaleDateString("en-GB", { weekday:"short", day:"numeric", month:"short" })}</td>
                       <td>{a.staff_name}</td>
                       <td style={{ color:C.sub, fontSize:12 }}>{a.department}</td>
                       <td><span className="tg tr" style={{ fontSize:10 }}>{a.status}</span></td>
                     </tr>
                   ))}
                 </tbody>
               </table>
             )}
          </div>
        </div>
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

// ─── MODULE: ATTENDANCE CHECK-IN ─────────────────────────────────────────────
function AttendanceCheckIn({ user }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;

  const [todayRecord, setTodayRecord]   = useState(null);
  const [loading,     setLoading]       = useState(true);
  const [actionLoading, setActionLoad]  = useState(false);
  const [error,       setError]         = useState(null);
  const [success,     setSuccess]       = useState(null);
  const [locStatus,   setLocStatus]     = useState("idle");

  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "long", year: "numeric", month: "long", day: "numeric"
  });

  function detectDevice() {
    const ua = navigator.userAgent;
    if (/tablet|ipad|playbook|silk/i.test(ua))               return "Tablet";
    if (/mobile|iphone|ipod|android|blackberry|mini|windows\sce|palm/i.test(ua)) return "Mobile";
    return "Desktop";
  }

  useEffect(() => {
    const todayIso = new Date().toISOString().split("T")[0];
    apiFetch(`${API_BASE}/hr/presence/attendance?date=${todayIso}&staff_id=${user.id}`)
      .then(data => {
        if (Array.isArray(data) && data.length > 0) setTodayRecord(data[0]);
      })
      .catch(() => {})
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
            latitude:  pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy:  pos.coords.accuracy,
            status:    "granted",
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
          latitude:          loc.latitude,
          longitude:         loc.longitude,
          location_accuracy: loc.accuracy,
          location_status:   loc.status,
          device_type:       detectDevice(),
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
          latitude:        loc.latitude,
          longitude:       loc.longitude,
          location_status: loc.status,
          device_type:     detectDevice(),
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

  const checkedIn  = !!todayRecord?.check_in;
  const checkedOut = !!todayRecord?.check_out;

  const locBadgeColor = {
    granted:     "#4ADE80",
    denied:      "#F87171",
    unavailable: "#94A3B8",
    idle:        "#94A3B8",
    requesting:  "#FBB040",
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
              {todayRecord.latitude && (
                <><span style={{ color: C.muted }}>Coordinates</span><span>{todayRecord.latitude.toFixed(5)}, {todayRecord.longitude.toFixed(5)}</span></>
              )}
              {todayRecord.location_status && (
                <><span style={{ color: C.muted }}>Location</span>
                <span style={{ color: { granted: "#4ADE80", denied: "#F87171", unavailable: "#94A3B8" }[todayRecord.location_status] }}>
                  {todayRecord.location_status}
                </span></>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            {!checkedIn && (
              <button
                className="bp"
                style={{ flex: 1, padding: "11px 0", fontSize: 14, fontWeight: 700 }}
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
          <TrendChart data={[72, 75, 82, 80, 85, 88]} color={Math.round(b.goals_40_pct+b.quality_20_pct+b.manager_review_40_pct)>=80?"#4ADE80":T.orange} />
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
        <div className="g3">
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
        <div className={isStaff?"g2":"g3"} style={{ gap:14 }}>
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
          <div className="g2" style={{ gap:10, marginBottom:18 }}>
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
            <div className="g2" style={{ gap:12 }}>
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
        <div className="g2" style={{ gap:16 }}>
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
          <div style={{ display:"flex", flexDirection:"column", gap:22 }}>
            <div><Lbl>Personnel Identification *</Lbl>
              <select className="inp" value={nf.uid} onChange={e=>setNf(x=>({...x,uid:e.target.value}))}>
                <option value="">— Select Staff Member —</option>
                {staff.map(u=><option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div className="g2" style={{ gap:16 }}>
              <div><Lbl>Gross Component (₦) *</Lbl><input type="number" className="inp" placeholder="0.00" value={nf.gross} onChange={e=>setNf(x=>({...x,gross:e.target.value}))}/></div>
              <div><Lbl>Tax / Reductions (₦)</Lbl><input type="number" className="inp" placeholder="0.00" value={nf.tax} onChange={e=>setNf(x=>({...x,tax:e.target.value}))}/></div>
            </div>
            <div><Lbl>Transaction Justification / Notes</Lbl><textarea className="inp" placeholder="E.g. Performance Bonus for Q1, Contractor retainer, Reimbursement of expenses..." value={nf.notes} onChange={e=>setNf(x=>({...x,notes:e.target.value}))}/></div>
            <button className="bp" onClick={addManual} style={{ padding:16, fontSize:15 }}>Submit Payroll Record</button>
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

// ─── HELPER: ORG CHART ───────────────────────────────────────────────────────
function OrgChartView({ staff }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  
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
      <div key={node.id} style={{ display:"flex", flexDirection:"column", alignItems:"center", padding:"0 10px" }}>
          <div style={{ background:C.surface, border:`2px solid rgb(249, 115, 22)`, borderRadius:12, padding:"12px 18px", display:"flex", alignItems:"center", gap:12, minWidth:220, position:"relative", zIndex:2, boxShadow:"0 4px 12px rgba(0,0,0,0.1)" }}>
              <Av av={node.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={38}/>
              <div>
                  <div style={{ fontSize:13, fontWeight:800, color:C.text }}>{node.full_name}</div>
                  <div style={{ fontSize:11, color:C.sub }}>{node.staff_profiles?.[0]?.job_title || node.role}</div>
                  <div style={{ fontSize:10, color:"#F97316", fontWeight:700 }}>{node.department}</div>
              </div>
          </div>
          {node.children.length > 0 && (
              <div style={{ display:"flex", position:"relative", marginTop:20, paddingTop:20 }}>
                  <div style={{ position:"absolute", top:0, left:"50%", width:2, height:20, background:`${C.border}`, transform:"translateX(-50%)" }} />
                  {node.children.length > 1 && (
                      <div style={{ position:"absolute", top:20, left:"50%", right:"50%", height:2, background:`${C.border}` }} />
                  )}
                  {node.children.map(child => (
                      <div key={child.id} style={{ position:"relative", display:"flex", flexDirection:"column", alignItems:"center" }}>
                          <div style={{ position:"absolute", top:-20, left:"50%", width:2, height:20, background:`${C.border}`, transform:"translateX(-50%)" }} />
                          {renderNode(child)}
                      </div>
                  ))}
              </div>
          )}
      </div>
  );

  return (
      <div style={{ overflowX:"auto", padding:"40px 0", minHeight:500, display:"flex", justifyContent:"center" }}>
          {tree.length > 0 ? (
              <div style={{ display:"flex", gap:40 }}>
                  {tree.map(root => renderNode(root))}
              </div>
          ) : (
              <div style={{ color:C.muted, marginTop:40 }}>No org chart data available.</div>
          )}
      </div>
  );
}

// ─── MODULE: STAFF DIRECTORY ─────────────────────────────────────────────────
function StaffDirectory({ authRole }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const viewOnly = authRole !== "hr";
  const [tab, setTab] = useState("full");
  const [view, setView] = useState(null);
  const [dtTab, setDtTab] = useState("details");
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newStaff, setNewStaff] = useState({ full_name:"", email:"", password:"", confirm_password:"", roles:["staff"], primary_role:"staff", staff_type:"full", department:"", line_manager_id:null });
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
      setNewStaff({ full_name:"", email:"", password:"", confirm_password:"", roles:["staff"], primary_role:"staff", staff_type:"full", department:"", line_manager_id:null });
      loadStaff();
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const archiveStaff = async () => {
    if(!view) return;
    const date = prompt("Enter Exit Date (YYYY-MM-DD):", new Date().toISOString().split('T')[0]);
    if(!date) return;
    const reason = prompt("Enter Exit Reason:");
    if(!reason) return;
    
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
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>Staff Directory</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>Full profiles — HR access only. Staff cannot see each other's records.</div>
        </div>
        <button className="bp" onClick={() => setShowAdd(true)}>+ Add Staff</button>
      </div>
      <div style={{ display:"flex", gap:12, alignItems:"center", marginBottom:16, flexWrap:"wrap" }}>
        <input
          className="inp"
          style={{ flex:1, minWidth:260 }}
          placeholder="Search staff by name, email, department, role"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div style={{ fontSize:13, color:C.sub }}>{activeList.length} active · {archivedList.length} archived</div>
      </div>
      <Tabs items={[["full","Full Staff"],["contractor","Contractors"],["onsite","Onsite / Labourers"], ["org","Org Chart"]]} active={tab} setActive={setTab}/>
      {loading ? (
        <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading staff records…</div>
      ) : tab === "org" ? (
        <OrgChartView staff={staff} />
      ) : activeList.length === 0 ? (
        <div className="gc" style={{ padding:48, textAlign:"center", color:C.muted }}>No active {tab} staff found.</div>
      ) : (
        <div className="g3" style={{ marginBottom:22 }}>
          {activeList.map(u => {
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
                <div className="g2" style={{ gap:8, marginBottom:12 }}>
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

      {archivedList.length > 0 && (
        <div style={{ marginTop:24 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
            <div style={{ fontSize:18, fontWeight:800 }}>Archived / Deactivated Staff</div>
            <div style={{ fontSize:13, color:C.sub }}>{archivedList.length} record{archivedList.length === 1 ? '' : 's'}</div>
          </div>
          <div className="g3" style={{ marginBottom:22 }}>
            {archivedList.map(u => {
              const prof = u.staff_profiles?.[0] || {};
              const sc = u.performance?.score;
              return (
                <div key={u.id} className="gc" style={{ padding:20, cursor:"pointer", opacity:0.88 }} onClick={()=>setView(u)}>
                  <div style={{ display:"flex", gap:14, alignItems:"center", marginBottom:14 }}>
                    <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={44}/>
                    <div>
                      <div style={{ fontSize:14, fontWeight:800, color:C.text }}>{u.full_name}</div>
                      <div style={{ fontSize:12, color:C.sub }}>{prof.job_title || u.role}</div>
                      <div style={{ fontSize:11, color:T.orange, fontWeight:800, marginTop:2 }}>{u.department}</div>
                    </div>
                  </div>
                  <div className="g2" style={{ gap:8, marginBottom:12 }}>
                    {[['Role',u.role?.replace(/,/g,' , ')],['Type',prof.staff_type||"full"],['Email',u.email?.split("@")[0]+"…"],['Status','Archived']].map(([l,v])=>(
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
        </div>
      )}

      {/* ADD STAFF MODAL */}
      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} title="Add New Staff Member" width={580}>
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <div className="g2" style={{ gap:12 }}>
              <div><Lbl>Full Name *</Lbl><input className="inp" placeholder="e.g. Adeola Balogun" value={newStaff.full_name} onChange={e=>setNewStaff(s=>({...s,full_name:e.target.value}))}/></div>
              <div><Lbl>Email Address *</Lbl><input className="inp" type="email" placeholder="adeola@eximps-cloves.com" value={newStaff.email} onChange={e=>setNewStaff(s=>({...s,email:e.target.value}))}/></div>
              <div><Lbl>Default Password *</Lbl><input className="inp" type="password" placeholder="Min 8 characters" value={newStaff.password} onChange={e=>setNewStaff(s=>({...s,password:e.target.value}))}/></div>
              <div><Lbl>Confirm Password *</Lbl><input className="inp" type="password" placeholder="Repeat password" value={newStaff.confirm_password} onChange={e=>setNewStaff(s=>({...s,confirm_password:e.target.value}))}/></div>
              <div style={{ gridColumn: '1 / -1' }}>
                <Lbl>System Roles *</Lbl>
                <div style={{ display:"flex", flexWrap:"wrap", gap:10, marginTop:6 }}>
                  {['staff','sales_rep','admin','lawyer','line_manager'].map(role => (
                    <label key={role} style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'8px 12px', border:`1px solid ${C.border}`, borderRadius:10, cursor:'pointer' }}>
                      <input type="checkbox" checked={newStaff.roles.includes(role)} onChange={() => toggleNewStaffRole(role)} />
                      {role.replace('_',' ')}
                    </label>
                  ))}
                </div>
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
              <div><Lbl>Staff Type</Lbl>
                <select className="inp" value={newStaff.staff_type} onChange={e=>setNewStaff(s=>({...s,staff_type:e.target.value}))}>
                  <option value="full">Full Staff</option>
                  <option value="contractor">Contractor</option>
                  <option value="onsite">Onsite / Labourer</option>
                </select>
              </div>
              <div><Lbl>Department</Lbl><input className="inp" placeholder="e.g. Sales & Acquisitions" value={newStaff.department} onChange={e=>setNewStaff(s=>({...s,department:e.target.value}))}/></div>
              <div style={{ gridColumn: '1 / -1' }}>
                <Lbl>Line Manager</Lbl>
                <select className="inp" value={newStaff.line_manager_id || ""} onChange={e => setNewStaff(s=>({...s,line_manager_id: e.target.value || null}))}>
                  <option value="">— Select Line Manager —</option>
                  {staff.filter(s => s.id).map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}
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
          
          {authRole === "hr" && (
            <div style={{ display:"flex", gap:10, marginBottom:18 }}>
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

          <Tabs items={[["details","Personnel Identity"],["bank","Finances"],["assets","Assets"],["docs","Documents"]]} active={dtTab} setActive={setDtTab}/>

          {dtTab === "details" && (
            <div className="g2 fade" style={{ gap:10, marginBottom:18 }}>
              <Field label="Full Name" value={view.full_name}/>
              <Field label="Email Address" value={view.email}/>
              <Field label="Role" value={view.role?.replace(/,/g,' , ')}/>
              <Field label="Primary Role" value={view.primary_role}/>
              <Field label="Line Manager" value={getStaffNameById(view.line_manager_id)}/>
              {editMode ? (
                <>
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
                    <div style={{ display:'flex', flexWrap:'wrap', gap:10, marginTop:6 }}>
                      {['staff','sales_rep','admin','lawyer','line_manager'].map(role => (
                        <label key={role} style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'8px 12px', border:`1px solid ${C.border}`, borderRadius:10, cursor:'pointer' }}>
                          <input type="checkbox" checked={draftView.roles?.includes(role)} onChange={() => setDraftView(d => ({ ...d, roles: d.roles?.includes(role) ? d.roles.filter(r => r !== role) : [...(d.roles || []), role] }))} />
                          {role.replace('_',' ')}
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
                  <Field label="Phone" value={view.staff_profiles?.[0]?.phone_number}/>
                  <Field label="Emergency Contact" value={view.staff_profiles?.[0]?.emergency_contact}/>
                  <Field label="Address" value={view.staff_profiles?.[0]?.address}/>
                  <Field label="Bio" value={view.staff_profiles?.[0]?.bio}/>
                  <Field label="Gender" value={view.staff_profiles?.[0]?.gender}/>
                  <Field label="DOB" value={view.staff_profiles?.[0]?.dob}/>
                  <Field label="Nationality" value={view.staff_profiles?.[0]?.nationality}/>
                  <Field label="Marital Status" value={view.staff_profiles?.[0]?.marital_status}/>
                  <Field label="Leave Quota" value={view.staff_profiles?.[0]?.leave_quota ? `${view.staff_profiles?.[0]?.leave_quota} days/yr` : '20 days/yr'}/>
                </>
              )}
              {view.is_active === false && (
                <>
                  <Field label="Exit Date" value={view.staff_profiles?.[0]?.exit_date}/>
                  <Field label="Exit Reason" value={view.staff_profiles?.[0]?.exit_reason}/>
                </>
              )}
            </div>
          )}

          {dtTab === "bank" && (
            <div className="g1 fade" style={{ gap:10, marginBottom:18 }}>
              <Field label="Bank Name" value={view.staff_profiles?.[0]?.bank_name}/>
              <Field label="Account Number" value={view.staff_profiles?.[0]?.account_number}/>
              <Field label="Account Name" value={view.staff_profiles?.[0]?.account_name}/>
              <Field label="Monthly Base Salary" value={view.staff_profiles?.[0]?.base_salary ? `₦${Number(view.staff_profiles[0].base_salary).toLocaleString()}` : "Not Set"}/>
              <div style={{ padding:12, background:`${T.orange}0D`, border:`1px solid ${T.orange}22`, borderRadius:8, fontSize:12, color:(dark?DARK:LIGHT).muted }}>
                Payment info is only visible to HR and Finance teams.
              </div>
            </div>
          )}

          {dtTab === "assets" && (
            <div className="fade">
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:12 }}>
                <div className="ho" style={{ fontSize:13 }}>Company Assets</div>
                <button className="bp" style={{ fontSize:11, padding:"4px 10px" }}>+ Assign Asset</button>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {view.staff_assets?.length > 0 ? (
                  view.staff_assets.map((a,i) => (
                    <div key={i} style={{ display:"flex", justifyContent:"space-between", padding:"10px 14px", background:`${C.surface}`, border:`1px solid ${C.border}`, borderRadius:10 }}>
                      <div><div style={{ fontSize:13, fontWeight:700 }}>{a.asset_name}</div><div style={{ fontSize:11, color:C.muted }}>{a.serial_number || "No Serial"} · Assigned {new Date(a.assigned_at).toLocaleDateString()}</div></div>
                      <span className="tg to" style={{ fontSize:10 }}>{a.condition || "Good"}</span>
                    </div>
                  ))
                ) : <div style={{ fontSize:12, color:C.muted, textAlign:"center", padding:20 }}>No assets assigned to this staff member.</div>}
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

          {!viewOnly && view.is_active !== false && (
            <div style={{ marginTop:22, borderTop:`1px solid ${C.border}`, paddingTop:22 }}>
              <button className="bd" style={{ width:"100%" }} onClick={archiveStaff}>Archive & Deactivate Staff</button>
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
      <div style={{ marginBottom:26 }}>
        <div className="ho" style={{ fontSize:26, marginBottom:4 }}>HR Overview</div>
        <div style={{ fontSize:13, color:C.sub }}>Live workforce intelligence — Eximp & Cloves Infrastructure Limited.</div>
      </div>
      {loading ? <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading workforce metrics…</div> : (
        <>
          {/* Row 1 — Live Today */}
          <div className="g4" style={{ marginBottom:14 }}>
            <StatCard label="Total Workforce" value={total} sub="Active Staff Members"/>
            <StatCard label="Present Today" value={a.present_today || 0} col="#4ADE80" sub={`${a.late_today || 0} checked in late`}/>
            <StatCard label="Absent Today" value={a.absent_today || 0} col="#F87171" sub={a.absent_names?.length > 0 ? "Action required" : "All accounted for"}/>
            <StatCard label="Suspicious" value={a.suspicious_today || 0} col="#FBB040" sub="Geofence violations"/>
          </div>
          {/* Row 2 — Ops Overview */}
          <div className="g4" style={{ marginBottom:22 }}>
            <StatCard label="On Leave" value={a.on_leave_today || 0} col="#60A5FA" sub="Approved leave today"/>
            <StatCard label="Pending Leaves" value={pendingLeaves} col={T.orange} sub="Awaiting approval"/>
            <StatCard label="Open Tasks" value={openTasks} col="#A78BFA" sub="Across all teams"/>
            <StatCard label="Critical Flags" value={seriousFlags} col="#F87171" sub="Disciplinary — urgent"/>
          </div>

          <div className="g2w" style={{ marginBottom:22 }}>
            <div style={{ display:"flex", flexDirection:"column", gap:22 }}>
              <div className="gc" style={{ padding:22 }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:18 }}>
                  <div className="ho" style={{ fontSize:16 }}>Workforce by Department</div>
                </div>
                {Object.entries(a.department_distribution || {}).map(([dept, count]) => (
                  <div key={dept} style={{ marginBottom:14 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:5 }}>
                      <span style={{ fontWeight:600, color:C.text }}>{dept}</span>
                      <span style={{ color:C.sub }}>{count} ({Math.round(count/total*100)}%)</span>
                    </div>
                    <div style={{ height:6, background:`${C.border}`, borderRadius:3, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${(count/total)*100}%`, background:T.orange }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="gc" style={{ padding:22 }}>
                 <div className="ho" style={{ fontSize:15, marginBottom:16 }}>Absence Log</div>
                 {a.absent_names?.length > 0 ? (
                   <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                     {a.absent_names.map(name => (
                       <div key={name} style={{ padding:"6px 12px", background:`${C.border}44`, borderRadius:20, fontSize:12, border:`1px solid ${C.border}` }}>
                         👤 {name}
                       </div>
                     ))}
                   </div>
                 ) : (
                   <div style={{ fontSize:13, color:"#4ADE80", textAlign:"center", padding:10 }}>✅ Everyone has checked in!</div>
                 )}
              </div>
            </div>
            <div className="gc" style={{ padding:22 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
                <div className="ho" style={{ fontSize:14 }}>Latest Active Staff</div>
                <span style={{ fontSize:11, color:C.muted }}>Recent Onboarding</span>
              </div>
              <div className="tw"><table className="ht">
                <thead><tr>{["Staff","Department","Role"].map(h=><th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {data.staff?.slice(0,5).map(u => (
                    <tr key={u.id}>
                      <td><div style={{ display:"flex", alignItems:"center", gap:10 }}><Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={24}/><span style={{ fontWeight:700 }}>{u.full_name}</span></div></td>
                      <td style={{ color:C.sub }}>{u.department}</td>
                      <td><span className="tg to" style={{ fontSize:9 }}>{u.role?.toUpperCase()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
              <div className="gc" style={{ padding:22 }}>
                <div className="ho" style={{ fontSize:14, marginBottom:16 }}>Administrative Alerts</div>
                {[
                  [`${pendingLeaves} Leave Requests Pending`, T.orange],
                  [`${seriousFlags} Serious Disciplinary Cases`, "#F87171"],
                  ["Payroll Processing Due", "#4ADE80"],
                  [
                    <button 
                      onClick={async () => {
                        if(!confirm("This will apply all pending database migrations. Proceed?")) return;
                        try {
                          const res = await apiFetch(`${API_BASE}/hr/migrate`, { method: "POST" });
                          alert(res.message);
                          window.location.reload();
                        } catch(e) { alert("Migration failed: " + e.message); }
                      }} 
                      className="bp" 
                      style={{ fontSize:10, padding:"6px 12px", marginTop:4 }}
                    >
                      🚀 Run System Update (Fix DB)
                    </button>, 
                    "#60A5FA"
                  ]
                ].map(([l,c],i)=>(
                  <div key={i} style={{ display:"flex", gap:12, alignItems:"center", marginBottom:12, padding:"12px 14px", background:`${c}0D`, border:`1px solid ${c}22`, borderRadius:10 }}>
                    {typeof l === 'string' && <div style={{ width:8, height:8, borderRadius:"50%", background:c }}/>}
                    <span style={{ fontSize:13, color:C.text }}>{l}</span>
                  </div>
                ))}
              </div>

              <div className="gc" style={{ padding:22 }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
                  <div className="ho" style={{ fontSize:14 }}>Recent Milestones</div>
                  <span style={{ fontSize:11, color:C.muted }}>Last 30 Days</span>
                </div>
                {a.recent_milestones?.length > 0 ? (
                  a.recent_milestones.map(m => (
                    <div key={m.id} style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                      <Av av={m.full_name?.split(" ").map(n=>n[0]).join("")} sz={24}/>
                      <div style={{ flex:1 }}>
                         <div style={{ fontSize:12, fontWeight:600 }}>{m.full_name}</div>
                         <div style={{ fontSize:10, color:C.sub }}>Joined {new Date(m.created_at).toLocaleDateString()}</div>
                      </div>
                      <span className="tg" style={{ fontSize:8, background:"#4ADE8011", color:"#4ADE80", border:"1px solid #4ADE8022" }}>NEW HIRE</span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize:11, color:C.muted, textAlign:"center", padding:10 }}>No recent onboarding.</div>
                )}
              </div>

              {a.upcoming_birthdays?.length > 0 && (
                <div className="gc" style={{ padding:22, marginTop:22 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
                    <div className="ho" style={{ fontSize:14 }}>Upcoming Birthdays 🎂</div>
                    <span style={{ fontSize:11, color:C.muted }}>Next 14 Days</span>
                  </div>
                  {a.upcoming_birthdays.map((b, i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                      <Av av={b.full_name?.split(" ").map(n=>n[0]).join("")} sz={28} />
                      <div style={{ flex:1 }}>
                         <div style={{ fontSize:12, fontWeight:700 }}>{b.full_name}</div>
                         <div style={{ fontSize:10, color:C.sub }}>{new Date(b.date).toLocaleDateString('en-GB', { day:'numeric', month:'short' })}</div>
                      </div>
                      <span className="tg" style={{ fontSize:9, background:"#FBB04022", color:"#FBB040", border:"1px solid #FBB04044" }}>
                         {b.days_left === 0 ? "TODAY!" : `in ${b.days_left}d`}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {a.upcoming_anniversaries?.length > 0 && (
                <div className="gc" style={{ padding:22, marginTop:22 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
                    <div className="ho" style={{ fontSize:14 }}>Work Anniversaries 🎊</div>
                    <span style={{ fontSize:11, color:C.muted }}>Next 30 Days</span>
                  </div>
                  {a.upcoming_anniversaries.map((anniv, i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                      <Av av={anniv.full_name?.split(" ").map(n=>n[0]).join("")} sz={28} gold/>
                      <div style={{ flex:1 }}>
                         <div style={{ fontSize:12, fontWeight:700 }}>{anniv.full_name}</div>
                         <div style={{ fontSize:10, color:C.sub }}>{anniv.years} years on {new Date(anniv.date).toLocaleDateString('en-GB', { day:'numeric', month:'short' })}</div>
                      </div>
                      <span className="tg" style={{ fontSize:9, background:"#60A5FA22", color:"#60A5FA", border:"1px solid #60A5FA44" }}>
                         {anniv.days_left === 0 ? "TODAY!" : `in ${anniv.days_left}d`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Staff on Leave — full panel */}
          <div className="g2" style={{ marginBottom:22 }}>
            {/* On Leave Today */}
            <div className="gc" style={{ padding:22 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
                <div className="ho" style={{ fontSize:15 }}>Staff on Leave Today</div>
                <span className="tg" style={{ background:`${T.orange}22`, color:T.orange, border:`1px solid ${T.orange}33`, fontSize:10 }}>
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
                    <div key={l.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"12px 14px", background:`${T.orange}08`, border:`1px solid ${T.orange}22`, borderRadius:10, marginBottom:8 }}>
                      <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={34}/>
                      <div style={{ flex:1 }}>
                        <div style={{ fontWeight:700, fontSize:13 }}>{u.full_name}</div>
                        <div style={{ fontSize:11, color:C.sub, marginTop:2 }}>
                          {l.leave_type} · Returns {returnDate.toLocaleDateString("en-GB", { day:"numeric", month:"short" })}
                        </div>
                      </div>
                      <div style={{ textAlign:"right" }}>
                        <div style={{ fontSize:11, fontWeight:700, color:T.orange }}>{l.days_count}d</div>
                        <div style={{ fontSize:9, color:C.muted }}>leave</div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign:"center", padding:"20px 0", color:C.muted }}>
                  <div style={{ fontSize:24, marginBottom:6 }}>🏢</div>
                  <div style={{ fontSize:12 }}>All staff are in today!</div>
                </div>
              )}
            </div>

            {/* Upcoming Leaves This Week */}
            <div className="gc" style={{ padding:22 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
                <div className="ho" style={{ fontSize:15 }}>Upcoming Leaves</div>
                <span style={{ fontSize:11, color:C.muted }}>Next 7 Days</span>
              </div>
              {data.leaves?.filter(l => {
                if (l.status !== "approved") return false;
                const today = new Date(); today.setHours(0,0,0,0);
                const nextWeek = new Date(today); nextWeek.setDate(today.getDate() + 7);
                const start = new Date(l.start_date);
                return start > today && start <= nextWeek;
              }).slice(0,5).length > 0 ? (
                data.leaves.filter(l => {
                  if (l.status !== "approved") return false;
                  const today = new Date(); today.setHours(0,0,0,0);
                  const nextWeek = new Date(today); nextWeek.setDate(today.getDate() + 7);
                  const start = new Date(l.start_date);
                  return start > today && start <= nextWeek;
                }).slice(0,5).map(l => {
                  const u = l.admins || {};
                  return (
                    <div key={l.id} style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                      <Av av={u.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={28}/>
                      <div style={{ flex:1 }}>
                        <div style={{ fontSize:13, fontWeight:600 }}>{u.full_name}</div>
                        <div style={{ fontSize:11, color:C.sub }}>
                          {l.leave_type} · {new Date(l.start_date).toLocaleDateString("en-GB", {day:"numeric", month:"short"})} → {new Date(l.end_date).toLocaleDateString("en-GB", {day:"numeric", month:"short"})}
                        </div>
                      </div>
                      <span style={{ fontSize:11, fontWeight:700, color:"#60A5FA" }}>{l.days_count}d</span>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign:"center", padding:"20px 0", color:C.muted, fontSize:12 }}>No approved leaves in the next 7 days.</div>
              )}
            </div>
          </div>

          <div className="gc" style={{ padding:22 }}>
            <div className="ho" style={{ fontSize:14, marginBottom:14 }}>Recent Open Tasks</div>
            <div className="g4" style={{ gap:12 }}>
              {(data.tasks || []).filter(t => t.status !== "completed").slice(0, 8).map(t => {
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

  if (loading) return <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading your profile…</div>;
  if (!prof)   return <div style={{ padding:40, textAlign:"center", color:"#F87171" }}>Could not load profile data.</div>;

  const p = prof.staff_profiles?.[0] || {};

  return (
    <div className="fade" style={{ maxWidth:720 }}>
      <div className="gc" style={{ padding:30, marginBottom:18 }}>
        <div style={{ display:"flex", gap:20, alignItems:"center", justifyContent:"space-between", marginBottom:26 }}>
          <div style={{ display:"flex", gap:20, alignItems:"center" }}>
            <Av av={prof.full_name?.split(" ").map(n=>n[0]).join("") || "??"} sz={70} gold/>
            <div>
              <div className="ho" style={{ fontSize:26 }}>{prof.full_name}</div>
              <div style={{ fontSize:14, color:C.sub }}>{p.job_title || prof.role}</div>
              <div style={{ fontSize:13, color:T.orange, fontWeight:800, marginTop:4 }}>{prof.department}</div>
              {p.bio && <div style={{ marginTop:14, maxWidth:520, fontSize:13, lineHeight:1.6, color:C.sub }}>{p.bio}</div>}
            </div>
          </div>
          <div style={{ display:"flex", gap:10, alignItems:"center" }}>
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

        <Tabs items={[["details","Personnel Identity"],["assets","My Assets"],["bank","Finances"],["docs","My Documents"]]} active={tab} setActive={setTab}/>

        {tab === "details" && (
          <div className="g2 fade" style={{ gap:12 }}>
            <Field label="Full Name" value={prof.full_name}/>
            <Field label="Email Address" value={prof.email}/>
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
                <Field label="Phone" value={p.phone_number}/>
                <Field label="Address" value={p.address}/>
                <Field label="Emergency Contact" value={p.emergency_contact}/>
                <Field label="Bio" value={p.bio}/>
                <Field label="Gender" value={p.gender}/>
                <Field label="DOB" value={p.dob}/>
                <Field label="Nationality" value={p.nationality}/>
                <Field label="Marital Status" value={p.marital_status}/>
              </>
            )}
          </div>
        )}

        {tab === "assets" && (
          <div className="fade">
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:12 }}>
              <div className="ho" style={{ fontSize:13 }}>My Company Assets</div>
            </div>
            {p.staff_assets?.length > 0 ? (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {p.staff_assets.map((a,i) => (
                  <div key={i} style={{ display:"flex", justifyContent:"space-between", padding:"12px 16px", background:C.surface, border:`1px solid ${C.border}`, borderRadius:12 }}>
                    <div>
                      <div style={{ fontSize:14, fontWeight:700 }}>{a.asset_name}</div>
                      <div style={{ fontSize:12, color:C.muted }}>{a.serial_number || "No serial"} · Assigned {new Date(a.assigned_at).toLocaleDateString()}</div>
                    </div>
                    <span className="tg to" style={{ fontSize:10 }}>{a.condition || "Good"}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding:28, textAlign:"center", color:C.muted, border:`1px dashed ${C.border}`, borderRadius:12 }}>No assets have been assigned to you yet.</div>
            )}
          </div>
        )}

        {tab === "bank" && (
          <div className="g1 fade" style={{ gap:12 }}>
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

function Portal({ user, onLogout, navItems, roleLabel, renderPage, initialPage }) {
  const [page, setPage] = useState(initialPage || navItems[0].id);
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
      <div className="hrm-main" style={{ flex:1, display:"flex", flexDirection:"column", minWidth:0 }}>
        <Topbar title={navItems.find(n=>n.id===page)?.label||""} user={user}/>
        <div className="hrm-content-padding" style={{ flex:1, padding:28 }}>
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
      if (p==="staff")     return <StaffDirectory authRole="hr"/>;
      if (p==="presence")  return <Presence currentUserId={user.id} currentUser={user}/>;
      if (p==="perf")      return <Performance/>;
      if (p==="goals")     return <Goals canManageKpiTemplates />;
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
      if (p==="team")      return <StaffDirectory authRole="manager"/>;
      if (p==="presence")  return <Presence currentUserId={user.id} currentUser={user}/>;
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
          
          <div className="g3" style={{ marginBottom:22 }}>
            <StatCard label="Direct Reports" value={team.length}/>
            <StatCard label="Active Tasks" value="8" col="#60A5FA"/>
            <StatCard label="Avg Team Score" value="82/100" col="#4ADE80"/>
          </div>

          {loading ? <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading team data…</div> : (
            <div className="g3">
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

  const staffType = user.staff_type || user.staff_profiles?.[0]?.staff_type || "full";
  const startPage = (staffType === "contractor" || staffType === "onsite") ? "profile" : "dashboard";

  return (
    <Portal user={user} onLogout={onLogout} navItems={nav} roleLabel="Team Member Portal" initialPage={startPage} renderPage={pg=>{
      if (pg==="profile")   return <MyProfile user={user}/>;
      if (pg==="perf")      return <Performance viewOnly userId={user.id}/>;
      if (pg==="goals")     return <Goals viewOnly userId={user.id}/>;
      if (pg==="tasks")     return <Tasks currentUser={user}/>;
      if (pg==="presence")  return <Presence currentUserId={user.id} currentUser={user}/>;
      if (pg==="payslip")   return <MyPayslip user={user}/>;
      if (pg==="mismanage") return <Mismanagement viewOnly userId={user.id}/>;
      
      return (
        <div className="fade">
          <div className="ho" style={{ fontSize:24, marginBottom:4 }}>Welcome, {user.full_name?.split(" ")[0]} 👋</div>
          <div style={{ fontSize:13, color:C.sub, marginBottom:22 }}>{user.staff_profiles?.[0]?.job_title || user.role} · {user.department}</div>
          
          <div className="g4" style={{ marginBottom:22 }}>
            <StatCard label="My Score" value={sc != null ? `${sc}/100` : "—"} col={col}/>
            <StatCard label="My Tasks" value={tasks.length} col="#60A5FA"/>
            <StatCard label="Pending" value={pendingTasks.length} col={T.orange}/>
            <StatCard label="Leave Left" value="11d"/>
          </div>

          <div className="g2" style={{ gap:18 }}>
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
