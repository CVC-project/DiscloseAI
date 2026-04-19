"""EQS 종합 점수 _aggregate 가중치 재정규화 검증."""

from modules.financial.eqs.score import _aggregate, DEFAULT_WEIGHTS
from modules.financial.eqs.types import ModuleScore


def test_aggregate_all_valid():
    """모든 모듈 유효 → 기본 가중평균."""
    modules = [
        ModuleScore(name="M1", score=100.0),
        ModuleScore(name="M2", score=50.0),
        ModuleScore(name="M3", score=80.0),
        ModuleScore(name="M4", score=60.0),
        ModuleScore(name="M5", score=70.0),
    ]
    result = _aggregate(modules, DEFAULT_WEIGHTS)
    # (100*0.2 + 50*0.2 + 80*0.2 + 60*0.2 + 70*0.2) / 1.0 = 72.0
    assert result is not None
    assert abs(result - 72.0) < 0.1


def test_aggregate_one_module_none():
    """M3만 None → M3 가중치를 남은 4개에 재배분."""
    modules = [
        ModuleScore(name="M1", score=80.0),
        ModuleScore(name="M2", score=80.0),
        ModuleScore(name="M3", score=None),  # 제외
        ModuleScore(name="M4", score=80.0),
        ModuleScore(name="M5", score=80.0),
    ]
    result = _aggregate(modules, DEFAULT_WEIGHTS)
    # M3 제외 → [M1, M2, M4, M5] 각 0.25 가중치
    # (80*0.25 + 80*0.25 + 80*0.25 + 80*0.25) = 80.0
    assert result is not None
    assert abs(result - 80.0) < 0.1


def test_aggregate_multiple_modules_none():
    """M1, M3, M5 None → M2, M4만 유효 (각 0.5 가중치로 재정규화)."""
    modules = [
        ModuleScore(name="M1", score=None),
        ModuleScore(name="M2", score=60.0),
        ModuleScore(name="M3", score=None),
        ModuleScore(name="M4", score=80.0),
        ModuleScore(name="M5", score=None),
    ]
    result = _aggregate(modules, DEFAULT_WEIGHTS)
    # 유효: M2(60), M4(80) → 기본 가중치 0.2, 0.2 → 재정규화 0.5, 0.5
    # (60*0.5 + 80*0.5) = 70.0
    assert result is not None
    assert abs(result - 70.0) < 0.1


def test_aggregate_all_none():
    """모든 모듈이 None → 결과는 None."""
    modules = [
        ModuleScore(name="M1", score=None),
        ModuleScore(name="M2", score=None),
        ModuleScore(name="M3", score=None),
        ModuleScore(name="M4", score=None),
        ModuleScore(name="M5", score=None),
    ]
    result = _aggregate(modules, DEFAULT_WEIGHTS)
    assert result is None


def test_aggregate_empty_modules():
    """빈 모듈 리스트 → None."""
    result = _aggregate([], DEFAULT_WEIGHTS)
    assert result is None


def test_aggregate_rounding():
    """결과가 0.1 단위로 반올림됨."""
    modules = [
        ModuleScore(name="M1", score=55.55),
        ModuleScore(name="M2", score=55.55),
        ModuleScore(name="M3", score=55.55),
        ModuleScore(name="M4", score=55.55),
        ModuleScore(name="M5", score=55.55),
    ]
    result = _aggregate(modules, DEFAULT_WEIGHTS)
    # 평균 55.55 → 55.6으로 반올림
    assert result is not None
    assert result == 55.5 or result == 55.6  # 반올림 오차 허용
