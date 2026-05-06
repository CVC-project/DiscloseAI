"""의존성 없는 작은 OLS — numpy 추가를 피하려고 직접 구현.

- ``ols_simple``: 단변량 회귀 (AR(1)용)
- ``ols_multi``: k-변수 회귀 (수정 Jones는 절편 없는 3변수)
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple


def ols_simple(x: Sequence[float], y: Sequence[float]) -> Optional[Tuple[float, float]]:
    """y = a + b*x. (a, b)를 반환. 표본이 부족하거나 x 분산이 0이면 None."""
    n = len(x)
    if n != len(y) or n < 2:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = sum((xi - mx) ** 2 for xi in x)
    if den == 0:
        return None
    b = num / den
    a = my - b * mx
    return a, b


def _solve(matrix: List[List[float]]) -> Optional[List[float]]:
    """가우스 소거법으로 정사각 augmented matrix [A|b]를 풀어 x 반환.

    부분 피벗팅으로 수치 안정성을 약간 챙긴다. 특이행렬이면 None.
    """
    n = len(matrix)
    a = [row[:] for row in matrix]  # 복사 (호출자 보호)
    for i in range(n):
        # 피벗 행 선택 (절댓값 최대)
        pivot_row = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[pivot_row][i]) < 1e-12:
            return None
        a[i], a[pivot_row] = a[pivot_row], a[i]
        # 정규화
        pivot = a[i][i]
        for j in range(i, n + 1):
            a[i][j] /= pivot
        # 제거
        for r in range(n):
            if r == i:
                continue
            factor = a[r][i]
            if factor == 0:
                continue
            for j in range(i, n + 1):
                a[r][j] -= factor * a[i][j]
    return [row[n] for row in a]


def ols_multi(
    X: Sequence[Sequence[float]], y: Sequence[float], intercept: bool = False
) -> Optional[List[float]]:
    """다변량 OLS. ``X``는 n×k, 반환 계수는 [β1, ..., βk] (intercept=True면 첫 항이 절편).

    정규방정식 (Xᵀ X) β = Xᵀ y 를 풀어 반환. 표본 부족·특이행렬이면 None.
    """
    n = len(X)
    if n == 0 or n != len(y):
        return None
    rows = [list(row) for row in X]
    if intercept:
        rows = [[1.0] + r for r in rows]
    k = len(rows[0])
    if n < k:
        return None
    # XᵀX
    xtx = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            xtx[i][j] = sum(rows[r][i] * rows[r][j] for r in range(n))
    # Xᵀy
    xty = [sum(rows[r][i] * y[r] for r in range(n)) for i in range(k)]
    # augmented
    aug = [xtx[i] + [xty[i]] for i in range(k)]
    return _solve(aug)
