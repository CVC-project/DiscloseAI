/* DiscloseAI v2 — App entry (J1: IntroScreen stub만)
 *
 * 단계: J1 = IntroScreen만 렌더. J2부터 phase-tab 화면 추가 예정.
 * dashboard.html과 무관 — modules/integration/v2/ 단방향.
 *
 * 클래스 네이밍은 styles.css 인벤토리(.app/.phase-intro/.intro-overlay/...)를
 * 그대로 따른다. CSS는 디코드 결과 그대로 사용.
 */

const { useState, useEffect, useCallback, useRef } = React;

// ------------------------------------------------------------------ //
// HUD 상단 (브랜드 + 메타)
// ------------------------------------------------------------------ //
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
          <span className="hud-meta-v">
            <span className="hud-dot" /> STABLE · {uplinkMs}ms
          </span>
        </div>
        <div className="hud-meta-row">
          <span className="hud-meta-k">UTC</span>
          <span className="hud-meta-v">{utc}</span>
        </div>
      </div>
    </header>
  );
}

// ------------------------------------------------------------------ //
// HUD 좌·우 사이드 레일 (관측소 좌표 표기)
// ------------------------------------------------------------------ //
function HudRails({ tElapsed }) {
  return (
    <>
      <div className="hud-rail hud-rail-left">
        <div className="rail-tick">SECTORS · 12</div>
        <div className="rail-tick">PLANETS · 50</div>
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

// ------------------------------------------------------------------ //
// HUD 하단 (관측소 상태 + 푸터)
// ------------------------------------------------------------------ //
function HudBottom() {
  return (
    <footer className="hud-bottom">
      <div className="hud-bottom-l">
        <span className="hud-dot" />
        OBSERVATORY ONLINE
        <span className="hud-sep">/</span>
        12 SECTORS · 50 PLANETS
        <span className="hud-sep">/</span>
        NEW DISCLOSURES TONIGHT · 47
      </div>
      <div className="hud-bottom-r">2026 AI ROOKIE · MSIT</div>
    </footer>
  );
}

// ------------------------------------------------------------------ //
// IntroScreen — 시적 헤로 + ENTER CTA
// ------------------------------------------------------------------ //
function IntroScreen({ onEnter, session, uplinkMs, utc, tElapsed }) {
  return (
    <div className="app phase-intro tone-glass">
      <div className="galaxy-bg" />
      <canvas className="galaxy-canvas" />

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
        {/* 클릭 어디서든 ENTER 동일 동작 */}
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

// ------------------------------------------------------------------ //
// FinanceTabPlaceholder — J2에서 실 컴포넌트로 교체 예정
// ------------------------------------------------------------------ //
function FinanceTabPlaceholder({ onBack }) {
  return (
    <div className="app phase-tab tone-glass">
      <div className="placeholder-tab">
        <div>
          <div className="ph-eyebrow">— J2 IN PROGRESS —</div>
          <h2 className="ph-title">FINANCIALS</h2>
          <div className="ph-sub">
            J1: IntroScreen 골격 완료. J2에서 TopTabs + Galaxy 진입 화면 구현 예정.
          </div>
          <button className="ph-back" onClick={onBack} type="button">
            ← BACK TO INTRO
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ //
// App
// ------------------------------------------------------------------ //
function App() {
  const [phase, setPhase] = useState("intro"); // 'intro' | 'tab'
  const [tElapsed, setTElapsed] = useState(0);
  const sessionId = useRef(`DA-${Math.floor(2000 + Math.random() * 700)}`);
  const utc = useNowUtc();

  // T+초 카운터 (intro에서만)
  useEffect(() => {
    if (phase !== "intro") return;
    const id = setInterval(() => setTElapsed((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [phase]);

  const handleEnter = useCallback(() => setPhase("tab"), []);
  const handleBack = useCallback(() => setPhase("intro"), []);

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
  return <FinanceTabPlaceholder onBack={handleBack} />;
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
    String(d.getUTCHours()).padStart(2, "0") +
    ":" +
    String(d.getUTCMinutes()).padStart(2, "0") +
    ":" +
    String(d.getUTCSeconds()).padStart(2, "0") +
    "Z"
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
