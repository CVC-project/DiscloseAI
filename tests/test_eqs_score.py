"""EQS 종합 점수 + 등급화 + fallback 통합.

v2: fallback 도입으로 업종 제외 없음. 모든 종목에서 5개 모듈 산출.
"""

from modules.financial.eqs import compute_eqs, grade_from_score
from modules.financial.eqs.score import _redistribute, DEFAULT_WEIGHTS
from tests._factories import healthy_panel, manipulator_panel


def test_grade_thresholds():
    assert grade_from_score(95) == "A"
    assert grade_from_score(80) == "A"
    assert grade_from_score(79.9) == "B"
    assert grade_from_score(65) == "B"
    assert grade_from_score(50) == "C"
    assert grade_from_score(35) == "D"
    assert grade_from_score(34.9) == "F"
    assert grade_from_score(0) == "F"
    assert grade_from_score(None) is None


def test_compute_eqs_healthy_returns_high_grade():
    res = compute_eqs(healthy_panel())
    assert res.total is not None
    assert res.grade in ("A", "B")
    assert len(res.modules) == 5
    assert res.excluded == []


def test_compute_eqs_manipulator_low():
    res_h = compute_eqs(healthy_panel())
    res_m = compute_eqs(manipulator_panel())
    assert res_h.total is not None and res_m.total is not None
    assert res_h.total > res_m.total


def test_compute_eqs_financial_all_5_modules():
    """v2: 금융업도 5개 모듈 모두 산출 (fallback 적용)."""
    panel = healthy_panel()
    panel.industry_code = "065"  # 증권
    res = compute_eqs(panel)
    assert res.excluded == []
    module_names = [m.name for m in res.modules]
    assert len(res.modules) == 5
    assert "M2" in module_names
    assert "M3" in module_names


def test_compute_eqs_holding_all_5_modules():
    """v2: 지주사도 5개 모듈 모두 산출 (fallback 적용)."""
    panel = healthy_panel()
    panel.industry_code = "100"
    res = compute_eqs(panel)
    assert res.excluded == []
    assert len(res.modules) == 5
    assert any(m.name == "M1" for m in res.modules)


def test_redistribute_renormalizes():
    # 비어있으면 변화 없음
    new = _redistribute(DEFAULT_WEIGHTS, [])
    assert abs(sum(new.values()) - 1.0) < 1e-9
    assert len(new) == 5
