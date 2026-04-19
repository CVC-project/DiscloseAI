"""M2 — Beneish M-score."""

from modules.financial.eqs.m2_beneish import (
    score_m2,
    m_score,
    BENEISH_US,
    M_THRESHOLD,
)
from modules.financial.eqs.types import FirmPanel
from tests._factories import healthy_panel, manipulator_panel, make_year


def test_m_score_healthy_below_threshold():
    panel = healthy_panel()
    m = m_score(panel.prior(), panel.latest(), BENEISH_US)
    assert m is not None
    assert m < M_THRESHOLD  # 정상


def test_m_score_manipulator_above_threshold():
    panel = manipulator_panel()
    m = m_score(panel.prior(), panel.latest(), BENEISH_US)
    assert m is not None
    assert m > M_THRESHOLD


def test_score_m2_healthy_higher_than_manipulator():
    s_h = score_m2(healthy_panel()).score
    s_m = score_m2(manipulator_panel()).score
    assert s_h is not None and s_m is not None
    assert s_h > s_m


def test_score_m2_missing_data():
    y0 = make_year(2023, revenue=None)  # type: ignore[arg-type]
    y1 = make_year(2024)
    panel = FirmPanel(corp_code="X", years=[y0, y1])
    s = score_m2(panel)
    assert s.score is None


def test_score_m2_insufficient_panel():
    panel = FirmPanel(corp_code="X", years=[make_year(2024)])
    s = score_m2(panel)
    assert s.score is None
