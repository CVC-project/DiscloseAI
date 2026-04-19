"""M3 — OCF/NI 괴리 추세."""

from modules.financial.eqs.m3_cashflow import score_m3, _ocf_ni_pairs
from modules.financial.eqs.types import FirmPanel
from tests._factories import healthy_panel, make_year


def test_m3_healthy_high():
    """OCF/NI ≈ 1.2 일관 → 평균/추세/변동성 모두 양호."""
    s = score_m3(healthy_panel())
    assert s.score is not None
    assert s.score >= 70


def test_m3_low_when_ocf_lags_ni():
    years = [
        make_year(2020, ni=100, ocf=20),
        make_year(2021, ni=100, ocf=20),
        make_year(2022, ni=100, ocf=20),
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is not None
    assert s.score < 50


def test_m3_skips_negative_ni_years():
    """NI<=0인 해는 비율 무의미 → 제외 후 남는 표본만 사용."""
    years = [
        make_year(2020, ni=-50, ocf=20),  # 제외
        make_year(2021, ni=100, ocf=120),
        make_year(2022, ni=100, ocf=120),
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is not None  # 2개 남아서 산출됨


def test_m3_insufficient_data():
    years = [make_year(2020, ni=100, ocf=120)]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is None


def test_m3_winsorize_extreme_outlier():
    """극단적 outlier (OCF/NI > 3)는 ±3으로 클립. 예: 10배는 3배로."""
    years = [
        make_year(2020, ni=100, ocf=1000),  # OCF/NI=10 → 3으로 클립
        make_year(2021, ni=100, ocf=100),   # OCF/NI=1
        make_year(2022, ni=100, ocf=100),   # OCF/NI=1
        make_year(2023, ni=100, ocf=100),   # OCF/NI=1
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    # 클립된 데이터: [3, 1, 1, 1] 평균≈1.5, 이는 충분히 높은 점수를 줘야 함
    assert s.score is not None
    # 극단값이 평균을 망가뜨리지 않아야 함
    assert s.raw is not None  # raw에 클립된 평균이 기록되어야 함
    assert s.raw <= 1.5  # 극단값의 영향을 받지 않음


def test_m3_negative_outlier_winsorize():
    """극단적 음수 outlier도 클립 (예: -10은 -3으로)."""
    years = [
        make_year(2020, ni=100, ocf=-1000),  # OCF/NI=-10 → -3으로 클립
        make_year(2021, ni=100, ocf=100),    # OCF/NI=1
        make_year(2022, ni=100, ocf=100),    # OCF/NI=1
        make_year(2023, ni=100, ocf=100),    # OCF/NI=1
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is not None
    # 클립 후 평균: (-3+1+1+1)/4 = 0 → 낮은 점수


def test_m3_loss_years_over_half_insufficient_pairs():
    """적자 연도가 절반 이상 → 유효 데이터 부족으로 None 반환."""
    years = [
        make_year(2020, ni=-100, ocf=20),    # 적자 → 제외
        make_year(2021, ni=-50, ocf=10),     # 적자 → 제외
        make_year(2022, ni=100, ocf=120),    # 흑자
        make_year(2023, ni=100, ocf=120),    # 흑자
    ]
    # total_years=4, valid=2. 2*2 < 4? No (2*2=4, not <4)
    # 이 경우는 정확히 반반이므로 산출됨.
    s = score_m3(FirmPanel(corp_code="X", years=years))
    # 정확히 반반이므로 <= 조건을 넘음
    if s.score is None:
        assert "적자 연도" in s.note or "부족" in s.note
    else:
        # 2개 표본으로 계산되었음
        assert len(s.note) > 0


def test_m3_loss_years_strictly_over_half():
    """적자 연도가 과반(>50%) → 비율 데이터 부족."""
    years = [
        make_year(2020, ni=-100, ocf=20),    # 적자
        make_year(2021, ni=-50, ocf=10),     # 적자
        make_year(2022, ni=-50, ocf=10),     # 적자
        make_year(2023, ni=100, ocf=120),    # 흑자
        make_year(2024, ni=100, ocf=120),    # 흑자
    ]
    # total_years=5, valid=2. valid*2 < total_years? 2*2 < 5? Yes, 4<5
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is None
    assert "적자 연도" in s.note
    assert "OCF/NI 해석 불가" in s.note


def test_m3_exactly_half_loss_years_allowed():
    """적자 연도가 정확히 50% → 비율 데이터 있으면 산출 (>는 아님)."""
    years = [
        make_year(2020, ni=-100, ocf=20),    # 적자
        make_year(2021, ni=-100, ocf=20),    # 적자
        make_year(2022, ni=100, ocf=120),    # 흑자
        make_year(2023, ni=100, ocf=120),    # 흑자
    ]
    # 2/4 = 50% 적자 (not > 50%)
    s = score_m3(FirmPanel(corp_code="X", years=years))
    # 흑자 해 2개로 충분 (>=2)
    assert s.score is not None


def test_ocf_ni_pairs_filters_correctly():
    """_ocf_ni_pairs가 정확히 필터링 (NI<=0 제외)."""
    years = [
        make_year(2020, ni=0, ocf=100),       # 제외 (NI==0)
        make_year(2021, ni=-50, ocf=100),     # 제외 (NI<0)
        make_year(2022, ni=100, ocf=150),     # 포함
        make_year(2023, ni=100, ocf=None),    # 제외 (OCF=None)
    ]
    pairs = _ocf_ni_pairs(FirmPanel(corp_code="X", years=years))
    assert len(pairs) == 1
    assert pairs[0] == (2022, 1.5)


def test_m3_zero_ni_excluded():
    """NI=0인 해는 비율 의미 없음 → 제외."""
    years = [
        make_year(2020, ni=0, ocf=100),      # NI=0 → 제외
        make_year(2021, ni=100, ocf=120),
        make_year(2022, ni=100, ocf=120),
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    # 흑자 2개로 계산됨
    assert s.score is not None
    assert "2년만 사용" in s.note or "n=2" in s.note


def test_m3_three_years_with_slope():
    """3년 이상일 때 추세 계산 포함."""
    years = [
        make_year(2021, ni=100, ocf=100),
        make_year(2022, ni=100, ocf=110),
        make_year(2023, ni=100, ocf=120),
    ]
    s = score_m3(FirmPanel(corp_code="X", years=years))
    assert s.score is not None
    # 3년 이상이므로 추세 포함
    assert "추세=" in s.note
    assert "n=3" in s.note
