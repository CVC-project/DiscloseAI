"""EQS 종합 점수 + 등급화.

5개 모듈의 가중평균으로 0~100점 산출 후 등급 부여.

기본 가중치 (5개 모듈, 합 1.0):
  M1(이익실체)=0.20, M2(회계투명)=0.20, M3(현금뒷받침)=0.20,
  M4(이익안정)=0.20, M5(재무체력)=0.20

v2: 모든 업종에서 5개 모듈을 항상 호출. 금융업·지주사·서비스업 등
표준 모델이 부적합한 경우 각 모듈 내부에서 fallback 모델이 자동 적용.
score=None인 모듈은 평균에서 제외되고 가중치가 재조정됨.

등급:
  A ≥ 80, B ≥ 65, C ≥ 50, D ≥ 35, F < 35
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .industry import excluded_modules
from .m1_accruals import score_m1
from .m2_beneish import score_m2
from .m3_cashflow import score_m3
from .m4_persistence import score_m4
from .m5_piotroski import score_m5
from .types import EQSResult, FirmPanel, ModuleScore

DEFAULT_WEIGHTS: Dict[str, float] = {
    "M1": 0.20,
    "M2": 0.20,
    "M3": 0.20,
    "M4": 0.20,
    "M5": 0.20,
}


def grade_from_score(score: Optional[float]) -> Optional[str]:
    """0~100 → A/B/C/D/F. None은 None."""
    if score is None:
        return None
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _redistribute(weights: Dict[str, float], excluded: Sequence[str]) -> Dict[str, float]:
    """제외된 모듈의 가중치를 남은 모듈에 비례 재배분."""
    kept = {k: v for k, v in weights.items() if k not in excluded}
    total = sum(kept.values())
    if total == 0:
        return kept
    return {k: v / total for k, v in kept.items()}


def _aggregate(
    modules: List[ModuleScore], weights: Dict[str, float]
) -> Optional[float]:
    """가중평균. score=None인 모듈은 평균에서 제외하고 가중치도 재조정."""
    valid = [(m, weights[m.name]) for m in modules if m.score is not None and m.name in weights]
    total_w = sum(w for _, w in valid)
    if total_w == 0:
        return None
    return round(sum(m.score * w for m, w in valid) / total_w, 1)


def compute_eqs(
    panel: FirmPanel,
    weights: Optional[Dict[str, float]] = None,
) -> EQSResult:
    """단일 기업 패널에 대한 EQS 산출 (단일기업 fallback 모드).

    Cross-section 회귀가 필요한 정확한 M1을 원하면 외부에서
    ``modified_jones_cross_section``으로 별도 산출 후 modules에 끼워 넣는다.
    """
    weights = (weights or DEFAULT_WEIGHTS).copy()
    excluded = sorted(excluded_modules(panel.industry_code))

    modules: List[ModuleScore] = [
        score_m1(panel),
        score_m2(panel),
        score_m3(panel),
        score_m4(panel),
        score_m5(panel),
    ]

    eff_weights = _redistribute(weights, excluded)
    total = _aggregate(modules, eff_weights)
    return EQSResult(
        corp_code=panel.corp_code,
        corp_name=panel.corp_name,
        industry_code=panel.industry_code,
        modules=modules,
        total=total,
        grade=grade_from_score(total),
        excluded=excluded,
    )
