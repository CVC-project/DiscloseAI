/* DiscloseAI v2 — mock.js
 *
 * fetch 실패 시 fallback용 mock 상수. 12 섹터 기본 색상·영문 매핑·간단 노드 샘플.
 * 정상 동작 시에는 사용되지 않으며, oncoming network/file:// 환경에서만 활성화.
 */
(function () {
  "use strict";

  // top50.csv `sector` distinct 결과 기준 12 섹터의 한글명 → 영문/색상 매핑.
  // 색상은 v2 standalone prototype의 팔레트(--cyan, --amber, --violet 등)에 맞춤.
  const SECTOR_META = {
    "반도체":         { en: "SEMICONDUCTOR", color: "#5eead4" },
    "금융":           { en: "FINANCIALS",    color: "#fbbf24" },
    "플랫폼":         { en: "PLATFORM",      color: "#4ade80" },
    "자동차":         { en: "AUTOMOTIVE",    color: "#a78bfa" },
    "바이오":         { en: "BIOTECH",       color: "#f87171" },
    "에너지":         { en: "ENERGY",        color: "#f97316" },
    "2차전지":        { en: "BATTERY",       color: "#60a5fa" },
    "중공업·방산":    { en: "INDUSTRIALS",   color: "#c084fc" },
    "디스플레이":     { en: "DISPLAY",       color: "#fde047" },
    "건설":           { en: "CONSTRUCTION",  color: "#a3e635" },
    "통신":           { en: "TELECOM",       color: "#f472b6" },
    "기타":           { en: "OTHER",         color: "#94a3b8" },
  };

  // EDGE TYPOLOGY 범례 — K-IFRS 지분율 분류 + 비-지분 (공정위·주석·수동 보정)
  const EDGE_LEGEND = {
    solid: [
      { label: "종속기업",   sub: ">50%",   color: "#ef4444", style: "solid" },
      { label: "관계기업",   sub: "20–50%", color: "#a78bfa", style: "solid" },
      { label: "유의적 투자", sub: "5–20%",  color: "#fbbf24", style: "solid" },
    ],
    dashed: [
      { label: "계열사",       sub: "공정위 지정 그룹",  color: "#fde047", style: "dashed" },
      { label: "특수관계자",    sub: "사업보고서 주석",   color: "#94a3b8", style: "dashed" },
      { label: "수동 보정",     sub: "manual override",  color: "#64748b", style: "dashed" },
    ],
  };

  // Mock 노드 (fetch 실패 시) — 최소 12개 정도, sector별 1~2개.
  const MOCK_NODES = [
    { n: "삼성전자",    t: "005930", s: "반도체",      sz: 1.6, mc: 480e12, group: "삼성", rl: [] },
    { n: "SK하이닉스",  t: "000660", s: "반도체",      sz: 1.3, mc: 220e12, group: "SK",    rl: [] },
    { n: "KB금융",      t: "105560", s: "금융",        sz: 1.0, mc: 32e12,  group: "KB",    rl: [] },
    { n: "신한지주",    t: "055550", s: "금융",        sz: 1.0, mc: 30e12,  group: "신한",  rl: [] },
    { n: "NAVER",       t: "035420", s: "플랫폼",      sz: 1.1, mc: 38e12,  group: "NAVER", rl: [] },
    { n: "카카오",      t: "035720", s: "플랫폼",      sz: 1.0, mc: 25e12,  group: "카카오", rl: [] },
    { n: "현대차",      t: "005380", s: "자동차",      sz: 1.2, mc: 55e12,  group: "현대차", rl: [] },
    { n: "기아",        t: "000270", s: "자동차",      sz: 1.0, mc: 45e12,  group: "현대차", rl: [] },
    { n: "삼성바이오로직스", t: "207940", s: "바이오", sz: 1.1, mc: 75e12, group: "삼성", rl: [] },
    { n: "SK이노베이션", t: "096770", s: "에너지",     sz: 0.9, mc: 12e12,  group: "SK",    rl: [] },
    { n: "LG에너지솔루션", t: "373220", s: "2차전지", sz: 1.2, mc: 95e12, group: "LG", rl: [] },
    { n: "한화에어로스페이스", t: "012450", s: "중공업·방산", sz: 1.0, mc: 25e12, group: "한화", rl: [] },
    { n: "LG디스플레이", t: "034220", s: "디스플레이", sz: 0.8, mc: 9e12, group: "LG", rl: [] },
    { n: "현대건설",    t: "000720", s: "건설",        sz: 0.8, mc: 4e12,  group: "현대차", rl: [] },
    { n: "SK텔레콤",    t: "017670", s: "통신",        sz: 0.9, mc: 12e12, group: "SK",    rl: [] },
  ];

  // KOSPI 마감가 mock (TopTabs status용 초기값)
  const KOSPI_MOCK = { value: 3142.8, delta: 0.42 };

  window.DiscloseAI = window.DiscloseAI || {};
  Object.assign(window.DiscloseAI, {
    SECTOR_META,
    EDGE_LEGEND,
    MOCK_NODES,
    KOSPI_MOCK,
  });
})();
