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

const SECTOR_PALETTE = (window.__realData && window.__realData.sectors && window.__realData.sectors.length) ? window.__realData.sectors : [
  { id: 'semi',    ko: '반도체',     en: 'Semiconductor',   color: '#5eead4', cap: 980 },
  { id: 'fin',     ko: '금융',       en: 'Financials',      color: '#fbbf24', cap: 720 },
  { id: 'auto',    ko: '자동차',     en: 'Automotive',      color: '#a78bfa', cap: 540 },
  { id: 'bio',     ko: '바이오',     en: 'Biotech',         color: '#f472b6', cap: 410 },
  { id: 'energy',  ko: '에너지',     en: 'Energy',          color: '#f97316', cap: 380 },
  { id: 'it',      ko: 'IT/플랫폼',  en: 'Platform',        color: '#60a5fa', cap: 660 },
  { id: 'chem',    ko: '화학',       en: 'Chemicals',       color: '#facc15', cap: 320 },
  { id: 'steel',   ko: '철강',       en: 'Steel',           color: '#94a3b8', cap: 240 },
  { id: 'ship',    ko: '조선',       en: 'Shipbuilding',    color: '#22d3ee', cap: 280 },
  { id: 'cons',    ko: '건설',       en: 'Construction',    color: '#fb923c', cap: 210 },
  { id: 'retail',  ko: '유통/소비재', en: 'Retail',         color: '#fb7185', cap: 260 },
  { id: 'tele',    ko: '통신',       en: 'Telecom',         color: '#818cf8', cap: 290 },
  { id: 'media',   ko: '미디어',     en: 'Media',           color: '#e879f9', cap: 180 },
  { id: 'food',    ko: '식음료',     en: 'F&B',             color: '#a3e635', cap: 200 },
  { id: 'logi',    ko: '운송/물류',  en: 'Logistics',       color: '#34d399', cap: 230 },
  { id: 'mat',     ko: '소재',       en: 'Materials',       color: '#fcd34d', cap: 220 },
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
        const useColor = sectorVisual === 'mono' ? '#5eead4' : sec.color;
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
  subsidiary:  { color: '#5eead4', dash: [],         label: '종속기업',   sub: 'K-IFRS · >50%' },
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
  const nodesRef = _useRef([]);
  const ghostNodesRef = _useRef([]);
  const [hoverCode, setHoverCode] = _useState(null);
  const bgStarsRef = _useRef([]);
  const shootingRef = _useRef([]);

  const sec = SECTOR_PALETTE.find(s => s.id === sectorId) || SECTOR_PALETTE[0];
  const companies = COMPANIES[sectorId] || COMPANIES.semi || [];

  // Compute gather positions: when active, ACTIVE stays in place; related ones orbit it
  const layout = _useMemo(() => {
    if (!activeCompanyCode) {
      return companies.map(c => ({ ...c, gx: c.x, gy: c.y }));
    }
    const active = companies.find(c => c.code === activeCompanyCode);
    if (!active) return companies.map(c => ({ ...c, gx: c.x, gy: c.y }));
    const rels = RELATIONS[activeCompanyCode] || [];
    const relMap = new Map(rels.map(r => [r.code, r.type]));
    return companies.map((c, i) => {
      if (c.code === activeCompanyCode) {
        // Active stays in its original position
        return { ...c, gx: c.x, gy: c.y, isActive: true };
      }
      if (relMap.has(c.code)) {
        // In-sector related: gather tightly around the active node
        const n = [...relMap.keys()].indexOf(c.code);
        const total = relMap.size;
        const ang = (n / total) * Math.PI * 2 + 0.4;
        const r = 0.2; // tight orbit around active
        return { ...c, gx: active.x + Math.cos(ang) * r, gy: active.y + Math.sin(ang) * r, relType: relMap.get(c.code) };
      }
      // un-related: push to the edge & dim
      return { ...c, gx: c.x * 1.08, gy: c.y * 1.08, fade: true };
    });
  }, [companies, activeCompanyCode]);

  // Ghost nodes: cross-sector relations orbit around the active company's position
  const ghostNodes = _useMemo(() => {
    if (!activeCompanyCode) return [];
    const active = companies.find(c => c.code === activeCompanyCode);
    const ax = active ? active.x : 0, ay = active ? active.y : 0;
    const inSectorCodes = new Set(companies.map(c => c.code));
    const rels = RELATIONS[activeCompanyCode] || [];
    const cross = rels.filter(r => !inSectorCodes.has(r.code));
    const seen = new Map();
    for (const r of cross) { if (!seen.has(r.code)) seen.set(r.code, r); }
    const RD = window.__realData || {};
    return Array.from(seen.values()).map((r, i, arr) => {
      const ang = (i / arr.length) * Math.PI * 2 - Math.PI / 2;
      const radius = 0.62;
      const node = RD.nodeByCode && RD.nodeByCode[r.code];
      // Use nameByCode for companies not in top50 (e.g. 삼성전기 009150)
      const name = (node && node.n) || (RD.nameByCode && RD.nameByCode[r.code]) || r.name || r.code;
      const sector = node ? (window.SECTOR_PALETTE || []).find(s => s.ko === node.s) : null;
      return { code: r.code, name, cap: 10,
               gx: ax + Math.cos(ang) * radius, gy: ay + Math.sin(ang) * radius,
               relType: r.type, isGhost: true, sectorId: sector ? sector.id : null };
    });
  }, [companies, activeCompanyCode]);

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

    // animated positions (sector companies + ghost nodes)
    const animPos = layout.map(c => ({ x: c.x, y: c.y }));
    const ghostAnimPos = ghostNodes.map(g => ({ x: g.gx * 0.3, y: g.gy * 0.3 }));

    const draw = () => {
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

      // Lerp positions toward target
      layout.forEach((c, i) => {
        animPos[i].x += (c.gx - animPos[i].x) * 0.08;
        animPos[i].y += (c.gy - animPos[i].y) * 0.08;
      });
      ghostNodes.forEach((g, i) => {
        ghostAnimPos[i].x += (g.gx - ghostAnimPos[i].x) * 0.06;
        ghostAnimPos[i].y += (g.gy - ghostAnimPos[i].y) * 0.06;
      });

      const cx = w / 2, cy = h / 2;
      // Zoom out when a company is active to show ghost nodes in outer ring
      const baseR = Math.min(w, h) * (activeCompanyCode ? 0.27 : 0.34);

      // Draw relationship edges (in-sector + ghost)
      if (activeCompanyCode) {
        const ai = layout.findIndex(c => c.code === activeCompanyCode);
        if (ai >= 0) {
          const ax = cx + animPos[ai].x * baseR, ay = cy + animPos[ai].y * baseR;
          // In-sector relations
          const rels = RELATIONS[activeCompanyCode] || [];
          rels.forEach(r => {
            const ti = layout.findIndex(c => c.code === r.code);
            if (ti < 0) return;
            const tx = cx + animPos[ti].x * baseR, ty = cy + animPos[ti].y * baseR;
            const style = REL_STYLES[r.type] || REL_STYLES.manual;
            ctx.strokeStyle = style.color + 'cc';
            ctx.lineWidth = 1.5;
            ctx.setLineDash(style.dash);
            ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(tx, ty); ctx.stroke();
            ctx.setLineDash([]);
          });
          // Ghost (cross-sector) relations
          ghostNodes.forEach((g, gi) => {
            const gx = cx + ghostAnimPos[gi].x * baseR, gy2 = cy + ghostAnimPos[gi].y * baseR;
            const style = REL_STYLES[g.relType] || REL_STYLES.manual;
            ctx.strokeStyle = style.color + '99';
            ctx.lineWidth = 1.2;
            ctx.setLineDash(style.dash.length ? style.dash : [4, 4]);
            ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(gx, gy2); ctx.stroke();
            ctx.setLineDash([]);
          });
        }
      }

      // Draw ghost nodes (cross-sector relations, outer ring)
      if (activeCompanyCode) {
        ghostNodes.forEach((g, gi) => {
          const gx = cx + ghostAnimPos[gi].x * baseR, gy2 = cy + ghostAnimPos[gi].y * baseR;
          const style = REL_STYLES[g.relType] || REL_STYLES.manual;
          ctx.globalAlpha = 0.65;
          // Small glow
          const grd = ctx.createRadialGradient(gx, gy2, 0, gx, gy2, 18);
          grd.addColorStop(0, style.color + '88'); grd.addColorStop(1, style.color + '00');
          ctx.fillStyle = grd;
          ctx.beginPath(); ctx.arc(gx, gy2, 18, 0, Math.PI * 2); ctx.fill();
          // Core dot
          ctx.fillStyle = style.color;
          ctx.beginPath(); ctx.arc(gx, gy2, 5, 0, Math.PI * 2); ctx.fill();
          ctx.globalAlpha = 1;
          // Label
          ctx.fillStyle = style.color;
          ctx.font = `9px var(--font-mono, monospace)`;
          ctx.textAlign = 'center';
          ctx.fillText(g.name, gx, gy2 - 11);
          ctx.fillStyle = '#64748b';
          ctx.font = `8px var(--font-mono, monospace)`;
          ctx.fillText(style.label, gx, gy2 + 18);
          ctx.textAlign = 'left';
        });
      }

      // Draw company nodes
      const positions = [];
      layout.forEach((c, i) => {
        const x = cx + animPos[i].x * baseR;
        const y = cy + animPos[i].y * baseR;
        const radius = 6 + Math.sqrt(c.cap) * 1.5;
        const isActive = c.code === activeCompanyCode;
        const isHover = hoverCode === c.code;
        const fade = c.fade ? 0.18 : 1;

        ctx.globalAlpha = fade;
        // glow
        const glowMul = isActive ? 9 : isHover ? 6 : 4.5;
        const g = ctx.createRadialGradient(x, y, 0, x, y, radius * glowMul);
        g.addColorStop(0, sec.color + 'cc');
        g.addColorStop(0.3, sec.color + '55');
        g.addColorStop(1, sec.color + '00');
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(x, y, radius * glowMul, 0, Math.PI * 2); ctx.fill();
        // bright core
        ctx.fillStyle = '#ffffff';
        ctx.beginPath(); ctx.arc(x, y, radius * 0.5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = sec.color;
        ctx.globalAlpha = fade * 0.9;
        ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;

        // pulse ring on active
        if (isActive) {
          const p = (Math.sin(t * 2.5) + 1) / 2;
          ctx.strokeStyle = sec.color + 'aa';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(x, y, radius * (2 + p * 0.5), 0, Math.PI * 2);
          ctx.stroke();
        }

        positions.push({ x, y, r: radius, c });
      });
      // Draw company name labels (always visible, not just on hover)
      ctx.textAlign = 'center';
      positions.forEach(({ x, y, r: nr, c }) => {
        const isActive = c.code === activeCompanyCode;
        ctx.globalAlpha = c.fade ? 0.2 : 0.85;
        ctx.fillStyle = isActive ? sec.color : 'rgba(148,163,184,0.9)';
        ctx.font = `${isActive ? '600 ' : ''}10px sans-serif`;
        const label = c.name.length > 7 ? c.name.slice(0, 7) + '…' : c.name;
        ctx.fillText(label, x, y - nr - 5);
        ctx.globalAlpha = 1;
      });
      ctx.textAlign = 'left';

      nodesRef.current = positions;

      // Store ghost screen positions for hit testing
      const ghostScreenPositions = ghostNodes.map((g, gi) => ({
        x: cx + ghostAnimPos[gi].x * baseR,
        y: cy + ghostAnimPos[gi].y * baseR,
        code: g.code,
        sectorId: g.sectorId,
        r: 14,
      }));
      ghostNodesRef.current = ghostScreenPositions;

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
      for (const p of ghostNodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < Math.min(bestD, 20)) { bestD = d; best = '_ghost_'; }
      }
      setHoverCode(best);
      cvs.style.cursor = (best && best !== '_ghost_') ? 'pointer' : (best === '_ghost_' ? 'pointer' : 'default');
    };
    const onClick = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      // Check regular nodes first
      let best = null, bestD = 28;
      for (const p of nodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = { code: p.c.code, isGhost: false }; }
      }
      // Check ghost nodes
      for (const p of ghostNodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < Math.min(bestD, 20)) { bestD = d; best = { code: p.code, isGhost: true, sectorId: p.sectorId }; }
      }
      if (best) {
        if (best.isGhost) onSelectGhost?.(best.code, best.sectorId);
        else onSelectCompany?.(best.code);
      } else {
        // Click empty space → deselect company
        onSelectCompany?.(null);
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
  }, [layout, ghostNodes, activeCompanyCode, hoverCode, sectorId]);

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
        {node && node.eqs != null && (
          <div className="sector-ov-section">
            <div className="ov-sec-title">EQS · 재무 건강도 ({node.gr || '-'} · {node.eqs}점)</div>
            <div className="company-ov-stats" style={{marginTop:6}}>
              <div className="ov-stat"><div className="ov-k">M1 현금</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m1)}</div></div>
              <div className="ov-stat"><div className="ov-k">M2 매출</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m2)}</div></div>
              <div className="ov-stat"><div className="ov-k">M3 부채</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m3)}</div></div>
              <div className="ov-stat"><div className="ov-k">M4 본업</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m4)}</div></div>
              <div className="ov-stat"><div className="ov-k">M5 자본</div><div className="ov-v" style={{fontSize:14}}>{fmtNum(node.m5)}</div></div>
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
          placeholder="⚠ 1차 데모: AI 응답은 미리 작성된 안내문"
          value=""
          disabled
          readOnly
        />
        <button disabled style={{opacity:0.4, cursor:'not-allowed'}}>↗</button>
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
    // Navigate to ghost company's sector, then select it
    const targetSectorId = sectorId || (() => {
      const RD = window.__realData || {};
      const node = RD.nodeByCode && RD.nodeByCode[code];
      if (!node) return null;
      const s = SECTOR_PALETTE.find(p => p.ko === node.s);
      return s ? s.id : null;
    })();
    if (!targetSectorId) return;
    enterSector(targetSectorId);
    setTimeout(() => {
      setActiveCompanyCode(code);
      setPhase('company');
    }, 1300);
  }, [enterSector]);

  const [corpOverlayTicker, setCorpOverlayTicker] = useState(null);
  const enterCorporation = useCallback(() => {
    if (!activeCompanyCode) return;
    setCorpOverlayTicker(activeCompanyCode);
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
                onSelectGhost={selectGhost}
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

      {/* ENTER CORPORATION overlay — v2 design-consistent fullscreen popup */}
      {corpOverlayTicker && (
        <div style={{
          position:'fixed', inset:0, zIndex:999,
          background:'rgba(2,4,12,0.88)', backdropFilter:'blur(18px)',
          display:'flex', flexDirection:'column',
        }}>
          {/* Header bar */}
          <div style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'10px 20px', borderBottom:'1px solid rgba(94,234,212,0.2)',
            background:'rgba(8,14,26,0.9)', flexShrink:0,
          }}>
            <div style={{display:'flex', alignItems:'center', gap:12}}>
              <span style={{width:8,height:8,borderRadius:'50%',background:'#5eead4',boxShadow:'0 0 8px #5eead4', display:'inline-block'}} />
              <span style={{fontFamily:'var(--font-mono,monospace)',fontSize:11,letterSpacing:'0.12em',color:'#5eead4'}}>CORPORATION DOSSIER</span>
              <span style={{fontFamily:'var(--font-mono,monospace)',fontSize:10,color:'#64748b',letterSpacing:'0.06em'}}>· {corpOverlayTicker}</span>
            </div>
            <button onClick={() => setCorpOverlayTicker(null)} style={{
              background:'transparent', border:'1px solid rgba(94,234,212,0.25)',
              color:'#94a3b8', fontFamily:'var(--font-mono,monospace)', fontSize:11,
              padding:'4px 14px', cursor:'pointer', letterSpacing:'0.08em',
              borderRadius:2,
            }}>✕ CLOSE</button>
          </div>
          {/* iframe — firm HTML */}
          <iframe
            src={`../../../docs/prototype/firm_${corpOverlayTicker}.html`}
            style={{flex:'1 1 0%', width:'100%', border:'none', background:'#020408'}}
            title={`firm-${corpOverlayTicker}`}
          />
          {/* Footer disclaimer */}
          <div style={{
            textAlign:'center', padding:'6px', fontFamily:'var(--font-mono,monospace)',
            fontSize:9, color:'#475569', borderTop:'1px solid rgba(94,234,212,0.1)',
            background:'rgba(8,14,26,0.9)', flexShrink:0,
          }}>
            ⚠ 과거 통계 기반 참고 정보 — 투자 조언 아님
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
