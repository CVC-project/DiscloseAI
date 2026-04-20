"""OLS 엔진 단위 테스트 — 특이행렬, 표본 부족, 절편 옵션."""

from modules.financial.eqs._ols import ols_simple, ols_multi


def test_ols_simple_normal():
    """기본 경우: y = 10 + 2*x."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [12.0, 14.0, 16.0, 18.0, 20.0]
    result = ols_simple(x, y)
    assert result is not None
    a, b = result
    assert abs(a - 10.0) < 1e-9
    assert abs(b - 2.0) < 1e-9


def test_ols_simple_insufficient_sample():
    """n < 2 → None."""
    assert ols_simple([1.0], [1.0]) is None
    assert ols_simple([], []) is None


def test_ols_simple_mismatched_length():
    """len(x) != len(y) → None."""
    assert ols_simple([1.0, 2.0], [1.0]) is None


def test_ols_simple_zero_variance():
    """x에 분산이 없으면 (모두 같은 값) → None."""
    x = [5.0, 5.0, 5.0]
    y = [10.0, 20.0, 30.0]
    assert ols_simple(x, y) is None


def test_ols_multi_basic():
    """3×2 회귀: y = 2*x1 + 3*x2."""
    X = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    y = [2.0, 3.0, 5.0]
    result = ols_multi(X, y, intercept=False)
    assert result is not None
    assert len(result) == 2
    assert abs(result[0] - 2.0) < 1e-9
    assert abs(result[1] - 3.0) < 1e-9


def test_ols_multi_with_intercept():
    """절편 포함: y = 5 + 2*x1 + 3*x2."""
    X = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    y = [7.0, 8.0, 10.0]
    result = ols_multi(X, y, intercept=True)
    assert result is not None
    assert len(result) == 3  # [절편, β1, β2]
    assert abs(result[0] - 5.0) < 1e-9
    assert abs(result[1] - 2.0) < 1e-9
    assert abs(result[2] - 3.0) < 1e-9


def test_ols_multi_underdetermined():
    """표본 < 변수 개수 → None."""
    X = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]  # 2 rows, 3 cols
    y = [10.0, 20.0]
    assert ols_multi(X, y, intercept=False) is None


def test_ols_multi_singular():
    """특이행렬 (두 열이 선형종속) → None."""
    X = [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]]
    y = [10.0, 20.0, 30.0]
    assert ols_multi(X, y, intercept=False) is None


def test_ols_multi_empty():
    """X 또는 y가 비어있음 → None."""
    assert ols_multi([], [], intercept=False) is None
    assert ols_multi([[1.0, 2.0]], [], intercept=False) is None


def test_ols_multi_mismatched_rows():
    """len(X) != len(y) → None."""
    X = [[1.0, 2.0], [3.0, 4.0]]
    y = [10.0]
    assert ols_multi(X, y, intercept=False) is None
