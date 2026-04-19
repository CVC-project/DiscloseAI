"""업종 분류 / 예외 처리."""

from modules.financial.eqs.industry import (
    is_financial,
    is_holding,
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


def test_is_holding():
    """지주·투자회사 내부 코드 '100' prefix 인식."""
    assert is_holding("100")
    assert is_holding("100A")  # 추후 하위 분류 가능성
    assert not is_holding("013")  # 반도체
    assert not is_holding("064")  # 금융
    assert not is_holding(None)
    assert not is_holding("")


def test_excluded_for_holding():
    """지주사(100)는 M1만 제외. 자회사 지분법이익이 단일기업 fallback에 부적합."""
    assert excluded_modules("100") == {"M1"}


def test_active_modules_filters_out_m1_for_holding():
    """지주사는 M1만 빠진 M2/M3/M4/M5 활성."""
    all_mods = ["M1", "M2", "M3", "M4", "M5"]
    assert active_modules(all_mods, "100") == ["M2", "M3", "M4", "M5"]
