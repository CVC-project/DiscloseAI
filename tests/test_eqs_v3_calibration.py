from __future__ import annotations

from modules.financial.eqs.calibration import (
    CalibrationResult,
    build_calibration,
    metric_values,
    profile_for_panel,
    score_against_peers,
)
from modules.financial.eqs.m2_beneish import score_m2
from modules.financial.eqs.m4_persistence import score_m4
from modules.financial.eqs.score import compute_eqs
from modules.financial.eqs.types import FirmPanel, FirmYear


def make_panel(index: int, industry_code: str = "26110") -> FirmPanel:
    equity_2023 = 100.0
    equity_2024 = 100.0 + index
    equity_2025 = 100.0 + index * 2
    years = [
        FirmYear(
            year=2023,
            revenue=100.0,
            operating_income=5.0 + index,
            operating_cashflow=8.0 + index,
            total_liabilities=40.0 + index,
            total_equity=equity_2023,
            accounts_receivable=10.0,
        ),
        FirmYear(
            year=2024,
            revenue=110.0,
            operating_income=6.0 + index,
            operating_cashflow=9.0 + index,
            total_liabilities=42.0 + index,
            total_equity=equity_2024,
            accounts_receivable=11.0 + index * 0.1,
        ),
        FirmYear(
            year=2025,
            revenue=121.0,
            operating_income=7.0 + index,
            operating_cashflow=10.0 + index,
            total_liabilities=44.0 + index,
            total_equity=equity_2025,
            accounts_receivable=12.1 + index * 0.2,
        ),
    ]
    return FirmPanel(
        corp_code=f"{index:08d}",
        corp_name=f"Peer {index}",
        industry_code=industry_code,
        years=years,
    )


def test_industry_profile_and_market_fallback_are_built():
    panels = [make_panel(index) for index in range(25)]
    calibration = build_calibration(panels, min_peers=20)

    industry_profile = calibration.profile_for("KSIC-261", "m3_debt_to_equity")
    assert industry_profile is not None
    assert industry_profile.sample_size == 25
    assert industry_profile.p10 < industry_profile.p50 < industry_profile.p90

    unknown = make_panel(1, industry_code="99999")
    market_profile = profile_for_panel(calibration, unknown, "m3_debt_to_equity")
    assert market_profile is not None
    assert market_profile.group == "MARKET"


def test_peer_scoring_tracks_percentile_direction():
    calibration = build_calibration([make_panel(index) for index in range(25)], min_peers=20)
    profile = calibration.profile_for("KSIC-261", "m3_debt_to_equity")
    assert profile is not None
    assert score_against_peers(profile.p10, profile, higher_is_better=False) == 100.0
    assert score_against_peers(profile.p50, profile, higher_is_better=False) == 50.0
    assert score_against_peers(profile.p90, profile, higher_is_better=False) == 0.0


def test_calibration_round_trip_preserves_profiles():
    calibration = build_calibration([make_panel(index) for index in range(25)], min_peers=20)
    restored = CalibrationResult.from_dict(calibration.as_dict())
    assert restored.profile_for("KSIC-261", "m4_average_margin") == calibration.profile_for(
        "KSIC-261", "m4_average_margin"
    )


def test_financial_m2_is_excluded_by_ksic_only():
    finance_panel = make_panel(3, industry_code="64132")
    assert "m2_receivable_gap" not in metric_values(finance_panel)
    assert score_m2(finance_panel).score is None


def test_financial_panels_fall_back_to_broad_financial_peers():
    non_financial = [make_panel(index, "26110") for index in range(25)]
    financial = (
        [make_panel(index + 30, "64132") for index in range(10)]
        + [make_panel(index + 40, "65110") for index in range(10)]
        + [make_panel(index + 50, "66110") for index in range(10)]
    )

    calibration = build_calibration(non_financial + financial, min_peers=20)
    profile = profile_for_panel(calibration, financial[0], "m3_debt_to_equity")
    assert profile is not None
    assert profile.group == "FINANCIAL"
    assert profile.sample_size == 30


def test_m4_uses_peer_margin_and_stability_scores():
    panels = [make_panel(index) for index in range(25)]
    calibration = build_calibration(panels, min_peers=20)
    low = score_m4(panels[1], calibration)
    high = score_m4(panels[-1], calibration)
    assert low.score is not None
    assert high.score is not None
    assert high.score > low.score


def test_v3_two_year_history_uses_reliability_weighted_modules():
    peers = [make_panel(index) for index in range(25)]
    calibration = build_calibration(peers, min_peers=20)
    panel = make_panel(2)
    panel.years = panel.years[-2:]

    result = compute_eqs(panel, calibration)
    modules = {module.name: module for module in result.modules}

    assert modules["M1"].score is not None
    assert modules["M4"].score is not None
    assert modules["M5"].score is not None
    assert modules["M1"].weight == 0.70
    assert modules["M4"].weight == 0.70
    assert modules["M5"].weight == 0.60
    assert result.total is not None


def test_v3_one_year_history_uses_only_interpretable_modules():
    peers = [make_panel(index) for index in range(25)]
    calibration = build_calibration(peers, min_peers=20)
    panel = make_panel(2)
    panel.years = panel.years[-1:]

    result = compute_eqs(panel, calibration)
    modules = {module.name: module for module in result.modules}

    assert modules["M1"].score is not None
    assert modules["M3"].score is not None
    assert modules["M4"].score is not None
    assert modules["M2"].score is None
    assert modules["M5"].score is None
    assert modules["M1"].weight == 0.40
    assert modules["M4"].weight == 0.40
