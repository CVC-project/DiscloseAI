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
// GalaxyCanvas — 별 트윙클 + 갤럭시 디스크 + dust 회전 + shooting stars
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
    let shootingStars = [];
    let nextShootAt = performance.now() + 1500 + Math.random() * 2500;
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

    function spawnShootingStar() {
      const W = canvas.width, H = canvas.height;
      // 우상단~좌하단 방향 (일반적 별똥별 패턴)
      const fromX = Math.random() * W * 0.6 + W * 0.4;
      const fromY = Math.random() * H * 0.4;
      // 속도 (px/sec) — DPR 보정
      const speed = (320 + Math.random() * 160) * dpr;
      const angle = Math.PI * (0.62 + Math.random() * 0.16); // 110~140도
      shootingStars.push({
        x: fromX,
        y: fromY,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 0,
        ttl: 0.9 + Math.random() * 0.5, // seconds
      });
    }

    let t = 0;
    let lastTs = performance.now();
    function loop(ts) {
      const dt = Math.min(50, ts - lastTs) / 1000;
      lastTs = ts;
      t += dt;
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

      // shooting stars
      if (ts >= nextShootAt && shootingStars.length < 3) {
        spawnShootingStar();
        nextShootAt = ts + 1800 + Math.random() * 4000;
      }
      shootingStars = shootingStars.filter((s) => s.life < s.ttl);
      for (const s of shootingStars) {
        s.x += s.vx * dt;
        s.y += s.vy * dt;
        s.life += dt;
        const lifeRatio = s.life / s.ttl;
        const alpha = (lifeRatio < 0.15 ? lifeRatio / 0.15 : 1 - (lifeRatio - 0.15) / 0.85) * 0.95;
        const len = 120 * dpr;
        const sp = Math.hypot(s.vx, s.vy);
        const tx = s.x - (s.vx / sp) * len;
        const ty = s.y - (s.vy / sp) * len;
        const lg = ctx.createLinearGradient(s.x, s.y, tx, ty);
        lg.addColorStop(0, `rgba(255,255,255,${alpha})`);
        lg.addColorStop(0.4, `rgba(225,235,255,${alpha * 0.5})`);
        lg.addColorStop(1, "rgba(255,255,255,0)");
        ctx.strokeStyle = lg;
        ctx.lineWidth = 1.6 * dpr;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(tx, ty);
        ctx.stroke();
        // bright head
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, 1.6 * dpr, 0, Math.PI * 2);
        ctx.fill();
      }

      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [density]);
  return <canvas className="galaxy-canvas" ref={ref} />;
}

// ====================================================================== //
// SolarStage — stage별 행성을 회전 + 클릭 hit-test.
//   stage='galaxy'  : sectors 12개
//   stage='sector'  : 해당 섹터의 회사 노드들
//   stage='company' : 회사 + rl 관계기업
// ====================================================================== //
function SolarStage({ stage, planets, activeId, accentColor, onPick }) {
  const ref = useRef(null);
  const hitsRef = useRef([]);

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

    // 행성마다 자기 궤도 — 동일한 메인 ring + 작은 변동 (각 행성당 0.92~1.08 배)
    // 일관된 변동을 위해 결정적 함수 사용 (planets 변경 시에도 같은 행성에는 같은 비율)
    const orbitVar = planets.map((p) => {
      const seed = (p.id || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0);
      // 0.92 ~ 1.08 (16% 범위)
      return 0.92 + ((seed * 17) % 17) / 100;
    });

    // 틸팅 (Y축 squash + 살짝 회전) — 원본 디자인의 "평평한 + 비스듬한" 타원
    const TILT = 0.16; // ~9.2도, 시계방향
    const Y_SQUASH = 0.32; // 더 평평하게 (이전 0.78에서 대폭 squash)
    const ORBIT_SPEED = 0.00065; // 매우 느림 (이전 0.0042에서 약 1/6)

    let t = 0;
    function loop() {
      t += ORBIT_SPEED;
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      const cx = W / 2, cy = H / 2;
      const baseR = Math.min(W, H) * 0.32;
      const sunRGB = stage === "galaxy" ? [255, 220, 160] : hexToRGB(accentColor || "#5eead4");

      // 중심 별 — 더 작게, glow 위주
      const sunR = 36 * dpr;
      const sunGrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, sunR * 2.5);
      sunGrd.addColorStop(0, `rgba(${sunRGB[0]}, ${sunRGB[1]}, ${sunRGB[2]}, 0.95)`);
      sunGrd.addColorStop(0.35, `rgba(${sunRGB[0]}, ${sunRGB[1]}, ${sunRGB[2]}, 0.45)`);
      sunGrd.addColorStop(1, `rgba(${sunRGB[0]}, ${sunRGB[1]}, ${sunRGB[2]}, 0)`);
      ctx.fillStyle = sunGrd;
      ctx.beginPath();
      ctx.arc(cx, cy, sunR * 2.5, 0, Math.PI * 2);
      ctx.fill();
      // sun core
      ctx.fillStyle = `rgba(${sunRGB[0]}, ${sunRGB[1]}, ${sunRGB[2]}, 0.9)`;
      ctx.beginPath();
      ctx.arc(cx, cy, sunR * 0.55, 0, Math.PI * 2);
      ctx.fill();

      hitsRef.current = [];
      const total = planets.length || 1;

      // ----- 1단계: 모든 비활성 궤도(점선) 먼저 그려서 행성 뒤에 깔리게 -----
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(TILT);
      planets.forEach((p, i) => {
        const isActive = p.id === activeId;
        const r = baseR * orbitVar[i];
        if (!isActive) {
          ctx.strokeStyle = "rgba(148,163,184,0.10)";
          ctx.lineWidth = 1;
          ctx.setLineDash([2, 5]);
          ctx.beginPath();
          ctx.ellipse(0, 0, r, r * Y_SQUASH, 0, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
      ctx.setLineDash([]);
      ctx.restore();

      // ----- 2단계: 활성 궤도 — 위로 올려 빛나게 -----
      const activeIdx = planets.findIndex((p) => p.id === activeId);
      if (activeIdx >= 0) {
        const ap = planets[activeIdx];
        const r = baseR * orbitVar[activeIdx];
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(TILT);
        // glow ellipse: 두 번 그려서 부드러운 외곽
        ctx.shadowColor = ap.color;
        ctx.shadowBlur = 18 * dpr;
        ctx.strokeStyle = hexA(ap.color, 0.55);
        ctx.lineWidth = 1.4 * dpr;
        ctx.beginPath();
        ctx.ellipse(0, 0, r, r * Y_SQUASH, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.restore();
      }

      // ----- 3단계: 행성 본체 + glow -----
      planets.forEach((p, i) => {
        const r = baseR * orbitVar[i];
        // 균등 각도 배치 + 매우 느린 자전. 작은 phase 차이로 행성마다 공전 위상 다름.
        const phase = (i * 0.7) % (Math.PI * 2);
        const ang = (i / total) * Math.PI * 2 + t + phase * 0.0;
        // 회전·squash 변환된 캔버스 좌표
        const lx = Math.cos(ang) * r;
        const ly = Math.sin(ang) * r * Y_SQUASH;
        // TILT 회전 적용 (canvas 절대 좌표)
        const x = cx + lx * Math.cos(TILT) - ly * Math.sin(TILT);
        const y = cy + lx * Math.sin(TILT) + ly * Math.cos(TILT);
        const isActive = p.id === activeId;
        const sizeRatio = p.sizeRatio || 1;
        const radius = (isActive ? 16 : 11) * dpr * sizeRatio;

        // soft glow (radial)
        const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 3.5);
        glow.addColorStop(0, hexA(p.color, 0.9));
        glow.addColorStop(0.35, hexA(p.color, 0.35));
        glow.addColorStop(1, hexA(p.color, 0));
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, radius * 3.5, 0, Math.PI * 2);
        ctx.fill();

        // 행성 본체
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();

        // 활성 행성 — 흰 외곽 ring + 작은 self-ring 2개
        if (isActive) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 1.5 * dpr;
          ctx.beginPath();
          ctx.arc(x, y, radius + 4 * dpr, 0, Math.PI * 2);
          ctx.stroke();
          // 행성 옆 작은 self-orbit ring (cyan dashed)
          ctx.strokeStyle = hexA(p.color, 0.55);
          ctx.lineWidth = 1 * dpr;
          ctx.setLineDash([2, 4]);
          ctx.beginPath();
          ctx.ellipse(x, y, radius * 1.9, radius * 0.85, 0, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // 라벨:
        //   galaxy   — 활성 sector만 (en + ko 두 줄)
        //   sector   — 모든 회사 (회사명 우선) + 활성은 ticker 같이
        //   company  — 모든 노드 (회사명)
        const showLabel = isActive || stage !== "galaxy";
        if (showLabel) {
          const primary = stage === "galaxy" ? p.en : p.label;
          const secondary = stage === "galaxy" ? p.label : (isActive ? p.en : null);
          if (primary) {
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.shadowColor = "rgba(0,0,0,0.85)";
            ctx.shadowBlur = 6;
            // 첫 줄
            ctx.font = `${(isActive ? 12 : 10) * dpr}px var(--font-${stage === "galaxy" ? "mono" : "body"}, sans-serif)`;
            ctx.fillStyle = isActive ? p.color : "rgba(226,232,240,0.85)";
            ctx.fillText(primary, x, y + radius + 7 * dpr);
            // 둘째 줄
            if (secondary && primary !== secondary) {
              ctx.font = `${10 * dpr}px var(--font-mono, monospace)`;
              ctx.fillStyle = "rgba(148,163,184,0.85)";
              ctx.fillText(secondary, x, y + radius + 7 * dpr + 13 * dpr);
            }
            ctx.shadowBlur = 0;
          }
        }

        hitsRef.current.push({ id: p.id, x, y, radius: radius + 6 * dpr });
      });

      raf = requestAnimationFrame(loop);
    }
    loop();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [stage, planets, activeId, accentColor]);

  const handleClick = useCallback((e) => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * dpr;
    const y = (e.clientY - rect.top) * dpr;
    let best = null;
    let bestD = Infinity;
    for (const p of hitsRef.current) {
      const d = Math.hypot(p.x - x, p.y - y);
      if (d < p.radius + 6 && d < bestD) {
        bestD = d;
        best = p;
      }
    }
    if (best && onPick) onPick(best.id);
  }, [onPick]);

  return <canvas className="solar-canvas" ref={ref} onClick={handleClick} />;
}

function hexToRGB(hex) {
  const h = (hex || "#5eead4").replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
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
function SectorPanel({ sectors, activeSectorId, onPickSector, title }) {
  return (
    <div className="panel panel-br">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-cyan" />
          <span className="panel-title">{title || "SECTOR INDEX"}</span>
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
// SectorOverviewPanel (panel-tl, stage='sector') — DAILY HIGHLIGHTS + SECTOR PULSE
// ====================================================================== //
function SectorOverviewPanel({ sector, highlights, onBackToGalaxy }) {
  // mock SECTOR PULSE — 12개 막대 (1차 mock + 워터마크)
  const pulseBars = useMemo(() => {
    const seed = (sector.id || "").length || 1;
    return Array.from({ length: 12 }, (_, i) => {
      const v = 0.3 + 0.7 * Math.abs(Math.sin(seed * 13 + i * 1.7));
      return v;
    });
  }, [sector.id]);

  return (
    <div className="panel panel-tl sector-overview-panel">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{ background: sector.color, boxShadow: `0 0 8px ${sector.color}` }} />
          <span className="panel-title">SECTOR OVERVIEW</span>
          <span className="panel-sub">섹터 개요</span>
        </div>
        <button className="back-link" onClick={onBackToGalaxy} type="button">
          ← GALAXY
        </button>
      </div>
      <div className="panel-body">
        <div className="sector-ov-body">
          <div className="sector-ov-hero">
            <div className="sector-ov-orb" style={{ background: sector.color }} />
            <div>
              <div className="sector-ov-en">{sector.en}</div>
              <div className="sector-ov-ko">{sector.ko}</div>
            </div>
          </div>

          <div className="sector-ov-stats">
            <div className="ov-stat">
              <div className="ov-k">시가총액</div>
              <div className="ov-v">{sector.cap}</div>
            </div>
            <div className="ov-stat">
              <div className="ov-k">기업 수</div>
              <div className="ov-v">{sector.memberCount}</div>
            </div>
            <div className="ov-stat">
              <div className="ov-k">YTD</div>
              <div
                className="ov-v"
                style={{ color: sector.ytdMock >= 0 ? "#4ade80" : "#f87171" }}
              >
                {(sector.ytdMock >= 0 ? "+" : "") + sector.ytdMock}%
              </div>
            </div>
            <div className="ov-stat">
              <div className="ov-k">P / E</div>
              <div className="ov-v">{sector.perMock}</div>
            </div>
          </div>

          <div className="sector-ov-section">
            <div className="ov-sec-title">DAILY HIGHLIGHTS · 오늘의 시그널</div>
            <ul className="ov-sec-list">
              {highlights.length === 0 ? (
                <li>
                  <span className="ov-bullet" style={{ background: "#94a3b8" }} />
                  <span style={{ color: "var(--text-3)", fontSize: 11 }}>
                    표시할 high_impact 공시가 없습니다.
                  </span>
                </li>
              ) : (
                highlights.map((h, i) => (
                  <li key={i}>
                    <span className="ov-time">{h.time}</span>
                    <span className="ov-bullet" style={{ background: sector.color }} />
                    <span>
                      <strong style={{ color: "#fff" }}>{h.corp_name}</strong>
                      {" · "}
                      {h.title.slice(0, 56)}
                      {h.title.length > 56 ? "…" : ""}
                    </span>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="sector-ov-section">
            <div className="ov-sec-title">
              SECTOR PULSE · 섹터 지수
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 8,
                  color: "var(--text-3)",
                  opacity: 0.7,
                  letterSpacing: "0.04em",
                  fontWeight: 400,
                }}
              >
                · 예시 데이터
              </span>
            </div>
            <div className="ov-bars">
              {pulseBars.map((v, i) => (
                <div
                  key={i}
                  className="ov-bar"
                  style={{
                    height: `${v * 100}%`,
                    background: sector.color,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ====================================================================== //
// CompanyOverviewPanel (panel-tl, stage='company')
// ====================================================================== //
function CompanyOverviewPanel({ node, sectorColor, onBackToSector, onEnterCorp }) {
  const D = window.DiscloseAI || {};
  const valuation = D.calcValuation ? D.calcValuation(node) : { per: null, pbr: null, roe: null };
  // 우선순위: percentile.roe → statements[0].roe → calcValuation.roe
  let roe = node.percentile?.roe;
  if (roe == null && Array.isArray(node.statements) && node.statements.length > 0) {
    roe = node.statements[0].roe;
  }
  if (roe == null) roe = valuation.roe;
  // raw 소수점이 길게 들어오는 경우(예: statements.roe) 정규화
  if (roe != null && Number.isFinite(roe)) roe = +Number(roe).toFixed(1);
  const fmt = (v, suf = "") => (v == null || !Number.isFinite(v) ? "-" : v + suf);
  const accent = sectorColor || "#5eead4";
  const recentDisc = (node.disc || []).slice(0, 3);
  const rels = (node.rl || []).slice(0, 4);

  const firmCount = 47; // docs/prototype/firm_<ticker>.html 47개 검증됨
  const FIRM_TICKERS = (window.__V2_FIRM_TICKERS__ ||= new Set());

  return (
    <div className="panel panel-tl company-overview-panel">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{ background: accent, boxShadow: `0 0 8px ${accent}` }} />
          <span className="panel-title">COMPANY DOSSIER</span>
          <span className="panel-sub">기업 개요</span>
        </div>
        <button className="back-link" onClick={onBackToSector} type="button">
          ← SECTOR
        </button>
      </div>
      <div className="panel-body">
        <div className="company-ov-body">
          <div className="company-ov-hero">
            <div className="company-ov-orb" style={{ background: accent }} />
            <div>
              <div className="company-ov-name">{node.n}</div>
              <div className="company-ov-en">KOSPI · {node.t} · {node.s}</div>
            </div>
          </div>

          <div className="company-ov-stats">
            <div className="ov-stat">
              <div className="ov-k">시가총액</div>
              <div className="ov-v">
                {node.market_cap ? D.trillionLabel(node.market_cap) : "-"}
              </div>
            </div>
            <div className="ov-stat">
              <div className="ov-k">PER</div>
              <div className="ov-v">{fmt(valuation.per)}</div>
            </div>
            <div className="ov-stat">
              <div className="ov-k">PBR</div>
              <div className="ov-v">{fmt(valuation.pbr)}</div>
            </div>
            <div className="ov-stat">
              <div className="ov-k">ROE</div>
              <div className="ov-v" style={{ color: roe >= 10 ? "#4ade80" : "#fff" }}>
                {fmt(roe, "%")}
              </div>
            </div>
          </div>

          {/* 현재가 — yfinance 미연결, "데이터 수집 중" 뱃지 */}
          <div className="company-ov-row" style={{ "--accent": "#94a3b8" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-3)", letterSpacing: "0.16em" }}>
              현재가
            </span>
            <span
              style={{
                fontSize: 11,
                color: "var(--text-3)",
                background: "rgba(148,163,184,0.10)",
                border: "1px solid rgba(148,163,184,0.18)",
                padding: "2px 8px",
                borderRadius: 2,
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.04em",
              }}
            >
              실시간 데이터 수집 중
            </span>
          </div>

          <div className="sector-ov-section">
            <div className="ov-sec-title">RECENT DISCLOSURES · 최근 공시</div>
            <ul className="ov-sec-list">
              {recentDisc.length === 0 ? (
                <li>
                  <span className="ov-bullet" style={{ background: "#94a3b8" }} />
                  <span style={{ color: "var(--text-3)", fontSize: 11 }}>
                    최근 공시가 없습니다.
                  </span>
                </li>
              ) : (
                recentDisc.map((d, i) => (
                  <li key={i}>
                    <span className="ov-time">{(d.date || "").slice(5).replace("-", "/")}</span>
                    <span
                      className="ov-bullet"
                      style={{ background: d.high_impact ? "#f87171" : accent }}
                    />
                    <span>{d.title.slice(0, 50)}{d.title.length > 50 ? "…" : ""}</span>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="sector-ov-section">
            <div className="ov-sec-title">RELATED ENTITIES · 관계 기업 ({rels.length})</div>
            <div className="ov-rels">
              {rels.length === 0 ? (
                <div style={{ color: "var(--text-3)", fontSize: 11 }}>관계 기업 데이터 없음</div>
              ) : (
                rels.map((r, i) => (
                  <div key={i} className="ov-rel">
                    <span
                      className="ov-rel-mark"
                      style={{ background: relColor(r.t || r.type) }}
                    />
                    <span className="ov-rel-code">{r.target_t || r.t || r.code || "-"}</span>
                    <span className="ov-rel-type" style={{ color: "var(--text-2)" }}>
                      {r.label || r.type || r.relation || "-"}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="company-ov-cta-wrap">
        <button
          className="enter-corp-cta"
          style={{ "--accent": accent }}
          onClick={onEnterCorp}
          type="button"
          aria-label="ENTER CORPORATION"
        >
          <span>ENTER CORPORATION</span>
          <span className="enter-corp-arrow">↗</span>
        </button>
        <div className="enter-corp-hint">
          새 창에서 재무정보 상세 열기
        </div>
      </div>
    </div>
  );
}

function relColor(typeOrCode) {
  // 관계 유형별 색상 (k-IFRS legend와 일치)
  const t = (typeOrCode || "").toString();
  if (/종속/.test(t)) return "#ef4444";
  if (/관계/.test(t)) return "#a78bfa";
  if (/유의/.test(t)) return "#fbbf24";
  if (/계열/.test(t)) return "#fde047";
  if (/특수/.test(t)) return "#94a3b8";
  return "#5eead4";
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
// FinanceTab — galaxy → sector → company 3단계
// ====================================================================== //
function FinanceTab({
  data,
  activeSectorId,
  activeCompanyCode,
  onPickSector,
  onPickCompany,
  onBackToGalaxy,
  onBackToSector,
  onEnterCorp,
}) {
  const sectors = data.sectors || [];
  const sector = activeSectorId ? sectors.find((s) => s.id === activeSectorId) : null;
  const node = activeCompanyCode && sector
    ? (sector.members || []).find((m) => m.t === activeCompanyCode)
    : null;
  const stage = node ? "company" : sector ? "sector" : "galaxy";

  // SolarStage planets
  let planets;
  let accentColor = "#5eead4";
  if (stage === "galaxy") {
    planets = sectors.map((s) => ({
      id: s.id,
      label: s.ko,   // 한글 (활성 sector 두 번째 줄)
      en: s.en,      // 영문 (활성 sector 첫 번째 줄)
      color: s.color,
      sizeRatio: Math.max(0.6, Math.min(1.4, Math.sqrt((s.memberCount || 1) / 4))),
    }));
  } else if (stage === "sector") {
    accentColor = sector.color;
    planets = (sector.members || []).map((m) => ({
      id: m.t,
      label: m.n,
      en: m.t,
      color: sector.color,
      sizeRatio: Math.max(0.7, Math.min(1.5, Math.sqrt(m.sz || 1))),
    }));
  } else {
    accentColor = sector.color;
    const rels = (node.rl || []).slice(0, 5);
    planets = [
      { id: node.t, label: node.n, en: node.t, color: sector.color, sizeRatio: 1.5 },
      ...rels.map((r, i) => ({
        id: r.target_t || r.t || `rel-${i}`,
        label: r.target_n || r.n || r.label || "",
        en: "",
        color: relColor(r.label || r.type),
        sizeRatio: 0.9,
      })),
    ];
  }

  // SolarStage 클릭: stage별 다른 동작
  const handlePick = useCallback(
    (id) => {
      if (stage === "galaxy") {
        onPickSector(id);
      } else if (stage === "sector") {
        onPickCompany(id);
      }
      // company stage: 관계 기업 클릭은 현재 무시 (J6 이후)
    },
    [stage, onPickSector, onPickCompany]
  );

  // BR panel 라벨
  const brTitle = stage === "galaxy" ? "SECTOR INDEX" : "SECTOR LIST";

  // Highlights for sector
  const sectorHighlights = useMemo(() => {
    if (!sector) return [];
    const D = window.DiscloseAI;
    if (!D || !D.highlightsForSector) return [];
    return D.highlightsForSector(data.discAll || [], sector.members || [], 3);
  }, [sector, data.discAll]);

  // TL panel 분기
  let tlPanel;
  if (stage === "galaxy") tlPanel = <MascotPanel stage="galaxy" />;
  else if (stage === "sector")
    tlPanel = (
      <SectorOverviewPanel
        sector={sector}
        highlights={sectorHighlights}
        onBackToGalaxy={onBackToGalaxy}
      />
    );
  else
    tlPanel = (
      <CompanyOverviewPanel
        node={node}
        sectorColor={sector.color}
        onBackToSector={onBackToSector}
        onEnterCorp={() => onEnterCorp(node)}
      />
    );

  return (
    <>
      <div className="finance-tab">
        <div className="solar-stage">
          <SolarStage
            stage={stage}
            planets={planets}
            activeId={
              stage === "galaxy" ? activeSectorId :
              stage === "sector" ? activeCompanyCode : null
            }
            accentColor={accentColor}
            onPick={handlePick}
          />
          <div className="solar-labels" />
        </div>
      </div>
      {tlPanel}
      <AssistantPanel stage={stage} />
      <LegendPanel />
      <SectorPanel
        sectors={sectors}
        activeSectorId={activeSectorId}
        onPickSector={onPickSector}
        title={brTitle}
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
  data,
  activeSectorId, activeCompanyCode,
  onPickSector, onPickCompany,
  onBackToGalaxy, onBackToSector,
  onEnterCorp,
  kospi, breadcrumb,
}) {
  let body;
  if (activeTab === "financials") {
    body = (
      <FinanceTab
        data={data}
        activeSectorId={activeSectorId}
        activeCompanyCode={activeCompanyCode}
        onPickSector={onPickSector}
        onPickCompany={onPickCompany}
        onBackToGalaxy={onBackToGalaxy}
        onBackToSector={onBackToSector}
        onEnterCorp={onEnterCorp}
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
  const [activeCompanyCode, setActiveCompanyCode] = useState(null);
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
    if (next !== "financials") {
      setActiveSectorId(null);
      setActiveCompanyCode(null);
    }
  }, []);
  const handlePickSector = useCallback((sid) => {
    setActiveSectorId(sid);
    setActiveCompanyCode(null);
  }, []);
  const handlePickCompany = useCallback((code) => setActiveCompanyCode(code), []);
  const handleBackToGalaxy = useCallback(() => {
    setActiveSectorId(null);
    setActiveCompanyCode(null);
  }, []);
  const handleBackToSector = useCallback(() => setActiveCompanyCode(null), []);
  const handleEnterCorp = useCallback((node) => {
    if (!node || !node.t) return;
    // docs/prototype/firm_<ticker>.html — 47개 존재. 미존재 ticker는 404 응답
    // 새 창에서 열기 (iframe overlay는 후속 phase)
    const url = `../../../docs/prototype/firm_${node.t}.html`;
    window.open(url, "_blank", "noopener,noreferrer");
  }, []);

  // dev/QA hook — 회전 SolarStage hit-test가 어려워 외부 자동화에서 직접 호출.
  // 안전: read-only로만 노출되며 production 사용자 동작 영향 0.
  useEffect(() => {
    window.__v2_dev = {
      pickSector: handlePickSector,
      pickCompany: handlePickCompany,
      backToGalaxy: handleBackToGalaxy,
      backToSector: handleBackToSector,
      enterCorp: handleEnterCorp,
    };
  }, [handlePickSector, handlePickCompany, handleBackToGalaxy, handleBackToSector, handleEnterCorp]);

  // breadcrumb (FINANCIALS만 의미)
  const breadcrumb = useMemo(() => {
    if (activeTab !== "financials") return [];
    const crumbs = [{ label: "GALAXY", onClick: handleBackToGalaxy }];
    if (activeSectorId) {
      const sec = (data.sectors || []).find((s) => s.id === activeSectorId);
      if (sec) {
        crumbs.push({
          label: sec.ko,
          onClick: activeCompanyCode ? handleBackToSector : undefined,
        });
        if (activeCompanyCode) {
          const node = (sec.members || []).find((m) => m.t === activeCompanyCode);
          if (node) crumbs.push({ label: node.n });
        }
      }
    }
    return crumbs;
  }, [activeTab, activeSectorId, activeCompanyCode, data.sectors, handleBackToGalaxy, handleBackToSector]);

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
      activeCompanyCode={activeCompanyCode}
      onPickSector={handlePickSector}
      onPickCompany={handlePickCompany}
      onBackToGalaxy={handleBackToGalaxy}
      onBackToSector={handleBackToSector}
      onEnterCorp={handleEnterCorp}
      kospi={kospi}
      breadcrumb={breadcrumb}
    />
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
