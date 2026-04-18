"""EQS 종합 점수 + 등급화 + 업종 예외 통합."""

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


def test_compute_eqs_excludes_m3_for_finance():
    panel = healthy_panel()
    panel.industry_code = "065"  # 증권
    res = compute_eqs(panel)
    assert "M3" in res.excluded
    module_names = [m.name for m in res.modules]
    assert "M3" not in module_names
    assert len(res.modules) == 4


def test_redistribute_renormalizes():
    new = _redistribute(DEFAULT_WEIGHTS, ["M3"])
    assert "M3" not in new
    # 남은 4개 가중치 합 == 1
    assert abs(sum(new.values()) - 1.0) < 1e-9
    # 균등 재배분
    for v in new.values():
        assert abs(v - 0.25) < 1e-9
