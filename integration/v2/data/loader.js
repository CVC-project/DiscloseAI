/* DiscloseAI v2 — loader.js
 *
 * 4개 JSON fetch (graph_top50 + eqs_summary + disclosures + price_scenarios)
 * + ticker(6자리) 인덱싱 + 노드 enrich + sector aggregate.
 *
 * `Promise.allSettled` + try/catch로 graceful degrade. 어떤 fetch가 실패해도
 * 다른 데이터로 계속 동작. graph_top50이 실패하면 mock.js의 MOCK_NODES fallback.
 *
 * 참조: dashboard.html L4970-5085 (fetch + 인덱싱 + 노드 enrich)
 */
(function () {
  "use strict";

  const D = window.DiscloseAI || {};
  const { trillionFmt, trillionLabel } = D;
  const { eqsNarration } = D;

  // 보정의 재현 가능한 원문은 JSON과 문서에 남기되, 화면에는 초보 투자자가
  // 읽기 쉬운 지표 설명만 표시한다.
  function publicEqsNote(note) {
    return (note || "").replace(/\s*\(동종업계[^)]*\)/g, "");
  }

  // 4개 JSON URL — v2/index.html(integration/v2/) 기준 상대경로.
  // 4개 모두 integration/data 공유 (graph_top50은 extract_data.py가 modules/relation에서 동기화한 사본).
  const URLS = {
    graph: "../data/graph_top50.json",
    eqs:   "../data/eqs_summary.json",
    disc:  "../data/disclosures.json",
    price: "../data/price_scenarios.json",
  };

  async function tryFetch(url) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } catch (e) {
      console.warn("[v2 loader] fetch fail:", url, e.message);
      return null;
    }
  }

  // 노드 한 개에 financial / disclosure / price 데이터 주입.
  // dashboard.html L5011-5085의 로직을 함수로 추출 (외형 유지).
  function enrichNode(n, eqsByTicker, discByTicker, stmtByTicker, scenariosByTicker) {
    const t = n.t;
    const out = { ...n };
    const fin = eqsByTicker[t];
    if (fin) {
      out.has_financial = true;
      out.market_cap = fin.market_cap ?? null;
      out.dart_url = fin.dart_url ?? null;
      out.industry_code = fin.industry_code ?? null;
      out.is_financial_biz = fin.is_financial === true;
      out.latest_year = fin.latest_year ?? null;
      out.eqs = fin.eqs_total != null ? Math.round(fin.eqs_total) : null;
      out.gr = fin.eqs_grade || "-";
      out.eqs_modules = fin.eqs_modules || {};
      out.eqs_profile_note = fin.eqs_profile_note || null;
      out.m1 = fin.eqs_m1 != null ? Math.round(fin.eqs_m1) : null;
      out.m2 = fin.eqs_m2 != null ? Math.round(fin.eqs_m2) : null;
      out.m3 = fin.eqs_m3 != null ? Math.round(fin.eqs_m3) : null;
      out.m4 = fin.eqs_m4 != null ? Math.round(fin.eqs_m4) : null;
      out.m5 = fin.eqs_m5 != null ? Math.round(fin.eqs_m5) : null;
      out.f1 = fin.eqs_modules && fin.eqs_modules.F1 && fin.eqs_modules.F1.score != null ? Math.round(fin.eqs_modules.F1.score) : null;
      out.f2 = fin.eqs_modules && fin.eqs_modules.F2 && fin.eqs_modules.F2.score != null ? Math.round(fin.eqs_modules.F2.score) : null;
      out.f3 = fin.eqs_modules && fin.eqs_modules.F3 && fin.eqs_modules.F3.score != null ? Math.round(fin.eqs_modules.F3.score) : null;
      out.f4 = fin.eqs_modules && fin.eqs_modules.F4 && fin.eqs_modules.F4.score != null ? Math.round(fin.eqs_modules.F4.score) : null;
      out.f5 = fin.eqs_modules && fin.eqs_modules.F5 && fin.eqs_modules.F5.score != null ? Math.round(fin.eqs_modules.F5.score) : null;
      out.eqs_method = fin.eqs_method || null;
      out.eqs_excluded = fin.eqs_excluded || [];
      out.eqs_module_notes = Object.fromEntries(
        Object.entries(fin.eqs_module_notes || {}).map(([key, note]) => [
          key,
          publicEqsNote(note),
        ])
      );
      out.m1t = out.eqs_module_notes.M1 || eqsNarration(1, out.m1);
      out.m2t = out.eqs_module_notes.M2 || eqsNarration(2, out.m2);
      out.m3t = out.eqs_module_notes.M3 || eqsNarration(3, out.m3);
      out.m4t = out.eqs_module_notes.M4 || eqsNarration(4, out.m4);
      out.m5t = out.eqs_module_notes.M5 || eqsNarration(5, out.m5);
      out.rv = trillionFmt(fin.revenue);
      out.oi = trillionFmt(fin.operating_income);
      out.ni = trillionFmt(fin.net_income);
      out.ta = fin.total_assets != null ? Math.round(fin.total_assets / 10000) : "-";
      out.tl = fin.total_liabilities != null ? Math.round(fin.total_liabilities / 10000) : "-";
      out.eq = fin.total_equity != null ? Math.round(fin.total_equity / 10000) : "-";
      out.dr =
        fin.total_equity && fin.total_equity > 0 && fin.total_liabilities != null
          ? Math.round((fin.total_liabilities / fin.total_equity) * 100)
          : null;
      out.ocf = trillionFmt(fin.operating_cashflow);
      out.icf = trillionFmt(fin.investing_cashflow);
      out.fcf = trillionFmt(fin.financing_cashflow);
      out.ocf_raw = fin.operating_cashflow;
      out.icf_raw = fin.investing_cashflow;
      out.fcf_raw = fin.financing_cashflow;
      out.oim =
        fin.revenue && fin.operating_income != null
          ? ((fin.operating_income / fin.revenue) * 100).toFixed(1)
          : null;
      out.history = fin.history || null;
      out.percentile = fin.percentile || null;
      out.net_income_raw = fin.net_income;
      out.equity_raw = fin.total_equity;
    } else {
      out.has_financial = false;
    }

    const recentDisc = discByTicker[t] || [];
    out.has_disclosure = recentDisc.length > 0;
    out.disc = recentDisc.slice(0, 5).map((d) => ({
      title: d.title || "",
      date: d.disclosure_date || "",
      type: d.disclosure_type || "",
      summary: d.summary || "",
      high_impact: !!d.high_impact,
      dilution_ratio: d.dilution_ratio,
    }));
    out.statements = stmtByTicker[t] || [];

    out.tmAll = scenariosByTicker[t] || [];
    out.has_quiz = out.tmAll.length > 0;
    return out;
  }

  // 12 섹터 자동 추출 + 시총·기업수 집계
  function aggregateSectors(nodes) {
    const map = new Map();
    nodes.forEach((n) => {
      const s = n.s || "기타";
      if (!map.has(s)) map.set(s, { name: s, members: [], totalCapWon: 0 });
      const e = map.get(s);
      e.members.push(n);
      // graph_top50의 mc는 항상 문자열("1262조")이라 예전의 `typeof n.mc === "number"`
      // 폴백은 한 번도 참이 될 수 없었다 — resolveMarketCap이 그 문자열까지 파싱한다.
      const mc = D.resolveMarketCap ? D.resolveMarketCap(n) : n.market_cap;
      if (mc) e.totalCapWon += mc;
    });
    const SM = D.SECTOR_META || {};
    const sectors = Array.from(map.values()).map((e) => {
      const meta = SM[e.name] || { en: e.name.toUpperCase(), color: "#94a3b8" };
      return {
        id: slugify(e.name),
        ko: e.name,
        en: meta.en,
        color: meta.color,
        capWon: e.totalCapWon,
        cap: trillionLabel(e.totalCapWon),
        memberCount: e.members.length,
        members: e.members,
      };
    });
    sectors.sort((a, b) => b.capWon - a.capWon);
    return sectors;
  }

  function slugify(s) {
    return (s || "")
      .replace(/[\s·.()/&]+/g, "_")
      .replace(/[^a-zA-Z0-9가-힣_]/g, "")
      .toLowerCase();
  }

  // DAILY HIGHLIGHTS — disclosures 중 high_impact=true 최신 N건
  function dailyHighlights(discAll, sectorKo, n = 3) {
    if (!Array.isArray(discAll)) return [];
    const items = discAll
      .filter((d) => d && d.high_impact)
      .filter((d) => !sectorKo || (d.sector && d.sector === sectorKo) || !sectorKo)
      .slice()
      .sort((a, b) => (b.disclosure_date || "").localeCompare(a.disclosure_date || ""));
    return items.slice(0, n).map((d) => ({
      time: (d.disclosure_date || "").slice(5).replace("-", "/"),
      title: d.title || "",
      corp_name: d.corp_name || "",
      type: d.disclosure_type || "",
      ticker: d.ticker || d.stock_code || "",
    }));
  }

  // Sector 단위 highlights — 해당 섹터 ticker로 필터.
  // high_impact 우선, 없으면 최근 공시 fallback (현재 데이터는 high_impact 1건뿐).
  function highlightsForSector(discAll, members, n = 3) {
    if (!Array.isArray(discAll) || !members) return [];
    const tickers = new Set(members.map((m) => m.t));
    const inSector = discAll
      .filter((d) => d && tickers.has(d.ticker || d.stock_code))
      .slice()
      .sort((a, b) => (b.disclosure_date || "").localeCompare(a.disclosure_date || ""));
    const high = inSector.filter((d) => d.high_impact);
    const items = high.length >= n ? high : [...high, ...inSector.filter((d) => !d.high_impact)];
    return items.slice(0, n).map((d) => ({
      time: (d.disclosure_date || "").slice(5).replace("-", "/"),
      title: (d.title || "").trim(),
      corp_name: d.corp_name || "",
      type: d.disclosure_type || "",
      ticker: d.ticker || d.stock_code || "",
      high_impact: !!d.high_impact,
    }));
  }

  async function loadAll() {
    const [graph, eqs, disc, price] = await Promise.all([
      tryFetch(URLS.graph),
      tryFetch(URLS.eqs),
      tryFetch(URLS.disc),
      tryFetch(URLS.price),
    ]);

    const usingMock = !graph;
    const relData = graph || D.MOCK_NODES || [];

    // ticker 인덱스 — dashboard L4990-5006
    const eqsByTicker = Object.fromEntries(
      ((eqs && eqs.data) || []).map((d) => [d.ticker, d])
    );
    const discByTicker = {};
    ((disc && disc.disclosures) || []).forEach((d) => {
      if (!d.ticker) return;
      (discByTicker[d.ticker] = discByTicker[d.ticker] || []).push(d);
    });
    const stmtByTicker = {};
    ((disc && disc.statements) || []).forEach((s) => {
      if (!s.ticker) return;
      (stmtByTicker[s.ticker] = stmtByTicker[s.ticker] || []).push(s);
    });
    const scenariosByTicker = {};
    ((price && price.data) || []).forEach((s) => {
      if (!s.ticker) return;
      (scenariosByTicker[s.ticker] = scenariosByTicker[s.ticker] || []).push(s);
    });

    const nodes = relData.map((n) =>
      enrichNode(n, eqsByTicker, discByTicker, stmtByTicker, scenariosByTicker)
    );
    const sectors = aggregateSectors(nodes);

    return {
      ok: !usingMock,
      usingMock,
      nodes,
      sectors,
      scenarios: (price && price.data) || [],
      discAll: (disc && disc.disclosures) || [],
      stmtAll: (disc && disc.statements) || [],
      meta: {
        graph: !!graph,
        eqs: !!eqs,
        disc: !!disc,
        price: !!price,
      },
    };
  }

  window.DiscloseAI = window.DiscloseAI || {};
  Object.assign(window.DiscloseAI, {
    loadAll,
    enrichNode,
    aggregateSectors,
    dailyHighlights,
    highlightsForSector,
  });
})();
