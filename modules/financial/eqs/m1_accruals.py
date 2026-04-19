"""M1 — 발생액 품질 (수정 Jones 모델).

수정 Jones 모델 (Dechow et al., 1995):

    TA_it / A_(it-1) = α·(1/A_(it-1))
                     + β1·((ΔREV_it - ΔAR_it)/A_(it-1))
                     + β2·(PPE_it/A_(it-1)) + ε

여기서 TA(총발생액) = NI - OCF.  같은 산업·연도 cross-section으로 회귀계수를
추정한 뒤, 적합값을 비재량 발생액(NDA), 잔차를 재량 발생액(DA)으로 본다.
|DA|가 클수록 이익조정 가능성이 높다.

본 모듈은 두 가지 진입점을 제공한다:

1. ``modified_jones_cross_section(panels, target)``:
   같은 산업·연도 패널 전체로 OLS 회귀를 돌려 target 기업의 |DA|를 산출.
   학술적으로 옳은 형태이지만 표본이 충분해야 한다(보통 8개 이상 권장).

2. ``score_m1(panel)``:
   단일 기업 fallback. cross-section을 못 받았을 때 |TA/Assets|를 그대로
   품질 신호로 사용. 절대값이 작을수록 점수가 높도록 변환.
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


def score_m1(panel: FirmPanel) -> ModuleScore:
    """단일기업 fallback. |TA/A_(t-1)|을 품질 신호로 사용.

    cross-section 회귀를 못 돌리는 상황(산업 표본 부족, 단일 기업 분석 등)에서
    사용한다. NDA를 분리하지 못하므로 정확도는 떨어지지만 방향성은 보존된다.
    """
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
