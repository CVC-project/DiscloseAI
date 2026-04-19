"""transform/filters.py 단위 테스트."""

from __future__ import annotations

import pytest

from modules.relation.transform.filters import (
    is_foundation,
    is_personal_shareholder,
    match_to_top50,
)


@pytest.mark.parametrize(
    "name,relate,expected",
    [
        # 개인: 2~5자 한글 + 개인 관계어
        ("이재용", "최대주주의 특수관계인", True),
        ("홍라희", "최대주주의 특수관계인", True),
        ("이부진", "계열회사 임원", True),
        ("이서현", "계열회사 임원", True),
        # 법인: 관계어와 무관하게 False
        ("삼성생명보험㈜", "최대주주 본인", False),  # 법인 표기(㈜) 있음
        ("삼성물산(주)", "계열회사", False),
        # 애매한 경우 — relate 없으면 False
        ("홍길동", None, False),
        # 빈 문자열
        ("", None, False),
    ],
)
def test_is_personal_shareholder(name, relate, expected):
    assert is_personal_shareholder(name, relate) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("삼성생명공익재단", True),
        ("삼성문화재단", True),
        ("하나공익재단", True),
        ("포스코장학회", True),
        ("삼성전자", False),
        ("현대차", False),
        ("", False),
    ],
)
def test_is_foundation(name, expected):
    assert is_foundation(name) == expected


def test_match_to_top50():
    ticker_map = {"삼성전자": "005930", "sk하이닉스": "000660"}
    assert match_to_top50("삼성전자", ticker_map) == "005930"
    assert match_to_top50("sk하이닉스", ticker_map) == "000660"
    assert match_to_top50("없는기업", ticker_map) is None
