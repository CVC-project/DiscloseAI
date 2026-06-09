"""Phase H 가격 시나리오 데이터 검증 테스트.

price_scenarios.json의 데이터 무결성을 검증합니다:
  1. 12개 시나리오 모두 필수 필드 보유
  2. id 2·11의 dart_url이 'dsab007/search.ax' 패턴 (새 DART URL 형식) 포함
  3. quiz_data.QUIZ_LIST와 price_scenarios.json의 dart_url 매칭 (extract_data.py 산출물 검증)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PRICE_SCENARIOS_JSON = ROOT / "integration" / "data" / "price_scenarios.json"


# --------------------------------------------------------------------------- #
#  fixture: price_scenarios.json 로드
# --------------------------------------------------------------------------- #
@pytest.fixture
def price_scenarios_data():
    """price_scenarios.json 파일 로드."""
    assert PRICE_SCENARIOS_JSON.exists(), f"price_scenarios.json 파일 없음: {PRICE_SCENARIOS_JSON}"
    with open(PRICE_SCENARIOS_JSON, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def quiz_list():
    """quiz_data.QUIZ_LIST 로드."""
    from modules.price.quiz_data import QUIZ_LIST
    return QUIZ_LIST


# --------------------------------------------------------------------------- #
#  테스트 1: 12개 시나리오 기본 구조 검증
# --------------------------------------------------------------------------- #
def test_price_scenarios_count(price_scenarios_data):
    """정확히 12개의 시나리오가 있는지 검증."""
    scenarios = price_scenarios_data.get("data", [])
    assert len(scenarios) == 12, f"시나리오 개수 불일치: {len(scenarios)} != 12"


def test_price_scenarios_required_fields(price_scenarios_data):
    """모든 시나리오가 필수 필드를 보유하는지 검증."""
    required_fields = {"id", "company", "ticker", "date", "title", "change_pct", "kospi_change_pct", "window"}
    scenarios = price_scenarios_data.get("data", [])

    for i, scenario in enumerate(scenarios):
        missing = required_fields - set(scenario.keys())
        assert not missing, (
            f"시나리오 {i} (id={scenario.get('id')})에서 필드 누락: {missing}"
        )


def test_price_scenarios_all_fields_not_none(price_scenarios_data):
    """모든 필수 필드가 None이 아닌지 검증."""
    required_fields = {"id", "company", "ticker", "date", "title", "change_pct", "kospi_change_pct", "window"}
    scenarios = price_scenarios_data.get("data", [])

    for i, scenario in enumerate(scenarios):
        for field in required_fields:
            assert scenario.get(field) is not None, (
                f"시나리오 {i} (id={scenario.get('id')})의 필드 '{field}'가 None"
            )


# --------------------------------------------------------------------------- #
#  테스트 2: id 2·11의 dart_url이 새로운 패턴 (dsab007/search.ax) 포함
# --------------------------------------------------------------------------- #
def test_id_2_dart_url_format(price_scenarios_data):
    """id=2의 dart_url이 'dsab007/search.ax' 패턴 포함하는지 검증."""
    scenarios = price_scenarios_data.get("data", [])
    scenario_id_2 = next((s for s in scenarios if s.get("id") == 2), None)

    assert scenario_id_2 is not None, "id=2인 시나리오를 찾을 수 없음"
    dart_url = scenario_id_2.get("dart_url", "")
    assert "dsab007/search.ax" in dart_url, (
        f"id=2의 dart_url에 'dsab007/search.ax' 패턴 없음: {dart_url}"
    )


def test_id_11_dart_url_format(price_scenarios_data):
    """id=11의 dart_url이 'dsab007/search.ax' 패턴 포함하는지 검증."""
    scenarios = price_scenarios_data.get("data", [])
    scenario_id_11 = next((s for s in scenarios if s.get("id") == 11), None)

    assert scenario_id_11 is not None, "id=11인 시나리오를 찾을 수 없음"
    dart_url = scenario_id_11.get("dart_url", "")
    assert "dsab007/search.ax" in dart_url, (
        f"id=11의 dart_url에 'dsab007/search.ax' 패턴 없음: {dart_url}"
    )


# --------------------------------------------------------------------------- #
#  테스트 3: quiz_data.QUIZ_LIST와의 dart_url 일치성 (extract_data.py 검증)
# --------------------------------------------------------------------------- #
def test_price_scenarios_dart_url_matches_quiz_list(price_scenarios_data, quiz_list):
    """price_scenarios.json의 dart_url이 quiz_data.QUIZ_LIST와 일치하는지 검증.

    extract_data.py가 quiz_data.py에서 올바르게 데이터를 추출했는지 확인합니다.
    """
    scenarios = price_scenarios_data.get("data", [])

    # quiz_list를 id 기준으로 맵핑
    quiz_map = {q.get("id"): q for q in quiz_list}

    for scenario in scenarios:
        scenario_id = scenario.get("id")
        quiz_item = quiz_map.get(scenario_id)

        # QUIZ_LIST에 해당 id가 없으면 스킵 (price_scenarios.json이 더 적을 수 있음)
        if quiz_item is None:
            continue

        # dart_url 일치 검증
        expected_url = quiz_item.get("dart_url")
        actual_url = scenario.get("dart_url")

        assert actual_url == expected_url, (
            f"id={scenario_id}의 dart_url 불일치:\n"
            f"  예상: {expected_url}\n"
            f"  실제: {actual_url}"
        )


def test_price_scenarios_all_required_quiz_items_present(price_scenarios_data, quiz_list):
    """price_scenarios.json에 모든 필수 quiz_list 항목이 있는지 검증.

    id 1-15 범위의 모든 항목이 매칭되어야 합니다 (gap이 있을 수 있음).
    """
    scenarios = price_scenarios_data.get("data", [])
    scenario_ids = {s.get("id") for s in scenarios}
    quiz_ids = {q.get("id") for q in quiz_list}

    # price_scenarios.json의 모든 id가 QUIZ_LIST에 있어야 함
    missing_in_quiz = scenario_ids - quiz_ids
    assert not missing_in_quiz, (
        f"price_scenarios.json의 id가 QUIZ_LIST에 없음: {missing_in_quiz}"
    )


# --------------------------------------------------------------------------- #
#  테스트 4: 엣지 케이스 검증
# --------------------------------------------------------------------------- #
def test_price_scenarios_ticker_format(price_scenarios_data):
    """모든 시나리오의 ticker가 6자리 숫자 형식인지 검증."""
    scenarios = price_scenarios_data.get("data", [])

    for scenario in scenarios:
        ticker = scenario.get("ticker", "")
        assert isinstance(ticker, str) and len(ticker) == 6, (
            f"id={scenario.get('id')}: ticker 형식 오류: {ticker}"
        )
        assert ticker.isdigit(), (
            f"id={scenario.get('id')}: ticker가 숫자가 아님: {ticker}"
        )


def test_price_scenarios_date_format(price_scenarios_data):
    """모든 시나리오의 date가 YYYY-MM-DD 형식인지 검증."""
    scenarios = price_scenarios_data.get("data", [])

    for scenario in scenarios:
        date_str = scenario.get("date", "")
        assert isinstance(date_str, str), (
            f"id={scenario.get('id')}: date가 문자열이 아님"
        )
        try:
            # YYYY-MM-DD 형식 검증
            year, month, day = date_str.split("-")
            assert len(year) == 4 and len(month) == 2 and len(day) == 2, (
                f"id={scenario.get('id')}: 날짜 부분 길이 오류"
            )
            int(year), int(month), int(day)  # 숫자 검증
        except (ValueError, AssertionError) as e:
            pytest.fail(f"id={scenario.get('id')}: date 형식 오류: {date_str} ({e})")


def test_price_scenarios_change_pct_numeric(price_scenarios_data):
    """모든 시나리오의 change_pct·kospi_change_pct가 숫자인지 검증."""
    scenarios = price_scenarios_data.get("data", [])

    for scenario in scenarios:
        for field in ["change_pct", "kospi_change_pct"]:
            value = scenario.get(field)
            assert isinstance(value, (int, float)), (
                f"id={scenario.get('id')}: {field}이 숫자가 아님: {value}"
            )


# --------------------------------------------------------------------------- #
#  테스트 5: meta 필드 검증
# --------------------------------------------------------------------------- #
def test_price_scenarios_meta_structure(price_scenarios_data):
    """price_scenarios.json의 meta 필드가 올바른 구조인지 검증."""
    meta = price_scenarios_data.get("meta", {})

    assert isinstance(meta, dict), "meta가 dict가 아님"
    assert "generated_at" in meta, "meta에 generated_at 필드 없음"
    assert "coverage" in meta, "meta에 coverage 필드 없음"

    coverage = meta.get("coverage", {})
    assert coverage.get("price_scenarios") == 12, (
        f"meta.coverage.price_scenarios가 12가 아님: {coverage.get('price_scenarios')}"
    )


# --------------------------------------------------------------------------- #
#  테스트 6: 회귀 테스트 - 데이터 일관성
# --------------------------------------------------------------------------- #
def test_price_scenarios_data_consistency(price_scenarios_data):
    """시나리오 간 중복이 없고 id가 고유한지 검증."""
    scenarios = price_scenarios_data.get("data", [])

    ids = [s.get("id") for s in scenarios]
    assert len(ids) == len(set(ids)), (
        f"시나리오 id 중복 발견: {ids}"
    )
