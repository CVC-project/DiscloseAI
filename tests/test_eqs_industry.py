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
    assert excluded_modules("064") == {"M3"}
    assert excluded_modules("013") == set()


def test_active_modules_filters_out_m3():
    all_mods = ["M1", "M2", "M3", "M4", "M5"]
    assert active_modules(all_mods, "065") == ["M1", "M2", "M4", "M5"]
    assert active_modules(all_mods, "013") == all_mods
