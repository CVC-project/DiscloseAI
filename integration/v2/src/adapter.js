/* adapter.js — bridge real data → standalone JSX globals.
 *
 * Standalone JSX (bundle.jsx) reads:
 *   - SECTOR_PALETTE: [{id, ko, en, color, cap}]
 *   - COMPANIES: { [sectorId]: [{code, name, en, cap, x, y}] }
 *   - RELATIONS: { [code]: [{code, type}] }   types: subsidiary|associate|significant|group|related|manual
 *
 * Our data:
 *   - graph_top50.json: nodes [{n, t, s, sz, mc, group, rl: ["name:type:value", ...]}]
 *   - eqs_summary.json: items with corp_code/ticker
 *   - top50.csv: rank/sector/corp_name/ticker (sector taxonomy)
 *
 * Strategy: load via DiscloseAI.loadAll(), build standalone-shaped globals,
 * stash on window.__realData, then dynamically inject bundle.jsx <script type=text/babel>.
 * On fetch failure we leave __realData undefined so bundle.jsx falls back to its mock literals.
 */
(function () {
  "use strict";

  // sector ko → {id, en, color}. universe 25 섹터 전량 등록 (universe/PLAN.md U-D7·§5.5 V-2).
  // 색 = 패밀리(계열) 그룹핑 — 관련 산업끼리 인접 색상. 배정 절차는 DESIGN.md §2.5 참조.
  // ⚠️ 신규 색 추가·변경은 DESIGN.md 절차 준수 + extract_data.py V-2 assert 통과 필수.
  // (구 12종 중 sectors.json에 없는 바이오/2차전지/디스플레이는 하위호환용으로 유지 — 미사용.)
  const SECTOR_DEF = {
    // 테크·전자 (teal→cyan→blue)
    "반도체":         { id: "semi",       en: "Semiconductor",   color: "#5eead4" },
    "전기전자부품":   { id: "elec_parts", en: "Electronic Parts", color: "#2dd4bf" },
    "소재":           { id: "materials",  en: "Materials",       color: "#67e8f9" },
    "플랫폼":         { id: "it",         en: "Platform",        color: "#60a5fa" },
    "통신":           { id: "tele",       en: "Telecom",         color: "#818cf8" },
    // 모빌리티·중공업 (violet→purple)
    "자동차":         { id: "auto",       en: "Automotive",      color: "#a78bfa" },
    "기계·장비":      { id: "machinery",  en: "Machinery",       color: "#c4b5fd" },
    "중공업·방산":    { id: "indust",     en: "Industrials",     color: "#c084fc" },
    "철강·금속":      { id: "steel",      en: "Steel & Metal",   color: "#a5b4fc" },
    // 금융 (amber→gold)
    "금융":           { id: "fin",        en: "Financials",      color: "#fbbf24" },
    "지주":           { id: "holding",    en: "Holdings",        color: "#fcd34d" },
    // 에너지·화학 (orange)
    "에너지":         { id: "energy",     en: "Energy",          color: "#f97316" },
    "건설":           { id: "cons",       en: "Construction",    color: "#fb923c" },
    "화학":           { id: "chem",       en: "Chemicals",       color: "#fdba74" },
    // 소비 (lime→green)
    "유통":           { id: "retail",     en: "Retail",          color: "#a3e635" },
    "식음료":         { id: "food",       en: "F&B",             color: "#bef264" },
    "레저·교육":      { id: "leisure",    en: "Leisure & Edu",   color: "#86efac" },
    // 헬스·뷰티 (pink→rose)
    "제약바이오":     { id: "pharma",     en: "Pharma & Bio",    color: "#f472b6" },
    "화장품":         { id: "cosmetics",  en: "Cosmetics",       color: "#f9a8d4" },
    "섬유·의류":      { id: "textile",    en: "Textile",         color: "#fda4af" },
    // 미디어 (magenta)
    "미디어":         { id: "media",      en: "Media",           color: "#e879f9" },
    // 서비스·중립
    "운송·물류":      { id: "logistics",  en: "Logistics",       color: "#7dd3fc" },
    "부동산":         { id: "realestate", en: "Real Estate",     color: "#d6bfa8" },
    "전문서비스":     { id: "prof_svc",   en: "Prof. Services",  color: "#cbd5e1" },
    "기타":           { id: "etc",        en: "Other",           color: "#94a3b8" },
    // 하위호환(구 top50 taxonomy, sectors.json 미포함 — 미사용)
    "바이오":         { id: "bio",        en: "Biotech",         color: "#f472b6" },
    "2차전지":        { id: "battery",    en: "Battery",         color: "#22d3ee" },
    "디스플레이":     { id: "display",    en: "Display",         color: "#fde047" },
  };

  // graph_top50 rl type → standalone REL_STYLES key.
  const REL_TYPE_MAP = {
    subsidiary:  "subsidiary",
    associate:   "associate",
    investment:  "significant",
    ftc_group:   "group",
  };

  // Korean company name → ticker (from graph_top50). Used to resolve rl strings.
  function buildNameTickerMap(nodes) {
    const m = new Map();
    for (const n of nodes) if (n.n && n.t) m.set(n.n, n.t);
    return m;
  }

  // Type priority: lower = more significant (shown first)
  const TYPE_PRIORITY = { subsidiary: 1, associate: 2, significant: 3, group: 4, related: 5, manual: 6 };

  function parseRelations(node, nameMap) {
    // Collect all types per target code, then pick highest-priority
    const byCode = new Map();
    for (const raw of node.rl || []) {
      const parts = String(raw).split(":");
      if (parts.length < 2) continue;
      const [name, rawType] = parts;
      const type = REL_TYPE_MAP[rawType];
      if (!type) continue;
      const code = nameMap.get(name);
      if (!code || code === node.t) continue;
      if (!byCode.has(code)) byCode.set(code, { code, name, types: [] });
      if (!byCode.get(code).types.includes(type)) byCode.get(code).types.push(type);
    }
    return Array.from(byCode.values()).map(({ code, name, types }) => {
      // Pick highest-priority type; flag if also has group (공정위 계열사 중복)
      types.sort((a, b) => (TYPE_PRIORITY[a] || 9) - (TYPE_PRIORITY[b] || 9));
      const type = types[0];
      const hasGroup = types.includes("group");
      const hasEquity = types.some(t => ["subsidiary","associate","significant"].includes(t));
      return { code, type, name, allTypes: types, hasGroup, hasEquity };
    });
  }

  // Build code→Korean name map from ALL rl strings (covers non-top50 related companies).
  function buildNameByCode(nodes) {
    const m = {};
    const nameMap = buildNameTickerMap(nodes);
    for (const node of nodes) {
      for (const raw of node.rl || []) {
        const parts = String(raw).split(":");
        if (parts.length < 2) continue;
        const [name, rawType] = parts;
        const type = REL_TYPE_MAP[rawType];
        if (!type) continue;
        const code = nameMap.get(name);
        if (code && !m[code]) m[code] = name;
      }
    }
    // Also add top50 companies themselves
    for (const n of nodes) if (n.t && n.n) m[n.t] = n.n;
    return m;
  }

  // Phyllotaxis layout in [-1, 1] disk, largest cap at center.
  function layoutCompanies(members) {
    if (!members.length) return [];
    const sorted = members.slice().sort((a, b) => (b.market_cap || b.mc || 0) - (a.market_cap || a.mc || 0));
    const out = [];
    const n = sorted.length;
    for (let i = 0; i < n; i++) {
      const m = sorted[i];
      let x = 0, y = 0;
      if (i > 0) {
        const ang = i * 2.39996;
        // Start at 0.45 so i=1 is far enough from center node, max 0.88 to avoid edge clip.
        const r = n === 1 ? 0 : 0.45 + ((i - 1) / Math.max(1, n - 1)) * 0.43;
        x = Math.cos(ang) * r;
        y = Math.sin(ang) * r;
      }
      // Cap value capped at 600 to prevent node radius from exceeding canvas.
      const capJo = m.market_cap ? Math.min(600, m.market_cap / 1e12) : (typeof m.mc === "number" ? Math.min(600, m.mc / 1e12) : Math.max(1, (m.sz || 1) * 5));
      out.push({
        code: m.t,
        name: m.n,
        en: m.n,         // english label not in our data; reuse Korean
        cap: Math.max(1, Math.round(capJo)),
        x, y,
      });
    }
    return out;
  }

  function buildPalette(sectors) {
    return sectors
      .filter((s) => SECTOR_DEF[s.ko] || SECTOR_DEF[s.name])
      .map((s) => {
        const ko = s.ko || s.name;
        const def = SECTOR_DEF[ko] || { id: s.id, en: (s.en || ko).toUpperCase(), color: "#94a3b8" };
        const totalJo = (s.capWon || 0) / 1e12;
        return {
          id: def.id,
          ko,
          en: def.en,
          color: def.color,
          cap: Math.max(1, Math.round(totalJo)),
          memberCount: s.memberCount,
          members: s.members,
          // universe(U2): 전량 기업 수 + LOD-1 배경 dots 좌표. top50 경로면 없음.
          count: s.count != null ? s.count : s.memberCount,
          dots: s.dots || [],
        };
      });
  }

  function buildCompaniesByPaletteId(palette, nodes) {
    const out = {};
    const koToId = new Map(palette.map((p) => [p.ko, p.id]));
    const bySector = new Map();
    for (const n of nodes) {
      const id = koToId.get(n.s);
      if (!id) continue;
      if (!bySector.has(id)) bySector.set(id, []);
      bySector.get(id).push(n);
    }
    for (const [id, members] of bySector) {
      out[id] = layoutCompanies(members);
    }
    return out;
  }

  function buildRelations(nodes) {
    const nameMap = buildNameTickerMap(nodes);
    const out = {};
    for (const n of nodes) {
      const rels = parseRelations(n, nameMap);
      if (rels.length) out[n.t] = rels;
    }
    // Add reverse edges (isIncoming: true) so A←B is visible when viewing B.
    // e.g. 삼성전자→삼성전기(associate) adds 삼성전기←삼성전자(associate, incoming).
    const nameByTicker = Object.fromEntries(nodes.map((n) => [n.t, n.n]));
    const forward = JSON.parse(JSON.stringify(out)); // snapshot before adding reverses
    for (const [srcCode, rels] of Object.entries(forward)) {
      for (const r of rels) {
        const tgt = r.code;
        if (!tgt) continue;
        if (!out[tgt]) out[tgt] = [];
        // Only add reverse if not already an outgoing edge from tgt→src
        if (!out[tgt].some((x) => x.code === srcCode)) {
          out[tgt].push({
            code: srcCode,
            type: r.type,          // keep same type for correct REL_STYLES
            name: nameByTicker[srcCode] || srcCode,
            allTypes: r.allTypes || [r.type],
            hasGroup: r.hasGroup,
            hasEquity: r.hasEquity,
            isIncoming: true,      // arrow points TOWARD active (A←B)
          });
        }
      }
    }
    return out;
  }

  async function injectBundleScript() {
    // Babel-standalone auto-transforms <script type="text/babel"> tags only at page load.
    // For dynamic injection we fetch the source ourselves, transform via Babel, then run.
    const url = "./src/bundle.jsx?v=k4c";
    const src = await fetch(url).then((r) => r.text());
    const out = window.Babel.transform(src, { presets: ["env", "react"] }).code;
    const s = document.createElement("script");
    s.text = out;
    document.body.appendChild(s);
  }

  async function boot() {
    const D = window.DiscloseAI || {};
    if (!D.loadAll) {
      console.warn("[adapter] DiscloseAI.loadAll missing; mounting with mock fallback.");
      injectBundleScript();
      return;
    }
    try {
      const result = await D.loadAll();
      const palette = buildPalette(result.sectors);
      const companies = buildCompaniesByPaletteId(palette, result.nodes);
      const relations = buildRelations(result.nodes);

      // Index by ticker for fast lookup in dossier panels.
      const nodeByCode = Object.fromEntries(result.nodes.map((n) => [n.t, n]));
      const discAll = result.discAll || [];
      const discByTicker = {};
      for (const d of discAll) {
        const t = d.ticker || d.stock_code;
        if (!t) continue;
        (discByTicker[t] = discByTicker[t] || []).push(d);
      }

      // dots: sector id → [[x,y,capBucket], ...] (LOD-1 배경 dots, U2 full 이전)
      const dots = {};
      for (const p of palette) if (p.dots && p.dots.length) dots[p.id] = p.dots;

      window.__realData = {
        sectors: palette,
        companies,
        relations,
        nodeByCode,
        nameByCode: buildNameByCode(result.nodes),
        discByTicker,
        discAll,
        scenarios: result.scenarios,
        meta: result.meta,
        usingMock: result.usingMock,
        usingUniverse: result.usingUniverse,
        dots,
        companiesIndex: result.companiesIndex || [],
        universeMeta: result.universeMeta || null,
      };
      console.log("[adapter] sectors:", palette.length,
                  "companies:", Object.values(companies).reduce((a, c) => a + c.length, 0),
                  "relations:", Object.keys(relations).length);
    } catch (e) {
      console.error("[adapter] boot failed; falling back to mock:", e);
    }
    injectBundleScript();
  }

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
