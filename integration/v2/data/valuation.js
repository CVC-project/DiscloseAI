/* DiscloseAI v2 — valuation.js
 *
 * dashboard.html의 _calcValuation·_percentileBadge·_trillionFmt·_sparkline 포팅.
 * IIFE + window.DiscloseAI 글로벌로 export (Babel in-browser 환경, 빌드 도구 없음).
 *
 * 원본: 구 v1 dashboard.html L4844-4920 — v1 폐지(2026-07-13), 이 포팅본이 정본. 원본은 git 이력
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

  // 큰 단위 시총(원) → "조원" 라벨 (예: 980조원, 1,461조원).
  function trillionLabel(won) {
    if (!won) return "-";
    const t = won / 1e12;
    if (t >= 1000) return Math.round(t).toLocaleString() + "조원";
    if (t >= 100) return Math.round(t) + "조원";
    if (t >= 10) return t.toFixed(0) + "조원";
    return t.toFixed(1) + "조원";
  }

  // "1262조"·"850억" 같은 표시용 문자열 시총을 원(KRW) 단위 숫자로 변환.
  // graph_top50.json의 `mc` 필드(모든 노드 문자열)가 이 형식이라, eqs 파이프라인의
  // 정식 market_cap이 없는 노드(현재 다수)의 유일한 시총 출처다.
  function parseMcString(s) {
    if (typeof s !== "string" || s === "-") return null;
    const m = s.match(/([0-9.]+)\s*(조|억|만)?/);
    if (!m) return null;
    const num = parseFloat(m[1]);
    if (!Number.isFinite(num)) return null;
    const unit = m[2];
    if (unit === "억") return num * 1e8;
    if (unit === "만") return num * 1e4;
    return num * 1e12;
  }

  // 노드 하나의 시총(원) — 정식 market_cap 우선, 그다음 mc(숫자|문자열).
  //
  // ★2026-08-02 (FN-015) `mc`는 **두 형태**로 들어온다 — 규약을 리졸버마다 다르게
  // 가정하면 조용히 죽는다. universe 경로에서 loader가 `mc: parseMcWon(n.mc)`로
  // **숫자(원)**를 넣는데(loader.js), 여기서는 parseMcString이 `typeof s !== "string"`
  // 이면 즉시 null이라 **400개 전량 null**이 됐다. market_cap도 eqs_summary에서
  // 47/47 결측이라 1차 분기가 못 받쳐 PER·PBR·섹터 P/E·시총 라벨이 통째로 사라졌다
  // (실측: 삼성전자 시가총액이 레이아웃용 클램프값 600조원으로 오표기).
  // adapter.js `_capJo`는 이미 `typeof m.mc === "number"` 분기를 갖고 정상 동작했다
  // — 같은 입력에 두 리졸버가 다른 답을 내던 것이 근본 원인이라 규약을 통일한다.
  function resolveMarketCap(n) {
    if (!n) return null;
    if (n.market_cap) return n.market_cap;
    if (typeof n.mc === "number") return Number.isFinite(n.mc) ? n.mc : null;
    return parseMcString(n.mc);
  }

  // 섹터 집계 PER — Σ시총 ÷ Σ당기순이익(흑자 기업만). 지수 제공사들이 쓰는 표준 방식.
  // 표본이 없거나 결과가 통계적으로 무의미할 정도로 크면(적자에 가까운 소수 기업이
  // 왜곡) null 반환 — 초보 투자자에게 혼란만 주는 숫자를 보여주지 않는다.
  function computeSectorPE(members) {
    if (!Array.isArray(members) || !members.length) return null;
    let capSum = 0;
    let niSum = 0;
    for (const m of members) {
      const mc = resolveMarketCap(m);
      const ni = m && m.net_income_raw;
      if (mc && ni != null && ni > 0) {
        capSum += mc;
        niSum += ni;
      }
    }
    if (!capSum || !niSum) return null;
    const per = capSum / 1e8 / niSum;
    return Number.isFinite(per) && per > 0 && per < 200 ? +per.toFixed(1) : null;
  }

  // PER·PBR·ROE 계산 — dashboard L4883
  function calcValuation(n) {
    let mc = resolveMarketCap(n);
    let ni = n.net_income_raw;
    let eq = n.equity_raw;
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
    parseMcString,
    resolveMarketCap,
    computeSectorPE,
    calcValuation,
    percentileBadge,
    sparklinePath,
  });
})();
