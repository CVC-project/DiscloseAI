"""M4 — 이익안정 (이익 지속성).

"올해 이익이 내년에도 비슷하게 유지될 가능성이 있는가?"를 측정한다.
점수가 높을수록 이익이 꾸준하고 예측 가능하다는 뜻이다.

점수 도출 경로 (2가지):

1. ``score_m4(panel)`` — 정상 경로 (5년 이상 데이터):
   AR(1) 회귀계수 φ로 지속성 측정: E_t = α + φ·E_(t-1) + ε
   - φ=1 → 완전 지속(100점), φ=0 → 무관(50점), φ=-1 → 반전(0점)
   - 일회성 비중 페널티: nonrecurring/|NI|가 클수록 감점.
   - robust trim (7년+): 사이클 침체 1점 제거 후 재추정.
   - 10년+ 이면 "안정 추정", 5~9년이면 "사이클 영향 가능" 표기.

2. ``_score_m4_short_history(panel)`` — 3~4년 단축 fallback:
   AR(1) 회귀가 통계적으로 불안정한 짧은 이력에서 대안 지표 사용.
   ROA 변동계수(CV, 60%) + 방향 일관성(40%).
   (Dichev & Tang, 2009 — 이익 변동성 = 지속성의 역수)
   대상: 금융지주사(KB금융, 신한지주 등), SK스퀘어, SK이노베이션 등.
   2년 이하는 여전히 None (최소 3년 필요).
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


def _score_m4_short_history(
    panel: FirmPanel, series: List[Tuple[int, float]]
) -> ModuleScore:
    """3~4년 데이터용 지속성 프록시 (Dichev & Tang, 2009).

    AR(1) 회귀가 통계적으로 불안정한 짧은 이력에서 ROA 변동계수(CV)와
    방향 일관성으로 지속성을 근사.
    """
    from statistics import mean as _mean, pstdev as _pstdev

    n = len(series)
    roas = [s[1] for s in series]
    avg = _mean(roas)

    # 1) ROA CV (60%) — 낮을수록 안정 (= 지속적)
    if avg != 0:
        cv = _pstdev(roas) / abs(avg)
        cv_score = max(0.0, 100 * (1 - min(1.0, cv)))
    else:
        cv = float("inf")
        cv_score = 0.0

    # 2) 방향 일관성 (40%) — 같은 방향으로 변할수록 예측 가능
    if n >= 3:
        changes = [1 if roas[i] >= roas[i - 1] else -1 for i in range(1, n)]
        same_dir = sum(
            1 for i in range(1, len(changes)) if changes[i] == changes[i - 1]
        )
        dir_score = (same_dir / max(1, len(changes) - 1)) * 100
    else:
        dir_score = 50.0

    score = round(cv_score * 0.6 + dir_score * 0.4, 1)
    return ModuleScore(
        name="M4",
        score=score,
        raw=cv if cv != float("inf") else None,
        note=f"ROA CV={cv:.2f}, 방향일치={dir_score:.0f}% — {n}년 단축 fallback",
    )


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
        if n >= 3:
            return _score_m4_short_history(panel, series)
        return ModuleScore(
            name="M4",
            score=None,
            note=f"ROA 시계열 {n}년 — 최소 3년 필요",
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
