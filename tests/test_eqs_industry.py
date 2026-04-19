"""업종 분류 / 예외 처리."""

from modules.financial.eqs.industry import (
    is_financial,
    excluded_modules,
    active_modules,
)


def test_financial_codes():
    assert is_financial("064")
    assert is_financial("065")
    assert is_financial("066")
    assert is_financial("067")  # 보험


def test_non_financial():
    assert not is_financial("013")  # 반도체
    assert not is_financial(None)
    assert not is_financial("")


def test_excluded_for_finance():
    # 금융업(064~067)은 M2·M3 둘 다 제외
    # M3: OCF 개념 다름, M2: 매출/매출원가 개념 부적합
    assert excluded_modules("064") == {"M2", "M3"}
    assert excluded_modules("067") == {"M2", "M3"}
    assert excluded_modules("013") == set()


def test_active_modules_filters_out_m2_m3():
    """금융업은 M2·M3 모두 빠진 M1/M4/M5만 활성."""
    all_mods = ["M1", "M2", "M3", "M4", "M5"]
    assert active_modules(all_mods, "065") == ["M1", "M4", "M5"]
    assert active_modules(all_mods, "013") == all_mods
