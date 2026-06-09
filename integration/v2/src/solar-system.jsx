// solar-system.jsx — 3D-tilted solar system inside a simplified galaxy backdrop
const { useRef, useEffect, useState, useMemo } = React;

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
