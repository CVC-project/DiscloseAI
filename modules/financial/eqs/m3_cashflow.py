"""M3 v2 — 부채 건전성 (Debt Health).

"회사 빚이 자기 돈의 몇 배인가? — 같은 업종 평균과 비교해서."

설계: ``modules/financial/EQS_V2_DESIGN.md`` §M3.

산출:
    D/E = 부채총계[t] ÷ 자본총계[t]
    점수 = 선형보간(D/E, 임계값[업종])

업종별 임계값 [T1=우량(100), T2=양호(80), T3=주의(50), T4=위험(0)]:
- 정보통신·소프트웨어 (0.30, 0.60, 1.20, 2.50)
- 제조업(일반)        (0.50, 1.00, 2.00, 4.00)
- 화학·정유          (0.60, 1.20, 2.20, 4.50)
- 유틸리티           (0.80, 1.50, 2.80, 5.00)
- 도소매·서비스      (0.50, 1.00, 2.00, 4.00)
- 건설업             (1.00, 2.00, 3.50, 6.00)
- 운수업             (1.00, 2.00, 3.50, 6.00)
- 금융지주·은행       (8.00, 12.00, 17.00, 25.00)
- 증권               (2.00, 4.00, 6.00, 10.00)
- 생명보험           (7.00, 11.00, 15.00, 22.00)
- 손해보험           (4.00, 7.00, 11.00, 17.00)

예외:
- 자본총계 ≤ 0 (자본잠식): 0점
- 부채/자본 결측: 산출 보류
"""

from __future__ import annotations

from .calibration import CalibrationResult, profile_for_panel, score_against_peers
from .industry_v2 import classify, m3_thresholds
from .types import FirmPanel, ModuleScore


def _piecewise_score(de: float, t: tuple) -> float:
    """업종 임계값 t=(T1,T2,T3,T4)에 따른 선형 보간 점수 (2026-04-27 보정).

    이전 정의는 ``D/E ≤ T1 → 100``으로 KOSPI 우량주 다수가 100점에 몰림(11/48).
    T1을 "양호선=80점"으로 재해석하고 "0점에서 시작 → T1 80점 → T4 0점" 4구간으로
    선형 보간해 변별력 확보.

    구간별:
      0 ≤ D/E ≤ T1            → 100 - 20 × (D/E / T1)              (0=100, T1=80)
      T1 < D/E ≤ T2           → 80  - 20 × ((D/E-T1)/(T2-T1))      (T2=60)
      T2 < D/E ≤ T3           → 60  - 25 × ((D/E-T2)/(T3-T2))      (T3=35)
      T3 < D/E ≤ T4           → 35  - 35 × ((D/E-T3)/(T4-T3))      (T4=0)
      D/E > T4                → 0
    """
    T1, T2, T3, T4 = t
    if de <= 0:
        return 100.0
    if de <= T1:
        return 100.0 - 20.0 * (de / T1)
    if de <= T2:
        return 80.0 - 20.0 * ((de - T1) / (T2 - T1))
    if de <= T3:
        return 60.0 - 25.0 * ((de - T2) / (T3 - T2))
    if de <= T4:
        return 35.0 - 35.0 * ((de - T3) / (T4 - T3))
    return 0.0


def score_m3(panel: FirmPanel, calibration: CalibrationResult | None = None) -> ModuleScore:
    curr = panel.latest()
    if curr is None:
        return ModuleScore(name="M3", score=None, note="최신 연도 데이터 없음")

    if curr.total_liabilities is None or curr.total_equity is None:
        return ModuleScore(name="M3", score=None, note="부채/자본 결측")

    if curr.total_equity <= 0:
        return ModuleScore(
            name="M3",
            score=0.0,
            raw=None,
            note=f"자본잠식(자본총계={curr.total_equity/1e8:.0f}억) — 상장폐지 사유",
        )

    de = curr.total_liabilities / curr.total_equity
    if calibration is not None:
        profile = profile_for_panel(calibration, panel, "m3_debt_to_equity")
        if profile is None:
            return ModuleScore(
                name="M3",
                score=None,
                raw=de,
                note="동종업계 유효 표본 부족 — M3 보류",
            )
        score = score_against_peers(de, profile, higher_is_better=False)
        note = (
            f"부채비율={de*100:.0f}% (동종업계 {profile.group} {profile.sample_size}개사, "
            f"P10/P50/P90={profile.p10*100:.0f}/{profile.p50*100:.0f}/{profile.p90*100:.0f}%)"
        )
    else:
        cls = classify(panel.corp_name)
        thr = m3_thresholds(cls.m3_bucket)
        score = _piecewise_score(de, thr)
        note = (
            f"부채비율={de*100:.0f}% (업종 {cls.m3_bucket}, "
            f"양호선={thr[1]*100:.0f}% / 위험선={thr[3]*100:.0f}%)"
        )
    return ModuleScore(
        name="M3",
        score=round(score, 1),
        raw=de,
        note=note,
    )
