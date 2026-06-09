// companies.jsx — Mock company data + sector map renderer

const COMPANIES = {
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
const RELATIONS = {
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

function SectorMap({ sectorId, activeCompanyCode, onSelectCompany }) {
  const canvasRef = _useRef(null);
  const rafRef = _useRef(0);
  const startRef = _useRef(performance.now());
  const sizeRef = _useRef({ w: 0, h: 0, dpr: 1 });
  const nodesRef = _useRef([]);
  const [hoverCode, setHoverCode] = _useState(null);
  const bgStarsRef = _useRef([]);
  const shootingRef = _useRef([]);

  const sec = SECTOR_PALETTE.find(s => s.id === sectorId) || SECTOR_PALETTE[0];
  const companies = COMPANIES[sectorId] || COMPANIES.semi;

  // Compute gather positions: when active, related companies pull toward the active
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
        return { ...c, gx: 0, gy: 0, isActive: true };
      }
      if (relMap.has(c.code)) {
        // phyllotaxis-ish gather around the active node
        const n = [...relMap.keys()].indexOf(c.code);
        const total = relMap.size;
        const ang = (n / total) * Math.PI * 2 + 0.4;
        const r = 0.45;
        return { ...c, gx: Math.cos(ang) * r, gy: Math.sin(ang) * r, relType: relMap.get(c.code) };
      }
      // un-related: push to the edge & dim
      return { ...c, gx: c.x * 1.1, gy: c.y * 1.1, fade: true };
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

    // animated positions
    const animPos = layout.map(c => ({ x: c.x, y: c.y }));

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

      const cx = w / 2, cy = h / 2;
      const baseR = Math.min(w, h) * 0.34;

      // Draw relationship edges first
      if (activeCompanyCode) {
        const active = layout.find(c => c.code === activeCompanyCode);
        if (active) {
          const rels = RELATIONS[activeCompanyCode] || [];
          rels.forEach(r => {
            const ti = layout.findIndex(c => c.code === r.code);
            if (ti < 0) return;
            const ai = layout.findIndex(c => c.code === activeCompanyCode);
            const ax = cx + animPos[ai].x * baseR;
            const ay = cy + animPos[ai].y * baseR;
            const tx = cx + animPos[ti].x * baseR;
            const ty = cy + animPos[ti].y * baseR;
            const style = REL_STYLES[r.type];
            ctx.strokeStyle = style.color + 'cc';
            ctx.lineWidth = 1.5;
            ctx.setLineDash(style.dash);
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(tx, ty);
            ctx.stroke();
            ctx.setLineDash([]);
          });
        }
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
      nodesRef.current = positions;

      rafRef.current = requestAnimationFrame(draw);
    };
    draw();

    const onMove = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = null, bestD = 30;
      for (const p of nodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = p.c.code; }
      }
      setHoverCode(best);
      cvs.style.cursor = best ? 'pointer' : 'default';
    };
    const onClick = (e) => {
      const rect = cvs.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = null, bestD = 30;
      for (const p of nodesRef.current) {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = p.c.code; }
      }
      if (best) onSelectCompany?.(best);
    };
    cvs.addEventListener('mousemove', onMove);
    cvs.addEventListener('click', onClick);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      cvs.removeEventListener('mousemove', onMove);
      cvs.removeEventListener('click', onClick);
    };
  }, [layout, activeCompanyCode, hoverCode, sectorId]);

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
