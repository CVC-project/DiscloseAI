// app.jsx — DiscloseAI: Phase 1 Intro → Phase 2 Galaxy → Phase 3 Sector → Phase 4 Company
const { useState, useEffect, useRef, useCallback } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "galaxyStyle": "cinematic",
  "transitionStyle": "zoom",
  "panelTone": "glass",
  "sectorVisual": "color",
  "orbitMotion": "concentric",
  "showFps": false
}/*EDITMODE-END*/;

const AI_GREETINGS = {
  galaxy: [
    { who: 'ai', text: "Welcome back, Captain. KOSPI is +0.42% — Semiconductor leads, Biotech lags." },
    { who: 'ai', text: "Pick any sector to dive in. I'll brief you on what's moving inside." },
  ],
  sector: [
    { who: 'ai', text: "We're now inside the sector. Each glowing node is a listed company." },
    { who: 'ai', text: "Click a company — I'll surface its disclosures and related entities." },
  ],
  company: [
    { who: 'ai', text: "Tracking this company. Solid lines are equity ties, dashed are group/related-party links." },
    { who: 'ai', text: "Press ENTER CORPORATION for the full financial dossier." },
  ],
};

// ─── Intro screen ──────────────────────────────────────────────────────────
function IntroScreen({ stage, onEnter }) {
  const [pulse, setPulse] = useState(0);
  useEffect(() => {
    let raf, t0 = performance.now();
    const tick = () => {
      setPulse((performance.now() - t0) / 1000);
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, []);
  const fade = stage > 0.3 ? Math.max(0, 1 - (stage - 0.3) * 2.2) : 1;

  return (
    <div className="intro-overlay" style={{ opacity: fade, pointerEvents: stage > 0.05 ? 'none' : 'auto' }}>
      <div className="hud-top">
        <div className="hud-brand">
          <div className="hud-logo">◉</div>
          <div className="hud-brand-text">
            <div className="hud-brand-name">DISCLOSE<span style={{color:'#5eead4'}}>AI</span></div>
            <div className="hud-brand-sub">CORPORATE GALAXY ATLAS · v2.4</div>
          </div>
        </div>
        <div className="hud-meta">
          <div className="hud-meta-row"><span className="hud-meta-k">SESSION</span><span className="hud-meta-v">DA-{(2604 + Math.floor(pulse)).toString().padStart(4,'0')}</span></div>
          <div className="hud-meta-row"><span className="hud-meta-k">UPLINK</span><span className="hud-meta-v" style={{color:'#5eead4'}}>● STABLE · 42ms</span></div>
          <div className="hud-meta-row"><span className="hud-meta-k">UTC</span><span className="hud-meta-v">{new Date().toISOString().slice(11,19)}Z</span></div>
        </div>
      </div>
      <div className="intro-center">
        <div className="intro-eyebrow">— TRANSMISSION FROM THE MARKET —</div>
        <h1 className="intro-headline">
          <span className="intro-line-1">What twelve headlines</span>
          <span className="intro-line-2">missed,</span>
          <span className="intro-line-3">a single number</span>
          <span className="intro-line-4">was already <em>whispering.</em></span>
        </h1>
        <div className="intro-sub">
          KOSPI · 1,400 disclosures / day · decoded by AI<br/>
          A spatial atlas of Korea's listed companies.
        </div>
        <button className="enter-button" onClick={onEnter}>
          <span className="enter-icon">▷</span>
          <span className="enter-label">ENTER THE GALAXY</span>
          <span className="enter-hint">click anywhere</span>
        </button>
      </div>
      <div className="hud-rail hud-rail-left">
        <div className="rail-tick">SECTORS · 16</div>
        <div className="rail-tick">PLANETS · 50</div>
        <div className="rail-tick">EDGES · 312</div>
        <div className="rail-tick">LIVE PULSES · 8</div>
      </div>
      <div className="hud-rail hud-rail-right">
        <div className="rail-tick">RA  04h 32m</div>
        <div className="rail-tick">DEC +21° 18′</div>
        <div className="rail-tick">Z   0.000142</div>
        <div className="rail-tick">T+0{Math.floor(pulse).toString().padStart(3,'0')}s</div>
      </div>
      <div className="hud-bottom">
        <div className="hud-bottom-l">
          <span className="hud-dot" />
          <span>OBSERVATORY ONLINE</span>
          <span className="hud-sep">/</span>
          <span>16 SECTORS · 50 PLANETS</span>
          <span className="hud-sep">/</span>
          <span>NEW DISCLOSURES TONIGHT · 47</span>
        </div>
        <div className="hud-bottom-r">
          <span>2026 AI ROOKIE · MSIT</span>
        </div>
      </div>
      <div className="intro-click" onClick={onEnter} />
    </div>
  );
}

// ─── Top tabs ──────────────────────────────────────────────────────────────
function TopTabs({ active, onChange, breadcrumb }) {
  const tabs = [
    { id: 'finance',   en: 'FINANCIALS',  ko: '재무정보' },
    { id: 'disclose',  en: 'DISCLOSURES', ko: '공시' },
    { id: 'timemach',  en: 'TIME MACHINE',ko: '타임머신' },
  ];
  return (
    <div className="top-tabs">
      <div className="top-tabs-brand">
        <div className="top-brand-mark">◉</div>
        <div className="top-brand-name">DISCLOSE<span style={{color:'#5eead4'}}>AI</span></div>
        {breadcrumb && (
          <div className="top-breadcrumb">
            {breadcrumb.map((b, i) => (
              <React.Fragment key={i}>
                <span className={"crumb " + (b.onClick ? 'is-clickable' : '')} onClick={b.onClick}>{b.label}</span>
                {i < breadcrumb.length - 1 && <span className="crumb-sep">›</span>}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
      <div className="top-tabs-row">
        {tabs.map(t => (
          <div key={t.id} className={"top-tab " + (active === t.id ? 'is-active' : '')} onClick={() => onChange(t.id)}>
            <div className="top-tab-en">{t.en}</div>
            <div className="top-tab-ko">{t.ko}</div>
          </div>
        ))}
      </div>
      <div className="top-tabs-status">
        <span className="hud-dot" />
        <span style={{color:'#94a3b8',fontSize:11,letterSpacing:'.08em'}}>KOSPI</span>
        <span style={{color:'#5eead4',fontSize:13,fontWeight:600}}>3,142.80</span>
        <span style={{color:'#4ade80',fontSize:11}}>+0.42%</span>
      </div>
    </div>
  );
}

// ─── PHASE 2: Mascot panel (top-left) ──────────────────────────────────────
function MascotPanel({ messages = ["섹터를 클릭하면, 기업을 확인할 수 있어요!"] }) {
  const [msgIdx, setMsgIdx] = useState(0);
  useEffect(() => {
    if (messages.length <= 1) return;
    const id = setInterval(() => setMsgIdx(i => (i + 1) % messages.length), 4500);
    return () => clearInterval(id);
  }, [messages.length]);
  return (
    <div className="panel panel-tl mascot-panel">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" />
          <span className="panel-title">MISSION GUIDE</span>
          <span className="panel-sub">우주인 안내자</span>
        </div>
        <div className="panel-count">CADET · LV.01</div>
      </div>
      <div className="mascot-stage">
        <div className="mascot-stars">
          {Array.from({length: 9}).map((_, i) => (
            <div key={i} className="mascot-star" style={{
              left: `${(i * 37) % 90 + 5}%`,
              top: `${(i * 53) % 75 + 5}%`,
              animationDelay: `${i * 0.3}s`,
            }} />
          ))}
        </div>
        <div className="mascot-bubble">
          <div className="mascot-bubble-text" key={msgIdx}>{messages[msgIdx]}</div>
          <div className="mascot-bubble-tail" />
        </div>
        <div className="mascot-floater">
          <img src={(window.__resources && window.__resources.astronaut) || "uploads/astronaut-clean.png"} alt="astronaut" className="mascot-img" />
        </div>
        <div className="mascot-shadow" />
      </div>
      <div className="mascot-foot">
        <div className="mascot-foot-row">
          <span className="mascot-k">TIP</span>
          <span className="mascot-v">은하 → 섹터 → 기업 순으로 탐색해 보세요.</span>
        </div>
      </div>
    </div>
  );
}

// ─── PHASE 3: Sector overview panel (top-left) ─────────────────────────────
function SectorOverviewPanel({ sector, companyCount, onBack }) {
  if (!sector) return null;
  return (
    <div className="panel panel-tl sector-overview-panel" style={{'--accent': sector.color}}>
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: sector.color, boxShadow:`0 0 8px ${sector.color}`}} />
          <span className="panel-title">SECTOR OVERVIEW</span>
          <span className="panel-sub">섹터 개요</span>
        </div>
        <button className="back-link" onClick={onBack}>← GALAXY</button>
      </div>
      <div className="panel-body sector-ov-body">
        <div className="sector-ov-hero">
          <div className="sector-ov-orb" style={{background: sector.color, boxShadow:`0 0 32px ${sector.color}`}} />
          <div>
            <div className="sector-ov-en">{sector.en.toUpperCase()}</div>
            <div className="sector-ov-ko">{sector.ko}</div>
          </div>
        </div>
        <div className="sector-ov-stats">
          <div className="ov-stat"><div className="ov-k">시가총액</div><div className="ov-v">{sector.cap}T</div></div>
          <div className="ov-stat"><div className="ov-k">기업 수</div><div className="ov-v">{companyCount}</div></div>
          <div className="ov-stat"><div className="ov-k">YTD</div><div className="ov-v" style={{color:'#4ade80'}}>+12.4%</div></div>
          <div className="ov-stat"><div className="ov-k">P / E</div><div className="ov-v">14.3</div></div>
        </div>
        <div className="sector-ov-section">
          <div className="ov-sec-title">DAILY HIGHLIGHTS · 오늘의 시그널</div>
          <ul className="ov-sec-list">
            <li><span className="ov-bullet" style={{background: sector.color}} /> HBM3E 장기공급 계약 7.2조 — SK하이닉스</li>
            <li><span className="ov-bullet" style={{background: sector.color}} /> 레인보우로보틱스 인수 5,000억 — 삼성전자</li>
            <li><span className="ov-bullet" style={{background: sector.color}} /> 외국인 순매수 +3,200억 (5일 연속)</li>
          </ul>
        </div>
        <div className="sector-ov-section">
          <div className="ov-sec-title">SECTOR PULSE · 섹터 지수</div>
          <div className="ov-bars">
            {[0.3, 0.5, 0.4, 0.7, 0.6, 0.8, 0.9, 0.75, 0.85, 0.95].map((v, i) => (
              <div key={i} className="ov-bar" style={{height: `${v*100}%`, background: sector.color}} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── PHASE 4: Company overview panel (top-left) ────────────────────────────
function CompanyOverviewPanel({ company, sector, onBack, onEnter }) {
  if (!company) return null;
  const rels = (window.RELATIONS[company.code] || []);
  return (
    <div className="panel panel-tl company-overview-panel" style={{'--accent': sector.color}}>
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: sector.color, boxShadow:`0 0 8px ${sector.color}`}} />
          <span className="panel-title">COMPANY DOSSIER</span>
          <span className="panel-sub">기업 개요</span>
        </div>
        <button className="back-link" onClick={onBack}>← SECTOR</button>
      </div>
      <div className="panel-body company-ov-body">
        <div className="company-ov-hero">
          <div className="company-ov-orb" style={{background: sector.color, boxShadow:`0 0 28px ${sector.color}`}} />
          <div className="company-ov-id">
            <div className="company-ov-name">{company.name}</div>
            <div className="company-ov-en">{company.en}</div>
            <div className="company-ov-code">KOSPI · {company.code} · {sector.ko}</div>
          </div>
        </div>
        <div className="company-ov-stats">
          <div className="ov-stat"><div className="ov-k">시가총액</div><div className="ov-v">{company.cap}T</div></div>
          <div className="ov-stat"><div className="ov-k">PER</div><div className="ov-v">12.4</div></div>
          <div className="ov-stat"><div className="ov-k">PBR</div><div className="ov-v">1.3</div></div>
          <div className="ov-stat"><div className="ov-k">ROE</div><div className="ov-v" style={{color:'#4ade80'}}>14.2%</div></div>
        </div>
        <div className="company-ov-row">
          <div className="ov-k">현재가</div>
          <div className="ov-v" style={{fontSize:18}}>74,200</div>
          <div style={{color:'#4ade80', fontFamily:'var(--font-mono)', fontSize:11}}>+1.6% / +1,180</div>
        </div>
        <div className="sector-ov-section">
          <div className="ov-sec-title">RECENT DISCLOSURES · 최근 공시</div>
          <ul className="ov-sec-list">
            <li><span className="ov-time">14:32</span> 타법인 주식 취득 — 5,000억</li>
            <li><span className="ov-time">11:08</span> 자기주식 처분 결정</li>
            <li><span className="ov-time">09:15</span> 분기보고서 (1Q26)</li>
          </ul>
        </div>
        <div className="sector-ov-section">
          <div className="ov-sec-title">RELATED ENTITIES · 관계 기업 ({rels.length})</div>
          <div className="ov-rels">
            {rels.map(r => {
              const t = window.REL_STYLES[r.type];
              return (
                <div key={r.code} className="ov-rel">
                  <span className="ov-rel-mark" style={{
                    background: t.dash.length === 0 ? t.color : 'transparent',
                    border: t.dash.length === 0 ? 'none' : `1.5px ${t.dash[0] > 3 ? 'dashed' : 'dotted'} ${t.color}`,
                  }} />
                  <span className="ov-rel-code">{r.code}</span>
                  <span className="ov-rel-type" style={{color: t.color}}>{t.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="company-ov-cta-wrap">
        <button className="enter-corp-cta" onClick={onEnter}>
          <span>ENTER CORPORATION</span>
          <span className="enter-corp-arrow">↗</span>
        </button>
        <div className="enter-corp-hint">새 창에서 재무정보 열림</div>
      </div>
    </div>
  );
}

// ─── AI assistant ─────────────────────────────────────────────────────────
function AssistantPanel({ phase }) {
  const [msgs, setMsgs] = useState(AI_GREETINGS[phase] || AI_GREETINGS.galaxy);
  const [input, setInput] = useState('');
  useEffect(() => {
    setMsgs(AI_GREETINGS[phase] || AI_GREETINGS.galaxy);
  }, [phase]);
  const send = () => {
    if (!input.trim()) return;
    const q = input.trim();
    setMsgs(m => [...m, { who:'user', text:q }]);
    setInput('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'ai', text: '분석 중입니다 — 12개월 통계 기반 인사이트를 곧 전달드릴게요.' }]);
    }, 700);
  };
  return (
    <div className="panel panel-tr">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-amber" />
          <span className="panel-title">AI FINANCIAL CO-PILOT</span>
          <span className="panel-sub">Gemini · 한·영</span>
        </div>
        <div className="panel-count">v2.4</div>
      </div>
      <div className="panel-body assist-body">
        {msgs.map((m, i) => (
          <div key={i} className={"chat-msg " + (m.who === 'ai' ? 'is-ai' : 'is-user')}>
            {m.who === 'ai' && <div className="chat-avatar">AI</div>}
            <div className="chat-bubble">{m.text}</div>
          </div>
        ))}
      </div>
      <div className="assist-input">
        <input
          placeholder="Ask about a sector, disclosure, or company…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') send(); }}
        />
        <button onClick={send}>↗</button>
      </div>
    </div>
  );
}

// ─── Edge legend (bottom-left) — clearer differentiation ─────────────────
function LegendPanel() {
  return (
    <div className="panel panel-bl legend-panel">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-violet" />
          <span className="panel-title">EDGE TYPOLOGY</span>
          <span className="panel-sub">관계 유형</span>
        </div>
        <div className="panel-count">312 LINKS</div>
      </div>
      <div className="panel-body legend-body">
        <div className="legend-section">
          <div className="legend-section-h">
            <span style={{color:'#5eead4'}}>━━━</span> SOLID · 지분율 분류 (K-IFRS)
          </div>
          <div className="legend-grid">
            <LegendRow color="#5eead4" kind="solid"   label="종속기업"    sub=">50%" />
            <LegendRow color="#a78bfa" kind="solid"   label="관계기업"    sub="20–50%" />
            <LegendRow color="#fbbf24" kind="solid"   label="유의적 투자" sub="5–20%" />
          </div>
        </div>
        <div className="legend-section">
          <div className="legend-section-h">
            <span style={{color:'#94a3b8',letterSpacing:'.04em'}}>┄ ┄ ┄</span> DASHED · 비-지분 / 공시 기반
          </div>
          <div className="legend-grid">
            <LegendRow color="#94a3b8" kind="dash"   label="계열사"    sub="공정위 지정 그룹" />
            <LegendRow color="#f472b6" kind="dot"    label="특수관계자" sub="사업보고서 주석" />
            <LegendRow color="#64748b" kind="ddash"  label="수동 보정"  sub="manual override" />
          </div>
        </div>
      </div>
    </div>
  );
}

function LegendRow({ color, kind, label, sub }) {
  // kind: solid / dash / dot / ddash
  const dashAttr =
    kind === 'solid'  ? '0' :
    kind === 'dash'   ? '6 4' :
    kind === 'dot'    ? '2 3' :
    '1 2 6 2'; // ddash
  return (
    <div className="legend-row">
      <svg width="44" height="14" viewBox="0 0 44 14" className="legend-svg">
        <line x1="2" y1="7" x2="42" y2="7"
              stroke={color}
              strokeWidth={kind === 'solid' ? 2 : 1.6}
              strokeDasharray={dashAttr}
              strokeLinecap="round" />
        <circle cx="2" cy="7" r="2.4" fill={color} />
        <circle cx="42" cy="7" r="2.4" fill={color} />
      </svg>
      <div className="legend-text">
        <div className="legend-label" style={{color}}>{label}</div>
        <div className="legend-sub">{sub}</div>
      </div>
    </div>
  );
}

// ─── Sector picker (bottom-right) ──────────────────────────────────────────
function SectorPanel({ activeId, onSelect, mode = 'grid' }) {
  // mode: grid (galaxy phase) | list (sector phase)
  return (
    <div className="panel panel-br">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-cyan" />
          <span className="panel-title">{mode === 'list' ? 'SECTOR LIST' : 'SECTOR INDEX'}</span>
          <span className="panel-sub">{mode === 'list' ? '섹터 list' : '섹터 구분 · 16'}</span>
        </div>
        <div className="panel-count">{activeId ? `· ${SECTOR_PALETTE.find(s=>s.id===activeId)?.ko ?? ''}` : 'ALL'}</div>
      </div>
      <div className="panel-body sector-body">
        <div className={"sector-grid " + (mode === 'list' ? 'is-list' : '')}>
          {SECTOR_PALETTE.map(s => (
            <div
              key={s.id}
              className={"sector-chip " + (activeId === s.id ? 'is-active' : '')}
              onClick={() => onSelect(s.id)}
              style={{ '--c': s.color }}
            >
              <span className="sector-dot" />
              <span className="sector-en">{s.en}</span>
              <span className="sector-ko">{s.ko}</span>
              <span className="sector-cap">{s.cap}T</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── ENTER SECTOR card (galaxy phase, when sector picked) ─────────────────
function SelectedSectorCard({ id, onClose, onEnter }) {
  if (!id) return null;
  const sec = SECTOR_PALETTE.find(s => s.id === id);
  if (!sec) return null;
  return (
    <div className="selected-card" style={{ borderColor: sec.color + '88' }}>
      <div className="selected-row">
        <div className="selected-orb" style={{ background: sec.color, boxShadow: `0 0 24px ${sec.color}` }} />
        <div className="selected-title">
          <div className="selected-en">{sec.en.toUpperCase()}</div>
          <div className="selected-ko">{sec.ko} · 시가총액 {sec.cap}T</div>
        </div>
        <div className="selected-stats">
          <div className="ss"><div className="ss-k">5Y CAGR</div><div className="ss-v">+8.2%</div></div>
          <div className="ss"><div className="ss-k">P/E</div><div className="ss-v">14.3</div></div>
          <div className="ss"><div className="ss-k">YTD</div><div className="ss-v" style={{color:'#4ade80'}}>+12.4%</div></div>
        </div>
        <button className="selected-cta" style={{ color: sec.color, borderColor: sec.color }} onClick={onEnter}>ENTER SECTOR ↗</button>
        <button className="selected-x" onClick={onClose}>✕</button>
      </div>
    </div>
  );
}

// ─── Sector zoom-in transition wrapper ────────────────────────────────────
function SectorZoomFrame({ progress, sector, children }) {
  // progress 0→1: galaxy fades + sector emerges
  if (!sector) return children;
  const galaxyOpacity = Math.max(0, 1 - progress * 1.6);
  const sectorOpacity = Math.max(0, (progress - 0.4) * 1.8);
  return (
    <>
      <div style={{position:'absolute', inset:0, opacity: galaxyOpacity, transition:'opacity 200ms', pointerEvents:'none', zIndex:2}}>
        {children}
      </div>
      <div style={{position:'absolute', inset:0, opacity: sectorOpacity, zIndex:3}}>
        {/* sector map mounts here */}
      </div>
    </>
  );
}

// ─── Main app ──────────────────────────────────────────────────────────────
function App() {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [introPhase, setIntroPhase] = useState('intro'); // intro | transitioning | tab
  const [stage, setStage] = useState(0);
  const [activeTab, setActiveTab] = useState('finance');

  // Phase within finance tab: galaxy | sector | company
  const [phase, setPhase] = useState('galaxy');
  const [activeSectorId, setActiveSectorId] = useState(null);
  const [activeCompanyCode, setActiveCompanyCode] = useState(null);

  // sector zoom-in transition
  const [zoomProgress, setZoomProgress] = useState(0);
  const zoomAnimRef = useRef(0);

  const startIntroTransition = useCallback(() => {
    if (introPhase !== 'intro') return;
    setIntroPhase('transitioning');
    const t0 = performance.now();
    const dur = 2400;
    const tick = () => {
      const k = Math.min(1, (performance.now() - t0) / dur);
      const eased = k < 0.5 ? 4*k*k*k : 1 - Math.pow(-2*k+2, 3) / 2;
      setStage(eased);
      if (k < 1) requestAnimationFrame(tick);
      else setIntroPhase('tab');
    };
    requestAnimationFrame(tick);
  }, [introPhase]);

  // ENTER SECTOR — animate galaxy → sector
  const enterSector = useCallback((sectorId) => {
    cancelAnimationFrame(zoomAnimRef.current);
    setActiveSectorId(sectorId);
    setPhase('sector');
    const t0 = performance.now();
    const dur = 1100;
    setZoomProgress(0);
    const tick = () => {
      const k = Math.min(1, (performance.now() - t0) / dur);
      const eased = k < 0.5 ? 4*k*k*k : 1 - Math.pow(-2*k+2, 3) / 2;
      setZoomProgress(eased);
      if (k < 1) zoomAnimRef.current = requestAnimationFrame(tick);
    };
    zoomAnimRef.current = requestAnimationFrame(tick);
  }, []);

  const backToGalaxy = useCallback(() => {
    cancelAnimationFrame(zoomAnimRef.current);
    setActiveCompanyCode(null);
    setPhase('galaxy');
    setActiveSectorId(null);
    setZoomProgress(0);
  }, []);

  const backToSector = useCallback(() => {
    setActiveCompanyCode(null);
    setPhase('sector');
  }, []);

  const selectCompany = useCallback((code) => {
    setActiveCompanyCode(code);
    setPhase('company');
  }, []);

  const enterCorporation = useCallback(() => {
    if (!activeCompanyCode) return;
    const url = `financial.html?code=${activeCompanyCode}`;
    window.open(url, '_blank', 'noopener');
  }, [activeCompanyCode]);

  const sector = activeSectorId ? SECTOR_PALETTE.find(s => s.id === activeSectorId) : null;
  const companies = activeSectorId ? (window.COMPANIES[activeSectorId] || window.COMPANIES.semi) : [];
  const company = activeCompanyCode ? companies.find(c => c.code === activeCompanyCode) : null;

  // breadcrumb
  const crumb = [];
  if (phase === 'galaxy') crumb.push({ label: 'GALAXY' });
  if (phase === 'sector' || phase === 'company') {
    crumb.push({ label: 'GALAXY', onClick: backToGalaxy });
    if (sector) crumb.push({ label: sector.ko, onClick: phase === 'company' ? backToSector : null });
  }
  if (phase === 'company' && company) crumb.push({ label: company.name });

  return (
    <div className={"app phase-" + introPhase + " tone-" + tweaks.panelTone}>
      {/* Galaxy backdrop — visible in intro and galaxy phase, fades during sector zoom */}
      <div className="galaxy-bg" style={{
        opacity: introPhase === 'tab' && phase !== 'galaxy' ? 0 : 1,
        transition: 'opacity 800ms ease-out',
      }}>
        <GalaxyCanvas stage={stage} />
      </div>

      {introPhase !== 'tab' && <IntroScreen stage={stage} onEnter={startIntroTransition} />}

      {introPhase === 'tab' && activeTab === 'finance' && (
        <div className="finance-tab">
          {/* Galaxy phase — full solar system with all sectors */}
          {phase === 'galaxy' && (
            <SolarSystem
              activeSectorId={activeSectorId}
              onSelectSector={setActiveSectorId}
              sectorVisual={tweaks.sectorVisual}
              orbitMotion={tweaks.orbitMotion === 'static' ? 'static' : tweaks.orbitMotion === 'realistic' ? 'realistic' : 'concentric'}
            />
          )}

          {/* Sector / company phase — sector map */}
          {(phase === 'sector' || phase === 'company') && sector && (
            <div className="sector-map-stage" style={{
              opacity: Math.max(0, (zoomProgress - 0.3) * 1.6),
              transform: `scale(${0.7 + zoomProgress * 0.3})`,
            }}>
              <SectorMap
                sectorId={activeSectorId}
                activeCompanyCode={activeCompanyCode}
                onSelectCompany={selectCompany}
              />
            </div>
          )}

          <TopTabs active={activeTab} onChange={setActiveTab} breadcrumb={crumb} />

          {/* Top-left panel — varies by phase */}
          {phase === 'galaxy' && <MascotPanel messages={["섹터를 클릭하면, 기업을 확인할 수 있어요!", "오른쪽 아래 섹터 INDEX에서도 선택할 수 있어요.", "AI 코파일럿에게 무엇이든 물어보세요."]} />}
          {phase === 'sector' && <SectorOverviewPanel sector={sector} companyCount={companies.length} onBack={backToGalaxy} />}
          {phase === 'company' && <CompanyOverviewPanel company={company} sector={sector} onBack={backToSector} onEnter={enterCorporation} />}

          {/* Top-right — AI co-pilot, content varies */}
          <AssistantPanel phase={phase} />

          {/* Bottom-left — legend (always) */}
          <LegendPanel />

          {/* Bottom-right — sector index (galaxy) / sector list (sector/company) */}
          <SectorPanel
            activeId={activeSectorId}
            mode={phase === 'galaxy' ? 'grid' : 'list'}
            onSelect={(id) => {
              if (phase === 'galaxy') {
                setActiveSectorId(activeSectorId === id ? null : id);
              } else {
                // switch sectors directly
                setActiveCompanyCode(null);
                if (id !== activeSectorId) {
                  enterSector(id);
                }
              }
            }}
          />

          {/* Galaxy phase — show ENTER SECTOR card when picked */}
          {phase === 'galaxy' && (
            <SelectedSectorCard
              id={activeSectorId}
              onClose={() => setActiveSectorId(null)}
              onEnter={() => enterSector(activeSectorId)}
            />
          )}
        </div>
      )}

      {introPhase === 'tab' && activeTab !== 'finance' && (
        <div className="finance-tab">
          <TopTabs active={activeTab} onChange={setActiveTab} />
          <div className="placeholder-tab">
            <div>
              <div className="ph-eyebrow">— UNDER CONSTRUCTION —</div>
              <div className="ph-title">{activeTab === 'disclose' ? 'DISCLOSURE NETWORK' : 'TIME MACHINE'}</div>
              <div className="ph-sub">이 탭은 추후 구현 예정. 본 데모는 인트로 + 재무정보 탭에 집중.</div>
              <button className="ph-back" onClick={() => setActiveTab('finance')}>← BACK TO FINANCIALS</button>
            </div>
          </div>
        </div>
      )}

      <TweaksPanel>
        <TweakSection label="Galaxy" />
        <TweakRadio label="Style" value={tweaks.galaxyStyle}
          options={['cinematic','editorial','observatory']}
          onChange={(v) => setTweak('galaxyStyle', v)} />
        <TweakRadio label="Transition" value={tweaks.transitionStyle}
          options={['zoom','fade','warp']}
          onChange={(v) => setTweak('transitionStyle', v)} />
        <TweakSection label="Solar system" />
        <TweakRadio label="Sector visual" value={tweaks.sectorVisual}
          options={['color','mono','both']}
          onChange={(v) => setTweak('sectorVisual', v)} />
        <TweakRadio label="Orbit motion" value={tweaks.orbitMotion}
          options={['concentric','realistic','static']}
          onChange={(v) => setTweak('orbitMotion', v)} />
        <TweakSection label="Panels" />
        <TweakRadio label="Tone" value={tweaks.panelTone}
          options={['glass','hud','minimal']}
          onChange={(v) => setTweak('panelTone', v)} />
        <TweakButton label="↺ Replay intro" onClick={() => {
          setIntroPhase('intro'); setStage(0); setActiveSectorId(null); setActiveCompanyCode(null); setPhase('galaxy');
        }} />
        <TweakButton label="◀ Back to galaxy" onClick={backToGalaxy} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
