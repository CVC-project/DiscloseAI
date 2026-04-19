"""M3 — OCF/NI 괴리 추세."""

from modules.financial.eqs.m3_cashflow import score_m3
from modules.financial.eqs.types import FirmPanel
from tests._factories import healthy_panel, make_year


def test_m3_healthy_high():
    """OCF/NI ≈ 1.2 일관 → 평균/추세/변동성 모두 양호."""
    s = score_m3(healthy_panel())
    assert s.score is not None
    assert s.score >= 70


def test_m3_low_when_ocf_lags_ni():
    years = [
        make_year(2020, ni=100, ocf=20),
        make_year(2021, ni=100, ocf=20),
        make_year(2022, ni=100, ocf=20),
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is not None
    assert s.score < 50


def test_m3_skips_negative_ni_years():
    """NI<=0인 해는 비율 무의미 → 제외 후 남는 표본만 사용."""
    years = [
        make_year(2020, ni=-50, ocf=20),  # 제외
        make_year(2021, ni=100, ocf=120),
        make_year(2022, ni=100, ocf=120),
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is not None  # 2개 남아서 산출됨


def test_m3_insufficient_data():
    years = [make_year(2020, ni=100, ocf=120)]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is None
