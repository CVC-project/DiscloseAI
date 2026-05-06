"""M1 v2 — 현금이익률 (Cash Earnings Ratio).

"본업에서 번 영업이익이 진짜 영업현금으로 돌아왔는가?"

설계: ``modules/financial/EQS_V2_DESIGN.md`` §M1 (+ 2026-04-27 보정: 100점 캡 1.0→2.0).

산출:
    R = (3년 누적 OCF) ÷ (3년 누적 영업이익)
    점수 변환 (선형 보간):
      R ≤ 0      → 0
      R = 1.0    → 75   (영업이익만큼 현금 유입)
      R = 2.0    → 100  (영업이익의 2배 현금 유입 — 매우 우량)
      R > 2.0    → 100

OCF의 "O"가 Operating(영업)이므로 분모도 영업단계 이익(operating_income)으로 맞춰
영업외 일회성 손익(자산처분·외화환산·법인세 변동)에 의한 비율 왜곡을 제거.

100점 캡을 1.0→2.0으로 늦춘 이유: KOSPI 우량주 다수가 R≥1.0이라 1.0 캡으로는
변별력 부족 (이전 분포에서 100점이 25/48). R=2.0 캡 + R=1.0=75점 anchor로
"이익만큼 들어왔으면 75점, 두 배 들어왔으면 100점" 단계적 평가.

예외:
- 3년 누적 영업이익 ≤ 0: 산출 보류 ("3년 누적 영업적자")
- 데이터 3년 미만: 가능한 연도(최소 1년)로 단축 산출, note에 n=2 등 표기
"""

from __future__ import annotations

from typing import List

from .types import FirmPanel, FirmYear, ModuleScore


def _recent_years(panel: FirmPanel, n: int = 3) -> List[FirmYear]:
    """최근 n년치 연도 데이터 (오름차순). 데이터가 적으면 가능한 만큼 반환."""
    return panel.years[-n:] if panel.years else []


def score_m1(panel: FirmPanel) -> ModuleScore:
    years = _recent_years(panel, 3)
    valid = [
        y for y in years
        if y.operating_income is not None and y.operating_cashflow is not None
    ]
    if not valid:
        return ModuleScore(name="M1", score=None, note="영업이익/OCF 결측 — 산출 불가")

    sum_ocf = sum(y.operating_cashflow for y in valid)
    sum_oi = sum(y.operating_income for y in valid)
    n = len(valid)

    if sum_oi <= 0:
        return ModuleScore(
            name="M1",
            score=None,
            raw=sum_oi,
            note=f"{n}년 누적 영업이익={sum_oi/1e8:.0f}억 ≤ 0 — 현금이익률 산출 불가",
        )

    R = sum_ocf / sum_oi
    if R <= 0:
        score = 0.0
    elif R <= 1.0:
        score = R * 75.0  # 0~75 선형 (R=1.0 → 75)
    elif R <= 2.0:
        score = 75.0 + (R - 1.0) * 25.0  # 75~100 선형 (R=2.0 → 100)
    else:
        score = 100.0
    n_tag = "" if n == 3 else f" — n={n} 단축"
    return ModuleScore(
        name="M1",
        score=round(score, 1),
        raw=R,
        note=f"3년 누적 OCF/영업이익={R:.2f}{n_tag}",
    )
