"""M4 — 이익 지속성 (AR(1) + 일회성 비중).

핵심 가설: 양질의 이익은 다음 기간에도 유지된다.

지속성 = AR(1) 회귀계수 φ:  E_t = α + φ·E_(t-1) + ε
- φ가 1에 가까울수록 영구적(persistent), 0에 가까울수록 일회성
- 음수면 평균회귀, 1 초과면 폭주(불안)

일회성 비중 = nonrecurring / |NI|. 클수록 감점.
이익은 자산 대비 ROA로 정규화한다 — 절대규모 트렌드 영향을 줄이려고.

**사이클 산업 보정 (옵션 c)**:
반도체·조선·정유 등 경기 사이클이 깊은 산업은 5년 윈도우에서 침체 1번에
AR(1) φ가 음수로 추정되어 점수가 0이 된다. 이를 보정하기 위해:

1. **권장 윈도우 10년+**: 패널이 길수록 사이클이 평균화된다.
2. **robust trim**: 패널이 7년 이상이면 가장 큰 잔차 1점(=사이클 침체)을 제외하고
   재추정. 1회성 충격을 사이클 잡음으로 처리.
3. **note에 윈도우 길이 명시**: 짧은 윈도우 추정의 신뢰도를 사용자가 알도록.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ._ols import ols_simple
from .types import FirmPanel, FirmYear, ModuleScore

# AR(1) 추정을 시도할 최소 연도 수. 미만이면 None 반환.
# 이론적으로는 3년이면 pair 2개로 기울기 계산 가능하지만, 3~4년 노이즈가
# 심해 φ가 ±1 극단값으로 튀는 경우가 많음 (예: 금융지주사). 5년 이상 요구해
# 통계적 신뢰도 확보.
MIN_YEARS = 5
# 이 길이 이상이면 robust trim(사이클 outlier 1점 제거) 적용
ROBUST_MIN_YEARS = 7
# 이 길이 이상이면 추정이 안정적이라는 의미로 note 표기
STABLE_MIN_YEARS = 10


def _roa_series(panel: FirmPanel) -> List[Tuple[int, float]]:
    out: List[Tuple[int, float]] = []
    for y in panel.years:
        if y.net_income is None or not y.total_assets:
            continue
        out.append((y.year, y.net_income / y.total_assets))
    return out


def _phi_to_score(phi: float) -> float:
    """φ를 0~100으로 변환.

    구간별 해석:
    - φ > 2 또는 φ ≤ -1: 발산/극단 반전 → 0점 (불안정)
    - 1 < φ ≤ 2: 폭주 구간. 100 → 0으로 감소 (과열 경고)
    - -1 < φ ≤ 1: 주 구간. 50+50·φ 선형. (φ=-1→0, φ=0→50, φ=1→100)

    경계 처리: φ=1.0은 "완전 지속(이상적)"이므로 주구간 상단 100점으로 처리.
    폭주 경고는 φ > 1.0에서 시작한다.

    변경 이력: 기존 하드 컷오프(φ≤0 즉시 0점)는 5년 단기 AR(1) 추정 노이즈에
    지나치게 민감했음. 경미한 음수 φ(예: -0.3)는 "들쑥날쑥 경향"으로 낮지만
    0점은 아닌 점수를 주도록 선형 매핑 구간을 [-1, 1]로 확장.
    """
    # 극단값 먼저 처리 (발산·완전반전)
    if phi > 2.0 or phi <= -1.0:
        return 0.0
    # 폭주 구간 (1, 2]: 100→0 선형. φ=1.5면 50점.
    if phi > 1.0:
        return round(100 * (2 - phi), 1)
    # 주 구간 [-1, 1]: φ=-1→0, φ=0→50, φ=1→100
    return round(50 + 50 * phi, 1)


def _nonrecurring_penalty(panel: FirmPanel) -> Optional[float]:
    curr = panel.latest()
    if not curr or curr.nonrecurring_income is None or not curr.net_income:
        return None
    return min(1.0, abs(curr.nonrecurring_income) / abs(curr.net_income))


def _robust_ar1(roa: List[float]) -> Optional[Tuple[float, int]]:
    """가장 큰 잔차의 **관측치 1개**를 trim하고 AR(1) φ 재추정.

    핵심: 단순히 잔차가 큰 1행만 제거하면, 사이클 침체 관측치는 (x=정상, y=침체)와
    (x=침체, y=회복) 두 행에 모두 등장하므로 한쪽만 제거해도 다른 쪽이 fit을 망가뜨림.
    따라서 침체 관측치 자체(roa의 한 원소)를 식별해 그것이 등장하는 모든 행을 제거.

    반환: (phi, 제거한 roa 원소의 인덱스). 추정 실패 시 None.
    """
    x = roa[:-1]
    y = roa[1:]
    fit = ols_simple(x, y)
    if fit is None:
        return None
    a, b = fit
    residuals = [yi - (a + b * xi) for xi, yi in zip(x, y)]
    # 잔차가 가장 큰 행 → 그 행의 y 또는 x 중 어느 것이 침체인지 찾기 위해
    # 일단 |residual|이 가장 큰 행의 y쪽(=roa[i+1])을 침체 후보로 본다 (가장 흔한 패턴)
    bad_row = max(range(len(residuals)), key=lambda i: abs(residuals[i]))
    outlier_obs = bad_row + 1  # roa-index

    # outlier_obs가 등장하는 모든 (x, y) 행 제외
    new_x: List[float] = []
    new_y: List[float] = []
    for i, (xi, yi) in enumerate(zip(x, y)):
        if i == outlier_obs or (i + 1) == outlier_obs:
            continue
        new_x.append(xi)
        new_y.append(yi)
    refit = ols_simple(new_x, new_y)
    if refit is None:
        return None
    return refit[1], outlier_obs


def score_m4(panel: FirmPanel, *, robust: bool = True) -> ModuleScore:
    """이익 지속성 점수.

    Args:
        panel: 다년도 패널. 5년 미만이면 None 반환, 10년+ 권장.
        robust: True(기본)이면 7년+ 패널에서 사이클 outlier 1점 trim 후 재추정.
                기존 5년 단순 AR(1) 결과로 회귀 검증하려면 False.
    """
    series = _roa_series(panel)
    n = len(series)
    if n < MIN_YEARS:
        return ModuleScore(
            name="M4",
            score=None,
            note=f"ROA 시계열 {n}년 — AR(1) 추정에 최소 {MIN_YEARS}년 필요",
        )
    roa = [s[1] for s in series]

    used_robust = False
    dropped_year: Optional[int] = None
    if robust and n >= ROBUST_MIN_YEARS:
        result = _robust_ar1(roa)
        if result is not None:
            phi, outlier_obs = result
            # outlier_obs는 roa-index → series에서 동일 인덱스의 연도
            dropped_year = series[outlier_obs][0]
            used_robust = True
        else:
            phi = None
    else:
        fit = ols_simple(roa[:-1], roa[1:])
        if fit is None:
            return ModuleScore(name="M4", score=None, note="AR(1) 추정 실패(분산 0)")
        phi = fit[1]

    if phi is None:
        return ModuleScore(name="M4", score=None, note="AR(1) 추정 실패")

    base = _phi_to_score(phi)
    penalty = _nonrecurring_penalty(panel)

    note_parts = [f"φ={phi:+.2f}"]
    if used_robust:
        note_parts.append(f"robust:{dropped_year}년 침체 trim")
    if n < STABLE_MIN_YEARS:
        note_parts.append(f"{n}년 추정(사이클 영향 가능)")
    else:
        note_parts.append(f"{n}년 추정(안정)")
    if penalty is not None:
        note_parts.append(f"일회성={penalty:.0%}")
        score = base * (1 - 0.5 * penalty)
    else:
        score = base
    return ModuleScore(
        name="M4",
        score=round(score, 1),
        raw=phi,
        note=", ".join(note_parts),
    )
