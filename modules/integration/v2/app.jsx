/* DiscloseAI v2 — App entry
 *
 * 단계: J1 IntroScreen 완료 → J2: TopTabs + Galaxy canvas + 3-탭 (FINANCIALS·DISCLOSURES·TIME MACHINE)
 * dashboard.html과 무관 — modules/integration/v2/ 단방향.
 *
 * 클래스 네이밍은 styles.css 인벤토리(.app/.phase-intro/.galaxy-canvas/.top-tabs/...)를 그대로 따름.
 */

const { useState, useEffect, useCallback, useRef, useMemo } = React;

// ====================================================================== //
// MOCK 데이터 (J3에서 graph_top50.json + eqs_summary.json + disclosures.json fetch로 교체 예정)
// 12 섹터는 top50.csv distinct 결과 기준.
// ====================================================================== //
const MOCK_SECTORS = [
  { id: "semiconductor", en: "SEMICONDUCTOR", ko: "반도체", color: "#5eead4", cap: "980T" },
  { id: "financials",    en: "FINANCIALS",    ko: "금융",     color: "#fbbf24", cap: "720T" },
  { id: "platform",      en: "PLATFORM",      ko: "IT/플랫폼", color: "#4ade80", cap: "660T" },
  { id: "automotive",    en: "AUTOMOTIVE",    ko: "자동차",   color: "#a78bfa", cap: "540T" },
  { id: "biotech",       en: "BIOTECH",       ko: "바이오",   color: "#f87171", cap: "410T" },
  { id: "energy",        en: "ENERGY",        ko: "에너지",   color: "#f97316", cap: "380T" },
  { id: "chemicals",     en: "CHEMICALS",     ko: "화학",     color: "#f472b6", cap: "320T" },
  { id: "telecom",       en: "TELECOM",       ko: "통신",     color: "#c084fc", cap: "290T" },
  { id: "shipbuilding",  en: "SHIPBUILDING",  ko: "조선",     color: "#60a5fa", cap: "280T" },
  { id: "retail",        en: "RETAIL",        ko: "유통/소비재", color: "#fb7185", cap: "260T" },
  { id: "construction",  en: "CONSTRUCTION",  ko: "건설",     color: "#a3e635", cap: "210T" },
  { id: "media",         en: "MEDIA",         ko: "미디어",   color: "#fde047", cap: "180T" },
];

// ====================================================================== //
// 공통: HUD top + bottom (인트로 전용 — phase-tab에선 TopTabs로 대체)
// ====================================================================== //
function HudTop({ session, uplinkMs, utc }) {
  return (
    <header className="hud-top">
      <div className="hud-brand">
        <div className="hud-logo">◉</div>
        <div className="hud-brand-text">
          <div className="hud-brand-name">DISCLOSEAI</div>
          <div className="hud-brand-sub">CORPORATE GALAXY ATLAS · v2.4</div>
        </div>
      </div>
      <div className="hud-meta">
        <div className="hud-meta-row">
          <span className="hud-meta-k">SESSION</span>
          <span className="hud-meta-v">{session}</span>
        </div>
        <div className="hud-meta-row">
          <span className="hud-meta-k">UPLINK</span>
          <span className="hud-meta-v"><span className="hud-dot" /> STABLE · {uplinkMs}ms</span>
        </div>
        <div className="hud-meta-row">
          <span className="hud-meta-k">UTC</span>
          <span className="hud-meta-v">{utc}</span>
        </div>
      </div>
    </header>
  );
}

function HudRails({ tElapsed, sectorCount = 12, planetCount = 50 }) {
  return (
    <>
      <div className="hud-rail hud-rail-left">
        <div className="rail-tick">SECTORS · {sectorCount}</div>
        <div className="rail-tick">PLANETS · {planetCount}</div>
        <div className="rail-tick">EDGES · 312</div>
        <div className="rail-tick">LIVE PULSES · 8</div>
      </div>
      <div className="hud-rail hud-rail-right">
        <div className="rail-tick">RA 04h 32m</div>
        <div className="rail-tick">DEC +21° 18′</div>
        <div className="rail-tick">Z 0.000142</div>
        <div className="rail-tick">T+{String(tElapsed).padStart(4, "0")}s</div>
      </div>
    </>
  );
}

function HudBottom({ sectorCount = 12, planetCount = 50, newDiscTonight = 47 }) {
  return (
    <footer className="hud-bottom">
      <div className="hud-bottom-l">
        <span className="hud-dot" />
        OBSERVATORY ONLINE
        <span className="hud-sep">/</span>
        {sectorCount} SECTORS · {planetCount} PLANETS
        <span className="hud-sep">/</span>
        NEW DISCLOSURES TONIGHT · {newDiscTonight}
      </div>
      <div className="hud-bottom-r">2026 AI ROOKIE · MSIT</div>
    </footer>
  );
}

// ====================================================================== //
// GalaxyCanvas — 인트로·phase-tab 공통 배경 (Canvas2D 별 + radial 갤럭시 디스크)
// ====================================================================== //
function GalaxyCanvas({ density = 220 }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf = 0;
    let stars = [];
    let dust = [];
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      const W = canvas.width, H = canvas.height;
      stars = Array.from({ length: density }, () => {
        const r = Math.random();
        return {
          x: Math.random() * W,
          y: Math.random() * H,
          r: r * r * 1.6 + 0.2,
          alpha: 0.3 + Math.random() * 0.6,
          tw: Math.random() * Math.PI * 2,
          spd: 0.4 + Math.random() * 1.2,
        };
      });
      dust = Array.from({ length: 60 }, () => {
        const ang = Math.random() * Math.PI * 2;
        const dist = (0.05 + Math.random() * 0.42) * Math.min(W, H);
        return { ang, dist, alpha: 0.05 + Math.random() * 0.18, spd: 0.0006 + Math.random() * 0.0014 };
      });
    }
    resize();
    const onResize = () => resize();
    window.addEventListener("resize", onResize);

    let t = 0;
    function loop() {
      t += 0.012;
      const W = canvas.width, H = canvas.height;
      ctx.fillStyle = "#02030a";
      ctx.fillRect(0, 0, W, H);

      // 갤럭시 디스크 — radial gradient (회전감은 dust 점들로)
      const cx = W / 2, cy = H / 2;
      const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(W, H) * 0.45);
      grd.addColorStop(0.0, "rgba(94, 234, 212, 0.10)");
      grd.addColorStop(0.30, "rgba(167, 139, 250, 0.05)");
      grd.addColorStop(0.55, "rgba(94, 234, 212, 0.018)");
      grd.addColorStop(1.0, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = grd;
      ctx.fillRect(0, 0, W, H);

      // dust (갤럭시 spiral 점)
      for (const d of dust) {
        d.ang += d.spd;
        const x = cx + Math.cos(d.ang) * d.dist + Math.sin(d.ang * 2.1) * d.dist * 0.18;
        const y = cy + Math.sin(d.ang) * d.dist * 0.55 + Math.cos(d.ang * 1.7) * d.dist * 0.12;
        ctx.beginPath();
        ctx.arc(x, y, 1.1 * dpr, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220, 230, 255, ${d.alpha})`;
        ctx.fill();
      }

      // stars (twinkle)
      for (const s of stars) {
        const opa = Math.max(0, s.alpha * (0.55 + 0.45 * Math.sin(t * s.spd + s.tw)));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * dpr, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${opa})`;
        ctx.fill();
      }

      raf = requestAnimationFrame(loop);
    }
    loop();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [density]);

  return <canvas className="galaxy-canvas" ref={ref} />;
}

// ====================================================================== //
// SolarCanvas — phase-tab의 12 섹터 회전 시스템 (mock, J3에서 실데이터 wired)
// ====================================================================== //
function SolarCanvas({ sectors, activeSectorId, onPickSector }) {
  const ref = useRef(null);
  // 클릭 hit-test를 위한 마지막 좌표 캐시
  const planetsRef = useRef([]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;

    function resize() {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
    }
    resize();
    const onResize = () => resize();
    window.addEventListener("resize", onResize);

    let t = 0;
    function loop() {
      t += 0.0042;
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      const cx = W / 2, cy = H / 2;
      const baseR = Math.min(W, H) * 0.30;

      // 중심 별 (Sun)
      const sunGrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, 60 * dpr);
      sunGrd.addColorStop(0, "rgba(255, 230, 180, 0.95)");
      sunGrd.addColorStop(0.4, "rgba(255, 200, 120, 0.45)");
      sunGrd.addColorStop(1, "rgba(255, 180, 90, 0)");
      ctx.fillStyle = sunGrd;
      ctx.beginPath();
      ctx.arc(cx, cy, 80 * dpr, 0, Math.PI * 2);
      ctx.fill();

      // 12 행성 — 두 링으로 분배
      planetsRef.current = [];
      sectors.forEach((s, i) => {
        const ring = i < 7 ? 0 : 1;
        const inRing = ring === 0 ? sectors.slice(0, 7).length : sectors.slice(7).length;
        const idxInRing = ring === 0 ? i : i - 7;
        const ringR = baseR + ring * baseR * 0.55;
        const ang = (idxInRing / inRing) * Math.PI * 2 + t * (ring ? -0.6 : 1);
        const x = cx + Math.cos(ang) * ringR;
        const y = cy + Math.sin(ang) * ringR * 0.78;
        const isActive = s.id === activeSectorId;
        const radius = (isActive ? 18 : 12) * dpr;

        // 궤도 점선
        ctx.strokeStyle = isActive ? "rgba(94,234,212,0.20)" : "rgba(148,163,184,0.06)";
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 6]);
        ctx.beginPath();
        ctx.ellipse(cx, cy, ringR, ringR * 0.78, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // 행성 glow
        const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 3);
        glow.addColorStop(0, hexA(s.color, 0.85));
        glow.addColorStop(0.4, hexA(s.color, 0.35));
        glow.addColorStop(1, hexA(s.color, 0));
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, radius * 3, 0, Math.PI * 2);
        ctx.fill();

        // 행성 본체
        ctx.fillStyle = s.color;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();

        if (isActive) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2 * dpr;
          ctx.beginPath();
          ctx.arc(x, y, radius + 6 * dpr, 0, Math.PI * 2);
          ctx.stroke();
        }

        planetsRef.current.push({ id: s.id, x, y, radius: radius + 6 * dpr });
      });

      raf = requestAnimationFrame(loop);
    }
    loop();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [sectors, activeSectorId]);

  // hit-test: canvas 좌표계로 변환
  const handleClick = useCallback(
    (e) => {
      const canvas = ref.current;
      if (!canvas) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) * dpr;
      const y = (e.clientY - rect.top) * dpr;
      let best = null;
      let bestD = Infinity;
      for (const p of planetsRef.current) {
        const d = Math.hypot(p.x - x, p.y - y);
        if (d < p.radius + 6 && d < bestD) {
          bestD = d;
          best = p;
        }
      }
      if (best && onPickSector) onPickSector(best.id);
    },
    [onPickSector]
  );

  return <canvas className="solar-canvas" ref={ref} onClick={handleClick} />;
}

function hexA(hex, a) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

// ====================================================================== //
// TopTabs (FINANCIALS · DISCLOSURES · TIME MACHINE) + breadcrumb + KOSPI live
// ====================================================================== //
const TABS = [
  { id: "financials",  en: "FINANCIALS",  ko: "재무정보" },
  { id: "disclosures", en: "DISCLOSURES", ko: "공시" },
  { id: "timemachine", en: "TIME MACHINE", ko: "타임머신" },
];

function TopTabs({ activeTab, onTabChange, breadcrumb, kospi }) {
  return (
    <div className="top-tabs">
      <div className="top-tabs-brand">
        <div className="top-brand-mark">◉</div>
        <div className="top-brand-name">DISCLOSEAI</div>
        {breadcrumb && breadcrumb.length > 0 && (
          <div className="top-breadcrumb">
            {breadcrumb.map((b, i) => (
              <React.Fragment key={i}>
                <span
                  className={"crumb" + (b.onClick ? " is-clickable" : "")}
                  onClick={b.onClick}
                  role={b.onClick ? "button" : undefined}
                >
                  {b.label}
                </span>
                {i < breadcrumb.length - 1 && <span className="crumb-sep">›</span>}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
      <div className="top-tabs-row" role="tablist">
        {TABS.map((t) => (
          <div
            key={t.id}
            className={"top-tab" + (activeTab === t.id ? " is-active" : "")}
            onClick={() => onTabChange(t.id)}
            role="tab"
            aria-selected={activeTab === t.id}
            tabIndex={0}
          >
            <div className="top-tab-en">{t.en}</div>
            <div className="top-tab-ko">{t.ko}</div>
          </div>
        ))}
      </div>
      <div className="top-tabs-status">
        <span className="hud-dot" />
        <span style={{ fontSize: 10, color: "var(--text-3)", letterSpacing: "0.16em" }}>
          KOSPI
        </span>
        <span style={{ fontWeight: 600, color: "#fff", fontSize: 13 }}>
          {kospi.value.toFixed(2)}
        </span>
        <span style={{ color: kospi.delta >= 0 ? "#4ade80" : "#f87171", fontSize: 11 }}>
          {(kospi.delta >= 0 ? "+" : "") + kospi.delta.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

// ====================================================================== //
// Placeholder (UNDER CONSTRUCTION) — DISCLOSURES / TIME MACHINE
// ====================================================================== //
function PlaceholderTab({ title, onBack }) {
  return (
    <div className="placeholder-tab">
      <div>
        <div className="ph-eyebrow">— UNDER CONSTRUCTION —</div>
        <h2 className="ph-title">{title}</h2>
        <div className="ph-sub">
          이 탭은 추후 구현 예정. 본 데모는 인트로 + 재무정보 탭에 집중.
        </div>
        <button className="ph-back" onClick={onBack} type="button">
          ← BACK TO FINANCIALS
        </button>
      </div>
    </div>
  );
}

// ====================================================================== //
// FinanceTab (J2: SolarCanvas + 12 mock 섹터. J3에서 panels + real data 추가 예정)
// ====================================================================== //
function FinanceTab({ activeSectorId, onPickSector }) {
  return (
    <div className="finance-tab">
      <div className="solar-stage">
        <SolarCanvas
          sectors={MOCK_SECTORS}
          activeSectorId={activeSectorId}
          onPickSector={onPickSector}
        />
        <div className="solar-labels" />
      </div>
    </div>
  );
}

// ====================================================================== //
// IntroScreen — 시적 헤로 + ENTER CTA
// ====================================================================== //
function IntroScreen({ onEnter, session, uplinkMs, utc, tElapsed }) {
  return (
    <div className="app phase-intro tone-glass">
      <div className="galaxy-bg">
        <GalaxyCanvas density={260} />
      </div>

      <div className="intro-overlay">
        <HudTop session={session} uplinkMs={uplinkMs} utc={utc} />

        <main className="intro-center">
          <div className="intro-eyebrow">— TRANSMISSION FROM THE MARKET —</div>
          <h1 className="intro-headline">
            <div className="intro-line-1">What twelve headlines</div>
            <div className="intro-line-2">missed,</div>
            <div className="intro-line-3">a single number</div>
            <div className="intro-line-4">
              was already <em>whispering.</em>
            </div>
          </h1>
          <div className="intro-sub">
            KOSPI · 1,400 disclosures / day · decoded by AI
            <br />
            A spatial atlas of Korea's listed companies.
          </div>
          <button className="enter-button" onClick={onEnter} type="button">
            <span className="enter-icon">▷</span>
            <span className="enter-label">ENTER THE GALAXY</span>
            <span className="enter-hint">click anywhere</span>
          </button>
        </main>

        <HudBottom />

        <HudRails tElapsed={tElapsed} />

        <button
          className="intro-click"
          aria-label="Enter the galaxy"
          onClick={onEnter}
          type="button"
        />
      </div>
    </div>
  );
}

// ====================================================================== //
// PhaseTab — TopTabs + 활성 탭 본체. FinanceTab은 SolarCanvas, 나머지는 PlaceholderTab.
// ====================================================================== //
function PhaseTab({ activeTab, onTabChange, activeSectorId, onPickSector, kospi, breadcrumb }) {
  let body;
  if (activeTab === "financials") {
    body = (
      <FinanceTab activeSectorId={activeSectorId} onPickSector={onPickSector} />
    );
  } else if (activeTab === "disclosures") {
    body = (
      <PlaceholderTab title="DISCLOSURE NETWORK" onBack={() => onTabChange("financials")} />
    );
  } else {
    body = (
      <PlaceholderTab title="TIME MACHINE" onBack={() => onTabChange("financials")} />
    );
  }
  return (
    <div className="app phase-tab tone-glass">
      <div className="galaxy-bg">
        <GalaxyCanvas density={140} />
      </div>
      {body}
      <TopTabs
        activeTab={activeTab}
        onTabChange={onTabChange}
        breadcrumb={breadcrumb}
        kospi={kospi}
      />
    </div>
  );
}

// ====================================================================== //
// useNowUtc + useKospiMock — UI hooks
// ====================================================================== //
function useNowUtc() {
  const [s, setS] = useState(formatUtc(new Date()));
  useEffect(() => {
    const id = setInterval(() => setS(formatUtc(new Date())), 1000);
    return () => clearInterval(id);
  }, []);
  return s;
}
function formatUtc(d) {
  return (
    String(d.getUTCHours()).padStart(2, "0") + ":" +
    String(d.getUTCMinutes()).padStart(2, "0") + ":" +
    String(d.getUTCSeconds()).padStart(2, "0") + "Z"
  );
}

// KOSPI mock — 매 5초마다 약간씩 흔들림. 후속 phase에서 yfinance 또는 KRX 캐시로 교체.
function useKospiMock() {
  const [val, setVal] = useState({ value: 3142.8, delta: 0.42 });
  useEffect(() => {
    const id = setInterval(() => {
      setVal((v) => {
        const dv = (Math.random() - 0.5) * 0.6;
        const nv = +(v.value + dv).toFixed(2);
        const delta = +(((nv - 3142.8) / 3142.8) * 100).toFixed(2);
        return { value: nv, delta };
      });
    }, 5000);
    return () => clearInterval(id);
  }, []);
  return val;
}

// ====================================================================== //
// App
// ====================================================================== //
function App() {
  const [phase, setPhase] = useState("intro"); // 'intro' | 'tab'
  const [activeTab, setActiveTab] = useState("financials"); // 'financials' | 'disclosures' | 'timemachine'
  const [activeSectorId, setActiveSectorId] = useState(null);
  const [tElapsed, setTElapsed] = useState(0);

  const sessionId = useRef(`DA-${Math.floor(2000 + Math.random() * 700)}`);
  const utc = useNowUtc();
  const kospi = useKospiMock();

  // T+초 카운터 (인트로에서만)
  useEffect(() => {
    if (phase !== "intro") return;
    const id = setInterval(() => setTElapsed((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [phase]);

  const handleEnter = useCallback(() => setPhase("tab"), []);
  const handleTabChange = useCallback((next) => {
    setActiveTab(next);
    if (next !== "financials") setActiveSectorId(null);
  }, []);
  const handlePickSector = useCallback((sid) => setActiveSectorId(sid), []);

  // breadcrumb (FINANCIALS만 의미 있음)
  const breadcrumb = useMemo(() => {
    if (activeTab !== "financials") return [];
    const crumbs = [
      { label: "GALAXY", onClick: () => setActiveSectorId(null) },
    ];
    if (activeSectorId) {
      const sec = MOCK_SECTORS.find((s) => s.id === activeSectorId);
      if (sec) crumbs.push({ label: sec.ko });
    }
    return crumbs;
  }, [activeTab, activeSectorId]);

  if (phase === "intro") {
    return (
      <IntroScreen
        onEnter={handleEnter}
        session={sessionId.current}
        uplinkMs={42}
        utc={utc}
        tElapsed={tElapsed}
      />
    );
  }
  return (
    <PhaseTab
      activeTab={activeTab}
      onTabChange={handleTabChange}
      activeSectorId={activeSectorId}
      onPickSector={handlePickSector}
      kospi={kospi}
      breadcrumb={breadcrumb}
    />
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
