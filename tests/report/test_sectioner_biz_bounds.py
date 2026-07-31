"""사업의내용 절 경계 회귀 테스트 (V-074).

종전 구현은 경계가 **아예 없었다** — `html[첫매치 : 첫매치+800_000]`. 전수 표본이
두 방향의 오염을 잡았다:
  · 시작: 첫 매치가 절 머리글인 보고서는 172/294뿐. 나머지 122건(41%)은 **목차 표 셀**
    (`<TD>II. 사업의 내용</TD>`)이나 **본문 참조 문장**에서 시작해 I. 회사의 개요부터 담았다.
  · 종료: 표본 196 중 189건(96%)이 800k를 꽉 채웠는데 절 실길이 중앙은 144,978자 —
    나머지는 III. 재무에 관한 사항 이후가 통째로 딸려온 것이다.

fixture는 전부 **실공시 발췌**(머리 주석에 ticker·rcept_no 명시)이고 머리글·경계 마크업은
원문 그대로다. 완화하려면 어느 실공시가 왜 달라졌는지부터 설명할 것.
"""

import os
import re

import pytest

from modules.report.sectioner import _BIZ_HEAD, find_biz_section

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


# (fixture, 잘못된 선행 후보가 있나, 변종 설명)
BIZ_BOUND_CASES = [
    ("biz_toc_cell.xml", True, "목차 표 셀이 진짜 머리글보다 앞선다 (064350)"),
    ("biz_inline_ref.xml", True, "본문 참조 문장이 진짜 머리글보다 앞선다 (032500)"),
    ("biz_boundary_iii.xml", False, "정상 머리글 + III. 재무에 관한 사항 경계 (005930)"),
]


@pytest.mark.parametrize("fname,has_decoy,desc", BIZ_BOUND_CASES)
def test_start_is_the_title_heading_not_the_first_match(fname, has_decoy, desc):
    """시작점은 **머리글**이어야 한다 — 목차 셀·본문 참조가 아니라."""
    html = _load(fname)
    bounds = find_biz_section(html)
    assert bounds is not None, desc
    start, _ = bounds
    # 시작 지점은 TITLE 머리글을 열고 있어야 한다
    assert html[start:].startswith("<TITLE"), desc
    if has_decoy:
        first = re.search(_BIZ_HEAD[0], html)
        # 옛 동작(첫 매치)은 미끼에 걸렸다 — 새 규칙은 그보다 뒤에서 시작한다
        assert first is not None and first.start() < start, desc


@pytest.mark.parametrize("fname,has_decoy,desc", BIZ_BOUND_CASES)
def test_end_stops_at_next_section_title(fname, has_decoy, desc):
    """종료는 다음 절의 TITLE 머리글에서 끊긴다 — 문서 끝까지 삼키지 않는다."""
    html = _load(fname)
    start, end = find_biz_section(html)
    assert end < len(html), f"{desc}: 절이 문서 끝까지 갔다"
    assert end > start, desc
    # 끊긴 자리 바로 뒤는 다음 절 TITLE이다
    assert re.match(
        r"<TITLE[^>]*>\s*(?:III|IV|IX|VIII|VII|VI|V|XII|XI|X)\.\s*[가-힣]",
        html[end:], re.I,
    ), f"{desc}: 종료 지점이 다음 절 머리글이 아니다"


@pytest.mark.parametrize("fname,has_decoy,desc", BIZ_BOUND_CASES)
def test_next_section_body_is_not_included(fname, has_decoy, desc):
    """잘라낸 구간에 다음 절 머리글이 들어있으면 안 된다(오염 0)."""
    html = _load(fname)
    start, end = find_biz_section(html)
    seg = html[start:end]
    assert not re.search(
        r"<TITLE[^>]*>\s*(?:III|IV|IX|VIII|VII|VI|V|XII|XI|X)\.\s*[가-힣]", seg, re.I
    ), desc


def test_returns_none_when_no_heading():
    """머리글이 없으면 None — [첨부정정]사업보고서처럼 본문 절이 없는 공시(실측 4건)."""
    assert find_biz_section("<TITLE>정 정 신 고 (보고)</TITLE><P>내용</P>") is None
