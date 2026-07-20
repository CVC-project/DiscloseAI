"""EQS v2 종합 점수 + 등급.

5개 모듈을 동일 가중(각 20%)으로 단순 평균.
일부 모듈이 score=None인 경우(예: 금융업의 M2 적용 제외, 데이터 결측) 해당
모듈을 제외하고 남은 모듈만 평균.

등급 (한국 시장 통용):
  A ≥ 80, B ≥ 65, C ≥ 50, D ≥ 35, F < 35

설계: ``modules/financial/EQS_V2_DESIGN.md`` §3.
v1의 가중치 재배분·산업별 fallback 분기는 모두 제거 (각 모듈 내부에서 처리).
"""

from __future__ import annotations

from typing import List, Optional

from .calibration import CalibrationResult
from .m1_accruals import score_m1
from .m2_beneish import score_m2
from .m3_cashflow import score_m3
from .m4_persistence import score_m4
from .m5_piotroski import score_m5
from .types import EQSResult, FirmPanel, ModuleScore


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


def _aggregate(modules: List[ModuleScore]) -> Optional[float]:
    """이력 신뢰도를 반영한 가중 평균. score=None 모듈은 제외."""
    valid = [(m.score, m.weight) for m in modules if m.score is not None]
    if not valid:
        return None
    weight_total = sum(weight for _, weight in valid)
    return round(sum(score * weight for score, weight in valid) / weight_total, 1)


def compute_eqs(
    panel: FirmPanel, calibration: CalibrationResult | None = None
) -> EQSResult:
    """단일 기업 EQS 산출. calibration이 있으면 v3 업종분포 기준을 쓴다."""
    modules: List[ModuleScore] = [
        score_m1(panel, short_history_weighting=calibration is not None),
        score_m2(panel, calibration),
        score_m3(panel, calibration),
        score_m4(panel, calibration),
        score_m5(panel, calibration),
    ]
    excluded = [m.name for m in modules if m.score is None]
    total = _aggregate(modules)
    return EQSResult(
        corp_code=panel.corp_code,
        corp_name=panel.corp_name,
        industry_code=panel.industry_code,
        modules=modules,
        total=total,
        grade=grade_from_score(total),
        excluded=excluded,
    )
