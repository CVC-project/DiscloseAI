/* DiscloseAI v2 — valuation.js
 *
 * dashboard.html의 _calcValuation·_percentileBadge·_trillionFmt·_sparkline 포팅.
 * IIFE + window.DiscloseAI 글로벌로 export (Babel in-browser 환경, 빌드 도구 없음).
 *
 * 참조: modules/integration/dashboard.html L4844-4920
 */
(function () {
  "use strict";

  // 억원 → 조원 변환 (소수 1자리), null 처리.
  function trillionFmt(v) {
    if (v == null || !Number.isFinite(v)) return "-";
    const t = v / 10000;
    if (Math.abs(t) >= 100) return Math.round(t).toString();
    if (Math.abs(t) >= 10) return t.toFixed(1);
    return t.toFixed(2);
  }

  // 큰 단위 시총(원) → "T" 라벨 (예: 980T, 1,461T).
  function trillionLabel(won) {
    if (!won) return "-";
    const t = won / 1e12;
    if (t >= 1000) return Math.round(t).toLocaleString() + "T";
    if (t >= 100) return Math.round(t) + "T";
    if (t >= 10) return t.toFixed(0) + "T";
    return t.toFixed(1) + "T";
  }

  // PER·PBR·ROE 계산 — dashboard L4883
  function calcValuation(n) {
    let mc = n.market_cap;
    let ni = n.net_income_raw;
    let eq = n.equity_raw;
    if (mc == null && typeof n.mc === "string" && n.mc !== "-") {
      const m = n.mc.match(/([0-9.]+)\s*(조|억|만)?/);
      if (m) {
        const num = parseFloat(m[1]);
        const unit = m[2];
        if (Number.isFinite(num)) {
          if (unit === "억") mc = num * 1e8;
          else if (unit === "만") mc = num * 1e4;
          else mc = num * 1e12;
        }
      }
    }
    if (ni == null && n.ni != null && n.ni !== "-") {
      const v = parseFloat(n.ni);
      if (!isNaN(v)) ni = v * 10000;
    }
    if (eq == null && n.eq != null && n.eq !== "-") {
      const v = parseFloat(n.eq);
      if (!isNaN(v)) eq = v * 10000;
    }
    const out = { per: null, pbr: null, roe: null };
    if (mc != null && ni != null && ni > 0) out.per = +(mc / 1e8 / ni).toFixed(1);
    if (mc != null && eq != null && eq > 0) out.pbr = +(mc / 1e8 / eq).toFixed(2);
    if (ni != null && eq != null && eq > 0) out.roe = +((ni / eq) * 100).toFixed(1);
    return out;
  }

  // 동종업계 백분위 뱃지 — 0~100, 100=업계 1등. 표본 < 3이면 빈 문자열.
  // dashboard L4873
  function percentileBadge(pct, sectorSize) {
    if (pct == null || !Number.isFinite(pct)) return null;
    if (sectorSize != null && sectorSize < 3) return null;
    const topPct = Math.max(1, Math.round(100 - pct));
    const color = topPct <= 30 ? "#4ade80" : topPct <= 70 ? "#fbbf24" : "#f87171";
    return { topPct, color, label: `업계 상위 ${topPct}%` };
  }

  // SVG path 문자열 — dashboard L4844 (이번 v2에선 React로 path만 반환)
  function sparklinePath(values, opts = {}) {
    if (!Array.isArray(values)) return null;
    const w = opts.w || 60,
      h = opts.h || 16,
      pad = opts.pad || 1;
    const valid = values.filter((v) => v != null && Number.isFinite(v));
    if (valid.length < 2) return null;
    const min = Math.min(...valid, 0);
    const max = Math.max(...valid, 0);
    const range = max - min || 1;
    const xStep = (w - pad * 2) / (values.length - 1);
    let d = "";
    let lastValid = null;
    let started = false;
    values.forEach((v, i) => {
      if (v == null || !Number.isFinite(v)) {
        started = false;
        return;
      }
      const x = pad + i * xStep;
      const y = h - pad - ((v - min) / range) * (h - pad * 2);
      d += (started ? " L " : " M ") + `${x.toFixed(1)} ${y.toFixed(1)}`;
      started = true;
      lastValid = [x, y];
    });
    if (!lastValid) return null;
    return { d, w, h, dot: { x: lastValid[0], y: lastValid[1] } };
  }

  window.DiscloseAI = window.DiscloseAI || {};
  Object.assign(window.DiscloseAI, {
    trillionFmt,
    trillionLabel,
    calcValuation,
    percentileBadge,
    sparklinePath,
  });
})();
