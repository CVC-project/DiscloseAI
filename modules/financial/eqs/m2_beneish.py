"""M2 — 회계투명 (분식 가능성 탐지).

"회계 처리가 투명한가, 분식 가능성은 없는가?"를 측정한다.
점수가 높을수록 회계가 투명하다는 뜻이다.

점수 도출 경로 (2가지):

1. ``score_m2(panel)`` — 정상 경로 (제조업 등 COGS가 있는 기업):
   Beneish(1999) 8변수 M-score 모델.
   DSRI·GMI·AQI·SGI·DEPI·SGAI·TATA·LVGI 8개 지수 가중합으로 M-score 산출.
   M > -1.78이면 분식 가능성 높음 (미국 표본 기준).
   로지스틱 변환: M이 낮을수록(=정상) 100점, 높을수록 0점.

2. ``_score_m2_fallback(panel)`` — TATA+SGI 간소화 모델:
   COGS가 없는 서비스/플랫폼/금융업, 또는 매출채권 결측 기업에 적용.
   TATA=(NI-OCF)/TA (Beneish 최고 예측력 변수, 계수 4.679) + SGI(매출성장)
   + OCF/Revenue(현금전환율) + LVGI(레버리지 변화) 4변수로 간소화.
   동일한 로지스틱 변환 함수(_m_to_score)를 사용해 0~100 스케일 유지.
   대상: 카카오, NAVER, SK텔레콤, 금융사, 기아, 한미반도체, 현대로템 등.

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
    """패널에 **양수 매출원가**가 한 해라도 있는지.

    None이거나 0으로 기록된 해만 있으면 서비스·플랫폼 기업 간주. cogs=0
    케이스도 실질적으로 매출원가 항목이 없다는 신호로 보고 제외.
    """
    return any(y.cogs is not None and y.cogs > 0 for y in panel.years)


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


def _score_m2_fallback(panel: FirmPanel, *, reason: str = "") -> ModuleScore:
    """COGS/매출채권 없는 기업용 간소화 M-score (TATA+SGI+OCFR+LVGI).

    Beneish(1999) 원논문에서 TATA(계수 4.679)가 단일 변수 중 가장 높은 예측력.
    SGI(0.892)와 결합하면 핵심 분식 신호를 포착 가능.
    OCF/Revenue(현금전환율)와 LVGI(레버리지 변화)로 보완.
    """
    curr = panel.latest()
    prev = panel.prior()
    if curr is None or prev is None:
        return ModuleScore(name="M2", score=None, note="패널 부족(t,t-1 필요)")

    # TATA — 핵심 (항상 산출 가능)
    if curr.net_income is None or curr.operating_cashflow is None or not curr.total_assets:
        return ModuleScore(name="M2", score=None, note="NI/OCF/TA 결측 — fallback 불가")
    tata = (curr.net_income - curr.operating_cashflow) / curr.total_assets

    # SGI — 매출 성장 (항상 산출 가능)
    if curr.revenue is None or prev.revenue is None or prev.revenue == 0:
        return ModuleScore(name="M2", score=None, note="매출 결측 — fallback 불가")
    sgi = curr.revenue / prev.revenue

    # OCFR — 현금전환율
    ocfr = curr.operating_cashflow / curr.revenue if curr.revenue != 0 else 0.0

    # LVGI — 레버리지 변화
    lev_curr = ((curr.long_term_debt or 0) + (curr.current_liabilities or 0)) / curr.total_assets
    lev_prev = (
        ((prev.long_term_debt or 0) + (prev.current_liabilities or 0)) / prev.total_assets
        if prev.total_assets
        else lev_curr
    )
    lvgi = lev_curr / lev_prev if lev_prev != 0 else 1.0

    # 간소화 M-score: TATA·SGI 중심, OCFR·LVGI 보완
    m = -3.50 + 5.0 * tata + 0.9 * sgi - 0.5 * ocfr - 0.3 * lvgi
    score = _m_to_score(m)
    flag = "의심" if m > M_THRESHOLD else "정상"
    return ModuleScore(
        name="M2", score=score, raw=m,
        note=f"M={m:.2f} ({flag}) — {reason} fallback",
    )


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
        return _score_m2_fallback(panel, reason="매출원가 없음(서비스·플랫폼형)")

    m = m_score(prev, curr, coefs)
    if m is None:
        # 어떤 핵심 지수가 빠졌는지 구체적으로 표시
        raw = _compute_all_indices(prev, curr)
        missing = [_CORE_LABELS[k] for k in _CORE_INDICES if raw[k] is None]
        reason = ", ".join(missing) if missing else "핵심 지수"
        return _score_m2_fallback(panel, reason=f"{reason} 결측")
    score = _m_to_score(m)
    flag = "분식 의심" if m > M_THRESHOLD else "정상"
    return ModuleScore(name="M2", score=score, raw=m, note=f"M={m:.2f} ({flag})")
