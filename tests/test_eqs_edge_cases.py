"""EQS 엣지케이스 회귀 테스트 — code-review 지적 #1~#4.

⚠️ v2 redesign(commit 45b180a)에서 v1 API(DEFAULT_WEIGHTS, _redistribute 등)가
제거되어 module-level skip 처리. v2 기준 회귀 테스트는 별도 PR에서 재작성 예정.
"""
import pytest
pytest.skip("v1 EQS API stale — 45b180a v2 redesign 이후", allow_module_level=True)

from modules.financial.eqs.m2_beneish import (
    score_m2,
    m_score,
    BENEISH_US,
    M_THRESHOLD,
)
from modules.financial.eqs.m3_cashflow import score_m3
from modules.financial.eqs.score import compute_eqs, _aggregate, DEFAULT_WEIGHTS
from modules.financial.eqs.types import FirmPanel, ModuleScore
from tests._factories import healthy_panel, make_year


class TestM2BeneishNegativeGrossMargin:
    """리뷰 지적 #1: M2 Beneish — 총이익률 음수 케이스.

    COGS > Revenue인 경우, 총이익률이 음수가 되면서 GMI 계산이 어떻게 되는지.
    현재 코드는 _beneish_indices() 에서 gm_curr, gm_prev를 음수로 계산하고,
    이를 인덱스 계산에 그대로 포함한다. 이 동작을 회귀 테스트로 고정.
    """

    def test_negative_gross_margin_score_is_deterministic(self):
        """총이익률 음수 → M2 점수가 None이 아닌 특정 값으로 계산되고 재현 가능."""
        # 음수 마진 패널 (COGS > Revenue)
        y0 = make_year(
            2023, revenue=1000, cogs=1200, sga=100, depreciation=50, ni=100, ocf=120
        )
        y1 = make_year(
            2024, revenue=1100, cogs=1300, sga=110, depreciation=55, ni=150, ocf=180
        )
        negative_margin = FirmPanel(
            corp_code="X", corp_name="NegativeCo", industry_code="013", years=[y0, y1]
        )

        # 같은 패널로 두 번 점수 계산하면 동일
        score1 = score_m2(negative_margin)
        score2 = score_m2(negative_margin)

        assert score1.score is not None
        assert score2.score is not None
        assert score1.score == score2.score
        # 점수가 0~100 범위 유지
        assert 0 <= score1.score <= 100

    def test_negative_gross_margin_raw_score_captured(self):
        """음수 마진의 M-score raw 값도 저장됨."""
        y0 = make_year(
            2023, revenue=1000, cogs=1500, ni=100, ocf=120, sga=100, depreciation=50
        )
        y1 = make_year(
            2024, revenue=1200, cogs=1800, ni=150, ocf=180, sga=120, depreciation=60
        )
        panel = FirmPanel(
            corp_code="X", corp_name="NegativeCo", industry_code="013", years=[y0, y1]
        )
        result = score_m2(panel)

        # raw 값이 M-score (음수일 가능성)
        assert result.raw is not None
        # 점수는 여전히 0~100
        assert result.score is not None
        assert 0 <= result.score <= 100

    def test_negative_gross_margin_indices_calculated(self):
        """음수 마진이 포함된 패널도 8개 지수가 모두 계산됨."""
        y0 = make_year(
            2023, revenue=1000, cogs=1100, ni=100, ocf=120, sga=100, depreciation=50
        )
        y1 = make_year(
            2024, revenue=1200, cogs=1400, ni=150, ocf=180, sga=120, depreciation=60
        )
        panel = FirmPanel(
            corp_code="X", corp_name="NegativeCo", industry_code="013", years=[y0, y1]
        )

        # M-score 계산 직접 호출
        m_raw = m_score(y0, y1, BENEISH_US)
        result = score_m2(panel)

        # raw와 점수 모두 None이 아님
        assert m_raw is not None
        assert result.score is not None
        assert result.raw is not None


class TestM3OCFNegativeNIPositive:
    """리뷰 지적 #2: M3 — OCF<0 이지만 NI>0 인 해의 추세 영향.

    _ocf_ni_pairs()는 NI<=0인 해를 제외하고, OCF<0인 해는 통과시킨다.
    그 결과 음수 비율(OCF/NI < 0)이 평균과 추세에 반영되는 동작 확인.
    """

    def test_ocf_negative_ni_positive_included_in_ratio(self):
        """OCF<0, NI>0 → 비율 = OCF/NI < 0 → 평균을 낮춤."""
        # 3년:
        # Y1: NI=100, OCF=-50 → ratio=-0.5
        # Y2: NI=100, OCF=100 → ratio=1.0
        # Y3: NI=100, OCF=100 → ratio=1.0
        # 평균 = (-0.5 + 1.0 + 1.0) / 3 ≈ 0.5
        years = [
            make_year(2020, ni=100, ocf=-50),  # OCF 음수
            make_year(2021, ni=100, ocf=100),
            make_year(2022, ni=100, ocf=100),
        ]
        panel = FirmPanel(corp_code="X", years=years)
        result = score_m3(panel)

        # 점수가 계산됨 (3년이므로 추세도 포함)
        assert result.score is not None
        # OCF<0 해가 섞여있으므로 평균이 1.0 미만 → 점수가 낮음
        assert result.score < 100
        # raw에 평균 비율 저장
        assert result.raw is not None
        assert result.raw < 1.0  # 음수 비율이 평균을 낮춤

    def test_ocf_negative_not_excluded_from_calculation(self):
        """OCF<0인 해가 _ocf_ni_pairs에서 제외되지 않음 (NI>0이면)."""
        # 정상: 모두 OCF>0, NI>0
        healthy = healthy_panel(n_years=3)
        score_healthy = score_m3(healthy)
        assert score_healthy.score is not None

        # OCF 음수 포함
        years_with_neg_ocf = [
            make_year(2020, ni=100, ocf=-30),  # OCF 음수도 포함됨
            make_year(2021, ni=110, ocf=110),
            make_year(2022, ni=120, ocf=120),
        ]
        panel = FirmPanel(corp_code="X", years=years_with_neg_ocf)
        score_with_neg_ocf = score_m3(panel)

        # 모두 점수 계산되지만, 음수 OCF가 평균을 낮춤
        assert score_healthy.score is not None
        assert score_with_neg_ocf.score is not None
        # OCF 음수가 포함되면 점수가 더 낮음
        assert score_with_neg_ocf.score < score_healthy.score

    def test_ocf_negative_all_years_accepted_by_filter(self):
        """3년 모두 OCF<0이지만 NI>0 → 모두 포함되어 음수 비율 연속."""
        years = [
            make_year(2020, ni=100, ocf=-50),
            make_year(2021, ni=110, ocf=-55),
            make_year(2022, ni=120, ocf=-60),
        ]
        panel = FirmPanel(corp_code="X", years=years)
        result = score_m3(panel)

        # 3년이므로 점수 계산됨
        assert result.score is not None
        # 모두 음수 비율 → 평균도 음수
        assert result.raw is not None
        assert result.raw < 0


class TestAggregatePartialWeights:
    """리뷰 지적 #3: score._aggregate — 외부 weights 키 누락 시 silent fallback.

    사용자가 weights={"M1": 0.5, "M2": 0.5} 처럼 일부 모듈만 넘기면,
    M3~M5가 weights 딕셔너리에 없어도 _aggregate는 조용히 제외한다.
    이 동작을 회귀 테스트로 고정.
    """

    def test_aggregate_missing_keys_silently_excluded(self):
        """weights 딕셔너리에 없는 모듈은 가중평균에서 제외됨."""
        modules = [
            ModuleScore(name="M1", score=100.0),
            ModuleScore(name="M2", score=50.0),
            ModuleScore(name="M3", score=80.0),
            ModuleScore(name="M4", score=60.0),
            ModuleScore(name="M5", score=70.0),
        ]
        # M1, M2만 가중치 지정
        partial_weights = {"M1": 0.5, "M2": 0.5}
        result = _aggregate(modules, partial_weights)

        # M3, M4, M5는 키가 없으므로 제외
        # (M1=100*0.5 + M2=50*0.5) / (0.5+0.5) = 75.0
        assert result is not None
        assert abs(result - 75.0) < 0.1

    def test_aggregate_missing_key_no_error_raised(self):
        """weights 딕셔너리에 모듈 키가 없어도 에러 없음 (조용한 제외)."""
        modules = [
            ModuleScore(name="M1", score=100.0),
            ModuleScore(name="M2", score=50.0),
        ]
        partial_weights = {"M1": 0.5}  # M2 키 없음

        # 예외 발생하지 않음
        result = _aggregate(modules, partial_weights)
        # M2는 제외되고 M1만 사용
        assert result is not None
        assert abs(result - 100.0) < 0.1

    def test_compute_eqs_with_partial_weights(self):
        """compute_eqs에 일부 가중치만 전달 → 해당 모듈만 계산됨."""
        panel = healthy_panel(n_years=3)
        # M1, M2만 가중치
        custom_weights = {"M1": 0.6, "M2": 0.4}
        result = compute_eqs(panel, weights=custom_weights)

        # 총점이 계산됨 (M1, M2만)
        assert result.total is not None
        # M3~M5가 키 없으므로 제외되었을 것
        # 모듈 점수들은 여전히 모두 계산되지만, 종합 가중평균은 M1, M2만 사용
        assert len(result.modules) >= 2  # 최소 M1, M2는 있음


class TestAggregateImbalancedWeights:
    """리뷰 지적 #4: score._aggregate — 가중치 합 ≠ 1 인 weights 통과 시 정규화.

    가중치 합이 0.5라면 _aggregate는 내부에서 재정규화하여
    여전히 가중평균(합=1 기준)을 계산한다. 이 동작을 명시하는 테스트.
    """

    def test_aggregate_sum_half_is_normalized(self):
        """가중치 합=0.5 → 내부에서 재정규화하여 가중평균 계산."""
        modules = [
            ModuleScore(name="M1", score=100.0),
            ModuleScore(name="M2", score=50.0),
            ModuleScore(name="M3", score=80.0),
            ModuleScore(name="M4", score=60.0),
            ModuleScore(name="M5", score=70.0),
        ]
        # 합이 0.5
        half_weights = {
            "M1": 0.1,
            "M2": 0.1,
            "M3": 0.1,
            "M4": 0.1,
            "M5": 0.1,
        }
        result = _aggregate(modules, half_weights)

        # 가중치가 정규화되지만, 같은 비율이므로 평균과 동일
        # (100*0.1 + 50*0.1 + 80*0.1 + 60*0.1 + 70*0.1) / 0.5
        # = (100 + 50 + 80 + 60 + 70) / 5 = 72.0
        assert result is not None
        assert abs(result - 72.0) < 0.1

    def test_aggregate_unequal_weights_normalized(self):
        """가중치 합=0.3, 비율=1:2:3 → 정규화 후 가중평균."""
        modules = [
            ModuleScore(name="M1", score=100.0),
            ModuleScore(name="M2", score=50.0),
            ModuleScore(name="M3", score=75.0),
        ]
        # 합=0.3, 비율=1:2:3
        imbalanced = {
            "M1": 0.05,
            "M2": 0.1,
            "M3": 0.15,
        }
        result = _aggregate(modules, imbalanced)

        # 정규화: M1=0.05/0.3, M2=0.1/0.3, M3=0.15/0.3
        # = 1/6, 2/6, 3/6
        # (100*(1/6) + 50*(2/6) + 75*(3/6)) = (100 + 100 + 225) / 6 ≈ 70.8
        assert result is not None
        assert abs(result - 70.833) < 0.1

    def test_aggregate_zero_sum_weights(self):
        """가중치 합=0 → None 반환."""
        modules = [
            ModuleScore(name="M1", score=100.0),
            ModuleScore(name="M2", score=50.0),
        ]
        zero_weights = {"M1": 0.0, "M2": 0.0}
        result = _aggregate(modules, zero_weights)

        # 유효한 가중치가 없으므로 None
        assert result is None

    def test_compute_eqs_imbalanced_weights(self):
        """compute_eqs에 합≠1 가중치 전달 → 내부 재정규화."""
        panel = healthy_panel(n_years=3)
        # 합 = 0.5
        imbalanced_weights = {
            "M1": 0.1,
            "M2": 0.1,
            "M3": 0.1,
            "M4": 0.1,
            "M5": 0.0,  # 명시적 0
        }
        result = compute_eqs(panel, weights=imbalanced_weights)

        # 점수 계산됨 (내부 정규화)
        assert result.total is not None
        # 합=0.5인 경우에도 정규화되므로 정상 범위
        assert 0 <= result.total <= 100
