/* DiscloseAI v2 — narration.js
 *
 * dashboard.html의 _eqsNarration·_eqsBucket 포팅.
 * EQS v2 5모듈 × 3단계(good/mid/bad) 텍스트 + 라벨·색상 상수.
 *
 * 원본: 구 v1 dashboard.html L3685(mods 배열)+L4939(_eqsNarration) — v1 폐지(2026-07-13), 이 포팅본이 정본. 원본은 git 이력
 */
(function () {
  "use strict";

  // EQS v2 5모듈 라벨 + 색상 (PROGRESS.md Phase E 결정)
  const MODS = [
    { id: "M1", name: "현금이익률",      color: "#4da6ff" },
    { id: "M2", name: "매출회수 건전성", color: "#f87171" },
    { id: "M3", name: "부채 건전성",     color: "#fbbf24" },
    { id: "M4", name: "본업 안정성",     color: "#4ade80" },
    { id: "M5", name: "자본 성장성",     color: "#7c6cf0" },
  ];

  function eqsBucket(score) {
    if (score == null || !Number.isFinite(score)) return "mid";
    if (score >= 70) return "good";
    if (score >= 40) return "mid";
    return "bad";
  }

  // dashboard L4939 그대로
  const NARRATION_TEXTS = {
    1: {
      good: "영업이익이 현금으로 충분히 회수됨 — 회계 이익이 실제 현금.",
      mid: "현금 회수가 영업이익 수준. 추세 모니터링 권장.",
      bad: "영업이익 대비 현금 회수 부족 — 외상이 쌓이는 신호.",
    },
    2: {
      good: "매출 증가 속도가 외상 증가보다 빠름 — 매출이 진짜 현금으로 회수.",
      mid: "매출과 외상 증가가 비슷한 수준 — 정상 범위.",
      bad: "외상이 매출보다 빠르게 늘고 있음 — 매출 신뢰도 점검 필요.",
    },
    3: {
      good: "부채비율이 업종 양호선 이내 — 자본 부담 낮음.",
      mid: "부채비율이 업종 평균 구간 — 추세 관찰 필요.",
      bad: "부채비율이 업종 위험선 이상 — 이자 부담·신용도 점검.",
    },
    4: {
      good: "영업이익률이 업종 우수선 위·변동폭 안정 — 본업 꾸준.",
      mid: "본업 수익은 평균 수준이나 변동폭 다소 큼.",
      bad: "본업 수익이 업종 평균 이하 또는 변동폭 과대.",
    },
    5: {
      good: "자기자본이 빠르게 누적 — 주주 몫이 커지는 속도 양호.",
      mid: "자본 성장 정체 — 이익 환원과 사내유보 균형 확인.",
      bad: "자본 감소 추세 — 적자·자사주매입·배당 환원 등 원인 점검.",
    },
  };

  function eqsNarration(idx, score) {
    const b = eqsBucket(score);
    const set = NARRATION_TEXTS[idx];
    if (!set) return "";
    return set[b] || "";
  }

  // 종합 점수 → 등급(A/B/C/D/F) 라벨 색상
  function gradeColor(grade) {
    switch ((grade || "").toUpperCase()) {
      case "A": return "#4ade80";
      case "B": return "#5eead4";
      case "C": return "#fbbf24";
      case "D": return "#f97316";
      case "F": return "#f87171";
      default: return "#94a3b8";
    }
  }

  window.DiscloseAI = window.DiscloseAI || {};
  Object.assign(window.DiscloseAI, {
    EQS_MODS: MODS,
    eqsBucket,
    eqsNarration,
    gradeColor,
  });
})();
