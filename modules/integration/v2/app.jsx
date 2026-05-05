/* DiscloseAI v2 — App entry
 *
 * 단계:
 *   J1 IntroScreen 골격 + HUD
 *   J2 TopTabs · GalaxyCanvas · SolarCanvas · UC placeholder
 *   J3 data wiring layer (loader/valuation/narration/mock) + 4 패널 추가
 *      (MascotPanel · AssistantPanel · LegendPanel · SectorPanel)
 *
 * dashboard.html과 무관 — modules/integration/v2/ 단방향.
 * window.DiscloseAI에 mock/valuation/narration/loader가 미리 로드돼 있다고 가정.
 */

const { useState, useEffect, useCallback, useRef, useMemo } = React;

// ====================================================================== //
// HUD blocks (인트로 전용)
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
// GalaxyCanvas — Canvas2D 별 + radial 갤럭시 디스크 + dust 회전
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
      const cx = W / 2, cy = H / 2;
      const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(W, H) * 0.45);
      grd.addColorStop(0.0, "rgba(94, 234, 212, 0.10)");
      grd.addColorStop(0.30, "rgba(167, 139, 250, 0.05)");
      grd.addColorStop(0.55, "rgba(94, 234, 212, 0.018)");
      grd.addColorStop(1.0, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = grd;
      ctx.fillRect(0, 0, W, H);
      for (const d of dust) {
        d.ang += d.spd;
        const x = cx + Math.cos(d.ang) * d.dist + Math.sin(d.ang * 2.1) * d.dist * 0.18;
        const y = cy + Math.sin(d.ang) * d.dist * 0.55 + Math.cos(d.ang * 1.7) * d.dist * 0.12;
        ctx.beginPath();
        ctx.arc(x, y, 1.1 * dpr, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220, 230, 255, ${d.alpha})`;
        ctx.fill();
      }
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
// SolarCanvas — 섹터 행성을 두 링으로 분배 + 회전 + 클릭 hit-test
// ====================================================================== //
function SolarCanvas({ sectors, activeSectorId, onPickSector }) {
  const ref = useRef(null);
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

      // 중심 별
      const sunGrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, 80 * dpr);
      sunGrd.addColorStop(0, "rgba(255, 230, 180, 0.95)");
      sunGrd.addColorStop(0.4, "rgba(255, 200, 120, 0.40)");
      sunGrd.addColorStop(1, "rgba(255, 180, 90, 0)");
      ctx.fillStyle = sunGrd;
      ctx.beginPath();
      ctx.arc(cx, cy, 80 * dpr, 0, Math.PI * 2);
      ctx.fill();

      planetsRef.current = [];
      const total = sectors.length || 1;
      const ringSplit = Math.ceil(total / 2);
      sectors.forEach((s, i) => {
        const ring = i < ringSplit ? 0 : 1;
        const inRing = ring === 0 ? ringSplit : total - ringSplit;
        const idxInRing = ring === 0 ? i : i - ringSplit;
        const ringR = baseR + ring * baseR * 0.55;
        const ang =
          (idxInRing / Math.max(1, inRing)) * Math.PI * 2 + t * (ring ? -0.6 : 1);
        const x = cx + Math.cos(ang) * ringR;
        const y = cy + Math.sin(ang) * ringR * 0.78;
        const isActive = s.id === activeSectorId;
        // 시총 비례 반경 (작은 차이로 작용)
        const sizeRatio = Math.max(0.6, Math.min(1.4, Math.sqrt((s.memberCount || 1) / 4)));
        const radius = (isActive ? 18 : 12) * dpr * sizeRatio;

        ctx.strokeStyle = isActive ? "rgba(94,234,212,0.22)" : "rgba(148,163,184,0.05)";
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 6]);
        ctx.beginPath();
        ctx.ellipse(cx, cy, ringR, ringR * 0.78, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 3);
        glow.addColorStop(0, hexA(s.color, 0.85));
        glow.addColorStop(0.4, hexA(s.color, 0.30));
        glow.addColorStop(1, hexA(s.color, 0));
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, radius * 3, 0, Math.PI * 2);
        ctx.fill();

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

        planetsRef.current.push({
          id: s.id, label: s.ko, en: s.en, x, y, radius: radius + 6 * dpr, color: s.color,
        });
      });

      raf = requestAnimationFrame(loop);
    }
    loop();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [sectors, activeSectorId]);

  const handleClick = useCallback((e) => {
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
  }, [onPickSector]);

  return <canvas className="solar-canvas" ref={ref} onClick={handleClick} />;
}

function hexA(hex, a) {
  const h = (hex || "#5eead4").replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

// ====================================================================== //
// TopTabs — 3 탭 + breadcrumb + KOSPI live
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
        <span style={{ fontSize: 10, color: "var(--text-3)", letterSpacing: "0.16em" }}>KOSPI</span>
        <span style={{ fontWeight: 600, color: "#fff", fontSize: 13 }}>{kospi.value.toFixed(2)}</span>
        <span style={{ color: kospi.delta >= 0 ? "#4ade80" : "#f87171", fontSize: 11 }}>
          {(kospi.delta >= 0 ? "+" : "") + kospi.delta.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

// ====================================================================== //
// MascotPanel (panel-tl) — 우주인 마스코트 + 모드별 말풍선
// ====================================================================== //
const MASCOT_MESSAGES = {
  galaxy: "섹터를 클릭하면, 기업을 확인할 수 있어요!",
  sector: "은하 → 섹터 → 기업 순으로 탐색해 보세요.",
  company: "ENTER CORPORATION으로 재무 상세를 열어보세요.",
};
function MascotPanel({ stage }) {
  const msg = MASCOT_MESSAGES[stage] || MASCOT_MESSAGES.galaxy;
  const stars = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => ({
        top: 8 + Math.random() * 70 + "%",
        left: 6 + Math.random() * 84 + "%",
        delay: (Math.random() * 2.4).toFixed(2) + "s",
      })),
    []
  );
  return (
    <div className="panel panel-tl mascot-panel">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" />
          <span className="panel-title">MISSION GUIDE</span>
          <span className="panel-sub">우주인 안내자</span>
        </div>
        <span className="panel-count">CADET · LV.01</span>
      </div>
      <div className="mascot-stage">
        <div className="mascot-stars">
          {stars.map((s, i) => (
            <span
              key={i}
              className="mascot-star"
              style={{ top: s.top, left: s.left, animationDelay: s.delay }}
            />
          ))}
        </div>
        <div className="mascot-bubble">
          <div className="mascot-bubble-text">{msg}</div>
          <div className="mascot-bubble-tail" />
        </div>
        <div className="mascot-floater">
          <img
            className="mascot-img"
            src="./assets/astronaut.png"
            alt="astronaut mascot"
            draggable="false"
          />
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

// ====================================================================== //
// AssistantPanel (panel-tr) — Mock AI Co-pilot (J3에서 mock 그대로, 후속 phase에 Gemini 연결)
// ====================================================================== //
const AI_GREETINGS_BY_STAGE = {
  galaxy: [
    "Welcome back, Captain. KOSPI is flowing — Semiconductor leads, Biotech lags.",
    "Pick any sector to dive in. I'll brief you on what's moving inside.",
  ],
  sector: [
    "We're now inside the sector. Each glowing node is a listed company.",
    "Click a company — I'll surface its disclosures and related entities.",
  ],
  company: [
    "Tracking this company. Solid lines are equity ties, dashed are group/related-party links.",
    "Press ENTER CORPORATION for the full financial dossier.",
  ],
};
function AssistantPanel({ stage }) {
  const msgs = AI_GREETINGS_BY_STAGE[stage] || AI_GREETINGS_BY_STAGE.galaxy;
  const [draft, setDraft] = useState("");
  return (
    <div className="panel panel-tr">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-amber" />
          <span className="panel-title">AI FINANCIAL CO-PILOT</span>
          <span className="panel-sub">Gemini · 한·영</span>
        </div>
        <span className="panel-count">v2.4</span>
      </div>
      <div className="panel-body">
        <div className="assist-body">
          {msgs.map((m, i) => (
            <div key={i} className="chat-msg is-ai">
              <div className="chat-avatar">AI</div>
              <div className="chat-bubble">{m}</div>
            </div>
          ))}
          <div
            style={{
              fontSize: 10,
              color: "var(--text-3)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.06em",
              padding: "6px 4px",
              borderTop: "1px dashed rgba(148,163,184,0.10)",
              marginTop: 6,
            }}
          >
            ⚠ 1차 데모: AI 응답은 미리 작성된 안내문입니다. 본 분석은 과거 통계 기반
            참고 정보이며 투자 권유가 아닙니다.
          </div>
        </div>
      </div>
      <div className="assist-input">
        <input
          type="text"
          placeholder="Ask about a sector, disclosure, or company…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled
          aria-disabled="true"
        />
        <button type="button" disabled aria-disabled="true">↗</button>
      </div>
    </div>
  );
}

// ====================================================================== //
// LegendPanel (panel-bl) — EDGE TYPOLOGY (K-IFRS + 비-지분)
// ====================================================================== //
function LegendLine({ color, style }) {
  if (style === "dashed") {
    return (
      <span
        className="legend-line"
        style={{
          display: "inline-block",
          width: 36,
          borderTop: `1px dashed ${color}`,
          opacity: 0.85,
        }}
      />
    );
  }
  return (
    <span
      className="legend-line"
      style={{
        display: "inline-block",
        width: 36,
        height: 0,
        borderTop: `2px solid ${color}`,
      }}
    />
  );
}

function LegendPanel() {
  const L = (window.DiscloseAI && window.DiscloseAI.EDGE_LEGEND) || { solid: [], dashed: [] };
  return (
    <div className="panel panel-bl legend-panel">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-violet" />
          <span className="panel-title">EDGE TYPOLOGY</span>
          <span className="panel-sub">관계 유형</span>
        </div>
        <span className="panel-count">312 LINKS</span>
      </div>
      <div className="panel-body">
        <div className="legend-body">
          <div className="legend-section">
            <div className="legend-section-h">━━━ SOLID · 지분율 분류 (K-IFRS)</div>
            <div className="legend-grid">
              {L.solid.map((row, i) => (
                <div key={i} className="legend-row">
                  <LegendLine color={row.color} style="solid" />
                  <div>
                    <div className="legend-label">{row.label}</div>
                    <div className="legend-sub">{row.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="legend-section">
            <div className="legend-section-h">┄ ┄ ┄ DASHED · 비-지분 / 공시 기반</div>
            <div className="legend-grid">
              {L.dashed.map((row, i) => (
                <div key={i} className="legend-row">
                  <LegendLine color={row.color} style="dashed" />
                  <div>
                    <div className="legend-label">{row.label}</div>
                    <div className="legend-sub">{row.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ====================================================================== //
// SectorPanel (panel-br) — 12 섹터 chip
// ====================================================================== //
function SectorPanel({ sectors, activeSectorId, onPickSector, breadcrumbCount }) {
  return (
    <div className="panel panel-br">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-cyan" />
          <span className="panel-title">SECTOR INDEX</span>
          <span className="panel-sub">섹터 구분 · {sectors.length}</span>
        </div>
        <span className="panel-count">
          {activeSectorId
            ? "· " + (sectors.find((s) => s.id === activeSectorId)?.ko || "")
            : "ALL"}
        </span>
      </div>
      <div className="panel-body sector-body">
        <div className="sector-grid">
          {sectors.map((s) => (
            <div
              key={s.id}
              className={"sector-chip" + (s.id === activeSectorId ? " is-active" : "")}
              onClick={() => onPickSector(s.id)}
              style={{ "--c": s.color }}
              role="button"
              tabIndex={0}
            >
              <span className="sector-dot" />
              <span className="sector-en">{s.en}</span>
              <span className="sector-ko">{s.ko}</span>
              <span className="sector-cap">{s.cap}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ====================================================================== //
// PlaceholderTab (DISCLOSURES / TIME MACHINE)
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
// FinanceTab — Galaxy 단계 (J3 현재). J4·J5에서 Sector·Company 단계 추가.
// ====================================================================== //
function FinanceTab({
  data,
  activeSectorId,
  onPickSector,
}) {
  const sectors = data.sectors || [];
  const stage = activeSectorId ? "sector" : "galaxy";
  return (
    <>
      <div className="finance-tab">
        <div className="solar-stage">
          <SolarCanvas
            sectors={sectors}
            activeSectorId={activeSectorId}
            onPickSector={onPickSector}
          />
          <div className="solar-labels" />
        </div>
      </div>
      <MascotPanel stage={stage} />
      <AssistantPanel stage={stage} />
      <LegendPanel />
      <SectorPanel
        sectors={sectors}
        activeSectorId={activeSectorId}
        onPickSector={onPickSector}
      />
    </>
  );
}

// ====================================================================== //
// IntroScreen
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
            <div className="intro-line-4">was already <em>whispering.</em></div>
          </h1>
          <div className="intro-sub">
            KOSPI · 1,400 disclosures / day · decoded by AI
            <br />A spatial atlas of Korea's listed companies.
          </div>
          <button className="enter-button" onClick={onEnter} type="button">
            <span className="enter-icon">▷</span>
            <span className="enter-label">ENTER THE GALAXY</span>
            <span className="enter-hint">click anywhere</span>
          </button>
        </main>
        <HudBottom />
        <HudRails tElapsed={tElapsed} />
        <button className="intro-click" aria-label="Enter the galaxy" onClick={onEnter} type="button" />
      </div>
    </div>
  );
}

// ====================================================================== //
// PhaseTab
// ====================================================================== //
function PhaseTab({
  activeTab, onTabChange,
  data, activeSectorId, onPickSector,
  kospi, breadcrumb,
}) {
  let body;
  if (activeTab === "financials") {
    body = (
      <FinanceTab
        data={data}
        activeSectorId={activeSectorId}
        onPickSector={onPickSector}
      />
    );
  } else if (activeTab === "disclosures") {
    body = <PlaceholderTab title="DISCLOSURE NETWORK" onBack={() => onTabChange("financials")} />;
  } else {
    body = <PlaceholderTab title="TIME MACHINE" onBack={() => onTabChange("financials")} />;
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
// Hooks: data loader + UTC + KOSPI mock
// ====================================================================== //
function useDataLoader() {
  const [state, setState] = useState({
    loading: true,
    error: null,
    data: { nodes: [], sectors: [], scenarios: [], discAll: [], stmtAll: [], usingMock: false, meta: {} },
  });
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const D = window.DiscloseAI;
        if (!D || !D.loadAll) {
          throw new Error("DiscloseAI.loadAll not available — data scripts not loaded");
        }
        const data = await D.loadAll();
        if (alive) setState({ loading: false, error: null, data });
      } catch (e) {
        console.error("[v2] data load failed:", e);
        if (alive) setState({ loading: false, error: e.message, data: { nodes: [], sectors: [], scenarios: [], discAll: [], stmtAll: [], usingMock: true, meta: {} } });
      }
    })();
    return () => { alive = false; };
  }, []);
  return state;
}

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

function useKospiMock() {
  const initial = (window.DiscloseAI && window.DiscloseAI.KOSPI_MOCK) || { value: 3142.8, delta: 0.42 };
  const [val, setVal] = useState(initial);
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
  const { loading, data, error } = useDataLoader();
  const [phase, setPhase] = useState("intro");
  const [activeTab, setActiveTab] = useState("financials");
  const [activeSectorId, setActiveSectorId] = useState(null);
  const [tElapsed, setTElapsed] = useState(0);

  const sessionId = useRef(`DA-${Math.floor(2000 + Math.random() * 700)}`);
  const utc = useNowUtc();
  const kospi = useKospiMock();

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

  const breadcrumb = useMemo(() => {
    if (activeTab !== "financials") return [];
    const crumbs = [{ label: "GALAXY", onClick: () => setActiveSectorId(null) }];
    if (activeSectorId) {
      const sec = (data.sectors || []).find((s) => s.id === activeSectorId);
      if (sec) crumbs.push({ label: sec.ko });
    }
    return crumbs;
  }, [activeTab, activeSectorId, data.sectors]);

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
      data={data}
      activeSectorId={activeSectorId}
      onPickSector={handlePickSector}
      kospi={kospi}
      breadcrumb={breadcrumb}
    />
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
