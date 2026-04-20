"""
테스트: modules/price/quiz_data.py

QUIZ_LIST 데이터 무결성 검증
- 항목 개수
- 필수 키 존재
- 데이터 타입 및 범위
- 논리적 일관성 (answer와 change_pct 관계)
"""

import pytest
from modules.price.quiz_data import QUIZ_LIST


class TestQuizListBasics:
    """QUIZ_LIST 기본 속성 검증"""

    def test_quiz_list_has_15_items(self):
        """QUIZ_LIST가 정확히 15개 항목을 포함한다"""
        assert len(QUIZ_LIST) == 15, f"Expected 15 quiz items, got {len(QUIZ_LIST)}"

    def test_all_items_are_dict(self):
        """모든 항목이 딕셔너리 타입이다"""
        for idx, item in enumerate(QUIZ_LIST):
            assert isinstance(item, dict), f"Item {idx} is not a dict: {type(item)}"


class TestRequiredKeys:
    """필수 키 검증"""

    REQUIRED_KEYS = {
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
    }

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_all_required_keys_present(self, quiz):
        """모든 항목이 필수 키를 모두 포함한다"""
        missing_keys = self.REQUIRED_KEYS - set(quiz.keys())
        assert not missing_keys, f"Missing keys in quiz {quiz.get('id')}: {missing_keys}"


class TestDataTypes:
    """데이터 타입 검증"""

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_id_is_int(self, quiz):
        """id는 정수형이다"""
        assert isinstance(quiz["id"], int), f"id is not int: {type(quiz['id'])}"

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_company_is_string(self, quiz):
        """company는 문자열이다"""
        assert isinstance(quiz["company"], str), f"company is not str: {type(quiz['company'])}"

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_ticker_is_string(self, quiz):
        """ticker는 문자열이다"""
        assert isinstance(quiz["ticker"], str), f"ticker is not str: {type(quiz['ticker'])}"

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_date_is_string(self, quiz):
        """date는 문자열이다"""
        assert isinstance(quiz["date"], str), f"date is not str: {type(quiz['date'])}"

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_change_pct_is_numeric(self, quiz):
        """change_pct는 숫자형(int 또는 float)이다"""
        assert isinstance(quiz["change_pct"], (int, float)), \
            f"change_pct is not numeric: {type(quiz['change_pct'])}"

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_kospi_change_pct_is_numeric(self, quiz):
        """kospi_change_pct는 숫자형이다"""
        assert isinstance(quiz["kospi_change_pct"], (int, float)), \
            f"kospi_change_pct is not numeric: {type(quiz['kospi_change_pct'])}"


class TestAnswerValidation:
    """answer 유효성 검증"""

    VALID_ANSWERS = {"수혜", "악재", "중립"}

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_answer_is_valid_category(self, quiz):
        """answer는 '수혜', '악재', '중립' 중 하나이다"""
        assert quiz["answer"] in self.VALID_ANSWERS, \
            f"Invalid answer in quiz {quiz['id']}: '{quiz['answer']}'"


class TestAnswerConsistency:
    """answer와 change_pct의 일관성 검증"""

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_answer_and_change_pct_consistency(self, quiz):
        """answer 방향이 change_pct와 일치한다

        - 수혜: change_pct >= 2.0
        - 악재: change_pct <= -2.0
        - 중립: -2.0 < change_pct < 2.0
        """
        answer = quiz["answer"]
        change = quiz["change_pct"]

        if answer == "수혜":
            assert change >= 2.0, \
                f"Quiz {quiz['id']}: answer='수혜' but change_pct={change} < 2.0"
        elif answer == "악재":
            assert change <= -2.0, \
                f"Quiz {quiz['id']}: answer='악재' but change_pct={change} > -2.0"
        elif answer == "중립":
            assert -2.0 < change < 2.0, \
                f"Quiz {quiz['id']}: answer='중립' but change_pct={change} not in (-2.0, 2.0)"


class TestTickerFormat:
    """ticker 형식 검증"""

    @pytest.mark.parametrize("quiz", QUIZ_LIST, ids=lambda q: f"id={q['id']}")
    def test_ticker_is_6_digit_number(self, quiz):
        """ticker는 6자리 숫자이다"""
        ticker = quiz["ticker"]
        assert len(ticker) == 6, \
            f"Quiz {quiz['id']}: ticker '{ticker}' is not 6 chars"
        assert ticker.isdigit(), \
            f"Quiz {quiz['id']}: ticker '{ticker}' is not all digits"


class TestIdUniqueness:
    """id 유일성 검증"""

    def test_all_ids_unique(self):
        """모든 id는 중복 없이 존재한다"""
        ids = [q["id"] for q in QUIZ_LIST]
        unique_ids = set(ids)
        assert len(ids) == len(unique_ids), \
            f"Duplicate IDs found: {[id for id in ids if ids.count(id) > 1]}"

    def test_ids_are_consecutive_1_to_15(self):
        """id는 1부터 15까지 연속적으로 존재한다"""
        ids = sorted([q["id"] for q in QUIZ_LIST])
        expected_ids = list(range(1, 16))
        assert ids == expected_ids, \
            f"IDs are not 1-15: {ids}"


class TestEdgeCases:
    """엣지 케이스 검증"""

    def test_no_empty_strings(self):
        """필수 문자열 필드가 비어있지 않다"""
        string_fields = ["company", "ticker", "date", "category", "title", "context", "answer", "window", "explanation"]
        for idx, quiz in enumerate(QUIZ_LIST):
            for field in string_fields:
                assert quiz[field].strip(), \
                    f"Quiz {quiz['id']}: '{field}' is empty or whitespace"

    def test_date_format(self):
        """date는 YYYY-MM-DD 형식이다"""
        import re
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        for quiz in QUIZ_LIST:
            assert re.match(date_pattern, quiz["date"]), \
                f"Quiz {quiz['id']}: date '{quiz['date']}' is not YYYY-MM-DD format"

    def test_context_and_explanation_have_content(self):
        """context와 explanation은 의미 있는 길이를 갖는다"""
        for quiz in QUIZ_LIST:
            assert len(quiz["context"]) > 20, \
                f"Quiz {quiz['id']}: context too short"
            assert len(quiz["explanation"]) > 20, \
                f"Quiz {quiz['id']}: explanation too short"
