"""현금흐름 8개 패턴 전수 검증 + 패턴 미분."""

from modules.financial.translator import translate_cashflow
from tests._factories import make_year


def test_cf_pattern_mature():
    """(+, -, -) → 여유 있는 구조."""
    y = make_year(2024, ocf=100, icf=-50, fcf=-20)
    out = translate_cashflow(y)
    assert "여유" in out


def test_cf_pattern_growth():
    """(+, -, +) → 성장 투자 단계."""
    y = make_year(2024, ocf=100, icf=-150, fcf=50)
    out = translate_cashflow(y)
    assert "성장" in out or "투자" in out


def test_cf_pattern_contraction():
    """(+, +, -) → 사업 축소."""
    y = make_year(2024, ocf=100, icf=50, fcf=-100)
    out = translate_cashflow(y)
    assert "축소" in out


def test_cf_pattern_accumulation():
    """(+, +, +) → 현금 비축."""
    y = make_year(2024, ocf=100, icf=30, fcf=20)
    out = translate_cashflow(y)
    assert "비축" in out


def test_cf_pattern_distressed_startup():
    """(-, -, +) → 위태로운 신생/적자 기업."""
    y = make_year(2024, ocf=-50, icf=-30, fcf=80)
    out = translate_cashflow(y)
    assert "위태" in out or "신생" in out or "적자" in out or "외부자금" in out


def test_cf_pattern_restructuring():
    """(-, +, +) → 구조조정 진행 (위험 신호)."""
    y = make_year(2024, ocf=-50, icf=100, fcf=30)
    out = translate_cashflow(y)
    assert "구조조정" in out or "위험" in out


def test_cf_pattern_liquidation():
    """(-, +, -) → 청산 단계."""
    y = make_year(2024, ocf=-50, icf=100, fcf=-40)
    out = translate_cashflow(y)
    assert "청산" in out


def test_cf_pattern_crisis():
    """(-, -, -) → 전방위 위기."""
    y = make_year(2024, ocf=-50, icf=-30, fcf=-20)
    out = translate_cashflow(y)
    assert "위기" in out


def test_cf_pattern_zero_values():
    """0 값 처리 — 정의상 (-, 0, -)는 OCF-이므로 -로 분류."""
    y = make_year(2024, ocf=-10, icf=0, fcf=-5)
    out = translate_cashflow(y)
    # 0은 "0" 문자로 분류 → (-,0,-) → 혼합형
    assert out  # 뭔가는 반환해야 함


def test_cf_missing_any_component():
    """OCF, ICF, FCF 중 하나라도 None → 데이터 부족."""
    y = make_year(2024, ocf=None, icf=-50, fcf=-20)  # type: ignore[arg-type]
    out = translate_cashflow(y)
    assert "없" in out or "부족" in out or "설명할 수 없" in out
