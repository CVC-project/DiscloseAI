"""M5 v2 — 자본 성장성 (Equity Growth).

"회사가 벌어서 자기 돈을 키워나가고 있는가?"

설계: ``modules/financial/EQS_V2_DESIGN.md`` §M5 (+ 2026-04-27 보정: 100점 캡 +10%→+30%).

산출:
    CAGR = (자본총계[t] ÷ 자본총계[t-2])^(1/2) - 1
    점수 변환 (선형 보간, 5단계):
      CAGR ≤ -10%/yr  → 0
      CAGR = 0%/yr    → 50
      CAGR = +10%/yr  → 80   (이전 100 → 80)
      CAGR = +20%/yr  → 95
      CAGR ≥ +30%/yr  → 100

이전 정의(±10%/yr 캡)는 KOSPI 우량주 다수가 +10%/yr 초과해 100점에 몰림(24/48).
+10%/yr=80점 anchor + +30%/yr=100점 캡으로 변별력 확보.

예외:
- 자본총계[t-2] ≤ 0: 0점 + "2년 전 자본잠식"
- 자본총계[t]   ≤ 0: 0점 + "현재 자본잠식 — 상장폐지 사유"
- 데이터 < 2년: 산출 보류
"""

from __future__ import annotations

from .types import FirmPanel, ModuleScore


def score_m5(panel: FirmPanel) -> ModuleScore:
    if len(panel.years) < 3:
        return ModuleScore(
            name="M5",
            score=None,
            note=f"패널 {len(panel.years)}년 — t와 t-2 자본 필요(최소 3년)",
        )

    curr = panel.years[-1]
    base = panel.years[-3]  # t-2

    if curr.total_equity is None or base.total_equity is None:
        return ModuleScore(name="M5", score=None, note="자본총계 결측")

    if base.total_equity <= 0:
        return ModuleScore(
            name="M5",
            score=0.0,
            raw=None,
            note=f"2년 전 자본잠식(자본={base.total_equity/1e8:.0f}억)",
        )
    if curr.total_equity <= 0:
        return ModuleScore(
            name="M5",
            score=0.0,
            raw=None,
            note="현재 자본잠식 — 상장폐지 사유",
        )

    ratio = curr.total_equity / base.total_equity
    cagr = ratio ** 0.5 - 1

    # 5단계 선형 보간: -10%→0, 0%→50, +10%→80, +20%→95, +30%+→100
    if cagr <= -0.10:
        score = 0.0
    elif cagr <= 0.0:
        score = (cagr + 0.10) / 0.10 * 50.0  # -10%~0% → 0~50
    elif cagr <= 0.10:
        score = 50.0 + (cagr / 0.10) * 30.0  # 0%~+10% → 50~80
    elif cagr <= 0.20:
        score = 80.0 + ((cagr - 0.10) / 0.10) * 15.0  # +10%~+20% → 80~95
    elif cagr <= 0.30:
        score = 95.0 + ((cagr - 0.20) / 0.10) * 5.0  # +20%~+30% → 95~100
    else:
        score = 100.0
    return ModuleScore(
        name="M5",
        score=round(score, 1),
        raw=cagr,
        note=f"자본 CAGR {cagr*100:+.1f}%/yr ({base.year}→{curr.year}, 자본 ×{ratio:.2f})",
    )
