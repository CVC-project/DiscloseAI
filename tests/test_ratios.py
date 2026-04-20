"""수익성 비율 계산 단위 테스트."""

from __future__ import annotations

import pytest

from modules.financial.eqs.types import FirmYear
from modules.financial.translator.ratios import LABELS, Ratios, compute_ratios

from tests._factories import make_year


def test_compute_ratios_happy_path():
    """정상 케이스: 모든 필드 채워져 있을 때 정확한 계산."""
    # revenue=1000, cogs=700, op=200, ni=100, equity=3000, assets=5000
    year = make_year(2024)
    r = compute_ratios(year)

    # gross_margin = (1000 - 700) / 1000 * 100 = 30.0
    assert r.gross_margin == pytest.approx(30.0)
    # operating_margin = 200 / 1000 * 100 = 20.0
    assert r.operating_margin == pytest.approx(20.0)
    # net_margin = 100 / 1000 * 100 = 10.0
    assert r.net_margin == pytest.approx(10.0)
    # roe = 100 / 3000 * 100 ≈ 3.33
    assert r.roe == pytest.approx(100 / 3000 * 100)
    # roa = 100 / 5000 * 100 = 2.0
    assert r.roa == pytest.approx(2.0)


def test_compute_ratios_missing_revenue():
    """revenue=None이면 margin 3개는 None, ROE·ROA는 계산됨."""
    year = make_year(2024, revenue=None, cogs=None)
    r = compute_ratios(year)

    assert r.gross_margin is None
    assert r.operating_margin is None
    assert r.net_margin is None
    assert r.roe is not None
    assert r.roa is not None


def test_compute_ratios_missing_equity():
    """total_equity=None이면 ROE는 None, 나머지는 정상."""
    year = make_year(2024, te=None)
    r = compute_ratios(year)

    assert r.roe is None
    assert r.roa is not None
    assert r.gross_margin is not None


def test_compute_ratios_zero_revenue():
    """분모 0일 때 division by zero 대신 None 반환."""
    year = make_year(2024, revenue=0)
    r = compute_ratios(year)

    assert r.gross_margin is None
    assert r.operating_margin is None
    assert r.net_margin is None


def test_compute_ratios_missing_cogs_only():
    """cogs만 None이면 gross_margin은 None, 나머지는 정상."""
    year = make_year(2024, cogs=None)
    r = compute_ratios(year)

    assert r.gross_margin is None
    assert r.operating_margin == pytest.approx(20.0)
    assert r.net_margin == pytest.approx(10.0)


def test_compute_ratios_negative_values():
    """영업적자·순적자도 음수 비율로 반환 (None 아님)."""
    year = make_year(2024, op=-100, ni=-50)
    r = compute_ratios(year)

    assert r.operating_margin == pytest.approx(-10.0)
    assert r.net_margin == pytest.approx(-5.0)
    assert r.roe == pytest.approx(-50 / 3000 * 100)


def test_ratios_as_dict_keys():
    """as_dict()가 LABELS와 일치하는 키를 반환."""
    r = compute_ratios(make_year(2024))
    d = r.as_dict()

    assert set(d.keys()) == set(LABELS.keys())


def test_compute_ratios_empty_year():
    """모든 값이 None인 FirmYear → 모든 비율 None."""
    year = FirmYear(year=2024)
    r = compute_ratios(year)

    assert r.gross_margin is None
    assert r.operating_margin is None
    assert r.net_margin is None
    assert r.roe is None
    assert r.roa is None
