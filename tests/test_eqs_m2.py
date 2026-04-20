"""M2 — Beneish M-score."""

from modules.financial.eqs.m2_beneish import (
    score_m2,
    m_score,
    BENEISH_US,
    M_THRESHOLD,
    _panel_has_cogs,
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


def test_panel_has_cogs_with_manufacturing():
    """제조업 기업 — COGS 있음."""
    panel = healthy_panel()
    assert _panel_has_cogs(panel) is True


def test_panel_has_cogs_service_company():
    """서비스/플랫폼 기업 — COGS 모두 None."""
    years = [
        make_year(2022, cogs=None),
        make_year(2023, cogs=None),
        make_year(2024, cogs=None),
    ]
    panel = FirmPanel(corp_code="SERVICE", years=years)
    assert _panel_has_cogs(panel) is False


def test_score_m2_service_company_fallback():
    """서비스 기업 자동 감지 → TATA+SGI fallback으로 점수 산출."""
    years = [
        make_year(2023, cogs=None, revenue=1000, ni=100),
        make_year(2024, cogs=None, revenue=1200, ni=120),
    ]
    panel = FirmPanel(corp_code="SERVICE", years=years)
    s = score_m2(panel)
    assert s.score is not None  # fallback으로 점수 나옴
    assert "fallback" in s.note
    assert "매출원가 없음" in s.note


def test_score_m2_missing_core_index_fallback():
    """핵심 지수 결측 시 fallback 적용."""
    y0 = make_year(2023, revenue=1000, cogs=700, ni=100, ocf=120)
    # y1에서 revenue=None → 정상 M-score 불가, fallback도 매출 필요
    y1 = make_year(2024, revenue=None, cogs=None, ni=150, ocf=180)
    panel = FirmPanel(corp_code="X", years=[y0, y1])
    s = score_m2(panel)
    # revenue가 None이면 fallback도 산출 불가
    assert s.score is None


def test_score_m2_partial_cogs_mixed():
    """COGS가 일부만 있는 경우 — has_cogs=True이므로 정상 계산."""
    years = [
        make_year(2023, cogs=700, revenue=1000),
        make_year(2024, cogs=800, revenue=1200),  # 둘 다 있음
    ]
    panel = FirmPanel(corp_code="X", years=years)
    assert _panel_has_cogs(panel) is True


def test_score_m2_service_with_one_cogs():
    """대부분 서비스이지만 한 해는 COGS 있는 경우 → has_cogs=True."""
    years = [
        make_year(2022, cogs=None),
        make_year(2023, cogs=None),
        make_year(2024, cogs=100),  # 마지막 해만
    ]
    panel = FirmPanel(corp_code="MIXED", years=years)
    assert _panel_has_cogs(panel) is True
