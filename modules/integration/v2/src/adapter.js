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

  // sector ko → {id, en, color}. Covers the 12 distinct sectors in top50.csv.
  const SECTOR_DEF = {
    "반도체":         { id: "semi",    en: "Semiconductor", color: "#5eead4" },
    "금융":           { id: "fin",     en: "Financials",    color: "#fbbf24" },
    "플랫폼":         { id: "it",      en: "Platform",      color: "#60a5fa" },
    "자동차":         { id: "auto",    en: "Automotive",    color: "#a78bfa" },
    "바이오":         { id: "bio",     en: "Biotech",       color: "#f472b6" },
    "에너지":         { id: "energy",  en: "Energy",        color: "#f97316" },
    "2차전지":        { id: "battery", en: "Battery",       color: "#22d3ee" },
    "중공업·방산":    { id: "indust",  en: "Industrials",   color: "#c084fc" },
    "디스플레이":     { id: "display", en: "Display",       color: "#fde047" },
    "건설":           { id: "cons",    en: "Construction",  color: "#fb923c" },
    "통신":           { id: "tele",    en: "Telecom",       color: "#818cf8" },
    "기타":           { id: "etc",     en: "Other",         color: "#94a3b8" },
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

  function parseRelations(node, nameMap) {
    const out = [];
    const seen = new Set();
    for (const raw of node.rl || []) {
      const parts = String(raw).split(":");
      if (parts.length < 2) continue;
      const [name, rawType] = parts;
      const type = REL_TYPE_MAP[rawType];
      if (!type) continue;
      const code = nameMap.get(name);
      if (!code || code === node.t) continue;
      const key = code + ":" + type;
      if (seen.has(key)) continue;
      seen.add(key);
      // Store the Korean company name alongside code for companies not in top50
      out.push({ code, type, name });
    }
    return out;
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
    // Add reverse edges so bidirectional relations are visible.
    // e.g. 삼성전자→삼성전기 (associate) also adds 삼성전기→삼성전자 (group).
    const nameByTicker = Object.fromEntries(nodes.map((n) => [n.t, n.n]));
    for (const [srcCode, rels] of Object.entries(out)) {
      for (const r of rels) {
        const tgt = r.code;
        if (!tgt) continue;
        if (!out[tgt]) out[tgt] = [];
        // Only add if not already present (by code)
        if (!out[tgt].some((x) => x.code === srcCode)) {
          out[tgt].push({ code: srcCode, type: "group", name: nameByTicker[srcCode] || srcCode });
        }
      }
    }
    return out;
  }

  async function injectBundleScript() {
    // Babel-standalone auto-transforms <script type="text/babel"> tags only at page load.
    // For dynamic injection we fetch the source ourselves, transform via Babel, then run.
    const url = "./src/bundle.jsx?v=k3b";
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
