"""업종 분류 / 예외 처리.

v2: fallback 도입으로 excluded_modules()는 항상 빈 set 반환.
is_financial / is_holding 분류 함수 자체는 유지 (각 모듈 내부에서 사용).
"""

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


def test_excluded_modules_always_empty():
    """v2: fallback 도입으로 업종 제외 없음. 모든 모듈이 항상 활성."""
    assert excluded_modules("064") == set()
    assert excluded_modules("067") == set()
    assert excluded_modules("100") == set()
    assert excluded_modules("013") == set()
    assert excluded_modules(None) == set()


def test_active_modules_all_active():
    """v2: 모든 업종에서 5개 모듈 전부 활성."""
    all_mods = ["M1", "M2", "M3", "M4", "M5"]
    assert active_modules(all_mods, "065") == all_mods
    assert active_modules(all_mods, "100") == all_mods
    assert active_modules(all_mods, "013") == all_mods


def test_is_holding():
    """지주·투자회사 내부 코드 '100' prefix 인식."""
    assert is_holding("100")
    assert is_holding("100A")  # 추후 하위 분류 가능성
    assert not is_holding("013")  # 반도체
    assert not is_holding("064")  # 금융
    assert not is_holding(None)
    assert not is_holding("")
