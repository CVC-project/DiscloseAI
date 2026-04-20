"""M1 — 이익실체 (발생액 품질).

"이익이 실제 현금 유입으로 뒷받침되는가?"를 측정한다.
장부상 이익(NI)과 실제 현금(OCF)의 괴리가 작을수록 이익 품질이 높다.

점수 도출 경로 (3가지):

1. ``modified_jones_cross_section(panels, target)``:
   수정 Jones 모델 (Dechow et al., 1995).
   같은 산업·연도 8개 이상 기업으로 OLS 회귀 → 재량 발생액 |DA/A| 추정.
   학술적으로 가장 정확하지만 동종 표본이 충분해야 함.

2. ``score_m1(panel)`` — 일반기업 단일기업 fallback:
   |TA/A| = |NI - OCF| / 전기 자산. 절대값이 작을수록 고점수.
   임계: 0% → 100점, 20% → 0점 (선형).

3. ``_score_m1_holding(panel)`` — 지주사 fallback:
   지주사는 자회사 지분법이익이 비현금성이라 정상적으로도 |TA/A|가 15~25%.
   임계를 0.40으로 완화(70%)하고, 자본누적 일치도(30%)를 보완 지표로 사용.
   대상: industry_code "100" (SK, HD현대, 두산, 삼성물산 등).
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from ._ols import ols_multi
from .types import FirmPanel, FirmYear, ModuleScore


# |DA/A| 또는 |TA/A| 0% → 100점, 20% 이상 → 0점으로 선형 매핑.
# 0.20 임계값은 Dechow(1995)의 미국 표본 평균 |DA| 약 4~6%의 4σ 근처 — 한국
# 데이터로 재추정 시 조정 예정.
_M1_FLOOR = 0.0
_M1_CAP = 0.20


def _ratio_to_score(ratio: float) -> float:
    """|DA/A|를 0~100 점수로 변환. 비율이 작을수록(=품질 양호) 높게."""
    clipped = max(_M1_FLOOR, min(_M1_CAP, ratio))
    return round((1 - (clipped - _M1_FLOOR) / (_M1_CAP - _M1_FLOOR)) * 100, 1)


def _total_accruals(curr: FirmYear) -> Optional[float]:
    """TA = NI - OCF. 둘 중 하나라도 없으면 None."""
    if curr.net_income is None or curr.operating_cashflow is None:
        return None
    return curr.net_income - curr.operating_cashflow


def _build_jones_row(
    prev: FirmYear, curr: FirmYear
) -> Optional[tuple[List[float], float]]:
    """수정 Jones 1행: (X_row, y) — 결측이면 None."""
    a_lag = prev.total_assets
    if a_lag in (None, 0):
        return None
    ta = _total_accruals(curr)
    if ta is None:
        return None
    if curr.revenue is None or prev.revenue is None:
        return None
    if curr.accounts_receivable is None or prev.accounts_receivable is None:
        return None
    if curr.ppe is None:
        return None
    d_rev = curr.revenue - prev.revenue
    d_ar = curr.accounts_receivable - prev.accounts_receivable
    x = [
        1.0 / a_lag,
        (d_rev - d_ar) / a_lag,
        curr.ppe / a_lag,
    ]
    y = ta / a_lag
    return x, y


def modified_jones_cross_section(
    panels: Sequence[FirmPanel], target_corp: str, year: int
) -> Optional[ModuleScore]:
    """동일 (산업,연도) cross-section 회귀로 target의 |DA/A|를 추정.

    ``panels``는 같은 산업/연도 표본이어야 한다 (호출자가 필터링). 표본이 너무
    작거나(<8) target 행을 만들 수 없으면 None을 반환하므로 호출자는
    ``score_m1`` fallback을 사용하면 된다.
    """
    rows: List[tuple[List[float], float]] = []
    target_row: Optional[tuple[List[float], float]] = None
    for p in panels:
        # 해당 연도와 직전연도 페어 찾기
        prev = next((y for y in p.years if y.year == year - 1), None)
        curr = next((y for y in p.years if y.year == year), None)
        if not prev or not curr:
            continue
        built = _build_jones_row(prev, curr)
        if not built:
            continue
        rows.append(built)
        if p.corp_code == target_corp:
            target_row = built

    if len(rows) < 8 or target_row is None:
        return None

    X = [r[0] for r in rows]
    y = [r[1] for r in rows]
    coefs = ols_multi(X, y, intercept=False)
    if coefs is None:
        return None
    x_t, y_t = target_row
    nda = sum(c * v for c, v in zip(coefs, x_t))
    da = y_t - nda
    score = _ratio_to_score(abs(da))
    note = f"|DA/A|={abs(da):.3f} (n={len(rows)})"
    return ModuleScore(name="M1", score=score, raw=da, note=note)


def _score_m1_holding(panel: FirmPanel) -> ModuleScore:
    """지주사용 발생액 품질 fallback.

    지주사는 자회사 지분법이익이 비현금성이라 정상적으로도 |TA/A|가 15~25%.
    일반기업 임계 0.20은 대부분 0점이 되므로, 임계를 0.40으로 완화하고
    자본누적 일치도(보고 이익 대비 자본 성장)를 보완 지표로 사용.
    """
    _HOLDING_CAP = 0.40

    curr = panel.latest()
    prev = panel.prior()
    if curr is None or prev is None:
        return ModuleScore(name="M1", score=None, note="패널 부족(t,t-1 필요)")
    ta = _total_accruals(curr)
    if ta is None or not prev.total_assets:
        return ModuleScore(name="M1", score=None, note="NI/OCF/자산 결측")

    # 1) NI-OCF 괴리 (70%) — 임계값 완화
    divergence = abs(ta) / prev.total_assets
    clipped = max(0.0, min(_HOLDING_CAP, divergence))
    div_score = (1 - clipped / _HOLDING_CAP) * 100

    # 2) 자본누적 일치도 (30%) — 누적 NI vs 자본 변화
    first = panel.years[0] if panel.years else None
    last = panel.years[-1] if panel.years else None
    if first and last and first.total_equity and last.total_equity:
        cumulative_ni = sum(
            y.net_income for y in panel.years
            if y.net_income is not None
        )
        equity_change = last.total_equity - first.total_equity
        if cumulative_ni > 0:
            ratio = max(0.0, min(1.5, equity_change / cumulative_ni))
            eq_score = (ratio / 1.5) * 100
        else:
            eq_score = 50.0  # 누적 NI <= 0 → 중립
    else:
        eq_score = 50.0

    score = round(div_score * 0.7 + eq_score * 0.3, 1)
    return ModuleScore(
        name="M1", score=score, raw=divergence,
        note=f"|NI-OCF|/자산={divergence:.3f} (지주 임계 0.40), 자본일치={eq_score:.0f} — 지주사 fallback",
    )


def score_m1(panel: FirmPanel) -> ModuleScore:
    """단일기업 fallback. |TA/A_(t-1)|을 품질 신호로 사용.

    cross-section 회귀를 못 돌리는 상황(산업 표본 부족, 단일 기업 분석 등)에서
    사용한다. NDA를 분리하지 못하므로 정확도는 떨어지지만 방향성은 보존된다.
    """
    # 지주사는 지분법이익 특성상 별도 fallback 사용
    from .industry import is_holding
    if is_holding(panel.industry_code):
        return _score_m1_holding(panel)

    curr = panel.latest()
    prev = panel.prior()
    if curr is None or prev is None:
        return ModuleScore(name="M1", score=None, note="패널 부족(t,t-1 필요)")
    ta = _total_accruals(curr)
    if ta is None or not prev.total_assets:
        return ModuleScore(name="M1", score=None, note="NI/OCF/자산 결측")
    ratio = abs(ta) / prev.total_assets
    score = _ratio_to_score(ratio)
    return ModuleScore(
        name="M1",
        score=score,
        raw=ratio,
        note=f"|TA/A|={ratio:.3f} (단일기업 fallback)",
    )
