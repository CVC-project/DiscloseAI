"""M1 — 발생액 품질 (수정 Jones)."""

from modules.financial.eqs.m1_accruals import (
    score_m1,
    modified_jones_cross_section,
)
from modules.financial.eqs.types import FirmPanel
from tests._factories import healthy_panel, manipulator_panel, make_year


def _varied_panel(seed: int) -> FirmPanel:
    """cross-section 회귀가 풀리도록 패널마다 규모/매출성장/PPE 비중을 변주.

    수정 Jones 회귀변수 3개(1/A, ΔSales/A, PPE/A)가 모두 패널마다 다른 값을
    갖도록 매출성장률·PPE/Asset·자산규모를 독립적으로 흔든다.
    """
    s = 1.0 + 0.07 * seed
    rev_growth = 1.05 + 0.03 * (seed % 4)  # 매출성장 5~14%
    ppe_ratio = 0.25 + 0.04 * (seed % 5)  # PPE/A 25~41%
    rev0 = 1000 * s
    rev1 = rev0 * rev_growth
    ta0 = 5000 * s
    ta1 = 5300 * s
    y0 = make_year(
        2023,
        revenue=rev0,
        ar=300 * s,
        ni=80 * s,
        ocf=70 * s,
        ta=ta0,
        ppe=ta0 * ppe_ratio,
        cogs=700 * s,
    )
    y1 = make_year(
        2024,
        revenue=rev1,
        ar=300 * s + 30 * (seed % 3),
        ni=90 * s,
        ocf=80 * s,
        ta=ta1,
        ppe=ta1 * ppe_ratio,
        cogs=770 * s,
    )
    return FirmPanel(corp_code=str(seed), years=[y0, y1])


def test_score_m1_healthy_high():
    """건강한 기업: |TA/A| 작음 → 80점 이상."""
    s = score_m1(healthy_panel())
    assert s.score is not None
    assert s.score >= 80


def test_score_m1_manipulator_lower_than_healthy():
    """분식 의심 패널의 |TA/A|가 더 크므로 점수가 healthy보다 낮아야."""
    s_h = score_m1(healthy_panel()).score
    s_m = score_m1(manipulator_panel()).score
    assert s_h is not None and s_m is not None
    assert s_m < s_h


def test_score_m1_insufficient_panel():
    panel = FirmPanel(corp_code="X", years=[make_year(2024)])
    s = score_m1(panel)
    assert s.score is None
    assert "부족" in s.note


def test_score_m1_missing_ocf():
    y0 = make_year(2023)
    y1 = make_year(2024, ocf=None)  # type: ignore[arg-type]
    panel = FirmPanel(corp_code="X", years=[y0, y1])
    s = score_m1(panel)
    assert s.score is None


def test_cross_section_needs_min_sample():
    """표본 8개 미만이면 None."""
    panels = [_varied_panel(i) for i in range(3)]
    res = modified_jones_cross_section(panels, "0", year=2024)
    assert res is None


def test_cross_section_runs_with_enough_sample():
    panels = [_varied_panel(i) for i in range(12)]
    res = modified_jones_cross_section(panels, "5", year=2024)
    assert res is not None
    assert res.name == "M1"
    assert 0 <= res.score <= 100
