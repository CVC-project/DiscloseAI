"""M2 — Beneish M-score (분식 확률).

Beneish(1999) 8변수 모델:

  DSRI = (AR_t/Sales_t) / (AR_(t-1)/Sales_(t-1))
  GMI  = GM_(t-1) / GM_t                       (GM = (Sales-COGS)/Sales)
  AQI  = (1-(CA+PPE)/TA)_t / (1-(CA+PPE)/TA)_(t-1)
  SGI  = Sales_t / Sales_(t-1)
  DEPI = (Dep_(t-1)/(Dep+PPE)_(t-1)) / (Dep_t/(Dep+PPE)_t)
  SGAI = (SGA_t/Sales_t) / (SGA_(t-1)/Sales_(t-1))
  TATA = (NI - OCF) / TA
  LVGI = ((LTD+CL)/TA)_t / ((LTD+CL)/TA)_(t-1)

  M = -4.84 + 0.92·DSRI + 0.528·GMI + 0.404·AQI + 0.892·SGI
        + 0.115·DEPI - 0.172·SGAI + 4.679·TATA - 0.327·LVGI

해석: M > -1.78이면 분식 가능성 높음 (미국 표본 기준).

K-Beneish: 미국 계수가 K-IFRS 환경(보수적 수익 인식, 다른 발생액 패턴)에는
잘 맞지 않는다는 한국 학계 비판이 꾸준하다. ``BeneishCoefficients``에 한국
재추정 계수 세트를 갈아끼울 수 있도록 분리.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .types import FirmPanel, FirmYear, ModuleScore


@dataclass(frozen=True)
class BeneishCoefficients:
    intercept: float
    dsri: float
    gmi: float
    aqi: float
    sgi: float
    depi: float
    sgai: float
    tata: float
    lvgi: float


# Beneish(1999) 미국 원본 계수
BENEISH_US = BeneishCoefficients(
    intercept=-4.84,
    dsri=0.92,
    gmi=0.528,
    aqi=0.404,
    sgi=0.892,
    depi=0.115,
    sgai=-0.172,
    tata=4.679,
    lvgi=-0.327,
)

# K-Beneish 자리 (한국 표본 재추정 계수 — TODO: 한국 상장사 데이터로 학습 후 갱신).
# 갱신 전까지는 미국 계수를 그대로 사용해 결과가 누락되지 않게 한다.
BENEISH_KR = BENEISH_US

# 분식 임계값 (Beneish 권고). 이 이상이면 manipulator 분류.
M_THRESHOLD = -1.78


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _compute_all_indices(prev: FirmYear, curr: FirmYear) -> dict:
    """8개 지수 원시 계산 (결측은 None 그대로). 필터링 X."""
    # 매출/AR
    dsri_curr = _safe_div(curr.accounts_receivable, curr.revenue)
    dsri_prev = _safe_div(prev.accounts_receivable, prev.revenue)
    dsri = _safe_div(dsri_curr, dsri_prev)
    # 매출총이익률
    gm_curr = (
        _safe_div((curr.revenue or 0) - (curr.cogs or 0), curr.revenue)
        if curr.revenue and curr.cogs is not None
        else None
    )
    gm_prev = (
        _safe_div((prev.revenue or 0) - (prev.cogs or 0), prev.revenue)
        if prev.revenue and prev.cogs is not None
        else None
    )
    gmi = _safe_div(gm_prev, gm_curr)
    # 자산건전성: 1 - (CA+PPE)/TA
    aq_curr = (
        1 - ((curr.current_assets or 0) + (curr.ppe or 0)) / curr.total_assets
        if curr.total_assets
        else None
    )
    aq_prev = (
        1 - ((prev.current_assets or 0) + (prev.ppe or 0)) / prev.total_assets
        if prev.total_assets
        else None
    )
    aqi = _safe_div(aq_curr, aq_prev)
    # 매출 성장
    sgi = _safe_div(curr.revenue, prev.revenue)
    # 감가상각률
    dep_curr = _safe_div(
        curr.depreciation,
        ((curr.depreciation or 0) + (curr.ppe or 0)) or None,
    )
    dep_prev = _safe_div(
        prev.depreciation,
        ((prev.depreciation or 0) + (prev.ppe or 0)) or None,
    )
    depi = _safe_div(dep_prev, dep_curr)
    # SGA율
    sga_curr = _safe_div(curr.sga, curr.revenue)
    sga_prev = _safe_div(prev.sga, prev.revenue)
    sgai = _safe_div(sga_curr, sga_prev)
    # 총발생액 / 자산
    if curr.net_income is None or curr.operating_cashflow is None or not curr.total_assets:
        tata = None
    else:
        tata = (curr.net_income - curr.operating_cashflow) / curr.total_assets
    # 레버리지
    lev_curr = (
        ((curr.long_term_debt or 0) + (curr.current_liabilities or 0))
        / curr.total_assets
        if curr.total_assets
        else None
    )
    lev_prev = (
        ((prev.long_term_debt or 0) + (prev.current_liabilities or 0))
        / prev.total_assets
        if prev.total_assets
        else None
    )
    lvgi = _safe_div(lev_curr, lev_prev)

    return {
        "DSRI": dsri,
        "GMI": gmi,
        "AQI": aqi,
        "SGI": sgi,
        "DEPI": depi,
        "SGAI": sgai,
        "TATA": tata,
        "LVGI": lvgi,
    }


# 핵심 지수 사람이 읽는 한글 라벨 (결측 사유 메시지용)
_CORE_LABELS = {
    "DSRI": "매출채권 비율",
    "GMI": "매출총이익률",
    "SGI": "매출 성장",
    "TATA": "발생액/자산",
}
_CORE_INDICES = tuple(_CORE_LABELS.keys())


def _beneish_indices(prev: FirmYear, curr: FirmYear) -> Optional[dict]:
    """핵심 4지수가 모두 있을 때만 8지수 dict 반환. 부차 결측은 1.0 대체."""
    indices = _compute_all_indices(prev, curr)
    if any(indices[k] is None for k in _CORE_INDICES):
        return None
    # 부차 지수 결측은 1.0 대체 (변화 없음 가정 — Beneish 원논문 관행)
    for k in ("AQI", "DEPI", "SGAI", "LVGI"):
        if indices[k] is None:
            indices[k] = 1.0
    return indices


def _panel_has_cogs(panel: FirmPanel) -> bool:
    """패널에 매출원가가 한 해라도 있는지. 모두 None이면 서비스·플랫폼 기업."""
    return any(y.cogs is not None for y in panel.years)


def m_score(prev: FirmYear, curr: FirmYear, coefs: BeneishCoefficients = BENEISH_KR) -> Optional[float]:
    """M-score 원시 계산값. 결측이면 None."""
    idx = _beneish_indices(prev, curr)
    if idx is None:
        return None
    return (
        coefs.intercept
        + coefs.dsri * idx["DSRI"]
        + coefs.gmi * idx["GMI"]
        + coefs.aqi * idx["AQI"]
        + coefs.sgi * idx["SGI"]
        + coefs.depi * idx["DEPI"]
        + coefs.sgai * idx["SGAI"]
        + coefs.tata * idx["TATA"]
        + coefs.lvgi * idx["LVGI"]
    )


def _m_to_score(m: float) -> float:
    """M-score → 0~100. M이 작을수록(=정상) 100에 가깝게.

    M_THRESHOLD(-1.78)에서 50점이 되도록 logistic 변환:
        score = 100 * sigmoid(-(m - threshold) * k),  k=2
    M이 크면(분식 의심) 점수가 0에 수렴, 작으면(건전) 100에 수렴.
    """
    k = 2.0
    z = -(m - M_THRESHOLD) * k
    # 오버플로우 가드
    if z > 60:
        return 100.0
    if z < -60:
        return 0.0
    sig = 1.0 / (1.0 + math.exp(-z))
    return round(sig * 100, 1)


def score_m2(
    panel: FirmPanel, coefs: BeneishCoefficients = BENEISH_KR
) -> ModuleScore:
    """패널의 가장 최근 (t-1, t) 페어로 M2 산출.

    ``note`` 필드는 산출 실패 시 구체적 사유를 담아 랭킹 대시보드 툴팁으로 노출된다.
    """
    curr = panel.latest()
    prev = panel.prior()
    if curr is None or prev is None:
        return ModuleScore(name="M2", score=None, note="패널 부족(t,t-1 필요)")

    # 서비스·플랫폼 기업 사전 감지 (DART에 매출원가 항목 자체 없음)
    if not _panel_has_cogs(panel):
        return ModuleScore(
            name="M2",
            score=None,
            note="매출원가 항목 없음(서비스·플랫폼형) — Beneish 모델 부적합",
        )

    m = m_score(prev, curr, coefs)
    if m is None:
        # 어떤 핵심 지수가 빠졌는지 구체적으로 표시
        raw = _compute_all_indices(prev, curr)
        missing = [_CORE_LABELS[k] for k in _CORE_INDICES if raw[k] is None]
        reason = ", ".join(missing) if missing else "핵심 지수"
        return ModuleScore(name="M2", score=None, note=f"{reason} 결측 — 산출 불가")
    score = _m_to_score(m)
    flag = "분식 의심" if m > M_THRESHOLD else "정상"
    return ModuleScore(name="M2", score=score, raw=m, note=f"M={m:.2f} ({flag})")
