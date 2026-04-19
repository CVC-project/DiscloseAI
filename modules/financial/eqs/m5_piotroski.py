"""M5 — Piotroski F-score (재무 건전성).

9개 binary criteria, 1점씩 합산 → 0~9.

수익성 (4):
1. ROA > 0
2. CFO > 0
3. ΔROA > 0  (전년 대비)
4. CFO > NI (이익이 현금으로 뒷받침)

레버리지·유동성 (3):
5. ΔLong-term debt < 0  (부채 감소)
6. ΔCurrent ratio > 0   (유동성 개선)
7. 신주 발행 없음 (shares_outstanding 비증가)

영업효율 (2):
8. ΔGross margin > 0
9. ΔAsset turnover > 0  (Sales/Assets)

데이터 누락 시 해당 criterion은 0점 처리(=보수적).
"""

from __future__ import annotations

from typing import Optional

from .types import FirmPanel, FirmYear, ModuleScore


def _roa(y: FirmYear) -> Optional[float]:
    if y.net_income is None or not y.total_assets:
        return None
    return y.net_income / y.total_assets


def _current_ratio(y: FirmYear) -> Optional[float]:
    if y.current_assets is None or not y.current_liabilities:
        return None
    return y.current_assets / y.current_liabilities


def _gross_margin(y: FirmYear) -> Optional[float]:
    if y.revenue is None or y.cogs is None or y.revenue == 0:
        return None
    return (y.revenue - y.cogs) / y.revenue


def _asset_turnover(y: FirmYear) -> Optional[float]:
    if y.revenue is None or not y.total_assets:
        return None
    return y.revenue / y.total_assets


def _gt(a: Optional[float], b: Optional[float]) -> int:
    if a is None or b is None:
        return 0
    return 1 if a > b else 0


def _lt(a: Optional[float], b: Optional[float]) -> int:
    if a is None or b is None:
        return 0
    return 1 if a < b else 0


def piotroski_f(prev: FirmYear, curr: FirmYear) -> int:
    """Piotroski F-score (0~9)."""
    score = 0
    roa_curr = _roa(curr)
    roa_prev = _roa(prev)
    cr_curr = _current_ratio(curr)
    cr_prev = _current_ratio(prev)
    gm_curr = _gross_margin(curr)
    gm_prev = _gross_margin(prev)
    at_curr = _asset_turnover(curr)
    at_prev = _asset_turnover(prev)

    # 1. ROA > 0
    score += _gt(roa_curr, 0.0)
    # 2. CFO > 0
    score += _gt(curr.operating_cashflow, 0.0)
    # 3. ΔROA > 0
    score += _gt(roa_curr, roa_prev)
    # 4. CFO > NI
    score += _gt(curr.operating_cashflow, curr.net_income)
    # 5. ΔLTD < 0  (부채 감소)
    score += _lt(curr.long_term_debt, prev.long_term_debt)
    # 6. ΔCurrent ratio > 0
    score += _gt(cr_curr, cr_prev)
    # 7. 신주발행 없음 (curr <= prev)
    if (
        curr.shares_outstanding is not None
        and prev.shares_outstanding is not None
        and curr.shares_outstanding <= prev.shares_outstanding
    ):
        score += 1
    # 8. ΔGross margin > 0
    score += _gt(gm_curr, gm_prev)
    # 9. ΔAsset turnover > 0
    score += _gt(at_curr, at_prev)
    return score


def score_m5(panel: FirmPanel) -> ModuleScore:
    curr = panel.latest()
    prev = panel.prior()
    if curr is None or prev is None:
        return ModuleScore(name="M5", score=None, note="패널 부족(t,t-1 필요)")
    f = piotroski_f(prev, curr)
    score = round(f / 9 * 100, 1)
    return ModuleScore(name="M5", score=score, raw=float(f), note=f"F-score={f}/9")
