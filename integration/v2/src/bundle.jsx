// bundle.jsx — concatenation of galaxy + solar-system + companies + app
// (Babel-in-browser scopes each script tag separately, so we bundle into one file.)

const { useRef, useEffect, useState, useMemo, useCallback } = React;

// Tweaks dev panel was a dev-only build feature (not present in original standalone bundle).
// Stubbed as no-op so app.jsx references don't crash.
function useTweaks(defaults) {
  const [tweaks, setTweaks] = useState(defaults);
  const setTweak = (k, v) => setTweaks((t) => ({ ...t, [k]: v }));
  return [tweaks, setTweak];
}
function TweaksPanel({ children }) { return null; }
function TweakSection() { return null; }
function TweakRadio() { return null; }
function TweakButton() { return null; }

// galaxy.jsx — Realistic Andromeda-style spiral galaxy + 3D-tilted solar system

// fallback 팔레트 = adapter.js SECTOR_DEF와 정합(universe 25 섹터, id·ko·color 동일).
// 실 데이터 로드 실패 시에만 사용. cap은 대략치(mock) — 색·id 정합이 목적(U2 이중 소스 해소).
const SECTOR_PALETTE = (window.__realData && window.__realData.sectors && window.__realData.sectors.length) ? window.__realData.sectors : [
  { id: 'semi',       ko: '반도체',       en: 'Semiconductor',    color: '#5eead4', cap: 3088 },
  { id: 'it',         ko: '플랫폼',       en: 'Platform',         color: '#60a5fa', cap: 1600 },
  { id: 'machinery',  ko: '기계·장비',    en: 'Machinery',        color: '#c4b5fd', cap: 900 },
  { id: 'fin',        ko: '금융',         en: 'Financials',       color: '#fbbf24', cap: 1400 },
  { id: 'pharma',     ko: '제약바이오',   en: 'Pharma & Bio',     color: '#f472b6', cap: 800 },
  { id: 'elec_parts', ko: '전기전자부품', en: 'Electronic Parts', color: '#2dd4bf', cap: 720 },
  { id: 'retail',     ko: '유통',         en: 'Retail',           color: '#a3e635', cap: 520 },
  { id: 'chem',       ko: '화학',         en: 'Chemicals',        color: '#fdba74', cap: 640 },
  { id: 'steel',      ko: '철강·금속',    en: 'Steel & Metal',    color: '#a5b4fc', cap: 480 },
  { id: 'materials',  ko: '소재',         en: 'Materials',        color: '#67e8f9', cap: 440 },
  { id: 'auto',       ko: '자동차',       en: 'Automotive',       color: '#a78bfa', cap: 1100 },
  { id: 'food',       ko: '식음료',       en: 'F&B',              color: '#bef264', cap: 360 },
  { id: 'holding',    ko: '지주',         en: 'Holdings',         color: '#fcd34d', cap: 700 },
  { id: 'cons',       ko: '건설',         en: 'Construction',     color: '#fb923c', cap: 340 },
  { id: 'media',      ko: '미디어',       en: 'Media',            color: '#e879f9', cap: 260 },
  { id: 'textile',    ko: '섬유·의류',    en: 'Textile',          color: '#fda4af', cap: 180 },
  { id: 'leisure',    ko: '레저·교육',    en: 'Leisure & Edu',    color: '#86efac', cap: 200 },
  { id: 'etc',        ko: '기타',         en: 'Other',            color: '#94a3b8', cap: 150 },
  { id: 'indust',     ko: '중공업·방산',  en: 'Industrials',      color: '#c084fc', cap: 620 },
  { id: 'logistics',  ko: '운송·물류',    en: 'Logistics',        color: '#7dd3fc', cap: 300 },
  { id: 'realestate', ko: '부동산',       en: 'Real Estate',      color: '#d6bfa8', cap: 170 },
  { id: 'cosmetics',  ko: '화장품',       en: 'Cosmetics',        color: '#f9a8d4', cap: 190 },
  { id: 'prof_svc',   ko: '전문서비스',   en: 'Prof. Services',   color: '#cbd5e1', cap: 130 },
  { id: 'energy',     ko: '에너지',       en: 'Energy',           color: '#f97316', cap: 420 },
  { id: 'tele',       ko: '통신',         en: 'Telecom',          color: '#818cf8', cap: 380 },
];

// Seeded RNG factory
function srng(seed) {
  let s = seed * 9301 + 49297;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

// Build a realistic Andromeda-style star field with logarithmic spirals
function buildAndromedaStars(seed = 17) {
  const rnd = srng(seed);
  const stars = [];
  const arms = 2;             // dominant 2-arm structure (with branches)
  const winding = 0.32;       // pitch — lower = tighter coil
  const baseR = 1.0;          // all radii in normalized units (0..1)
  const armCount = 26000;     // dense disk

  for (let i = 0; i < armCount; i++) {
    const arm = i % arms;
    // density biased to mid-disk (not just center) — Andromeda has a luminous ring at ~0.55
    const u = rnd();
    let t = Math.pow(u, 0.7);
    if (rnd() < 0.45) t = 0.4 + rnd() * 0.5; // ring boost
    const r = 0.05 + t * baseR;

    const baseAngle = (arm / arms) * Math.PI * 2;
    // logarithmic spiral
    const ang = baseAngle + Math.log(r * 18 + 1) / winding + (rnd() - 0.5) * 0.18;
    // arm thickness: tighter near center, fluffier outside
    const thickness = 0.012 + (1 - t) * 0.05 + rnd() * 0.02;
    const offR = (rnd() - 0.5) * thickness * 4;

    const x = Math.cos(ang) * (r + offR);
    const y = Math.sin(ang) * (r + offR);

    // brightness: hot core, dim outskirts, plus rare bright giants
    const dist = Math.hypot(x, y);
    let brightness = Math.pow(1 - dist, 1.6) * 0.7 + 0.08;
    if (rnd() < 0.018) brightness += 0.45; // bright stars
    brightness = Math.min(brightness, 1);

    // color: warm yellow-white core → cooler blue-white arms → reddish dust regions
    let color;
    const cRoll = rnd();
    if (dist < 0.18) {
      color = `rgba(${255},${238 + Math.floor(rnd()*15)},${190 + Math.floor(rnd()*30)},`;
    } else if (dist < 0.42) {
      color = `rgba(${255},${220 + Math.floor(rnd()*25)},${180 + Math.floor(rnd()*40)},`;
    } else if (cRoll < 0.55) {
      color = `rgba(${200 + Math.floor(rnd()*40)},${215 + Math.floor(rnd()*30)},${250},`;
    } else if (cRoll < 0.85) {
      color = `rgba(${255},${230 + Math.floor(rnd()*20)},${210 + Math.floor(rnd()*30)},`;
    } else {
      // pinkish HII region
      color = `rgba(${255},${180 + Math.floor(rnd()*40)},${190 + Math.floor(rnd()*40)},`;
    }
    const alpha = 0.35 + brightness * 0.6;
    const finalColor = color + alpha.toFixed(3) + ')';

    const size = brightness > 0.85 ? 1.8 : brightness > 0.6 ? 1.2 : brightness > 0.35 ? 0.85 : 0.55;
    stars.push({ x, y, size, color: finalColor, b: brightness });
  }

  // Outer halo / faint stars
  for (let i = 0; i < 1800; i++) {
    const a = rnd() * Math.PI * 2;
    const r = 1.0 + Math.pow(rnd(), 2) * 0.45;
    const x = Math.cos(a) * r;
    const y = Math.sin(a) * r;
    stars.push({ x, y, size: 0.5, color: `rgba(220,225,255,${0.15 + rnd() * 0.25})`, b: 0.2 });
  }

  return stars;
}

// Pre-compute dust lane mask points (dark filaments along the inside edge of arms)
function buildDustLanes(seed = 31) {
  const rnd = srng(seed);
  const points = [];
  for (let arm = 0; arm < 2; arm++) {
    for (let i = 0; i < 1400; i++) {
      const t = i / 1400;
      const r = 0.12 + t * 0.85;
      const baseAngle = (arm / 2) * Math.PI * 2;
      const ang = baseAngle + Math.log(r * 18 + 1) / 0.32 - 0.10;
      const off = (rnd() - 0.5) * 0.04 * (0.5 + (1 - t));
      const x = Math.cos(ang) * (r + off);
      const y = Math.sin(ang) * (r + off);
      const opacity = 0.35 + rnd() * 0.4;
      const radius = 0.025 + rnd() * 0.04;
      points.push({ x, y, opacity, radius });
    }
  }
  return points;
}

// HII / pink emission knots
function buildHIIRegions(seed = 47) {
  const rnd = srng(seed);
  const knots = [];
  for (let i = 0; i < 90; i++) {
    const arm = i % 2;
    const r = 0.25 + rnd() * 0.6;
    const baseAngle = (arm / 2) * Math.PI * 2;
    const ang = baseAngle + Math.log(r * 18 + 1) / 0.32 + (rnd() - 0.5) * 0.12;
    knots.push({
      x: Math.cos(ang) * r,
      y: Math.sin(ang) * r,
      r: 0.012 + rnd() * 0.022,
      hue: rnd() < 0.5 ? 'pink' : 'blue',
    });
  }
  return knots;
}

// ─── Background star field with twinkle + shooting stars ─────────────────
function drawBackground(ctx, w, h, t, bgStars, shootingRef) {
  // deep space gradient
  const bg = ctx.createRadialGradient(w * 0.5, h * 0.4, 0, w * 0.5, h * 0.4, Math.max(w, h) * 0.8);
  bg.addColorStop(0,   '#0a0d1a');
  bg.addColorStop(0.4, '#04060e');
  bg.addColorStop(1,   '#000003');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);

  // distant nebula glow patches
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  const nebula1 = ctx.createRadialGradient(w * 0.18, h * 0.78, 0, w * 0.18, h * 0.78, w * 0.4);
  nebula1.addColorStop(0, 'rgba(80, 60, 140, 0.18)');
  nebula1.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = nebula1;
  ctx.fillRect(0, 0, w, h);
  const nebula2 = ctx.createRadialGradient(w * 0.85, h * 0.2, 0, w * 0.85, h * 0.2, w * 0.35);
  nebula2.addColorStop(0, 'rgba(40, 80, 130, 0.14)');
  nebula2.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = nebula2;
  ctx.fillRect(0, 0, w, h);
  ctx.restore();

  // background stars (twinkle)
  for (const s of bgStars) {
    const tw = 0.6 + Math.sin(t * s.tf + s.phase) * 0.4;
    const a = s.alpha * tw;
    ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${a})`;
    if (s.size > 1.2) {
      // bright star with cross diffraction spike
      ctx.fillRect(s.x - s.size/2, s.y - s.size/2, s.size, s.size);
      ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${a * 0.4})`;
      ctx.fillRect(s.x - s.size * 2.2, s.y - 0.3, s.size * 4.4, 0.6);
      ctx.fillRect(s.x - 0.3, s.y - s.size * 2.2, 0.6, s.size * 4.4);
    } else {
      ctx.fillRect(s.x, s.y, s.size, s.size);
    }
  }

  // shooting stars
  const arr = shootingRef.current;
  for (let i = arr.length - 1; i >= 0; i--) {
    const sh = arr[i];
    sh.life += 1/60;
    if (sh.life > sh.maxLife) { arr.splice(i, 1); continue; }
    const k = sh.life / sh.maxLife;
    const alpha = k < 0.15 ? k / 0.15 : k > 0.7 ? 1 - (k - 0.7) / 0.3 : 1;
    const x = sh.x + sh.vx * sh.life * 240;
    const y = sh.y + sh.vy * sh.life * 240;
    const tx = x - sh.vx * 80;
    const ty = y - sh.vy * 80;
    const grad = ctx.createLinearGradient(tx, ty, x, y);
    grad.addColorStop(0, 'rgba(255,255,255,0)');
    grad.addColorStop(0.6, `rgba(255,250,230,${0.6 * alpha})`);
    grad.addColorStop(1, `rgba(255,255,255,${alpha})`);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(tx, ty);
    ctx.lineTo(x, y);
    ctx.stroke();
    // bright head
    ctx.fillStyle = `rgba(255,255,255,${alpha})`;
    ctx.beginPath();
    ctx.arc(x, y, 1.6, 0, Math.PI * 2);
    ctx.fill();
  }
  // chance to spawn
  if (Math.random() < 0.008 && arr.length < 2) {
    const startX = Math.random() * w * 0.7;
    const startY = Math.random() * h * 0.4;
    const angle = -Math.PI / 4 + (Math.random() - 0.5) * 0.4;
    arr.push({
      x: startX, y: startY,
      vx: Math.cos(angle), vy: -Math.sin(angle) * -1, // downward-right
      life: 0,
      maxLife: 0.9 + Math.random() * 0.5,
    });
    // fix vy sign
    arr[arr.length-1].vy = Math.sin(angle);
  }
}

function buildBgStars(seed, w, h, count) {
  const rnd = srng(seed);
  const stars = [];
  for (let i = 0; i < count; i++) {
    const size = rnd() < 0.04 ? 1.6 : rnd() < 0.2 ? 1.0 : 0.6;
    const r = rnd();
    let cr = 220, cg = 230, cb = 255;
    if (r < 0.1) { cr = 255; cg = 220; cb = 200; } // warm
    else if (r < 0.2) { cr = 200; cg = 215; cb = 255; } // cool
    stars.push({
      x: rnd() * w,
      y: rnd() * h,
      size,
      r: cr, g: cg, b: cb,
      alpha: 0.25 + rnd() * 0.55,
      tf: 0.5 + rnd() * 2.2,
      phase: rnd() * Math.PI * 2,
    });
  }
  return stars;
}

// ─── Main galaxy renderer (intro + transition) ───────────────────────────
function GalaxyCanvas({ stage }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const startRef = useRef(performance.now());
  const stageRef = useRef(stage);
  stageRef.current = stage;
  const shootingRef = useRef([]);

  const galaxyStars = useMemo(() => buildAndromedaStars(17), []);
  const dustLanes   = useMemo(() => buildDustLanes(31), []);
  const hii         = useMemo(() => buildHIIRegions(47), []);

  useEffect(() => {
    const cvs = canvasRef.current;
    const ctx = cvs.getContext('2d');
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let bgStars = [];

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      cvs.width = cvs.clientWidth * dpr;
      cvs.height = cvs.clientHeight * dpr;
      bgStars = buildBgStars(91, cvs.width, cvs.height, 700);
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      if (window.__dossierOpen) { rafRef.current = requestAnimationFrame(draw); return; }
      const w = cvs.width, h = cvs.height;
      const t = (performance.now() - startRef.current) / 1000;
      const s = stageRef.current;

      // Background (always — even during transition)
      drawBackground(ctx, w, h, t, bgStars, shootingRef);

      const cx = w / 2, cy = h / 2;

      // Galaxy alpha & scale: grows + dims as we zoom in
      const galaxyAlpha = Math.max(0, 1 - s * 1.7);
      // Bigger base size: fits ~88% of viewport min dimension at rest
      const baseSize = Math.min(w, h) * 0.78;
      const galaxyScale = baseSize * (1 + s * 4.0);
      const tilt = -0.34;          // ~20° tilt (Andromeda-like)
      const yaw  = -0.32;          // slight rotation
      const slowSpin = t * 0.006;  // very slow rotation

      if (galaxyAlpha > 0.005) {
        ctx.save();
        ctx.globalAlpha = galaxyAlpha;
        ctx.translate(cx, cy);
        // Tilt: project the disk by squashing Y. Add slight rotation.
        ctx.rotate(yaw + slowSpin);
        ctx.scale(galaxyScale, galaxyScale * Math.cos(Math.PI / 2 + tilt) * -1);
        // After scale, units are normalized (-1..1)

        // Soft outer halo
        const halo = ctx.createRadialGradient(0, 0, 0, 0, 0, 1.4);
        halo.addColorStop(0,    'rgba(255,235,200,0.10)');
        halo.addColorStop(0.35, 'rgba(180,160,200,0.04)');
        halo.addColorStop(1,    'rgba(0,0,0,0)');
        ctx.fillStyle = halo;
        ctx.beginPath(); ctx.arc(0, 0, 1.4, 0, Math.PI * 2); ctx.fill();

        // Galaxy bulge — bright warm core
        const bulge = ctx.createRadialGradient(0, 0, 0, 0, 0, 0.55);
        bulge.addColorStop(0,    'rgba(255,248,220,0.95)');
        bulge.addColorStop(0.10, 'rgba(255,235,180,0.78)');
        bulge.addColorStop(0.25, 'rgba(255,210,160,0.42)');
        bulge.addColorStop(0.5,  'rgba(220,170,130,0.16)');
        bulge.addColorStop(1,    'rgba(0,0,0,0)');
        ctx.fillStyle = bulge;
        ctx.beginPath(); ctx.arc(0, 0, 0.55, 0, Math.PI * 2); ctx.fill();

        // Stars (additive)
        ctx.globalCompositeOperation = 'lighter';
        const starSize = 1 / galaxyScale; // counter-scale so dots stay screen-pixel size
        for (const st of galaxyStars) {
          ctx.fillStyle = st.color;
          ctx.beginPath();
          ctx.arc(st.x, st.y, st.size * starSize * 1.2, 0, Math.PI * 2);
          ctx.fill();
        }

        // HII pink/blue knots
        for (const k of hii) {
          const grad = ctx.createRadialGradient(k.x, k.y, 0, k.x, k.y, k.r);
          if (k.hue === 'pink') {
            grad.addColorStop(0, 'rgba(255,170,200,0.6)');
            grad.addColorStop(1, 'rgba(255,170,200,0)');
          } else {
            grad.addColorStop(0, 'rgba(180,210,255,0.5)');
            grad.addColorStop(1, 'rgba(180,210,255,0)');
          }
          ctx.fillStyle = grad;
          ctx.beginPath(); ctx.arc(k.x, k.y, k.r, 0, Math.PI * 2); ctx.fill();
        }

        // Dust lanes (subtractive — dark filaments tracing the spiral)
        ctx.globalCompositeOperation = 'multiply';
        for (const d of dustLanes) {
          const grad = ctx.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.radius);
          grad.addColorStop(0, `rgba(8,4,16,${d.opacity})`);
          grad.addColorStop(1, 'rgba(0,0,0,0)');
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(d.x, d.y, d.radius, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalCompositeOperation = 'source-over';

        // Bright core punch
        ctx.globalCompositeOperation = 'lighter';
        const corePunch = ctx.createRadialGradient(0, 0, 0, 0, 0, 0.12);
        corePunch.addColorStop(0, 'rgba(255,255,245,0.75)');
        corePunch.addColorStop(1, 'rgba(255,240,210,0)');
        ctx.fillStyle = corePunch;
        ctx.beginPath(); ctx.arc(0, 0, 0.12, 0, Math.PI * 2); ctx.fill();
        ctx.globalCompositeOperation = 'source-over';

        ctx.restore();
      }

      // Solar system fade-in during transition
      const solarAlpha = Math.max(0, Math.min(1, (s - 0.55) * 2.6));
      if (solarAlpha > 0.01) {
        ctx.save();
        ctx.globalAlpha = solarAlpha;
        ctx.translate(cx, cy);
        const baseR = Math.min(w, h) * 0.42;
        const sunR = baseR * 0.085;
        const sunGlow = ctx.createRadialGradient(0, 0, 0, 0, 0, sunR * 7);
        sunGlow.addColorStop(0, 'rgba(255,250,220,0.95)');
        sunGlow.addColorStop(0.18, 'rgba(255,220,160,0.5)');
        sunGlow.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = sunGlow;
        ctx.beginPath(); ctx.arc(0, 0, sunR * 7, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [galaxyStars, dustLanes, hii]);

  return <canvas ref={canvasRef} className="galaxy-canvas" />;
}

window.GalaxyCanvas = GalaxyCanvas;
window.SECTOR_PALETTE = SECTOR_PALETTE;
window.__galaxyHelpers = { buildBgStars, drawBackground, srng };
// solar-system.jsx — 3D-tilted solar system inside a simplified galaxy backdrop
// (React hooks already destructured at top of bundle)

function SolarSystem({ activeSectorId, onSelectSector, sectorVisual, orbitMotion }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const startRef = useRef(performance.now());
  const [labels, setLabels] = useState([]);
  const [hoverIdx, setHoverIdx] = useState(-1);
  const sizeRef = useRef({ w: 0, h: 0, dpr: 1 });
  const sectorsRef = useRef([]);
  const shootingRef = useRef([]);
  const bgStarsRef = useRef([]);
  const galaxyDustRef = useRef([]);

  // Tilt & yaw for 3D effect (Andromeda-like)
  const TILT = 1.05;     // Y squash (cos of tilt) — ~62° tilt
  const YAW  = -0.28;    // slight rotation around z

  // Project a normalized (x,y) on the disk → screen
  // Disk plane: x stays, y is squashed by cos(tilt)
  const project = (nx, ny, cx, cy, baseR) => {
    // rotate by yaw
    const cosY = Math.cos(YAW), sinY = Math.sin(YAW);
    const rx = nx * cosY - ny * sinY;
    const ry = nx * sinY + ny * cosY;
    // tilt: squash y
    const py = ry * Math.cos(TILT);
    return { x: cx + rx * baseR, y: cy + py * baseR, depth: ry }; // depth: -1 (back) .. 1 (front)
  };

  // Sector orbit assignments — one orbit per sector for visual clarity
  const orbitRings = useMemo(() => {
    // 16 sectors × distinct radii from 0.14 to 0.66
    return SECTOR_PALETTE.map((_, i) => {
      const r = 0.14 + (i / (SECTOR_PALETTE.length - 1)) * 0.52;
      return { radius: r, count: 1 };
    });
  }, []);

  const sectorOrbits = useMemo(() => {
    return SECTOR_PALETTE.map((_, i) => {
      // staggered initial phase so they don't line up on one side
      const phase = (i * 2.39996) % (Math.PI * 2); // golden-angle-ish
      return { radius: orbitRings[i].radius, phase, ringIdx: i };
    });
  }, [orbitRings]);

  // Build a simplified galaxy backdrop (dust arms + faint stars in disk)
  const buildBackdrop = (w, h) => {
    const rnd = window.__galaxyHelpers.srng(53);
    // bg twinkle stars — denser, more present
    const bg = window.__galaxyHelpers.buildBgStars(91, w, h, 900);
    bgStarsRef.current = bg;

    // simplified spiral arm "smoke" — confined to inner disk, very subtle
    const dust = [];
    for (let arm = 0; arm < 2; arm++) {
      for (let i = 0; i < 220; i++) {
        const t = i / 220;
        // restrict radial range so arms stay well within orbits
        const r = 0.16 + t * 0.55;
        const baseAngle = (arm / 2) * Math.PI * 2;
        const ang = baseAngle + Math.log(r * 18 + 1) / 0.32 + (rnd() - 0.5) * 0.18;
        const off = (rnd() - 0.5) * 0.035 * (0.5 + (1 - t));
        dust.push({
          x: Math.cos(ang) * (r + off),
          y: Math.sin(ang) * (r + off),
          radius: 0.025 + rnd() * 0.035,
          opacity: 0.05 + rnd() * 0.10,
          warm: rnd() < 0.4,
        });
      }
    }
    galaxyDustRef.current = dust;
  };

  useEffect(() => {
    const cvs = canvasRef.current;
    const ctx = cvs.getContext('2d');

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = cvs.clientWidth, h = cvs.clientHeight;
      cvs.width = w * dpr; cvs.height = h * dpr;
      sizeRef.current = { w, h, dpr };
      buildBackdrop(w, h);
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      if (window.__dossierOpen) { rafRef.current = requestAnimationFrame(draw); return; }
      const { w, h, dpr } = sizeRef.current;
      const t = (performance.now() - startRef.current) / 1000;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // ── Deep space background ──────────────────────────────────────
      const bg = ctx.createRadialGradient(w * 0.5, h * 0.5, 0, w * 0.5, h * 0.5, Math.max(w, h) * 0.85);
      bg.addColorStop(0,   '#0a0e1c');
      bg.addColorStop(0.45, '#04060e');
      bg.addColorStop(1,   '#000003');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // distant nebula tints
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      const n1 = ctx.createRadialGradient(w * 0.15, h * 0.85, 0, w * 0.15, h * 0.85, w * 0.5);
      n1.addColorStop(0, 'rgba(60, 40, 110, 0.16)');
      n1.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = n1; ctx.fillRect(0, 0, w, h);
      const n2 = ctx.createRadialGradient(w * 0.9, h * 0.1, 0, w * 0.9, h * 0.1, w * 0.4);
      n2.addColorStop(0, 'rgba(30, 70, 130, 0.13)');
      n2.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = n2; ctx.fillRect(0, 0, w, h);
      ctx.restore();

      // background twinkle stars
      for (const s of bgStarsRef.current) {
        const tw = 0.6 + Math.sin(t * s.tf + s.phase) * 0.4;
        const a = s.alpha * tw;
        ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${a})`;
        if (s.size > 1.2) {
          ctx.fillRect(s.x - s.size/2, s.y - s.size/2, s.size, s.size);
          ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${a * 0.35})`;
          ctx.fillRect(s.x - s.size * 2, s.y - 0.3, s.size * 4, 0.6);
          ctx.fillRect(s.x - 0.3, s.y - s.size * 2, 0.6, s.size * 4);
        } else {
          ctx.fillRect(s.x, s.y, s.size, s.size);
        }
      }

      // shooting stars
      const arr = shootingRef.current;
      for (let i = arr.length - 1; i >= 0; i--) {
        const sh = arr[i];
        sh.life += 1/60;
        if (sh.life > sh.maxLife) { arr.splice(i, 1); continue; }
        const k = sh.life / sh.maxLife;
        const alpha = k < 0.15 ? k / 0.15 : k > 0.7 ? 1 - (k - 0.7) / 0.3 : 1;
        const x = sh.x + sh.vx * sh.life * 280;
        const y = sh.y + sh.vy * sh.life * 280;
        const tx = x - sh.vx * 90;
        const ty = y - sh.vy * 90;
        const grad = ctx.createLinearGradient(tx, ty, x, y);
        grad.addColorStop(0, 'rgba(255,255,255,0)');
        grad.addColorStop(0.6, `rgba(255,250,230,${0.5 * alpha})`);
        grad.addColorStop(1, `rgba(255,255,255,${alpha})`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.4;
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(x, y); ctx.stroke();
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx.beginPath(); ctx.arc(x, y, 1.6, 0, Math.PI * 2); ctx.fill();
      }
      if (Math.random() < 0.012 && arr.length < 3) {
        const startX = Math.random() * w * 0.7;
        const startY = Math.random() * h * 0.4;
        const angle = Math.PI / 5 + (Math.random() - 0.5) * 0.3;
        arr.push({ x: startX, y: startY, vx: Math.cos(angle), vy: Math.sin(angle), life: 0, maxLife: 0.9 + Math.random() * 0.5 });
      }

      const cx = w / 2, cy = h / 2;
      const baseR = Math.min(w, h) * 0.42;

      // ── Galaxy backdrop: just a soft warm haze (no muddy dust puffs) ──
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(YAW);
      // Tilted soft glow ellipse (suggests we're in a galactic disk)
      ctx.save();
      ctx.scale(1, Math.cos(TILT));
      const haze = ctx.createRadialGradient(0, 0, 0, 0, 0, baseR * 1.5);
      haze.addColorStop(0,    'rgba(255,225,180,0.10)');
      haze.addColorStop(0.25, 'rgba(180,170,210,0.05)');
      haze.addColorStop(0.6,  'rgba(80,90,140,0.02)');
      haze.addColorStop(1,    'rgba(0,0,0,0)');
      ctx.fillStyle = haze;
      ctx.beginPath(); ctx.arc(0, 0, baseR * 1.5, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      ctx.restore();

      // ── Orbit ellipses (one per sector, tilted, sector-tinted) ─────
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(YAW);
      ctx.scale(1, Math.cos(TILT));
      ctx.lineWidth = 0.9;
      for (let i = 0; i < orbitRings.length; i++) {
        const ring = orbitRings[i];
        const sec = SECTOR_PALETTE[i];
        const isActive = activeSectorId === sec.id;
        const useColor = sectorVisual === 'mono' ? '#74EEC6' : sec.color;
        ctx.strokeStyle = isActive
          ? useColor + 'b0'
          : useColor + '24';
        ctx.lineWidth = isActive ? 1.4 : 0.9;
        ctx.setLineDash(isActive ? [] : [2, 4]);
        ctx.beginPath();
        ctx.arc(0, 0, baseR * ring.radius, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.setLineDash([]);
      ctx.restore();

      // ── Sun (bright bulge) ─────────────────────────────────────────
      const sunR = baseR * 0.075;
      const sunHaloR = sunR * 9;
      const sunHalo = ctx.createRadialGradient(cx, cy, 0, cx, cy, sunHaloR);
      sunHalo.addColorStop(0,    'rgba(255,248,220,0.85)');
      sunHalo.addColorStop(0.10, 'rgba(255,230,180,0.5)');
      sunHalo.addColorStop(0.32, 'rgba(255,200,150,0.18)');
      sunHalo.addColorStop(1,    'rgba(0,0,0,0)');
      ctx.fillStyle = sunHalo;
      ctx.beginPath(); ctx.arc(cx, cy, sunHaloR, 0, Math.PI * 2); ctx.fill();
      const sunCore = ctx.createRadialGradient(cx, cy, 0, cx, cy, sunR);
      sunCore.addColorStop(0, '#fffbe8');
      sunCore.addColorStop(0.5, '#ffd9a0');
      sunCore.addColorStop(1, 'rgba(255,180,120,0.7)');
      ctx.fillStyle = sunCore;
      ctx.beginPath(); ctx.arc(cx, cy, sunR, 0, Math.PI * 2); ctx.fill();

      // ── Sectors ─────────────────────────────────────────────────────
      // Compute positions with depth, sort back-to-front for proper layering
      const positions = [];
      SECTOR_PALETTE.forEach((sec, i) => {
        const orb = sectorOrbits[i];
        let ang;
        if (orbitMotion === 'static') ang = orb.phase;
        else {
          const speed = 0.04 + (1 - orb.radius) * 0.05;
          const dir = orbitMotion === 'realistic' ? (orb.ringIdx % 2 === 0 ? 1 : -1) : 1;
          ang = orb.phase + t * speed * dir;
        }
        const nx = Math.cos(ang) * orb.radius;
        const ny = Math.sin(ang) * orb.radius;
        const p = project(nx, ny, cx, cy, baseR);
        // depth-based scale (0.7..1.15) — closer = bigger
        const depthK = (p.depth + 1) * 0.5; // 0..1
        const planetR = (4 + Math.sqrt(sec.cap) * 0.18) * (0.78 + depthK * 0.4);
        positions.push({ x: p.x, y: p.y, r: planetR, depth: p.depth, sec, idx: i });
      });
      positions.sort((a, b) => a.depth - b.depth);

      positions.forEach(p => {
        const sec = p.sec;
        const useColor = sectorVisual === 'mono' ? '#a5f3fc' : sec.color;
        const isActive = activeSectorId === sec.id;
        const isHover = hoverIdx === p.idx;
        const glowMul = isActive ? 8 : isHover ? 6.5 : 5;

        // Outer glow
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * glowMul);
        g.addColorStop(0, useColor + 'cc');
        g.addColorStop(0.25, useColor + '55');
        g.addColorStop(1, useColor + '00');
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * glowMul, 0, Math.PI * 2); ctx.fill();

        // Active dashed halo (tilted ellipse)
        if (isActive) {
          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate(YAW);
          ctx.scale(1, Math.cos(TILT));
          ctx.strokeStyle = useColor + 'aa';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.arc(0, 0, p.r * 2.6, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.restore();
        }

        // Bright core
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 0.5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = useColor;
        ctx.globalAlpha = 0.9;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
      });

      sectorsRef.current = positions;

      rafRef.current = requestAnimationFrame(draw);
    };

    draw();

    const labelInterval = setInterval(() => {
      const next = sectorsRef.current.map(p => ({
        idx: p.idx,
        x: p.x,
        y: p.y - p.r - 14,
        sec: p.sec,
      }));
      setLabels(next);
    }, 120);

    const onMove = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = -1, bestD = 26;
      sectorsRef.current.forEach(p => {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = p.idx; }
      });
      setHoverIdx(best);
      cvs.style.cursor = best >= 0 ? 'pointer' : 'default';
    };
    const onClick = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = -1, bestD = 30;
      sectorsRef.current.forEach(p => {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = p.idx; }
      });
      if (best >= 0) onSelectSector?.(SECTOR_PALETTE[best].id);
    };
    cvs.addEventListener('mousemove', onMove);
    cvs.addEventListener('click', onClick);

    return () => {
      cancelAnimationFrame(rafRef.current);
      clearInterval(labelInterval);
      window.removeEventListener('resize', resize);
      cvs.removeEventListener('mousemove', onMove);
      cvs.removeEventListener('click', onClick);
    };
  }, [activeSectorId, hoverIdx, sectorVisual, orbitMotion, sectorOrbits, orbitRings, onSelectSector]);

  return (
    <div className="solar-stage">
      <canvas ref={canvasRef} className="solar-canvas" />
      <div className="solar-labels">
        {labels.map(l => {
          const sec = l.sec;
          const active = activeSectorId === sec.id;
          const hover = hoverIdx === l.idx;
          if (!active && !hover) return null;
          return (
            <div
              key={sec.id}
              className={"sector-label " + (active ? 'is-active' : '')}
              style={{ left: l.x, top: l.y, color: sec.color }}
            >
              <div className="sector-label-en">{sec.en}</div>
              <div className="sector-label-ko">{sec.ko}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

window.SolarSystem = SolarSystem;
// companies.jsx — Mock company data + sector map renderer

const COMPANIES = (window.__realData && window.__realData.companies) ? window.__realData.companies : {
  semi: [
    { code: '005930', name: '삼성전자',     en: 'Samsung Electronics',  cap: 480, x: 0.0, y: 0.0 },
    { code: '000660', name: 'SK하이닉스',   en: 'SK Hynix',             cap: 120, x: 0.55, y: -0.25 },
    { code: '042700', name: '한미반도체',   en: 'Hanmi Semicon',        cap: 12,  x: -0.5, y: 0.4 },
    { code: '240810', name: '원익IPS',      en: 'WONIK IPS',            cap: 4,   x: 0.4, y: 0.55 },
    { code: '108320', name: 'LX세미콘',     en: 'LX Semicon',           cap: 3,   x: -0.6, y: -0.35 },
    { code: '058470', name: '리노공업',     en: 'Leeno',                cap: 5,   x: 0.7, y: 0.3 },
    { code: '178320', name: 'ISC',         en: 'ISC',                   cap: 2,   x: -0.3, y: 0.65 },
  ],
  fin: [
    { code: '055550', name: '신한지주',     en: 'Shinhan FG',           cap: 28, x: 0, y: 0 },
    { code: '105560', name: 'KB금융',       en: 'KB FG',                cap: 32, x: 0.5, y: -0.3 },
    { code: '086790', name: '하나금융지주', en: 'Hana FG',              cap: 18, x: -0.5, y: -0.2 },
    { code: '316140', name: '우리금융지주', en: 'Woori FG',             cap: 14, x: -0.3, y: 0.5 },
    { code: '138930', name: 'BNK금융지주',  en: 'BNK FG',               cap: 5,  x: 0.6, y: 0.4 },
  ],
  auto: [
    { code: '005380', name: '현대차',       en: 'Hyundai Motor',        cap: 65, x: 0, y: 0 },
    { code: '000270', name: '기아',         en: 'Kia',                  cap: 42, x: 0.5, y: -0.2 },
    { code: '012330', name: '현대모비스',   en: 'Hyundai Mobis',        cap: 22, x: -0.5, y: -0.1 },
    { code: '011210', name: '현대위아',     en: 'Hyundai Wia',          cap: 4,  x: -0.3, y: 0.55 },
    { code: '161390', name: '한국타이어',   en: 'Hankook Tire',         cap: 5,  x: 0.5, y: 0.5 },
  ],
};

// Mock relationships keyed by company code → array of { code, type }
// types: subsidiary, associate, significant, group, related, manual
const RELATIONS = (window.__realData && window.__realData.relations) ? window.__realData.relations : {
  '005930': [
    { code: '000660', type: 'group' },
    { code: '042700', type: 'related' },
    { code: '240810', type: 'related' },
    { code: '058470', type: 'significant' },
  ],
  '000660': [
    { code: '005930', type: 'group' },
    { code: '108320', type: 'subsidiary' },
    { code: '178320', type: 'related' },
  ],
  '005380': [
    { code: '000270', type: 'subsidiary' },
    { code: '012330', type: 'subsidiary' },
    { code: '011210', type: 'subsidiary' },
    { code: '161390', type: 'related' },
  ],
  '000270': [{ code: '005380', type: 'group' }, { code: '012330', type: 'group' }],
};

const REL_STYLES = {
  subsidiary:  { color: '#74EEC6', dash: [],         label: '종속기업',   sub: 'K-IFRS · >50%' },
  associate:   { color: '#a78bfa', dash: [],         label: '관계기업',   sub: '20–50%' },
  significant: { color: '#fbbf24', dash: [],         label: '유의적 투자', sub: '5–20%' },
  group:       { color: '#94a3b8', dash: [6, 4],     label: '계열사',    sub: '공정위 지정' },
  related:     { color: '#f472b6', dash: [2, 3],     label: '특수관계자', sub: '주석 공시' },
  manual:      { color: '#64748b', dash: [1, 4],     label: '수동 보정',  sub: 'Override' },
};

window.COMPANIES = COMPANIES;
window.RELATIONS = RELATIONS;
window.REL_STYLES = REL_STYLES;

// ─── Sector map: companies as glowing nodes inside the chosen sector ────
const { useRef: _useRef, useEffect: _useEffect, useState: _useState, useMemo: _useMemo } = React;

function SectorMap({ sectorId, activeCompanyCode, onSelectCompany, onSelectGhost }) {
  const canvasRef = _useRef(null);
  const rafRef = _useRef(0);
  const startRef = _useRef(performance.now());
  const sizeRef = _useRef({ w: 0, h: 0, dpr: 1 });
  const nodesRef = _useRef([]);        // active sector company screen positions
  const relatedNodesRef = _useRef([]); // all related nodes (in-sector + cross-sector)
  const hoverRef = _useRef(null);
  const [hoverCode, setHoverCode] = _useState(null);
  const bgStarsRef = _useRef([]);
  const shootingRef = _useRef([]);
  const dotsCanvasRef = _useRef(null);   // LOD-1 배경 dots 오프스크린 (섹터 진입 시 1회 빌드)

  const sec = SECTOR_PALETTE.find(s => s.id === sectorId) || SECTOR_PALETTE[0];
  const companies = COMPANIES[sectorId] || COMPANIES.semi || [];

  // Company layout: only position data, no relation-based movement
  const layout = _useMemo(() =>
    companies.map(c => ({ ...c, gx: c.x, gy: c.y })),
  [companies]);

  // ALL related nodes in a polygon around canvas center.
  // Merges in-sector + cross-sector so lines never overlap and bounds never exceeded.
  const allRelated = _useMemo(() => {
    if (!activeCompanyCode) return [];
    const rels = RELATIONS[activeCompanyCode] || [];
    const seen = new Map();
    for (const r of rels) {
      if (!r.code || r.code === activeCompanyCode) continue;
      if (!seen.has(r.code)) seen.set(r.code, r);
    }
    const arr = Array.from(seen.values());
    const n = arr.length;
    if (!n) return [];
    const RD = window.__realData || {};
    const inSectorCodes = new Set(companies.map(c => c.code));
    // Radius grows with count to maintain arc-spacing; capped at 0.88
    const radius = Math.min(0.88, 0.60 + n * 0.032);
    const startAng = -Math.PI / 2; // first node at top
    return arr.map((r, i) => {
      const ang = startAng + (i / n) * Math.PI * 2;
      const node = RD.nodeByCode && RD.nodeByCode[r.code];
      const name = (node && node.n) || (RD.nameByCode && RD.nameByCode[r.code]) || r.name || r.code;
      const sector = node ? (window.SECTOR_PALETTE || []).find(s => s.ko === node.s) : null;
      return { code: r.code, name, cap: 10,
               gx: Math.cos(ang) * radius, gy: Math.sin(ang) * radius,
               relType: r.type || 'group', isIncoming: !!r.isIncoming,
               hasGroup: !!r.hasGroup, hasEquity: !!r.hasEquity,
               isGhost: !inSectorCodes.has(r.code),
               sectorId: sector ? sector.id : null };
    });
  }, [companies, activeCompanyCode]);

  _useEffect(() => {
    const cvs = canvasRef.current;
    const ctx = cvs.getContext('2d');
    // LOD-1 배경 dots: universe.json sectors[].dots([-1,1] 디스크 좌표)를 섹터색 옅은 점으로
    // 오프스크린 캔버스에 1회 렌더. 프레임마다 drawImage로 합성만 하고 재도장하지 않음
    // (universe/PLAN.md §5 "오프스크린 캔버스 1회 렌더 후 합성 — 프레임당 재도장 금지").
    const buildDotsLayer = (w, h, dpr) => {
      const dots = (window.__realData && window.__realData.dots && window.__realData.dots[sectorId]) || [];
      if (!dots.length) { dotsCanvasRef.current = null; return; }
      const off = document.createElement('canvas');
      off.width = w * dpr; off.height = h * dpr;
      const octx = off.getContext('2d');
      octx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const cx = w / 2, cy = h / 2;
      const baseR = Math.min(w, h) * 0.34;   // 섹터 뷰 named 레이어와 동일 스케일
      // dots는 named 클러스터와 같은 디스크를 채우되(잔여 기업 배경), named보다 훨씬
      // 작고 균일해 "성긴 별먼지"처럼 읽히게 한다. 소량 지터로 격자감 제거.
      octx.globalCompositeOperation = 'screen';
      for (let i = 0; i < dots.length; i++) {
        const d = dots[i];
        const dx = d[0], dy = d[1], bucket = d[2] || 0;
        const px = cx + dx * baseR, py = cy + dy * baseR;
        const r = 1.1 + bucket * 0.5;         // capBucket(0~) → 점 크기(named보다 작게)
        const glow = octx.createRadialGradient(px, py, 0, px, py, r * 3);
        glow.addColorStop(0, sec.color + '55');
        glow.addColorStop(1, sec.color + '00');
        octx.fillStyle = glow;
        octx.beginPath(); octx.arc(px, py, r * 3, 0, Math.PI * 2); octx.fill();
        octx.fillStyle = sec.color + 'ee';
        octx.beginPath(); octx.arc(px, py, r, 0, Math.PI * 2); octx.fill();
      }
      dotsCanvasRef.current = off;
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = cvs.clientWidth, h = cvs.clientHeight;
      cvs.width = w * dpr; cvs.height = h * dpr;
      sizeRef.current = { w, h, dpr };
      bgStarsRef.current = window.__galaxyHelpers.buildBgStars(53, w, h, 700);
      buildDotsLayer(w, h, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const animPos = layout.map(c => ({ x: c.x, y: c.y }));
    const relAnimPos = allRelated.map(r => ({ x: r.gx * 0.3, y: r.gy * 0.3 }));

    // Draw arrowhead: from (fx,fy) toward (tx,ty), head placed at target end
    function drawArrowHead(fx, fy, tx, ty, color, size) {
      const ang = Math.atan2(ty - fy, tx - fx);
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(tx - size * Math.cos(ang - 0.42), ty - size * Math.sin(ang - 0.42));
      ctx.lineTo(tx - size * Math.cos(ang + 0.42), ty - size * Math.sin(ang + 0.42));
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();
    }

    const draw = () => {
      if (window.__dossierOpen) { rafRef.current = requestAnimationFrame(draw); return; }
      const { w, h, dpr } = sizeRef.current;
      const t = (performance.now() - startRef.current) / 1000;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Background — sector-tinted deep space
      const bg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.85);
      bg.addColorStop(0, '#0a0e1c');
      bg.addColorStop(0.5, '#04060e');
      bg.addColorStop(1, '#000003');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // sector tint glow
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      const tint = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.5);
      tint.addColorStop(0, sec.color + '24');
      tint.addColorStop(1, sec.color + '00');
      ctx.fillStyle = tint;
      ctx.fillRect(0, 0, w, h);
      ctx.restore();

      // bg stars
      for (const s of bgStarsRef.current) {
        const tw = 0.6 + Math.sin(t * s.tf + s.phase) * 0.4;
        const a = s.alpha * tw;
        ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${a})`;
        ctx.fillRect(s.x, s.y, s.size, s.size);
      }

      // LOD-1 배경 dots (named 아닌 잔여 기업) — 프레임당 재도장 없이 합성만.
      // 미세 호흡(0.5~0.75) 외 정적. 기업 선택 시엔 초점 흐리지 않게 더 옅게.
      if (dotsCanvasRef.current) {
        ctx.save();
        ctx.globalAlpha = activeCompanyCode ? 0.35 : (0.72 + Math.sin(t * 0.6) * 0.08);
        ctx.drawImage(dotsCanvasRef.current, 0, 0, w, h);
        ctx.restore();
      }

      // Lerp
      layout.forEach((c, i) => {
        animPos[i].x += (c.gx - animPos[i].x) * 0.08;
        animPos[i].y += (c.gy - animPos[i].y) * 0.08;
      });
      allRelated.forEach((r, i) => {
        relAnimPos[i].x += (r.gx - relAnimPos[i].x) * 0.06;
        relAnimPos[i].y += (r.gy - relAnimPos[i].y) * 0.06;
      });

      const cx = w / 2, cy = h / 2;
      const baseR = Math.min(w, h) * (activeCompanyCode ? 0.27 : 0.34);

      // Active company screen position + node radius (for arrowhead offset)
      const ai = layout.findIndex(c => c.code === activeCompanyCode);
      const ax = ai >= 0 ? cx + animPos[ai].x * baseR : cx;
      const ay = ai >= 0 ? cy + animPos[ai].y * baseR : cy;
      const activeNodeR = ai >= 0
        ? Math.min(40, 6 + Math.sqrt(layout[ai].cap || 10) * 1.5)
        : 20;
      // Incoming arrowhead: just outside active node solid boundary (nodeR * 1.4)
      const activeHaloR = activeNodeR * 1.4;

      // Equity types = solid line + arrowhead; group/non-equity = dashed, no arrow
      const EQUITY_TYPES = new Set(['subsidiary', 'associate', 'significant']);

      // --- Relation lines + arrows ---
      if (activeCompanyCode && ai >= 0) {
        allRelated.forEach((r, i) => {
          const rx = cx + relAnimPos[i].x * baseR;
          const ry = cy + relAnimPos[i].y * baseR;
          const style = REL_STYLES[r.relType] || REL_STYLES.manual;
          const isEquity = EQUITY_TYPES.has(r.relType);

          if (r.hasGroup && r.hasEquity) {
            // ── Double parallel lines: equity (solid) + group (dashed), offset 4px ──
            const dx = rx - ax, dy = ry - ay;
            const len = Math.sqrt(dx*dx + dy*dy) || 1;
            const px = -dy/len * 2, py = dx/len * 2; // perpendicular offset (2px gap)

            // Solid equity line (offset +4px perp)
            ctx.strokeStyle = style.color + 'cc';
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            ctx.beginPath(); ctx.moveTo(ax+px, ay+py); ctx.lineTo(rx+px, ry+py); ctx.stroke();

            // Dashed group line (offset -4px perp)
            ctx.strokeStyle = REL_STYLES.group.color + 'aa';
            ctx.lineWidth = 1.2;
            ctx.setLineDash(REL_STYLES.group.dash);
            ctx.beginPath(); ctx.moveTo(ax-px, ay-py); ctx.lineTo(rx-px, ry-py); ctx.stroke();
            ctx.setLineDash([]);

            // Equity arrowhead on the solid offset line
            const arrowSz = 14;
            if (!r.isIncoming) {
              drawArrowHead(ax+px, ay+py, rx+px, ry+py, style.color + 'ee', arrowSz);
            } else {
              // Incoming: offset arrowhead to activeHaloR from active center
              const dxn = dx/len, dyn = dy/len;
              const hx = ax + dxn * activeHaloR, hy = ay + dyn * activeHaloR;
              drawArrowHead(rx+px, ry+py, hx+px, hy+py, style.color + 'ee', arrowSz);
            }

          } else {
            // ── Single line ──
            ctx.strokeStyle = style.color + 'cc';
            ctx.lineWidth = isEquity ? 2 : 1.5;
            ctx.setLineDash(style.dash);
            ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(rx, ry); ctx.stroke();
            ctx.setLineDash([]);

            if (isEquity) {
              const arrowSz = 14; // Fix 1: larger arrow
              if (!r.isIncoming) {
                // Outgoing A→B: arrowhead at related company
                drawArrowHead(ax, ay, rx, ry, style.color + 'ee', arrowSz);
              } else {
                // Incoming A←B: arrowhead outside active node halo (Fix 2)
                const dx = rx - ax, dy = ry - ay;
                const len = Math.sqrt(dx*dx + dy*dy) || 1;
                const dxn = dx/len, dyn = dy/len;
                // Place arrowhead at activeHaloR from active center toward related
                const hx = ax + dxn * activeHaloR, hy = ay + dyn * activeHaloR;
                drawArrowHead(rx, ry, hx, hy, style.color + 'ee', arrowSz);
              }
            }
          }
        });
      }

      // --- Related nodes ---
      const relScreenPos = [];
      if (activeCompanyCode) {
        allRelated.forEach((r, i) => {
          const rx = cx + relAnimPos[i].x * baseR;
          const ry = cy + relAnimPos[i].y * baseR;
          const style = REL_STYLES[r.relType] || REL_STYLES.manual;
          // Node color = related company's SECTOR color; edge color stays as relation type
          const nodeColor = (r.sectorId && (window.SECTOR_PALETTE || []).find(s => s.id === r.sectorId)?.color) || style.color;
          ctx.globalAlpha = 0.75;
          const grd = ctx.createRadialGradient(rx, ry, 0, rx, ry, 20);
          grd.addColorStop(0, nodeColor + '99'); grd.addColorStop(1, nodeColor + '00');
          ctx.fillStyle = grd;
          ctx.beginPath(); ctx.arc(rx, ry, 20, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = nodeColor;
          ctx.beginPath(); ctx.arc(rx, ry, 5, 0, Math.PI * 2); ctx.fill();
          ctx.globalAlpha = 1;
          ctx.textAlign = 'center';
          ctx.fillStyle = nodeColor;
          ctx.font = 'bold 9px sans-serif';
          ctx.fillText(r.name, rx, ry - 13);
          // Label: rel type + arrow direction indicator
          ctx.fillStyle = '#64748b';
          ctx.font = '8px sans-serif';
          // Label: type only, no direction symbols (arrows on lines are self-explanatory)
          const typeStr = style.label + (r.hasGroup && r.hasEquity ? '+계열' : '');
          ctx.fillText(typeStr, rx, ry + 19);
          ctx.textAlign = 'left';
          relScreenPos.push({ x: rx, y: ry, r: 18, code: r.code, sectorId: r.sectorId });
        });
      }
      relatedNodesRef.current = relScreenPos;

      // --- Sector company nodes (only active when company selected) ---
      const positions = [];
      layout.forEach((c, i) => {
        const x = cx + animPos[i].x * baseR;
        const y = cy + animPos[i].y * baseR;
        const isActive = c.code === activeCompanyCode;
        if (activeCompanyCode && !isActive) return; // hide non-active when selected
        const nodeR = Math.min(40, 6 + Math.sqrt(c.cap) * 1.5);
        const isHover = hoverRef.current === c.code;
        ctx.globalAlpha = 1;
        const glowMul = isActive ? 9 : isHover ? 6 : 4.5;
        const g = ctx.createRadialGradient(x, y, 0, x, y, nodeR * glowMul);
        g.addColorStop(0, sec.color + 'cc');
        g.addColorStop(0.3, sec.color + '55');
        g.addColorStop(1, sec.color + '00');
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(x, y, nodeR * glowMul, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.arc(x, y, nodeR * 0.5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = sec.color;
        ctx.globalAlpha = 0.9;
        ctx.beginPath(); ctx.arc(x, y, nodeR, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
        if (isActive) {
          const p = (Math.sin(t * 2.5) + 1) / 2;
          ctx.strokeStyle = sec.color + 'aa';
          ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.arc(x, y, nodeR * (2 + p * 0.5), 0, Math.PI * 2); ctx.stroke();
        }
        positions.push({ x, y, r: nodeR, c });
      });
      // Labels for sector companies
      ctx.textAlign = 'center';
      positions.forEach(({ x, y, r: nr, c }) => {
        const isActive = c.code === activeCompanyCode;
        ctx.globalAlpha = isActive ? 1 : 0.8;
        ctx.fillStyle = isActive ? sec.color : 'rgba(148,163,184,0.9)';
        ctx.font = `${isActive ? '600 ' : ''}10px sans-serif`;
        ctx.fillText(c.name.length > 7 ? c.name.slice(0,7)+'…' : c.name, x, y - nr - 5);
        ctx.globalAlpha = 1;
      });
      ctx.textAlign = 'left';
      nodesRef.current = positions;

      rafRef.current = requestAnimationFrame(draw);
    };
    draw();

    const onMove = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = null, bestD = 28;
      for (const p of nodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = p.c.code; }
      }
      for (const p of relatedNodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < Math.min(bestD, 22)) { bestD = d; best = '_related_'; }
      }
      hoverRef.current = best;
      setHoverCode(best);
      cvs.style.cursor = best ? 'pointer' : 'default';
    };
    const onClick = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = null, bestD = 28;
      for (const p of nodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = { code: p.c.code, isRelated: false }; }
      }
      for (const p of relatedNodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < Math.min(bestD, 22)) { bestD = d; best = { code: p.code, isRelated: true, sectorId: p.sectorId }; }
      }
      if (best) {
        if (best.isRelated) onSelectGhost?.(best.code, best.sectorId);
        else onSelectCompany?.(best.code);
      } else {
        onSelectCompany?.(null); // click empty → deselect
      }
    };
    cvs.addEventListener('mousemove', onMove);
    cvs.addEventListener('click', onClick);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      cvs.removeEventListener('mousemove', onMove);
      cvs.removeEventListener('click', onClick);
    };
  }, [layout, allRelated, activeCompanyCode, sectorId]);

  return (
    <div className="solar-stage">
      <canvas ref={canvasRef} className="solar-canvas" />
      <div className="solar-labels">
        {nodesRef.current.map((p, i) => {
          const isActive = p.c.code === activeCompanyCode;
          const isHover = hoverCode === p.c.code;
          if (!isActive && !isHover) return null;
          return (
            <div key={p.c.code} className={"company-label " + (isActive ? 'is-active' : '')}
              style={{ left: p.x, top: p.y - p.r - 14, color: sec.color }}>
              <div className="company-label-name">{p.c.name}</div>
              <div className="company-label-code">{p.c.code} · {p.c.cap}T</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

window.SectorMap = SectorMap;
// app.jsx — DiscloseAI: Phase 1 Intro → Phase 2 Galaxy → Phase 3 Sector → Phase 4 Company
// (React hooks already destructured at top of bundle)

// ─── Gemini AI streaming helper ─────────────────────────────────────────────

async function geminiStream({ apiKey, model, systemPrompt, history, onChunk, onDone, onError }) {
  const m = model || window.GEMINI_MODEL || 'gemini-2.5-flash';
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${m}:streamGenerateContent?alt=sse&key=${apiKey}`;
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: systemPrompt }] },
        contents: history,
        generationConfig: { temperature: 0.7, maxOutputTokens: 1024 },
      }),
    });
    if (!resp.ok) {
      const errText = await resp.text().catch(() => resp.status);
      throw new Error(`HTTP ${resp.status}: ${String(errText).slice(0, 120)}`);
    }
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw || raw === '[DONE]') continue;
        try {
          const data = JSON.parse(raw);
          const chunk = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
          if (chunk) onChunk(chunk);
        } catch {}
      }
    }
    onDone();
  } catch (e) {
    onError(e.message || String(e));
  }
}

function buildGeminiSystemPrompt({ context, companyName, ticker, disc, node }) {
  const name = companyName || '기업';
  const base = `당신은 DiscloseAI의 AI 코파일럿입니다. CPA(공인회계사) 수준의 한국 주식시장 공시·재무제표 전문 지식을 보유합니다.
답변 원칙: ① 한국어로 간결하게 (3-5문장) ② 투자 조언 금지 — "과거 통계 기반 참고 정보"로만 표현 ③ 불확실한 내용은 명확히 표시.`;

  if (context === 'disclosure') {
    const d = disc || {};
    return `${base}

현재 분석 대상: ${name} (${ticker || ''}) ${node && node.s ? '· ' + node.s : ''}
공시 유형: ${d.disclosure_type || '-'}  |  공시일: ${d.disclosure_date || '-'}
공시 제목: ${d.title || '(제목 없음)'}
AI 분석 요약:
${d.summary || '(요약 없음)'}`;
  }

  if (context === 'sector') {
    const sName = companyName || '섹터';
    return `${base}

현재 분석 섹터: ${sName}
섹터 내 기업들의 공시 및 재무 동향에 대해 질문에 답합니다.`;
  }

  // finance / company context
  const n = node || {};
  return `${base}

현재 분석 대상: ${name} (${ticker || ''}) ${n.s ? '· ' + n.s : ''}
EQS 종합 점수: ${n.eqs != null ? n.eqs + '점 (' + n.gr + '등급)' : '-'}
EQS 모듈: M1(현금이익률) ${n.m1 ?? '-'} / M2(회수건전성) ${n.m2 ?? '-'} / M3(부채건전성) ${n.m3 ?? '-'} / M4(본업안정성) ${n.m4 ?? '-'} / M5(자본성장성) ${n.m5 ?? '-'}
매출 ${n.rv ?? '-'}조 / 영업이익 ${n.oi ?? '-'}조 (영업이익률 ${n.oim ?? '-'}%) / 부채비율 ${n.dr ?? '-'}%`;
}

// ─── DISCLOSURES tab — TL panels ───────────────────────────────────────────

function SectorDisclosurePanel({ sector, onBack, onSelect }) {
  if (!sector) return null;
  const RD = window.__realData || {};
  const discAll = RD.discAll || [];
  const tickers = React.useMemo(
    () => new Set((sector.members || []).map(m => m.t)),
    [sector.id]
  );
  const items = React.useMemo(
    () => discAll
      .filter(d => tickers.has(d.ticker || d.stock_code))
      .sort((a, b) => (b.disclosure_date || '').localeCompare(a.disclosure_date || ''))
      .slice(0, 10),
    [tickers, discAll.length]
  );
  return (
    <div className="panel panel-tl sector-overview-panel" style={{'--accent': sector.color}}>
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: sector.color, boxShadow: `0 0 8px ${sector.color}`}} />
          <span className="panel-title">SECTOR DISCLOSURES</span>
          <span className="panel-sub">공시 피드</span>
        </div>
        <button className="back-link" onClick={onBack}>← GALAXY</button>
      </div>
      <div className="panel-body">
        {items.length === 0 && (
          <div style={{padding: '20px', textAlign: 'center', color: '#475569', fontSize: 11}}>공시 데이터 없음</div>
        )}
        {items.map((d, i) => (
          <div key={i} className={'disc-feed-row' + (!!d.high_impact ? ' hi' : '')} onClick={() => onSelect && onSelect(d)}>
            <div style={{display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2}}>
              <span className="disc-feed-date">{(d.disclosure_date || '').slice(5).replace('-', '/')}</span>
              <span className="disc-feed-corp">{d.corp_name}</span>
              {!!d.high_impact && <span className="disc-hi-badge">HI</span>}
              <span className="disc-type-badge">{d.disclosure_type || '기타'}</span>
            </div>
            <div className="disc-feed-title">{(d.title || '').slice(0, 36)}{(d.title || '').length > 36 ? '…' : ''}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompanyDisclosurePanel({ company, sector, onBack, onSelect, onEnterDisclosures }) {
  if (!company) return null;
  const [showRel, setShowRel] = React.useState(false);
  const RD = window.__realData || {};
  const ownDiscs = React.useMemo(
    () => ((RD.discByTicker && RD.discByTicker[company.code]) || []).slice(0, 8),
    [company.code]
  );
  const relDiscs = React.useMemo(() => {
    if (!showRel) return [];
    const rels = RELATIONS[company.code] || [];
    const arr = [];
    rels.forEach(r => {
      ((RD.discByTicker && RD.discByTicker[r.code]) || []).slice(0, 2).forEach(d => arr.push({...d, _relType: r.type}));
    });
    return arr.sort((a, b) => (b.disclosure_date || '').localeCompare(a.disclosure_date || '')).slice(0, 10);
  }, [company.code, showRel]);
  const relCount = React.useMemo(() => {
    return (RELATIONS[company.code] || []).reduce((acc, r) => acc + ((RD.discByTicker && RD.discByTicker[r.code]) || []).length, 0);
  }, [company.code]);
  const accentColor = sector ? sector.color : '#74EEC6';
  return (
    <div className="panel panel-tl" style={{'--accent': accentColor}}>
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: accentColor, boxShadow: `0 0 8px ${accentColor}`}} />
          <span className="panel-title">{company.name}</span>
          <span className="panel-sub" style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 9}}>{company.code}</span>
        </div>
        <button className="back-link" onClick={onBack}>← SECTOR</button>
      </div>
      <div className="panel-body" style={{display: 'flex', flexDirection: 'column'}}>
        <div style={{padding: '5px 10px 4px', fontFamily: 'var(--font-mono,monospace)', fontSize: 9, letterSpacing: '.08em', color: '#74EEC6', borderBottom: '1px solid rgba(116, 238, 198,0.1)'}}>RECENT DISCLOSURES</div>
        {ownDiscs.length === 0 && <div style={{padding: '14px 10px', color: '#475569', fontSize: 11}}>수집된 공시 없음</div>}
        {ownDiscs.map((d, i) => (
          <div key={i} className={'disc-feed-row' + (!!d.high_impact ? ' hi' : '')} onClick={() => onSelect && onSelect(d)}>
            <div style={{display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2}}>
              <span className="disc-feed-date">{(d.disclosure_date || '').slice(5).replace('-', '/')}</span>
              {!!d.high_impact && <span className="disc-hi-badge">HI</span>}
              <span className="disc-type-badge">{d.disclosure_type || '기타'}</span>
            </div>
            <div className="disc-feed-title">{(d.title || '').slice(0, 32)}{(d.title || '').length > 32 ? '…' : ''}</div>
          </div>
        ))}
        <div className="disc-rel-toggle" onClick={() => setShowRel(v => !v)}>
          <span>{showRel ? '▾' : '▸'} 관계 기업 공시</span>
          <span style={{color: '#64748b', fontSize: 9}}>{relCount}건</span>
        </div>
        {showRel && (
          <div className="disc-rel-section">
            {relDiscs.length === 0 && <div style={{padding: '8px 10px', color: '#475569', fontSize: 11}}>관계 기업 공시 없음</div>}
            {relDiscs.map((d, i) => (
              <div key={i} className={'disc-rel-row' + (!!d.high_impact ? ' hi' : '')} onClick={() => onSelect && onSelect(d)}>
                <div style={{display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2}}>
                  <span className="disc-rel-name">{d.corp_name}</span>
                  <span className="disc-type-badge" style={{fontSize: 8}}>{d._relType || ''}</span>
                  <span className="disc-feed-date">{(d.disclosure_date || '').slice(5).replace('-', '/')}</span>
                </div>
                <div className="disc-feed-title">{(d.title || '').slice(0, 28)}{(d.title || '').length > 28 ? '…' : ''}</div>
              </div>
            ))}
          </div>
        )}
        <div style={{marginTop: 'auto', padding: '10px', borderTop: '1px solid rgba(116, 238, 198,0.08)'}}>
          <button className="disc-enter-btn" onClick={onEnterDisclosures}>ENTER DISCLOSURES ↗</button>
        </div>
      </div>
    </div>
  );
}

// ─── Disclosure detail helpers ────────────────────────────────────────────

const DISC_SUM_META = {
  'Cash':          { emoji: '💰', color: '#fbbf24' },
  'Risk':          { emoji: '⚠️',  color: '#f87171' },
  'Hidden Agenda': { emoji: '🕵️', color: '#a78bfa' },
  'Verdict':       { emoji: '🎯', color: '#74EEC6' },
};

function parseDisclosureSummary(summary) {
  if (!summary) return null;
  const lines = summary.split('\n');
  const sections = [];
  let key = null, buf = [];
  for (const line of lines) {
    const m = line.match(/^\[([^\]]+)\]/);
    if (m && DISC_SUM_META[m[1]]) {
      if (key) sections.push({ key, text: buf.join(' ').trim() });
      key = m[1];
      const rest = line.slice(m[0].length).trim();
      buf = rest ? [rest] : [];
    } else if (key && line.trim()) {
      buf.push(line.trim());
    }
  }
  if (key) sections.push({ key, text: buf.join(' ').trim() });
  return sections.length > 0 ? sections : null;
}

function DisclosureSummaryView({ summary }) {
  const sections = parseDisclosureSummary(summary);
  if (!sections) return <div className="disc-ov-summary">{summary}</div>;
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 10}}>
      {sections.map((s, i) => {
        const m = DISC_SUM_META[s.key];
        return (
          <div key={i} className="disc-sum-section">
            <div className="disc-sum-label" style={{color: m.color}}>
              {m.emoji} <b>{s.key}</b>
            </div>
            <div className="disc-sum-text">{s.text}</div>
          </div>
        );
      })}
    </div>
  );
}

function QuarterlyTable({ disc }) {
  const RD = window.__realData || {};
  const ticker = disc && (disc.ticker || disc.stock_code);
  const node = ticker ? (RD.nodeByCode && RD.nodeByCode[ticker]) : null;
  const stmts = (node && node.statements && node.statements.length) ? node.statements : null;
  if (!stmts) return null;
  const sorted = [...stmts]
    .sort((a, b) => b.year !== a.year ? b.year - a.year : (b.quarter || 0) - (a.quarter || 0))
    .slice(0, 7);
  const fmtT = v => v != null ? (v / 1e12).toFixed(1) : '-';
  const fmtOi = v => v != null ? (v / 1e12).toFixed(2) : '-';
  return (
    <div style={{marginTop: 8, paddingTop: 14, borderTop: '1px solid rgba(116, 238, 198,0.1)'}}>
      <div style={{fontSize: 13, fontWeight: 700, color: '#f1f5f9', marginBottom: 8}}>
        📊 분기 재무 추이 (최근 {sorted.length}분기)
      </div>
      <table style={{width: '100%', borderCollapse: 'collapse', fontSize: 12}}>
        <thead>
          <tr style={{borderBottom: '1px solid rgba(116, 238, 198,0.2)'}}>
            {['시점', '매출(조)', '영업이익(조)', 'ROE%'].map(h => (
              <td key={h} style={{padding: '5px 0', color: '#64748b', fontWeight: 600}}>{h}</td>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((s, i) => {
            const oiColor = s.operating_income != null ? (s.operating_income >= 0 ? '#4ade80' : '#f87171') : '#94a3b8';
            return (
              <tr key={i} style={{borderBottom: '1px solid rgba(116, 238, 198,0.06)'}}>
                <td style={{padding: '5px 0', color: '#94a3b8'}}>{s.year}Q{s.quarter}</td>
                <td style={{padding: '5px 0', color: '#e2e8f0'}}>{fmtT(s.revenue)}</td>
                <td style={{padding: '5px 0', color: oiColor}}>{fmtOi(s.operating_income)}</td>
                <td style={{padding: '5px 0', color: '#e2e8f0'}}>{s.roe != null ? s.roe.toFixed(1) : '-'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function DisclosureDetailOverlay({ disc, onClose }) {
  if (!disc) return null;
  const RD = window.__realData || {};
  const D = window.DiscloseAI || {};
  const ticker = disc.ticker || disc.stock_code;
  const node = ticker ? (RD.nodeByCode && RD.nodeByCode[ticker]) : null;
  const dartDiscUrl = disc.disclosure_id
    ? `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${disc.disclosure_id}`
    : (disc.corp_name && disc.disclosure_date)
    ? `https://dart.fss.or.kr/dsab007/search.ax?textCrpNm=${encodeURIComponent(disc.corp_name)}&startDay=${(disc.disclosure_date||'').replace(/-/g,'')}&endDay=${(disc.disclosure_date||'').replace(/-/g,'')}`
    : null;
  const corpName = (node && node.n) || disc.corp_name;
  return (
    <div style={{position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(2,4,12,0.88)', backdropFilter: 'blur(18px)', display: 'flex', flexDirection: 'column'}}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      {/* Header */}
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 20px', borderBottom: '1px solid rgba(251,191,36,0.2)', background: 'rgba(8,14,26,0.9)', flexShrink: 0}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
          <span style={{width: 8, height: 8, borderRadius: '50%', background: '#fbbf24', boxShadow: '0 0 8px #fbbf24', display: 'inline-block'}} />
          <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 11, letterSpacing: '.12em', color: '#fbbf24'}}>{corpName} 공시</span>
          <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 10, color: '#64748b'}}>· {ticker}</span>
          {node && node.s && <span style={{fontSize: 10, color: '#475569'}}>· {node.s}</span>}
        </div>
        <button onClick={onClose} style={{background: 'transparent', border: '1px solid rgba(251,191,36,0.25)', color: '#94a3b8', fontFamily: 'var(--font-mono,monospace)', fontSize: 11, padding: '4px 14px', cursor: 'pointer', letterSpacing: '.08em', borderRadius: 2}}>✕ CLOSE</button>
      </div>
      {/* Body — 2-column: content left, AI chat right */}
      <div style={{flex: '1 1 0%', display: 'flex', overflow: 'hidden'}}>
        <div style={{flex: '1 1 0%', overflowY: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 12}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap'}}>
            <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 11, color: '#e2e8f0'}}>{disc.disclosure_date}</span>
            <span className="disc-type-badge" style={{padding: '2px 7px'}}>{disc.disclosure_type || '기타'}</span>
            {!!disc.high_impact && <span className="disc-hi-badge" style={{padding: '2px 7px'}}>⚡ HIGH IMPACT</span>}
          </div>
          <div className="disc-ov-title">{disc.title}</div>
          {(disc.amount != null || disc.dilution_ratio != null) && (
            <div className="disc-ov-amount">
              {disc.amount != null && <span>금액: <b style={{color: '#f1f5f9'}}>{Number(disc.amount).toLocaleString()}억원</b></span>}
              {disc.dilution_ratio != null && <span style={{marginLeft: 16}}>희석률: <b style={{color: '#f87171'}}>{(disc.dilution_ratio * 100).toFixed(1)}%</b></span>}
            </div>
          )}
          {disc.summary
            ? <DisclosureSummaryView summary={disc.summary} />
            : <div style={{color: '#475569', fontSize: 12, fontStyle: 'italic'}}>AI 요약 없음 (수집 중)</div>
          }
          {dartDiscUrl && <div><a href={dartDiscUrl} target="_blank" rel="noopener" className="disc-dart-btn">📄 DART 원문 보기 ↗</a></div>}
          <QuarterlyTable disc={disc} />
        </div>
        <OverlayAiChat companyName={corpName} ticker={ticker} context="disclosure" disc={disc} node={node} />
      </div>
      <div style={{textAlign: 'center', padding: '6px', fontFamily: 'var(--font-mono,monospace)', fontSize: 9, color: '#475569', borderTop: '1px solid rgba(251,191,36,0.1)', background: 'rgba(8,14,26,0.9)', flexShrink: 0}}>
        ⚠ 과거 통계 기반 참고 정보 — 투자 조언 아님
      </div>
    </div>
  );
}

function DisclosureFullOverlay({ ticker, onClose }) {
  const [view, setView] = React.useState('list');
  const [selectedDisc, setSelectedDisc] = React.useState(null);
  const RD = window.__realData || {};
  const D = window.DiscloseAI || {};
  const discAll = RD.discAll || [];
  const node = (RD.nodeByCode && RD.nodeByCode[ticker]) || null;
  const items = React.useMemo(
    () => discAll
      .filter(d => (d.ticker || d.stock_code) === ticker)
      .sort((a, b) => (b.disclosure_date || '').localeCompare(a.disclosure_date || '')),
    [ticker]
  );
  const corpName = node ? node.n : (items[0] && items[0].corp_name) || ticker;
  const sectorKo = node ? node.s : '';
  const capLabel = (node && node.market_cap && D.trillionLabel) ? D.trillionLabel(node.market_cap) : '';
  const dartUrl = selectedDisc
    ? (selectedDisc.disclosure_id
        ? `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${selectedDisc.disclosure_id}`
        : (selectedDisc.corp_name && selectedDisc.disclosure_date)
        ? `https://dart.fss.or.kr/dsab007/search.ax?textCrpNm=${encodeURIComponent(selectedDisc.corp_name)}&startDay=${(selectedDisc.disclosure_date||'').replace(/-/g,'')}&endDay=${(selectedDisc.disclosure_date||'').replace(/-/g,'')}`
        : null)
    : null;
  return (
    <div style={{position: 'fixed', inset: 0, zIndex: 999, background: 'rgba(2,4,12,0.88)', backdropFilter: 'blur(18px)', display: 'flex', flexDirection: 'column'}}>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 20px', borderBottom: '1px solid rgba(116, 238, 198,0.2)', background: 'rgba(8,14,26,0.9)', flexShrink: 0}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <span style={{width: 8, height: 8, borderRadius: '50%', background: '#74EEC6', boxShadow: '0 0 8px #74EEC6', display: 'inline-block'}} />
          <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 11, letterSpacing: '.12em', color: '#74EEC6'}}>DISCLOSURE DOSSIER</span>
          <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 10, color: '#64748b', letterSpacing: '.06em'}}>· {ticker}</span>
          {view === 'detail' && <button onClick={() => setView('list')} className="disc-back-link">← 목록</button>}
        </div>
        <button onClick={onClose} style={{background: 'transparent', border: '1px solid rgba(116, 238, 198,0.25)', color: '#94a3b8', fontFamily: 'var(--font-mono,monospace)', fontSize: 11, padding: '4px 14px', cursor: 'pointer', letterSpacing: '.08em', borderRadius: 2}}>✕ CLOSE</button>
      </div>
      <div style={{flex: '1 1 0%', display: 'flex', overflow: 'hidden'}}>
      {/* Left: disclosure content */}
      <div style={{flex: '1 1 0%', overflowY: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 10}}>
        <div style={{display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 6, flexWrap: 'wrap'}}>
          <span style={{color: '#f1f5f9', fontSize: 20, fontWeight: 700}}>{corpName}</span>
          {sectorKo && <span style={{color: '#64748b', fontSize: 11}}>{sectorKo}</span>}
          {capLabel && <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 11, color: '#74EEC6'}}>{capLabel}</span>}
          <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 10, color: '#475569', marginLeft: 'auto'}}>총 {items.length}건</span>
        </div>
        {view === 'list' ? (
          <>
            {items.length === 0 && <div style={{color: '#475569', fontSize: 12}}>공시 데이터 없음</div>}
            {items.map((d, i) => (
              <div key={i} className={'disc-full-list-row' + (!!d.high_impact ? ' hi' : '')} onClick={() => { setSelectedDisc(d); setView('detail'); }}>
                <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3}}>
                  <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 10, color: '#e2e8f0'}}>{d.disclosure_date}</span>
                  <span className="disc-type-badge">{d.disclosure_type || '기타'}</span>
                  {!!d.high_impact && <span className="disc-hi-badge">⚡ HI</span>}
                </div>
                <div style={{color: '#e2e8f0', fontSize: 13, lineHeight: 1.4, marginBottom: 6}}>{d.title}</div>
                {d.summary && parseDisclosureSummary(d.summary) && (
                  <DisclosureSummaryView summary={d.summary} />
                )}
              </div>
            ))}
          </>
        ) : selectedDisc ? (
          <>
            <div style={{display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap'}}>
              <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 11, color: '#e2e8f0'}}>{selectedDisc.disclosure_date}</span>
              <span className="disc-type-badge" style={{padding: '2px 7px'}}>{selectedDisc.disclosure_type || '기타'}</span>
              {!!selectedDisc.high_impact && <span className="disc-hi-badge" style={{padding: '2px 7px'}}>⚡ HIGH IMPACT</span>}
            </div>
            <div className="disc-ov-title">{selectedDisc.title}</div>
            {(selectedDisc.amount != null || selectedDisc.dilution_ratio != null) && (
              <div className="disc-ov-amount">
                {selectedDisc.amount != null && <span>금액: <b style={{color: '#f1f5f9'}}>{Number(selectedDisc.amount).toLocaleString()}억원</b></span>}
                {selectedDisc.dilution_ratio != null && <span style={{marginLeft: 16}}>희석률: <b style={{color: '#f87171'}}>{(selectedDisc.dilution_ratio * 100).toFixed(1)}%</b></span>}
              </div>
            )}
            {selectedDisc.summary
              ? <DisclosureSummaryView summary={selectedDisc.summary} />
              : <div style={{color: '#475569', fontSize: 12, fontStyle: 'italic'}}>AI 요약 없음</div>
            }
            {dartUrl && <div><a href={dartUrl} target="_blank" rel="noopener" className="disc-dart-btn">📄 DART 원문 보기 ↗</a></div>}
            <QuarterlyTable disc={selectedDisc} />
          </>
        ) : null}
      </div>{/* end left content */}
      <OverlayAiChat companyName={corpName} ticker={ticker} context="disclosure" disc={view === 'detail' ? selectedDisc : null} node={node} />
      </div>{/* end flex row */}
      <div style={{textAlign: 'center', padding: '6px', fontFamily: 'var(--font-mono,monospace)', fontSize: 9, color: '#475569', borderTop: '1px solid rgba(116, 238, 198,0.1)', background: 'rgba(8,14,26,0.9)', flexShrink: 0}}>
        ⚠ 과거 통계 기반 참고 정보 — 투자 조언 아님
      </div>
    </div>
  );
}

// ─── Overlay AI chat sidebar (Gemini functional) ──────────────────────────

function AiChatBubble({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{display: 'flex', gap: 8, alignItems: 'flex-start', flexDirection: isUser ? 'row-reverse' : 'row'}}>
      {!isUser && (
        <div style={{width: 24, height: 24, borderRadius: '50%', background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontFamily: 'var(--font-mono,monospace)', fontSize: 8, color: '#fbbf24'}}>AI</div>
      )}
      <div style={{
        background: isUser ? 'rgba(116, 238, 198,0.08)' : 'rgba(255,255,255,0.04)',
        border: isUser ? '1px solid rgba(116, 238, 198,0.15)' : 'none',
        borderRadius: 4, padding: '7px 10px',
        fontSize: 11.5, lineHeight: 1.65,
        color: isUser ? '#74EEC6' : (msg.error ? '#f87171' : '#94a3b8'),
        maxWidth: '88%', wordBreak: 'break-word',
      }}>
        {msg.text}
        {msg.streaming && <span style={{opacity: 0.5, animation: 'pulseDot 0.8s infinite'}}>▍</span>}
      </div>
    </div>
  );
}

function OverlayAiChat({ companyName, ticker, context, disc, node }) {
  const name = companyName || '기업';
  const apiKey = (window.GEMINI_API_KEY && typeof window.GEMINI_API_KEY === 'string') ? window.GEMINI_API_KEY.trim() : null;
  const hasKey = !!(apiKey && apiKey.length > 20);

  const initText = context === 'disclosure'
    ? `${name}의 공시를 분석했습니다. 궁금한 점을 질문해 보세요.\n\nTip: "이 공시가 주가에 미치는 영향은?", "Cash 항목 설명해줘" 등`
    : `${name}의 재무제표를 분석했습니다. 궁금한 점을 질문해 보세요.\n\nTip: "EQS 점수 해석해줘", "부채비율이 높은 이유는?" 등`;

  const [messages, setMessages] = React.useState([{ role: 'ai', text: initText }]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const bodyRef = React.useRef(null);

  React.useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages]);

  // Reset when disc changes (new disclosure selected)
  React.useEffect(() => {
    setMessages([{ role: 'ai', text: initText }]);
    setInput('');
  }, [disc && disc.disclosure_id, ticker]);

  async function send() {
    const text = input.trim();
    if (!text || loading || !hasKey) return;
    setInput('');
    const userMsg = { role: 'user', text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    const history = nextMessages.map(m => ({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.text }],
    }));
    const placeholder = { role: 'ai', text: '', streaming: true };
    setMessages(prev => [...prev, placeholder]);

    let accumulated = '';
    await geminiStream({
      apiKey,
      systemPrompt: buildGeminiSystemPrompt({ context, companyName: name, ticker, disc, node }),
      history,
      onChunk: (chunk) => {
        accumulated += chunk;
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'ai', text: accumulated, streaming: true };
          return updated;
        });
      },
      onDone: () => {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'ai', text: accumulated };
          return updated;
        });
        setLoading(false);
      },
      onError: (err) => {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'ai', text: `⚠ ${err}`, error: true };
          return updated;
        });
        setLoading(false);
      },
    });
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }

  const dotColor = hasKey ? '#4ade80' : '#fbbf24';
  return (
    <div style={{width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', borderLeft: '1px solid rgba(116, 238, 198,0.12)', background: 'rgba(4,7,18,0.72)', backdropFilter: 'blur(12px)'}}>
      <div style={{padding: '10px 14px', flexShrink: 0, borderBottom: '1px solid rgba(116, 238, 198,0.1)', display: 'flex', alignItems: 'center', gap: 8}}>
        <span style={{width: 7, height: 7, borderRadius: '50%', background: dotColor, boxShadow: `0 0 6px ${dotColor}`, display: 'inline-block'}} />
        <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 10, letterSpacing: '.12em', color: '#fbbf24'}}>AI FINANCIAL</span>
        <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 8, color: '#475569', marginLeft: 4}}>
          {hasKey ? 'Gemini 2.5 Flash' : '키 미설정'}
        </span>
      </div>
      {!hasKey && (
        <div style={{padding: '14px', fontSize: 11, color: '#64748b', lineHeight: 1.7, borderBottom: '1px solid rgba(116, 238, 198,0.08)'}}>
          <div style={{color: '#fbbf24', fontFamily: 'var(--font-mono,monospace)', fontSize: 9, marginBottom: 6}}>⚠ API 키 미설정</div>
          <code style={{fontSize: 10, background: 'rgba(255,255,255,0.05)', padding: '3px 7px', borderRadius: 3, display: 'block', marginBottom: 6}}>v2/config.local.js</code>
          파일에 Gemini API 키를 설정하면 활성화됩니다.
        </div>
      )}
      <div ref={bodyRef} style={{flex: '1 1 0%', overflowY: 'auto', padding: '12px 12px', display: 'flex', flexDirection: 'column', gap: 10}}>
        {messages.map((m, i) => <AiChatBubble key={i} msg={m} />)}
        {loading && messages[messages.length - 1]?.streaming !== true && (
          <div style={{fontSize: 10, color: '#475569', fontFamily: 'var(--font-mono,monospace)'}}>생성 중…</div>
        )}
      </div>
      <div style={{padding: '8px 10px', borderTop: '1px solid rgba(116, 238, 198,0.08)', flexShrink: 0, display: 'flex', gap: 6}}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          disabled={!hasKey || loading}
          placeholder={hasKey ? (loading ? 'AI 응답 중…' : '질문 입력 (Enter)') : 'config.local.js 키 설정 필요'}
          style={{flex: 1, background: 'rgba(255,255,255,0.04)', border: `1px solid ${hasKey ? 'rgba(116, 238, 198,0.2)' : 'rgba(100,116,139,0.2)'}`, borderRadius: 2, color: hasKey ? '#e2e8f0' : '#475569', fontFamily: 'inherit', fontSize: 11, padding: '6px 9px', outline: 'none'}}
        />
        <button
          onClick={send}
          disabled={!hasKey || loading || !input.trim()}
          style={{background: 'rgba(116, 238, 198,0.1)', border: '1px solid rgba(116, 238, 198,0.25)', color: '#74EEC6', padding: '6px 10px', borderRadius: 2, cursor: hasKey && !loading && input.trim() ? 'pointer' : 'not-allowed', opacity: (!hasKey || loading || !input.trim()) ? 0.35 : 1, transition: 'opacity 150ms'}}
        >↗</button>
      </div>
      <div style={{textAlign: 'center', padding: '3px 14px 5px', fontFamily: 'var(--font-mono,monospace)', fontSize: 8, color: '#334155'}}>
        과거 통계 기반 참고 · 투자 조언 아님
      </div>
    </div>
  );
}

// ─── TIME MACHINE tab components ───────────────────────────────────────────

function ScenarioCard({ scenario, phase, choice, onChoose, onNext }) {
  if (!scenario) {
    return (
      <div className="panel panel-tl">
        <div className="panel-head">
          <div className="panel-head-l">
            <span className="panel-dot" style={{background: '#a78bfa', boxShadow: '0 0 8px #a78bfa'}} />
            <span className="panel-title">TIME MACHINE</span>
            <span className="panel-sub">과거 공시 시뮬레이터</span>
          </div>
        </div>
        <div className="panel-body" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 12}}>시나리오 없음</div>
      </div>
    );
  }
  const isPositive = scenario.change_pct > 0;
  const answerDir = scenario.answer === '수혜' ? 'good' : scenario.answer === '악재' ? 'bad' : 'neutral';
  const choiceCorrect = choice === answerDir;
  return (
    <div className="panel panel-tl" style={{'--accent': '#a78bfa'}}>
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: '#a78bfa', boxShadow: '0 0 8px #a78bfa'}} />
          <span className="panel-title">TIME MACHINE</span>
          <span className="panel-sub">과거 공시 시뮬레이터</span>
        </div>
      </div>
      <div className="panel-body" style={{padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto'}}>
        <div className="tm-corp-head">
          <span style={{color: '#f1f5f9', fontWeight: 700, fontSize: 14}}>{scenario.company}</span>
          <span className="disc-type-badge" style={{marginLeft: 8}}>{scenario.ticker}</span>
          <span className="tm-date-chip">{scenario.date}</span>
          <span className="tm-cat-badge">{scenario.category}</span>
        </div>
        <div className="tm-title">{scenario.title}</div>
        <div className="tm-context">{scenario.context}</div>
        {phase === 'question' ? (
          <div className="tm-answers">
            <button className="tm-btn tm-btn-bad" onClick={() => onChoose('bad')}>악재 ↓</button>
            <button className="tm-btn tm-btn-neutral" onClick={() => onChoose('neutral')}>중립 →</button>
            <button className="tm-btn tm-btn-good" onClick={() => onChoose('good')}>호재 ↑</button>
          </div>
        ) : (
          <div style={{display: 'flex', flexDirection: 'column', gap: 8}}>
            <span className="tm-verdict" style={{
              background: choiceCorrect ? 'rgba(74,222,128,.12)' : 'rgba(248,113,113,.12)',
              borderColor: choiceCorrect ? '#4ade80' : '#f87171',
              color: choiceCorrect ? '#4ade80' : '#f87171',
            }}>{choiceCorrect ? '✓ CORRECT' : '✗ INCORRECT'}</span>
            <div className="tm-result-num" style={{color: isPositive ? '#4ade80' : '#f87171'}}>
              {isPositive ? '+' : ''}{scenario.change_pct}%
            </div>
            <div className="tm-result-sub">{scenario.window} · KOSPI {scenario.kospi_change_pct >= 0 ? '+' : ''}{scenario.kospi_change_pct}%</div>
            <div className="tm-explanation">{scenario.explanation}</div>
            <div className="tm-reveal-actions">
              {scenario.dart_url && <a href={scenario.dart_url} target="_blank" rel="noopener" className="tm-dart-btn">DART ↗</a>}
              <button className="tm-next-btn" onClick={onNext}>NEXT →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreBoardPanel({ score }) {
  const pct = score.total > 0 ? Math.round(score.correct / score.total * 100) : 0;
  return (
    <div className="panel panel-tr">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" />
          <span className="panel-title">SCORE BOARD</span>
          <span className="panel-sub">세션 점수</span>
        </div>
      </div>
      <div className="panel-body" style={{padding: '12px 14px'}}>
        <div style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 32, fontWeight: 700, color: '#74EEC6', lineHeight: 1.1, marginBottom: 6}}>
          {score.correct}<span style={{color: '#475569', fontSize: 18}}>/{score.total}</span>
        </div>
        <div style={{fontSize: 10, color: '#64748b', marginBottom: 8}}>정답률 {pct}%</div>
        <div className="score-acc-bar-wrap"><div className="score-acc-bar" style={{width: pct + '%'}} /></div>
        <div style={{marginTop: 12, display: 'flex', flexDirection: 'column', gap: 4}}>
          {[...score.history].reverse().slice(0, 6).map((h, i) => (
            <div key={i} className="score-hist-row">
              <span style={{flex: 1, fontSize: 10, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{h.company}</span>
              <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 10, color: h.change_pct >= 0 ? '#4ade80' : '#f87171'}}>{h.change_pct >= 0 ? '+' : ''}{h.change_pct}%</span>
              <span style={{marginLeft: 6, fontSize: 12, color: h.correct ? '#4ade80' : '#f87171'}}>{h.correct ? '✓' : '✗'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TmCategoryFilterPanel({ scenarios, activeCategories, onToggle }) {
  const cats = React.useMemo(() => {
    const map = {};
    scenarios.forEach(s => { map[s.category] = (map[s.category] || 0) + 1; });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [scenarios]);
  return (
    <div className="panel panel-bl">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: '#a78bfa', boxShadow: '0 0 8px #a78bfa'}} />
          <span className="panel-title">SCENARIO TYPE</span>
          <span className="panel-sub">유형 필터</span>
        </div>
        <span className="panel-count">{scenarios.length}건</span>
      </div>
      <div className="panel-body" style={{display: 'flex', flexWrap: 'wrap', gap: 6, padding: '8px 10px'}}>
        {cats.map(([cat, cnt]) => (
          <button key={cat} className={'tm-cat-chip' + (activeCategories.has(cat) ? ' is-active' : '')} onClick={() => onToggle(cat)}>
            {cat} <span style={{opacity: .6}}>{cnt}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function ScenarioIndexPanel({ scenarios, currentIndex, answeredSet, onJump }) {
  return (
    <div className="panel panel-br">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" />
          <span className="panel-title">SCENARIO LIST</span>
          <span className="panel-sub">시나리오 목록</span>
        </div>
        <span className="panel-count">{scenarios.length}</span>
      </div>
      <div className="panel-body">
        {scenarios.map((s, i) => (
          <div key={s.id} className={'sc-idx-row' + (i === currentIndex ? ' is-active' : '')} onClick={() => onJump(i)}>
            <span style={{fontFamily: 'var(--font-mono,monospace)', fontSize: 9, color: '#475569', minWidth: 16}}>{i + 1}</span>
            <span style={{flex: 1, fontSize: 11, color: i === currentIndex ? '#74EEC6' : '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{s.company}</span>
            <span className="disc-type-badge" style={{fontSize: 8}}>{s.category}</span>
            <span className={'sc-idx-dot' + (answeredSet.has(s.id) ? ' done' : '')} />
          </div>
        ))}
      </div>
    </div>
  );
}

function TimeMachineTab({ scenarios, activeTab, onTabChange }) {
  const allCats = React.useMemo(() => new Set(scenarios.map(s => s.category)), [scenarios]);
  const [activeCategories, setActiveCategories] = React.useState(allCats);
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const [tmPhase, setTmPhase] = React.useState('question');
  const [tmChoice, setTmChoice] = React.useState(null);
  const [answeredSet, setAnsweredSet] = React.useState(new Set());
  const [score, setScore] = React.useState({ correct: 0, total: 0, history: [] });
  const filtered = React.useMemo(
    () => scenarios.filter(s => activeCategories.has(s.category)),
    [scenarios, activeCategories]
  );
  const current = filtered[currentIndex] || null;
  function toggleCategory(cat) {
    setActiveCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat) && next.size > 1) next.delete(cat); else next.add(cat);
      return next;
    });
    setCurrentIndex(0); setTmPhase('question'); setTmChoice(null);
  }
  function handleChoose(dir) {
    if (!current) return;
    const answerDir = current.answer === '수혜' ? 'good' : current.answer === '악재' ? 'bad' : 'neutral';
    const correct = dir === answerDir;
    setTmChoice(dir); setTmPhase('reveal');
    setAnsweredSet(prev => new Set([...prev, current.id]));
    setScore(prev => ({
      correct: prev.correct + (correct ? 1 : 0),
      total: prev.total + 1,
      history: [...prev.history, { company: current.company, category: current.category, correct, change_pct: current.change_pct }],
    }));
  }
  function handleNext() { setTmPhase('question'); setTmChoice(null); setCurrentIndex(i => (i + 1) % Math.max(1, filtered.length)); }
  function handleJump(i) { setCurrentIndex(i); setTmPhase('question'); setTmChoice(null); }
  return (
    <div className="finance-tab">
      <TopTabs active={activeTab} onChange={onTabChange} />
      <ScenarioCard scenario={current} phase={tmPhase} choice={tmChoice} onChoose={handleChoose} onNext={handleNext} />
      <ScoreBoardPanel score={score} />
      <TmCategoryFilterPanel scenarios={scenarios} activeCategories={activeCategories} onToggle={toggleCategory} />
      <ScenarioIndexPanel scenarios={filtered} currentIndex={currentIndex} answeredSet={answeredSet} onJump={handleJump} />
    </div>
  );
}

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
        <div className="top-brand-name">DISCLOSE<span style={{color:'#74EEC6'}}>AI</span></div>
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
        <span style={{color:'#74EEC6',fontSize:13,fontWeight:600}}>3,142.80</span>
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
        </div>
        <div className="panel-count">우주비행사 · LV.01</div>
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
  const D = window.DiscloseAI || {};
  const realData = window.__realData;
  const members = (sector.members || []).map(n => n);
  const highlights = (D.highlightsForSector && realData) ? D.highlightsForSector(realData.discAll, members, 3) : null;
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
            {highlights && highlights.length ? highlights.map((h, i) => (
              <li key={i}>
                <span className="ov-bullet" style={{background: h.high_impact ? '#f87171' : sector.color}} />
                {h.high_impact && <span style={{color:'#f87171', fontFamily:'var(--font-mono)', fontSize:9, marginRight:4}}>HIGH</span>}
                <span style={{fontFamily:'var(--font-mono)', fontSize:10, color:'#94a3b8', marginRight:6}}>{h.time}</span>
                {(h.title || '').slice(0, 30)} — {h.corp_name}
              </li>
            )) : (
              <li style={{color:'#64748b'}}>최근 공시 데이터 없음</li>
            )}
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
  const node = window.__realData && window.__realData.nodeByCode && window.__realData.nodeByCode[company.code];
  const D = window.DiscloseAI || {};
  const valu = node && D.calcValuation ? D.calcValuation(node) : null;
  const capLabel = (node && node.market_cap && D.trillionLabel) ? D.trillionLabel(node.market_cap) : (company.cap + 'T');
  const fmtNum = (v, suffix) => (v == null ? '-' : v + (suffix || ''));
  const recentDisc = (node && node.disc) ? node.disc.slice(0, 3) : null;

  // #8: Sparkline (revenue history) + percentile badge
  const sparkPath = (node && node.history && D.sparklinePath)
    ? D.sparklinePath(node.history.revenue, {w: 72, h: 16, pad: 1}) : null;
  const sectorSize = sector && sector.memberCount ? sector.memberCount : null;
  const pctBadge = (node && D.percentileBadge)
    ? D.percentileBadge(node.percentile && node.percentile.eqs_total, sectorSize) : null;

  // #9: income / balance / cashflow fields from enrichNode
  const rv   = node && node.rv   ? node.rv   : null;   // revenue T
  const oi   = node && node.oi   ? node.oi   : null;   // op.income T
  const oim  = node && node.oim  ? node.oim  : null;   // op.margin %
  const dr   = node && node.dr   ? node.dr   : null;   // debt ratio %
  const ocf  = node && node.ocf  ? node.ocf  : null;   // op.cashflow T
  const ic   = node && node.icf  ? node.icf  : null;   // inv.cashflow T
  const eqsNotes = (node && node.eqs_module_notes) || {};
  const eqsMethod = node && node.eqs_method && node.eqs_method.startsWith('v3_')
    ? 'V3 · 2021~2025 · 동종업계 비교 보정'
    : null;
  return (
    <div className="panel panel-tl company-overview-panel" style={{'--accent': sector.color}}>
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot" style={{background: sector.color, boxShadow:`0 0 8px ${sector.color}`}} />
          <span className="panel-title">COMPANY DOSSIER</span>
          <span className="panel-sub">기업 개요</span>
        </div>
        <div style={{display:'flex', alignItems:'center', gap:6}}>
          {(() => {
            const reportUrl = (node && node.dart_url)
              || `https://dart.fss.or.kr/dsab007/search.ax?textCrpNm=${encodeURIComponent(company.name)}&autoSearch=Y`;
            return (
              <a href={reportUrl} target="_blank" rel="noopener" style={{fontFamily:'var(--font-mono,monospace)', fontSize:9, letterSpacing:'.06em', color:'#74EEC6', border:'1px solid rgba(116, 238, 198,0.3)', padding:'3px 7px', borderRadius:2, textDecoration:'none', whiteSpace:'nowrap'}}>📄 사업보고서</a>
            );
          })()}
          <button className="back-link" onClick={onBack}>← SECTOR</button>
        </div>
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
          <div className="ov-stat"><div className="ov-k">시가총액</div><div className="ov-v">{capLabel}</div></div>
          <div className="ov-stat"><div className="ov-k">PER</div><div className="ov-v">{fmtNum(valu && valu.per)}</div></div>
          <div className="ov-stat"><div className="ov-k">PBR</div><div className="ov-v">{fmtNum(valu && valu.pbr)}</div></div>
          <div className="ov-stat"><div className="ov-k">ROE</div><div className="ov-v" style={{color: (valu && valu.roe != null && valu.roe >= 0) ? '#4ade80' : '#f87171'}}>{fmtNum(valu && valu.roe, '%')}</div></div>
        </div>
        <div className="company-ov-row">
          <div className="ov-k">현재가</div>
          <div className="ov-v" style={{fontSize:13, color:'#94a3b8', fontFamily:'var(--font-mono)'}}>데이터 수집 중</div>
          <div style={{color:'#64748b', fontFamily:'var(--font-mono)', fontSize:10}}>yfinance pending</div>
        </div>
        {/* #9: Income / Balance / Cashflow */}
        {(rv || oi || dr || ocf) && (
          <div className="sector-ov-section">
            <div className="ov-sec-title">FINANCIALS · 재무 요약</div>
            <div className="company-ov-stats" style={{marginTop:6, flexWrap:'wrap'}}>
              {rv  && <div className="ov-stat"><div className="ov-k">매출</div><div className="ov-v" style={{fontSize:13}}>{rv}T</div></div>}
              {oi  && <div className="ov-stat"><div className="ov-k">영업이익</div><div className="ov-v" style={{fontSize:13}}>{oi}T</div></div>}
              {oim && <div className="ov-stat"><div className="ov-k">영업이익률</div><div className="ov-v" style={{fontSize:13, color: parseFloat(oim) > 0 ? '#4ade80' : '#f87171'}}>{oim}%</div></div>}
              {dr  && <div className="ov-stat"><div className="ov-k">부채비율</div><div className="ov-v" style={{fontSize:13, color: dr > 200 ? '#f87171' : '#e2e8f0'}}>{dr}%</div></div>}
              {ocf && <div className="ov-stat"><div className="ov-k">영업CF</div><div className="ov-v" style={{fontSize:13}}>{ocf}T</div></div>}
              {ic  && <div className="ov-stat"><div className="ov-k">투자CF</div><div className="ov-v" style={{fontSize:13}}>{ic}T</div></div>}
            </div>
            {/* #8: Revenue sparkline + percentile */}
            {(sparkPath || pctBadge) && (
              <div style={{display:'flex', alignItems:'center', gap:10, marginTop:8}}>
                {sparkPath && (
                  <svg width={sparkPath.w} height={sparkPath.h} style={{flexShrink:0}}>
                    <path d={sparkPath.d} fill="none" stroke="#74EEC6" strokeWidth="1.5" opacity="0.8" />
                    <circle cx={sparkPath.dot.x} cy={sparkPath.dot.y} r="2" fill="#74EEC6" />
                  </svg>
                )}
                {sparkPath && <span style={{fontSize:9,color:'#64748b',fontFamily:'var(--font-mono)'}}>매출 5년 추이</span>}
                {pctBadge && (
                  <span style={{marginLeft:'auto', fontSize:9, fontFamily:'var(--font-mono)',
                    color: pctBadge.color, border:`1px solid ${pctBadge.color}44`,
                    padding:'1px 6px', borderRadius:2}}>
                    {pctBadge.label}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
        {node && node.eqs != null && (
          <div className="sector-ov-section">
            <div className="ov-sec-title">EQS · 재무 건강도 ({node.gr || '-'} · {node.eqs}점)</div>
            {eqsMethod && <div style={{fontSize:9, color:'#5eead4', marginTop:4}}>{eqsMethod}</div>}
            <div className="company-ov-stats" style={{marginTop:6}}>
              <div className="ov-stat" title={eqsNotes.M1 || ''}><div className="ov-k">M1 현금</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m1)}</div></div>
              <div className="ov-stat" title={eqsNotes.M2 || ''}><div className="ov-k">M2 매출</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m2)}</div></div>
              <div className="ov-stat" title={eqsNotes.M3 || ''}><div className="ov-k">M3 부채</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m3)}</div></div>
              <div className="ov-stat" title={eqsNotes.M4 || ''}><div className="ov-k">M4 본업</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m4)}</div></div>
              <div className="ov-stat" title={eqsNotes.M5 || ''}><div className="ov-k">M5 자본</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m5)}</div></div>
            </div>
            <div style={{fontSize:10, color:'#64748b', marginTop:6, fontFamily:'var(--font-mono)'}}>
              ⚠ AI 산출 — 투자 조언 아님, 과거 통계 기반 참고
            </div>
          </div>
        )}
        <div className="sector-ov-section">
          <div className="ov-sec-title">RECENT DISCLOSURES · 최근 공시</div>
          <ul className="ov-sec-list">
            {recentDisc && recentDisc.length ? recentDisc.map((d, i) => (
              <li key={i}>
                <span className="ov-time" title={d.high_impact ? 'HIGH IMPACT' : ''} style={{color: d.high_impact ? '#f87171' : undefined}}>
                  {(d.date || '').slice(5).replace('-', '/')}
                </span>{' '}
                {(d.title || '').slice(0, 36)}
              </li>
            )) : (
              <li style={{color:'#64748b'}}>최근 공시 데이터 없음</li>
            )}
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

// ─── AI assistant (panel-tr — Gemini functional) ──────────────────────────
function AssistantPanel({ phase, sector, company, activeTab }) {
  const apiKey = (window.GEMINI_API_KEY && typeof window.GEMINI_API_KEY === 'string') ? window.GEMINI_API_KEY.trim() : null;
  const hasKey = !!(apiKey && apiKey.length > 20);

  const initGreeting = React.useMemo(() => {
    const greeting = AI_GREETINGS[phase] || AI_GREETINGS.galaxy;
    return greeting.map(m => ({ role: 'ai', text: m.text }));
  }, [phase]);

  const [messages, setMessages] = useState(initGreeting);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bodyRef = React.useRef(null);

  useEffect(() => {
    setMessages(initGreeting);
    setInput('');
  }, [phase, sector && sector.id, company && company.code]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading || !hasKey) return;
    setInput('');
    const next = [...messages, { role: 'user', text }];
    setMessages(next);
    setLoading(true);

    const RD = window.__realData || {};
    const node = company ? (RD.nodeByCode && RD.nodeByCode[company.code]) : null;
    const ctx = phase === 'company' ? 'finance' : phase === 'sector' ? 'sector' : 'galaxy';
    const systemPrompt = buildGeminiSystemPrompt({
      context: ctx,
      companyName: company ? company.name : (sector ? sector.ko : 'DiscloseAI'),
      ticker: company ? company.code : null,
      disc: null,
      node,
    });
    const history = next.map(m => ({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.text }],
    }));

    let accumulated = '';
    setMessages(prev => [...prev, { role: 'ai', text: '', streaming: true }]);
    await geminiStream({
      apiKey,
      systemPrompt,
      history,
      onChunk: (chunk) => {
        accumulated += chunk;
        setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: 'ai', text: accumulated, streaming: true }; return u; });
      },
      onDone: () => {
        setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: 'ai', text: accumulated }; return u; });
        setLoading(false);
      },
      onError: (err) => {
        setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: 'ai', text: `⚠ ${err}`, error: true }; return u; });
        setLoading(false);
      },
    });
  }

  function onKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }

  const dotColor = hasKey ? '#4ade80' : '#fbbf24';
  return (
    <div className="panel panel-tr">
      <div className="panel-head">
        <div className="panel-head-l">
          <span className="panel-dot panel-dot-amber" style={{background: dotColor, boxShadow: `0 0 6px ${dotColor}`}} />
          <span className="panel-title">AI FINANCIAL</span>
          <span className="panel-sub">{hasKey ? 'Gemini 2.5 Flash' : '키 미설정'}</span>
        </div>
      </div>
      <div ref={bodyRef} className="panel-body assist-body" style={{overflowY: 'auto'}}>
        {messages.map((m, i) => (
          <div key={i} className={"chat-msg " + (m.role === 'ai' ? 'is-ai' : 'is-user')}>
            {m.role === 'ai' && <div className="chat-avatar">AI</div>}
            <div className="chat-bubble" style={{color: m.error ? '#f87171' : undefined}}>
              {m.text}
              {m.streaming && <span style={{opacity: 0.5}}>▍</span>}
            </div>
          </div>
        ))}
      </div>
      <div className="assist-input">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          disabled={!hasKey || loading}
          placeholder={hasKey ? (loading ? 'AI 응답 중…' : '질문 입력 (Enter)') : 'config.local.js 키 설정 필요'}
        />
        <button onClick={send} disabled={!hasKey || loading || !input.trim()} style={{opacity: (!hasKey || loading || !input.trim()) ? 0.35 : 1, cursor: hasKey && !loading && input.trim() ? 'pointer' : 'not-allowed'}}>↗</button>
      </div>
      <div style={{fontSize:9, color:'#64748b', textAlign:'center', padding:'4px 12px 6px', fontFamily:'var(--font-mono)'}}>
        과거 통계 기반 참고 · 투자 조언 아님
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
            <span style={{color:'#74EEC6'}}>━━━</span> SOLID · 지분율 분류 (K-IFRS)
          </div>
          <div className="legend-grid">
            <LegendRow color="#74EEC6" kind="solid"   label="종속기업"    sub=">50%" />
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
        <div className="panel-count" style={{maxWidth:80,overflow:'hidden',textOverflow:'ellipsis'}}>
          {activeId ? `· ${SECTOR_PALETTE.find(s=>s.id===activeId)?.ko ?? ''}` : 'ALL'}
        </div>
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
  const [introPhase, setIntroPhase] = useState('tab'); // 인트로 제거(2026-07-13) — 진입 즉시 기업 우주(galaxy)
  const [stage, setStage] = useState(1);
  const [activeTab, setActiveTab] = useState('finance');

  // Phase within finance tab: galaxy | sector | company
  const [phase, setPhase] = useState('galaxy');
  const [activeSectorId, setActiveSectorId] = useState(null);
  const [activeCompanyCode, setActiveCompanyCode] = useState(null);

  // sector zoom-in transition
  const [zoomProgress, setZoomProgress] = useState(0);
  const zoomAnimRef = useRef(0);


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
    if (!code) {
      // null → deselect, return to sector view
      setActiveCompanyCode(null);
      setPhase('sector');
      return;
    }
    setActiveCompanyCode(code);
    setPhase('company');
  }, []);

  const selectGhost = useCallback((code, sectorId) => {
    const targetSectorId = sectorId || (() => {
      const RD = window.__realData || {};
      const node = RD.nodeByCode && RD.nodeByCode[code];
      if (!node) return null;
      const s = SECTOR_PALETTE.find(p => p.ko === node.s);
      return s ? s.id : null;
    })();
    if (!targetSectorId) return;
    // React 18 automatic batching: all state updates in the same callback are
    // batched into a single render — no intermediate "empty sector" screen.
    enterSector(targetSectorId);
    setActiveCompanyCode(code);
    setPhase('company');
  }, [enterSector]);

  const [corpOverlayTicker, setCorpOverlayTicker] = useState(null);
  const [discDetailItem, setDiscDetailItem] = useState(null);
  const [discFullOverlayTicker, setDiscFullOverlayTicker] = useState(null);
  const [dossierTab, setDossierTab] = useState('business');
  const [aiOpen, setAiOpen] = useState(false); // AI 사이드바 접기/펼치기 (기본 접힘)
  // 현금 은하수 탭 활성 티커 — dossier/data/galaxy_index.json 매니페스트 로드(build_galaxy_index.py 생성).
  // 하드코딩 대신 매니페스트라 새 골든 추가 시 스크립트 재실행만으로 UI 자동 반영(V-054).
  const [galaxyTickers, setGalaxyTickers] = useState(() => new Set(['005930']));
  useEffect(() => {
    let alive = true;
    fetch('../dossier/data/galaxy_index.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => { if (alive && m && Array.isArray(m.tickers)) setGalaxyTickers(new Set(m.tickers)); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  // DOSSIER_TABS (D1) — 탭 추가 = 이 배열 한 줄 + dossier/<id>.html + <id>_<ticker>.json
  const DOSSIER_TABS = [
    { id: 'business', label: '사업·기업',   src: 'business.html', context: 'business', activeWhen: 'always'  }, // ① 사업·기업 개요
    { id: 'galaxy',   label: '현금 은하수', src: 'galaxy.html',   context: 'galaxy',   activeWhen: 'hasData' }, // ② 현금 은하수 (galaxy_<t>.json 티커만)
    { id: 'eqs',      label: 'EQS 재무분석', src: 'firm.html',    context: 'finance',  activeWhen: 'always'  }, // ③ EQS 재무분석
  ];
  // hasData 판정 = 위 galaxyTickers(매니페스트). (구 하드코딩 GALAXY_TICKERS 제거 — V-054)

  const enterCorporation = useCallback(() => {
    if (!activeCompanyCode) return;
    setCorpOverlayTicker(activeCompanyCode);
    setDossierTab('business');
  }, [activeCompanyCode]);

  const enterDisclosures = useCallback(() => {
    if (!activeCompanyCode) return;
    setDiscFullOverlayTicker(activeCompanyCode);
  }, [activeCompanyCode]);

  // 딥링크: ?corp=<ticker> 로 CORPORATION DOSSIER 오버레이 바로 열기 (로컬 테스트 편의)
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const c = q.get('corp');
    if (c) { const s = q.get('sector'); if (s) setActiveSectorId(s); setCorpOverlayTicker(c); setDossierTab('business'); } // ?corp=&sector= 딥링크(테스트·산업군 색 확인)
  }, []);
  // 오버레이 열림 동안 배경 캔버스 draw 정지 (성능 §8)
  useEffect(() => { window.__dossierOpen = !!corpOverlayTicker; }, [corpOverlayTicker]);

  const sector = activeSectorId ? SECTOR_PALETTE.find(s => s.id === activeSectorId) : null;
  // 산업군 테마 액센트 — 오버레이 크롬(헤더·탭바)과 3탭 iframe에 공통 적용 (섹터색)
  const sectorAccent = (sector && sector.color) || '#74EEC6';
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

      {(activeTab === 'finance' || activeTab === 'disclose') && (
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
                onSelectGhost={selectGhost}
              />
            </div>
          )}

          <TopTabs active={activeTab} onChange={setActiveTab} breadcrumb={crumb} />

          {/* Top-left panel — varies by phase and active tab */}
          {activeTab === 'finance' ? (
            <>
              {phase === 'galaxy' && <MascotPanel messages={["섹터를 클릭하면, 기업을 확인할 수 있어요!", "오른쪽 아래 섹터 INDEX에서도 선택할 수 있어요.", "AI 코파일럿에게 무엇이든 물어보세요."]} />}
              {phase === 'sector' && <SectorOverviewPanel sector={sector} companyCount={companies.length} onBack={backToGalaxy} />}
              {phase === 'company' && <CompanyOverviewPanel company={company} sector={sector} onBack={backToSector} onEnter={enterCorporation} />}
            </>
          ) : (
            <>
              {phase === 'galaxy' && <MascotPanel messages={["섹터를 클릭하면 기업 공시를 확인할 수 있어요!", "고영향 공시 발생 시 DAILY HIGHLIGHTS에 즉시 표시됩니다.", "AI 코파일럿에게 공시 내용에 대해 질문해 보세요."]} />}
              {phase === 'sector' && <SectorDisclosurePanel sector={sector} onBack={backToGalaxy} onSelect={setDiscDetailItem} />}
              {phase === 'company' && <CompanyDisclosurePanel company={company} sector={sector} onBack={backToSector} onSelect={setDiscDetailItem} onEnterDisclosures={enterDisclosures} />}
            </>
          )}

          {/* Top-right — AI co-pilot, content varies */}
          <AssistantPanel phase={phase} sector={sector} company={company} activeTab={activeTab} />

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

      {introPhase === 'tab' && activeTab === 'timemach' && (
        <TimeMachineTab
          scenarios={(window.__realData && window.__realData.scenarios) || []}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      )}

      {/* ENTER CORPORATION overlay — v2 design-consistent fullscreen popup */}
      {corpOverlayTicker && (
        <div style={{
          position:'fixed', inset:0, zIndex:999,
          background:'rgba(2,4,12,0.88)', backdropFilter:'blur(18px)',
          display:'flex', flexDirection:'column',
        }}>
          {/* Header bar — 산업군 색 테마(sectorAccent) */}
          <div style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'10px 20px', borderBottom:'1px solid ' + sectorAccent + '33',
            background:'rgba(8,14,26,0.9)', flexShrink:0,
          }}>
            <div style={{display:'flex', alignItems:'center', gap:12}}>
              <span style={{width:8,height:8,borderRadius:'50%',background:sectorAccent,boxShadow:'0 0 8px '+sectorAccent, display:'inline-block'}} />
              <span style={{fontFamily:'var(--font-mono,monospace)',fontSize:11,letterSpacing:'0.12em',color:sectorAccent}}>CORPORATION DOSSIER</span>
              <span style={{fontFamily:'var(--font-mono,monospace)',fontSize:10,color:'#64748b',letterSpacing:'0.06em'}}>· {corpOverlayTicker}</span>
            </div>
            <button onClick={() => setCorpOverlayTicker(null)} style={{
              background:'transparent', border:'1px solid ' + sectorAccent + '40',
              color:'#94a3b8', fontFamily:'var(--font-mono,monospace)', fontSize:11,
              padding:'4px 14px', cursor:'pointer', letterSpacing:'0.08em',
              borderRadius:2,
            }}>✕ CLOSE</button>
          </div>
          {/* Tab bar — DOSSIER_TABS (D1), 활성 탭 = 산업군 색 */}
          <div style={{display:'flex', padding:'0 20px', flexShrink:0, background:'rgba(5,6,13,0.95)', borderBottom:'1px solid rgba(140,170,210,0.13)'}}>
            {DOSSIER_TABS.map((tab) => {
              const enabled = tab.activeWhen === 'always' || galaxyTickers.has(corpOverlayTicker);
              const active = dossierTab === tab.id;
              return (
                <button key={tab.id} disabled={!enabled} onClick={() => enabled && setDossierTab(tab.id)}
                  style={{
                    fontFamily:"'IBM Plex Mono', var(--font-mono, monospace)", fontSize:12, letterSpacing:'0.06em',
                    padding:'11px 20px', cursor: enabled ? 'pointer' : 'not-allowed', background:'transparent', border:'none',
                    color: active ? sectorAccent : (enabled ? '#8fa1b6' : '#475569'),
                    borderBottom: active ? '2px solid ' + sectorAccent : '2px solid transparent',
                    textShadow: active ? '0 0 12px ' + sectorAccent + '80' : 'none',
                  }}>
                  {tab.label}{enabled ? '' : ' · 준비중'}
                </button>
              );
            })}
          </div>
          {/* Body — 활성 탭 iframe(keep-alive display 토글) + 토글식 AI 사이드바 */}
          <div style={{flex:'1 1 0%', display:'flex', overflow:'hidden', position:'relative'}}>
            <div style={{flex:'1 1 0%', position:'relative', minWidth:0}}>
              {DOSSIER_TABS.map((tab) => {
                const enabled = tab.activeWhen === 'always' || galaxyTickers.has(corpOverlayTicker);
                if (!enabled) return null;
                const active = dossierTab === tab.id;
                return (
                  <iframe key={tab.id}
                    src={`../dossier/${tab.src}?ticker=${corpOverlayTicker}${tab.id === 'eqs' ? '&theme=galaxy' : ''}&accent=${encodeURIComponent(sectorAccent)}`}
                    title={`${tab.id}-${corpOverlayTicker}`}
                    style={{position:'absolute', inset:0, width:'100%', height:'100%', border:'none', background:'#020408', display: active ? 'block' : 'none'}}
                    onLoad={undefined /* firm.html은 ?theme=galaxy 자체 테마(스코프 CSS) */}
                  />
                );
              })}
            </div>
            {/* AI 토글 버튼 — 스크롤 무관 항시 표시(오버레이 크롬이라 iframe 내부 스크롤 영향 없음) */}
            <button onClick={() => setAiOpen((o) => !o)} title={aiOpen ? 'AI 어시스턴트 접기' : 'AI 어시스턴트 열기'}
              style={{
                position:'absolute', top:'50%', right: aiOpen ? '300px' : '0', transform:'translateY(-50%)',
                zIndex:12, writingMode:'vertical-rl', textOrientation:'mixed',
                background:'rgba(8,14,26,0.96)', border:'1px solid rgba(116, 238, 198,0.35)', borderRight:'none',
                color:'#74EEC6', fontFamily:"'IBM Plex Mono', var(--font-mono, monospace)", fontSize:11, letterSpacing:'0.14em',
                padding:'16px 7px', cursor:'pointer', borderRadius:'8px 0 0 8px',
                boxShadow:'0 0 18px rgba(116, 238, 198,0.14)', transition:'right .18s ease',
              }}>
              {aiOpen ? '접기 ▶' : '◀ AI 어시스턴트'}
            </button>
            {aiOpen && (
              <OverlayAiChat
                companyName={(window.__realData && window.__realData.nodeByCode && window.__realData.nodeByCode[corpOverlayTicker] && window.__realData.nodeByCode[corpOverlayTicker].n) || corpOverlayTicker}
                ticker={corpOverlayTicker}
                context={(DOSSIER_TABS.find((t) => t.id === dossierTab) || {}).context || 'finance'}
                node={(window.__realData && window.__realData.nodeByCode && window.__realData.nodeByCode[corpOverlayTicker]) || null}
              />
            )}
          </div>
          {/* Footer disclaimer */}
          <div style={{
            textAlign:'center', padding:'6px', fontFamily:'var(--font-mono,monospace)',
            fontSize:9, color:'#475569', borderTop:'1px solid rgba(116, 238, 198,0.1)',
            background:'rgba(8,14,26,0.9)', flexShrink:0,
          }}>
            ⚠ 과거 통계 기반 참고 정보 — 투자 조언 아님
          </div>
        </div>
      )}

      {discDetailItem && (
        <DisclosureDetailOverlay disc={discDetailItem} onClose={() => setDiscDetailItem(null)} />
      )}

      {discFullOverlayTicker && (
        <DisclosureFullOverlay ticker={discFullOverlayTicker} onClose={() => setDiscFullOverlayTicker(null)} />
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
