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

// ─── EgoView 데이터 헬퍼 (universe/PLAN.md §5 LOD-2 — ego/<ticker>.json governance 레이어) ──
// ego 원시 relation_type → 기존 REL_STYLES 키(시각 문법 U-D12 불변, allRelated와 동일 재사용).
const EGO_TYPE_MAP = {
  subsidiary: 'subsidiary', associate: 'associate', investment: 'significant',
  ftc_group: 'group', dart_filing: 'related', manual: 'manual',
};
const EGO_TYPE_PRIORITY = { subsidiary: 1, associate: 2, investment: 3, ftc_group: 4, dart_filing: 5, manual: 6 };

// 같은 이웃(t)에 다중 type 엣지가 있으면(예: investment+ftc_group) 하나로 병합 —
// allRelated의 hasGroup/hasEquity 이중 평행선 병합과 동일 패턴(bundle.jsx parseRelations 대응).
// U5(2026-07-29): 비상장·개인 이웃은 `t`(티커)가 없다 — ego 파일이 이름·kind를 자급한다.
// 키는 `u:<표기>`(앵커 안에서 고유, 이미 export가 중복 정리), code는 살아 있지만
// **companies_index에 없으므로 클릭 re-root 대상이 아니다**(selectNeighbor에서 차단).
const UNLISTED_KINDS = new Set(['private_corp', 'person', 'coop_fund', 'public_org']);
const UNLISTED_COLOR = '#5c6b80';   // --dim2 · 무채(신원 미상장) — 새 색 토큰 추가 없음
const UNLISTED_KIND_LABEL = { private_corp: '비상장법인', person: '개인',
                              coop_fund: '조합·펀드', public_org: '공공기관' };

// kind별 노드 형태 — 색이 아니라 형태로 유형을 가른다(색은 무채 고정).
function drawUnlistedNode(ctx, x, y, kind, r, color) {
  ctx.save();
  ctx.fillStyle = color; ctx.strokeStyle = color; ctx.lineWidth = 1.5;
  ctx.setLineDash([]);
  if (kind === 'person') {
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
  } else if (kind === 'coop_fund') {
    ctx.setLineDash([2.5, 2.5]);
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
  } else if (kind === 'public_org') {
    ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(x, y, r * 1.3, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, r * 0.55, 0, Math.PI * 2); ctx.stroke();
  } else {                       // private_corp (기본)
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

function mergeEgoNeighbors(rawList) {
  const byCode = new Map();
  for (const r of (rawList || [])) {
    const key = r.t || (r.kind ? 'u:' + r.n : null);
    if (!key) continue;
    if (!byCode.has(key)) {
      byCode.set(key, { code: key, name: r.n, sectorKo: r.s, tier: r.tier,
                        kind: r.kind || null, types: [], detailByType: {}, dirByType: {} });
    }
    const e = byCode.get(key);
    if (r.tier === 'named400') e.tier = 'named400';
    if (!e.types.includes(r.type)) e.types.push(r.type);
    e.detailByType[r.type] = r.detail;
    e.dirByType[r.type] = r.dir;
  }
  return Array.from(byCode.values()).map(e => {
    e.types.sort((a, b) => (EGO_TYPE_PRIORITY[a] || 9) - (EGO_TYPE_PRIORITY[b] || 9));
    const primary = e.types[0];
    // isIncoming은 반드시 primary(최우선) 타입의 dir로 — "처음 만난 엣지"의 dir을 쓰면
    // 삼성물산처럼 investment(in)+ftc_group(out) 혼재 시 JSON 순서에 따라 위/아래가
    // 뒤바뀌는 순서 종속이 생긴다(V-3 오라클 설계 중 발견). hasEquity면 primary는
    // 항상 지분 타입(우선순위 1~3 < 4~6)이라 UX-011 "지분 엣지의 출자 방향" 계약과 일치.
    return {
      code: e.code, name: e.name, sectorKo: e.sectorKo, tier: e.tier,
      kind: e.kind, isUnlisted: !!e.kind,
      isIncoming: e.dirByType[primary] === 'in',
      relType: EGO_TYPE_MAP[primary] || 'manual',
      hasGroup: e.types.includes('ftc_group'),
      hasEquity: e.types.some(t => t === 'subsidiary' || t === 'associate' || t === 'investment'),
      detail: e.detailByType[primary], rawType: primary,
    };
  });
}

// 랭킹: tier(named400 우선) → type 중요도 → 지분율(숫자 파싱 가능하면 큰 값 우선) — valuechain §5 D6 "tier→amount" 준용.
function rankEgoNeighbor(n) {
  // U5: 상장 우선 · 비상장 후순위 — TOP_N 컷에서 상장 이웃이 먼저 자리를 잡는다.
  const tierRank = n.isUnlisted ? 2 : (n.tier === 'named400' ? 0 : 1);
  const typeRank = EGO_TYPE_PRIORITY[n.rawType] || 9;
  const pct = parseFloat(n.detail);
  const amtRank = Number.isFinite(pct) ? -pct : 0;
  return [tierRank, typeRank, amtRank];
}
function cmpTuple(a, b) {
  for (let i = 0; i < a.length; i++) { if (a[i] !== b[i]) return a[i] - b[i]; }
  return 0;
}

// UX-011 축 재정의 — 세로축 = 위계 있음(지분), 가로축 = 위계 없음(순수 비지분).
//
//   기존엔 dir(in/out)만으로 위/아래를 갈랐는데, 계열사·특수관계자의 dir은 "DB에 어느
//   방향으로 기록됐나"일 뿐 위계가 아니다. 그걸 위에 두면 "지배한다"로 오독된다
//   (리더 지적: 삼성SDI 화면의 삼성화재해상보험).
//
//   규칙: 지분 엣지가 하나라도 있으면 세로축(위=출자 들어옴 / 아래=피출자).
//         계열·특수관계는 기존 이중 평행선으로 같은 엣지에 얹는다(현행 유지).
//         순수 비지분만인 상대만 가로축 — 좌=계열사, 우=특수관계자.
//   실측 근거: 순수 비지분 이웃은 2,651사 중 2,496사가 0개, 최대 10개 — 가로축 혼잡 없음.
//   지배기업 특수관계자 12건은 전부 지분 엣지를 동반해 자동으로 세로축에 남는다.
function splitEgoSides(governance, topN, sideN) {
  const merged = mergeEgoNeighbors(governance);
  const bySort = (arr) => arr.sort((a, b) => cmpTuple(rankEgoNeighbor(a), rankEgoNeighbor(b)));
  const vertical = merged.filter(n => n.hasEquity);
  const horizontal = merged.filter(n => !n.hasEquity);
  const above = bySort(vertical.filter(n => n.isIncoming));
  const below = bySort(vertical.filter(n => !n.isIncoming));
  // 좌=계열사(파선) / 우=특수관계자(점선). 둘 다 아닌 잔여(manual 등)는 우측에 붙인다.
  const left = bySort(horizontal.filter(n => n.relType === 'group'));
  const right = bySort(horizontal.filter(n => n.relType !== 'group'));
  const cut = (arr, n) => ({ shown: arr.slice(0, n), rest: arr.slice(n) });
  return {
    above: cut(above, topN), below: cut(below, topN),
    left: cut(left, sideN), right: cut(right, sideN),
  };
}
// ─── 밸류체인 레이어 (U3, U-D14·UX-013) ─────────────────────────────────────
// 문법 축 분리: 색=흐름 단일색(은백 — 관계 6색·시맨틱 6색·섹터 25색 어느 축과도 미충돌,
// integration 배정), 선 스타일=신뢰등급(T1/T2/T3), 화살촉=오픈 셰브런(물자 흐름 위→아래).
const VC_FLOW_COLOR = '#e8f1ff';
const VC_TIER_STYLES = {
  T1: { alpha: 'dd', width: 2,   dash: [],     label: 'T1 · 정형 공시' },
  T2: { alpha: '77', width: 1.5, dash: [],     label: 'T2 · 서술 추출' },
  T3: { alpha: '66', width: 1.2, dash: [3, 4], label: 'T3 · 산업연관표' },
};
const _TIER_RANK = { T1: 1, T2: 2, T3: 3 };

function fmtVcAmount(v) {
  if (v == null || !isFinite(v)) return '';
  if (v >= 1e12) return (v / 1e12).toFixed(1) + '조';
  if (v >= 1e8) return Math.round(v / 1e8).toLocaleString() + '억';
  return Math.round(v / 1e4).toLocaleString() + '만';
}

// UX-013: 상/하는 up/down 배열 소속이 아니라 type에서 파생 — 배열은 미러 기록이라
// (실측: up/down 완전 대칭 1,378/1,378·143/143) 신호가 아니다. supply(상대가 공급자)=위,
// customer(상대가 고객)=아래. 같은 (상대,type) 다연도 엣지는 최신 as_of로 병합.
function splitVcSides(vc, topN, opts) {
  const _idxV = (window.__realData && window.__realData.indexByCode) || {};
  const byKey = new Map();
  for (const side of ['up', 'down']) {
    for (const e of (vc && vc[side]) || []) {
      if (!e.t) continue;
      const key = e.t + ':' + e.type;
      const prev = byKey.get(key);
      if (!prev || (e.as_of || 0) > (prev.as_of || 0)) {
        byKey.set(key, { code: e.t, name: e.n, type: e.type,
                         sectorKo: (_idxV[e.t] || {}).s || null,  // 노드색=섹터색 유지(엣지 문법만 교체)
                         tier: e.tier_grade || 'T1', amount: e.amount, as_of: e.as_of, prov: e.prov });
      }
    }
  }
  const rank = (n) => [_TIER_RANK[n.tier] || 9, -(n.amount || 0), -(n.as_of || 0)];
  const bySort = (arr) => arr.sort((a, b) => cmpTuple(rank(a), rank(b)));
  const above = bySort([...byKey.values()].filter(n => n.type === 'supply'));
  const below = bySort([...byKey.values()].filter(n => n.type !== 'supply'));
  if (opts && opts.grouped) {
    // UX-015 산업군 묶음 모드 — shown = 그룹에 실제로 표시되는 기업 전부
    const pack = (arr) => {
      const g = groupVcSide(arr, VC_MAX_GROUPS, VC_MAX_PER_GROUP);
      const shown = g.groups.flatMap(x => x.items);
      const hidden = g.groups.reduce((a, x) => a + x.hidden, 0);
      return { shown, rest: [...g.restItems], groups: g.groups,
               restGroupCount: g.restGroupCount, hiddenInGroups: hidden };
    };
    const A = pack(above), B = pack(below);
    // UX-019: 양쪽에 공통으로 나오는 섹터는 같은 상대 순서 — 공급처의 플랫폼이 왼쪽
    // 1번이면 고객사의 플랫폼도 왼쪽 1번(세로 비교가 쉬워짐). 그룹 "선정"은 랭킹
    // 그대로, "표시 순서"만 공급처 순서를 기준으로 재배열.
    const aOrder = A.groups.map(g => g.sectorKo);
    B.groups.sort((x, y) => {
      const xi = aOrder.indexOf(x.sectorKo), yi = aOrder.indexOf(y.sectorKo);
      if (xi >= 0 && yi >= 0) return xi - yi;
      if (xi >= 0) return -1;
      if (yi >= 0) return 1;
      return 0;   // 둘 다 공급처에 없으면 원래 랭킹 순 유지(안정 정렬)
    });
    return { above: A, below: B };
  }
  const cut = (arr) => ({ shown: arr.slice(0, topN), rest: arr.slice(topN) });
  return { above: cut(above), below: cut(below) };
}

// UX-015: 밸류체인은 기업 나열이 아니라 **산업군 묶음**으로 읽는다 — "어느 산업에서 사와서
// 어느 산업에 파는가". 랭킹 순서를 유지한 채 섹터로 접고(그룹 순서 = 최상위 멤버 순위),
// 그룹 캡 5 · 그룹당 4를 넘으면 각각 묶음으로. 실측: 산업 수 위 최대 7·아래 최대 11·중앙값 1.
const VC_MAX_GROUPS = 5;
const VC_MAX_PER_GROUP = 4;

function groupVcSide(items, maxGroups, maxPerGroup) {
  const order = [];
  const byKo = new Map();
  for (const it of items) {           // items는 이미 rank 정렬됨
    const ko = it.sectorKo || '기타';
    if (!byKo.has(ko)) { byKo.set(ko, []); order.push(ko); }
    byKo.get(ko).push(it);
  }
  const groups = order.slice(0, maxGroups).map(ko => {
    const all = byKo.get(ko);
    const pal = (window.SECTOR_PALETTE || []).find(s => s.ko === ko);
    return { sectorKo: ko, color: (pal && pal.color) || VC_FLOW_COLOR,
             items: all.slice(0, maxPerGroup), hidden: Math.max(0, all.length - maxPerGroup),
             hiddenItems: all.slice(maxPerGroup),   // UX-022: 그룹 내 초과분 — "+N사" 노드·팝업용
             count: all.length,
             amount: all.reduce((a, b) => a + (b.amount || 0), 0) };
  });
  const restKos = order.slice(maxGroups);
  const restItems = restKos.flatMap(ko => byKo.get(ko));
  return { groups, restGroupCount: restKos.length, restItems };
}

window.mergeEgoNeighbors = mergeEgoNeighbors;
window.splitEgoSides = splitEgoSides;   // V-3 렌더 하네스가 페이지 내 분할 로직을 직접 조회
window.splitVcSides = splitVcSides;
window.groupVcSide = groupVcSide;

// ─── Sector map: companies as glowing nodes inside the chosen sector ────
const { useRef: _useRef, useEffect: _useEffect, useState: _useState, useMemo: _useMemo } = React;

function SectorMap({ sectorId, activeMarket, activeCompanyCode, onSelectMarket, onSelectCompany, onSelectGhost }) {
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
  const dotsScreenRef = _useRef([]);     // UX-009: dot 화면 좌표+신원 [{x,y,r,t,n}] — hover/클릭 히트테스트
  const [hoverDot, setHoverDot] = _useState(null);  // {x,y,n} — DOM 툴팁 (⚠ effect deps에 넣지 말 것, DESIGN §9-1)

  const sec = SECTOR_PALETTE.find(s => s.id === sectorId) || SECTOR_PALETTE[0];

  // U2 드릴인 LOD: sectorMarketData가 있으면 모드별 레이아웃 계산
  //   - 개요(시장 미선택): KOSPI/KOSDAQ 성운 프록시 2노드 + 양쪽 dots
  //   - 드릴인(시장 선택): 그 시장 상위 ~10 named 중앙 배치 + 나머지 dots
  // 없으면(top50 fallback) 기존 COMPANIES/dots 단일 클러스터.
  const _md = (window.__realData && window.__realData.sectorMarketData && window.__realData.sectorMarketData[sectorId]) || null;
  const MARKET_CAP = 10;

  // FN-008: 활성 기업이 있으면 그 기업의 시장이 곧 렌더 시장 — ghost 진입·딥링크로
  // activeMarket이 리셋/불일치여도 개요 모드(프록시 노드)로 떨어지지 않게 방어.
  const _idx = (window.__realData && window.__realData.indexByCode) || {};
  const effectiveMarket = activeMarket ||
    (activeCompanyCode && _idx[activeCompanyCode] && _idx[activeCompanyCode].mkt) || null;

  const { layout, dotsData } = _useMemo(() => {
    const srng = (seed) => { let s = ((seed * 9301 + 49297) % 233280 + 233280) % 233280; return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; }; };
    // dots 항목: [x, y, capBucket, ticker, name] — UX-009 hover 툴팁·클릭 진입용 신원 보존
    const scatter = (cx, cy, r, seed, items) => {
      const rng = srng(seed), o = [];
      for (let i = 0; i < items.length; i++) {
        const a = rng() * Math.PI * 2, rr = r * Math.sqrt(rng());
        const it = items[i] || {};
        o.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, it.cb || 0, it.t || null, it.n || null]);
      }
      return o;
    };
    const phyllo = (items, cx, cy, r) => items.map((m, i) => {
      if (i === 0) return { ...m, x: cx, y: cy, gx: cx, gy: cy };
      const ang = i * 2.39996, rr = r * (0.34 + ((i - 1) / Math.max(1, items.length - 1)) * 0.62);
      const gx = cx + Math.cos(ang) * rr, gy = cy + Math.sin(ang) * rr;
      return { ...m, x: gx, y: gy, gx, gy };
    });
    // UX-007: 구(노드) 겹침 해소 — 노드 반경(draw와 동일 공식)을 정규 좌표로 환산해
    // 겹치는 쌍을 서로 밀어내는 완화(relaxation) 패스. 결정적(난수 없음).
    const relax = (nodes, baseRpx) => {
      const rn = nodes.map(n => (Math.min(40, 6 + Math.sqrt(n.cap || 10) * 1.5) * 1.6) / baseRpx);
      for (let iter = 0; iter < 40; iter++) {
        let moved = false;
        for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.gx - a.gx, dy = b.gy - a.gy;
          const d = Math.sqrt(dx * dx + dy * dy) || 0.0001;
          const min = rn[i] + rn[j];
          if (d < min) {
            const push = (min - d) / 2, ux = dx / d, uy = dy / d;
            a.gx -= ux * push; a.gy -= uy * push;
            b.gx += ux * push; b.gy += uy * push;
            moved = true;
          }
        }
        if (!moved) break;
      }
      for (const n of nodes) { n.x = n.gx; n.y = n.gy; }
      return nodes;
    };

    if (!_md) {
      const comp = COMPANIES[sectorId] || COMPANIES.semi || [];
      const dd = (window.__realData && window.__realData.dots && window.__realData.dots[sectorId]) || [];
      return { layout: comp.map(c => ({ ...c, gx: c.x, gy: c.y })), dotsData: dd };
    }
    if (!effectiveMarket) {
      // 개요: 두 성운 프록시 노드(클릭 시 드릴인) + 양쪽 dots 성운
      const nodes = [], dots = [];
      const specs = [{ M: 'KOSPI', cx: -0.85, seed: 11 }, { M: 'KOSDAQ', cx: 0.85, seed: 22 }];
      for (const sp of specs) {
        const m = _md[sp.M]; if (!m) continue;
        nodes.push({ code: '__mkt_' + sp.M, name: sp.M, en: sp.M, isMarket: true, market: sp.M, count: m.total,
                     cap: Math.min(90, 26 + m.total * 0.16), x: sp.cx, y: 0, gx: sp.cx, gy: 0 });
        const items = [...m.dotItems, ...m.named.map(c => ({ cb: 1, t: c.code, n: c.name }))];
        dots.push(...scatter(sp.cx, 0, 0.42, sp.seed, items));
      }
      return { layout: nodes, dotsData: dots };
    }
    // 드릴인: 단일 시장 중앙, 상위 ~10 named + 나머지 dots
    const m = _md[effectiveMarket] || { named: [], dotItems: [] };
    const shown = m.named.slice(0, MARKET_CAP).map(c => ({ code: c.code, name: c.name, en: c.name, cap: c.cap, market: c.market }));
    // FN-008: 활성 기업이 top-N 밖(dot 기업·캡 초과 named)이면 노드로 승격해 중앙에 표시
    if (activeCompanyCode && !shown.some(c => c.code === activeCompanyCode)) {
      const over = m.named.find(c => c.code === activeCompanyCode);
      const di = _idx[activeCompanyCode];
      if (over) shown.push({ code: over.code, name: over.name, en: over.name, cap: over.cap, market: over.market });
      else if (di) shown.push({ code: activeCompanyCode, name: di.n, en: di.n, cap: Math.max(2, (di.cb || 0) * 6 + 2), market: di.mkt });
    }
    const named = relax(phyllo(shown, 0, 0, 0.72), Math.min(window.innerWidth || 1200, window.innerHeight || 740) * 0.34);
    const restItems = [...m.dotItems, ...m.named.slice(MARKET_CAP).map(c => ({ cb: 1, t: c.code, n: c.name }))]
      .filter(it => it.t !== activeCompanyCode);
    const dots = scatter(0, 0, 0.9, effectiveMarket === 'KOSPI' ? 31 : 32, restItems);
    return { layout: named, dotsData: dots };
  }, [_md, sectorId, effectiveMarket, activeCompanyCode]);

  const companies = layout;

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
      const dots = dotsData || [];
      dotsScreenRef.current = [];
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
        // UX-009: 신원 있는 dot만 히트테스트 대상으로 등록
        if (d[3]) dotsScreenRef.current.push({ x: px, y: py, r, t: d[3], n: d[4] || d[3] });
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

      // U2 성운 헤일로 + 라벨 (드릴인 LOD).
      //  개요: KOSPI(좌)/KOSDAQ(우) 두 성운 헤일로 + "KOSPI · N사" 라벨(클릭 유도).
      //  드릴인: 해당 시장 단일 중앙 헤일로.
      if (_md) {
        const baseRh = Math.min(w, h) * 0.34;
        const cyN = h / 2;
        const drawHalo = (cxN, R) => {
          ctx.save();
          ctx.globalCompositeOperation = 'screen';
          const g = ctx.createRadialGradient(cxN, cyN, 0, cxN, cyN, R);
          g.addColorStop(0, sec.color + '16');
          g.addColorStop(0.6, sec.color + '0a');
          g.addColorStop(1, sec.color + '00');
          ctx.fillStyle = g;
          ctx.beginPath(); ctx.arc(cxN, cyN, R, 0, Math.PI * 2); ctx.fill();
          ctx.restore();
        };
        if (!effectiveMarket) {
          const specs = [
            { key: 'KOSPI',  cxN: w / 2 + (-0.85) * baseRh, total: (_md.KOSPI && _md.KOSPI.total) || 0 },
            { key: 'KOSDAQ', cxN: w / 2 + (0.85) * baseRh,  total: (_md.KOSDAQ && _md.KOSDAQ.total) || 0 },
          ];
          for (const nb of specs) {
            drawHalo(nb.cxN, baseRh * 0.6);
            ctx.save();
            ctx.textAlign = 'center';
            ctx.font = '600 13px "IBM Plex Mono", ui-monospace, monospace';
            ctx.fillStyle = sec.color + 'dd';
            ctx.fillText(nb.key, nb.cxN, cyN - baseRh * 0.72);
            ctx.fillStyle = 'rgba(143,161,182,0.85)';
            ctx.font = '400 11px "IBM Plex Mono", ui-monospace, monospace';
            ctx.fillText(nb.total + '사 · 클릭', nb.cxN, cyN - baseRh * 0.72 + 16);
            ctx.restore();
          }
        } else {
          drawHalo(w / 2, baseRh * 0.95);
        }
      }

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
      // UX-009: named/관계 노드 히트가 없으면 배경 dot 히트테스트 → 이름 툴팁
      let dotHit = null;
      if (!best) {
        let dBest = 9;  // 최소 9px 히트 반경 (작은 dot도 잡히게)
        for (const d of dotsScreenRef.current) {
          const dist = Math.hypot(d.x - mx, d.y - my);
          if (dist < Math.max(9, d.r * 3) && dist < dBest + d.r * 3) { dBest = dist; dotHit = d; }
        }
      }
      setHoverDot(dotHit ? { x: dotHit.x, y: dotHit.y, n: dotHit.n } : null);
      cvs.style.cursor = (best || dotHit) ? 'pointer' : 'default';
    };
    const onClick = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      // 개요 모드: 성운 프록시 노드는 히트 반경을 크게(덩이 전체) 잡아 드릴인.
      let best = null, bestD = 28;
      for (const p of nodesRef.current) {
        const hitR = p.c.isMarket ? 90 : 28;
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < hitR && d < bestD + (p.c.isMarket ? 70 : 0)) { bestD = d; best = { node: p.c, isRelated: false }; }
      }
      for (const p of relatedNodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < Math.min(bestD, 22)) { bestD = d; best = { node: { code: p.code }, isRelated: true, sectorId: p.sectorId }; }
      }
      if (best) {
        if (best.node.isMarket) onSelectMarket?.(best.node.market);
        else if (best.isRelated) onSelectGhost?.(best.node.code, best.sectorId);
        else onSelectCompany?.(best.node.code);
        return;
      }
      // UX-009: 배경 dot 클릭 → 그 기업으로 진입 (개요·드릴인 양쪽)
      let dotHit = null, dBest = 9;
      for (const d of dotsScreenRef.current) {
        const dist = Math.hypot(d.x - mx, d.y - my);
        if (dist < Math.max(9, d.r * 3) && dist < dBest + d.r * 3) { dBest = dist; dotHit = d; }
      }
      if (dotHit) { onSelectCompany?.(dotHit.t); return; }
      if (effectiveMarket) {
        onSelectCompany?.(null); // 드릴인에서 빈 곳 클릭 → 기업 선택 해제
      }
    };
    const onLeave = () => { setHoverDot(null); hoverRef.current = null; setHoverCode(null); cvs.style.cursor = 'default'; };
    cvs.addEventListener('mousemove', onMove);
    cvs.addEventListener('click', onClick);
    cvs.addEventListener('mouseleave', onLeave);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      cvs.removeEventListener('mousemove', onMove);
      cvs.removeEventListener('click', onClick);
      cvs.removeEventListener('mouseleave', onLeave);
    };
  }, [layout, dotsData, allRelated, activeCompanyCode, effectiveMarket, sectorId]);

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
        {/* UX-009: 배경 dot hover 이름 툴팁 */}
        {hoverDot && (
          <div className="company-label" style={{ left: hoverDot.x, top: hoverDot.y - 16, color: sec.color }}>
            <div className="company-label-name">{hoverDot.n}</div>
          </div>
        )}
      </div>
    </div>
  );
}

window.SectorMap = SectorMap;

// ─── EgoView (③ 셸, universe/PLAN.md §5 LOD-2) ──────────────────────────────
// 앵커 기업 중앙 고정 + ego/<ticker>.json governance 1-hop 재구성 뷰.
// 상(dir=in·출자 들어옴) / 하(dir=out·피출자·나감) 배치 — valuechain §5 D5 상/하 문법을
// 지배구조 의미로 재사용(U2 진행 시나리오). 사이드당 Top-N 6 + "외 n사" 묶음 노드(D6).
// 시각 문법(REL_STYLES 색·이중 평행선·화살표=출자 방향)은 allRelated와 동일 — U-D12 불변.
function EgoView({ anchor, chain, layer, onLayerChange, onReRoot, onChainJump }) {
  const canvasRef = _useRef(null);
  const rafRef = _useRef(0);
  const startRef = _useRef(performance.now());
  const sizeRef = _useRef({ w: 0, h: 0, dpr: 1 });
  const bgStarsRef = _useRef([]);
  const hitRef = _useRef([]);
  const [hoverCode, setHoverCode] = _useState(null);
  const [overflowSide, setOverflowSide] = _useState(null); // 'above' | 'below' | null
  const [unlistedInfo, setUnlistedInfo] = _useState(null); // U5: 비상장 노드 정보 팝오버

  const TOP_N = 6;    // 세로(지분) 사이드당
  const SIDE_N = 4;   // 가로(비지분) 사이드당 — 실측상 대부분 0~2개
  const sec = (window.SECTOR_PALETTE || []).find(s => s.ko === anchor.s) || (window.SECTOR_PALETTE || [])[0] || { color: '#74EEC6' };

  // U3: 밸류체인 레이어 — 데이터가 있는 기업만 활성(현재 T1 509사). hasVc가 false면
  // layer state가 'valuechain'이어도 지배구조로 렌더(re-root로 무데이터 기업 이동 시 안전).
  const vcData = (anchor.layers && anchor.layers.valuechain) || null;
  const hasVc = !!(vcData && (((vcData.up || []).length) || ((vcData.down || []).length)));
  const isVc = layer === 'valuechain' && hasVc;

  const { above, below, left, right } = _useMemo(() => {
    if (isVc) {
      const s = splitVcSides(vcData, TOP_N, { grouped: true });
      // 밸류체인은 상하(흐름)만 — 가로축 없음(U-D14 문법 축 분리)
      return { above: s.above, below: s.below,
               left: { shown: [], rest: [] }, right: { shown: [], rest: [] } };
    }
    return splitEgoSides((anchor.layers && anchor.layers.governance) || [], TOP_N, SIDE_N);
  }, [anchor, isVc]);

  // UX-015 레일 레이아웃 — 그룹(산업군)을 x축에 분배, 그룹 안에서 기업을 다시 분배.
  //   sign<0: 공급처(위) / sign>0: 고객사(아래).  라벨=최외곽 · 기업=중간 · 레일=앵커쪽.
  // 레일(앵커쪽) → 산업 라벨 → 기업 세로 스택(바깥). 그룹 내 기업을 수평으로 뿌리면
  // 세그먼트 폭에 이름이 안 들어가 라벨이 뭉갠다(실측) — 세로 1행 1사로 고정.
  // UX-019: 스파인·노드·라벨 전부 세그먼트 "중앙" 정렬 + 좌우 폭 확대(HALF 0.88→1.22).
  const VC_RAIL_Y = 0.34, VC_LABEL_Y = 0.46, VC_NODE_Y = 0.60, VC_ROW_GAP = 0.115, VC_HALF = 1.22;
  const VC_SEG_MAX = 0.50;  // 세그먼트 폭 상한 — 그룹 1~2개일 때 화면 전체로 퍼져
                            // 스파인·노드가 중심에서 밀려나는 버그 방지(그룹들을 중앙 정렬)
  const buildVcSide = (side, sign) => {
    const gs = side.groups || [];
    const withBundleG = gs.length + ((side.restGroupCount || 0) > 0 ? 1 : 0);
    if (!withBundleG) return { nodes: [], groups: [] };
    const segW = Math.min(VC_SEG_MAX, (2 * VC_HALF) / withBundleG);
    const totalW = segW * withBundleG;
    const nodes = [], groups = [];
    for (let gi = 0; gi < withBundleG; gi++) {
      const cxg = -totalW / 2 + segW * (gi + 0.5);
      const isRestGroup = gi >= gs.length;
      if (isRestGroup) {
        groups.push({ cx: cxg, label: '외 ' + side.restGroupCount + '개 산업',
                      color: '#94a3b8', sign, isRest: true, count: side.rest.length,
                      segHalf: segW / 2 });
        nodes.push({ isBundle: true, side: sign < 0 ? 'above' : 'below', rest: side.rest,
                     code: '__bundle_vc_' + (sign < 0 ? 'above' : 'below'),
                     gx: cxg, gy: sign * VC_NODE_Y });
        continue;
      }
      const g = gs[gi];
      const extraRow = g.hidden > 0 ? 1 : 0;
      groups.push({ cx: cxg, label: g.sectorKo, color: g.color, sign,
                    count: g.count, hidden: g.hidden, amount: g.amount,
                    segHalf: segW / 2, rows: g.items.length + extraRow });
      // 세로 스택 — 노드·스파인 = 세그먼트 중앙, 이름은 노드 오른쪽
      g.items.forEach((it, i) => {
        nodes.push({ ...it, gx: cxg, gy: sign * (VC_NODE_Y + i * VC_ROW_GAP),
                     isVcNode: true, groupIdx: gi, labelRight: true, segW });
      });
      // UX-022: 그룹당 4사 초과분 = 스택 맨 아래 같은 섹터색 "+N사" 노드 (클릭 → 팝업)
      if (g.hidden > 0) {
        nodes.push({ isBundle: true, isGroupBundle: true, bundleColor: g.color,
                     rest: g.hiddenItems, restLabel: '+' + g.hidden + '사',
                     customTitle: g.sectorKo + ' ' + (sign < 0 ? '공급처' : '고객사'),
                     code: '__gb_' + (sign < 0 ? 'a' : 'b') + '_' + gi,
                     gx: cxg, gy: sign * (VC_NODE_Y + g.items.length * VC_ROW_GAP), segW });
      }
    }
    return { nodes, groups };
  };
  const vcAbove = _useMemo(() => (isVc ? buildVcSide(above, -1) : { nodes: [], groups: [] }), [isVc, above]);
  const vcBelow = _useMemo(() => (isVc ? buildVcSide(below, 1) : { nodes: [], groups: [] }), [isVc, below]);

  // 세로 사이드: 가로로 펼친 행. 가로 사이드: 앵커 높이 좌우로 세로 살짝 퍼진 열.
  const layoutRow = (items, y) => {
    const n = items.length;
    if (!n) return [];
    if (n === 1) return [{ ...items[0], gx: 0, gy: y }];
    const span = 0.82;
    return items.map((it, i) => ({ ...it, gx: -span + (2 * span) * (i / (n - 1)), gy: y }));
  };
  const layoutCol = (items, x) => {
    const n = items.length;
    if (!n) return [];
    if (n === 1) return [{ ...items[0], gx: x, gy: 0, isSide: true }];
    const span = 0.3;
    return items.map((it, i) => ({ ...it, gx: x, gy: -span + (2 * span) * (i / (n - 1)), isSide: true }));
  };
  const withBundle = (side, key) => {
    const items = side.shown.slice();
    if (side.rest.length) items.push({ isBundle: true, side: key, rest: side.rest, code: '__bundle_' + key });
    return items;
  };
  const aboveNodes = _useMemo(() => layoutRow(withBundle(above, 'above'), -0.62), [above]);
  const belowNodes = _useMemo(() => layoutRow(withBundle(below, 'below'), 0.62), [below]);
  const leftNodes  = _useMemo(() => layoutCol(withBundle(left, 'left'), -0.86), [left]);
  const rightNodes = _useMemo(() => layoutCol(withBundle(right, 'right'), 0.86), [right]);
  const allNodes = _useMemo(
    () => (isVc ? [...vcAbove.nodes, ...vcBelow.nodes]
                : [...aboveNodes, ...belowNodes, ...leftNodes, ...rightNodes]),
    [isVc, vcAbove, vcBelow, aboveNodes, belowNodes, leftNodes, rightNodes]
  );

  // V-3 렌더 하네스 훅 — 화면이 실제 채택한 분할 상태를 기계 검증용으로 노출(무해·읽기 전용).
  _useEffect(() => {
    window.__egoDebug = {
      anchor: anchor.t,
      layer: isVc ? 'valuechain' : 'governance', hasVc,
      above: above.shown.map(n => n.code), aboveRest: above.rest.length,
      below: below.shown.map(n => n.code), belowRest: below.rest.length,
      left:  left.shown.map(n => n.code),  leftRest:  left.rest.length,
      right: right.shown.map(n => n.code), rightRest: right.rest.length,
      // UX-015 산업군 묶음 상태 (VC 전용)
      vcGroups: isVc ? {
        above: (above.groups || []).map(g => ({ ko: g.sectorKo, n: g.count, shown: g.items.length })),
        below: (below.groups || []).map(g => ({ ko: g.sectorKo, n: g.count, shown: g.items.length })),
        aboveRestGroups: above.restGroupCount || 0,
        belowRestGroups: below.restGroupCount || 0,
      } : null,
    };
  }, [anchor, isVc, hasVc, above, below, left, right]);

  _useEffect(() => {
    const cvs = canvasRef.current;
    const ctx = cvs.getContext('2d');
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = cvs.clientWidth, h = cvs.clientHeight;
      cvs.width = w * dpr; cvs.height = h * dpr;
      sizeRef.current = { w, h, dpr };
      bgStarsRef.current = window.__galaxyHelpers.buildBgStars(53, w, h, 700);
    };
    resize();
    window.addEventListener('resize', resize);

    const animPos = allNodes.map(n => ({ x: n.gx, y: n.gy }));

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

    // UX-017: 라벨이 세그먼트 폭을 넘어 이웃과 붙지 않게 — 측정 후 문자 단위 축약
    function clipText(text, maxW) {
      if (ctx.measureText(text).width <= maxW) return text;
      let s = String(text);
      while (s.length > 1 && ctx.measureText(s + '…').width > maxW) s = s.slice(0, -1);
      return s + '…';
    }
    // UX-019: 잘라내기 전에 폰트를 줄여서 전부 보이게 — 안 들어가면 px를 낮추고,
    // 최소 크기에서도 초과할 때만 축약. 반환값은 실제 적용된 font 문자열.
    function fitText(text, maxW, px, minPx, weight, family) {
      for (let p = px; p >= minPx; p -= 0.5) {
        ctx.font = `${weight} ${p}px ${family}`;
        if (ctx.measureText(text).width <= maxW) return { text, font: ctx.font };
      }
      ctx.font = `${weight} ${minPx}px ${family}`;
      return { text: clipText(text, maxW), font: ctx.font };
    }

    // (구 drawChevron은 UX-023에서 폐기 — 화살촉은 지배구조와 동일한 drawArrowHead로 통일)

    const draw = () => {
      if (window.__dossierOpen) { rafRef.current = requestAnimationFrame(draw); return; }
      const { w, h, dpr } = sizeRef.current;
      const t = (performance.now() - startRef.current) / 1000;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const bg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.85);
      bg.addColorStop(0, '#0a0e1c'); bg.addColorStop(0.5, '#04060e'); bg.addColorStop(1, '#000003');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);

      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      const tint = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.5);
      tint.addColorStop(0, sec.color + '22'); tint.addColorStop(1, sec.color + '00');
      ctx.fillStyle = tint; ctx.fillRect(0, 0, w, h);
      ctx.restore();

      for (const s of bgStarsRef.current) {
        const tw = 0.6 + Math.sin(t * s.tf + s.phase) * 0.4;
        ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${s.alpha * tw})`;
        ctx.fillRect(s.x, s.y, s.size, s.size);
      }

      allNodes.forEach((n, i) => {
        animPos[i].x += (n.gx - animPos[i].x) * 0.09;
        animPos[i].y += (n.gy - animPos[i].y) * 0.09;
      });

      const cx = w / 2, cy = h / 2;
      const baseR = Math.min(w, h) * 0.36;
      const anchorR = Math.min(44, 10 + Math.sqrt(30) * 1.5);
      const haloR = anchorR * 1.4;
      const EQUITY = new Set(['subsidiary', 'associate', 'significant']);
      const hits = [{ x: cx, y: cy, r: anchorR, isAnchor: true }];

      // UX-015 밸류체인 레일: 앵커 ↔ 레일 트렁크 + 산업군 세그먼트 + 그룹 드롭.
      // (기업마다 앵커까지 선을 뽑지 않는다 — 산업 단위로 읽히게)
      if (isVc) {
        const drawRailSide = (sideObj, sign, trunkLabel) => {
          if (!sideObj.groups.length) return;
          const railY = cy + sign * VC_RAIL_Y * baseR;
          const ts0 = VC_TIER_STYLES.T1;
          // UX-017: 골격(트렁크+레일) = 앵커 섹터색 — "삼성전자의 공급처·고객사 연결선은
          // 반도체 색". 산업별 색은 스파인이 맡는다.
          // UX-023: 라벨은 트렁크 "중심"에 — 라벨 구간만 선을 끊어(갭) 글자가 선에 안 묻히게.
          //         화살촉은 지배구조와 동일한 채운 삼각형(셰브런 폐기 — 레이어 구분은
          //         토글·전용 범례·색 문법이 이미 담당).
          const skel = sec.color;
          const midY = (cy + sign * haloR + railY) / 2;
          const yTop = Math.min(cy + sign * haloR, railY), yBot = Math.max(cy + sign * haloR, railY);
          ctx.strokeStyle = skel + 'cc'; ctx.lineWidth = 2; ctx.setLineDash([]);
          ctx.beginPath();
          ctx.moveTo(cx, yTop); ctx.lineTo(cx, midY - 11);
          ctx.moveTo(cx, midY + 11); ctx.lineTo(cx, yBot);
          ctx.stroke();
          if (sign < 0) drawArrowHead(cx, railY, cx, cy - haloR, skel + 'ee', 14);
          else drawArrowHead(cx, cy + haloR, cx, railY, skel + 'ee', 14);
          ctx.save();
          ctx.font = '600 11px "IBM Plex Mono", ui-monospace, monospace';
          ctx.textAlign = 'center'; ctx.fillStyle = skel + 'ee';
          ctx.fillText(trunkLabel, cx, midY + 4);
          ctx.restore();
          // 레일 본선 — 앵커 섹터색 한 줄. 범위는 스파인·묶음 x + 트렁크 x(cx)의 min~max
          // (UX-018: 그룹 1개면 스파인 min==max라 레일이 사라져 트렁크와 끊겨 보였음 — KCC건설).
          const spineXs = sideObj.groups.map(g => cx + g.cx * baseR);  // UX-019: 스파인=세그 중앙
          const railX0 = Math.min(...spineXs, cx), railX1 = Math.max(...spineXs, cx);
          ctx.strokeStyle = skel + 'bb'; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(railX0, railY); ctx.lineTo(railX1, railY); ctx.stroke();
          // 그룹별 드롭 + 세그먼트 캡 + 산업 라벨
          sideObj.groups.forEach((g) => {
            const gx = cx + g.cx * baseR;
            const lastRowY = cy + sign * (VC_NODE_Y + Math.max(0, (g.rows || 1) - 1) * VC_ROW_GAP) * baseR;
            // 레일 → 그룹 마지막 행까지 수직 스파인(세그 중앙, UX-019) — 섹터색 뚜렷하게
            ctx.strokeStyle = (g.isRest ? '#94a3b8' : g.color) + (g.isRest ? '88' : 'aa');
            ctx.lineWidth = g.isRest ? 1 : 1.4;
            ctx.setLineDash(g.isRest ? [2, 3] : []);
            ctx.beginPath(); ctx.moveTo(gx, railY); ctx.lineTo(gx, lastRowY); ctx.stroke();
            ctx.setLineDash([]);
            // 산업 라벨(레일 바로 바깥) + 집계 — 세그 중앙 정렬, 폰트 자동 축소로 전부 표시(UX-019)
            const ly = cy + sign * VC_LABEL_Y * baseR;
            ctx.textAlign = 'center';
            const maxW = Math.max(30, (g.segHalf || 0.2) * 2 * baseR - 8);
            const lab = fitText(g.label, maxW, 11, 8.5, '600', '"IBM Plex Mono", ui-monospace, monospace');
            ctx.fillStyle = (g.isRest ? '#94a3b8' : g.color) + 'ee';
            ctx.font = lab.font;
            ctx.fillText(lab.text, gx, ly);
            const sub = g.isRest ? (g.count + '사')
              : (g.count + '사' + (g.amount ? '·' + fmtVcAmount(g.amount) : ''));
            const subFit = fitText(sub, maxW, 9, 8, '400', 'sans-serif');
            ctx.fillStyle = '#64748b'; ctx.font = subFit.font;
            ctx.fillText(subFit.text, gx, ly + 11);
          });
        };
        drawRailSide(vcAbove, -1, '공급처');
        drawRailSide(vcBelow, 1, '고객사');
      }

      // 관계선 + 화살표 (묶음 노드는 신원 없는 얇은 점선만)
      allNodes.forEach((n, i) => {
        if (isVc) return;   // VC는 위 레일이 대신함
        const nx = cx + animPos[i].x * baseR, ny = cy + animPos[i].y * baseR;
        if (n.isBundle) {
          ctx.strokeStyle = 'rgba(148,163,184,0.35)';
          ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
          ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(nx, ny); ctx.stroke();
          ctx.setLineDash([]);
          return;
        }
        // (구 방사형 VC 엣지 경로는 UX-015 레일 전환으로 제거 — 레일은 위 drawRailSide가 전담)
        const style = REL_STYLES[n.relType] || REL_STYLES.manual;
        const isEquity = EQUITY.has(n.relType);
        // U5: 비상장 상대는 **중요도 강등**. 선 스타일 축(파선=계열·점선=특관·
        // 빈테두리=T2)은 이미 점유돼 있어 건드리지 않고 **투명도**로만 낮춘다.
        // 0.42는 실화면에서 너무 안 보였다(리더) — 강등은 유지하되 가독 우선으로 상향.
        const uAlpha = n.isUnlisted ? 0.68 : 1;
        ctx.save(); ctx.globalAlpha = uAlpha;
        if (n.hasGroup && n.hasEquity) {
          const dx = nx - cx, dy = ny - cy, len = Math.sqrt(dx * dx + dy * dy) || 1;
          const px = -dy / len * 2, py = dx / len * 2;
          ctx.strokeStyle = style.color + 'cc'; ctx.lineWidth = 2; ctx.setLineDash([]);
          ctx.beginPath(); ctx.moveTo(cx + px, cy + py); ctx.lineTo(nx + px, ny + py); ctx.stroke();
          ctx.strokeStyle = REL_STYLES.group.color + 'aa'; ctx.lineWidth = 1.2; ctx.setLineDash(REL_STYLES.group.dash);
          ctx.beginPath(); ctx.moveTo(cx - px, cy - py); ctx.lineTo(nx - px, ny - py); ctx.stroke();
          ctx.setLineDash([]);
          const dxn = dx / len, dyn = dy / len;
          if (!n.isIncoming) drawArrowHead(cx + px, cy + py, nx + px, ny + py, style.color + 'ee', 14);
          else { const hx = cx + dxn * haloR, hy = cy + dyn * haloR; drawArrowHead(nx + px, ny + py, hx + px, hy + py, style.color + 'ee', 14); }
        } else {
          ctx.strokeStyle = style.color + 'cc'; ctx.lineWidth = isEquity ? 2 : 1.5; ctx.setLineDash(style.dash);
          ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(nx, ny); ctx.stroke(); ctx.setLineDash([]);
          if (isEquity) {
            if (!n.isIncoming) drawArrowHead(cx, cy, nx, ny, style.color + 'ee', 14);
            else {
              const dx = nx - cx, dy = ny - cy, len = Math.sqrt(dx * dx + dy * dy) || 1, dxn = dx / len, dyn = dy / len;
              const hx = cx + dxn * haloR, hy = cy + dyn * haloR;
              drawArrowHead(nx, ny, hx, hy, style.color + 'ee', 14);
            }
          }
        }
        ctx.restore();
      });

      // 앵커 노드
      const aGrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, anchorR * 1.8);
      aGrd.addColorStop(0, sec.color + 'aa'); aGrd.addColorStop(1, sec.color + '00');
      ctx.fillStyle = aGrd; ctx.beginPath(); ctx.arc(cx, cy, anchorR * 1.8, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = sec.color; ctx.beginPath(); ctx.arc(cx, cy, anchorR * 0.5, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, anchorR * 0.5, 0, Math.PI * 2); ctx.stroke();
      // UX-018: 앵커명 = 백킹 박스 없이 섹터색 글씨 — 이웃 노드 라벨과 같은 문법
      // (구 백킹은 방사형 VC의 엣지 다발 대응이었음 — 레일 전환으로 불필요)
      ctx.textAlign = 'center';
      ctx.font = 'bold 12px sans-serif';
      ctx.fillStyle = sec.color;
      ctx.fillText(anchor.n, cx, cy - anchorR * 0.5 - 10);

      // 이웃 + 묶음 노드
      allNodes.forEach((n, i) => {
        const nx = cx + animPos[i].x * baseR, ny = cy + animPos[i].y * baseR;
        if (n.isBundle && n.isGroupBundle) {
          // UX-022: 그룹 내 초과분 — 스택 맨 아래 같은 섹터색 "+N사" 노드 (클릭 → 팝업)
          const bc = n.bundleColor || '#94a3b8';
          ctx.fillStyle = bc + '2e';
          ctx.beginPath(); ctx.arc(nx, ny, 9, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = bc + 'aa'; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.arc(nx, ny, 9, 0, Math.PI * 2); ctx.stroke();
          ctx.textAlign = 'left'; ctx.fillStyle = bc; ctx.font = 'bold 9px sans-serif';
          ctx.fillText(n.restLabel, nx + 13, ny + 3);
          hits.push({ x: nx, y: ny, r: 12, isBundle: true,
                      custom: { title: n.customTitle, items: n.rest } });
          return;
        }
        if (n.isBundle) {
          ctx.fillStyle = 'rgba(148,163,184,0.18)';
          ctx.beginPath(); ctx.arc(nx, ny, 16, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = 'rgba(148,163,184,0.6)'; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.arc(nx, ny, 16, 0, Math.PI * 2); ctx.stroke();
          ctx.fillStyle = '#cbd5e1'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
          ctx.fillText('+' + n.rest.length, nx, ny + 3);
          const firstName = (n.rest[0] && n.rest[0].name) || '';
          // 잔여가 1개면 "외 0사"가 되어버린다 - 그땐 이름만 (오프바이원 방지).
          const clip = (s, n2) => (s.length > n2 ? s.slice(0, n2) + '…' : s);
          const label = n.rest.length === 1
            ? clip(firstName, 9)
            : clip(firstName, 6) + ' 외 ' + (n.rest.length - 1) + '사';
          ctx.fillStyle = '#94a3b8'; ctx.font = '8px sans-serif';
          ctx.fillText(label, nx, ny + (n.side === 'below' ? 30 : -22));
          hits.push({ x: nx, y: ny, r: 16, isBundle: true, side: n.side });
          return;
        }
        // U5: 비상장류는 섹터가 없다 — 무채 단일색으로 그린다(신원 미상장의 표식).
        const nodeColor = n.isUnlisted ? UNLISTED_COLOR
          : ((n.sectorKo && (window.SECTOR_PALETTE || []).find(s => s.ko === n.sectorKo)?.color)
          || (isVc ? VC_FLOW_COLOR : (REL_STYLES[n.relType] || REL_STYLES.manual).color));
        const isHover = hoverCode === n.code;
        // UX-015: 밸류체인은 노드 크기 = 신뢰등급 (T1 정형 공시 크게 / T2 서술 추출 작게)
        const coreR = isVc ? ((n.tier === 'T1') ? 6.5 : (n.tier === 'T2') ? 4 : 3) : 5;
        ctx.globalAlpha = 0.8;
        const r0 = (isHover ? 26 : 20) * (isVc ? (coreR / 5) : 1);
        const grd = ctx.createRadialGradient(nx, ny, 0, nx, ny, r0);
        grd.addColorStop(0, nodeColor + '99'); grd.addColorStop(1, nodeColor + '00');
        ctx.fillStyle = grd; ctx.beginPath(); ctx.arc(nx, ny, r0, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
        if (n.isUnlisted) {
          // 형태 = 유형(NODE TYPOLOGY): 법인 채운 원 / 개인 링 / 조합·펀드 점선 링 /
          // 공공기관 이중 링. 상장 최소(5)보다 한 단계 작게 그려 위계를 낮춘다.
          drawUnlistedNode(ctx, nx, ny, n.kind, 4.2, nodeColor);
        } else {
          ctx.fillStyle = nodeColor;
          ctx.beginPath(); ctx.arc(nx, ny, coreR, 0, Math.PI * 2); ctx.fill();
        }
        if (isVc && n.tier === 'T2') {   // 서술 추출은 테두리를 비워 '추정' 뉘앙스
          ctx.strokeStyle = nodeColor; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.arc(nx, ny, coreR + 2, 0, Math.PI * 2); ctx.stroke();
        }
        if (n.labelRight) {
          // UX-015 세로 스택: 노드 오른쪽에 이름 + 금액 한 줄씩(왼쪽 정렬).
          // UX-019: 노드=세그 중앙 → 이름 가용폭 = 세그 오른쪽 절반. 폰트 축소 우선, 축약은 최후.
          const nMaxW = Math.max(30, (n.segW || 0.3) * 0.5 * baseR - 12);
          ctx.textAlign = 'left';
          const fitLocal = (text, maxW, px, minPx, weight) => {
            for (let p = px; p >= minPx; p -= 0.5) {
              ctx.font = `${weight} ${p}px sans-serif`;
              if (ctx.measureText(text).width <= maxW) return text;
            }
            let s = String(text);
            while (s.length > 1 && ctx.measureText(s + '…').width > maxW) s = s.slice(0, -1);
            return s + '…';
          };
          ctx.fillStyle = nodeColor;
          ctx.fillText(fitLocal(n.name, nMaxW, 9, 7.5, 'bold'), nx + 10, ny - 1);
          if (n.amount) {
            ctx.fillStyle = '#64748b';
            const am = fmtVcAmount(n.amount) + (n.as_of ? '·' + n.as_of : '');
            ctx.fillText(fitLocal(am, nMaxW, 8, 7, '400'), nx + 10, ny + 9);
          }
        } else {
          const labelUp = n.isSide || n.gy < 0;
          ctx.textAlign = 'center'; ctx.fillStyle = nodeColor; ctx.font = 'bold 9px sans-serif';
          const nameY = labelUp ? ny - 13 : ny + 18;
          ctx.fillText(n.name, nx, nameY);
          ctx.fillStyle = '#64748b'; ctx.font = '8px sans-serif';
          const s = REL_STYLES[n.relType] || REL_STYLES.manual;
          ctx.fillText(s.label + (n.detail ? ' · ' + n.detail : ''), nx, labelUp ? nameY + 9 : nameY + 11);
        }
        hits.push({ x: nx, y: ny, r: isVc ? 14 : 20, code: n.code, name: n.name,
                    sectorKo: n.sectorKo, isUnlisted: n.isUnlisted, kind: n.kind,
                    detail: n.detail, relType: n.relType });
      });

      hitRef.current = hits;
      if (window.__egoDebug) window.__egoDebug.renderedCodes = hits.filter(h => h.code).map(h => h.code);
      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(rafRef.current); window.removeEventListener('resize', resize); };
  }, [allNodes, anchor, sec.color, isVc]);

  const hitTest = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const h of hitRef.current) {
      if (Math.hypot(mx - h.x, my - h.y) <= h.r + 4) return h;
    }
    return null;
  };
  const handleClick = (e) => {
    const h = hitTest(e);
    if (!h || h.isAnchor) return;
    // UX-022: 그룹 내 "+N사" 번들은 자체 리스트를 들고 있다(custom) — 사이드 묶음과 구분
    if (h.isBundle) { setOverflowSide(h.custom ? { custom: h.custom } : h.side); return; }
    // U5: 비상장·개인은 companies_index에 없다 — 이동하지 않고 정보만 보여준다.
    if (h.isUnlisted) { setUnlistedInfo(h); return; }
    onReRoot(h.code, h.name, h.sectorKo);
  };
  const handleMove = (e) => {
    const h = hitTest(e);
    setHoverCode(h && !h.isBundle && !h.isAnchor ? h.code : null);
    canvasRef.current.style.cursor = (h && !h.isAnchor) ? 'pointer' : 'default';
  };

  const OVERFLOW_TITLE = isVc
    ? { above: '공급처', below: '고객사' }
    : { above: '출자사', below: '피출자사', left: '계열사', right: '특수관계자' };
  const isCustomOverflow = !!(overflowSide && typeof overflowSide === 'object' && overflowSide.custom);
  const overflowList = !overflowSide ? null
    : isCustomOverflow ? overflowSide.custom.items
    : ({ above, below, left, right }[overflowSide] || {}).rest || null;
  const overflowTitle = isCustomOverflow
    ? overflowSide.custom.title
    : (OVERFLOW_TITLE[overflowSide] || '') + ' 전체';

  return (
    // FN-009: 캔버스 사이징(position/inset·100%)은 인라인으로 고정한다 — styles.css가
    // 캐시된 구버전이면 .ego-stage/.ego-canvas 규칙이 없어 캔버스가 기본 300x150으로
    // 붕괴하고 그림이 좌상단에 박힌다(실제 발생·재현). 레이아웃은 스타일시트 캐시에 의존 금지.
    <div className="ego-stage" style={{position:'absolute', inset:0}}>
      <canvas ref={canvasRef} className="ego-canvas"
        style={{width:'100%', height:'100%', display:'block'}}
        onClick={handleClick} onMouseMove={handleMove}
        onMouseLeave={() => setHoverCode(null)} />
      {/* UX-012: 상단 중앙 바는 레이어 토글 2개 전용. 재구성 이력을 여기에 나열하니
          탐색할수록 무한 증식해 토글이 밀렸다(리더 지적) — 이력은 한 단계 뒤로 버튼으로 축약.
          현재 위치는 좌상단 전역 브레드크럼(GALAXY › 섹터 › 시장 › 기업)이 이미 보여준다. */}
      <div className="ego-topbar">
        {chain.length > 1 && (
          <button className="ego-back-btn" title={chain[chain.length - 2].name + '(으)로'}
            onClick={() => onChainJump(chain.length - 2)}>
            ← {chain[chain.length - 2].name}
          </button>
        )}
        <div className="ego-layer-toggle">
          <button className={"ego-layer-btn" + (!isVc ? " is-active" : "")}
            onClick={() => onLayerChange && onLayerChange('governance')}>지배구조</button>
          <button
            className={"ego-layer-btn" + (isVc ? " is-active" : hasVc ? "" : " is-disabled")}
            disabled={!hasVc}
            title={hasVc ? '밸류체인 레이어 — 공시 기반 물자 흐름' : '밸류체인 공시 데이터 없음'}
            onClick={() => hasVc && onLayerChange && onLayerChange('valuechain')}>밸류체인</button>
        </div>
      </div>
      {unlistedInfo && (
        <div className="panel ego-overflow-panel">
          <div className="panel-head">
            <div className="panel-head-l">
              <span className="panel-dot" style={{background: UNLISTED_COLOR}} />
              <span className="panel-title">{UNLISTED_KIND_LABEL[unlistedInfo.kind] || '비상장'}</span>
            </div>
            <button className="back-link" onClick={() => setUnlistedInfo(null)}>✕</button>
          </div>
          <div className="panel-body">
            <div style={{fontSize: 13, color: '#e2e8f0', fontWeight: 600, marginBottom: 6,
                         wordBreak: 'break-all'}}>{unlistedInfo.name}</div>
            <div style={{fontSize: 11, color: '#94a3b8', lineHeight: 1.8}}>
              관계 · <span style={{color: (REL_STYLES[unlistedInfo.relType] || REL_STYLES.manual).color}}>
                {(REL_STYLES[unlistedInfo.relType] || REL_STYLES.manual).label}</span>
              {unlistedInfo.detail ? <> · {unlistedInfo.detail}</> : null}
            </div>
            <div style={{fontSize: 10.5, color: '#5c6b80', lineHeight: 1.7, marginTop: 10,
                         paddingTop: 8, borderTop: '1px solid rgba(140,170,210,.13)'}}>
              사업보고서에 기재된 표기 그대로입니다. 비상장이라 별도 기업 정보가 없어
              이동하지 않습니다.
            </div>
          </div>
        </div>
      )}
      {overflowList && (
        <div className="panel ego-overflow-panel">
          <div className="panel-head">
            <div className="panel-head-l">
              <span className="panel-dot" style={{background: sec.color, boxShadow: `0 0 8px ${sec.color}`}} />
              <span className="panel-title">{overflowTitle}</span>
            </div>
            <div style={{display:'flex', alignItems:'center', gap:8}}>
              <span className="panel-count">{overflowList.length}사</span>
              <button className="back-link" onClick={() => setOverflowSide(null)}>✕</button>
            </div>
          </div>
          <div className="panel-body">
            {(() => {
              // UX-021: 도트=기업의 섹터색(신원), 라벨=관계유형 색(관계) — 두 축 분리
              const row = (n, style) => (
                <div key={n.code + ':' + (n.type || n.relType)} className="ego-overflow-row"
                  onClick={() => {
                    if (n.isUnlisted) { setOverflowSide(null); setUnlistedInfo(n); return; }
                    setOverflowSide(null); onReRoot(n.code, n.name, n.sectorKo);
                  }}>
                  <span className="ov-rel-mark" style={{
                    background: style.dash.length === 0 ? style.markColor : 'transparent',
                    border: style.dash.length === 0 ? 'none' : `1.5px dashed ${style.markColor}`,
                  }} />
                  <span className="ego-overflow-name">{n.name}</span>
                  <span className="ego-overflow-type" style={{color: style.labelColor}}>{style.label}</span>
                </div>
              );
              // UX-016·020: 팝오버는 두 레이어 모두 산업별 섹션 — "유통 ── / 삼성물산 / …".
              // 헤더=섹터색, 행 스타일은 레이어 문법 유지(지배구조=관계유형 색·대시 / VC=섹터색+등급 대시).
              const order = [], byKo = new Map();
              for (const n of overflowList) {
                const ko = n.sectorKo || '기타';
                if (!byKo.has(ko)) { byKo.set(ko, []); order.push(ko); }
                byKo.get(ko).push(n);
              }
              return order.map(ko => {
                const pal = (window.SECTOR_PALETTE || []).find(s => s.ko === ko);
                const c = (pal && pal.color) || '#94a3b8';
                return (
                  <React.Fragment key={'sec_' + ko}>
                    <div className="ego-overflow-sec" style={{color: c, borderColor: c + '44'}}>
                      <span className="ego-overflow-sec-dot" style={{background: c, boxShadow: `0 0 6px ${c}`}} />
                      {ko} <span style={{color: '#64748b'}}>· {byKo.get(ko).length}사</span>
                    </div>
                    {byKo.get(ko).map(n => {
                      if (isVc) {
                        return row(n, {
                          markColor: c, labelColor: c,
                          dash: (VC_TIER_STYLES[n.tier] || VC_TIER_STYLES.T1).dash,
                          label: (n.type === 'supply' ? '공급처' : '고객사') + (n.amount ? ' · ' + fmtVcAmount(n.amount) : ''),
                        });
                      }
                      const s = REL_STYLES[n.relType] || REL_STYLES.manual;
                      return row(n, { markColor: c, labelColor: s.color, dash: [],
                                      label: s.label + (n.detail ? ' · ' + n.detail : '') });
                    })}
                  </React.Fragment>
                );
              });
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
window.EgoView = EgoView;

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
// UX-008: 모드별 콘텐츠 — 성운 개요(activeMarket 없음)=DAILY HIGHLIGHTS+SECTOR PULSE,
// 시장 드릴인(activeMarket)=그 시장 기업 목록(시총순, 클릭 시 기업 선택).
function SectorOverviewPanel({ sector, companyCount, activeMarket, onBack, onSelectCompany }) {
  if (!sector) return null;
  const D = window.DiscloseAI || {};
  const realData = window.__realData;
  const members = (sector.members || []).map(n => n);
  const highlights = (D.highlightsForSector && realData) ? D.highlightsForSector(realData.discAll, members, 3) : null;
  // 드릴인 기업 목록: named(시총 정확) 먼저 cap desc → dot 기업 cb desc·이름순
  const marketList = React.useMemo(() => {
    if (!activeMarket || !realData || !realData.sectorMarketData) return null;
    const md = realData.sectorMarketData[sector.id];
    const m = md && md[activeMarket];
    if (!m) return null;
    const namedRows = m.named.map(c => ({ code: c.code, name: c.name, capT: c.cap, isNamed: true }));
    const namedCodes = new Set(namedRows.map(r => r.code));
    const dotRows = m.dotItems
      .filter(d => d.t && !namedCodes.has(d.t))
      .sort((a, b) => (b.cb - a.cb) || String(a.n).localeCompare(String(b.n), 'ko'))
      .map(d => ({ code: d.t, name: d.n, capT: null, isNamed: false }));
    return [...namedRows, ...dotRows];
  }, [activeMarket, sector.id, realData]);
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
        {!marketList && (<>
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
        </>)}
        {marketList && (
          <div className="sector-ov-section">
            <div className="ov-sec-title">{activeMarket} COMPANIES · 시총순 {marketList.length}사</div>
            <ul className="ov-sec-list" style={{maxHeight: 300, overflowY: 'auto'}}>
              {marketList.map((r) => (
                <li key={r.code} onClick={() => onSelectCompany && onSelectCompany(r.code)}
                    style={{cursor: 'pointer', display:'flex', alignItems:'baseline', gap:6}}>
                  <span className="ov-bullet" style={{background: sector.color, opacity: r.isNamed ? 1 : 0.4}} />
                  <span style={{flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{r.name}</span>
                  <span style={{fontFamily:'var(--font-mono)', fontSize:10, color:'#94a3b8'}}>
                    {r.capT != null ? r.capT + 'T' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── PHASE 4: Company overview panel (top-left) ────────────────────────────
function CompanyOverviewPanel({ company, sector, onBack, onEnter, egoAnchor }) {
  if (!company) return null;
  // ③ ego 데이터 있으면 우선(universe 전량 커버) — 없으면 기존 top50-scoped RELATIONS 폴백.
  const rels = (egoAnchor && egoAnchor.layers)
    ? mergeEgoNeighbors(egoAnchor.layers.governance).map(n => ({ code: n.code, type: n.relType }))
    : (window.RELATIONS[company.code] || []);
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


// U5: 노드 유형 범례 — 두 레이어 공통(비상장 노드는 양쪽 다 나타난다).
// 색은 무채 고정이고 **형태**가 유형을 가른다(DESIGN.md §2 색=의미 보존 — 새 색 없음).
function NodeTypologySection() {
  const mark = (kind) => {
    const c = UNLISTED_COLOR;
    if (kind === 'listed') return <circle cx="11" cy="9" r="5.5" fill="#5eead4" />;
    if (kind === 'person') return <circle cx="11" cy="9" r="4.5" fill="none" stroke={c} strokeWidth="1.5" />;
    if (kind === 'coop_fund') return <circle cx="11" cy="9" r="4.5" fill="none" stroke={c} strokeWidth="1.5" strokeDasharray="2.5 2.5" />;
    if (kind === 'public_org') return <g><circle cx="11" cy="9" r="5.8" fill="none" stroke={c} strokeWidth="1.2" />
      <circle cx="11" cy="9" r="2.6" fill="none" stroke={c} strokeWidth="1.2" /></g>;
    return <circle cx="11" cy="9" r="4.2" fill={c} />;
  };
  const row = (kind, label, note) => (
    <div className="legend-row" key={kind}>
      <svg width="22" height="18" className="legend-svg">{mark(kind)}</svg>
      <div className="legend-text">
        <div className="legend-label">{label}</div>
        <div className="legend-sub">{note}</div>
      </div>
    </div>
  );
  return (
    <div className="legend-section">
      <div className="legend-section-h">
        <span style={{color: UNLISTED_COLOR}}>◌</span> NODE · 노드 유형
      </div>
      <div className="legend-grid">
        {row('listed', '상장사', '섹터색 · 클릭 시 이동')}
        {row('private_corp', '비상장법인', '무채 · 이동 없음')}
        {row('person', '개인', '링')}
        {row('coop_fund', '조합·펀드', '점선 링')}
        {row('public_org', '공공기관', '이중 링')}
      </div>
    </div>
  );
}

// ─── Edge legend (bottom-left) — clearer differentiation ─────────────────
function LegendPanel({ mode }) {
  // U-D14: 레이어 전환 시 범례도 통째로 교체 — 혼합 범례 금지. mode='valuechain'이면
  // 흐름 문법 전용 범례(색=은백 단일, 선=신뢰등급, 셰브런=물자 흐름 위→아래).
  if (mode === 'valuechain') {
    return (
      <div className="panel panel-bl legend-panel">
        <div className="panel-head">
          <div className="panel-head-l">
            <span className="panel-dot" style={{background: '#e8f1ff', boxShadow: '0 0 8px #e8f1ff'}} />
            <span className="panel-title">FLOW TYPOLOGY</span>
            <span className="panel-sub">물자 흐름</span>
          </div>
          <div className="panel-count">VALUE CHAIN</div>
        </div>
        <div className="panel-body legend-body">
          <div className="legend-section">
            <div className="legend-section-h">
              <span style={{color:'#e8f1ff'}}>━━━</span> LINE · 신뢰등급 (원천별)
            </div>
            <div className="legend-grid">
              <LegendRow color="#e8f1ff" kind="solid" label="T1 정형 공시" sub="특수관계자 거래·공급계약" />
              <LegendRow color="#e8f1ff77" kind="solid" label="T2 서술 추출" sub="사업보고서 서술 (준비 중)" />
              <LegendRow color="#e8f1ff88" kind="dot" label="T3 산업연관표" sub="섹터 백본 (준비 중)" />
            </div>
          </div>
          <NodeTypologySection />
          <div className="legend-section">
            <div className="legend-section-h">
              <span style={{color:'#e8f1ff'}}>▼</span> ARROW · 물자 흐름 방향
            </div>
            <div style={{fontSize: 10.5, color: '#94a3b8', lineHeight: 1.7, padding: '2px 2px 0'}}>
              위 = <span style={{color:'#e8f1ff'}}>공급처</span> (매입·조달) → 앵커 →
              아래 = <span style={{color:'#e8f1ff'}}>고객사</span> (매출·공급계약).<br/>
              금액은 최신 공시 연도 기준 · 공시 기반 참고 정보 — 투자 조언 아님.
            </div>
          </div>
        </div>
      </div>
    );
  }
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
        <NodeTypologySection />
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
  const [activeMarket, setActiveMarket] = useState(null);  // U2 드릴인: null=성운 개요, 'KOSPI'|'KOSDAQ'=드릴인

  // ③ EgoView (universe/PLAN.md §5 LOD-2) — ego/<ticker>.json 지연 fetch 상태 + re-root 체인.
  // 실패(404 등) 시 egoStatus='error' → 렌더 분기가 기존 SectorMap(allRelated 폴리곤)으로
  // 폴백한다(FN-005 사다리 패턴, graph_top50 경로 회귀 무손상 — UX-010).
  const [egoAnchor, setEgoAnchor] = useState(null);
  const [egoStatus, setEgoStatus] = useState('idle'); // idle | loading | ok | error
  const [egoChain, setEgoChain] = useState([]); // [{code,name,sectorKo}] re-root 브레드크럼
  const egoCacheRef = useRef(new Map());
  // U3: 레이어 토글 상태 — re-root로 기업이 바뀌어도 유지(레이어 비교 탐색 흐름).
  // 데이터 없는 기업에선 EgoView가 지배구조로 안전 폴백(hasVc 가드).
  const [egoLayer, setEgoLayer] = useState('governance');
  const egoHasVc = !!(egoAnchor && egoAnchor.layers && egoAnchor.layers.valuechain
    && (((egoAnchor.layers.valuechain.up || []).length) || ((egoAnchor.layers.valuechain.down || []).length)));
  // 범례(U-D14 전용 범례 교체)는 화면이 실제 그리는 유효 레이어를 따른다
  const effectiveEgoLayer = (egoLayer === 'valuechain' && egoHasVc) ? 'valuechain' : 'governance';

  // sector zoom-in transition
  const [zoomProgress, setZoomProgress] = useState(0);
  const zoomAnimRef = useRef(0);


  // ENTER SECTOR — animate galaxy → sector
  const enterSector = useCallback((sectorId) => {
    cancelAnimationFrame(zoomAnimRef.current);
    setActiveSectorId(sectorId);
    setActiveMarket(null);   // 진입 시 성운 개요부터
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
    setActiveMarket(null);
    setPhase('galaxy');
    setActiveSectorId(null);
    setZoomProgress(0);
  }, []);

  // 성운 개요로(드릴인·기업 해제)
  const backToSectorOverview = useCallback(() => {
    setActiveCompanyCode(null);
    setActiveMarket(null);
    setPhase('sector');
  }, []);

  // 기업 → 시장 드릴인 뷰로 (activeMarket 유지)
  const backToSector = useCallback(() => {
    setActiveCompanyCode(null);
    setPhase('sector');
  }, []);

  const enterMarket = useCallback((market) => {
    setActiveMarket(market);
    setActiveCompanyCode(null);
    setPhase('sector');
  }, []);

  // FN-008: 기업 코드 → 소속 시장(KOSPI|KOSDAQ). named·dot 전 기업 커버(indexByCode).
  const marketOf = useCallback((code) => {
    const RD = window.__realData || {};
    return (RD.indexByCode && RD.indexByCode[code] && RD.indexByCode[code].mkt) || null;
  }, []);

  const selectCompany = useCallback((code) => {
    if (!code) {
      // null → deselect, return to sector view
      setActiveCompanyCode(null);
      setPhase('sector');
      setEgoChain([]);
      return;
    }
    setActiveCompanyCode(code);
    // FN-008: 시장 미설정(개요에서 dot 클릭 등)이면 그 기업의 시장으로 자동 드릴인
    setActiveMarket(prev => prev || marketOf(code));
    setPhase('company');
    setEgoChain([]); // 새 진입 — ego fetch effect가 로드 성공 시 [{anchor}]로 시딩
  }, [marketOf]);

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
    // FN-008: enterSector가 activeMarket을 null로 리셋 — 그대로 두면 SectorMap이
    // 개요 모드(시장 프록시 노드)로 렌더돼 활성 기업이 화면에서 사라짐(SK 진입 붕괴).
    // ghost 기업의 소속 시장으로 즉시 드릴인 설정.
    setActiveMarket(marketOf(code));
    setPhase('company');
    setEgoChain([]); // 새 진입(재구성 아님) — 체인 리셋
  }, [enterSector, marketOf]);

  // ③ EgoView ego/<ticker>.json 지연 fetch — activeCompanyCode 변경마다(재구성 포함) 재실행.
  // 세션 캐시로 재방문 시 재요청 없이 즉시 반영(성능 게이트 <300ms, universe/PLAN.md §5).
  useEffect(() => {
    if (phase !== 'company' || !activeCompanyCode) { setEgoStatus('idle'); return; }
    let alive = true;
    const cached = egoCacheRef.current.get(activeCompanyCode);
    const apply = (json) => {
      if (!alive) return;
      if (json) {
        setEgoAnchor(json);
        setEgoStatus('ok');
        setEgoChain(prev => prev.length ? prev : [{ code: json.t, name: json.n, sectorKo: json.s }]);
      } else {
        setEgoAnchor(null);
        setEgoStatus('error'); // → 렌더 분기가 SectorMap(allRelated)으로 폴백
      }
    };
    if (cached) { apply(cached); return; }
    setEgoStatus('loading');
    fetch(`../data/ego/${activeCompanyCode}.json`)
      .then(r => (r.ok ? r.json() : null))
      .then(json => { if (json) egoCacheRef.current.set(activeCompanyCode, json); apply(json); })
      .catch(() => apply(null));
    return () => { alive = false; };
  }, [phase, activeCompanyCode]);

  // 이웃 노드 클릭 = 앵커 재구성(re-root) — valuechain §5 D5. 섹터·시장이 바뀌면 함께 갱신
  // (selectGhost와 동일한 크로스섹터 점프 패턴 — 어느 진입로든 전 상장사 도달 불변식).
  const reRootEgo = useCallback((code, name, sectorKo) => {
    const targetSector = SECTOR_PALETTE.find(s => s.ko === sectorKo);
    if (targetSector && targetSector.id !== activeSectorId) setActiveSectorId(targetSector.id);
    setActiveCompanyCode(code);
    setActiveMarket(marketOf(code));
    setPhase('company');
    setEgoChain(prev => [...prev, { code, name, sectorKo }]);
  }, [activeSectorId, marketOf]);

  // 브레드크럼 클릭 = 그 지점까지 체인 절단 후 재구성(추가 아님)
  const jumpEgoChain = useCallback((index) => {
    const entry = egoChain[index];
    if (!entry) return;
    const targetSector = SECTOR_PALETTE.find(s => s.ko === entry.sectorKo);
    if (targetSector && targetSector.id !== activeSectorId) setActiveSectorId(targetSector.id);
    setActiveCompanyCode(entry.code);
    setActiveMarket(marketOf(entry.code));
    setPhase('company');
    setEgoChain(prev => prev.slice(0, index + 1));
  }, [egoChain, activeSectorId, marketOf]);

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
  // UX-009: dot 기업(top-N 밖)은 COMPANIES 평탄 목록에 없음 → indexByCode 신원으로 폴백
  // (CompanyOverviewPanel은 node 데이터 없으면 기본 정보만 렌더 — null-safe 확인됨)
  const company = activeCompanyCode
    ? (companies.find(c => c.code === activeCompanyCode)
       || (() => {
            const RD = window.__realData || {};
            const di = RD.indexByCode && RD.indexByCode[activeCompanyCode];
            return di ? { code: activeCompanyCode, name: di.n, en: di.n, cap: Math.max(1, (di.cb || 0) * 6 + 1) } : null;
          })())
    : null;

  // breadcrumb — GALAXY › 섹터 › [KOSPI|KOSDAQ] › 기업 (U2 드릴인)
  const crumb = [];
  if (phase === 'galaxy') crumb.push({ label: 'GALAXY' });
  if (phase === 'sector' || phase === 'company') {
    crumb.push({ label: 'GALAXY', onClick: backToGalaxy });
    if (sector) crumb.push({ label: sector.ko, onClick: activeMarket ? backToSectorOverview : null });
    if (activeMarket) crumb.push({ label: activeMarket, onClick: phase === 'company' ? backToSector : null });
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

          {/* Sector / company phase — sector map, 또는 ③ EgoView(지배구조 셸, LOD-2) */}
          {(phase === 'sector' || phase === 'company') && sector && (
            <div className="sector-map-stage" style={{
              opacity: Math.max(0, (zoomProgress - 0.3) * 1.6),
              transform: `scale(${0.7 + zoomProgress * 0.3})`,
            }}>
              {phase === 'company' && egoStatus === 'loading' ? (
                <div className="ego-loading"><div className="ego-loading-spinner" /></div>
              ) : phase === 'company' && egoStatus === 'ok' && egoAnchor ? (
                <EgoView
                  anchor={egoAnchor}
                  chain={egoChain}
                  layer={egoLayer}
                  onLayerChange={setEgoLayer}
                  onReRoot={reRootEgo}
                  onChainJump={jumpEgoChain}
                />
              ) : (
                <SectorMap
                  sectorId={activeSectorId}
                  activeMarket={activeMarket}
                  activeCompanyCode={activeCompanyCode}
                  onSelectMarket={enterMarket}
                  onSelectCompany={selectCompany}
                  onSelectGhost={selectGhost}
                />
              )}
            </div>
          )}

          <TopTabs active={activeTab} onChange={setActiveTab} breadcrumb={crumb} />

          {/* Top-left panel — varies by phase and active tab */}
          {activeTab === 'finance' ? (
            <>
              {phase === 'galaxy' && <MascotPanel messages={["섹터를 클릭하면, 기업을 확인할 수 있어요!", "오른쪽 아래 섹터 INDEX에서도 선택할 수 있어요.", "AI 코파일럿에게 무엇이든 물어보세요."]} />}
              {phase === 'sector' && <SectorOverviewPanel sector={sector} companyCount={sector.count || companies.length} activeMarket={activeMarket} onSelectCompany={selectCompany} onBack={activeMarket ? backToSectorOverview : backToGalaxy} />}
              {phase === 'company' && <CompanyOverviewPanel company={company} sector={sector} onBack={backToSector} onEnter={enterCorporation} egoAnchor={egoStatus === 'ok' ? egoAnchor : null} />}
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

          {/* Bottom-left — legend. company phase + EgoView일 땐 유효 레이어의 전용 범례(U-D14) */}
          <LegendPanel mode={phase === 'company' && egoStatus === 'ok' ? effectiveEgoLayer : 'governance'} />

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
