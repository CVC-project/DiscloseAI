"""M4 — 이익 지속성 (AR(1) + 일회성)."""

from modules.financial.eqs.m4_persistence import score_m4
from modules.financial.eqs.types import FirmPanel
from tests._factories import make_year


def _panel_persistent_roa():
    """ROA가 단조 증가하는 trending → AR(1) φ ≈ 1."""
    nis = [100, 101, 102, 103, 104, 105]
    years = [make_year(2018 + i, ni=nis[i], ta=5000) for i in range(len(nis))]
    return FirmPanel(corp_code="X", years=years)


def _panel_volatile_roa():
    """ROA가 +/-로 튀는 패턴 → φ 음수 → 낮은 점수."""
    pattern = [100, -100, 100, -100, 100, -100]
    years = [make_year(2018 + i, ni=ni, ta=5000) for i, ni in enumerate(pattern)]
    return FirmPanel(corp_code="X", years=years)


def test_m4_persistent_high():
    s = score_m4(_panel_persistent_roa())
    assert s.score is not None
    assert s.score >= 70


def test_m4_volatile_low():
    s = score_m4(_panel_volatile_roa())
    assert s.score is not None
    assert s.score < 50


def test_m4_nonrecurring_penalty():
    """동일 AR(1)이라도 일회성 비중이 크면 점수가 낮아져야."""
    nis = [100, 101, 102, 103, 104, 105]

    def _build(with_nonrec: bool) -> FirmPanel:
        ys = [make_year(2018 + i, ni=nis[i], ta=5000) for i in range(len(nis))]
        if with_nonrec:
            ys[-1].nonrecurring_income = 80  # 약 80% 일회성
        return FirmPanel(corp_code="X", years=ys)

    s_with = score_m4(_build(True)).score
    s_without = score_m4(_build(False)).score
    assert s_with is not None and s_without is not None
    assert s_with < s_without


def test_m4_insufficient_panel():
    years = [make_year(2023), make_year(2024)]
    s = score_m4(FirmPanel(corp_code="X", years=years))
    assert s.score is None


def test_m4_short_history_fallback():
    """3~4년 패널은 AR(1) 대신 ROA CV+방향 일관성 fallback."""
    for n in (3, 4):
        years = [make_year(2020 + i, ni=100 + i, ta=5000) for i in range(n)]
        s = score_m4(FirmPanel(corp_code="X", years=years))
        assert s.score is not None, f"{n}년 데이터인데 fallback 실패"
        assert "fallback" in s.note


def test_m4_requires_3_years_minimum():
    """2년 이하는 fallback도 불가 → None."""
    for n in (1, 2):
        years = [make_year(2020 + i, ni=100 + i, ta=5000) for i in range(n)]
        s = score_m4(FirmPanel(corp_code="X", years=years))
        assert s.score is None


def test_m4_robust_trims_cyclical_outlier():
    """10년 안정 + 1년 사이클 침체 → robust=True가 robust=False보다 점수 높아야."""
    # 9년은 ROA가 상승 트렌드, 1년만 폭락(사이클 침체)
    nis = [100, 102, 104, 106, 108, 110, 30, 110, 112, 114]  # idx=6에 침체
    years = [make_year(2015 + i, ni=nis[i], ta=5000) for i in range(len(nis))]
    panel = FirmPanel(corp_code="X", years=years)
    s_robust = score_m4(panel, robust=True).score
    s_naive = score_m4(panel, robust=False).score
    assert s_robust is not None and s_naive is not None
    assert s_robust > s_naive


def test_m4_robust_note_indicates_trimmed_year():
    nis = [100, 102, 104, 106, 108, 110, 30, 110, 112, 114]
    years = [make_year(2015 + i, ni=nis[i], ta=5000) for i in range(len(nis))]
    panel = FirmPanel(corp_code="X", years=years)
    s = score_m4(panel, robust=True)
    assert "robust" in s.note
    assert "trim" in s.note


def test_m4_short_window_skips_robust_and_warns():
    """5년만 있으면 robust 미적용, note에 사이클 영향 경고."""
    nis = [100, 101, 102, 103, 104]
    years = [make_year(2020 + i, ni=nis[i], ta=5000) for i in range(len(nis))]
    panel = FirmPanel(corp_code="X", years=years)
    s = score_m4(panel, robust=True)
    assert "robust" not in s.note  # 7년 미만이라 미적용
    assert "사이클 영향 가능" in s.note


def test_m4_long_window_marked_stable():
    nis = list(range(100, 110))  # 10개
    years = [make_year(2015 + i, ni=nis[i], ta=5000) for i in range(len(nis))]
    panel = FirmPanel(corp_code="X", years=years)
    s = score_m4(panel)
    assert "안정" in s.note


def test_m4_phi_zero_maps_to_middle_not_zero():
    """_phi_to_score: 기존 하드 컷오프(φ=0 → 0점) 대신 중간값(50점) 부여.

    5년 단기 AR(1) 추정 노이즈가 φ를 0 부근으로 흔드는 사이클 산업에서
    즉시 0점 처리되던 문제를 완화. 경미한 음수 φ도 낮지만 0은 아닌 점수로.
    """
    from modules.financial.eqs.m4_persistence import _phi_to_score

    # φ = 1: 완전 지속 → 100
    assert _phi_to_score(1.0) == 100.0
    # φ = 0: 무관 → 50 (기존 0)
    assert _phi_to_score(0.0) == 50.0
    # φ = -0.5: 약한 반전 → 25 (기존 0)
    assert _phi_to_score(-0.5) == 25.0
    # φ = -1: 완전 반전 → 0
    assert _phi_to_score(-1.0) == 0.0
    # φ = -1.5: 더 나쁨 → 0
    assert _phi_to_score(-1.5) == 0.0
    # φ = 0.5: 중간 지속 → 75
    assert _phi_to_score(0.5) == 75.0


def test_m4_phi_exploding_range_mapped_correctly():
    """폭주 구간 [1, 2]는 100→0 선형 감소. φ=1.5 → 50점 (regression guard).

    초기 구현에서 조건 순서 버그로 φ>1.0 케이스가 도달 불가했던 dead code를
    수정한 이후 추가. 폭주 과열 기업이 만점 받지 않도록 검증.
    """
    from modules.financial.eqs.m4_persistence import _phi_to_score

    assert _phi_to_score(1.0) == 100.0  # 경계: 이상적 지속
    assert _phi_to_score(1.5) == 50.0  # 폭주 중간
    assert _phi_to_score(2.0) == 0.0  # 폭주 경계
    assert _phi_to_score(2.5) == 0.0  # 발산
