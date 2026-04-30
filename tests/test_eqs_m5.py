"""M5 — Piotroski F-score.

⚠️ v2 redesign(45b180a)에서 M5를 '자본 성장성(2년 자본 CAGR)'로 변경.
piotroski_f 제거. module-level skip — v2 M5 테스트 재작성 예정.
"""
import pytest
pytest.skip("v1 M5(Piotroski) API stale — 45b180a v2 redesign 이후", allow_module_level=True)

from modules.financial.eqs.m5_piotroski import score_m5, piotroski_f
from modules.financial.eqs.types import FirmPanel
from tests._factories import healthy_panel, make_year


def test_m5_healthy_high():
    """건강 패널은 9개 중 다수 충족."""
    s = score_m5(healthy_panel())
    assert s.score is not None
    assert s.score >= 60


def test_m5_perfect_score():
    """모든 9개 criteria를 만족하도록 설계된 케이스."""
    prev = make_year(
        2023,
        revenue=1000,
        cogs=700,
        ni=50,
        ta=5000,
        ca=2000,
        cl=1500,
        ltd=1000,
        ppe=1500,
        ar=300,
        shares=1000,
        ocf=40,
    )
    curr = make_year(
        2024,
        revenue=1300,  # 매출↑
        cogs=850,  # GM 개선 (1-850/1300=34.6% > 30%)
        ni=120,  # ROA↑
        ta=5500,  # asset turnover: 1300/5500=0.236 > 1000/5000=0.2
        ca=2500,
        cl=1500,  # current ratio↑
        ltd=800,  # 부채↓
        ppe=1500,
        ar=300,
        shares=1000,  # 신주 없음
        ocf=200,  # CFO>0, CFO>NI
    )
    panel = FirmPanel(corp_code="X", years=[prev, curr])
    f = piotroski_f(prev, curr)
    assert f == 9
    assert score_m5(panel).score == 100.0


def test_m5_zero_score_when_all_negative():
    """전부 악화: ROA<0, CFO<0, 부채↑, 신주발행, 마진↓ 등."""
    prev = make_year(
        2023, ni=100, ocf=120, ltd=500, shares=1000, cogs=600, revenue=1000
    )
    curr = make_year(
        2024,
        ni=-100,
        ocf=-50,
        ltd=1000,  # 부채 증가
        shares=1500,  # 신주발행
        cogs=900,
        revenue=900,  # 매출 감소, 마진 악화
        ca=500,
        cl=1500,  # current ratio 악화
    )
    panel = FirmPanel(corp_code="X", years=[prev, curr])
    f = piotroski_f(prev, curr)
    assert f <= 1
    assert score_m5(panel).score is not None


def test_m5_insufficient_panel():
    s = score_m5(FirmPanel(corp_code="X", years=[make_year(2024)]))
    assert s.score is None
