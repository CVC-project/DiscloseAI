// galaxy.jsx — Realistic Andromeda-style spiral galaxy + 3D-tilted solar system

const { useRef, useEffect, useMemo } = React;

const SECTOR_PALETTE = [
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
