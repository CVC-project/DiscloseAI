"""M3 — 현금흐름 괴리 (OCF/NI 비율 추세).

핵심 가정: 정상 영업기업은 장기적으로 OCF가 NI를 따라가야 한다. NI는 늘어나는데
OCF가 따라오지 못하면 발생액 누적·재고 비대화·매출채권 부풀리기 신호.

지표 3가지를 합산:
- 평균 비율: mean(OCF/NI), 1.0 이상이 이상적
- 추세 (slope of OCF/NI over years): >0 이면 가산, <0 이면 감점
- 변동성: std/|mean|, 낮을수록 가산

NI<=0인 해는 비율이 무의미하므로 (OCF, NI) 모두 양수인 해만 사용.
금융업은 호출자에서 제외 (industry.excluded_modules).
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import List, Tuple

from ._ols import ols_simple
from .types import FirmPanel, ModuleScore


def _ocf_ni_pairs(panel: FirmPanel) -> List[Tuple[int, float]]:
    """(year, OCF/NI) 리스트. NI<=0 또는 결측 제외."""
    out: List[Tuple[int, float]] = []
    for y in panel.years:
        if (
            y.net_income is None
            or y.operating_cashflow is None
            or y.net_income <= 0
        ):
            continue
        out.append((y.year, y.operating_cashflow / y.net_income))
    return out


def _level_score(avg: float) -> float:
    """평균 OCF/NI를 0~100점으로. 1.0 이상=만점, 0 이하=0점."""
    if avg >= 1.0:
        return 100.0
    if avg <= 0.0:
        return 0.0
    return round(avg * 100, 1)


def _trend_score(slope: float) -> float:
    """연 변화량 slope를 0~100점으로. ±0.1을 포화점으로 둠."""
    cap = 0.1
    clipped = max(-cap, min(cap, slope))
    return round(50 + (clipped / cap) * 50, 1)


def _vol_score(values: List[float]) -> float:
    """변동계수(CV)가 낮을수록 가산. CV>=1이면 0점, CV=0이면 100점."""
    m = mean(values)
    if m == 0:
        return 0.0
    cv = pstdev(values) / abs(m)
    cv = min(1.0, cv)
    return round((1 - cv) * 100, 1)


def score_m3(panel: FirmPanel) -> ModuleScore:
    pairs = _ocf_ni_pairs(panel)
    if len(pairs) < 2:
        return ModuleScore(name="M3", score=None, note="OCF/NI 비율 데이터 부족(2년 이상 필요)")
    years = [p[0] for p in pairs]
    ratios = [p[1] for p in pairs]
    avg = mean(ratios)

    if len(pairs) >= 3:
        fit = ols_simple(years, ratios)
        slope = fit[1] if fit else 0.0
        # 평균 50%, 추세 25%, 변동성 25% 가중
        score = (
            _level_score(avg) * 0.5
            + _trend_score(slope) * 0.25
            + _vol_score(ratios) * 0.25
        )
        note = f"평균 OCF/NI={avg:.2f}, 추세={slope:+.3f}/yr, n={len(pairs)}"
    else:
        score = _level_score(avg)
        note = f"평균 OCF/NI={avg:.2f} (2년만 사용)"
    return ModuleScore(name="M3", score=round(score, 1), raw=avg, note=note)
