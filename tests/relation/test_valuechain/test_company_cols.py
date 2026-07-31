"""행=회사·열=거래유형 파서 회귀 테스트 (후속25).

부재 진단 B4b **711사**가 이 형태였다. 앞 4종 파서는 전부 `당기` 마커 **블록/열**을
앵커로 삼는데, 이 형태는 기간이 **표 밖 문맥**에 있거나(`(당기)`가 표 앞 형제)
**2단 헤더 상단**에 있어 전부 조용히 []를 냈다.

fixture는 전부 **실공시 발췌**(머리 주석에 rcept_no 명시)이고 표·앞 문맥 마크업은
원문 그대로다. 완화하려면 어느 실공시가 왜 달라졌는지부터 설명할 것.
"""

import os

import pytest

from modules.relation.valuechain.extract.related_party import (
    parse_note,
    parse_note_company_cols,
    parse_note_company_rows,
    parse_note_html_grid,
    parse_note_transposed,
)

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


def _load(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


CASES = [
    ("vc_company_cols_ctx.xml", "F-A 기간이 표 밖 문맥 (영원무역 계열)"),
    ("vc_company_cols_rev2.xml", "F-C 역순 2단 헤더 (네이처셀)"),
    ("vc_company_cols_noth.xml", "F-B 본표에 <th> 없음"),
]


@pytest.mark.parametrize("fname,desc", CASES)
def test_company_cols_yields_edges(fname, desc):
    """세 형태 모두 상대회사·금액이 나와야 한다."""
    items = parse_note_company_cols(_load(fname))
    assert items, desc
    assert all(i["amount"] > 0 for i in items), desc
    assert all(i["direction"] in ("customer", "supply", "capital_out", "capital_in")
               for i in items), desc


@pytest.mark.parametrize("fname,desc", CASES)
def test_existing_parsers_return_nothing_here(fname, desc):
    """앞 4종은 이 형태에서 [] — 신설이 **사슬 맨 끝**이라 기존 산출이 불변임을 박제.

    하나라도 값을 내기 시작하면 사슬 순서상 이 파서에 도달하지 않게 되므로,
    그때는 게이트 의미가 바뀐 것이니 반드시 A/B로 소실을 세야 한다.
    """
    html = _load(fname)
    assert not parse_note_transposed(html), desc
    assert not parse_note_html_grid(html), desc
    assert not parse_note(html), desc
    assert not parse_note_company_rows(html), desc


def test_current_period_only_prior_table_skipped():
    """당기 표만 담는다 — 같은 노트의 전기 표는 스킵(중복 방지).

    영원무역 계열 fixture는 당기·전기 표가 쌍으로 있고 당기 표의 상대는 6사다.
    전기까지 담으면 같은 상대가 두 번(다른 금액으로) 들어간다.
    """
    items = parse_note_company_cols(_load("vc_company_cols_ctx.xml"))
    names = [i["counterparty"] for i in items]
    assert len(names) == len(set(names)), f"상대 중복(전기 혼입 의심): {names}"
    # 실공시 실측: 당기 매출 상대 6사
    assert len(items) == 6
    by = {i["counterparty"]: i["amount"] for i in items}
    assert by["㈜영원무역"] == 28_407_000  # 원문 28,407천원
    assert by["㈜영원아웃도어"] == 138_944_000


def test_other_income_columns_are_not_captured():
    """`기타수익`·`기타비용`은 상거래 어휘가 아니므로 담지 않는다(금액 의미 유지).

    이 형태의 표는 그런 열을 흔히 달고 있다 — 어휘를 넓히면 매출·매입의 정의가 바뀐다.
    """
    items = parse_note_company_cols(_load("vc_company_cols_ctx.xml"))
    assert all("기타" not in i["label"] for i in items)
    # 원문에서 '지배기업의 대표이사 등 임원' 행은 기타수익·기타비용만 있어 제외된다
    assert all("임원" not in i["counterparty"] for i in items)


def test_balance_table_is_excluded():
    """`당기말` 헤더가 있는 잔액표는 표 전체 배제(후속22 규칙 승계)."""
    html = (
        '<p>(당기)</p><p>(단위: 천원)</p>'
        "<table><tr><th>특수관계자명</th><th>매출</th><th>당기말</th></tr>"
        "<tr><td>㈜가나다</td><td>1,000</td><td>500</td></tr></table>"
    )
    assert parse_note_company_cols(html) == []


def test_no_period_context_is_skipped():
    """기간 문맥이 없으면 담지 않는다 — 억지 매칭 금지(실측 293건)."""
    html = (
        '<p>(단위: 천원)</p>'
        "<table><tr><th>특수관계자명</th><th>매출</th></tr>"
        "<tr><td>㈜가나다</td><td>1,000</td></tr></table>"
    )
    assert parse_note_company_cols(html) == []
