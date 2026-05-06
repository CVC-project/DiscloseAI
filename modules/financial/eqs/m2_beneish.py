"""M2 v2 — 매출 회수 건전성 (AR Quality).

"매출 늘어났다는데 진짜 매출인가, 외상으로 잡은 건가?"

설계: ``modules/financial/EQS_V2_DESIGN.md`` §M2.

산출:
    g_R  = (Rev[t]  / Rev[t-1])  - 1     # 매출증가율
    g_RC = (RC[t]   / RC[t-1])   - 1     # 미수채권증가율
    D    = g_RC - g_R                    # %p

    점수 변환 (선형 보간):
      D ≤ -10%p              → 100
      -10%p < D ≤ 0%p        → 80 + (-D/10) × 20
      0%p   < D ≤ +10%p      → 80 - (D/10)  × 30
      +10%p < D ≤ +30%p      → 50 - ((D-10)/20) × 50
      D > +30%p              → 0

미수채권 RC:
- 일반업종: 매출채권 (accounts_receivable)
- 수주산업(건설·조선·중공업): 매출채권 + 계약자산 (contract_assets)

예외:
- 금융업: 매출채권 개념 부적합 → 산출 제외 (score=None, note="금융업 — 적용 제외")
- 매출 또는 RC 결측·0: 산출 보류
- 수주산업이지만 contract_assets 결측: 매출채권만 사용 + note에 "계약자산 결측"
"""

from __future__ import annotations

from typing import Optional

from .industry_v2 import classify, includes_contract_assets
from .types import FirmPanel, FirmYear, ModuleScore


def _receivable(y: FirmYear, with_contract: bool) -> Optional[float]:
    """미수채권 = 매출채권 + (수주산업이면 계약자산)."""
    ar = y.accounts_receivable
    if ar is None:
        return None
    if with_contract and y.contract_assets is not None:
        return ar + y.contract_assets
    return ar


def _D_to_score(D: float) -> float:
    """D(%p, 소수단위 — 0.10 = 10%p) → 0~100 점수, 선형 보간."""
    if D <= -0.10:
        return 100.0
    if D <= 0:
        return 80.0 + (-D / 0.10) * 20.0
    if D <= 0.10:
        return 80.0 - (D / 0.10) * 30.0
    if D <= 0.30:
        return 50.0 - ((D - 0.10) / 0.20) * 50.0
    return 0.0


def score_m2(panel: FirmPanel) -> ModuleScore:
    cls = classify(panel.corp_name)
    if cls.m2_excluded:
        return ModuleScore(
            name="M2",
            score=None,
            note="금융업 — 매출채권 개념 부적합으로 적용 제외",
        )

    curr = panel.latest()
    prev = panel.prior()
    if curr is None or prev is None:
        return ModuleScore(name="M2", score=None, note="패널 부족(t,t-1 필요)")

    if not curr.revenue or not prev.revenue:
        return ModuleScore(name="M2", score=None, note="매출 결측")

    with_contract = includes_contract_assets(panel.corp_name)
    rc_curr = _receivable(curr, with_contract)
    rc_prev = _receivable(prev, with_contract)
    if rc_curr is None or rc_prev is None or rc_prev == 0:
        return ModuleScore(name="M2", score=None, note="매출채권/계약자산 결측")

    g_R = curr.revenue / prev.revenue - 1
    g_RC = rc_curr / rc_prev - 1
    D = g_RC - g_R
    score = _D_to_score(D)

    rc_label = "매출채권+계약자산" if (with_contract and curr.contract_assets is not None) else "매출채권"
    contract_warn = (
        " — 계약자산 결측, 매출채권만 사용"
        if with_contract and curr.contract_assets is None
        else ""
    )
    return ModuleScore(
        name="M2",
        score=round(score, 1),
        raw=D,
        note=(
            f"매출증가율 {g_R*100:+.1f}%, {rc_label}증가율 {g_RC*100:+.1f}%, "
            f"차이 D={D*100:+.1f}%p{contract_warn}"
        ),
    )
