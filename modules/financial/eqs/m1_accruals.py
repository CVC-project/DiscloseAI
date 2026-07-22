"""M1 v2 — 현금이익률 (Cash Earnings Ratio).

"본업에서 번 영업이익이 진짜 영업현금으로 돌아왔는가?"

설계: ``docs/EQS_V3_CALIBRATION.md`` §M1.

산출:
    R = (3년 누적 OCF) ÷ (3년 누적 영업이익)
    점수 변환 (선형 보간):
      R ≤ 0      → 0
      R = 0.5    → 25   (이익의 절반만 현금 전환)
      R = 0.8    → 50   (현금 전환 부족)
      R = 1.0    → 80   (영업이익만큼 현금 유입)
      R ≥ 1.2    → 100  (이익보다 20% 이상 많은 현금 유입)

OCF의 "O"가 Operating(영업)이므로 분모도 영업단계 이익(operating_income)으로 맞춰
영업외 일회성 손익(자산처분·외화환산·법인세 변동)에 의한 비율 왜곡을 제거.

R=1.0은 회계이익과 영업현금이 일치한 기준점이며 80점이다. 1.2 이상은 매출채권·
재고의 현금 회수까지 양호한 상태로 보아 100점으로 캡을 둔다.

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


def score_m1(
    panel: FirmPanel,
    *,
    require_three_years: bool = False,
    short_history_weighting: bool = False,
) -> ModuleScore:
    years = _recent_years(panel, 3)
    valid = [
        y for y in years
        if y.operating_income is not None and y.operating_cashflow is not None
    ]
    if not valid:
        return ModuleScore(name="M1", score=None, note="영업이익/OCF 결측 — 산출 불가")

    if require_three_years and len(valid) < 3:
        return ModuleScore(name="M1", score=None, note="V3 비교에는 3개 사업연도 영업이익/OCF 필요")

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
    elif R <= 0.5:
        score = R * 50.0  # 0~25
    elif R <= 0.8:
        score = 25.0 + (R - 0.5) / 0.3 * 25.0  # 25~50
    elif R <= 1.0:
        score = 50.0 + (R - 0.8) / 0.2 * 30.0  # 50~80
    elif R <= 1.2:
        score = 80.0 + (R - 1.0) / 0.2 * 20.0  # 80~100
    else:
        score = 100.0
    confidence = {1: 0.40, 2: 0.70, 3: 1.00}[min(n, 3)]
    if short_history_weighting and n < 3:
        score = 50.0 + (score - 50.0) * confidence
    n_tag = "" if n == 3 else f" — {n}년 이력 신뢰도 {confidence:.0%}"
    return ModuleScore(
        name="M1",
        score=round(score, 1),
        raw=R,
        note=f"{n}년 누적 OCF/영업이익={R:.2f}{n_tag}",
        weight=confidence if short_history_weighting else 1.0,
    )
