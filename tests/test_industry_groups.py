"""업종 그룹 매핑 + 섹터 평균 집계 단위 테스트."""

from __future__ import annotations

import json
import os

import pytest

from modules.financial.industry_groups import (
    SECTORS,
    SectorStats,
    compute_sector_stats,
    get_sector,
    load_sector_stats,
    save_sector_stats,
    sector_members,
)


def test_get_sector_samsung():
    """삼성전자 → 반도체/전자부품."""
    assert get_sector("삼성전자") == "반도체/전자부품"


def test_get_sector_preferred_stock_same_as_common():
    """우선주는 본주와 같은 섹터."""
    assert get_sector("삼성전자우") == get_sector("삼성전자")


def test_get_sector_financial():
    """금융/보험 섹터 회사들 확인."""
    assert get_sector("KB금융") == "금융/보험"
    assert get_sector("삼성생명") == "금융/보험"
    assert get_sector("미래에셋증권") == "금융/보험"


def test_get_sector_etf_excluded():
    """KODEX 200 같은 ETF는 None (섹터 없음)."""
    assert get_sector("KODEX 200") is None


def test_get_sector_unknown():
    """매핑 없는 이름 → None."""
    assert get_sector("없는회사XYZ") is None


def test_sectors_cover_kospi50():
    """KOSPI 50 중 ETF(KODEX 200) 제외한 49개 전부 섹터 매핑되어야."""
    from modules.financial.batch import KOSPI_TOP_50

    unmapped = [n for n in KOSPI_TOP_50 if n != "KODEX 200" and get_sector(n) is None]
    assert unmapped == [], f"Unmapped: {unmapped}"


def test_sectors_no_duplicates():
    """한 회사가 2개 이상 섹터에 속하면 안 됨."""
    seen: dict[str, str] = {}
    for sector, members in SECTORS.items():
        for m in members:
            assert m not in seen, f"{m} 중복: {seen.get(m)} + {sector}"
            seen[m] = sector


def test_sector_members_lookup():
    """sector_members()로 구성원 리스트 조회."""
    members = sector_members("반도체/전자부품")
    assert "삼성전자" in members
    assert "SK하이닉스" in members


def test_compute_sector_stats_basic():
    """3개 반도체 회사의 평균이 올바르게 계산됨."""
    company_ratios = {
        "삼성전자": {
            "gross_margin": 30.0, "operating_margin": 12.0,
            "net_margin": 10.0, "roe": 10.0, "roa": 5.0,
        },
        "SK하이닉스": {
            "gross_margin": 40.0, "operating_margin": 18.0,
            "net_margin": 15.0, "roe": 15.0, "roa": 7.0,
        },
        "삼성전기": {
            "gross_margin": 20.0, "operating_margin": 6.0,
            "net_margin": 5.0, "roe": 5.0, "roa": 3.0,
        },
    }
    stats = compute_sector_stats(company_ratios)
    semi = stats["반도체/전자부품"]
    assert semi.n_companies == 3
    assert semi.avg_gross_margin == pytest.approx(30.0)  # (30+40+20)/3
    assert semi.avg_operating_margin == pytest.approx(12.0)
    assert semi.avg_net_margin == pytest.approx(10.0)
    assert semi.avg_roe == pytest.approx(10.0)
    assert semi.avg_roa == pytest.approx(5.0)


def test_compute_sector_stats_ignores_none():
    """None 값은 평균 계산에서 제외."""
    company_ratios = {
        "삼성전자": {"gross_margin": 30.0, "roe": None},
        "SK하이닉스": {"gross_margin": 40.0, "roe": 15.0},
    }
    stats = compute_sector_stats(company_ratios)
    semi = stats["반도체/전자부품"]
    assert semi.avg_gross_margin == pytest.approx(35.0)
    assert semi.avg_roe == pytest.approx(15.0)  # None 제외하고 1개만


def test_compute_sector_stats_all_none_returns_none():
    """모든 회사가 None이면 평균도 None."""
    company_ratios = {
        "삼성전자": {"gross_margin": None, "roe": None},
        "SK하이닉스": {"gross_margin": None, "roe": None},
    }
    stats = compute_sector_stats(company_ratios)
    semi = stats["반도체/전자부품"]
    assert semi.avg_gross_margin is None
    assert semi.avg_roe is None


def test_compute_sector_stats_unmapped_company_ignored():
    """매핑 없는 회사는 조용히 제외됨."""
    company_ratios = {
        "삼성전자": {"gross_margin": 30.0},
        "없는회사": {"gross_margin": 100.0},  # 무시되어야
    }
    stats = compute_sector_stats(company_ratios)
    assert stats["반도체/전자부품"].avg_gross_margin == pytest.approx(30.0)


def test_save_and_load_sector_stats(tmp_path):
    """JSON 왕복 저장·로드."""
    original = {
        "반도체/전자부품": SectorStats(
            sector="반도체/전자부품",
            n_companies=3,
            avg_gross_margin=30.0,
            avg_roe=10.0,
            members=["삼성전자", "SK하이닉스", "삼성전기"],
        ),
    }
    path = str(tmp_path / "sector_stats.json")
    save_sector_stats(original, path)

    loaded = load_sector_stats(path)
    assert "반도체/전자부품" in loaded
    assert loaded["반도체/전자부품"].avg_gross_margin == 30.0
    assert loaded["반도체/전자부품"].n_companies == 3
    assert loaded["반도체/전자부품"].members == ["삼성전자", "SK하이닉스", "삼성전기"]


def test_load_sector_stats_missing_file_returns_empty(tmp_path):
    """파일 없으면 빈 dict."""
    path = str(tmp_path / "nonexistent.json")
    assert load_sector_stats(path) == {}
