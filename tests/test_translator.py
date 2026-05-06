"""재무제표 번역기 + highlights."""

from modules.financial.translator import (
    translate_income,
    translate_balance,
    translate_cashflow,
    translate_all,
    extract_highlights,
)
from modules.financial.eqs.types import FirmPanel
from tests._factories import healthy_panel, manipulator_panel, make_year


def test_translate_income_basic():
    y = make_year(2024, revenue=1000, op=120, ni=80)
    out = translate_income(y)
    assert "100원 팔면" in out
    assert "12원" in out  # 영업이익률 12%
    assert "8원" in out  # 순이익률 8%


def test_translate_income_missing():
    y = make_year(2024, revenue=None, op=None)  # type: ignore[arg-type]
    out = translate_income(y)
    assert "부족" in out or "없" in out


def test_translate_balance_debt_ratio():
    y = make_year(2024, ta=1000, tl=220, te=780)
    out = translate_balance(y)
    assert "22%" in out


def test_translate_cashflow_pattern_mature():
    """OCF+, ICF-, FCF- → 여유 있는 구조."""
    y = make_year(2024, ocf=200, icf=-100, fcf=-50)
    out = translate_cashflow(y)
    assert "여유" in out


def test_translate_cashflow_pattern_growth():
    """OCF+, ICF-, FCF+ → 성장 투자 단계."""
    y = make_year(2024, ocf=200, icf=-300, fcf=100)
    out = translate_cashflow(y)
    assert "성장" in out


def test_translate_all_returns_three_lines():
    y = make_year(2024)
    lines = translate_all(y)
    assert len(lines) == 3


def test_highlights_returns_at_most_three():
    h = extract_highlights(manipulator_panel())
    assert len(h) <= 3


def test_highlights_detect_manipulator_signals():
    """분식 의심 패널에서 OCF/NI 괴리 또는 AR 급증 highlight가 잡혀야."""
    h = extract_highlights(manipulator_panel())
    titles = [x.title for x in h]
    assert any("현금" in t or "매출채권" in t or "부채" in t for t in titles)


def test_highlights_severity_ordering():
    """심각도 내림차순 정렬."""
    panel = manipulator_panel()
    h = extract_highlights(panel, top_k=10)
    for a, b in zip(h, h[1:]):
        assert a.severity >= b.severity


def test_highlights_negative_equity_top_priority():
    """자본잠식이 발견되면 최상위로."""
    y0 = make_year(2023)
    y1 = make_year(2024, te=-500, tl=5500, ta=5000)  # 자본 음수
    panel = FirmPanel(corp_code="X", years=[y0, y1])
    h = extract_highlights(panel)
    assert h, "자본잠식이라도 highlight가 비어선 안 됨"
    assert "자본잠식" in h[0].title


def test_highlights_positive_signal_for_healthy():
    h = extract_highlights(healthy_panel())
    titles = [x.title for x in h]
    # 건강한 패널: 부정 highlight 없거나 거의 없고, 긍정 신호가 잡힐 수 있음
    assert all("자본잠식" not in t and "영업적자" not in t for t in titles)
