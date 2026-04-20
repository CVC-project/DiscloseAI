"""M3 — 현금뒷받침 (이익의 현금 실현도).

"번 돈이 실제 현금으로 들어왔는가?"를 측정한다.
점수가 높을수록 이익이 현금으로 잘 뒷받침된다는 뜻이다.

점수 도출 경로 (3가지):

1. ``score_m3(panel)`` — 정상 경로 (일반 영업기업):
   OCF/NI 비율의 평균(50%) + 추세(25%) + 변동성(25%) 가중합.
   1.0 이상이 이상적. NI<=0 해는 제외, OCF 음수는 의도적 포함(핵심 신호).
   개별 연도 비율은 ±3으로 winsorize.

2. ``_score_m3_financial(panel)`` — 금융업 소득안정성 fallback:
   금융업(064~067)은 OCF 개념이 다르므로(예금 유출입, 이자수익 중심)
   ROE 안정성(CV, 50%) + 영업마진 안정성(CV, 30%) + NI 성장방향 일관성(20%)으로
   이익 품질을 측정. (Barth et al., 2008)
   대상: KB금융, 신한지주, 삼성생명, 삼성화재, 미래에셋증권 등.

3. ``_score_m3_loss_heavy(panel)`` — 적자빈발 기업 현금창출력 fallback:
   적자 연도 >50%이면 OCF/NI 해석 불가. 대신 OCF/자산(CROA) 평균(60%) +
   CROA 추세(40%)로 현금 창출 능력 측정. (Credit Suisse HOLT 개념)
   대상: 한국전력, 삼성중공업, SK이노베이션 등.
"""

from __future__ import annotations

import math
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


# 개별 연도 OCF/NI 비율 outlier 제한 — 단일 연도의 폭발적 악화가 다년 평균을
# 왜곡하지 않도록. 3 = OCF가 NI의 3배, -3 = OCF가 NI의 -3배 수준. 실무에서 이
# 정도 범위를 벗어나면 일회성·비경상적 요인이라 해석이 어렵다.
_RATIO_CLIP = 3.0


def _score_m3_financial(panel: FirmPanel) -> ModuleScore:
    """금융업용 소득안정성 fallback.

    금융업은 OCF 개념이 비금융과 근본적으로 다르므로(예금 유출입, 이자수익)
    OCF/NI 대신 ROE·영업마진 안정성 + NI 성장 방향 일관성으로 이익 품질 측정.
    (Barth et al., 2008 — 안정적 이익 = 높은 이익 품질)
    """
    years = [y for y in panel.years
             if y.net_income is not None and y.total_equity and y.total_equity != 0
             and y.revenue and y.operating_income is not None]
    if len(years) < 3:
        return ModuleScore(name="M3", score=None, note="금융업 fallback: 3년 이상 필요")

    roes = [y.net_income / y.total_equity for y in years]
    opms = [y.operating_income / y.revenue for y in years]

    # 1) ROE 안정성 (CV 기반, 50%)
    avg_roe = mean(roes)
    roe_score = max(0.0, 100 * (1 - pstdev(roes) / abs(avg_roe))) if avg_roe != 0 else 0.0

    # 2) 영업마진 안정성 (CV 기반, 30%)
    avg_opm = mean(opms)
    opm_score = max(0.0, 100 * (1 - pstdev(opms) / abs(avg_opm))) if avg_opm != 0 else 0.0

    # 3) NI 성장 방향 일관성 (20%)
    ni_vals = [y.net_income for y in years]
    if len(ni_vals) >= 3:
        changes = [1 if ni_vals[i] >= ni_vals[i - 1] else -1 for i in range(1, len(ni_vals))]
        # 같은 방향으로 갈수록 일관성 높음
        same_dir = sum(1 for i in range(1, len(changes)) if changes[i] == changes[i - 1])
        dir_score = (same_dir / max(1, len(changes) - 1)) * 100
    else:
        dir_score = 50.0  # 데이터 부족 시 중립

    score = round(roe_score * 0.5 + opm_score * 0.3 + dir_score * 0.2, 1)
    cv_roe = pstdev(roes) / abs(avg_roe) if avg_roe != 0 else float("inf")
    return ModuleScore(
        name="M3", score=score, raw=cv_roe,
        note=f"ROE CV={cv_roe:.2f}, 영업마진CV={pstdev(opms)/abs(avg_opm) if avg_opm != 0 else 0:.2f} — 금융업 소득안정성 fallback",
    )


def _score_m3_loss_heavy(panel: FirmPanel) -> ModuleScore:
    """적자빈발 기업용 현금창출력 fallback.

    적자 연도가 과반이면 OCF/NI 비율 해석이 불가. 대신 OCF/자산(CROA)으로
    이익 부호와 무관하게 현금 창출 능력을 측정.
    (Credit Suisse HOLT Cash Return on Assets 개념)
    """
    croa_pairs = []
    for y in panel.years:
        if y.operating_cashflow is not None and y.total_assets and y.total_assets != 0:
            croa_pairs.append((y.year, y.operating_cashflow / y.total_assets))
    if len(croa_pairs) < 2:
        return ModuleScore(name="M3", score=None, note="OCF/자산 데이터 부족")

    years_list = [p[0] for p in croa_pairs]
    croas = [p[1] for p in croa_pairs]
    avg_croa = mean(croas)

    # 1) 평균 CROA 레벨 (60%): logistic, 5%에서 50점
    z = (avg_croa - 0.05) * 30
    z = max(-60, min(60, z))
    level_score = 100 / (1 + math.exp(-z))

    # 2) CROA 추세 (40%): slope
    if len(croa_pairs) >= 3:
        fit = ols_simple(years_list, croas)
        slope = fit[1] if fit else 0.0
        clipped = max(-0.02, min(0.02, slope))
        trend_score = 50 + (clipped / 0.02) * 50
        score = round(level_score * 0.6 + trend_score * 0.4, 1)
        note = f"평균 OCF/자산={avg_croa:.1%}, 추세={slope:+.4f}/yr — 적자빈발 현금창출력 fallback"
    else:
        score = round(level_score, 1)
        note = f"평균 OCF/자산={avg_croa:.1%} — 적자빈발 현금창출력 fallback (2년)"

    return ModuleScore(name="M3", score=score, raw=avg_croa, note=note)


def score_m3(panel: FirmPanel) -> ModuleScore:
    # 금융업은 OCF 개념이 다르므로 소득안정성 fallback 사용
    from .industry import is_financial
    if is_financial(panel.industry_code):
        return _score_m3_financial(panel)

    pairs = _ocf_ni_pairs(panel)
    if len(pairs) < 2:
        return _score_m3_loss_heavy(panel)

    # 데이터 품질 체크: 전체 연도 중 순적자 해가 과반이면 비율 해석 자체가 어려움.
    total_years = len(panel.years)
    valid = len(pairs)
    if valid * 2 < total_years:
        return _score_m3_loss_heavy(panel)

    years = [p[0] for p in pairs]
    ratios_raw = [p[1] for p in pairs]
    # 개별 연도 outlier winsorize — 단일 연도가 평균을 망가뜨리는 것 방지
    ratios = [max(-_RATIO_CLIP, min(_RATIO_CLIP, r)) for r in ratios_raw]
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
