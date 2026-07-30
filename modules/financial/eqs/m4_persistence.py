"""M4 v2 — 본업 안정성 (Operating Margin Stability).

"본업이 꾸준히 돈을 내는가, 아니면 들쭉날쭉한가? — 같은 업종 평균과 비교해서."

설계: ``modules/financial/EQS_V2_DESIGN.md`` §M4.

산출:
    OM[y] = OperatingIncome[y] ÷ Revenue[y]   (y = t-2, t-1, t)
    평균 OM         = 최근값일수록 높은 1:2:3 가중평균(2년이면 1:2)
    변동폭          = max(OM) - min(OM)

    수익성점수  = 업종 분위수 보간(평균 OM, 높을수록 양호)  # P10/P25/P50/P75/P90 = 0/25/50/75/100
    안정성점수  = 업종 분위수 보간(변동폭, 낮을수록 양호)   # P10/P25/P50/P75/P90 = 100/75/50/25/0
    M4         = 수익성점수 × 0.7 + 안정성점수 × 0.3

예외:
- 매출=0/결측 해 제외, 유효 연도 < 2년이면 산출 보류
- 2년만 있을 경우 변동폭은 단순 차이, note에 "n=2 단축"
"""

from __future__ import annotations

from typing import List, Tuple

from .calibration import CalibrationResult, profile_for_panel, score_against_peers
from .industry_v2 import classify, m4_mean_thresholds, m4_vol_thresholds
from .types import FirmPanel, ModuleScore


def _mean_score(avg: float, t: Tuple[float, float, float, float, float]) -> float:
    """평균 OM → 점수. 5단계 임계값 [위험=0, 손익=20, 보통=50, 우수=80, 최우수=100]."""
    T1, T2, T3, T4, T5 = t
    if avg <= T1:
        return 0.0
    if avg <= T2:
        return ((avg - T1) / (T2 - T1)) * 20.0
    if avg <= T3:
        return 20.0 + ((avg - T2) / (T3 - T2)) * 30.0
    if avg <= T4:
        return 50.0 + ((avg - T3) / (T4 - T3)) * 30.0
    if avg <= T5:
        return 80.0 + ((avg - T4) / (T5 - T4)) * 20.0
    return 100.0


def _vol_score(vol: float, v: Tuple[float, float, float, float]) -> float:
    """변동폭 → 점수. 4단계 임계값 [안정=100, 보통=70, 들쭉=50, 불안정=0]."""
    V1, V2, V3, V4 = v
    if vol <= V1:
        return 100.0
    if vol <= V2:
        return 100.0 - ((vol - V1) / (V2 - V1)) * 30.0
    if vol <= V3:
        return 70.0 - ((vol - V2) / (V3 - V2)) * 20.0
    if vol <= V4:
        return 50.0 - ((vol - V3) / (V4 - V3)) * 50.0
    return 0.0


def _operating_margins(panel: FirmPanel, n: int = 3) -> List[float]:
    """최근 n년 영업이익률 — 매출=0/결측 해 제외."""
    out = []
    for y in panel.years[-n:]:
        if y.revenue and y.revenue != 0 and y.operating_income is not None:
            out.append(y.operating_income / y.revenue)
    return out


def _recent_weighted_average(values: List[float]) -> float:
    """최근값일수록 높은 1:2:3 가중평균. 입력은 과거->최근 순서."""
    tail = values[-3:]
    weights = list(range(1, len(tail) + 1))
    return sum(value * weight for value, weight in zip(tail, weights)) / sum(weights)


def score_m4(panel: FirmPanel, calibration: CalibrationResult | None = None) -> ModuleScore:
    oms = _operating_margins(panel, 3)
    n = len(oms)
    if n < 1:
        return ModuleScore(
            name="M4",
            score=None,
            note="영업이익률 결측",
        )

    if n < 2:
        return ModuleScore(
            name="M4",
            score=None,
            raw=oms[0] if oms else None,
            note="유효 영업이익률 1년 — 안정성 판단에는 최소 2년 필요",
        )

    avg = _recent_weighted_average(oms)
    vol = max(oms) - min(oms)

    if calibration is not None:
        mean_profile = profile_for_panel(calibration, panel, "m4_average_margin")
        vol_profile = profile_for_panel(calibration, panel, "m4_margin_volatility")
        if mean_profile is None or vol_profile is None:
            return ModuleScore(
                name="M4",
                score=None,
                raw=avg,
                note="동종업계 유효 표본 부족 — M4 보류",
            )
        s_mean = score_against_peers(avg, mean_profile, higher_is_better=True)
        s_vol = score_against_peers(vol, vol_profile, higher_is_better=False)
        score = s_mean * 0.7 + s_vol * 0.3
        note = (
            f"{n}년 가중평균 영업이익률 {avg*100:+.1f}%, 변동폭 {vol*100:.1f}%p "
            f"— 수익성 70% + 안정성 30%"
        )
        if n < 3:
            note += " — 2년 이력"
        return ModuleScore(
            name="M4",
            score=round(score, 1),
            raw=avg,
            note=note,
            weight=1.0,
        )

    if n < 2:
        return ModuleScore(name="M4", score=None, raw=avg, note="유효 영업이익률 1년 — 최소 2년 필요")
    cls = classify(panel.corp_name)
    mean_thr = m4_mean_thresholds(cls.m4_mean_bucket)
    vol_thr = m4_vol_thresholds(cls.m4_vol_bucket)
    s_mean = _mean_score(avg, mean_thr)
    s_vol = _vol_score(vol, vol_thr)
    score = round(s_mean * 0.7 + s_vol * 0.3, 1)
    note = (
        f"{n}년 가중평균 영업이익률 {avg*100:+.1f}%, 변동폭 {vol*100:.1f}%p "
        f"(업종 {cls.m4_mean_bucket}/{cls.m4_vol_bucket})"
    )
    n_tag = "" if n == 3 else f" — n={n} 단축"
    return ModuleScore(
        name="M4",
        score=score,
        raw=avg,
        note=f"{note}{n_tag}",
    )
