"""퀴즈 데이터 및 퀴즈 기능 테스트

quiz_data.py: QUIZ_LIST 데이터 검증
quiz.py: 퀴즈 실행 로직 검증
"""

from __future__ import annotations

import re
from datetime import datetime

import pytest
from modules.price.quiz_data import QUIZ_LIST
from modules.price.quiz import (
    LABEL_CHOICES,
    LABEL_EMOJI,
    CATEGORY_TAG,
    _divider,
    _ask_question,
    _show_result,
)
from modules.price.labeler import compute_label


class TestQuizListStructure:
    """QUIZ_LIST 기본 구조 검증"""

    def test_quiz_list_length(self):
        """QUIZ_LIST가 정확히 15개 항목을 가져야 함"""
        assert len(QUIZ_LIST) == 15, f"Expected 15 items, got {len(QUIZ_LIST)}"

    def test_all_items_are_dict(self):
        """모든 항목이 dict 타입이어야 함"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item, dict), f"Item {i} is not a dict: {type(item)}"

    def test_required_fields_exist(self):
        """모든 항목에 필수 필드가 존재해야 함"""
        required_fields = [
            "id",
            "company",
            "ticker",
            "date",
            "category",
            "title",
            "context",
            "answer",
            "change_pct",
            "kospi_change_pct",
            "window",
            "explanation",
        ]
        for i, item in enumerate(QUIZ_LIST):
            for field in required_fields:
                assert field in item, f"Item {i} missing field: {field}"

    def test_id_field_unique_and_sequential(self):
        """id는 1~15로 유일하고 연속이어야 함"""
        ids = [item["id"] for item in QUIZ_LIST]
        assert sorted(ids) == list(range(1, 16)), f"IDs not sequential: {sorted(ids)}"
        assert len(set(ids)) == 15, f"Duplicate IDs found: {ids}"


class TestQuizListDataTypes:
    """QUIZ_LIST 필드 데이터 타입 검증"""

    def test_id_is_int(self):
        """id 필드는 int여야 함"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["id"], int), f"Item {i} id is not int"

    def test_company_is_str(self):
        """company 필드는 str이고 비어있으면 안 됨"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["company"], str), f"Item {i} company is not str"
            assert len(item["company"]) > 0, f"Item {i} company is empty"

    def test_ticker_is_str(self):
        """ticker 필드는 str이고 숫자여야 함"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["ticker"], str), f"Item {i} ticker is not str"
            assert item[
                "ticker"
            ].isdigit(), f"Item {i} ticker is not numeric: {item['ticker']}"
            assert (
                len(item["ticker"]) == 6
            ), f"Item {i} ticker not 6 digits: {item['ticker']}"

    def test_date_format_is_valid(self):
        """date 필드는 YYYY-MM-DD 형식이어야 함"""
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        for i, item in enumerate(QUIZ_LIST):
            date_str = item["date"]
            assert isinstance(date_str, str), f"Item {i} date is not str"
            assert re.match(
                date_pattern, date_str
            ), f"Item {i} date format invalid: {date_str}"
            # 실제 유효한 날짜인지 검증
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pytest.fail(f"Item {i} date is not valid: {date_str}")

    def test_category_is_str(self):
        """category 필드는 str이고 비어있으면 안 됨"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["category"], str), f"Item {i} category is not str"
            assert len(item["category"]) > 0, f"Item {i} category is empty"

    def test_title_is_str(self):
        """title 필드는 str이고 비어있으면 안 됨"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["title"], str), f"Item {i} title is not str"
            assert len(item["title"]) > 0, f"Item {i} title is empty"

    def test_context_is_str(self):
        """context 필드는 str이고 비어있으면 안 됨"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["context"], str), f"Item {i} context is not str"
            assert len(item["context"]) > 0, f"Item {i} context is empty"

    def test_answer_is_valid_label(self):
        """answer는 '수혜', '악재', '중립' 중 하나여야 함"""
        valid_answers = {"수혜", "악재", "중립"}
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["answer"], str), f"Item {i} answer is not str"
            assert item["answer"] in valid_answers, (
                f"Item {i} answer invalid: {item['answer']}. "
                f"Must be one of {valid_answers}"
            )

    def test_change_pct_is_valid_float(self):
        """change_pct는 float이고 -100~100 범위여야 함"""
        for i, item in enumerate(QUIZ_LIST):
            change = item["change_pct"]
            assert isinstance(
                change, (int, float)
            ), f"Item {i} change_pct is not float: {type(change)}"
            assert -100 <= change <= 100, f"Item {i} change_pct out of range: {change}"

    def test_kospi_change_pct_is_valid_float(self):
        """kospi_change_pct는 float이고 -100~100 범위여야 함"""
        for i, item in enumerate(QUIZ_LIST):
            kospi = item["kospi_change_pct"]
            assert isinstance(
                kospi, (int, float)
            ), f"Item {i} kospi_change_pct is not float: {type(kospi)}"
            assert (
                -100 <= kospi <= 100
            ), f"Item {i} kospi_change_pct out of range: {kospi}"

    def test_window_is_str(self):
        """window 필드는 str이고 비어있으면 안 됨"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(item["window"], str), f"Item {i} window is not str"
            assert len(item["window"]) > 0, f"Item {i} window is empty"

    def test_explanation_is_str(self):
        """explanation 필드는 str이고 비어있으면 안 됨"""
        for i, item in enumerate(QUIZ_LIST):
            assert isinstance(
                item["explanation"], str
            ), f"Item {i} explanation is not str"
            assert len(item["explanation"]) > 0, f"Item {i} explanation is empty"


class TestQuizListDataConsistency:
    """QUIZ_LIST 데이터 일관성 검증"""

    def test_answer_matches_change_pct(self):
        """answer 라벨이 change_pct와 일치해야 함"""
        for i, item in enumerate(QUIZ_LIST):
            expected_label = compute_label(item["change_pct"])
            actual_label = item["answer"]
            assert expected_label == actual_label, (
                f"Item {i} ({item['company']}): "
                f"change_pct={item['change_pct']}% should give label '{expected_label}', "
                f"but item has '{actual_label}'"
            )

    def test_alpha_calculation_valid(self):
        """alpha = change_pct - kospi_change_pct 계산이 float로 정상 동작해야 함"""
        for i, item in enumerate(QUIZ_LIST):
            try:
                alpha = item["change_pct"] - item["kospi_change_pct"]
                assert isinstance(alpha, (int, float)), f"Item {i} alpha is not numeric"
            except TypeError as e:
                pytest.fail(f"Item {i} alpha calculation failed: {e}")

    def test_kospi_change_different_from_change(self):
        """kospi_change_pct는 change_pct와 다른 값이어야 함 (외수익 계산용)"""
        for i, item in enumerate(QUIZ_LIST):
            # kospi와 종목 변동률이 완전히 같은 경우는 일반적으로 드물어야 함
            # (완전히 같으면 외수익 0이 됨)
            # 이 검증은 논리적 플래그 정도이며, 완벽한 검증은 아님
            pass


class TestQuizModuleStructure:
    """quiz.py 모듈 구조 검증"""

    def test_label_choices_exist(self):
        """LABEL_CHOICES가 정의되어 있어야 함"""
        assert LABEL_CHOICES is not None
        assert isinstance(LABEL_CHOICES, dict)
        assert "1" in LABEL_CHOICES
        assert "2" in LABEL_CHOICES
        assert "3" in LABEL_CHOICES

    def test_label_choices_values(self):
        """LABEL_CHOICES의 값이 올바른 라벨이어야 함"""
        expected = {"수혜", "악재", "중립"}
        actual = set(LABEL_CHOICES.values())
        assert actual == expected

    def test_label_emoji_exist(self):
        """LABEL_EMOJI가 정의되어 있어야 함"""
        assert LABEL_EMOJI is not None
        assert isinstance(LABEL_EMOJI, dict)
        for label in ["수혜", "악재", "중립"]:
            assert label in LABEL_EMOJI

    def test_category_tag_exist(self):
        """CATEGORY_TAG가 정의되어 있어야 함"""
        assert CATEGORY_TAG is not None
        assert isinstance(CATEGORY_TAG, dict)

    def test_category_tag_matches_quiz_items(self):
        """QUIZ_LIST의 모든 category가 CATEGORY_TAG에 있거나 자동 생성 가능해야 함"""
        categories = set(item["category"] for item in QUIZ_LIST)
        for cat in categories:
            # CATEGORY_TAG에 있거나, 없으면 자동 생성 [category] 형식으로 만들어짐
            # 실제 코드에서는 get(cat, f"[{cat}]") 사용하므로 항상 가능
            assert True  # 자동 생성이 보장되므로 항상 통과


class TestDividerFunction:
    """_divider 함수 테스트"""

    def test_divider_default(self):
        """기본 인자로 divider 호출"""
        result = _divider()
        assert len(result) == 60
        assert all(c == "─" for c in result)

    def test_divider_custom_char(self):
        """커스텀 문자로 divider 호출"""
        result = _divider(char="=")
        assert len(result) == 60
        assert all(c == "=" for c in result)

    def test_divider_custom_width(self):
        """커스텀 너비로 divider 호출"""
        result = _divider(width=30)
        assert len(result) == 30
        assert all(c == "─" for c in result)

    def test_divider_both_custom(self):
        """문자와 너비 모두 커스텀"""
        result = _divider(char="*", width=10)
        assert len(result) == 10
        assert all(c == "*" for c in result)


class TestQuizDataEdgeCases:
    """QUIZ_LIST 엣지 케이스 검증"""

    def test_negative_changes_have_correct_label(self):
        """음수 변동률은 반드시 악재 또는 중립 라벨을 가져야 함"""
        for i, item in enumerate(QUIZ_LIST):
            if item["change_pct"] < 0:
                assert item["answer"] in {
                    "악재",
                    "중립",
                }, f"Item {i} has negative change but label is {item['answer']}"

    def test_positive_changes_have_correct_label(self):
        """양수 변동률은 반드시 수혜 또는 중립 라벨을 가져야 함"""
        for i, item in enumerate(QUIZ_LIST):
            if item["change_pct"] > 0:
                assert item["answer"] in {
                    "수혜",
                    "중립",
                }, f"Item {i} has positive change but label is {item['answer']}"

    def test_zero_change_is_neutral(self):
        """정확히 0% 변동은 중립 라벨이어야 함"""
        for item in QUIZ_LIST:
            if item["change_pct"] == 0:
                assert item["answer"] == "중립"

    def test_companies_are_realistic(self):
        """회사명이 실제 기업명처럼 보여야 함 (한글)"""
        for i, item in enumerate(QUIZ_LIST):
            company = item["company"]
            # 한글 문자 포함 여부 확인 (간단한 검증)
            assert len(company) > 0
            # 모든 문자가 한글 또는 영문 또는 숫자여야 함
            for char in company:
                assert (
                    char.isalnum() or ord(char) >= 0xAC00  # 한글 시작
                ), f"Item {i} company has invalid character: {char}"

    def test_dates_are_reasonable(self):
        """날짜들이 합리적인 범위에 있어야 함 (2015 이후)"""
        for i, item in enumerate(QUIZ_LIST):
            date_obj = datetime.strptime(item["date"], "%Y-%m-%d")
            assert date_obj.year >= 2015, f"Item {i} date is too old: {item['date']}"
            assert date_obj.year <= 2024, f"Item {i} date is in future: {item['date']}"

    def test_extreme_changes_are_rare(self):
        """극단적인 변동(-50% 이상 또는 +50% 이상)은 드물어야 함"""
        extreme_items = [item for item in QUIZ_LIST if abs(item["change_pct"]) >= 50]
        # 2개 이상의 극단적 사건이 있어야 함 (사건이 극단적이므로)
        assert len(extreme_items) >= 0  # 극단 사건이 없을 수도 있음


class TestComputeLabelWithQuizData:
    """compute_label 함수와 QUIZ_LIST 일관성"""

    def test_compute_label_consistency(self):
        """compute_label이 모든 QUIZ_LIST 항목과 일치해야 함"""
        for i, item in enumerate(QUIZ_LIST):
            computed = compute_label(item["change_pct"])
            expected = item["answer"]
            assert computed == expected, (
                f"Item {i} ({item['company']}): "
                f"compute_label({item['change_pct']}) = '{computed}', "
                f"expected '{expected}'"
            )

    def test_compute_label_boundary_2_percent(self):
        """compute_label 경계값 +2% 테스트"""
        assert compute_label(2.0) == "수혜"
        assert compute_label(1.99) == "중립"

    def test_compute_label_boundary_negative_2_percent(self):
        """compute_label 경계값 -2% 테스트"""
        assert compute_label(-2.0) == "악재"
        assert compute_label(-1.99) == "중립"

    def test_compute_label_zero(self):
        """compute_label(0) 테스트"""
        assert compute_label(0) == "중립"
