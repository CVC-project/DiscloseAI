"""섹셔너 주석 머리글 마크업 변종 회귀 테스트 (V-070).

전수 계측에서 드러난 사실: 최신연도 2,570사 중 **1,559사가 통째로 미섹셔닝**이었고,
그 중 1,053사는 연결주석이 원문에 멀쩡히 있는데 머리글 마크업이 달라서 안 잡힌 것이었다.
여기 fixture는 전부 **실공시 발췌**(`fixtures/*.xml` 머리 주석에 ticker·rcept_no 명시)로,
머리글·절 경계 마크업은 원문 그대로다 — 합성 문자열로 통과시키지 않는다.

각 케이스는 "이 변종을 못 읽으면 특수관계자 주석을 잃는다"를 박제한다. 완화하려면
어느 실공시가 왜 달라졌는지부터 설명할 것.
"""

import os
import re

import pytest

from modules.report import sectioner

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


# (fixture, 최소 노트 수, 특수관계자 주번호, 제목 접두, 본문 표 기대, 변종 설명)
#  · 본문 표 기대=False는 **원문에 거래 표가 없는 회사** — 주요 경영진 보상만 적은 유형
#    (실측 37사). 섹셔닝을 고쳐도 열리지 않는 것이 정상이라 표를 요구하지 않는다.
CONN_VARIANTS = [
    ("f1b_jusuk_dash.xml", 35, "33", "특수관계자", True, "주석N - 제목 (연결) — 영풍"),
    ("f1b_jusuk_prefix_dash.xml", 35, "38", "특수관계자", True, "주석 - N. 제목 - 연결 (연결) — 롯데칠성"),
    ("f1b_bracket_no.xml", 35, "40", "특수관계자", True, "[NN] 제목 (연결) — 우리기술투자"),
    ("f1_alpha_subno.xml", 40, "35", "특수관계자", True, "알파벳 하위번호 6-A/6-B — 유안타증권"),
    ("f1_dup_no.xml", 40, "42", "특수관계자", True, "같은 번호 재등장(주16 2회) — 신세계"),
    ("f1_out_of_order.xml", 35, "37", "특수관계자", True, "원문 번호 역전 38→37 — GS건설"),
    ("f2_p_headings.xml", 25, "26", "특수관계자", True, "본문 <P>N. 제목 — 케이알모터스"),
    ("f2_mid_paragraph.xml", 25, "28", "특수관계자", True, "문단 중간 머리글 — 삼천리"),
    ("f2_after_span.xml", 35, "39", "특수관계자", True, "</SPAN> 직후 머리글"),
    ("f1_stray_suffix.xml", 25, "32", "특수관계자", False, "무관한 (연결) 제목 1개 → F2 폴백 — 제이알글로벌리츠"),
]


@pytest.mark.parametrize("name,min_notes,rp_no,rp_prefix,has_table,desc", CONN_VARIANTS)
def test_conn_variant_yields_related_party_note(
    name, min_notes, rp_no, rp_prefix, has_table, desc
):
    notes = sectioner._split_conn_notes(_load(name))
    assert len(notes) >= min_notes, f"{desc}: 노트 {len(notes)}개 (<{min_notes})"
    rp = [(no, title) for no, title, _ in notes if "특수관계" in title]
    assert rp, f"{desc}: 특수관계자 주석 미검출"
    assert rp[0][0] == rp_no, f"{desc}: 주번호 {rp[0][0]} != {rp_no}"
    # 소비 측(relation reports_source)이 제목 접두로 거르므로 접두가 계약이다
    assert rp[0][1].startswith(rp_prefix), f"{desc}: 제목 '{rp[0][1]}'"
    body = [h for no, _, h in notes if no == rp_no][0]
    if has_table:
        # 머리글만 잡고 끝나면 소용없다 — 상대 목록 표가 본문에 들어와야 한다
        assert len(body) > 3000, f"{desc}: 특수관계자 주석 본문 {len(body)}자"
        assert "<TABLE" in body.upper(), f"{desc}: 본문에 표 없음"
        assert re.search(r"[가-힣]{2,}", sectioner._to_md(body)), f"{desc}: 표에 한글 없음"
    else:
        assert len(body) > 200, f"{desc}: 본문 {len(body)}자"


def test_sep_notes_only_for_non_consolidating_filer():
    """연결 미작성사(신라섬유)는 개별 재무제표 주석에서 특수관계자를 얻는다."""
    html = _load("f2_sep_notes.xml")
    assert sectioner._split_conn_notes(html) == [], "연결주석이 없어야 하는 표본"
    notes = sectioner._split_sep_notes(html)
    assert len(notes) >= 30
    rp = [(no, t) for no, t, _ in notes if "특수관계" in t]
    assert rp and rp[0][0] == "33" and rp[0][1].startswith("특수관계자")


def test_consolidated_filer_never_gets_sep_section():
    """연결주석이 있으면 별도주석은 담지 않는다(리더 판정 2026-07-30).

    별도는 종속기업 거래가 내부거래로 제거되지 않아 금액 의미가 다르다 — 같은 회사에
    두 판이 공존하면 안 된다. section_all의 분기 조건을 함수 수준에서 박제.
    """
    for name in ("f2_p_headings.xml", "f1b_jusuk_dash.xml"):
        html = _load(name)
        conn = sectioner._split_conn_notes(html)
        assert conn, f"{name}: 연결주석 표본이어야 함"
        # section_all은 conn이 비었을 때만 sep을 채운다
        assert not (not conn and sectioner._split_sep_notes(html))


# ── 하위 규칙 단위 테스트 ──


def test_note_key_reads_alphabetic_subnumber():
    """'6-A' < '6-B' — 못 읽으면 둘 다 (6,0)이라 번호 역행으로 오판해 뒤를 다 버린다."""
    assert sectioner._note_key("6-A") == (6, 1)
    assert sectioner._note_key("6-B") == (6, 2)
    assert sectioner._note_key("6-A") < sectioner._note_key("6-B")
    assert sectioner._note_key("31-6") == (31, 6)
    assert sectioner._note_key("3") == (3, 0)


def test_split_notes_stops_at_separate_fs_reset():
    """번호가 1~2로 리셋되면 별도 주석 진입 → 중단(NAVER 주37 사고 방어)."""
    html = (
        "<TITLE>1. 일반사항 (연결)</TITLE>a"
        "<TITLE>30. 우발부채 (연결)</TITLE>b"
        "<TITLE>1. 일반사항 (연결)</TITLE>별도주석이라 담으면 안 됨"
    )
    notes = sectioner._split_notes(html)
    assert [no for no, _, _ in notes] == ["1", "30"]
    assert "담으면 안 됨" not in notes[-1][2]


def test_tidy_title_strips_merged_numbers_and_tail():
    assert sectioner._tidy_title("특수관계자 - 연결") == "특수관계자"
    assert sectioner._tidy_title(", 11. 매출채권") == "매출채권"
    assert sectioner._tidy_title("-A 대여유가증권") == "A 대여유가증권"


def test_clean_note_title_cuts_body_that_follows_heading():
    """머리글 원소가 본문까지 품는 공시 — 제목만 잘라야 소비 측 접두 필터에 걸린다."""
    raw = "특수관계자 거래(1) 보고기간종료일 현재 당사의 지배기업은 다음과 같습니다."
    assert sectioner._clean_note_title(raw) == "특수관계자 거래"


def test_split_inbody_ignores_short_block():
    assert sectioner._find_note_section("<TITLE>3. 연결재무제표 주석</TITLE>해당사항 없음", "conn")
    assert sectioner._split_conn_notes("<TITLE>3. 연결재무제표 주석</TITLE>해당사항 없음") == []


def test_account_word_note_title_is_not_a_section_boundary():
    """V-098 (403870 HPSP 2025 실공시): 계정과목형 주석 제목은 절 경계가 아니다.

    주1~10은 <P>/<SPAN> 머리글이다가 **주11부터 <TITLE> 머리글로 전환**되는 문서에서
    `<TITLE>11. 재고자산</TITLE>`(목차 앵커 AASSOCNOTE 없음)이 `_SECT_BOUND_RE`의
    계정과목 어휘에 걸려 절 경계로 오판됐다 — 블록이 주10에서 잘려 주11~34
    (실공시에선 주33 특수관계자 포함)가 통째로 유실됐다. 경계 인정은 AASSOCNOTE가
    있는 진짜 목차 절뿐이다.
    """
    html = _load("f2_title_switch_account_word.xml")
    notes = sectioner._split_sep_notes(html)
    nos = [no for no, _, _ in notes]
    # 종전 버그: 주11에서 절단 → ['1'..'10']. 수정 후 11·12가 살아야 한다.
    assert "11" in nos and "12" in nos, f"주11 이후 유실: {nos}"
    assert any(no == "11" and "재고자산" in t for no, t, _ in notes)
    # 진짜 목차 절(AASSOCNOTE 보유 '6. 배당에 관한 사항')은 여전히 경계다 —
    # 배당 절 본문이 어떤 노트에도 섞이면 안 된다.
    assert not any("배당에 관한 회사의 정책" in b for _, _, b in notes)


def test_account_word_with_anchor_still_bounds():
    """AASSOCNOTE를 가진 계정과목형 TITLE은 종전대로 절 경계다(완화 아님을 박제)."""
    html = _load("f2_title_switch_account_word.xml").replace(
        '<TITLE ATOC="Y" ENG="11. Inventories" ATOCID="74">',
        '<TITLE ATOC="Y" AASSOCNOTE="D-0-3-8-2" ENG="11. Inventories" ATOCID="74">',
    )
    notes = sectioner._split_sep_notes(html)
    nos = [no for no, _, _ in notes]
    assert "11" not in nos, f"앵커 보유 경계가 무시됨: {nos}"
